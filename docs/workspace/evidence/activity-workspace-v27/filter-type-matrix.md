# V27 Filter Type Matrix — Activities Workspace

- Tested head: `b71cd61f46ebe358d1b15eee21068977b03493cf`
- Implementation: `apps/web/src/workspace-activity-filters.ts`
- Contract: filters are a display concern. They never recalculate dates, float,
  cost or progress, and never write to the database.

## 1. Filter fields (11)

| Field ID | Label | Value type | Operators offered (Version 26 order) | Notes |
|---|---|---|---|---|
| `activity_id` | Activity ID | text | contains, not-contains, equals, not-equals, is-empty, is-not-empty | Case-insensitive contains |
| `activity_name` | Activity Name | text | contains, not-contains, equals, not-equals, is-empty, is-not-empty | — |
| `wbs` | WBS | text | contains, not-contains, equals, not-equals, is-empty, is-not-empty | Matches the stored WBS path/name |
| `activity_status` | Status | choice | contains, not-contains, equals, not-equals, is-empty, is-not-empty | Not Started / In Progress / Completed |
| `activity_type` | Activity Type | choice | contains, not-contains, equals, not-equals, is-empty, is-not-empty | Six V26 activity types |
| `start` | Start | date | equals, not-equals, less-than, greater-than, within-range, is-empty, is-not-empty | Accepts date or `CD`, `CD±Nd/w/m` |
| `finish` | Finish | date | equals, not-equals, less-than, greater-than, within-range, is-empty, is-not-empty | Same relative forms |
| `progress` | Progress | number | equals, not-equals, less-than, greater-than, within-range, is-empty, is-not-empty | Stored percent |
| `duration` | Duration | number | equals, not-equals, less-than, greater-than, within-range, is-empty, is-not-empty | Stored duration |
| `total_float` | Total Float | number | equals, not-equals, less-than, greater-than, within-range, is-empty, is-not-empty | Negative float supported |
| `is_critical` | Critical | boolean | equals, not-equals | true / false picker |

Operator catalog (9): `contains`, `not-contains`, `equals`, `not-equals`,
`greater-than`, `less-than`, `within-range`, `is-empty`, `is-not-empty`.
Typed controls follow the field type: text input, number input, date input with
relative-date parsing, choice select, boolean select.

## 2. Dialog behavior

| Capability | Implementation | Status | Evidence |
|---|---|---|---|
| Any / All parameter rows | Runtime group mode | **مطابق و تأییدشده** | `activity-filters-v26` |
| Add / delete / reorder criteria | Second row uses the Add criterion control; order preserved | **مطابق و تأییدشده** | `activity-filters-v26`, `activities-v26-scenarios` |
| Typed value control | Select for choice/boolean, input for text/number/date | **مطابق و تأییدشده** | `activities-v26-scenarios` |
| Range validation | High value required for `within-range`; order validated for numeric ranges | **مطابق و تأییدشده** | `workspace-activity-filters.test.ts` |
| Live preview | Count preview before applying | **مطابق و تأییدشده** | `activity-filters-v26` |
| Apply / replace / highlight | Applied to the rendered table only | **مطابق و تأییدشده** | `activity-filters-v26` |
| Saved custom filters | Persisted with project presentation; restored after reload | **مطابق و تأییدشده** | `workspace-activity-filters.test.ts`, `activity-filters-v26` |
| Clear | Restores the unfiltered read model | **مطابق و تأییدشده** | `activity-filters-v26` |
| Lookahead filter | Supported through relative date values; no separate "lookahead" preset row | **ناقص** vs a dedicated lookahead dialog | `create_a_lookahead_filter.htm` is in the crosswalk; 403 today |

## 3. Built-in filters (7)

| Filter | Criterion | Matching |
|---|---|---|
| In Progress | status equals "In Progress" | exact stored value |
| Not Started | status equals "Not Started" | exact |
| Completed | status equals "Completed" | exact |
| Critical | is_critical equals true | boolean |
| Non Critical | is_critical equals false | boolean |
| Negative Float | total_float < 0 | numeric |
| Milestone | activity_type contains "milestone" | covers Start/Finish Milestone |

## 4. Integrity checks

- Filtering never mutates persisted rows: `activities-v26-scenarios` scenario 18
  and the filter suite both assert no schedule write is issued.
- Unknown or empty cell values never match an `equals` filter and are only
  included by `is-empty`.
- Persian values are matched on the stored data, not on the translated display text.

## 5. Deviation

No dedicated lookahead-window dialog is implemented; the capability is expressed
through relative dates (`CD`, `CD+7d`, …) and ranges. This is recorded in
`deviation-register.md` (D-V27-05), not presented as full parity.
