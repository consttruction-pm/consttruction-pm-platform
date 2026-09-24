# Project Finalized Logic & Preferences — Master Reference

## هدف و وضعیت این سند

این سند مرجع اصلی تصمیم‌ها، منطق‌ها، ترجیحات و قواعدی است که از ابتدای پروژه «Construction PM Platform» تا این نقطه نهایی شده‌اند.

هدف:
- جلوگیری از فراموشی تصمیم‌های قبلی.
- جلوگیری از طراحی مجدد یا تغییر ناخواسته قراردادها.
- ایجاد مرجع مشترک برای همه توسعه‌دهندگان و ChatGPTهای متصل به Repository.
- نگه‌داشتن منطق سازگار با Primavera P6، PMBOK و استانداردهای معماری پروژه.
- جدا نگه‌داشتن «استاندارد/مرجع»، «تصمیم محصول» و «جزئیات پیاده‌سازی».

**قاعده:** اگر تصمیم جدیدی با این سند تعارض دارد، ابتدا باید تعارض مشخص و مستند شود؛ تغییر یک قاعده مشترک محاسباتی نباید صرفاً به دلیل ترجیح یک توسعه‌دهنده انجام شود.

---

# 1. چشم‌انداز محصول

محصول یک پلتفرم Web-based برای مدیریت پروژه و کنترل ساخت است که هدف آن ارائه قابلیت‌های حرفه‌ای و یکپارچه در سطحی است که کاربر پروژه ساختمانی تا حد امکان به استفاده همزمان از Primavera P6 و Microsoft Project نیاز نداشته باشد.

بازار هدف اصلی:
- شرکت‌های ساختمانی
- پیمانکاران
- پروژه‌های ساخت و زیرساخت
- کنترل پروژه و مدیریت منابع/هزینه/پیشرفت

اولویت محصول:
- جایگزینی عملی برای ابزارهای زمان‌بندی موجود
- تجربه آشنا برای کاربران P6/MS Project
- قابلیت Enterprise
- کاهش آموزش مجدد کاربر

---

# 2. مراجع اصلی پروژه

## 2.1 Primavera P6

هرجا قابلیت با Primavera P6 همپوشانی دارد، رفتار و منطق P6 مبنای compatibility baseline است.

قواعد:
- منطق Scheduling مشترک نباید از P6 ناقص‌تر باشد.
- محاسبات مشترک باید قابل آزمون و مقایسه با P6 باشند.
- رفتار relationship، calendar، duration، lag، constraints، resource/cost و سایر حوزه‌های مشترک باید با منطق P6 سازگار طراحی شود.
- در بخش‌های مشترک P6، سؤال تکراری از کاربر برای تصمیمی که قبلاً نهایی شده مجاز نیست؛ باید baseline ثبت‌شده اجرا شود.

## 2.2 PMBOK / PMI

در معماری و قابلیت‌های غیرالزام‌آور محصول، PMBOK Guide — Eighth Edition (November 2025) و The Standard for Project Management ANSI/PMI 99-001-2025 به‌عنوان مراجع استفاده می‌شوند.

در بخش AI:
- PMI Artificial Intelligence in Portfolio, Program and Project Management (June 2026) به‌عنوان مرجع مرتبط با قابلیت‌های AI پروژه در نظر گرفته می‌شود.

**اصل:** استانداردهای PMI مرجع طراحی و حاکمیت هستند؛ منطق محاسباتی محصول در جاهایی که با P6 همپوشانی دارد باید با baseline محاسباتی P6 نیز سازگار باشد.

---

# 3. زبان و تقویم

## زبان
- رابط کاربری فارسی و انگلیسی.
- داده‌های پروژه نیز باید قابلیت نگهداری فارسی و انگلیسی را داشته باشند.
- معماری باید امکان اضافه‌شدن زبان‌های دیگر را داشته باشد.
- Language Pack می‌تواند آنلاین/آفلاین باشد.
- نسخه Language Pack باید مدیریت شود.
- در نبود ترجمه، fallback به زبان پیش‌فرض انجام شود.

## تقویم
- Gregorian و Jalali/Shamsi.
- هر پروژه calendar context مشخص دارد.
- تقویم پروژه قابل ویرایش و versioned است.
- Standard calendar templates قابل استفاده‌اند.
- Calendar باید همراه project export/import قابل انتقال باشد.
- محاسبات تاریخ و مدت باید reproducible و cross-device deterministic باشند.

---

# 4. Scheduling Engine — منطق نهایی

