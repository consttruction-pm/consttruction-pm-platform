# Two-environment reference map — P0-N.2

The programme has **two independent Oracle V26 references**. They are not
interchangeable, and neither is a substitute for the other.

| | Professional (desktop) | EPPM (enterprise server) |
| --- | --- | --- |
| Product | Primavera P6 Professional | Primavera P6 EPPM |
| Canonical HTML help | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm | https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm |
| Document identity | P6 Professional Help V26, G57535-02, 9 Oct 2026 | P6 EPPM Help V26, May 2026 |
| Local artifact | Owner-supplied PDF, 815 pages, SHA-256 `0746e8521d9f3bac85b1b6c4ec7fabfd139cc4bf79ae59b03a1a3ee1f8e9dc0b` | No PDF supplied; HTML is the authoritative form |
| Page citation | Absolute PDF page + HTML topic URL | HTML topic URL only (`N/A (HTML)`) |
| Scope | Desktop workspace, menus, toolbars, windows, layouts, single-user operations | Enterprise pages, security, server services, multi-project administration |
| CUBI consumer | Visual workspace and Activities/scheduling behavior | Enterprise parity baseline (`docs/enterprise/CUBI_ENTERPRISE_PRIMAVERA_P6_EPPM_HELP_PARITY_V26.md`) |
| Supporting sets | Professional User/Admin/Reporting/Visualizer guides (supporting only) | Team Member Help V26 is a separate set: https://docs.oracle.com/cd/G48897_01/team_member/web/help/en/toc.htm |

## 1. Non-substitution rules

1. A Professional topic never answers an EPPM requirement, even when the feature name
   matches.
2. An EPPM topic never overrides Professional desktop behavior.
3. A URL is used only after it appears in the official HTML TOC of its own set. No
   filename is guessed and no “similar” release is substituted.
4. The PDF and HTML for Professional are two renderings of the same help set; the PDF
   page is recorded alongside the HTML topic.
5. Team Member is a third help set and is not used for Enterprise task parity in this
   evidence.

## 2. Capability crosswalk

Rows are the capabilities in scope for P0-N.2. Full columns and statuses are in
`professional-help-traceability.md` and `eppm-help-traceability.md`.

| Capability | Professional topic (PDF page) | EPPM topic | CUBI owner | Shared behavior |
| --- | --- | --- | --- | --- |
| Calendar definition | Calendars (159) | About Calendars | `calendar_master_repository.py` | versioned, scope-bound calendar |
| Project calendar | Project Calendars (161) | Creating Project Calendars | `calendar_master_repository.py` | project-level definition |
| Resource calendar | Resource Calendars (166) | Creating Resource Calendars | `p6_versioned_resource_calendar_resolver.py` | own arithmetic per resource |
| Work hours / standard week | Defining default hours per time period (160) | Configuring the Standard Work Week for Global Calendars | `calendar_work_hours_repository.py` | weekly rules change dates |
| Activity calendar assignment | Assign a calendar to an activity (201) | Assigning Calendars to Resources | `scheduling/calendar_context.py` | explicit reference, no default substitution |
| Relationship lag calendar | Choose a calendar for relationship lag (296) | Configuring Advanced Scheduling Options | `scheduling/calendar_context.py` | lag arithmetic uses selected calendar |
| Schedule calculation | Schedule a project (294) | About Scheduling Projects | `scheduling/time_schedule.py` | forward/backward pass, floats |
| Constraints | Enter activity constraints (295) | About Scheduling Projects | `scheduling/time_constraints.py` | closed-set constraint kinds |
| Critical path / float | Define critical activities (290) | About Critical Path Activities | `scheduling/time_schedule.py` | per-activity floats |
| Multiple float paths | Calculate multiple float paths (292) | Configuring Advanced Scheduling Options | `scheduling/schedule.py` | ranked float paths (desktop engine) |
| Leveling | Level resources (300) | About Resource Leveling | `scheduling/resource_leveling.py` | constrained reordering |
| Durable job execution | Job Services (434) | About Project Scheduled Services | `deployment/scheduling_worker.py` | execute outside the request, durable result |
| Multiple projects | Working with multiple projects (507) | Configuring Project Preferences for Multiple Projects | `scheduling_worker_scheduler.py` | bounded concurrent execution |
| Baselines | Creating Baselines (266) | About Baselines | `p6_baseline_api.py` | revision-pinned baseline |
| Progress update | Updating progress (280) | About Updating Progress | `p6_activity_progress_api.py` | persisted actuals |
| Schedule health check | Checking schedules (296) | Running the Project Checker | — | **not implemented** |
| Summarization | Summarize project data (433) | Summarizing Projects | — | **not implemented** |
| Budgeting | Budgeting (263) | — (EPPM portfolio reporting) | `p6_earned_value_read_model.py` | read model only |
| Cross-project allocation profile | View a profile of resource allocation across all projects (356) | About the Check Resource Overallocation Service | — | **not implemented** |

## 3. Meaning for P0-N.2 acceptance

* The runtime activation is a **Professional-documented calculation behavior**
  implemented once in the shared core; EPPM documentation confirms the enterprise
  service semantics (server-side execution, scheduled services, multi-project).
* Where Professional and EPPM describe the same arithmetic (calendars, scheduling,
  leveling), CUBI uses one authority — `scheduling/time_schedule.py` — not two
  implementations. This satisfies the continuity protocol rule that Enterprise must not
  create a parallel calculation engine.
* Where only one environment documents a capability (e.g. Professional multiple float
  paths, EPPM project checker), the matrix does not transfer the row to the other
  environment.

## 4. Evidence pointers

* `professional-help-traceability.md` — 22-row Professional matrix with PDF pages.
* `eppm-help-traceability.md` — 21-row EPPM matrix with exact HTML URLs.
* `environment.json` — PDF hash, page count, host fingerprint.
* `logs/full-suite.log`, `logs/targeted.log` — executed test evidence.
* Frozen extracts used for page lookup: `pdftotext -layout` of the attached PDF; HTML
  TOCs fetched from the two canonical URLs above.
