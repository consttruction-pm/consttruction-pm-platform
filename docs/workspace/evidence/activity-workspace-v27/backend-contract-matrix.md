# V27 Backend Contract Matrix — Activities Workspace

- Tested head: `b71cd61f46ebe358d1b15eee21068977b03493cf`
- Backend: local full-stack preview (`construction_pm.preview`) over the real WSGI
  API, SQLite repositories and Shared Domain core. No production database and no
  external deployment were touched.
- Principle: the browser never invents an endpoint or derives scheduling facts.
  Every write carries authentication/scope and a revision guard where applicable.

## 1. Read contracts used by the Activities workspace

| Contract | Method / path | Notes | Status |
|---|---|---|---|
| Workspace control-room read | `GET /api/v1/workspace/control-room/read` | Returns activities, columns, WBS nodes, Gantt facts, scope headers (`X-Tenant-Id`, `X-Project-Id`, `X-Project-Revision`) | **مطابق و تأییدشده** |
| P6 field registry | `GET /api/projects/{id}/p6/fields/p6-field-registry.v1` | Flat DTO `fields[].field_id`; includes `activity.percent_complete_type` (`enum`, writable) | **مطابق و تأییدشده** |
| Project layout | `GET /api/projects/{id}/p6/layouts/project/activity` | Persisted columns incl. hidden `activity.percent_complete_type`; revision returned | **مطابق و تأییدشده** |
| Activity master record | `GET /api/projects/{id}/p6/activities/{activityId}` | Revision-bearing record for the General editor | **مطابق و تأییدشده** |
| Activity steps | `GET /api/projects/{id}/p6/activities/{id}/steps` | Read-only list | **مطابق و تأییدشده** (read) |
| Progress history | `GET /api/projects/{id}/p6/activities/{id}/progress-history` | Read-only history | **مطابق و تأییدشده** |
| Resource capacities / rates | `GET /api/projects/{id}/p6/resource-capacities` (+ rate facts) | Effective-dated facts, no derivation | **پیاده‌سازی‌شده ولی آزمون‌نشده** in V27 |
| Health | `GET /preview/health` | Runtime and seed facts | **مطابق و تأییدشده** |

## 2. Write contracts

| Contract | Method / path | Guard | Status |
|---|---|---|---|
| Activity General edit | `PATCH /api/projects/{id}/p6/activities/{activityId}` | `expected_revision`; only changed fields; 409 on stale | **مطابق و تأییدشده** (V27 suite) |
| Layout save | `PUT` layout endpoint | Layout revision guard | **مطابق و تأییدشده** (`layout-selector-v26`) |
| Relationship create/remove | Relationship endpoints | Project revision | **مطابق و تأییدشده** (`activity-relationships-v26`) |
| WBS mutations | WBS endpoints | Project/WBS revision | **مطابق و تأییدشده** (`wbs-*` suites) |
| Assignment periods | Assignment endpoints | Project revision | **پیاده‌سازی‌شده ولی آزمون‌نشده** in V27 |
| Expenses / Issues | Their endpoints | Record revision | **پیاده‌سازی‌شده ولی آزمون‌نشده** in V27 |
| UDF values | UDF endpoints | Subject record revision | **پیاده‌سازی‌شده ولی آزمون‌نشده** in V27 |
| Project status / metadata | Project endpoints | `expected_revision` | **پیاده‌سازی‌شده ولی آزمون‌نشده** in V27 |

## 3. V27 read-model change — `activity.percent_complete_type`

| Layer | Change | File | Verification |
|---|---|---|---|
| Field registry | Field already existed: `("activity.percent_complete_type", …, "enum", writable)` | `src/construction_pm/p6_field_registry.py` | Registry API returns the field |
| Read model | Emit `"activity.percent_complete_type": _enum_text(...)` in each activity's `cells` | `src/construction_pm/backend_p0/workspace_read_provider.py` | `tests/backend_p0/test_workspace_read_provider.py` asserts `DURATION` |
| Preview seed | Curated field added to `CURATED_FIELD_IDS`; hidden layout column added after `is_critical` | `src/construction_pm/preview/fixtures.py` | Preview read returns 21 columns; column visible after Columns dialog |
| Preview runtime test | Column count 20 → 21 with label/type assertions | `tests/test_preview_runtime.py` | 30 passed with provider suite |
| Browser | Columns dialog toggle, header, stored cell, reload persistence | `e2e/activity-percent-complete-v27.mjs` | Passed at `b71cd61f4` (`DURATION`, index 8, restored) |

The field is stored per project revision in `activity_master.percent_complete_type`
and read through the real repository. No browser-side default is applied.

## 4. Grid refresh after a Details save

| Aspect | Implementation | Verification |
|---|---|---|
| Trigger | `onActivitySaved` callback from the General editor after a successful PATCH | `activity-general-edit-v26` |
| Action | Re-read the project through `WorkspaceReadClient` + `loadP6Presentation` | Grid row shows the saved name after the save (`gridRefresh.refreshed = true`); code path reviewed |
| Context preservation | Active window, locale and selected activity retained; confirmation re-applied | Details pane shows the new name; suite's `gridRefresh.refreshed = true` |
| Failure path | Sets `data-activity-refresh-error` on the status bar instead of silently leaving stale data | Code review; no forced failure test |
| Duplicate engine | None; dates and float remain from the server read model | `activities-v26-scenarios` integrity checks |

## 5. Gaps (classified, with owners)

| ID | Classification | Detail | Owner / next action |
|---|---|---|---|
| R4 | CONTRACT/API GAP | Activity Codes: `SQLiteP6CodeAssignmentRepository` and `P6CodeAssignmentAPI` exist, but there is **no HTTP route**; deletion is not supported. The Codes tab is read-only. | Platform: expose assign/remove endpoints with revision guard; UI wiring follows. |
| R5 | CONTRACT/API GAP | Notebook: no persisted topic service. The Comments rail is browser-local. | Platform: define notebook topic CRUD, then wire the Notebook tab. |
| R6 | CONTRACT/API GAP | Steps: repository supports upsert, but only `P6ActivityStepReadAPI` is exposed. | Platform: add step create/update/delete routes; no UI before that. |
| R7 | CONTRACT/API GAP | Documents: no per-activity document association route. | Platform: define the link contract. |
| R8 | OFFICIAL REFERENCE UNAVAILABLE | HTML Help 403 today; PDF missing. | Supply the PDF or enable Help access. |
| R9 | ENVIRONMENT LIMITATION | Full Python collection imports POSIX-only `resource` and `pypdf` is absent on this Windows host; one Vercel path test assumes POSIX `/tmp`. Four unrelated tests fail for these reasons. | CI environment with the intended dependencies; not changed in this PR. |

## 6. Boundaries respected

No change was made to Scheduling Core, CPM, calendars computation, float/critical
path, leveling, EVM/cost, database schema/migrations, identity/tenant authorization
or production composition. The only shared read-model change is the additive
`activity.percent_complete_type` cell; the only shared shell change is the
save-refresh wiring and the workspace CSS floor (disclosed in the PR).
