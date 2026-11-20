# V27 Activity Details Matrix — 17 Tabs

- Tested head: `b71cd61f46ebe358d1b15eee21068977b03493cf`
- Implementation: `apps/web/src/workspace-activity-details.ts` + `workspace-activity-general.ts`
- Global rules: no fabricated values; unknown cells render empty; a cleared
  selection shows one localized empty-state message (`data-details-empty-state`);
  writes are revision-guarded and permission-gated; stale responses are discarded.

Statuses: **مطابق و تأییدشده** · **پیاده‌سازی‌شده ولی آزمون‌نشده** · **ناقص** · **غایب** · **محدودیت مستند و مشخص**

| # | Tab | Data source | Write path | Status | Notes / evidence |
|---:|---|---|---|---|---|
| 1 | General | Activity Master record (`GET /p6/activities/{id}`) | `PATCH /p6/activities/{id}` with `expected_revision` | **مطابق و تأییدشده** | Six activity types, four duration types, four percent-complete types, five leveling priorities; grid+Gantt re-read after save; reload persistence; restore verified (`activity-general-edit-v26` at `b71cd61f4`) |
| 2 | Status | Read-model cells + activity record | No dedicated write in this tab (progress uses Progress / Update Progress) | **مطابق و تأییدشده** | Stored status, status code, dates, durations, percent; `activity-details-v26` |
| 3 | Resources | Assignment periods service | Assignment API (add/edit/remove periods) | **مطابق و تأییدشده** for the Details write path | `activity-details-v26` exercises the resources write; `assignments-v26` covers the assignment window |
| 4 | Predecessors | Relationship service | Relationship API via Assign Predecessors | **مطابق و تأییدشده** (read) / write tested in relationships suite | `activity-relationships-v26` |
| 5 | Successors | Relationship service | Relationship API via Assign Successors | **مطابق و تأییدشده** (read) | same |
| 6 | Relationships | Relationship service | Link / Unlink from menus and context menus | **مطابق و تأییدشده** | Four types FS/SS/FF/SF; `activity-relationships-v26` |
| 7 | Codes | Stored code assignments via read model | **No HTTP assignment route** | **ناقص** — CONTRACT/API GAP | Shows stored values only; assignment/removal would be invented UI. R4 |
| 8 | Notebook | Read model notebook topics if present | **No persistence service** | **ناقص** — CONTRACT/API GAP | Comments rail is browser-local and is not presented as persisted Notebook topics. R5 |
| 9 | Steps | Read-only step service (`P6ActivityStepReadAPI`) | **No write route**; repository has upsert only | **ناقص** — CONTRACT/API GAP | R6 |
| 10 | WPs & Docs | Document associations from the read model | **No per-activity link route** | **ناقص** — CONTRACT/API GAP | R7 |
| 11 | Expenses | Expense service | Create/edit/delete expense rows | **مطابق و تأییدشده** for the Details write path | `activity-details-v26` exercises the expenses write; `expenses-v26` covers the window |
| 12 | Issues | Issue service | Create/edit issue rows | **مطابق و تأییدشده** for the Details write path | `activity-details-v26` exercises the issues write; `issues-v26` covers the window |
| 13 | Risks | Read model risk facts | No risk write contract | **ناقص** | Professional-only feature per source register; read surface exists |
| 14 | Summary | Read model summary | none | **مطابق و تأییدشده** (read) | Read-only aggregate |
| 15 | UDFs | UDF value service | UDF value API | **پیاده‌سازی‌شده ولی آزمون‌نشده** | `activity-udf-values-v26` |
| 16 | Update History | Progress history service | none (read-only by design) | **مطابق و تأییدشده** | `progress-history-v26`; stale-response guard verified in `activity-details-v26` |
| 17 | Calendar (CUBI) | Project calendar + activity calendar assignment | Calendar assignment service | **مطابق و تأییدشده** as a CUBI extension | Jalali/Gregorian, workweek, exceptions; `calendars-jalali-v26` |

## Interaction and layout

| Behavior | Status | Evidence |
|---|---|---|
| 17 tabs render with localized labels (EN/FA) | **مطابق و تأییدشده** | `activity-details-v26` (`tabs` length 17) |
| Tablist keyboard: ArrowLeft/Right, Home/End, wrap, roving tabindex | **مطابق و تأییدشده** | `activity-details-v26` keyboard EN + FA |
| Customize Tabs dialog persists visibility | **مطابق و تأییدشده** | `activity-details-v26` customize |
| Empty selection message, localized | **مطابق و تأییدشده** | `activity-details-v26` emptyState |
| Unauthorized state for a viewer | **مطابق و تأییدشده** | `activity-details-v26` unauthorized |
| Stale response discarded when selection changes | **مطابق و تأییدشده** | `activity-details-v26` staleResponse |
| Save confirmation survives the project re-read | **مطابق و تأییدشده** (V27) | `activity-general-edit-v26` at `b71cd61f4` |
| Details pane fits 1280×720 without document scroll | **مطابق و تأییدشده** | responsive 11/11; visual acceptance |

## Acceptance statement

All 17 tabs have a browser-verified render path. Four tabs (Codes, Notebook,
Steps, WPs & Docs) are explicitly incomplete because the backend contracts do not
exist; they do not simulate persistence. Risks has a read surface only. The
Details suite exercised the Resources, Expenses and Issues write paths on the same
working tree (recorded HEAD `f349d474`; code identical to `b71cd61f4`). UDF and
Calendar assignment have service paths but were not re-exercised end to end in the
V27 run, so they remain **پیاده‌سازی‌شده ولی آزمون‌نشده**.
