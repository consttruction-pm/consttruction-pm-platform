# P6 EPPM V26 vs P6 Professional V26 — Data Dictionary, Schema, and API Field-Surface Matrix

**Status:** Documentary comparison with explicit version boundaries  
**Scope:** Field dictionaries, core/reporting schemas, REST and Java API surfaces, UDF subject areas/types, representative Activity field mapping, and report data access.  
**Out of scope:** Database inspection, SQL execution, migrations, application changes, workspace changes, and any agent-owned implementation.  
**Version discipline:** EPPM sources below are V26. Professional user/help sources are V26. The publicly surfaced Professional API reference used for field-shape illustration is Release 24 (and the combined API programming guide surfaced in current Oracle materials is V25); these are explicitly **not** treated as V26 proof. A V26 Professional API field inventory remains open.

## 1. Executive findings

1. **The EPPM Data Dictionary is a business-field glossary, not the physical database schema.** Oracle separately publishes the EPPM core database schema, Extended Schema guide, and Extended Schema download. These artifacts answer different questions and must not be conflated.
2. **EPPM Extended Schema is a reporting layer of views.** Oracle says the objects are technically views, populated by Publication Services, containing calculated/denormalized values, with reporting support limited to those views. It is not simply another name for the transactional database tables.
3. **Professional V26 supports two database contexts:** a standalone P6 Professional database, or a P6 EPPM database. The client is the same product family component, but its available enterprise functions, permissions, and integration surfaces depend on the connected database. A comparison that omits this context is unreliable.
4. **The public V26 documentation catalogues are not symmetrical.** EPPM V26 publishes a Data Dictionary, core Schema Guides, Extended Schema Guide, REST API, and Primavera Data Service documentation. Professional V26's published guide inventory lists its Help/User/Admin/Reporting/Visualizer guides, but does not list a matching V26 core-schema download, Extended Schema guide, REST API reference, or separate Data Dictionary guide. This is a difference in the documented/public reference surface, not proof that Professional lacks database tables or APIs.
5. **P6 EPPM REST V26 is not the same interface as the P6 Professional Java API.** EPPM REST is documented as HTTP/JSON operations with GET/POST/PUT/DELETE and field-discovery endpoints. The Professional API is a Java API; the latest combined programming guide located during this audit is V25 and says the Professional API is Local Mode only. A version-matched V26 Professional API contract was not found in the V26 Professional guide inventory.
6. **The business model has extensive shared concepts and fields.** Activity, WBS, Project, Calendar, Resource, ResourceAssignment, Baseline, UDF, code, risk and document objects occur across the product family and the Professional API reference. Similar labels do not prove identical storage types, REST names, permissions, or version-specific field sets.
7. **UDF comparisons require separate UI and API views.** Professional V26 user documentation lists seven visible data types (Text, Start Date, Finish Date, Cost, Indicator, Number, Integer) and nine example subject areas. EPPM V26 REST UDFType metadata lists Text, Start Date, Finish Date, Cost, Double, Integer, Indicator and Code, with additional calculated/conditional/secure-code metadata and additional subject-area values. Some of those distinctions are API-contract detail, not proof of a UI-only product feature.

## 2. Comparison matrix

