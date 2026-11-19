"""P0-N: adaptive, tenant-isolated cache for immutable schedule results.

A scheduling calculation is a pure function of an immutable snapshot and the
calculation identity (which already covers project, revision, calendar versions,
rules version, engine version, timezone and tenant). Re-evaluating exactly the
same inputs therefore cannot produce a different result, so the canonical output
can be reused instead of recomputed.

Rules
-----
* The key is derived from every input that can change a value: the semantic
  calculation identity (version 2), the engine version, the tenant and project,
  the snapshot hash when the caller has it, and a cache schema version. The
  float execution policy is deliberately *not* part of the key: it changes
  elapsed time only, and the existing equality tests prove the payload is the
  same for any worker count.
* A value is stored as immutable bytes (a canonical JSON payload). Nothing that
  is handed back to a caller aliases cached state.
* Capacity adapts to the number of active projects and to available memory, and
  a single tenant can never occupy the whole cache: the rest is evicted by
  weighted LRU within that tenant's fair share.
* Every cache operation is optional. A miss, a disabled cache or an over-sized
  entry falls through to a full calculation.
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable


CACHE_SCHEMA = "construction-pm/schedule-result-cache/v1"
DEFAULT_MAX_WEIGHT_BYTES = 256 * 1024 * 1024
DEFAULT_TENANT_SHARE = 0.6
DEFAULT_MAX_ENTRIES = 4096
_ENTRY_OVERHEAD_BYTES = 128


class ScheduleCacheError(ValueError):
    pass


@dataclass(frozen=True)
class CacheKey:
    """Every deterministic input that selects one canonical result."""

    tenant_id: str
    project_id: str
    calculation_identity: str
    engine_version: str
    snapshot_hash: str | None = None
    schema: str = CACHE_SCHEMA

    def __post_init__(self) -> None:
        for name in ("tenant_id", "project_id", "calculation_identity", "engine_version"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ScheduleCacheError("INVALID_CACHE_KEY")
        if self.snapshot_hash is not None and (
            not isinstance(self.snapshot_hash, str) or not self.snapshot_hash
        ):
            raise ScheduleCacheError("INVALID_CACHE_KEY")
        if not isinstance(self.schema, str) or not self.schema:
            raise ScheduleCacheError("INVALID_CACHE_KEY")

    def digest(self) -> str:
        # No hashing needed for correctness: the tuple is used as the dict key.
        return (
            f"{self.schema}|{self.tenant_id}|{self.project_id}|"
            f"{self.calculation_identity}|{self.engine_version}|"
            f"{self.snapshot_hash or ''}"
        )


@dataclass(frozen=True)
class CacheEntry:
    key: CacheKey
    value: bytes
    weight: int
    stored_at: float

    def __post_init__(self) -> None:
        if not isinstance(self.value, (bytes, bytearray)):
            raise ScheduleCacheError("CACHE_VALUE_MUST_BE_BYTES")
        if self.weight < 1:
            raise ScheduleCacheError("INVALID_CACHE_WEIGHT")


class _TenantStore:
    __slots__ = ("entries", "weight")

    def __init__(self) -> None:
        self.entries: "OrderedDict[str, CacheEntry]" = OrderedDict()
        self.weight = 0


class ScheduleResultCache:
    """Weighted-LRU cache with adaptive capacity and per-tenant fair share."""

    def __init__(
        self,
        *,
        max_weight_bytes: int = DEFAULT_MAX_WEIGHT_BYTES,
        tenant_share: float = DEFAULT_TENANT_SHARE,
        max_entries: int = DEFAULT_MAX_ENTRIES,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_weight_bytes < 1:
            raise ScheduleCacheError("INVALID_CACHE_CAPACITY")
        if not (0.0 < tenant_share <= 1.0):
            raise ScheduleCacheError("INVALID_TENANT_SHARE")
        if max_entries < 1:
            raise ScheduleCacheError("INVALID_MAX_ENTRIES")
        self._max_weight_bytes = max_weight_bytes
        self._tenant_share = tenant_share
        self._max_entries = max_entries
        self._clock = clock
        self._capacity = max_weight_bytes
        self._tenants: dict[str, _TenantStore] = {}
        self._total_weight = 0
        self._total_entries = 0
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._rejected = 0
        self._stores = 0
        self._last_adaptation: dict[str, object] = {}
        self._lock = threading.RLock()

    # -- capacity ---------------------------------------------------------

    @property
    def capacity_bytes(self) -> int:
        return self._capacity

    def adapt(
        self,
        *,
        active_jobs: int,
        active_tenants: int | None = None,
        available_bytes: int | None = None,
    ) -> int:
        with self._lock:
            return self._adapt(
                active_jobs=active_jobs,
                active_tenants=active_tenants,
                available_bytes=available_bytes,
            )

    def _adapt(
        self,
        *,
        active_jobs: int,
        active_tenants: int | None = None,
        available_bytes: int | None = None,
    ) -> int:
        """Recompute capacity from current load and the machine's free memory.

        One project alone may use the full configured cache. Several concurrent
        projects shrink the total so the memory stays available to the
        calculations themselves, and each tenant receives a fair share. When
        the process reports low available memory the capacity follows it down
        and eviction happens immediately, never on the next insert.
        """
        if isinstance(active_jobs, bool) or not isinstance(active_jobs, int) or active_jobs < 0:
            raise ScheduleCacheError("INVALID_ACTIVE_JOBS")
        if active_tenants is not None and (
            isinstance(active_tenants, bool)
            or not isinstance(active_tenants, int)
            or active_tenants < 0
        ):
            raise ScheduleCacheError("INVALID_ACTIVE_TENANTS")
        if available_bytes is not None and available_bytes < 0:
            raise ScheduleCacheError("INVALID_AVAILABLE_BYTES")
        capacity = self._max_weight_bytes
        if available_bytes is not None:
            # Never claim more than a quarter of the memory the process may use.
            capacity = min(capacity, max(0, available_bytes // 4))
        if active_jobs <= 1:
            capacity = max(1, capacity)
        elif active_jobs <= 2:
            capacity = max(1, int(capacity * 0.85))
        else:
            capacity = max(1, int(capacity * 0.7))
        self._capacity = capacity
        self._last_adaptation = {
            "active_jobs": active_jobs,
            "active_tenants": active_tenants,
            "available_bytes": available_bytes,
            "capacity_bytes": capacity,
        }
        self._enforce_capacity(active_tenants=max(1, (active_tenants or 0)))
        return capacity

    def _tenant_capacity(self, active_tenants: int) -> int:
        share = self._capacity / max(1, active_tenants)
        return max(1, int(share * self._tenant_share) if active_tenants > 1 else self._capacity)

    # -- core operations --------------------------------------------------

    def get(self, key: CacheKey) -> bytes | None:
        with self._lock:
            return self._get(key)

    def _get(self, key: CacheKey) -> bytes | None:
        if not isinstance(key, CacheKey):
            raise ScheduleCacheError("INVALID_CACHE_KEY_TYPE")
        store = self._tenants.get(key.tenant_id)
        if store is None:
            self._misses += 1
            return None
        entry = store.entries.get(key.digest())
        if entry is None:
            self._misses += 1
            return None
        store.entries.move_to_end(key.digest())
        self._hits += 1
        # Return an immutable copy so no caller can mutate cached state.
        return bytes(entry.value)

    def put(self, key: CacheKey, value: bytes, *, weight: int | None = None) -> bool:
        with self._lock:
            return self._put(key, value, weight=weight)

    def _put(self, key: CacheKey, value: bytes, *, weight: int | None = None) -> bool:
        if not isinstance(key, CacheKey):
            raise ScheduleCacheError("INVALID_CACHE_KEY_TYPE")
        if isinstance(value, bytearray):
            value = bytes(value)
        if not isinstance(value, bytes):
            raise ScheduleCacheError("CACHE_VALUE_MUST_BE_BYTES")
        size = weight if weight is not None else len(value) + _ENTRY_OVERHEAD_BYTES
        if isinstance(size, bool) or not isinstance(size, int) or size < 1:
            raise ScheduleCacheError("INVALID_CACHE_WEIGHT")
        if size > self._capacity:
            self._rejected += 1
            return False
        digest = key.digest()
        store = self._tenants.setdefault(key.tenant_id, _TenantStore())
        existing = store.entries.pop(digest, None)
        if existing is not None:
            store.weight -= existing.weight
            self._total_weight -= existing.weight
            self._total_entries -= 1
        entry = CacheEntry(key=key, value=value, weight=size, stored_at=self._clock())
        store.entries[digest] = entry
        store.weight += size
        self._total_weight += size
        self._total_entries += 1
        self._stores += 1
        self._evict_for(key.tenant_id, keep=digest, tenant_capacity=self._tenant_capacity(
            max(1, len(self._tenants))
        ))
        return digest in store.entries

    def _evict_for(self, tenant_id: str, *, keep: str, tenant_capacity: int) -> None:
        store = self._tenants[tenant_id]
        # First within the tenant's own fair share.
        while store.weight > tenant_capacity and len(store.entries) > 1:
            oldest_key, oldest = next(iter(store.entries.items()))
            if oldest_key == keep:
                oldest_key, oldest = next(reversed(store.entries.items()))
            store.entries.pop(oldest_key, None)
            store.weight -= oldest.weight
            self._total_weight -= oldest.weight
            self._total_entries -= 1
            self._evictions += 1
        # Then globally, in case several tenants are over together.
        while self._total_weight > self._capacity and self._total_entries > 1:
            victim_tenant = None
            victim_key = None
            for name, candidate in self._tenants.items():
                if not candidate.entries:
                    continue
                first_key = next(iter(candidate.entries))
                if victim_tenant is None or candidate.entries[first_key].stored_at < (
                    self._tenants[victim_tenant].entries[victim_key].stored_at
                ):
                    victim_tenant = name
                    victim_key = first_key
            if victim_tenant is None:
                break
            if victim_tenant == tenant_id and victim_key == keep and len(self._tenants[victim_tenant].entries) > 1:
                victim_key = next(key for key in self._tenants[victim_tenant].entries if key != keep)
            elif victim_tenant == tenant_id and victim_key == keep:
                break
            removed = self._tenants[victim_tenant].entries.pop(victim_key)
            self._tenants[victim_tenant].weight -= removed.weight
            self._total_weight -= removed.weight
            self._total_entries -= 1
            self._evictions += 1

    def _enforce_capacity(self, *, active_tenants: int) -> None:
        if self._total_weight <= self._capacity:
            return
        for tenant_id in list(self._tenants):
            store = self._tenants[tenant_id]
            tenant_capacity = self._tenant_capacity(active_tenants)
            while store.weight > tenant_capacity and store.entries:
                _, removed = store.entries.popitem(last=False)
                store.weight -= removed.weight
                self._total_weight -= removed.weight
                self._total_entries -= 1
                self._evictions += 1
        while self._total_weight > self._capacity and self._total_entries > 0:
            victim = None
            for name, candidate in self._tenants.items():
                if candidate.entries:
                    oldest_key = next(iter(candidate.entries))
                    entry = candidate.entries[oldest_key]
                    if victim is None or entry.stored_at < victim[2].stored_at:
                        victim = (name, oldest_key, entry)
            if victim is None:
                break
            name, oldest_key, entry = victim
            self._tenants[name].entries.pop(oldest_key)
            self._tenants[name].weight -= entry.weight
            self._total_weight -= entry.weight
            self._total_entries -= 1
            self._evictions += 1

    # -- observation ------------------------------------------------------

    def stats(self) -> dict[str, object]:
        with self._lock:
            return self._stats()

    def _stats(self) -> dict[str, object]:
        lookups = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "stores": self._stores,
            "evictions": self._evictions,
            "rejected_oversize": self._rejected,
            "entries": self._total_entries,
            "weight_bytes": self._total_weight,
            "capacity_bytes": self._capacity,
            "tenants": len(self._tenants),
            "hit_ratio": (self._hits / lookups) if lookups else 0.0,
            "last_adaptation": dict(self._last_adaptation),
        }

    def clear(self) -> None:
        with self._lock:
            self._clear()

    def _clear(self) -> None:
        self._tenants.clear()
        self._total_weight = 0
        self._total_entries = 0


__all__ = [
    "CACHE_SCHEMA",
    "CacheEntry",
    "CacheKey",
    "DEFAULT_MAX_ENTRIES",
    "DEFAULT_MAX_WEIGHT_BYTES",
    "DEFAULT_TENANT_SHARE",
    "ScheduleCacheError",
    "ScheduleResultCache",
]
