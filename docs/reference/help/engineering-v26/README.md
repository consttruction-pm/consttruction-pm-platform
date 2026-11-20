# Engineering Help reference (V26)

This directory is the durable copy of the Engineering environment's authoritative Help
reference. It is committed so that every session and every agent reads the same file with the
same page numbers — no re-upload, no drift between citations.

| File | What it is |
| --- | --- |
| `P6_PROFESSIONAL_HELP_G57535-02.pdf` | The official 815-page Help PDF, version G57535-02, October 2026 |
| `pages.txt` | Text layer extracted page by page (`\f` between pages), layout preserved |
| `outline.json` | The 988 PDF bookmarks with their 1-based page numbers |
| `index.json` | Per-page heading/chapter map (815 entries) plus the 16 chapter start pages |

## Look things up with the tool

```bash
python3 tools/help_pdf_lookup.py chapters
python3 tools/help_pdf_lookup.py topic "Leveling Resources"
python3 tools/help_pdf_lookup.py search "data date" --limit 5
python3 tools/help_pdf_lookup.py page 271
```

## Rules

1. Every Help citation in `docs/traceability/engineering-v26.json` must resolve to a page in
   `pages.txt` and, when quoted, to a bookmark in `outline.json`.
2. The bookmark outline covers pages up to 520. Pages 521–815 have no bookmarks; cite them by
   page number from `index.json` and quote the heading line, never by an invented anchor.
3. This is a **reference**, not product copy. Never paste Help text into the customer UI, and
   never surface the vendor name, product name or brand in any customer-facing surface.
4. If the PDF is replaced, regenerate `pages.txt`, `outline.json` and `index.json` and update the
   page count assertion in `tests/test_help_reference.py`.

The Enterprise environment uses the HTML Help (`G48897_01`); it has no PDF and is cited by topic
ID and URL only. See `docs/traceability/enterprise-v26.json`.
