# Version 26 source status — 2026-11-12

Contract: `cubi-knowledge-provenance.v1`
Branch: `feature/cubi-knowledge-assistant-v1`
Base commit: `fe3f55c66de3570cdddf199fa0c997a4441420fd`
Artifacts: `cubi-knowledge-v26.sqlite3`, `coverage.json`,
`ingestion-report.json`, `ingestion-summary.json`, `ingest.log`,
`provenance-summary.json`, `assistant-smoke.json`.

`ingestion-summary.json` records the completed live totals.
`ingestion-report.json` and `ingest.log` are from the idempotent re-run
(0 new pages), which verifies resumability rather than re-conversion.
`assistant-smoke.json` publishes two real cards **in a disposable copy** and
proves grounded English/Persian answers, a knowledge gap, Smart Guide progress
and audit events. The central evidence database itself remains all-draft.

## Ingested sources

| Source | Official URL | Discovered | Converted | Failed | Mandatory areas |
| --- | --- | ---: | ---: | ---: | ---: |
| `p6-26-help` | `https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-help/toc.htm` | 988 | 988 | 0 | 31/31 |
| `p6-26-user-guide` | `https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/toc.htm` | 527 | 527 | 0 | 29/31 |
| `p6-26-html-help` | `https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm` | 982 | 982 | 0 | 31/31 |

Totals: **2,497 topics converted, 0 failed, 2,497 draft cards, 438,910 words**.
All topics carry a 64-character content hash and a source URL. No duplicate
topic keys, duplicate card ids or cards without provenance were found. No card
is published or human-reviewed; ingestion produces structurally validated drafts.

The user guide covers 29 of 31 mandatory areas on its own. Its "Managing
Projects" and "Project Management" wording complements the help and legacy
sets, so the combined corpus covers 31/31. Coverage is computed from official
topic titles, not from inferred content.

## Registered but non-ingestable sources

| Source | URL | Reason |
| --- | --- | --- |
| `p6-26-books` | `books.html` | Documentation index; no per-topic table of contents |
| `p6-26-docs-home` | Version 26 documentation home | Landing page; no per-topic table of contents |

## Supplementary PDF

| Artifact | Status | Detail |
| --- | --- | --- |
| 815-page Version 26 PDF | **MISSING / VERIFY** | Not present in the workspace or repository during this run. No page was extracted, converted or cited. Its absence must be resolved before claiming PDF coverage. |

## Extraction quality checks

- The parser retains chapter/section ordinals out of titles; the official TOC
  title is authoritative for topics such as "Title and Copyright Information".
- Sub-headings rendered as `p.subhead1/2` are promoted to section headings.
- Stub pages with no body text produce an explicit limitation. **192** cards
  state that no body content was available; they are not presented as
  procedures. **1,478** cards contain extracted steps.
- Card types: operation 1,438; concept 726; configuration 206; relationship 60;
  training 36; reference 25; workflow 4; troubleshooting 2.
- Language detection reports `en` for all 2,497 official topics. Persian/Arabic
  query normalization and RTL-ready responses are handled at search/assistant
  level, not by translating source content.

## Reproducing the run

```bash
python tools/ingest_v26_help.py \
  --db docs/workspace/evidence/knowledge-v26-2026-11-12/cubi-knowledge-v26.sqlite3 \
  --delay 0.02 --fetch-workers 10 \
  --coverage-out docs/workspace/evidence/knowledge-v26-2026-11-12/coverage.json \
  --report-out docs/workspace/evidence/knowledge-v26-2026-11-12/ingestion-report.json
```

Re-running is idempotent: discovered topics are not duplicated, converted pages
are skipped unless `--force` is supplied, and the source status is updated to
`converted` only when no topic remains outstanding.