| # | Topic | P6 EPPM V26 evidence | P6 Professional V26 evidence | Reconciled finding / status |
|---:|---|---|---|---|
| 1 | Documentation inventory | EPPM V26 Guides catalog has User, Admin, Import/Export, Integration and Schema guides | Professional V26 catalog lists Client Requirements, Admin, Help, Licensing, Reporting, User and Visualizer | Different published reference inventories. CONFIRMED |
| 2 | Separate field glossary | Dedicated P6 EPPM Data Dictionary V26 guide and EPPM Help Data Dictionary topics | No separate Data Dictionary guide in Professional V26 All Guides inventory; Professional User Guide documents Hint Help and field-specific behaviors | Documentation packaging differs; do not infer fields are absent. CONFIRMED (catalogue scope) |
| 3 | Data Dictionary meaning | Defines business fields and their meanings/calculations (e.g., Activity ID, Total Float, UDF values) | Contextual Hint Help and user-guide explanations describe visible fields and workflows | A field glossary is not a physical schema/column catalogue. CONFIRMED |
| 4 | Core database schema documentation | EPPM V26 Schema Guides list database schema table downloads for 26.4 and 26.1 | Professional V26 All Guides inventory has no corresponding schema-download entry | Published V26 schema-documentation availability differs. NOT VERIFIED for underlying Pro schema equivalence |
| 5 | EPPM Extended Schema | V26 guide describes reporting schema made of views | No separate Professional V26 Extended Schema guide is listed | Extended Schema is an EPPM reporting artifact; do not assume a same-named Pro reporting schema. CONFIRMED |
| 6 | Extended Schema object type | Objects are technically views (predefined SQL queries over one or more P6 tables) | Professional reporting uses report data sources/fields from the connected database; no Pro Extended Schema layer documented in V26 Pro guide inventory | Views vs transactional tables must be distinguished. CONFIRMED |
| 7 | Calculated/denormalized values | Publication Services recalculate logical/denormalized fields and store them in Extended Schema views | Professional Report Wizard/Editor uses data sources and fields from the connected database | EPPM reporting values may be publication-derived rather than a live transaction read. CONFIRMED |
| 8 | Publication cadence | Project and Global Publication Services update project/global reporting data; services can publish changed data incrementally | No equivalent EPPM Publication Services model is documented as a Professional standalone reporting feature | Do not treat Professional report execution as a substitute for EPPM publication. CONFIRMED |
| 9 | Project data publication scope | Publish Project includes WBS, activities, assignments, relationships, risks, documents, expenses, steps, milestones, UDFs, notes, issues, timesheets and more | Professional report data sources cover project entities; publication list is not a Pro API contract | Same subject matter may be reportable through different mechanisms. CONFIRMED |
| 10 | Global data publication | Publish Audit, Enterprise, Resource, Calendar, Enterprise Summary, Resource Management and Security data | No matching V26 Professional global publication-service catalog is listed | EPPM has an explicit reporting-publication service layer. CONFIRMED |
| 11 | Extended Schema field relationships | Views commonly expose OBJECTID and related object IDs; primary/foreign keys are not hard-wired into views | Professional API exposes ObjectId fields and related object IDs in Java business objects (reference located is Release 24) | Join by documented business-object IDs, not guessed physical keys. CONFIRMED for EPPM; Pro field reference is version-limited |
| 12 | Extended Schema naming | Many ODS-like view names receive a P6 prefix (e.g., ACTIVITY → P6ACTIVITY); HIERARCHY and SPREAD suffix patterns convey view purpose | No V26 Professional Extended Schema naming convention documented | EPPM reporting-layer naming rule. CONFIRMED |
| 13 | Oracle DB reporting security | Oracle DB Extended Schema views apply P6 security privileges | Professional connected to EPPM database uses EPPM permissions for product functions | Reporting-view access and desktop permission model must be tested in the actual database context. PARTIALLY VERIFIED |
| 14 | SQL Server reporting security | Oracle guide warns P6 security privileges are not enforced by the reporting software for SQL Server; report SQL must include appropriate security predicates | Professional can connect to SQL Server Professional DB or EPPM DB | High-impact security difference for report consumers; do not assume Oracle view security on SQL Server. CONFIRMED |
| 15 | Professional DB contexts | EPPM database is the primary P6 suite database | Professional V26 User Guide distinguishes connected-to-EPPM from connected-to-Professional database and supports standalone mode | Connection context changes features and security/integration behavior. CONFIRMED |
| 16 | EPPM REST API | V26 REST API has business-object services, field discovery and CRUD operations | Professional V26 guide inventory does not list an equivalent Professional REST API reference | EPPM REST is a documented EPPM interface; a V26 Pro REST equivalent is NOT VERIFIED |
| 17 | EPPM REST Activity | Activity endpoint supports create/read/update/delete, get field lengths and view Activity fields | Professional V26 User Guide describes Activities UI; Professional API reference is Java and not a REST contract | UI concepts do not define REST contract parity. CONFIRMED |
| 18 | EPPM REST Project | Project REST service has project fields, IDs, summary and scheduling-related properties | Professional User Guide manages projects in standalone and EPPM contexts | Shared project concepts, different documented integration contracts. CONFIRMED |
| 19 | REST object identifier | EPPM REST Activity has string Id (short ID within project), numeric ObjectId and GUID | Professional API reference uses Id and ObjectId on Activity (reference located is Release 24) | Distinguish business ID from generated object ID; never substitute Activity ID for ObjectId. CONFIRMED / Pro version-limited |
| 20 | Activity field name and display label | EPPM REST uses canonical names such as PlannedDuration, PlannedStartDate, ActualStartDate, RemainingDuration and TotalFloat | Professional API reference uses the same canonical field names and documents industry aliases (e.g., PlannedDuration is named OriginalDuration in Engineering & Construction) | Canonical names and UI labels may differ by industry configuration. PARTIALLY VERIFIED for V26 Pro API |
| 21 | Activity ID definition | EPPM Data Dictionary defines Activity ID as a unique activity identifier built from prefix, suffix and increment | Professional V26 Hint Help describes Activity ID as a short ID uniquely identifying an activity within its project | Same business concept; scope wording differs. Do not assume global uniqueness. CONFIRMED |
| 22 | Activity Name | EPPM dictionary: activity name; names need not be unique | Professional V26 Help likewise treats Activity Name as descriptive and non-unique | Shared semantics. CONFIRMED |
| 23 | Activity Type | EPPM dictionary defines how duration and schedule dates are calculated; task/resource dependent, LOE, milestones | Professional V26 User Guide documents six activity types including WBS Summary | Shared activity model; verify UI context and type availability. CONFIRMED |
| 24 | Planned vs Budgeted terminology | EPPM uses one consistent field naming convention, with industry-related display labels in connected Professional | Professional install/industry settings can show Budgeted/Original or Planned terminology for the same canonical fields | Label differences are not automatically schema-field differences. CONFIRMED |
| 25 | Total Float definition | EPPM dictionary defines delay allowance before risking project finish; formula can be Late Start − Early Start or Late Finish − Early Finish | Professional V26 User Guide explains Total Float and Free Float in the same operational terms | Shared semantics; exact calculated value depends on schedule settings/calendar context. CONFIRMED |
| 26 | Activity field/API types | EPPM REST represents dates as date-time strings, durations/costs as numbers, booleans and IDs as typed JSON fields | Professional Java API field reference uses Java Date/Duration/Cost/ObjectId/boolean types | Different transport/type systems; do not compare raw JSON and Java types as if identical. CONFIRMED |
| 27 | Read-only vs writable fields | EPPM REST schemas indicate required/optional and request/response fields per operation | Professional Java FieldSummary includes a Read Only flag | Different metadata conventions; field writeability is operation/context-specific. CONFIRMED |
| 28 | EPPM Data Service (PDS) | V26 PDS provides metadata tables/columns and read-only query access for supported cloud data configurations | No PDS counterpart is listed in Professional V26 guide inventory | PDS is an EPPM/Unifier data extraction service, not a Professional desktop API. CONFIRMED |
| 29 | PDS configuration contexts | Metadata endpoints accept ds_p6adminuser, ds_p6reportuser or ds_unifier configuration codes | No corresponding Professional V26 PDS configuration model documented | These configuration codes are PDS connection identities, not P6 user roles or Professional database profiles. CONFIRMED |
| 30 | PDS metadata tables | V26 endpoint returns physical/display table names, table type (STANDARD/VIEW/SYNONYM), service code and blacklist flag | No equivalent Pro V26 metadata REST endpoint located | EPPM data-service metadata discovery is a distinct service surface. CONFIRMED |
| 31 | PDS metadata columns | V26 endpoint returns column name, display name, data type, physical type, PK/FK flags, FK table and table type | No equivalent Pro V26 metadata REST endpoint located | EPPM has an explicit metadata-discovery contract; absence of a Pro guide entry is not proof no internal metadata exists. CONFIRMED |
| 32 | PDS access mode | PDS is documented as read-only access to cloud-based P6 EPPM/Unifier transactional data | Professional client can edit project data subject to database context and privileges | PDS is not an alternative write API. CONFIRMED |
| 33 | P6 Integration API modes | Combined API guide says P6 Integration API can run Local or Remote | Combined API guide says P6 Professional API runs Local only | Distinct Java API deployment modes. Source located is V25, so V26 exactness remains PARTIALLY VERIFIED |
| 34 | EPPM Integration API vs Professional API | EPPM Integration API is the server-oriented API; current EPPM V26 integration catalog separately lists REST and Web Services | Professional Java API is a distinct local-mode interface | Do not label both simply "P6 API" without naming product/interface. PARTIALLY VERIFIED for V26 |
| 35 | UDF visible data types | EPPM REST UDFType schema lists Text, Start Date, Finish Date, Cost, Double, Integer, Indicator and Code | Professional V26 User Guide lists Text, Start Date, Finish Date, Cost, Indicator, Number (two decimal places) and Integer | Professional UI calls the decimal type Number while API contract uses Double; Code is not listed among Professional UI types. UI/API distinction is important. CONFIRMED |
| 36 | UDF subject areas | EPPM REST V26 UDFType includes Activity, Activity Expense, Activity Step, Project, Project Issue, Project Risk, Resource, Resource Assignment, WBS, Work Products and Documents, Lean Task and Roles (API schema lists subject area values) | Professional V26 User Guide examples list Activities, Activity Steps, Activity Resource Assignments, Projects, Resources, WBS, Expenses, Issues and Work Products & Documents | EPPM API documents additional subject areas; exact UI availability and Professional V26 API parity remain PARTIALLY VERIFIED |
| 37 | UDF calculated/conditional metadata | EPPM REST exposes Formula, IsCalculated, IsConditional, IsSecureCode, SummaryMethod and DisplayIndicatorFlag | Professional V26 UI guide describes UDF values and indicators; does not enumerate these API metadata fields | EPPM REST schema is richer than the UI help description; Pro API V24 has analogous metadata fields, so not safe to label EPPM-exclusive. PARTIALLY VERIFIED |
| 38 | UDF security | EPPM UDF values are subject to P6 security; REST requests are authenticated/authorized | Professional V26 Help says only users with global privileges may edit UDF definitions; cost UDF values require project cost-view privilege | Shared privilege concepts; exact per-subject authorization matrix not yet field-by-field verified. CONFIRMED |
| 39 | UDF value storage | EPPM separates UDFType metadata from UDFValue assignment/value objects in Integration API | Professional API reference also contains UDFType/UDFValue business objects (Release 24) | Same conceptual metadata/value separation in the Java API family; Pro V26 contract needs a version-matched confirmation. PARTIALLY VERIFIED |
| 40 | Report data source | EPPM reporting can query Extended Schema views and publication-calculated values | Professional Report Editor data source corresponds to a subject area/category from the connected database; fields are selected within that source | Different report architecture and field-resolution paths. CONFIRMED |
| 41 | Professional report field binding | Not an EPPM REST field contract | Report Editor fields are bound to a selected data source; changing data source changes available field names | Report field lists are context-dependent; they are not a global schema dictionary. CONFIRMED |
| 42 | Report access control | Extended Schema access differs by DB platform and publication/security configuration | Professional V26 reports require database-context-specific global/project report privileges to create/edit; viewing does not require the same edit privileges | Report definition permissions and underlying data permissions are separate. CONFIRMED |
| 43 | Direct physical schema inspection | EPPM schema ZIPs and Extended Schema DMD are published; PDS metadata can reveal table/column metadata for supported configs | No public V26 Professional schema ZIP was found in its V26 guide inventory | Cannot produce a complete V26 physical-column parity table from public Pro documentation alone. NOT VERIFIED |
| 44 | V26 Professional API schema inventory | EPPM V26 REST and Integration API references are published | Professional V26 All Guides inventory does not list a V26 Pro API Javadoc/field summary; V24 Pro API reference and V25 combined programming guide are available | Exact V26 Pro API field-level parity remains open. CONFIRMED (catalogue) / NOT VERIFIED (API parity) |

