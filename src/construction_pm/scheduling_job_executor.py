"""P0-G: adaptive execution of durable scheduling jobs.

The executor is a thin, engine-agnostic loop:

1. discover queued jobs (the durable lifecycle from P0-F),
2. claim one under a lease token,
3. acquire one permit from the process-wide worker budget,
4. call the caller-supplied ``calculate`` function, which runs the single
   authoritative CUBI engine on the job's immutable snapshot,
5. renew the lease while the calculation runs, and
6. complete with the engine's canonical result or record a terminal failure.

It contains no scheduling logic and no per-surface variant. Cloud, Local Server,
Desktop and a Worker process all run this same loop over the same engine; the
only thing that differs is how many permits the machine can actually support,
which ``scheduling_execution_budget`` derives from affinity, cgroup quota and
available memory.

Adaptation changes *how much* of the budget is used, never the budget itself: a
``AdaptiveWorkerController`` raises the dispatch target toward the hard cap while
the queue has a backlog and lowers it after consecutive empty observations.
"""

from __future__ import annotations

import json
import multiprocessing
import pickle
import threading
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any, Callable

from .scheduling_execution_budget import (
    AdaptiveWorkerController,
    GlobalExecutionBudget,
    global_execution_budget,
)
from .scheduling_result_cache import CacheKey, ScheduleResultCache
from .scheduling_worker_scheduler import (
    PendingTask,
    ProjectWorkload,
    SlotAllocationPolicy,
    _default_start_method,
)
from .scheduling_job_lifecycle import (
    SchedulingJob,
    SchedulingJobCancelled,
    SchedulingJobError,
    SchedulingJobLeaseError,
    SchedulingJobResult,
    SchedulingJobService,
    SchedulingJobState,
)


