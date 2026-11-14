# CUBI Product Surface Architecture — Two Complementary Environments

**Status:** Product-owner decision / mandatory architecture principle  
**Decision date:** 2026-11-14  
**Decision record:** [CUBI-ARCH-ENV-001](../architecture/CUBI_TWO_ENVIRONMENT_PRODUCT_ARCHITECTURE.md)

## 1. Product identity

CUBI is one product platform with two complementary product environments:

- **CUBI Engineering** — the primary engineering and project-controls environment.
- **CUBI Enterprise** — the organizational and project-collaboration environment.

The environments have distinct responsibilities and must not become duplicate products. The Engineering Visual Workspace remains the canonical Engineering shell. Enterprise is a separately developed environment and must not disrupt Engineering completion.

The earlier one-environment-only decision is superseded to the extent that it prohibited CUBI Enterprise. Its Engineering no-regression protections remain in force.

## 2. Public website and product entry

The public website contains:
1. Home and normal public/informational pages.
2. A product entry flow.
3. The personal workbench / personal dashboard.
4. Role or working-context selection.
5. Selection of an authorized environment: CUBI Engineering or CUBI Enterprise.

The personal workbench is an entry/personal coordination surface, not a third product environment. It must not replace or absorb either environment's workspace.

## 3. Temporary entry behavior and final authentication

The final login/authentication system is not yet implemented. Until its final-stage delivery, the role-selection step is a temporary substitute for login for current development navigation only. It is not production authentication and must not be treated as proof of identity or authorization.

At the final authentication milestone:
- roles and environment choices are sourced from authenticated identity and server-side grants;
- users see only the roles and environments they are authorized to access;
- the intended personal workbench → role/context → environment selection flow is preserved unless separately approved.

## 4. Environment responsibilities

### CUBI Engineering

- Primary current completion workstream.
- Owns engineering/project-control behavior and authoritative calculations and records.
- Its current Visual Workspace shell, layout, routes, data contracts, tests and delivery sequence are protected from unrelated Enterprise changes.
- The first development agent continues its implementation. ChatGPT coordinates by issuing scoped instructions and reviewing boundaries/evidence.

### CUBI Enterprise

- Separate, currently developing environment.
- Owns organizational and collaboration capabilities, including PMBOK-aligned management features, teams, tasks, workflows, approvals, communication, operations, stakeholder collaboration and portfolio/executive coordination.
- ChatGPT owns its architecture definition, workstream separation, gap analysis, planning and staged coordination.
- Its unfinished state is not a blocker or prerequisite for Engineering or website completion.
- Its designated current entry point is the hidden Enterprise menu/entry, subject to the product's role and environment access rules.

## 5. Form Builder is shared

Form Builder exists as a cross-environment capability:
- Both Engineering and Enterprise may use forms and form workflows in their own contexts.
- Form libraries, schema/version ownership, access, submissions and approval boundaries must be explicit.
- The shared Formula/Calculation Core remains the sole authority for supported calculations.
- Form Builder must not create shadow engineering calculations.
- CUBI-FORM-CALC-001, CUBI-FORM-DESIGN-002 and issues #1481/#1617 remain mandatory implementation references; documentation is not implementation evidence.

## 6. Integration and no-interference rules

- Distinct environment responsibilities, code ownership, navigation and release boundaries.
- Versioned, permission-checked APIs/events for cross-environment operations.
- Engineering remains authoritative for engineering calculations and records.
- No direct Enterprise access to Engineering operational tables unless a separately approved architecture explicitly establishes a safe contract.
- Enterprise jobs must not degrade Engineering runtime or delivery gates.
- No broad Engineering shell, route, database or calculation refactor is authorized by Enterprise work.

## 7. Delivery priority

CUBI Engineering and the currently committed website work remain the active completion priority. CUBI Enterprise proceeds as a separate parallel workstream only where it cannot block, delay or destabilize Engineering.

No unfinished Enterprise module, PMBOK capability, Form Builder feature, personal dashboard or authentication flow may be made a prerequisite for Engineering completion.

## 8. Acceptance

The platform is accepted only when the two environments, the personal entry flow, temporary role-selection limitation, final authentication boundary, shared Form Builder rules and non-interference guarantees are demonstrated with implementation and test evidence.