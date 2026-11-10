# ممیزی تطبیقی پنجره‌ها و اجزای محیط کار CUBI با Help نسخه ۲۶

- تاریخ ممیزی: 2026-11-10
- شاخه مبنا: `main`
- SHA مبنا: `1014b9db0e0cd54d47e7cc95d620cffe9ba353c7`
- هدف: ثبت کمبودهای پوسته و اجزای قابل مشاهده/انتخاب کاربر؛ بدون تغییر کد اجرایی
- وضعیت این سند: **مرحله ۱ ـ تطبیق منبع، کد و شواهد موجود**. این سند ادعای تأیید تصویری تمام پنجره‌ها در مرورگر را ندارد.

## 1. مرجع قطعی و روش

مرجع اصلی، Help کامل HTML نسخه ۲۶ با شناسه مستند G57535-02 و نسخه PDF دارای ۸۱۵ صفحه است:

- Help HTML کامل: https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm
- PDF رسمی Help (۸۱۵ صفحه): https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-help/p6-professional-help.pdf
- User Guide نسخه ۲۶، فقط منبع پشتیبان گردش کار: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/index.html

**تمایز مهم:** لینک `pro-user` مربوط به User Guide نسخه ۲۶ با شناسه G57529-01 و ۲۶۶ صفحه است؛ جایگزین Help اصلی ۸۱۵ صفحه‌ای نیست. معیار کنترل جزئیات منو، نوار ابزار، پنجره، گزینه، فیلتر، میانبر و نمودار، Help اصلی است.

صفحات HTML که در این مرحله مستقیماً بررسی شدند:

| حوزه | صفحه مرجع |
|---|---|
| نقشه کامل موضوعات Help | `toc.htm` |
| پنجره‌های اصلی و رفتار تب‌ها | `using_main_windows.htm` |
| منوبار و فعال/غیرفعال شدن فرمان‌ها | `menu_bar.htm` |
| میانبرهای منویی و Hot Keys | `63585.htm` |
| Shortcut Keys | `63783.htm` |
| نوار ابزار Layout و فهرست آیکن‌ها | `layout_toolbar.htm` |
| منوهای راست‌کلیک | `use_shortcut_menus.htm` |
| پنجره Activities | `activities_window.htm` |
| Activity Details | `activity_details.htm` |
| Gantt | `ganttchart.htm` |
| Activity Network | `activitynetwork.htm` |
| فیلترها | `filter_a_layout.htm` |
| Status Bar و Layout Options | `using_the_status_bar_and_display_layout_options_bar.htm` |
| پنجره‌های Projects، WBS، Resources، Resource Assignments، Reports و Tracking | `projects_window.htm`, `wbs_window.htm`, `resources_window.htm`, `resource_assignments_window.htm`, `reports_window.htm`, `tracking_window.htm` |

روش تطبیق:
1. ساختار و گزینه‌های مرجع از Help نسخه ۲۶ استخراج شد؛ User Guide فقط برای روشن‌کردن گردش کار کمک می‌کند.
2. رجیستری‌های جاری `main` و کدهای Desktop Shell، Toolbar، Window Navigation، Details، Icons، Context Menus و نمای هر پنجره بررسی شدند.
3. ماتریس‌های موجود QA و Web Surface به‌عنوان شواهد قبلی خوانده شدند؛ تاریخ و شاخه آن‌ها کنترل شد تا سند قدیمی به‌جای وضعیت جاری جا زده نشود.
4. هرجا فقط عنوان، منو یا placeholder وجود دارد، آن را معادل قابلیت کامل حساب نکردم.
5. هر موردی که به اجرای مرورگر و تصویر از همان SHA نیاز دارد، «نیازمند آزمون زنده» باقی می‌ماند.

**محدودیت شواهد مرحله ۱:** آدرس Preview اصلی در 2026-11-10 پاسخ HTTP 200 و HTML entry shell برگرداند، اما ابزار دسترسی این ممیزی مرورگر تعاملی با DOM نهایی و ثبت Screenshot از همه پنجره‌ها فراهم نکرد. بنابراین وضعیت بصری هر پنجره‌ای که Screenshot تازه از همان SHA ندارد، تأییدشده اعلام نمی‌شود. تصاویر قبلی Activities فقط برای همان اجرا و SHA خودشان معتبرند.

## 2. واژگان وضعیت

| وضعیت | معنی |
|---|---|
| **مطابق و تأییدشده** | انطباق منبع، عملکرد و Screenshot/Browser test مربوط به همان SHA در دست است. |
| **پیاده‌سازی‌شده ولی آزمون‌نشده** | کد/کنترل دیده شد، اما اجرای کامل همان رفتار با مرورگر و شواهد کافی انجام نشده است. |
| **ناقص** | بخشی از کنترل یا گردش کار وجود دارد، ولی بخشی از گزینه‌ها/رفتار/محتوا حذف یا غایب است. |
| **غایب** | پنجره، نمودار، کنترل یا سرویس مورد نیاز در سطح جاری وجود ندارد. |
| **محدودیت مستند و مشخص** | قابلیت به علت نبود قرارداد داده/سرویس/مجوز عمداً غیرفعال است و علت آن به کاربر اعلام می‌شود. |

