# P6 Resource-Leveling Priority Conformance Matrix — 2026-10-16

**Status: PARTIAL / NOT CERTIFIED.** This is a source-to-rule-to-code/test record for review, not a claim of Oracle certification. No code change is authorized by an unresolved row. The applicable candidate PR remains Draft.

## Versioned official sources

1. **P6 Professional User Guide, Version 26 — Leveling priority definitions**  
   https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/leveling_priority_definitions.htm
2. **P6 Professional User Guide, Version 26 — Level resources**  
   https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/level_resources.htm
3. **P6 Professional Integration API — Activity fields, `Activity.LevelingPriority`**  
   https://docs.oracle.com/cd/F25600_01/English/Integration/p6_pro_api_reference/FieldSummary.html
4. **P6 EPPM REST API, Release 26 — Activity GET/PUT, `LevelingPriority`**  
   https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-get.html  
   https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-put.html
5. **P6 EPPM User Guide — configuring resource-leveling priorities**  
   https://docs.oracle.com/cd/G48897_01/English/User_Guides/p6_eppm_user/7974_1.htm
6. **P6 EPPM ScheduleOptions REST GET/PUT, Release 26**  
   https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-scheduleoptions-get.html  
   https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-scheduleoptions-put.html
7. **P6 EPPM REST API, Release 26 — Project GET/PUT and Project resource-leveling settings**  
   https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-project-get.html  
   https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-syncservice-updateproject-put.html
8. **P6 EPPM REST API, Release 26 — ScheduleOptions GET/PUT field schema**  
   https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-scheduleoptions-get.html  
   https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-scheduleoptions-put.html
9. **P6 Integration API Release 26.4 — Project and ScheduleOptions Java properties**  
   Project: https://docs.oracle.com/cd/G48897_01/English/Integration_Documentation/p6_eppm_api_reference/com/primavera/integration/client/bo/object/Project.html  
   ScheduleOptions: https://docs.oracle.com/cd/G48897_01/English/Integration_Documentation/p6_eppm_api_reference/com/primavera/integration/client/bo/object/ScheduleOptions.html

## Source-to-rule-to-code/test matrix

| ID | Source-derived rule | Current implementation / regression evidence | Disposition |
|---|---|---|---|
| RL-P6-01 | Configured priority rows are ordered; row order establishes precedence. Priorities are relevant when multiple activities compete for a resource at the same time. | Shared Core tuple keeps configured row order; `tests/scheduling/test_leveling_boundary.py::test_scheduler_leveling_boundary_maps_ordered_priority_list`. | **PARTIAL** — broad row-order test exists; full mixed-field, tie and both-pass precedence matrix remains open. |
| RL-P6-02 | With no configured prioritization codes, P6 Professional falls back to Activity ID. The guide separately says numbers precede alphabetic characters and blank values follow, but the reviewed text does not establish that an empty Activity ID is valid. | `LevelingActivity.__post_init__` rejects empty IDs with `INVALID_ACTIVITY_ID`; `_activity_id_value_key` orders valid numeric IDs before alphabetic IDs; tests cover numeric/alphabetic order and deterministic `02` / `2` ties in both passes. | **PARTIAL / UNVERIFIED** — retain non-empty identity validation. Do not infer that an empty Activity ID is a valid sortable activity from the generic “blank values” sentence. The lexical tie-break for numerically equivalent IDs is deterministic CUBI behavior, not a claimed P6-specific rule; blank-value semantics and the full backward tie matrix remain subject to review. |
| RL-P6-03 | The Professional v26 priority-table criterion is labelled **Activity Priority**. The Professional Integration API describes `Activity.LevelingPriority` as the resource-leveling priority enum: `Top`, `High`, `Normal`, `Low`, `Lowest`. EPPM REST Release 26 documents the same `LevelingPriority` field and values. | Canonical field registry entry: `activity.leveling_priority` → Activity `LevelingPriority`, string. Domain enum: `ActivityLevelingPriority`. Tests: `tests/scheduling/test_resource_leveling.py::test_activity_leveling_priority_accepts_only_documented_p6_values` and `test_activity_leveling_priority_orders_forward_candidates` / `...backward_candidates`. | **PARTIAL / REVIEW REQUIRED** — the mapping between Professional UI label `Activity Priority`, EPPM UI label `Activity Leveling Priority`, interchange field and canonical field must be signed off by an independent reviewer. |
| RL-P6-04 | Numeric **Project Leveling Priority** is a distinct concept from the Activity `LevelingPriority` enum; it must not be conflated with an activity's Top/High/Normal/Low/Lowest value. | Shared Core carries `project_priority` separately and validates its 1–100 range; forward/backward tests exercise higher/lower project rank behavior. | **PARTIAL** — version/profile source mapping and end-to-end persistence/import evidence still need independent confirmation. |
| RL-P6-05 | Sort direction applies to the selected priority field. For hierarchical fields, Professional documentation says Hierarchy appears only for eligible hierarchical criteria; it is not a universal third sort direction for every field. | `PrioritySortOrder` and `leveling_boundary._map_priority_list` currently support Ascending/Descending only. | **BLOCKED** for Hierarchy: Release 26 ScheduleOptions does not identify a canonical per-row Hierarchy wire representation/eligibility contract in the reviewed schema. Do not invent one; record an explicit unsupported boundary if vendor evidence cannot establish it. |
| RL-P6-06 | Source schemas do not by themselves certify the internal-to-wire mapping. Release 26 ScheduleOptions REST declares `PriorityList` and `ResourceList` as scalar strings; the Integration API presents array accessors. | Internal domain/snapshot use typed tuples/arrays; related issue #1379 tracks this interface-boundary mismatch. | **BLOCKED** — the REST inner encoding/escaping and lossless round-trip contract are not specified by the reviewed official schema. Do not guess delimiter or JSON encoding. |
| RL-P6-07 | A documented blank priority value and unavailable source data are not automatically the same state. Missing required authoritative data must not be silently fabricated. | Several priority fields fail closed with `MISSING_LEVELING_PRIORITY_VALUE`; the Activity ID key implements numeric/alphabetic/blank categories. | **PARTIAL** — define/test each applicable field's blank-vs-missing state per product profile before relaxing fail-closed validation. |
| RL-P6-08 | The resource-leveling settings exposed by Release 26 Project REST are `Project.LevelPriorityList` (ordered resource-leveling priority fields, with Ascending/Descending/Hierarchy when eligible) and `Project.LevelResourceList` (resources to level). The separate `ScheduleOptions` REST object exposes `PriorityList` and `ResourceList` as scalar strings, but that schema provides no equivalent resource-leveling description for those properties; the Release 26.4 Integration API documents `ScheduleOptions.getPriorityList()/getResourceList()` as `String[]`, while Project's `getLevelPriorityList()/getLevelResourceList()` are `String`. Do not assume these similarly named fields are interchangeable. | Candidate code in `scheduling/leveling_boundary.py` maps `ScheduleOptions.priority_list` and `ScheduleOptions.resource_list` directly into the Shared Core leveling boundary. Source/code trace has not yet established the exact supported product profile, authoritative object, conversion/escaping rules or lossless round-trip for the selected-resource/priority settings. | **BLOCKED / SOURCE-TO-MODEL MAPPING UNVERIFIED** — establish object-plane ownership using the applicable P6 API/profile and an actual authoritative read/write/read round trip; tests must detect a mismatch between Project-level `LevelPriorityList/LevelResourceList` and ScheduleOptions-level `PriorityList/ResourceList`. Do not guess scalar-string encoding or silently alias fields. Independent semantic review required. |

