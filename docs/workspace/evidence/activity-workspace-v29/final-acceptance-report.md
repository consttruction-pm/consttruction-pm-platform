# V29 — Final engineering report (Activities)

- Repository: `consttruction-pm/consttruction-pm-platform`
- Branch: `feat/2047-activity-workspace-v26`
- PR: #2048 (OPEN; continued, not duplicated)
- Tested code SHA: **`4779f7b4e`**
- Working tree: clean code tree; evidence and this report are the documentation commit
  that follows `4779f7b4e`.
- Environment: Qoder Desktop local full-stack preview. No Vercel, no deployment, no
  production data, no merge.

## What is newly real

1. **Activity Codes (R4)** — list/assign/replace/remove, tenant + project scope,
   PROJECT_READ/WRITE checks, unique code type per activity, record revision,
   persistence and reload. UI in Details > Codes.
2. **Notebook (R5)** — add/modify/delete topics with record revisions (409 on stale),
   server-side HTML allow-list sanitisation, ordering, persistence and reload.
   UI in Details > Notebook; comments in the rail stay separate.
3. **Steps (R6)** — create, edit name/weight/percent, move up/down, delete; stored
   completion record; authoritative sequence order; no recalculation of activity
   dates, float, critical path or activity percent. UI in Details > Steps.
4. **WPs & Docs (R7)** — link and unlink an activity through the existing document
   service and its revision guard; no parallel document model. UI in Details > WPs & Docs.
5. **Toolbars** — added Move, Standard and Top Layout; Project and Reports carry their
   reference names; Standard has New/Open/Save/Print/Undo/Redo/Cut/Copy/Paste/Delete/
   Find/Help; Top Layout switches the real top pane. Reports is no longer empty.
6. **Two-step Alt accelators** — waiting state, hint, Escape cancel, 2 s timeout, input
   and modal protection, menu preservation, 15 recorded bindings; Alt+F,N and Alt+P,A
   execute, unsupported commands say why.
7. **Shortcut corrections from PDF pp. 16–17** — F7 is Spell Check (disabled), Shift+F9
   is Level Resources (disabled), Shift+F12 is Disable Auto-Reorganization (disabled),
   Ctrl+R Replace and Alt+F1 Hint Help were added (disabled). No silent dead keys.
8. **Two-session conflict (409)** — real second browser session, stale save rejected,
   UI message, winner preserved, reload, fixture restored.
9. **Network / Trace Logic / Usage** — measured in real Chrome: 14 nodes, 15 edges,
   zoom persistence, Trace Logic rows, Usage profile and spreadsheet backed by a real
   stored assignment period created through the resource service.
10. **Visual matrix** — 36 real screenshots: 6 themes × 3 sizes × EN/FA; RTL asserted,
    no horizontal overflow, dark-skin row contrast ≥ 4.5:1.
11. **264-topic disposition** — every numbered PDF topic has a row with page, mapped
    surface, status and reason: 107 confirmed, 36 partial, 7 absent, 26 delegated,
    15 out-of-scope, 73 verify (open).

## Acceptance criteria status

| # | Criterion | Status |
|---:|---|---|
| 1 | Activities Help topics reviewed | Partial — 264 dispositioned, 73 still VERIFY |
| 2 | All 264 topics dispositioned | Yes (matrix) |
| 3 | R4–R7 complete or externally blocked | Complete for preview contract (production schema review pending) |
| 4 | Risks dispositioned | Existing service used; individual topics partly VERIFY |
| 5 | Toolbar gaps | Reference families represented; clipboard/Move/report actions honestly disabled |
| 6 | Two-step shortcuts | Implemented and unit-tested; unsupported ones disabled with reasons |
| 7 | Gantt Curtain and Attachments | **Not implemented** — see `remaining-items.md` |
| 8 | Network and Trace Logic tested | Yes (`activity-views-v29`) |
| 9 | Usage Profile tested | Yes, with a real stored period |
| 10 | Menus and commands reviewed | Audit updated; long-tail commands disabled with reasons |
| 11 | Dialogs and options tested | Partly; 73 VERIFY rows remain |
| 12 | RTL and LTR confirmed | Yes, all 36 cells |
| 13 | Six themes × three sizes | Yes, 36 cells |
| 14 | Real 409 | Yes, two independent sessions |
| 15 | Persistence of writes | Codes, notebook, steps, document link verified across reload |
| 16 | Regression | Web 1186 + 15, targeted Python 64 + 117; Shared Core untouched |
| 17 | CI on last SHA | **10/10 workflows pass** at `6a3bb76a4` (Web CI, ConstructionPM CI, Client Typecheck, PostgreSQL Integration and the remaining PR checks) |
| 18 | Docs and PR updated | Evidence set + PR body updated; not merged |

## Boundaries respected

- No change to the Shared Scheduling Core, CPM, leveling, calendars, float, EVM, cost
  calculations, authorization policy or tenant isolation.
- No browser-side reimplementation of scheduling values.
- No new production migration; preview tables are created by the preview repositories.
- No force push, no branch deletion, no history rewrite; other PRs' branches untouched.
- **No merge, no deploy, no Vercel work.**
