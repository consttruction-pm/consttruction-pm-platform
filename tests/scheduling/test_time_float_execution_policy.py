"""P0-J phase 3: safe parallel float execution in the real worker path.

The float pass is the only part of the time-aware engine that can run in
child processes. These tests pin the two properties that matter:

* a worker count can change elapsed time but never a value, so the canonical
  payload hash is identical for 1 and N slots;
* a threaded process is never forked (the job executor calculates on a worker
  thread), the one process-wide budget caps the pool, and every unsuitable
  state falls back to the exact sequential loop.
"""

from __future__ import annotations

import importlib
import multiprocessing
import threading

import pytest

time_schedule_module = importlib.import_module("construction_pm.scheduling.time_schedule")
from construction_pm.scheduling.benchmark_fixtures import (
    canonical_hash,
    time_network,
    time_schedule_payload,
)
from construction_pm.scheduling.time_schedule import (
    FloatExecutionPolicy,
    _select_float_start_method,
    _time_float_context,
    time_backward_pass,
    time_forward_pass,
    time_schedule,
)
from construction_pm.scheduling_execution_budget import (
    GlobalExecutionBudget,
    SchedulingBudgetError,
)


def _fixture(size: int = 40):
    network = time_network(size, "mixed", 20261117)
    early = time_forward_pass(
        network.activities,
        network.relationships,
        network.project_start,
        network.registry,
    )
    finish = max(item.finish for item in early.values())
    late = time_backward_pass(
        network.activities,
        network.relationships,
        early,
        finish,
        network.registry,
    )
    context = _time_float_context(
        network.activities,
        network.relationships,
        early,
        late,
        network.registry,
        None,
    )
    return network, context


def _schedule(network, *, policy: FloatExecutionPolicy | None = None):
    return time_schedule(
        network.activities,
        network.relationships,
        network.project_start,
        network.project_finish,
        network.registry,
        float_policy=policy,
    )


class _grant:
    """Trivial admission context manager that grants a fixed total."""

    def __init__(self, requested: int, granted: int) -> None:
        self.requested = requested
        self.granted = min(requested, granted)

    def __enter__(self) -> int:
        return self.granted

    def __exit__(self, *exc) -> None:
        return None


def test_policy_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="INVALID_FLOAT_WORKERS"):
        FloatExecutionPolicy(workers=0)
    with pytest.raises(ValueError, match="INVALID_FLOAT_WORKERS"):
        FloatExecutionPolicy(workers=True)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="INVALID_FLOAT_ADMISSION"):
        FloatExecutionPolicy(workers=2, admission=3)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="INVALID_FLOAT_ALLOW_SPAWN"):
        FloatExecutionPolicy(workers=2, allow_spawn="yes")  # type: ignore[arg-type]


def test_start_method_never_forks_a_threaded_process() -> None:
    _, context = _fixture()
    default: list[str | None] = []
    opted_in: list[str | None] = []

    def probe() -> None:
        default.append(_select_float_start_method(context))
        opted_in.append(_select_float_start_method(context, allow_spawn=True))

    thread = threading.Thread(target=probe)
    thread.start()
    thread.join()
    # Threaded process: fork is never safe, spawn only on explicit opt-in.
    assert default == [None]
    assert opted_in == ["spawn"]


def test_pool_merge_is_identical_for_any_worker_count() -> None:
    network, _ = _fixture(60)
    sequential = _schedule(network)
    expected = canonical_hash(time_schedule_payload(sequential))

    for workers in (2, 3, 4):
        parallel = _schedule(
            network,
            policy=FloatExecutionPolicy(
                workers=workers,
                admission=lambda requested: _grant(requested, workers),
            ),
        )
        assert canonical_hash(time_schedule_payload(parallel)) == expected
        assert parallel.floats == sequential.floats


class _RecordingContext:
    """Proxy that records which start method created a pool."""

    def __init__(self, context, method, log: list[str]) -> None:
        self._context = context
        self._method = method
        self._log = log

    def Pool(self, *args, **kwargs):
        self._log.append(self._method)
        return self._context.Pool(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._context, name)


