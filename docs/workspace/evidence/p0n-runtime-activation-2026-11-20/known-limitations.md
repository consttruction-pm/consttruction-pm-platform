# Known limitations — P0-N.2

Every limitation below is a real, observed boundary. None is an excuse for an
unfinished acceptance criterion; the criteria that are met are marked in
`final-acceptance-report.md`.

## 1. Product limitations (intentional, fail-closed)

| Area | Limitation | Why this is safe | Where recorded |
| --- | --- | --- | --- |
| Calendar defaulting | No implicit global/default calendar. A reference must name a persisted `calendar_id@calendar_version`. | A missing calendar makes the job `FAILED` with an explicit reason; it never silently schedules on a guessed calendar. | `calendar-registry-traceability.md` |
| Personal vs shared resource calendars | Not modeled; resource calendars are shared definitions. | The calculation path does not need the personal/shared distinction; no false parity is claimed. | `professional-help-traceability.md` |
| Dated work-hour details | A dated detailed rule without a date key fails with `DATED_DETAILED_WORK_HOURS_REQUIRE_DATE_KEY`. | Prevents applying a dated rule to the wrong weekday. | `calendar-registry-traceability.md` |
| Multiple float paths | Implemented in the desktop engine (`scheduling/schedule.py`), not in the time-aware worker path. | The worker path still publishes deterministic floats; the gap is named instead of claimed. | `professional-help-traceability.md` |
| Critical float threshold | Exposed in desktop scheduling options, not yet in the time-aware job path. | Float values are published; critical labeling with a threshold is a separate surface. | `professional-help-traceability.md` |
| Leveling in jobs | Leveling engine and persisted resolver exist, but leveling is not part of the durable job execution path. | No leveling result is claimed for worker jobs. | `professional-help-traceability.md` |
| Recurring scheduled services | Durable jobs are one-shot; there is no cron/trigger definition or recurrence UI. | Execution semantics (exactly once, lease, recovery) are proven; recurrence is honestly absent. | `eppm-help-traceability.md` |
| Schedule checker / summarization / cross-project allocation profile / budgeting workflow | Not implemented. | Listed as `MISSING`; not used to claim parity. | both traceability files |

## 2. Evidence limitations

| Limitation | Impact | Mitigation |
| --- | --- | --- |
| No browser/UI screenshots | P0-N.2 changed no UI code; there is no screen to capture. `screenshots/` documents this instead of fabricating images. | API/worker evidence is captured as logs and JSON. |
| EPPM has no PDF in this task | EPPM rows cite HTML only (`N/A (HTML)`). | Exact topic URLs were read from the official EPPM TOC; no page number is invented. |
| PDF page lookup by exact heading | A heading that repeats (chapter landing vs task page) needs a choice. | The page choice is stated in the matrix notes; the HTML topic URL is always provided as the primary identity. |
| Host is 4 CPUs | Capacity above 4 slots measures oversubscription, not linear scaling. | The capacity table reports the measured wall time and notes saturation; no extrapolation. |
| Single host / single PostgreSQL instance | Numbers are specific to this environment. | `environment.json` records CPU, memory, Python, PostgreSQL version; raw JSON is preserved. |

## 3. Infrastructure vs product failures

No infrastructure failure affected the final test evidence:

* PostgreSQL 14.24 was reachable at `127.0.0.1:55432` for every database run.
* The process-placement test started a real child (`process_starts >= 1`).
* The full suite completed with exit code 0.

If a future run fails to connect to PostgreSQL, that is an environment failure, not a
product regression, and must be reported with the connection error and the exact
command. It must not be converted into a skip that hides a missing proof.

## 4. CI status

CI on the exact final SHA is recorded in `final-acceptance-report.md`. Local results do
not substitute for CI, and CI does not substitute for the local PostgreSQL/worker
evidence.
