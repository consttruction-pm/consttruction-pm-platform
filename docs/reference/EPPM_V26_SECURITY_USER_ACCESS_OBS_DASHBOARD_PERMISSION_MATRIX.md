# P6 EPPM V26 vs P6 Professional V26 — Security, User Access, OBS, Resource Security and Dashboard Visibility Matrix

- **Status:** Topic-level comparison completed for the security/access slice; not a complete privilege-by-privilege enumeration of every checkbox.
- **Prepared:** 2026-11-14
- **Baseline:** Oracle Primavera P6 EPPM Version 26 and P6 Professional Version 26.
- **Parent audit:** `PRIMAVERA_P6_EPPM_V26_VS_PROFESSIONAL_V26_DIFFERENCE_AUDIT.md`
- **Scope:** Product behavior and documentation comparison only. No CUBI Workspace, Professional parity, navigation, scheduler, or application code changes are authorized or made.

## 1. Evidence and interpretation rules

This matrix distinguishes:
1. **EPPM web/platform** — browser application, application administration, module access, user interface views, dashboards and portlets.
2. **Professional desktop on a Professional database** — desktop client and its local/admin security model.
3. **Professional desktop connected to an EPPM database** — still the Professional client, but EPPM database security and selected EPPM-only workflows apply.

Oracle explicitly documents all three contexts. A topic labelled “P6 Professional Only” is not a blanket statement about every Professional deployment; likewise “P6 EPPM Only” can describe a workflow available through Professional when connected to an EPPM database.

**Evidence labels**
- **CONFIRMED** — direct Version 26 topic or guide evidence supports the stated behavior.
- **BOTH / DIFFERENT SURFACE** — both products have a related concept, but the workflow or scope differs.
- **NOT VERIFIED** — the available V26 evidence does not justify an absence claim or a field-level conclusion.

## 2. Security and access matrix

