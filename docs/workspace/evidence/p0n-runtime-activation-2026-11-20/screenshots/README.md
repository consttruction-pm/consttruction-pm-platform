# Screenshots

No screenshots are included for P0-N.2.

Reason: this change is a runtime/composition/worker activation. It does not modify any
browser surface, layout, component or style, so there is no before/after screen that
would be truthful evidence. Generating a screenshot of an unrelated page would
misrepresent the work.

The equivalent evidence for this change is machine-readable:

* `logs/targeted.log` — 114 passed (API, job lifecycle, calendar registry, runtime).
* `logs/full-suite.log` — 5381 passed, 1 environmental skip.
* `results/` — raw benchmark and worker end-to-end JSON produced on real PostgreSQL.
* `environment.json` — host and PDF fingerprint.
* `final-acceptance-report.md` — criterion-by-criterion mapping.

If a future change adds a user-visible surface, real screenshots from the built preview
must be added here; an empty directory is not evidence.
