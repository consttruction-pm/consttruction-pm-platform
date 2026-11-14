# P6 EPPM V26 vs P6 Professional V26 — Resource/Role Planning, Teams & Assignments Matrix

**Status:** V26 documentary comparison of high-level planning and activity-level assignment  
**Scope:** Resource/role teams, project/WBS-level resource planning, assignment search, availability, commitments, unit allocation, splitting, future-period planning, resource curves, and usage analysis.  
**Out of scope:** Creating resource teams, assigning resources, editing allocation spreadsheets, changing project data, or modifying any workspace/product.  
**Version rule:** EPPM Help/User Guide and Professional Help/User Guide V26. The Professional Help TOC lists resource/role assignments, resource curves, manual future-period bucket planning and resource usage profiles; it does not list EPPM-style Resource Teams, Role Teams or Resource Planning pages. This is documented UI-surface evidence, not proof of internal API absence.

## 1. Executive findings

1. **Both products support enterprise Resources and Roles, activity assignments, rates, calendars, resource curves, leveling, and resource/role usage analysis.** Those should not be marked EPPM-only.
2. **EPPM V26 adds separate Resource Teams and Role Teams.** These group resources and roles independently of resource/role codes; they can be Global or User teams and can be used to group data on Planning, Assignments and Analysis pages. The Professional V26 Help TOC does not list corresponding team objects or pages.
3. **EPPM Resource Planning is a high-level project/WBS planning workflow.** It assigns labor resources or roles to a project or WBS before activities are fully defined, allocates units across the project timescale, searches for resources by role/proficiency/availability, and splits allocations. Professional V26 documents activity-level resource/role assignments and resource usage profiles, but not the same project/WBS Resource Planning page.
4. **EPPM Resource Planning is not live transactional resource availability.** The Planning spreadsheet uses published and summarized data; changes made to assignments after the last publish/summarize are not reflected until the next publication and summarization. Resource availability is recalculated as planning allocations are edited, but the base project/resource data is from the last published/summarized state.
5. **Professional Resource Usage Profile has a different aggregation model.** It can show a specific project or all projects, view by resource or role, include limits/overallocation/availability, and use live data for open projects plus stored summary data for closed projects. This is related to EPPM Resource Analysis but not a substitute for project/WBS planning.
6. **Future-period planning exists in both products but is not the same page.** EPPM places Future Period Planning under Resource Assignments; Professional documents Manually Planning Future Period Assignments and its own future-period bucket layouts/FAQ.
7. **Do not equate teams with codes.** EPPM Resource/Role Teams group multiple resources/roles for analysis; Resource Codes and Role Codes classify individual objects. Professional V26 documents codes and hierarchies but not the EPPM team grouping pages.

## 2. Resource and role capability matrix

