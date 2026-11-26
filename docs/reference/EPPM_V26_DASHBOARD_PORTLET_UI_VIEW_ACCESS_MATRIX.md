# P6 EPPM V26 vs P6 Professional V26 — Dashboards, Portlets, UI Views & Access Matrix

**Status:** V26 documentary comparison of web dashboards versus desktop layouts  
**Scope:** Dashboard groups, access settings, UI Views, portlet catalogue, custom portlets, security boundaries, Professional layouts, reports and Visualizer.  
**Out of scope:** Creating dashboards, assigning users, configuring portlets/UI Views, changing menus/layouts, or modifying any workspace/product.  
**Version rule:** EPPM Help and Administration Guide V26; Professional Help/User Guide V26. Older portlet catalogues are not used to assert V26 availability.

## 1. Executive findings

1. **EPPM V26 has a web Dashboard/Portlet surface; Professional V26 does not document an equivalent Dashboard page.** Professional provides desktop windows, user-defined layouts, reports, Visualizer and Project Web Site Publisher instead.
2. **EPPM dashboard visibility has two separate controls.** A dashboard must be assigned to the user's UI View and its Access tab must allow that user (or all users). Being in a UI View alone is not sufficient for a multi-user dashboard.
3. **UI Views are presentation/navigation configuration, not a security boundary.** Project/resource data remains subject to module access, global/project privileges, OBS/resource security and project relationship.
4. **EPPM dashboard types are user/private, multi-user and global.** Access can be restricted to the current user, a specified list of users, or all users. Global dashboards can be edited only by users with the required privilege.
5. **The V26 portlet catalogue is configuration-dependent and has a documentation inconsistency.** The List of Portlets page says it lists all possible portlets but omits Document Review and Resource Team Summary portlets, which are documented by separate V26 topics. Do not rely on the list alone as a complete V26 portlet inventory.
6. **Custom Portlets are URL-based.** The V26 procedure asks the user to enter a title and URL; the documented feature is not limited to BI Publisher reports.
7. **Professional layouts are not dashboards.** Professional layouts customize a window's table/Gantt/network/profile/spreadsheet presentation, can be saved/shared/exported, and operate in the desktop client. They do not provide EPPM's multi-user/global dashboard, portlet and UI View access model.

## 2. Dashboard, portlet and access matrix

