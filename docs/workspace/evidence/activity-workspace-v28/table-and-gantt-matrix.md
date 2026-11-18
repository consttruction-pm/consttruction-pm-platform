# V28 Activity Table and Gantt Matrix (PDF-backed)

- PDF: G57535-02; pages are printed pages in Chapter 7 unless noted.
- Status vocabulary: **مطابق و تأییدشده** · **پیاده‌سازی‌شده ولی آزمون‌نشده** · **ناقص** · **غایب** · **محدودیت مستند و مشخص**.

## 1. Activity Table

| Capability | PDF page | CUBI implementation | Status | Evidence |
|---|---:|---|---|---|
| Grid/table display and purpose | 6 | `#cp-activity-grid` from the read model | **مطابق و تأییدشده** | columns 11/11, visual acceptance |
| Define columns (select, order, width, title, alignment, visibility) | 6 | Columns dialog + persisted layout | **مطابق و تأییدشده** | `activity-columns-v26`, `field-chooser-v26`, `activity-percent-complete-v27` |
| Change activity information in the table | 8 | General editor writes through the revision-guarded API and re-reads the project | **مطابق و تأییدشده** | `activity-general-edit-v26` |
| Sort activity information | 8 | Sort levels in Group and Sort; reverse sort | **مطابق و تأییدشده** | `activity-group-sort-v26`, layout selector |
| Group row fonts/colors and grouping bands | 8 | WBS band colors from presentation; expand/collapse | **مطابق و تأییدشده** | `activity-wbs-band-v26`, visual acceptance |
| Table font, color, row height | 8 | Table Font and Row dialog, persisted | **مطابق و تأییدشده** | `activity-table-font-v26` |
| Line numbers | 5 | Toggleable, first column, applies to grids; heading `#` | **مطابق و تأییدشده** | `activity-columns-v26`, `activity-table-font-v26` |
| Filtering | ch9 p1–10 | Filters dialog + saved filters | **مطابق و تأییدشده** | `activity-filters-v26` 14/14, `activity-lookahead-v28` |
| Selection / multi-selection | ch2 p9 | Shift/Ctrl, roving focus | **مطابق و تأییدشده** | `activity-multi-select-v26`, `activity-grid-keyboard-v26` |
| Layout save/restore | 1–3 | Layout API, revision guarded | **مطابق و تأییدشده** with one-layout-per-project limit | `layout-selector-v26`, `layout-trace-v26` |

## 2. Gantt

| Capability | PDF page | CUBI implementation | Status | Evidence |
|---|---:|---|---|---|
| Gantt display and navigation | 9–10 | `#cp-gantt`, scroll sync with table | **مطابق و تأییدشده** | `gantt-scroll-sync-v26`, visual acceptance |
| Timescale format / display period | 9 | Day/Week/Month/Quarter/Year + zoom | **مطابق و تأییدشده** | `gantt-options-v26`, `gantt-fit-v26` |
| Add/change bars, apply settings | 11–12 | Bar Styles dialog, persisted presentation | **مطابق و تأییدشده** | `gantt-bar-styles-v26` |
| Background lines, legend, relationship lines | 12–13 | Presentation toggles | **مطابق و تأییدشده** | `activity-gantt-overlays-v26` |
| Data date line | 13 | Vertical line + label | **مطابق و تأییدشده** | overlays, visual acceptance |
| Bar filter / label / settings / style / timescale | 14–15 | Bar Styles editor | **مطابق و تأییدشده** | `gantt-bar-styles-v26` |
| Move to activity, change dates/duration in Gantt | 15–16 | Selection sync; direct scheduling edits are not offered from the browser (no second engine) | **محدودیت مستند و مشخص** | `gantt-scroll-sync-v26`; schedule edits go through the API |
| Curtain/text attachments, notebook-to-bar attachments | 16–19 | Not implemented | **غایب** | Beyond current Activities data model |
| Progress line | 19 | Optional progress line | **مطابق و تأییدشده** | `activity-gantt-overlays-v26` |
| Activity Network | 20–23 | Network view with navigation/preferences | **پیاده‌سازی‌شده ولی آزمون‌نشده** | `activity-network-v26` |
| Activity box layout, fonts/colors | 23 | Network box presentation | **پیاده‌سازی‌شده ولی آزمون‌نشده** | `activity-network-v26` |
| Trace Logic | 24+ | Trace logic view | **پیاده‌سازی‌شده ولی آزمون‌نشده** | `activity-trace-logic-v26` |

## 3. Integration rules

- Table and Gantt read the same activity rows and the same stored schedule facts;
  there is no browser scheduling engine.
- Selection, grouping bands, collapse state and row heights stay aligned
  (`rowHeightMismatch: 0`, `firstRowOffset` equal in visual acceptance).
- Editing in Details re-reads the project so both surfaces show the saved revision
  (`gridRefresh.refreshed = true`).
- Bar colors come from bar styles; critical/milestone/summary semantics come from
  the read model, never from browser inference.

## 4. Gaps

Curtain/text attachments, notebook-on-bar attachments, and direct Gantt date or
duration editing are **غایب/محدودیت مستند** and are listed in the deviation
register for owner decision.
