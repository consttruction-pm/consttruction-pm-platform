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

import threading
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Callable

from .scheduling_execution_budget import (
    AdaptiveWorkerController,
    GlobalExecutionBudget,
    global_execution_budget,
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
    ) -> None:
        if not owner or not owner.strip():
            raise SchedulingExecutionError("INVALID_EXECUTOR_OWNER")
        if poll_interval < 0:
            raise SchedulingExecutionError("INVALID_POLL_INTERVAL")
        if dispatch_batch < 1:
            raise SchedulingExecutionError("INVALID_DISPATCH_BATCH")
        if idle_polls_before_exit < 1:
            raise SchedulingExecutionError("INVALID_IDLE_POLLS")
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
        with self._lock:
            return len(self._in_flight)

    def run_once(self) -> bool:
        """Claim and execute one queued job. Returns False when none is queued."""
        if self._recover_expired:
            self._service.recover_expired(limit=self._dispatch_batch)
        candidates = self._service.queued_jobs(1)
        if not candidates:
            return False
        self._run_job(candidates[0])
        return True

    def run_until_idle(self, *, timeout: float | None = None) -> SchedulingExecutionSummary:
        """Drain the queue with an adaptively sized dispatch target.

        Returns when the queue is empty and no calculation is in flight, when
        ``timeout`` elapses, or when ``request_stop`` is called. In-flight
        calculations finish; stopping never abandons a lease silently.
        """
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
