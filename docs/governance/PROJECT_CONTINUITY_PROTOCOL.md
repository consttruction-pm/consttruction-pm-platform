# Project Continuity Protocol — Mandatory Read-First Workflow

**Status:** proposed on the Jalal 5 governance PR; becomes the repository's canonical workflow when merged.  
**Decision gate:** [Issue #1486](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1486).  
**Last reviewed:** 2026-10-18.

## Purpose

Prevent decision loss, repeated discovery, scope drift, unsupported progress percentages and team members working from different assumptions. Chat history and a model's recollection are helpful context, but they are not the system of record. GitHub is.

## Required start-of-session / start-of-task checklist

Before any planning, implementation, review, testing, prioritization, assignment or progress report, every human/AI contributor must:

1. Read the repository `README.md`, this protocol, and [Project State Ledger](PROJECT_STATE_LEDGER.md).
2. Read the current Jalal 5 master weighted schedule and its authoritative workbook. If the workbook is stored in the user's Library or another location rather than in the repository, locate and read that exact artifact; never assume its cells match the Markdown schedule.
3. Verify the current `main` SHA and inspect relevant open/closed GitHub issues, PRs, PR review comments, and check runs. In particular, check [Issue #1486](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1486), the Jalal 5 PR, and any blocker linked from the ledger. Use current GitHub evidence, not old message timestamps.
4. Resolve conflicts in favor of the latest explicit product-owner decision recorded in GitHub. **Native Mobile is mandatory in V1** per Issue #1486; any document or workbook that says Mobile V2 is stale and must be corrected.
5. State a short preflight in the work record: current-main SHA; task/issue ID; source docs read; current PR/check evidence; scope and acceptance criterion; known unknowns. If a required file, test, or connector result is unavailable, mark it `BLOCKED / UNKNOWN` and explain why before claiming progress.

Do not start coding or give a progress percentage before this checklist. If the required current evidence cannot be fetched, work may continue only on clearly bounded read-only investigation; implementation acceptance remains blocked.

## Repository templates and review controls

- New work, blockers, and material decisions should use [the Jalal 5 issue template](../../.github/ISSUE_TEMPLATE/jalal5_task.yml) so activity ID, owner/reviewer, canonical sources, predecessor impact and Definition of Done are captured before work starts.
- Implementation/documentation changes should use [the required PR checklist](../../.github/pull_request_template.md) to record preflight, exact SHAs, test/runtime evidence, workbook impacts and reviewer disposition.
- These templates reduce omissions but do not mechanically prove that someone read the source documents. A reviewer must verify checkboxes and linked evidence; branch protection/required checks would need separate repository administration if later desired.

## Authoritative record hierarchy

1. Latest explicit product-owner decision in a GitHub issue/change request.
2. Accepted repository decision/architecture documents on `main`.
3. Current Jalal 5 master schedule **and its updated workbook together** for task IDs, weights, predecessors, owners, dependencies and forecast.
4. Merged implementation plus fresh checks and accepted runtime/behavior evidence.
5. Open PRs, local analysis, chat messages and historical reports are proposals/context only; they do not supersede higher levels or earn product-completion credit.

A draft PR is not an accepted baseline. Until its changes merge, clearly distinguish `main` state from proposed branch state.

## Recording every decision and activity

- Every material product, architecture, calculation-semantic, schedule, weight, priority, V1/V2 or team-ownership decision must be recorded in a GitHub issue or a linked version-controlled decision record. Include date, decision owner/approver, problem, chosen option, alternatives considered where relevant, scope/weight/dependency/forecast impact, acceptance criteria and the previous decision being superseded.
- Never silently edit away a previous decision. Mark it superseded and link the replacement issue/record.
- Every scheduled activity must have a stable activity ID in the authoritative workbook and a linked GitHub issue/PR. Record owner, status, predecessors, estimate, definition of done, evidence URL and affected code/document paths. If a work item does not yet have an ID, create/assign one before treating it as scheduled work.
- Each implementation claim must identify the merged commit SHA, relevant tests/check-run links and runtime/acceptance evidence. Re-run or confirm checks for the exact candidate SHA. Stale check runs, open PRs, docs, comments, screenshots, mocks or a green result on a different SHA are not completion proof.
- Weight changes, added scope and material dependency changes require recalculating the workbook's 100.00-point total, predecessor validity, owner lanes and forecast. Never invent a weight to make a total look complete.
- Update the ledger and linked issue/PR at each meaningful handoff: what changed, where, exact SHA, verification result, current status, unresolved risks and the next concrete action.

## Required status vocabulary

Use one of the following and apply it consistently:

- **DECIDED** — explicit owner decision recorded; not necessarily implemented.
- **PLANNED** — accepted or proposed schedule row exists; not implementation evidence.
- **IN PROGRESS** — work has started; no completion credit yet.
- **BLOCKED** — a dependency, missing file, scope decision or verification is preventing acceptance.
- **IMPLEMENTED — UNVERIFIED** — candidate code exists but required checks/evidence are not all accepted.
- **MERGED — VERIFYING** — code is on main; required fresh verification or acceptance remains.
- **ACCEPTED** — current-main code, required exact-SHA CI/tests, runtime/behavior acceptance and traceability are all recorded.
- **SUPERSEDED** — replaced by a later linked decision; retain the historical record.

Overall weighted progress may rise only from the workbook rows whose Definitions of Done are met and whose acceptance evidence is current and linked. Report documentation/planning maturity separately from product implementation progress.

## Required end-of-session handoff

Before ending a task, update [Project State Ledger](PROJECT_STATE_LEDGER.md) in the same governed PR or a follow-up PR. Record:
- current-main SHA and proposed branch/PR SHA separately;
- completed, in-progress, blocked and next activity IDs;
- issues/PRs touched and their state;
- files/paths changed;
- exact CI/test/runtime outcomes, including failures and skipped gates;
- decisions made or superseded, with issue links;
- workbook/weights/forecast update state;
- the single next actionable step.

Never say "done", "fixed", "merged", "tested" or quote a new percentage unless the linked evidence supports that exact claim.

## Responsibility

All contributors follow this protocol, including Jalal, Hasan, Farmj and reviewers. The task owner must update the source record; the reviewer independently checks evidence. The coordinator must verify, not assume, that other team members have read the latest decision. If an automated PR template or CI enforcement is later added, it supplements rather than replaces this workflow.

## Important limitation

A Markdown instruction cannot technically force a separate ChatGPT conversation to load itself automatically. The practical guardrail is to keep this file linked from the root README and agent instructions, maintain the state ledger, and make the first step of every new CUBI task to read them from the repository before using conversational context.