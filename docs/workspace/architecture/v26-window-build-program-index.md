# CUBI Version 26 Window Build Program

- Parent issue: [#1722 - Complete CUBI window build catalog and Version 26 requirements traceability](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1722)
- Baseline source commit: 49201ddfbec83550e7147ce2fa3cc961e39eef55

## Read these documents in order

1. [Official Version 26 source register](../reference/v26-source-register.md)  
   Identifies the official Help, User, Administration, Reporting and Visualizer documents, their release IDs, applicability and safe use rules.

2. [Complete window and component catalog](v26-complete-window-component-catalog.md)  
   Defines the target global shell, all menu/toolbar/context-menu families, and the required contents and behavior of every major window. Activities is the first reference window and has its own detailed build contract.

3. [Window traceability and acceptance matrix](v26-window-traceability-and-acceptance-matrix.md)  
   Converts the catalog into requirement IDs, tests, evidence, status vocabulary, high-volume schedule checks and phased stop/go gates.

## Governing implementation priority

1. Finish the single global workspace shell and shared command/window architecture.
2. Complete Activities end-to-end, including WBS hierarchy, synchronized Gantt, Activity Details, Network, usage/Trace Logic views and context menus.
3. Complete Projects and WBS.
4. Complete Resource Assignments, Resources, Roles and Calendars.
5. Complete Schedule, Progress, Baselines, EVM and Tracking.
6. Complete Documents, Expenses/Cost Accounts/Budget, Issues, Thresholds and Risks.
7. Complete Reports, Administration, import/export, backup/recovery and remaining tools.
8. Complete the approved CUBI-specific additions and cross-platform surfaces.

This order does not authorize a hollow shell for later windows. Each window must be completed to its own visual and functional acceptance gate before it is declared complete.

## Relationship to existing architecture/audits

The catalog supplements, rather than silently replaces:
- workspace-visual-shell-master-audit.md
- workspace-information-architecture.md
- workspace-window-inventory.md
- workspace-visual-reference-audit.md
- oracle-p6-window-reference.md
- oracle-p6-menu-reference.md
- WEB_SURFACE_TRACEABILITY_MATRIX.md
- CUBI_V1_ACCEPTANCE_MATRIX.md

Existing audits use different branches and dates. Before any implementation is declared complete, refresh the current-state evidence on the exact target branch and run the real workspace in a browser.

## Completion policy

- A window title, route, menu item, icon, screenshot or static preview does not equal completion.
- Every displayed command must work or be truthfully disabled with a reason.
- All data operations must use the authoritative application/service/shared-core path.
- All views and filters are display projections; they must not silently reduce the authoritative schedule population.
- The final acceptance record must include exact commit SHA, tests, real browser evidence, unresolved gaps and reviewer sign-off.
