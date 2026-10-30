# گزارش بازبینی بصری پوستهٔ Workspace

تاریخ: ۲۰۲۶-۱۰-۳۰ · شاخه: `feat/workspace-visual-shell` · دامنه: فقط پوستهٔ بصری Workspace با دادهٔ ثابت نمایشی `CUBI-DEMO-001`.

این گزارش نتیجهٔ چیزی است که واقعاً در پیش‌نمایش محلی اجرا و دیده شده است. هیچ فرمول، API، پایگاه داده یا منطق محاسبه تغییر نکرده و هیچ عملیات واقعی جعل نشده است.

## روش

- پیش‌نمایش واقعی: `py -m construction_pm.preview --web-root apps/web --database "C:/Users/SAAM FF/AppData/Local/Temp/cubi-viewer.sqlite3" --port 4174`، سپس ورود نمایشی با نقش `planner` و باز کردن `/app?view=visual`.
- بازبینی خودکار با Chrome DevTools Protocol روی همان صفحهٔ واقعی: هر زبانهٔ پنجره، هر دکمهٔ نوار ابزار، هر فرمان منو (شامل زیرمنوها)، هر زبانهٔ Activity Details و هر دکمهٔ درون‌پنجره‌ای کلیک می‌شود و مقصد بازشده ثبت می‌شود. پس از هر بازترسیم، عناصر دوباره جست‌وجو می‌شوند تا ارجاع کهنه باعث نتیجهٔ کاذب نشود.
- خروجی ماشینی: `docs/workspace/screenshots/visual/visual-audit.json` — ۴۳ تصویر شماره‌دار در `docs/workspace/screenshots/visual/` (به‌همراه `00-smoke.png`).
- هر دو زبان انگلیسی و فارسی، در عرض‌های ۱۳۶۶، ۱۴۴۰ و ۱۹۲۰ پیکسل.

## نتیجهٔ ممیزی نهایی (اجرای آخر روی کد نهایی)

```json
{
  "windows": "21/21",
  "menus": 8,
  "menuCommands": 85,
  "toolbarButtons": 36,
  "commands": 121,
  "reachedDialogs": "36/36",
  "missingDialogs": 0,
  "detailTabs": "17/17 active and non-empty",
  "detailsCollapse": { "collapsed": true, "bodyHidden": true, "toggleVisible": true, "expandedAfter": true },
  "adminSections": "6/6 active with content",
  "calendar": { "startMonth": "December 2026", "nextMonth": "January 2027", "backMonth": "December 2026", "cells": 40, "dataDate": "3" },
  "errors": []
}
```

## سطوحی که در پیش‌نمایش دیده و پیمایش شدند

| سطح | نمونهٔ تصویر | وضعیت |
| --- | --- | --- |
| Activities: جدول + Gantt + Activity Details | `01-activities-en-1440.png`، `02-activities-fa-1440.png` | کامل؛ ۲۱ ردیف، گروه‌بندی WBS، نوارهای خلاصه/بحرانی/نقطه‌عطف، فلش‌های FS، خط تاریخ داده |
| Activity Details جمع‌شونده | `42-details-collapsed-en-1440.png`، `43-details-collapsed-fa-1440.png` | دکمهٔ باز/بستن، ۱۷ زبانه، ناوبری قبلی/بعدی |
| مقیاس روز/هفته/ماه/فصل/سال | `37-gantt-day-scale-en-1440.png` | اعداد روز ۱۸px/day، اسکرول افقی، دو باند ماه/روز |
| WBS / Projects / Resources / Assignments | `06`–`09` | جدول‌ها و اکشن‌ها |
| Calendars / Reports / Tracking / Documents / Expenses / Thresholds / Issues / Risks / Administration | `10`–`18` | همه دارای محتوای قابل مشاهده |
| Activity Network | `19-network-en-1440.png` | ۱۲ جعبه و ۱۱ رابطهٔ واقعی FS با فلش اندازه‌گیری‌شده |
| Trace Logic | `20-trace-en-1440.png` | پیش‌نیازها و جانشین‌ها با خطوط رابطهٔ دوطرفه و توضیح یک‌سطحی |
| Timeline | `39-timeline-en-1440.png`، `40-timeline-fa-1440.png` | ۵ خط فاز، خط تاریخ داده، ۶ نقطه‌عطف، برچسب‌های لبه‌ای |
| Usage Profile / Spreadsheet | `21`، `22`، `23`، `24` | ۳۰ هفتهٔ کامل پروژه (W45…W21)، جدول‌های متقاطع |
| منوها و زیرمنوها | `25`، `26` | ۸ منو، زیرمنوی Layouts شامل Timeline |
| دیالوگ‌ها | `29`–`36`، `41` | ۳۶ دیالوگ بازشدنی، شامل Column، Filters، Group and Sort، Timescale، Bars، Calendar، Print، Shortcuts، Timeline Options |

