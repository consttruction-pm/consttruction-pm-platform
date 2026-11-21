# Help Crosswalk

Every studio records a `help_topic` and `help_status` on the server. The
Workbench does not fabricate a Help URL: until the Workbench document is added
to the generated traceability registry, each studio is marked
`HELP_REFERENCE_PENDING` and the Inspector lists the topic and status.

## Recorded topics

| Studio | Recorded `help_topic` | Recorded status | Candidate registry entry |
|---|---|---|---|
| Project Import Review & Staging | Import and Export Projects | `HELP_REFERENCE_PENDING` | `ENG-WS-EXCHANGE` (`/app/exchange/`) |
| Schedule Scenario Studio | Activities, Gantt Chart, Schedule Calculation | `HELP_REFERENCE_PENDING` | `ENG-WS-SCHEDULE` (`/app/schedule/`) |
| Risk Analysis Studio | Risk register | `HELP_REFERENCE_PENDING` | `ENG-WS-RISKS` (`/app/risks/`) |
| Project Analysis Studio | Project Statistics, Schedule Performance, Earned Value | `HELP_REFERENCE_PENDING` | no single entry; `ENG-WS-SCHEDULE` is the closest |
| Decision & Approval Workspace | Approvals, Workflows, Change Management | `HELP_REFERENCE_PENDING` | `ENT-FEEDBACK-APPROVAL` (`/enterprise/approvals/`) |

## Verified P6 Help sources already in the repository

These entries are published in `apps/web/src/help-registry.generated.ts`; they
are the reference material the Workbench topics point at. They are **not** yet
wired as per-studio deep links.

- Risks: `https://docs.oracle.com/cd/G48902_01/client_help/en_US/risks.htm`
- Scheduling: `https://docs.oracle.com/cd/G48902_01/client_help/en_US/schedulingprojects.htm`
- Importing and exporting: `https://docs.oracle.com/cd/G48902_01/client_help/en_US/48617.htm`
- The Gantt Chart: `https://docs.oracle.com/cd/G48902_01/client_help/en_US/the_gantt_chart.htm`
- Enterprise approvals: `https://docs.oracle.com/cd/G48897_01/p6help/en/51331.htm`

## What must happen to clear the pending status

1. Add `/ai-workbench/` (and the studio anchors) to the traceability source
   used by `scripts/generate-assistant-registries.mjs`.
2. Regenerate `help-registry.generated.ts` so the document and each studio have
   a stable entry id.
3. Change the server `help_status` from `HELP_REFERENCE_PENDING` to
   `PUBLISHED`/`IMPLEMENTED` only for entries that resolve to a real page.
4. Add a browser acceptance check that the Inspector link opens the registered
   entry, not a guessed URL.

Until then, the Inspector shows the topic and `HELP_REFERENCE_PENDING`; no link
is rendered.
