# ماتریس انطباق Activities با P6 Professional نسخه ۲۶

تاریخ اجرای مرورگر: ۲۰۲۶-۱۱-۱۲ — شاخه: `feat/v26-gantt-options` (کد آزمون‌شده `b20501f`، شاهد `7ea89d5`؛ ادغام در `main`)
مرجع رفتاری/مؤلفه‌ای: P6 Professional Help Version 26 (HTML) — <https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm>. هیچ وابستگی به PDF در این سند وجود ندارد.

شواهد مرورگر (۱۸ سناریو): `apps/web/e2e/artifacts/activities-v26/activities-v26-scenarios.json` و کپی پایدار در `docs/workspace/evidence/activities-v26-scenarios-2026-11-08.json`؛ تصاویر واقعی در `docs/workspace/screenshots/visual/74…101`.
شواهد پذیرش بصری ۲۰۲۶-۱۱-۱۲: `docs/workspace/evidence/visual-acceptance-v26-2026-11-12/workspace-visual-acceptance-v26.json` (۲۱ تصویر، ۶ سلول: ۱۲۸۰×۷۲۰، ۱۳۶۶×۷۶۸، ۱۹۲۰×۱۰۸۰ در `en/LTR` و `fa/RTL`).
شواهد پذیرش گانت‌آپشنز ۲۰۲۶-۱۱-۱۲: `docs/workspace/evidence/gantt-options-v26-2026-11-12/gantt-options-v26.json` (۲۲ تصویر، ۲ سلول ۱۳۶۶×۷۶۸ در `en/LTR` و `fa/RTL`).
شواهد پذیرش Fit پویا ۲۰۲۶-۱۱-۱۲: `docs/workspace/evidence/gantt-fit-v26-2026-11-12/gantt-fit-v26.json` (۴ تصویر، ۴ سلول: ۱۳۶۶×۷۶۸ و ۱۹۲۰×۱۰۸۰ در `en/LTR` و `fa/RTL`؛ کد آزمون‌شده `08302a5`، شاهد `f2523c1`).
شواهد پذیرش اسکرول همگام ۲۰۲۶-۱۱-۱۲: `docs/workspace/evidence/gantt-scroll-sync-v26-2026-11-12/gantt-scroll-sync-v26.json` (۱۲ تصویر، ۴ سلول: ۱۲۸۰×۷۲۰ و ۱۳۶۶×۷۶۸ در `en/LTR` و `fa/RTL`؛ کد آزمون‌شده `eaf2d91`، شاهد `4156d22`).
شواهد فعال‌سازی فرمان‌های زمینه ۲۰۲۶-۱۱-۲۵: `docs/workspace/evidence/activity-export-assign-v26-2026-11-25/activity-export-assign-v26.json` (۴ سناریو، ۳ تصویر؛ دانلود واقعی `activities.xlsx` با هش برابر سرآیند سرور؛ شاخهٔ `feat/engineering-activities-v26-commands` بر پایهٔ `1593e6027`).
اجرای سناریوها: **۱۸ از ۱۸ PASS**، `exceptions=0`، `consoleErrors=0`، `apiFailures=0`، تعداد روابط دیتابیس پس از پاک‌سازی موقت: ۲۱ (بدون باقی‌مانده). اجرای پذیرش بصری: **۶ از ۶ سلول PASS**، `exceptions=0`، `consoleErrors=0`، `apiFailures=0`.

## واژگان وضعیت (تنها مقادیر مجاز)

**مطابق و تأییدشده** / **پیاده‌سازی‌شده ولی آزمون‌نشده** / **ناقص** / **غایب** / **محدودیت مستند و مشخص**

هیچ ردیف «مطابق و تأییدشده» فقط بر پایهٔ کد نیست؛ هر ردیف تأییدشده به سناریوی مرورگر و شمارهٔ تصویر ارجاع می‌دهد.

## ماتریس

