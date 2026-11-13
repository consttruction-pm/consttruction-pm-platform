# WBS-001 hierarchical WBS table and chart acceptance — 2026-11-13

Tested code SHA: `31c79ca6`
Contract: `cubi-wbs-001-table-chart.v1`

PASS — the WBS window renders a table grid
PASS — the table exposes code, name, activities, sequence and revision columns
PASS — rows follow the persisted hierarchy order and depth
PASS — activity counts match the persisted assignments
PASS — the table shows exactly the nodes the WBS API returns
PASS — the chart view is rendered
PASS — chart cards keep the table order and depth
PASS — the chart toggle is the pressed view
PASS — the table marks the clicked record and reads its details
PASS — the chart highlights the same record after the view switch
PASS — a chart selection survives the return to the table
PASS — the WBS API persists the new child
PASS — the reloaded table shows the persisted child directly under its parent at depth three
PASS — the chart shows the same persisted child at the same position
PASS — every rendered child references a parent present in the same snapshot
PASS — the Persian WBS table is right-to-left
PASS — the table headers are localized
PASS — the page does not overflow horizontally; the table scrolls inside its own wrapper
PASS — each chart node is a focusable button identified by its WBS ID

Scenarios: 7; checks: 19; passed: 19; failed: 0
Exceptions: 0; console errors: 0; API 5xx: 0
