"""P0-N: global slot allocation and process placement.

The policy tests are pure: they check the ordering and grant arithmetic. The
scheduler tests run real processes and compare the canonical payload hash with
the sequential engine, so a slot count can only change elapsed time.
"""

from __future__ import annotations

import multiprocessing
import time

import pytest

from construction_pm.scheduling.benchmark_fixtures import (
    canonical_hash,
    time_network,
    time_schedule_payload,
)
from construction_pm.scheduling.time_schedule import time_schedule
from construction_pm.scheduling_execution_budget import GlobalExecutionBudget
from construction_pm.scheduling_worker_scheduler import (
    GlobalWorkerScheduler,
    PendingTask,
    ProjectWorkload,
    SchedulingSchedulerError,
    SlotAllocationPolicy,
)


def _now() -> float:
    return 1000.0


def _task(
    key: str,
    activities: int | None,
    *,
    submitted_at: float = 990.0,
    priority: int = 0,
) -> PendingTask:
    return PendingTask(
        key=key,
        workload=ProjectWorkload(activities),
        submitted_at=submitted_at,
        priority=priority,
    )


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------


def test_workload_validation_and_size_key():
    with pytest.raises(SchedulingSchedulerError):
        ProjectWorkload(-1)
    with pytest.raises(SchedulingSchedulerError):
        ProjectWorkload(True)  # type: ignore[arg-type]
    assert ProjectWorkload(None).size_key > ProjectWorkload(10**9).size_key
    assert ProjectWorkload(10, 20).weight_bytes() == 10 * 512 + 20 * 160


def test_policy_rejects_invalid_settings():
    with pytest.raises(SchedulingSchedulerError):
        SlotAllocationPolicy(target_activities_per_slot=0)
    with pytest.raises(SchedulingSchedulerError):
        SlotAllocationPolicy(max_slots_per_job=0)
    with pytest.raises(SchedulingSchedulerError):
        SlotAllocationPolicy(aging_seconds=0)


def test_small_projects_run_first_and_get_one_slot():
    policy = SlotAllocationPolicy()
    plan = policy.plan(
        [_task("large", 25_000), _task("small", 400)],
        free_slots=4,
        active_jobs=0,
        now=_now(),
    )
    assert plan[0].key == "small" and plan[0].slots == 1
    assert sum(grant.slots for grant in plan) <= 4


def test_single_project_takes_the_whole_budget():
    policy = SlotAllocationPolicy()
    plan = policy.plan([_task("only", 50_000)], free_slots=8, active_jobs=0, now=_now())
    assert [(grant.key, grant.slots) for grant in plan] == [("only", 8)]


def test_reservation_leaves_a_slot_for_waiting_work():
    policy = SlotAllocationPolicy()
    plan = policy.plan(
        [_task("large", 50_000), _task("other", 50_000)],
        free_slots=2,
        active_jobs=0,
        now=_now(),
    )
    # With two queued large projects and two free slots the first may take only
    # one, so the second starts immediately instead of waiting for a full pass.
    assert plan[0].slots == 1
    assert sum(grant.slots for grant in plan) == 2


def test_size_share_and_max_slots_per_job():
    policy = SlotAllocationPolicy(max_slots_per_job=2)
    plan = policy.plan([_task("big", 100_000)], free_slots=8, active_jobs=0, now=_now())
    assert plan[0].slots == 2


def test_unknown_workload_is_conservative_and_ordered_last():
    policy = SlotAllocationPolicy()
    ordered = policy.order([_task("unknown", None), _task("known", 900)], now=_now())
    assert [task.key for task in ordered] == ["known", "unknown"]
    plan = policy.plan(
        [_task("unknown", None), _task("known", 5000)],
        free_slots=4,
        active_jobs=1,
        now=_now(),
    )
    slots = {grant.key: grant.slots for grant in plan}
    assert slots["unknown"] == 1


def test_aging_overtakes_a_newer_arrival():
    policy = SlotAllocationPolicy(aging_seconds=1.0)
    old = _task("old", 50_000, submitted_at=0.0)
    new = _task("new", 50_000, submitted_at=999.9)
    ordered = policy.order([new, old], now=_now())
    assert ordered[0].key == "old"


def test_plan_never_exceeds_free_slots_or_starts_with_zero():
    policy = SlotAllocationPolicy()
    tasks = [_task(f"job-{index}", 5000) for index in range(10)]
    plan = policy.plan(tasks, free_slots=3, active_jobs=0, now=_now())
    assert sum(grant.slots for grant in plan) <= 3
    assert all(grant.slots >= 1 for grant in plan)
    assert policy.plan(tasks, free_slots=0, active_jobs=0, now=_now()) == []