| ID | Control / capability | P6 EPPM V26 evidence and behavior | P6 Professional V26 evidence and behavior | Classification / conclusion |
|---|---|---|---|---|
| SEC-001 | User account and module access | EPPM Users administration controls security attributes plus project and module access. A user needs login name, global profile and module access. | Professional has Admin > Users and a Module Access tab; Professional-only setup explicitly enables P6 Professional. When connected to EPPM DB, EPPM access model applies. | BOTH / DIFFERENT SURFACE — CONFIRMED |
| SEC-002 | Module access granularity | EPPM module access determines which suite modules a user can enter. The V26 Help describes Projects, Portfolios, Resources, Contributor and Enterprise Reporting as access options; licensed modules without a valid module-access selection do not grant application login by themselves. | Professional has a P6 Professional module access checkbox in its Professional DB security workflow. EPPM-connected Professional use is not equivalent to granting browser module access. | EPPM module model broader; do not collapse module entitlement into menu visibility — CONFIRMED |
| SEC-003 | Global security profile | Every EPPM user requires a global profile. Global profile controls application-wide privileges and global data access. | Professional uses a global profile in its Global Access tab. The connected-database context changes where profiles are defined and administered. | BOTH / DIFFERENT SURFACE — CONFIRMED |
| SEC-004 | Project security profile | EPPM project profiles grant project-specific privileges and are associated with OBS elements/responsible managers. | Professional profiles also scope project permissions by OBS/responsible manager; Professional Help distinguishes Professional DB and EPPM DB contexts. | BOTH / DIFFERENT SURFACE — CONFIRMED |
| SEC-005 | OBS hierarchy | EPPM User Access includes OBS configuration; OBS assignments determine which EPS/projects and WBS scope a user can access. | Professional also uses OBS/responsible-manager assignments to scope project access. The detailed administration surface depends on database context. | BOTH / DIFFERENT SURFACE — CONFIRMED |
| SEC-006 | OBS + project profile enforcement | EPPM combines the user's OBS assignment, project security profile and the OBS responsibility attached to EPS/WBS/project elements. A root-EPS OBS assignment can expose all projects. | Professional Help describes OBS/project-profile scoping and inheritance through the EPS hierarchy; connected to EPPM DB, profile assignment is defined in P6. | BOTH / DIFFERENT SURFACE — CONFIRMED; root assignment is a high-risk privilege |
| SEC-007 | Global privilege hierarchy | EPPM global profiles can grant view/assign/edit/add/delete privileges; Oracle documents hierarchical privilege dependencies for profile permissions. | Professional global profiles also govern application-wide actions. Exact checkbox-by-checkbox parity is not established by this matrix. | BOTH / DIFFERENT SURFACE — partial; full privilege inventory NOT VERIFIED |
| SEC-008 | Project privilege hierarchy | EPPM project profiles control project data such as baselines, WBS, expenses, activities, risks and issues according to assigned OBS scope. | Professional project profiles similarly govern actions on project data within OBS scope. | BOTH / DIFFERENT SURFACE — CONFIRMED at model level; exact privilege mapping NOT VERIFIED |
| SEC-009 | Admin Superuser | EPPM Admin Superuser is a predefined global profile with broad global and all-project access; project/OBS assignments do not constrain it. Oracle recommends limiting assignment. | Professional has Admin Superuser with equivalent elevated administrative intent in the Professional security model. | BOTH / HIGH-RISK PRIVILEGE — CONFIRMED |
| SEC-010 | Project Superuser | EPPM Project Superuser is a predefined project profile granting complete access to elements within a project; assignment requires appropriate administrator authority. | Professional also documents Project Superuser in its project profile model. | BOTH / HIGH-RISK PRIVILEGE — CONFIRMED |
| SEC-011 | Resource security | EPPM V26 allows No Resources, All Resources, or Select Resources (up to five resource nodes and their children); Admin Superusers bypass the restriction. Changes require re-login to be reflected. | Professional V26 Global Access allows All Resource Access or up to five root resource nodes; no selection means no resource access. Changes are honored on next login. | BOTH / DIFFERENT SURFACE — CONFIRMED |
| SEC-012 | Resource security vs project assignments | EPPM documentation warns resource access filtering is not identical to project privileges; project resource assignments can remain visible/editable when the user has the necessary project privileges. | Professional separates resource security from project profile access. | BOTH / DIFFERENT SCOPE — do not assume resource dictionary filtering alone removes every project assignment reference |
| SEC-013 | User Interface Views | EPPM V26 provides role-oriented views controlling visible menu items/pages, start page, activity editing permissions, dashboards and page ordering; views can be assigned to users. | No equivalent Professional desktop feature with the same EPPM web navigation/view model was established from the reviewed Professional V26 topic pages. This is not proof that every analogous desktop customization is absent. | EPPM WEB CAPABILITY — CONFIRMED; Professional equivalence NOT VERIFIED |
| SEC-014 | View as presentation vs authorization | EPPM UI Views hide or show interface features and can constrain Activity Editing options, but actual access also depends on module access, global/project profiles, OBS, resource access and project relationship. | Professional menu/tool customization and security profiles are distinct mechanisms; hiding a menu item must not be treated as a security boundary. | BOTH / DIFFERENT LAYERS — CONFIRMED principle |
| SEC-015 | Personal view preferences | EPPM My Preferences > View lets users configure start page and selected menu items within the view/permissions assigned to them; assigned view and personal settings determine visible menu items. | Professional desktop has its own user preferences/layout configuration, not the same browser User Interface View assignment contract. | BOTH / DIFFERENT SURFACE — CONFIRMED at product surface level |
| SEC-016 | Private/user dashboard | EPPM user dashboards are private workspaces, available only to the current user; creator can customize content, layout and access. | No corresponding dashboard/portlet page in the Professional desktop workflow was verified. Professional layouts are not equivalent to EPPM dashboards. | EPPM WEB CAPABILITY — CONFIRMED; absence in all Professional contexts NOT VERIFIED |
| SEC-017 | Multi-user dashboard | EPPM dashboard access can be restricted to a specified list of users. Only the creator can modify a multi-user dashboard; users must both be included in the assigned UI view and have dashboard access. | No equivalent multi-user dashboard/portlet surface confirmed in Professional desktop Help. | EPPM WEB CAPABILITY — CONFIRMED |
| SEC-018 | Global dashboard | EPPM global dashboards can be exposed to all users, but editing content/layout/access requires the relevant security privilege. | No equivalent global dashboard/portlet surface confirmed in Professional desktop Help. | EPPM WEB CAPABILITY — CONFIRMED |
| SEC-019 | Dashboard access selector | EPPM Access tab supports Current User, All Users and List of Users. All Users requires the appropriate security privilege; users cannot change access on another creator's multi-user dashboard. | Not established as a Professional desktop feature. | EPPM WEB CAPABILITY — CONFIRMED |
| SEC-020 | Dashboard visibility is a two-part gate | EPPM dashboard availability is affected by UI View assignment and dashboard Access settings. A multi-user dashboard assigned to a view remains invisible to users who are not authorized in the dashboard Access tab. | Professional desktop does not inherit the EPPM browser dashboard visibility model merely by connecting to an EPPM database. | EPPM WEB CAPABILITY — CONFIRMED |
| SEC-021 | Dashboard data scope | EPPM dashboards/portlets display data according to module access, security privileges and the user's relationship to the project; portlet filters and dashboard filters further shape the displayed subset. | Professional client data visibility is governed by its security context and desktop views, not EPPM dashboard filters. | BOTH / DIFFERENT SURFACE — CONFIRMED |
| SEC-022 | Contributor access | EPPM Contributor module access is a limited application access mode; the V26 Help describes dashboard/project access and states Activity Editing view options apply. Project access also depends on OBS and whether the person is assigned as a resource or activity owner. | No direct equivalent in Professional desktop user-access setup confirmed. | EPPM ROLE-BASED MODULE — CONFIRMED |
| SEC-023 | API authorization | EPPM REST/Web Services operate under global and project security profiles; service calls that violate a profile can fail with a security fault. | Do not infer API privileges from Professional desktop UI access; API authorization must be checked against the EPPM service contract and database context. | EPPM API SECURITY — CONFIRMED |
| SEC-024 | Identity provisioning | EPPM cloud documentation separates identity/application provisioning from P6 user access configuration; after application access provisioning, P6 module/project privileges still need configuration. | Professional DB user setup has its own account/security workflow; identity management for EPPM cloud must not be collapsed into Professional desktop account setup. | DEPLOYMENT-DEPENDENT — CONFIRMED in guide architecture; exact tenant workflow varies |
| SEC-025 | Security change propagation | EPPM resource access documentation says users must exit and log in again for changed resource access to be reflected. | Professional resource security changes are honored on next login; offline users may be affected by changes to user details, profiles, OBS assignments and resource security. | BOTH / OPERATIONAL DIFFERENCE — CONFIRMED |
| SEC-026 | UI visibility and data authorization must be separate | EPPM docs separately describe User Interface Views (feature visibility), Module Access, Global/Project Security Profiles, OBS and Resource Access. They are separate controls and should not be represented as one permission bit. | Professional security profiles/resource security likewise remain distinct from layout/menu customization. | BOTH — CONFIRMED architectural distinction |

