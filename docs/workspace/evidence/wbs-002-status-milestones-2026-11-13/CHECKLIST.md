# WBS-002 status, percent-complete technique and weighted milestones acceptance — 2026-11-13

Tested code SHA: `154825b0`
Contract: `cubi-wbs-002-status-milestones.v1`

PASS — the General tab shows the persisted status and technique instead of placeholders
PASS — the General tab exposes the status and technique editor
PASS — PATCH persists status=active and technique=milestones with an advanced revision
PASS — the General tab reflects the saved status and technique
PASS — a node without milestones shows an empty authoritative list, not fabricated rows
PASS — the editor previews 9 of 12 weight complete as 75.00%
PASS — PUT persists four weighted milestones and returns 75%
PASS — the WBS record exposes the same weighted percent complete
PASS — the reloaded milestone tab shows the persisted weights and 75.00%
PASS — the fourth milestone completion can be toggled
PASS — the editor previews 10 of 12 weight complete as 83.33%
PASS — saving advances the WBS revision and persists 83.33%
PASS — a PUT with an old expected revision returns 409 REVISION_CONFLICT
PASS — the rejected write leaves the persisted milestones untouched
PASS — a duplicate milestone ID is explained in the editor and no milestone write is sent
PASS — a zero weight is blocked by the field constraints and no milestone write is sent
PASS — the Persian WBS status and milestones are right-to-left
PASS — the Persian details show the localized status labels
PASS — the persisted milestones and roll-up are visible in Persian
PASS — the page does not overflow horizontally
PASS — the reloaded General tab still shows Active and WBS Milestones
PASS — the reloaded milestone editor lists all four persisted milestones at 83.33%

Scenarios: 9; checks: 22; passed: 22; failed: 0
Exceptions: 0; console errors: 0; API 5xx: 0