# ---------------------------------------------------------------------------
# Scheduler (real processes)
# ---------------------------------------------------------------------------


def _compute(args: tuple[int, str, str, int]) -> str:
    size, shape, seed, float_workers = args
    fixture = time_network(size, shape, seed)
    result = time_schedule(
        fixture.activities,
        fixture.relationships,
        fixture.project_start,
        fixture.project_finish,
        fixture.registry,
        float_workers=float_workers,
    )
    return canonical_hash(time_schedule_payload(result))


def _sequential_hash(size: int, shape: str = "dag", seed: int = 7) -> str:
    return _compute((size, shape, seed, 1))


def _scheduler(budget: int = 4, **kwargs) -> GlobalWorkerScheduler:
    return GlobalWorkerScheduler(
        budget=GlobalExecutionBudget(budget), poll_interval=0.002, **kwargs
    )


@pytest.mark.skipif(
    "fork" not in multiprocessing.get_all_start_methods(),
    reason="requires fork to inherit the test fixture",
)
def test_scheduler_runs_tasks_and_matches_sequential_hash():
    sizes = [(900, "dag", 3), (900, "mixed", 4), (600, "wide", 5), (600, "fan", 6)]
    scheduler = _scheduler(budget=3)
    for index, (size, shape, seed) in enumerate(sizes):
        scheduler.submit(
            f"job-{index}",
            lambda slots, item=(size, shape, seed, 1): _compute(item),
            workload=ProjectWorkload(size),
        )
    scheduler.run_until_idle()
    results = {row["key"]: row for row in scheduler.results()}
    assert len(results) == len(sizes)
    for index, (size, shape, seed) in enumerate(sizes):
        row = results[f"job-{index}"]
        assert row["state"] == "SUCCEEDED", row
    for index, (size, shape, seed) in enumerate(sizes):
        assert scheduler.value_for(f"job-{index}") == _sequential_hash(size, shape, seed)
    stats = scheduler.snapshot()
    assert stats["peak_slots"] <= 3
    assert stats["process_starts"] >= 1


@pytest.mark.skipif(
    "fork" not in multiprocessing.get_all_start_methods(),
    reason="requires fork to inherit the test fixture",
)
def test_scheduler_respects_the_global_budget_under_two_schedulers():
    budget = GlobalExecutionBudget(2)
    first = GlobalWorkerScheduler(budget=budget, poll_interval=0.002)
    second = GlobalWorkerScheduler(budget=budget, poll_interval=0.002)
    for scheduler, prefix in ((first, "a"), (second, "b")):
        for index in range(2):
            scheduler.submit(
                f"{prefix}-{index}",
                lambda slots: _compute((600, "dag", 11, 1)),
                workload=ProjectWorkload(600),
            )
    first.run_until_idle()
    second.run_until_idle()
    # Sequential draining of both schedulers can never compose more than the
    # budget; both peaks are recorded against the same semaphore.
    assert first.snapshot()["peak_slots"] <= 2
    assert second.snapshot()["peak_slots"] <= 2
    assert budget.peak <= 2


def test_scheduler_rejects_duplicate_keys_and_bad_arguments():
    scheduler = _scheduler(budget=1)
    scheduler.submit("job", lambda slots: 1)
    with pytest.raises(SchedulingSchedulerError):
        scheduler.submit("job", lambda slots: 2)
    with pytest.raises(SchedulingSchedulerError):
        scheduler.submit("", lambda slots: 1)
    with pytest.raises(SchedulingSchedulerError):
        scheduler.submit("other", "not-callable")  # type: ignore[arg-type]
    with pytest.raises(SchedulingSchedulerError):
        GlobalWorkerScheduler(start_method="does-not-exist")


def test_scheduler_cancels_a_pending_task():
    scheduler = _scheduler(budget=1)
    scheduler.submit("job", lambda slots: 1)
    assert scheduler.cancel("job") is True
    scheduler.run_until_idle()
    rows = {row["key"]: row for row in scheduler.results()}
    assert rows["job"]["state"] == "CANCELLED"
    assert scheduler.cancel("missing") is False


@pytest.mark.skipif(
    "fork" not in multiprocessing.get_all_start_methods(),
    reason="requires fork to inherit the test fixture",
)
def test_scheduler_reports_a_failing_task_without_stopping_others():
    def fail(slots: int) -> str:
        raise RuntimeError("boom")

    scheduler = _scheduler(budget=2)
    scheduler.submit("bad", fail)
    scheduler.submit("good", lambda slots: _compute((400, "dag", 9, 1)))
    scheduler.run_until_idle()
    rows = {row["key"]: row for row in scheduler.results()}
    assert rows["bad"]["state"] == "FAILED"
    assert "boom" in (rows["bad"]["error"] or "")
    assert rows["good"]["state"] == "SUCCEEDED"


