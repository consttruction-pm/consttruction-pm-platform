# Knowledge corpus verification — PostgreSQL, 2026-11-13

Branch base: `f07364f02eb3dc9fa6bfc5301eb523d3edab7e52` (main after PR #1845).

This directory holds the machine-readable evidence for the full-corpus
PostgreSQL verification, multilingual coverage inventory and retrieval probe.
Nothing here is a fixture result: every count comes from ingesting the
authoritative Version 26 HTML Help table of contents and the Version 26
Professional User Guide.

## Commands

```bash
python tools/knowledge_corpus_verify.py \
  --dsn postgresql://postgres@127.0.0.1:55432/kb_corpus \
  --sqlite /tmp/kb_sqlite_corpus.sqlite3 \
  --repeat-ingest \
  --out docs/workspace/evidence/knowledge-corpus-postgres-2026-11-13/corpus-verification.json
```

PostgreSQL 14.24, schema v4. The SQLite comparison corpus was built by the same
pipeline against the same two sources; the verifier copies it before opening
it so the evidence file is never migrated or modified in place.

## Result

- `ok: true`, `parity.equal: true`, `repeat_ingest.unchanged: true`.
- PostgreSQL: 1090 cards, 1539 topics, 0 translations, 0 events, 465 audit rows.
- SQLite: 1090 cards, 1539 topics, 0 translations, 0 events, 453 audit rows.
- 982 HTML Help topics + 557 User Guide topics, all `converted`.
- 449 `topic_merged` decisions; no duplicate card content signatures, no
  duplicate topic keys, no orphan translations, every card has a topic, every
  stored hash is sha256, every topic URL is on `https://docs.oracle.com/`.
- The second ingestion added no cards, topics or translations; it only recorded
  its own run bookkeeping (`audits` 465 → 469).

Audit totals differ between the engines because PostgreSQL was ingested twice
during recovery testing and SQLite once. Corpus-affecting audit facts
(`topic_merged`, failures) are compared exactly; run bookkeeping is reported
separately, as implemented in `tools/knowledge_corpus_verify.py`.

## Partial-run recovery

`partial-run-user-guide.json` records a deliberately interrupted User Guide
run: 557 topics discovered, 30 converted, process stops. `resume-run-user-guide.json`
records the continuation: 0 newly discovered, 527 converted, 0 failed. The
combined 557 topics equal the authoritative total and no duplicate card was
produced.

## Multilingual inventory

`translation-coverage.json` measures the committed evidence corpus
(`cubi-knowledge-v26.sqlite3`), which carries the nine `cubi_authored` seed
records:

- 1030 cards × 9 target locales = 9270 slots.
- 9 filled, 0 published, 0 approved, 9261 missing → 0.10 % filled.
- Every seed record is `translated` / `pending`; `answerable` is 0 for every
  locale, so no seed translation may answer as published content.
- The live PostgreSQL corpus has 0 translation records: the ingestion pipeline
  never fabricates translations, and no English text is silently relabelled.

`retrieval-evidence.json` is the eight-language probe against the committed
corpus after publishing the real "Create a project" card. All eight questions
return `kind: answer`, the correct `response_language`, `direction` (`rtl` for
fa/ar, `ltr` otherwise), and the official source URL. Non-English answers report
`fallback_used: true` with `translation_status: translated` because the seed is
not approved; the citation therefore keeps the reviewed English source title.
The unpublished probe shows `missing` for a reader and `unpublished` for a
reviewer, with zero citations in both cases.

## Source-registry discrepancy (recorded, not invented)

The mission text refers to "17 registered source identifiers". This repository
contains:

- 5 `SourceDefinition` entries in `src/construction_pm/knowledge/sources.py`
  (2 ingestable, 2 alternate/landing, 1 documentation home);
- 6 audited identifiers in `source-audit.json` (982 + 557 authoritative,
  988 and 527 alternates not ingested, 2 landing pages);
- 21 distinct official pages listed in `docs/workspace/reference/oracle-p6-reference-index.md`.

No file defines 17 identifiers. The verification therefore reports the actual
registry and does not claim a 17-source inventory.

## Remaining blockers

- Translation coverage is 0.10 % and 0 published/approved records. Producing
  real translations requires an authorized human translation workflow; the
  repository must not fabricate them or call an external AI.
- Publishing the branch and opening the PR requires a GitHub credential. The
  temporary credential used for PR #1839/#1842 was deliberately deleted; if no
  credential is available the delivery is `BLOCKED_EXTERNAL` and the exact
  commands are left in the final report.

## Next concrete action

Authorize a reviewer identity, approve and publish the nine seed translations
(or replace them with human-reviewed text), then re-run
`tools/knowledge_corpus_verify.py` and
`translation_coverage()` to move `answerable` above zero; use the PR checklist
in `docs/architecture/CUBI_KNOWLEDGE_AGENT1_INTEGRATION_CONTRACT.md` for the
Agent 1 handoff.
