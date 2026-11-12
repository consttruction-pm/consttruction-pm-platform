# CUBI Canonical Visual Workspace — Migration Ledger

**Status:** Controlled migration; not accepted for merge or production.
**Last audited:** 2026-11-05
**Repository:** `consttruction-pm/consttruction-pm-platform`
**Continuation branch:** `codex/jalal/cubi-shell-v26-20261104`
**Approved common base:** `7c3f4821` (latest `origin/main`)
**Last independently evidenced continuation head:** the integration of `a170c87a` (PR #1716) into `301ddb91` on this branch; browser evidence was captured on that merged tree. Do not reset or force-push either ref.
**Recovery point:** the approved base plus the reviewed continuation branch; do not reset or force-push either ref.

This ledger is the durable, file-versioned record for the one-workspace migration. Update it in the same pull request after each accepted slice. A source window is not considered migrated merely because a tab, menu item, dialog, or placeholder renders.

## 1. Product rule — one authenticated workspace

CUBI has exactly one authenticated product workspace. It must be the existing project-backed `cp-app-shell`, retaining the approved visual composition and all required visual windows inside that shell.

The public Home page and ordinary public website pages remain outside the authenticated workspace. The intended journey is:

`Public Home / pages → Login → one authenticated Visual Workspace → Sign out → Public Home`

No separate dashboard, static preview application, visual-demo route, or alternate authenticated shell may remain exposed as a second product environment.

**Do not remove the current visual-demo boot path yet.** The authenticated shell currently has fewer windows than the approved visual catalogue. First migrate and verify the approved window inventory into the authenticated shell, using project-scoped read/write services or a truthful unavailable state. Only after acceptance may the separate demo bootstrap be retired.

## 1.1 CUBI – Complete Visual and Functional Parity Standard

This catalogue and every window comparison in it follow the binding parity
standard:

1. **Authority.** The Version 26 official HTML Help
   (https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm) and the
   supplied 815-page Version 26 PDF govern control order, options, terminology
   and acceptance. Older screenshots inform appearance only.
2. **No fabrication.** A window capability without an authoritative service is
   presented as unavailable with a reason. No invented records, dates, progress
   or enabled-looking dead controls.
3. **No premature completion claim.** “The shell is complete” and “matches
   version 26” are prohibited until the compliance matrix is complete and the 18
   mandatory browser scenarios carry real screenshots from the built preview.
4. **Exact status vocabulary.** **مطابق و تأییدشده**،
   **پیاده‌سازی‌شده ولی آزمون‌نشده**، **ناقص**، **غایب**،
   **محدودیت مستند و مشخص**.
5. **Change control.** No destructive change, no branch deletion, no force-push,
   no merge to `main` or Production before tests and visual review; Preview
   first.
6. **Scope.** Activities and its direct dependencies only; the API, scheduling
   core, data model, other windows, main shell and entry route stay unchanged.
7. **Mirrors.** Also recorded in
   `docs/governance/PROJECT_CONTINUITY_PROTOCOL.md` and
   `docs/workspace/reference/oracle-p6-reference-index.md`.

## 2. Protected invariants

The following are change-control constraints for every migration slice:

- Preserve the current approved workspace composition, pane dimensions, toolbar hierarchy, colors, icons, and window behaviour unless a specifically reviewed task requires a change.
- Do not change Gantt time-scale units, schedule calculations, calculated dates, project records, or sample-to-project data boundaries.
- Never copy fixture activity/resource/cost/date/float/status values from `workspace-visual-demo.ts` into an authorized project.
- Preserve Activities, Gantt, WBS, Details, Form Builder, assistant, comments, navigation, menus, tabs, dialogs, layout persistence, and public pages.
- Use existing project-scoped API/read models, permission checks, revision guards and shared core contracts. Do not create parallel state stores or service adapters where an existing contract is available.
- When a required service does not exist, keep the visual affordance only if it can accurately communicate an unavailable/disabled state; do not fabricate records or show false success.
- Make one bounded, reviewable change at a time. No broad shell rewrite, direct main edits, force-push, history rewrite, unreviewed rebase, or deployment before acceptance.

## 3. Source-of-truth window inventory

The approved visual-demo catalogue in `apps/web/src/workspace-visual-demo.ts` contains 48 window IDs. The authenticated `WINDOW_TITLES` / `WorkspaceMenuKey` catalogue in `apps/web/src/workspace-desktop-shell.ts` contains 18 IDs. This is the verified starting inventory, not proof that all 48 are already migrated.

### 3.1 Canonical 48-window catalogue and migration treatment

| # | Approved visual window ID | Authenticated target / treatment | Current migration status |
|---:|---|---|---|
| 1 | `projects` | `project` | Existing target; partial/read-backed |
| 2 | `wbs` | `wbs` | Existing target; wired with documented gaps |
| 3 | `activities` | `schedule` | Existing target; core schedule surface |
| 4 | `assignments` | `assignments` | Existing target; wired with documented gaps |
| 5 | `resources` | `resources` | Existing target; read-backed/partial |
| 6 | `roles` | `roles` | Existing target; wired/partial |
| 7 | `calendars` | `calendars` | Existing target; wired/partial |
| 8 | `reports` | `reports` | Existing placeholder; reporting API gap |
| 9 | `tracking` | `tracking` | Existing static/preview surface; tracking API gap |
| 10 | `documents` | `documents` | Existing read-only target; document write gap |
| 11 | `expenses` | `expenses` | Existing target; wired/partial |
| 12 | `thresholds` | `thresholds` | Existing shell; core model gap |
| 13 | `issues` | `issues` | Existing shell; P6-style register gap |
| 14 | `risks` | `risks` | Existing shell; risk model gap |
| 15 | `administration` | `settings` plus existing Administration menu surfaces | Verify every admin operation and permission separately |
| 16 | `network` | Schedule subview | Migrated as a top-layout projection of persisted activities/relationships; selectable, keyboard-operable and persisted per tenant/project |
| 17 | `trace` | Schedule subview | Not a separate application/window; requires trace/relationship presentation |
| 18 | `timeline` | Schedule subview | Not a separate application/window; preserve Gantt time-scale behaviour |
| 19 | `activity-profile` | Schedule subview | Requires authoritative time-phased activity data |
| 20 | `resource-profile` | Resources/Assignments subview | Requires authoritative time-phased resource data |
| 21 | `activity-sheet` | Schedule subview | Requires authoritative time-phased activity data |
| 22 | `resource-sheet` | Resources/Assignments subview | Requires authoritative time-phased resource data |
| 23 | `cost-control` | `cost` | Existing target; baseline/cash-flow gaps remain |
| 24 | `progress-control` | `progress` | Existing target; progress-history gaps remain |
| 25 | `procurement` | Existing procurement in-shell surface/rail where backed | Promote only after verifying actual read/write contracts |
| 26 | `changes-claims` | Existing Changes & Claims in-shell surface/rail | Verify contracts, permissions and project scoping |
| 27 | `form-builder` | Existing Form Builder mounted inside `cp-app-shell` | Preserve organization and project libraries and complete workflow |
| 28 | `organization` | Existing Organization menu and organization-scoped surfaces | No second shell; verify tenant scope and access |
| 29 | `engineering-analysis` | In-shell engineering tool/window | Not yet mapped to a verified live service |
| 30 | `project-watchdog` | In-shell engineering tool/window | Not yet mapped to a verified live service |
| 31 | `scenario-lab` | In-shell engineering tool/window | Not yet mapped to a verified live service |
| 32 | `optimization-studio` | In-shell engineering tool/window | Not yet mapped to a verified live service |
| 33 | `project-quality` | In-shell engineering tool/window | Not yet mapped to a verified live service |
| 34 | `construction-productivity` | In-shell engineering tool/window | Not yet mapped to a verified live service |
| 35 | `data-reconciliation` | In-shell engineering tool/window | Not yet mapped to a verified live service |
| 36 | `portfolio-capacity` | In-shell engineering tool/window | Requires organization/portfolio capacity model |
| 37 | `automation-center` | In-shell engineering tool/window | Requires governed automation contracts and permissions |
| 38 | `engineering-standards` | In-shell engineering tool/window | Requires a versioned standards/knowledge source |
| 39 | `project-templates` | In-shell project/template tool | Requires authorized template read/write contracts |
| 40 | `decision-register` | In-shell project-control tool | Requires persisted decision register |
| 41 | `deadline-monitor` | In-shell project-control tool | Requires authoritative deadlines/SLA model |
| 42 | `data-quality` | In-shell project-control tool | Requires validated project data-quality service |
| 43 | `recovery-center` | In-shell project-control tool | Requires authorized history/restore service |
| 44 | `command-dictionaries` | In-shell help/reference tool | Requires governed command dictionary source |
| 45 | `smart-guide` | Existing Smart Guide/control surface | Verify project-context binding and every action |
| 46 | `assistant` | Existing authenticated assistant/avatar panel | Keep in-shell; no geometry-changing separate app |
| 47 | `search` | Existing in-shell find/search tooling | Global search not proven; verify scope and results |
| 48 | `comments` | Existing workspace comments/notebook panel | Preserve in-shell; verify persistence and non-overlap |

### 3.2 Authenticated window catalogue (18)

The current authenticated shell keys are:

`project, wbs, schedule, progress, resources, assignments, roles, calendars, cost, expenses, documents, reports, tracking, issues, risks, thresholds, control, settings`

These are the target shell surfaces. Do not create new top-level application shells for the additional approved visual IDs; add them as windows, subviews, panels, tabs, menu items or dialogs inside this shell.

## 4. Verified service/read-model readiness baseline

The following reflects the code traceability matrix inspected on 2026-11-05. Re-check it at the exact commit before changing a service or declaring a page operational.

| Authenticated window | Evidence-based status | Remaining service/product limitation |
|---|---|---|
| Project | Partial / wired-read | No close/archive/status operation; no EPS hierarchy |
| WBS | Wired | No reorder/move, budget/milestone/document/EVM/planning-resource models or chart export |
| Schedule | Implemented / wired | Numeric parity against a licensed V26 reference run not proven; long-tail dialogs need audit |
| Progress | Wired / partial | No persisted update log, out-of-sequence review, dashboard charts or period actual cost/units |
| Resources | Wired-read / partial | No complete labor/nonlabor/material/role resource dictionary register |
| Assignments | Wired / partial | No edit/delete, period/spread editor or usage profile; resource IDs remain free text |
| Roles | Wired / partial | No delete route, rates/limits or role-assignment tabs |
| Calendars | Wired / partial | No blank-calendar snapshot creation or exception deletion; workweek update uses copy contract |
| Cost | Wired / partial | Baseline capture from the calculated schedule (GAP-BAS-03 resolved 2026-11-12); no cash flow, forecast, change/claim or variance-to-baseline view; EVM result is not stored |
| Expenses | Wired / partial | No update/delete; no authoritative vendor/accrual/status or cost-account reference fields |
| Documents | Wired / partial | Metadata create/edit/status/history over the versioned document API; binary upload/download remains GAP-DOC-02 |
| Reports | Wired / partial | Versioned report register, stored runs and history; no scheduling, parameters, grouping, charts, print or CSV/PDF/XLSX export |
| Tracking | SHELL / preview | No tracking read model, charts, profiles or project set (GAP-TRK-01) |
| Issues | Wired / partial | Versioned issue register with filters, create/edit/status graph, comments and history; no attachment upload or user-directory assignment |
| Risks | GAP-CORE | No authoritative risk register/read-write model (GAP-RSK-01) |
| Thresholds | GAP-CORE | No authoritative threshold register/monitoring model (GAP-THR-01) |
| Control | Wired-read / partial | Control-room summary is read-backed; browser-side analysis is not implemented; Changes/Claims remains a separate in-shell surface |
| Settings | Wired / partial | Only activity-grid layout persistence is exposed; full translation-pack coverage is unproven (GAP-I18N-01) |

### Required handling of gaps

- Keep every gap ID visible in the project execution record.
- Build missing capabilities in their owning shared/core/API layer before connecting their controls.
- For missing services, render a localized, explicit unavailable state instead of fixture records or simulated success.
- Preserve read-only records exactly as returned by authorized services.
- Permission denial, stale revision, missing project context, empty dataset and service failure must remain distinct states.

## 5. Current continuation slice — resize/layout

The continuation branch implements a bounded resize slice in the authenticated workspace:

- Details/top-pane horizontal splitter.
- Activities table/Gantt vertical splitter.
- Activity column drag handles.
- Bounded values and RTL/LTR-aware pointer maths.
- Keyboard adjustment and pointer cancellation handling.
- Local persistence for pane ratios scoped by tenant/project/window.
- Column-width persistence through the existing revision-checked layout callback/API.
- Gantt time-scale model and calculated date values intentionally unchanged.

Relevant files on the continuation branch:
- `apps/web/src/workspace-resizing.ts`
- `apps/web/src/workspace-resizing.test.ts`
- `apps/web/src/workspace-view.ts`
- `apps/web/src/workspace-desktop-shell.ts`
- `apps/web/styles.css`
- `apps/web/public/styles.css`
- `apps/web/e2e/preview-e2e.mjs`
- `.github/workflows/web.yml`

**Acceptance status:** implementation and focused unit coverage exist; full browser acceptance, refresh persistence, cross-window/table coverage, and screenshots at 1280×720, 1366×768 and 1920×1080 are not yet evidenced. Do not mark this slice complete until those proofs exist.

## 6. Ordered migration plan and gates

Each phase is a separate reviewable slice. A failed gate blocks the next phase.

### Gate 0 — branch and runtime stability
- Refresh and record exact `main`, branch and PR head SHAs.
- Reconcile the four main-only commits individually; they include accidental test-file writes and subsequent forward reverts. Do not blindly rebase or merge them.
- Complete exact-head Web CI, assistant-avatar E2E, Form Builder E2E and preview journey.
- Confirm sign-out actually revokes the session; navigation to Home alone is not logout.
- Capture a rollback point before any source edit.

### Gate 1 — shell composition inventory
- Verify title/brand, menu bar, global icon toolbar, window tabs, left navigation, one contextual command bar, right Add (+) rail, Details pane, comment bar and status strip.
- Compare all 48 approved catalogue entries with their authenticated destinations.
- Consolidate duplicate toolbar rows only after command ownership and page-context rules are mapped.
- Keep all existing menu items and commands unless their replacement is tested and equivalent.

### Gate 2 — existing live windows
Migrate the highest-value already-backed windows first:
1. Project and WBS.
2. Activities/Schedule, Gantt, Network, Trace and Timeline.
3. Resources, Assignments, Activity/Resource Profiles and Sheets only when authoritative time-phased data is available.
4. Progress, Cost, Expenses and Baselines.
5. Documents, Reports, Tracking, Issues, Risks and Thresholds according to their owning service gaps.
6. Organization, Administration, Procurement and Changes/Claims after tenant/project permissions are proven.

### Gate 3 — in-shell engineering tools
For every tool in IDs 29–44, record:
- owning service or versioned knowledge source;
- read/write contract and tenant/project scope;
- permission and approval requirements;
- window/menu/command/dialog/Details design;
- empty, unavailable, loading, error and success states;
- tests and screenshots.
Do not expose a fake operational tool merely to match a visual-demo label.

### Gate 4 — canonical route consolidation
Only after all approved visual windows have an authenticated destination (operational or truthfully unavailable), remove the separate visual-demo boot path. Prove:
- public pages remain unchanged;
- login opens the canonical authenticated shell;
- direct deep links and refresh preserve project/window context;
- session recovery returns to the same shell;
- sign-out revokes session and returns Home;
- no separate demo/dashboard/app shell is reachable.

### Gate 5 — final acceptance
Required at exact head:
- Python 3.11 / 3.12 / 3.13.
- Web, desktop, mobile and client-sync Typechecks.
- Web and full CI, PostgreSQL integration and Preview runtime.
- Browser E2E for login, project selection, each migrated window group, assistant, Form Builder, language switch, refresh, deep link and sign-out.
- Pointer/keyboard resize and refresh-persistence tests.
- Screenshots at 1280×720, 1366×768 and 1920×1080; RTL/LTR where applicable.
- Before/after visual comparison and explicit confirmation that Gantt time-scale and scheduling facts are unchanged.
- Review of exact-head code diff and rollback point.

## 7. Required per-slice change record

Append one record for every slice. Do not overwrite prior records.

| Field | Required evidence |
|---|---|
| Slice ID / date | Stable identifier and date |
| Base SHA / head SHA | Exact commits |
| Window IDs | Exact catalogue IDs covered |
| Files changed | Complete path list |
| Data contract | API/read model/write route or explicit unavailable reason |
| Security | Tenant/project scope, permission and revision checks |
| Visual evidence | Screenshot paths and viewport sizes |
| Tests | Exact commands/workflow run IDs and results |
| Gantt regression | Confirmation that time-scale and calculated facts are unchanged |
| Remaining gaps | IDs and concrete next dependency |
| Rollback | Last known good SHA and reversal procedure |
| Acceptance | Pass/fail with reviewer evidence |

## 8. Audit history

### 2026-11-05 — baseline audit (documentation only)
- Approved common base: `3214e3c8cd204d772ae641dd489a97c781c87e59`.
- Continuation branch compared with approved base: 25 commits ahead, 0 behind at the audit snapshot.
- Continuation branch compared with current `main`: 25 commits ahead, 4 behind; merge-base remains the approved base.
- `apps/web/src/main.ts` blob SHA was identical on `main` and the continuation branch at the audit snapshot; the separate visual-demo bootstrap remained active.
- Visual catalogue contains 48 entries; authenticated shell contains 18 entries.
- The last inspected Web CI run was `41926457725`: Typecheck, unit tests, build, production-shaped artifact validation and Preview Runtime Smoke Test passed. Browser E2E for assistant avatars was still `in_progress`; Form Builder E2E was `pending`. No screenshots or complete browser acceptance were established.
- No application source, route, CSS, project data, Gantt behaviour, main ref, merge or deployment was changed by this audit.

### 2026-11-05 — first protected implementation slice
- Resize implementation is present on the continuation branch as described in Section 5.
- Focused resize unit tests exist; full browser acceptance remains pending.
- Recovery point: `a4586e77d0be15594dbeb77c091136418aa8719e` (last specifically evidenced continuation head at audit time).
- Do not interpret this entry as final acceptance or permission to merge.

---
**Current decision:** keep the continuation PR unmerged and undeployed. Preserve the 48-window visual inventory, authenticated project data, existing shell and Gantt. Continue only with one tested, reversible migration slice at a time.


## 11. Continuation evidence — resizable workspace and reference viewports (2026-11-05)

**Verified head:** 5c2a4bc8579d27a90295e013c89c5568c525f202  
**PR:** #1716 — remains open; not merged or deployed.  
**Preview evidence:** GitHub Actions run 41942211196; artifact cubi-workspace-visual-evidence (ID 13375889253).

### Accepted in this slice

- The existing authenticated workspace now has a bounded horizontal Details splitter and a bounded vertical table/Gantt splitter. Both respond to pointer drag and keyboard input; double-click restores their default ratios.
- Split preferences are stored by tenant, project, active window and split kind, and survive a full browser reload.
- Activity column widths resize with pointer and keyboard input, commit through the existing revision-checked layout API, and survive a full reload. The test compares the restored width to the post-drag API-committed value, not the earlier pre-drag value.
- The .cp-p6-body grid now has an explicit minmax(0, 1fr) column. This prevents intrinsic child width from expanding the body beyond its available workspace width and displacing the splitters.
- The persistent assistant launcher is compact and contained in the existing command rail, outside the workspace content rectangle. It remains mounted at the document level; no new workspace shell or width-reducing assistant panel was introduced.
- Source and published CSS mirrors are synchronized.

### Exact-head verification

- Client Typecheck: passed for web, mobile, desktop and client-sync.
- ConstructionPM CI: passed on Python 3.11, 3.12 and 3.13.
- ConstructionPM Web CI: passed — Typecheck, unit tests, build, production-shaped Pages artifact validation, preview runtime smoke test, browser E2E for workspace/assistant, browser E2E for Form Builder, and visual evidence upload.
- Browser E2E verified pane drag, column drag, persistence and reload, and viewport geometry at 1280×720, 1366×768 and 1920×1080.
- Screenshots for all three target viewport sizes are included in the run artifact above.

### Still open — do not infer acceptance from the resize pass

- The toolbar/menu hierarchy is still too tall and contains duplicated command surfaces. In the screenshot, the global icon toolbar, layout options row, command menubar, grouped command row, two tab strips, activity metadata row and page command row remain visible. Consolidate these into the approved title/menu/icon-toolbar/single-tabs/context-toolbar sequence without removing commands or breaking handlers.
- The Details pane's rendered content density at 1280×720 needs a separate visual review; do not change the Gantt timescale or force a global pane ratio to hide clipping.
- Add a real reset-to-default column widths action and verify it against the existing layout API; this slice does not claim it.
- The 48 approved visual windows versus 18 authenticated window keys remain a controlled migration. Do not delete the visual-demo bootstrap or expose a second authenticated workspace until the approved window inventory is migrated and verified inside cp-app-shell.
- The full page-by-page menu/dialog/service/permission audit remains open.
- Baseline, Documents write/upload, Reports, Tracking, Risks, Thresholds and Issues service gaps remain open unless separately verified with exact-head tests.
- Numerical schedule parity against an authorized latest-version reference remains unverified; no parity claim is made.
- No production deploy or merge was performed. The PR branch must be reconciled with the four newer main commits and re-tested before any merge decision.

## 12. Exact-head resize and viewport verification — 2026-11-05

**Integration:** `a170c87a` (PR #1716) merged into `301ddb91` on `codex/jalal/cubi-shell-v26-20261104`. The evidence below was captured on the merged tree immediately before the integration commit.  
**PR:** independent pull request from `codex/jalal/cubi-shell-v26-20261104` — Draft, not merged, not deployed. PR #1716 must not merge independently; it carries the same shell work.  
**Approved common base:** `7c3f4821` (latest `origin/main`).

### Executed on the merged tree
- Web workspace unit tests: 571 passed, 0 failed (`npm test`).
- Shell/public-page HTML tests: 14 passed, 0 failed.
- `tsc -p tsconfig.test.json --noEmit` and `npx tsc --noEmit`: passed.
- Python preview runtime tests: 19 passed.
- Managed full-stack browser E2E (`npm run test:e2e:preview`): **98 recorded checks, 53 screenshots, 0 uncaught exceptions, 0 API 5xx**; the only console errors are the two intentional stale-write failures described below. Evidence: `apps/web/e2e/artifacts/evidence.json`.
- Exact-head GitHub CI for this integration commit is requested by pushing the branch; the run has not been observed at the time of writing.

### Verified by browser E2E
- Details and table/Gantt splitters respond to mouse resizing and preserve layout preferences; storage keys are `cubi:workspace:split:<tenant>:<project>:<window>:<pane>`.
- Activity column hide/add/reorder/width/pin/freeze operations persist through the layout API.
- Layout survives a full reload through the real API and SQLite; the final reload restores the baseline columns.
- Geometry checks and pointer hit-target checks passed at 1280×720, 1366×768 and 1920×1080; compact navigation verified at 1024px.
- Assistant launcher stays inside the 36px right rail gutter (`assistantInsideRail: true`) and outside the workspace body at all three viewports.
- Both browser E2E suites passed, including Form Builder.

### Fixes carried into the integration
- One layout engine only: the browser-verified inline resize engine in `workspace-view.ts`; the duplicate `workspace-resizing.ts` from #1716 was removed rather than shipping two implementations.
- The E2E still records the two intentional `P6 layout save failed` console entries produced by its stale-write scenarios ("fails closed, reloads the head", "revision gap reloads the newest head"). Those checks assert the localized notice and the unchanged server head; they are expected, not tolerated races.
- The Vazirmatn stylesheet is requested after `load` instead of blocking module scripts. A stalled font CDN previously could leave `/app` blank with no API calls, because module scripts wait for pending style sheets.
- The native-drag helper waits one frame between press and move so pointer capture is installed before the movement, matching human input.
- Assistant launcher/panel offsets moved into the rail gutter so they no longer cover Details or the status bar.

### Shell consolidation — closed in this slice

The sibling continuation branch was merged into `codex/jalal/cubi-shell-v26-20261104`; overlapping resize code was resolved in favour of the browser-verified engine in `workspace-view.ts` rather than keeping two engines.

- One menu bar, one compact icon toolbar, one window-tab strip, one contextual command bar and one Details pane are rendered. The duplicate layout/command rows were removed.
- The left directory is a 46px icon strip with a full 18-window menu flyout; the right context rail is 36px.
- Details sits below the activity/Gantt split with a persistent 70/30 default; table/Gantt split defaults to 45% with 25–75 bounds; column widths persist through the revision-checked P6 layout callback.
- Pane preferences use per-tenant/project/window/pane storage keys and survive a full reload.
- Before/after evidence was captured at 1280×720; geometry was checked at 1280×720, 1366×768 and 1920×1080.
- The assistant launcher and closed assistant surface stay inside the right rail gutter and no longer cover Details or the status bar.

### Version 26 documentation pass — 2026-11-05

The six required Oracle Version 26 pages were opened and read in this session:
the user-guide index (`G57529-01`, October 2026), the help table of contents,
the Menu bar reference, the Layout toolbar reference, "Change Activity Table
font, color, and row height", and the Gantt "Change a bar's style" page.
The index is a JavaScript shell whose substantive content lives in the linked
chapters, so structure was read from the table of contents rather than the
index shell. Four deeper help pages (status/layout-options bar, main windows,
Activity Network, Activity Details) returned HTTP 403 when fetched and are
therefore **not** claimed as studied.

Two documentation-backed corrections were made:

- **Activity Network placement.** The documentation describes the Activities
  window as an activity table with a Gantt chart or Activity Network beside it.
  The network previously replaced the whole split; it now occupies the right
  pane while the activity table stays on the left, with the same splitter and
  selection model.
- **Table Font and Row.** The dialog now has a real font-size selector
  (10–13 px) and a fixed row-height field (18–34 px), both persisted and applied
  to the rendered activity grid. The earlier density radio only set an unused
  CSS variable; it is replaced by the height control, and density is derived
  from the chosen height. Font family, background colour, "optimize row heights
  by content" and "Show Icons" from the reference dialog are still missing.

The reference Layout toolbar lists twelve actions; CUBI exposes Columns,
Filter, Group/Sort, Timescale, Bars and Table Font and Row. Line Numbers and
User Preferences are not on CUBI's bar, and "Save/Save As/Open Layout" are
handled elsewhere. This divergence is recorded rather than hidden.

### Gaps that remain open

1. The 48-window visual catalogue is **not** fully migrated. Windows without an authoritative service remain visibly unavailable; do not create demo records.
2. Reporting, tracking, thresholds, issues/risks, engineering intelligence, project comparison and several administration surfaces still need real service contracts.
3. Column drag, filters, timescale and bars have acceptance coverage; the Activity Network now renders beside the activity table from persisted relationships. Activity/resource Usage Spreadsheet/Profile and Trace Logic remain disabled because their authoritative time-phased services are not wired.
4. Jalali/Gregorian rendering and the 48-window catalogue were re-audited. Arabic, French, Japanese and Korean remain selectable language-pack targets but carry no UI pack; the switcher now labels them as English-until-installed rather than implying a translated interface.
5. The Bars dialog now edits seven real bar types with start/body/finish shapes, colours, patterns, filters, labels and row assignment, persisted with the layout. It still lacks user-defined Add/Delete/Copy From bars, per-bar timescales, Bar Settings grouping/necking, Sight Lines and an inline Preview column; see the 2026-11-06 bar-style entry below.
6. The reference Menu bar has eight fixed menus plus a conditional Admin menu; CUBI exposes eleven task-oriented menus (adding Schedule, Resources, Reports and Window) and no Admin menu because the preview has no database administration surface.

### Integration guard

PR #1716 remains open and must not be merged independently while this branch carries the same shell work. The merge commit preserves its server deep-link/logout changes, CI evidence upload, browser E2E additions and this ledger, while the resize engine is the single implementation tested above. Keep every PR in Draft until exact-head CI and visual review are complete.

### WBS bands, synchronized collapse and activity context menu — 2026-11-06

**Branch/head:** `codex/jalal/cubi-shell-v26-20261104`, code commit `3857d7a1` on base `2ccfd942`; pushed, not merged, no Production change.

- **Colored WBS hierarchy.** A real display-row view model (`apps/web/src/workspace-wbs-display.ts`) emits one WBS band row for every node that still contains filtered activities, followed by its activity rows. The six-level palette is `#3B3BBF`, `#FFFF00`, `#C6FFC6`, `#CCF2FF`, `#FFD9EC`, `#EEE0FF`; the band fill uses high-specificity selectors so the even-row and pinned/frozen column rules cannot wash it out, and level 1 switches to white text. The Gantt group row carries the same level color and the summary bar is derived from the persisted child activities. The preview project has only two real levels (root plus six groups), so levels 3–6 are covered by unit tests but are not claimed as visually demonstrated.
- **Synchronized collapse.** One display-row list feeds both the table and the Gantt. The `+/−` control on a band toggles that branch, child activities disappear from both views, and the state persists per project in `localStorage` under `cubi:workspace-wbs-collapse`. Live check on `preview-rps-01`: collapsing `WBS-RPS-PM` removed `A100`, `A110` and `A210` from the table and the Gantt (14 → 11 in both), while the 7 bands, 7 summary bars and all unrelated activities stayed. Gantt links now use bar indices for horizontal geometry and display-row indices for vertical anchors, which also fixed an undefined-anchor crash introduced by the inserted band rows.
- **Gantt.** Task, summary, milestone and critical bars render from the persisted schedule; FS and SS relationships keep their persisted semantics; group rows, day/week/month/quarter/year ticks and the shared zoom remain aligned with the table.
- **Activity context menu.** Twenty commands in the reference order are delegated from the activity rows and cells: Activity Details, Cut, Copy, Paste, Fill Down, Add, Delete, Dissolve, Renumber Activity IDs, Export to Excel, Assign, Link Activities, Columns…, Line Numbers, Table Font and Row…, Filters…, Group and Sort…, Expand All, Collapse All and Collapse To…. Eleven are enabled and routed through the shared command registry; nine are disabled with a specific reason because the runtime exposes no corresponding write or export route. The menu is clamped inside `.cp-p6-workspace` (measured top 228, height 474, workspace 97–706), scrolls when needed, closes on Escape and restores focus. The RTL/Persian variant is mirrored and fully visible.
- **Verification.** `npx tsc --noEmit` passed; web unit tests 614/614; preview resolver tests 14/14; `npm run build` passed. The managed browser E2E recorded 98 checks and 53 screenshots from the working tree (evidence `git_head` 2ccfd94; the tested content is committed as 3857d7a1). WBS/context-menu evidence was captured with `apps/web/e2e/capture-wbs-menu.mjs` into `e2e/artifacts/wbs-live/wbs-menu-capture.json` and screenshots at 1280×720, 1440×900, 1920×1080, plus menu zoom and Persian RTL.
- **Audit record:** full command-by-command and measurement record in `docs/qa/WBS_GANTT_CONTEXT_MENU_AUDIT_2026-11-06.md`, with committed screenshots `docs/workspace/screenshots/visual/44`–`48` and raw capture `docs/workspace/evidence/wbs-context-menu-2026-11-06.json`.
- **Correction — band fill to the last column (2026-11-06).** The first pass painted only the data and pinned cells, so the Predecessors (`cp-logic-column`) and Edit (`cp-actions-column`) cells stayed white. The band rule now targets every `td` in the band row, including the final two cells, and a stylesheet contract test fails if the narrowed selector returns. Recapture on all seven bands reports 12/12 cells with the band background; after scrolling the table to its end both final cells are visible and keep the color. Screenshot `48-wbs-bands-last-columns-en-1280.png`; web unit tests are now 615/615.
- **Not claimed.** Delete, Cut, Copy, Paste, Fill Down, Dissolve, Renumber, XLSX export and Assign remain disabled until real service routes exist. No visual proof is offered for WBS levels 3–6. Exact-head CI for `3857d7a1` had not completed at the time of this entry. PR #1716 still must not merge independently, and no merge to `main` or Production deployment was performed.


### Advanced activity filters — 2026-11-06

**Branch:** `codex/jalal/cubi-shell-v26-20261104`; pushed, not merged, no Production change.

- **Reference scope.** Chapter 9 of the supplied Version 26 help (`G57535-02`, PDF pages 403–412): the fourteen predefined activity filters, the Field/Is/Value builder reached from View > Filter By > Customize > New, AND/OR criteria, save and re-apply, and combined filters. No Oracle/Primavera branding or proprietary assets were introduced.
- **Real filter model.** `apps/web/src/workspace-activity-filters.ts` evaluates criteria against the same row values the table renders. Seven documented defaults are live (In Progress, Not Started, Completed, Critical, Non Critical, Negative Float, Milestone). Custom filters support four Field/Is/Value rows, AND/OR, contains, equals, is not equal to, greater/less than and empty/not-empty, with bounded normalization (20 saved filters, 8 criteria, 120-character values).
- **WBS semantics fixed.** A `wbs` criterion now resolves the WBS node’s displayed code and name instead of the internal node id. Regression test: `WBS contains Procurement` matches the row stored as `WBS-RPS-PROC`, while `WBS contains WBS-RPS` matches nothing.
- **Apply, persist, clear.** The Filters dialog is reachable from View > Filters, the toolbar Filters button and the activity context menu. Selection is applied before display-row construction, so the table and Gantt always show the same IDs. Saved filters live in the layout presentation metadata and re-apply after reload. Choosing another entry in the Apply list resets the custom builder, so “All activities” really clears instead of resaving stale criteria.
- **Live evidence.** `preview-rps-01`, 1280×720: baseline 14 activities; In Progress → `A130`; custom AND “Civil open” → `A130, A140, A145, A160`; custom OR “Civil or procurement” → the same four plus `A120, A150`; reload kept the six-row OR filter; clearing restored 14. Table and Gantt IDs were identical in all six states. Dialog 640×457 inside the viewport.
- **Verification.** `npx tsc --noEmit` passed; web unit tests 625/625; preview resolver tests 14/14; `npm run build` passed. Capture tool `apps/web/e2e/capture-filters.mjs`; raw record `docs/workspace/evidence/filters-2026-11-06.json`; screenshots 49–54; audit `docs/qa/ACTIVITY_FILTERS_AUDIT_2026-11-06.md`.
- **Not claimed.** Seven remaining documented defaults (constraint-based filters, Level of Effort, Longest Path, New Feedback, Non What-If, Normal) need row aliases that are not exposed yet. No multi-filter combination, global filters, date/numeric range operators, or filters on other windows. PR #1716 must not merge independently; no `main` merge or Production deployment was performed.

### Gantt bar styles and a summary bar that obeys them — 2026-11-06

**Branch:** `codex/jalal/cubi-shell-v26-20261104`; pushed, not merged, no Production change.

- **Reference scope.** Chapter 7 of the supplied Version 26 help (`G57535-02`, PDF page 334, help pages 11–12 of 48): “Add a bar to the Gantt Chart”, “Change a bar in the Gantt Chart” and “Position a bar in the Gantt Chart”. No Oracle/Primavera branding or proprietary assets were introduced.
- **Real bar model.** Seven bar types (Task, Critical, Summary, Milestone, Progress, Actual, Baseline) each carry Display, Filter, Row 1–3, Height, Pattern (solid/striped/hatched/outline), Start/Body/Finish shape (bar/line/triangle-up/triangle-down/diamond/circle/none), Start/Body/Finish/Border colour, Label and Label position. Filters are All, Task, Critical, Non-critical, Milestone, Summary, In Progress, Completed and Not Started. Actual and Baseline are disabled with an explicit note when no dates exist.
- **Summary bar fix.** The WBS summary renderer previously ignored the summary style. It now consumes the persisted height, pattern, start/finish shapes and label, with matching CSS for striped/hatched/outline bodies and line/diamond/circle/triangle bodies. The default summary label is `none`, because “1”/“2”/“3” duplicated the band code. Regression test added in `workspace-view.test.ts`.
- **Live evidence.** `preview-rps-01`, 1280×720: defaults showed a 13 px solid task bar (`#eef3f8`, label A110) and a 10 px solid summary bar (`#17324d`, triangle-down endpoints, no label). The customized run submitted `#c0392b`, striped, diamond body, circle start, triangle-up finish and an inside-centre “Mobilization” label for tasks, and `#0b5fa5`, hatched, 16 px, diamond endpoints and a right “Riverside Pump Station Upgrade” label for summaries; the DOM reported exactly those computed values. Reload reproduced them; the saved defaults restored the original rendering. Bar counts stayed 6 task / 7 critical / 7 summary. Dialog 780×619 inside the viewport.
- **Verification.** `npx tsc --noEmit` passed; web unit tests 626/626; preview resolver tests 14/14; `npm run build` passed; both stylesheets byte-identical. Capture tool `apps/web/e2e/capture-bars.mjs`; raw record `docs/workspace/evidence/bars-2026-11-06.json`; screenshots 55–58; audit `docs/qa/GANTT_BAR_STYLES_AUDIT_2026-11-06.md`.
- **Not claimed.** No Add/Delete/Copy From bar definitions, per-bar timescale, Bar Settings grouping/necking, Sight Lines, inline Preview column or Apply-without-closing. The 18 px task height renders at 14 px because stacked layers are scaled into the 22 px activity row; this is recorded rather than hidden. Styling never re-dates a bar. PR #1716 must not merge independently; no `main` merge or Production deployment was performed.

### Multi-level Group and Sort — 2026-11-06

**Branch:** `codex/jalal/cubi-shell-v26-20261104`; pushed, not merged, no Production change.

- **Reference scope.** Chapter 8 of the supplied Version 26 help (`G57535-02`, PDF pages 377–378, help pages 6–7 of 31): “Group and sort a tracking layout using standard settings” and “…using custom settings”. No Oracle/Primavera branding or proprietary assets were introduced.
- **Ordered sort plan.** The Group and Sort dialog now has three ordered Field/Order rows (Ascending or Descending). Empty rows are ignored, duplicate fields collapse to their first position, unknown columns are dropped and the plan is capped at three. The first row drives the toolbar “Sort by” value and its direction button; changing the toolbar select replaces the plan with one field; the toolbar direction button flips only level one and keeps deeper levels.
- **Real ordering.** `workspace-filter-sort.ts` compares every level in order, keeps blank values last in both directions, compares numbers numerically, and uses the activity ID only as the final tie-break after all levels. Under WBS grouping the plan applies inside each WBS block, and a WBS level is ignored because the grouping already supplies it. No schedule data is written or re-dated.
- **Live evidence.** `preview-rps-01`, 1280×720: default order `A100, A110, A210, A120, A130, A140, A145, A160, A150, A155, A180, A170, A190, A200`; after Status ↓ then Name ↑ the table and Gantt both showed `A210, A110, A100, A140, A145, A160, A130, A120, A150, A155, A180, A190, A170, A200`. Completed rows in “Project management” reordered by name (Mobilization before Project kickoff), Not Started rows in “Civil works” ordered Piling → Site utilities → Steel erection, and “MEP works” ordered Commissioning before MEP first fix. Restoring WBS returned the original order. Counts stayed 14/14 in every state. Dialog 520×465 inside the viewport.
- **Verification.** `npx tsc --noEmit` passed; web unit tests 629/629; preview resolver tests 14/14; `npm run build` passed; both stylesheets byte-identical. Capture tool `apps/web/e2e/capture-group-sort.mjs`; raw record `docs/workspace/evidence/group-sort-2026-11-06.json`; screenshots 59–61; audit `docs/qa/GROUP_SORT_AUDIT_2026-11-06.md`.
- **Not claimed.** Grouping is still WBS or none; there are no other grouping categories, band title/colour controls, alphabetical band sorting, hide-if-empty, grand totals or summaries-only. The sort list is a fixed three rows rather than an unbounded Add/Delete list, and group/sort are not yet saved into layout metadata, so a reload returns to the WBS default. PR #1716 must not merge independently; no `main` merge or Production deployment was performed.

### Server-evaluated formula columns — 2026-11-06

**Branch:** `codex/jalal/cubi-shell-v26-20261104`; pushed, not merged, no Production change.

- **Reference position.** The supplied Version 26 help (`G57535-02`) documents the Columns dialog and Edit Column on PDF pages 330–331 and calculated fields on pages 129 and 749, but it does not document a formula-column dialog. The editor is an extension built for the directive's “Column Formula / formula settings” requirement; it is not claimed as a verbatim v26 window.
- **Real service in the owning layer.** `P6FormulaColumnService` / `P6FormulaColumnAPI` (`src/construction_pm/p6_formula_column.py`) normalise the `formula.` prefix, compile through the shared formula engine, reject unknown fields and self-reference, persist immutable definitions (`cubi-formula-column.v1`, `shared-core:p6-formula-column`) and evaluate per activity in dependency order. The registry projects each saved column as a computed read-only field; the validator schema includes it; the workspace read provider injects `formula.<id>` cells from real activity values. The browser never evaluates an expression.
- **HTTP and wiring.** `GET/POST /api/projects/<project>/p6/formula-columns` return `p6-formula-column-api.v1` with project scope and permission checks (400 on invalid payload, 401/403 unauthorised). The preview runtime wires SQLite persistence, the definition service, registry, validator and both read providers. Production composition accepts the parameter but still does not construct the API, so production does not silently expose it.
- **UI flow.** Project > Formula editor validates the expression first, then saves title, ID and expression. The catalogue lists the saved definition; a successful save re-reads the registry, adds the field to the persisted layout, commits it and re-renders from the server.
- **Live evidence.** `preview-rps-01`, 1280×720: `[activity.duration_percent_complete] * 2` validated with dependency `activity.duration_percent_complete` and type `double`; saving `Double progress` / `formula.double_progress` produced a `Double progress ƒx` column with A100/A110/A120 `200.0`, A130 `75.0`, not-started rows `—` and blank WBS bands; a full reload kept header and values; the SQLite row contains the version, expression, dependency JSON and column metadata. `[activity.missing_field] * 2` was rejected with `FIELD_NOT_FOUND:activity.missing_field` and nothing was saved. The Persian RTL capture shows the same column and values with the WBS band colour continuing to the last columns.
- **Verification.** `py -3 -m pytest tests/test_p6_formula_column.py tests/test_project_lifecycle_http_routes.py tests/backend_p0 -q` — 191 passed. `npx tsc --noEmit` passed; web unit tests 637/637; preview resolver tests 14/14; `npm run build` passed; both stylesheets byte-identical. Capture tool `docs/workspace/qa/formula-column-shot.mjs`; screenshots `62`, `63`, `64`, `67`, `65` and the Persian `66`; audit `docs/qa/COLUMN_FORMULA_AUDIT_2026-11-06.md`.
- **Not claimed.** No formula deletion, rename or edit-in-place; no formula sharing between projects; no formula-specific function catalogue beyond the shared engine. Production composition remains unwired. PR #1716 must not merge independently; no `main` merge or Production deployment was performed.

### Activity Table Columns and Edit Column — 2026-11-06

**Branch:** `codex/jalal/cubi-shell-v26-20261104`; pushed, not merged, no Production change.

- **Reference scope.** Chapter 7 of the supplied Version 26 help (`G57535-02`, PDF pages 330–331, help pages 6–8 of 48): View > Columns, Available Columns / Selected Options transfer, Add/Add All/Remove/Remove All, move order, Copy From, OK/Apply/Default, and Edit Column with title, width, alignment and Default. No Oracle/Primavera branding or proprietary assets were introduced.
- **Server-owned defaults.** `p6_layout_defaults.py` holds the canonical activity column set and `P6LayoutDefinitionAPI.default_layout()` returns it at revision 0 without writing. `GET /api/projects/<project>/p6/layouts/<scope>/<view>/default` enforces session, project scope and `PROJECT_READ`, and answers `404 P6_LAYOUT_DEFAULT_NOT_DEFINED` for views without defaults. The browser loads this through `loadP6DefaultLayout()`; defaults are not duplicated client-side.
- **Real Columns dialog.** `p6-columns-dialog.ts` implements the draft model and the mounted modal: search, subject filter, add, add all, remove, remove all with a last-column guard, move, per-column visibility, Edit Column (title/width/alignment, default title in parentheses, restore default), Default from the server, OK saves and closes, Apply saves without closing and rebases on the saved revision, Cancel discards. The toolbar Columns button, View > Columns and the activity context menu all open the same dialog through `main.ts`. Copy From is disabled with the real one-layout-per-view reason instead of a simulated picker.
- **Live evidence.** `preview-rps-01`, 1280×720, planner session: the stored 20-column layout opened with 1 available field; Edit Column on Activity Name reported title `Activity Name`, default `Name`, width 151, Left; Default produced 8 selected / 13 available with the reference titles; OK saved, the table rendered those eight plus the fixed Predecessors and Edit columns, and a full reload returned the same headers. Apply kept the dialog open with “Columns applied.” The Persian pass measured 860×575 at (210, 73), direction `rtl`, with mirrored panes and footer. Dialog geometry EN 860×571 at (210, 75); the selected list scrolls (298 px viewport, 334 px content).
- **Verification.** `npx tsc --noEmit` passed; web unit tests 646/646 (8 new dialog tests); preview resolver tests 14/14; `py -3 -m pytest tests/test_p6_layout_definition_api.py tests/test_project_lifecycle_http_routes.py -q` 100 passed; `npm run build` passed; both stylesheets byte-identical. Capture tools `docs/workspace/qa/columns-dialog-shot.mjs` and `columns-dialog-measure.mjs`; screenshots 68–73; audit `docs/qa/COLUMNS_DIALOG_AUDIT_2026-11-06.md`.
- **Not claimed.** Copy From needs a named-layout list service and stays disabled. The registry’s short technical names (`Id`, `Name`, `Planned Duration`, …) make the reference default labels appear as custom titles in the dialog and make Edit Column > Default restore the short name; the grid itself matches the reference. Move order is up/down in the vertical list. No available-column grouping bar, no multi-layout naming or sharing. PR #1716 must not merge independently; no `main` merge or Production deployment was performed.