| موضوع Help نسخه ۲۶ | نشانی دقیق Help | محل نمایش | تعداد مؤلفه مرجع | تعداد مؤلفه CUBI | وضعیت بصری | وضعیت عملکردی | وضعیت آزمون مرورگر | تفاوت مشاهده‌شده | اصلاح لازم | نتیجه نهایی |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| پنجرهٔ Activities و چیدمان کلی | https://docs.oracle.com/cd/G48902_01/client_help/en_US/using_main_windows.htm | کل پنجرهٔ `?view=live` | ۱ پنجره | ۱ پنجره | مطابق و تأییدشده | مطابق و تأییدشده | مطابق و تأییدشده (سناریو ۱، تصویر ۷۴) | تم و فاصله‌ها مطابق سند بصری CUBI است، نه کپی پیکسلی P6 | ندارد | مطابق و تأییدشده |
| نوار منو هشت‌گانه | https://docs.oracle.com/cd/G48902_01/client_help/en_US/menu_bar.htm | نوار بالای پنجره | ۸ منو | ۸ منو | مطابق و تأییدشده | ناقص | پیاده‌سازی‌شده ولی آزمون‌نشده | چند فرمان با دلیل واقعی غیرفعال است؛ همهٔ منوها تک‌به‌تک باز نشدند | آزمون باز/بستهٔ هر منو و هر آیتم | ناقص |
| نوار ابزار فرمان‌ها | https://docs.oracle.com/cd/G48902_01/client_help/en_US/layout_toolbar.htm | نوار آیکون بالای جدول | ۱۴ فرمان نوار چیدمان | ۳۰ فرمان در یک نوار یکپارچه | مطابق و تأییدشده | ناقص | پیاده‌سازی‌شده ولی آزمون‌نشده | فرمان‌های فایل/ویرایش هم در همان نوار است؛ Print/Export غیرفعال‌اند | آزمون کلیک تک‌تک و ثبت نتیجه | ناقص |
| آیکون‌ها | https://docs.oracle.com/cd/G48902_01/client_help/en_US/layout_toolbar.htm | نوار ابزار، ریل، منوها | مجموعهٔ آیکون مرجع | SVG درون‌خطی CUBI | ناقص | مطابق و تأییدشده | پیاده‌سازی‌شده ولی آزمون‌نشده | آیکون‌ها هم‌معنا هستند، نه هم‌شکل | جای‌گزینی با ست آیکون هم‌شکل در صورت الزام | ناقص |
| جدول فعالیت‌ها (ستون‌های داده) | https://docs.oracle.com/cd/G48902_01/client_help/en_US/activitytable.htm | ناحیهٔ بالا-چپ | ۷ ستون داده + ستون‌های ساختار/عملیات | ۷ ستون داده + ستون‌های ساختار/عملیات | مطابق و تأییدشده | مطابق و تأییدشده | مطابق و تأییدشده (سناریوهای ۱ و ۶، تصویر ۷۴) | ترتیب پیش‌فرض ستون‌ها با مرجع یکی نیست | ندارد | مطابق و تأییدشده |
| Columns و Edit Column | https://docs.oracle.com/cd/G48902_01/client_help/en_US/49095.htm | گفت‌وگوی Columns | افزودن/حذف/جابه‌جایی/عرض/ویرایش ستون | همان مجموعه | مطابق و تأییدشده | ناقص | مطابق و تأییدشده (سناریو ۶، تصاویر ۸۰ و ۸۱) | ویرایش عنوان/تراز ستون در همان اجرا آزمون نشد | آزمون جداگانهٔ Edit Column | ناقص |
| فیلترهای پیش‌فرض و All Activities | https://docs.oracle.com/cd/G48902_01/client_help/en_US/filter_a_layout.htm | گفت‌وگوی Filters و سرصفحهٔ جدول | ۷ فیلتر پیش‌فرض | ۷ فیلتر پیش‌فرض | مطابق و تأییدشده | مطابق و تأییدشده | مطابق و تأییدشده (سناریوهای ۷ و ۸، تصویر ۸۲) | فهرست User-Defined خالی است و صادقانه توضیح داده می‌شود | ندارد در محدودهٔ سرویس موجود | مطابق و تأییدشده |
| ترکیب فیلترها (All/Any) و Apply | https://docs.oracle.com/cd/G48902_01/client_help/en_US/filter_a_layout.htm | گفت‌وگوی Filters | ۲ حالت ترکیب + ۲ حالت اعمال | ۲ حالت ترکیب + ۲ حالت اعمال | مطابق و تأییدشده | ناقص | مطابق و تأییدشده برای replace (سناریو ۷، تصویر ۸۲) | حالت Highlight پیاده‌سازی شده ولی در مرورگر کلیک نشد | آزمون Highlight با تصویر | ناقص |
| ساخت و ویرایش فیلتر | https://docs.oracle.com/cd/G48902_01/client_help/en_US/filter_a_layout.htm | گفت‌وگوی Filters → New/Modify | ۹ فیلد، ۷ عملگر، ۴ دامنه | ۹ فیلد، ۷ عملگر، ۴ دامنه | مطابق و تأییدشده | مطابق و تأییدشده | مطابق و تأییدشده (سناریو ۸، تصاویر ۸۳ و ۸۴) | فیلترهای پیش‌فرض عمداً غیرقابل‌ویرایش‌اند | ندارد | مطابق و تأییدشده |
| Group and Sort چندسطحی | https://docs.oracle.com/cd/G48902_01/client_help/en_US/grouping_activities_by_field.htm | گفت‌وگوی Group and Sort | تا ۳ سطح گروه‌بندی + ۳ سطح ترتیب | ۳ سطح گروه‌بندی + ۳ سطح ترتیب | مطابق و تأییدشده | ناقص | پیاده‌سازی‌شده ولی آزمون‌نشده (سناریو ۹ فقط سطح اول، تصویر ۸۵) | فیلد Sort از فیلدهای چیدمان است؛ فیلد «وضعیت» در این چیدمان نیست | آزمون دو/سه‌سطحی با اسکرین‌شات | ناقص |
| تب‌های Activity Details | https://docs.oracle.com/cd/G48902_01/client_help/en_US/activity_details.htm | ناحیهٔ پایین | ۱۷ تب رسمی | ۱۷ تب رسمی + ۱ تب تقویم CUBI | مطابق و تأییدشده | ناقص | مطابق و تأییدشده (سناریو ۱۰، تصاویر ۸۶–۸۹) | تب تقویم افزودهٔ CUBI است و در Help رسمی نیست | ندارد؛ برچسب CUBI دارد | ناقص |
| باز/بستن و تغییر اندازهٔ Activity Details | https://docs.oracle.com/cd/G48902_01/client_help/en_US/using_the_status_bar_and_display_layout_options_bar.htm | Details پایین + Splitterها | ۲ Splitter | ۲ Splitter | مطابق و تأییدشده | مطابق و تأییدشده | مطابق و تأییدشده (سناریوهای ۳ و ۴، تصاویر ۷۶–۷۸) | ندارد | ندارد | مطابق و تأییدشده |
| پایداری چیدمان پس از Refresh | https://docs.oracle.com/cd/G48902_01/client_help/en_US/layout_toolbar.htm | Layout سرور + localStorage | ماندگاری Layout | ماندگاری Layout و ستون‌ها | مطابق و تأییدشده | مطابق و تأییدشده | مطابق و تأییدشده (سناریوهای ۵ و ۶، تصویر ۷۹) | انتخاب ردیف جزو Layout ذخیره‌شده نیست | ندارد | مطابق و تأییدشده |
| باندهای WBS و رنگ سطح | https://docs.oracle.com/cd/G48902_01/client_help/en_US/work_breakdown_structure.htm | جدول و گانت | سلسله‌مراتب WBS با باند رنگی | ۷ باند در پروژهٔ RPS | مطابق و تأییدشده | مطابق و تأییدشده | مطابق و تأییدشده (سناریوهای ۱ و ۹، تصویر ۷۴) | پالت رنگ مطابق سند بصری CUBI است | ندارد | مطابق و تأییدشده |
| میله‌های گانت (Summary/Task/Milestone) و برچسب لبه | https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_a_gantt_chart_bars_label_layouts.htm | Gantt | ۳ نوع میله + درصد پیشرفت + جای‌گاه برچسب | ۳ نوع میله + لایهٔ پیشرفت + برچسب آینه‌ای/داخلی در لبه | ناقص | مطابق و تأییدشده | مطابق و تأییدشده (سناریوهای ۱، ۱۴ و ۱۵، تصویر ۷۴؛ پذیرش ۲۰۲۶-۱۱-۱۲، ۶ سلول) | برچسب میله‌هایی که به لبهٔ راست می‌رسند به چپ آینه یا داخل لبه می‌روند؛ ضخامت/شکل میله‌ها هنوز کاملاً هم‌شکل مرجع نیست | تنظیم دقیق استایل در گام بصری بعدی | ناقص |
| Timescale پنج‌گانه | https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_a_layout_s_timescale_format_50.htm | نوار Gantt | ۵ مقیاس (روز/هفته/ماه/فصل/سال) | ۵ مقیاس | مطابق و تأییدشده | مطابق و تأییدشده | مطابق و تأییدشده (پذیرش گانت‌آپشنز ۲۰۲۶-۱۱-۱۲، ۲ سلول en/fa) | هر پنج مقیاس با عرض مستند ۵۲۰/۶۴۰/۸۰۰/۱۱۰۰/۱۶۰۰ و نشانه‌های واقعی آزمون شد | ندارد | مطابق و تأییدشده |
| زمینهٔ غیرکاری تقویم (Calendar nonwork time) | https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_a_gantt_chart_bar_s_settings.htm — https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_the_background_lines_in_the_gantt_chart.htm — https://docs.oracle.com/cd/G48902_01/client_help/en_US/the_gantt_chart.htm | نوار Gantt (پشت میله‌ها و خطوط شبکه) | گزینهٔ Calendar nonwork time در تنظیمات میله/خطوط پس‌زمینه | ۱۱ باند پایه در پروژهٔ RPS (۱۰ آخر هفته + ۱ تعطیل ۲۰۲۶-۱۰-۲۸) + استثناهای ذخیره‌شدهٔ تقویم از projection هستهٔ مشترک | مطابق و تأییدشده | مطابق و تأییدشده (snapshot + day-facts) | مطابق و تأییدشده (پذیرش ۲۰۲۶-۱۱-۱۲، ۶ سلول en/fa؛ e2e استثناها ۲۰۲۶-۱۱-۲۵، ۵ سناریو) | ردیف‌های `calendar_exception` محلی و ارثی اکنون از مسیر `GET .../day-facts` روی باندها اثر می‌گذارند (nonwork/تعطیل ← باند، total/detailed work hours ← حذف باند آخر هفته)؛ toggle نمایش/پنهان‌سازی وجود ندارد | افزودن toggle در گفت‌وگوی Bars | ناقص (تنها toggle) |
| راهنمای گانت (Legend) و خطوط دید | https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_the_background_lines_in_the_gantt_chart.htm — https://docs.oracle.com/cd/G48902_01/client_help/en_US/the_gantt_chart.htm | بالای/پایین نوار Gantt و پشت ردیف‌ها | راهنما بالای/پایین + خطوط دید افقی/عمودی | راهنما بالای/پایین + ۳ نوع خط دید | مطابق و تأییدشده | مطابق و تأییدشده | مطابق و تأییدشده (پذیرش گانت‌آپشنز ۲۰۲۶-۱۱-۱۲، ۲ سلول en/fa) | راهنما فقط انواع میلهٔ نمایش‌داده‌شده را می‌آورد؛ خط افقی اصلی = تعداد گروه‌های WBS، خط فرعی با فاصلهٔ ردیف | ندارد | مطابق و تأییدشده |
| گفت‌وگوی Bar Styles و خطوط | https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_a_gantt_chart_bar_s_settings.htm | گفت‌وگوی Bars | مجموعهٔ کامل گزینه‌های میله | ۳ نوع میله × شکل/رنگ/برچسب/نکینگ | ناقص | مطابق و تأییدشده برای فیلتر/نمایش هر نوع میله | مطابق و تأییدشده (پذیرش گانت‌آپشنز ۲۰۲۶-۱۱-۱۲، ۲ سلول en/fa) | فیلتر ناسازگار به میلهٔ task بازمی‌گردد؛ Add/Delete bar و برخی شکل‌ها مطابق مرجع کامل نیست | تکمیل Add/Delete و شکل‌های باقی‌مانده | ناقص |
| Progress Line | https://docs.oracle.com/cd/G48902_01/client_help/en_US/applying_a_progress_line_to_the_gantt_chart.htm | Gantt | ۱ خط پیشرفت | ۱ خط پیشرفت (SVG path با ۱۴ نقطه) | مطابق و تأییدشده | مطابق و تأییدشده | مطابق و تأییدشده (سناریو ۱۳، تصویر ۹۴) | رنگ `#c0392b` و ضخامت `3px` اعمال و سپس مخفی شد | ندارد | مطابق و تأییدشده |
| Data Date Line | https://docs.oracle.com/cd/G48902_01/client_help/en_US/customize_the_data_date_line.htm | Gantt / گفت‌وگوی Bars | ۱ خط | ۰ خط رسم‌شده | محدودیت مستند و مشخص | محدودیت مستند و مشخص | مطابق و تأییدشده (سناریو ۱۳، تصویر ۹۳) | read model پروژه Data Date ندارد؛ فیلدست غیرفعال با یادداشت صادقانه است | اتصال به تاریخ معتبر در صورت تأمین سرویس | محدودیت مستند و مشخص |
| روابط FS/SS/FF/SF | https://docs.oracle.com/cd/G48902_01/client_help/en_US/show_or_hide_relationship_lines_in_the_gantt_chart.htm | Gantt | ۴ نوع رابطه | ۴ نوع رابطه | مطابق و تأییدشده | مطابق و تأییدشده | مطابق و تأییدشده (سناریو ۱۴، تصویر ۹۵) | فقط FS/SS از دادهٔ اولیه وجود داشت؛ FF/SF موقت ساخته و حذف شد | ندارد | مطابق و تأییدشده |
| Zoom و Scroll همگام | https://docs.oracle.com/cd/G48902_01/client_help/en_US/zoom_in_and_out_of_a_timescaled_layout.htm | Gantt | Zoom in/out/fit + Scroll | Zoom in/out/fit پویا + Scroll | مطابق و تأییدشده | مطابق و تأییدشده | مطابق و تأییدشده (پذیرش گانت‌آپشنز، Fit و اسکرول ۲۰۲۶-۱۱-۱۲، ۱۰ سلول en/fa) | Fit ریزترین مقیاس جا‌شونده در پنل را می‌گیرد؛ اسکرول عمودی جدول↔گانت همگام است و هدر جدول/محور گانت ثابت می‌ماند؛ Fit پله‌ای است و pan آزاد وجود ندارد | ندارد در محدودهٔ Zoom/Scroll | مطابق و تأییدشده |
| Splitterها در ۱۰۲۴/۱۲۸۰/۱۴۴۰/۱۹۲۰ | https://docs.oracle.com/cd/G48902_01/client_help/en_US/using_the_status_bar_and_display_layout_options_bar.htm | کل چیدمان | ۲ Splitter | ۲ Splitter | مطابق و تأییدشده | مطابق و تأییدشده | مطابق و تأییدشده (سناریو ۱۶، تصاویر ۹۷ و ۹۸) | ۴ اندازه بدون سرریز افقی | ندارد | مطابق و تأییدشده |
| منوی راست‌کلیک فعالیت | https://docs.oracle.com/cd/G48902_01/client_help/en_US/use_shortcut_menus.htm | جدول (ردیف، سلول، سرستون، ناحیهٔ خالی، باند WBS)، گانت (میله، رابطه، خلاصهٔ WBS، ناحیهٔ خالی، مقیاس زمانی)، Activity Details | مجموعهٔ کامل فرمان‌های زمینه + Customize Activity Details | ۲۰ فرمان جدول + منوهای اختصاصی هر شیء + منوی Details | مطابق و تأییدشده | مطابق و تأییدشده | مطابق و تأییدشده (سناریو ۱۱، ماتریس ۸۴ بررسی `context-menus-v26`؛ بازبینی ۲۰۲۶-۱۱-۲۵ با `activity-export-assign-v26`) | Cut/Delete با دلیل واقعی غیرفعال‌اند؛ Assign/Export از ۲۰۲۶-۱۱-۲۵ فعال‌اند؛ Details فقط Customize دارد (مطابق Help) | ندارد در محدودهٔ سرویس موجود | مطابق و تأییدشده |
| میان‌برها | https://docs.oracle.com/cd/G48902_01/client_help/en_US/63783.htm | گفت‌وگوی F1 | جدول میان‌برهای مرجع | ۳۱ ردیف | مطابق و تأییدشده | ناقص | مطابق و تأییدشده برای F1/Ctrl+F/Ctrl+Numpad± (سناریو ۱۲، تصویر ۹۲) | Alt+10…18 قابل فشردن نیست؛ برچسب‌های آن‌ها حذف شد | آزمون باقی میان‌برها | ناقص |
| راست‌به‌چپ و چپ‌به‌راست | https://docs.oracle.com/cd/G48902_01/client_help/en_US/using_main_windows.htm | کل محیط | ۲ جهت | ۲ جهت (fa/en) | مطابق و تأییدشده | مطابق و تأییدشده | مطابق و تأییدشده (سناریو ۱۷، تصاویر ۹۹ و ۱۰۰) | ندارد | ندارد | مطابق و تأییدشده |
| پاکی Console/Runtime/API | — | کل جلسه | ۰ خطا | ۰ خطا | مطابق و تأییدشده | مطابق و تأییدشده | مطابق و تأییدشده (سناریو ۱۸، تصویر ۱۰۱) | ندارد | ندارد | مطابق و تأییدشده |
| شمارهٔ سطر، Table Font and Row، User Preferences | https://docs.oracle.com/cd/G48902_01/client_help/en_US/layout_toolbar.htm | گفت‌وگوهای نوار چیدمان | ۳ گفت‌وگو | ۳ گفت‌وگو | مطابق و تأییدشده | پیاده‌سازی‌شده ولی آزمون‌نشده | پیاده‌سازی‌شده ولی آزمون‌نشده | در ۱۸ سناریو کلیک نشدند | آزمون هر سه با اسکرین‌شات | ناقص |
| ذخیره/بازکردن/Undo/Redo چیدمان | https://docs.oracle.com/cd/G48902_01/client_help/en_US/layout_toolbar.htm | چیدمان ماندگار | ۴ فرمان | ۴ فرمان | مطابق و تأییدشده | ناقص | مطابق و تأییدشده برای ماندگاری (سناریوهای ۵ و ۶) | Undo/Redo در این اجرا آزمون نشد | آزمون Undo/Redo | ناقص |
| افزودن/ویرایش فعالیت | https://docs.oracle.com/cd/G48902_01/client_help/en_US/49094.htm | نوار ابزار/منوی زمینه | ۲ فرمان | ۲ فرمان با مسیر واقعی نوشتن | مطابق و تأییدشده | پیاده‌سازی‌شده ولی آزمون‌نشده | پیاده‌سازی‌شده ولی آزمون‌نشده | در ۱۸ سناریو ایجاد/ویرایش فعالیتاجرا نشد | آزمون چرخهٔ کامل نوشتن | ناقص |
| Assign Resources | https://docs.oracle.com/cd/G48902_01/client_help/en_US/assign_resources_to_activities.htm | منوی زمینهٔ ردیف + Activity Details → Resources | مسیر Help: Details → Resources → Add Resource → Assign | منوی زمینه (فرم ایجاد تخصیص با فعالیت پیش‌پُرشده) + همان فرم واقعی در تب Resources | مطابق و تأییدشده | مطابق و تأییدشده | مطابق و تأییدشده (سناریو ۰۳ در `activity-export-assign-v26`، ۲۰۲۶-۱۱-۲۵) | CUBI فرمان را در منوی زمینه هم می‌آورد و به پنجرهٔ تخصیص‌های خودش می‌برد؛ Help آن را از تب Resources می‌خواهد. هر دو مسیر به همان سرویس نوشتن اصلی می‌رسند و هیچ تخصیصی از مرورگر ساخته نمی‌شود | ندارد در محدودهٔ سرویس موجود | مطابق و تأییدشده |
| Export to Excel | https://docs.oracle.com/cd/G48902_01/client_help/en_US/use_shortcut_menus.htm — topic «Copy and paste resource spreadsheet data to Microsoft Excel» | منوی زمینهٔ ردیف | انتقال دادهٔ فعالیت به Excel با Range Copy/Paste | یک فرمان یک‌مرحله‌ای XLSX از همان facts معتبر | مطابق و تأییدشده | مطابق و تأییدشده | مطابق و تأییدشده (سناریو ۰۲ در `activity-export-assign-v26`، ۲۰۲۶-۱۱-۲۵) | Help نسخهٔ v26 فرمان «Export to Excel» ندارد؛ مسیر رسمی کپی/چسباندن است. CUBI همان داده را با سرویس Exchange و هش پاسخ به‌صورت XLSX می‌دهد؛ این یک افزودهٔ مستند CUBI است، نه ادعای فرمان P6 | دارد: تفاوت فرمان در بخش «افزایش ۲۰۲۶-۱۱-۲۵» ثبت شد | مطابق و تأییدشده |
| Cut/Copy/Paste/Fill Down | https://docs.oracle.com/cd/G48902_01/client_help/en_US/quickly_enter_the_same_text_in_multiple_table_rows_2.htm | منوی زمینه | ۴ فرمان | ۴ فرمان با کلیپ‌بورد نشست | ناقص | محدودیت مستند و مشخص | محدودیت مستند و مشخص (سناریو ۱۱ موجود بودن را دید) | ماندگاری کلیپ‌بورد میان نشست‌ها وجود ندارد | ذخیره‌سازی در صورت نیاز | محدودیت مستند و مشخص |
| تب‌های UDFs/Steps/Tasks/Codes/Expenses/Risks | https://docs.oracle.com/cd/G48902_01/client_help/en_US/activity_details.htm | Activity Details | ۶ تب دادهٔ تکمیلی | ۶ تب با empty-state صادقانه | مطابق و تأییدشده | محدودیت مستند و مشخص | مطابق و تأییدشده (سناریو ۱۰، تصاویر ۸۶–۸۹) | محتوا بیش‌تر «Not available» صادقانه است | اتصال به سرویس‌های تکمیلی | محدودیت مستند و مشخص |