تنظیمات پایه ثبت‌شده:

    {"duration":"working-day","calendar":"jalali-gregorian","lag":"working","constraints":"hybrid","mode":"both"}

اصول:
- Duration پیش‌فرض در منطق زمان‌بندی بر مبنای working-day است.
- Calendar arithmetic باید calendar-aware باشد.
- WorkingTimeResolver مرجع تشخیص working/non-working time است.
- Relationshipهای اصلی:
  - FS
  - SS
  - FF
  - SF
- Forward Pass.
- Backward Pass.
- Constraints و lag با مدل hybrid.
- Lag کاری در context تقویم محاسبه می‌شود.
- Scheduling deterministic است.
- project-specific scheduling settings و calendar version باید همراه project منتقل شوند.
- نتیجه یک پروژه روی دستگاه دیگر با همان context باید reproducible باشد.
- Scheduling calculation نباید به UI وابسته باشد.

## Calendar Arithmetic
باید عملیات واقعی و قابل آزمون برای:
- add_working_duration
- subtract_working_duration
- calculate_duration
- تشخیص working/non-working periods
داشته باشد.

هیچ ماژول دیگری نباید الگوریتم مستقل و متناقض برای محاسبه duration یا working time بسازد.

---

# 5. WBS و Activities

ساختار اصلی:
- Project
- WBS
- Activities

قواعد:
- WBS برای ساختاردهی پروژه است.
- Activity واحد اصلی زمان‌بندی، progress و assignment است.
- روابط Activityها در scheduling engine پردازش می‌شوند.
- گزارش‌ها و roll-upها باید hierarchy پروژه را حفظ کنند.
- محاسبات roll-up نباید صرفاً با average ساده انجام شوند مگر rule صریحاً آن را تعیین کند.

---

# 6. Baseline / Current / Actual / Forecast

این چهار مفهوم از هم جدا هستند.

- Baseline = مرجع مصوب/مبنای مقایسه.
- Current = وضعیت فعلی برنامه/داده.
- Actual = واقعیت ثبت‌شده.
- Forecast = پیش‌بینی وضعیت آینده.

نباید این مقادیر در یک فیلد یا formula مبهم ادغام شوند.

---

# 7. Progress Engine

Pipeline نهایی:

Progress Input
→ Normalize
→ Validate
→ Apply Actuals
→ Calculate Progress
→ Remaining Work
→ Remaining Duration
→ Scheduling
→ EVM
→ Earned Schedule
→ Reports

قواعد:
- Progress باید rule-driven باشد.
- Effective progress changes باید revision داشته باشند.
- Audit باید append-only باشد.
- WBS roll-up باید weighted و متناسب با metric باشد؛ simple averaging ممنوع است مگر rule صریح.
- Progress نباید مستقیماً منطق Scheduling یا EVM را duplicate کند.

---

# 8. EVM و Schedule Performance

EVM دارای engine مرکزی و authoritative است.

مفاهیم اصلی:
- PV
- EV
- AC
- BAC
- ETC
- EAC
- CV
- SV
- Earned Schedule و reconciliation

Resource/Cost می‌تواند داده موردنیاز EVM را تأمین کند اما نباید semantics مرکزی EVM را جایگزین کند.

نمونه قرارداد Resource EVM:
- ETC می‌تواند از remaining resource cost تغذیه شود.
- EAC = AC + ETC.
- VAC = BAC - EAC در صورت وجود BAC.
- CV و SV توسط EVM semantics مرکزی مدیریت می‌شوند.

---

# 9. Resources & Costs

Resource categories:
- Labor
- Machinery
- Materials

نمونه resourceها:
- Worker
- Electrician
- Mechanic
- Plumber
- Machinery
- Brick
- Block

برای resourceها:
- Unit type صریح.
- Calendar.
- Availability/capacity.
- Rate.
- Effective date/version.
- Assignment به Activity.
- Planned/Budgeted units.
- Actual units.
- Remaining units.
- Planned/Actual/Remaining cost.
- Time-phased loading.
- Curves.
- Histogram.
- Variance.
- Overload detection.
- Leveling primitives.

## Resource Leveling
Resource domain فقط ظرفیت و conflict را محاسبه/گزارش می‌کند.
تصمیم برای جابه‌جایی Activity، split کردن work، تغییر assignment یا پذیرش overload در Scheduling/Application layer است.

---

# 10. Cost و Financial Precision

