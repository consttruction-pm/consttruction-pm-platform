# CUBI full-stack local preview

This document describes the real, reproducible local preview used to inspect the
CUBI Web workspace against the real WSGI API, SQLite persistence and the Shared
Domain/Calculation Core. It is **not production**, it uses **demo data only**, and
no external preview has been published.

## Status and external blocker

- External preview: **not available**. The GitHub repository reports
  `has_pages=false`; there is no GitHub Pages site to update. No deployment was
  performed. The local preview below is the inspectable replacement.
- A production login route does not exist in the product. The preview adds a
  loopback-only demo identity page; it is not a production credential system.
- The CUBISITE workbook is not present in the repository, so official
  weights/completion percentages are not available and are not invented here.

## One command

```bash
cd apps/web
npm install          # first run only
npm run preview:full
```

Then open:

- Login: <http://127.0.0.1:4174/preview/login>
- Workspace: <http://127.0.0.1:4174/app>
- Health: <http://127.0.0.1:4174/preview/health>
- Landing page: <http://127.0.0.1:4174/>

`preview:full` builds the Web client with the repository TypeScript toolchain,
then starts the Python preview composition. It uses `py -3` on Windows and
`python3` elsewhere; set `CUBI_PYTHON` to override the interpreter.

Equivalent direct command from the repository root:

```bash
PYTHONPATH=src py -3 -m construction_pm.preview --web-root apps/web --port 4174
```

Add `--reset` once to rebuild the guarded demo database (the previous database is
backed up under `.preview/backups/`). Without `--reset`, saved layouts, settings
and sessions continue across restarts; in-memory demo sessions are recreated when
the process restarts.

## What is real in the preview

| Layer | Implementation |
| --- | --- |
| Web client | Built CUBI Web assets (`apps/web/dist/...`) served by the preview. |
| HTTP | Real `ProjectLifecycleWsgiApp` routes, not a mock server. |
| Persistence | Real SQLite repositories for activities, relationships, calendars, settings, layouts, field registry, UDFs, snapshots and the mapping registry. |
| Calculation | Published immutable snapshot + `POST /api/v1/schedule/query` through the Shared Domain/Calculation Core. Dates, float and critical flags are not computed in the browser. |
| Presentation | Persisted `p6-layout.v1` revisions and `p6-field-registry.v1` fields; optimistic layout revisions. |
| Resource capacity | Typed effective-dated Resource Max Units/Time persisted per tenant/project/revision through `SQLiteP6ResourceCapacityRepository`; read through `GET /api/projects/{project}/p6/resource-capacities[/{resource_id}]`. Ceilings come from explicit fixture segments, never from assignment `units_per_time` or a calendar default. |
| Interchange | Real provider XML codec and persisted mapping registry through `POST .../p6/interchange/PRIMAVERA_XML/{export,import}`. |
| Sessions | In-memory opaque demo sessions (8-hour TTL), server-enforced role policy. |
| Dates | Schedule dates are stored and calculated as canonical ISO Gregorian values. The workspace calendar-mode toggle renders Jalali labels with a UTC-based presentation conversion only; stored and calculated dates do not change. |
| Database safety | The preview refuses foreign/stale SQLite files and rebuilds only its own application ID, marker and seed version. |

Only the guarded demo database, demo identities and curated fixtures are
preview-specific. Scheduling and authorization decisions remain in the product
code paths.

## Demo identities

The login page offers three fixture-only identities. Roles are enforced by the
real authorization policy after login:

| Identity | Role | Expected behavior |
| --- | --- | --- |
| `preview-planner` | planner | Read, save layout/settings, publish snapshots, import exchange data. |
| `preview-viewer` | viewer | Read-only; layout/settings writes, snapshot publication and import return 403. |
| `preview-admin` | project administrator | Planner capabilities plus project creation where the Web exposes it. |

The fixed banner on every authenticated page reads
`LOCAL PREVIEW · DEMO DATA · NOT PRODUCTION` and identifies the signed-in demo
user. There is no password, no production identity and no external service call.

## Reproducible fixture data

The fixture is defined in `src/construction_pm/preview/fixtures.py`.

| Project | Revision | Activities | Calendar | Data date | Notes |
| --- | --- | --- | --- | --- | --- |
| `preview-rps-01` — Riverside Pump Station Upgrade | 7 | 14 | `CUBI-RPS-CAL`, Monday–Friday, Gregorian, holiday 2026-10-28 | 2026-10-12 | Project start 2026-09-21; A130 is in progress at 2026-10-07 with 37.5% complete; seven critical activities in the fixture output. |
| `preview-nse-02` — نوسازی سامانه شرقی | 2 | 6 | `CUBI-NSE-CAL`, Saturday–Wednesday, Jalali, one recorded Jalali holiday | — | Persian activity/WBS labels and a Jalali calendar system. |