@pytest.mark.skipif(
    "fork" not in multiprocessing.get_all_start_methods(),
    reason="requires fork to inherit the test fixture",
)
def test_scheduler_records_queue_wait_and_run_time():
    scheduler = _scheduler(budget=2)
    for index in range(2):
        scheduler.submit(
            f"job-{index}",
            lambda slots: _compute((700, "dag", 21, 1)),
            workload=ProjectWorkload(700),
        )
    scheduler.run_until_idle()
    for row in scheduler.results():
        assert row["queue_wait_ms"] is not None and row["queue_wait_ms"] >= 0
        assert row["run_ms"] is not None and row["run_ms"] > 0
        assert row["pid"] is not None


def test_scheduler_inline_fallback_when_no_start_method_is_available():
    scheduler = GlobalWorkerScheduler(
        budget=GlobalExecutionBudget(2), start_method=None, poll_interval=0.0
    )
    # Force the inline branch exactly as a platform without fork/spawn would.
    scheduler._start_method = None
    scheduler._mp = None  # type: ignore[attr-defined]
    scheduler.submit("job", lambda slots: 7)
    scheduler.run_until_idle()
    rows = scheduler.results()
    assert rows[0]["state"] == "SUCCEEDED"

def test_scheduler_stop_releases_every_slot():
    scheduler = _scheduler(budget=2)
    budget = scheduler.budget
    scheduler.submit("job", lambda slots: time.sleep(0.05) or "done")
    scheduler.run_until_idle()
    assert budget.active == 0
    assert scheduler.snapshot()["slots_held"] == 0


@pytest.mark.skipif(
    "fork" not in multiprocessing.get_all_start_methods(),
    reason="requires fork to inherit the test fixture",
)
def test_scheduler_holds_arrivals_until_their_release_time():
    scheduler = _scheduler(budget=2)
    now = time.monotonic()
    scheduler.submit("early", lambda slots: _compute((500, "dag", 21, 1)))
    scheduler.submit(
        "late",
        lambda slots: _compute((500, "dag", 21, 1)),
        release_at=now + 0.3,
    )
    scheduler.run_until_idle()
    rows = {row["key"]: row for row in scheduler.results()}
    assert rows["early"]["state"] == "SUCCEEDED"
    assert rows["late"]["state"] == "SUCCEEDED"
    assert rows["late"]["queue_wait_ms"] >= 250.0
    assert scheduler.snapshot()["slots_held"] == 0


@pytest.mark.skipif(
    "fork" not in multiprocessing.get_all_start_methods(),
    reason="requires fork to inherit the test fixture",
)
def test_scheduler_rejects_a_non_numeric_release_time():
    scheduler = _scheduler(budget=1)
    with pytest.raises(SchedulingSchedulerError):
        scheduler.submit("job", lambda slots: 1, release_at="soon")  # type: ignore[arg-type]


@pytest.mark.skipif(
    "fork" not in multiprocessing.get_all_start_methods(),
    reason="requires fork to inherit the test fixture",
)
def test_scheduler_result_cache_skips_a_repeated_project():
    from construction_pm.scheduling_result_cache import CacheKey, ScheduleResultCache

    key = CacheKey(
        tenant_id="tenant-a",
        project_id="project-600",
        calculation_identity="identity-v2",
        engine_version="v1",
    )
    cache = ScheduleResultCache(max_weight_bytes=8 * 1024 * 1024)
    first = _scheduler(budget=2)
    first.attach_result_cache(cache)
    first.submit(
        "project",
        lambda slots: _compute((600, "dag", 21, 1)),
        workload=ProjectWorkload(600),
        cache_key=key,
    )
    first.run_until_idle()
    assert cache.stats()["entries"] == 1

    second = _scheduler(budget=2)
    second.attach_result_cache(cache)
    second.submit(
        "project",
        lambda slots: _compute((600, "dag", 21, 1)),
        workload=ProjectWorkload(600),
        cache_key=key,
    )
    second.run_until_idle()
    rows = second.results()
    assert rows[0]["state"] == "CACHE_HIT"
    assert rows[0]["cache_hit"] is True
    assert second.snapshot()["process_starts"] == 0
    assert second.snapshot()["cache_hits"] == 1
    assert second.value_for("project") == first.value_for("project")
