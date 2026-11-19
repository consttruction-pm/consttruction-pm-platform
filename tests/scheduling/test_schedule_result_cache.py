"""P0-N: adaptive schedule-result cache.

The cache is execution-only: it can only return the payload produced for the
same immutable inputs. These tests pin the key coverage, tenant isolation,
weighted eviction and adaptive capacity behaviour.
"""

from __future__ import annotations

import threading

import pytest

from construction_pm.scheduling_result_cache import (
    CACHE_SCHEMA,
    CacheKey,
    ScheduleCacheError,
    ScheduleResultCache,
)


def _key(
    tenant: str = "tenant-a",
    project: str = "project-1",
    identity: str = "calc-1",
    engine: str = "cubi-26.0.0",
    snapshot_hash: str | None = "a" * 64,
) -> CacheKey:
    return CacheKey(
        tenant_id=tenant,
        project_id=project,
        calculation_identity=identity,
        engine_version=engine,
        snapshot_hash=snapshot_hash,
    )


def test_roundtrip_returns_an_immutable_copy():
    cache = ScheduleResultCache(max_weight_bytes=1024)
    cache.put(_key(), b'{"x":1}')
    assert cache.get(_key()) == b'{"x":1}'
    # Stored bytes are never aliased to the caller's buffer.
    mutable = bytearray(b"hello")
    cache.put(_key(identity="calc-2"), mutable)
    mutable[0] = ord("X")
    assert cache.get(_key(identity="calc-2")) == b"hello"


def test_key_covers_every_semantic_input():
    cache = ScheduleResultCache(max_weight_bytes=1024)
    cache.put(_key(), b"value")
    for other in (
        _key(tenant="tenant-b"),
        _key(project="project-2"),
        _key(identity="calc-2"),
        _key(engine="cubi-26.0.1"),
        _key(snapshot_hash="b" * 64),
    ):
        assert cache.get(other) is None
    assert cache.get(_key()) == b"value"


def test_schema_is_part_of_the_key():
    cache = ScheduleResultCache(max_weight_bytes=1024)
    cache.put(_key(), b"value")
    different = CacheKey(
        tenant_id="tenant-a",
        project_id="project-1",
        calculation_identity="calc-1",
        engine_version="cubi-26.0.0",
        schema="construction-pm/schedule-result-cache/v2",
    )
    assert different.digest() != _key().digest()
    assert cache.get(different) is None


def test_tenant_isolation_and_fair_share_eviction():
    cache = ScheduleResultCache(max_weight_bytes=1000, tenant_share=0.6)
    # Two tenants share the cache; each may hold at most 60 % of the capacity.
    for index in range(6):
        cache.put(_key(tenant="tenant-a", identity=f"a-{index}"), b"x" * 100)
        cache.put(_key(tenant="tenant-b", identity=f"b-{index}"), b"x" * 100)
    stats = cache.stats()
    assert stats["weight_bytes"] <= 1000
    # A single tenant cannot pin the whole cache: some of its entries are gone.
    tenant_a = [
        cache.get(_key(tenant="tenant-a", identity=f"a-{index}")) for index in range(6)
    ]
    assert tenant_a.count(None) >= 1
    assert stats["evictions"] >= 1


def test_weighted_lru_evicts_the_oldest_entry():
    cache = ScheduleResultCache(max_weight_bytes=250)
    cache.put(_key(identity="first"), b"x" * 100, weight=100)
    cache.put(_key(identity="second"), b"x" * 100, weight=100)
    cache.get(_key(identity="first"))  # promote
    cache.put(_key(identity="third"), b"x" * 100, weight=100)
    assert cache.get(_key(identity="second")) is None
    assert cache.get(_key(identity="first")) is not None
    assert cache.get(_key(identity="third")) is not None


def test_oversized_entry_is_rejected_without_evicting():
    cache = ScheduleResultCache(max_weight_bytes=100)
    assert cache.put(_key(), b"x" * 200) is False
    stats = cache.stats()
    assert stats["rejected_oversize"] == 1
    assert stats["entries"] == 0


def test_adaptation_shrinks_capacity_and_evicts_immediately():
    cache = ScheduleResultCache(max_weight_bytes=1000)
    for index in range(8):
        cache.put(_key(identity=f"id-{index}"), b"x" * 100)
    before = cache.stats()["weight_bytes"]
    assert before > 400
    capacity = cache.adapt(active_jobs=4, active_tenants=2, available_bytes=800)
    assert capacity == 140  # quarter of available memory, then the 4-project factor
    stats = cache.stats()
    assert stats["weight_bytes"] <= 200
    assert stats["evictions"] >= 1
    assert stats["last_adaptation"]["active_jobs"] == 4


def test_one_project_alone_keeps_the_full_capacity():
    cache = ScheduleResultCache(max_weight_bytes=1000)
    assert cache.adapt(active_jobs=1) == 1000
    assert cache.adapt(active_jobs=2) == 850
    assert cache.adapt(active_jobs=4) == 700


def test_stats_track_hit_ratio():
    cache = ScheduleResultCache(max_weight_bytes=1024)
    cache.put(_key(), b"value")
    cache.get(_key())
    cache.get(_key(identity="missing"))
    stats = cache.stats()
    assert stats["hits"] == 1 and stats["misses"] == 1
    assert stats["hit_ratio"] == pytest.approx(0.5)


def test_invalid_arguments_are_rejected():
    with pytest.raises(ScheduleCacheError):
        ScheduleResultCache(max_weight_bytes=0)
    with pytest.raises(ScheduleCacheError):
        ScheduleResultCache(tenant_share=0)
    with pytest.raises(ScheduleCacheError):
        CacheKey("", "p", "c", "e")
    with pytest.raises(ScheduleCacheError):
        CacheKey("t", "p", "c", "e", snapshot_hash="")
    cache = ScheduleResultCache(max_weight_bytes=10)
    with pytest.raises(ScheduleCacheError):
        cache.put(_key(), "not-bytes")  # type: ignore[arg-type]
    with pytest.raises(ScheduleCacheError):
        cache.get("not-a-key")  # type: ignore[arg-type]
    with pytest.raises(ScheduleCacheError):
        cache.adapt(active_jobs=-1)


def test_clear_empties_the_cache():
    cache = ScheduleResultCache(max_weight_bytes=1024)
    cache.put(_key(), b"value")
    cache.clear()
    assert cache.get(_key()) is None
    assert cache.stats()["entries"] == 0


def test_concurrent_access_is_consistent():
    cache = ScheduleResultCache(max_weight_bytes=10_000)

    def worker(index: int) -> None:
        for round_number in range(50):
            key = _key(identity=f"id-{index}-{round_number}")
            cache.put(key, b"x" * 10)
            cache.get(key)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    stats = cache.stats()
    assert stats["weight_bytes"] <= 10_000
    assert stats["hits"] == 400


def test_schema_constant_is_stable():
    assert CACHE_SCHEMA == "construction-pm/schedule-result-cache/v1"
