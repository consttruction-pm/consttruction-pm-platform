"""Tests for the P0-G execution budget: detection, policy, permits, adaptation."""

from __future__ import annotations

import threading
from decimal import Decimal

import pytest

from construction_pm.scheduling_execution_budget import (
    AdaptiveWorkerController,
    EffectiveCapacity,
    GlobalExecutionBudget,
    SchedulingBudgetError,
    WorkerBudgetPolicy,
    configure_global_budget,
    detect_effective_capacity,
    parse_cgroup_cpu_max,
    parse_cgroup_memory_limit,
    parse_cgroup_v1_cpu_quota,
    parse_meminfo_value,
    reset_global_budget,
)


@pytest.fixture(autouse=True)
def _reset_budget():
    reset_global_budget()
    yield
    reset_global_budget()


def _capacity(cores: int = 4, memory: int = 8 * 1024**3, **kwargs) -> EffectiveCapacity:
    return EffectiveCapacity(
        cpu_affinity=cores, memory_available_bytes=memory, **kwargs
    )


# -- parsing ----------------------------------------------------------------


def test_parse_cgroup_v2_cpu_max():
    assert parse_cgroup_cpu_max("max 100000\n") is None
    assert parse_cgroup_cpu_max("200000 100000") == 2.0
    assert parse_cgroup_cpu_max("150000 100000") == 1.5
    with pytest.raises(SchedulingBudgetError):
        parse_cgroup_cpu_max("200000")
    with pytest.raises(SchedulingBudgetError):
        parse_cgroup_cpu_max("0 100000")
    with pytest.raises(SchedulingBudgetError):
        parse_cgroup_cpu_max("abc 100000")


def test_parse_cgroup_v1_cpu_quota():
    assert parse_cgroup_v1_cpu_quota("-1", "100000") is None
    assert parse_cgroup_v1_cpu_quota("50000", "100000") == 0.5
    with pytest.raises(SchedulingBudgetError):
        parse_cgroup_v1_cpu_quota("0", "100000")
    with pytest.raises(SchedulingBudgetError):
        parse_cgroup_v1_cpu_quota("nope", "100000")


def test_parse_meminfo_value_units():
    text = "MemTotal:       16384 kB\nMemAvailable:   4096 kB\nSwapTotal: 0 kB\n"
    assert parse_meminfo_value(text, "MemAvailable") == 4096 * 1024
    assert parse_meminfo_value(text, "MemTotal") == 16384 * 1024
    assert parse_meminfo_value(text, "Missing") is None
    assert parse_meminfo_value("MemAvailable: 1048576 B", "MemAvailable") == 1048576
    with pytest.raises(SchedulingBudgetError):
        parse_meminfo_value("MemAvailable: 1 GB", "MemAvailable")


def test_parse_cgroup_memory_limit():
    assert parse_cgroup_memory_limit("max\n") is None
    assert parse_cgroup_memory_limit("1073741824") == 1073741824
    # cgroup v1 "no limit" sentinel
    assert parse_cgroup_memory_limit("9223372036854771712") is None
    with pytest.raises(SchedulingBudgetError):
        parse_cgroup_memory_limit("0")


# -- detection --------------------------------------------------------------


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="ascii")


def test_detect_effective_capacity_reads_cgroup_v2(tmp_path):
    proc = tmp_path / "proc"
    cgroup = tmp_path / "cgroup"
    _write(proc / "meminfo", "MemAvailable: 2097152 kB\nMemTotal: 8388608 kB\n")
    _write(cgroup / "cpu.max", "300000 100000\n")
    _write(cgroup / "memory.max", "4294967296\n")

    capacity = detect_effective_capacity(
        procfs=proc, cgroup_root=cgroup, affinity=8, environ={}
    )

    assert capacity.cpu_affinity == 8
    assert capacity.cgroup_cpu_cores == 3.0
    assert capacity.effective_cores == 3.0
    assert capacity.cgroup_memory_limit_bytes == 4294967296
    assert capacity.effective_memory_bytes == 2 * 1024**3
    assert "cgroup_v2_cpu.max" in capacity.provenance
    assert "proc_meminfo_MemAvailable" in capacity.provenance


def test_detect_effective_capacity_falls_back_to_cgroup_v1_and_memtotal(tmp_path):
    proc = tmp_path / "proc"
    cgroup = tmp_path / "cgroup"
    _write(proc / "meminfo", "MemTotal: 1048576 kB\n")
    _write(cgroup / "cpu" / "cpu.cfs_quota_us", "250000\n")
    _write(cgroup / "cpu" / "cpu.cfs_period_us", "100000\n")
    _write(cgroup / "memory" / "memory.limit_in_bytes", "9223372036854771712\n")

    capacity = detect_effective_capacity(
        procfs=proc, cgroup_root=cgroup, affinity=4, environ={}
    )

    assert capacity.cgroup_cpu_cores == 2.5
    assert capacity.effective_cores == 2.5
    assert capacity.memory_available_bytes == 1024**3
    assert capacity.cgroup_memory_limit_bytes is None
    assert "cgroup_v1_cpu.cfs_quota_us" in capacity.provenance
    assert "proc_meminfo_MemTotal" in capacity.provenance


def test_detect_effective_capacity_never_crashes_on_missing_trees(tmp_path):
    capacity = detect_effective_capacity(
        procfs=tmp_path / "nope",
        cgroup_root=tmp_path / "nope2",
        affinity=2,
        environ={"CONSTRUCTION_PM_SCHEDULING_WORKERS": "5"},
    )
    assert capacity.cpu_affinity == 2
    assert capacity.memory_available_bytes == 0
    assert "memory_available_unknown" in capacity.provenance
    assert "env:CONSTRUCTION_PM_SCHEDULING_WORKERS" in capacity.provenance


