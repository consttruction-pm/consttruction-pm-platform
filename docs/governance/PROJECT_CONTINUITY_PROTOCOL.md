# CUBI Project Continuity Protocol

**Status:** Required workflow for every planning, coding, review, testing and handoff task.
**Effective date:** 2026-10-25
**Repository:** `consttruction-pm/consttruction-pm-platform`

## 1. Read-first order

Before doing work, inspect the current `main` tree and exact commit first, then read:

1. `README.md`
2. This protocol and `docs/governance/PROJECT_STATE_LEDGER.md`
3. The schedule of record for the workstream: `cubisite.xlsx` in the ChatGPT Library for CUBISITE website work; the separately governed Jalal 5 workbook for whole-product V1 work. Never substitute one for the other.
4. The linked GitHub issue(s), latest open PR(s), their current head SHAs, merge state and exact-head checks.
5. The relevant source, tests, configuration and architecture contracts.

If a required artifact is missing or unreadable, record **MISSING / VERIFY** and repair the continuity entrypoint. Do not silently proceed as if the artifact existed.

## 1.1 Mandatory Version 26 Help package for every Qoder instruction

- The authoritative desktop-workspace reference is the **official P6 Professional Help, Version 26**. Its complete HTML Help table of contents is: https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm
- The supporting Version 26 Professional User Guide (HTML) is: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/index.html
- **Every Qoder instruction prepared for CUBI workspace, Activity, WBS, Gantt, menus, dialogs, layouts or scheduling UI must include the complete HTML Help URL above** (and the supporting User Guide URL when useful). Do not send a task instruction with an implicit or unspecified reference version.
- When the instruction is sent to Qoder, the product owner will attach the supplied **815-page Version 26 PDF**. The instruction must explicitly tell Qoder to read both the HTML Help and the attached PDF, inspect the relevant topics in detail, and record the exact topic/page evidence used.
- Version 26 Help governs behavior, menu structure, controls, options, terminology mapping, and acceptance. Older manuals or screenshots (including Version 22 captures) are supplementary visual evidence only; they must not override or define Version 26 behavior. Resolve differences in favor of Version 26 and record the discrepancy.
- If the 815-page PDF is not attached or cannot be read, record **MISSING / VERIFY** for that evidence and do not claim Version 26 parity or close the related acceptance gate.
- Preserve CUBI branding in customer-facing UI. Third-party source names and links belong only in internal engineering traceability records.

## 1.2 CUBI – Complete Visual and Functional Parity Standard

This standard is binding for the Activities workspace and for every statement of
parity across the CUBI workspace programme.

1. **Reference.** Version 26 official Help
   (https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm) plus the
   supplied 815-page Version 26 PDF govern behavior, controls, order, wording and
   acceptance. Older screenshots may inform appearance only.
2. **Real services only.** A capability that has no authoritative service must
   be shown as unavailable with a stated reason. Fabricated records, invented
   dates, fake progress, placeholder charts and enabled-looking controls without
   effect are prohibited.
3. **No premature completion claim.** Until the compliance matrix is complete and
   the 18 mandatory browser scenarios have real screenshots from the built
   preview, the phrases “the shell is complete” and “it matches version 26” must
   not be used.
4. **Status vocabulary (exact).** Every matrix row uses exactly one of:
   **مطابق و تأییدشده**، **پیاده‌سازی‌شده ولی آزمون‌نشده**، **ناقص**،
   **غایب**، **محدودیت مستند و مشخص**.
5. **Change control.** No destructive change, no branch deletion, no force-push
   and no merge to `main` or Production before the tests and visual review are
   approved. Deliver the corrected version in Preview first.
6. **Evidence.** Exact-head CI on the final SHA, real-runtime browser
   verification and before/after screenshots are required. Documentation alone
   earns no implementation credit.
7. **Scope.** Only the Activities window and its direct dependencies: activity
   table, linked Gantt, Activity Details, filters, columns, grouping/sorting,
   timescale, layout options, and the menus/toolbars/context menus/shortcuts
   those surfaces need. Do not change the API, scheduling/CPM core, data model,
   other windows, the main shell or the entry route; do not change Timeline Size
   without documented necessity and approval.
8. **Recording points.** This standard is mirrored in
   `docs/workspace/reference/oracle-p6-reference-index.md` and the master window
   catalogue `docs/workspace/CANONICAL_VISUAL_WORKSPACE_MIGRATION_LEDGER.md`.

