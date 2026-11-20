# V28 Activity Details and Dialog Audit (PDF-backed)

- PDF: G57535-02, October 2026. Printed page numbers below are from that file.
- HTML Help: HTTP 403 (BLOCKED).
- Code inspected: `workspace-activity-details.ts`, `workspace-activity-general.ts`, `workspace-dialogs.ts`, filter/layout services.

## 1. Activity Details tabs

The PDF does not print a single 17-tab list; it documents tab behavior inside the
relevant tasks. The CUBI tab set remains the project's list, now checked against
the behavior the PDF requires.

| Tab | PDF evidence (printed page) | Required behavior from PDF | CUBI status | Gap |
|---|---|---|---|---|
| General | Activity types 5; duration types 6; percent types 7; calendar 7; duration 8; dates 9 | Six activity types, four duration types, four percent types, calendar and dates | **مطابق و تأییدشده** | — |
| Status | Activity dates 5; float 13; summaries 14 | Show start/finish/actual/early/late/float | **مطابق و تأییدشده** | — |
| Resources | Assigning resources and roles 25+ | Resource assignments and units/time | **پیاده‌سازی‌شده ولی آزمون‌نشده** | Full assignment dialog not re-run in V28 |
| Predecessors | Add predecessor 18; change 20; remove 22 | List/edit/remove predecessors | **مطابق و تأییدشده** (read + relationship service) | — |
| Successors | Add successor 18; change 20; remove 23 | List/edit/remove successors | **مطابق و تأییدشده** | — |
| Relationships | Relationship types 17; view 23–24 | FS/SS/FF/SF with lag | **مطابق و تأییدشده** | — |
| Codes | Activity codes and values 22; assign 22; change 23 | Assign/change code values | **ناقص** | No HTTP assignment route (R4) |
| Notebook | Add notebook 67; remove notebook 67 | Add/Delete notebook topics, HTML-capable text | **ناقص** | No persistence service (R5) |
| Steps | Add steps 63; update 64; weights 64–65; delete 65–66 | Add, Modify (HTML description), move, delete, weights, % complete | **ناقص** | Read-only route; repository upsert not exposed (R6) |
| WPs & Docs | Assign 57; remove 58; open 60; details 61 | Link/unlink work products and documents | **ناقص** | No link route (R7) |
| Expenses | Add 56; categories 58; delete 60 | Add/delete expenses | **پیاده‌سازی‌شده ولی آزمون‌نشده** | Prior suite; not re-run in V28 |
| Issues | Not enumerated as a Details tab in the PDF pages inspected | — | **ناقص / VERIFY** | Risk/issue write contract |
| Risks | Professional-only feature per source register; not reached in this pass | — | **ناقص / VERIFY** | Write path absent |
| Summary | View activity summaries 14 | Aggregated summary | **مطابق و تأییدشده** (read) | — |
| UDFs | User-defined fields (Enterprise) 3.x / Steps UDF 63 | Typed UDF values | **پیاده‌سازی‌شده ولی آزمون‌نشده** | Not re-run |
| Update History | Progress update topics 6.x | Stored history | **مطابق و تأییدشده** (read) | — |
| Calendar (CUBI) | Edit a project calendar 3.x; activity calendar 7 | Calendar assignment and exceptions | **مطابق و تأییدشده** as a CUBI extension | — |

The PDF page 1 (PDF 195) mentions **Feedback** only "when connected to a P6
Professional database", and the Tasks tab appears in Team Member/EPPM contexts
(printed pages around 746 of the PDF). Neither is a desktop Activities tab in the
pages inspected. The earlier Tasks/Discussion/Feedback discrepancy is therefore
resolved as **edition boundary**, not as missing CUBI tabs.

## 2. Dialogs

| Dialog | PDF page | Required controls | CUBI status |
|---|---:|---|---|
| Customize Activity Details | 5 (ch7) | Available/Display tabs, add/remove, add all/remove all, move left/right, Apply/OK | **مطابق و تأییدشده** (17 tabs, keyboard, persistence) |
| Columns | 6 (ch7) | Select columns, width, title, alignment, visibility | **مطابق و تأییدشده** (11/11) |
| Filters | 9–10 (ch9) | Categories, All/Any, rows, Add/Delete, Parameter/Is/Value/High, Apply preview, Replace/Highlight, New/Delete | **مطابق و تأییدشده** (14/14) |
| Lookahead | 10 (ch9) | Start within CD…CF+6w; Activity % Complete != 100; Save + Apply | **مطابق و تأییدشده** (new exact test this stage) |
| Group and Sort | 1–2 (ch9) | Group by field/hierarchy/WBS path; sort; bands | **مطابق و تأییدشده** |
| Timescale | 9 (ch7) | Format and display timeperiod | **مطابق و تأییدشده** |
| Bar Styles / labels / settings | 14 (ch7) | Bar filter, label, style, timescale | **مطابق و تأییدشده** |
| Data date line | 13 (ch7) | Show/style data date | **مطابق و تأییدشده** |
| Progress Line | 19 (ch7) | Apply progress line | **مطابق و تأییدشده** |
| Table font/color/row height | 8 (ch7) | Font, color, row height | **مطابق و تأییدشده** |
| Activity Network layout | 20–23 (ch7) | Box layout, fonts, navigation | **پیاده‌سازی‌شده ولی آزمون‌نشده** |
| Trace Logic | 24+ (ch7) | Preferences and navigation | **پیاده‌سازی‌شده ولی آزمون‌نشده** |
| Activity Usage Profile/Spreadsheet | 25+ (ch7) | Display profile/spreadsheet | **پیاده‌سازی‌شده ولی آزمون‌نشده** |

## 3. Concrete defects found and fixed in this stage

| Defect | Impact | Fix | Test |
|---|---|---|---|
| `not-equals` / `not-contains` rejected blank stored values | The exact PDF lookahead recipe (`Activity % Complete is not equal to 100`) matched 0 of 14 activities because not-started activities have no stored percent | Negative criteria now treat a blank value as satisfying the criterion; positive criteria still require a value | New unit test + `activity-lookahead-v28` (10/14 matched, reload, no schedule writes) |
| Filter parameter label said "Progress %" | Terminology differed from the PDF's "Activity % Complete" | Label changed in both locales | `activity-lookahead-v28` asserts the label |

## 4. Remaining work owned by backend contracts

Codes (R4), Notebook (R5), Steps (R6), WPs & Docs (R7) and Risks need real HTTP
contracts. The PDF requires Add/Modify/Delete and persistence for Steps and
Notebook; implementing client-only state would violate the no-mock rule. These
are recorded as **ناقص** with a precise next action rather than simulated.
