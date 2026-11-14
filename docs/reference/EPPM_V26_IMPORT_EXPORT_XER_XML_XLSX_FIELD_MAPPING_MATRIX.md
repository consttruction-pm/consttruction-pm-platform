# P6 EPPM V26 vs P6 Professional V26 — Import/Export, XER/XML/XLSX Field Mapping Matrix

**Status:** V26 documentary comparison; shared Oracle mapping guides plus product-specific import behavior  
**Scope:** XER, Primavera XML, XLSX/Excel, supported exchange formats, mapping rules, import actions, project/enterprise data, and documented Professional/EPPM exceptions.  
**Out of scope:** Running imports, modifying project data, writing conversion code, changing any application/workspace, or performing agent-owned work.  
**Version rule:** EPPM Importing and Exporting Guide and XER/XLSX Data Map Guides are V26. The XER and XLSX data-map guides explicitly say that “P6 EPPM” includes P6 Professional and label application-specific content. Professional-specific workflow statements are drawn from V26 EPPM Help topics that explicitly compare P6 and P6 Professional. Older Professional Import/Export guides are cited only for supplementary detail, not to override V26 behavior.

## 1. Executive findings

1. **The V26 XER and XLSX field-map guides are shared product-family references.** They explicitly state that “P6 EPPM” includes P6 Professional and mark differences. Therefore, it is incorrect to treat these mapping guides as EPPM-only.
2. **The XER format is shared, but import behavior is not identical.** V26 Help explicitly states that XML import options in P6 have additional categories/statuses/locations/WP&Docs options compared with Professional, Professional XER import has less configuration than its XML import, and Professional project import requires Admin Superuser or Project Superuser while EPPM accepts users with appropriate permissions.
3. **XER contains product-specific table/field data.** The V26 Project XER map marks PROJEST (Estimate History) and RISKTYPE as Professional-only, while publication priority and last scheduled date are EPPM-only fields. This is explicit evidence of differences in exported data structures, not merely UI labels.
4. **Some field labels differ while the exchange field is shared.** XLSX mapping maps EPPM Planned Duration and Professional Original Duration/Planned Duration to the same `target_drtn_hr_cnt`; Budgeted/Planned Cost to `target_cost`; and Budgeted/Planned Units to `target_qty`. This is a direct example of UI terminology not implying separate fields.
5. **Risk export/import needs special care.** Oracle states that Professional risks are stored in the ProjRisk table and included in XER; when imported into EPPM they are not visible in P6 EPPM, and Oracle recommends XML for risk exchange.
6. **Secure codes are not symmetric in XER.** Professional does not export secure codes; EPPM imports secure codes only when the importing user has the required add/delete secure-code privileges.
7. **Import/export should not be described as lossless or round-trip equivalent without testing.** Calculated/non-importable XLSX fields are ignored, field-name changes cause columns to be ignored, some global data must already exist, role-rate handling differs, and certain reference data exports differ by application.

## 2. V26 format and capability matrix

