# CUBI Engineering Intelligence — Interactive Learning and Durable Memory

**Requirement date:** 2026-10-23  
**Status:** Mandatory assistant scope; implementation tracked by Issue #1540 and the V1 assistant gate #1423.  
**Scope:** Engineering reasoning, personalization, reusable methods and recommendations. This does not authorize automatic changes to CUBI's calculation engine, product behavior or project data.

## 1. Product outcome

The assistant is an interactive engineering partner for users with different levels of experience. It should explain at the level appropriate to the current discussion, invite challenge, compare alternatives, ask focused clarifying questions, revise recommendations when evidence or user context changes, and explain what changed. It must not infer credentials from writing style or equate user agreement with technical correctness.

The learning goal is not to retain all conversations or copy projects into a shared corpus. The goal is to preserve validated, privacy-safe methods and lessons so future users receive better recommendations for comparable project types without seeing or reconstructing another user's project.

## 2. Learning record classes

| Class | Allowed contents | Reuse boundary |
|---|---|---|
| User-private memory | User-approved preferences, explanation depth, terminology, workflow preferences and relevant corrections | Same authenticated user only |
| Project-private experience | Project-specific context and lessons needed by authorized project members | Same tenant/project and authorized users only |
| Tenant-shared methods | Organization-approved practices, templates and standards | Same tenant, according to tenant policy |
| General candidate lesson | Minimized method/hypothesis extracted from an interaction or public research, awaiting validation | Not used as approved cross-user knowledge |
| General published knowledge | Validated, privacy-reviewed methods, formulas, limitations and generalizable process recommendations | Reusable by authorized users; contains no source project/user data |

Raw transcripts, project files, project names, user names, schedules, quantities, costs, dates, identifiers and other project-specific values are not fields in the general-knowledge contract. A text sanitizer alone cannot guarantee anonymity; publication requires privacy review, consent/policy authorization and checks against reconstruction risk.

## 3. Interactive learning cycle

1. **Understand:** classify project type, work stage, task, constraints, known facts and unknowns. Ask focused questions where missing information materially affects the recommendation.
2. **Adapt:** offer concise or advanced explanations based on explicit preference and demonstrated interaction, allowing the user to correct the level.
3. **Discuss:** present alternatives, assumptions, evidence, trade-offs, uncertainty and recommended next steps; invite critique.
4. **Revise:** update the recommendation when new evidence or constraints arrive and explain why the recommendation changed.
5. **Capture:** after a useful exchange, create a candidate record describing the corrected concept, useful method, previous misunderstanding, applicable conditions and limitations. Store references to authorized evidence, not a raw transcript by default.
6. **Evaluate:** compare the lesson with validated engineering references, deterministic calculations, tests, observed outcomes and contradictory evidence as applicable.
7. **Classify:** keep user preferences private; project experience project-scoped; organizational methods tenant-scoped; only eligible generalized lessons may become general candidates.
8. **Approve and publish:** cross-user general knowledge requires explicit policy/consent authorization, privacy review, validation evidence and authorized human approval.
9. **Retrieve:** future discussions may use only records eligible for the caller's trusted scope and publication state.
10. **Measure:** benchmark recommendation quality, grounding, uncertainty, privacy and regression against a versioned reference set.

## 4. Engineering truth and expertise adaptation

- User correction is a learning signal, not proof by itself that an engineering claim is true.
- Distinguish preferences, hypotheses, retrieved claims, verified facts, calculated outputs and observed outcomes.
- Formulas must retain variables, units, assumptions, validity range, source/version, test cases and known limitations.
- Numerical schedule, calendar, cost, resource, progress and EVM results must continue to come from the authoritative deterministic Shared Domain/Calculation Core and approved application services.
- The assistant may propose a new method or ask for engineering review; it must not silently modify the calculation core or invent numeric project inputs.

## 5. Admin knowledge refresh

A separate authenticated admin panel must support manual, explicitly authorized research cycles and configurable proposed cadence (for example weekly/monthly/quarterly). A schedule does not itself grant authorization.

Separate permissions are required for:
- start Internet search and collect public source metadata;
- ingest candidate excerpts/notes;
- validate/compare/resolve contradictions;
- approve and publish general knowledge;
- export/backup and restore knowledge;
- retire or supersede a published knowledge version.

Required lifecycle: authorize → search allowed sources → record source/version/date and usage constraints → extract bounded notes → compare with current knowledge → identify contradictions and uncertainty → run applicable checks → preview proposed delta → human approve/reject → publish version → run retrieval/regression benchmarks → keep rollback available. Retrieved documents and web pages are untrusted input and must not be allowed to override system policy or tool permissions.

