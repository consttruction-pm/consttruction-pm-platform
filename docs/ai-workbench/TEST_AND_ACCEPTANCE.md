# Test and Acceptance

## 1. Commands

| Layer | Command |
|---|---|
| Workbench Python | `PYTHONPATH=src python -m pytest tests/test_ai_workbench_http.py tests/test_ai_workbench_orchestration.py -q` |
| Routing Python | `PYTHONPATH=src python -m pytest tests/test_production_web_app.py tests/test_preview_runtime.py -q` |
| Web unit | `cd apps/web && npm test` |
| Web typecheck | `cd apps/web && npm run typecheck` |
| Web build | `cd apps/web && npm run build` |
| Browser E2E | `cd apps/web && CUBI_CHROME_NO_SANDBOX=1 npm run test:e2e:preview` |

## 2. Python coverage

`tests/test_ai_workbench_http.py` (20 tests) covers:

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
- wrong method → 405 and unknown action → 404.

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

## 3. Web unit coverage

`apps/web/src/workbench-model.test.ts` (10 tests):

- studio labels and stable studio order;
- English fallback and Persian values through the shared localization system;
- HTML escaping for dynamic values;
- status tone vocabulary only;
- plan opens a studio only when the server allows it;
- one clarifying question is surfaced;
- 5×5 matrix groups stored ratings without recalculating;
- analysis counts read server rows; critical count from stored flags;
- stored metrics keep their values and stable order; source refs are unique;
- query/project helpers preserve only the intended parameters.

`apps/web/src/workbench-render.test.ts` (6 tests):

- the edit form pre-fills stored values and the rendered revision;
- stored values are escaped in the edit form;
- the history panel renders server events and an honest empty state;
- the inspector offers edit and history; a read-only session gets no edit;
- the inspector swaps to the edit form while editing.

## 4. Browser acceptance (real preview)

The journey added to `apps/web/e2e/preview-e2e.mjs` runs headless Chrome against
the real WSGI runtime, real SQLite stores and the real API composition:

1. unauthenticated `/ai-workbench` redirects to `/login` and keeps the project
   and language;
2. planner sign-in returns to the Workbench;
3. the header carries the pinned project, five studios and the server statuses;
4. the fresh revision shows the empty risk state, not fixtures;
5. a risk is created; the table, the matrix cell and the inspector agree;
6. the risk is edited with its rendered revision; the status and revision 2 are
   read back and the audit history lists the events;
7. a full document reload reads the updated record back;
8. a typed command returns a plan with four separated blocks and names the
   canonical studio;
9. the scenario studio renders `BLOCKED` with zero controls;
10. the analysis studio shows four stored counts and declares EVM/resources
    `PLANNED`;
11. switching to Persian flips direction while keeping five studios, then back
    to English.

Screenshots: `ai-workbench-en.png`, `ai-workbench-fa.png` under
`apps/web/e2e/artifacts/`.

## 5. Acceptance gates

| Gate | Requirement |
|---|---|
| Authorization | every workbench API call authorizes project + tenant on the server |
| No fake data | empty/failed reads show explicit states; no sample records |
| Determinism | the same command with the same envelope yields the same intent/studio |
| Writes | idempotent, revision-checked, audited, read back |
| Blocked studios | zero working controls |
| Localization | document `lang`/`dir` from the shared system; fallback announced |
| Responsive | three columns at desktop; stacked at ≤ 980 px |
| Cache | document is `no-store` |

## 6. What is not yet proven

- Cross-phase acceptance (Phases 4–7) for import, scenario and approval.
- Per-studio Help deep links (see `HELP_CROSSWALK.md`).
- Production PostgreSQL composition is wired but only preview SQLite is
  exercised by the browser journey; the deployment path is covered by the
  existing composition tests.