| # | Format / workflow | P6 EPPM V26 | P6 Professional V26 | Finding / evidence status |
|---:|---|---|---|---|
| 1 | Shared XER map scope | V26 XER Project Data Map Guide | The same guide explicitly includes P6 Professional | Shared mapping source; not EPPM-exclusive. CONFIRMED |
| 2 | Shared XLSX map scope | V26 XLSX Data Map Guide | The same guide explicitly includes P6 Professional | Shared mapping source; not EPPM-exclusive. CONFIRMED |
| 3 | XER purpose | Native Primavera exchange format for projects, baselines and associated data | Native Primavera PM XER format | Shared format; product-specific fields/import rules still apply. CONFIRMED |
| 4 | Primavera XML purpose | Exchange project and baseline information; supports multiple projects and zip package | Professional can import/export P6 XML | Shared exchange family. CONFIRMED |
| 5 | XLSX project/activity exchange | V26 field map provides subject-area sheets and exact field-name mappings | Same V26 field map includes Professional display labels | Shared exchange field map. CONFIRMED |
| 6 | Other EPPM V26 formats | CPP, IPMDAR, Microsoft Project MPX/XML, UN/CEFACT, Unifier Schedule Sheet, XER Project/Resource/Role, XLSX | Professional V26 public guides do not publish an equally complete separate map inventory; the shared XER/XLSX guides apply to Pro | EPPM has a broad named guide inventory; Pro applicability is format-specific. CONFIRMED |
| 7 | Import/export privilege | Global and Project level privileges control import/export | Project export requires Export Project Data privilege; XER project import is limited to Admin Superuser or Project Superuser | Product workflow/security differs. CONFIRMED |
| 8 | XER project import actions | Create New, Add Into Existing Project, Replace Existing, Update Existing | Professional Import dialog has its own import configuration and action workflow | Do not assume identical dialog options/configuration. CONFIRMED |
| 9 | XER import configuration breadth | P6 uses the same set of import options for XER as for XML | Professional XER import allows less configuration than Professional XML import | Direct workflow difference. CONFIRMED |
| 10 | XML import option categories | P6 XML options include Document Categories, Document Statuses, Locations, and Work Products & Documents | Those extra categories are not included in the corresponding Professional XML import options | Direct product-specific import difference. CONFIRMED |
| 11 | Project import authorization | Any user with appropriate permissions can import projects | Only Admin Superuser global profile or Project Superuser project profile can import projects | Strong security/workflow difference. CONFIRMED |
| 12 | Export project checksum | P6 adds SHA-256 checksum to XML/XER exports and validates it during import | V26 Professional Help parity for the checksum mechanism is not stated in the compared Professional guide inventory | EPPM behavior confirmed; Professional parity PARTIALLY VERIFIED |
| 13 | XER secure-code export | Secure codes are represented in map, with privilege-gated import | Professional does not export secure codes | Explicit asymmetric behavior. CONFIRMED |
| 14 | XER secure-code import | EPPM imports secure codes only if importing user has privileges to add and delete secure codes | Pro does not export secure codes; no equivalent Pro import rule should be inferred | Product difference. CONFIRMED |
| 15 | XER risk data | P6 EPPM supports risks, but ProjRisk XER rows imported from Professional are not visible in P6 EPPM | Professional risks are stored in ProjRisk and included in XER | XER presence does not guarantee target UI visibility; Oracle recommends XML for risk transfer. CONFIRMED |
| 16 | Professional risk table | EPPM has its own ProjectRisk/RiskResponsePlan model; ProjRisk rows imported from Professional XER are not visible in P6 EPPM | PRORISK (Risks) table is explicitly Professional-only | The same exchange file can carry a Professional-only risk structure that EPPM does not display. CONFIRMED |
| 17 | Risk-type lookup table | EPPM V26 XER map does not label RISKTYPE as an EPPM table | RISKTYPE table is explicitly Professional-only | Product-specific XER table. CONFIRMED |
| 18 | Estimate history | Not identified as the matching EPPM table in the V26 map | PROJEST (Estimate History) is explicitly Professional-only | Product-specific XER table. CONFIRMED |
| 19 | Project risk-level field | EPPM risk model uses its own risk objects/matrices | XER map marks project `risk_level` as Professional-only | Field-level difference; do not infer all risk functionality is Pro-only. CONFIRMED |
| 19 | Project publication priority | EPPM project field Publication Priority | XER map labels `px_priority` as EPPM-only | EPPM-specific publication field. CONFIRMED |
| 20 | Last Publish Project date | EPPM has publication-service timestamps/controls | XER map labels `px_last_update_date` as Professional-only, “Last time Publish Project was run on this project” | The field is a Professional-only XER field despite its publication wording; do not map it to EPPM Publication Priority. CONFIRMED |
| 21 | Last scheduled date | EPPM XER map labels Last Scheduled Date as EPPM-only | No same field label is marked Professional-only in the cited map | EPPM-specific field. CONFIRMED |
| 22 | Project summarization fields | EPPM publication/summarization is server-managed and uses its own service model | XER map marks Summarized Data Date and Contains Summarized Data Only as Professional-only | Distinct project data flags. CONFIRMED |
| 23 | Project MS Project-managed flag | Not marked as the corresponding EPPM-only field | XER map marks `msp_managed_flag` as Professional-only | Product-specific exchange metadata. CONFIRMED |
| 24 | Activity ID mapping | `task_code` | `task_code` | Same XER/XLSX field; do not confuse with unique task_id/ObjectId. CONFIRMED |
| 25 | Activity unique identifier | `task_id` maps to Unique ID | Same shared mapping | Distinct from Activity ID. CONFIRMED |
| 26 | Activity Name | `task_name` | `task_name` | Same field mapping. CONFIRMED |
| 27 | Activity Status | `status_code` | `status_code` | Same mapping; when status appears in expense/assignment/relationship sheets it may be reference-only and ignored on import. CONFIRMED |
| 28 | Activity % Complete | `complete_pct` | `complete_pct` | Same XLSX mapping. CONFIRMED |
| 29 | Planned Duration terminology | Planned Duration | Original Duration or Planned Duration | Both map to `target_drtn_hr_cnt`; one exchange field. CONFIRMED |
| 30 | Planned Start/Finish | Activity planned date fields map through common exchange fields | Same mapping | Shared exchange concept; check date semantics and scheduling recalculation. CONFIRMED |
| 31 | Actual Start/Finish | `act_start_date`, `act_end_date` | Same mapping | Shared exchange fields. CONFIRMED |
| 32 | Remaining Duration | `remain_drtn_hr_cnt` | Same mapping | Shared exchange field. CONFIRMED |
| 33 | Primary/Secondary Constraints | `cstr_type`, `cstr_date`, `cstr_type2`, `cstr_date2` | Same mapping | Shared constraint fields. CONFIRMED |
| 34 | Calendar | `clndr_id` | Same mapping | Shared exchange field; target database calendar resolution still matters. CONFIRMED |
| 35 | WBS Code | `wbs_id` | Same mapping | Shared mapping. CONFIRMED |
| 36 | Activity Codes | `actv_code_XXXX_id` | Same mapping | Shared mapping; global dictionaries must already exist where required. CONFIRMED |
| 37 | Project Codes | `proj_catg_XXXXX_id` | Same mapping | Shared field mapping; XLSX map states project codes cannot be imported/updated through that route. CONFIRMED |
| 38 | UDFs | `user_field_XXXX` | Same mapping | Shared exchange family; exact UDF definition/type must be compatible in target. CONFIRMED |
| 39 | Expense Planned Cost | Planned Cost | Budgeted Cost or Planned Cost | Both map to `target_cost`. CONFIRMED |
| 40 | Expense Planned Units | Planned Units | Budgeted Units or Planned Units | Both map to `target_qty`. CONFIRMED |
| 41 | Resource Assignment Planned Cost/Units | Planned Cost/Units | Budgeted or Planned Cost/Units | Same exchange fields `target_cost`, `target_qty`. CONFIRMED |
| 42 | Relationship fields | Lag `lag_hr_cnt`, predecessor `pred_task_id`, relationship type `pred_type`, successor `task_id` | Same mapping | Shared relationship field mapping. CONFIRMED |
| 43 | Resource ID/Name | `rsrc_short_name`, `rsrc_name` | Same mapping | Shared mapping. CONFIRMED |
| 44 | Resource assignment role and resource IDs | `rsrc_id`, `role_id` | Same mapping | Shared mapping; assignments may have distinct resource/role identities. CONFIRMED |
| 45 | Project code weighting | EPPM field map does not label project code type/value weights as Pro-only | `max_proj_catg_wt`, `proj_catg_type_wt`, and `proj_catg_wt` are marked Professional-only | Pro-specific code-weight fields. CONFIRMED |
| 46 | PHASE / Current Phase / WBS Category | PHASE data is visible as Current Phase project code | The same PHASE data is visible as WBS Category column | One underlying exchange table serves different product UI concepts. CONFIRMED |
| 47 | Location export scope | Exports only Locations assigned to the projects being exported, their activities and resources | Exports all Locations defined in Enterprise Data regardless of project use | Different export scope; can create additional reference data in Professional exports. CONFIRMED |
| 48 | Role price labels | Standard Rate, Internal Rate, External Rate | Price/Unit1, Price/Unit2, Price/Unit3 | Same mapped role rate fields with different UI labels. CONFIRMED |
| 49 | Resource rate import behavior | Updates resource rates when effective date matches; creates new rates when effective date does not match | Overwrites resource rates and their respective effective dates during import | Significant data overwrite behavior difference. CONFIRMED |
| 50 | XLSX calculated fields | Columns marked with asterisk are calculated/non-importable and ignored on import | Same shared guide applies to Professional | Do not treat all exported columns as writable. CONFIRMED |
| 51 | XLSX field-name integrity | If a field name is modified, column is ignored during import | Same shared rule | Preserve exact field names; captions can differ only where guide allows. CONFIRMED |
| 52 | XLSX global data | Cannot import global data that does not already exist in EPPM database | Shared mapping guide says same for P6 family; Pro-specific dictionary behavior needs target-context verification | Shared constraint in the V26 map. CONFIRMED |
| 53 | XLSX project codes | Project codes cannot be updated or imported through the XLSX data-map process | Same shared map | Do not treat project-code columns as writable XLSX data. CONFIRMED |
| 54 | XLSX cost account hierarchy | Hierarchical information is not exported; Cost Account IDs must be unique across the entire dictionary | Same shared XLSX map | Non-unique cost account IDs can cause overwrite/collision on import. CONFIRMED |
| 55 | XLSX activity status in non-Activity sheets | Status shown in Expenses, Resource Assignments and Relationships is reference-only and ignored during import | Same shared map | Update status through Activities subject area only. CONFIRMED |
| 56 | XLSX required columns | Italicized fields are required and cannot be removed from export template/import file | Same shared map | Preserve required columns. CONFIRMED |
| 57 | Enterprise data XLSX import | Export each selected enterprise data page to separate tab; preserve rows 1-2; cannot delete enterprise data by importing XLSX | Professional SDK macro-enabled enterprise import/export was retired after 18.8; EPPM administration has dedicated XLSX enterprise-data workflow | EPPM enterprise-data workflow is not the old Professional SDK macro workflow. CONFIRMED |
| 58 | Enterprise-data delete semantics | Importing an XLSX enterprise-data file cannot delete data | No equivalent deletion-by-import behavior documented for Pro V26 | Do not use enterprise-data import as a delete mechanism. CONFIRMED |
| 59 | Import target dictionary | Importing Activity Owner data requires target user to exist | Same user identity resolution applies to imported owner references in the shared XER file | Reference objects must resolve in target database. CONFIRMED |
| 60 | Round-trip equivalence | Oracle warns that external tools may recalculate dates/durations and other values after export | Same warning applies to exchanges with other project-management tools | Export/import does not guarantee schedule-value identity after external recalculation. CONFIRMED |

