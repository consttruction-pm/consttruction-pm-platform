# Knowledge inventory — measured 2026-11-12

**Database:** `docs/workspace/evidence/knowledge-multilingual-v26-2026-11-12/cubi-knowledge-v26.sqlite3`
**SHA-256:** `ac3eee96dbbebac31544145114bfc5b4a9389b369a06e642954d044825ad86af`
**Schema version in that file:** 2 (the runtime is now 3; the file is evidence and is opened read-only)
**Command:** `python tools/knowledge_inventory.py <database>` (read-only URI, no migration, no writes)

These are measured counts, not estimates. Where a number understates the
product, the gap is stated rather than rounded up.

## Cards

| Metric | Count |
| --- | --- |
| Total cards | 1030 |
| Draft (publication) | 1030 |
| Validated (validation) | 1030 |
| Published | **0** |
| Rejected | 0 |
| Retired | 0 |

Card types: `operation` 596, `concept` 289, `configuration` 94, `relationship` 24,
`training` 14, `reference` 9, `workflow` 3, `troubleshooting` 1.

**Consequence:** with zero published cards the production search and assistant
correctly answer `insufficient_knowledge`. Review and publication have not been
performed on the real corpus; the pipeline is ready but the content is not live.

## Official source coverage

| Source | Topics | Status |
| --- | --- | --- |
| `p6-26-html-help` | 982 | converted |
| `p6-26-user-guide` | 557 | converted |
| Total | 1539 | 0 failed |

Recorded cross-source merges: **509** (`topic_merged` audit rows). The merge
signature was hardened in `fix/knowledge-technical-debt-2026-11-12`: page
filename and card type are no longer part of it, and purpose plus the full
content lists must match, so pages that only share a heading are kept apart.
The historical 509 merges were produced under the previous signature and are
preserved as audit history; they are not retroactively re-split.

## Translations per locale

Source language is `en`. Nine locales have content; one card
("Create a project") has one record in each. All nine are human-provenance,
`translated`, `pending` review, and were written before source-hash binding
existed, so `source_bound` is 0 for them.

| Locale | Records | Approved | Published | Missing slots |
| --- | --- | --- | --- | --- |
| fa | 1 | 0 | 0 | 1029 |
| de | 1 | 0 | 0 | 1029 |
| zh-CN | 1 | 0 | 0 | 1029 |
| zh-TW | 1 | 0 | 0 | 1029 |
| ar | 1 | 0 | 0 | 1029 |
| fr | 1 | 0 | 0 | 1029 |
| ja | 1 | 0 | 0 | 1029 |
| ko | 1 | 0 | 0 | 1029 |
| ru | 1 | 0 | 0 | 1029 |

| Translation metric | Count |
| --- | --- |
| Available slots (1030 cards × 9 target locales) | 9270 |
| Filled slots | 9 |
| Missing slots | 9261 |
| Approved | 0 |
| Published | 0 |
| Rejected / review required | 0 |
| Machine-generated | 0 |
| Source-hash bound | 0 |
| Stale source-bound | 0 |

Locale *infrastructure* is complete and tested for all ten locales. Translated
*content* is 9 records out of 9270 slots (0.10%). That is the real state and it
is not described as coverage.

## What this means for the next step

1. The ten-locale engine, review queue, approval rules, source binding and
   fallback behaviour are implemented and tested (224 knowledge tests).
2. The corpus is ingested but unpublished; publication requires a human
   reviewer per card, and no such review has been recorded.
3. Translation seed content is a single card. Producing real multilingual
   content for 1030 cards is human translation work, not something the
   pipeline can legitimately invent.
