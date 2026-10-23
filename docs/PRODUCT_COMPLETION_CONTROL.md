# Product Completion Control — Main-First / No-Duplication Policy

**Effective:** 2026-09-30  
**Priority:** Finish the Web product and commercially usable software before expanding side tracks.

## 1. Authoritative source hierarchy

When two records disagree, use this order:

1. Latest merged `main` code.
2. Tests and CI/runtime evidence attached to the merged implementation.
3. Current PR/issue evidence based on that `main`.
4. Current roadmap/status documentation.
5. Historical branches, old PRs and old chat notes — evidence only, never implementation authority.

This prevents the project from moving backward because an old continuation note says a completed stage is unfinished.

## 2. No-backtracking gate

Before any coding begins:

- identify the exact capability;
- search current `main`;
- identify the authoritative implementation and tests;
- inspect the last merged PR(s);
- identify what is genuinely missing;
- define the smallest missing boundary.

If nothing is missing, do not code. Mark the capability verified and move to the next real gap.

## 3. Ownership matrix

| Area | Jalal | Hasan | Javad |
|---|---|---|---|
| Shared calculations / P6 | **Owner** | Consume | Consume |
| Calendar arithmetic / scheduling | **Owner** | Persistence/API only | Presentation only |
| Progress / EVM | **Owner** | Persistence/API only | Presentation only |
| PostgreSQL / Repository | Integration | **Owner** | Consume |
| API/Application | Architecture/acceptance | **Owner** | Consume |
| Web UI | Acceptance | Contract support | **Owner: Javad (Farmj22002)** |
| Desktop/Mobile | Acceptance | Contract support | **Owner: Javad (Farmj22002)** |
| UX / RTL / LTR / localization UI | Acceptance | Contract support | **Owner: Javad (Farmj22002)** |
| Client sync UI | Acceptance | Sync authority | **Owner: Javad (Farmj22002)** |
| Import/export mapping | Semantic authority | **Owner** | UI/UX integration |
| Final integration | **Owner** | Participate | Participate |
| Release acceptance | **Owner** | Evidence | Evidence |

## 4. Immediate product-completion priority

### P0 — protect the baseline
- keep `main` green;
- remove stale continuation instructions;
- stop duplicate branches;
- verify required CI triggers;
- record exact merge evidence.

### P1 — Web product completion
Work in vertical slices, not isolated backend/client fragments:

1. Application shell, authentication and authorization.
2. Project creation/opening and project settings.
3. WBS and Activity workspace.
4. Calendar configuration and assignment.
5. Scheduling/Gantt and schedule-result presentation.
6. Resources, assignments and costs.
7. Progress, actuals and EVM/control views.
8. Documents, revisions, correspondence/RFI/Submittal/claims.
9. Reports, dashboards and print/export.
10. Excel/XLSX and Microsoft Project interchange.
11. Persian/English, RTL/LTR, Jalali/Gregorian UX.
12. Audit trail, permissions, error handling and recovery.
13. End-to-end Web acceptance.

Each slice must be usable from UI through API/application/persistence to authoritative calculation where applicable.

### P2 — cross-client completion
Only after the Web path is usable:
- Desktop;
- Mobile;
- offline mutation/sync;
- cross-client parity.

## Cross-cutting V1 release requirements — mandatory, staged delivery

These are release requirements, not optional P3 enhancements. Their implementation must be staged behind a stable, persisted product path, but contract/design work may proceed in parallel.

