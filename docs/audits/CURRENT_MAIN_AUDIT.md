# Current Main Audit Pointer — 2026-10-08

This file is the single live pointer for V1 current-main audit evidence. Historical audit documents remain historical records and must not be interpreted as the current repository state.

## Current integration point

- Repository: `consttruction-pm/consttruction-pm-platform`
- Current main at audit: `b15aef35b73031887756af28b87a75c33517613f`
- Current V1 weighted-progress source: approved **Jalal 3** workbook, updated 2026-10-08.
- Current verified weighted progress recorded from that workbook reconciliation: **59.41%**.
- Remaining weighted work: **40.59%**.
- Progress rule: only current-main evidence and verified merged work may increase completion; open/unmerged PRs do not add progress.

## Recent current-main evidence

- PR #1285 — P6 calendar exception precedence wired into authoritative resolvers; merged as `1ea4c9333a49c53f894dd1c93178ed1b7152d1ed`.
- PR #1281 — Web P6 workspace preserves canonical P6 field data types; merged as `5382c1ac24f027f8e37066399983df0d40d455a9`.
- PR #1276 — authenticated P6 Calendar CRUD/copy/replace and atomic replication; merged as `f5edaf2254a87c1eea05eb4b76972d1d94654f8a`.
- PR #1279 — authenticated P6 Expense API; merged as `6c689d14532c4a9dc5ec402891f85782ddf373bc`.
- PR #1260 — endpoint-aware P6 import upload limits; merged as `e4855110f2077cf673ed823d93161e9eca6a1a596`.

## Open Jalal work

- PR #1282 / Issue #1251 — calculation identity v2 and replay semantics; exact-head CI was refreshed after a test-helper correction.
- PR #1280 / Issue #1248 — proposal-only scenario query avoids unnecessary CPM evaluation; exact-head CI is green.
- Issue #1247 — authoritative CalculationContext persistence/reconstruction; implementation remains gated behind the identity policy work.
- Issue #1249 — canonical Web/Desktop/Mobile scheduling adapter; the current main tree now contains the canonical client-sync adapter and thin Web/Desktop/Mobile adapters, but the issue still requires explicit current-main reconciliation and exact-head acceptance evidence.
- Issue #1259 — duplicate legacy resource infrastructure boundaries; audit shows legacy modules remain consumed by the existing Resource package/test surface, so deletion or migration must not be performed speculatively.

## Governance rule

Historical snapshots in `docs/V1_MASTER_AUDIT_MATRIX.md`, `docs/architecture/V1_WEIGHTED_PROGRESS_BASELINE_2026-10-01.md`, and dated audit files remain valid evidence of their historical state only. New progress reports must use this live pointer together with the approved Jalal 3 workbook and current GitHub merge/CI evidence.
