"""P0-N: one global worker scheduler for every scheduling project.

The executor (P0-G) dispatched each durable job onto a Python *thread* while the
engine is pure Python, so concurrent jobs serialised on the GIL and the P0-M
float pipeline (which requires a fork-safe parent) declined in that path. This
module makes the placement unit explicit:

* every job runs in its own OS process, created from a single-threaded parent,
  so two jobs really compute at the same time;
* every process holds a number of *slots* from the one process-wide
  ``GlobalExecutionBudget``; a slot is what the engine may use for its own
  intra-project float workers, so a job with three slots runs one parent and two
  float children and the sum across jobs never exceeds the budget;
* slots are allocated adaptively from the measured workload (activity count),
  queue pressure and waiting time, with a hard reservation for small projects so
  a large project cannot occupy the whole machine while work is waiting.

Nothing here contains scheduling logic. A slot changes *where* the unchanged
engine runs and how much of it runs concurrently; it never changes a value.
"""

from __future__ import annotations

import multiprocessing
import os
import pickle
import threading
import time
import traceback
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Sequence

from .scheduling_execution_budget import (
    GlobalExecutionBudget,
    global_execution_budget,
)


DEFAULT_TARGET_ACTIVITIES_PER_SLOT = 1250
DEFAULT_SMALL_PROJECT_ACTIVITIES = 1500
DEFAULT_AGING_SECONDS = 2.0

#: Result a cache entry decodes to when the stored payload is unreadable.
_CACHE_MISS = object()


class SchedulingSchedulerError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Workload and allocation policy
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProjectWorkload:
    """Measured size of one project, used only for placement decisions.

    ``activity_count`` is the number of activities in the immutable snapshot.
    It is a size proxy, not an estimate of a duration: the policy only compares
    projects with each other and never predicts wall time.
    """

    activity_count: int | None = None
    relationship_count: int | None = None

    def __post_init__(self) -> None:
        for name in ("activity_count", "relationship_count"):
            value = getattr(self, name)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise SchedulingSchedulerError("INVALID_PROJECT_WORKLOAD")

    @property
    def known(self) -> bool:
        return self.activity_count is not None

    @property
    def size_key(self) -> int:
        """Ordering key: unknown workloads are treated as the largest."""
        if self.activity_count is None:
            return 1 << 62
        return self.activity_count

    def weight_bytes(self) -> int:
        """Rough resident weight of the immutable input, for memory accounting."""
        activities = self.activity_count or 0
        relationships = self.relationship_count or 0
        return activities * 512 + relationships * 160


@dataclass(frozen=True)
class PendingTask:
    """One queued unit of work as the policy sees it."""

    key: str
    workload: ProjectWorkload
    submitted_at: float
    priority: int = 0
    tenant_id: str | None = None


@dataclass(frozen=True)
class SlotGrant:
    key: str
    slots: int
    reason: str