هر ردیف باید جداگانه وضعیت بصری، رفتاری، داده‌ای و آزمون مرورگر داشته باشد. یک وضعیت کلی سبز برای یک پنجره قابل قبول نیست.

## 3. نتیجه‌های سطح پوسته

### 3.1 ساختار منوها: اختلاف ساختاری قطعی

معماری تأییدشده CUBI در `workspace-visual-shell-master-audit.md` منوی سطح اول زیر را مقرر می‌کند:

`Workspace | Edit | View | Project | Organization | Tools | Administration | Help`

اما رجیستری اجرایی `apps/web/src/workspace-desktop-shell.ts` در `DesktopMenuId` و `getDesktopMenus()` این موارد را می‌سازد:

`File | Edit | View | Project | Enterprise | Tools | Window | Help`

نتیجه:
- **Workspace** با برچسب File نمایش داده شده است؛ باید برچسب و فرمان‌های آن با واژگان CUBI تطبیق پیدا کند.
- **Organization** با Enterprise جایگزین شده است؛ واژگان سازمانی مورد تأیید CUBI باید در UI به‌کار رود.
- **Administration** منوی مستقل سطح اول ندارد؛ موارد مدیریتی فعلی زیر Enterprise یا Tools قرار گرفته‌اند.
- **Window** به منوی اصلی افزوده شده و در فهرست هشت‌گانه‌ی معماری محصول جایگزین Administration شده است.
- وجود هشت منو، به‌تنهایی به معنی انطباق هشت‌گانه نیست؛ ترکیب و نام آن‌ها متفاوت است.
- Help نسخه ۲۶، منوی Admin را در اتصال/مجوز مناسب به‌صورت شرطی عرضه می‌کند؛ CUBI باید نمایش آن را با مجوز کاربر پیوند دهد، نه اینکه عملکرد مدیریتی را در منوهای دیگر پنهان کند.

**وضعیت:** ناقص.  
**معیار اصلاح:** هشت عنوان سطح اول مطابق معماری CUBI؛ تمام فرمان‌های مرجع با ID پایدار، وضعیت فعال/غیرفعال بر اساس پنجره/چیدمان/انتخاب/مجوز، و بدون حذف فرمان‌های معتبر.

### 3.2 نوار ابزار و گروه‌بندی آیکن‌ها

Help، نوار Layout را با ۱۲ عملکرد مشخص تعریف می‌کند: New Layout، Open، Save، Save As، Bars، Columns، Timescale، Filter، Group and Sort، Line Numbers، Table Font and Row و User Preferences. برخی آیکن‌ها فقط در پنجره یا چیدمان مربوط فعال هستند.

در CUBI:
- `getDesktopToolbar()` حدود ۳۰ کنترل را در یک نوار اصلی با گروه‌های File، Edit، Layout، View، Project، Activities و Tools قرار داده است.
- چند فرمان عمومی و خاص Activities در یک ردیف جمع شده‌اند؛ تفکیک و امکان نمایش/پنهان‌سازی مستقل خانواده‌های Toolbar مرجع هنوز با همان دقت احراز نشده است.
- `workspace-icons.ts` یک مجموعه SVG خطی ۱۶×۱۶ دارد؛ وجود SVG به معنی تطبیق معنایی و یکتایی همه آیکن‌ها نیست.
- برای برخی عملکردهای متفاوت از شکل تکراری/عمومی استفاده شده است؛ نمونه‌ها: `book` برای Open و Import و Export، `bars` برای Fit و Bars، و `table` برای Line Numbers و Panels.
- تابع `workspaceIcon()` برای نام ناشناخته به‌صورت خاموش آیکن `activity` را برمی‌گرداند؛ این fallback خطای نگاشت آیکن را پنهان می‌کند.
- در نتیجه، «تعداد SVGها» یا «وجود آیکن در Toolbar» معیار تکمیل نیست؛ نگاشت آیکن به فرمان، عنوان، Tooltip، وضعیت disabled و رفتار لازم باید تک‌به‌تک ثبت شود.

**وضعیت:** ناقص.  
**معیار اصلاح:** ماتریس آیکن به آیکن شامل ID، نام CUBI، Tooltip، گروه، وضعیت فعال‌سازی، محل‌های مجاز، میانبر و رفتار؛ حذف fallback بی‌صدای آیکن نامعتبر؛ تفکیک Toolbars و Overflow قابل سفارشی‌سازی.

### 3.3 میانبرها و دسترسی صفحه‌کلید

Help نسخه ۲۶ دو مجموعه جدا دارد: Hot Keys برای پیمایش منوها (مانند Alt+F سپس حرف فرمان) و Shortcut Keys مانند Ctrl+N، Ctrl+O، Ctrl+W، Ctrl+P، F10، F5، Ctrl+Z/X/C/V، Insert، Delete، Ctrl+F، F3، Ctrl+R، F9 و Shift+F9.

