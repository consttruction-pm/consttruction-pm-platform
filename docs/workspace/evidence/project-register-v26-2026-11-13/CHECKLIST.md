# PRJ-001 project register acceptance — 2026-11-13

Tested code SHA: `02369cbe`
Contract: `cubi-prj-001-project-register.v1`

PASS — the Projects window renders the register
PASS — the register reports every project in the session list
PASS — table rows are exactly the API projects
PASS — every listed project belongs to the session tenant
PASS — each row shows its stored Business Domain
PASS — the tree groups the persisted domains
PASS — the tree contains every project once
PASS — the open project is the only aria-current row
PASS — the open project is selected before any click
PASS — only the matching project row remains
PASS — the count reports the filtered result
PASS — the tree shows only the matching domain group
PASS — an unmatched search shows a no-match state, not fabricated rows
PASS — Clear filters restores every authorized row
PASS — the domain filter keeps only that domain
PASS — Start date sorts the persisted rows ascending
PASS — the tree selection marks the chosen project, not the open one
PASS — the selection card shows the persisted record
PASS — selection does not change the open project
PASS — Open project switches the workspace and marks the row current
PASS — Enter on a focused row selects that project
PASS — the domain group collapses without losing its rows
PASS — the group expands again
PASS — a project created through the API starts in its chosen domain
PASS — the new record is in the authorized list with its domain
PASS — the reloaded tree contains the new Construction group
PASS — a revision-guarded PATCH moves the project to Energy
PASS — a stale configuration revision is rejected without overwriting
PASS — an unknown classification is rejected
PASS — the stored record still holds the last accepted domain
PASS — the Energy group now contains the project and Construction is gone
PASS — the Persian workspace is right-to-left
PASS — the tree and rows use Persian domain labels
PASS — search, filter and selection surfaces are present in Persian
PASS — the register does not overflow the 1280 viewport
PASS — the Viewer sees exactly the session-authorized records
PASS — the Viewer gets the same Business Domain hierarchy
PASS — a Viewer PATCH is denied by the server