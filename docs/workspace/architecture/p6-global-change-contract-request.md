# Contract request — Global Change preview and apply (`p6-global-change-api.v1`)

Status: **REQUESTED — Agent 3 / Shared Core**
Owner of this request: Agent 1 (frontend / workspace integration)
Requested: 2026-11-14
Related audit: UTIL-001 (Global Change preview and apply)

## Why

V26 Global Change (`Tools > Global Change`) is a parameter-based bulk update:
the user builds filter conditions, assigns old-value or arithmetic changes,
previews the affected records and before/after values, and only then applies the
operation. `docs/workspace/architecture/v26-complete-window-component-catalog.md`
§4.18 requires a typed condition builder, IF / THEN / ELSE structure, preview
counts, explicit approval and an immutable audit of actor, revision, timestamp
and before/after values.

CUBI has **no Global Change window, evaluator, preview route, apply route or run
history**. The dialog inventory records it as `Missing`
(`docs/workspace/architecture/workspace-dialog-inventory.md`), and
`src/construction_pm/p6_code_reference.py` (TOOLS-001) explicitly says that no
verified safe evaluator or transaction path was found and that the capability
must not be exposed as complete before it exists and is tested. A search of the
Python package finds no `global-change`, bulk-update or mass-update module and no
route containing `global-change` or `bulk`.

The only authoritative write path that exists is the per-activity one:

- `src/construction_pm/activity_master_repository.py` stores `ActivityMaster`
  rows with a per-record `record_revision` and a project-scoped
  `project_revision`.
- `P6ActivityMasterAPI.update` (`src/construction_pm/p6_activity_master_api.py`)
  requires an integer `expected_revision >= 1` and `PROJECT_WRITE`, and rejects a
  stale record with `REVISION_CONFLICT`.
- `PATCH /api/projects/{project_id}/p6/activities/{activity_id}` is the only
  exposed mutation; there is no batch endpoint.
- Activity writes check that `scope.project_revision` matches the stored WBS
  scope, but they **do not advance the project revision**. A bulk operation that
  routes through them therefore has no single project-level concurrency token
  unless the new service adds one.

Running N independent `PATCH` calls from the browser would not satisfy V26: it
would not be atomic, could partially apply, would lose the before/after audit,
and would let the browser evaluate expressions. The page will not imitate a
preview with client-side math and will not apply through a loop of per-row
writes.

## Requested routes

| Method | Path | Permission | Purpose |
|---|---|---|---|
| `POST` | `/api/projects/{project_id}/p6/global-changes/preview` | `PROJECT_WRITE` | Evaluate a plan and return counts plus before/after rows; never writes |
| `POST` | `/api/projects/{project_id}/p6/global-changes` | `PROJECT_WRITE` | Apply exactly one stored preview atomically |
| `GET` | `/api/projects/{project_id}/p6/global-changes` | `PROJECT_READ` | List immutable run history |
| `GET` | `/api/projects/{project_id}/p6/global-changes/{run_id}` | `PROJECT_READ` | Read one run with its plan and before/after audit |

A viewer sees the window and controls disabled with a localized reason and
receives 403 `GLOBAL_CHANGE_WRITE_NOT_AUTHORIZED` on a direct preview or apply.
Cross-scope calls return `CROSS_SCOPE_ACCESS`.

## Plan payload (preview)

```json
{
  "contract_version": "p6-global-change-api.v1",
  "kind": "global_change_plan",
  "subject": "activities",
  "filter": {
    "match": "all",
    "conditions": [
      { "field": "activity_type", "operator": "equals", "value": "task" },
      { "field": "percent_complete", "operator": "less_than", "value": "100" }
    ]
  },
  "action": {
    "kind": "assign",
    "assignments": [
      { "field": "duration_value", "operator": "add", "value": "2" },
      { "field": "status", "operator": "set", "value": "not_started" }
    ]
  },
  "expected_revision": 7,
  "preview_limit": 50
}
```

### Subjects and fields

- `subject` is `activities` only in this slice. Assignments, resources, WBS and
  relationships are out of scope until their own typed plans exist.
- Filter fields are a frozen whitelist of fields present in the Activity Master
  DTO: `activity_id`, `name`, `short_name`, `activity_type`, `status`,
  `status_code`, `duration_value`, `duration_unit`, `actual_start`,
  `actual_finish`, `remaining_duration`, `remaining_start`, `percent_complete`,
  `percent_complete_type`, `expected_finish`, `planned_finish`,
  `leveling_priority`, `original_duration`, `wbs_id`, `record_revision`.
