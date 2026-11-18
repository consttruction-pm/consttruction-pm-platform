# Activity Details General tab - Version 26 edit path

- Tested code: `554b0c7417101a6a290e3c1a7c0cbb24038c584f`
- Captured: 2026-11-18T02:11:51.411Z
- Environment: managed Python preview runtime, SQLite demo project, headless Chrome, English 1366x768
- Activity: A100

## Verified

- The General editor reads the authoritative Activity Master record before opening; the loaded revision is shown to the user.
- Activity Type exposes the six Version 26 values: Task Dependent, Resource Dependent, Level of Effort, Start Milestone, Finish Milestone, WBS Summary.
- Duration Type exposes the four Version 26 values: Fixed Units/Time, Fixed Duration & Units/Time, Fixed Units, Fixed Duration & Units.
- Percent Complete Type exposes: DURATION, UNITS, PHYSICAL, SCOPE.
- Saving sends a PATCH that carries `expected_revision` and only the changed field.
- The saved name repaints in the details pane and survives a full page reload.
- The original name was restored at the end of the run so the shared preview database is unchanged.

## Not verified in this run

- Version 26 visual side-by-side screenshots of the General tab; the run records CUBI states only.
- Changing Activity Type or Duration Type was exercised only through option enumeration, not through a saved schedule run.
- Revision-conflict handling is unit-tested; provoking a real 409 in the preview runtime is out of scope for this suite.
- The Activity Grid repaints only on its next project read; this run verifies the details pane and a full page reload.

## Reproduce

```bash
PYTHONPATH=src py -m construction_pm.preview \
  --web-root apps/web --database /tmp/activity-general.sqlite --port 4193 --reset
cd apps/web && npm run build
CUBI_PREVIEW_URL=http://127.0.0.1:4193 CUBI_EVIDENCE_DATE=2026-11-18 \
  CUBI_TESTED_CODE_SHA=$(git rev-parse HEAD) node e2e/activity-general-edit-v26.mjs
```
