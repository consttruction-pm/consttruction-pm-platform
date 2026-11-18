# V27 Final Acceptance Report — Activities Workspace

- Issue: [#2047](https://github.com/consttruction-pm/consttruction-pm-platform/issues/2047)
- Pull request: [#2048](https://github.com/consttruction-pm/consttruction-pm-platform/pull/2048)
- Branch: `feat/2047-activity-workspace-v26`
- Tested code head: `b71cd61f46ebe358d1b15eee21068977b03493cf`
- Working tree when tests ran: code commit clean; evidence documents staged after the run
- Environment: Hasan's Qoder Desktop, Windows 10.0.17763, local full-stack preview only
- Merge status: **NOT MERGED**. No deployment was performed.

## خلاصهٔ اجرایی (فارسی)

در این مرحله از دستور V27، سه شکاف باقی‌ماندهٔ V26 بسته شد و برای هرکدام آزمون واقعی اجرا شد:

1. **شکاف R1 — ارتفاع ۱۲۸۰×۷۲۰**: کف ارتفاع محیط کار اصلاح شد. اکنون در ۱۲۸۰×۷۲۰
   اسکرول عمودی سند وجود ندارد و عرض سند دقیقاً برابر عرض نماست (LTR و RTL).
2. **شکاف R2 — تازه‌سازی جدول پس از ذخیرهٔ General**: پس از ذخیره، پروژه از سرویس
   دوباره خوانده می‌شود؛ فعالیت انتخاب‌شده و زبانهٔ General حفظ می‌شوند و پیام ذخیره
   دوباره نمایش داده می‌شود. آزمون مرورگر این را با `gridRefresh.refreshed = true`
   تأیید کرد.
3. **شکاف R3 — ستون Percent Complete Type**: این فیلد به read model، دادهٔ نمونه و
   چیدمان ذخیره‌شده اضافه شد. ستون از گفت‌وگوی Columns نمایان می‌شود، مقدار ذخیره‌شده
   (`DURATION`) را نشان می‌دهد و پس از بارگذاری کامل باقی می‌ماند.

آزمون‌های نهایی: `npm test` با ۱۱۷۸ + ۱۵ تست موفق؛ مجموعهٔ هدفمند پایتون ۳۰ تست موفق؛
۳ مجموعهٔ مرورگر کلیدی در SHA `b71cd61f4` موفق؛ ۸ مجموعهٔ دیگر روی همان درخت کاری موفق.
شکاف‌های باقی‌مانده (Codes، Notebook، Steps، پیوند سند، Help در دسترس نیست) صادقانه
مستند شده‌اند و هیچ قابلیت جعلی اضافه نشده است. **این PR ادغام نشده است.**

## 1. What changed in this increment

| Change | File(s) | Why |
|---|---|---|
| `activity.percent_complete_type` emitted in the activity read cells | `src/construction_pm/backend_p0/workspace_read_provider.py` | R3 read-model gap |
| Curated field and hidden layout column added to the preview seed | `src/construction_pm/preview/fixtures.py` | Make the column available and persisted |
| Preview tests updated to 21 columns with label/type assertions | `tests/test_preview_runtime.py` | Keep the runtime contract honest |
| Provider test asserts the stored enum value | `tests/backend_p0/test_workspace_read_provider.py` | Prove the cell content |
| Project re-read after a General save, preserving selection and confirmation | `apps/web/src/main.ts`, `apps/web/src/workspace-activity-details.ts` | R2 grid refresh |
| Workspace floor relaxed to fit 1280×720 | `apps/web/styles.css`, `apps/web/public/styles.css` | R1 geometry |
| New browser suite for the percent-complete column | `apps/web/e2e/activity-percent-complete-v27.mjs` | Verification |
| General-edit suite asserts the grid re-read | `apps/web/e2e/activity-general-edit-v26.mjs` | Regression guard |
| Responsive suite stops Chrome and exits | `apps/web/e2e/workspace-responsive-v26.mjs` | No hung test processes |

No change to Scheduling Core, CPM, calendars computation, float/critical path,
leveling, EVM/cost, schema/migrations, identity/tenant authorization or production
composition.

## 2. Acceptance status by area

| Area | Status | Basis |
|---|---|---|
| Menus, commands, toolbars, shortcuts | **مطابق و تأییدشده** | 8/118/57/24 registries + browser suites |
| Layout, columns, filters, grouping/sorting | **مطابق و تأییدشده** | columns 11/11, filters, group/sort, field chooser 4/4 |
| Activity Table incl. Percent Complete Type | **مطابق و تأییدشده** | percent-complete V27 + columns + scenarios |
| Gantt, links, data date, progress line | **مطابق و تأییدشده** | Gantt suites, visual acceptance |
| Activity Details 17 tabs — render/interaction | **مطابق و تأییدشده** | details suite (17 tabs, keyboard, empty, stale, customize) |
| General edit path | **مطابق و تأییدشده** | general-edit at `b71cd61f4` |
| Codes / Notebook / Steps / Document links | **ناقص** — contract gaps | R4–R7 |
| Risks write | **ناقص** | read surface only |
| Resources/Expenses/Issues/UDF/Calendar writes | **پیاده‌سازی‌شده ولی آزمون‌نشده** in V27 | prior suites; not re-exercised end to end |
| Reports/Admin depth | **ناقص** (outside Activity scope) | entry points exist |
| Help-sourced option text/defaults | **VERIFY / BLOCKED** | 403 + missing PDF |
| Pixel-level vendor visual identity | **محدودیت مستند و مشخص** | no lawful screenshot set; not claimed |

## 3. Verification actually executed

| Check | Result |
|---|---|
| `npm run typecheck` | 0 errors |
| `npm run build` | success |
| `npm test` | 1178/1178 source + 15/15 preview server |
| Targeted Python | 30 passed |
| Broad Python (excluding 8 Windows-only modules) | 4676 passed, 224 skipped, 4 environment failures |
| `activity-general-edit-v26` at `b71cd61f4` | PASS — grid refresh, persistence, restore, 0 exceptions |
| `activity-percent-complete-v27` at `b71cd61f4` | PASS — index 8, `DURATION`, reload, restored |
| `workspace-responsive-v26` at `b71cd61f4` | 11/11 PASS — incl. 1280×720 without overflow |
| 8 additional suites on the same tree | PASS (columns 11, details 17 tabs, field chooser 4, window tabs 11, toolbars 6, shell 7, scenarios 18, visual 6 cells) |

All evidence is in this directory and the dated `*-v26-2026-11-18/` sibling
directories. No test result is copied from an earlier commit without disclosure.

## 4. Remaining blockers and ownership

| ID | Blocker | Owner / next action |
|---|---|---|
| R4 | Activity Codes assignment HTTP contract | Platform |
| R5 | Notebook topic persistence | Platform |
| R6 | Steps write route | Platform |
| R7 | Per-activity document link route | Platform |
| R8 | Help 403 / PDF missing | Product owner supplies PDF or access |
| R9 | Windows-only Python collection failures | CI on intended platform |

## 5. CI and delivery

Exact-head CI on `6926d6a4e` (code + evidence) — **all 10 checks pass**:

| Check | Result |
|---|---|
| `test (3.11)`, `test (3.12)`, `test (3.13)` | pass |
| `typecheck (apps/web)`, `(apps/client-sync)`, `(apps/desktop)`, `(apps/mobile)` | pass |
| `web` | pass |
| Vercel Preview Comments / `cubi-web-preview` | pass (repository automation; no Vercel work in this PR) |

Any later commit in this PR is documentation-only and re-runs the same checks.

- No merge, no deployment, no production change, no Vercel configuration work.
- The PR remains reviewable; approval to merge is the owner's decision.

## 6. Conclusion

The V27 increment closes the three concrete V26 defects that were reproducible in
this environment and adds a browser-verified Percent Complete Type column. It does
**not** claim complete parity: the four Activity Details contract gaps and the
unavailable official Help source remain explicit, classified and owned. The
implementation and its evidence are ready for review; merging is not part of this
work.