@dataclass(frozen=True)
class SlotAllocationPolicy:
    """Deterministic, size-aware allocation inside the global budget.

    Rules, in order:

    1. A job never gets more slots than remain free or than
       ``max_slots_per_job``; every grant is at least one slot.
    2. A job whose size is unknown or below ``small_project_activities`` gets
       one slot. Small jobs are ordered first, so they cannot be trapped
       behind a backlog of large ones.
    3. Otherwise the size-derived desire is ``ceil(activities / target)``.
       ``target_activities_per_slot`` is the measured point where another
       float worker stops paying for itself on the reference host.
    4. Fair share: while several projects are queued, each grant is bounded by
       ``free_slots // projects_still_waiting`` (at least one). Ten 5k projects
       on four slots therefore run one slot each (maximum concurrency), while
       two 5k projects on four slots run two each (depth where it helps).
    5. Work conservation: when a project is the only one queued and nothing is
       running, it may take every free slot, so a lone large project uses the
       whole machine.
    6. Waiting time raises effective priority (aging), so no queued project is
       postponed indefinitely by a stream of newer arrivals.

    There is no preemption: a job that already holds slots keeps them, because
    cancelling it would throw away completed work. A project that arrives while
    every slot is held starts at the next completion.
    """

    target_activities_per_slot: int = DEFAULT_TARGET_ACTIVITIES_PER_SLOT
    small_project_activities: int = DEFAULT_SMALL_PROJECT_ACTIVITIES
    max_slots_per_job: int | None = None
    aging_seconds: float = DEFAULT_AGING_SECONDS

    def __post_init__(self) -> None:
        if self.target_activities_per_slot < 1:
            raise SchedulingSchedulerError("INVALID_TARGET_ACTIVITIES_PER_SLOT")
        if self.small_project_activities < 0:
            raise SchedulingSchedulerError("INVALID_SMALL_PROJECT_ACTIVITIES")
        if self.max_slots_per_job is not None and self.max_slots_per_job < 1:
            raise SchedulingSchedulerError("INVALID_MAX_SLOTS_PER_JOB")
        if self.aging_seconds <= 0:
            raise SchedulingSchedulerError("INVALID_AGING_SECONDS")

    def effective_priority(self, task: PendingTask, now: float) -> float:
        waited = max(0.0, now - task.submitted_at)
        return float(task.priority) + waited / self.aging_seconds

    def order(self, tasks: Iterable[PendingTask], now: float) -> list[PendingTask]:
        """Small and aged work first; ties by submission order."""
        return sorted(
            tasks,
            key=lambda task: (
                -self.effective_priority(task, now),
                task.workload.size_key,
                task.submitted_at,
                task.key,
            ),
        )

    def desired_slots(self, task: PendingTask) -> int:
        count = task.workload.activity_count
        if count is None or count < self.small_project_activities:
            return 1
        return max(1, -(-count // self.target_activities_per_slot))

    def slots_for(
        self,
        task: PendingTask,
        *,
        free_slots: int,
        share: int,
        alone: bool,
    ) -> int:
        if free_slots < 1:
            return 0
        maximum = free_slots
        if self.max_slots_per_job is not None:
            maximum = min(maximum, self.max_slots_per_job)
        desired = self.desired_slots(task)
        if desired <= 1:
            return 1
        if alone:
            # Work conservation: one project alone may use the whole budget.
            return max(1, maximum)
        return max(1, min(desired, max(1, share), maximum))

    def plan(
        self,
        tasks: Sequence[PendingTask],
        *,
        free_slots: int,
        active_jobs: int,
        now: float,
    ) -> list[SlotGrant]:
        if free_slots <= 0 or not tasks:
            return []
        ordered = self.order(tasks, now)
        grants: list[SlotGrant] = []
        remaining = free_slots
        for index, task in enumerate(ordered):
            if remaining <= 0:
                break
            waiting = len(ordered) - index
            share = remaining // waiting
            alone = waiting == 1 and active_jobs == 0
            slots = self.slots_for(
                task, free_slots=remaining, share=share, alone=alone
            )
            if slots < 1:
                break
            grants.append(SlotGrant(task.key, slots, "alone" if alone else "share"))
            remaining -= slots
        return grants


# ---------------------------------------------------------------------------
# Standalone scheduler
# ---------------------------------------------------------------------------


@dataclass
class _Task:
    key: str
    function: Callable[[int], Any]
    workload: ProjectWorkload
    priority: int
    tenant_id: str | None
    cache_key: Any
    submitted_at: float
    submitted_wall: float
    release_at: float | None = None
    state: str = "QUEUED"
    slots: int = 0
    pid: int | None = None
    started_at: float | None = None
    finished_at: float | None = None
    queue_wait_ms: float | None = None
    run_ms: float | None = None
    value: Any = None
    child_run_ms: float | None = None
    cpu_seconds: float | None = None
    error: str | None = None
    exitcode: int | None = None
    start_method: str | None = None
    cache_hit: bool = False
    attempts: int = 0


@dataclass
class _Run:
    task: _Task
    process: Any
    receiver: Any
    slots: int


def _default_start_method() -> str | None:
    """A start method that is safe for the current process state.

    ``fork`` is only safe while the process has a single thread; a threaded
    embedder gets ``forkserver`` (a clean, single-threaded helper) or ``spawn``.
    """
    methods = set(multiprocessing.get_all_start_methods())
    if "fork" in methods and threading.active_count() == 1:
        return "fork"
    if "forkserver" in methods:
        return "forkserver"
    if "spawn" in methods:
        return "spawn"
    return None


def _cpu_times() -> tuple[float, float, float, float]:
    """Self plus waited-for children, so nested float pools are included."""
    snapshot = os.times()
    return (
        snapshot.user,
        snapshot.system,
        snapshot.children_user,
        snapshot.children_system,
    )


def _cpu_delta(
    started: tuple[float, float, float, float],
    finished: tuple[float, float, float, float],
) -> float:
    return max(0.0, sum(finished) - sum(started))


def _child_main(function: Callable[[int], Any], slots: int, sender: Any) -> None:
    try:
        started = _cpu_times()
        wall_started = time.perf_counter()
        value = function(slots)
        cpu = _cpu_delta(started, _cpu_times())
        wall = time.perf_counter() - wall_started
        sender.send(("ok", value, cpu, wall))
    except BaseException as error:  # noqa: BLE001 - forwarded to the parent
        try:
            sender.send(("error", f"{type(error).__name__}: {error}", traceback.format_exc()))
        except BaseException:  # pragma: no cover - broken pipe
            pass
    finally:
        sender.close()


class GlobalWorkerScheduler:
    """Run independent scheduling jobs across the one global budget.

    ``submit`` accepts a callable that takes the slot count it was granted and
    returns any picklable value. The scheduler creates one process per job,
    holds the job's slots for the whole run, and re-allocates a slot to the next
    waiting job as soon as a process exits (work stealing at slot granularity).

    The scheduler never exceeds ``budget.workers``: a grant is all-or-nothing
    and a partially acquired grant is released immediately.
    """

    def __init__(
        self,
        *,
        budget: GlobalExecutionBudget | None = None,
        policy: SlotAllocationPolicy | None = None,
        start_method: str | None = None,
        job_timeout: float | None = None,
        poll_interval: float = 0.01,
        monotonic: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], float] = time.time,
        tick: Callable[[], None] | None = None,
    ) -> None:
        self._budget = budget or global_execution_budget()
        self._policy = policy or SlotAllocationPolicy()
        if start_method is not None:
            if start_method not in multiprocessing.get_all_start_methods():
                raise SchedulingSchedulerError("UNKNOWN_START_METHOD")
            if start_method == "fork" and threading.active_count() != 1:
                raise SchedulingSchedulerError("FORK_REQUIRES_SINGLE_THREADED_PARENT")
            self._start_method = start_method
        else:
            self._start_method = _default_start_method()
        if job_timeout is not None and job_timeout <= 0:
            raise SchedulingSchedulerError("INVALID_JOB_TIMEOUT")
        if poll_interval < 0:
            raise SchedulingSchedulerError("INVALID_POLL_INTERVAL")
        self._poll_interval = poll_interval
        self._job_timeout = job_timeout
        self._monotonic = monotonic
        self._wall_clock = wall_clock
        self._tick = tick
        self._pending: dict[str, _Task] = {}
        self._active: dict[str, _Run] = {}
        self._finished: dict[str, _Task] = {}
        self._lock = threading.Lock()
        self._slots_held = 0
        self._peak_slots = 0
        self._grants_total = 0
        self._process_starts = 0
        self._inline_fallbacks = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._stolen_slots = 0
        self._result_cache = None

    # -- configuration ----------------------------------------------------

    @property
    def budget(self) -> GlobalExecutionBudget:
        return self._budget

    @property
    def policy(self) -> SlotAllocationPolicy:
        return self._policy

    @property
    def start_method(self) -> str | None:
        return self._start_method

    def attach_result_cache(self, cache: Any) -> None:
        """Optional cache exposing ``get(key)``/``put(key, value, weight=)``."""
        self._result_cache = cache

    # -- submission -------------------------------------------------------

    def submit(
        self,
        key: str,
        function: Callable[[int], Any],
        *,
        workload: ProjectWorkload | None = None,
        priority: int = 0,
        tenant_id: str | None = None,
        cache_key: Any = None,
        release_at: float | None = None,
    ) -> None:
        if not key or not isinstance(key, str):
            raise SchedulingSchedulerError("INVALID_TASK_KEY")
        if not callable(function):
            raise SchedulingSchedulerError("INVALID_TASK_FUNCTION")
        if isinstance(priority, bool) or not isinstance(priority, int):
            raise SchedulingSchedulerError("INVALID_TASK_PRIORITY")
        if release_at is not None and not isinstance(release_at, (int, float)):
            raise SchedulingSchedulerError("INVALID_TASK_RELEASE")
        with self._lock:
            if key in self._pending or key in self._active or key in self._finished:
                raise SchedulingSchedulerError("DUPLICATE_TASK_KEY")
            now = self._monotonic()
            self._pending[key] = _Task(
                key=key,
                function=function,
                workload=workload or ProjectWorkload(),
                priority=priority,
                tenant_id=tenant_id,
                cache_key=cache_key,
                submitted_at=now,
                submitted_wall=self._wall_clock(),
                release_at=None if release_at is None else float(release_at),
            )
            if cache_key is not None and self._result_cache is not None:
                cached = self._result_cache.get(cache_key)
                if cached is not None:
                    try:
                        decoded = pickle.loads(cached)
                    except Exception:  # noqa: BLE001 - a corrupt entry is a miss
                        decoded = _CACHE_MISS
                    if decoded is not _CACHE_MISS:
                        task = self._pending.pop(key)
                        task.state = "CACHE_HIT"
                        task.cache_hit = True
                        task.value = decoded
                        task.started_at = now
                        task.finished_at = now
                        task.queue_wait_ms = 0.0
                        task.run_ms = 0.0
                        self._finished[key] = task
                        self._cache_hits += 1
                        return
                self._cache_misses += 1

    def cancel(self, key: str) -> bool:
        with self._lock:
            run = self._active.get(key)
            if run is not None:
                process = run.process
                process.terminate()
                return True
            if key in self._pending:
                task = self._pending.pop(key)
                task.state = "CANCELLED"
                self._finished[key] = task
                return True
        return False

    # -- statistics -------------------------------------------------------

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "budget": self._budget.workers,
                "slots_held": self._slots_held,
                "peak_slots": self._peak_slots,
                "slots_acquired_total": self._grants_total,
                "process_starts": self._process_starts,
                "inline_fallbacks": self._inline_fallbacks,
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "stolen_slots": self._stolen_slots,
                "queued": len(self._pending),
                "active": len(self._active),
                "finished": len(self._finished),
            }

    def value_for(self, key: str) -> Any:
        """Value returned by a finished task (``None`` when it has not run)."""
        with self._lock:
            task = self._finished.get(key)
        return None if task is None else task.value

    def results(self) -> list[dict[str, object]]:
        with self._lock:
            return [self._task_payload(task) for task in self._finished.values()]

    @staticmethod
    def _task_payload(task: _Task) -> dict[str, object]:
        return {
            "key": task.key,
            "tenant_id": task.tenant_id,
            "activity_count": task.workload.activity_count,
            "state": task.state,
            "slots": task.slots,
            "cache_hit": task.cache_hit,
            "queue_wait_ms": task.queue_wait_ms,
            "run_ms": task.run_ms,
            "child_run_ms": task.child_run_ms,
            "cpu_seconds": None
            if task.cpu_seconds is None
            else round(float(task.cpu_seconds), 4),
            "overhead_ms": (
                None
                if task.run_ms is None or task.child_run_ms is None
                else max(0.0, task.run_ms - task.child_run_ms)
            ),
            "pid": task.pid,
            "exitcode": task.exitcode,
            "start_method": task.start_method,
            "error": task.error,
            "submitted_at": task.submitted_wall,
        }

    # -- dispatch loop ----------------------------------------------------

    def run_until_idle(self, *, timeout: float | None = None, poll_interval: float | None = None) -> None:
        interval = self._poll_interval if poll_interval is None else poll_interval
        deadline = None if timeout is None else self._monotonic() + timeout
        while True:
            if self._tick is not None:
                self._tick()
            self._reap()
            self._dispatch()
            with self._lock:
                pending = list(self._pending.values())
            if not pending and not self._active:
                break
            now = self._monotonic()
            if deadline is not None and now >= deadline:
                self._terminate_active("TIMEOUT")
                self._reap()
                break
            sleep_for = interval
            # Only unreleased arrivals remain: wake exactly when the next one
            # becomes eligible instead of spinning through the queue.
            if pending and not self._active:
                releases = [task.release_at for task in pending if task.release_at is not None]
                if releases and len(releases) == len(pending):
                    sleep_for = max(0.0, min(sleep_for, min(releases) - now))
            if deadline is not None:
                sleep_for = max(0.0, min(sleep_for, deadline - now))
            if sleep_for > 0:
                time.sleep(sleep_for)

    def _dispatch(self) -> None:
        now = self._monotonic()
        with self._lock:
            pending = [
                task
                for task in self._pending.values()
                if task.release_at is None or task.release_at <= now
            ]
            free = self._budget.workers - self._slots_held
            active_jobs = len(self._active)
        if not pending or free <= 0:
            return
        descriptors = [
            PendingTask(
                key=task.key,
                workload=task.workload,
                submitted_at=task.submitted_at,
                priority=task.priority,
                tenant_id=task.tenant_id,
            )
            for task in pending
        ]
        grants = self._policy.plan(
            descriptors, free_slots=free, active_jobs=active_jobs, now=now
        )
        for grant in grants:
            self._start(grant)

    def _start(self, grant: SlotGrant) -> None:
        with self._lock:
            task = self._pending.pop(grant.key, None)
        if task is None:
            return
        acquired = self._acquire_slots(grant.slots)
        if acquired < grant.slots:
            with self._lock:
                self._pending[task.key] = task
            return
        task.slots = grant.slots
        task.started_at = self._monotonic()
        task.queue_wait_ms = max(0.0, (task.started_at - task.submitted_at) * 1000.0)
        task.state = "RUNNING"

        start_method = self._start_method
        if start_method is None:
            self._execute_inline(task)
            return
        receiver = sender = None
        try:
            context = multiprocessing.get_context(start_method)
            receiver, sender = context.Pipe(duplex=False)
            process = context.Process(
                target=_child_main,
                args=(task.function, task.slots, sender),
                name=f"sched-proj-{task.key[:16]}",
                daemon=False,
            )
            task.start_method = start_method
            process.start()
            task.pid = process.pid
            sender.close()
            sender = None
        except Exception:  # noqa: BLE001 - fall back to the exact inline run
            if receiver is not None:
                receiver.close()
            if sender is not None:
                sender.close()
            with self._lock:
                self._inline_fallbacks += 1
            task.error = None
            task.state = "RUNNING"
            self._execute_inline(task)
            return
        with self._lock:
            self._active[task.key] = _Run(task, process, receiver, task.slots)
            self._process_starts += 1

    def _execute_inline(self, task: _Task) -> None:
        """Run the task in this process and release its slots afterwards.

        Only used when the platform exposes no usable start method; the run is
        exact but occupies the dispatching process, so no two inline tasks can
        ever overlap.
        """
        started = time.perf_counter()
        cpu_started = _cpu_times()
        try:
            task.value = task.function(task.slots)
            task.state = "SUCCEEDED"
        except Exception as error:  # noqa: BLE001
            task.error = f"{type(error).__name__}: {error}"
            task.state = "FAILED"
        task.run_ms = (time.perf_counter() - started) * 1000.0
        task.child_run_ms = task.run_ms
        task.cpu_seconds = _cpu_delta(cpu_started, _cpu_times())
        task.finished_at = self._monotonic()
        self._release_slots(task.slots)
        self._store_cache(task)
        with self._lock:
            self._finished[task.key] = task

    def _acquire_slots(self, requested: int) -> int:
        acquired = 0
        for _ in range(requested):
            if not self._budget.try_acquire(timeout=0.0):
                break
            acquired += 1
        if acquired < requested:
            for _ in range(acquired):
                self._budget.release()
            return 0
        with self._lock:
            self._slots_held += acquired
            self._peak_slots = max(self._peak_slots, self._slots_held)
            self._grants_total += 1
        return acquired

    def _release_slots(self, slots: int) -> None:
        if slots <= 0:
            return
        for _ in range(slots):
            self._budget.release()
        with self._lock:
            self._slots_held = max(0, self._slots_held - slots)

    def _reap(self) -> None:
        with self._lock:
            runs = list(self._active.values())
        for run in runs:
            if run.process.is_alive():
                timeout = self._job_timeout
                if timeout is not None:
                    started = run.task.started_at or self._monotonic()
                    if self._monotonic() - started > timeout:
                        run.process.terminate()
                continue
            self._finish(run)

    def _finish(self, run: _Run) -> None:
        process = run.process
        process.join(timeout=1.0)
        task = run.task
        task.exitcode = process.exitcode
        payload: tuple | None = None
        try:
            if run.receiver.poll(0.5):
                payload = run.receiver.recv()
        except (EOFError, OSError):
            payload = None
        finally:
            run.receiver.close()
        task.finished_at = self._monotonic()
        task.run_ms = max(0.0, (task.finished_at - (task.started_at or task.finished_at)) * 1000.0)
        if payload is not None and payload[0] == "ok":
            task.state = "SUCCEEDED"
            task.value = payload[1]
            task.cpu_seconds = max(0.0, float(payload[2])) if len(payload) > 2 else None
            if len(payload) > 3:
                task.child_run_ms = max(0.0, float(payload[3]) * 1000.0)
        elif payload is not None and payload[0] == "error":
            task.state = "FAILED"
            task.error = payload[1]
        else:
            task.state = "FAILED"
            task.error = f"CHILD_EXITED_WITHOUT_RESULT:exitcode={process.exitcode}"
        with self._lock:
            self._active.pop(task.key, None)
        self._release_slots(run.slots)
        self._store_cache(task)
        with self._lock:
            self._finished[task.key] = task

    def _store_cache(self, task: _Task) -> None:
        if task.cache_key is None or self._result_cache is None:
            return
        if task.state != "SUCCEEDED":
            return
        try:
            self._result_cache.put(task.cache_key, pickle.dumps(task.value))
        except Exception:  # noqa: BLE001 - caching must never fail a job
            pass

    def _terminate_active(self, reason: str) -> None:
        with self._lock:
            runs = list(self._active.values())
        for run in runs:
            run.process.terminate()
            run.task.state = "CANCELLED"
            run.task.error = reason

    def shutdown(self, *, timeout: float = 5.0) -> None:
        self._terminate_active("SHUTDOWN")
        deadline = self._monotonic() + timeout
        while self._monotonic() < deadline:
            self._reap()
            with self._lock:
                if not self._active:
                    break
            time.sleep(0.01)


def make_slot_admission(slots: int):
    """Return an admission callable for a job that already owns ``slots``.

    Inside a job process the global semaphore is a private copy, so the child
    receives the exact grant the scheduler reserved for it. The engine may use
    at most ``slots`` total (its own pass plus float children).
    """

    if isinstance(slots, bool) or not isinstance(slots, int) or slots < 1:
        raise SchedulingSchedulerError("INVALID_SLOT_GRANT")
    from contextlib import nullcontext

    def admission(requested: int):
        return nullcontext(min(int(requested), slots))

    return admission


__all__ = [
    "DEFAULT_AGING_SECONDS",
    "DEFAULT_SMALL_PROJECT_ACTIVITIES",
    "DEFAULT_TARGET_ACTIVITIES_PER_SLOT",
    "GlobalWorkerScheduler",
    "PendingTask",
    "ProjectWorkload",
    "SchedulingSchedulerError",
    "SlotAllocationPolicy",
    "SlotGrant",
    "make_slot_admission",
]