| # | Topic | P6 EPPM V26 | P6 Professional V26 | Finding / evidence status |
|---:|---|---|---|---|
| 1 | Resource dictionary | Global resource records with labor, nonlabor and material resources | Enterprise Resources with labor, nonlabor and material types | Shared resource master capability. CONFIRMED |
| 2 | Role dictionary | Global roles with role codes/rates and resource-role associations | Roles with role codes/rates and resource-role associations | Shared role master capability. CONFIRMED |
| 3 | Resource-to-role association | Resource can be assigned one or more roles; proficiency and primary role can be set | Resource can have roles and proficiency/primary role associations | Shared model. CONFIRMED |
| 4 | Activity-level resource assignment | Assign resources to activities and multiple activities; configure activity resource details | Assign resources to activities, directly or by role | Shared core capability. CONFIRMED |
| 5 | Activity-level role assignment | Assign roles to activities and later staff with a resource | Assign roles to activities and replace/staff as needed | Shared capability. CONFIRMED |
| 6 | Resource rates | Multiple resource rate types, effective dates and assignment rate source | Multiple price/unit rates over time and assignment rate source | Shared rate model; exact defaults and rate-type mapping require field-level test. CONFIRMED |
| 7 | Role rates | Role rate types and effective-dated rates | Price/Unit rates for roles over time | Shared concept with label differences. CONFIRMED |
| 8 | Resource calendars | Assign calendars to resources and configure working time | Assign calendars to resources | Shared capability. CONFIRMED |
| 9 | Resource curves | Define resource curves and assign to resource/role assignments | Define resource curves and assign to resource/role assignments | Shared capability; do not mark EPPM-only. CONFIRMED |
| 10 | Resource leveling | Configure priorities/options and level project resources | Configure leveling priorities and level selected/all resources | Shared capability; detailed engine settings are covered by scheduling matrix. CONFIRMED |
| 11 | Resource analysis | Dedicated Analysis page for resource and role usage/cost, histograms, stacked histograms, area and pie charts | Resource Usage Profile/Spreadsheet in Activities bottom layout; by Resource or By Role | Related analytics; different UI and data path. CONFIRMED |
| 12 | Resource Usage Profile across projects | Resource Analysis page shows usage/allocations from published/summarized project data | Resource Usage Profile supports Show All Projects, By Resource, By Role, availability, limits, overallocations and past-period actuals | Both aggregate across projects; Professional's documented profile behavior is distinct. CONFIRMED |
| 13 | Resource/Role Teams | Separate Resource Teams and Role Teams tabs in Resources > Administration | No Resource Teams or Role Teams page in Professional V26 Help TOC | EPPM-specific documented team objects. CONFIRMED (Help inventory) |
| 14 | Resource Team purpose | Groups personnel into meaningful groups for staffing, allocation and project communication | Professional uses Resource Codes/filters and role/resource hierarchies; no matching team grouping page documented | Team grouping vs code classification. CONFIRMED |
| 15 | Role Team purpose | Groups related roles; can display total team units or individual role values | Professional can group by role hierarchy/codes; no matching Role Team object/page documented | EPPM-specific documented role grouping. CONFIRMED |
| 16 | Team scope | Global teams available to all users; User teams visible only to creator/current user | No equivalent Resource/Role Team global/user scope documented in Professional V26 Help | EPPM team scope model. CONFIRMED |
| 17 | Multiple team membership | A resource can belong to multiple resource teams; a role can belong to multiple role teams | Resource/role codes can classify objects; team membership model not documented | Different grouping model. CONFIRMED |
| 18 | Team grouping in analysis | Planning, Assignments and Analysis pages can group by Resource Team or Role Team; Resource Team Summary portlet can show team totals and members | Resource Usage Profile groups by resource, role, resource code/role code or hierarchy; no team grouping option documented | EPPM-specific grouping surface. CONFIRMED |
| 19 | Resource Planning page | Dedicated Planning page for project-level and WBS-level resource/role allocations | Professional V26 Help TOC has no Resource Planning page; has activity assignments and resource usage profile | High-level planning page difference. CONFIRMED (Help inventory) |
| 20 | Planning before activities exist | EPPM can assign resources or roles to a proposed project/WBS before detailed activity plans exist | Professional assigns resources/roles to activities; no matching project/WBS planning page documented | EPPM supports earlier-stage resource demand planning. CONFIRMED |
| 21 | Project/WBS-level assignment | Assign labor resource or role to project or WBS element | Professional resource assignment workflow is activity-oriented; no equivalent high-level project/WBS planning page documented | EPPM-specific documented planning capability. CONFIRMED |
| 22 | Material resources in planning | Resource Planning page cannot assign material resources; it supports labor resources or roles | Professional can assign material resources to activities | Different scope: EPPM high-level Planning excludes material; Pro activity assignment supports material. CONFIRMED |
| 23 | Role-first planning | Assign role to project/WBS, then staff the role later with a resource | Professional assigns roles to activities and resources; no project/WBS role planning page documented | EPPM high-level staffing workflow. CONFIRMED |
| 24 | Search for resource to assign | Search by start/finish, requested units, roles, proficiency, resource/resource code; choose Match All or Any criteria | Professional can filter resources/roles and select from resource/role dictionaries; no same project/WBS Assign by Search page documented | EPPM has dedicated capacity-aware planning search. CONFIRMED |
| 25 | Search criteria templates | EPPM can save resource search criteria as templates for reuse | No corresponding project/WBS resource search template page in Professional V26 Help | EPPM planning search feature. CONFIRMED |
| 26 | Committed allocation | Committed checkbox indicates whether planned units are committed; only committed assignments count in high-level availability | Professional resource assignments use remaining/planned units and project/resource preferences; no equivalent project/WBS committed flag in the cited V26 workflow | EPPM-specific planning commitment state. CONFIRMED |
| 27 | Availability recalculation | Resource availability recalculates live as Planning spreadsheet allocation values are edited | Professional Resource Usage Profile recalculates/reflects resource assignment and summary values according to view/preferences | Related but different recalculation context. CONFIRMED |
| 28 | Published/summarized data dependency | Planning availability is based on last published and summarized project state; later assignment changes are not reflected until next publish/summarize | Professional Resource Usage Profile can use live data for open projects and stored summary for closed projects | Material freshness difference. CONFIRMED |
| 29 | Planning allocations in other pages | Project preference controls whether Planning allocations are included in other allocation pages such as Resource Usage after summarize/publish | Professional usage profiles show activity/resource assignment data and summary data, not the same Planning allocation inclusion switch | EPPM-specific inclusion setting. CONFIRMED |
| 30 | Unit allocation | EPPM can allocate total units to resource/role and spread units across time periods for project/WBS | Professional assigns units to activity resource/role assignments and supports future-period bucket entry | Similar unit concepts; different assignment level. CONFIRMED |
| 31 | Split resource assignment | EPPM Planning page can split overloaded resource assignments by moving a percentage of total units to another resource | Professional can replace resources and reassign activity assignments; no equivalent high-level Planning split dialog documented | EPPM project/WBS planning tool. CONFIRMED |
| 32 | Planning spreadsheet export | Export resource planning spreadsheet from the Planning page | Professional exports resource assignment views and can export usage data | Similar export outcome, different sheet/data structure. CONFIRMED |
| 33 | Future Period Planning | Future Period Planning is under Resource Assignments; supports future period values/layouts for assignments | Manually Planning Future Period Assignments with future-period bucket planning layouts and FAQ | Shared feature family; workflows and constraints differ. CONFIRMED |
| 34 | Resource assignment curves | Curves can be assigned from Resource Assignments page and Activities page | Curves can be assigned to resource/role assignments from Activities and resource views | Shared capability. CONFIRMED |
| 35 | Resource Usage profile dimensions | Resource Analysis page supports resource and role usage/cost and team grouping | Professional profile can show quantity/cost, time scale, past period actuals, actual-to-date, early/late dates, banana curves, overtime, limits and availability | Professional profile has rich display options; not evidence of EPPM feature absence. CONFIRMED |
| 36 | Open vs closed project data | EPPM resource planning uses published/summarized data and last-published state | Professional all-project profile can combine live open-project data with summary past-period actuals for closed projects | Different data freshness and aggregation rules. CONFIRMED |
| 37 | Unstaffed activities | EPPM Team Usage and Resource Analysis support assigning resources to unstaffed activities | Professional can assign resource/role to activities and use role staffing | Shared staffing goal; different Team Usage/Planning surfaces. CONFIRMED |
| 38 | Resource Team dashboard | Resource Team Summary portlet can show team resources, primary roles and active project count | No matching Resource Team Summary portlet in Professional V26 Help | EPPM web dashboard integration. CONFIRMED |
| 39 | Resource/Role code vs team | EPPM supports both codes and teams; codes classify, teams group members for analysis | Professional supports Resource Codes and Role Codes, not the documented EPPM team object pages | Do not map team membership directly to code assignment. CONFIRMED |
| 40 | Resource security | EPPM resource access is a separate security layer from project/OBS access | Professional has resource security and project/user security, with database-context differences | Shared security concern; detailed security matrix is separate. CONFIRMED |