## شواهد ۱۸ سناریوی الزامی

| # | سناریو | نتیجه | تصاویر | دادهٔ کلیدی شواهد |
| --- | --- | --- | --- | --- |
| ۱ | بازکردن پنجره Activities | PASS | 74 | ۱۴ فعالیت، ۱۴ ردیف گانت، ۷ باند، ۱۷ تب رسمی، ۱۷ میله |
| ۲ | انتخاب فعالیت و هماهنگی جدول/Gantt/Details | PASS | 75 | A130 در هر سه ناحیه |
| ۳ | باز و بسته کردن Activity Details | PASS | 76، 77 | closed=false، reopened=true |
| ۴ | تغییر ارتفاع و عرض نواحی | PASS | 78 | table 50%→60.18%، details 70%→75.30% |
| ۵ | Refresh و پایداری Layout | PASS | 79 | همان split و همان ترتیب ردیف‌ها |
| ۶ | تغییر عرض و جابه‌جایی ستون‌ها | PASS | 80، 81 | Activity ID به جای اول، عرض ۲۱۰، پایدار پس از reload |
| ۷ | اعمال و ترکیب فیلترها | PASS | 82 | In Progress=[A130]؛ ترکیب Any با Critical=۷ ردیف؛ برچسب و شناسهٔ فیلتر |
| ۸ | ایجاد و ویرایش فیلتر | PASS | 83، 84 | ساخت «Civil open»، ویرایش به ۳ ردیف، بازخوانی نام |
| ۹ | Group و Sort | PASS | 85 | گروه WBS، ترتیب نزولی، ماندگاری پس از reload |
| ۱۰ | بازکردن تمام ۱۷ تب | PASS | 86–89 | ۱۸ تب موجود، ۱۷ رسمی، همهٔ پنل‌ها فعال |
| ۱۱ | راست‌کلیک در تمام نواحی | PASS | 90، 91 | ۲۰ فرمان؛ جدول/گانت/WBS/ناحیهٔ خالی باز شد؛ Details منوی Customize Activity Details داد |
| ۱۲ | میان‌برهای تأییدشده | PASS | 92 | F1، Ctrl+F، Ctrl+Numpad−/+ با کاهش ۰→۶ و بازگشت به ۰ |
| ۱۳ | Data Date Line و Progress Line | PASS | 93، 94 | Data Date غیرفعال با یادداشت صادقانه؛ خط پیشرفت ۱، ۱۴ نقطه، رنگ و ضخامت اعمال، سپس ۰ |
| ۱۴ | چهار نوع رابطه | PASS | 95 | قبل FS=14/SS=1؛ بعد FS=14/SS=1/FF=1/SF=1؛ بازگشت به ۲۱ رابطه |
| ۱۵ | Zoom و Scroll | PASS | 96 | month→week→month، tick 4→11→4، scrollLeft 0→240 |
| ۱۶ | Splitter در ۴ اندازه | PASS | 97، 98 | ۱۰۲۴/۱۲۸۰/۱۴۴۰/۱۹۲۰ بدون سرریز افقی |
| ۱۷ | RTL و LTR | PASS | 99، 100 | fa/rtl و en/ltr برای سند و جدول |
| ۱۸ | خطای Console و Runtime | PASS | 101 | ۰ exception، ۰ console error، ۰ پاسخ ۵xx |

