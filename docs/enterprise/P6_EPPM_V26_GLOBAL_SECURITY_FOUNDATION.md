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
6. Built-in profile provisioning is idempotent. Custom profile creation cannot create or impersonate a built-in profile.

## Additional V26 user-access constraints now enforced

- Module access accepts only the V26 Users Page options: Projects, Portfolios, Resources, Contributor, Enterprise Reporting, Integration API, P6 Analytics, P6 Professional, Team Member, Timesheet, Visualizer, and Web Services.
- Contributor is mutually exclusive with every other module-access option, as specified by the V26 Users Page.
- Selected Resource Access accepts at most five resource roots; each selected root is intended to include its descendants. Admin Superuser retains all-resource access regardless of the stored setting.

Official HTML references:
- [Users Page](https://docs.oracle.com/cd/G48897_01/p6help/en/6187.htm)
- [Assigning Global Security Profiles](https://docs.oracle.com/cd/G48897_01/p6help/en/8117.htm)
- [Global Security Profiles Page](https://docs.oracle.com/cd/G48897_01/p6help/en/9003.htm)
- [Creating Global Security Profiles](https://docs.oracle.com/cd/G48897_01/p6help/en/35572.htm)

## Code

- `src/construction_pm/p6_global_security.py`
- `src/construction_pm/deployment/schema.py`
- `tests/test_p6_global_security.py`

## Security boundaries and incomplete work

This increment deliberately does **not** claim complete V26 parity:

- The complete ordered Global Security privilege catalogue and its exact Help dependencies are not yet encoded. Until that catalogue exists, custom global privilege strings are persisted but must not be used as an authorization decision.
- The domain predicate is not yet wired into every production API, web route, report, export, or service boundary. Do not use it as a substitute for route-level enforcement.
- Initial Admin Superuser assignment needs a controlled tenant bootstrap/provisioning path and a tested last-admin protection rule.
- Module-access values now validate against the V26 Users Page options and Contributor exclusivity; route/login enforcement is still required.
- Selected resource access now enforces the V26 maximum of five roots. Resource hierarchy selection still needs canonical Resource/WBS repositories, ancestry resolution, secure-code filtering, and exhaustive API enforcement.
- Project Owner and Contributor exceptions require the exact applicable EPPM V26 module-access rules and resource-assignment provenance before implementation; no broad role shortcut is allowed.
- Project OBS responsibility must be evaluated at EPS, project, WBS, issue, risk, and threshold levels. The documented higher-level OBS override behavior must be represented without weakening tenant boundaries.
- UI pages, user assignment workflows, revocation, full audit views, PostgreSQL live integration, and browser E2E remain acceptance gates.

## Required acceptance gates

- Machine-reviewed ordered manifest for all global privileges with one official V26 Help URL and dependency/exception test per row.
- Built-in profile bootstrap and at-least-one-Admin-Superuser invariants, including concurrent assignment/revocation tests.
- Module access enforced on login, session resolution, APIs, and navigation.
- Resource access enforced in every resource read/write/query/export and secure-code path.
- Project profile + OBS responsibility + Project Superuser + documented owner/Contributor exception tests.
- Cross-tenant, IDOR, revocation, audit immutability, and live PostgreSQL tests.
- Browser E2E for profile creation, assignment, module access, resource scope, project access, and denied paths.

No completion label should be applied until every gate passes on the same commit SHA.
