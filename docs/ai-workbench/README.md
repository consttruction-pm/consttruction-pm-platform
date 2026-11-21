# CUBI AI Workbench

The AI Workbench is an authenticated engineering surface inside the CUBI
Engineering environment. It turns a typed engineering command into a
deterministic plan, opens exactly one canonical studio, and never invents
project data.

It is **not** a third-party AI product. There is no external model provider,
embedding service or inference runtime. The command layer is typed schemas,
dictionaries, deterministic intent matching and structured questions; see
`docs/architecture/CUBI_INTERNAL_COMMAND_ASSISTANT_PRINCIPLE.md`.

## Entry points

| Entry | Path | Behaviour |
|---|---|---|
| Engineering menu | Enterprise → AI Workbench | Opens the Workbench with the active project and language |
| Direct document | `/ai-workbench?project=<id>&lang=<code>` | Session-gated; unknown query parameters are dropped after sign-in |
| Command API | `POST /api/projects/<id>/workbench/command` | Deterministic plan, no side effects |
| Context API | `GET /api/projects/<id>/workbench/context` | Project scope, data date, permissions and studio statuses |

## Studios and current status

| Studio | Status | Backing service |
|---|---|---|
| Risk Analysis Studio | `WIRED_WRITE` | `risk_api.py` / `/api/projects/{id}/risks` |
| Project Analysis Studio | `WIRED_READ` | workspace read v2 + control-intelligence metrics |
| Project Import Review & Staging | `PARTIAL` | register exchange only; no project import engine |
| Schedule Scenario Studio | `BLOCKED` | no revision-bound scenario service |
| Decision & Approval Workspace | `PARTIAL` | approvals exist; no proposal/execution contract |

Status vocabulary is fixed: `LIVE_VERIFIED`, `WIRED_WRITE`, `WIRED_READ`,
`PARTIAL`, `SHELL_ONLY`, `PLANNED`, `BLOCKED`, `HELP_REFERENCE_PENDING`.
A studio whose server status is `BLOCKED` renders no working controls.

## Documents

- `ARCHITECTURE.md` — shell composition and ownership boundaries
- `COMMAND_CONTRACT.md` — envelope, intents, questions and plan shape
- `STUDIO_CAPABILITY_MATRIX.md` — per-studio capabilities and evidence
- `HELP_CROSSWALK.md` — Help topics and deep-link status
- `API_AND_PERSISTENCE.md` — endpoints, headers, persistence and read-back
- `SECURITY_AND_AUTHORIZATION.md` — session, tenant, project, CSRF, audit
- `TEST_AND_ACCEPTANCE.md` — unit, HTTP, browser and preview acceptance
- `IMPLEMENTATION_STATUS.md` — current delivery status and remaining gates

## Non-negotiable rules

1. One authoritative domain service per capability; no parallel CPM, cost,
   EVM, leveling, import, risk, workflow or portfolio engine.
2. No fake data. Empty, unconnected and insufficient states are explicit:
   `SOURCE_NOT_CONNECTED`, `INSUFFICIENT_DATA`, `CALCULATION_BLOCKED`.
3. Authorization is server-side. The UI never decides permission.
4. Every write is idempotent, revision-checked, audited and read back.
5. Every user-visible string passes through the shared localization system;
   an English fallback is announced, never silent.