RPS relationships include FS, SS with working-day lag and a fan-out from A130.
The seeded snapshots are published through the same snapshot publisher used by
the product, so the workspace/Gantt reads persisted schedule facts and the run
panel re-publishes and re-queries the current saved state.

RPS also seeds two registered capacity segments for `RPS-CIVIL-CREW`: 8 units/day
through 2026-10-14 and 12 units/day from 2026-10-15 onward, with explicit 8
hours/day and fixture sources. NSE seeds 4 units/day for `NSE-DESIGN-TEAM`.
The create-project form creates an empty project with the curated 20-field
catalogue (10 visible columns by default), a revision-1 layout, a default
calendar and no invented activities or capacity.

## Automated verification

Run the repository browser E2E (Chrome or Edge must be installed; set
`CHROME_PATH` if the browser is not in a standard location):

```bash
cd apps/web
npm run test:e2e:preview
```

The script starts an isolated preview on a random loopback port with a temporary
SQLite database and a real headless browser. It verifies:

- health identity, landing page, unauthenticated `/app` redirect and session 401;
- the three demo personas and planner project selection;
- menus/submenus, persisted grid rows, Gantt rows and shared grid/Gantt selection;
- column hide/remove/add/reorder/width/pin/freeze through the real layout API,
  followed by a full reload and read-back;
- filter and numeric sort behavior, including an explicit empty state;
- project settings/calendar read, save and revision increment;
- snapshot publication plus Shared Core query results and content hash;
- typed resource capacity read, effective-dated profile, day→week conversion with
  an explicit 40 h/week factor, distinct immutable identities and a fail-closed
  404 for an unregistered resource;
- provider XML export/import round-trip through persisted mappings;
- Jalali/Gregorian display toggle: 2026-10-07 renders as ۱۴۰۵/۰۷/۱۵ and the stored
  ISO value is unchanged when switching back;
- Persian RTL labels/filter with the persisted project;
- a 1024×768 compact desktop layout with navigation inside the viewport;
- saved settings/calendar/layout after a full reload;
- logout, `/app` guard, viewer read-only session, 403 write denials and an explicit
  failed-calculation message with zero fabricated result rows;
- admin-only project creation from the Web form, persisted project name, empty
  activity grid and curated layout;
- no uncaught browser exceptions and no API 5xx responses.

The latest isolated run recorded **24 checks and 12 screenshots**.

Artifacts are written to `apps/web/e2e/artifacts/` (gitignored):
`01-login.png` through `12-admin-project-created.png`, the preview server log and
`evidence.json`.

Fast backend checks for the preview composition:

```bash
PYTHONPATH=src py -3 -m pytest tests/test_preview_runtime.py -q
```

They prove the foreign-database guard, real calculated reads and revision
conflict, login/banner/static/logout behavior, layout persistence across a runtime
restart, viewer write denial, the interchange round-trip, registered-capacity
effective-date reads across restart and admin project creation with a consistent
initialized workspace.

## Manual walkthrough

1. Open `/preview/login` and choose **Planner**.
2. Select **Riverside Pump Station Upgrade**; inspect the activity grid and Gantt.
3. Hide, add, reorder, resize, pin or freeze columns; reload and confirm persistence.
4. Filter by `civil` or `civil completed`; sort by Id or Total Float.
5. Toggle **Jalali** and confirm dates change for display only; toggle back.
6. Open **Schedule → Schedule settings**, confirm `CUBI-RPS-CAL` and save.
7. Open **Schedule → Run Schedule** and compare the returned A130 dates, float,
   critical flag and snapshot hash.
8. Read the seeded capacity through
   `GET /api/projects/preview-rps-01/p6/resource-capacities/RPS-CIVIL-CREW`
   (planner session, scope headers); confirm the 2026-10-15 basis change and that
   an unregistered resource returns 404 `RESOURCE_CAPACITY_NOT_REGISTERED`.
9. Switch the top-right language control to Persian and confirm RTL labels.
10. Sign out, sign in as **Viewer**, and confirm writes fail explicitly while reads
    remain available.
11. Sign out, sign in as **Admin**, create a project from the project-selection
    form, and confirm the new empty workspace, curated layout and persisted name.

## Known limitations

- No external preview URL/deployment is available; GitHub Pages is not enabled for
  this repository.
- Import/export is exposed and tested at the authenticated API level. A dedicated
  Web import/export screen is not implemented yet.
- Jalali dates are rendered through the display toggle; typed Jalali date entry in
  workspace controls is not implemented yet.
- The WBS surface is a flat persisted WBS grouping, not a hierarchy editor.
- Typed Resource Max Units/Time is implemented as domain + persistence + read API
  and seeded in the preview. A capacity-editing panel in the Web UI is not
  implemented yet; the API remains the authoritative surface.
- Assignment-level early/late dates and backward placement are not exposed; the
  placement module documents this contract boundary and the activity-level Shared
  Core result remains authoritative.
- CUBISITE workbook-derived official weights, scoring or completion percentages
  are unavailable and must not be inferred from file counts.
