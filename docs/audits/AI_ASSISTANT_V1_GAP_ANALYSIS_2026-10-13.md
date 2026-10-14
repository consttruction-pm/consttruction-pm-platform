# V1 AI Assistant Omission — Root-Cause and Gap Audit

Audit date: 2026-10-13
Baseline: `main` at `f811f8d351c48b2feae733653262a97ac47f31dd`
Purpose: Explain why the AI assistant, despite repeated product emphasis, had not become an integrated V1 release capability. This audit is evidence-based; it does not infer individual intent.

## Executive finding

The main cause is a **governance-to-implementation gap**, compounded by contradictory prioritization and no single end-to-end acceptance owner/gate. AI was described as a product principle and a P0 capability in some architecture documents, but a separate product-completion policy classified the AI assistant as P3/advanced. The implementation work consequently emphasized data/control-intelligence contracts, Smart Guide projection and proposal/approval primitives without an integrated, production model-to-tool-to-mutation-to-verification workflow.

This is not evidence that the team deliberately ignored the requirement. The repository itself contained competing instructions, and the measurable weighted plan underrepresented the promised capability.

## Evidence

### 1. Contradictory priority was written into authoritative project documents

- `docs/architecture/PRODUCT_PRINCIPLES.md` described AI-native assistance as a required product layer, required AI to be grounded/auditable/action-aware, and defined a release completeness gate.
- `docs/architecture/COMPETITIVE_COMPLETENESS_MATRIX.md` listed “AI Project Controls Copilot + auditable agent framework” as P0 and had a hard stop for AI lacking provenance, action controls or auditability.
- However, `docs/PRODUCT_COMPLETION_CONTROL.md`, Section 4, explicitly put “AI assistant/guide” and voice entry under **P3 — advanced capabilities**, and stated P3 must not interrupt unfinished P1 work.
- `docs/roadmap/STAGE_34_CONSTRUCTION_COMPLETENESS_PROGRAM.md` described AI Copilot in a multi-phase program, but did not replace or resolve the conflicting P3 release-control instruction.
- The V1 master matrix and progress report classified the Web AI Assistant / Smart Guide as a small separate UI work item, not as an end-to-end product capability spanning UI, model orchestration, tools, persistence, permissions, approvals, calculations, import and report generation.

Conclusion: different documents gave developers and coordinators conflicting interpretations of whether AI was a V1 blocker or an optional later enhancement.

### 2. Weighted project tracking did not represent the user's promised scope

The last reconciled Jalal 3 matrix on 2026-10-12 assigned “Web AI Assistant / Smart Guide” a weight of **3%**, with **20% task completion** recorded (0.60 earned weighted points). That label and weight capture a narrow frontend work item; they do not measure the wider AI Project Controls Assistant specified by the product principles.

The same report explicitly recorded **0% for system-wide integration/regression/release QA**. Thus there was no evidence-backed end-to-end V1 acceptance result that would prevent a static guide or partial contract from being mistaken for a production assistant.

Source: `docs/audits/WEIGHTED_PROGRESS_RECONCILIATION_2026-10-12.md`.

### 3. Current implementation proves foundations, not the complete assistant

Verified current-main examples:
- `apps/web/src/workspace-smart-guide.ts` creates a structured projection of findings and proposed actions.
- `apps/web/src/workspace-control-intelligence.ts` validates scope/revision/source references and projects control findings and actions.
- `src/construction_pm/backend_p0/authoritative_schedule_query.py` can evaluate an immutable schedule snapshot and return authoritative schedule data. Its docstring expressly puts natural-language interpretation outside that adapter.
- `src/construction_pm/ai_action_boundary.py` defines proposal, permission-adapter, decision and audit-sink abstractions. The inspected reference implementation uses a fixed allowed-tool set and an in-memory audit sink; this is useful foundation/test infrastructure, not proof of production-persisted policy and audit integration.
- `apps/web/src/workspace-view.ts` renders proposed actions as cards, but those cards alone are not a complete approve/reject, execute and verify flow.
- `apps/web/src/main.ts` wires the workspace and its current UI actions; an integrated production model/provider conversation and tool-execution loop was not evidenced in the inspected main path.
- The repository search found no direct OpenAI/Anthropic model execution/provider client in the relevant current-main assistant path. Provider-independent design remains possible, but execution/orchestration is a missing integration seam.

These observations distinguish available primitives from an integrated feature. They do not claim that every possible provider or deployment path in the full system has been exhaustively disproved.

### 4. Missing release proof reinforced the gap

No evidence was identified in the inspected V1 release records of an integrated test starting with a user's natural-language/file input and proving all of the following as one flow:
1. scoped project intent and validated import;
2. real project/WBS/activity/calendar/relationship writes;
3. authoritative schedule execution and revision-bound result;
4. preview plus user approval/rejection;
5. permission denial and stale revision fail-closed behavior;
6. fresh read-after-write;
7. real Gantt/report/export based on the persisted calculation;
8. complete execution/failure report and durable audit.

Isolated schema/unit/route tests are valuable, but cannot prove this end-to-end requirement by themselves.

## Root-cause statement

The evidence supports four systemic causes:
1. **Conflicting governance:** AI was simultaneously described as P0 and P3.
2. **Underscoped work item:** tracking captured “Web Smart Guide” rather than the cross-layer V1 assistant the product required.
3. **Primitive-first delivery:** contracts, static projections, query services and approval boundaries were developed without a single vertical end-to-end release path.
4. **Missing mandatory acceptance gate:** there was no explicit current-main rule requiring project creation/import → calculation → controlled action → verification/reporting before declaring V1 assistant complete.

## Corrective controls introduced by this change

- `docs/architecture/PRODUCT_PRINCIPLES.md` now states in Principle 1B that all applicable calculations must conform to the versioned authoritative P6 documentation baseline and remain owned by Shared Core; AI cannot act as a second calculation authority.
- The same principles now make a production, project-aware AI Assistant a mandatory V1 release blocker.
- `docs/PRODUCT_COMPLETION_CONTROL.md` no longer classifies the required V1 assistant as P3.
- `docs/architecture/AI_ASSISTANT_V1_REQUIREMENTS.md` defines the required assistant capabilities, personalization, typed tools, permission families, approval, security and end-to-end acceptance tests.
- `docs/architecture/COMPETITIVE_COMPLETENESS_MATRIX.md` now classifies the integrated assistant/natural-language scheduling as a release-gate capability rather than treating architecture alone as sufficient.
- `docs/roadmap/AI_ACTION_APPROVAL_BOUNDARY.md` now distinguishes reference approval primitives from production authorization/audit/execution requirements.

## Remaining implementation gap — do not mark closed by documentation alone

The documentation change does **not** implement the production assistant. The following remain implementation/release work:
- select/configure the supported model provider(s), secrets and runtime policy;
- build the grounded orchestration/tool loop with typed, allowlisted tools;
- wire tools to real Application/API/persistence for all released operations;
- complete production permission adapter, approval-bound proposal identity/revision, durable audit and idempotent execution;
- integrate supported import/document parsing and validation;
- implement functional approval/rejection and operation status in UI;
- produce charts/reports only from authoritative persisted results;
- add and pass end-to-end, negative-security, stale-revision, import/round-trip and cost/latency tests;
- reconcile all AI tasks and release weights with a single current-main capability matrix.

Release control: issue #459 and Gate B must remain open until these requirements have runtime evidence. A documentation commit does not increase implementation progress.
