# P6 EPPM V26 vs P6 Professional V26 — Portfolios, Capacity Planning & What-if Analysis Matrix

**Status:** V26 documentary comparison of portfolio grouping versus portfolio analysis  
**Scope:** Project portfolios, portfolio membership/access, filters, portfolio views/scorecards, waterline, performance thresholds, capacity planning, role allocation, scenarios, what-if projects and reflections.  
**Out of scope:** Creating portfolios/projects/scenarios, changing forecasts, editing resource allocations, or modifying any product/workspace.  
**Version rule:** EPPM Help V26 and Professional Help/User Guide V26. The Professional V26 Help explicitly documents Project Portfolios, but does not list Portfolio Analysis or Capacity Planning topics. Missing Help topics are treated as documentation-surface evidence, not proof of an internal capability being impossible.

## 1. Executive findings

1. **Both products support project portfolios.** Professional V26 has an Enterprise > Project Portfolios feature for creating a portfolio, granting user access, and adding/removing projects. It is incorrect to say Professional has no portfolio capability.
2. **EPPM V26 adds a broader portfolio analysis layer.** Its Portfolios navigation includes Portfolio Analysis, Portfolio Views, scorecards, bubble/pie/histogram charts, performance thresholds, What-if Analysis, and Capacity Planning.
3. **Professional's documented portfolio object is a project grouping, not the EPPM Portfolio Analysis workbench.** The Professional V26 Help TOC lists create/add/remove/rename/change/view portfolio tasks but no Portfolio Analysis, Portfolio Views, portfolio scorecards, or Capacity Planning pages. The Professional User Guide instead documents project-level what-if projects, reflections and resource usage profiles.
4. **Both products support filtered portfolios as well as manual portfolios.** EPPM V26 documents filter criteria and refresh behavior. Professional V26 Help explicitly states that filtered portfolios exist and cannot be manually populated from the Projects tab; the Pro filter-creation criteria and refresh cadence are not detailed in the cited V26 topic. EPPM's REST/Integration API also distinguishes UI-created filtered portfolios from API-created manual portfolios.
5. **EPPM capacity planning is role-centric and portfolio-level.** It analyzes project/role allocation and costs over time, includes net availability, waterline, role selection, forecast-date adjustments, and scenario snapshots. Professional provides resource/role analysis and usage profiles across projects, but not the same V26 portfolio capacity planning page.
6. **EPPM portfolio scenarios and Professional What-if projects/reflections are not the same.** EPPM scenarios preserve a snapshot of summarized portfolio/project/role data for comparison. Professional What-if projects are project copies with What-If status; reflections are linked copies whose selected changes can be merged back into the source project.
7. **Do not equate every scorecard with a Portfolio View scorecard.** EPPM explicitly distinguishes named Portfolio View scorecards from the general project-selection scorecard on the Capacity Planning page.

## 2. Portfolio and analysis matrix

