# CUBI Two-Environment Product Architecture & Workstream Boundary

**Decision ID:** CUBI-ARCH-ENV-001  
**Status:** Product-owner direction — architecture baseline for planning; implementation remains staged  
**Decision date:** 2026-11-14  
**Supersedes:** The one-product-environment restriction in README.md, docs/product/CUBI_PRODUCT_SURFACE_ARCHITECTURE.md and issue #1712, to the extent it prohibits CUBI Enterprise.  
**Related:** Form Builder contracts CUBI-FORM-CALC-001 and CUBI-FORM-DESIGN-002; issues #1481 and #1617.

## 1. Product structure

CUBI is one product platform with two complementary work environments:

1. **CUBI Engineering** — the primary engineering and project-controls environment. It owns engineering execution, project planning and controls, schedule, resource/cost and other authoritative engineering calculations and data.
2. **CUBI Enterprise** — the organizational and project-collaboration environment. It owns organizational processes, PMBOK-aligned management capabilities, collaboration and cross-project coordination.

This is a two-environment platform, not two competing products and not a second copy of the Engineering application. Each environment has its own responsibility boundary and must not duplicate the other's authoritative domain logic.

## 2. CUBI Engineering — current delivery priority

CUBI Engineering is the active primary completion workstream. Its completion must continue without interruption.

- The existing Engineering implementation remains the source of truth for engineering and project-control calculations and data.
- The first development agent continues implementing CUBI Engineering.
- ChatGPT coordinates this workstream by defining scoped instructions, sequencing, boundary constraints and review requirements for that agent.
- CUBI Enterprise design or implementation must not block, delay, destabilize, or impose prerequisite work on Engineering completion.
- No Engineering feature, route, shell, schema, calculation, test baseline or delivery sequence may be changed merely to accommodate Enterprise unless separately approved and demonstrated to be non-disruptive.
- Shared capabilities may be reused only through explicit contracts and without transferring ownership of Engineering calculations.

## 3. CUBI Enterprise — separate workstream ownership

ChatGPT is responsible for the CUBI Enterprise architecture, scope definition, workstream separation, gap analysis, coordination and staged development planning.

CUBI Enterprise is currently under development and is not yet a completed or fully established runtime environment. Its unfinished state must not be treated as a release blocker or completion dependency for CUBI Engineering or the public website.

Enterprise scope includes:
- Organizational structures, people, roles, teams and access governance.
- Personal workbench, personal dashboard and daily command center.
- Team and cross-project task/action management.
- PMBOK-aligned project and organizational management capabilities, tailored to project context rather than presented as mandatory universal templates.
- Workflow, feedback, review, approval, decision and escalation processes.
- Organizational communication, notifications and collaboration.
- Operations and job monitoring for Enterprise-owned services.
- Project and stakeholder portals.
- Portfolio and executive-level management, read models and decision coordination.
- Integration and organizational knowledge capabilities.

The existing PMBOK-related product work and organizational capabilities belong to the CUBI Enterprise product domain unless a specific calculation or authoritative engineering record remains owned by CUBI Engineering.


## 3A. CUBI Enterprise — canonical product scope and eight modules

CUBI Enterprise is an **EPPM-inspired independent environment** within the single CUBI platform. Its core domain includes teams and tasks, workflow and approvals, communications, organizational operations, portfolio management and PMBOK-aligned capabilities. The following eight modules are the canonical functional decomposition; they are product modules, not a requirement to create eight unrelated application shells.

### 1. Team & Task Center — team and task management
- Create teams and specialist groups.
- Assign tasks to individuals or groups.
- Manage due dates, priority, status and task dependencies.
- Support personal tasks and project tasks.
- Link tasks to authorized Engineering activities, WBS elements, documents and risks through stable references.
- Provide a per-user My Tasks view.
- Advanced capability: project events (for example, an activity delay) may propose a corrective task. Event-to-task creation must be policy-controlled, traceable and must not silently mutate Engineering data.

### 2. Feedback & Approval Center
- Submit requests to correct reported progress.
- Approve or reject submitted information.
- Return submissions for correction with a mandatory reason.
- Preserve decision history and the accountable decision-maker.
- Support multi-stage approval.
- Clearly distinguish proposed/submitted information from approved/authoritative information.
- Advanced capability: before approval, show a read-only impact preview for schedule, cost and critical-path consequences using authoritative Engineering services and revision-pinned source data. Enterprise must not calculate these impacts itself.