## 3. Key XER field differences directly marked by Oracle

The V26 Project XER Data Map explicitly labels these examples:

### Professional-only structures/fields
- `PROJEST` — Estimate History table.
- `PRORISK` — Risks table.
- `RISKTYPE` — Risk Types table.
- `risk_level` — Project Risk Level.
- `sum_data_date` — Summarized Data Date.
- `sum_only_flag` — Contains Summarized Data Only.
- `msp_managed_flag` — MS Project Managed Flag.
- `px_last_update_date` — Last time Publish Project was run on this project.
- `ts_rsrc_vs_inact_actv_flag` — Resource can view activities from an inactive project.
- Project-code weighting fields such as `max_proj_catg_wt`, `proj_catg_type_wt`, and `proj_catg_wt`.

### EPPM-only structures/fields
- `px_priority` — Publication Priority.
- `last_schedule_date` — Last Scheduled Date.
- `rsrc_private` — Personal Calendar.

### Shared fields with different product labels
- Planned Duration vs Original Duration.
- Planned Cost vs Budgeted Cost.
- Planned Units vs Budgeted Units.
- Standard/Internal/External Rate vs Price/Unit1/2/3.
- Current Phase vs WBS Category.

These are stronger evidence than a generic feature checklist because Oracle marks product scope directly in the shared mapping guide.