| # | Topic | P6 EPPM V26 | P6 Professional V26 | Finding / evidence status |
|---:|---|---|---|---|
| 1 | Portfolio capability | Portfolios section with project grouping and analysis tools | Enterprise > Project Portfolios; create/manage project portfolios | Both support portfolios. CONFIRMED |
| 2 | Main navigation | Dedicated Portfolios section in P6 web navigation | Enterprise menu > Project Portfolios | Different user surface. CONFIRMED |
| 3 | Portfolio purpose | Group projects for strategic review, comparison, performance and resource capacity | Group projects and control which users can access the project portfolio | Shared grouping purpose; different depth. CONFIRMED |
| 4 | Portfolio membership | Manual selection or automatic membership by filter | Professional V26 Help explicitly references filtered portfolios and says projects cannot be manually added to them; manual portfolios accept selected projects | Both products support manual and filtered portfolio concepts; Pro filter-creation workflow is less fully documented. CONFIRMED |
| 5 | Filtered membership | EPPM documents filter criteria and a configurable stale-period refresh when a portfolio is viewed | Professional V26 Help confirms filtered portfolios exist, but the cited add-project topic does not document filter creation criteria or refresh cadence | Filtered portfolios are shared; EPPM refresh behavior is explicit, Pro configuration details remain PARTIALLY VERIFIED |
| 6 | Portfolio types/access | User, Multiple Users, Global portfolio groups; access settings on multi-user portfolios | General tab selects users with access; Shared Users are added on User Access tab | Similar audience controls, different configuration model. CONFIRMED |
| 7 | Global portfolio | Available to users with appropriate access/module privileges | Professional portfolio access can be configured for users; global portfolio icon is documented | Shared global portfolio concept. CONFIRMED |
| 8 | Portfolio details | Name, description, membership and access configured in Manage Portfolios | Name, description, user access and Projects tab | Shared metadata. CONFIRMED |
| 9 | Portfolio views | Separate Portfolio Views page manages scorecard, bubble, pie, histogram, side-by-side and stacked histogram views | No Portfolio Views page in Professional V26 Help TOC | EPPM view layer not documented in Professional. CONFIRMED (Help inventory) |
| 10 | Portfolio Analysis page | Dedicated page compares portfolio/project groups and supports scenario-based analysis | No Portfolio Analysis page in Professional V26 Help TOC | EPPM analysis workbench not documented in Professional. CONFIRMED (Help inventory) |
| 11 | Side-by-side comparison | Portfolio Analysis work area has two scorecard/view panels for comparison | Professional Project Portfolios page manages one portfolio's membership/access | Different capability scope. CONFIRMED |
| 12 | Scorecard as named view | Portfolio View Scorecard is a named reusable view, can appear on Portfolio Analysis, Capacity Planning and dashboards | Professional has tables/layouts and portfolio grouping but no named Portfolio View Scorecard page | Do not equate any table with EPPM Portfolio View Scorecard. CONFIRMED |
| 13 | Scorecard fields | Up to 30 project data fields in columns | Professional Project Portfolios has project membership, not a portfolio scorecard column designer | EPPM portfolio analysis feature. CONFIRMED |
| 14 | Scorecard editing | EPPM scorecards can edit selected project/global fields, including project codes, UDFs and responsible manager | Professional edits project data through project windows/tables; no equivalent portfolio scorecard editor documented | Different editing surface. CONFIRMED |
| 15 | Waterline analysis | Scorecard can rank projects into groups above/below a constraint limit | No waterline feature in Professional Project Portfolios Help | EPPM-specific documented analysis. CONFIRMED |
| 16 | Portfolio charts | Bubble, pie, histogram, side-by-side histogram, stacked histogram | Professional has Resource Usage Profile/Spreadsheet charts, not portfolio project-variable charts | Similar visualization concept, different data model/use. CONFIRMED |
| 17 | Bubble chart | Four fields: X, Y, bubble size, grouping field | No corresponding Portfolio View Bubble Chart in Professional V26 Help | EPPM portfolio analysis view. CONFIRMED |
| 18 | Performance thresholds | Portfolio views and project/WBS metrics support configurable performance thresholds and ranges | Professional has project thresholds/issues but no equivalent portfolio performance-threshold view documented | Distinguish project thresholds from EPPM portfolio performance thresholds. CONFIRMED |
| 19 | What-if Analysis | EPPM portfolio what-if analysis assesses potential scenarios and compares assumptions across projects | Professional supports What-If projects and reflections | Both support what-if thinking; mechanics differ. CONFIRMED |
| 20 | EPPM portfolio scenario | Captures a specific state of portfolio/project/role data for later comparison | Professional does not document the same portfolio scenario object in V26 Help | EPPM snapshot model. CONFIRMED (documented scope) |
| 21 | Scenario comparison | Compare a scenario to latest summarized data or other scenarios | Professional What-If project is a project copy with status; not the same summarized portfolio snapshot | Not equivalent. CONFIRMED |
| 22 | Professional What-If project | EPPM can create what-if projects while working in portfolio scorecards; also has portfolio scenarios | Professional defines a What-If project in project management; it is copied and assigned What-If status | Shared label, different context. CONFIRMED |
| 23 | Professional Reflection | EPPM portfolio scenarios capture analysis snapshots; not the same project-reflection merge process | Reflection is a copy linked to source; selected changes can be merged back into source while preserving active source data | Professional-specific project merge workflow. CONFIRMED |
| 24 | Capacity Planning page | Dedicated page for role allocation and cost over time across projects | No Capacity Planning page in Professional V26 Help TOC | EPPM portfolio-level page. CONFIRMED (Help inventory) |
| 25 | Capacity analysis inputs | Role estimates should be created for each project before assessing role demand/capacity | Professional resource analysis uses resource/role assignments, usage profiles and project data | Different prerequisites/data sources. CONFIRMED |
| 26 | Capacity chart types | Stacked histogram, area chart, net availability chart, spreadsheet | Resource Usage Profile supports regular/stacked histograms and spreadsheet-style analysis | Similar chart types, different workflow and semantics. CONFIRMED |
| 27 | Net availability | Shows under/over allocation for each selected role; net availability chart is units-based | Professional resource profiles show usage/availability/overallocation; no identical portfolio net-availability page documented | Related but not a one-to-one view. CONFIRMED |
| 28 | Role selector | Select/group roles by role hierarchy, role teams or search for capacity chart | Professional resource/role usage views use project/resource analysis layouts | EPPM has a dedicated portfolio role selector. CONFIRMED |
| 29 | Forecast dates | EPPM Capacity Planning Gantt shows current and forecast bars; forecast bar can be dragged to change forecast dates when latest summarized data is displayed | Professional changes project schedules/dates through project and schedule workflows; no equivalent portfolio forecast bar documented | Different analysis control. CONFIRMED |
| 30 | Scenario chart editing | When displaying scenario data, EPPM forecast bars cannot be moved; Current Bar is never movable | Professional What-If project/reflection edits project data, not EPPM scenario chart bars | Different editing semantics. CONFIRMED |
| 31 | Waterline in capacity planning | Capacity Planning supports waterline/limit analysis of role capacity and project selection | No equivalent portfolio capacity waterline page documented in Professional | EPPM-specific analysis. CONFIRMED |
| 32 | Projects vs WBS in scorecards | Portfolio View scorecards can show WBS and project rows; Capacity Planning scorecard shows project rows only | Professional portfolio object contains projects; no WBS portfolio scorecard | Important EPPM distinction between two scorecard types. CONFIRMED |
| 33 | Summarized data dependency | Capacity Planning displays latest summarized data or a selected scenario; timescale depends on project summarization | Professional Resource Analysis can use live data from open projects and stored summary data from closed projects | Different summary-data path. CONFIRMED |
| 34 | All-project analysis | EPPM can display current portfolio projects or all projects; some all-project views cannot use scenarios | Professional resource analysis can include closed projects based on User Preferences and leveling priority | Both aggregate across projects, but selection/summary rules differ. CONFIRMED |
| 35 | Create portfolio from analysis | EPPM can create a portfolio from selected projects in Portfolio Analysis or Capacity Planning | Professional creates portfolio from Enterprise > Project Portfolios and adds projects | Different entry points. CONFIRMED |
| 36 | Portfolio project filtering | EPPM can define filter criteria, including project selection based on filters; portfolio views can filter by EPS, portfolio or project code | Professional supports filtered portfolios, but exact filterable fields and refresh semantics are not established by the cited V26 Help page | Shared filter concept; EPPM field/scope details are clearer in V26 docs. PARTIALLY VERIFIED |
| 37 | Resource usage profiles | EPPM Capacity Planning is role-first, with staffed/un-staffed and project/role/code stacking | Professional Resource Usage Profile and Resource Analysis are resource/role allocation views across projects | Related resource analytics, not identical feature. CONFIRMED |
| 38 | Resource summary treatment | EPPM Capacity Planning uses latest summarized project data and scenario snapshots | Professional Resource Analysis can combine live open-project data with stored summary for closed projects, excluding What-If projects in one preference option | Different aggregation rules. CONFIRMED |
| 39 | What-if project effect on summaries | EPPM portfolio scenarios preserve data snapshots; What-If projects can be included in portfolio analysis depending status/filter | Professional What-If projects are excluded from some resource calculations and leveling, per Resource Analysis preferences | Must record project status and preference before comparing capacity results. CONFIRMED |
| 40 | Dashboard presentation | EPPM Portfolio View portlets display named portfolio views on private, multi-user or global dashboards | Professional Project Portfolios is a desktop management object; no equivalent web Portfolio View portlet documented | EPPM web/dashboard integration. CONFIRMED |
| 41 | Portfolio API create scope | V26 ProjectPortfolio REST/Integration API supports manual portfolios; filtered portfolios are based on web-app filter results and cannot be created/modified through that API workflow | Professional Java API Release 24 reference also documents filtered portfolio types and restricts API creation to manual portfolios; not V26 proof | UI capability and API capability must be compared separately. CONFIRMED for EPPM V26; Pro API version-limited |
| 42 | Manual project assignment to filtered portfolio | EPPM Help states filtered portfolios are populated from their filter and refreshed according to stale-period settings | Professional V26 Help explicitly says projects cannot be manually added to a filtered portfolio | Shared filtered-portfolio behavior. CONFIRMED |