### 3. Operations & Job Center
- Show processing/job status, queues and execution times.
- Expose failures and actionable failure causes.
- Support controlled retry with idempotency and authorization safeguards.
- Report scheduled processing.
- Preserve user-attributed operation history and audit context.
- Advanced capability: one operations center for users and administrators, with ordinary, sensitive and system-level processing visibly classified and separately permissioned.

### 4. Workflow Studio
- Design workflow stages and transitions.
- Assign responsible users and delegates.
- Define stage-entry/exit conditions.
- Support approve, reject and return-for-correction paths.
- Configure response deadlines, reminders and alerts.
- Provide reusable project-process templates.
- Advanced capability: authorized organization administrators can design and version workflows without changing CUBI Engineering code. Workflow publication requires validation, versioning, permissions and audit.

### 5. Organization & Access Center
- Manage members and user invitations.
- Manage roles and granular permissions.
- Manage team and project memberships.
- Assign managers and approvers.
- Preserve permission-change history.
- Provide access reports.
- Advanced capability: policy decisions consider role, organization, project, team, data classification/type and requested operation—not only a global user role. Enforce authorization server-side and audit sensitive decisions.

### 6. Project Portal
- Publish permitted project reports.
- Share approved project status.
- Provide constrained access for clients/owners, contractors and consultants.
- Display approved documents and outputs.
- Support expiring and revocable share links.
- Advanced capability: provide stakeholder-specific portal views and content filtered by explicit grants, project membership, document classification and purpose. Portal access is not a bypass around project authorization.

### 7. Integration Hub
- Manage versioned APIs and webhooks.
- Connect approved organizational systems.
- Manage connector credentials, scopes and permissions securely.
- Preserve data-exchange history.
- Monitor integration failures and support controlled replay/retry.
- Provide controlled import and export.
- Advanced capability: a connector catalog and organization-specific connector definitions, with secret isolation, schema/version validation, rate limits, audit and tenant isolation.

### 8. Portfolio & Executive Center
- List projects the organization is authorized to see.
- Show project status and health.
- Present KPIs, trends and comparisons.
- Surface management alerts.
- Produce organization-level performance reporting.
- Advanced capability: analyze the potential impact of one project's delay on resources, commitments and other project priorities using authoritative, revision-aware source data. Enterprise orchestrates and presents analysis; it does not reproduce Engineering calculations.

## 3B. Enterprise capabilities beyond conventional EPPM

These six cross-cutting capabilities extend the eight modules and may be delivered incrementally; they are not additional competing environments:

1. **Personal Command Center** — each person's daily tasks, notifications, approvals and follow-ups.
2. **Cross-Project Action Center** — consolidated tasks and requests spanning multiple authorized projects.
3. **Intelligent Escalation** — detect overdue/stalled items and route them to the next accountable level under explicit escalation policies.
4. **Stakeholder Portal** — tailored workspaces for clients/owners, consultants, contractors and executives; implemented through the Project Portal with distinct stakeholder permissions.
5. **Organizational Knowledge Center** — connect decisions, documents, lessons learned and project knowledge with provenance and access control.
6. **Engineering Impact Preview** — preview the possible project effects of organizational decisions before approval by requesting analysis from authoritative Engineering services. This is a read/preview integration, not a second schedule/cost calculation engine.

## 3C. Capability ownership and shared product features

- PMBOK-aligned project-management capabilities and organizational capabilities are in the CUBI Enterprise domain.
- Form Builder is shared by CUBI Engineering and CUBI Enterprise. Form design, libraries, submissions and workflow usage are context-specific, with explicit ownership, versioning and access policies. Calculated fields continue to use the approved shared Formula/Calculation Core.
- Communications, team, invitation, identity, entitlements and storage capabilities must reuse and reconcile with `docs/requirements/CUBI_SUBSCRIPTIONS_IDENTITY_TEAMS_MESSAGING_AND_STORAGE_V1.md`, its versioned schema and issue #1605. Do not create a second identity/team/messaging implementation.
- Portfolio read models and approval/decision boundaries must reuse and extend the existing Stage 34.2.9 and Stage 34.2.10 contracts and their subsequent lifecycle/persistence stages. Preserve opaque references to authoritative Engineering results, revision safety and human approval; do not create duplicate project calculations or automatic project mutations.
- Existing background processing, reporting, operations monitoring, explicit access-control and audit-event infrastructure must be inventoried and reused where contracts fit. New modules must not introduce parallel job queues, duplicate audit trails or shadow permission systems without an approved gap analysis.
- The cited Dribbble/product/vendor references in the product proposal are visual or capability inspiration only; they do not define vendor dependencies, integrations, licensed assets or implementation requirements.

