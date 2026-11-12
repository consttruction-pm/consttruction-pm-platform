# CUBI Knowledge V26 — source and extraction status

Run date: 2026-11-12 (UTC). Database: `cubi-knowledge-v26.sqlite3`.

## Authoritative sources

Only these two official Version 26 HTML sources are ingestable
(`INGESTABLE_SOURCES` in `src/construction_pm/knowledge/sources.py`):

| Source id | Exact URL | Topics | Converted | Failed |
| --- | --- | --- | --- | --- |
| `p6-26-html-help` | https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm | 982 | 982 | 0 |
| `p6-26-user-guide` | https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/toc.htm | 557 | 557 | 0 |

Both URLs were fetched during the run and returned HTTP 200. No other source
was ingested into this database and no stale or substitute content is present.

## Source audit and the 527/557 User Guide discrepancy

`source-audit.json` (`cubi-knowledge-source-audit.v1`) re-fetches every official
HTML TOC and records its HTTP status, content hash and parsed topic count:

| Official URL | Topics | Role |
| --- | --- | --- |
| `cd/G48902_01/client_help/en_US/toc.htm` | 982 | authoritative, ingested as `p6-26-html-help` |
| `cd/G48902_01/English/User_Guides/p6_pro_user/toc.htm` | 557 | authoritative, ingested as `p6-26-user-guide` |
| `26/pro-help/toc.htm` | 988 | official alternate edition, not ingested |
| `26/pro-user/toc.htm` | 527 | official alternate edition, not ingested |
| `26/` and `26/books.html` | landing pages | linked from the registry, no topics ingested |

The earlier 527 and 557 counts are therefore both real but describe **different
official TOCs**. The earlier evidence database used `pro-user/toc.htm` (527);
this branch uses the G48902 `p6_pro_user/toc.htm` (557). The source id
`p6-26-user-guide` maps only to the G48902 edition, so the two topic sets are
never mixed under one id. The alternate TOCs remain audited and are not claimed
as ingested.

## Extraction and merge result

- 1,539 topics discovered and converted, 0 failures.
- Every topic keeps its own `source_id`, `topic_key`, exact `url`, breadcrumb,
  headings, steps, prerequisites, warnings, limitations and relations.
- 509 topics in the User Guide are byte-equivalent (page basename plus
  normalized substantive content) to an existing HTML Help card. Those topics
  are recorded as `topic_merged` audit events and point at the canonical card,
  so the same procedure is stored once while both official URLs remain in the
  topic records as provenance.
- 48 User Guide topics are unique and produced their own cards.
- 1,030 unique cards are retained (982 from HTML Help + 48 unique User Guide).
- `coverage.json` reports 31/31 mandatory areas covered by HTML Help and 29/31
  by the User Guide alone. The two missing User Guide areas — "Working with
  Toolbars and Menus" and "Working with Projects" — are covered by HTML Help;
  they are not claimed as present in the User Guide.

## Honest publication state

- Card publication status in this evidence database: 1,030 `draft`, 0
  `validated`, 0 `published`, 0 `rejected`, 0 `retired`.
- Nine non-English locales have seed translations in `translations.py` format
  (`fa`, `de`, `zh-CN`, `zh-TW`, `ar`, `fr`, `ja`, `ko`, `ru`), all with
  `translation_status=translated` and `review_status=pending`. English is the
  source locale (`draft`).
- No draft or machine-produced translation is marked approved or published in
  this database. `seed-report.json` records the seed result and
  `translation-matrix.json` the per-locale status.
- `assistant-smoke.json` was produced from a **disposable copy** of this
  database. In that copy only the flagship card and its Russian translation
  were approved and published, to exercise the published path end to end.
  That publication is not present in the evidence database.
- All other locales answered through the honest fallback path: response text in
  the requested language with the unapproved-translation notice, the official
  English content marked as the source, and `fallback_used=true`.

## Artifacts

- `ingestion-report.json` — per-source discovered/processed/converted/skipped/
  failed counts and mandatory-area coverage.
- `coverage.json` — `cubi-knowledge-coverage.v1` report for the two ingestable
  sources.
- `source-audit.json` — `cubi-knowledge-source-audit.v1` live audit of every
  official TOC and landing page, with hashes, counts and the 527/557 resolution.
- `translation-matrix.json` — `cubi-knowledge-translation-matrix.v1` per-locale
  card content, translation/review status, version and hash.
- `assistant-smoke.json` — `cubi-multilingual-assistant-smoke.v1` answers for
  all ten locales, Russian Smart Guide, Russian and Persian workflow starts, and
  ten localized searches with retrieval evidence.
- `seed-report.json` — translation seed outcome.
- `ingest.log` — resumable extraction log.
- `cubi-knowledge-v26.sqlite3` — the draft evidence database.

## Reproduction

```bash
python3 tools/ingest_v26_help.py \
  --db docs/workspace/evidence/knowledge-multilingual-v26-2026-11-12/cubi-knowledge-v26.sqlite3 \
  --coverage-out docs/workspace/evidence/knowledge-multilingual-v26-2026-11-12/coverage.json \
  --report-out docs/workspace/evidence/knowledge-multilingual-v26-2026-11-12/ingestion-report.json

python3 tools/knowledge_multilingual_evidence.py \
  --db docs/workspace/evidence/knowledge-multilingual-v26-2026-11-12/cubi-knowledge-v26.sqlite3 \
  --out docs/workspace/evidence/knowledge-multilingual-v26-2026-11-12 \
  --copy-db /tmp/cubi-multilingual-smoke.sqlite3

python3 tools/knowledge_source_audit.py \
  --db docs/workspace/evidence/knowledge-multilingual-v26-2026-11-12/cubi-knowledge-v26.sqlite3 \
  --out docs/workspace/evidence/knowledge-multilingual-v26-2026-11-12/source-audit.json
```

The evidence tools never write credentials and never create projects in the
main evidence database.