- محاسبات مالی با Decimal.
- float ممنوع برای محاسبات مالی.
- نرخ‌ها typed و versioned هستند.
- Actual/Baseline/Current/Forecast cost جدا هستند.
- Time-phased values باید calendar context داشته باشند.
- Recalculation deterministic و idempotent باشد.

---

# 11. Excel Import / Export

یکی از ترجیحات قطعی پروژه:

Excel باید با داده‌های استاندارد و قابل محاسبه کار کند.

بنابراین:
- Number جدا از Text.
- Date جدا از Text.
- Duration typed.
- Boolean typed.
- Decimal values نباید برای Excel به text تبدیل شوند مگر قرارداد صریح.
- Excel formulas باید بتوانند روی ستون‌های عددی محاسبه انجام دهند.
- schema version در workbook وجود داشته باشد.
- import/export باید round-trip قابل آزمون داشته باشد.
- Header/schema validation اجباری است.

---

# 12. Documentation Management

ماژول اسناد شامل:
- Contracts
- Drawings
- Correspondence
- RFI
- Submittal
- Delay Claims
- Evidence
- Approval Workflow
- OCR
- Revision / Version Control
- Intelligent Search
- Security
- Audit Trail

اسناد باید قابلیت ارتباط با:
- Schedule
- Activity
- Cost
- Progress
را داشته باشند.

---

# 13. AI Assistant و Smart Guide

AI فقط یک chatbot جداگانه نیست.

AI Assistant:
- کمک به کارهای تکراری.
- Voice Data Entry.
- ورود داده از متن/صوت/Excel/Document.
- پیشنهاد WBS.
- پیشنهاد Activity.
- پیشنهاد relationship.
- پیشنهاد FS/SS/FF/SF و Lag/Lead.
- پیشنهاد resource، نیروی انسانی و تجهیزات.
- کمک به initialization/planning.

Smart Guide باید در تمام بخش‌ها حاضر باشد:
- توضیح دهد کاربر در هر مرحله چه کاری انجام دهد.
- خطاهای ورود داده را تشخیص دهد.
- خطاهای محاسباتی را شناسایی کند.
- correction پیشنهاد دهد.
- next workflow action پیشنهاد کند.
- در صورت امکان offline نیز برای قابلیت‌های تعریف‌شده کار کند.
- print formatting/layout assistance نیز در scope قرار دارد.

AI نباید بدون traceability یا خارج از business rules، نتیجه محاسبات رسمی پروژه را خودسرانه تغییر دهد.

---

# 14. Remote / Web Architecture

مدل محصول باید Web-ready باشد.

الزامات دائمی:
- Shared Domain/Calculation Core.
- API/Application/Repository separation.
- Shared business rules.
- UI-independent core.
- استقلال از Windows.
- استقلال از PostgreSQL.
- استقلال از filesystem.
- استقلال از authentication implementation.
- Document Storage abstraction.
- Background Jobs abstraction.
- API Contracts.
- Multi-tenant.
- Optimistic Locking.
- Transaction Boundaries.
- Project portability.

معماری لایه‌ای:

Domain / Calculation Core
→ Application
→ Repository / Persistence
→ API
→ UI

Repository نباید business calculation را پنهانی انجام دهد.
API نباید formulaهای Domain را تکرار کند.

---

# 15. Multi-Tenant و Context Isolation

هر شرکت/tenant و project باید context مالکیت و دسترسی مشخص داشته باشد.

هیچ query یا write نباید بتواند داده tenant/project دیگر را مخلوط کند.

این موضوع باید در:
- Domain context
- Application use case
- Repository
- Persistence
- API authorization
هماهنگ باشد.

---

# 16. Concurrency / Optimistic Locking

برای داده‌های قابل ویرایش همزمان:
- revision/version باید مشخص باشد.
- stale update باید رد شود.
- overwrite بی‌صدا ممنوع است.

Assignmentها نیز مانند Resourceها در صورت نیاز به concurrency control مستقل، باید revision semantics داشته باشند.

---

# 17. Transaction Boundaries

Transaction باید در سطح use case مناسب تعریف شود.

Repository می‌تواند عملیات persistence را اجرا کند، اما transaction semantics یک عملیات چندمرحله‌ای نباید به‌صورت پنهان و پراکنده ایجاد شود.

Use caseهایی که چند aggregate/repository را تغییر می‌دهند باید atomicity مشخص داشته باشند.

---

# 18. Audit / Revision / History