## 3. Important field-mapping rules

### 3.1 Do not confuse Activity ID, ObjectId and GUID

The EPPM REST Activity contract distinguishes:
- `Id`: short Activity ID, unique within a project
- `ObjectId`: system-generated numeric identifier
- `GUID`: globally unique ID

Professional API reference likewise exposes an Activity short ID and an ObjectId. Cross-system integrations must use the key appropriate to the operation and database context. An Activity ID can repeat across projects; it is not a substitute for a globally unique database identifier.

### 3.2 UI labels are not canonical field names

Oracle explicitly documents industry-specific labels in Professional: for example, a canonical `PlannedDuration` can appear as Original Duration in Engineering & Construction. Likewise Budgeted vs Planned cost/unit labels can reflect industry terminology. Field mapping should retain:
- canonical API/business field name,
- UI label under the configured industry type,
- database object/column where verified,
- data type and unit,
- read/write behavior,
- connected database context.

A spreadsheet that maps UI captions directly to physical columns without this normalization is not a reliable data dictionary.

### 3.3 The Extended Schema is not the transaction schema

The EPPM Extended Schema is a reporting layer of views. Some durations and other calculated values are computed at publication time and stored for reporting. Other values are transformed into reportable structures. It is therefore unsafe to:
- assume every P6 business field has a same-named physical column,
- join views on arbitrary ID-like columns,
- compare an Extended Schema value to a live UI value without recording publication time and selected baseline/summarization context,
- treat Extended Schema view names as a supported direct-write API.

