# Native Mobile V1 Rebaseline Backlog — 2026-10-18

**Decision:** Native Mobile is mandatory in CUBI V1 alongside the Website and Desktop application. See [Issue #1486](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1486).  
**Status:** Proposed task decomposition; estimates, weights, dates and predecessor-network review are **OPEN**. These rows do not yet count in the Jalal 5 100-point denominator or earn progress.  
**Workbook companion:** `Jalal5_Weighted_Master_Schedule_2026-10-18_MobileV1-Rebaseline.xlsx`, `Mobile V1 Rebaseline` sheet (14 candidate rows; weight/effort intentionally TBD). The workbook's old 130-row/100-point/535.21-PD model is not the final baseline after this scope decision.

## Scheduling and ownership rules

- Farmj22002 leads native client/runtime and Mobile user journeys; Hasan covers backend/API/persistence/identity/sync contracts; Jalal owns calculation semantics, architecture, integration and release acceptance.
- This backlog must be sized at task level, assigned to actual owner lanes, connected to relevant predecessors, then merged into the authoritative Jalal 5 schedule workbook. Reallocate existing scope only after explicit impact review; keep all accepted activity weights at exactly 100.00 points and rerun formula, dependency and owner-lane forecast QA.
- The former Jalal 3 plan reserved 20 points for Mobile. That is a historical sizing reference only, not a pre-approved Jalal 5 allocation. Do not copy it across automatically.
- All scheduling/calendar/resource/progress/cost/EVM calculations must remain in the authoritative Shared Domain/Calculation Core through versioned APIs. Mobile must not implement a parallel calculation engine.
- Acceptance credit requires merged current-main code, checks for the exact candidate SHA, appropriate real-device/runtime and integration evidence, owner review and updated workbook links.

## Candidate activity inventory

| Candidate ID | Activity / scope | Primary owner | Support / reviewer | Dependencies to validate | Definition of Done |
|---|---|---|---|---|---|
| MV1-01 | Mobile screen, route, action, permission and acceptance map | Farmj22002 | Jalal | A01, A02, #1486 | Approved inventory maps each Mobile V1 journey to requirement, owner, API/contract, permissions, locales, empty/error/recovery states, test ID and acceptance evidence. |
| MV1-02 | Native host, runtime, startup and app lifecycle | Farmj22002 | Hasan; Jalal | A01, G01 | Installable native target passes startup, navigation, foreground/background, crash/error recovery and session lifecycle checks. |
| MV1-03 | Authentication, session, project list and workspace selection | Farmj22002 | Hasan | MV1-02, G01, G09 | Real signed-in user can select permitted projects; tenant/role denials, logout, session expiry, empty/error and inaccessible-project states are tested. |
| MV1-04 | WBS and work-package navigation/editing | Farmj22002 | Hasan; Jalal | MV1-03, G02, G03 | Authorized hierarchy changes persist through write → commit → fresh-read; invalid parentage and stale revision are rejected. |
| MV1-05 | Activity detail, create/edit and typed field validation | Farmj22002 | Hasan; Jalal | MV1-04, G02, G03, G04 | Essential activity fields and typed dates/durations/percent values persist correctly; invalid input and optimistic-revision conflicts are tested. |
| MV1-06 | Relationship editor: FS/SS/FF/SF, lead/lag | Farmj22002 | Jalal; Hasan | MV1-05, B03, G03 | Relationship types and negative/zero/positive lags are passed to authoritative validation; cycle, unsupported and stale edits are rejected with regression proof. |
| MV1-07 | Invoke schedule/recalculate and display authoritative results | Farmj22002 | Jalal; Hasan | MV1-06, B04, B06, G03 | Returned schedule revision/identity, early/late dates, float and criticality match the shared engine; no client CPM/calendar/float calculation. |
| MV1-08 | Calendar assignment and Jalali/Gregorian date experience | Farmj22002 | Jalal; Hasan | MV1-03, B05, H04 | In-scope calendar assignments and versions round-trip with no silent default fallback; Jalali/Gregorian boundary and locale tests pass. |
| MV1-09 | Field logs, attendance/timecards and equipment status | Farmj22002 | Hasan; Jalal | MV1-03, G06 | Owner-approved subset persists via real API and passes validation, authorization, audit and fresh-read tests. |
| MV1-10 | Inspection, quality, safety and punch/closeout workflows | Farmj22002 | Hasan; Jalal | MV1-03, G06, MV1-09 | Exact first-release field assurance subset is approved and end-to-end tested for permissions, invalid transitions, evidence and closure. |
| MV1-11 | Sync/offline boundaries, conflicts and recovery | Farmj22002 | Hasan; Jalal | MV1-05, MV1-09, MV1-10, G04, G11 | Declared offline flows pass retry/idempotency, ACK/CONFLICT/REJECTED, stale revision, reconnect readback and app-restart recovery tests. |
| MV1-12 | Localization, RTL/LTR, accessibility and contextual Help | Farmj22002 | Jalal; Hasan | MV1-02, H01–H04, H07 | Every declared supported language covers Mobile V1 screens/actions/errors; RTL/LTR, keyboard/screen-reader, font and locale formatting tests pass. |
| MV1-13 | AI assistant integration and verified voice/native readiness | Farmj22002 | Hasan; Jalal | MV1-03, D04, D11, D22, H05 | Mobile uses shared assistant contracts, permission checks, preview/approval, authoritative actions and audit; voice/OCR/offline capability is claimed only after real runtime proof. |
| MV1-14 | Mobile cross-client parity, device matrix and release gate | Jalal | Farmj22002; Hasan | MV1-01–MV1-13, J01, J02, J03, J07, J10 | Approved device/runtime matrix, install/upgrade/recovery, security, integration, client parity and exact-SHA release gates pass with no unresolved P0 blocker. |

## Mandatory exit gate

Do not approve Jalal 5's master baseline until these candidate IDs are either integrated into the main activity table with accepted task-level weights/estimates/dependencies, or have a documented owner-approved disposition. After integration, recalculate the 100.00-point denominator, effort, workstream summary, dependency graph, owner-lane checks and delivery forecast; independently inspect formula results. Until then, status remains **DRAFT / MOBILE WEIGHTING OPEN**, and Jalal 5 earned progress remains **Pending**.
