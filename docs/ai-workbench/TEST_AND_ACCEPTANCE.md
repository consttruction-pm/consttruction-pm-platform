# Test and Acceptance

## 1. Commands

| Layer | Command |
|---|---|
| Workbench Python | `PYTHONPATH=src python -m pytest tests/test_ai_workbench_http.py tests/test_ai_workbench_orchestration.py -q` |
| Deployment routing | `PYTHONPATH=src python -m pytest tests/test_workspace_shell_routing.py -q` |
| Routing Python | `PYTHONPATH=src python -m pytest tests/test_production_web_app.py tests/test_preview_runtime.py -q` |
| Web unit | `cd apps/web && npm test` |
| Web typecheck | `cd apps/web && npm run typecheck` |
| Web build | `cd apps/web && npm run build` |
| Browser E2E | `cd apps/web && CUBI_CHROME_NO_SANDBOX=1 npm run test:e2e:preview` |

## 2. Python coverage

`tests/test_ai_workbench_http.py` (29 tests) covers:

- delegation of non-owned paths;
- missing and unknown session → 401;
- forbidden or foreign project → 403;
- full context payload, including project scope, permissions and studio
  statuses;
- data date resolved from the settings provider, and `null` when unavailable;
- viewer cannot propose; planner can;
- risk command resolves to `WIRED_WRITE` and can execute;
- scenario command resolves to `BLOCKED` and cannot open;
- Persian import command resolves to the partial import studio;
- unknown command returns one clarifying question;
- empty command, invalid locale, invalid correlation, oversized body;
- wrong method → 405 and unknown action → 404;
- **Phase 7 gates**: a project owned by another tenant is not disclosed to the
  requesting session; the same project id in two tenants resolves to each
  tenant's own record; the data-date provider receives the session tenant;
  scope fields in the command body cannot override the URL project or server
  revision; encoded separators, `.`/`..` segments and control characters in the
  project id are rejected with `PROJECT_ID_INVALID` before any lookup;
- the decision studio reports `WIRED_WRITE` only when the canonical proposal
  runtime is mounted and stays `PARTIAL` with a reason otherwise.

`tests/test_ai_workbench_orchestration.py` (27 tests) covers the envelope,
intent rules, objective/constraint extraction, studio registry and the pure
planner.

`tests/test_production_web_app.py` adds:

- `_safe_next` preserves `/ai-workbench` with `project`/`lang` only, and drops
  unknown or unsafe query values;
- the document redirects without a session and preserves the deep link;
- with a session it serves `ai-workbench.html`, not the Engineering shell;
- `ai-workbench.css` is served from the web root.

`tests/test_preview_runtime.py` adds:

- the preview document gate and preserved `next` target;
- the Workbench document is not the `#app` workspace document;
- the stylesheet is served;
- an undocumented `redirect` parameter is dropped.

`tests/test_workspace_shell_routing.py` covers the deployment entrypoint that
Vercel maps every workspace document onto:

- `/app` and the retired `/enterprise` resolve without a rewrite query;
- `__path=enterprise`, `__path=cubi`, nested `/cubi/*` and `/ai-workbench`
  preserve the requested document;
- unknown, blank and traversal paths fall back to `/app` and never become a
  filesystem path;
- both API shell entrypoints use the shared resolver instead of forcing
  `PATH_INFO` to `/app`;
- the `__path` marker is stripped from the user query before the HTTP boundary
  builds a post-login `next` target;
- both `vercel.json` files route `/cubi` and `/ai-workbench` to the shell, and
  every deployment build stages `enterprise.html`, `ai-workbench.html` and
  `ai-workbench.css`.

## 3. Web unit coverage

`apps/web/src/workbench-model.test.ts` (16 tests):

- studio labels and stable studio order;
- English fallback and Persian values through the shared localization system;
- HTML escaping for dynamic values;
- status tone vocabulary only;
- plan opens a studio only when the server allows it;
- one clarifying question is surfaced;
- 5×5 matrix groups stored ratings without recalculating;
- analysis counts read server rows; critical count from stored flags;
- the canonical `workspace.wbs_nodes` collection drives the WBS count, with the
  legacy `workspace.wbs` field only as a fallback;
- stored metrics keep their values and stable order; source refs are unique;
- query/project helpers preserve only the intended parameters;
- only an `https://docs.oracle.com/` reference becomes a Help link; other
  origins, `http:` and `javascript:` are refused;
- proposal impact compares the literal `activity.create` payload with the
  current read (not present → no warnings);
- proposal impact names an existing activity id and an unknown WBS by code
  without calculating a schedule;
- proposal impact states `CURRENT_STATE_UNAVAILABLE` when no read is held and
  ignores tools other than `activity.create`;
- only a missing or failed AI provider is classified as a fallback condition; a
  stale revision or an authorization refusal is not.

`apps/web/src/workbench-render.test.ts` (23 tests):

- the edit form pre-fills stored values and the rendered revision;
- stored values are escaped in the edit form;
- the history panel renders server events and an honest empty state;
- the inspector offers edit and history; a read-only session gets no edit;
- the inspector swaps to the edit form while editing;
- without a baseline the EVM section states `INSUFFICIENT_DATA` with no control;
- a stored baseline exposes baseline, currency and data-date inputs;
- earned-value values are shown exactly as the server returned them;
- an authoritative EVM error is surfaced verbatim with no fabricated metrics;
- a read-only session sees no proposal list; an empty store is stated without a
  fabricated row;
- a pending proposal offers approve/reject and never execution, with the payload
  escaped; an approved proposal offers execution only;
- the analysis panel renders the canonical WBS element count, not the legacy
  field;
- a pending `activity.create` proposal renders the literal impact table with the
  current state, the proposed change and the "no schedule/cost/EVM calculation"
  note;