## 3. High-level Resource Planning semantics

### 3.1 Project/WBS allocation is not an Activity assignment

EPPM Resource Planning lets a planner assign a labor resource or role to a project or WBS before detailed activities exist. This creates high-level demand over the project timescale. When the detailed plan becomes available, resource/role assignments can be managed at activity level. The two assignment levels should not be merged into one “resource assignment” capability row.

### 3.2 Committed vs uncommitted

The EPPM Planning page distinguishes committed and uncommitted allocations. Only committed assignments are considered when calculating high-level resource availability. The planner can preserve tentative demand without treating it as committed resource consumption.

### 3.3 Publication freshness

The EPPM Planning spreadsheet calculates availability from published and summarized data. If activity/resource assignment data changes after the last publish/summarize operation, the Planning page does not immediately reflect those changes. A new publication and summarization is required. This is not the same as live resource availability recalculated while editing Planning allocations.

### 3.4 Search by proficiency and requested units

EPPM can search for a suitable resource based on a time window, requested units, roles, proficiency levels, resource and resource code. Search criteria can require all or any selected conditions and can be saved for reuse. This is a high-level staffing workflow, not just a filter over the resource dictionary.

### 3.5 Resource Teams are not Resource Codes

A Resource Team groups resources and can be used as a hierarchy in Planning, Assignments, Analysis and dashboard portlets. A Resource Code classifies each resource. A resource can belong to multiple teams; code assignments are separate classification values. The same distinction applies to Role Teams vs Role Codes.

