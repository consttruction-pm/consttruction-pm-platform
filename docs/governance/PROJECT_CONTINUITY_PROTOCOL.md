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