## افزایش برابری منوهای زمینه و Customize Activity Details (PR #1732)

شواهد: `apps/web/e2e/artifacts/context-menus-v26/context-menus-v26.json` و کپی پایدار در `docs/workspace/evidence/context-menus-v26-2026-11-09/`؛ تصاویر در `docs/workspace/screenshots/context-menus-v26/`.

- **حذف کامل نوار فرمان مصنوعی:** `.cp-context-command-bar` و سرصفحهٔ قدیمی جدول از markup و CSS حذف شدند؛ بدنهٔ پنجره یک ردیف شبکه‌ای دارد و هیچ ردیف فرمان/جداکنندهٔ جای‌گزین ساخته نشد. فرمان‌ها به مکان واقعی خود بازگردانده شدند: افزودن فعالیت، Columns، WBS، Layout Options و بازنشانی‌ها در سرصفحهٔ جدول/گانت، و Tools از ریل چپ.
- **پنجرهٔ منو در سطح viewport:** منو در `document.body` و با `position: fixed` دقیقاً در مختصات اشاره‌گر باز می‌شود؛ در لبه‌های راست/پایین برمی‌گردد و با حاشیهٔ ۴ پیکسل در viewport می‌ماند. اسکرول منو را نمی‌بندد؛ Escape، Tab و کلیک بیرون آن را می‌بندند و تمرکز به لنگر بازمی‌گردد. Shift+F10 / کلید ContextMenu منو را روی کنترل متمرکز باز می‌کند و اولین فرمان را فوکوس می‌دهد؛ بازکردن با ماوس فوکوس را جابه‌جا نمی‌کند.
- **منوی اختصاصی هر شیء:** ردیف/سلول جدول، سرستون، ناحیهٔ خالی جدول، باند WBS، میلهٔ گانت، خط رابطه (با نوار برخورد نامرئی ۸ پیکسلی)، خلاصهٔ WBS در گانت، ناحیهٔ خالی گانت و سرصفحهٔ مقیاس زمانی هرکدام فقط فرمان‌های شیء خود را دارند؛ فرمان‌های فعالیت روی اشیای نامرتبط نمایش داده نمی‌شوند.
- **گفت‌وگوهای واقعی:** Columns از منوی زمینه/نوار ابزار گفت‌وگوی واقعی Columns را باز می‌کند؛ Customize Activity Details از راست‌کلیک ناحیهٔ Details با دو فهرست Available/Display، افزودن/حذف/افزودن همه/حذف همه/بالا/پایین/Default/Apply/OK/Cancel باز می‌شود، ترتیب را در پنل زنده اعمال می‌کند و پس از reload در `localStorage` می‌ماند.
- **وضعیت صادقانه:** Cut/Delete/Paste/Fill Down/Dissolve/Renumber با دلیل واقعی محلی غیرفعال‌اند چون مسیر نوشتن/خروجی متناظر در سرویس وجود ندارد؛ خط رابطه Delete با تأیید و revision واقعی کار می‌کند. Export to Excel و Assign از ۲۰۲۶-۱۱-۲۵ فعال شده‌اند (بخش «افزایش ۲۰۲۶-۱۱-۲۵» را ببینید) و Delete فعالیت همچنان غیرفعال است چون core هیچ repository delete/route ندارد.
- **آزمون:** ماتریس زندهٔ ۸۴ بررسی در `en/LTR` و `fa/RTL` و سه اندازهٔ ۱۲۸۰×۸۰۰، ۱۴۴۰×۹۰۰ و ۱۹۲۰×۱۰۸۰ تمام‌شد؛ متریک‌های بصری (ارتفاع ردیف ۲۲px، Tahoma، کادر `#7f9db9`)، چرخش/مهار لبه، عدم بسته‌شدن با اسکرول، Escape، Shift+F10، منوهای هر شیء، دیالوگ Columns، Customize + ماندگاری و RTL بررسی شدند.