در کد CUBI، handler موجود در `workspace-desktop-shell.ts` این زیرمجموعه را پردازش می‌کند:
- F1 برای بازکردن فهرست میانبرها؛
- Alt+1 تا Alt+9 برای جابه‌جایی بین پنجره‌های باز؛
- Ctrl+Numpad+ و Ctrl+Numpad− برای Expand/Collapse در شرایط مناسب؛
- Ctrl+F، Ctrl+Z، Ctrl+Y، Ctrl+S و Ctrl+W.

مواردی که در فهرست میانبرهای Help وجود دارند ولی در handler جاری معادل آن‌ها دیده نشدند یا نیازمند نگاشت مستقل‌اند: Ctrl+N، Ctrl+O، Ctrl+P در سطح پنجره، F5، F10، Ctrl+X/C/V، Insert، Delete، F3، Ctrl+R، Shift+F9، Shift+F12 و ترکیب‌های Alt+F/Alt+E/Alt+V/Alt+P/Alt+N/Alt+T/Alt+A/Alt+H. بخشی از این فرمان‌ها ممکن است به دلیل تفاوت محصول CUBI عمداً تغییر کنند؛ در آن صورت باید جایگزین CUBI و دلیل آن مستند شود.

گفت‌وگوی Shortcuts فعلی از `getDesktopMenus()` ردیف می‌سازد؛ بنابراین فقط میانبرهایی را نشان می‌دهد که به آیتم منو افزوده شده‌اند، نه لزوماً کاتالوگ کامل میانبرهای قابل اجرا.

**وضعیت:** ناقص.  
**معیار اصلاح:** کاتالوگ مرکزی میانبرها، جدول مستقل از منو، تست واقعی فشار کلید برای هر مورد، جلوگیری از برخورد با تایپ در Input، و نمایش فقط کلیدهایی که واقعاً کار می‌کنند.

### 3.4 تب‌های پنجره، ترتیب و چرخه عمر

ساختار جاری پنجره‌ها یک Tab Strip دارد و باز/بستن پنجره‌ها و انتخاب پنجره پیاده‌سازی شده است. اما در کد رندر تب‌ها:
- هر تب به‌صورت span با role=tab و دکمهٔ عنوان/بستن تولید می‌شود؛
- نشانهٔ Dirty/Unsaved در رندر جاری دیده نمی‌شود؛
- قابلیت Drag/Reorder در کد رندر جاری مشاهده نشد؛
- چرخهٔ Save/Discard/Cancel برای بستن پنجرهٔ دارای تغییر ذخیره‌نشده باید در مرورگر و به تفکیک پنجره آزموده شود.

**وضعیت:** ناقص / پیاده‌سازی‌شده ولی آزمون‌نشده.  
**معیار اصلاح:** reorder با موس و صفحه‌کلید، dirty indicator، dirty-close prompt، حفظ state هر پنجره (layout، selection، scroll، filter، grouping، sort و Details tab) و بازیابی پس از reload.

### 3.5 Layout bar، Status bar و نواحی کاری

Help برای هر پنجره Layout/Display Options bar با نام Layout و Filter و فرمان‌های وابسته به پنجره تعریف می‌کند. Status Bar باید فقط اطلاعات واقعی محیط را نشان دهد.

در CUBI، عنوان و وضعیت پروژه/اتصال/زبان/تقویم/پوسته وجود دارد، اما باید کنترل شود که:
- Layout name و Filter name در تمام پنجره‌های مربوط نمایش داده شوند؛
- تعداد انتخاب‌شده، تعداد نتیجه و محدودهٔ فیلتر از هم متمایز باشند؛
- وضعیت ذخیره/همگام‌سازی، revision و Data Date فقط از منبع واقعی بیاید؛
- کنترل‌های Layout هر پنجره، گزینه‌های مجاز همان پنجره را ارائه کند و گزینهٔ متعلق به Activities بی‌دلیل به تمام پنجره‌ها تعمیم نیابد.

**وضعیت:** ناقص؛ نیازمند آزمون پنجره به پنجره.

## 4. ماتریس پنجره به پنجره

این جدول وضعیت کد/سرویس موجود را از کمبودهای سطح Help جدا می‌کند. برای همه پنجره‌ها هنوز Screenshot تازه از همان SHA و پیمایش کامل تمام گزینه‌ها نداریم.