## 4. Import/export behavior reconciliations

### 4.1 XER and XML are not interchangeable in import-option richness

The V26 Help topic says P6 XML import options include extra options for Document Categories, Document Statuses, Locations, and Work Products & Documents compared with Professional. It also says Professional XER import allows less configuration than Professional XML import. This is a UI/workflow difference, not a statement that XER lacks the underlying data objects.

### 4.2 Risk exchange must use the right format

Professional risk rows in XER can be imported into an EPPM database but are not visible in P6 EPPM. Oracle recommends XML for risk import/export. This is a concrete example where “import succeeded” does not mean “target product can display/use the imported data.”

### 4.3 Secure-code exchange is permission-sensitive

Professional does not export secure codes. EPPM import of secure codes requires appropriate privileges. A successful XER transfer of ordinary codes does not prove secure-code transfer.

### 4.4 Resource rates are a destructive-difference risk

Professional import overwrites resource rates and effective dates. EPPM uses effective-date matching to update an existing rate or create a new rate. This difference should be tested with multiple effective dates before bulk exchange.

### 4.5 XLSX is a field-mapped worksheet format, not a generic spreadsheet import

The map identifies database field names and required columns. A renamed field header is ignored. Calculated/non-importable fields are ignored. A visible status field in the assignment or expense worksheet is reference-only. Project codes cannot be imported/updated through the mapped XLSX route. These constraints must be carried into any migration or exchange checklist.