| # | Topic | P6 EPPM V26 | P6 Professional V26 | Finding / evidence status |
|---:|---|---|---|---|
| 1 | Dashboard surface | Dedicated Dashboards page with customizable dashboards and portlets | No Dashboard page or dashboard portlet catalogue in Professional V26 Help TOC | EPPM web-specific surface. CONFIRMED (Help inventory) |
| 2 | Dashboard purpose | Displays multiple projects and portfolio, project, resource and personal data; supports collaboration | Professional uses project/resource windows, layouts, reports and Visualizer | Related presentation goals, different product surface. CONFIRMED |
| 3 | Dashboard types | User/private, multi-user and global dashboards | No equivalent dashboard types in Professional V26 | EPPM-specific access model. CONFIRMED |
| 4 | User/private dashboard | Available only to current user | Professional layouts can be user-specific/shared, but not a private dashboard with portlets | Not equivalent. CONFIRMED |
| 5 | Multi-user dashboard | Visible to a specified list of users; must be assigned to UI View | Professional layouts can be shared with users, but no dashboard-level multi-user portlet model | Different sharing model. CONFIRMED |
| 6 | Global dashboard | Available to all users who are assigned the relevant UI View and have required module/data access | Professional has global/shared layouts but no global dashboard page | Different global presentation model. CONFIRMED |
| 7 | Dashboard Access options | Current user only, list of specified users, or all users | Professional layout sharing controls access to layout, not dashboard access | EPPM-specific access control. CONFIRMED |
| 8 | UI View assignment | Admin assigns dashboard to UI View; dashboards displayed on login are defined by UI View | No EPPM UI View mechanism in Professional V26 Help | EPPM navigation/presentation control. CONFIRMED |
| 9 | Dual visibility requirement | Multi-user dashboard requires both UI View assignment and dashboard Access tab permission | No equivalent dual-control dashboard model | Two independent EPPM visibility gates. CONFIRMED |
| 10 | UI View security meaning | UI View determines which pages/dashboards/navigation items appear; it does not grant underlying data privileges | Professional user layouts/menus do not replace global/project/resource security | Presentation is not authorization. CONFIRMED |
| 11 | Data access in portlets | Portlet data is based on module access, security privileges and user's role relative to project | Professional windows display data according to database-context privileges and security | Dashboard access does not grant project/resource data access. CONFIRMED |
| 12 | Dashboard content tabs | Content tab selects portlets and their options | Professional layouts use Layout Options and window-specific configuration | Different configuration mechanism. CONFIRMED |
| 13 | Dashboard layout | Layout tab arranges portlets; drag/drop and Narrow/Wide sizing | Professional layouts customize table/Gantt/network/profile/spreadsheet panes and timescales | Different layout units. CONFIRMED |
| 14 | Dashboard filter | Dashboard can have owner filter; user may override if owner has not restricted filter changes | Professional layouts have project/activity filters; no dashboard-level shared filter | Different filter scope. CONFIRMED |
| 15 | Global dashboard editing | Only users with required security privilege can change global dashboard content/layout/access | Professional global layouts have their own sharing/edit permissions | Not equivalent to dashboard administrator privileges. CONFIRMED |
| 16 | Multi-user dashboard editing | User can customize own multi-user dashboard; cannot customize another user's multi-user dashboard without required rights | Professional layouts can be shared; no multi-user dashboard owner/edit model | EPPM-specific ownership semantics. CONFIRMED |
| 17 | Default portlet maximum | Default administrative limit is 12 portlets per dashboard; administrator can change maximum | No dashboard portlet count in Professional | EPPM-specific limit. CONFIRMED |
| 18 | Portlet availability | V26 Help says available portlets vary by configuration | No portlet catalogue in Professional V26 | Configuration-dependent EPPM feature. CONFIRMED |
| 19 | Personal data portlets | My Activities, My Issues, My Projects, My Calendar and My Risks | Professional windows show user's project/activity/resource data but not personal dashboard portlets | Different personal work surface. CONFIRMED |
| 20 | Portfolio portlet | Portfolio View portlet can display bubble, pie, scorecard, histogram, side-by-side and stacked histogram views | Professional Project Portfolios are project groupings; no Portfolio View portlet | EPPM dashboard integration. CONFIRMED |
| 21 | Project performance portlets | Earned Value, Schedule Performance, Index Performance, Project Statistics, Project Health, Project Notebooks and Project Gantt Chart | Professional can create reports, tracking layouts and Visualizer views; no equivalent dashboard portlets | Different presentation model. CONFIRMED |
| 22 | Resource portlets | Open Requests for Resources is listed; Resource Team Summary is documented separately | Professional has Resource Usage Profile/Spreadsheet and Resource Analysis layouts | Related resource functions, not a dashboard equivalent. CONFIRMED |
| 23 | Document review portlet | Separate V26 Document Review Portlets topic documents participating/terminating reviews from portlets | Professional V26 Work Products & Documents has no equivalent repository review portlet workflow | EPPM repository/workflow integration. CONFIRMED |
| 24 | Resource Team Summary portlet | V26 Sending Email to Resource Teams topic explicitly references Resource Team Summary portlet and filtering by team | Professional V26 Help does not document Resource Team Summary portlet | EPPM team/dashboard integration. CONFIRMED |
| 25 | Portlet catalogue completeness | List of Portlets page says it lists all possible portlets but omits Document Review and Resource Team Summary portlets documented elsewhere in V26 Help | No corresponding Professional portlet catalogue | V26 documentation inconsistency; use related topics, not only the list page. DOCUMENTATION INCONSISTENCY CONFIRMED |
| 26 | Custom portlets | User can add a custom portlet by entering a title and URL | Professional can publish project websites/reports and use Visualizer, but no dashboard custom-portlet URL feature documented | EPPM URL-based portlet extension. CONFIRMED |
| 27 | Portfolio View portlet creation | Select a new/existing Portfolio View, choose type and configure chart/scorecard settings | No equivalent Portfolio View portlet in Professional | EPPM-only dashboard feature. CONFIRMED |
| 28 | Portlet filter behavior | Some portlets have additional filter/configuration options; dashboard filter may be owner-restricted | Professional filters are saved in layouts and applied to window data | Different filter ownership and sharing. CONFIRMED |
| 29 | Dashboard page visibility | Global and multi-user dashboards displayed as defined by UI View, plus private user dashboards | Professional opens windows and layouts from desktop navigation | Different login/home surface. CONFIRMED |
| 30 | Manage Dashboards | Separate page lists Displayed Dashboards and Available Dashboards | Professional has Open Layout/Manage Layouts workflows | Different object-management interface. CONFIRMED |
| 31 | Customizing dashboard content | Select portlets and configure portlet-specific fields/options on Content tab | Professional selects table columns, bars, grouping, sorting and profile options | Different content model. CONFIRMED |
| 32 | Dashboard collaboration | Portlets support personal/project/portfolio/resource data and collaboration | Professional supports team discussions, email and shared layouts but no dashboard collaboration portlets | Different collaboration surface. CONFIRMED |
| 33 | Professional Activity Layout | Table, Gantt, Activity Network, Trace Logic, Activity/Resource Usage Profile and Spreadsheet | Core Professional customization model | Desktop layout, not a web dashboard. CONFIRMED |
| 34 | Professional Tracking Layout | Project Table, Project Bar Chart, Project Gantt/Profile and Resource Analysis | User can create/share/export/import tracking layouts | Desktop analysis, not portlet dashboard. CONFIRMED |
| 35 | Professional layout sharing | Layouts can be saved as project layouts and shared with other users; layouts can be exported/imported | No global/multi-user dashboard Access tab or UI View assignment | Shared layouts are not shared dashboards. CONFIRMED |
| 36 | Professional reporting alternative | EPPM uses dashboards and report delivery; reports may also be exposed through portlets | Professional has Report Wizard/Editor, report batches, command-line reports and Project Web Site Publisher | Related output capabilities, not equivalent live dashboard. CONFIRMED |
| 37 | Professional Project Web Site Publisher | EPPM dashboards are interactive and security-aware web pages | Professional can publish static project websites and activity/tracking layouts | Static publication is not an interactive dashboard. CONFIRMED |
| 38 | Professional Visualizer | EPPM uses Portfolio View/Project Gantt portlets and web dashboards | Professional Visualizer provides desktop time-scaled and layout-based visualization | Different visualization product surface. CONFIRMED |
| 39 | UI View vs Professional layout | UI View controls available pages and dashboard tabs for users | Professional layout controls table/chart/profile presentation within a selected window | Different abstraction levels. CONFIRMED |
| 40 | Dashboard vs data security | Dashboard Access/visibility does not override project, resource, OBS, financial or module security | Professional layouts similarly do not bypass underlying project/resource privileges | Security remains server/database-side. CONFIRMED |