## 2. Baseline and evidence

- `main` is the only source of truth for completed implementation. A branch, open PR, issue, design, generated workbook, passing stale run or documentation-only commit is not merged-product completion.
- Record exact branch, base SHA, head SHA and changed paths for every implementation change.
- Verify status checks against the **exact current head SHA** after the last code change. A green check on an earlier commit does not certify later changes.
- Use these states consistently: **Verified on main**, **In progress**, **Audit required**, **Blocked**, **Not implemented**, **Unknown / verify**.
- Do not infer progress from commit, PR, file or issue counts. Do not award implementation credit for documentation, mocks, fixtures alone or an open PR.
- Separate product-scope progress, CUBISITE website progress, source-code implementation and scheduling/calculation conformance. Do not combine their denominators.

## 3. No-regression scope rule

- Work is additive unless the product owner explicitly authorizes a scope change. Preserve all previous acceptance criteria, dependencies, platform targets and calculation rules.
- CUBI V1 includes Web, Desktop and Native Mobile. This CUBISITE schedule controls the website workstream only; it cannot be used to remove or certify Desktop/Mobile scope.
- The Shared Domain/Calculation Core remains the sole authority for scheduling, calendar, resource, cost, progress and EVM calculations. AI and clients must call versioned application contracts; they may not create parallel calculation engines.
- All-language localization, RTL/LTR, Jalali/Gregorian support, offline/online boundaries, access control and user-facing CUBI terminology remain in force.
- User-facing pages/docs must not expose prohibited third-party branding/source names or references; keep technical provenance internal where required.

## 4. Implementation and verification sequence

For each bounded task:

1. Inspect current implementation and the authoritative requirement; identify the actual missing or defective path before editing.
2. Trace inputs → authorization/scope → application service → repository/transaction → authoritative calculation or output → fresh read-back → UI/report.
3. Implement the smallest complete vertical slice. Do not add production-default permissive fallbacks.
4. Add positive, negative, stale-revision, replay/idempotency, tenant isolation, persistence and regression tests as applicable.
5. Run the targeted test locally/in the project environment where available, then run exact-head CI, Client Typecheck, PostgreSQL Integration and end-to-end gates relevant to the changed paths.
6. Review all results; fix failures before opening/advancing a release gate. A missing provider or unsupported operation must fail closed and be clearly surfaced.
7. Update the matching issue/PR and the project ledger with paths, exact SHA, check run URLs/results, remaining gaps, risk and next concrete action.

## 5. Schedule governance

- `cubisite.xlsx` is the CUBISITE website schedule of record in the ChatGPT Library. The 2026-10-25 reconciliation adds AI-C01–AI-C07 without deleting T01–T45 or BUF.
- Schedule weights must total exactly 100.00 points across active capability activities. Risk reserve is tracked separately and earns no product-completion credit.
- Proposed estimates/dependencies/date forecasts for new scope remain **Pending acceptance / rebaseline** until reviewed; keep earned progress at zero for new tasks until code and acceptance evidence qualify.
- Validate formulas, unique activity IDs, dependency references, calendar assumptions, one-person capacity, date forecast and release gates before calling the baseline final.
- Keep CUBISITE and Jalal 5 in distinct workbooks and denominators. If a requirement belongs in both, link the two records explicitly rather than copy numbers across baselines.

## 6. Task closeout and new-session handoff

Every non-trivial task must end by updating `PROJECT_STATE_LEDGER.md` and its linked issue/PR with:
- completed and uncompleted acceptance criteria;
- exact current-main SHA and working branch/head SHA;
- changed files and behavior;
- exact check runs and conclusions;
- persistence/read-back/security/E2E evidence;
- remaining risks and blockers;
- one next action that can be started without re-asking already answered questions.

Never claim work continues in the background. Continue only while tools and current context permit; if blocked, name the specific missing access/artifact/check and leave a reproducible next action.

## 7. Active release gates (2026-10-25)

- #1423 — complete production AI Project Controls Assistant V1.
- #1530 — production AI action authorization, real handlers, durable audit and execution integration.
- #1540 — interactive engineering learning, privacy-safe general knowledge and durable AI memory.
- #1546 — reconcile the new assistant scope into the CUBISITE website schedule.
- #1486 — whole-product Jalal 5 continuity and mandatory Mobile V1 scope.
- #680 — weighted progress must be evidence-based and denominator-consistent.

These are open work unless current GitHub state and exact-main evidence says otherwise.
