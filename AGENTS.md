# Repository-wide agent instructions — CUBI

MANDATORY: Before any task, every human or automated agent MUST read:

1. `docs/standards/CUBI_PAGE_BY_PAGE_DESIGN_AND_ACCEPTANCE.md`
2. `docs/traceability/ENTERPRISE_PAGE_BY_PAGE_ICON_HELP_CROSSWALK.md` for every Enterprise task (including shared shell, navigation, dashboard, permissions and cross-environment flows).
3. Every applicable nested `AGENTS.md`
4. The exact page's inheritance, capability, icon and official Help records referenced by the standard/crosswalk.

The standard and Enterprise crosswalk are binding for planning, implementation, review, testing and acceptance. No Enterprise task may begin implementation until its exact PageId/route, inheritance chain, environment-specific official Help topic(s), complete feature/control/icon inventory, visual measurement plan and acceptance tests have been identified. If the old Enterprise traceability file conflicts with the current `apps/web/src/enterprise/router.ts`, the mismatch must be reported and reconciled; do not assume old routes are canonical.

There is exactly ONE official Preview URL. Use only the canonical URL recorded in the standard. Never create or promote a per-task/per-PR URL, random deployment URL, parallel Vercel project or alternate Preview as the official environment. If the canonical URL is unhealthy, stop and report; do not substitute another address.

Use P6 Professional v26 Help for CUBI Engineering and P6 EPPM v26 Help for CUBI Enterprise. Never mix the references. Preserve CUBI branding; do not expose Oracle/Primavera/P6 branding in product UI.

No page is complete without functional tests, visual comparison evidence for all controls and layout details, every registered icon verified, permission/data verification, and explicit acceptance against its page record. A build passing or an agent saying "done" is insufficient.

Preserve existing user identities, credentials, entitlements, database records, project data, routes and working environments unless the task explicitly authorizes a scoped change. Never introduce role/persona selection at login. Do not create duplicate shells or parallel implementations.

If these rules conflict with a task shortcut, the rules win. If a prerequisite or source is missing, stop and report the exact blocker instead of guessing.
