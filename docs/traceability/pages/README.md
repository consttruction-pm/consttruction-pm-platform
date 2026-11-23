# CUBI page-by-page traceability index

This index tracks individual page specifications required by `docs/standards/CUBI_PAGE_BY_PAGE_DESIGN_AND_ACCEPTANCE.md`.

**Important:** Entries below are inventory references from the existing route/capability matrix. They are NOT a claim that the pages have already passed the new detailed functional and visual acceptance gate.

## Implemented page records

| Page | Record | Status |
|---|---|---|
| ENT-07 — Projects register and project portal | [ENT-07-projects-register.md](ENT-07-projects-register.md) | Implemented; local full-stack verification passed; official Preview blocked; visual parity not claimed |

## Enterprise page-by-page Help and icon specification

The current Enterprise application has a separately verified 26-PageId router inventory. Its canonical routes, inheritance chain, page-specific EPPM V26 Help links, semantic icon-by-icon register, current source gaps and visual acceptance requirements are recorded in [ENTERPRISE_PAGE_BY_PAGE_ICON_HELP_CROSSWALK.md](../ENTERPRISE_PAGE_BY_PAGE_ICON_HELP_CROSSWALK.md). The older 16-row Enterprise traceability registry has route mismatches and is not a substitute for the current router. All Enterprise agents must read the crosswalk before work. **This is a specification and source audit; it does not claim that the current UI has already implemented or passed the icon/visual checks.**

## Existing public route inventory

| Route | Existing matrix entry | Detailed page specification | Visual acceptance |
|---|---|---|---|
| `/` | ENG-PUB-HOME | Required | Not yet evidenced |
| `/platform/` | ENG-PUB-PLATFORM | Required | Not yet evidenced |
| `/features/` | ENG-PUB-FEATURES | Required | Not yet evidenced |
| `/features/scheduling/` | ENG-PUB-FEATURES-SCHEDULING | Required | Not yet evidenced |
| `/features/project-controls/` | ENG-PUB-FEATURES-PROJECT-CONTROLS | Required | Not yet evidenced |
| `/features/resources/` | ENG-PUB-FEATURES-RESOURCES | Required | Not yet evidenced |
| `/features/cost/` | ENG-PUB-FEATURES-COST | Required | Not yet evidenced |
| `/features/documents/` | ENG-PUB-FEATURES-DOCUMENTS | Required | Not yet evidenced |
| `/features/risks/` | ENG-PUB-FEATURES-RISKS | Required | Not yet evidenced |
| `/features/reporting/` | ENG-PUB-FEATURES-REPORTING | Required | Not yet evidenced |
| `/features/ai-assistant/` | ENG-PUB-FEATURES-AI-ASSISTANT | Required | Not yet evidenced |
| `/solutions/` | ENG-PUB-SOLUTIONS | Required | Not yet evidenced |
| `/integrations/` | ENG-PUB-INTEGRATIONS | Required | Not yet evidenced |
| `/pricing/` | ENG-PUB-PRICING | Required | Not yet evidenced |
| `/resources/` | ENG-PUB-RESOURCES | Required | Not yet evidenced |
| `/documentation/` | ENG-PUB-DOCUMENTATION | Required | Not yet evidenced |
| `/help/` | ENG-PUB-HELP | Required | Not yet evidenced |
| `/faq/` | ENG-PUB-FAQ | Required | Not yet evidenced |
| `/about/` | ENG-PUB-ABOUT | Required | Not yet evidenced |
| `/security/` | ENG-PUB-SECURITY | Required | Not yet evidenced |
| `/payments/` | ENG-PUB-PAYMENTS | Required | Not yet evidenced |
| `/contact/` | ENG-PUB-CONTACT | Required | Not yet evidenced |
| `/get-started/` | ENG-PUB-GET-STARTED | Required | Not yet evidenced |
| `/privacy/` | ENG-PUB-PRIVACY | Required | Not yet evidenced |
| `/terms/` | ENG-PUB-TERMS | Required | Not yet evidenced |
| `/login/` | Boundary / internal docs | Required | Not yet evidenced |
| `/app/` | ENG-WS-SHELL | Required | Not yet evidenced |

## Authenticated and operational route inventory — audit required

The public matrix is not a complete application inventory. The next route-discovery pass MUST inspect the current router, server route registry, deployment rewrites, navigation configuration and permission gates to enumerate every live operational route, including at minimum:

- Personal Workbench and every dashboard/landing surface.
- CUBI Engineering and all of its modules, windows, tabs and dialogs.
- CUBI Enterprise and all of its modules, pages and dashboards.
- Global Administration and Organization Administration.
- User, organization, entitlement, permission and session management.
- Project setup, project overview, WBS, Activities, Gantt, schedule/scenario, resources, risks, reports and forms.
- CUBI AI Workbench and assistant contextual surfaces.
- Settings, profile, notifications, help and documentation.
- Sign-in, sign-out, session recovery, redirects and compatibility routes.
- Any route hidden behind feature flags, organization membership or access checks.

For every discovered route, create a separate page record using the required schema in the standard. Include nested routes and meaningful modal/dialog workflows where they have independent behavior. Do not assume that a navigation item is the only page or that a public marketing route represents the operational page.

## Completion policy

- Work page by page, not by applying a generic skin to the whole site.
- A page record may move to `SPECIFIED`, `IMPLEMENTED`, `VISUALLY_VERIFIED`, and finally `ACCEPTED` only with the evidence required by the standard.
- Keep blocked items explicit. Do not mark an item accepted because a shared shell looks polished.
- Update this index as each route is audited and accepted, and link each row to its detailed record.
