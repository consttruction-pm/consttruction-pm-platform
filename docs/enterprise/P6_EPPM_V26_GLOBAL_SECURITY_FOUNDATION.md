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
- Selected resource access now enforces the V26 maximum of five roots. The user_can_access_resource policy applies none/all/selected semantics, Admin Superuser's all-resource exception, tenant/user identity matching, and selected-root descendant inheritance against authoritative ancestry supplied by a tenant-scoped resource repository. Route-level integration remains required for all resource endpoints and associated-resource visibility.
- `No Global Privileges` has an explicit resolver seam in `P6GlobalSecurityAuthorizationPolicy`: it requires Projects module access and delegates project permission to an authoritative `project_permission(tenant_id, user_id, project_id, permission)` OBS/project-profile resolver. Without that resolver it remains fail-closed; a CUBI role is never treated as an OBS assignment. The production composition handoff is still pending because the OBS/WBS owner PR #1983 currently owns the shared production-runtime composition path. Project Owner and Contributor exceptions still require exact V26 module-access rules and resource-assignment provenance.
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
4. No Global Privileges: require Projects module access and delegate to the
   authoritative OBS/project-profile resolver seam. The policy denies if that
   resolver is not injected; generic CUBI roles are never OBS grants. The
   production composition still needs the shared-runtime handoff from PR #1983.
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
introduced by this change. The focused guard tests reject zero remaining administrators and allow
one or more remaining administrators.


## Resource Access hierarchy policy increment — 2026-11-17

Implemented user_can_access_resource in src/construction_pm/p6_global_security.py.
The policy consumes authoritative resource ancestry (resource itself plus parents)
from a tenant-scoped repository and enforces the V26 Users Page semantics:
- none: deny resource access;
- all: allow any resource in the caller's tenant-scoped query;
- selected: allow only selected roots and their descendants;
- Admin Superuser: all-resource exception;
- mismatched tenant/user identity, malformed ancestry, or ancestry that omits
  the requested resource: deny.

Focused unit tests cover descendant inclusion, sibling exclusion, none/all,
Admin Superuser, tenant mismatch, and malformed ancestry. This is a policy
slice, not completion of route enforcement: resource list/detail/mutation,
assignment pickers, associated-resource restrictions, filters, aggregations,
and exports must all call the same policy with repository-resolved ancestry.

Official V26 HTML Help:
- Users Page — Resource Access permits all resources, up to five selected resources, or no resources: https://docs.oracle.com/cd/G48897_01/p6help/en/6187.htm
- Module Access Detail Window — Resources module is distinct from Resource Access: https://docs.oracle.com/cd/G48897_01/p6help/en/6184.htm

## Exact-head PostgreSQL CI finding — 2026-11-17

At commit b96b0ae0961123c3c7691df5d23a49a250943085, Python 3.11/3.12/3.13
and web/desktop/client-sync typechecks passed, but the PostgreSQL workflow failed:
tests/integration/test_production_login_postgres_live.py had 7 failures
(175 passed). All seven failures involve fixture actors denied by the newly
required persisted Global Security assignment / Projects module gate, plus
cross-tenant and stale-revision error precedence. The shared integration test
file is owned by PR #1983; a detailed handoff comment was posted there, and
this branch did not modify that file. Re-run all workflows after the fixture
handoff and the new resource policy commits.


## Secure-code authorization policy increment — 2026-11-17

The global-profile domain now exposes explicit predicates for View, Assign,
Edit, and Add/Delete Secure Codes. The checks are fail-closed for unknown
actions, inactive profiles, and No Global Privileges; only the application-
generated Admin Superuser bypasses the individual secure-code grants. Custom
profiles must carry the exact normalized privilege for the requested action.

Oracle V26 Help defines secure-code protection across project, activity,
resource, role, and issue codes and their values. The hierarchy is Add/Delete
⇒ Edit + Assign + View; Edit ⇒ Assign + View; Assign ⇒ View. See:
- [Working with Security Profiles — Secure Codes](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/workingwithsecurityprofiles-36451a.html)
- [Global Security Profile Privileges Detail](https://docs.oracle.com/cd/G48897_01/p6help/en/102785.htm)

This is a domain authorization seam, not yet route enforcement. Every code
producer/consumer must invoke the predicate before detail serialization,
list/search/filter, counts/aggregations, assignment pickers, import/export,
and mutation. The Associated Resource user mapping and the full Project
Security Profile privilege-to-route matrix remain separate open work items;
no parity claim is made for them in this increment.


## Resource Access — first live API enforcement slice — 2026-11-17

The persisted global-security policy now exposes `can_access_resource(context,
resource_id,ancestor_resource_ids)`. It loads the caller's persisted global
assignment/profile, requires the Resources module for non-Admin-Superusers,
and delegates the exact none/all/selected + descendant rule to
`user_can_access_resource`. Missing assignment/profile, inactive profile,
missing Resources module, malformed ancestry, and tenant/user mismatch deny.

`P6ResourceAPI` now consumes that policy at the authoritative resource-master
boundary. GET detail hides out-of-scope resources as not found; list filters
out-of-scope rows before serialization; create checks the new resource's
repository-resolved parent chain; update checks both the existing record and
its proposed new ancestry so a resource cannot be moved across the caller's
scope. Ancestry is derived from the same tenant/project/revision-scoped master
repository, never from client-supplied ancestry.

This closes the master register HTTP route because it delegates to
`P6ResourceAPI`. It does not yet close every resource-bearing route: assignment,
capacity, rates, spread, role-resource pickers, exchange/import/export, and
associated-resource visibility need the same gate. The legacy policy adapter
path remains compatible for non-P6 preview/test compositions; production must
supply `P6GlobalSecurityAuthorizationPolicy` to activate persisted V26 checks.

Official HTML Help: [Users Page — Resource Access and Associated Resource](https://docs.oracle.com/cd/G48897_01/p6help/en/6187.htm),
[Module Access Detail — Resources module](https://docs.oracle.com/cd/G48897_01/p6help/en/6184.htm),
and [Working with Security Profiles — V26](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/workingwithsecurityprofiles-36451a.html).

Acceptance still requires PostgreSQL integration coverage and browser E2E on
the exact final SHA. No completion claim is made by this slice.


### Resource Access expansion to resource-bearing APIs — 2026-11-17

A shared repository-backed gate now resolves the requested resource's
self-to-root ancestry and is consumed by:
- resource assignment, assignment-period, and spread reads;
- resource assignment and assignment-period writes;
- effective-dated resource capacity and rate reads/writes;
- role-to-resource mapping list, add, and remove operations.

Read lists filter before DTO serialization; detail reads hide inaccessible
records; writes reject before persistence. The production WSGI composition
replaces these APIs' authorization policy with the persisted global policy and
injects the same authoritative resource-master repository. If a P6 global
policy is active but no resource-master repository is supplied, composition
fails with `P6_RESOURCE_ACCESS_REPOSITORY_REQUIRED` rather than silently
running without ancestry enforcement. The preview composition now supplies its
resource master to all resource read/write APIs as well.

Tests added for the shared ancestry resolver, fail-closed configuration,
master-register list/detail filtering, assignment list/detail filtering,
selected-root descendants, sibling denial, and persisted Resources-module
requirements. Live PostgreSQL and browser checks are still required; the
resource-bearing API matrix should be reviewed against every remaining import,
export, role picker, and reporting surface before acceptance.
