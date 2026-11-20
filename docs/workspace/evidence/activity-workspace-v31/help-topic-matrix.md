# V31 — Help topic disposition delta

Source: Primavera P6 Professional Help **G57535-02, October 2026**, physical PDF.
Basis: V30 `pdf-topic-disposition.md` (264 numbered topics). Only rows whose behaviour changed in this increment are rewritten here; all other V30 decisions carry forward.

## Changed rows

| # | Chapter | Topic (PDF) | Printed page | CUBI equivalent | V30 | V31 | Test / evidence |
|---:|---|---|---:|---|---|---|---|
| 24 | 1. Chapter 5 | Copy and paste activities in the Activity Table | 14 | `workspace-activity-copy.ts`, `main.ts`, `workspace-activity-clipboard.ts` | confirmed | **confirmed (expanded)** | `activity-v31-renumber-copy.mjs` (Copy Options: codes + expenses + relationship, Steps cleared), `workspace-activity-copy.test.ts` |
| 28 | 1. Chapter 5 | Renumber activity IDs in the Activity Table | 16 | `workspace-activity-renumber.ts`, `main.ts`, `P6ActivityMasterAPI.renumber`, `activity_master_repository.py` | verify | **confirmed** | `activity-v31-renumber-copy.mjs` (preview, apply, relationship follows), `test_activity_master_repository.py`, `test_p6_activity_master_http_routes.py` |
| 169 | 2. Chapter 7 | Hide all curtain attachments in the Gantt Chart | 18 | `workspace-view.ts`, `main.ts` (`onGanttCurtainsVisibilityChange`) | partial | **confirmed** | `activity-v31-renumber-copy.mjs` (hide all, reload), `gantt-attachments-v30.mjs` |
| 171 | 2. Chapter 7 | Display all curtain attachments in the Gantt Chart | 19 | `workspace-view.ts`, `main.ts` (`onGanttCurtainsVisibilityChange`) | partial | **confirmed** | `activity-v31-renumber-copy.mjs` (show all, reload), `gantt-attachments-v30.mjs` |

## Dialog/section topics outside the 264-topic chapter list

| Help topic | Implementation | Evidence |
|---|---|---|
| Copy Activity Options dialog box (Chapter 14 reference, p. 39) | `mountActivityCopyOptionsDialog`; every checkbox maps to a persisted replay path | `activity-v31-renumber-copy.mjs`, `workspace-activity-copy.test.ts` |
| Renumber Activity IDs dialog box — copied activities (p. 125) | Increment / Auto-Number / Replace Beginning Characters with collision stepping and Duplicates resolution in the preview table | `workspace-activity-renumber.test.ts`, `activity-v31-renumber-copy.mjs` |
| Renumber Activity IDs dialog box — current project (p. 125) | Same dialog posts one renumber request; baselines checkbox controls baseline participation | `test_activity_master_repository.py`, `test_p6_activity_master_http_routes.py` |
| Quickly enter the same text in multiple table rows (Chapter 2, p. 9) | `workspace-activity-fill.ts`: active column, type validation, preview, revision-checked PATCH | `workspace-activity-fill.test.ts`, `activity-v31-renumber-copy.mjs` |

## Updated totals

| Status | V30 | V31 |
|---|---:|---:|
| confirmed | 116 | **119** |
| partial | 34 | **32** |
| absent | 0 | 0 |
| delegated | 26 | 26 |
| out-of-scope | 15 | 15 |
| verify | 73 | **72** |
| total | 264 | 264 |

No other row was relabelled. `remaining-items.md` records the open set.