برای تغییرات حساس:
- Audit Trail.
- Revision.
- Immutable history در موارد لازم.
- Append-only history برای progress revisions.
- Rate history باید در صورت نیاز به historical reporting حفظ شود.
- update نباید بدون قرارداد history را حذف کند.

---

# 19. Reporting & Print

Reporting باید:
- dataset معتبر از Core/Application دریافت کند.
- formula جدید و متناقض با Core نسازد.
- typed data را حفظ کند.
- baseline/current/actual/forecast را تفکیک کند.
- قابلیت print formatting داشته باشد.
- برای Excel/print خروجی استاندارد تولید کند.

---

# 20. Project Portability

Project export/import باید تا حد امکان context لازم برای بازسازی محاسبات را حمل کند، از جمله:
- calendar
- calendar version
- scheduling settings
- project calculation settings
- language/data context لازم
- schema versions
- resource/cost configuration
- project-specific rules

هدف:
**Restore project on another device = same calculation context + reproducible results.**

---

# 21. Common Calculation Core — قانون طلایی

قانون اصلی کل پروژه:

**اول منطق محاسباتی در Shared Domain/Calculation Core تعریف می‌شود؛ Application آن را orchestration می‌کند؛ Repository آن را پایدار می‌کند؛ API آن را به typed contract تبدیل می‌کند؛ UI فقط آن را نمایش یا ویرایش می‌کند.**

هیچ module نباید:
- formula اختصاصی خود را برای همان مفهوم بسازد.
- یک مقدار را با نوع متفاوت ذخیره کند.
- محاسبه Core را دوباره انجام دهد.
- semantics ماژول دیگر را بدون قرارداد تغییر دهد.

---

# 22. خطای واقعی ثبت‌شده برای یادگیری

در Resource Backend، در DTO mapping تابع assignment_to_dto، مقدار method مربوط به normalized remaining units به جای نتیجه اجرای method به decimal داده شده بود.

درس مشترک:
- method و method result یکی نیستند.
- DTO باید نتیجه typed واقعی را منتقل کند.
- تست باید مقدار واقعی را assert کند.

این مورد در review branch اصلاح شد و به عنوان regression learning در سند مشترک ثبت شده است.

---

# 23. کیفیت کد و تست

هر قابلیت محاسباتی باید همراه با:
- Unit Test
- Integration Test در صورت نیاز
- Edge Cases
- Invalid Input Tests
- Regression Test
- Determinism Test در موارد مهم
ارائه شود.

برای P6-compatible calculations:
- conformance tests لازم است.
- خروجی باید با baseline مورد انتظار قابل مقایسه باشد.

---

# 24. قرارداد توسعه‌دهنده

قبل از تغییر:
1. اسناد پروژه را بخوان.
2. Stage Status را بررسی کن.
3. آخرین SHA فایل را دریافت کن.
4. منطق موجود را تکرار نکن.
5. calculation را در Core نگه دار.
6. کد + تست + مستندات را همزمان تغییر بده.
7. بعد از زیرمرحله progress را ثبت کن.
8. تغییرات کوچک و قابل بازبینی commit کن.
9. روی branch مستقل کار کن اگر کار همزمان است.
10. قبل از merge، integration و regression را بررسی کن.

---

# 25. وضعیت مراحل نهایی‌شده ثبت‌شده

- Stage 32.3 Progress Rules & Calculation — 100%
- Stage 32.4 Progress History/Audit/Revision — 100%
- Stage 32.5 Progress Update Workflow — 100%
- Stage 32.6 Dashboard & Control Center — 100%
- Stage 32.7 Reporting & Print Engine — 100%
- Stage 32.8 Resource & Cost Control Center — 100%
- Stage 33 System Integration & Platform Hardening — نقطه بعدی ثبت‌شده

Stage 32.8 شامل Resource domain، rates، assignments، loading، control، performance، calendars، capacity، overload detection، curves، histogram، EVM bridge، typed XLSX I/O و integration review ثبت شده است.

---

# 26. قاعده تغییر این سند

این فایل «Master Reference» است، اما نباید محل نگهداری جزئیات پیاده‌سازی متغیر باشد.

اگر rule جدیدی تصویب شد:
1. ابتدا در سند تخصصی همان domain ثبت شود.
2. سپس اگر rule بین چند module مشترک است، به این Master Reference اضافه شود.
3. تغییرات محاسباتی مشترک باید regression test داشته باشند.
4. rule جدید نباید بدون بررسی اثر آن بر P6 compatibility، PMBOK/PMI alignment، EVM، Excel typing، portability و Web-readiness وارد Core شود.

