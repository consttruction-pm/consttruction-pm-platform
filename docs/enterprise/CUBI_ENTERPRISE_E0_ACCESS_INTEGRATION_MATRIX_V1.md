# CUBI Enterprise E0 — Shared Identity, Security and Project Access Integration Matrix

**Status:** Active integration/acceptance control document; not a claim that E0 is released or fully compliant.  
**Date:** 2026-11-17  
**Architecture parent:** `CUBI-ARCH-ENV-001`, GitHub issue #1928.  
**Priority:** Enterprise-first E0 foundation tranche, with Engineering records/calculations remaining authoritative.  
**Baseline snapshot:** `main` = `20778a0394dfad0686e2854a4dd043f3b1189172`. Re-fetch main and all PR heads before every integration action.

## 1. Purpose and ownership

E0 establishes the shared security boundary needed by CUBI Enterprise and by any authorized Enterprise-to-Engineering interaction:

- authenticated identity and tenant context;
- organization/team membership and role grants;
- global and project security profiles;
- project/OBS/WBS responsibility scope;
- server-side authorization, immediate revocation and append-only audit.

This is a coordinated integration of existing work, not permission to create a second identity, authorization, project-access or audit service.

**Ownership boundary**
- Enterprise owns organization membership, invitations, organizational roles and the grants it administers.
- Engineering remains authoritative for projects, EPS/WBS, activities, resources, costs, progress, schedule and all engineering calculations.
- A team or Enterprise role never implies project, OBS, WBS, resource, document, report or claim-party access.
- A reference to an Engineering record never grants access to that record.
- Every read/write/search/export/download/background operation must re-check the authenticated actor's current tenant and relevant scope; revocation must take effect immediately.
- Personal Pro entitlement and personal storage are separate from company installation/seat entitlement and never bypass organization membership or project grants.

## 2. Current E0 work packages

| Work package | PR | Current branch head (snapshot) | Scope / ownership | Integration state |
|---|---:|---|---|---|
| Global + Project Security Profiles and privilege enforcement | #1974 | `06cdc36ab70420e8242f2e0aedb08ff89d811e62` | Profile catalog, privilege definitions, authenticated administration UI/API, built-in profiles, privilege dependencies and selected Engineering API enforcement | Open, draft; GitHub Actions workflow-run query returned no runs for this exact SHA; compare against current main: 325 ahead / 37 behind; GitHub reports mergeable=false |
| Project / OBS / WBS responsible access | #1983 | `12cf348d2c6d88d2f6177ad28c446d2f3530d497` | Project Security Profile assignments, OBS grants, Responsible OBS on WBS and linked Engineering records, project access UI/API | Open; exact-head Python 3.11/3.12/3.13, PostgreSQL, Web CI and four client typechecks observed successful; compare against current main: 269 ahead / 8 behind |
| CUBI-ID and team invitations | #1971 | `df3439a366d1bba641b7fa79891ad3dc5b4ee22d` | Immutable public CUBI ID, exact-ID lookup, invitation lifecycle and membership creation on acceptance | Open; exact-head ConstructionPM CI, PostgreSQL Integration, Web CI and Client Typecheck observed successful; compare against current main: 56 ahead / 38 behind |
| Trusted claim-party membership | #2006 | `877168d7fdd5d96d9256da1c441d29090a55f2e7` | Contract/claim/party/user-scoped membership for ENT-13 | Downstream E3; keep behind E0. Exact-head ConstructionPM CI, PostgreSQL Integration and Client Typecheck observed successful; compare against current main: 9 ahead / 6 behind |

These are point-in-time observations, not current guarantees. Refresh the SHA, compare result, workflow runs, check-runs, Vercel status and PR conversation immediately before any merge or acceptance decision.

## 3. Verified changed-path collisions

A changed-file comparison of the current PR snapshots found these exact intersections.

### #1971 ∩ #1974 — 12 shared paths

