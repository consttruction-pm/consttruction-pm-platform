# CUBI — Mandatory Page-by-Page Design, Help Traceability and Acceptance Standard

**Status:** Mandatory project rule  
**Applies to:** Every agent, developer, reviewer, QA operator and automated coding agent working anywhere in this repository  
**Effective:** Immediately  
**Owner:** Product owner  
**Change control:** Do not weaken or replace this standard without explicit product-owner approval.

## 1. One official Preview — immutable project rule

The one and only official CUBI Preview entry is:

**https://cubi-web-preview-git-feat-vercel-p-8eb184-foroughichamshir-7811.vercel.app/app?project=preview-rps-01&view=live**

- This is the canonical shared Preview URL and the canonical Engineering workspace project is `preview-rps-01` (Riverside Pump Station Upgrade).
- Do not create, select, publish, or report a new Vercel project, parallel Preview environment, random deployment URL, per-PR Preview URL, or replacement alias as the official Preview.
- Do not change this URL in project instructions, test reports, documentation, or agent prompts without explicit product-owner approval.
- Every agent must test against this same official entry. A deployment-specific URL may be used internally by the platform, but it is not a second product Preview and must never be presented as the canonical link.
- A new deployment must update the version behind the established official entry; it must not change the canonical entry point.
- If the official alias does not resolve to the intended current deployment, stop and report the routing/alias problem. Do not silently invent another Preview URL.
- Local test servers and CI ephemeral environments may be used only as auxiliary test machinery; they are not user-facing Preview environments and do not replace the canonical Preview.

## 2. Mandatory reading before any work

Before inspecting, planning, coding, reviewing, testing, or handing off a task, every agent MUST read:

1. This file: `docs/standards/CUBI_PAGE_BY_PAGE_DESIGN_AND_ACCEPTANCE.md`.
2. Repository-wide instructions: `/AGENTS.md` and every applicable nested `AGENTS.md`.
3. `docs/cubisite/CAPABILITY_PAGE_INHERITANCE_HELP_MATRIX.md` — existing C01–C35 capability, public-route, workspace-surface and Help inheritance map.
4. `apps/web/src/capability-inheritance.ts` and `apps/web/src/help-registry.ts` — executable inheritance and contextual Help source.
5. `apps/web/site/routes.mjs` and `apps/web/site/capabilities.mjs` — public route and capability contracts.
6. `docs/traceability/README.md`, `docs/traceability/CUBI_ENGINEERING_V26_TRACEABILITY.md`, `docs/traceability/CUBI_ENTERPRISE_V26_TRACEABILITY.md`, and the corresponding JSON/CSV registries.
7. The relevant page-specific reference Help topics and the relevant implementation/source files before making any change.

Reading only a task prompt, a screenshot, a previous agent summary, or a generated checklist does not satisfy this requirement. Record the exact revision/commit of the standards and references read in the task evidence.

## 3. Official reference hierarchy — never mix product environments

### CUBI Engineering
- Primary official reference: [P6 Professional v26 HTML Help](https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm).
- Companion user guide: [P6 Professional v26 User Guide](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/index.html).
- Scheduling, WBS, activities, calendars, relationships, CPM, baselines, resources, Gantt, layouts, codes, risks/issues, tracking, import/export and other Professional workspace functions must use the exact relevant Professional v26 Help topic.