## 3. Reconciled meanings

### 3.1 “Portfolio” is a shared noun, not one identical feature

Professional V26 supports a project portfolio object. The user can create it, select which users can access it, and add projects. That is real portfolio functionality.

EPPM V26 builds a larger analysis environment around portfolio membership: named views, scorecards, charts, scenarios, waterline, performance thresholds and capacity planning. A feature comparison that marks “Portfolio” as simply Yes/Yes misses the key depth difference; marking it EPPM-only is also incorrect.

### 3.2 EPPM portfolio scenario vs Professional What-If project vs Reflection

These three concepts should not be mapped as one field:
- **EPPM Portfolio Scenario:** snapshot of summarized project/role/portfolio data for comparison against latest or other scenarios.
- **Professional What-If Project:** copied project assigned What-If status for analysis.
- **Professional Reflection:** linked project copy; selected changes can later be merged into the source.

They have different persistence, identity, merge and calculation semantics.

### 3.3 Capacity Planning vs Resource Usage Profile

EPPM Capacity Planning is a portfolio decision-support page: role estimates, role selection, capacity/net availability, project forecast dates, scenarios, waterline and project selection all operate together.

Professional Resource Usage Profile/Resource Analysis provides resource/role usage and allocation information across projects. It can be configured to combine live data from open projects and stored summary from closed projects. That is useful and related, but it is not the same portfolio capacity-planning workflow.

