# Contract request — resource curves and resource shifts

Status: **REQUESTED — Agent 3 / Shared Core**
Owner of this request: Agent 1 (frontend / workspace integration)
Requested: 2026-11-14
Related audit: RES-005 (resource curves, shifts and rates over time)

## Why

RES-005 splits into three capabilities. One of them is implemented:

- **Effective-dated rates** are stored by `p6-resource-rate-fact` and written
  through `p6-resource-rate-write-api.v1`
  (`POST /api/projects/{project_id}/p6/resource-rates`) with append-only
  supersession, overlap rejection, revision checking and authenticated
  provenance. The Resources Rates tab now appends a change through that
  contract and reads the result back from the read API.

The other two capabilities have no stored contract, so the UI cannot offer them
without inventing data:

- **Resource curves.** `src/construction_pm/p6_resource_spread_api.py` persists
  typed spread buckets, but there is no curve library, no curve selection on an
  assignment, and no rule that maps a curve onto future-period buckets.
  `p6_code_reference.py` (RES-006) records the same gap.
- **Resource shifts.** Calendar work-hour rules store detailed intervals and
  reject overlapping windows
  (`src/construction_pm/calendar_work_hours_repository.py`), but there is no
  resource shift master, no resource-to-shift effective assignment, and the
  leveling input contract explicitly lacks shift-aware capacity
  (`p6_code_reference.py`, RES-007). Treating calendar intervals as a resource
  shift would collapse multiple shifts into one default window.

Rates, curves and shifts are separate facts. The UI will not derive one from
another, will not spread assignment demand in the browser, and will not display
a curve or shift editor that cannot persist what it shows.

## Requested — resource curves (`p6-resource-curve-api.v1`)

| Method | Path | Permission | Purpose |
|---|---|---|---|
| `GET` | `/api/projects/{project_id}/p6/resource-curves` | `PROJECT_READ` | List stored curve definitions in scope |
| `POST` | `/api/projects/{project_id}/p6/resource-curves` | `PROJECT_WRITE` | Create or revise one curve definition |
| `GET` | `/api/projects/{project_id}/p6/resource-assignments/{assignment_id}/curve` | `PROJECT_READ` | Read the assignment's selected curve and stored bucket overrides |
| `PUT` | `/api/projects/{project_id}/p6/resource-assignments/{assignment_id}/curve` | `PROJECT_WRITE` | Select a curve or store manual future-period buckets |

### Required semantics

- A curve definition carries an id, a name, an explicit distribution basis and
  either normalized distribution points or a named formula. Distribution points
  must sum to exactly one within the service's declared precision, or the write
  is rejected with a stable code.
- An assignment references a stored curve by id. Selecting a curve recomputes
  nothing in the client; the service owns the bucket mapping.
- Manual future-period bucket overrides are distinguishable from curve-derived
  values in both read and write payloads, and a later curve change must not
  silently overwrite a manual override.
- Every write takes `expected_revision` and returns the stored revision.
  Replaying an identical write is idempotent; divergent content on the same
  identity returns a conflict.
- Bucket values carry an explicit time interval and the hours/units basis.
  `p6_resource_spread_api.py` buckets do not store a width today, so the
  contract must add one (or a linked period definition) before any demand can
  be attributed to a period.

### Failure codes the UI expects

`RESOURCE_CURVE_NOT_FOUND`, `RESOURCE_CURVE_DISTRIBUTION_INVALID`,
`RESOURCE_CURVE_SELECTION_CONFLICT`, `RESOURCE_BUCKET_BASIS_REQUIRED`,
`REVISION_CONFLICT`, `RESOURCE_CURVE_WRITE_NOT_AUTHORIZED`.

## Requested — resource shifts (`p6-resource-shift-api.v1`)

| Method | Path | Permission | Purpose |
|---|---|---|---|
| `GET` | `/api/projects/{project_id}/p6/resource-shifts` | `PROJECT_READ` | List stored shift definitions |
| `POST` | `/api/projects/{project_id}/p6/resource-shifts` | `PROJECT_WRITE` | Create or revise one shift definition |
| `GET` | `/api/projects/{project_id}/p6/resource-shifts/{resource_id}` | `PROJECT_READ` | Read a resource's effective-dated shift assignments and capacity |
| `PUT` | `/api/projects/{project_id}/p6/resource-shifts/{resource_id}` | `PROJECT_WRITE` | Assign shifts to a resource for an effective interval |

### Required semantics

- A shift definition carries an id, a name, a time zone, working intervals per
  weekday, and a bound `calendar_id` + `calendar_version`. It is versioned like
  other calendar facts.
- A resource-shift assignment is effective-dated and stores the units or hours
  of capacity available in that shift. Overlapping assignments for the same
  resource must be rejected with a stable code instead of being summed.
- Capacity is time-zone-aware. The service, not the browser, converts a shift
  window to the demand's basis and hours definition.
- Leveling input must consume the stored shift facts. It must not collapse two
  shifts into one default calendar window or aggregate overlapping shift
  capacity twice.
- Every write takes `expected_revision`; stale writes return `REVISION_CONFLICT`
  and mutate nothing.

### Failure codes the UI expects

`RESOURCE_SHIFT_NOT_FOUND`, `RESOURCE_SHIFT_INTERVALS_OVERLAP`,
`RESOURCE_SHIFT_CALENDAR_NOT_FOUND`, `RESOURCE_SHIFT_TIME_ZONE_INVALID`,
`RESOURCE_SHIFT_CAPACITY_BASIS_REQUIRED`, `REVISION_CONFLICT`,
`RESOURCE_SHIFT_WRITE_NOT_AUTHORIZED`.

## What the frontend will do once the contracts exist

1. Render a **Curves** control on the assignment and a **Shifts** tab on the
   resource, both reading only stored facts and both fail-closed when a fact is
   missing.
2. Submit changes through `p6-resource-curve-api.v1` /
   `p6-resource-shift-api.v1` with the project revision, then reload and verify
   the read-back instead of patching the local row.
3. Show rejection codes verbatim (`RESOURCE_CURVE_DISTRIBUTION_INVALID`,
   `RESOURCE_SHIFT_INTERVALS_OVERLAP`, `REVISION_CONFLICT`) in en and fa.
4. Keep demand, availability and excess display tied to the service-resolved
   facts; no curve or shift calculation will run in the page.

## Acceptance evidence requested from Agent 3

- Repository round-trip tests for curve definitions and assignment curve
  selection, including manual bucket overrides surviving a curve change.
- Overlap, stale-revision, idempotent-replay, permission and cross-scope tests
  for both routes.
- A leveling input test proving two shifts of one resource are not collapsed
  into the default calendar and do not double-count overlapping capacity.
- A fixture that lets the browser suite verify one curve-derived bucket series
  and one shift-aware capacity series end to end.
