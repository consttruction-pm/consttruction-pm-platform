"""P0-G: one adaptive execution budget for the authoritative scheduler.

Every execution surface runs the same engine and the same engine version; this
module only decides how many calculations may run at once. It reads the capacity
the process can actually use (CPU affinity, cgroup quota, available memory)
instead of ``os.cpu_count()``, and it exposes a single process-wide permit set so
that two executors in the same process cannot add up to more than the budget.

Rules
-----
* The budget is derived, not guessed. Values come from the kernel/cgroup files
  or from explicit test inputs; nothing is inferred from a hostname or a
  hard-coded worker count.
* The budget is a hard cap. A controller may dispatch fewer jobs when the queue
  is empty, but never more than the budget, and every job holds a permit for the
  whole calculation.
* The budget never changes scheduling semantics. It contains no calculation
  logic and no per-surface variant; Cloud, Local Server, Desktop and a Worker
  all use this one module and the same engine identity.
"""

from __future__ import annotations

import math
import os
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Iterator, Sequence


DEFAULT_PER_JOB_MEMORY_BYTES = 512 * 1024 * 1024
DEFAULT_MEMORY_RESERVE_FRACTION = Decimal("0.25")
DEFAULT_MAX_WORKERS = 64
WORKER_COUNT_ENV = "CONSTRUCTION_PM_SCHEDULING_WORKERS"


class SchedulingBudgetError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Capacity detection
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EffectiveCapacity:
    """Capacity the current process may really use."""

    cpu_affinity: int
    memory_available_bytes: int
    cgroup_cpu_cores: float | None = None
    cgroup_memory_limit_bytes: int | None = None
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if isinstance(self.cpu_affinity, bool) or not isinstance(self.cpu_affinity, int):
            raise SchedulingBudgetError("INVALID_CPU_AFFINITY")
        if self.cpu_affinity < 1:
            raise SchedulingBudgetError("INVALID_CPU_AFFINITY")
        if self.memory_available_bytes < 0:
            raise SchedulingBudgetError("INVALID_MEMORY_AVAILABLE")
        if self.cgroup_cpu_cores is not None and self.cgroup_cpu_cores <= 0:
            raise SchedulingBudgetError("INVALID_CGROUP_CPU_QUOTA")
        if (
            self.cgroup_memory_limit_bytes is not None
            and self.cgroup_memory_limit_bytes <= 0
        ):
            raise SchedulingBudgetError("INVALID_CGROUP_MEMORY_LIMIT")

    @property
    def effective_cores(self) -> float:
        cores = float(self.cpu_affinity)
        if self.cgroup_cpu_cores is not None:
            cores = min(cores, self.cgroup_cpu_cores)
        return max(cores, 0.01)

    @property
    def effective_memory_bytes(self) -> int:
        limit = self.memory_available_bytes
        if self.cgroup_memory_limit_bytes is not None:
            limit = min(limit, self.cgroup_memory_limit_bytes)
        return max(limit, 0)

    def as_dict(self) -> dict[str, object]:
        return {
            "cpu_affinity": self.cpu_affinity,
            "cgroup_cpu_cores": self.cgroup_cpu_cores,
            "memory_available_bytes": self.memory_available_bytes,
            "cgroup_memory_limit_bytes": self.cgroup_memory_limit_bytes,
            "effective_cores": round(self.effective_cores, 4),
            "effective_memory_bytes": self.effective_memory_bytes,
            "provenance": list(self.provenance),
        }


def parse_cgroup_cpu_max(text: str) -> float | None:
    """Parse cgroup v2 ``cpu.max`` ("quota period" or "max period")."""
    fields = text.split()
    if len(fields) != 2:
        raise SchedulingBudgetError("INVALID_CGROUP_CPU_MAX")
    quota, period = fields
    if quota == "max":
        return None
    try:
        quota_value = int(quota)
        period_value = int(period)
    except ValueError as error:
        raise SchedulingBudgetError("INVALID_CGROUP_CPU_MAX") from error
    if quota_value <= 0 or period_value <= 0:
        raise SchedulingBudgetError("INVALID_CGROUP_CPU_MAX")
    return quota_value / period_value


