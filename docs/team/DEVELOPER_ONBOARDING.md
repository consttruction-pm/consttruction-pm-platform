# Developer Onboarding — نفر اول

## هدف
این سند نقطه شروع توسعه‌دهنده Backend/Database است. هر ChatGPT یا توسعه‌دهنده‌ای که به این Repository متصل می‌شود باید ابتدا این فایل و اسناد معماری را بخواند و سپس از آخرین Stage ثبت‌شده ادامه دهد.

## Repository
- Repository: consttruction-pm-platform
- Branch اصلی: main
- وضعیت: Private
- نقش نفر اول: Backend / Database Development

## مسیر شروع
- `docs/team/PROJECT_FINALIZED_LOGIC_AND_PREFERENCES.md` — Master Reference تمام منطق‌ها و ترجیحات نهایی پروژه، شامل P6، PMBOK/PMI و تصمیم‌های معماری/محصول
- `docs/team/COMMON_CALCULATION_LOGIC_AND_LEARNING.md` — مرجع اجباری منطق محاسبات مشترک و خطاهای ثبت‌شده برای یادگیری
1. README.md
2. docs/architecture/ARCHITECTURE.md
3. docs/requirements/PRODUCT_SCOPE.md
4. docs/scheduling/SCHEDULING_ENGINE.md
5. docs/progress/PROGRESS_ENGINE.md
6. docs/resources-cost/STAGE_32_8_SPEC.md
7. docs/roadmap/STAGE_STATUS.md
8. src/README.md
9. tests/README.md

## نقطه ادامه فعلی
Stage 32.8 — Resource & Cost Control Center.
بخش‌های Resource domain، calculator، loading، validation، portfolio control، performance bridge، resource calendar، capacity، overload detection، leveling primitives، curves و histogram پیاده‌سازی شده‌اند.
آخرین نقطه توسعه: 32.8.10.
گام بعدی: 32.8.11 — Resource/Cost ↔ EVM integration، سپس Typed Excel Import/Export.

## تقسیم مسئولیت نفر اول
### Backend
- Domain models و business rules
- Database schema و migrations
- Repository layer
- Application services
- API contracts/endpoints
- Resource & Cost backend
- Integration tests و unit tests
- deterministic calculations و validation

### مواردی که نباید بدون هماهنگی تغییر کند
- Scheduling/P6 calculation semantics
- Progress/EVM core semantics
- Shared Domain/Calculation Core contracts
- API/Application/Repository boundaries
- Web-readiness rules
- Excel typed-data contracts
- project portability/versioning rules

## قواعد توسعه
- قبل از تغییر فایل موجود، آخرین نسخه و SHA آن را بررسی کن.
- هر قابلیت جدید باید testable و deterministic باشد.
- منطق محاسباتی نباید داخل UI قرار گیرد.
- از Decimal برای محاسبات مالی استفاده شود.
- تاریخ/زمان و مدت باید typed باشند.
- تغییرات مرتبط با یک قابلیت با تست همان قابلیت ارائه شوند.
- هیچ محاسبه‌ای نباید با تبدیل عدد به متن باعث خراب شدن Excel formulas شود.
- تغییرات P6 مشترک باید با منطق P6 سازگار و قابل آزمون باشند.
- هر commit باید کوچک، مشخص و قابل بازبینی باشد.
- از بازنویسی فایل‌های در حال کار نفر دیگر خودداری کن؛ برای کار مستقل از branch استفاده کن.

## قرارداد همکاری با ChatGPT
ChatGPT متصل به این Repository باید:
1. ابتدا این سند و Stage Status را بخواند.
2. آخرین Stage و درصد پیشرفت را پیدا کند.
3. کار انجام‌شده را تکرار نکند.
4. مستقیماً از اولین کار ناتمام ادامه دهد.
5. قبل از تغییر فایل، SHA فعلی را دریافت کند.
6. کد + تست + مستندات را با هم جلو ببرد.
7. پس از هر زیرمرحله درصد پیشرفت را ثبت کند.
8. برای تصمیم‌های معماری P6 مشترک، منطق P6 را baseline بداند و سؤال تکراری از کاربر نپرسد.
9. برای قابلیت‌های محصولی خارج از P6، تصمیم‌های ثبت‌شده در مستندات پروژه را رعایت کند.
10. در پایان هر مرحله، نقطه ادامه بعدی را در Stage Status ثبت کند.

## اصل مهم
این Repository مرجع مشترک پروژه است. هیچ ChatGPT متصل نباید فرض کند پروژه از صفر است. ابتدا اسناد را بخوان، وضعیت را بررسی کن و سپس از نقطه ثبت‌شده ادامه بده.
