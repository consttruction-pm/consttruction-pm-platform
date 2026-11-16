"""Deterministic topological ordering shared by the date and time CPM paths.

Both scheduling paths previously maintained a sorted Python list of ready
activities and re-sorted it after every edge relaxation.  That is
``O(V log V + E log V)`` with a hidden ``O(V)`` list shift on every
``pop(0)``, and the two copies could drift apart.  This module is the single
authoritative ordering primitive for both paths.

Semantics preserved exactly
---------------------------
* The ready activity is always the lexicographically smallest available id
  (the previous implementation kept its ready list sorted and popped index 0).
* Duplicate relationships are counted individually, so a successor is released
  only after every incoming edge has been relaxed.
* Unknown activity references still raise ``KeyError`` because the predecessor
  count is indexed directly, exactly as before.
* A network that does not release every activity raises
  :class:`TopologicalCycleError`, which is a ``ValueError``.  The date path
  translates it to its own ``SchedulingCycleError`` so existing callers and
  diagnostics are unchanged.

The successor list is deliberately not sorted: the heap decides the order, so
sorting each adjacency list only adds work without changing a single emitted
position.
"""

from __future__ import annotations

import heapq
from typing import Iterable


class TopologicalCycleError(ValueError):
    """Raised when the activity network contains a cycle."""


def heap_topological_order(
    activity_ids: Iterable[str],
    edges: Iterable[tuple[str, str]],
) -> list[str]:
    """Return the deterministic topological order of ``activity_ids``.

    ``edges`` yields ``(predecessor_id, successor_id)`` pairs, one per
    relationship, in input order.
    """

    ids = sorted(activity_ids)
    predecessor_count = {activity_id: 0 for activity_id in ids}
    successors: dict[str, list[str]] = {activity_id: [] for activity_id in ids}
    for predecessor_id, successor_id in edges:
        predecessor_count[successor_id] += 1
        successors[predecessor_id].append(successor_id)

    ready = [
        activity_id
        for activity_id, count in predecessor_count.items()
        if count == 0
    ]
    heapq.heapify(ready)
    order: list[str] = []
    while ready:
        current = heapq.heappop(ready)
        order.append(current)
        for successor_id in successors[current]:
            predecessor_count[successor_id] -= 1
            if predecessor_count[successor_id] == 0:
                heapq.heappush(ready, successor_id)
    if len(order) != len(ids):
        raise TopologicalCycleError("activity network contains a cycle")
    return order