def parse_cgroup_v1_cpu_quota(quota: str, period: str) -> float | None:
    """Parse cgroup v1 ``cpu.cfs_quota_us`` / ``cpu.cfs_period_us``."""
    try:
        quota_value = int(quota.strip())
        period_value = int(period.strip())
    except ValueError as error:
        raise SchedulingBudgetError("INVALID_CGROUP_V1_CPU_QUOTA") from error
    if quota_value == -1:
        return None
    if quota_value <= 0 or period_value <= 0:
        raise SchedulingBudgetError("INVALID_CGROUP_V1_CPU_QUOTA")
    return quota_value / period_value


def parse_meminfo_value(text: str, key: str) -> int | None:
    """Return a ``/proc/meminfo`` value in bytes."""
    for line in text.splitlines():
        name, _, rest = line.partition(":")
        if name != key:
            continue
        fields = rest.split()
        if not fields:
            return None
        try:
            value = int(fields[0])
        except ValueError:
            return None
        unit = fields[1].lower() if len(fields) > 1 else "b"
        if unit == "kb":
            return value * 1024
        if unit == "mb":
            return value * 1024 * 1024
        if unit == "b":
            return value
        raise SchedulingBudgetError("INVALID_MEMINFO_UNIT")
    return None


def parse_cgroup_memory_limit(text: str) -> int | None:
    """Parse cgroup v2 ``memory.max`` / v1 ``memory.limit_in_bytes``."""
    value = text.strip()
    if value == "max":
        return None
    try:
        parsed = int(value)
    except ValueError as error:
        raise SchedulingBudgetError("INVALID_CGROUP_MEMORY_LIMIT") from error
    if parsed <= 0:
        raise SchedulingBudgetError("INVALID_CGROUP_MEMORY_LIMIT")
    # cgroup v1 reports a huge sentinel when no limit is configured.
    if parsed >= (1 << 60):
        return None
    return parsed


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="ascii")
    except (OSError, UnicodeDecodeError):
        return None


