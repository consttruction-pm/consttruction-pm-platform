# AI Workbench — canonical workspace read and proposal impact review

Date: 2026-11-21
Base commit: `6c25964a4765d583cf267c6fa0c941c7d8589095` (origin/main, PR #2101)
Branch: `feat/cubi-workbench-production-actions`

## Problem

Two real defects were found by reading the canonical contract instead of the
client code:

1. The canonical workspace read (`PersistedWorkspaceReadProvider`) publishes the
   WBS hierarchy under `workspace.wbs_nodes`. The Workbench client read
   `workspace.wbs`, so the Project Analysis panel always reported **0 WBS
   elements** for a project that had stored WBS nodes.
2. The Decision studio listed `activity.create` proposals but showed only the
   raw payload. There was no comparison against the current project state, so a
   planner could not see what the proposal would change before approving it.

Both are read-side defects. No scheduling, cost or earned-value logic was
introduced.

## What changed

### 1. Canonical workspace read (`apps/web/src/workbench`)

- `api.ts`: `WorkspaceReadSnapshot` now types the canonical
  `workspace.activities`, `workspace.wbs_nodes` and `workspace.relationships`
  collections, with `workspace.wbs` kept only as a legacy, optional field.
- `model.ts`: `workspaceWbsNodes(snapshot)` returns `wbs_nodes` and falls back to
  `wbs` only when the canonical field is absent. `analysisCounts` uses it for the
  WBS element count.
- `mount.ts`: the workspace read is loaded once per project revision, deduplicated
  while in flight, and cleared when the server reports a new revision. A failed
  read surfaces `impactError` instead of silently empty data.

### 2. Proposal impact review (`model.ts`, `render.ts`)

`proposalImpact(snapshot, proposal)` builds a **literal** before/after for
`activity.create` only:

| Field | Current state | Proposed change |
|---|---|---|
| Activity ID | existing activity name or "Not present in the current read" | payload id |
| Name | current name | payload name |
| WBS node | current node label | payload node label from `wbs_nodes` |
| Duration | current `cells.duration` | payload duration + unit |

Warnings are emitted by stable code:

- `CURRENT_STATE_UNAVAILABLE` — no canonical read is held;
- `ACTIVITY_ID_EXISTS` — the id already exists in the read;
- `WBS_NOT_IN_CURRENT_READ` — the payload WBS id is not in the current revision.

The panel carries an explicit note that it performs no schedule, cost or
earned-value calculation and estimates no date. Other tools return `null` and
render no impact panel.

### 3. Browser journey

`apps/web/e2e/preview-e2e.mjs` now:

- requires the WBS element count to be **> 0**, read from `wbs_nodes`;
- captures the pending proposal's impact table and warning codes;
- asserts the pending `activity.create` proposal shows "Approval acceptance" and
  the stored WBS node, with no `CURRENT_STATE_UNAVAILABLE` or
  `ACTIVITY_ID_EXISTS` warning;
- records `impact_preview` and `impact_warnings` in `evidence.json`.

## Verification (all run on the branch head)

| Command | Result |
|---|---|
| `cd apps/web && npm run typecheck` | clean |
| `npx tsx --test src/workbench-model.test.ts src/workbench-render.test.ts` | 35 passed |
| `cd apps/web && npm test` | 1292 passed (web) + 16 passed (preview server), 0 failed |
| `cd apps/web && npm run build` | success, bundles emitted |
| `CUBI_CHROME_NO_SANDBOX=1 npm run test:e2e:preview` | passed, 113 recorded checks, 57 screenshots |

E2E evidence (`apps/web/e2e/artifacts/evidence.json`, `git_head`
`6c25964a...`):

- Project analysis: Activities 14, WBS elements 7, Relationships 15,
  Critical activities 7 — the WBS count is no longer 0.
- Decision studio: `status: rejected`, `impact_preview: true`,
  `impact_warnings: []`.

Screenshots: `apps/web/e2e/artifacts/ai-workbench-en.png`,
`ai-workbench-fa.png`.

## Notes and limits

- One earlier E2E attempt failed at the unrelated `schedule flyout opens` step
  (a later navigation journey). A rerun of the same tree passed the full suite;
  the failure is recorded here as a harness flake, not a Workbench defect. No
  code changed for it.
- The impact review is deliberately literal. It is not a simulation and makes no
  claim about downstream schedule, cost or EVM effects. A true impact simulation
  depends on the scenario service (#1989) and a wired schedule publication path,
  which remain separate, tracked gaps.
- The count fix is a read correction only; it does not recompute any stored
  value.
