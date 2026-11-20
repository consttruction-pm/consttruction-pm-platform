# V30 — HTML topic disposition

## Attempts against the mandated edition

| Attempt | Command | Result |
|---|---|---|
| 1 | `curl -L https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-help/index.html` | **HTTP 403**, final URL unchanged |
| 2 | Same URL with a desktop Chrome 131 user agent | **HTTP 403** |
| 3 | HTML Help index from the previous edition (`https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm`) | **HTTP 403** (re-checked) |

No page content, navigation tree or anchor was received. Nothing was inferred from the URL
shape, the product name or an older edition.

## Consequence

The PDF of the same edition (G57535-02, October 2026, 815 pages) is the only readable
reference. Every V30 topic was read from the PDF with printed page numbers recorded in
`reference-traceability.md`. The HTML column is therefore **blocked**, not silently
“matched”.

## Topics that would use HTML anchors when access is available

- Gantt attachments: “Add a curtain attachment in a Gantt Chart”, “Add a text attachment to a
  Gantt Chart”, “Attach notebook items to bars in a Gantt Chart”.
- Edit commands: “Delete an activity”, “Dissolve an activity”, “Copy and paste activities in the
  Activity Table”, “Cut and paste activities in the Activity Table”.
- Toolbar/menu reference: the Edit toolbar and Menu reference tables (printed pages 58–59 of 93).

## Verification policy

A topic is marked `confirmed` only when a real test exercised the CUBI behaviour. A 403 HTML
reference never upgrades a topic by itself. The full status table is
`pdf-topic-disposition.md`; the blocking evidence is this file.