## 3. EPPM menu and dashboard authorization flow

The V26 evidence supports the following conceptual gate sequence. It is a model for interpreting Oracle behavior, not an implementation design or authorization to change CUBI.

1. **Identity/application provisioning:** the person has an identity and the relevant P6 application access (deployment dependent).
2. **P6 user account:** user exists in P6 and has a login.
3. **Module access:** user is allowed into the relevant P6 EPPM module(s).
4. **Global security profile:** global data and application-wide actions are constrained.
5. **Project security profile + OBS:** determines project/EPS/WBS scope and permitted project actions.
6. **Resource access:** separately restricts resource dictionary visibility.
7. **User Interface View:** controls role-oriented feature/menu/page visibility and start page.
8. **Dashboard access:** private, selected-user or global audience; dashboard content and filters determine what is displayed, while underlying authorization still applies.
9. **Relationship/role and data filters:** contributor access and portlet data can depend on project relationship, assignment/activity ownership and filter configuration.
10. **API enforcement:** REST/SOAP operations remain subject to server-side security profiles; client-side hiding is not a substitute.

## 4. Direct Version 26 Oracle evidence

### EPPM V26
- About Administration — User Administration, module access, OBS, profiles and UI Views:
  https://docs.oracle.com/cd/G48897_01/p6help/en/6590.htm
- About User Access:
  https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-app-admin/aboutuseraccess-6597a.html
- Configuring Users in P6 EPPM:
  https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-app-admin/configuringusersince-product-names_p6-eppm-short__-6918a.html
- Authorization: What Users Can Access:
  https://docs.oracle.com/cd/G48897_01/English/Admin/p6_eppm_application_admin/99163.htm
- About Security Profiles:
  https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/aboutsecurityprofiles-6595a.html
- Working with Security Profiles:
  https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/workingwithsecurityprofiles-36451a.html
- Assigning Resource Access:
  https://docs.oracle.com/cd/G48897_01/p6help/nl/7793.htm