## قانون نهایی

**محاسبه واحد، نوع داده صحیح، context صریح، نتیجه deterministic، history قابل ردیابی و قرارداد مشترک — پایه تمام منطق پروژه است.**


# 27. ابلاغ اجباری تغییرات به نفر اول (Hasan)

از این تاریخ، هر **منطق جدید، قاعده محاسباتی، تصمیم معماری، ترجیح محصول، قرارداد API/Data، یا محدودیت مشترک** که در ادامه پروژه نهایی و مورد پذیرش قرار گیرد، باید:

1. در اولین محل تخصصی مرتبط ثبت شود.
2. اگر بر بیش از یک ماژول اثر دارد، در همین Master Reference نیز ثبت شود.
3. همراه با تاریخ/مرحله و در صورت لزوم دلیل تصمیم ثبت شود.
4. اثر آن بر P6 compatibility، PMBOK/PMI alignment، Shared Calculation Core، Web-readiness، portability و تست‌ها بررسی شود.
5. **به Hasan (نفر اول Backend/Database) به‌صورت صریح اعلام شود** تا از آخرین منطق و ترجیح پروژه مطلع باشد.
6. اگر تغییر نیازمند اقدام کدنویسی Hasan است، محدوده اقدام، فایل/ماژول مرتبط و تست مورد انتظار نیز در اعلامیه مشخص شود.
7. Hasan نباید بر اساس حافظه یا تفسیر شخصی، منطق جدید را حدس بزند؛ Master Reference و سند تخصصی آخرین مرجع هستند.

### قالب ابلاغ پیشنهادی
- **عنوان تغییر:**
- **مرحله/تاریخ:**
- **منطق یا ترجیح جدید:**
- **دلیل/مرجع:**
- **ماژول‌های تحت تأثیر:**
- **اقدام مورد انتظار از Hasan:**
- **تست/Regression مورد انتظار:**

**قاعده همکاری:** از این نقطه به بعد، هر بار که تصمیم جدیدی به Master Reference اضافه یا یک rule مشترک اصلاح شد، همان تغییر باید به‌عنوان یک اطلاع‌رسانی توسعه‌دهنده به Hasan اعلام شود؛ حتی اگر تغییر کوچک باشد.


## 28. Parallel Web + Desktop Client Development — 2026-09-24

The product is now formally developed as two parallel clients: Website/Web Application and Desktop Application.

Mandatory rules:
- Both clients use the same Shared Domain/Calculation Core and authoritative business calculations.
- Web and Desktop must remain capability-equivalent at the business-function level.
- Client UI/platform differences are allowed; business semantics and calculated results must not diverge.
- Both clients consume the shared Application/API contracts and must not access the database directly for business operations.
- Typed data, ProjectContext, optimistic locking, transaction boundaries, audit/revision and portability rules apply to both clients.
- A feature is complete only after shared contract/core work, Web integration, Desktop integration, shared regression tests and applicable cross-client parity tests.

Team split:
- User/Product Client Track: Web and Desktop UI/UX, client integration, workflows, localization/presentation, dashboards/Gantt/report presentation, client AI/Smart Guide UX and parity acceptance.
- Hasan/Developer 1: Backend, Database, Application, API, shared contracts, persistence, context isolation, transactions, resource/cost backend, documents, import/export, backend AI contracts and integration tests.

This rule was introduced to allow simultaneous progress of the Website and Desktop Application without creating duplicate calculation engines.

## 29. Typed Client Integration Contract — 2026-09-24

Shared Web/Desktop API contracts are versioned and authoritative. Decimal-like unit and financial values cross client boundaries as canonical decimal strings; dates use explicit ISO-8601 representation; nullable fields are explicit; calculated values must be obtained by invoking authoritative Domain methods. Web and Desktop must consume the same contract version and must not introduce alternative calculation formulas. Changes require schema versioning and regression tests.

## 30. Stage 33.3 — Production Application/API Hardening — 2026-09-24

Stage 33.3 is now the active platform-hardening stage after completion of Stage 33.2.