## نقص‌های واقعی که در این افزایش کشف و اصلاح شد

1. **گفت‌وگوی Filters پس از OK باز می‌ماند (نقص واقعی محصول).** هنگام تغییر فیلتر، `renderDesktopShell` گفت‌وگوی باز را snapshot و دوباره باز می‌کرد، سپس هندلر submit آن را می‌بست و نتیجه «OK بی‌اثر» دیده می‌شد. اصلاح: بستن گفت‌وگو پیش از اعمال patch در `apps/web/src/workspace-desktop-shell.ts`. شاهد: سناریو ۷ — گفت‌وگو بسته شد و فیلتر ترکیبی اعمال شد.
2. **میان‌بر Alt+10…18 در جدول Help تبلیغ می‌شد ولی هندلر فقط Alt+1…9 را می‌گرفت.** اصلاح: فقط برای ۹ پنجرهٔ اول میان‌بر نمایش داده می‌شود (`index < 9`) و آزمون واحد افزوده شد. این تغییر از نمایش یک affordance بی‌اثر جلوگیری می‌کند.

## پذیرش بصری مستقل ۲۰۲۶-۱۱-۱۲ (کد `9378378`، شاهد `77f7b67`)

- **افزایش تقویم‌آگاهی Gantt:** زمینهٔ روزهای غیرکاری مستقیماً از snapshot نسخه‌بند‌شدهٔ تقویم اصلی پروژه می‌آید (`calendar_snapshot`: `workingWeekdays` و `holidays`)؛ هیچ روز کاری از تاریخ‌های برنامه استنتاج نمی‌شود. `createGanttNonWorkingBands` روزهای پیوسته را در یک باند ادغام، باندها را به محدودهٔ دید برش و حداقل عرض ۰٫۰۵٪ اعمال می‌کند؛ اگر تقویم روز کاری اعلام‌نشده داشته باشد (`CALENDAR_WORKWEEK_MISSING`) هیچ سایه‌ای رسم نمی‌شود. مسیر خواندن: `apps/web/src/workspace-read-api.ts` (`primaryCalendarId` → `readProjectCalendar` → `loadCalendarSnapshot`)؛ رندر: `apps/web/src/workspace-view.ts` (`renderGantt`). هیچ تاریخ زمان‌بندی دوباره محاسبه نمی‌شود. (به‌روزرسانی ۲۰۲۶-۱۱-۲۵: استثناهای ذخیره‌شدهٔ تقویم نیز از مسیر day-facts به همین باندها اضافه شدند — بخش «اتصال استثناهای تقویم به باندهای گانت ۲۰۲۶-۱۱-۲۵».)

- **ابزار:** `apps/web/e2e/workspace-visual-acceptance-v26.mjs` (قرارداد `cubi-workspace-visual-acceptance-v26.v1`).
- **سلول‌ها:** ۱۲۸۰×۷۲۰، ۱۳۶۶×۷۶۸ و ۱۹۲۰×۱۰۸۰ در `en/LTR` و `fa/RTL`؛ هر سلول: Activities، دیالوگ Columns، و جزئیات پس از تغییر اندازهٔ Splitter. تعویض پنجره (Reports و بازگشت به Activities) در سلول ۱۳۶۶×۷۶۸/en.
- **سنجه‌های هر سلول (همه PASS):** `documentScrollWidth ≤ viewport`، نوار فرمان و نوار ابزار داخل viewport، دستهٔ فرمان جدول/گانت داخل سرصفحه بدون سرریز، Details داخل viewport و بزرگ‌تر از ۴۰px، ارتفاع ردیف جدول = ارتفاع ردیف گانت، اختلاف افست ردیف اول ≤ ۱px، ۷ باند WBS و ۱۴/۱۴ ردیف، ۲۱ برچسب میله و صفر برچسب بیرون از محتوای ترسیم‌شده، صفر برچسب لبه‌ای حل‌نشده، **۱۱ باند غیرکاری در هر سلول (۱۰ آخر هفته + ۱ تعطیل رسمی `2026-10-28`)، صفر باند بیرون از محدودهٔ ترسیم‌شده (`outside=0`)**، و صفر exception/console error/HTTP 5xx.
- **نقص واقعی کشف‌شده و اصلاح‌شده:** میله‌ای که به لبهٔ راست محتوای گانت می‌رسد، برچسب `right/above/below` را بیرون از محتوای قابل‌اسکرول می‌برد و مرورگر آن را می‌بُرید (تصویر قبلی `apps/web/e2e/artifacts/05-workspace-1920x1080.png`). اصلاح: `resolveGanttLabelPosition` در `apps/web/src/workspace-gantt.ts` برچسب را به چپ آینه می‌کند، و اگر میله از لبهٔ چپ هم شروع شود (مثل خلاصهٔ WBS تمام‌عرض) آن را به داخل لبهٔ پایان منتقل می‌کند؛ جای‌گاه‌های `inside-*` بدون تغییر می‌مانند. آزمون واحد و رندر در `workspace-gantt.test.ts` و `workspace-view.test.ts` افزوده شد.
- **شواهد:** `docs/workspace/evidence/visual-acceptance-v26-2026-11-12/` شامل JSON و ۲۱ PNG، از جمله `activities-1920x1080-en.png`، `activities-1920x1080-fa.png`، `details-resized-1366x768-fa.png` و `window-switch-reports-1366x768-en.png`.
- **محدودیت:** این اجرا مالکیت بصری/چیدمان را می‌سنجد و ادعای تطابق کامل رفتار یا محتوای همهٔ ۱۷ تب Details را نمی‌کند.