Oracle's guide says support is provided for reports written against Extended Schema views only.

### 3.4 PDS is not REST CRUD

The V26 Primavera Data Service is a separate read-only data extraction service. It exposes table/column metadata and query operations for supported cloud configurations. It should not be described as a replacement for P6 EPPM REST create/update operations or as a Professional desktop API.

### 3.5 A Professional connection changes the comparison baseline

The P6 Professional V26 User Guide explicitly documents different behavior when connected to:
- a P6 Professional database, and
- a P6 EPPM database.

Examples include database type in the status bar, user/security privilege source, application settings source, reporting privilege rules, and use of EPPM job services. Every field/API comparison must state which database context is assumed.

## 4. Representative Activity field crosswalk

The following is a **semantic crosswalk**, not a claim of exhaustive schema identity:

| Business concept | EPPM V26 REST name | Professional API name in available Release 24 reference | Notes |
|---|---|---|---|
| Activity short identifier | Id | Id | Short ID; unique within project |
| Internal activity key | ObjectId | ObjectId | Generated database/business-object key |
| Globally unique identifier | GUID | GUID (where exposed) | Not the same as Activity ID |
| Activity label | Name | Name | Names need not be unique |
| Planned duration | PlannedDuration | PlannedDuration | UI alias may be Original Duration |
| Planned start | PlannedStartDate | PlannedStartDate | Scheduler-calculated, may be manually changed |
| Planned finish | PlannedFinishDate | PlannedFinishDate | Scheduler-calculated, may be manually changed |
| Actual start | ActualStartDate | ActualStartDate | Actual progress date |
| Actual finish | ActualFinishDate | ActualFinishDate | Actual completion date |
| Remaining duration | RemainingDuration | RemainingDuration | Calendar-based remaining working time |
| At-completion duration | AtCompletionDuration | AtCompletionDuration | Current start-to-current finish duration |
| Total float | TotalFloat | TotalFloat | Scheduler option controls start/finish basis |
| Free float | FreeFloat | FreeFloat | Delay before delaying successor start |
| Critical flag | IsCritical | IsCritical | Classification flag; not equivalent to path membership |
| Longest-path flag | IsLongestPath | IsLongestPath | Separate from critical flag |
| Float path rank | FloatPath | FloatPath | 1 = most critical path |
| Float path order | FloatPathOrder | FloatPathOrder | Order in which activity was found on path |
| Activity calendar | CalendarObjectId / CalendarName | CalendarObjectId / CalendarName | ID vs display name |
| Activity type | Type | Type | Enum values must be compared by exact version |
| Percent complete type | PercentCompleteType | PercentCompleteType | Duration / Units / Physical |
| Resource assignment relation | ResourceAssignmentObjectId etc. | ResourceAssignmentObjectId etc. | Separate business object, not embedded Activity row |