Mandatory shared rules:
- Application services own use-case orchestration and transaction boundaries.
- Repositories own persistence mechanics and never redefine domain calculations.
- API adapters serialize versioned typed contracts and never duplicate Scheduling/P6, Progress/EVM, Resource/Cost or duration calculations.
- ProjectContext is mandatory for project-scoped application operations.
- Optimistic-locking revisions must survive Application → Repository → API round trips.
- Decimal-like calculated values remain canonical decimal strings at API boundaries.
- API errors use stable typed categories rather than leaking database/framework exceptions.
- Externally retried mutation operations that can duplicate business effects require an explicit idempotency contract.
- Authorization checks belong at Application/API boundaries; the Shared Domain/Calculation Core remains independent of authentication providers.
- Web and Desktop consume the same API contracts and business semantics.
- Integration tests must cover validation failure, context isolation, stale revision/conflict, transaction failure and typed serialization.

Stage 33.3 work sequence:
33.3.1 Application/API contract audit
33.3.2 Stable error contract
33.3.3 Mutation idempotency contract
33.3.4 Authorization boundary
33.3.5 Integration regression

Reference document:
docs/architecture/STAGE_33_3_APPLICATION_API_HARDENING.md

This stage does not redefine Primavera P6/Scheduling or Progress/EVM semantics.


## 31. Mobile Client as a First-Class Product Client — 2026-09-24

The product is formally developed as three first-class client surfaces: **Web, Desktop and Mobile**. Mobile is not a reduced Web/Desktop screen set; it is optimized for field operations and rapid data capture.

Mandatory rules:
- Web, Desktop and Mobile consume the same versioned API/Application contracts and Shared Domain/Calculation Core.
- No client may duplicate Scheduling/P6, Progress/EVM, Resource/Cost, duration, calendar or financial calculation semantics.
- ProjectContext, authorization, optimistic locking, idempotency, stable errors, audit/revision and portability rules apply to Mobile as well.
- Mobile supports Persian/English and Jalali/Gregorian presentation; calendar arithmetic remains in Shared Core.
- Offline workflows are explicitly scoped and use shared synchronization/conflict contracts; Mobile never accesses the database directly.
- Mobile field workflows include progress entry, daily reports, attendance, machinery status/breakdown, document/photo capture, notifications, and applicable RFI/Submittal workflows.
- Voice input and AI Smart Guide are exposed through shared service/API contracts, not independent business logic.

### 31.1 Team split
- User/Product Client Track: Web, Desktop and Mobile UI/UX, navigation, workflows, localization/presentation, dashboards/Gantt/report presentation, field UX, AI/Smart Guide UX and parity acceptance.
- Hasan/Developer 1: backend/API/shared contracts, synchronization/security boundaries, persistence, context isolation, transactions, resource/cost backend, documents, import/export, backend AI contracts and integration tests.

### 31.2 Compatibility impact review
- P6/Scheduling: unchanged; calculation authority remains Shared Core.
- Progress/EVM: unchanged; Mobile submits/reads authoritative results.
- PMBOK/PMI alignment: supports distributed field data capture and controlled workflows without redefining core semantics.
- Web-readiness: strengthened by making Mobile consume the same API/Application contracts.
- Portability/tests: Mobile sync, conflict, revision and parity cases become mandatory regression coverage.


## 32. Offline-Capable Desktop and Mobile Scheduling — 2026-09-24

Desktop is a first-class standalone application and must be able to operate after installation without requiring Web or Internet for core project work. Desktop must be capable of running the Shared Domain/Calculation Core locally, using local project persistence, including Scheduling/P6-compatible calculations.

Mobile is also allowed and required, for approved planning workflows, to operate offline without depending on the Web client. In particular, Mobile must support a simple standalone planning flow: create/open a project, create a WBS, create activities, define FS/SS/FF/SF relationships and lag/lead, run Schedule/Recalculate, and view authoritative Start/Finish/Duration and applicable float/criticality results.

This does not authorize a second or divergent scheduling engine. The same Shared Scheduling semantics/Core implementation must be portable to supported offline clients. Online mode uses the same authoritative contracts and can synchronize local changes/results with the server. Offline mode stores changes locally and queues synchronization; conflict/revision/idempotency rules remain mandatory.

Compatibility review:
- P6/Scheduling: semantics remain centralized and P6-compatible; offline execution changes deployment location, not calculation rules.
- Shared Core: strengthened; Core must be portable and UI/Internet independent.
- Web-readiness: preserved; server/API remains authoritative for shared online synchronization.
- Portability: project calendar/settings/schema/context must travel with the local project context so results remain reproducible.
- Testing: offline/online parity, deterministic scheduling, sync/conflict/revision and cross-client regression tests are mandatory.

Required developer action: Hasan must provide/maintain the API/Application contracts and persistence/synchronization boundaries needed for local-capable Desktop/Mobile operation; no client-side duplicate scheduling formulas are permitted.
