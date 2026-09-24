# Common Calculation Logic & Developer Learning Guide

## هدف
این سند مرجع مشترک تمام توسعه‌دهندگان پروژه است و برای جلوگیری از تکرار خطاهای محاسباتی و ایجاد درک واحد از منطق محاسبات پروژه استفاده می‌شود.

**قاعده اصلی:** هیچ ماژولی نباید منطق محاسباتی مستقل و متناقض با Shared Domain/Calculation Core ایجاد کند.

## 1. اصول غیرقابل مذاکره

1. **Single Source of Truth:** هر مفهوم محاسباتی یک مرجع معتبر دارد. API، Repository، Database و UI نباید همان محاسبه را دوباره پیاده‌سازی کنند.
2. **Typed Data:** عدد، Decimal، تاریخ، مدت، Boolean و متن جدا هستند. عدد محاسباتی فقط در boundary قراردادی لازم است به متن تبدیل شود.
3. **Decimal:** پول و مقادیر دقیق مالی با Decimal محاسبه شوند؛ float برای محاسبات مالی ممنوع است.
4. **Deterministic:** ورودی و context یکسان باید همیشه خروجی یکسان بدهد؛ وابستگی پنهان به UI، ساعت سیستم، timezone یا state قبلی ممنوع است.
5. **Idempotency:** اجرای مجدد بدون تغییر ورودی نباید نتیجه متفاوت یا ثبت دوباره ایجاد کند.
6. **Calendar Context:** مدت کاری، lag کاری، تاریخ‌ها و time-phased values باید calendar context مشخص داشته باشند. WorkingTimeResolver مرجع working/non-working time است.
7. **Actual/Baseline/Current/Forecast:** این مفاهیم همیشه جدا بمانند.
8. **Revision/Audit:** تغییرات مؤثر بر محاسبات قابل ردیابی باشند و history حساس بی‌دلیل حذف نشود.
9. **Concurrency:** داده‌های قابل ویرایش همزمان باید revision/version داشته باشند و stale write نباید بی‌صدا overwrite کند.
10. **Transaction Boundary:** use case چندمرحله‌ای باید مرز transaction مشخص داشته باشد.

## 2. مرز لایه‌ها

### Domain / Calculation Core
محل business rules و محاسبات: Scheduling، Calendar Arithmetic، Progress، EVM، Resources، Costs، Loading، Variance و deterministic transformations.

### Application
محل orchestration، ترتیب use case، transaction boundary، context و هماهنگی چند repository/aggregate.

### Repository / Persistence
محل persistence، mapping، query و database-specific behavior. Repository نباید business calculation را جایگزین Domain کند.

### API
محل contract، boundary validation و serialization/deserialization. API نباید business calculation را دوباره انجام دهد.

## 3. خطای واقعی ثبت‌شده برای یادگیری — Resource API DTO

در review Resource Backend، در assignment_to_dto مقدار normalized_remaining_units به‌جای فراخوانی method، خود object تابع به decimal داده شده بود.

قاعده آموزشی:
- اگر مقدار یک method است، نتیجه آن باید با () گرفته شود.
- در DTO mapping باید مقدار نهایی typed و قابل serialization باشد.
- تست API باید مقدار واقعی محاسبه‌شده را assert کند، نه فقط عدم exception را.

این خطا در review branch اصلاح شد و regression test آن باید حفظ شود.

## 4. خطاهای مشابه که قبل از Commit باید بررسی شوند

### A. Method vs Method Result
بررسی کن آیا method reference منتقل شده یا method() و نتیجه واقعی.

### B. Property vs Callable
قبل از DTO mapping نوع واقعی مقدار را بررسی کن.

### C. Repeated Calculation
محاسبه‌ای که Domain تولید کرده نباید در API/Repository/Reporting دوباره با formula دیگری محاسبه شود.

### D. Silent Type Coercion
تبدیل ناخواسته Decimal به float، date به string، duration به string یا numeric به text می‌تواند Excel، EVM و reconciliation را خراب کند.

### E. Boundary Validation
ورودی نامعتبر در boundary مناسب رد شود؛ business rule نهایی در Domain باقی بماند.

### F. Partial Update
در update چندفیلدی مشخص باشد چه چیزی تغییر کرده و revision چگونه افزایش یافته است.

## 5. قواعد مشترک Scheduling / Progress / Resource / Cost / EVM

- Schedule engine مرجع زمان‌بندی است.
- Progress engine مرجع progress semantics است.
- EVM engine مرجع semantics مرکزی PV/EV/AC/BAC/EAC/ETC/CV/SV و reconciliation است.
- Resource/Cost domain محاسبات resource/cost را تولید می‌کند و semantics مرکزی EVM را جایگزین نمی‌کند.
- Reporting فقط dataset معتبر را مصرف می‌کند و نباید formula متناقض جدید بسازد.
- Resource leveling تصمیم scheduling است؛ resource domain فقط capacity/conflict را گزارش می‌کند.
- Calendar، settings، versions و project context باید همراه project قابل portability باشند.

## 6. چک‌لیست اجباری قبل از Commit

- [ ] منطق محاسباتی در Domain/Calculation Core است.
- [ ] API فقط mapping/contract انجام می‌دهد.
- [ ] Repository calculation را دوباره انجام نمی‌دهد.
- [ ] مقادیر مالی Decimal هستند.
- [ ] date/duration/number typed باقی مانده‌اند.
- [ ] calculation deterministic است.
- [ ] اجرای دوباره idempotent است.
- [ ] calendar context صریح است.
- [ ] Actual/Baseline/Current/Forecast مخلوط نشده‌اند.
- [ ] revision/optimistic locking رعایت شده است.
- [ ] transaction boundary use case مشخص است.
- [ ] history/audit حساس از بین نمی‌رود.
- [ ] unit و integration tests اضافه شده‌اند.
- [ ] API test مقدار واقعی result را بررسی می‌کند.
- [ ] edge cases و invalid inputs تست شده‌اند.
- [ ] تغییر با P6 و Shared Calculation Core سازگار است.

## 7. قانون طلایی تیم

**اول منطق محاسباتی را در Core تعریف کن؛ سپس Application آن را orchestration کند؛ Repository آن را پایدار کند؛ API آن را به قرارداد typed تبدیل کند؛ UI فقط آن را نمایش/ویرایش کند.**

هر developer، به‌خصوص Backend/Database، باید این سند را قبل از تغییر در محاسبات مشترک مطالعه کند. هر خطای جدید باید به شکل «نمونه خطا + علت + قاعده جلوگیری + regression test» ثبت شود.