- **Production AI Project Controls Assistant (#1423):** natural-language and supported project-file intake, validation/preview, typed approved tools, user-controlled project/tenant/operation permissions, preview/approval/rejection, audit, authoritative Shared Core calculation, fresh-read verification, and reports/charts/Gantt from real persisted results. Voice/file intake required by the V1 assistant belongs to this scope.
- **All-language localization (#1428 and Help Center #607):** registry-driven UI, project data, help and AI workflows across all Web surfaces; no two-language-only hard-coded ceiling; preserve RTL/LTR and Jalali/Gregorian behavior.
- **Page-level SEO and language indexing (#1436):** page-specific titles/descriptions, canonical and hreflang handling, sitemap/indexing and clear separation between public marketing pages and the private app workspace.
- **Durable V1 reliability (#1439):** command-level Undo/Redo, project-version restore, and verified backup/recovery are separate acceptance tracks; passing one does not imply the others are complete.

The production AI workflow must use real application services and the same authoritative Shared Core—not a separate scheduler or a direct privileged database writer. These dependencies are sequencing constraints, not permission to defer mandatory V1 acceptance.

### P3 — optional advanced enhancements after V1 gates
- OCR/search enhancements beyond the supported project-file intake required for the V1 assistant;
- independent advanced automation and other non-critical enhancements.

P3 must not repeatedly interrupt unfinished critical P0/V1 workflows.

## 5. Javad (Farmj22002)'s current mission

Javad is **not** assigned to rebuild scheduling or other Shared Core logic.

His next work must be selected from the Web completion backlog and must follow this order:

1. audit current Web implementation;
2. identify the first genuinely missing user-facing workflow;
3. implement that workflow against existing API/Shared Core contracts;
4. add client tests;
5. verify RTL/LTR and Persian/English behavior;
6. verify error/loading/empty/offline states;
7. integrate and run client CI;
8. record the exact next missing Web workflow.

A branch named `feature/javad/...` is not evidence that its work is still required. Its actual code must be compared against current `main` before reuse.

## 5A. Supervisor / Observer — NO ASSIGNED DUTY

The **Supervisor/Observer (ناظر)** has **no development or delivery responsibility** in this project operating model.

- No coding, testing, review, integration, task ownership, PR ownership, roadmap ownership, or release responsibility is assigned to the Supervisor/Observer.
- Do not create implementation tasks for the Supervisor/Observer as part of the three-person development team.
- The only implementation owners are **Jalal**, **Hasan**, and **Javad (Farmj22002)** within their defined boundaries.

## 6. Hasan's current mission

Hasan must focus on backend gaps required to make P1 Web workflows complete.

Priority:
1. current-main audit;
2. identify missing API/application/persistence boundary;
3. implement only the missing boundary;
4. PostgreSQL verification where applicable;
5. tenant/revision/idempotency/transaction verification;
6. CI;
7. merge;
8. update continuation evidence.

The current Codex review-quota blocker must not cause duplicate implementation. When review capacity is unavailable, the work is simply blocked and preserved.

## 7. Jalal's current mission

Jalal controls:
- authoritative calculation semantics;
- P6 parity;
- cross-team dependency order;
- current-main reconciliation;
- duplicate detection;
- integration;
- final acceptance.

Jalal's first question for every new task is:

**"What is the smallest real gap on current main that prevents the product from being more complete?"**

Not:

**"Which old stage or branch should we revive?"**

## 8. Required PR template

Every new PR must state:

- Base SHA:
- Owner:
- Capability:
- Current-main implementation checked:
- Existing PRs/paths checked:
- Exact missing gap:
- Dependencies:
- Files/modules expected to change:
- Production behavior:
- Tests:
- CI gates:
- Non-goals:
- Next task after merge:

## 9. Branch rules

- Never branch from an old feature branch unless explicitly required for a documented reason.
- Prefer a fresh branch from current `main`.
- Never revive a stale PR merely because it contains useful commits.
- Port only still-valid intent after comparing it with current `main`.
- One capability = one owner = one authoritative implementation.
- After merge, the merged code becomes the only implementation baseline.

## 10. Stage completion rule

A stage is complete only when:

**Implementation + tests + required integration + CI/runtime evidence + merge + continuation record**

are all present.

A stage number alone is never a completion percentage.

## 11. Whole-product progress rule

Do not calculate overall product percentage from the highest Stage number.

The project contains parallel workstreams and nested stages. Overall progress must be calculated from an authoritative capability matrix covering:

- Shared Core/P6;
- Scheduling/Calendar;
- Progress/EVM;
- Resource/Cost;
- Backend/API/Database;
- Web;
- Desktop/Mobile;
- Documents;
- Import/Export;
- Localization;
- AI;
- Security/Audit;
- QA/Release.

Until that matrix is generated from current `main`, any single overall percentage would be an estimate rather than evidence.

## 12. Anti-regression checkpoint

At the start and end of every work session:

**START**
`main SHA → current PRs → relevant files → existing tests → real gap`

**END**
`tests → CI → merged SHA → status update → next single task`

This checkpoint is mandatory to prevent the project from returning to old stages or repeating completed work.