## 3. Critical access rules

### 3.1 Dashboard visibility requires two checks

For a multi-user dashboard:
1. The dashboard must be assigned to the user's UI View so it appears in navigation.
2. The dashboard's Access tab must include the user (or allow all users).

For a global dashboard, the administrator assigns it to the relevant UI View and the user must still have the required module/data access. A dashboard tab appearing does not mean the user can see every project or every field in its portlets.

### 3.2 UI Views are not security profiles

UI Views configure which pages and dashboards appear. They are not substitutes for:
- Module Access,
- Global Security Profiles,
- Project Security Profiles,
- OBS project access,
- Resource Security,
- Financial data privileges,
- API/server-side authorization.

### 3.3 Portlet catalogue must be read with related topics

The V26 List of Portlets page does not list Document Review or Resource Team Summary portlets, but separate V26 Help topics document them. Therefore, a source audit must search related topics and not treat the list page as a complete inventory.

### 3.4 Professional layouts are not EPPM dashboards

A Professional Activity Layout controls a desktop window's table/Gantt/network/profile/spreadsheet display. A Tracking Layout controls project/resource analysis presentation. Sharing a layout with another user does not create a dashboard with access tabs, UI View assignment, portlets, and multi-project web data.

## 4. Source register — Oracle primary sources

