# V28 Lookahead and Filter Parity

- Reference: G57535-02, "Create a lookahead filter", Chapter 9 *Filtering*, printed page 10 (PDF page 412), plus "Combine filters" page 9.
- Tested code: `2b7d035a1fc459ea71f8563bb8e285b218aa957f`.
- Evidence: `lookahead-filter.json`, `01-lookahead-recipe-en-1366.png`, `02-lookahead-applied-en-1366.png`, `03-lookahead-after-reload-en-1366.png`.

## 1. What the reference actually specifies

The PDF does **not** define a separate Lookahead dialog. It defines lookahead as
a user-created filter with relative dates:

1. `View, Filter By` → `New…`, name "Six-Week Lookahead".
2. Combine mode "(All of the following)".
3. Row: Parameter `Start`, Is `is within range of`, Value `CD` (Current Date),
   High Value `CF+6w`.
4. Add row: Parameter `Activity % Complete`, Is `is not equal to`, Value `100`.
5. Apply mode: Replace activities (or Highlight).
6. OK to save, then select and apply the filter.

The PDF explicitly allows typing `CD+6w`/`CF+6w` in value fields. CUBI's relative
grammar already supported `CD`, `CS`, `CF` with `±n[dwmy]`.

## 2. Defect found by executing the exact recipe

| Observation | Root cause | Fix |
|---|---|---|
| The exact recipe matched **0 of 14** activities, although 10 should match | `activityMatchesCriterion` rejected any blank stored value before evaluating the operator. Not-started activities have no stored percent, so `Activity % Complete is not equal to 100` evaluated false. | Blank values now satisfy negative operators (`not-equals`, `not-contains`); positive operators still require a value. |

A unit test was added to lock the semantic: a row with no stored `progress`
matches `progress not-equals 100`.

## 3. Result after the fix

| Check | Result |
|---|---|
| Recipe rows | 3 editor rows; row 1 Start within `CD`…`CF+6w`; row 3 Activity % Complete `is not equal to` 100 |
| Labels | `Start`, `is within range of`, `Activity % Complete`, `is not equal to` (renamed from "Progress %" to match the PDF) |
| Preview | valid; **10 of 14** activities match |
| Apply (Replace) | grid shows exactly the 10 previewed rows |
| Persistence | filter saved as "Six-Week Lookahead" in the layout and re-applied after a full reload (10 rows) |
| Schedule writes | **none**; the only write is the layout persistence of the saved filter, which is expected |
| Browser health | 0 exceptions, 0 console errors, 0 API 5xx |

Command:

```bash
CUBI_PREVIEW_URL=http://127.0.0.1:4198 \
CUBI_TESTED_CODE_SHA=$(git rev-parse HEAD) node e2e/activity-lookahead-v28.mjs
```

## 4. Full filter regression

`activity-filters-v26.mjs` still passes **14/14** after the semantic and label
changes, covering categories, All/Any, typed pickers, relative dates, high values,
preview, replace/highlight, persistence, RTL, 1920 width, Optimize, Duplicate,
Cut/Paste and Clear.

## 5. Status

| Capability | Status |
|---|---|
| Create/edit/save/delete filter | **مطابق و تأییدشده** |
| Any/All, Replace/Highlight, preview | **مطابق و تأییدشده** |
| Relative dates CD/CS/CF ± n d/w/m/y | **مطابق و تأییدشده** |
| Range + High value and validation | **مطابق و تأییدشده** |
| Exact PDF six-week lookahead recipe | **مطابق و تأییدشده** |
| Lookahead as a dedicated dialog | **محدودیت مستند و مشخص** — the reference does not define one |
| Saved filter scope (default/global/layout/user) | **مطابق و تأییدشده** in the manager; server stores layout-scoped filters |
