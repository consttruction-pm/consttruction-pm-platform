# P6 EPPM V26 Global Security Profile Foundation

Status: implementation foundation; **not full V26 security parity**.

## Normative Oracle V26 HTML Help

- [Working with Security Profiles](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/workingwithsecurityprofiles-36451a.html)
- [About Security Profiles](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/aboutsecurityprofiles-6595a.html)
- [About User Access](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-app-admin/aboutuseraccess-6597a.html)
- [Working with User Access](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-app-admin/workingwithuseraccess-36439a.html)
- [Project Security Profiles Page](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/9004.html)
- [Assigning OBS Elements and Project Profiles](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-app-admin/assigningobselementsandprojectprofilesince-product-names_p6-eppm-short__-6876a.html)
- [Project Profile Service](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-ws-ref/projectprofileservice-41917a.html)

## V26 semantics represented in this increment

1. Global Security Profiles are a separate authorization layer from project profiles, CUBI organization roles, and team membership.
2. Admin Superuser is an application-generated, immutable profile. Only this profile can produce the global project-access bypass represented by the domain predicate.
3. No Global Privileges is a distinct application-generated profile. It has no explicit global privilege grants but is represented as read-only for global data; an OBS/project profile may still grant scoped project access.
4. Every user-global-security record has one global profile assignment, an explicit module-access set, and an explicit resource-access mode: none, all, or selected hierarchy roots.
5. Global profile definitions and user assignments are tenant-scoped, revisioned, and append-audited. Audit rows are protected from update/delete.
6. Built-in profile provisioning is idempotent. Custom profile creation cannot create or impersonate a built-in profile ID/name. Custom profiles persist descriptions and the default-profile indicator; duplicate, edit, default selection, and guarded delete operations are audited and revision-checked.

## Additional V26 user-access constraints now enforced

- Module access accepts only the V26 Users Page options: Projects, Portfolios, Resources, Contributor, Enterprise Reports, Integration API, P6 Analytics, P6 Professional, Team Member, Timesheet, Visualizer, and Web Services.
- Contributor is mutually exclusive with every other module-access option, as specified by the V26 Users Page.
- Selected Resource Access accepts at most five resource roots; each selected root is intended to include its descendants. Admin Superuser retains all-resource access regardless of the stored setting.

