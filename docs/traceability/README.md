# CUBI — Environment ↔ official Help traceability (P1)

This directory is the canonical P1 traceability evidence for Issue #2069. It maps
**every CUBI page** to the official Help baseline of its environment, and maps
each row to the CUBI implementation evidence that backs the claim.

| Environment | Official Help baseline | Baseline identifier |
|---|---|---|
| CUBI Engineering | P6 Professional **V26 HTML Help** + the **815-page V26 Help PDF** | HTML: `https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm` · PDF: `G57535-02`, October 2026, 815 pages |
| CUBI Enterprise | P6 EPPM **V26 HTML Help** | `https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm` · `G48897-01`, May 2026 (HTML only; no page-numbered PDF baseline) |

## Files

| File | Role |
|---|---|
| `engineering-v26.json` | Single source of truth for CUBI Engineering rows (25 public routes + 42 workspace windows). |
| `enterprise-v26.json` | Single source of truth for CUBI Enterprise rows (16 pages across the eight canonical modules). |
| `CUBI_ENGINEERING_V26_TRACEABILITY.md` | Generated per-page matrix; do not edit by hand. |
| `CUBI_ENTERPRISE_V26_TRACEABILITY.md` | Generated per-page matrix; do not edit by hand. |
| `cubi-engineering-v26.csv`, `cubi-enterprise-v26.csv` | Generated spreadsheet exports. |

## Row contract

```json
{
  "id": "ENG-WS-SCHEDULE",
  "environment": "engineering",
  "kind": "workspace_page",
  "page": "/app/schedule/",
  "surface": "Schedule dialog",
  "module": null,
  "help": {
    "source": "P6 Professional V26 HTML Help",
    "title": "Scheduling projects",
    "url": "https://docs.oracle.com/cd/G48902_01/client_help/en_US/scheduling_projects.htm",
    "pdfPage": 287
  },
  "helpRationale": null,
  "cubiBehavior": "Typed schedule options bound to the authoritative snapshot.",
  "evidence": "apps/web/src/workspace-administration.test.ts",
  "status": "IMPLEMENTED"
}
```

Rules enforced by `apps/web/src/traceability.test.ts`:

1. IDs are unique and prefixed by environment.
2. Engineering rows cite a `https://docs.oracle.com/cd/G48902_01/` topic **and** a
   PDF page in `1..815`. Enterprise rows cite a
   `https://docs.oracle.com/cd/G48897_01/p6help/en/` topic and carry no PDF page.
3. Every row has a `cubiBehavior` and a repo-relative `evidence` path that exists.
4. `help` may be `null` only when `status` is `CUBI_OWNED` or `LEGAL`, and the
   `helpRationale` explains why no official topic applies.
5. Every English route in `apps/web/site/routes.mjs` appears exactly once as an
   Engineering public-page row.
6. All eight canonical Enterprise modules are represented.

## Status semantics

| Status | Meaning |
|---|---|
| `PUBLISHED` | Public page ships as content; the Help topic constrains its claims. |
| `IMPLEMENTED` | The product surface is wired and has executable evidence. |
| `PARTIAL` | A wired subset exists; the specific gap is stated in `cubiBehavior`. |
| `PLANNED` | Target design mapped to Help, not yet built. |
| `CUBI_OWNED` | CUBI-only surface; no official Help topic documents it. |
| `LEGAL` | Legal policy page; no product Help topic applies. |

A row is never promoted to `IMPLEMENTED` from a route, mock, schema or document
alone. The evidence path must be executable (test, module, or shipped document).

## No vendor branding in the customer UI

The Help baselines are internal parity references. Customer-facing surfaces must
never display Oracle, Primavera, P6 or EPPM names. This is enforced by the same
test across:

- `apps/web/public/**/*.html` and `apps/web/index.html`;
- `apps/web/site/locales/*.mjs` and `apps/web/src/landing*.ts`.

Internal documents under `docs/` and internal code identifiers may name the
baseline; that is traceability, not product branding.

## Maintenance

1. Edit the JSON file only.
2. Run `node apps/web/scripts/render-traceability.mjs` to regenerate Markdown and CSV.
3. Run `cd apps/web && npm test` — the traceability test fails on schema drift,
   missing evidence, an uncovered route or a branding regression.