## 5. Source register — Oracle primary sources

### V26 shared import/export references
1. V26 Importing and Exporting Guide (October 2026): https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-import-export/index.html
2. V26 Import/Export Guides index: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/importexport.html
3. V26 XER Import/Export Data Map Guide (Project): https://docs.oracle.com/cd/G48897_01/English/Mapping_and_Schema/xer_import_export_data_map_project/xer_import_export_data_map_project.pdf
4. V26 XLSX Import/Export Data Map Guide: https://docs.oracle.com/cd/G48897_01/English/Mapping_and_Schema/xlsx_import_export_data_map/xlsx_import_export_data_map.pdf
5. V26 About Importing and Exporting Data: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/aboutimportingandexportingdata-6604a.html
6. V26 Importing Projects using Primavera XER Format: https://docs.oracle.com/cd/G48897_01/p6help/en/101760.htm
7. V26 Global Data tab of XML/XER Import Template: https://docs.oracle.com/cd/G48897_01/p6help/pt_BR/94025.htm
8. V26 Creating an Import File (Enterprise Data): https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-import-export/creatinganimportfile-98155a.html
9. V26 Importing and Exporting Enterprise Data: https://docs.oracle.com/cd/G48897_01/English/Admin/p6_eppm_application_admin/112996.htm
10. V26 Configuring Microsoft Project Templates: https://docs.oracle.com/cd/G48897_01/English/Admin/p6_eppm_importing_exporting/43970.htm

### Version-limited Professional supporting references
11. Professional Importing and Exporting Guide Version 25: https://docs.oracle.com/cd/G18296_01/English/admin/p6_pro_importing_exporting/p6_pro_importing_exporting.pdf
12. Professional Importing and Exporting Guide Version 24: https://docs.oracle.com/cd/F88968_01/English/admin/p6_pro_importing_exporting/p6_pro_importing_exporting.pdf
13. Professional V26 User Guide: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/p6_pro_user.pdf

## 6. Remaining gaps — explicitly open

This matrix does not claim a complete line-by-line comparison of every data-map PDF. The following remain open:
- Complete row-by-row parse of every V26 XER table and every field in XER Project, Resource Only and Role Only maps.
- Complete row-by-row parse of V26 Microsoft Project XML, MPX, CPP, IPMDAR, UN/CEFACT and Unifier Schedule Sheet maps.
- Complete XER/XML import-option template matrix, including every per-object Insert/Update/Keep/Do Not Import/Delete option.
- Exact V26 Professional-specific import UI and permission documentation, where the current Pro V26 guide inventory does not provide a matching import/export guide.
- XML field/tag-level crosswalk against V26 REST API and Web Services Javadoc.
- Risk/response-plan XER vs XML behavior and object visibility after import, including ProjRisk vs EPPM Risk/ProjectRisk entities.
- Secure-code behavior for every code type, import action and permission combination.
- Full resource/role rate import behavior for all rate types, currencies and effective dates.
- Baseline matching, project update, Replace Existing, Add Into Existing Project and external relationship behavior under mixed database versions.
- XER/XML checksum verification behavior in Professional V26.
- Actual round-trip tests using V26 EPPM and V26 Professional connected to both database contexts.

## 7. Boundary and conclusion

This is a **documentation-only reference comparison**. No import/export operation was executed, no project/database was changed, and no product feature, CUBI workspace, menu, schema, code, or agent-owned task was created or modified.

**Conclusion:** P6 EPPM V26 and P6 Professional V26 share the XER/XLSX field-mapping framework, but not every exported structure or import workflow is identical. Oracle's shared V26 maps explicitly identify Pro-only tables/fields, EPPM-only publication fields, label aliases, and import differences. Risk visibility, secure-code export/import, location export scope, role-rate overwrite behavior, import permissions, and XML-vs-XER option richness are material differences. The next verification step is exhaustive parsing of all remaining V26 format maps and controlled round-trip testing; the current evidence does not justify a blanket “same import/export behavior” or “EPPM-only format” claim.