- an existing activity id and an unknown WBS render `data-impact-warning` codes
  rather than a fabricated comparison;
- an unavailable workspace read renders `data-impact-error` and
  `CURRENT_STATE_UNAVAILABLE`;
- a stale proposal shows a warning and no control; an executed proposal shows
  the canonical result and decision maker; a read error shows its stable code;
- the assistant transcript renders canonical messages, escapes them, links to
  Decision & Approval and offers no approve/execute control of its own;
- an empty transcript with nothing pending renders no region.

## 4. Browser acceptance (real preview)

The journey added to `apps/web/e2e/preview-e2e.mjs` runs headless Chrome against
the real WSGI runtime, real SQLite stores and the real API composition:

1. the preview runtime serves the landing page, and the two product
   environments resolve to their own documents: `/enterprise` redirects to
   `/cubi/` (308), `/cubi/` serves the Enterprise document and bundle, and
   `/cubi/enterprise/*` and `/ai-workbench` keep their session gates and deep
   links;
2. unauthenticated `/ai-workbench` redirects to `/login` and keeps the project
   and language;
3. planner sign-in returns to the Workbench;
4. the header carries the pinned project, five studios and the server statuses;
5. the fresh revision shows the empty risk state, not fixtures;
6. a risk is created; the table, the matrix cell and the inspector agree;
7. the risk is edited with its rendered revision; the status and revision 2 are
   read back and the audit history lists the events;
8. a full document reload reads the updated record back;
9. the typed sentence is first sent to the canonical assistant endpoint; with no
   provider configured the response body is `AI_ASSISTANT_NOT_CONFIGURED`, the
   panel states that honestly and routes the same sentence through the
   deterministic planner, which returns four separated blocks and names the
   canonical studio (the transcript keeps the user message and offers no
   approval control);
10. the scenario studio renders `BLOCKED` with zero controls;
11. the analysis studio shows four stored counts (read from the canonical
    `activities`/`wbs_nodes`/`relationships` collections) and states
    `INSUFFICIENT_DATA` for EVM with no control when no baseline exists;
12. a baseline is captured through the canonical service; the EVM form appears;
    submitting it surfaces the server refusal (`EVM_`/`EARNED_VALUE_`) and draws
    no fabricated figure;
13. the decision studio starts empty; a canonical `activity.create` proposal is
    created through the runtime, listed as proposed with approve/reject and no
    execute control; the pending proposal shows the literal impact table with
    its WBS node and no `CURRENT_STATE_UNAVAILABLE`/`ACTIVITY_ID_EXISTS`
    warning; rejecting records the decision; a reload shows the rejected
    proposal with no live control and the activity was never created;
14. switching to Persian flips direction while keeping five studios, then back
    to English.

Screenshots: `ai-workbench-en.png`, `ai-workbench-fa.png` under
`apps/web/e2e/artifacts/`.

## 5. Acceptance gates

| Gate | Requirement |
|---|---|
| Authorization | every workbench API call authorizes project + tenant on the server |
| Tenant isolation | a project id owned by another tenant is never disclosed, and a shared id resolves per-tenant |
| Scope binding | body/query cannot override tenant, project, actor, roles or revision |
| Request path | decoded project ids reject separators, dot segments and control characters |
| No fake data | empty/failed reads show explicit states; no sample records |
| Determinism | the same command with the same envelope yields the same intent/studio |
| Writes | idempotent, revision-checked, audited, read back |
| Approvals | proposal read, decision and execution use the canonical runtime with the pinned revision; a stale proposal has no control |
| Blocked studios | zero working controls |
| Environments | `/app`, `/cubi/*` and `/ai-workbench` are separate documents; Vercel builds stage each document and the shell restores the requested path |
| Localization | document `lang`/`dir` from the shared system; fallback announced |
| Help | a studio links only a recorded official page; no URL is guessed and per-control rows stay pending |
| Responsive | three columns at desktop; stacked at ≤ 980 px |
| Assistant | the panel calls `ai-assistant-turn.v1` first; only a proven provider-unavailable 503 falls back to the deterministic planner, and every other 5xx fails the browser run |
| Cache | document is `no-store` |

## 6. Phase 7 security acceptance (implemented)

The workbench HTTP boundary now has explicit cross-tenant and scope-binding
tests, not only the lifecycle service tests:

| Test | Proves |
|---|---|
| `test_project_owned_by_another_tenant_is_not_disclosed` | tenant B receives `403 PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED` for tenant A's project, with no project payload |
| `test_same_project_id_resolves_to_each_tenants_own_record` | the same id in two tenants returns each tenant's name and revision |
| `test_data_date_provider_receives_the_session_tenant` | derived settings are resolved with the session tenant, not a client value |
| `test_command_body_cannot_override_server_scope` | body `tenant_id`, `project_id`, `revision`, `actor_id`, `roles` are ignored |
| `test_encoded_path_separator_is_rejected` | `%2F` cannot inject a path segment |
| `test_dot_segment_project_id_is_rejected` | `.` and `%2E%2E` are rejected before lookup |
| `test_control_character_project_id_is_rejected` | `%00` is rejected before lookup |

Cross-phase acceptance for import, scenario and approval stays pending because
those contracts do not exist yet (see `IMPLEMENTATION_STATUS.md`).

## 7. What is not yet proven

- Cross-phase acceptance for import and scenario stays pending because those
  contracts do not exist yet. Proposal/approval is exercised end to end where
  the canonical runtime is mounted; scenario-specific approvals await #1989.
- Per-studio Help deep links (see `HELP_CROSSWALK.md`).
- Production PostgreSQL composition is wired but only preview SQLite is
  exercised by the browser journey; the deployment path is covered by the
  existing composition tests.