## اتصال استثناهای تقویم به باندهای گانت ۲۰۲۶-۱۱-۲۵

- **مسئله:** باندهای غیرکاری فقط از snapshot نسخه‌بند‌شده ساخته می‌شدند؛ ردیف‌های `calendar_exception` (از جمله استثناهای ارثی از تقویم پایه) در Activities دیده نمی‌شدند.
- **راه‌حل بدون تکرار منطق:** endpoint جدید `GET /api/projects/{project_id}/p6/calendars/{calendar_id}/{calendar_version}/day-facts` با قرارداد `p6-calendar-day-facts.v1` در `src/construction_pm/p6_calendar_day_facts_api.py`. این projection همان registry و resolverهای Shared Calculation Core را به کار می‌برد (زنجیرهٔ ارثی، قواعد ساعات کاری هفتگی، حالت‌های چهارگانهٔ استثنا) و فقط تاریخ‌های دارای استثنا را برمی‌گرداند؛ هیچ محاسبهٔ موازی در مرورگر نیست.
- **رابط کاربری:** `loadCalendarDayFacts` در `apps/web/src/workspace-calendars.ts` پاسخ را اعتبارسنجی می‌کند؛ `workspace-read-api.ts` آن را به `workingDates`/`nonWorkingDates` تبدیل می‌کند و `createGanttNonWorkingBands` با تقدم «workingDates ← حذف باند» و «nonWorkingDates/holiday ← باند تعطیل» رسم می‌کند. خطای projection سایه‌ی استثنا را حذف می‌کند و باندهای snapshot را دست‌نخورده نگه می‌دارد (`dayFactsErrorCode`).
- **آزمون‌ها:** ۱۱ آزمون API در `tests/test_p6_calendar_day_facts_api.py` (حالت‌های چهارگانه، ارثی، محلی بر ارثی، تقویم زمان‌کاری، خطاهای مرجع/دسترسی/دامنه)؛ مسیر HTTP در `tests/test_project_lifecycle_http_routes.py`؛ آزمون‌های گانت/read-api/view در وب (کل مجموعه: ۱۳۶۵ PASS + ۱۶ preview-server).
- **پذیرش مرورگر:** `apps/web/e2e/gantt-calendar-exceptions-v26.mjs` (قرارداد `cubi-gantt-calendar-exceptions-v26.v1`)، ۵ سناریو PASS: پایه، nonwork روی ۲۰۲۶-۱۱-۰۵، total-work-hours روی شنبه ۲۰۲۶-۱۰-۳۱، حذف و بازگشت، و صفر exception/۵xx. شواهد: `docs/workspace/evidence/gantt-calendar-exceptions-v26-2026-11-25/`.
- **محدودیت:** toggle نمایش/پنهان‌سازی Calendar nonwork time هنوز وجود ندارد؛ این افزایش فقط اتصال داده را کامل می‌کند.

## پذیرش گانت‌آپشنز ۲۰۲۶-۱۱-۱۲ (کد `b20501f`، شاهد `7ea89d5`)

- **ابزار:** `apps/web/e2e/gantt-options-v26.mjs` (قرارداد `cubi-gantt-options-v26.v1`) در `1366×768` برای `en/LTR` و `fa/RTL`.
- **راهنما:** نمایش بالای نمودار، جابه‌جایی به پایین، ۷ آیتم برای ۷ نوع میلهٔ نمایان، دست‌کم ۴ رنگ متمایز، و حذف آیتم هنگام پنهان‌کردن نوع میله. شاهد: ۲۲ تصویر در `docs/workspace/evidence/gantt-options-v26-2026-11-12/`.
- **خطوط دید:** خط افقی اصلی = ۷ گروه WBS، خط افقی فرعی با فاصلهٔ ۲ ردیف = ۱۰ خط روی ۲۱ ردیف نمودار، و خط عمودی فرعی = همهٔ نشانه‌ها به‌جز نشانهٔ لبهٔ چپ.
- **فیلتر هر میله:** فیلتر ناسازگار `milestone` روی میلهٔ `critical` آن را حذف و به میلهٔ `task` بازمی‌گرداند (۶+۷ = ۱۳ میلهٔ task، مجموع ۱۷ بدون تغییر)؛ پنهان‌کردن `critical` همان بازگشت و حذف یک آیتم از راهنما را می‌دهد.
- **پنج مقیاس:** سال/فصل/ماه/هفته/روز با عرض محتوای ۵۲۰/۶۴۰/۸۰۰/۱۱۰۰/۱۶۰۰ و ۱/۲/۴/۱۱/۳۸ نشانه؛ ویرایش فقط‌قالب سربرگ، مقیاس انتخاب‌شده را بازنشانی نمی‌کند و تغییر فاصله، چگالی متناظر را انتخاب می‌کند.
- **Zoom/Fit و جمع‌شدن WBS:** zoom in/out بین ماه/فصل جابه‌جا می‌شود، Collapse All/Expand All ردیف‌ها را ۱۴→۰→۱۴ با حفظ ۷ گروه WBS و بدون سرریز افقی برمی‌گرداند. (Fit در این اجرا هنوز به ماه می‌رفت؛ در بخش بعدی اصلاح و اثبات شد.)
- **دو نقص واقعی کشف و اصلاح‌شده:** (۱) راهنمای پایین با `position: sticky` روی ردیف‌های انتهایی نمودار می‌نشست و آن‌ها را می‌پوشاند؛ اکنون فضای خود را زیر نمودار می‌گیرد. (۲) گفت‌وگوی Timescale یک انتخاب «Scale» تکراری داشت که با فاصلهٔ سربرگ بازنویسی می‌شد و با هر OK مقیاس را بی‌صدا به ماه بازمی‌گرداند؛ کنترل تکراری حذف شد و فقط تغییر واقعی فاصله، مقیاس را جابه‌جا می‌کند.
- **محدودیت باقی‌مانده:** همگامی اسکرول افقی/عمودی و کشیدن (pan) در این اجرا سنجیده نشد.

## پذیرش Fit پویا ۲۰۲۶-۱۱-۱۲ (کد `08302a5`، شاهد `f2523c1`)