## نقص‌های پیداشده و اصلاح‌شده

1. **منوهای بازشده زیر نوار ابزار گم می‌شدند** — علت: `overflow` محاسبه‌شدهٔ `.cp-vd-menubar` روی `auto` بود. با `overflow: visible` و `z-index: 40` اصلاح شد؛ اکنون پاپ‌آپ ۲۵۰×۳۱۱ پیکسل بالای نوار ابزار و قابل کلیک است.
2. **Activity Network جعبه‌های ساختگی و فلش قطع‌شده داشت** — با ۱۲ فعالیت واقعی از دادهٔ نمایشی و ۱۱ رابطهٔ FS بازسازی شد. خطوط از مختصات واقعی جعبه‌ها اندازه‌گیری می‌شوند، نه درصدهای حدسی.
3. **Trace Logic بدون خط رابطه بود** — لایهٔ SVG با مسیرهای پیش‌نیاز→انتخاب‌شده و انتخاب‌شده→جانشین اضافه شد؛ در EN و FA بررسی شد.
4. **مقیاس روز ناخوانا بود** — از ۹px/day به حداقل ۱۸px/day و عرض ۳۷۴۴px با اسکرول افقی تغییر کرد.
5. **در RTL تاریخ‌ها و رشته‌های مختلط جابه‌جا می‌شدند** — «03-Dec-2026» به «Dec-2026-03» و «5-Day Workweek» به «Day Workweek-5» تبدیل می‌شد. همهٔ موارد در `<bdi dir="ltr">` و ورودی‌های جزئیات با `direction: ltr` اصلاح شدند.
6. **آخرین نقطه‌عطف Timeline از لبهٔ کانتینر بیرون می‌زد** — موقعیت به بازهٔ ۰٫۶٪ تا ۹۹٫۴٪ محدود و برچسب نقطهٔ پایانی به سمت داخل برگردانده شد.
7. **پنل Activity Details فضای جدول را می‌گرفت** — پنل تاشو شد؛ در حالت باز ۸ ردیف و در حالت بسته ۱۴ ردیف از ۲۱ ردیف دیده می‌شود و بقیه با اسکرول در دسترس است.
8. **پروفایل و صفحهٔ مصرف فقط ۱۰–۱۱ هفته را نشان می‌دادند** — به ۳۰ هفتهٔ کامل پروژه با شماره‌های ISO هفته (W45…W21) و ستون‌بندی هم‌تراز با مقیاس زمانی گسترش یافتند.
9. **تقویم روز ۱ را زیر ستون اشتباه می‌گذاشت** — تعداد خانه‌های خالی از روی روز واقعی اول ماه محاسبه می‌شود، نه فرض دوشنبه؛ دسامبر ۲۰۲۶ با ۱ در سه‌شنبه و تاریخ داده ۳ در پنجشنبه نمایش داده می‌شود. ناوبری ماه (نوامبر ۲۰۲۶ تا مه ۲۰۲۷) واقعاً ماه را عوض می‌کند و در RTL ستون‌ها از شنبه شروع می‌شوند.
10. **موارد کنار Administration فقط «Users» را نشان می‌دادند** — هر شش بخش (کاربران، پروفایل‌های امنیتی، تنظیمات عمومی، ارزها، کدهای فعالیت، UDFs) اکنون انتخاب‌شدنی است و پنل خودش را با دادهٔ نمونه نشان می‌دهد.
11. **ورودی‌های دیالوگ Calendar Editor کشیده و بلند بودند** — با `align-content: start` در `.cp-vd-form` ارتفاع طبیعی ۲۶px بازگشت.
12. **پنل جدید Activity Details در Workspace واقعی شناسهٔ انتخاب‌شده را از دست می‌داد** — بازنویسی پنل، عنصر `.cp-detail-selected` را حذف کرده بود و E2E «A130 selection details» شکست خورد؛ کلاس قرارداد روی `.cp-details-id` بازگردانده شد و یک تست واحد جدید آن را قفل می‌کند. پس از اصلاح، E2E کامل پیش‌نمایش با ۸۰ بررسی سبز شد.