class SchedulingExecutionError(RuntimeError):
    """A calculation failed; set ``retryable`` to allow a lease-free requeue."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass(frozen=True)
class SchedulingJobEvent:
    kind: str
    job_id: str
    tenant_id: str
    project_id: str
    owner: str
    at: datetime
    queue_wait_ms: float | None = None
    run_ms: float | None = None
    error: str | None = None


@dataclass(frozen=True)
class SchedulingExecutionSummary:
    claimed: int = 0
    succeeded: int = 0
    failed: int = 0
    retried: int = 0
    cancelled: int = 0
    lease_lost: int = 0
    skipped: int = 0
    idle_polls: int = 0
    stopped: bool = False
    # P0-N process placement (zero on the historical thread path).
    process_starts: int = 0
    inline_fallbacks: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    slots_acquired_total: int = 0
    peak_slots: int = 0

    def merged(self, other: "SchedulingExecutionSummary") -> "SchedulingExecutionSummary":
        return SchedulingExecutionSummary(
            claimed=self.claimed + other.claimed,
            succeeded=self.succeeded + other.succeeded,
            failed=self.failed + other.failed,
            retried=self.retried + other.retried,
            cancelled=self.cancelled + other.cancelled,
            lease_lost=self.lease_lost + other.lease_lost,
            skipped=self.skipped + other.skipped,
            idle_polls=self.idle_polls + other.idle_polls,
            stopped=self.stopped or other.stopped,
            process_starts=self.process_starts + other.process_starts,
            inline_fallbacks=self.inline_fallbacks + other.inline_fallbacks,
            cache_hits=self.cache_hits + other.cache_hits,
            cache_misses=self.cache_misses + other.cache_misses,
            slots_acquired_total=(
                self.slots_acquired_total + other.slots_acquired_total
            ),
            peak_slots=max(self.peak_slots, other.peak_slots),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "claimed": self.claimed,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "retried": self.retried,
            "cancelled": self.cancelled,
            "lease_lost": self.lease_lost,
            "skipped": self.skipped,
            "idle_polls": self.idle_polls,
            "stopped": self.stopped,
            "process_starts": self.process_starts,
            "inline_fallbacks": self.inline_fallbacks,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "slots_acquired_total": self.slots_acquired_total,
            "peak_slots": self.peak_slots,
        }


@dataclass(frozen=True)
class _Counters:
    claimed: int = 0
    succeeded: int = 0
    failed: int = 0
    retried: int = 0
    cancelled: int = 0
    lease_lost: int = 0
    skipped: int = 0
    idle_polls: int = 0
    process_starts: int = 0
    inline_fallbacks: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    slots_acquired_total: int = 0
    peak_slots: int = 0


class SchedulingJobExecutor:
    """One worker's view of the queue, bounded by the global budget."""

    def __init__(
        self,
        service: SchedulingJobService,
        *,
        calculate: Callable[[SchedulingJob], SchedulingJobResult],
        owner: str,
        budget: GlobalExecutionBudget | None = None,
        controller: AdaptiveWorkerController | None = None,
        engine_identity: tuple[str, str] | None = None,
        poll_interval: float = 0.05,
        dispatch_batch: int = 16,
        idle_polls_before_exit: int = 2,
        recover_expired: bool = True,
        event_sink: Callable[[SchedulingJobEvent], None] | None = None,
        clock: Callable[[], datetime] | None = None,
        execution_mode: str = "thread",
        slot_policy: SlotAllocationPolicy | None = None,
        workload_estimator: Callable[[SchedulingJob], ProjectWorkload | None] | None = None,
        result_cache: ScheduleResultCache | None = None,
        start_method: str | None = None,
        calculate_with_slots: Callable[[SchedulingJob, int], SchedulingJobResult] | None = None,
        job_timeout: float | None = None,
    ) -> None:
        if not owner or not owner.strip():
            raise SchedulingExecutionError("INVALID_EXECUTOR_OWNER")
        if poll_interval < 0:
            raise SchedulingExecutionError("INVALID_POLL_INTERVAL")
        if dispatch_batch < 1:
            raise SchedulingExecutionError("INVALID_DISPATCH_BATCH")
        if idle_polls_before_exit < 1:
            raise SchedulingExecutionError("INVALID_IDLE_POLLS")
        if execution_mode not in ("thread", "process"):
            raise SchedulingExecutionError("INVALID_EXECUTION_MODE")
        if execution_mode == "thread" and (
            slot_policy is not None
            or workload_estimator is not None
            or result_cache is not None
            or calculate_with_slots is not None
            or start_method is not None
            or job_timeout is not None
        ):
            raise SchedulingExecutionError("PROCESS_SETTINGS_REQUIRE_PROCESS_MODE")
        if start_method is not None and start_method not in multiprocessing.get_all_start_methods():
            raise SchedulingExecutionError("UNKNOWN_START_METHOD")
        if job_timeout is not None and job_timeout <= 0:
            raise SchedulingExecutionError("INVALID_JOB_TIMEOUT")
        self._service = service
        self._calculate = calculate
        self._owner = owner
        self._budget = budget or global_execution_budget()
        self._controller = controller or AdaptiveWorkerController(
            maximum=self._budget.workers
        )
        if self._controller.maximum > self._budget.workers:
            raise SchedulingExecutionError("CONTROLLER_EXCEEDS_WORKER_BUDGET")
        self._engine_identity = engine_identity
        self._poll_interval = poll_interval
        self._dispatch_batch = dispatch_batch
        self._idle_polls_before_exit = idle_polls_before_exit
        self._recover_expired = recover_expired
        self._event_sink = event_sink
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._in_flight: dict[str, threading.Thread] = {}
        self._counters = _Counters()
        self._execution_mode = execution_mode
        self._slot_policy = slot_policy or SlotAllocationPolicy()
        self._workload_estimator = workload_estimator
        self._result_cache = result_cache
        self._calculate_with_slots = calculate_with_slots
        self._job_timeout = job_timeout
        self._start_method_explicit = start_method is not None
        self._start_method = (
            start_method if start_method is not None else _default_start_method()
        )
        self._process_jobs: dict[str, _ProcessJob] = {}
        self._slots_held = 0
        self._mp = multiprocessing.get_context(self._start_method) if self._start_method else None

    # -- public API -------------------------------------------------------

    @property
    def budget(self) -> GlobalExecutionBudget:
        return self._budget

    @property
    def controller(self) -> AdaptiveWorkerController:
        return self._controller

    def request_stop(self) -> None:
        self._stop.set()

    def in_flight(self) -> int:
        if self._execution_mode == "process":
            return len(self._process_jobs)
        with self._lock:
            return len(self._in_flight)

    def summary(self) -> SchedulingExecutionSummary:
        """Cumulative counters of this worker, for telemetry and delta reads."""
        with self._lock:
            counters = self._counters
        return SchedulingExecutionSummary(
            claimed=counters.claimed,
            succeeded=counters.succeeded,
            failed=counters.failed,
            retried=counters.retried,
            cancelled=counters.cancelled,
            lease_lost=counters.lease_lost,
            skipped=counters.skipped,
            idle_polls=counters.idle_polls,
            stopped=self._stop.is_set(),
            process_starts=counters.process_starts,
            inline_fallbacks=counters.inline_fallbacks,
            cache_hits=counters.cache_hits,
            cache_misses=counters.cache_misses,
            slots_acquired_total=counters.slots_acquired_total,
            peak_slots=counters.peak_slots,
        )

    def run_once(self) -> bool:
        """Claim and execute one queued job. Returns False when none is queued."""
        if self._recover_expired:
            self._service.recover_expired(limit=self._dispatch_batch)
        candidates = self._service.queued_jobs(1)
        if not candidates:
            return False
        if self._execution_mode == "process":
            self._dispatch_process_jobs(pending=1, target=1)
            while self._process_jobs:
                self._reap_process_jobs()
                if not self._process_jobs:
                    break
                time.sleep(max(self._poll_interval, 0.005))
            return True
        self._run_job(candidates[0])
        return True

    def run_until_idle(self, *, timeout: float | None = None) -> SchedulingExecutionSummary:
        """Drain the queue with an adaptively sized dispatch target.

        Returns when the queue is empty and no calculation is in flight, when
        ``timeout`` elapses, or when ``request_stop`` is called. In-flight
        calculations finish; stopping never abandons a lease silently.
        """
        if self._execution_mode == "process":
            return self._run_process_mode(timeout=timeout)
        deadline = None if timeout is None else time.monotonic() + timeout
        idle_polls = 0
        while not self._stop.is_set():
            self._reap()
            pending = self._service.pending_count()
            active = self.in_flight()
            target = self._controller.observe(pending=pending, active=active)
            self._dispatch(pending=pending, target=target)
            if pending == 0 and self.in_flight() == 0:
                idle_polls += 1
                if idle_polls >= self._idle_polls_before_exit:
                    break
            else:
                idle_polls = 0
            if deadline is not None and time.monotonic() >= deadline:
                break
            if self._poll_interval:
                time.sleep(self._poll_interval)
        self._reap()
        with self._lock:
            counters = self._counters
        return SchedulingExecutionSummary(
            claimed=counters.claimed,
            succeeded=counters.succeeded,
            failed=counters.failed,
            retried=counters.retried,
            cancelled=counters.cancelled,
            lease_lost=counters.lease_lost,
            skipped=counters.skipped,
            idle_polls=idle_polls,
            stopped=self._stop.is_set(),
            process_starts=counters.process_starts,
            inline_fallbacks=counters.inline_fallbacks,
            cache_hits=counters.cache_hits,
            cache_misses=counters.cache_misses,
            slots_acquired_total=counters.slots_acquired_total,
            peak_slots=counters.peak_slots,
        )

    # -- dispatch ---------------------------------------------------------

    def _dispatch(self, *, pending: int, target: int) -> None:
        if pending <= 0:
            return
        slots = target - self.in_flight()
        if slots <= 0:
            return
        candidates = self._service.queued_jobs(self._dispatch_batch)
        dispatched = 0
        for job in candidates:
            if dispatched >= slots:
                break
            with self._lock:
                if job.job_id in self._in_flight:
                    continue
                thread = threading.Thread(
                    target=self._run_job,
                    args=(job,),
                    name=f"sched-job-{job.job_id[:12]}",
                    daemon=True,
                )
                self._in_flight[job.job_id] = thread
            thread.start()
            dispatched += 1

    def _reap(self) -> None:
        finished: list[str] = []
        with self._lock:
            for job_id, thread in self._in_flight.items():
                if not thread.is_alive():
                    finished.append(job_id)
        if finished:
            with self._lock:
                for job_id in finished:
                    self._in_flight.pop(job_id, None)

    def _increment(self, **deltas: int) -> None:
        with self._lock:
            self._counters = replace(
                self._counters,
                **{
                    name: getattr(self._counters, name) + delta
                    for name, delta in deltas.items()
                },
            )

    # -- one job ----------------------------------------------------------

    def _run_job(self, job: SchedulingJob) -> None:
        claimed_at = self._clock()
        try:
            claimed = self._service.claim(
                tenant_id=job.tenant_id,
                project_id=job.project_id,
                job_id=job.job_id,
                owner=self._owner,
            )
        except SchedulingJobError:
            # Another worker won the claim, or the job became terminal.
            self._increment(skipped=1)
            return

        self._increment(claimed=1)
        queue_wait = max(
            0.0, (claimed_at - claimed.created_at).total_seconds() * 1000.0
        )
        self._emit(
            "CLAIMED",
            claimed,
            at=claimed_at,
            queue_wait_ms=queue_wait,
        )

        heartbeat = _LeaseHeartbeat(
            service=self._service,
            job=claimed,
            interval=max(self._service.lease_ttl.total_seconds() / 3.0, 0.05),
        )
        heartbeat.start()
        started = time.perf_counter()
        try:
            if self._engine_identity is not None:
                expected_engine, expected_calculation = self._engine_identity
                if (
                    claimed.engine_version != expected_engine
                    or claimed.calculation_identity != expected_calculation
                ):
                    raise SchedulingExecutionError(
                        "ENGINE_IDENTITY_MISMATCH", retryable=False
                    )
            with self._budget.permit():
                result = self._calculate(claimed)
            if heartbeat.cancelled:
                raise SchedulingJobCancelled("SCHEDULING_JOB_CANCELLED")
            self._service.complete(
                tenant_id=claimed.tenant_id,
                project_id=claimed.project_id,
                job_id=claimed.job_id,
                token=claimed.lease_token or "",
                result=result,
            )
        except SchedulingJobCancelled:
            self._increment(cancelled=1)
            self._emit("CANCELLED", claimed, at=self._clock())
        except SchedulingJobLeaseError as error:
            # The lease expired and another worker may own the job now. Do not
            # write a terminal state; recovery is the repository's job.
            self._increment(lease_lost=1)
            self._emit("LEASE_LOST", claimed, at=self._clock(), error=str(error))
        except Exception as error:  # noqa: BLE001 - every failure must be recorded
            self._record_failure(claimed, error)
        else:
            run_ms = (time.perf_counter() - started) * 1000.0
            self._increment(succeeded=1)
            self._emit(
                "SUCCEEDED",
                claimed,
                at=self._clock(),
                queue_wait_ms=queue_wait,
                run_ms=run_ms,
            )
        finally:
            heartbeat.stop()
            heartbeat.join(timeout=5.0)
            with self._lock:
                self._in_flight.pop(claimed.job_id, None)

    def _record_failure(self, claimed: SchedulingJob, error: Exception) -> None:
        retryable = bool(getattr(error, "retryable", False))
        message = f"{type(error).__name__}: {error}"
        try:
            updated = self._service.fail(
                tenant_id=claimed.tenant_id,
                project_id=claimed.project_id,
                job_id=claimed.job_id,
                token=claimed.lease_token or "",
                error=message,
                retryable=retryable,
            )
        except SchedulingJobCancelled:
            self._increment(cancelled=1)
            self._emit("CANCELLED", claimed, at=self._clock())
            return
        except SchedulingJobLeaseError as lease_error:
            self._increment(lease_lost=1)
            self._emit(
                "LEASE_LOST", claimed, at=self._clock(), error=str(lease_error)
            )
            return
        if updated.state is SchedulingJobState.QUEUED:
            self._increment(retried=1)
            self._emit("RETRY_QUEUED", claimed, at=self._clock(), error=message)
        else:
            self._increment(failed=1)
            self._emit("FAILED", claimed, at=self._clock(), error=message)

    def _emit(
        self,
        kind: str,
        job: SchedulingJob,
        *,
        at: datetime,
        queue_wait_ms: float | None = None,
        run_ms: float | None = None,
        error: str | None = None,
    ) -> None:
        if self._event_sink is None:
            return
        self._event_sink(
            SchedulingJobEvent(
                kind=kind,
                job_id=job.job_id,
                tenant_id=job.tenant_id,
                project_id=job.project_id,
                owner=self._owner,
                at=at,
                queue_wait_ms=queue_wait_ms,
                run_ms=run_ms,
                error=error,
            )
        )

    # -- P0-N process placement -------------------------------------------

    def _run_process_mode(self, *, timeout: float | None) -> SchedulingExecutionSummary:
        """Drain the queue by running each job in its own process.

        The dispatching thread stays responsive: it renews leases synchronously
        (so no heartbeat thread exists to make a later fork unsafe), reaps
        finished children and re-allocates freed slots to waiting jobs.
        """
        deadline = None if timeout is None else time.monotonic() + timeout
        idle_polls = 0
        while not self._stop.is_set():
            self._reap_process_jobs()
            self._renew_process_leases()
            pending = self._service.pending_count()
            active = len(self._process_jobs)
            target = self._controller.observe(pending=pending, active=active)
            self._dispatch_process_jobs(pending=pending, target=target)
            if pending == 0 and not self._process_jobs:
                idle_polls += 1
                if idle_polls >= self._idle_polls_before_exit:
                    break
            else:
                idle_polls = 0
            if deadline is not None and time.monotonic() >= deadline:
                break
            if self._poll_interval:
                time.sleep(self._poll_interval)
        # In-flight calculations finish, exactly like the thread path.
        while self._process_jobs:
            self._reap_process_jobs()
            self._renew_process_leases()
            if not self._process_jobs:
                break
            time.sleep(max(self._poll_interval, 0.005))
        with self._lock:
            counters = self._counters
        return SchedulingExecutionSummary(
            claimed=counters.claimed,
            succeeded=counters.succeeded,
            failed=counters.failed,
            retried=counters.retried,
            cancelled=counters.cancelled,
            lease_lost=counters.lease_lost,
            skipped=counters.skipped,
            idle_polls=idle_polls,
            stopped=self._stop.is_set(),
            process_starts=counters.process_starts,
            inline_fallbacks=counters.inline_fallbacks,
            cache_hits=counters.cache_hits,
            cache_misses=counters.cache_misses,
            slots_acquired_total=counters.slots_acquired_total,
            peak_slots=counters.peak_slots,
        )

    def _dispatch_process_jobs(self, *, pending: int, target: int) -> None:
        if pending <= 0:
            return
        # The controller bounds how many *jobs* run at once; the slot budget
        # alone bounds how many slots those jobs share, so one project alone
        # still receives the whole machine.
        free_slots = self._budget.workers - self._slots_held
        jobs_allowed = target - len(self._process_jobs)
        if free_slots <= 0 or jobs_allowed <= 0:
            return
        candidates = self._service.queued_jobs(self._dispatch_batch)
        if not candidates:
            return
        now = time.monotonic()
        wall_now = self._clock()
        descriptors: list[PendingTask] = []
        by_id: dict[str, SchedulingJob] = {}
        for job in candidates:
            if job.job_id in self._process_jobs:
                continue
            workload = None
            if self._workload_estimator is not None:
                try:
                    workload = self._workload_estimator(job)
                except Exception:  # noqa: BLE001 - a hint must never fail a job
                    workload = None
            queued_seconds = max(0.0, (wall_now - job.created_at).total_seconds())
            descriptors.append(
                PendingTask(
                    key=job.job_id,
                    workload=workload or ProjectWorkload(),
                    submitted_at=now - queued_seconds,
                    priority=0,
                    tenant_id=job.tenant_id,
                )
            )
            by_id[job.job_id] = job
        if not descriptors:
            return
        grants = self._slot_policy.plan(
            descriptors,
            free_slots=free_slots,
            active_jobs=len(self._process_jobs),
            now=now,
        )
        started = 0
        for grant in grants:
            if started >= jobs_allowed:
                break
            job = by_id.get(grant.key)
            if job is not None:
                self._start_process_job(job, grant.slots)
                started += 1

    def _start_process_job(self, job: SchedulingJob, slots: int) -> None:
        claimed_at = self._clock()
        try:
            claimed = self._service.claim(
                tenant_id=job.tenant_id,
                project_id=job.project_id,
                job_id=job.job_id,
                owner=self._owner,
            )
        except SchedulingJobError:
            self._increment(skipped=1)
            return
        self._increment(claimed=1)
        queue_wait = max(0.0, (claimed_at - claimed.created_at).total_seconds() * 1000.0)
        self._emit("CLAIMED", claimed, at=claimed_at, queue_wait_ms=queue_wait)

        cached = self._cached_result(claimed)
        if cached is not None:
            try:
                self._service.complete(
                    tenant_id=claimed.tenant_id,
                    project_id=claimed.project_id,
                    job_id=claimed.job_id,
                    token=claimed.lease_token or "",
                    result=cached,
                )
            except SchedulingJobCancelled:
                self._increment(cancelled=1)
                self._emit("CANCELLED", claimed, at=self._clock())
            except SchedulingJobLeaseError as error:
                self._increment(lease_lost=1)
                self._emit("LEASE_LOST", claimed, at=self._clock(), error=str(error))
            except Exception as error:  # noqa: BLE001
                self._record_failure(claimed, error)
            else:
                self._increment(succeeded=1)
                self._emit("SUCCEEDED", claimed, at=self._clock(), queue_wait_ms=queue_wait)
            return

        if not self._acquire_slots(slots):
            self._record_failure(
                claimed,
                SchedulingExecutionError("WORKER_BUDGET_UNAVAILABLE", retryable=True),
            )
            return

        use_slots = self._calculate_with_slots is not None
        runner: Callable[..., SchedulingJobResult]
        runner = self._calculate_with_slots if use_slots else self._calculate
        if not self._start_method_explicit:
            method = _default_start_method()
            if method != self._start_method:
                self._start_method = method
                self._mp = multiprocessing.get_context(method) if method else None
        receiver = sender = process = None
        start_failed = False
        if self._mp is None:
            start_failed = True
        elif self._start_method != "fork":
            try:
                pickle.dumps((runner, claimed))
            except Exception:  # noqa: BLE001 - not transferable by value
                start_failed = True
        if not start_failed:
            try:
                receiver, sender = self._mp.Pipe(duplex=False)
                process = self._mp.Process(
                    target=_process_job_entry,
                    args=(runner, use_slots, claimed, slots, sender),
                    name=f"sched-proc-{claimed.job_id[:12]}",
                    daemon=False,
                )
                process.start()
                sender.close()
                sender = None
            except Exception:  # noqa: BLE001 - process creation unavailable
                start_failed = True
                if receiver is not None:
                    receiver.close()
                if sender is not None:
                    sender.close()
                receiver = sender = process = None
        if start_failed or process is None or receiver is None:
            self._increment(inline_fallbacks=1)
            started = time.monotonic()
            try:
                result = self._calculate(claimed)
            except Exception as error:  # noqa: BLE001
                self._release_slots(slots)
                self._record_failure(claimed, error)
                return
            self._complete_successful(claimed, result, started, queue_wait, slots)
            return
        assert process.pid is not None
        self._process_jobs[claimed.job_id] = _ProcessJob(
            job=claimed,
            process=process,
            receiver=receiver,
            slots=slots,
            started=time.monotonic(),
            queue_wait_ms=queue_wait,
            next_renewal=time.monotonic() + self._lease_interval(),
        )
        self._increment(process_starts=1)

    def _lease_interval(self) -> float:
        return max(self._service.lease_ttl.total_seconds() / 3.0, 0.05)

    def _renew_process_leases(self) -> None:
        now = time.monotonic()
        for job_id, run in list(self._process_jobs.items()):
            if now < run.next_renewal:
                continue
            try:
                self._service.renew(
                    tenant_id=run.job.tenant_id,
                    project_id=run.job.project_id,
                    job_id=job_id,
                    token=run.job.lease_token or "",
                )
            except SchedulingJobCancelled:
                self._abort_process(run, cancelled=True)
                continue
            except SchedulingJobLeaseError as error:
                self._abort_process(run, cancelled=False, error=str(error))
                continue
            except SchedulingJobError as error:
                self._abort_process(run, cancelled=False, error=str(error))
                continue
            run.next_renewal = time.monotonic() + self._lease_interval()

    def _abort_process(
        self, run: _ProcessJob, *, cancelled: bool, error: str | None = None
    ) -> None:
        try:
            run.process.terminate()
        finally:
            run.process.join(timeout=1.0)
            run.receiver.close()
        self._process_jobs.pop(run.job.job_id, None)
        self._release_slots(run.slots)
        if cancelled:
            self._increment(cancelled=1)
            self._emit("CANCELLED", run.job, at=self._clock())
        else:
            self._increment(lease_lost=1)
            self._emit("LEASE_LOST", run.job, at=self._clock(), error=error)

    def _reap_process_jobs(self) -> None:
        now = time.monotonic()
        for job_id, run in list(self._process_jobs.items()):
            # Read a published payload *before* waiting for exit. A child that
            # has finished calculating but whose result exceeds the OS pipe
            # buffer stays blocked in ``send`` until the parent reads, so
            # joining first would deadlock both sides until the job timeout.
            self._drain_process_pipe(run, timeout=0.0)
            if run.process.is_alive():
                if self._job_timeout is not None and now - run.started > self._job_timeout:
                    run.timed_out = True
                    run.process.terminate()
                continue
            self._drain_process_pipe(run, timeout=0.1)
            self._finish_process_job(run)

    def _drain_process_pipe(self, run: _ProcessJob, *, timeout: float) -> None:
        """Move a completed child payload out of the pipe into ``run``.

        Safe to call while the child is alive: it only reads once ``poll``
        reports that bytes are buffered (the child is mid-``send`` or has
        finished it), and it treats EOF/truncation as "no payload".
        """
        if run.payload is not None or run.pipe_closed:
            return
        try:
            if not run.receiver.poll(timeout):
                return
            run.payload = run.receiver.recv()
        except (EOFError, OSError, pickle.UnpicklingError):
            run.pipe_closed = True

    def _finish_process_job(self, run: _ProcessJob) -> None:
        run.process.join(timeout=1.0)
        self._drain_process_pipe(run, timeout=0.1)
        payload = run.payload
        run.receiver.close()
        self._process_jobs.pop(run.job.job_id, None)
        self._release_slots(run.slots)
        slots = 0  # already released
        started = run.started
        if run.timed_out:
            self._record_failure(
                run.job,
                SchedulingExecutionError("SCHEDULING_JOB_TIMEOUT", retryable=True),
            )
            return
        if payload is not None and payload[0] == "ok":
            self._complete_successful(
                run.job, payload[1], started, run.queue_wait_ms, slots
            )
            return
        if payload is not None and payload[0] == "error":
            message = str(payload[1])
            retryable = bool(payload[2])
            if "SCHEDULING_JOB_CANCELLED" in message:
                self._increment(cancelled=1)
                self._emit("CANCELLED", run.job, at=self._clock())
                return
            self._record_failure(run.job, SchedulingExecutionError(message, retryable=retryable))
            return
        self._record_failure(
            run.job,
            SchedulingExecutionError(
                f"CHILD_EXITED_WITHOUT_RESULT:exitcode={run.process.exitcode}",
                retryable=True,
            ),
        )

    def _complete_successful(
        self,
        job: SchedulingJob,
        result: SchedulingJobResult,
        started: float,
        queue_wait: float,
        slots: int,
    ) -> None:
        try:
            self._service.complete(
                tenant_id=job.tenant_id,
                project_id=job.project_id,
                job_id=job.job_id,
                token=job.lease_token or "",
                result=result,
            )
        except SchedulingJobCancelled:
            self._release_slots(slots)
            self._increment(cancelled=1)
            self._emit("CANCELLED", job, at=self._clock())
            return
        except SchedulingJobLeaseError as error:
            self._release_slots(slots)
            self._increment(lease_lost=1)
            self._emit("LEASE_LOST", job, at=self._clock(), error=str(error))
            return
        except Exception as error:  # noqa: BLE001
            self._release_slots(slots)
            self._record_failure(job, error)
            return
        self._release_slots(slots)
        if self._result_cache is not None:
            self._store_cache(job, result)
        run_ms = (time.monotonic() - started) * 1000.0
        self._increment(succeeded=1)
        self._emit("SUCCEEDED", job, at=self._clock(), queue_wait_ms=queue_wait, run_ms=run_ms)

    # -- slots ------------------------------------------------------------

    def _acquire_slots(self, requested: int) -> bool:
        acquired = 0
        for _ in range(requested):
            if not self._budget.try_acquire(timeout=0.0):
                break
            acquired += 1
        if acquired < requested:
            for _ in range(acquired):
                self._budget.release()
            return False
        self._slots_held += acquired
        with self._lock:
            self._counters = replace(
                self._counters,
                slots_acquired_total=self._counters.slots_acquired_total + 1,
            )
        peak = max(self._counters.peak_slots, self._slots_held)
        with self._lock:
            self._counters = replace(self._counters, peak_slots=peak)
        return True

    def _release_slots(self, slots: int) -> None:
        if slots <= 0:
            return
        for _ in range(slots):
            self._budget.release()
        self._slots_held = max(0, self._slots_held - slots)

    # -- result cache -----------------------------------------------------

    def _cache_key(self, job: SchedulingJob) -> CacheKey:
        return CacheKey(
            tenant_id=job.tenant_id,
            project_id=job.project_id,
            calculation_identity=job.calculation_identity,
            engine_version=job.engine_version,
        )

    def _cached_result(self, job: SchedulingJob) -> SchedulingJobResult | None:
        if self._result_cache is None:
            return None
        stored = self._result_cache.get(self._cache_key(job))
        if stored is None:
            with self._lock:
                self._counters = replace(
                    self._counters, cache_misses=self._counters.cache_misses + 1
                )
            return None
        try:
            decoded = json.loads(stored.decode("utf-8"))
            output_hash = decoded["output_hash"]
            payload = decoded["payload"]
        except (ValueError, KeyError, UnicodeDecodeError):
            with self._lock:
                self._counters = replace(
                    self._counters, cache_misses=self._counters.cache_misses + 1
                )
            return None
        if not isinstance(output_hash, str) or not isinstance(payload, dict):
            with self._lock:
                self._counters = replace(
                    self._counters, cache_misses=self._counters.cache_misses + 1
                )
            return None
        with self._lock:
            self._counters = replace(
                self._counters, cache_hits=self._counters.cache_hits + 1
            )
        return SchedulingJobResult(
            tenant_id=job.tenant_id,
            project_id=job.project_id,
            job_id=job.job_id,
            engine_version=job.engine_version,
            calculation_identity=job.calculation_identity,
            output_hash=output_hash,
            payload=payload,
            persisted_at=self._clock(),
        )

    def _store_cache(self, job: SchedulingJob, result: SchedulingJobResult) -> None:
        if self._result_cache is None:
            return
        try:
            encoded = json.dumps(
                {"output_hash": result.output_hash, "payload": dict(result.payload)},
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                default=str,
            ).encode("utf-8")
        except (TypeError, ValueError):
            return
        self._result_cache.put(self._cache_key(job), encoded)