### P6 EPPM V26
1. Working with Dashboards: https://docs.oracle.com/cd/G48897_01/p6help/en/6665.htm
2. List of Portlets: https://docs.oracle.com/cd/G48897_01/p6help/en/6667.htm
3. Creating Dashboards: https://docs.oracle.com/cd/G48897_01/p6help/en/7826.htm
4. Customizing Dashboards: https://docs.oracle.com/cd/G48897_01/p6help/en/7827.htm
5. Configuring Dashboard Access: https://docs.oracle.com/cd/G48897_01/p6help/en/32010.htm
6. Creating Custom Portlets: https://docs.oracle.com/cd/G48897_01/p6help/en/41580.htm
7. Creating Portfolio View Portlets: https://docs.oracle.com/cd/G48897_01/p6help/en/44295.htm
8. Document Review Portlets: https://docs.oracle.com/cd/G48897_01/p6help/en/44954.htm
9. Sending Email to Resource Teams / Resource Team Summary portlet: https://docs.oracle.com/cd/G48897_01/p6help/en/44309_1.htm
10. Creating User Interface Views (V26 Admin Guide): https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-app-admin/creatinguserinterfaceviews-7802a.html
11. Configuring User Interface Views (V26 Admin Guide): https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-app-admin/configuringuserinterfaceviews-7801a.html

### P6 Professional V26
12. Professional V26 Help TOC: https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm
13. Customizing Activity Layouts: https://docs.oracle.com/cd/G48902_01/client_help/en_US/customizingactivitylayouts.htm
14. Professional V26 User Guide (layouts, tracking, reports and Visualizer): https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/p6_pro_user.pdf

## 5. Remaining gaps — explicitly open

- Exact V26 UI View assignment fields and privileges for every dashboard group and user type.
- Full V26 portlet inventory by deployment/configuration; reconcile List of Portlets omissions with related topics.
- Exact privilege matrix for adding/removing custom portlets and Portfolio View portlets.
- Portlet-specific data security and field visibility under all module/project/resource/OBS combinations.
- Exact custom portlet URL authentication, CSP, allowed-host, iframe and security behavior.
- Professional V26 global/user/project layout access matrix and all export/import constraints.
- Full comparison of Professional Project Web Site Publisher vs EPPM dashboard publication and access.
- Full dashboard/portlet source-topic census and breadcrumb mapping in both V26 Help trees.
- Independent reviewer verification of the V26 portlet catalogue inconsistency and UI View/security distinction.

## 6. Boundary and conclusion

This is a **documentation-only reference comparison**. No dashboard, UI View, portlet, user access setting, menu, layout, report, website, CUBI workspace, code, schema or project data was created or changed.

**Conclusion:** P6 EPPM V26 has a distinct web Dashboard/Portlet/UI View model with user, multi-user and global dashboards, access tabs, portlet catalogues, portfolio views and custom URL portlets. P6 Professional V26 instead provides desktop windows, layouts, tracking layouts, reports, Visualizer and static Project Web Site publishing. Shared visualization or sharing goals do not make those objects equivalent. Dashboard visibility and UI Views must also remain separate from actual project/resource authorization.
