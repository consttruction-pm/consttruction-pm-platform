# Resource leveling conformance matrix

Status: internal documentation/test-design artifact only. No implementation parity is claimed.

## Official source references
- https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/leveling_priority_definitions.htm
- https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/level_resources.htm
- https://docs.oracle.com/cd/G48902_01/client_help/en_US/level_resources_dialog_box.htm

## Acceptance gates
1. Cover all 13 documented priority fields with canonical mapping and ascending/descending tests. Current source mapping supports only Activity ID, Activity Priority, Early Start, Early Finish, and Total Float.
2. Test priority row precedence and number/alphabetic/blank ordering. Do not infer unresolved mixed-value semantics.
3. Test default Activity ID ordering with numeric, alphabetic, and mixed IDs. Current lexical ordering is not accepted as proof of reference behavior.
4. Test all-resources, explicit selected resources, empty selection, and unknown IDs. A requested leveling run with no selected resources must not silently report success.
5. Test signed original float (negative, zero, positive) with within-float both enabled and disabled; preserve float provenance and use final CPM as authoritative.
6. Test forward-only and forward/backward leveling with FS/SS/FF/SF links, constraints, and final CPM. Keep final resource-capacity validation strict.
7. Test a single project with different activity and resource calendars. One resolver does not prove mixed-calendar parity; leave blocked until reference evidence exists.

## Mandatory pre-code evidence
For each rule: record exact product/version/page/section, source-derived semantics, unresolved edge cases, deterministic regression fixtures and expected output, then obtain independent review. Only then implement in a focused branch and run targeted tests, Python 3.11/3.12/3.13 CI, client typecheck, and PostgreSQL integration on the exact final commit.

This is an internal engineering artifact. Do not expose third-party product names, URLs, icons, or source indications in customer-facing CUBI UI, help, docs, or branding.