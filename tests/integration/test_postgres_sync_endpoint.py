import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

psycopg = pytest.importorskip("psycopg")

from construction_pm.client_sync.api_endpoint import PostgresSyncEndpoint
from construction_pm.client_sync.sync_outcome import SyncDisposition

DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")


class CountingHandler:
    def __init__(self, entered=None, release=None):
        self.calls = 0
        self._lock = threading.Lock()
        self.entered = entered
        self.release = release

    def handle(self, mutation):
        with self._lock:
            self.calls += 1
        if self.entered is not None:
            self.entered.set()
        if self.release is not None:
            assert self.release.wait(5)


@pytest.fixture
def postgres():
    if not DSN:
        pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is required for live PostgreSQL tests")
    yield


def _body(key: str, mutation_id: str = "mutation-1") -> dict[str, object]:
    return {
        "contract_version": "sync-mutation.v1",
        "mutation_id": mutation_id,
        "tenant_id": "tenant-live",
        "project_id": "project-live",
        "expected_revision": 1,
        "operation": "update_activity",
        "payload": {"id": "A1"},
        "idempotency_key": key,
    }


def _headers():
    return {
        "Idempotency-Key": "placeholder",
        "X-Tenant-Id": "tenant-live",
        "X-Project-Id": "project-live",
        "X-Project-Revision": "1",
    }


def _cleanup(key: str) -> None:
    with psycopg.connect(DSN) as connection:
        connection.execute(
            "DELETE FROM sync_idempotency WHERE tenant_id=%s AND project_id=%s AND idempotency_key=%s",
            ("tenant-live", "project-live", key),
        )
        connection.commit()


def test_http_sync_endpoint_replays_durable_outcome_after_restart(postgres):
    key = f"http-replay-{uuid.uuid4()}"
    handler = CountingHandler()
    try:
        headers = _headers()
        headers["Idempotency-Key"] = key
        with psycopg.connect(DSN) as connection:
            first = PostgresSyncEndpoint("tenant-live", "project-live", connection, handler).post(
                _body(key), headers
            )

        second_handler = CountingHandler()
        with psycopg.connect(DSN) as connection:
            second = PostgresSyncEndpoint(
                "tenant-live", "project-live", connection, second_handler
            ).post(_body(key), headers)

        assert first["disposition"] == SyncDisposition.ACKNOWLEDGED.value
        assert second == first
        assert handler.calls == 1
        assert second_handler.calls == 0
    finally:
        _cleanup(key)


def test_http_sync_endpoint_rejects_reused_key_after_restart(postgres):
    key = f"http-reuse-{uuid.uuid4()}"
    headers = _headers()
    headers["Idempotency-Key"] = key
    try:
        with psycopg.connect(DSN) as connection:
            PostgresSyncEndpoint(
                "tenant-live", "project-live", connection, CountingHandler()
            ).post(_body(key), headers)

        changed = _body(key, mutation_id="mutation-2")
        changed["payload"] = {"id": "A2"}
        with psycopg.connect(DSN) as connection:
            result = PostgresSyncEndpoint(
                "tenant-live", "project-live", connection, CountingHandler()
            ).post(changed, headers)

        assert result["disposition"] == SyncDisposition.REJECTED.value
        assert result["error_code"] == "IDEMPOTENCY_KEY_REUSE"
    finally:
        _cleanup(key)


def test_http_sync_endpoint_same_key_concurrent_requests_execute_once(postgres):
    key = f"http-concurrent-{uuid.uuid4()}"
    entered = threading.Event()
    release = threading.Event()
    handler = CountingHandler(entered=entered, release=release)
    headers = _headers()
    headers["Idempotency-Key"] = key

    try:
        def run():
            with psycopg.connect(DSN) as connection:
                return PostgresSyncEndpoint(
                    "tenant-live", "project-live", connection, handler
                ).post(_body(key), headers)

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run), pool.submit(run)]
            assert entered.wait(5)
            assert handler.calls == 1
            release.set()
            results = [future.result(timeout=5) for future in futures]

        assert all(result["disposition"] == SyncDisposition.ACKNOWLEDGED.value for result in results)
        assert handler.calls == 1
    finally:
        release.set()
        _cleanup(key)