## 3D. Implementation decomposition and sequencing

The eight modules are the target functional architecture, not a mandate to implement them simultaneously. Initial implementation order should follow dependency and reuse analysis:
1. Inventory and contract mapping: identity, organization, teams, messaging, permissions, audit, jobs, reports, forms and portfolio.
2. Enterprise foundations: personal workbench context, organization/access, team/task and communication integration.
3. Workflow and feedback/approval, including versioned Workflow Studio and decision history.
4. Operations & Job Center and Integration Hub, reusing existing job/report/monitoring contracts.
5. Project Portal and Portfolio & Executive Center.
6. Cross-cutting enhancements: Personal Command Center, Cross-Project Action Center, Intelligent Escalation, Organizational Knowledge Center and Engineering Impact Preview.

This sequence is an Enterprise-only planning track. It does not change CUBI Engineering's active completion schedule or create prerequisites for it. Every capability must be marked as existing, partial, planned or verified only with evidence from source, persistence, tests and the target runtime; a specification or prototype is not proof of completion.

## 4. Form Builder is shared across both environments

Form Builder is a cross-environment capability, not exclusively an Enterprise module and not exclusively an Engineering module.

- Both environments may provide form creation, configuration, templates, data capture, review, approval, reporting and export appropriate to their own workflows.
- Organization-wide form libraries and project form libraries must preserve their defined ownership, versioning and permission rules.
- Each environment consumes forms through its own authorized context and application workflows.
- Form definitions and submissions must not cause duplicated schedule, cost, resource, EVM or other authoritative calculations.
- Calculated fields must use the approved shared Formula/Calculation Core and the contracts in CUBI-FORM-CALC-001.
- The Form Designer requirements in CUBI-FORM-DESIGN-002 and execution mapping in issues #1481/#1617 remain mandatory. Existing documents/issues are not proof that every feature is implemented.

## 5. Entry, role selection and environment selection

The intended post-entry journey is:

1. User selects or confirms their role / working context. While final authentication is unavailable, this role selection temporarily serves as the login step.
2. The selected role/context opens the user's personal workbench / personal dashboard.
3. From the personal workbench, the user chooses an authorized environment:
   - CUBI Engineering; or
   - CUBI Enterprise (currently reached through the designated hidden menu / entry point).
4. The selected environment opens in its own appropriate workspace context.

**Temporary pre-authentication behavior:** The product does not yet have the final login/authentication flow. Until the final authentication milestone, the role-selection step is a temporary login substitute; after role selection the user enters their personal workbench/dashboard and chooses an environment from there. This is provisional and is not production-grade identity verification or authorization.

**Final-stage behavior:** At the final authentication stage, role and environment choices must be derived from authenticated identity, grants and access policy. The user must only be offered environments and roles they are authorized to use. Preserve the intended role/authentication → personal workbench/dashboard → environment selection sequence unless a separately approved UX decision changes it.

The personal workbench is an entry and personal coordination surface; it is not a third product environment and must not be used to merge the two environment shells.

## 6. Environment separation and integration

- Engineering and Enterprise must have clearly separated code ownership, application responsibilities, navigation namespaces and release boundaries.
- Enterprise-owned operational data must have an explicit ownership and persistence boundary; do not assume direct access to Engineering operational tables.
- Cross-environment exchange must use documented, versioned APIs/events and permission-checked application services.
- Engineering remains authoritative for Engineering calculations and records. Enterprise may request, display or coordinate approved changes but must not implement shadow calculation engines.
- Identity may be shared at the platform level, while environment grants and resource permissions remain explicit and auditable.
- Background jobs and resource-intensive Enterprise work must not degrade Engineering runtime or release gates.
- Shared components such as Form Builder, identity primitives or design-system elements require explicit ownership, contracts and compatibility tests; shared does not mean coupled deployment.

## 7. Delivery priority and non-blocking rule

The active priority is:

**P0 — Complete CUBI Engineering and the currently committed website work.**  
**Parallel, separately managed — Define and develop CUBI Enterprise without introducing dependencies into the P0 Engineering path.**

Enterprise work may proceed in parallel only within an isolated scope. If a proposed Enterprise task needs a change to Engineering, the Engineering owner must first receive a narrowly scoped proposal and explicit approval. No broad refactor, route migration, shell replacement, shared database change or release coupling is authorized by this decision.

An unfinished Enterprise feature, menu, dashboard, login flow, PMBOK module or form workflow must never be used as a reason to pause Engineering completion.

## 8. Reconciliation with earlier one-workspace documents

The former one-environment statements were written before this product-owner decision. They are superseded only insofar as they prohibit the second CUBI Enterprise environment.

The existing CUBI Engineering Visual Workspace remains the canonical Engineering shell and must retain its approved layout and behavior. This decision does not authorize redesigning it, replacing it with a dashboard, or moving its existing tools.

The product surface and navigation specifications must now distinguish:
- public website;
- personal workbench / entry surface;
- CUBI Engineering environment;
- CUBI Enterprise environment.

The prior issue #1712 must be treated as superseded for the one-environment prohibition, while its no-regression requirements for the existing Engineering workspace remain applicable. Runtime implementation and acceptance evidence must be updated in a later, separately scoped work package.

## 9. Non-goals and prohibitions

- Do not implement CUBI Enterprise as a duplicate of CUBI Engineering.
- Do not create a second scheduling, CPM, calendar, resource-leveling, cost or EVM calculation engine.
- Do not force Enterprise completion before Engineering or website completion.
- Do not alter Engineering's current delivery priority or delegate its implementation ownership to the Enterprise workstream.
- Do not treat temporary role selection as secure authentication.
- Do not claim Enterprise is complete merely because architecture documents, menus, prototypes or partial modules exist.
- Do not claim Form Builder is complete without end-to-end UI, persistence, permissions, calculations, approvals, exports and tests.

## 10. Acceptance gates

- [ ] Product documentation recognizes one CUBI platform with two complementary environments.
- [ ] Engineering remains the primary active completion workstream and its existing shell is protected.
- [ ] Enterprise has a separately owned architecture and delivery backlog.
- [ ] PMBOK and organizational capabilities are assigned to Enterprise; Form Builder is explicitly shared.
- [ ] Personal workbench → role/context selection → authorized environment selection is documented.
- [ ] Temporary role-selection behavior is clearly marked as non-authentication.
- [ ] Final authentication and environment grants are deferred to the final authentication milestone.
- [ ] Engineering/Enterprise data, code, runtime and release boundaries are documented and tested.
- [ ] No Enterprise task is a dependency or blocker for Engineering completion.
- [ ] Existing form and PMBOK specifications/issues are reconciled without falsely marking implementation complete.


## 11. Product delivery priority — Engineering first, Enterprise second

This priority is mandatory and overrides any interpretation of Enterprise as an equal-priority delivery stream.

- **Priority 1: CUBI Engineering.** Its active completion plan, staffing, delivery cadence and release path remain primary. Enterprise planning or implementation must not reduce Engineering throughput, divert its assigned implementation agent, add prerequisites, or delay its milestones.
- **Priority 2: CUBI Enterprise.** Enterprise is a separately governed workstream that may progress only with available capacity and isolated changes. If parallel work creates a resource, review, runtime, CI, release or coordination conflict, Engineering wins and Enterprise pauses or is resequenced.
- Enterprise is not allowed to make Engineering completion conditional on shared shell, shared route, common database, authentication redesign, visual refresh or any Enterprise module.
- No shared change is presumed harmless: it requires an explicit impact assessment, ownership, compatibility evidence and approval from the Engineering owner where Engineering is affected.
- Existing Enterprise documentation, prototypes, branch work or draft PRs do not change this priority.

## 12. Enterprise functional roadmap — EPPM-first

The first functional objective of CUBI Enterprise is to cover the organizational and project-management capabilities of **Oracle Primavera P6 EPPM** to a useful, coherent level. The roadmap is capability-oriented, not a commitment to reproduce Oracle screens or implementation details.

The initial EPPM-first order is:

1. Dashboards, personal landing views and configurable portlets.
2. Portfolio management, portfolio views and executive monitoring.
3. Project overview, project hierarchy/EPS and authorized project navigation.
4. Resource administration, resource assignments and organizational capacity views.
5. Team Member-style work execution, task status, timesheet/work reporting where applicable, and approval workflows.
6. Risk and issue management, including ownership, scoring, response and follow-up.
7. Reports, performance status, KPI views and management summaries.
8. Enterprise administration, access governance, role/security configuration and audit visibility.
9. Project document access and document-related controls to the extent covered by the selected P6 EPPM scope.

Oracle Help topics and version-specific product documentation are the reference library for functional discovery and acceptance criteria. Each capability must have a documented CUBI mapping, source/help reference, existing-code reuse assessment, gap list and testable acceptance criteria. P6 EPPM and Primavera Unifier are distinct products: Unifier capabilities must not be represented as P6 EPPM parity. They may inform later, separately assessed Enterprise extensions.

## 13. Enterprise extensions — feasibility-gated and incremental

After the EPPM-first baseline, the following proposed extensions may be assessed individually. They are not approved as an unconditional build commitment and must not displace Engineering priority or the EPPM-first sequence.

1. Resource & Capacity Management extensions beyond the EPPM baseline.
2. Advanced Risk & Schedule Assurance.
3. Scenario & What-if Analysis.
4. Benefits & Value Realization.
5. Enterprise Knowledge & PMO Framework.
6. Document & Information Management beyond the baseline document capabilities.
7. Contract & Commercial Management (informed by Primavera Unifier, not mislabeled as P6 EPPM).
8. Field & Mobile Operations.

For each extension, perform a feasibility review before implementation: business value, overlap with current CUBI capabilities, reuse candidates, authoritative data ownership, required new persistence/API/UI, security/audit implications, delivery cost, operational impact and measurable acceptance criteria. Prefer a small, independently releasable increment. Defer or reject features whose marginal value does not justify new complexity.

## 14. Reuse-first and minimal-change rule

The governing implementation principle is **maximum product value with minimum safe change**.

- Inspect and prove the current runtime capability before proposing a replacement.
- Reuse existing identity, organization/team, task, workflow, forms, reporting, portfolio, operations, audit and storage foundations where their contracts and runtime behavior fit.
- Do not create parallel services, tables, permission models, job systems, reporting pipelines or calculation engines merely to make a module appear self-contained.
- Add only the smallest missing capability at a clear ownership boundary.
- External integrations are not an active delivery focus in this roadmap. Preserve architectural extensibility, but do not spend current Enterprise capacity on connector catalog expansion or broad third-party integration work.
- Engineering remains the authority for engineering calculations and records. Enterprise may consume authorized, versioned and revision-aware results; it must not reproduce Engineering calculation logic.

## 15. Design exploration and future CUBI design-system decision

CUBI should ultimately provide a professional and coherent product experience. However, **a shared visual system, shared shell, shared tokens or shared component library are not current implementation prerequisites or acceptance blockers**. The initial design of each environment must remain free to respond to its real users, workflows, information density and technical constraints.

- Design CUBI Engineering and CUBI Enterprise initially according to their own product needs. Preserve the existing Engineering shell and do not redesign it for visual consistency.
- Treat a common CUBI identity, shared design tokens, shared components and common shell conventions as design hypotheses to explore—not mandatory constraints for initial product design or implementation.
- Do not force early convergence of color palettes, typography, navigation, layout, controls or component behavior where doing so could reduce usability, conflict with existing architecture or cause unnecessary rework.
- Evaluate commonality after the initial designs and representative screens exist. Compare actual user journeys, responsive behavior, RTL/Persian and LTR behavior, accessibility, visual clarity and technical compatibility.
- Any proposed shared system must pass documented design reviews and relevant automated/manual tests, including regression and environment-specific acceptance tests. Adopt it only after the responsible product owners approve the evidence.
- Until that approval, environment-specific design decisions are permitted. Avoid arbitrary inconsistency, but do not treat vendor-inspired patterns or a shared CUBI theme as implementation mandates.
- Any change affecting the Engineering shell, routes, CSS, components or behavior requires a separate, narrowly scoped proposal, compatibility evidence and explicit Engineering-owner approval.
- A design-system specification or prototype is not evidence that a shared system has been implemented or validated.

The exploratory design brief and future evaluation criteria are documented in `docs/design/CUBI_PRODUCT_DESIGN_SYSTEM_AND_ENVIRONMENT_SHELLS.md`. Its contents are non-binding until a later explicit approval decision.