def detect_effective_capacity(
    *,
    procfs: Path | str | None = None,
    cgroup_root: Path | str | None = None,
    affinity: int | None = None,
    environ: dict[str, str] | None = None,
) -> EffectiveCapacity:
    """Read the capacity this process can actually use.

    Paths are injectable so tests exercise real parsing on synthetic trees.
    The cgroup lookup intentionally reads the root view; a runtime that mounts a
    subtree at ``/sys/fs/cgroup`` is covered, and an unrecognised layout falls
    back to affinity and ``MemAvailable`` with a recorded provenance entry.
    """
    proc = Path(procfs) if procfs is not None else Path("/proc")
    cgroup = Path(cgroup_root) if cgroup_root is not None else Path("/sys/fs/cgroup")
    env = os.environ if environ is None else environ
    provenance: list[str] = []

    if affinity is None:
        affinity = _cpu_affinity()
    provenance.append("cpu_affinity")

    cgroup_cpu: float | None = None
    cpu_max = _read_text(cgroup / "cpu.max")
    if cpu_max is not None:
        try:
            cgroup_cpu = parse_cgroup_cpu_max(cpu_max)
            provenance.append("cgroup_v2_cpu.max")
        except SchedulingBudgetError:
            provenance.append("cgroup_v2_cpu.max_unparsed")
    else:
        quota = _read_text(cgroup / "cpu" / "cpu.cfs_quota_us")
        period = _read_text(cgroup / "cpu" / "cpu.cfs_period_us")
        if quota is not None and period is not None:
            try:
                cgroup_cpu = parse_cgroup_v1_cpu_quota(quota, period)
                provenance.append("cgroup_v1_cpu.cfs_quota_us")
            except SchedulingBudgetError:
                provenance.append("cgroup_v1_cpu_unparsed")

    meminfo = _read_text(proc / "meminfo")
    available = parse_meminfo_value(meminfo, "MemAvailable") if meminfo else None
    if available is None and meminfo:
        total = parse_meminfo_value(meminfo, "MemTotal")
        available = total
        if total is not None:
            provenance.append("proc_meminfo_MemTotal")
    elif available is not None:
        provenance.append("proc_meminfo_MemAvailable")
    if available is None:
        available = 0
        provenance.append("memory_available_unknown")

    cgroup_memory: int | None = None
    memory_max = _read_text(cgroup / "memory.max")
    if memory_max is not None:
        try:
            cgroup_memory = parse_cgroup_memory_limit(memory_max)
            provenance.append("cgroup_v2_memory.max")
        except SchedulingBudgetError:
            provenance.append("cgroup_v2_memory.max_unparsed")
    else:
        memory_limit = _read_text(cgroup / "memory" / "memory.limit_in_bytes")
        if memory_limit is not None:
            try:
                cgroup_memory = parse_cgroup_memory_limit(memory_limit)
                provenance.append("cgroup_v1_memory.limit_in_bytes")
            except SchedulingBudgetError:
                provenance.append("cgroup_v1_memory_unparsed")

    override = env.get(WORKER_COUNT_ENV)
    if override:
        provenance.append(f"env:{WORKER_COUNT_ENV}")

    return EffectiveCapacity(
        cpu_affinity=affinity,
        memory_available_bytes=available,
        cgroup_cpu_cores=cgroup_cpu,
        cgroup_memory_limit_bytes=cgroup_memory,
        provenance=tuple(provenance),
    )


def _cpu_affinity() -> int:
    try:
        return max(1, len(os.sched_getaffinity(0)))  # type: ignore[attr-defined]
    except (AttributeError, OSError):  # pragma: no cover - non-Linux
        return max(1, os.cpu_count() or 1)


# ---------------------------------------------------------------------------
# Budget policy
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkerBudgetPolicy:
    """Deterministic mapping from real capacity to a worker count."""

    per_job_memory_bytes: int = DEFAULT_PER_JOB_MEMORY_BYTES
    memory_reserve_fraction: Decimal = DEFAULT_MEMORY_RESERVE_FRACTION
    max_workers: int = DEFAULT_MAX_WORKERS
    jobs_per_core: float = 1.0
    minimum_workers: int = 1

    def __post_init__(self) -> None:
        if self.per_job_memory_bytes < 1:
            raise SchedulingBudgetError("INVALID_PER_JOB_MEMORY")
        if not (Decimal("0") <= self.memory_reserve_fraction < Decimal("1")):
            raise SchedulingBudgetError("INVALID_MEMORY_RESERVE_FRACTION")
        if self.max_workers < 1:
            raise SchedulingBudgetError("INVALID_MAX_WORKERS")
        if self.jobs_per_core <= 0:
            raise SchedulingBudgetError("INVALID_JOBS_PER_CORE")
        if not (1 <= self.minimum_workers <= self.max_workers):
            raise SchedulingBudgetError("INVALID_MINIMUM_WORKERS")

    def compute(self, capacity: EffectiveCapacity) -> "WorkerBudget":
        cpu_workers = max(
            self.minimum_workers,
            int(math.floor(capacity.effective_cores * self.jobs_per_core)),
        )
        reserve = int(capacity.effective_memory_bytes * self.memory_reserve_fraction)
        usable = max(0, capacity.effective_memory_bytes - reserve)
        memory_workers = max(
            self.minimum_workers, usable // self.per_job_memory_bytes
        )
        candidates = {
            "cpu": cpu_workers,
            "memory": memory_workers,
            "policy_cap": self.max_workers,
        }
        limiting_factor = min(candidates, key=lambda name: candidates[name])
        workers = max(self.minimum_workers, candidates[limiting_factor])
        return WorkerBudget(
            workers=workers,
            cpu_workers=cpu_workers,
            memory_workers=memory_workers,
            max_workers=self.max_workers,
            limiting_factor=limiting_factor,
            capacity=capacity,
            policy=self,
        )


