"""P0-B differential tests for the deterministic heap topological ordering.

The reference implementation below is the exact algorithm that shipped before
P0-B: a sorted ready list with ``pop(0)`` and a re-sort after every relaxation.
Every test compares the new heap implementation against it, so a change in
tie-breaking, duplicate-edge counting or cycle behaviour fails immediately.
"""

import random

import pytest

from construction_pm.scheduling.forward_pass import (
    SchedulingCycleError,
    _topological_order,
)
from construction_pm.scheduling.relationships import Relationship, RelationshipType
from construction_pm.scheduling.topological_order import (
    TopologicalCycleError,
    heap_topological_order,
)


def legacy_topological_order(activity_ids, edges):
    ids = sorted(activity_ids)
    predecessor_count = {activity_id: 0 for activity_id in ids}
    successors = {activity_id: [] for activity_id in ids}
    for predecessor_id, successor_id in edges:
        predecessor_count[successor_id] += 1
        successors[predecessor_id].append(successor_id)
    ready = sorted(
        activity_id for activity_id, count in predecessor_count.items() if count == 0
    )
    order = []
    while ready:
        current = ready.pop(0)
        order.append(current)
        for successor_id in sorted(successors[current]):
            predecessor_count[successor_id] -= 1
            if predecessor_count[successor_id] == 0:
                ready.append(successor_id)
                ready.sort()
    if len(order) != len(ids):
        raise ValueError("activity network contains a cycle")
    return order


def random_dag(seed, size, extra_edges=0, duplicate_edges=False):
    rng = random.Random(seed)
    ids = [f"N{index:04d}" for index in range(size)]
    edges = []
    for index in range(1, size):
        edges.append((ids[rng.randrange(index)], ids[index]))
    for _ in range(extra_edges):
        left = rng.randrange(size - 1)
        right = rng.randrange(left + 1, size)
        edges.append((ids[left], ids[right]))
    if duplicate_edges and edges:
        picks = rng.sample(edges, k=max(1, len(edges) // 5))
        edges.extend(picks)
    return ids, edges


@pytest.mark.parametrize("seed", range(20))
def test_random_dags_match_legacy_order_exactly(seed):
    ids, edges = random_dag(seed, size=60, extra_edges=45, duplicate_edges=True)
    assert heap_topological_order(ids, edges) == legacy_topological_order(ids, edges)


@pytest.mark.parametrize("seed", range(5))
def test_larger_random_dags_match_legacy_order_exactly(seed):
    ids, edges = random_dag(seed + 1000, size=400, extra_edges=600, duplicate_edges=True)
    assert heap_topological_order(ids, edges) == legacy_topological_order(ids, edges)


def test_wide_network_is_sorted_lexicographically():
    ids = ["A10", "A2", "A1", "B0"]
    assert heap_topological_order(ids, []) == ["A1", "A10", "A2", "B0"]


def test_chain_follows_logic_even_when_ids_sort_against_it():
    edges = [("Z", "A"), ("A", "M")]
    assert heap_topological_order(["Z", "A", "M"], edges) == ["Z", "A", "M"]


def test_ready_ties_are_broken_lexicographically_like_the_legacy_list():
    ids, edges = random_dag(7, size=30, extra_edges=20)
    order = heap_topological_order(ids, edges)
    for position, activity_id in enumerate(order):
        available = {
            candidate
            for candidate in ids
            if candidate not in order[:position]
            and all(pred in order[:position] for pred, succ in edges if succ == candidate)
        }
        assert activity_id == min(available)


def test_disconnected_components_interleave_deterministically():
    ids = ["D", "A", "F", "B", "E", "C"]
    edges = [("D", "E"), ("A", "B")]
    assert heap_topological_order(ids, edges) == legacy_topological_order(ids, edges)
    assert heap_topological_order(ids, edges) == ["A", "B", "C", "D", "E", "F"]


def test_duplicate_edges_are_counted_and_do_not_create_a_false_cycle():
    edges = [("A", "C"), ("A", "C"), ("B", "C"), ("B", "C"), ("C", "D")]
    order = heap_topological_order(["A", "B", "C", "D"], edges)
    assert order == ["A", "B", "C", "D"]


def test_cycle_raises_the_shared_error_type():
    with pytest.raises(TopologicalCycleError):
        heap_topological_order(["A", "B"], [("A", "B"), ("B", "A")])


def test_self_loop_is_a_cycle():
    with pytest.raises(TopologicalCycleError):
        heap_topological_order(["A"], [("A", "A")])


def test_cycle_error_is_a_value_error_for_time_path_callers():
    assert issubclass(TopologicalCycleError, ValueError)


def test_date_path_still_raises_its_scheduling_cycle_error():
    relationships = [
        Relationship("A", "B", RelationshipType.FS),
        Relationship("B", "A", RelationshipType.FS),
    ]
    with pytest.raises(SchedulingCycleError):
        _topological_order(["A", "B"], relationships)


def test_date_path_order_matches_legacy_for_all_relationship_types():
    relationships = [
        Relationship("C", "A", RelationshipType.SS, lag=-1),
        Relationship("A", "D", RelationshipType.FF, lag=2),
        Relationship("B", "D", RelationshipType.SF, lag=1),
        Relationship("B", "C", RelationshipType.FS, lag=0),
    ]
    edges = [(rel.predecessor_id, rel.successor_id) for rel in relationships]
    assert _topological_order(["A", "B", "C", "D"], relationships) == legacy_topological_order(
        ["A", "B", "C", "D"], edges
    )


def test_unknown_activity_reference_still_raises_key_error():
    with pytest.raises(KeyError):
        heap_topological_order(["A"], [("A", "MISSING")])
    with pytest.raises(KeyError):
        heap_topological_order(["A"], [("MISSING", "A")])


def test_empty_network_is_empty():
    assert heap_topological_order([], []) == []
