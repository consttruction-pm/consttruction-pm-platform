"""Tests for the P0-A deterministic benchmark fixtures and canonical hashing."""

from decimal import Decimal

import pytest

from construction_pm.scheduling.benchmark_fixtures import (
    SHAPES,
    _edges,
    canonical_hash,
    canonical_json,
    date_network,
    date_schedule_payload,
    environment_fingerprint,
    leveling_case,
    leveling_payload,
    measure,
    run_date_schedule,
    run_leveling,
    run_time_schedule,
    time_network,
    time_schedule_payload,
)


@pytest.mark.parametrize("shape", SHAPES)
def test_date_fixture_is_reproducible(shape):
    first = date_network(200, shape, seed=7)
    second = date_network(200, shape, seed=7)
    assert first.activities == second.activities
    assert first.relationships == second.relationships
    assert first.counts == second.counts


@pytest.mark.parametrize("shape", SHAPES)
def test_time_fixture_is_reproducible(shape):
    first = time_network(100, shape, seed=7, float_days=2)
    second = time_network(100, shape, seed=7, float_days=2)
    assert first.activities == second.activities
    assert first.relationships == second.relationships
    assert first.project_finish == second.project_finish


def test_leveling_fixture_is_reproducible():
    first = leveling_case(100, seed=7)
    second = leveling_case(100, seed=7)
    assert first.activities == second.activities
    assert first.capacities == second.capacities


@pytest.mark.parametrize("shape", SHAPES)
def test_all_fixture_edges_point_forward_so_the_network_is_a_dag(shape):
    for size in (0, 1, 2, 3, 17, 200):
        for predecessor, successor, _ in _edges(size, shape, seed=3):
            assert 0 <= predecessor < successor < size


def test_seed_changes_the_dag_but_not_the_activity_set():
    first = date_network(200, "dag", seed=1)
    second = date_network(200, "dag", seed=2)
    assert first.activities == second.activities
    assert first.relationships != second.relationships


def test_date_fixture_counts_match_the_network_size():
    fixture = date_network(1000, "dag")
    assert fixture.counts["activities"] == 1000
    assert fixture.counts["relationships"] > 0


def test_canonical_hash_is_stable_and_order_insensitive_for_mappings():
    left = {"a": 1, "b": {"y": 2, "x": 1}}
    right = {"b": {"x": 1, "y": 2}, "a": 1}
    assert canonical_json(left) == canonical_json(right)
    assert canonical_hash(left) == canonical_hash(right)


def test_canonical_hash_changes_when_a_value_changes():
    assert canonical_hash({"float": 1}) != canonical_hash({"float": 2})


def test_date_schedule_payload_is_deterministic_for_one_network():
    fixture = date_network(60, "mixed", seed=5)
    first = canonical_hash(date_schedule_payload(run_date_schedule(fixture)))
    second = canonical_hash(date_schedule_payload(run_date_schedule(fixture)))
    assert first == second


def test_time_schedule_payload_is_deterministic_for_one_network():
    fixture = time_network(40, "mixed", seed=5, float_days=1)
    first = canonical_hash(time_schedule_payload(run_time_schedule(fixture)))
    second = canonical_hash(time_schedule_payload(run_time_schedule(fixture)))
    assert first == second


def test_leveling_case_actually_over_allocates_and_shifts():
    fixture = leveling_case(40)
    shifts = run_leveling(fixture)
    assert shifts, "the fixture must exercise real leveling work"
    assert all(shift.shift_working_days > 0 for shift in shifts)
    assert canonical_hash(leveling_payload(shifts)) == canonical_hash(
        leveling_payload(run_leveling(leveling_case(40)))
    )


def test_measure_reports_real_samples_and_process_peak_rss():
    timing = measure(lambda: sum(range(1000)), repeat=3, warmup=1)
    assert timing["wall"]["count"] == 3
    assert timing["cpu"]["count"] == 3
    assert timing["wall"]["min_ms"] >= 0
    assert timing["peak_rss_kb"] > 0
    assert "result" in timing


def test_environment_fingerprint_reports_capacity():
    fingerprint = environment_fingerprint("deadbeef")
    assert fingerprint["python"]
    assert fingerprint["cpu_count"] >= 1
    assert fingerprint["git_sha"] == "deadbeef"


def test_leveling_case_rejects_invalid_arguments():
    with pytest.raises(ValueError):
        leveling_case(10, resources=0)
    with pytest.raises(ValueError):
        date_network(10, "unknown-shape")


def test_time_amounts_remain_decimal_in_the_payload():
    fixture = time_network(20, "dag", float_days=1)
    result = run_time_schedule(fixture)
    payload = time_schedule_payload(result)
    sample = payload["floats"]["ACT-0000000"]
    assert isinstance(sample["total_float_value"], str)
    assert Decimal(sample["total_float_value"]) >= Decimal("0")
