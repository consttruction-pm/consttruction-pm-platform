# Progress index — Help traceability and acceptance specifications

This is the resumable state of the Agent 2 workstream. It is the first file a
new session reads. Update it in every section PR.

## Current state

| Field | Value |
| --- | --- |
| Last verified `main` | `74370eeca` (Section 2 merged) |
| Baseline for this workstream | PR #2101 merged as `6c25964a4` |
| Canonical page↔Help index | `docs/traceability/{engineering,enterprise}-v26.json` |
| Help link check | **84/84 rows verified**, report in `evidence/help-link-verification-2026-11-21.json` |
| Open PR (this section) | Section 3 PR |
| Next exact task | Section 4 — Gantt, Relationships and Calendars |
| Owner split | Agent 1 implements; Agent 2 documents, traces and specifies tests only |

## Section plan

Statuses: `NOT_STARTED`, `IN_PROGRESS`, `DOCUMENTED`, `HELP_VERIFIED`,
`TEST_SPECIFIED`, `PR_OPEN`, `MERGED`, `BLOCKED`.

| # | Section | Status | Document | PR / merge | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | Repository audit and documentation ownership map | `MERGED` | `README.md`, `OFFICIAL_HELP_BASELINE.md`, `SPEC_TEMPLATE.md`, this index | PR #2106 → `99e77d01c` | 84/84 Help rows verified; no product files touched |
| 2 | Engineering workspace and Activities | `MERGED` | `ENGINEERING_WORKSPACE_ACTIVITIES.md` | PR #2107 → `74370eeca` | 18 Help + 16 User Guide URLs; 11 scenarios; 4 documented divergences |
| 3 | Activity Details and WBS | `PR_OPEN` | `ENGINEERING_ACTIVITY_DETAILS_WBS.md` | — | 43 rows, 23 scenarios; 40 Help + 27 User Guide URLs; 8 documented divergences/gaps |
| 4 | Gantt, Relationships and Calendars | `NOT_STARTED` | `ENGINEERING_GANTT_RELATIONSHIPS_CALENDARS.md` | — | bars, progress, logic lines, constraints, calendars |
| 5 | Resources, Costs and Project Dictionaries | `NOT_STARTED` | `ENGINEERING_RESOURCES_COSTS_DICTIONARIES.md` | — | roles, assignments, cost fields, codes |
| 6 | Filters, Layouts and Toolbars | `NOT_STARTED` | `ENGINEERING_FILTERS_LAYOUTS_TOOLBARS.md` | — | filters, grouping, saved layouts, menus |
| 7 | Documents, Tracking and Reports | `NOT_STARTED` | `ENGINEERING_DOCUMENTS_TRACKING_REPORTS.md` | — | work products, progress, print/report |
| 8 | Import, Export, Backup and Workflow | `NOT_STARTED` | `ENGINEERING_EXCHANGE_BACKUP_WORKFLOW.md` | — | interchange, backup/restore, project workflow |
| 9 | Enterprise workspace and personal workbench | `NOT_STARTED` | `ENTERPRISE_WORKSPACE_WORKBENCH.md` | — | environment selection, roles |
| 10 | Enterprise Team, Organization and Administration | `NOT_STARTED` | `ENTERPRISE_TEAM_ORG_ADMIN.md` | — | task center, org access, admin |
| 11 | Enterprise Workflow, Communications and Portfolio | `NOT_STARTED` | `ENTERPRISE_WORKFLOW_COMMS_PORTFOLIO.md` | — | approvals, messaging, portfolio |
| 12 | Enterprise PMBOK, Contract and Commercial | `NOT_STARTED` | `ENTERPRISE_PMBOK_CONTRACT_COMMERCIAL.md` | — | PMBOK surfaces, contracts |
| 13 | Enterprise Claims, Resources and Risk | `NOT_STARTED` | `ENTERPRISE_CLAIMS_RESOURCES_RISK.md` | — | delay analysis, capacity, assurance |
| 14 | Enterprise Document and Information Management | `NOT_STARTED` | `ENTERPRISE_DOCUMENTS_INFORMATION.md` | — | document control, retention |
| 15 | Knowledge and Assistant functional specifications | `NOT_STARTED` | `KNOWLEDGE_ASSISTANT_SPEC.md` | — | sources, topics, cards, translations, publication |
| 16 | AI Workbench acceptance specifications | `NOT_STARTED` | `AI_WORKBENCH_ACCEPTANCE.md` | — | proposal → review → approve → execute → audit |
| 17 | Localization acceptance | `NOT_STARTED` | `LOCALIZATION_ACCEPTANCE.md` | — | ten locales, RTL/LTR, dates and numbers |
| 18 | Final traceability and coverage audit | `NOT_STARTED` | `COVERAGE_AUDIT.md` | — | completeness, gaps, defect index |

