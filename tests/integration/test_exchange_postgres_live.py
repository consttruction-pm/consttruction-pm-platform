from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.application.authorization import (  # noqa: E402
    AuthorizationContext,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope  # noqa: E402
from construction_pm.client_sync.postgres_transaction import (  # noqa: E402
    PostgresTransactionManager,
)
from construction_pm.exchange_application import (  # noqa: E402
    ExchangeService,
    RESOURCE_COLUMNS,
)
from construction_pm.exchange_persistence import PostgresExchangeStore  # noqa: E402
from construction_pm.p6_resource_master_repository import (  # noqa: E402
    PostgresP6ResourceRepository,
)


RUN = uuid.uuid4().hex[:10]
TENANT = f"exchange-t-{RUN}"
PROJECT = f"exchange-p-{RUN}"
SCOPE = BackendScope(TENANT, PROJECT, 1)
AUTH = AuthorizationContext(TENANT, PROJECT, "u1", frozenset({"project_admin"}))


class _ResourceAPI:
    def __init__(self, repository, *, fail_on: str | None = None) -> None:
        self.repository = repository
        self.fail_on = fail_on
        self.created: list[str] = []

    def create(self, resource, *, auth_context):
        if resource.resource_id == self.fail_on:
            raise RuntimeError("simulated write failure")
        self.repository.save(resource)
        self.created.append(resource.resource_id)


def _csv(ids: list[str]) -> str:
    lines = [",".join(RESOURCE_COLUMNS)]
    for resource_id in ids:
        lines.append(f"{resource_id},Name,labor,,,,,,true")
    return "\n".join(lines) + "\n"


def _service(connection, *, fail_on: str | None = None):
    repository = PostgresP6ResourceRepository(connection)
    repository.initialize()
    store = PostgresExchangeStore(connection)
    store.initialize()
    api = _ResourceAPI(repository, fail_on=fail_on)
    service = ExchangeService(
        store=store,
        activity_repository=type("A", (), {"list": lambda self, scope: ()})(),
        resource_repository=repository,
        resource_api=api,
        risk_store=type("R", (), {})(),
        authorization_policy=default_project_policy(),
        transaction_manager=PostgresTransactionManager(connection),
    )
    return service, repository, store


def test_live_postgres_exchange_apply_replay_and_idempotency_conflict():
    with psycopg.connect(DSN) as connection:
        service, repository, store = _service(connection)
        content = _csv([f"R-{RUN}-1", f"R-{RUN}-2"])

        applied = service.apply_import(
            scope=SCOPE,
            dataset="resources",
            content=content,
            idempotency_key=f"key-{RUN}",
            context=AUTH,
            occurred_at=datetime(2026, 1, 5, tzinfo=timezone.utc),
        )
        assert applied["valid"] is True
        assert applied["atomic"] is True
        assert applied["created"] == [f"R-{RUN}-1", f"R-{RUN}-2"]
        assert len(repository.list(TENANT, PROJECT, 1)) == 2

        replay = service.apply_import(
            scope=SCOPE,
            dataset="resources",
            content=content,
            idempotency_key=f"key-{RUN}",
            context=AUTH,
            occurred_at=datetime(2026, 1, 5, tzinfo=timezone.utc),
        )
        assert replay["replayed"] is True
        assert replay["run_id"] == applied["run_id"]
        assert len(repository.list(TENANT, PROJECT, 1)) == 2

        with pytest.raises(Exception, match="EXCHANGE_IDEMPOTENCY_KEY_REUSE"):
            service.apply_import(
                scope=SCOPE,
                dataset="resources",
                content=content.replace("Name", "Changed"),
                idempotency_key=f"key-{RUN}",
                context=AUTH,
                occurred_at=datetime(2026, 1, 5, tzinfo=timezone.utc),
            )


def test_live_postgres_exchange_failure_rolls_back_every_row():
    with psycopg.connect(DSN) as connection:
        service, repository, store = _service(connection, fail_on=f"FAIL-{RUN}")
        # A separate project keeps this rollback proof independent of the
        # successful apply above, which shares the module tenant.
        atomic_scope = BackendScope(TENANT, f"{PROJECT}-atomic", 1)
        atomic_auth = AuthorizationContext(
            TENANT, f"{PROJECT}-atomic", "u1", frozenset({"project_admin"})
        )
        content = _csv([f"OK-{RUN}", f"FAIL-{RUN}"])

        failed = service.apply_import(
            scope=atomic_scope,
            dataset="resources",
            content=content,
            idempotency_key=f"atomic-{RUN}",
            context=atomic_auth,
            occurred_at=datetime(2026, 1, 5, tzinfo=timezone.utc),
        )

        assert failed["valid"] is False
        assert failed["atomic"] is True
        assert repository.list(TENANT, f"{PROJECT}-atomic", 1) == ()
        assert store.read_idempotency(TENANT, f"{PROJECT}-atomic", f"atomic-{RUN}") is None
        assert any(
            run.mode == "apply" and not run.result["valid"]
            for run in store.list_runs(TENANT, f"{PROJECT}-atomic")
        )