### 3.4 Scorecard terminology

EPPM uses “scorecard” for both a named Portfolio View Scorecard and the general project-selection scorecard on Capacity Planning. Oracle explicitly warns these are not the same. The named Portfolio View scorecard can be reused in Portfolio Analysis and dashboards; the Capacity Planning scorecard selects projects and is limited to project rows.

## 4. Source register — Oracle primary sources

### P6 EPPM V26
1. EPPM V26 Help TOC (Portfolios and Capacity Planning): https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm
2. About Portfolios: https://docs.oracle.com/cd/G48897_01/p6help/en/6611.htm
3. Working with Portfolios: https://docs.oracle.com/cd/G48897_01/p6help/en/6671.htm
4. Creating Portfolios (V26 User Guide): https://docs.oracle.com/cd/G48897_01/English/User_Guides/p6_eppm_user/7858.htm
5. Working with Portfolio Views: https://docs.oracle.com/cd/G48897_01/p6help/en/14090.htm
6. Working with Portfolio View Scorecards: https://docs.oracle.com/cd/G48897_01/p6help/en/9116.htm
7. About What-if Analysis: https://docs.oracle.com/cd/G48897_01/p6help/en/36491.htm
8. About Capacity Planning: https://docs.oracle.com/cd/G48897_01/p6help/en/36490.htm
9. Capacity Planning Page: https://docs.oracle.com/cd/G48897_01/p6help/en/5973.htm
10. Working with the Capacity Planning Page: https://docs.oracle.com/cd/G48897_01/p6help/en/36496.htm
11. Defining Performance Thresholds: https://docs.oracle.com/cd/G48897_01/p6help/en/7857.htm
12. EPPM V26 REST ProjectPortfolio endpoints: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/api-projectportfolio.html

### P6 Professional V26
13. Professional V26 Help TOC: https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm
14. Create a portfolio: https://docs.oracle.com/cd/G48902_01/client_help/en_US/create_a_portfolio.htm
15. Add projects to a portfolio: https://docs.oracle.com/cd/G48902_01/client_help/en_US/add_projects_to_a_portfolio.htm
16. Add users to a portfolio: https://docs.oracle.com/cd/G48902_01/client_help/en_US/add_users_to_a_portfolio.htm
17. Define a what-if project: https://docs.oracle.com/cd/G48902_01/client_help/en_US/define_a_what-if_project.htm
18. Professional V26 User Guide — Resource Analysis and What-If projects: https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/p6_pro_user.pdf

19. Professional API ProjectPortfolio (Release 24; version-limited): https://docs.oracle.com/cd/F88968_01/English/Integration/p6_pro_api_reference/com/primavera/integration/client/bo/object/ProjectPortfolio.html

## 5. Remaining gaps — explicitly open

- Full V26 EPPM portfolio/Capacity Planning field inventory and API schema.
- Exact portfolio and portfolio-view privilege matrix, including global vs multi-user access and dashboard portlet privileges.
- All EPPM performance threshold definitions and scorecard field edit permissions.
- Complete EPPM scenario schema, retention, sharing, stale-data behavior and comparison rules.
- Full Professional Project Portfolio permissions and behavior in both Professional and EPPM database contexts.
- Exact Professional Resource Analysis calculation and data-source rules across all User Preference combinations.
- Role estimate generation and role-team hierarchy behavior in EPPM Capacity Planning.
- Numerical test comparing EPPM Capacity Planning and Professional Resource Usage Profile for the same projects/resources/roles and summary states.
- Verification of every portfolio-related Help topic and cross-link in both V26 Help trees; this matrix is a focused slice, not the full topic census.

## 6. Boundary and conclusion

This is a **documentation-only reference comparison**. No portfolio, project, scenario, what-if project, reflection, resource estimate, forecast date, or resource allocation was created or modified. No product feature, CUBI workspace, code, schema, menu, data flow or agent-owned task was changed.

**Conclusion:** P6 Professional V26 does support Project Portfolios and What-If/Reflection workflows, so “no portfolio capability” is false. However, the EPPM V26 Portfolios area is a materially richer analysis layer: filtered portfolios, named portfolio views, scorecards, charting, performance thresholds, scenarios, waterline analysis and role-based Capacity Planning. Professional's project portfolio grouping and resource usage profiles are related capabilities but not a one-to-one replacement for EPPM Portfolio Analysis or Capacity Planning.