| کلید پنجره CUBI | مرجع/حوزه Help | وضعیت فعلی از کد و ماتریس موجود | کمبودهای ثبت‌شده |
|---|---|---|---|
| Projects | Projects / EPS / Project Details | ناقص؛ صفحه پروژه و Project Details وجود دارد، بازکردن پروژه و نمایش ساختار بارگذاری‌شده واقعی است | درخت کامل Business Domain/EPS/Portfolio، رجیستر چندپروژه‌ای، فیلتر/گروه/ستون‌های کامل، نماهای Project Table/Project Bar Chart/Project Gantt/Profile، چرخه باز/بستن/آرشیو/وضعیت و جزئیات کامل هنوز تأیید نشده‌اند |
| WBS | WBS table/chart/details | پیاده‌سازی‌شده با داده واقعی؛ درخت و نمودار از رکوردهای یکسان استفاده می‌کنند | Move/Reorder/Indent/Outdent کامل، ابزار Move، weighted milestones، Earned Value، لینک سند و نماهای تکمیلی؛ Export نمودار و تست همه عمق‌ها و context menu |
| Activities | Activity Table/Gantt/Network/Details/Usage/Trace Logic | قوی‌ترین پنجره؛ ۱۸ سناریوی Browser در اجرای قبلی PASS گزارش شده‌اند | انطباق کامل منو/آیکن/میانبر، تمام گزینه‌های Bars و Barchart Options، پنج مقیاس، Zoom-to-Fit، چندسطحی Group/Sort، Highlight filter، عنوان/تراز ستون، Table Font/Row، Undo/Redo، create/edit؛ Activity Network، Usage Spreadsheet/Profile و Trace Logic هنوز باید در اجرای جاری اثبات شوند |
| Progress | Update Progress / actuals / spotlight | صفحه و مسیر ویرایش درصد/تاریخ واقعی وجود دارد | Progress update log، out-of-sequence، period actual cost/units، progress charts، Spotlight و ثبت تاریخچه |
| Resources | Resources hierarchy/table/chart/details | در حال حاضر پنل ظرفیت و خواندن محدود وجود دارد؛ رجیستر کامل سازمانی در ماتریس موجود غایب توصیف شده | درخت منابع، نوع Labor/Nonlabor/Material، Move toolbar، جدول/نمودار، نرخ‌های مؤثر، Roles، Calendar، Shifts، Curves، Codes و Resource Details |
| Resource Assignments | Assignment register/spreadsheet/profile/details | رجیستر واقعی و ایجاد/خواندن تخصیص وجود دارد | گروه‌بندی کامل بر اساس Resource/Activity، Resource Usage Spreadsheet/Profile، period buckets، units/time، cost/time، curves، overallocation، ویرایش/حذف یا قراردادهای جایگزین immutable |
| Roles | Roles hierarchy/rates/limits | لیست و Create/Update موجود است | hierarchy/chart، proficiency، rates/price per unit با تاریخ اثر، limits، assignments، Codes و Delete |
| Calendars | Global/Project/Resource Calendars | کاتالوگ واقعی و بخشی از ویرایش/استثنا موجود است | ایجاد تقویم خالی، ویرایش ساعات روز و split shifts، copy/assign scope کامل، حذف exception، recurring holidays، preview و assignment source/inheritance |
| Cost | Budget / EVM / financial periods | داده‌های EVM و دوره مالی از مسیرهای authoritative خوانده می‌شوند | baseline capture، cash flow، forecast، commitments، variance-to-baseline، EVM stored history و charts |
| Expenses | Expense Register / activity expenses / cost accounts | رجیسترهای واقعی و Create/Read در بعضی مسیرها وجود دارند | Update/Delete (مدل فعلی immutable)، accrual/category/vendor/status/cost-account linkage تا زمان وجود فیلد authoritative، نماهای time-phased/cost profile |
| Documents | WPs & Docs register/details | خواندن و انتخاب رکوردهای بارگذاری‌شده موجود است | مسیر upload/blob، create/update/status/link/unlink، launch/preview، revisions، file location و آزمون مجوزها؛ تا اتصال سرویس نباید دکمهٔ فعال نمایشی باشد |
| Reports | Reports register/groups/batches/wizard/editor/preview | SHELL/Preview؛ صفحه فعلی placeholder یا ابزار محدود دارد | کاتالوگ گزارش، Report Wizard/Editor، Groups، Batches، dataset/parameters، filter/columns/group/sort، run/preview/print/export/distribution و run history |
| Tracking | Tracking layouts / Project Table / Bar Chart / Gantt-Profile / Resource Analysis | SHELL؛ صفحه static است و selector فعلی فقط label/layout محلی را تغییر می‌دهد | Project Explorer، چند pane، Open/Save/Share/Import/Export layout، Project Table، Project Bar Chart، Project Gantt/Profile، Resource Analysis، Resource Explorer، spreadsheet/profile و summary state |
| Issues | Issue register/history/notify | SHELL؛ رجیستر مستقل هنوز کامل نیست | فهرست واقعی، status/priority/owner/responsible، activity/WBS links، history، notification، documents، chart و context menu |
| Risks | Professional Risk register / probability-impact | GAP-CORE؛ ماژول authoritative جاری گزارش نشده | مدل Risk، probability/impact، response/owner، cost/schedule exposure، assignment، risk matrix/chart، Details و مجوزها |
| Thresholds | Threshold register/monitor | GAP-CORE؛ ماژول authoritative جاری گزارش نشده | definition/parameter/tolerance، WBS/activity assignments، monitor run، alert/generated issue، history، Details و نمودار monitoring |
| Control | CUBI control intelligence / Changes & Claims | Read-side metrics/findings و سطح rail وجود دارد | رجیستر کامل Changes & Claims، تحلیل اثر، action workflow، history/evidence و تفکیک واضح Control Summary از ابزارهای مستقل |
| Settings / Administration | Preferences / access / audit / categories | تنظیمات و مدیریت layout بخشی از UI وجود دارد | User Preferences کامل، Admin Preferences، users/teams/access profiles/permissions، categories/currencies/financial periods، audit/recovery، ترجمه‌های فعال و تنظیمات نمایش/میانبر |

