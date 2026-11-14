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

1. User reaches the personal workbench / personal dashboard after entering the product.
2. User selects or confirms their role / working context.
3. User chooses an authorized environment:
   - CUBI Engineering; or
   - CUBI Enterprise (currently reached through the designated hidden menu / entry point).
4. The selected environment opens in its own appropriate workspace context.

**Temporary pre-authentication behavior:** The product does not yet have the final login/authentication flow. Until the final authentication milestone, the role-selection step is a temporary login substitute for development and navigation purposes. It must be treated as provisional, not as production-grade identity verification or authorization.

**Final-stage behavior:** At the final authentication stage, role and environment choices must be derived from authenticated identity, grants and access policy. The user must only be offered environments and roles they are authorized to use. Preserve the intended personal workbench → role/context → environment selection sequence unless a separately approved UX decision changes it.

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