# ---------------------------------------------------------------------------
# P0-N: process placement behind the same lifecycle
# ---------------------------------------------------------------------------


@dataclass
class _ProcessJob:
    """One calculation process the executor owns."""

    job: SchedulingJob
    process: Any
    receiver: Any
    slots: int
    started: float
    queue_wait_ms: float
    next_renewal: float
    timed_out: bool = False
    payload: tuple | None = None
    pipe_closed: bool = False


def _process_job_entry(
    calculate: Callable[..., SchedulingJobResult],
    use_slots: bool,
    job: SchedulingJob,
    slots: int,
    sender: Any,
) -> None:  # pragma: no cover - runs in a child process
    """Run one claimed job in a dedicated, non-daemonic process.

    The child is single-threaded, so the engine may fork its own float workers
    inside the slot grant the parent reserved. Any exception is reported as a
    value so the parent can apply the normal failure/retry policy; a crash
    without a message is handled by the parent as a retryable failure.
    """
    try:
        result = calculate(job, slots) if use_slots else calculate(job)
        sender.send(("ok", result))
    except BaseException as error:  # noqa: BLE001 - forwarded to the parent
        try:
            sender.send(
                (
                    "error",
                    f"{type(error).__name__}: {error}",
                    bool(getattr(error, "retryable", False)),
                )
            )
        except BaseException:  # pragma: no cover - broken pipe
            pass
    finally:
        sender.close()