### 4.1 پنجره‌هایی که مرجع آن‌ها چند Layout مستقل دارد

نباید فقط یک Grid ساده برای این پنجره‌ها ساخته شود:
- Projects: Project Table، Project Bar Chart، Project Gantt/Profile، EPS/Portfolio hierarchy.
- WBS: WBS table، WBS chart، Gantt، WBS Details.
- Resources: resource hierarchy/table، chart، usage/profile.
- Resource Assignments: assignment table، Resource Usage Spreadsheet، Assignment Details.
- Activities: table، Gantt، Activity Network، Activity/Resource Usage Spreadsheet/Profile، Trace Logic، Activity Details.
- Tracking: Project Table، Project Bar Chart، Project Gantt/Profile، Resource Analysis، Project Explorer و Resource Explorer.

وجود دکمهٔ انتخاب Layout بدون ترسیم نمودار مربوط یا بدون منبع دادهٔ معتبر، تکمیل محسوب نمی‌شود.

## 5. ممیزی عمیق Activities و نمودارها

### 5.1 Activity Details و تب‌ها

Help رسمی Activity Details تب‌های زیر را فهرست می‌کند: General، Status، Resources، Predecessors، Successors، Codes، Tasks، Discussion، Notebook، Steps، Feedback، WPs & Docs، Expenses، Summary، Relationships، Risks (در اتصال/شرایط مربوط) و UDFs. در بالای هر تب نیز Previous/Next، Activity ID، Activity Name و Project قرار دارد.

CUBI این ۱۷ تب را در رجیستری دارد و یک تب Calendar با برچسب CUBI اضافه کرده است؛ این اضافه‌شدن نباید جای تب رسمی را بگیرد. وجود تب‌ها کافی نیست: محتوا، binding به activity انتخاب‌شده، فیلدهای editable/read-only، کنترل‌های action، empty/loading/error/permission state و ذخیره‌سازی هر تب باید به‌صورت جداگانه آزموده شوند. گزارش قبلی می‌گوید بخش زیادی از تب‌های اضافی empty-state صادقانه‌اند؛ این‌ها «محتوای تکمیل‌شده» نیستند.

کمبودها:
- ثبت داده و فیلدهای واقعی برای هر تب؛
- آزمون تغییر رکورد با Previous/Next و حفظ تب انتخاب‌شده؛
- آزمون Customize Activity Details و reorder/show/hide؛
- آزمون راست‌کلیک در بدنهٔ Details و گزینهٔ Customize؛
- تکمیل فیلدهای Resources/Predecessors/Successors با ستون‌های قابل تنظیم.

### 5.2 Gantt و Bars

Help، Gantt را به یک میلهٔ ساده محدود نمی‌کند. کاتالوگ شامل موارد زیر است:
- انواع Bar و ترتیب آن‌ها، Show/Hide، Shape، Pattern، Fill، Outline، Height/Position؛
- برچسب‌های Above/Inside/Below و Left/Right؛
- Filter اختصاصی برای هر Bar؛
- Summary، Task، Milestone، Critical، Actual، Remaining و Baseline؛
- relationship lines و arrowheads؛
- Legend، grid/background lines، non-work time، Data Date line و Progress line؛
- Timescale اختصاصی bar، جابه‌جایی/zoom/fit، انتخاب activity و edit معتبر تاریخ/مدت؛
- اتصال Gantt به Activity Table و حفظ هم‌ترازی عمودی هنگام resize/scroll/collapse.

در CUBI، task/summary/milestone و خطوط ارتباطی از دادهٔ ذخیره‌شده رندر می‌شوند و برای Progress Line آزمون قبلی وجود دارد. با این حال، ماتریس قبلی Bars را ناقص گزارش کرده و Add/Delete Bar و شکل/برچسب‌ها را کامل نمی‌داند. Data Date line در گزارش قبلی به‌دلیل نبود Data Date معتبر غیرفعال بوده است؛ این محدودیت باید باقی بماند تا تاریخ authoritative فراهم شود.

کمبودهای قابل پیگیری:
1. تکمیل همه کنترل‌ها و fieldها در Bars و Bar Chart Options؛
2. preview واقعی برای هر سبک و label position؛
3. legend و background/non-work lines؛
4. تست هر پنج Timescale و بازه‌های Start/Finish؛
5. تست Zoom In/Out/Fit، scroll و حفظ axis؛
6. آزمون drag/edit فقط از مسیر mutation authoritative؛
7. بررسی اتصال و محل عبور خطوط FS/SS/FF/SF و جلوگیری از clipping/crossing؛
8. تست رندر در تمام اندازه‌های 1280×720، 1366×768 و 1920×1080 و پس از تغییر splitter.