def test_worker_thread_produces_the_same_canonical_hash(monkeypatch) -> None:
    network, _ = _fixture(50)
    expected = canonical_hash(time_schedule_payload(_schedule(network)))
    budget = GlobalExecutionBudget(4)
    seen: list[str] = []
    errors: list[BaseException] = []
    pool_methods: list[str] = []

    real_get_context = multiprocessing.get_context

    def recording_get_context(method=None):
        context = real_get_context(method)
        return _RecordingContext(context, method, pool_methods)

    monkeypatch.setattr(multiprocessing, "get_context", recording_get_context)

    def run() -> None:
        try:
            result = _schedule(
                network,
                policy=FloatExecutionPolicy(
                    workers=3, admission=budget.admit_extra, allow_spawn=True
                ),
            )
            seen.append(canonical_hash(time_schedule_payload(result)))
        except BaseException as error:  # noqa: BLE001 - surface in the main thread
            errors.append(error)

    thread = threading.Thread(target=run)
    thread.start()
    thread.join()

    assert errors == []
    assert seen == [expected]
    # The pool reserved its extra slots from the same budget and returned them.
    assert budget.extra_active == 0
    assert budget.extra_peak >= 1
    assert budget.active == 0
    # Spawned children are separate processes, so the hash also proves the
    # immutable float context crossed the process boundary unchanged.
    assert budget.extra_acquired_total >= 1
    # The threaded process created its pool with spawn; fork was never used.
    assert pool_methods == ["spawn"]


def test_threaded_process_stays_sequential_without_opt_in(monkeypatch) -> None:
    network, _ = _fixture(40)
    expected = canonical_hash(time_schedule_payload(_schedule(network)))
    budget = GlobalExecutionBudget(4)
    pool_methods: list[str] = []

    real_get_context = multiprocessing.get_context

    def recording_get_context(method=None):
        context = real_get_context(method)
        return _RecordingContext(context, method, pool_methods)

    monkeypatch.setattr(multiprocessing, "get_context", recording_get_context)
    seen: list[str] = []

    def run() -> None:
        result = _schedule(
            network,
            policy=FloatExecutionPolicy(workers=3, admission=budget.admit_extra),
        )
        seen.append(canonical_hash(time_schedule_payload(result)))

    thread = threading.Thread(target=run)
    thread.start()
    thread.join()

    assert seen == [expected]
    assert pool_methods == []
    assert budget.extra_peak == 0


def test_exhausted_budget_falls_back_to_exact_sequential_loop() -> None:
    network, _ = _fixture(20)
    expected = canonical_hash(time_schedule_payload(_schedule(network)))
    budget = GlobalExecutionBudget(1)
    with budget.permit():
        result = _schedule(
            network,
            policy=FloatExecutionPolicy(workers=4, admission=budget.admit_extra),
        )
    assert canonical_hash(time_schedule_payload(result)) == expected
    assert budget.extra_peak == 0
    assert budget.active == 0


def test_float_workers_keyword_still_selects_the_same_execution_path() -> None:
    network, _ = _fixture(20)
    sequential = time_schedule(
        network.activities,
        network.relationships,
        network.project_start,
        network.project_finish,
        network.registry,
    )
    legacy = time_schedule(
        network.activities,
        network.relationships,
        network.project_start,
        network.project_finish,
        network.registry,
        float_workers=2,
    )
    assert canonical_hash(time_schedule_payload(legacy)) == canonical_hash(
        time_schedule_payload(sequential)
    )


def test_admit_extra_never_exceeds_the_process_budget() -> None:
    budget = GlobalExecutionBudget(4)
    assert budget.workers == 4
    with budget.permit():
        with budget.admit_extra(8) as granted:
            assert granted == 4
            assert budget.extra_active == 3
            assert budget.active == 1
        assert budget.extra_active == 0
    assert budget.active == 0
    assert budget.extra_peak == 3


def test_admit_extra_returns_only_what_is_available() -> None:
    budget = GlobalExecutionBudget(2)
    with budget.permit():
        with budget.permit():
            with budget.admit_extra(4) as granted:
                assert granted == 1
        with budget.admit_extra(4) as granted:
            assert granted == 2
    assert budget.active == 0
    assert budget.extra_active == 0


def test_admit_extra_validates_requests() -> None:
    budget = GlobalExecutionBudget(2)
    with pytest.raises(SchedulingBudgetError, match="INVALID_EXTRA_PERMIT_REQUEST"):
        with budget.admit_extra(0):
            pass
    with pytest.raises(SchedulingBudgetError, match="INVALID_EXTRA_PERMIT_TIMEOUT"):
        with budget.admit_extra(2, timeout=-1):
            pass


def test_nested_float_pool_is_refused() -> None:
    network, _ = _fixture(20)
    expected = time_schedule_payload(_schedule(network))["floats"]
    assert time_schedule_module._FLOAT_POOL_GUARD.acquire(blocking=False)
    try:
        result = _schedule(
            network,
            policy=FloatExecutionPolicy(workers=3, admission=lambda requested: _grant(requested, 3)),
        )
    finally:
        time_schedule_module._FLOAT_POOL_GUARD.release()
    assert time_schedule_payload(result)["floats"] == expected