- `.github/workflows/postgres-integration.yml`
- `apps/web/src/enterprise-organization-access.ts`
- `apps/web/src/enterprise-task-center.ts`
- `apps/web/src/main.ts`
- `src/construction_pm/deployment/production_runtime.py`
- `src/construction_pm/deployment/schema.py`
- `src/construction_pm/enterprise_organization_access.py`
- `src/construction_pm/enterprise_organization_access_http.py`
- `src/construction_pm/enterprise_organization_access_repository.py`
- `tests/integration/test_enterprise_organization_access_postgres_live.py`
- `tests/test_enterprise_organization_access.py`
- `tests/test_enterprise_organization_access_http.py`

### #1971 ∩ #1983 — 7 shared paths

- `.github/workflows/postgres-integration.yml`
- `apps/web/public/styles.css`
- `apps/web/src/enterprise-task-center.ts`
- `apps/web/src/main.ts`
- `apps/web/styles.css`
- `src/construction_pm/deployment/production_runtime.py`
- `src/construction_pm/deployment/schema.py`

### #1974 ∩ #1983 — 25 shared paths

- `.github/workflows/postgres-integration.yml`
- `apps/web/src/enterprise-task-center.ts`
- `apps/web/src/main.ts`
- `src/construction_pm/application/authorization.py`
- `src/construction_pm/deployment/production_runtime.py`
- `src/construction_pm/deployment/schema.py`
- `src/construction_pm/http/production_composition.py`
- `src/construction_pm/http/project_lifecycle_routes.py`
- `src/construction_pm/p6_activity_master_api.py`
- `src/construction_pm/p6_baseline_api.py`
- `src/construction_pm/p6_baseline_assignment_api.py`
- `src/construction_pm/p6_baseline_update_api.py`
- `src/construction_pm/p6_expense_api.py`
- `src/construction_pm/p6_issue_api.py`
- `src/construction_pm/p6_relationship_api.py`
- `src/construction_pm/p6_wbs_master_api.py`
- `src/construction_pm/risk_application.py`
- `src/construction_pm/threshold_application.py`
- `tests/integration/test_production_login_postgres_live.py`
- `tests/test_administration_api.py`
- `tests/test_p6_activity_master_http_routes.py`
- `tests/test_p6_expense_api.py`
- `tests/test_p6_issue_api.py`
- `tests/test_risk_application.py`
- `tests/test_threshold_application.py`

### #2006 dependency

#2006 shares `src/construction_pm/deployment/schema.py` with each of #1971, #1974 and #1983. It is a downstream E3 work package, not a fourth independent E0 merge.

**Consequence:** none of these PRs may be independently merged or have shared paths independently rewritten without an explicit integrated path-owner reconciliation and exact-head verification.

## 4. Required integration sequence

1. **Freeze the integration contract.** Record the current `main` SHA and all four PR heads; inspect the full changed-file lists, merge bases, reviews and branch protections. Do not assume a previous “ahead/behind” or green status remains valid.
2. **Reconcile #1974 first as the security-profile foundation.** Resolve its current divergence from main and obtain fresh exact-head Python matrix, PostgreSQL, Web, client and security tests. It owns the canonical privilege catalogue and profile semantics.
3. **Integrate #1983 on top of the accepted #1974 result.** Reconcile every overlapping authorization, production composition, project lifecycle, Engineering API and UI path. Prove OBS/WBS responsibility enforcement on the actual current APIs, including source and destination checks for moves/relationships and immediate revocation.
4. **Integrate #1971 against the same reconciled identity/team/access baseline.** Preserve immutable CUBI-ID privacy, target-account-bound invitations, one-time acceptance, atomic membership creation and append-only audit. Team membership remains distinct from project/OBS/WBS grants.
5. **Only after the integrated E0 foundation is stable, rebase #2006 and continue E3.** Claim-party membership remains separate from team membership and project access; it must consume authenticated identity and must not expose claim evidence or create an alternative Claims Register.
6. After each integrated slice, rerun all required tests on the exact resulting SHA. Never cite CI from a pre-rebase SHA as evidence for the new head.

If branch protection, preview quota or an external credential blocks a required gate, record the exact blocker and continue independent non-protected checks. Do not bypass required checks or merge with stale evidence.

## 5. Mandatory security acceptance matrix

