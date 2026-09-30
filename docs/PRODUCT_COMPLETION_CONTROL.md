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
| Web UI | Acceptance | Contract support | **Owner** |
| Desktop/Mobile | Acceptance | Contract support | **Owner** |
| UX / RTL / LTR / localization UI | Acceptance | Contract support | **Owner** |
| Client sync UI | Acceptance | Sync authority | **Owner** |
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

### P3 — advanced capabilities
- AI assistant/guide;
- voice entry;
- intelligent document/OCR/search enhancements;
- advanced automation and non-critical enhancements.

P3 must not repeatedly interrupt an unfinished P1 workflow.

## 5. Javad's current mission

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