## 4. Source register — Oracle primary sources

### P6 EPPM V26
1. EPPM V26 Help TOC — Resources: https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm
2. Resource Planning: https://docs.oracle.com/cd/G48897_01/p6help/en/100977.htm
3. About Resource Planning: https://docs.oracle.com/cd/G48897_01/p6help/en/100875.htm
4. Assigning Resources or Roles to Projects or WBS Elements: https://docs.oracle.com/cd/G48897_01/p6help/en/100879.htm
5. Searching for a Resource to Assign: https://docs.oracle.com/cd/G48897_01/p6help/en/101099.htm
6. Allocating Units to Resources or Roles: https://docs.oracle.com/cd/G48897_01/p6help/en/100881.htm
7. Splitting Resource Assignments: https://docs.oracle.com/cd/G48897_01/p6help/en/101092.htm
8. Resource Teams: https://docs.oracle.com/cd/G48897_01/p6help/en/43339.htm
9. About Resource Teams: https://docs.oracle.com/cd/G48897_01/p6help/en/44162.htm
10. Role Teams: https://docs.oracle.com/cd/G48897_01/p6help/en/43338.htm
11. About Role Teams: https://docs.oracle.com/cd/G48897_01/p6help/en/44163.htm
12. EPPM V26 User Guide — Defining Resources and Roles: https://docs.oracle.com/cd/G48897_01/English/User_Guides/p6_eppm_user/9582.htm
13. EPPM V26 User Guide — Resource Planning and Team operations: https://docs.oracle.com/cd/G48897_01/English/User_Guides/p6_eppm_user/p6_eppm_user.pdf

### P6 Professional V26
14. Professional V26 Help TOC: https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm
15. Professional V26 User Guide — Resource Usage Profile: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/p6_pro_user.pdf
16. Professional V26 Help — Future Period Bucket Planning (listed under Manually Planning Future Period Assignments): https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm
17. Professional V26 Help — Resource Curves: https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm

## 5. Remaining gaps — explicitly open

- Full EPPM Resource/Role Team REST and Integration API field mapping against any V26 Professional API equivalent.
- Exact V26 Professional UI behavior for filtered resource views, role proficiency search and assignment replacement in every database context.
- Complete EPPM Resource Planning privileges at project and WBS levels, including who can view vs add/modify/delete.
- Exact interaction between Committed allocations, role search criteria, availability and other resource analysis pages.
- Full EPPM Resource Planning publication/summarization service dependencies and stale-period behavior.
- Detailed Future Period Planning field-by-field comparison, including assignment types, time periods, locked periods, cost/units, actuals and import/export.
- Numerical resource availability comparison for the same data in EPPM Planning, EPPM Resource Analysis and Professional Resource Usage Profile.
- Full resource curves and rate-type field comparison, including multiple effective dates, role/resource assignment rate sources and currencies.
- Resource team and role team deletion/transfer behavior and effect on saved layouts/filters.
- Independent page-by-page census of all Resource/Role topics in both V26 Help trees; this matrix is a focused comparison, not a complete source-corpus audit.

## 6. Boundary and conclusion

This is a **documentation-only reference comparison**. No resource, role, team, project/WBS allocation, activity assignment, curve, rate, calendar or future-period value was created or changed. No product feature, CUBI workspace, code, schema, menu, data flow or agent-owned task was modified.

**Conclusion:** P6 Professional V26 and P6 EPPM V26 share the core resource/role assignment, rate, calendar, curve, leveling and usage-analysis capabilities. EPPM V26 adds explicit Resource Teams/Role Teams and a separate high-level Resource Planning page that allocates labor resources or roles to projects/WBS before detailed activities exist. Its Planning availability is based on published/summarized data and includes committed/uncommitted allocation semantics, resource search by role/proficiency/availability, unit spreading and split assignments. Professional's Resource Usage Profile and manual future-period bucket planning are valuable but distinct; they do not constitute the same documented project/WBS planning workflow.