- About User Interface Views:
  https://docs.oracle.com/cd/G48897_01/p6help/en/6598.htm
- Creating User Interface Views:
  https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/creatinguserinterfaceviews-7802a.html
- Configuring User Interface Views:
  https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/configuringuserinterfaceviews-7801a.html
- Assigning User Interface Views:
  https://docs.oracle.com/cd/G48897_01/p6help/nl/7800.htm
- Working with Dashboards:
  https://docs.oracle.com/cd/G48897_01/p6help/en/6665.htm
- Customizing Dashboards:
  https://docs.oracle.com/cd/G48897_01/p6help/en/7827.htm
- Dashboard Access tab:
  https://docs.oracle.com/cd/G48897_01/p6help/en/8106.htm
- REST API Application Level Security:
  https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/D99816.html

### Professional V26
- Setting up user security (P6 Professional Only):
  https://docs.oracle.com/cd/G48902_01/client_help/en_US/setting_up_user_security.htm
- Global Access tab — Users dialog (P6 Professional Only):
  https://docs.oracle.com/cd/G48902_01/client_help/en_US/global_access_tab_-_users_dialog_box.htm
- OBS security:
  https://docs.oracle.com/cd/G48902_01/client_help/en_US/obs_security.htm
- Security profiles:
  https://docs.oracle.com/cd/G48902_01/English/admin/p6_pro_admin/security_profiles.htm
- Professional V26 guide catalogue:
  https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/books.html

## 5. Important conclusions for the parent audit

1. EPPM authorization is layered. A single “user permission” flag is not a faithful model of Oracle's module, global profile, project profile, OBS, resource access, UI View and dashboard access controls.
2. A dashboard being visible in a UI View does not itself grant access to its underlying project/resource data.
3. UI Views are presentation/interaction configuration and can constrain visible pages and selected activity-editing fields, but they do not replace server-side authorization.
4. EPPM dashboards have three distinct audiences: current user, selected users, and all users. Multi-user dashboards have creator-controlled edit rights and recipient-controlled visibility.
5. Professional has its own global/project security and resource security workflows. When connected to an EPPM database, Professional uses EPPM-defined profiles; this does not turn the desktop client into the EPPM web dashboard experience.
6. Resource security is separate from project/OBS security. A restricted resource dictionary does not automatically imply that every resource assignment in an authorized project disappears.
7. API calls are subject to server-side security profiles; hiding menu items is never a security boundary.
8. Admin Superuser and Project Superuser are exceptional high-privilege profiles and should be treated as privileged administrative roles, not ordinary user categories.
9. The Professional Help source does not provide enough evidence to claim the absence of every UI-view-like customization or every dashboard-related API. Such absences remain NOT VERIFIED.

## 6. Open evidence gaps before calling this slice fully exhaustive

- Enumerate every global security privilege and every project security privilege checkbox in V26, including exact privilege dependencies.
- Compare every module-access option against the current V26 licensing matrix and cloud/on-premises differences.
- Enumerate all OBS assignment edge cases: root EPS, inherited children, multiple OBS assignments, default project profile and overlapping responsibility.
- Compare all resource-security edge cases, including deleted nodes, reassignment, imports, and visibility of existing project assignments.
- Capture every UI View content/Activity Editing field and its exact effect on each page.
- Compare dashboard create/edit/delete privileges and every portlet's underlying data-security behavior.
- Verify the current V26 REST API security behavior endpoint-by-endpoint; the API overview alone is not a full endpoint matrix.
- Review Professional V26 menus/layouts and connected-EPPM behavior before making any broader claim of feature absence.

## 7. CUBI boundary and design implications (non-implementation)

For any separately authorized future personal-menu work, the Oracle evidence implies these non-negotiable design constraints:
- Keep **feature visibility** separate from **data authorization**.
- Evaluate access on the server for every dashboard card, list, message, form, approval and notification target.
- Resolve the user's project/OBS scope and resource scope before displaying counts, names, previews or deep links.
- Treat private, selected-user and global dashboard audiences as distinct access policies.
- Do not infer a user's rights from job title, menu visibility, a client-side role label or a cached dashboard configuration.
- Do not expose a notification's title/snippet or existence if the user cannot access the referenced object.
- Re-check permissions when opening an item; notification delivery is not an authorization grant.
- Preserve auditability for privilege changes and administrative overrides.

These are product-analysis implications only. No CUBI requirement, schema, UI, route, API or code was changed by this document.
