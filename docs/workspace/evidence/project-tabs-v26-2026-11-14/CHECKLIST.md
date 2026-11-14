# PRJ-003 project tab lifecycle acceptance — 2026-11-14

Tested code SHA: `f1ecba6eeea4310dc05e231b21a83d6e1d6073c8`
Contract: `cubi-prj-003-project-tabs.v1`

PASS — one tab exists for the opened project
PASS — that tab is active and named from the session list
PASS — the last project tab has no close control
PASS — the title bar names the same project
PASS — the strip now holds both projects
PASS — the opened project is the active tab and the title
PASS — both tabs are closable
PASS — the switch went through the server open endpoint
PASS — the first project lost its Projects window
PASS — a project opened for the first time gets the default window set
PASS — switching back restores the first project's window set
PASS — a cancelled switch keeps the current project and its editor
PASS — accepting the prompt switches projects
PASS — the discarded editor is not left on the new project
PASS — closing an inactive tab keeps the open project
PASS — closing a tab issues no project open transition
PASS — closing the active tab opens its neighbour
PASS — the neighbour was re-authorized through the server
PASS — the same two tabs return after a full reload
PASS — the active project is restored
PASS — an external save advances the project revision
PASS — the register shows the record saved by the other writer
PASS — the selection card shows the advanced configuration revision
PASS — a stale revision cannot overwrite the newer record
PASS — the Persian workspace is right-to-left
PASS — both project tabs remain and one is active
PASS — the tab strip is labelled in Persian
PASS — the strip does not overflow the 1280 viewport
PASS — every open tab belongs to the Viewer's own list
PASS — opening a project the session does not list is denied

Scenarios: 9; checks: 30; passed: 30; failed: 0
Exceptions: 0; console errors: 0; API 5xx: 0