- **نقص پیشین:** فرمان Fit همیشه مقیاس ماه را انتخاب می‌کرد؛ در پنل باریک‌تر از ۸۰۰px اسکرول افقی می‌ساخت و پهنای واقعی پنل را در نظر نمی‌گرفت.
- **اصلاح:** تابع `fitGanttScale` در `apps/web/src/workspace-gantt.ts` همراه با جدول عرض‌های `GANTT_CONTENT_WIDTH` (روز ۱۶۰۰، هفته ۱۱۰۰، ماه ۸۰۰، فصل ۶۴۰، سال ۵۲۰) ریزترین مقیاسی را برمی‌گرداند که تمام تایم‌لاینش در پنل دیده‌شده جای می‌گیرد؛ سال کف است و پنل چیده‌نشده (۰/NaN) به ماه برمی‌گردد. `view.fit` در `apps/web/src/main.ts` عرض واقعی `#cp-gantt .cp-gantt-chart` را می‌خواند.
- **ابزار:** `apps/web/e2e/gantt-fit-v26.mjs` (قرارداد `cubi-gantt-fit-v26.v1`) در ۱۳۶۶×۷۶۸ و ۱۹۲۰×۱۰۸۰ برای `en/LTR` و `fa/RTL`.
- **نتایج هر ۴ سلول PASS:** پنل ۶۳۸px→`year` (۵۲۰≤۶۳۸) و پنل ۹۱۵px→`month` (۸۰۰≤۹۱۵)؛ مقیاس انتخاب‌شده همیشه جا می‌شود، هیچ مقیاس ریزتری جا می‌شد ولی انتخاب نشد، و اگر محتوا از پنل پهن‌تر باشد (سال در پنل باریک) نمودار همچنان تا انتهای محتوا اسکرول می‌شود؛ صفر exception/console error/HTTP 5xx. تصاویر: `docs/workspace/evidence/gantt-fit-v26-2026-11-12/`.
- **آزمون واحد:** `fitGanttScale` در `apps/web/src/workspace-gantt.test.ts` مرزهای ۱۶۰۰/۱۱۰۰/۸۰۰/۶۴۰/۵۲۰ و حالت‌های ۰/NaN را می‌سنجد.
- **محدودیت باقی‌مانده:** Fit فقط بین پنج مقیاس مستند انتخاب می‌کند (نه پیوسته)؛ اسکرول همگام در بخش بعدی همین سند آزمون شد و pan آزاد هنوز پیاده‌سازی نشده است.

## پذیرش اسکرول همگام جدول و گانت ۲۰۲۶-۱۱-۱۲ (کد `eaf2d91`، شاهد `4156d22`)

- **نقص واقعی کشف‌شده:** قاعدهٔ `.cp-p6 #cp-activity-grid thead th[data-column-id] { position: relative; }` بر `position: sticky` سرستون‌ها غلبه می‌کرد و با اسکرول عمودی، سرستون‌های داده از دید خارج می‌شدند در حالی که محور زمان گانت ثابت می‌ماند. `position: sticky` خودش بلوک شامل دسته‌های تغییر عرض است، بنابراین قاعدهٔ اضافی حذف شد (هر دو نسخهٔ `apps/web/styles.css` و `apps/web/public/styles.css`). آزمون واحد CSS در `apps/web/src/workspace-presentation-css.test.ts` افزوده شد.
- **ابزار:** `apps/web/e2e/gantt-scroll-sync-v26.mjs` (قرارداد `cubi-gantt-scroll-sync-v26.v1`) در ۱۲۸۰×۷۲۰ و ۱۳۶۶×۷۶۸ برای `en/LTR` و `fa/RTL`.
- **نتایج هر ۴ سلول PASS:** اسکرول نیمهٔ جدول، گانت را به همان ردیف می‌برد (اختلاف ردیف‌ها ≤۱px)؛ بازگشت گانت به بالا، جدول را برمی‌گرداند؛ در انتهای هر دو پنل، آخرین ردیف جدول و آخرین میله کامل دیده می‌شوند؛ هدر جدول و محور گانت در تمام اسکرول ثابت می‌مانند؛ اسکرول افقی گانت تا انتهای تایم‌لاین (مثلاً ۱۰۰۵ از ۱۶۰۰px در پنل ۵۹۵px؛ در RTL مقدار منفی ۱۰۱۰) جدول را جابه‌جا نمی‌کند و محور بالای نمودار می‌ماند؛ صفر exception/console error/HTTP 5xx. تصاویر: `docs/workspace/evidence/gantt-scroll-sync-v26-2026-11-12/`.
- **محدودیت باقی‌مانده:** اختلاف ردیف‌ها در حال اسکرول تا ۱px است (گِردکردن زیرپیکسلی)؛ Fit پله‌ای است و pan آزاد (کشیدن با ماوس) وجود ندارد.

## افزایش فعال‌سازی فرمان‌های زمینه با مسیر سرویس موجود — ۲۰۲۶-۱۱-۲۵

**مبنای کد:** `1593e6027` (آخرین `origin/main` پیش از این افزایش) — شاخهٔ `feat/engineering-activities-v26-commands`.

**کشف واقعی (پیش از تغییر):** در منوی زمینهٔ ردیف Activities، فرمان‌های `Export to Excel` و `Assign` با دلیل «مسیر سرویس وجود ندارد» غیرفعال بودند، در حالی که:
- سرویس Exchange از پیش `GET /api/projects/{id}/exchange/export?dataset=activities&format=xlsx` را با `Content-Disposition` و `X-Content-SHA256` برمی‌گرداند؛
- سرویس نوشتن تخصیص (`P6ResourceWriteAPI`) و فرم واقعی ایجاد تخصیص در پنجرهٔ Assignments از پیش وجود داشت؛
- فرمان `Filters` در منوی زمینه به‌جای بازکردن گفت‌وگوی Filters، جعبهٔ جستجو را فوکوس می‌کرد (سیم‌کشی نادرست).

**اصلاحات محصول (نه مستندسازی تنها):**
- `apps/web/src/workspace-activity-export.ts` (جدید): فرمان از سرویس معتبر دانلود می‌کند، نام فایل را از `Content-Disposition` (شامل `filename*=UTF-8''`) می‌خواند، SHA-256 بدنه را با WebCrypto دوباره حساب می‌کند و با سرآیند `X-Content-SHA256` مقایسه می‌کند؛ عدم تطابق هش، بدنهٔ خالی و نبود قابلیت دانلود در transport به خطای صریح می‌رسند و فایلی پیشنهاد نمی‌شود. هیچ سلول شبکه در مرورگر به workbook تبدیل نمی‌شود.
- `apps/web/src/main.ts`: فرمان `edit.export-excel` نتیجه را با اعلان `filename · bytes · digest verified` گزارش می‌کند؛ فرمان `activity.assign-resources` پنجرهٔ Assignments را فعال، فرم ایجاد را باز و فعالیت انتخاب‌شده را پیش‌پُر می‌کند (بدون نوشتن خودکار).
- `apps/web/src/workspace-view.ts`: دو آیتم از فهرست غیرفعال خارج شدند؛ فرمان `filters` به `openDesktopDialog(desktopHost, "filters")` وصل شد.
- `apps/web/src/workspace-desktop-shell.ts`: `DesktopCommand` شامل `edit.export-excel` شد.

**Crosswalk با مرجع v26:** HTML Help مرجع تصمیم است (`G48902_01`، اکتبر ۲۰۲۶). فایل Help 815 (`G57535-02`، ۹ اکتبر ۲۰۲۶، ۸۱۵ صفحه) برای شمارهٔ صفحهٔ فیزیکی استفاده شده است؛ شماره‌های چاپ‌شده در فهرست PDF با شمارهٔ صفحهٔ فیزیکی اختلاف offset دارند، بنابراین در این جدول **صفحهٔ فیزیکی PDF** ذکر می‌شود. عنوان موضوع‌ها بین HTML و PDF تطبیق داده شد؛ هر موردی که در PDF معادل نداشت، صریح علامت خورده است.

