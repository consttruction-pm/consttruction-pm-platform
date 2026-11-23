# CUBI Reference Workspace — Phase 1 audit (verified on `main`)

Status date: 2026-11-23
Base commit: `e75623a6` (`feat(import): persist, calculate and connect the three DEMO reference projects (#2124)`)
Scope: read-only inspection of the merged import, persistence, repository, schedule and
Enterprise contracts. No production data, schema or identity was changed by this audit.

This record exists so the next slices are built on observed behaviour rather than on the
earlier plan. Every statement below was checked against the code in this repository; when a
claim could not be checked, it is listed as *not verified* instead of assumed.

---

## 1. What is already true

| Fact | Evidence |
| --- | --- |
| Three reference projects are imported from a frozen, hashed bundle, not from fixtures | `src/construction_pm/importing/reference_persistence.py` (`load_bundle`, `ensure_reference_projects`); bundle `importing/data/cubi_reference_projects.v1.json.gz`, contract `cubi-reference-import-bundle.v1`, workbook sha256 `0848454d…fa26` |
| Per-project rows: 180 activities, 238 relationships, 129 WBS nodes, 3 calendars, 40 resources, 240 assignments, 180 baseline activities, 180 progress rows | `tests/test_reference_persistence.py`, `tests/test_reference_api.py` |
| The importer calls the canonical engine (`evaluate_schedule_snapshot`) and records a run manifest (`cubi_reference_schedule_run`) with engine version, options, input/output hash, status, duration | `reference_persistence.py` (`ScheduleRunManifest`, `_record_run`) |
| EVM is measured through the canonical `P6EarnedValueReadModelService` over HTTP, not recomputed in the UI | `tests/test_reference_api.py::test_each_reference_project_measures_earned_value_over_http` |
| Engineering, Enterprise registers, Assistant and the workbench read the same project ids | `tests/test_reference_api.py`, `docs/engineering/CUBI_REFERENCE_PROJECTS_IMPORT_MAPPING.md` §11 |
| Personal Workbench is the signed-in landing route and `/workbench*` is served by the app shell | `apps/web/vercel.json` rewrites, `tests/test_vercel_entrypoints.py` |

## 2. Where the reference data lives today

The importer is wired **only** into the preview runtime:

* `src/construction_pm/preview/runtime.py:1197` (seed) and `:1578` (open) are the only callers of
  `ensure_reference_projects`.
* The preview store is SQLite (`preview/storage.py`, `PreviewStore`, `preview_project*` tables).
* The PostgreSQL production runtime (`deployment/production_runtime.py`,
  `deployment/migrations.py`) does **not** import the reference bundle, so the three projects
  are absent from PostgreSQL and from every production-only API.

Consequence: the reference workspace is currently a **preview-only** capability. This is
acceptable for the test workspace, but it does not yet satisfy "registered in PostgreSQL" and
"survives deploy and restart" for the operational environment.

## 3. Fixture-only and preview-only paths (checked)

| Path | Behaviour today | File |
| --- | --- | --- |
| Session bootstrap | Any cookie-less non-`/preview` request is given a fresh demo session with role `planner` | `deployment/vercel_preview.py:199-207` |
| Demo identities | `planner`, `viewer`, `admin`, `enterprise`, `newcomer` only | `preview/storage.py` (`DEMO_USERS`) |
| Reference membership | Only `DEMO_PROJECT_MEMBER_USER_IDS` (all personas except `newcomer`) are added as members; membership is the only visibility gate | `preview/runtime.py:1162`, `:1201`, `:1582` |
| Member administration | No HTTP route creates, changes or revokes a project membership; the role/expiry columns the mission needs do not exist | `application/project_lifecycle.py`, `preview/storage.py` (`preview_project_member`) |
| Reviewer / Test Operator roles | No such role token exists; `default_role_permissions()` defines only viewer, planner, project_admin | `application/authorization.py` |
| Grant semantics | `enterprise_*` grants exist in the Enterprise store but are not consulted by the project lifecycle policy | `enterprise_workbench_http.py`, `application/authorization.py` |
| Enterprise portlets / portfolio / EVM | Unconditional `503 ENGINEERING_SOURCE_NOT_CONNECTED` | `enterprise_workbench_http.py:790-791` |
| Scenario service | Contract types only; the AI Workbench studio is composed with `scenario_service=False` and renders BLOCKED | `control_intelligence/scenario.py`, `ai_workbench/studios.py:47` |
| Production schema | 12 ordered steps; next free version is 13; no down steps by policy | `deployment/migrations.py` (`PRODUCTION_STEPS`) |
| SQLite-only importer details | `sqlite3.Connection` type check, `sqlite_master`/`PRAGMA` probes, `json_extract`, `?` placeholders, ad-hoc marker tables | `importing/reference_persistence.py`, `importing/reference_enterprise.py` |

## 4. Data decisions re-verified

The import mapping document records the decisions applied by the importer. Independently
re-read in code:

1. **Activity durations** come from the workbook's *Original Duration* in days and are
   converted with the project calendar; no duration is defaulted.
2. **Physical percent complete** is taken from the *Activity Progress* sheet; duration percent
   complete is derived by the engine, never stored as an independent value.
3. **Calendar** workweeks and exceptions are resolved through the calendar registry
   (`build_calendar_registry`), not a fixed five-day default.
4. **Data date** is pinned to the workbook status date (`2026-11-22`) for every reference run.
5. **EVM** is computed by the canonical read model from baseline + progress + cost; the import
   does not store PV/EV/AC.
6. **Resource assignments** are stored as rows; remaining units/costs are recomputed, not copied.
7. **Baseline** is a stored baseline with 180 baseline activities per project; EVM requires an
   explicit `baseline_id` and `data_date`.

Read-only re-execution confirmed three distinct run ids and three distinct output hashes, so the
projects are not copies of one another.

## 5. Gaps this mission must close, in priority order

1. **Access control.** Add Viewer / Reviewer / Test Operator semantics, make the shared reference
   dataset readable by every authenticated user without copying it, and keep it read-only for
   project roles so a reviewer cannot alter source data. Reviewer accounts and grants must be
   created by an administrator on the normal login path — no parallel reviewer login.
2. **PostgreSQL persistence.** Register the reference tables in the migration registry, make the
   importer connection-agnostic and transactional, add the PostgreSQL repository composition and
   prove SQLite↔PostgreSQL manifest equality.
3. **Scenario service.** One canonical scenario service branching from a pinned project revision,
   with its own revision, change set, run id, approval, apply-with-conflict and audit.
4. **Scenario UI** in the AI Workbench and Personal Workbench using that one service.
5. **Enterprise integration.** Replace the unconditional portlet/portfolio/EVM 503 with the
   existing read models; keep the canonical Engineering services authoritative.
6. **Assistant integration** and **full 22-path browser acceptance**.

## 6. Honest non-claims

* No reviewer account can be created yet; this audit changed no behaviour.
* The reference projects are not in PostgreSQL yet.
* No scenario can be created, compared or applied yet.
* Enterprise portlets, portfolio and EVM still return `ENGINEERING_SOURCE_NOT_CONNECTED` on the
  Enterprise HTTP surface.
* The preview auto-session remains writable for the `planner` persona until the access slice
  lands; that is why access control is the first implementation slice.
