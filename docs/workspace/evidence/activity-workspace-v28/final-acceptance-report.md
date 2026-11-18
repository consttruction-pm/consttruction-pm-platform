# V28 Final Acceptance Report — Activities Workspace

- Issue #2047 · PR #2048 · Branch `feat/2047-activity-workspace-v26`
- Base at mission start: `b3df87eb6c517ea9f7e837d31832848e5edcbab6` (main `9408552b`)
- V28 code commit: `2b7d035a1fc459ea71f8563bb8e285b218aa957f`
- PDF reference: **G57535-02, October 2026, 815 pages** — verified and text-extracted.
- HTML Help: HTTP 403 on 2026-11-18 (BLOCKED).
- Merge status: **NOT MERGED**. No deploy, no Vercel work, no production change.

## خلاصهٔ اجرایی (فارسی)

این مرحله با PDF رسمی ۸۱۵ صفحه‌ای انجام شد؛ فایل باز، هویت آن تأیید و متن آن استخراج شد.
فهرست ۲۶۴ موضوع Activities از فهرست مطالب PDF با شماره صفحه ثبت شد.

**آنچه تکمیل شد**
- دستور دقیق «Six-Week Lookahead» از صفحه ۱۰ فصل ۹ پیاده‌سازی و آزمون شد. یک نقص واقعی
  پیدا شد: فیلترهای منفی (`is not equal to`) مقادیر خالی را رد می‌کردند و دستور PDF
  صفر نتیجه می‌داد. اصلاح شد و اکنون ۱۰ از ۱۴ فعالیت مطابقت دارد، فیلتر ذخیره و پس از
  reload بازگردانی می‌شود و هیچ نوشتن زمان‌بندی رخ نمی‌دهد.
- برچسب پارامتر از «Progress %» به «Activity % Complete» مطابق PDF تغییر کرد.
- شش Theme واقعی آزمون شد و یک نقص بصری جدی کشف شد: در Midnight و Graphite متن روشن روی
  ردیف سفید تقریباً ناخوانا بود. اصلاح شد؛ کنتراست اندازه‌گیری‌شده ۱۳٫۶۵:۱ و ۱۴٫۱۴:۱ است.
- ممیزی منوها، Toolbarها، منوی زمینه و میانبرها با ارجاع صفحه PDF ثبت شد.
- ممیزی ۱۷ زبانهٔ Activity Details و Dialogها با صفحه PDF ثبت شد؛ الزامات Add/Modify/Delete
  برای Steps و Notebook مستند شد.

**آنچه هنوز ناقص/مسدود است**
- Codes، Notebook، Steps و اتصال سند: بدون قرارداد HTTP؛ UI جعلی ساخته نشد.
- دو مرحله‌ای بودن کلیدهای Alt (مثل Alt-F, N) پیاده‌سازی نشده و به مالکیت فایل‌های مشترک
  گره خورده است.
- ۱۸ خانوادهٔ Toolbar در PDF در برابر ۱۱ خانوادهٔ CUBI.
- الحاقیه‌های Curtain/Text روی Gantt غایب است.
- Help HTML هنوز 403 است؛ PDF مرجع اصلی در دسترس است.

**آزمون‌های اجراشده:** typecheck و build موفق؛ ۱۱۷۸ + ۱۵ تست واحد؛ Lookahead دقیقاً مطابق PDF
موفق؛ ۱۴/۱۴ فیلتر؛ ۶/۶ Theme متمایز با کنتراست AA؛ ۱۱/۱۱ Responsive. CI روی commit نهایی
پس از push بررسی می‌شود. **هیچ ادغامی انجام نشد و هیچ قابلیت ناقصی موفق اعلام نشد.**

## 1. PDF audit progress

| Measure | Value |
|---|---:|
| PDF pages verified | 815 |
| Distinct Activities-related TOC topics indexed | 264 (ch5 120, ch7 110, ch9 34) |
| Topics with a per-row CUBI comparison recorded | key matrices below (menus/toolbars, dialogs, Details, filters, table/Gantt) |
| Topics still needing a line-by-line row | remaining ch5/ch7 details; tracked as D-V28-11 |

The inventory (`pdf-topic-inventory.md`) and the matrices are real records of what
was read. A complete 264-row comparison is **not** claimed.

## 2. Delivered evidence in this directory

| File | Contents |
|---|---|
| `baseline-and-reference.md` | Repo/PR/CI baseline, PDF identity, chapter map, ownership check |
| `pdf-topic-inventory.md` | 264 PDF topics with printed page numbers |
| `menu-toolbar-shortcut-audit.md` | Menu/toolbar/context/keyboard comparison, PDF pages 13–15, 25, 46–78 |
| `activity-details-and-dialogs-audit.md` | 17 tabs + dialogs, PDF pages 5–10 (ch7), 57–67 (ch5) |
| `table-and-gantt-matrix.md` | Table/Gantt capabilities and gaps with PDF pages |
| `lookahead-and-filters.md` | Exact recipe verification, defect and fix |
| `theme-acceptance.md` | Six skins, contrast, persistence |
| `test-coverage.md` | Commands, results, limitations |
| `deviation-register.md` | Every known gap with owner/action |
| `final-acceptance-report.md` | This report |
| `lookahead-filter.json` + 3 screenshots | Machine-readable lookahead evidence |
| `theme-acceptance.json` + 7 screenshots | Machine-readable theme evidence |

V27 matrices remain valid for the backend contracts, visual fidelity and the 17-tab
baseline: `docs/workspace/evidence/activity-workspace-v27/`.

## 3. Verification executed

| Check | Result |
|---|---|
| `npm run typecheck` | 0 errors |
| `npm run build` | success |
| `npm test` | 1178/1178 + 15/15 |
| Filter unit tests | 17/17 |
| `activity-lookahead-v28` | PASS — 10/14, reload 10, no schedule writes |
| `activity-filters-v26` | PASS 14/14 |
| `theme-acceptance-v28` | PASS — 6 distinct skins, AA contrast in dark skins |
| `workspace-responsive-v26` | PASS 11/11 |
| Browser health | 0 exceptions, 0 console errors, 0 API 5xx in each suite |

Backend tests were unchanged in V28; the V27 result (30 targeted pass; broad
4676/224/4 environment-only failures) remains the latest backend verification.

## 4. Status summary

| Area | Status |
|---|---|
| Build, typecheck, unit suite | **مطابق و تأییدشده** |
| Lookahead exact PDF recipe | **مطابق و تأییدشده** |
| Filters overall | **مطابق و تأییدشده** |
| Six themes + dark-skin readability | **مطابق و تأییدشده** (1366) |
| Responsive/RTL Classic | **مطابق و تأییدشده** |
| Menus/toolbars/shortcuts full PDF parity | **ناقص** (see audit) |
| Activity Details (General/Status/relationships/etc.) | **مطابق و تأییدشده**; Steps/Notebook/Codes/Docs **ناقص** |
| Table/Gantt | **مطابق و تأییدشده**; attachments **غایب** |
| Help HTML | **BLOCKED** (403); PDF used instead |
| Pixel-level vendor comparison | **محدودیت مستند و مشخص** |

## 5. Delivery

No merge or deployment. The V28 code changes (filter semantics, label, dark-skin
CSS, two new E2E suites, unit test) and this evidence set are committed to the PR
branch for review; exact-head CI is checked after the push.