- Assignment fields are the writable subset: `name`, `short_name`,
  `activity_type`, `status`, `status_code`, `duration_value`, `duration_unit`,
  `actual_start`, `actual_finish`, `remaining_duration`, `remaining_start`,
  `percent_complete`, `percent_complete_type`, `expected_finish`,
  `planned_finish`, `leveling_priority`, `original_duration`, `wbs_id`.
  `activity_id` and `record_revision` are read-only and must be rejected as
  assignment targets.
- An unknown field is rejected, never ignored.

### Operators (typed, no expression language)

| Value type | Filter operators | Assignment operators |
|---|---|---|
| text / enum | `equals`, `not_equals`, `in`, `not_in` | `set` |
| decimal / integer | `equals`, `not_equals`, `less_than`, `less_or_equal`, `greater_than`, `greater_or_equal` | `set`, `add`, `subtract` |
| date / datetime | `equals`, `before`, `on_or_before`, `after`, `on_or_after` | `set`, `add_days`, `subtract_days` |
| boolean | `is_true`, `is_false` | `set` |

- `match` is `all` or `any`. Nested AND/OR groups and IF / THEN / ELSE
  branching are a later revision of the contract; when they arrive they must be
  a typed tree, not a string parsed by an evaluator.
- `add` / `subtract` on a decimal must use exact decimal arithmetic and the same
  precision the field stores. `add_days` / `subtract_days` move calendar days
  only; workday arithmetic is **not** part of this contract because it would
  silently depend on a calendar and change duration semantics.
- No arbitrary Python, JavaScript or SQL is accepted or evaluated. Any
  expression-shaped input is rejected with
  `GLOBAL_CHANGE_EXPRESSION_UNSUPPORTED`.
- An empty `conditions` list is rejected with `GLOBAL_CHANGE_FILTER_REQUIRED`.
  An explicit "all activities" operation needs a separate confirmation flag and
  is not part of this slice.

`expected_revision` must equal the stored project revision. A mismatch returns
`GLOBAL_CHANGE_REVISION_CONFLICT` and evaluates nothing.

## Preview response

```json
{
  "contract_version": "p6-global-change-api.v1",
  "kind": "global_change_preview",
  "run_id": null,
  "preview_token": "opaque-single-use-token",
  "expires_at": "2026-11-14T12:30:00Z",
  "project_revision": 7,
  "matched_count": 42,
  "unchanged_count": 3,
  "affected_count": 39,
  "rows": [
    {
      "activity_id": "A120",
      "label": "Pour slab",
      "before": { "duration_value": "4", "status": "not_started" },
      "after": { "duration_value": "6", "status": "not_started" }
    }
  ],
  "truncated": false,
  "unsupported": []
}
```

- `rows` is capped by `preview_limit` (server maximum 100) and the response sets
  `truncated` when rows were omitted. Counts always cover the whole match set.
- `before` and `after` contain only the assigned fields; the server computes both
  sides. The browser displays them and never derives a value.
- `unsupported` lists conditions or assignments the service refused. A non-empty
  list still returns 200 with counts of the evaluable subset **only if** the
  request asked for partial evaluation; by default a single unsupported item
  fails the whole preview with one of the codes below.
- `preview_token` is opaque, bound to the canonical plan hash, the project
  revision, the authenticated actor and an expiry (default 15 minutes). It is
  single-use and is never derived in the browser.

## Apply payload

```json
{
  "contract_version": "p6-global-change-api.v1",
  "kind": "global_change_apply",
  "preview_token": "opaque-single-use-token",
  "idempotency_key": "7d2c…"
}
```

Required semantics:

- The apply executes **exactly** the stored preview plan. The client cannot
  substitute a different filter or assignment at apply time.
- Before writing, the service rechecks the project revision, every targeted
  activity's `record_revision`, the token expiry and whether the token was
  already used. Any change returns `GLOBAL_CHANGE_PREVIEW_STALE` (409) or
  `GLOBAL_CHANGE_PREVIEW_EXPIRED` (409) and writes nothing.
- All writes happen in one transaction. A failure on any record rolls the whole
  batch back (`GLOBAL_CHANGE_APPLY_FAILED`), with no partial update.
- Writes go through the authoritative activity persistence with each row's
  expected record revision; the service does not bypass the repository.
- The apply advances the project revision exactly once (or records an equivalent
  project-level change token consulted by later writes). Today's per-activity
  path does not advance it, so this is an explicit new requirement rather than
  inherited behavior.
- Idempotency: repeating the same `idempotency_key` with the same plan returns
  the stored run (200, no new writes). Reusing the key with different content
  returns 409 `GLOBAL_CHANGE_IDEMPOTENCY_KEY_REUSE`.