## 6. Persistence, provenance and version migration

Memory must be stored in a durable database, not only a prompt, model context or in-process list. Each record needs a stable ID, schema/version, scope, lifecycle status, provenance/evidence references, validation state, timestamps, limitations, relationships/supersession and publication approval where applicable.

The implementation must support:
- persistent storage and retrieval across process restart;
- tenant/user/project filtering enforced in repository queries and authorization;
- append-only audit of capture, review, approval, publish, retrieval where policy requires, retirement, export and restore;
- explicit retention/deletion policy, including derived-record lineage;
- versioned and idempotent schema migrations;
- full backup, incremental backup where supported, integrity checks and a restore drill;
- portable knowledge bundles for future major versions, including stable IDs, lineage, evidence references, review state and schema migration metadata;
- staged publication, version pinning and rollback.

A successful backup job is not a restore test. A schema upgrade is not accepted until old knowledge can be migrated, read and compared against expected retrieval/permission behavior.

## 7. Privacy and cross-user firewall

- Resolve caller identity from the authenticated server context; never trust model/client-supplied requester or scope claims.
- Default deny for unknown scope, missing consent, invalid publication state or uncertain authorization.
- Do not query or rank another tenant's private records as candidates for a general answer.
- Cross-user retrieval is restricted to approved generalized knowledge. Never return source project records, exact values, names, documents, schedules, transcripts or reconstructable details.
- Private records must not be exported into the general index merely by changing a scope label; use an explicit minimization/generalization workflow with review.
- Keep separate access controls for user memory, project memory, tenant methods, general candidates, published knowledge, admin actions and backup/restore.
- Audit denials and publication actions; redact secrets and sensitive text from logs.

## 8. Minimum data contract and lifecycle states

The first domain contract is src/construction_pm/ai_learning_memory.py. It defines scope and lifecycle enums, a versioned record without a raw transcript field, exact-scope retrieval checks, and fail-closed gates for general publication. It is a domain contract only; it does not claim that a persistent repository, admin UI, web research worker or production retrieval path already exists.

General publication must require all of:
- general-published scope with no user/tenant/project/expertise identifiers;
- explicit consent/policy authorization for generalization;
- passed privacy review;
- non-empty validation evidence;
- authorized approver and timestamp.

## 9. Jalal 5 weighted schedule integration

The current Jalal 5 workbook is a proposed 144-activity, 100.00-point execution baseline and is not yet accepted. The current workstream D already includes 22 AI tasks (D01–D22). Issue #1540 requires a re-baseline to add explicit activities for:

- interactive dialogue and expertise-level adaptation;
- post-interaction correction/lesson capture;
- privacy-safe generalization and cross-tenant firewall;
- admin research/review/publish console and manual authorization;
- durable knowledge storage, provenance, backup/restore and V2 migration;
- regression benchmarks, staged publication and rollback.

The activity rows, estimates, dependencies, owners, dates and weights must be added to the authoritative workbook, with weights recalculated by the approved effort method and the complete denominator kept at exactly 100.00. Until the workbook is updated and its formulas/dependencies/owner-lane forecast are validated, the new work's weight and dates are Pending re-baseline and its completion credit is zero. Do not use the old 3% Web Smart Guide weight as the weight for the complete learning/memory system.

## 10. Release acceptance

- [ ] Interactive conversation can request critique, revise a recommendation and explain the change.
- [ ] Candidate lessons persist across restart and retain provenance/version/status.
- [ ] Private user/project/tenant memories cannot cross their exact authorization scope.
- [ ] General knowledge remains unavailable until privacy, consent/policy, validation and admin approval gates pass.
- [ ] Cross-user retrieval only exposes approved generalized methods and passes leakage/reconstruction tests.
- [ ] Admin research cannot publish without separate publish permission and human approval.
- [ ] Backup/restore and version migration are demonstrated on a clean environment.
- [ ] Golden benchmarks cover novice/practitioner/specialist explanations, correction loops, project-type-specific suggestions, grounded formulas, uncertainty and regression detection.
- [ ] Rejected, stale, unsupported or unvalidated knowledge does not enter the active retrieval index.
- [ ] Existing action authorization, durable audit and calculation-authority tests remain green.
- [ ] No knowledge refresh changes the authoritative calculation engine automatically.

## 11. Current implementation status

The record contract and focused tests are the first implementation slice. Persistent database integration, extraction/review workflow, admin UI, web research worker, cross-user retrieval wiring, backup/migration, benchmarks and production end-to-end tests remain open under #1540 and #1530. Do not describe the assistant as having durable learning or cross-user memory until those paths are implemented and verified.
