# V27 Dialog and Field Matrix — Activities Workspace

- Tested head: `b71cd61f46ebe358d1b15eee21068977b03493cf`
- Inventories: `docs/workspace/architecture/workspace-dialog-inventory.md`,
  `workspace-form-field-inventory.md`; runtime DOM in `apps/web/src/workspace-dialogs.ts`
  and `workspace-desktop-shell.ts`.
- Rule: no enabled-looking control without effect. Every unavailable service is
  shown as unavailable with a reason.

Statuses: **مطابق و تأییدشده** · **پیاده‌سازی‌شده ولی آزمون‌نشده** · **ناقص** · **غایب** · **VERIFY**

| Dialog | Key fields / controls | Persistence / service | Status | Evidence |
|---|---|---|---|---|
| Columns | Available and selected lists, subject filter, add/remove, add all/remove all, width, title, alignment, visibility, pin/freeze, Copy From, OK/Cancel | Project layout via `/p6/layouts/project/activity`, revision guarded | **مطابق و تأییدشده** | `activity-columns-v26` 11/11, `field-chooser-v26` 4/4, `activity-percent-complete-v27` |
| Filters | Filter list (built-in + saved), Any/All, parameter rows, Is operator, Value, high value for ranges, add/delete/reorder, preview count, apply, save, clear | Presentation-local + project presentation persistence; no schedule write | **مطابق و تأییدشده** | `activity-filters-v26`, `workspace-activity-filters.test.ts` |
| Group and Sort | Ordered group levels (`group.field.N`, direction), sort levels, WBS bands, none | Project presentation; restored after reload | **مطابق و تأییدشده** | `activity-group-sort-v26`, `layout-selector-v26` |
| Timescale | Day / Week / Month / Quarter / Year, zoom, fit | Presentation; persisted | **مطابق و تأییدشده** | `gantt-options-v26`, `gantt-fit-v26` |
| Bar Styles | Bar type, color, label layout, filters | Presentation; persisted | **مطابق و تأییدشده** | `gantt-bar-styles-v26` |
| Table Font and Row | Font family/size, row height, colors | Presentation; persisted | **مطابق و تأییدشده** | `activity-table-font-v26` |
| User Preferences | Locale, theme, calendar display, presentation density | Browser-local + presentation; survives reload | **مطابق و تأییدشده** | `workspace-desktop-shell.test.ts`, `toolbars-v26` |
| Layout selector (open/new/save as/import/export) | Layout name, dirty chip, Save / New / Reset / Import / Export, viewer read-only | Layout API, revision guarded; one layout per project/view (server limit) | **مطابق و تأییدشده** with documented limit | `layout-selector-v26` 15/15, `layout-trace-v26` |
| General activity editor | Name, Activity Type (6), Duration Type (4), Percent Complete Type (4), Leveling Priority (5), Cost Account, revision hint, Save/Cancel | `PATCH /p6/activities/{id}` with `expected_revision`; grid + Gantt re-read after save | **مطابق و تأییدشده** (V27) | `activity-general-edit-v26` at `b71cd61f4`: gridRefresh true, persisted after reload, restore clean |
| Customize Activity Details | 17 tab checkboxes, reset, apply | Browser-local tab visibility | **مطابق و تأییدشده** | `activity-details-v26` customize checks |
| Collapse To | Level selector (WBS level / all) | Presentation | **مطابق و تأییدشده** when grouped | `activity-wbs-collapse-v26` |
| Project properties | Project ID, name, dates, date system, calendar | Project API, revision guarded | **پیاده‌سازی‌شده ولی آزمون‌نشده** in V27 re-run | `project-details-v26`, `project-status-v26` |
| Project Status | Status, leveling priority, critical threshold | Project API, revision guarded | **پیاده‌سازی‌شده ولی آزمون‌نشده** | `project-status-v26` |
| Import / Export | Source file, target, preview, confirm | Interchange service | **پیاده‌سازی‌شده ولی آزمون‌نشده** | `exchange-v26` |
| Print / Print preview | Layout selection, browser dialog | Browser print; no server render | **پیاده‌سازی‌شده ولی آزمون‌نشده** | `workspace-shell-v26` route |
| Forms & Workflows | Form list, fields, submit | Forms service | **پیاده‌سازی‌شده ولی آزمون‌نشده** | `form-builder-e2e`, `workspace-forms` unit |
| Search activities | Search term, field scope, next/previous | Client-side over the read model | **مطابق و تأییدشده** | `workspace-shell-v26`, `activity-grid-keyboard-v26` |
| Keyboard shortcuts | Grouped shortcut list with reasons | Static registry | **مطابق و تأییدشده** | `workspace-desktop-shell.test.ts` |
| About CUBI Workspace | Product, version, environment | Static | **مطابق و تأییدشده** | shell tests |
| Assign Resources | Resource picker, units/time, curve, cost | Assignment API | **پیاده‌سازی‌شده ولی آزمون‌نشده** | `assignments-v26`, `resources-v26` |
| Assign Predecessor / Successor | Activity picker, relationship type, lag | Relationship API | **پیاده‌سازی‌شده ولی آزمون‌نشده** | `activity-relationships-v26` |
| UDF Values | Per-UDF typed controls | UDF API | **پیاده‌سازی‌شده ولی آزمون‌نشده** | `activity-udf-values-v26` |
| Backup / Recovery | Backup list, restore confirm | Backup service | **پیاده‌سازی‌شده ولی آزمون‌نشده** | `backup-v26` |
| Activity Codes assignment | — | **No HTTP route** | **غایب** (contract gap) | `backend-contract-matrix.md` R4 |
| Notebook topic editor | — | **No persistence service** | **غایب** (contract gap) | R5 |
| Step editor | — | **No write route** | **غایب** (contract gap) | R6 |
| Document link picker (per activity) | — | **No link route** | **غایب** (contract gap) | R7 |

## Field-level notes

- The General editor is prefilled from the authoritative Activity Master record,
  states the loaded revision, sends only changed fields, and surfaces a 409 as a
  conflict rather than overwriting.
- Enum catalogs are read from the domain, not hard-coded in the browser:
  Activity Type 6, Duration Type 4, Percent Complete Type 4, Leveling Priority 5.
- The Columns dialog lists `activity.percent_complete_type` with the persisted
  project layout; the column becomes visible after OK and survives a reload
  (`activity-percent-complete-v27`).

## Not verified

- A real 409 from the preview runtime (conflict handling is unit-tested; the suite
  does not provoke a concurrent edit).
- Vendor Help field labels for the four contract-gap dialogs (Help 403).
