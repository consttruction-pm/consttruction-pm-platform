# Official Help baseline — verified inventory

Verified: 2026-11-21
Verified by: `python scripts/verify_help_traceability.py`
Result: **84 / 84 traceability rows verified**, 0 failures.

This page records the official documentation baseline used by every
specification in this directory. It is evidence, not a substitute for reading
the topic: each section document cites the exact topic and the behavior it
describes.

## 1. Baselines

| Environment | Document | Identifier | Entry point |
| --- | --- | --- | --- |
| CUBI Engineering | P6 Professional **V26 HTML Help** | `G48902-01`, October 2026 | <https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm> |
| CUBI Engineering detail | P6 Professional **V26 User Guide** | `G57529-01`, 9 October 2026 | <https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/toc.htm> |
| CUBI Enterprise | P6 EPPM **V26 HTML Help** | `G48897-01`, May 2026 | <https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm> |

The HTML Help Table of Contents is the mandatory reference. The 815-page Help
PDF (`G57535-02`) is cited by `docs/traceability` for page numbers only; it is
never used instead of an HTML topic. No third-party tutorial, screenshot,
stale PDF or memory is accepted as a reference.

## 2. What was parsed and checked

| Check | Engineering | Enterprise |
| --- | --- | --- |
| TOC reachable (`HTTP 200`) | yes | yes |
| Topics discovered in the TOC | 982 | 823 |
| Traceability rows checked | 68 | 16 |
| Rows with a Help URL | 68 | 16 |
| URL returns `HTTP 200` | 68 | 16 |
| URL listed in the official TOC | 68 | 16 |
| Recorded title matches the topic title | 68 | 16 |

Fifteen further rows across the two files are intentionally without a Help
topic (`CUBI_OWNED` or `LEGAL`) and carry a written rationale; they are not
counted as Help rows.

The User Guide TOC (`toc.htm`, JavaScript-rendered shell with a static topic
list) exposes 525 topic pages with stable slugs such as
`theganttchart-19631a.html`. A direct User Guide URL is cited only after that
page returned `HTTP 200` and its `<title>` matched the cited section.

## 3. Method

```bash
python scripts/verify_help_traceability.py \
  --out docs/quality/help-traceability/evidence/help-link-verification-2026-11-21.json
```

For each row the script:

1. loads `docs/traceability/engineering-v26.json` or
   `enterprise-v26.json` (the canonical page↔Help index owned by the
   traceability workstream);
2. parses the official `toc.htm` for that environment and builds a
   `URL → title` map;
3. requests the row URL and requires `HTTP 200`;
4. requires the URL to be present in the official TOC;
5. compares the recorded title with the page `<title>`, allowing the product
   name suffix that the official page appends.

A row fails on `NO_HELP_URL`, `NOT_IN_OFFICIAL_TOC`, `HTTP_<status>`,
`TITLE_MISMATCH` or `UNREACHABLE`. The machine report in `evidence/` records
every row, its TOC title, page title and status.

## 4. Source-of-truth boundaries

- `docs/traceability/*.json` owns row identity, page route, status and CUBI
  implementation evidence.
- `apps/web/src/traceability.test.ts` enforces that contract (unique IDs,
  route coverage, existing evidence paths, no vendor branding in the customer
  UI).
- This directory adds behavior specifications and acceptance scenarios on top
  of those rows. It does not duplicate or renumber them.

## 5. Known limits

- The baseline documents P6 Professional and P6 EPPM. A CUBI-only surface (for
  example the AI Workbench) has no official topic and is marked
  `NO DIRECT P6 HELP EQUIVALENT — CUBI-SPECIFIC REQUIREMENT`.
- A Help topic describes the vendor behavior, not CUBI's implementation. Every
  row separates `Expected behavior` (from Help) from `CUBI status` (observed in
  this repository and named evidence).
- Topic titles can be generic. The section documents therefore name the
  subsection (for example "Customizing Activity Layouts → Add a column") rather
  than only the page title.
- Oracle can revise a topic. The verification report is dated and must be rerun
  when a section is added or a URL changes.
