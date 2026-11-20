# CUBISITE — capability, page and Help inheritance matrix (C01–C35)

This matrix is generated from the committed sources. It answers one question per identifier:
which public pages may claim the capability, which workspace surface implements it, and which
recorded Help topic — if any — constrains what the claim may say. Nothing here is authored by hand
beyond the C-number assignment; titles, URLs and page numbers come from the Help registry.

## 1. Sources and the workbook gap

| Source | Role |
| --- | --- |
| `docs/cubisite/AUDIT_BASELINE_2026-11-20.md` | The accepted C01–C35 enumeration and status vocabulary. |
| `docs/traceability/engineering-v26.json`, `enterprise-v26.json` | Official Help topics, PDF pages and executable evidence per surface (83 rows). |
| `apps/web/site/routes.mjs` | The 25 approved public routes. |
| `apps/web/site/capabilities.mjs` | The published feature contract (10 entries). |
| `apps/web/src/help-registry.ts` | The resolver that turns a route into one of four Help levels. |

The product owner's workbook, `/CUBISITE/cubisite.xlsx` v8, is the authority for the C-numbering.
It is **not present** in this repository, in its history, or in the issue's attachments, so the
enumeration in the audit baseline is used as-is. That is why C05 has no name: inventing one would
put a fabricated capability into the product contract.

## 2. Inheritance rules

1. **direct** — the route (or the workspace menu on it) has its own traceability row with an official topic.
2. **parent** — a deeper path without its own row inherits the nearest documented ancestor.
3. **inherited** — a path under `/app/` or `/environments/` inherits the environment shell topic.
4. **internal-docs** — no official topic exists; the assistant links to CUBI's own documentation and may say only the recorded reason.

The same four levels are what the assistant renders, so this matrix and the live assistant cannot
disagree: both call `resolveContextualHelp`.

## 3. Capabilities C01–C35