## Already existing work this plan builds on

| Artifact | Role | Relationship |
| --- | --- | --- |
| `docs/traceability/README.md` + JSON/CSV/MD | Page ↔ Help index, 68 Engineering + 16 Enterprise rows | Consumed, never duplicated |
| `apps/web/src/traceability.test.ts` | Enforces the JSON contract and route coverage | Left unchanged |
| `docs/qa/*` audits (activities, filters, Gantt, WBS, toolbars) | Implementation audits by area | Read as evidence; this workstream adds Help-based specs and scenarios |
| `docs/governance/CUBI_V1_ACCEPTANCE_MATRIX.md` | Foundation/security acceptance evidence | Read; not extended here |
| `docs/product/CUBI_PAGE_ACCEPTANCE_REPORT.md` | Page acceptance snapshot | Read; report statuses are not re-used as Help verification |
| `docs/ai-workbench/IMPLEMENTATION_STATUS.md` | Agent 1 implementation status | Read; acceptance specs reference it, no edits |
| `scripts/verify_help_traceability.py` | Link/TOC/title verification | New, documentation-only |

## Open coordination items

| Item | Type | State | Note |
| --- | --- | --- | --- |
| #2015 | Issue | open | Engineering Help-to-UI parity specification; this directory supplies the per-page specs and scenarios it asks for |
| #2007 | Issue | open | Help/UI parity architecture; documentation crosswalk is complementary |
| #2019 | Issue | open | Contextual command-assistant support; Section 16 covers acceptance |
| #2090 | Issue | open | AI Workbench studios; Section 16 covers acceptance |
| #2047 | Issue | open | Activity workspace windows; Section 2/3 document expected behavior |
| PR #1985 | PR | open | Governance: Oracle V26 HTML Help canonical; this workstream follows that rule |

No product implementation file is modified by this workstream.

## Section log

| Section | Commit | PR | CI | Merge commit | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 — Foundation | `d27acfc94` | #2106 | green (test 3.11–3.13, typecheck ×4; the two unrelated Vercel projects fail on pre-existing account state) | `99e77d01c` | 84/84 Help rows verified |
| 2 — Workspace and Activities | `82304984f` | #2107 | green (test 3.11–3.13, typecheck ×4; the two unrelated Vercel projects fail on pre-existing account state) | `74370eeca` | 18 Help URLs, 16 User Guide URLs, 11 scenarios |
| 3 — Activity Details and WBS | this PR | this PR | pending | pending | 40 Help URLs, 27 User Guide URLs, 23 scenarios |

## Open gaps

- Sections 4–18 are `NOT_STARTED`; Section 3 is `PR_OPEN`.
- Section 3 records deliberate read-only scopes: activity code assignments, step
  editing, notebook persistence and risk-to-activity assignment are not
  available in the read model, and WBS delete does not cascade activity
  deletion. The UI states these limits; they are gaps, not asserted defects.
- The User Guide exposes stable per-topic URLs, but only sections opened and
  title-matched are cited. Unopened sections are marked
  `HELP REFERENCE NOT YET VERIFIED`.
- Enterprise Help has no page-numbered PDF baseline; row citations use HTML
  only.
- No executed acceptance run is claimed by this workstream. A scenario is
  `TEST_SPECIFIED` until Agent 1's suite or an observed runtime result proves
  it.