- No undo. V26 permits undo only for a transactionally reversible operation; a
  generic bulk undo is unsafe. The immutable run detail is the supported restore
  path, and a reversal is a new Global Change.
- Audit rows are immutable and stored in the same transaction: run id
  `GCH-<n>`, actor, timestamp, normalized plan JSON and SHA-256, matched /
  unchanged / affected counts, and one entry per changed activity with
  `activity_id`, `before`, `after`, `previous_record_revision` and
  `new_record_revision`.

## Run history response

```json
{
  "contract_version": "p6-global-change-api.v1",
  "kind": "global_change_run",
  "run_id": "GCH-7",
  "status": "applied",
  "actor": "preview-admin",
  "applied_at": "2026-11-14T12:05:00Z",
  "project_revision_before": 7,
  "project_revision_after": 8,
  "plan_sha256": "…",
  "matched_count": 42,
  "unchanged_count": 3,
  "affected_count": 39,
  "entries": [
    {
      "activity_id": "A120",
      "before": { "duration_value": "4" },
      "after": { "duration_value": "6" },
      "previous_record_revision": 2,
      "new_record_revision": 3
    }
  ]
}
```

Reads require `PROJECT_READ` and are ordered newest first. A run is never
deleted or rewritten.

## Failure codes the UI expects

`GLOBAL_CHANGE_CONTRACT_VERSION_UNSUPPORTED`,
`GLOBAL_CHANGE_SUBJECT_UNSUPPORTED`,
`GLOBAL_CHANGE_FIELDS_REQUIRED`,
`GLOBAL_CHANGE_FILTER_REQUIRED`,
`GLOBAL_CHANGE_FIELD_UNSUPPORTED`,
`GLOBAL_CHANGE_OPERATOR_UNSUPPORTED`,
`GLOBAL_CHANGE_EXPRESSION_UNSUPPORTED`,
`GLOBAL_CHANGE_VALUE_INVALID`,
`GLOBAL_CHANGE_TYPE_MISMATCH`,
`GLOBAL_CHANGE_ASSIGNMENT_FIELD_READ_ONLY`,
`GLOBAL_CHANGE_REVISION_CONFLICT`,
`GLOBAL_CHANGE_NO_MATCHES`,
`GLOBAL_CHANGE_PREVIEW_STALE`,
`GLOBAL_CHANGE_PREVIEW_EXPIRED`,
`GLOBAL_CHANGE_PREVIEW_ALREADY_APPLIED`,
`GLOBAL_CHANGE_IDEMPOTENCY_KEY_REUSE`,
`GLOBAL_CHANGE_WRITE_NOT_AUTHORIZED`,
`GLOBAL_CHANGE_APPLY_FAILED`,
`GLOBAL_CHANGE_RUN_NOT_FOUND`.

## What the frontend will do once the contract exists

1. Add `Tools > Global Change` as a first-class workspace window with three
   areas: **Change** (subject, filter rows, action rows, Preview), **Preview**
   (counts, before/after table, truncation and unsupported notices, Apply) and
   **History** (immutable runs with per-activity before/after).
2. Build a typed plan from selectors and text inputs only. The page renders
   field/operator choices from the frozen lists and validates value shape for
   immediate feedback, but the server remains authoritative.
3. Keep Apply disabled until the current preview is clean. A stale-revision,
   expired or already-applied token clears Apply, shows the localized reason and
   requires a new preview. A successful apply shows the run id and reloads the
   activity register from the server.
4. Localize every label, error and disabled reason in en and fa, check RTL at
   1280×720, and state that no expression language is executed.
5. Persist nothing in localStorage; history comes from the run routes.

## Acceptance evidence requested from Agent 3

- Unit tests: field/operator whitelists, read-only assignment rejection, exact
  decimal arithmetic, calendar-day arithmetic, `all`/`any` filters, zero
  matches, truncated previews, preview writes nothing, apply is all-or-nothing,
  stale/expired/already-used tokens, idempotent replay and key reuse.
- Revision tests: preview bound to the project revision; a concurrent activity
  edit invalidates the preview; apply advances the project revision once; audit
  rows match the stored rows.
- Permission tests: `PROJECT_WRITE` for preview/apply, `PROJECT_READ` for runs,
  viewer 403, cross-scope rejection.
- Persistence tests: SQLite and live PostgreSQL readback of runs and audit
  entries, including a forced mid-batch failure that leaves every activity and
  the project revision unchanged.
- A 250-activity fixture proving preview/apply counts and duration, plus a
  larger stress case for the transaction and audit volume.
- A fixture with at least three runs so the browser suite can prove history
  ordering, before/after display and a rejected stale preview in en and fa RTL.
