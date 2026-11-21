# P6 Leveling Conformance Audit — 2026-10-22

Source review found two confirmed gaps:

1. `AuthoritativeScheduleQueryProvider.execute()` calls `evaluate_schedule_snapshot()` without `leveling_input`. The evaluator raises `SCHEDULE_LEVELING_INPUT_REQUIRED` whenever resource leveling is enabled. The production Schedule Query path therefore does not yet demonstrate end-to-end resource leveling.
2. `leveling_boundary.py` only accepts Activity ID, Activity Priority, Early Start, Early Finish, and Total Float. Oracle P6 documents additional priorities including Free Float, Late Start/Finish, Planned Finish, Planned Duration, Remaining Duration, Project Priority and Project Planned Start. Unsupported fields should be implemented only when authoritative values exist, otherwise rejected explicitly.

Further parity gates: define cross-project assignment policy; prove preserve-early/late-dates forward-only vs backward leveling; test time-phased demand/capacity, calendar exceptions, zero/missing capacity, and final CPM/resource validation.

No test pass or full P6 parity is claimed. The next implementation step is to connect the authorized resource-read adapter to the snapshot evaluator for the exact tenant/project/revision, then add end-to-end tests.

Oracle v26 references:
- https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/leveling_resources.htm
- https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/level_resources.htm
- https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/leveling_priority_definitions.htm
