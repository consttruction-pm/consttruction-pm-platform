# Knowledge corpus verification — PostgreSQL, 2026-11-13

Publication branch: `feat/knowledge-corpus-postgres-verification-2026-11-13-publish`.

- Original base main: `f07364f02eb3dc9fa6bfc5301eb523d3edab7e52`
- Current main base: `218977dc72405061b4fc3d0f228db7e70df7e140`
- Recovered implementation: `a2a809f8af7a0c5784ce0d7fce4ae0dcdf37eb13`
- Rebased implementation: `a3bb6b3`
- Rebased pre-policy head: `c69b528`
- Locale-policy implementation: `938f382`
- Original artifacts: `knowledge-corpus-postgres-2026-11-13.patch`,
  `knowledge-corpus-postgres-2026-11-13.bundle`

This directory holds machine-readable evidence for the full-corpus PostgreSQL
verification, the corpus-count reconciliation, the translation-locale policy
and the retrieval probe. Every count comes from ingesting the authoritative
Version 26 HTML Help table of contents and the Version 26 Professional User
Guide; no count is hand-written.

## Commands

```bash
python tools/knowledge_corpus_verify.py \
  --dsn postgresql://postgres@127.0.0.1:55432/kb_corpus_rebase_20261113 \
  --sqlite /tmp/kb_sqlite_corpus.sqlite3 \
  --repeat-ingest \
  --out docs/workspace/evidence/knowledge-corpus-postgres-2026-11-13/corpus-verification.json
```

PostgreSQL 14.24, dedicated database `kb_corpus_rebase_20261113`, schema v4.
The SQLite comparison corpus was built by the same pipeline against the same
two sources; the verifier copies it before opening, so the evidence file is
never migrated or modified in place.

## Result

- `ok: true`, `parity.equal: true`, `repeat_ingest.unchanged: true`.
- PostgreSQL: 1090 cards, 1539 topics, 0 translations, 0 events, 465 audits.
- SQLite: 1090 cards, 1539 topics, 0 translations, 0 events, 453 audits.
- 982 HTML Help topics + 557 User Guide topics, all `converted`.
- 449 `topic_merged` decisions; no duplicate card content signatures, no
  duplicate topic keys, no orphan translations, every card has a topic, every
  stored hash is sha256, every topic URL is on `https://docs.oracle.com/`.
- The second ingestion added no cards, topics or translations; it recorded only
  its own run bookkeeping (`audits` 465 → 469).

Audit totals differ because PostgreSQL was ingested twice during recovery and
SQLite once. Corpus-affecting audit facts (`topic_merged`, failures) are
compared exactly; run bookkeeping is reported separately by the verifier.

## Corpus-count reconciliation: 1030/1539/509 → 1090/1539/449

`corpus-merge-reconciliation.json` and `.csv` list **every** topic whose merge
decision changed, with canonical and duplicate identity, official URLs,
previous and current card ids, previous and current content signatures, the
exact field-level difference and the reason.

- 61 pages that were merged in the legacy evidence corpus now stay separate:
  they share title and procedure text but have a different official breadcrumb
  (`purpose`), so the current signature keeps them under their own source
  section.
- 1 pair that previously stayed separate now merges because its normalized
  content signature is identical in the current corpus.
- Net effect: +60 cards (1030 → 1090), topic count unchanged at 1539,
  `topic_merged` decisions 509 → 449.

The difference is **not** produced by weakening duplicate detection. The current
signature is stricter (it includes `purpose`); no duplicate content signature
remains after re-ingestion.

## Translation policy and coverage

Product policy (`src/construction_pm/knowledge/locales.py`):

- Product languages: `fa`, `en` (source), `de`, `zh-Hans`, `ar`, `fr`, `ja`, `ko`
  — eight locales, seven translation targets.
- `zh`, `zh-CN`, `zh-SG`, `zh-TW`, `zh-Hant`, `zh-HK` and `zh-MO` all resolve to
  `zh-Hans`. Chinese is one translation slot, not two.
- `ru` remains readable as a legacy locale. Stored Russian rows are preserved
  and still answer, but Russian is not a product target and is excluded from
  every coverage denominator.

Evidence (`translation-policy-reconciliation.json`,
`translation-coverage.json`):

- Full PostgreSQL corpus: 1090 cards × 7 targets = **7630 slots**, 0 filled,
  0 published, 0 approved, 0 machine-generated, 7630 missing → 0.00 %.
- Committed legacy SQLite corpus: 1030 cards × 7 targets = **7210 slots**,
  7 filled → 0.10 %. The nine stored seed rows are `fa`, `de`, `zh-CN`,
  `zh-TW`, `ar`, `fr`, `ja`, `ko`, `ru`; the two Chinese rows collapse into the
  single `zh-Hans` slot, and `ru` is reported as one legacy record.
- All nine legacy rows are `translated` / `pending`, `cubi_authored`,
  `machine_translated = 0`, no reviewer, no source binding, not answerable.
  No English text is relabelled as a translation and no machine output is
  approved.
- No legacy row was deleted or rewritten. `translation_locale_candidates()`
  performs a read-time alias lookup (`zh-Hans` → `zh-CN` → `zh-TW`) and the
  coverage report exposes `legacy.storage_codes` and
  `legacy.normalized_records`.

Remaining human-review work: the seven product seed cards (`fa`, `de`,
`zh-Hans`, `ar`, `fr`, `ja`, `ko`) each need a human reviewer to approve and
publish through the review queue. The legacy Russian record requires no product
review. Machine approval is impossible by construction.

## Retrieval evidence

`retrieval-evidence.json` is the eight-language probe against the committed
corpus after publishing the real "Create a project" card. All eight questions
return `kind: answer`, the correct `response_language`, `direction` (`rtl` for
fa/ar, `ltr` otherwise), `evidence_state: verified` and the official source
URL. Non-English answers report `fallback_used: true` with
`translation_status: translated` because the seed is not approved; the
citation therefore keeps the reviewed English source title. The unpublished
probe returns `missing` for a reader and `unpublished` for a reviewer, with
zero citations in both cases.

## Partial-run recovery

`partial-run-user-guide.json` records a deliberately interrupted User Guide
run: 557 topics discovered, 30 converted, process stops.
`resume-run-user-guide.json` records the continuation: 0 newly discovered,
527 converted, 0 failed. The combined 557 topics equal the authoritative total
and no duplicate card was produced.

## Source-registry discrepancy (recorded, not invented)

The mission text refers to "17 registered source identifiers". This repository
contains 5 `SourceDefinition` entries, 6 audited identifiers in
`source-audit.json` (982 + 557 authoritative, 988 and 527 alternates not
ingested, 2 landing pages) and 21 distinct official pages in the reference
index. No file defines 17 identifiers. The verification reports the actual
registry and does not claim a 17-source inventory.

## Remaining blockers

- Translation coverage is 0.10 % of the legacy corpus and 0 % of the fresh
  PostgreSQL corpus, with 0 published/approved records. Real translations
  require an authorized human workflow; the repository must not fabricate them
  or call an external AI.
- Publication is performed by the operator with an ephemeral repository-scoped
  credential; the credential is never written to the repository, the evidence
  or the logs.

## Next concrete action

Approve and publish the seven product seed translations (or replace them with
human-reviewed text), re-run `tools/knowledge_corpus_verify.py` and
`translation_coverage()`, and hand the Agent 1 checklist in
`docs/architecture/CUBI_KNOWLEDGE_AGENT1_INTEGRATION_CONTRACT.md` to the
workspace team.