| رفتار مرجع (v26) | نشانی HTML Help | Help 815 (صفحهٔ فیزیکی) | رفتار CUBI | تفاوت |
| --- | --- | --- | --- | --- |
| منوی زمینه با کلیک راست در هر شیء پنجره | <https://docs.oracle.com/cd/G48902_01/client_help/en_US/use_shortcut_menus.htm> | ۳۸ | منوی زمینهٔ ردیف/سلول/سرستون/باند/گانت/Details؛ منوی viewport با Escape/Tab/کلیک بیرون بسته می‌شود | ندارد |
| ویرایش/فیلتر/گروه‌بندی/مرتب‌سازی جدول فعالیت | <https://docs.oracle.com/cd/G48902_01/client_help/en_US/activitytable.htm> | ۳۲۹–۳۳۱ | همان جدول با گفت‌وگوهای Columns/Filters/Group and Sort | ندارد |
| تخصیص منبع از Activity Details → Resources → Add Resource | <https://docs.oracle.com/cd/G48902_01/client_help/en_US/assign_resources_to_activities.htm> | ۲۱۹ (و دیالوگ Assign Resources ص ۵۳۹) | تب Resources همان فهرست معتبر را می‌خواند و فرم «Add assignment» را دارد؛ فرمان زمینه نیز فرم پنجرهٔ Assignments را با فعالیت پیش‌پُر می‌کند | Help فقط مسیر تب Resources را می‌گوید؛ فرمان زمینه یک افزودهٔ CUBI است، اما هر دو به همان سرویس نوشتن می‌رسند |
| انتقال دادهٔ فعالیت به Excel | <https://docs.oracle.com/cd/G48902_01/client_help/en_US/use_shortcut_menus.htm> و موضوع «Copy and paste resource spreadsheet data to Microsoft Excel» | ۲۰۸ (کپی/چسباندن فعالیت)، ۳۷۰ و ۷۴۵ (کپی دادهٔ spreadsheet به Excel) | فرمان یک‌مرحله‌ای Export to Excel که workbook معتبر را با هش تأییدشده دانلود می‌کند | P6 v26 فرمان Export to Excel ندارد و مسیر رسمی Range Copy/Paste است؛ CUBI قابلیت را با یک فرمان و همان facts ارائه می‌کند |
| حذف فعالیت | <https://docs.oracle.com/cd/G48902_01/client_help/en_US/activitytable.htm> | ۲۰۶ | فرمان Delete با دلیل واقعی غیرفعال است | core هیچ repository delete/route برای فعالیت ندارد؛ این شکاف در GAP-V26-02 ثبت شده و ساخت آن نیازمند تصمیم دامنه است |
| Activity Details و تب‌های آن | <https://docs.oracle.com/cd/G48902_01/client_help/en_US/activity_details.htm> | ۴۱ و ۳۲۸ | ۱۷ تب رسمی + تب تقویم CUBI | ندارد؛ تب تقویم افزودهٔ CUBI است |

**شواهد اجرا (مرورگر واقعی، runtime محلی SQLite، بدون mock):**
- `apps/web/e2e/activity-export-assign-v26.mjs` — ۴ سناریو، **۴/۴ PASS**، `exceptions=0`، `consoleErrors=0`، `apiFailures=0`.
- سناریو ۰۲: دانلود واقعی `activities.xlsx` با ۶٬۰۱۶ بایت؛ SHA-256 فایل دانلودشده با `X-Content-SHA256` پاسخ سرور و با هش محاسبه‌شده از بدنهٔ پاسخ برابر است؛ اعلان «digest verified» در رابط دیده شد.
- سناریو ۰۳: پنجرهٔ Assignments فعال، فرم ایجاد باز، مقدار `activity-id` برابر فعالیت انتخاب‌شده (`A110`)؛ تعداد تخصیص‌های ذخیره‌شده قبل و بعد از فرمان ۰→۰ (هیچ رکورد جعلی/خودکار ساخته نشد).
- شواهد: `apps/web/e2e/artifacts/activity-export-assign-v26/` و کپی پایدار `docs/workspace/evidence/activity-export-assign-v26-2026-11-25/` (JSON + ۳ تصویر).
- آزمون سرور: `tests/test_exchange_api.py::test_activities_workbook_export_carries_a_verifiable_digest` — ۲۰۰، نوع `spreadsheetml.sheet`، `activities.xlsx`، برابری هش سرآیند با بدنه، و ۴۰۱/۴۰۳ بدون نشست.
- آزمون واحد وب: `apps/web/src/workspace-activity-export.test.ts` — ۷ مورد (قرارداد مسیر، پارس filename، traversal، هش درست/نادرست، بدنهٔ خالی، transport بدون دانلود، خطای سرور).
- مجموعه‌ها پس از تغییر: `npm test` → ۱۳۵۹/۱۳۵۹ و ۱۶/۱۶؛ `tsc` و `esbuild` موفق؛ Python → **۵۲۹۵ passed، ۲۷۰ skipped، ۰ failed** (آزمون‌های DSN-gated در این محیط skip شدند).

**محدودیت‌ها:** این افزایش ادعای parity عددی یا پوشش کامل همهٔ فرمان‌های منو را نمی‌کند. Export یک افزودهٔ CUBI با مسیر رسمی متفاوت است؛ Delete فعالیت بدون قابلیت core انجام نشد؛ Preview ≠ Production و هیچ تغییر Production/Supabase انجام نشده است.

## محدودیت‌های صریح باقی‌مانده (بدون ادعای تطابق کامل)

- Data Date معتبر در read model پروژهٔ پیش‌نمایش وجود ندارد؛ خط رسم نمی‌شود و در گفت‌وگو با یادداشت صادقانه غیرفعال است.
- At Complete Duration، Activity Calendar، Duration Type و Responsible Manager در read model فعلی برنمی‌گردند؛ «Not available» نمایش داده می‌شوند و هرگز با فیلد دیگری مانند Scheduled Duration پر نمی‌شوند.
- منوی زمینه در پنل Details فقط فرمان «Customize Activity Details…» را دارد (مطابق Help)؛ فرمان‌های فعالیت در جدول، گانت، باند WBS و ناحیهٔ خالی جدول کار می‌کنند.
- نوشتن تخصیص منبع، خروجی XLSX، ماندگاری کلیپ‌بورد میان نشست‌ها و دادهٔ کامل تب‌های تکمیلی سرویس واقعی ندارند و صادقانه غیرفعال/خالی‌اند. (به‌روزرسانی ۲۰۲۶-۱۱-۲۵: نوشتن تخصیص و خروجی XLSX از مسیر واقعی فعال و در مرورگر آزمون شدند؛ کلیپ‌بورد و تب‌های تکمیلی همچنان محدودیت دارند.)
- Group & Sort تا ۳ سطح ذخیره می‌شود، اما در این اجرا فقط سطح اول آزمون شد.
- Fit پله‌ای است (پنج مقیاس مستند)، نه پیوسته؛ pan آزاد (کشیدن با ماوس) هنوز پیاده‌سازی/آزمون نشده است. همگامی عمودی جدول/گانت و اسکرول افقی گانت با هدر و محور ثابت آزمون شد.
- زمینهٔ روزهای غیرکاری از snapshot تقویم اصلی پروژه و projection روزبهروز هستهٔ مشترک می‌آید؛ ردیف‌های `calendar_exception` ذخیره‌شده (محلی و ارثی) اکنون روی باندها اثر می‌گذارند؛ toggle نمایش/پنهان‌سازی هنوز وجود ندارد.
- Undo/Redo چیدمان، Table Font and Row، Line Numbers و User Preferences در این اجرا کلیک نشدند.
- تطابق آیکون‌ها هم‌معناست، نه پیکسل‌به‌پیکسل؛ هیچ ادعای pixel parity مطرح نیست.
- این سند روی `main` به‌روزرسانی شده است؛ شواهد پیشین که روی شاخهٔ اختصاصی تولید شده‌اند با SHA همان اجرا نقل می‌شوند. هیچ انتشار Production انجام نشده است.