Official HTML references:
- [Global Security Profiles Page — Add, Delete, Set As Default, Duplicate, Description and Default Profile indicator](https://docs.oracle.com/cd/G48897_01/p6help/en/9003.htm)
- [Global Privileges Detail Window — all 72 global privilege definitions and dependencies](https://docs.oracle.com/cd/G48897_01/p6help/en/102785.htm)
- [Module Access Detail Window — exact module names and Contributor exclusivity](https://docs.oracle.com/cd/G48897_01/p6help/en/6184.htm)
- [Users Page](https://docs.oracle.com/cd/G48897_01/p6help/en/6187.htm)
- [Assigning Global Security Profiles](https://docs.oracle.com/cd/G48897_01/p6help/en/8117.htm)
- [Global Security Profiles Page](https://docs.oracle.com/cd/G48897_01/p6help/en/9003.htm)
- [Privileges Detail Window of the Global Security Profiles Page](https://docs.oracle.com/cd/G48897_01/p6help/en/102785.htm)
- [Module Access Detail Window of the Users Page](https://docs.oracle.com/cd/G48897_01/p6help/en/6184.htm)

## Code

- `src/construction_pm/p6_global_security.py`
- `src/construction_pm/deployment/schema.py`
- `tests/test_p6_global_security.py`

## Security boundaries and incomplete work

This increment deliberately does **not** claim complete V26 parity:

- The V26 Global Security privilege catalogue is now encoded as 72 entries across the seven Help categories, with documented code/resource hierarchy dependencies normalized and validated. Route-level authorization still needs to consume this catalogue before the values may be treated as effective grants.
- The persisted global assignment/profile is now composed into the production `AuthorizationPolicy` used by the production lifecycle API and the APIs composed with that policy. Missing assignments and inactive/missing profiles fail closed; the V26 Admin Superuser bypass is evaluated from the persisted built-in identity only; non-admin users must have Projects module access before the existing project policy is evaluated. This does not yet prove every non-policy route, report, export, or static navigation surface is gated.
- Initial Admin Superuser assignment still needs a controlled tenant bootstrap/provisioning path and a tested last-admin protection rule. Until then, the new production policy intentionally denies project API access for users without a persisted assignment.
- Module-access values now validate against the V26 Users Page options and Contributor exclusivity; route/login enforcement is still required.
- Selected resource access now enforces the V26 maximum of five roots. Resource hierarchy selection still needs canonical Resource/WBS repositories, ancestry resolution, secure-code filtering, and exhaustive API enforcement.
- `No Global Privileges` is currently denied by the production project policy until an authoritative OBS-to-project assignment resolver exists. This is deliberately fail-closed: a CUBI role is not a substitute for Oracle's OBS assignment. Project Owner and Contributor exceptions still require exact V26 module-access rules and resource-assignment provenance.
- Project OBS responsibility must be evaluated at EPS, project, WBS, issue, risk, and threshold levels. The documented higher-level OBS override behavior must be represented without weakening tenant boundaries.
- UI pages, user assignment workflows, revocation, full audit views, and browser E2E remain acceptance gates. The PostgreSQL lifecycle tests now cover profile duplicate/default/edit/delete, revisions, and audit behavior.

## Required acceptance gates

- Machine-reviewed ordered manifest for all 72 global privileges with one official V26 Help URL and dependency/exception test per row (catalogue is now encoded; per-row exhaustive behavior tests and route mapping remain).
- Built-in profile bootstrap and at-least-one-Admin-Superuser invariants, including concurrent assignment/revocation tests.
- Module access enforced on login, session resolution, APIs, and navigation. The production project-API gate now requires a persisted assignment and Projects module access for non-admin users; remaining modules and navigation still require coverage.
- Resource access enforced in every resource read/write/query/export and secure-code path.
- Project profile + OBS responsibility + Project Superuser + documented owner/Contributor exception tests.
- Cross-tenant, IDOR, revocation, audit immutability, and live PostgreSQL tests.
- Browser E2E for profile creation, assignment, module access, resource scope, project access, and denied paths.

No completion label should be applied until every gate passes on the same commit SHA.


## Production authorization integration — 2026-11-17

The global profile model is no longer only a domain primitive. The production
runtime now composes `P6GlobalSecurityAuthorizationPolicy` around the existing
role policy and injects it into the shared production API composition. The
policy applies these rules:

1. Missing user-global-security assignment: deny.
2. Missing or inactive assigned profile: deny.
3. Application-generated Admin Superuser: allow the project permission without
   falling through to the coarse CUBI role map, matching the documented global
   project bypass.
4. No Global Privileges: deny project API access until the OBS assignment
   resolver is available; do not infer OBS scope from generic CUBI roles.
5. Other profiles: require the Projects module and then the existing project
   policy. This is an interim composition; the project privilege catalogue and
   per-resource OBS/WBS scope still need to replace broad role permissions.

Focused policy tests cover missing assignment, Admin Superuser bypass,
No Global Privileges fail-closed behavior, missing Projects module, and the
normal project-role conjunction. These changes are committed in the PR branch;
the exact-SHA GitHub checks are pending at the time of this update.


## Last-Admin Superuser concurrency invariant — 2026-11-17

Global assignment mutations now take a tenant-scoped PostgreSQL transaction
advisory lock before reading or changing assignments. When an existing
Admin Superuser assignment is changed to another profile, the repository
counts active, application-generated Admin Superuser assignments and rejects
the change if it would leave the tenant with none
(`LAST_ADMIN_SUPERUSER_REQUIRED`). The lock serializes competing revocations,
so two concurrent requests cannot both remove the final pair of administrators.

This protects the last-admin invariant for profile reassignment. It does not
create the first Admin Superuser: initial tenant bootstrap still requires a
controlled operator provisioning path, and no public bootstrap endpoint is
introduced by this change. The focused guard tests cover zero, one, and two
remaining administrators.