@dataclass(frozen=True)
class WorkerBudget:
    workers: int
    cpu_workers: int
    memory_workers: int
    max_workers: int
    limiting_factor: str
    capacity: EffectiveCapacity
    policy: WorkerBudgetPolicy

    def as_dict(self) -> dict[str, object]:
        return {
            "workers": self.workers,
            "cpu_workers": self.cpu_workers,
            "memory_workers": self.memory_workers,
            "max_workers": self.max_workers,
            "limiting_factor": self.limiting_factor,
            "per_job_memory_bytes": self.policy.per_job_memory_bytes,
            "memory_reserve_fraction": str(self.policy.memory_reserve_fraction),
            "jobs_per_core": self.policy.jobs_per_core,
            "capacity": self.capacity.as_dict(),
        }


# ---------------------------------------------------------------------------
# One global permit set
# ---------------------------------------------------------------------------


class GlobalExecutionBudget:
    """Process-wide permits shared by every scheduling executor.

    A permit is held for the whole calculation, so the sum of concurrent
    scheduling runs in this process can never exceed ``workers``, regardless of
    how many executors or caller threads exist.
    """

    def __init__(self, workers: int) -> None:
        if isinstance(workers, bool) or not isinstance(workers, int) or workers < 1:
            raise SchedulingBudgetError("INVALID_WORKER_BUDGET")
        self._workers = workers
        self._permits = threading.BoundedSemaphore(workers)
        self._lock = threading.Lock()
        self._active = 0
        self._peak = 0
        self._acquired = 0

    @property
    def workers(self) -> int:
        return self._workers

    @property
    def active(self) -> int:
        with self._lock:
            return self._active

    @property
    def peak(self) -> int:
        with self._lock:
            return self._peak

    @property
    def acquired_total(self) -> int:
        with self._lock:
            return self._acquired

    def try_acquire(self, timeout: float | None = None) -> bool:
        if timeout is None:
            acquired = self._permits.acquire()
        else:
            acquired = self._permits.acquire(timeout=timeout)
        if not acquired:
            return False
        with self._lock:
            self._active += 1
            self._acquired += 1
            self._peak = max(self._peak, self._active)
        return True

    def release(self) -> None:
        with self._lock:
            if self._active <= 0:
                raise SchedulingBudgetError("WORKER_BUDGET_RELEASE_WITHOUT_PERMIT")
            self._active -= 1
        self._permits.release()

    @contextmanager
    def permit(self, timeout: float | None = None) -> Iterator[None]:
        if not self.try_acquire(timeout):
            raise SchedulingBudgetError("WORKER_BUDGET_TIMEOUT")
        try:
            yield
        finally:
            self.release()

    def as_dict(self) -> dict[str, object]:
        with self._lock:
            return {
                "workers": self._workers,
                "active": self._active,
                "peak": self._peak,
                "acquired_total": self._acquired,
            }


_global_lock = threading.RLock()
_global_budget: GlobalExecutionBudget | None = None