# -- policy -----------------------------------------------------------------


def test_policy_is_limited_by_cpu():
    budget = WorkerBudgetPolicy().compute(_capacity(cores=4))
    assert budget.workers == 4
    assert budget.cpu_workers == 4
    assert budget.limiting_factor == "cpu"


def test_policy_is_limited_by_memory_reserve():
    policy = WorkerBudgetPolicy(per_job_memory_bytes=1024**3)
    budget = policy.compute(_capacity(cores=32, memory=2 * 1024**3))
    # 2 GiB - 25% reserve = 1.5 GiB, one 1 GiB job fits.
    assert budget.memory_workers == 1
    assert budget.workers == 1
    assert budget.limiting_factor == "memory"


def test_policy_honours_the_explicit_cap():
    budget = WorkerBudgetPolicy(max_workers=3).compute(_capacity(cores=16))
    assert budget.workers == 3
    assert budget.limiting_factor == "policy_cap"


def test_policy_never_returns_zero_and_reads_fractional_quota():
    budget = WorkerBudgetPolicy().compute(
        _capacity(cores=1, cgroup_cpu_cores=0.5, memory=1024)
    )
    assert budget.workers == 1
    assert budget.cpu_workers == 1


def test_policy_rejects_invalid_values():
    with pytest.raises(SchedulingBudgetError):
        WorkerBudgetPolicy(per_job_memory_bytes=0)
    with pytest.raises(SchedulingBudgetError):
        WorkerBudgetPolicy(memory_reserve_fraction=Decimal("1"))
    with pytest.raises(SchedulingBudgetError):
        WorkerBudgetPolicy(max_workers=0)
    with pytest.raises(SchedulingBudgetError):
        WorkerBudgetPolicy(minimum_workers=5, max_workers=2)
    with pytest.raises(SchedulingBudgetError):
        EffectiveCapacity(cpu_affinity=0, memory_available_bytes=1)
    with pytest.raises(SchedulingBudgetError):
        EffectiveCapacity(cpu_affinity=1, memory_available_bytes=1, cgroup_cpu_cores=0)


# -- global permits ---------------------------------------------------------


def test_global_budget_tracks_peak_and_never_exceeds_its_cap():
    budget = GlobalExecutionBudget(2)
    observed: list[int] = []
    lock = threading.Lock()
    barrier = threading.Barrier(6)

    def worker() -> None:
        barrier.wait()
        with budget.permit():
            with lock:
                observed.append(budget.active)
            threading.Event().wait(0.02)

    threads = [threading.Thread(target=worker) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(observed) == 6
    assert max(observed) <= 2
    assert budget.peak <= 2
    assert budget.active == 0
    assert budget.acquired_total == 6


def test_global_budget_rejects_release_without_a_permit():
    budget = GlobalExecutionBudget(1)
    with pytest.raises(SchedulingBudgetError):
        budget.release()
    with pytest.raises(SchedulingBudgetError):
        GlobalExecutionBudget(0)


def test_global_singleton_derives_once_and_refuses_a_conflict():
    budget = configure_global_budget(capacity=_capacity(cores=3))
    assert budget.workers == 3
    assert configure_global_budget() is budget
    with pytest.raises(SchedulingBudgetError):
        configure_global_budget(7)
    reset_global_budget()
    assert configure_global_budget(7).workers == 7


def test_global_singleton_reads_the_environment_override(monkeypatch):
    monkeypatch.setenv("CONSTRUCTION_PM_SCHEDULING_WORKERS", "9")
    assert configure_global_budget().workers == 9
    monkeypatch.setenv("CONSTRUCTION_PM_SCHEDULING_WORKERS", "nope")
    reset_global_budget()
    with pytest.raises(SchedulingBudgetError):
        configure_global_budget()


# -- adaptation -------------------------------------------------------------


def test_adaptive_controller_grows_toward_the_cap_and_shrinks_after_idle():
    controller = AdaptiveWorkerController(maximum=4, idle_observations_before_shrink=2)
    assert controller.target == 1
    assert controller.observe(pending=10, active=0) == 2
    assert controller.observe(pending=10, active=1) == 3
    assert controller.observe(pending=10, active=2) == 4
    assert controller.observe(pending=10, active=3) == 4
    assert controller.observe(pending=0, active=2) == 4
    assert controller.observe(pending=0, active=0) == 3
    assert controller.observe(pending=0, active=0) == 3  # minimum wait met, shrinks again
    assert controller.observe(pending=0, active=0) == 2


def test_adaptive_controller_is_bounded_and_rejects_invalid_input():
    controller = AdaptiveWorkerController(maximum=2, minimum=2)
    assert controller.observe(pending=0, active=0) == 2
    with pytest.raises(SchedulingBudgetError):
        AdaptiveWorkerController(maximum=0)
    with pytest.raises(SchedulingBudgetError):
        AdaptiveWorkerController(maximum=2, minimum=3)
    with pytest.raises(SchedulingBudgetError):
        AdaptiveWorkerController(maximum=2, step=0)
    with pytest.raises(SchedulingBudgetError):
        AdaptiveWorkerController(maximum=2, idle_observations_before_shrink=0)
    with pytest.raises(SchedulingBudgetError):
        controller.observe(pending=-1, active=0)
