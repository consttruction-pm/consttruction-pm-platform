# V28 Deviation Register

| ID | Deviation | Type | Evidence | Owner / next action |
|---|---|---|---|---|
| D-V28-01 | PDF "hot keys" are two-step menu accelerators (`Alt-F, N`); CUBI has menu access keys and Ctrl shortcuts but no two-step dispatcher | Keyboard gap | `menu-toolbar-shortcut-audit.md` §4 (PDF p13–15) | Implement after #1716/#1711 merge; add a test per sequence |
| D-V28-02 | The Reports toolbar family is declared but has no buttons | UI gap | menu/toolbar audit §2 | Populate or remove the family |
| D-V28-03 | PDF defines 18 toolbar families; CUBI has 11 declared families / 57 buttons | Visual/functional gap | menu/toolbar audit §2 (PDF contents p ii, 46–78) | Map families; mark unsupported commands unavailable |
| D-V28-04 | Activity Codes, Notebook, Steps and per-activity Document links still have no HTTP write contract | CONTRACT/API GAP | Details audit §1, §4; V27 backend matrix R4–R7 | Platform: define contracts; then wire Add/Modify/Delete as the PDF requires (Steps p63–64, Notebook p67) |
| D-V28-05 | Curtain/text attachments and notebook-on-bar attachments are not implemented | Functional gap | table/Gantt matrix §2 (PDF p16–19) | Needs a data model; owner decision |
| D-V28-06 | Official HTML Help still returns 403 | Reference BLOCKED | baseline §2.1, re-fetched 2026-11-18 | Use the attached PDF (now verified) until HTML access is restored |
| D-V28-07 | Theme acceptance is 1366×768 only | Coverage gap | theme-acceptance.md §Limits | Add 1280/1920 per skin if required |
| D-V28-08 | Dark-skin row background fix touches shared `styles.css` and `public/styles.css` | Shared-file disclosure | theme-acceptance.md | Coordinate with #1716/#1711/#1983 |
| D-V28-09 | No pixel-level vendor comparison | Scope limitation | visual fidelity V27 | Obtain lawful reference captures if required |
| D-V28-10 | 409 conflict is unit-tested only | Coverage gap | general-edit suite notes | Provoke with two sessions in a future run |
| D-V28-11 | Per-row comparison of all 264 PDF topics is not complete | Audit progress | pdf-topic-inventory.md | Continue chapter by chapter; the inventory and key matrices exist |

## Fixed in this stage (not deviations)

- Blank values under `not-equals`/`not-contains` now match, enabling the exact PDF
  lookahead recipe (was 0/14, now 10/14).
- Filter parameter label "Activity % Complete" matches the PDF.
- Dark skins no longer render light text on white rows; measured contrast
  Graphite 13.65:1, Midnight 14.14:1.