def configure_global_budget(
    workers: int | None = None,
    *,
    capacity: EffectiveCapacity | None = None,
    policy: WorkerBudgetPolicy | None = None,
) -> GlobalExecutionBudget:
    """Return the one process-wide budget, creating it on first use.

    An explicit ``workers`` value is the only way to override the derived count
    (tests and benchmarks use it). A second call with a different non-``None``
    count raises instead of silently changing a budget other executors hold.
    """
    global _global_budget
    with _global_lock:
        if _global_budget is None:
            if workers is None:
                env_value = os.environ.get(WORKER_COUNT_ENV)
                if env_value:
                    try:
                        workers = int(env_value)
                    except ValueError as error:
                        raise SchedulingBudgetError(
                            "INVALID_WORKER_COUNT_OVERRIDE"
                        ) from error
                else:
                    derived = (policy or WorkerBudgetPolicy()).compute(
                        capacity or detect_effective_capacity()
                    )
                    workers = derived.workers
            _global_budget = GlobalExecutionBudget(workers)
        elif workers is not None and workers != _global_budget.workers:
            raise SchedulingBudgetError("GLOBAL_WORKER_BUDGET_ALREADY_CONFIGURED")
        return _global_budget


def global_execution_budget() -> GlobalExecutionBudget:
    return configure_global_budget()


def reset_global_budget() -> None:
    """Test seam: forget the singleton. Never called by production code."""
    global _global_budget
    with _global_lock:
        _global_budget = None


# ---------------------------------------------------------------------------
# Adaptive dispatch target
# ---------------------------------------------------------------------------


@dataclass
class AdaptiveWorkerController:
    """Choose the dispatch target from queue pressure, inside the hard cap.

    Growth is one worker per observation while a backlog exists; shrink waits
    for ``idle_observations_before_shrink`` consecutive empty observations. The
    result is bounded by ``[minimum, maximum]`` and by the budget at the call
    site, so adaptation can only change *how much* of the budget is used, never
    exceed it.
    """

    maximum: int
    minimum: int = 1
    step: int = 1
    idle_observations_before_shrink: int = 3
    _target: int = field(init=False)
    _idle_observations: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        if self.maximum < 1:
            raise SchedulingBudgetError("INVALID_ADAPTIVE_MAXIMUM")
        if not (1 <= self.minimum <= self.maximum):
            raise SchedulingBudgetError("INVALID_ADAPTIVE_MINIMUM")
        if self.step < 1:
            raise SchedulingBudgetError("INVALID_ADAPTIVE_STEP")
        if self.idle_observations_before_shrink < 1:
            raise SchedulingBudgetError("INVALID_ADAPTIVE_IDLE_THRESHOLD")
        self._target = self.minimum

    @property
    def target(self) -> int:
        return self._target

    @property
    def idle_observations(self) -> int:
        return self._idle_observations

    def observe(self, *, pending: int, active: int) -> int:
        if pending < 0 or active < 0:
            raise SchedulingBudgetError("INVALID_QUEUE_OBSERVATION")
        if pending > 0:
            self._idle_observations = 0
            self._target = min(self.maximum, self._target + self.step)
        else:
            self._idle_observations += 1
            if self._idle_observations >= self.idle_observations_before_shrink:
                self._target = max(self.minimum, self._target - self.step)
                self._idle_observations = 0
        return self._target

    def snapshot(self) -> dict[str, int]:
        return {
            "target": self._target,
            "maximum": self.maximum,
            "minimum": self.minimum,
            "idle_observations": self._idle_observations,
        }


def summarize_capacity(capacity: EffectiveCapacity) -> Sequence[tuple[str, object]]:
    """Stable key/value view for evidence files."""
    return tuple(capacity.as_dict().items())


__all__ = [
    "AdaptiveWorkerController",
    "DEFAULT_MAX_WORKERS",
    "DEFAULT_MEMORY_RESERVE_FRACTION",
    "DEFAULT_PER_JOB_MEMORY_BYTES",
    "EffectiveCapacity",
    "GlobalExecutionBudget",
    "SchedulingBudgetError",
    "WORKER_COUNT_ENV",
    "WorkerBudget",
    "WorkerBudgetPolicy",
    "configure_global_budget",
    "detect_effective_capacity",
    "global_execution_budget",
    "parse_cgroup_cpu_max",
    "parse_cgroup_memory_limit",
    "parse_cgroup_v1_cpu_quota",
    "parse_meminfo_value",
    "reset_global_budget",
    "summarize_capacity",
]