### CUBI Enterprise
- Primary official reference: [P6 EPPM v26 Help](https://docs.oracle.com/cd/G48897_01/p6help/en/).
- Enterprise portfolio, dashboards, organizational access, resource/portfolio management, workflows, approvals, reports and EPPM functions must use the exact relevant EPPM v26 Help topic and the Enterprise traceability registry.
- Do not use the Professional Help as a substitute for an EPPM topic, or vice versa. If a capability genuinely has no matching official Help topic, record that gap and obtain product-owner direction; do not invent a reference.

Oracle/Primavera/P6 materials are design and behavior references only. CUBI's product UI, visible branding, navigation and copy must remain CUBI-branded. Never display Oracle, Primavera or P6 branding in CUBI product screens.

## 4. Source-of-truth inheritance audit — page by page

The existing capability/page matrix is a starting point, not permission to skip verification. Before implementing or changing a page, inspect the current repository and establish the complete inheritance chain for that exact page:

- Actual route and route owner/router.
- Parent page, parent shell and inherited layout/component chain.
- Capability IDs (C01–C35 where applicable) and feature contract.
- Exact workspace surface / traceability row that implements the capability.
- Exact official Help topic title, URL, relevant section/steps, and PDF page where the registry provides one.
- Relevant UI components, styles/tokens, icons, menus, filters, dialogs, data/API services, authorization checks and persistence source.
- Shared components inherited by sibling pages and any page-specific overrides.
- Existing tests, known gaps, and previously accepted evidence.

Use these existing sources and reconcile them against the current code:
- `docs/cubisite/CAPABILITY_PAGE_INHERITANCE_HELP_MATRIX.md`
- `apps/web/src/capability-inheritance.ts`
- `apps/web/src/help-registry.ts`
- `apps/web/site/routes.mjs`
- `apps/web/site/capabilities.mjs`
- `docs/traceability/*`

Audit every route that actually exists in the application, not only the 25 public marketing routes in the current matrix. Include authentication, Personal Workbench/dashboard, Engineering, Enterprise, global administration, organization administration, project pages, AI Workbench, settings, reports, forms, help and all role/permission-gated pages. Mark routes as public, authenticated, admin-only, organization-scoped, environment-scoped, redirect, or compatibility route. Detect orphaned, duplicate and legacy shells. Do not create a second Engineering shell or treat the Enterprise environment as the current Engineering workspace.

If the current route inventory, matrix, code or Help registry disagree, document the mismatch and resolve the source of truth before implementation. Never silently overwrite an earlier audit or invent a page-to-Help relationship.

## 5. Required page specification — complete before implementation

Create or update one traceability record for EACH page. A page is not ready for implementation until its specification includes:

### A. Identity and inheritance
- Stable page ID, exact route, environment, page purpose and intended audience.
- Parent route, parent shell, inherited components and exact source paths.
- Capability IDs, feature IDs, workspace traceability IDs and status.
- Exact official Help topic(s): title, direct URL, section/heading, steps, and page number where applicable.
- Data/API/service owner, database/persistence source and authorization boundary.

### B. Functional behavior
Document each control and workflow individually, including:
- Every toolbar/menu/ribbon item, icon button, action, command and context-menu item.
- Every field, column, form control, dropdown, selector, tab, panel and detail section.
- Every filter, search, grouping, sorting, layout, view, chart and display option.
- Every dialog, drawer, popover, tooltip, confirmation, validation and error state.
- Default values, dependencies, enabled/disabled rules, empty/loading/error states.
- Input validation, keyboard behavior, accessibility name, focus order and shortcuts.
- Create/read/update/delete behavior, bulk operations, undo/redo where applicable, persistence, audit history and concurrency behavior.
- Permission behavior for each action, including unauthorized, read-only and restricted states.
- Exact user workflow from entry to completion, with expected result and failure handling.

A label or decorative control is not an implementation. Every visible control must have a real, tested behavior or be explicitly marked unavailable and hidden/disabled according to the product owner's direction.

### C. Visual specification — no approximate styling accepted
For each page, inspect the relevant official Help illustrations/screens and capture the corresponding reference state. Record and implement, element by element:

- Overall page/window geometry, layout regions, panel split, alignment, spacing, margins and density.
- Exact measured widths/heights, row heights, column widths, toolbar/ribbon heights, panel dimensions and dialog dimensions at the comparison viewport.
- Typography: font family, size, weight, line-height and hierarchy.
- Every icon: source/shape, visual size, stroke/weight, alignment, padding and interaction state.
- Every button: dimensions, padding, radius, border, fill, text, icon gap, hover, focus, pressed, selected, disabled and destructive states.
- Every filter/search control: dimensions, icon, label, border, dropdown affordance, spacing and active state.
- Every tab, menu, toolbar, tree, grid, table, chart, Gantt bar, relationship line, badge, tooltip, dialog and contextual menu.
- Color values for backgrounds, surfaces, borders, text, selected rows, hover, focus, status, warnings, errors, progress, chart series and relationship types.
- Scrollbars, separators, resize handles, shadows, corner radii and responsive/breakpoint behavior.
- LTR/RTL behavior, locale-specific text expansion, date/number formatting and font fallback.

Do not guess pixel sizes or colors. Extract exact values from a reference image/specification when available. If the Help describes behavior but does not specify a pixel value, measure the reference screenshot at a recorded viewport and label the value as a measured visual target (not an official documented numeric value). Record viewport, zoom/device scale, screenshot path, source URL and measurement method. If no authoritative visual exists, explicitly mark the detail as an unresolved design decision and obtain product-owner approval before inventing a new design.

Use CUBI's approved identity and theme tokens while matching the reference's information architecture, hierarchy, density, control behavior and visual proportions. The result must look like a polished first-class professional application, not a raw form, generic admin template, wireframe or unfinished collection of cards.

## 6. Professional dashboard standard

Every dashboard must be designed as a complete, modern, first-class product dashboard, based on the signed-in user's actual entitlements and organizational/project scope.

- Show relevant KPIs, actionable alerts, work queues, project/portfolio status, recent activity, deadlines, trends and drill-down paths appropriate to that dashboard's purpose.
- Personal Workbench is the post-login landing destination; the user then opens an authorized environment. Do not introduce role/persona selection at login.
- Engineering and Enterprise dashboards are separate domain experiences with their correct Help references and permissions.
- Global Administration and Organization Administration are distinct scopes. Global Admin retains system-wide authority; organization administrators are restricted to their own organization.
- Do not infer access from a hard-coded demo persona or project role. Apply server-authoritative entitlements configured by the authorized administrators.
- Dashboard cards must be live and data-backed, or visibly identified as unavailable; never fabricate KPI values or render decorative nonfunctional charts.
- Include meaningful loading, no-data, error, restricted and responsive states.
- Visual quality must include a coherent design system, high information density without clutter, clear hierarchy, professional charts, consistent spacing and typography, and accessible contrast.

## 7. Mandatory pre-build sequence

For each page, every agent must follow this order:

1. Read the mandatory files in section 2.
2. Inspect the current official Preview and record its exact URL; do not substitute another.
3. Identify the route and full inheritance chain from code, not assumption.
4. Open the exact official Help topic for that page and read the relevant procedure and all related subtopics.
5. Inspect reference illustrations/screens and produce the page's functional and visual specification.
6. Inspect existing implementation, data/API, permissions and tests.
7. Write a concise gap analysis: required vs current vs missing, with evidence.
8. Define acceptance tests and visual comparison captures before coding.
9. Only then implement the page. Keep shared components shared; do not fork duplicate page logic or shells.
10. Test functional behavior, permissions, persistence, visual parity and regressions on the one official Preview.
11. Update the page record with actual evidence, commit, tests and Preview result.

If any prerequisite is missing, blocked, ambiguous or contradictory, stop at that page and report the precise blocker. Do not start coding based on a guess.

## 8. Acceptance gate — a page is not "done" until every item passes

A page may be accepted only when all of the following are evidenced:

- [ ] Its route, parent, inheritance chain, capability and feature mappings are current and correct.
- [ ] The exact environment-specific official Help topic was read and is linked from its traceability record.
- [ ] Every required feature/control/workflow is mapped to Help and implemented, or explicitly recorded as a blocker.
- [ ] Every icon, button, filter, field, menu, dialog, grid, chart and panel has been compared against the reference.
- [ ] Geometry, sizes, spacing, typography, colors, icon dimensions and interaction states have visual evidence at a recorded viewport.
- [ ] Functional tests cover normal, edge, empty, loading, error, unauthorized and read-only states as applicable.
- [ ] Data is from the correct service/database and persists correctly; no fake/static KPI or decorative control is passed as live.
- [ ] Role/entitlement and organization boundaries are tested without changing real users, passwords or grants.
- [ ] Accessibility, keyboard, responsive and RTL/localization checks pass where applicable.
- [ ] Screenshot comparison and reviewer sign-off are attached to the page record.
- [ ] Tests pass and the exact commit/PR and official Preview verification are recorded.
- [ ] No unrelated page, route, shell, database, identity, authorization or infrastructure behavior regressed.

A code merge, successful build, agent self-report or screenshot of a page alone is NOT acceptance.

## 9. Required evidence record

Maintain a page-by-page record under `docs/traceability/pages/` (one Markdown or structured record per page, with an index). Every record must contain:

- Page ID, route, environment, status and owner.
- Inheritance chain and source paths.
- Capability/feature/traceability IDs.
- Exact Help title, URL, topic/section and relevant page.
- Functional control inventory and behavior mapping.
- Visual measurements and screenshot references.
- API/data/persistence and permission mapping.
- Acceptance test IDs and results.
- Before/after screenshots and visual comparison outcome.
- Known gaps, decisions and approvals.
- Commit SHA, PR, test run and official Preview verification date/result.

Update the master index and the existing capability/help matrix when a page or inheritance relationship changes. Keep historical evidence; do not silently replace a failed or earlier review with a passing claim.

## 10. Agent handoff and enforcement

Every task prompt and handoff must explicitly state:

> Read `/AGENTS.md` and `docs/standards/CUBI_PAGE_BY_PAGE_DESIGN_AND_ACCEPTANCE.md` plus all referenced page/Help records before starting. The single official Preview URL is fixed by this standard. First report the page's inheritance chain, exact Help topic and pre-build gap/spec. Do not code until that page-level specification and acceptance criteria are complete. Deliver functional and visual evidence, not a self-reported completion claim.

The receiving agent must confirm the files read and identify the page record before accepting the task. Reviewers must reject changes that lack the pre-build specification or page-level acceptance evidence.

No agent may change the canonical Preview URL, create a parallel official Preview, alter identity/access policy, or relax this acceptance gate as a side effect of an unrelated task.

## 11. Known existing baseline and gaps to reconcile

The repository already contains a 25-public-route CUBISITE matrix and the C01–C35 capability inheritance registry. These are valuable existing work and must be preserved, not recreated from scratch. However, they do not by themselves prove that every authenticated/admin/dashboard page has a complete feature-by-feature visual specification or has passed pixel-level acceptance.

The product owner previously supplied the CUBISITE v8 workbook and a separate 25-page route matrix. The workbook is not currently committed in the repository according to the existing matrix. Do not fabricate missing workbook rows (including C05); retrieve the authoritative source artifact from the product owner/project files and reconcile it before changing capability definitions.

The current traceability registries are the starting point for official Help topic mappings. Revalidate each entry against the live official Help before relying on it. Engineering and Enterprise Help sources remain separate.

**Definition of done for this standard:** this policy is committed, linked from repository-wide agent instructions, and every agent reads it before work; each page is then audited and accepted individually. Committing this policy does not falsely imply that all pages have already been audited or visually completed.