## New Release 26 object-plane discrepancy — BLOCKED / UNVERIFIED

The current candidate maps internal `ScheduleOptions.priority_list` and `ScheduleOptions.resource_list` into `ResourceLevelingOptions`. Official Release 26 schemas expose names with different context:
- ScheduleOptions REST GET/PUT: `PriorityList: string`, `ResourceList: string`; the schema does not give these properties the Project-level resource-leveling description.
- Project REST GET and Update Project: `LevelPriorityList: string` describes the ordered fields used to prioritize resources while leveling, including conditional `Hierarchy`; `LevelResourceList: string` is the list of resources to level.
- Integration API Release 26.4: Project getters for `LevelPriorityList`/`LevelResourceList` return `String`; ScheduleOptions getters for `PriorityList`/`ResourceList` return `String[]`.

This establishes a real contract-shape/object-name discrepancy, **not yet a proven product behavior bug**. The intended current CUBI mapping may be correct only for a specific supported P6 profile; that has not been source-to-model-to-wire demonstrated. The review must identify the authoritative source object for the product workflow, canonical stored representation, exact conversion/escaping, and a lossless read/write/read fixture. Until then, this matrix row remains BLOCKED and the candidate must not claim complete resource-leveling parity.

## Outstanding source-to-code review

### Potential Activity Priority alias mismatch — UNVERIFIED until independent sign-off

The current candidate boundary accepts both `activity_priority` and `activity_leveling_priority`, which resolve to different Shared Core values (numeric versus the LevelingPriority enum). The canonical P6 field registry maps `activity.leveling_priority` to `Activity.LevelingPriority`; it does not establish a separate numeric P6 Activity Priority field.

The official sources above support the UI/API label distinction and the five-value enum, but a reviewer must confirm the exact mapping for each supported product profile before implementation changes. Until approved:
- Do not silently alias a numeric internal field to the P6 UI criterion.
- Do not invent a separate P6 numeric field.
- Keep unresolved mapping `UNVERIFIED/BLOCKED`.
- Add a source-backed mapping test demonstrating the selected criterion flows through import/persistence/snapshot materialization into the same authoritative comparator.
- If numeric `activity_priority` is a CUBI-only extension, it needs an explicitly non-conflicting identifier and must not be represented as the P6 Professional **Activity Priority** field.

## Verification snapshot

- Candidate: PR #1457 (Draft, unmerged), branch `fix/backward-leveling-rebased-main-2026-10-16`.
- Latest source/code review for this matrix includes live candidate head `e09aac5a4be13f61b8cbc9c01b0e1a44d01696d7`; this document-only update creates a new head and invalidates the previous exact-head certification until checks rerun.
- The previous live candidate head `e09aac5a4be13f61b8cbc9c01b0e1a44d01696d7` had successful recorded checks: ConstructionPM CI run `38970547448`, Client Typecheck run `38970547313`, and PostgreSQL Integration run `38970547311`.
- The earlier failing fixture run on `fcab7fffa5ffba34aeeff33614e76fa08cc01f06` and the earlier green run on `4fa88f27a5b93952131aba0012cd6b20918f2609` are historical and are not the current candidate verification snapshot.
- The PR description also contains a stale “Latest exact-head verification” entry naming `c403a72e5fbb4091120967c13ddcc0917913df36`; it must not be treated as the current candidate head.
- These successful workflows verify the tested code paths only. They do not establish P6 scheduling parity, resolve the REST scalar-string encoding for `PriorityList`/`ResourceList`, or replace independent semantic review.
- The current PR head has green checks, but this document-only follow-up will create a new head and therefore requires fresh exact-head checks. Keep Draft and unmerged until the integration-path, wire-contract, priority mapping, and independent-review gates are evidenced.
- No independent semantic approval is recorded. The newly identified object-plane mapping discrepancy RL-P6-08 also remains blocked. The matrix remains **PARTIAL / NOT CERTIFIED**.