## مقایسه با تصاویر مرجع

مبنای مقایسه، مشاهدات ثبت‌شده در `docs/workspace/visual-reference-audit.md` است: چیدمان دو نوار ابزار، نوار زبانهٔ پنجره‌ها، جدول + Gantt + Activity Details، نوار گروه آبی، ردیف خلاصه، نوار بحرانی قرمز، الماس نقطه‌عطف، خط تاریخ داده، دیالوگ‌های ستون/فیلتر/گروه و ترتیب/مقیاس، و نوار وضعیت چندبخشی. تفاوت‌های عمدی: هویت CUBI، فونت و تراکم بزرگ‌تر برای خوانایی، و نبود هرگونه نام یا نشان Oracle/Primavera/P6.

## محدودیت‌های صادقانه

- تصویر مرجع شمارهٔ ۱ (Activities کامل با منوی Edit باز) با HTTP 403 از سوی Oracle قابل دریافت نبود و نسخهٔ آرشیوی هم نداشت؛ این ناحیه با تصاویر ۲، ۳، ۸، ۹ و ۱۰ و مستندات نسخهٔ ۲۶ مقایسه شد.
- تصاویر مرجع نسخهٔ ۸.۳–۱۸ هستند، نه نسخهٔ ۲۶؛ جزئیات فقط برای چیدمان و تراکم استفاده شدند.
- این پیش‌نمایش دادهٔ ثابت نمایشی دارد و هیچ محاسبه، ذخیره یا فراخوانی API واقعی انجام نمی‌دهد؛ برچسب «Visual demo · sample data» و نوار «LOCAL PREVIEW · DEMO DATA — NOT PRODUCTION» همیشه نمایش داده می‌شوند.
- جدول Activities در عرض ۱۴۴۰ ستون‌های بیشتری از عرض دید دارد و اسکرول افقی طبیعی است؛ در مرز تقسیم، لبهٔ ستون بعدی دیده می‌شود.
- در Trace Logic فضای سفید باقی می‌ماند؛ با یادداشت توضیحی یک‌سطحی بودن منطق پر شده، اما تراکم کامل نمودار شبکه در این واحد هدف نبود.
- Activity Details در حالت باز هنوز همهٔ ۲۱ ردیف را هم‌زمان نشان نمی‌دهد؛ حالت جمع‌شده ۱۴ ردیف نشان می‌دهد و اسکرول برای بقیه لازم است.

## اجرای پیش‌نمایش

```bash
py -m construction_pm.preview --web-root apps/web --database "C:/Users/SAAM FF/AppData/Local/Temp/cubi-viewer.sqlite3" --port 4174
# سپس ورود نمایشی و باز کردن:
# http://127.0.0.1:4174/app?view=visual
```

مسیر دسترسی از محیط کار عادی: `Help → Visual workspace demo` یا پارامتر `?view=visual`.

اجرای دوبارهٔ ممیزی (در ریشهٔ مخزن، با پیش‌نمایش و Chrome در حال اجرا):

```bash
node docs/workspace/qa/visual-qa.mjs all
node docs/workspace/qa/view-shot.mjs activities en 1440 900 "$TEMP/activities.png"
```

## وضعیت تحویل

- شاخه: `feat/workspace-visual-shell` — PR [#1653](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1653)
- تست‌ها: ۴۲۲ تست TypeScript + ۱۳ تست preview (Node) + ۱۳ تست Python، همه سبز؛ E2E کامل پیش‌نمایش (۸۰ بررسی) نیز سبز
- `tsc --noEmit` و `npm run build` سبز
- `apps/web/styles.css` و `apps/web/public/styles.css` بایت‌به‌بایت یکسان
- Commit اصلاح رگرسیون جزئیات: `fix(workspace): keep activity details selection identity`؛ ادغام فقط پس از سبز شدن CI روی SHA دقیق انجام می‌شود.