class _LeaseHeartbeat:
    """Renew a lease while a slow calculation runs.

    A renewal that observes a cancellation request flips ``cancelled`` so the
    executor discards the result instead of publishing it. Renewal failures are
    recorded but never mask the calculation's own exception.
    """

    def __init__(
        self, *, service: SchedulingJobService, job: SchedulingJob, interval: float
    ) -> None:
        self._service = service
        self._job = job
        self._interval = interval
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._run, name=f"sched-lease-{job.job_id[:12]}", daemon=True
        )
        self.cancelled = False

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def join(self, timeout: float | None = None) -> None:
        self._thread.join(timeout=timeout)

    def _run(self) -> None:
        while not self._stop.wait(self._interval):
            try:
                self._service.renew(
                    tenant_id=self._job.tenant_id,
                    project_id=self._job.project_id,
                    job_id=self._job.job_id,
                    token=self._job.lease_token or "",
                )
            except SchedulingJobCancelled:
                self.cancelled = True
                return
            except SchedulingJobError:
                # Losing the lease is handled by the completion path; keep the
                # heartbeat quiet rather than raising in a daemon thread.
                return


__all__ = [
    "SchedulingExecutionError",
    "SchedulingExecutionSummary",
    "SchedulingJobEvent",
    "SchedulingJobExecutor",
]