| ID | Capability | Status | Public pages | Workspace surface | Help entry | Feature |
| --- | --- | --- | --- | --- | --- | --- |
| C01 | Workspace / Projects | PARTIAL | `/platform/`, `/get-started/` | `ENG-WS-PROJECTS` | `ENG-WS-PROJECTS` | — |
| C02 | WBS / Activities | PARTIAL | `/features/project-controls/` | `ENG-WS-WBS`, `ENG-WS-ACTIVITY-TABLE` | `ENG-WS-WBS` | `project-controls` |
| C03 | Field Registry | IMPLEMENTED | `/features/project-controls/` | `ENG-WS-ACTIVITY-TABLE`, `ENG-WS-UDF` | `ENG-WS-UDF` | `project-controls` |
| C04 | Grid / Layout | PARTIAL | `/features/project-controls/` | `ENG-WS-LAYOUTS`, `ENG-WS-ACTIVITY-TABLE` | `ENG-WS-LAYOUTS` | `project-controls` |
| C05 | Unresolved — see workbook gap | MISSING_EVIDENCE | — | — | — | — |
| C06 | Calendar | PARTIAL | `/features/scheduling/` | `ENG-WS-CALENDARS` | `ENG-WS-CALENDARS` | `scheduling` |
| C07 | Schedule Options | PARTIAL | `/features/scheduling/` | `ENG-WS-SCHEDULE` | `ENG-WS-SCHEDULE` | `scheduling` |
| C08 | Relationships | PARTIAL | `/features/scheduling/` | `ENG-WS-RELATIONSHIPS`, `ENG-WS-GANTT-RELATIONSHIPS` | `ENG-WS-RELATIONSHIPS` | `scheduling` |
| C09 | CPM Engine | IMPLEMENTED | `/features/scheduling/` | `ENG-WS-SCHEDULE`, `ENG-WS-CRITICAL-PATH` | `ENG-WS-SCHEDULE` | `scheduling` |
| C10 | Progress / Actuals | PARTIAL | `/features/project-controls/` | `ENG-WS-TRACKING` | `ENG-WS-TRACKING` | `project-controls` |
| C11 | Baselines | PARTIAL | `/features/project-controls/` | `ENG-WS-BASELINES` | `ENG-WS-BASELINES` | `project-controls` |
| C12 | Resources / Assignments | PARTIAL | `/features/resources/` | `ENG-WS-RESOURCES`, `ENG-WS-RESOURCE-USAGE` | `ENG-WS-RESOURCES` | `resources` |
| C13 | Cost / Financial Periods | PARTIAL | `/features/cost/`, `/pricing/` | `ENG-WS-EXPENSES` | `ENG-WS-EXPENSES` | `cost` |
| C14 | EVM / Earned Schedule | PARTIAL | `/features/project-controls/` | `ENG-WS-TRACKING`, `ENG-WS-USAGE-PROFILE` | `ENG-WS-TRACKING` | `project-controls` |
| C15 | Codes / Steps / Issues / Risks | PARTIAL | `/features/risks/` | `ENG-WS-RISKS`, `ENG-WS-ISSUES`, `ENG-WS-STEPS`, `ENG-WS-ACTIVITY-CODES` | `ENG-WS-RISKS` | `risks` |
| C16 | Interchange | PARTIAL | `/integrations/` | `ENG-WS-EXCHANGE` | `ENG-WS-EXCHANGE` | — |
| C17 | Dashboard / Analytics | PARTIAL | `/platform/`, `/features/reporting/` | `ENG-WS-PORTFOLIOS`, `ENT-DASHBOARDS` | `ENT-DASHBOARDS` | `portfolio-executive` |
| C18 | Charts | PREVIEW | `/features/reporting/` | `ENG-WS-GANTT`, `ENG-WS-GANTT-BARS` | `ENG-WS-GANTT` | `reporting` |
| C19 | Reporting | PREVIEW | `/features/reporting/` | `ENG-WS-REPORTS`, `ENT-REPORTS` | `ENG-WS-REPORTS` | `reporting` |
| C20 | Forms | PARTIAL | `/features/` | — | — | — |
| C21 | Form Calculations | PARTIAL | `/features/` | — | — | — |
| C22 | Workflow / Approvals | PARTIAL | `/features/` | `ENT-WORKFLOW`, `ENT-FEEDBACK-APPROVAL` | `ENT-WORKFLOW` | `team-tasks` |
| C23 | PMBOK Layer | PARTIAL | `/platform/`, `/features/` | — | — | — |
| C24 | AI Permissions | PARTIAL | `/features/ai-assistant/`, `/security/` | `ENG-WS-ADMIN` | `ENG-WS-ADMIN` | `ai-assistant` |
| C25 | AI Project Bootstrap | PARTIAL | `/features/ai-assistant/` | `ENG-WS-PROJECTS` | `ENG-WS-PROJECTS` | `ai-assistant` |
| C26 | AI Schedule Analysis | PARTIAL | `/features/ai-assistant/` | `ENG-WS-SCHEDULE` | `ENG-WS-SCHEDULE` | `ai-assistant` |
| C27 | AI Document / Form Support | PARTIAL | `/features/ai-assistant/`, `/features/documents/` | `ENG-WS-DOCUMENTS` | `ENG-WS-DOCUMENTS` | `ai-assistant` |
| C28 | AI Reliability | PARTIAL | `/features/ai-assistant/` | — | — | `ai-assistant` |
| C29 | Localization | PARTIAL | every published page | — | — | — |
| C30 | RTL / Calendar / Fonts | PARTIAL | every published page | — | — | — |
| C31 | Language Packs | PARTIAL | every published page | — | — | — |
| C32 | Help / Documentation | PARTIAL | `/documentation/`, `/help/`, `/faq/` | — | — | — |
| C33 | AI / Product Guide | PARTIAL | every published page | — | — | `ai-assistant` |
| C34 | Security / Tenancy | PARTIAL | `/security/`, `/privacy/`, `/terms/` | `ENG-WS-ADMIN`, `ENT-ORG-ACCESS` | `ENG-WS-ADMIN` | — |
| C35 | Release / Quality | PARTIAL | `/platform/` | — | — | — |

`C29`, `C30`, `C31` and `C33` are site-wide by nature: localization, direction and fonts, language
packs and the contextual assistant apply to every published page, so they are listed once rather
than repeated in each page row.

## 4. Page inheritance — the 25 public routes

