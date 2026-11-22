# AI Workbench — Test Traceability

This matrix separates what is tested now from what cannot be tested until a
canonical service exists. A placeholder or a skipped test is not a pass.

## Implemented and executed

| Test | Covers | File | Result |
|---|---|---|---|
| Envelope identity/validation | tenant/actor/correlation/roles/environment/revision | `tests/test_ai_workbench_orchestration.py` | PASS |
| Session envelope builder | roles from session, invalid roles rejected | same | PASS |
| Bilingual intent routing (14 cases) | import, scenario, risk, analysis, decision, export, explain in fa/en | same | PASS |
| Unknown command | returns clarification, no studio | same | PASS |
| Import plan | PARTIAL, opens, cannot execute, asks for source file | same | PASS |
| Scenario plan | BLOCKED without scenario service, explains why | same | PASS |
| Capability override | wiring scenario service changes status without code change | same | PASS |
| Read-only role | viewer opens risk studio but cannot execute | same | PASS |
| Missing project | asks, does not invent scope | same | PASS |
| Objective/constraints | captured as assumptions, never as results | same | PASS |
| Enterprise scope isolation | Enterprise command cannot borrow Engineering project | same | PASS |
| Response serialization | calculated/recommendations empty, facts only from envelope | same | PASS |
| Studio registry | five studios, verified Help topic and URL declared | same | PASS |
| Assistant fallback classification | only provider-unavailable codes fall back; stale/denied do not | `apps/web/src/workbench-model.test.ts` | PASS |
| Transcript rendering | canonical messages, escaped, link to Decision & Approval, no approval control | `apps/web/src/workbench-render.test.ts` | PASS |
| Browser: assistant first | canonical turn attempted; unconfigured 503 disclosed and routed to the planner | `apps/web/e2e/preview-e2e.mjs` | PASS |
| Browser: Enterprise sign-in | preview sign-in posts to the declared `/preview/login`, never to an unimplemented credential route | same | PASS |
| Browser: Enterprise environment | own document, full sidebar, no `/enterprise` links, workbench return link | same | PASS |
| Browser: Enterprise write and audit | directory record created, read back from the store and found in the audit trail | same | PASS |
| Browser: Enterprise gate | a non-Enterprise session is returned to the Personal Workbench with the restricted note | same | PASS |
| Blank optional email | a record form submitting `email: ""` is accepted; a malformed address is still rejected | `tests/test_enterprise_workbench_http.py` | PASS |
| Knowledge status tones | publication/translation badges map server state; only `published` uses the success tone | `apps/web/src/enterprise-knowledge.test.ts` | PASS |
| Browser: knowledge honesty | a card in the success tone carries `publication_status: published` | `apps/web/e2e/preview-e2e.mjs` | PASS |
| Browser: ten locales (Workbench) | `en`,`fa`,`de`,`zh`,`ar`,`fr`,`ja`,`ko`,`ru`,`tr` keep five studios; `fa`/`ar` flip to RTL; Persian does not mirror English | `apps/web/e2e/preview-e2e.mjs` | PASS |
| Browser: ten locales (Enterprise) | every locale keeps the Enterprise document, sets `html lang` (incl. `tr-TR`) and translates the sidebar | `apps/web/e2e/preview-e2e.mjs` | PASS |
| Locale collation | `sortRecords` follows German collation instead of code-point order | `apps/web/src/enterprise-records.test.ts` | PASS |

Command: `python -m pytest tests/test_ai_workbench_orchestration.py -q`

## Blocked (no canonical service)

| Area | Required test | Blocker |
|---|---|---|
| Import staging | valid/invalid project import, duplicate IDs, missing WBS, dangling/cyclic logic, calendar mismatch, resource mapping, baseline, unsupported fields, data-loss warning, mapping correction, cancel, confirmation, stale revision, failed transaction, retry, post-import verification | project import engine (#1799) |
| Scenario | load real project/baseline, create/duplicate/modify duration/logic/resources, preserve calendar, recalculate, compare, switch, validate, approve, execute, conflict, rollback | scenario service (#1989) |
| Risk quantitative | EMV/PERT/Monte Carlo/sensitivity with deterministic seed | risk analysis service |
| Decision execution | approve exact/partial, stale revision, unauthorized, duplicate, failed execution, audit | proposal/execution service |
| UI | RTL/LTR, desktop/tablet/mobile, keyboard, screen reader, filters, columns, context menu, Gantt sync, inspector resize, hidden details, loading/empty/error/forbidden/stale | Workbench shell (PLANNED) |
| Browser E2E | full command→studio→decision journey | shell + studios |

## Required evidence when unblocked

- Exact tested commit SHA, CI URLs and preview URL.
- Screenshots for every studio in fa RTL and en LTR at 1440×1000, 1366×768 and
  1280×720.
- Import round-trip and negative fixtures with deterministic project files.
- Deterministic schedule fixture and run reproducibility record for scenarios.
- Permission matrix results for admin/planner/viewer.