### 5.3 نماهای گرافیکی غایب یا ناقص

- **Activity Network:** Help یک Layout مستقل دارد: تنظیمات node، اندازه و فیلدهای box، رنگ/قلم، type و lag روابط، align/arrange، spacing، zoom و ذخیره/بازکردن layout. در وضعیت فعلی این نما در کاتالوگ هدف وجود دارد اما Browser evidence جاری برای پیاده‌سازی آن در دست نیست؛ غایب/نیازمند اثبات است.
- **Trace Logic:** باید به‌عنوان bottom view مستقل با عمق predecessor/successor و حرکت بین فعالیت‌ها باشد؛ evidence جاری برای آن وجود ندارد.
- **Activity/Resource Usage Spreadsheet:** ستون‌های دوره‌ای، bucket size، Units/Cost/Remaining/Actual، totals، grouping/sort و copy/export لازم است؛ در وضعیت فعلی به‌عنوان Layout کامل اثبات نشده است.
- **Resource Usage Profile/Histogram:** regular/stacked histogram، cumulative/non-cumulative، availability، limits، overallocation، overtime، curves و legend لازم است؛ نما/دادهٔ واقعی اثبات نشده است.
- **Tracking Charts:** Project Bar Chart، Project Gantt/Profile و Resource Analysis در Help فصل مستقلی دارند. در صفحه Tracking جاری، طبق matrix، فقط ساختار static و selector نمایشی وجود دارد.

## 6. دیالوگ‌ها و گزینه‌های قابل انتخاب

| دیالوگ/گروه | حداقل کنترل‌های مورد انتظار از Help | وضعیت/کمبود |
|---|---|---|
| Columns / Edit Column | Available/Selected، search، Add/Add All/Remove/Remove All، order، width، alignment، title، default/restore | دیالوگ واقعی وجود دارد؛ سناریوی قبلی برخی عملیات را آزموده، اما Title/Alignment و انتقال‌های همه‌گانه باید جداگانه Screenshot و assertion داشته باشند |
| Filters | Any/All، field، operator، value، Add/Delete، order، save/modify/apply/remove/combine | پیاده‌سازی و بعضی browser scenarios وجود دارند؛ Highlight و تمام حالت‌های اعمال/ترکیب باید کامل شوند |
| Group and Sort | سطوح متعدد Group و Sort، direction، hierarchy/WBS path، empty groups، band format، summary/totals | سه سطح در UI ثبت شده؛ آزمون قبلی فقط سطح نخست را تأیید کرده است |
| Timescale | واحد/interval اصلی و فرعی، date labels، fiscal، start/end، range و fit | پنج scale در کنترل وجود دارد؛ اجرای قبلی فقط بخشی از تبدیلات را آزموده است |
| Bars | Definition، order، show/hide، shape/pattern/fill/outline، labels/fields/filter/legend | ناقص؛ تمام fieldها و Add/Delete/Apply/Default نیازمند تطبیق هستند |
| Bar Chart Options | grid/background، nonwork، data date، progress، baseline، relations، critical، labels، legend | بخشی از Progress/Data Date آزمایش شده؛ کل گزینه‌ها اثبات نشده‌اند |
| Table Font and Row | font family/size، font color/background، row height، optimize-by-content، icons، defaults | وجود dialog در کد گزارش شده، اما آزمون کامل مرورگر و همه فیلدها موجود نیست |
| User Preferences | time/date/currency، language، units، startup، default window/layout، tooltips/password/email در محدوده محصول | کنترل جاری وجود دارد/اعلان شده، اما complete field-by-field audit انجام نشده است |
| Activity Details Customize | Available/Displayed tabs، add/remove، order، default و persistence | پیاده‌سازی شده؛ رفتار همه tabها و persistence باید تکمیل شود |
| Activity Network Options | box template، فیلدهای node، font/color، spacing، direction، arrange/align | نیازمند پیاده‌سازی/اثبات |
| Profile/Spreadsheet Options | bucket, period, fields, totals, histogram/stacked, limits, availability, overtime, legend | نیازمند پیاده‌سازی/اثبات |
| Calendar Editor | global/project/resource scope، work hours، split shift، exceptions، recurring/holidays، preview، assign | بخشی وجود دارد؛ scope و edge caseها ناقص‌اند |
| Report Wizard/Editor | data source، fields، filters، grouping، cells، formatting، page setup، preview/run | غایب/placeholder |
| Tracking Layout dialogs | Open/Save/Save As/Share/Import/Export/Delete و layout scope | غایب/placeholder |

## 7. راست‌کلیک و منوهای زمینه

Help صریحاً می‌گوید shortcut menu با راست‌کلیک روی عنصر یا فضای سفید هر پنجره باز می‌شود. در نتیجه فقط منوی جدول Activities کافی نیست.