| Route | Capabilities | Help level | Entry | Official topic |
| --- | --- | --- | --- | --- |
| `/` | C29, C30, C31, C33 | direct | ENG-PUB-HOME | Working with Projects, p. 115 |
| `/platform/` | C01, C17, C23, C29, C30, C31, C33, C35 | internal-docs | ENG-PUB-PLATFORM | — (internal documentation) |
| `/features/` | C20, C21, C22, C23, C29, C30, C31, C33 | direct | ENG-PUB-FEATURES | Define Activity Table columns, p. 329 |
| `/features/scheduling/` | C06, C07, C08, C09, C29, C30, C31, C33 | direct | ENG-PUB-FEATURES-SCHEDULING | Scheduling Projects, p. 287 |
| `/features/project-controls/` | C02, C03, C04, C10, C11, C14, C29, C30, C31, C33 | direct | ENG-PUB-FEATURES-PROJECT-CONTROLS | Tracking, p. 372 |
| `/features/resources/` | C12, C29, C30, C31, C33 | direct | ENG-PUB-FEATURES-RESOURCES | Resources, p. 170 |
| `/features/cost/` | C13, C29, C30, C31, C33 | direct | ENG-PUB-FEATURES-COST | Expenses, p. 250 |
| `/features/documents/` | C27, C29, C30, C31, C33 | direct | ENG-PUB-FEATURES-DOCUMENTS | Work Products and Documents, p. 316 |
| `/features/risks/` | C15, C29, C30, C31, C33 | direct | ENG-PUB-FEATURES-RISKS | Risks (P6 Professional Only), p. 310 |
| `/features/reporting/` | C17, C18, C19, C29, C30, C31, C33 | direct | ENG-PUB-FEATURES-REPORTING | Print budget reports, p. 266 |
| `/features/ai-assistant/` | C24, C25, C26, C27, C28, C29, C30, C31, C33 | internal-docs | ENG-PUB-FEATURES-AI-ASSISTANT | — (internal documentation) |
| `/solutions/` | C29, C30, C31, C33 | internal-docs | ENG-PUB-SOLUTIONS | — (internal documentation) |
| `/integrations/` | C16, C29, C30, C31, C33 | direct | ENG-PUB-INTEGRATIONS | Importing and exporting data - Future period bucket planning FAQ, p. 243 |
| `/pricing/` | C13, C29, C30, C31, C33 | internal-docs | ENG-PUB-PRICING | — (internal documentation) |
| `/resources/` | C29, C30, C31, C33 | internal-docs | ENG-PUB-RESOURCES | — (internal documentation) |
| `/documentation/` | C29, C30, C31, C32, C33 | internal-docs | ENG-PUB-DOCUMENTATION | — (internal documentation) |
| `/help/` | C29, C30, C31, C32, C33 | internal-docs | ENG-PUB-HELP | — (internal documentation) |
| `/faq/` | C29, C30, C31, C32, C33 | internal-docs | ENG-PUB-FAQ | — (internal documentation) |
| `/about/` | C29, C30, C31, C33 | internal-docs | ENG-PUB-ABOUT | — (internal documentation) |
| `/security/` | C24, C29, C30, C31, C33, C34 | direct | ENG-PUB-SECURITY | Setting up user security (P6 Professional Only), p. 479 |
| `/payments/` | C29, C30, C31, C33 | internal-docs | ENG-PUB-PAYMENTS | — (internal documentation) |
| `/contact/` | C29, C30, C31, C33 | internal-docs | ENG-PUB-CONTACT | — (internal documentation) |
| `/get-started/` | C01, C29, C30, C31, C33 | internal-docs | ENG-PUB-GET-STARTED | — (internal documentation) |
| `/privacy/` | C29, C30, C31, C33, C34 | internal-docs | ENG-PUB-PRIVACY | — (internal documentation) |
| `/terms/` | C29, C30, C31, C33, C34 | internal-docs | ENG-PUB-TERMS | — (internal documentation) |

## 5. Boundaries

| Route | Help level | Entry | Official topic |
| --- | --- | --- | --- |
| `/login/` | internal-docs | — | — (internal documentation) |
| `/app/` | direct | ENG-WS-SHELL | Using main windows, p. 33 |

/login/ and /app/ are boundaries, not indexable routes: the first is the
sign-in entry and the second is the canonical workspace.

## 6. C05 investigation

Every repository artefact was searched for `C05`: the audit baseline, the traceability registries,
the capability contract, the crosswalks and the issue text. The only hit outside the audit is
`docs/audits/JALAL4_TO_JALAL5_CROSSWALK_2026-10-18.md`, which maps a `C05` of a **different**
numbering series (the Jalal crosswalk's C01–C09 covers commercial, contract and claims work) to
J4-40. That series is not the CUBISITE C01–C35 series, so it cannot name the missing row.

Conclusion: C05 is an **evidence gap in the source workbook**, not an implementation gap. It is
carried as `MISSING_EVIDENCE` with no public page, no workspace surface and no Help topic, and it
is excluded from every page's capability list.

## 7. PDF ↔ official HTML Help reconciliation

The Engineering baseline pairs each topic with a page of the 815-page V26 Help PDF. Both sides were
checked on 2026-11-20 against the supplied PDF and the live HTML Help:

| Check | Result |
| --- | --- |
| Engineering rows with a PDF page | 53 |
| PDF pages whose header or body carries the recorded topic title | 53 / 53 |
| Rows with an official HTML topic (Engineering + Enterprise) | 69 |
| Topics that answered HTTP 200 with the recorded title in the page | 69 / 69 |

Method: `pdftotext -f <page> -l <page> <pdf> -` per Engineering row, and a bounded `curl` per URL;
titles were compared after lowercasing and stripping punctuation. No row needed a page correction,
so the PDF page and the HTML topic in the registry refer to the same subject for every Engineering
row. Enterprise rows cite the HTML-only Enterprise baseline and carry no PDF page by design.

## 8. Open gaps

| Item | Status | Owner action |
| --- | --- | --- |
| C05 name and definition | Blocked on source | Supply row C05 of the v8 workbook; the matrix will pick it up through `CAPABILITY_INHERITANCE`. |
| C20–C23 public entry | Partial | Forms, calculations, workflow and PMBOK have no dedicated route; they inherit the feature index. |
| C29 workspace localization | Partial | Workspace UI is English/Persian only; the ten locales cover the public site. |