**Version qualification:** EPPM column names above are from the V26 REST contract. Professional names above are from the published Professional API field reference for Release 24; they are included to identify likely field correspondences, not to assert V26 API parity. A V26 Professional field summary or runtime introspection is still required to close this crosswalk.

## 5. Source register — Oracle primary sources

### P6 EPPM V26
1. EPPM V26 Guides: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/guides.html
2. EPPM V26 Data Dictionary PDF (January 2026): https://docs.oracle.com/cd/G48897_01/English/User_Guides/p6_eppm_data_dictionary/p6_eppm_data_dictionary.pdf
3. EPPM V26 Schema Guides (26.4 / 26.1 core schema and reporting schema): https://docs.oracle.com/cd/G48897_01/102094.htm
4. EPPM V26 Extended Schema Guide (January 2026): https://docs.oracle.com/cd/G48897_01/English/Mapping_and_Schema/extended_schema/extended_schema.pdf
5. EPPM V26 REST API all endpoints: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/rest-endpoints.html
6. EPPM V26 REST Activity service: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/api-activity.html
7. EPPM V26 REST Update Activity schema: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-activity-put.html
8. EPPM V26 REST UDFType fields: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-ws-ref/udftypefields-42370a.html
9. EPPM V26 REST Update UDFTypes: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-udftype-put.html
10. EPPM V26 Integration API UDFType: https://docs.oracle.com/cd/G48897_01/English/Integration_Documentation/p6_eppm_api_reference/com/primavera/integration/client/bo/object/UDFType.html
11. EPPM V26 PDS all endpoints: https://docs.oracle.com/en/industries/construction-engineering/primavera-administration/26/data-service/api-primaveradataservice.html
12. PDS V26 table metadata: https://docs.oracle.com/en/industries/construction-engineering/primavera-administration/26/data-service/op-dataservice-metadata-tables-get.html
13. PDS V26 column metadata: https://docs.oracle.com/en/industries/construction-engineering/primavera-administration/26/data-service/op-dataservice-metadata-columns-tablename-get.html
14. EPPM V26 Industry-Specific Field Names: https://docs.oracle.com/cd/G48897_01/p6help/en/48181.htm
15. EPPM V26 Publication Services / Extended Schema concepts: https://docs.oracle.com/cd/G48897_01/English/Admin/p6_eppm_reporting/49312.htm