ماتریس مورد نیاز CUBI:
- ردیف و سلول جدول؛ سرستون؛ فضای خالی جدول؛ WBS band؛
- Gantt task/summary/milestone bar؛ relationship arrow؛ فضای خالی نمودار؛ timescale header؛
- Activity Details tab strip و body؛
- WBS node و blank chart؛
- Project row/tree/chart/blank area؛
- Resource row/tree/chart/blank area؛
- Assignment row/spreadsheet cell/blank area؛
- Report row/group/batch/blank area؛
- Tracking project row، bar/chart/profile و blank area؛
- Calendar/Role/Expense/Document/Issue/Risk/Threshold record و blank area.

برای هر target باید order فرمان‌ها، آیکن، shortcut، enabled/disabled reason، permission و effect بررسی شود. منوی دارای ۲۰ فرمان در Activities به‌تنهایی اثبات منوهای پنجره‌های دیگر نیست.

## 8. اولویت کمبودها

| اولویت | شناسه | کمبود | معیار پذیرش |
|---|---|---|---|
| P0 | SHELL-MENU-01 | منوهای سطح اول با معماری CUBI هم‌نام/هم‌ساختار نیستند؛ Administration مستقل وجود ندارد | ۸ منوی صحیح CUBI، فرمان‌های کامل و enabled-state وابسته به context |
| P0 | SHELL-ICON-01 | نگاشت آیکن به فرمان کامل و قابل ردیابی نیست؛ fallback ناشناخته به activity | icon registry بدون fallback خاموش + آیکن/tooltip/command map کامل + screenshot sheet |
| P0 | SHELL-HOTKEY-01 | Shortcut dialog فقط shortcutهای تعریف‌شده در menu items را می‌سازد؛ بخشی از Help hotkeys/shortcuts پوشش داده نشده | catalog مرکزی و test واقعی برای هر میانبر |
| P0 | SHELL-WINDOW-01 | تب‌های پنجره dirty/reorder/keyboard lifecycle کامل اثبات نشده‌اند | open/switch/reorder/close/dirty prompt/persist tests |
| P0 | WINDOW-REPORTS-01 | Reports placeholder | Report catalog/wizard/editor/run/preview/history با داده واقعی یا disabled reason |
| P0 | WINDOW-TRACKING-01 | Tracking static placeholder | پروژه‌کاوشگر، layouts و چهار mode واقعی همراه profile/spreadsheet |
| P0 | WINDOW-RISK-01 | Risks فاقد core authoritative | مدل/API/permission و risk register/matrix |
| P0 | WINDOW-THR-01 | Thresholds فاقد core authoritative | تعریف/monitor/issue linkage و نمودار |
| P1 | ACT-BARS-01 | Bars و Barchart Options کامل نیستند | همه فیلدها و گزینه‌ها با screenshot/interaction proof |
| P1 | ACT-NETWORK-01 | Activity Network ناقص/اثبات‌نشده | node/edge options، layout، save/open، selection sync |
| P1 | ACT-USAGE-01 | Usage Spreadsheet/Profile و Trace Logic اثبات نشده‌اند | داده زمان‌محور، bucketها، legend، navigation |
| P1 | ACT-DETAILS-01 | محتوای بسیاری از ۱۷ تب رسمی empty state است | field binding، controls، permission و persistence هر تب |
| P1 | WINDOW-RES-01 | Resources dictionary کامل نیست | resource hierarchy/table/chart/details/rates/calendar/curve |
| P1 | WINDOW-ASN-01 | Resource Assignments فاقد full spread/profile/editor | units/time، costs، bucket، histogram و revise flow |
| P1 | WINDOW-CAL-01 | Calendar scope/editor/exception lifecycle ناقص | global/project/resource، shifts و recurring exceptions |
| P1 | WINDOW-PRJ-01 | Project register/EPS hierarchy چندپروژه‌ای ناقص | authorized tree، filter/group/layout و project details |
| P1 | WINDOW-WBS-01 | WBS move/reorder و جزئیات کامل نمودار/ویژگی‌ها ناقص | Move toolbar، weighted milestones، links، chart export |
| P1 | WINDOW-DOC-01 | Document write/upload/launch path کامل نیست | blob storage، file revisions، permissions و launch/preview |
| P2 | WINDOW-PROGRESS-01 | Progress log و نمودارهای تحلیلی ناقص‌اند | تاریخچه، out-of-sequence و time-phased reports |
| P2 | WINDOW-COST-01 | Cash flow/forecast/baseline capture ناقص | baseline lifecycle، forecast و variance charts |
| P2 | WINDOW-ISSUE-01 | Issue register و history/notification کامل نیست | owner/priority/status/links/history/notify |
| P2 | WINDOW-ROLE-01 | Role rates/limits/proficiency ناقص | effective-dated rate/limit editor و assignments |
| P2 | WINDOW-EXP-01 | Expense model fields و update/delete محدودند | فقط پس از وجود مدل/API معتبر؛ داده جعلی ممنوع |

