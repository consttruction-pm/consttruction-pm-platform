# CUBI Project State Ledger

**Snapshot date:** 2026-10-25
**Repository:** `consttruction-pm/consttruction-pm-platform`
**State rule:** Main-only completion; update this ledger whenever implementation or acceptance materially changes.

## Current baseline

| Item | Verified state |
|---|---|
| Current main SHA inspected | `61d3ab7f1f2defa5415c42be99e9c32c96a9743d` |
| Default branch | `main` |
| Current website schedule of record | ChatGPT Library workbook `/cubisite.xlsx` (v2 after reconciliation on 2026-10-25); companion copy `/CUBISITE/cubisite.xlsx` must remain identical |
| Current CUBISITE scope | Original T01–T45 and risk reserve BUF retained; AI-C01–AI-C07 added |
| CUBISITE schedule arithmetic | 193 active effort-days proposed (previous 171 + 22 proposed AI days), 25-day risk reserve, 218 total; 52 capability activities plus separate BUF; active capability weights total 100.00 points |
| Estimated weighted progress | 26.89% formula estimate after denominator expansion; **not QA-certified**. The previous 30.4% is historical only |
| Forecast assumption | Single executor, half-day sequencing, Mon–Fri; public holidays, leave and external waiting excluded. Proposed base finish 2027-05-21; finish with 25-day reserve 2027-06-25. Dates are not an accepted contractual baseline |
| CUBISITE exit gate | Full production website E2E and release sign-off remain open |

## Current implementation evidence

### Production AI action path — PR #1547

- PR: https://github.com/consttruction-pm/consttruction-pm-platform/pull/1547
- Branch: `feat/ai-action-runtime-production-20261023`
- Current head (2026-10-25): `8d38b8d16c9c5a49b6f0c53da266d973981ea746`
- State: **Open / unmerged**; do not count its code as main completion.
- Exact-head gates:
  - ConstructionPM CI: https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40136179164 — PASS (Python 3.11/3.12/3.13).
  - PostgreSQL Integration: https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40136179465 — PASS.
  - Client Typecheck: https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/40136179203 — PASS (Web, Desktop, Mobile, Client Sync).
- Recent safety correction: executor error after entering execution now yields proposal status `uncertain`, audit event `execution_outcome_uncertain`, and conflict response; normal execution cannot replay an uncertain action. Regression test simulates a side effect followed by an error.
- This is a tested incremental safety seam, **not full assistant completion**.

### Explicitly open assistant gaps

- No complete deployed model/provider orchestration through real authenticated project use cases.
- No complete registered production project-mutation set for create/edit WBS, activities, relationships, calendars, resource/cost records.
- Current grant source and each handler’s optimistic-lock/idempotency enforcement inside the authoritative transaction must be supplied and verified.
- No end-to-end proof yet of mutation → commit → fresh-connection read-back → Shared Core calculation identity → grounded explanation/report.
- Document/voice/Excel intake and mapping/preview, final AI client UI, report/chart/export integration remain incomplete.
- Knowledge research/review/human publication, privacy-safe generalization, retention/deletion propagation, backup/restore drills, migration lineage and model/knowledge golden benchmarks remain incomplete.
- The new `uncertain` status prevents an unsafe blind retry but is not yet accompanied by an operator-authorized, authoritative reconciliation/recovery workflow.
- PR #1547 remains open; #1423 and #1530 must remain open until their full acceptance criteria are evidenced.

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

Complete the real project-use-case integration for #1530: bind the authenticated current-grant provider and register a minimal typed activity-create tool through the existing Activity Master application API/repository, enforce expected project revision and idempotency inside the authoritative transaction, add fresh-connection PostgreSQL read-back and denial/replay/stale tests, and verify all checks on one exact head. Do not pretend this single vertical slice completes all #1423/#1540 capabilities; extend the same pattern to WBS, relationships, calendars, resources/cost and outputs, while preserving the Shared Core as sole calculation authority.