| Boundary | Required invariant | Required negative / lifecycle evidence |
|---|---|---|
| Authentication | Actor and tenant derive only from the validated server session | No caller-supplied actor/tenant; unauthenticated requests denied |
| Tenant isolation | Every identity, team, profile, assignment and project reference is tenant-scoped | Guessed IDs and cross-tenant foreign keys cannot read or mutate records |
| Organization membership | Membership is an explicit persisted relationship | Revocation immediately removes effective membership; no email/display-name inference |
| Team invitation | Invitation is bound to exact target account, tenant, team, role, expiry and one-time token hash | Wrong account, expired/revoked/replayed token and cross-tenant acceptance fail closed |
| Global/project profiles | Global and project privilege catalogs remain distinct and version-traceable | Built-ins protected; privilege dependencies enforced; no invented selectable V26 checkbox rows |
| OBS / WBS scope | Project grants and Responsible OBS/WBS grants are evaluated at the record's actual scope | Project-only access cannot leak into another OBS/WBS; source and destination both authorized for moves |
| Engineering APIs | Enterprise grants do not replace Engineering authorization; current grants are checked at every operation | Read/list/history/write/delete/copy/relationship/assignment paths deny out-of-scope access |
| Revocation | Revocation is effective on the next request, not after cache expiry or background sync | Re-run the same read/write immediately after revoke and assert denial |
| Audit | Security-relevant grant, revoke, invitation, profile and administrative changes are attributable and append-only | Actor, tenant, scope, action, before/after revision, reason and timestamp; mutation + audit atomicity |
| Data export | Export/download/search/background work uses the same scope as direct reads | No export, report, attachment or job path bypasses a revoked or missing grant |
| Personal vs company entitlement | Personal Pro, company seat and On-Prem installation license are separate | Company seat expiry does not silently revoke independently paid personal Pro; personal Pro never licenses the company installation or grants organization access |
| Preview/runtime | Preview behavior is not misrepresented as production runtime behavior | Browser/API checks use a composition that actually mounts the production middleware; fixture-only 404s are not accepted as production API proof |

## 6. Oracle P6 EPPM V26 HTML Help traceability

The EPPM V26 HTML Help is the primary functional source for the Organization & Access / user-security surface. Record the exact observed topic behavior, screen elements, prerequisites, privilege names, navigation and error behavior in each PR's crosswalk and tests.

- [EPPM V26 HTML Help TOC](https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm)
- [Users Page](https://docs.oracle.com/cd/G48897_01/p6help/en/6187.htm)
- [Assigning OBS Elements to Users](https://docs.oracle.com/cd/G48897_01/English/Admin/p6_eppm_application_admin/35460_1.htm)
- [About Security Profiles](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/aboutsecurityprofiles-6595a.html)
- [Working with Security Profiles](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/workingwithsecurityprofiles-36451a.html)
- [Project Security Profile Privilege Detail Window](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-help/102786.html)
- [Project Privilege Definitions](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/p6-ws-ref/projectprivilegedefinitions-47746a.html)

P6 Team Member V26 Help is a separate required source for contributor workflows; mark it Not Applicable only where the exact TOC/topic search demonstrates no relevant Organization & Access administration behavior. Primavera Cloud and P6 Professional Help are not substitutes for EPPM V26 parity.

## 7. Release / completion gate

E0 is not complete until all of the following are true on the final integrated main SHA:

- #1974, #1983 and #1971 changes are reconciled into one coherent identity/security/project-access boundary.
- #2006 is rebased and integrated only after its E0 dependency is satisfied.
- Exact-head Python 3.11/3.12/3.13, PostgreSQL live integration, Web CI/build, all client typechecks and relevant security suites pass.
- Browser acceptance proves actual authenticated UI/API flows against a runtime composition that mounts the relevant middleware; a ready static page or fixture-only preview is insufficient.
- Cross-tenant, cross-project, OBS/WBS, privilege dependency, revocation, invitation replay, audit atomicity and export/download negative tests pass.
- V26 Help traceability is complete for the delivered scope; every remaining gap is explicit.
- Engineering schedule/CPM/activity/WBS/resource/cost/progress/EVM behavior is unchanged except for the intended server-side enforcement of the same grants.
- No duplicate identity, team, permission, project-access or audit subsystem is introduced.

**Current disposition:** E0 is in progress. This document records path collisions, dependencies and acceptance controls; it does not approve any PR for merge, claim full P6 V26 parity, or certify production readiness.