## 9. شواهد قبلی و مواردی که نباید دوباره ادعای تکمیل شوند

- سند `docs/qa/ACTIVITIES_V26_COMPLIANCE_MATRIX_2026-11-08.md` گزارش می‌کند ۱۸ سناریوی Activities در اجرای 2026-11-09 PASS شدند. همان ماتریس در ردیف‌های دیگر صریحاً مواردی را ناقص/آزمون‌نشده می‌داند: همه منوها و آیکن‌ها، عنوان/تراز ستون، Highlight filter، Group/Sort چندسطحی، پنج Timescale، Zoom-to-Fit، همه Bars، Table Font/Row، User Preferences، Undo/Redo و Add/Edit. بنابراین ۱۸/۱۸ PASS به معنی parity کامل Activities نیست.
- همان سند Data Date line را به‌درستی به علت نبود Data Date authoritative غیرفعال گزارش می‌کند؛ این فرمان نباید با تاریخ ساختگی فعال شود.
- `docs/engineering/WEB_SURFACE_TRACEABILITY_MATRIX.md` هنوز تاریخ audit و branch/head اولیه نوامبر ۳/۴ را در header دارد. محتوای آن برای یافتن GAP مفید است، اما قبل از اینکه current main را نمایندگی کند باید با کد و Browser evidence جدید بازبینی و تاریخ‌گذاری شود.
- `docs/workspace/architecture/workspace-window-inventory.md` نیز بخشی از وضعیت اکتبر ۳۰ را بازتاب می‌دهد و با ماتریس جدیدتر Web Surface اختلاف دارد. نباید این دو سند متعارض را هم‌زمان به‌عنوان وضعیت قطعی به کار برد.
- `docs/workspace/architecture/workspace-toolbar-inventory.md` یک blueprint است؛ «Missing» در آن وضعیت فعلی هر آیکن در main را ثابت نمی‌کند. همه ردیف‌ها باید با رجیستری و مرورگر همان SHA تطبیق شوند.

## 10. دامنه مرحله بعدی آزمون تصویری و پنجره‌به‌پنجره

این مرحله هنوز اجرا نشده و باید برای هر پنجره به‌صورت مستقل ثبت شود:
1. بازکردن پنجره از menu و navigation tree و window tab؛
2. بازکردن تک‌تک منوها/زیرمنوها، کلیک تک‌تک آیتم‌ها و ثبت target/disabled reason؛
3. فهرست آیکن‌ها با icon ID، label، tooltip، size، color، order، group و action؛
4. تمام تب‌ها، dropdownها، checkboxها، radioها، listها، fieldها، defaultها و حالت‌های انتخاب؛
5. اندازه و جایگاه dialog، تعداد fieldها، tab order، separators، scroll و actions؛
6. همه chart/layoutها: نوع، axes، scale، labels، legend، series/bars/edges/nodes و context menu؛
7. تمام hotkeyها و keyboard-only navigation؛
8. تصاویر در 1280×720، 1366×768 و 1920×1080؛ زبان فارسی/انگلیسی و RTL/LTR؛
9. disabled/loading/empty/error/permission/dirty/conflict states؛
10. ثبت SHA، نام test، screenshot path، شماره صفحه/Topic Help و نتیجه.

هیچ کنترل disabled نباید به‌صورت کنترل فعال فریبنده نمایش داده شود. هیچ داده، زمان، مبلغ، منحنی، خط مبنا یا نمودار ساختگی نباید برای پرکردن UI ساخته شود.

## 11. حفاظت دامنه تغییر

این ممیزی فقط اسناد و گزارش QA است. هیچ فایل اجرایی، API، shared scheduling core، schema، database، Activities/Gantt/Details logic، theme، route، deploy یا data fixture در این مرحله تغییر نمی‌کند.

هر دستور بعدی به Qoder برای اصلاح باید این مراجع را داشته باشد:
- Complete HTML Help v26: https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm
- Supporting User Guide HTML: https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/index.html
- `docs/workspace/reference/oracle-p6-reference-index.md`
- `docs/workspace/reference/v26-source-register.md` (فهرست ۱۷ source ID جاری)
- همین سند ممیزی و `docs/workspace/architecture/v26-window-traceability-and-acceptance-matrix.md`

## 12. جمع‌بندی

در این مرحله، مهم‌ترین کمبودها فقط «زیباتر کردن رنگ و قاب» نیستند. اختلاف در ساختار منوها، خانواده‌های Toolbar، نگاشت آیکن، پوشش میانبرها، چرخه عمر Window tab، و کمبود واقعی چند پنجره/نمودار/دیالوگ وجود دارد. Activities از بقیه جلوتر است، اما قبولی سناریوهای منتخب آن را نباید parity کامل دانست. Reports، Tracking، Risks و Thresholds بیشترین فاصله را تا پنجره حرفه‌ای قابل استفاده دارند. مرحله بعد باید شواهد زنده‌ی جداگانه برای هر پنجره را تولید کند و ماتریس فعلی را از روی همان SHA به‌روزرسانی کند.