### P6 Professional V26
16. Professional V26 Guides: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/guides.html
17. Professional V26 All Guides: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/books.html
18. Professional V26 User Guide (June 2026): https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/p6_pro_user.pdf
19. Professional V26 Help TOC: https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm
20. Professional V26 UDF data types and subject areas: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/p6_pro_user.pdf
21. Professional V26 Report Editor window: https://docs.oracle.com/cd/G48902_01/English/admin/p6_pro_reporting/report_editor_window.htm
22. Professional V26 Industry terminology note (EPPM Help): https://docs.oracle.com/cd/G48897_01/p6help/en/48181.htm
23. Professional V26 Introducing P6 Professional / database context: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-help/introducingp6professional-20853a.html

### Explicitly version-limited API references (not treated as V26 proof)
24. Professional API FieldSummary, Release 24: https://docs.oracle.com/cd/F88968_01/English/Integration/p6_pro_api_reference/FieldSummary.html
25. Professional API UDFType, Release 24: https://docs.oracle.com/cd/F88968_01/English/Integration/p6_pro_api_reference/com/primavera/integration/client/bo/object/UDFType.html
26. Combined P6 EPPM Web and Professional API Programming Guide, Version 25: https://docs.oracle.com/cd/G18296_01/English/Integration/p6_and_p6_pro_api_programming/p6_and_p6_pro_api_programming.pdf

## 6. Remaining gaps — explicitly open

This matrix does not claim full field-by-field parity. The following require more evidence:
- Version-matched P6 Professional V26 API Javadoc/FieldSummary and all business-object class definitions.
- Full EPPM REST V26 versus Professional API field diff for Activity, WBS, Project, Resource, ResourceAssignment, Calendar, Baseline, Risk, Document, Timesheet, UDFType and UDFValue.
- Exact field lengths, nullability, requiredness, enumerations, default values, read/write flags, and operation-level constraints for both APIs.
- Physical database table/column/PK/FK mapping for EPPM 26.4 and Professional V26 standalone schemas; EPPM ZIP downloads are published but the schema packages were not parsed in this documentary pass.
- Whether a separate V26 Professional schema package is distributed outside the public Professional V26 guide catalogue.
- Runtime confirmation of the P6 Professional API when connected to Professional versus EPPM database.
- Full UDF subject-area/type parity, including formula, code, secure-code, conditional indicator and summary methods.
- SQL Server Extended Schema/report security enforcement and exact query patterns for each report consumer.
- Field-level differences in financial periods, stored period actuals, summary fields, resource spreads, future-period buckets, risk response plans and timesheet audit fields.
- Exact behavior of Extended Schema publication lag, incremental publication timestamps, deleted records and project-level security joins.
- Direct test of REST vs Java API serialization, date/time zones, duration units, enumerations, and ID semantics.

## 7. Boundary and conclusion

This is a **documentation-only reference comparison**. It does not create or change a product capability, database, API, schema, CUBI workspace, menu, data flow, application code, scheduler or agent-owned task.

**Conclusion:** The source material supports a shared P6 business-object model with different documentation and integration surfaces. EPPM V26 clearly documents the transactional REST API, the Data Service metadata/query surface, and an Extended Schema reporting layer. Professional V26 documents standalone and EPPM-connected database contexts, its desktop reporting/field UI, and a Java API lineage, but its published V26 guide inventory does not expose a version-matched Professional API field schema or standalone schema download. Therefore, broad business-field correspondence can be documented, but an exhaustive physical-column/API-field parity claim is not yet supportable from the public V26 materials reviewed.
