# Resource leveling conformance matrix

Status: internal documentation/test-design artifact only. No implementation parity is claimed.

## Official source references (version-pinned)

- Oracle Primavera P6 Professional User Guide, Version 26 (full guide PDF): https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/p6_pro_user.pdf
- Level resources: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/level_resources.htm
- Leveling priority definitions: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/leveling_priority_definitions.htm
- Level Resources dialog and minimum-float option: https://docs.oracle.com/cd/G48902_01/client_help/en_US/level_resources_dialog_box.htm
- Schedule Options General tab (authoritative Total Float basis): https://docs.oracle.com/cd/G48902_01/client_help/en_US/general_tab_-_schedule_options_dialog_box.htm
- Negative float: https://docs.oracle.com/cd/G48897_01/p6help/nl/46283.htm
- Suspend or resume an activity's progress: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/suspend_or_resume_an_activity_s_progress.htm

## Acceptance gates

1. Cover all 13 documented priority fields with canonical mapping and ascending/descending tests. Current source mapping supports only Activity ID, Activity Priority, Early Start, Early Finish, and Total Float.
2. Test priority row precedence and number/alphabetic/blank ordering. Do not infer unresolved mixed-value semantics.
3. Test default Activity ID ordering with numeric, alphabetic, and mixed IDs. Current lexical ordering is not accepted as proof of reference behavior.
4. Test all-resources, explicit selected resources, empty selection, and unknown IDs. A requested leveling run with no selected resources must not silently report success.
5. Test signed original float (negative, zero, positive) with within-float both enabled and disabled; preserve float provenance and use final CPM as authoritative. Negative float is a documented schedule condition. The shared leveling input now carries signed float, but backward-priority semantics must still be tested under Start Float, Finish Float, and Smaller Float.
6. Test forward-only and forward/backward leveling with FS/SS/FF/SF links and constraints. Explicitly cover minimum float preserved = 0 and > 0, with Preserve Scheduled Early and Late Dates enabled and disabled. Assert final CPM dates, late dates, and remaining float against version-pinned reference fixtures. The backward proposal still has no `min_float_to_preserve` parameter; do not count forward-only coverage as satisfying this gate. The backward-priority `total_float` implementation also must use the authoritative configured basis (Start Float, Finish Float, or Smaller Float), not merely the early-to-late start window. Keep final resource-capacity validation strict.
7. Test a single project with different activity and resource calendars. One resolver does not prove mixed-calendar parity; leave blocked until reference evidence and a suitable authoritative per-activity/resource calendar path are established.
8. Trace suspend/resume semantics from the authoritative progress/demand-period builder through the adapter and leveling engine. Fixture: an eligible activity with an actual start, suspend date, resume date, and resource assignment competes with another activity for the same constrained resource. Assert no demand/overload is attributed to the suspended interval, the resource is available to competing work until the resume date, demand resumes from the resume date, and final CPM relationships and capacity are valid. Do not infer a runtime defect solely from the transport adapter; prove where demand periods are actually produced.
9. Distinguish resource curves from manual future-period values with a controlled competing-activities fixture. Case A: configure a resource curve with no manual future-period overrides and prove curve shape alone does not change leveling demand or the selected move. Case B: set manual future-period bucket values that shift demand to another period and prove those values are used and can change the selected move. Assert demand slices, selected move, final CPM dates/relationships, and capacity; do not duplicate curve-spreading logic in the leveling proposal layer.
10. Ensure acceptance fixtures exercise the actual persisted assignment-period contract and the authoritative upstream demand builder—not only synthetic ResourceDemand inputs—and capture source IDs, calendar IDs/versions, dates, units, selected options, expected move, and final schedule/capacity evidence for reproducibility.

## Mandatory pre-code evidence

For each rule: record exact product/version/page/section, source-derived semantics, unresolved edge cases, deterministic regression fixtures and expected output, then obtain independent review. Only then implement in a focused branch and run targeted tests, Python 3.11/3.12/3.13 CI, client typecheck, and PostgreSQL integration on the exact final commit. A green test run does not by itself prove reference parity.

This is an internal engineering artifact. Do not expose third-party product names, URLs, icons, or source indications in customer-facing CUBI UI, help, docs, or branding.
