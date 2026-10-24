# CUBI Project State Ledger

**Snapshot date:** 2026-10-25
**Repository:** `consttruction-pm/consttruction-pm-platform`
**State rule:** Main-only completion; update this ledger whenever implementation or acceptance materially changes.

## Current baseline

| Item | Verified state |
|---|---|
| Current main SHA inspected | `259461b18d71d8185ad02cfb9f443e05cdad2648` |
| Default branch | `main` |
| Current website schedule of record | ChatGPT Library workbook `/cubisite.xlsx` (v3 after reconciliation on 2026-10-25); companion copy `/CUBISITE/cubisite.xlsx` is maintained as an identical mirror |
| Current CUBISITE scope | Original T01–T45 and risk reserve BUF retained; AI-C01–AI-C07 added |
| CUBISITE schedule arithmetic | 193 active effort-days proposed (previous 171 + 22 proposed AI days), 25-day risk reserve, 218 total; 52 capability activities plus separate BUF; active capability weights total 100.00 points |
| Estimated weighted progress | 26.89% formula estimate after denominator expansion; **not QA-certified**. The previous 30.4% is historical only |
| Forecast assumption | Single executor, half-day sequencing, Mon–Fri; public holidays, leave and external waiting excluded. Proposed base finish 2027-05-21; finish with 25-day reserve 2027-06-25. Dates are not an accepted contractual baseline |
| CUBISITE exit gate | Full production website E2E and release sign-off remain open |

## Current implementation evidence

### Production AI action path — PR #1547 (merged)

- PR: https://github.com/consttruction-pm/consttruction-pm-platform/pull/1547
- Source branch: `feat/ai-action-runtime-production-20261023`
- Merged main SHA (squash): `259461b18d71d8185ad02cfb9f443e05cdad2648`
- Source PR head: `8232a74cdf566de0c31e6d4332e16aa2541eb835`; last code/test head was `bf110ac62b9ff88539ced03b6bd16952df83a4de` (later change only updated the integration document).
- Exact code-head gates:
  - ConstructionPM CI: https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40139930835 — PASS, Python 3.11/3.12/3.13.
  - PostgreSQL Integration: https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40139930827 — PASS.
  - Client Typecheck: https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40139930828 — PASS for Web, Desktop, Mobile and Client Sync.
- Main post-merge runs for SHA `259461b18d71d8185ad02cfb9f443e05cdad2648` were queued at ledger update time and must be recorded after they finish.
- The merged production slice includes authenticated Web proposal/list/detail/approve/reject/execute routes, fail-closed server tool registry, scoped proposal/audit stores, exact current-grant checks, durable execution reservation, non-replayable stale/denied/uncertain states, and idempotency.
- First real typed mutation `activity.create` now goes through the existing `P6ActivityMasterAPI` and Activity Master repository; mutation and idempotency share a transaction, and SQLite plus live PostgreSQL tests verify fresh-connection read-back.
- `uncertain` and interrupted `executing` states are safely non-replayable, but an admin-authorized reconciliation/recovery workflow remains open. The first create tool does not yet call the Shared Core to run a schedule and ground a returned schedule result. This is an incremental production slice, **not full assistant completion**.

### Activity Master SQLite transaction ownership — PR #1548 (merged)

- PR: https://github.com/consttruction-pm/consttruction-pm-platform/pull/1548
- Merged main SHA: `7eaeea4fda70f447c4ad1969d52a18ffaaac8ceb`
- The repository commits or rolls back only a transaction it started itself; a caller-owned transaction is preserved, including on revision conflict. Tests cover outer rollback, conflict behavior and failed owned writes.

### Explicitly open assistant gaps

- The model/provider orchestration and natural-language tool selection are still not wired into a conversational assistant turn; there is no production assistant client flow.
- Only the first real Activity Master creation tool is registered through the explicit production composition; WBS, activity edit, relationships, calendars, resources/cost and other project-control actions remain unregistered.
- Production deployment must supply the trusted current-grant adapter and transaction manager. The first Activity Create handler enforces proposal scope and uses idempotency in the shared transaction; revision lifecycle integration across every write handler remains to be proven.
- No end-to-end proof yet of mutation → commit → fresh-connection read-back → Shared Core calculation identity → grounded explanation/report.
- Document/voice/Excel intake and mapping/preview, final AI client UI, report/chart/export integration remain incomplete.
- Knowledge research/review/human publication, privacy-safe generalization, retention/deletion propagation, backup/restore drills, migration lineage and model/knowledge golden benchmarks remain incomplete.
- The `uncertain` status prevents an unsafe blind retry but remains without an operator-authorized, authoritative reconciliation/recovery workflow.
- PR #1547 is merged as an incremental slice. #1423 and #1530 must remain open until their full acceptance criteria are evidenced.

## Canonical CUBISITE schedule reconciliation

Updated in the ChatGPT Library workbook on 2026-10-25:

- Added AI-C01–AI-C07 for interactive/adaptive dialogue, candidate-lesson capture, durable scoped memory and lineage, privacy/tenant firewall, admin research/review/publish, backup/restore/migration, and golden benchmarks/version rollback.
- Preserved T01–T45 and BUF, added dependency mapping and acceptance tests, and recalculated suggested effort weights to exactly 100.00 points.
- All seven AI activities have zero earned completion. Their effort, weights and dates remain **proposed / pending acceptance**, not an approved rebaseline.
- No progress credit is awarded for documentation or an open PR.
- Original 30.4% figure retained only as historical; current 26.89% is a formula estimate with the expanded denominator and is not QA acceptance.
- The workbook is still a Library artifact rather than a versioned file committed to this repository. Preserve the Library file as the user-requested schedule of record and keep this ledger synchronized to it.

## Other active pull requests / audits to reconcile

- #1545 — CUBISITE AI learning schedule addendum; open draft, internal package weights only; do not treat as replacing the whole CUBISITE schedule.
- #1522 — option-level scheduling compatibility reference; open, not exhaustive; resource-dependent behavior and calendar inheritance remain explicit gaps.
- #1520 — WBS persistence; open draft and separate persistence slice, not full WBS production UI.
- #1518 / #1511 / #1509 — resource-driving/leveling slices; remain gated by exact-head checks and complete end-to-end semantics.
- #1519 — Web localization error-message slice, open draft; does not prove all-language coverage.
- #1486 — whole-product V1 Mobile requirement and continuity gate; must remain separate from CUBISITE-only schedule.
- #680 — evidence-based weighted progress governance; no percentages from PR/commit counts.

## Governance repair being proposed in this branch

GitHub issue #1486 requires `docs/governance/PROJECT_CONTINUITY_PROTOCOL.md` and `docs/governance/PROJECT_STATE_LEDGER.md` to be the read-first entrypoint. At the time of inspection (2026-10-25), those paths were not retrievable from `main` via the GitHub Contents API or repository code search. This branch creates them as a continuity repair; they are **not main-current until merged**.

## Next concrete action

Next P0: implement the actual server-side assistant-turn/provider orchestration and conversational Web UI, with constrained server-owned tool selection that can only create proposals—not mutate without explicit approval. After the first turn is functional, implement human-admin reconciliation for `uncertain`/interrupted actions with fresh authoritative read-back and audit. Add remaining WBS/relationship/calendar/resource/cost tools and Shared Core schedule-result grounding; keep #1423/#1530/#1540 open until one integrated exact-head E2E path proves the full flow.
