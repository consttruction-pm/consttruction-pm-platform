"""Standalone durable scheduling worker for the production runtime.

The web runtime (``ProductionRuntime``) only submits, reads and cancels
scheduling jobs: those calls live inside one HTTP request and can safely use
the pooled request connection. A calculation must not run on that connection
and must not run inside a serverless request, so this module owns the worker:

* one process holds one ``SchedulingJobService`` over the authoritative
  Postgres lifecycle and one ``SchedulingEngineJobRunner``;
* every thread that touches the database gets its own connection, because the
  executor runs calculations on worker threads and renews leases from a
  heartbeat thread;
* the connection is in ``autocommit`` mode. Every lifecycle mutation is a
  single compare-and-set or insert statement, so each statement is atomic on
  its own; no cross-thread transaction is ever shared.

``thread`` mode runs jobs in-process (single float worker per job). ``process``
mode gives each job a dedicated child process that opens its own connection
from the DSN, which is the only safe way to fork an engine with several float
workers.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
from dataclasses import dataclass
from typing import Any, Mapping

from ..backend_p0.authoritative_schedule_query import AuthoritativeScheduleQueryProvider
from ..calendar_exception_repository import PostgresCalendarExceptionRepository
from ..calendar_master_repository import PostgresCalendarMasterRepository
from ..calendar_snapshot_repository import PostgresCalendarSnapshotRepository
from ..calendar_work_hours_repository import PostgresCalendarWorkHourRepository
from ..p6_versioned_resource_calendar_resolver import build_calendar_registry_for_scope
from ..postgres_scheduling_job_lifecycle import PostgresSchedulingJobRepository
from ..schedule_calculation_context_repository import (
    PostgresCalculationContextRepository,
)
from ..schedule_input_snapshot_repository import (
    PostgresScheduleInputSnapshotRepository,
)
from ..scheduling_execution_budget import GlobalExecutionBudget
from ..scheduling_job_lifecycle import SchedulingJobService
from ..scheduling_job_runner import SchedulingEngineJobRunner, SchedulingJobRunOutcome
from .schema import initialize_production_schema


class SchedulingWorkerConfigurationError(RuntimeError):
    """Worker startup is incomplete; the message is safe to log."""


class ThreadLocalConnection:
    """One autocommit Postgres connection per thread, opened on first use."""

    def __init__(self, database_url: str, *, connect_timeout: int = 10) -> None:
        self._database_url = database_url
        self._connect_timeout = connect_timeout
        self._local = threading.local()
        self._all: list[Any] = []
        self._lock = threading.Lock()

    def _connection(self) -> Any:
        import psycopg

        connection = getattr(self._local, "connection", None)
        if connection is None or getattr(connection, "closed", False):
            connection = psycopg.connect(
                self._database_url,
                autocommit=True,
                connect_timeout=self._connect_timeout,
                options="-c statement_timeout=600000",
            )
            self._local.connection = connection
            with self._lock:
                self._all.append(connection)
        return connection

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
        return self._connection().execute(sql, params)

    def commit(self) -> None:
        # The connection is in autocommit mode; every statement is already
        # committed when execute() returns.
        return None

    def rollback(self) -> None:
        return None

    def close_all(self) -> None:
        with self._lock:
            connections, self._all = self._all, []
        for connection in connections:
            try:
                connection.close()
            except Exception:  # pragma: no cover - close must never raise
                pass


@dataclass(frozen=True)
class SchedulingWorkerSettings:
    database_url: str
    execution_mode: str = "thread"
    owner: str = "scheduling-worker"
    slots: int = 0
    poll_interval: float = 0.25
    job_timeout: float | None = None
    connect_timeout: int = 10

    @classmethod
    def from_environment(
        cls, environment: Mapping[str, str] | None = None
    ) -> "SchedulingWorkerSettings":
        env = os.environ if environment is None else environment
        database_url = env.get("CONSTRUCTION_PM_DATABASE_URL", "").strip()
        if not database_url.startswith(("postgresql://", "postgres://")):
            raise SchedulingWorkerConfigurationError(
                "CONSTRUCTION_PM_DATABASE_URL_INVALID"
            )
        mode = env.get("CONSTRUCTION_PM_SCHEDULING_WORKER_MODE", "thread").strip()
        if mode not in ("thread", "process"):
            raise SchedulingWorkerConfigurationError("SCHEDULING_WORKER_MODE_INVALID")
        owner = env.get("CONSTRUCTION_PM_SCHEDULING_WORKER_OWNER", "").strip() or (
            f"{os.uname().nodename}-{os.getpid()}"
        )
        raw_slots = env.get("CONSTRUCTION_PM_SCHEDULING_WORKER_SLOTS", "").strip()
        try:
            slots = int(raw_slots) if raw_slots else 0
        except ValueError as error:
            raise SchedulingWorkerConfigurationError(
                "SCHEDULING_WORKER_SLOTS_INVALID"
            ) from error
        if slots and not 1 <= slots <= 128:
            raise SchedulingWorkerConfigurationError("SCHEDULING_WORKER_SLOTS_INVALID")
        raw_poll = env.get("CONSTRUCTION_PM_SCHEDULING_WORKER_POLL", "").strip()
        try:
            poll = float(raw_poll) if raw_poll else 0.25
        except ValueError as error:
            raise SchedulingWorkerConfigurationError(
                "SCHEDULING_WORKER_POLL_INVALID"
            ) from error
        raw_timeout = env.get(
            "CONSTRUCTION_PM_SCHEDULING_WORKER_JOB_TIMEOUT", ""
        ).strip()
        try:
            job_timeout = float(raw_timeout) if raw_timeout else None
        except ValueError as error:
            raise SchedulingWorkerConfigurationError(
                "SCHEDULING_WORKER_JOB_TIMEOUT_INVALID"
            ) from error
        return cls(
            database_url=database_url,
            execution_mode=mode,
            owner=owner,
            slots=slots,
            poll_interval=max(0.0, poll),
            job_timeout=job_timeout,
            connect_timeout=max(
                2,
                min(
                    30,
                    int(
                        env.get("CONSTRUCTION_PM_DB_CONNECT_TIMEOUT", "10") or 10
                    ),
                ),
            ),
        )


class SchedulingWorkerRuntime:
    """One durable worker: Postgres lifecycle, real calendars, real engine."""

    def __init__(
        self,
        settings: SchedulingWorkerSettings,
        *,
        budget: GlobalExecutionBudget | None = None,
        start_method: str | None = None,
    ) -> None:
        self.settings = settings
        self.connection = ThreadLocalConnection(
            settings.database_url, connect_timeout=settings.connect_timeout
        )
        self._initialize_schema()
        self._budget = budget or GlobalExecutionBudget(
            settings.slots or _default_slots()
        )
        if settings.slots and settings.slots != self._budget.workers:
            raise SchedulingWorkerConfigurationError(
                "SCHEDULING_WORKER_BUDGET_MISMATCH"
            )

        master_repository = PostgresCalendarMasterRepository(self.connection)
        calendar_snapshot_repository = PostgresCalendarSnapshotRepository(
            self.connection
        )
        exception_repository = PostgresCalendarExceptionRepository(self.connection)
        work_hours_repository = PostgresCalendarWorkHourRepository(self.connection)

        def scoped_factory(scope):
            return build_calendar_registry_for_scope(
                scope=scope,
                calendar_repository=master_repository,
                snapshot_repository=calendar_snapshot_repository,
                exception_repository=exception_repository,
                work_hours_repository=work_hours_repository,
            )

        provider = AuthoritativeScheduleQueryProvider(
            snapshot_repository=PostgresScheduleInputSnapshotRepository(self.connection),
            scoped_calendar_registry_factory=scoped_factory,
            calculation_context_repository=PostgresCalculationContextRepository(
                self.connection
            ),
        )
        self.service = SchedulingJobService(
            PostgresSchedulingJobRepository(self.connection)
        )
        self.runner = SchedulingEngineJobRunner(
            self.service,
            provider=None if settings.execution_mode == "process" else provider,
            child_database_url=(
                settings.database_url
                if settings.execution_mode == "process"
                else None
            ),
            execution_mode=settings.execution_mode,
            owner=settings.owner,
            budget=self._budget,
            job_timeout=settings.job_timeout,
            start_method=start_method,
            poll_interval=settings.poll_interval,
        )

    def _initialize_schema(self) -> None:
        import psycopg

        connection = psycopg.connect(
            self.settings.database_url,
            autocommit=False,
            connect_timeout=self.settings.connect_timeout,
        )
        try:
            initialize_production_schema(connection)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def run_once(self) -> tuple[SchedulingJobRunOutcome, bool]:
        return self.runner.run_once()

    def drain(self, *, timeout: float | None = None) -> SchedulingJobRunOutcome:
        outcome, _ = self.runner.drain(timeout=timeout)
        return outcome

    def run_forever(self, *, stop: threading.Event | None = None) -> None:
        stop_event = stop or threading.Event()
        while not stop_event.is_set():
            _, ran = self.runner.run_once()
            if not ran:
                stop_event.wait(self.settings.poll_interval)

    def snapshot(self) -> dict[str, object]:
        return self.runner.snapshot()

    def close(self) -> None:
        self.connection.close_all()


def _default_slots() -> int:
    try:
        return max(1, os.cpu_count() or 1)
    except Exception:  # pragma: no cover - defensive
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cubi-scheduling-worker",
        description="Run durable CUBI scheduling jobs from PostgreSQL.",
    )
    parser.add_argument(
        "--once", action="store_true", help="claim and execute at most one job"
    )
    parser.add_argument(
        "--drain",
        action="store_true",
        help="execute queued jobs until the queue is idle, then exit",
    )
    parser.add_argument("--timeout", type=float, default=None)
    parser.add_argument("--forever", action="store_true")
    arguments = parser.parse_args(argv)
    if not (arguments.once or arguments.drain or arguments.forever):
        parser.error("choose --once, --drain or --forever")

    try:
        runtime = SchedulingWorkerRuntime(
            SchedulingWorkerSettings.from_environment()
        )
    except SchedulingWorkerConfigurationError as error:
        print(f"cubi-worker: configuration error: {error}", file=sys.stderr)
        return 2
    try:
        if arguments.once:
            outcome, ran = runtime.run_once()
            print(f"cubi-worker: ran={ran} {outcome.as_dict()}")
        elif arguments.drain:
            print(f"cubi-worker: {runtime.drain(timeout=arguments.timeout).as_dict()}")
        else:
            runtime.run_forever()
    finally:
        runtime.close()
    return 0


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())


__all__ = [
    "SchedulingWorkerConfigurationError",
    "SchedulingWorkerRuntime",
    "SchedulingWorkerSettings",
    "ThreadLocalConnection",
    "main",
]
