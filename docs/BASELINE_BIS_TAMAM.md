# Baseline — بیس تمام

## 1. Purpose

این سند Baseline رسمی برنامه باقیمانده تیم برای تکمیل نسخه Web قابل تحویل و آماده‌سازی Release Candidate/Pilot است.

نام Baseline: **بیس تمام**  
نسخه: **1.0**  
مبنای Baseline: وضعیت `main` در commit `fae9927b5d0e749303a394d056c2b89af2dbeae0`  
تاریخ مبنا: **2026-09-30**  
مدت مبنا: **30 روز کاری / 6 هفته**  
وزن کل: **100%**

این Baseline برای اندازه‌گیری پیشرفت آتی استفاده می‌شود. وقتی کاربر «درصد بیس‌لاین تمام» را درخواست کند، پیشرفت واقعی تیم باید در برابر همین Baseline سنجیده شود، نه در برابر برآوردهای قبلی.

## 2. Team ownership

- **Jalal** — Lead Developer / Architect / Integration Control؛ مالک Shared Core، Scheduling/P6 semantics، Calendar، Progress/EVM، integration، regression و acceptance.
- **Hasan** — Backend / Database / API؛ مالک Authentication persistence boundary، PostgreSQL، repositories، API، authorization persistence، transactions، concurrency، import/export backend و DB tests.
- **Javad (Farmj22002)** — Web / Frontend / UX؛ مالک Web host/client، login/session UI، Project/WBS/Activity UI، Gantt، dashboards/forms/reports، localization و client integration.
- **Supervisor / Observer (ناظر)** — **هیچ مسئولیت اجرایی ندارد** و در درصد پیشرفت به‌عنوان owner فعالیت محاسبه نمی‌شود.

## 3. Baseline rules

1. `main` فعلی مرجع قطعی است.
2. هیچ قابلیت موجود دوباره پیاده‌سازی نمی‌شود.
3. هر قابلیت فقط یک implementation owner دارد.
4. همپوشانی زمانی مجاز است؛ همپوشانی مالکیت/پیاده‌سازی مجاز نیست.
5. پیشرفت هر فعالیت فقط با evidence قابل قبول ثبت می‌شود: merged code، test/CI، integration evidence یا acceptance evidence.
6. صرف ایجاد فایل، UI ظاهری، mock یا طراحی بدون رفتار قابل اجرا، پیشرفت کامل محسوب نمی‌شود.
7. وزن‌ها ثابت‌اند مگر اینکه Baseline جدیدی به‌طور صریح تصویب شود.
8. تغییر Scope بعد از Baseline باید جداگانه ثبت شود و نباید به‌صورت پنهانی درصد Baseline را تغییر دهد.

## 4. Weighted baseline schedule

| ID | بازه | فعالیت | مالک | وزن |
|---|---|---|---|---:|
| B01 | W1 / روز 1-2 | Audit فعلی main، integration control، regression و تعیین dependencyهای واقعی | Jalal | 3% |
| B02 | W1 / روز 1-4 | Authentication/Credential Issuance + Session واقعی + امنیت session | Hasan | 6% |
| B03 | W1 / روز 2-5 | اتصال runtime/WSGI به composition واقعی و PostgreSQL boundary | Hasan + Jalal | 4% |
| B04 | W1 / روز 2-5 | Web Login/Session/Project bootstrap و pilot-ready shell | Javad (Farmj22002) | 3% |
| **W1** | **روز 1-5** | **جمع هفته 1** | **تیمی** | **16%** |
| B05 | W2 / روز 6-9 | Project/WBS/Activity persistence و mutation API | Hasan | 7% |
| B06 | W2 / روز 6-10 | Project/WBS/Activity UI و field editing | Javad (Farmj22002) | 7% |
| B07 | W2 / روز 7-10 | اتصال authoritative contracts، permissions، revision و end-to-end Project→Activity | Jalal + تیم | 4% |
| **W2** | **روز 6-10** | **جمع هفته 2** | **تیمی** | **18%** |
| B08 | W3 / روز 11-15 | Scheduling/Calendar/relationship/progress API persistence و mutation integration | Hasan | 7% |
| B09 | W3 / روز 11-16 | Gantt، schedule results، float/critical path، progress/EVM UI | Javad (Farmj22002) | 7% |
| B10 | W3 / روز 11-17 | Shared Core integration، P6 semantic verification، multi-calendar regression و acceptance | Jalal | 8% |
| **W3** | **روز 11-15/17** | **جمع هفته 3** | **تیمی** | **22%** |
| B11 | W4 / روز 16-19 | Documents/RFI/Submittal/Delay Claim/Reports/Import-Export backend | Hasan | 6% |
| B12 | W4 / روز 16-20 | Documents/Reports/Import-Export/Print Web UI | Javad (Farmj22002) | 6% |
| B13 | W4 / روز 16-20 | ارتباط documents/reports/import-export با schedule/cost/progress و validation | Jalal + تیم | 6% |
| **W4** | **روز 16-20** | **جمع هفته 4** | **تیمی** | **18%** |
| B14 | W5 / روز 21-24 | PostgreSQL hardening، transactions، concurrency، idempotency و authorization tests | Hasan | 4% |
| B15 | W5 / روز 21-25 | Browser UX، RTL/LTR، Persian/English، Jalali/Gregorian، responsive و error states | Javad (Farmj22002) | 5% |
| B16 | W5 / روز 21-25 | Security، calculation consistency، regression، performance و operational hardening | Jalal + تیم | 5% |
| **W5** | **روز 21-25** | **جمع هفته 5** | **تیمی** | **14%** |
| B17 | W6 / روز 26-28 | Full End-to-End acceptance از Login تا Project/Activity/Schedule/Gantt/Report/Import-Export | Jalal + تیم | 5% |
| B18 | W6 / روز 26-29 | Release Candidate، defect fixing و final regression | Jalal + Hasan + Javad (Farmj22002) | 4% |
| B19 | W6 / روز 27-30 | آماده‌سازی Pilot: محیط Staging، کاربران محدود، backup، monitoring، logging و acceptance package | Hasan + Javad + Jalal | 3% |
| **W6** | **روز 26-30** | **جمع هفته 6** | **تیمی** | **12%** |
| | | **TOTAL BASELINE — بیس تمام** | | **100%** |

## 5. Weekly weighted curve

| پایان | Baseline cumulative |
|---|---:|
| پایان W1 | 16% |
| پایان W2 | 34% |
| پایان W3 | 56% |
| پایان W4 | 74% |
| پایان W5 | 88% |
| پایان W6 | **100%** |

## 6. Definition of Done for Baseline

برای اینکه یک فعالیت وزن خود را بگیرد، باید رفتار مورد انتظار واقعاً قابل اجرا باشد و در صورت نیاز تست/CI/integration evidence داشته باشد.

به‌خصوص برای قابلیت‌های داده‌ای:

**Input → Validation → Calculation → Save → Reload → Display → Edit → Save**

و برای Scheduling:

**Calendar → Activity → Relationship → Lag/Constraint → Schedule → Gantt → Float/Critical Path → Progress/EVM → Report**

و برای Web:

**Login → Session → Project selection/open → real data → mutation → persistence → logout/login → data recovery**

## 7. Progress calculation

پیشرفت Baseline برابر است با مجموع وزن فعالیت‌هایی که Definition of Done آن‌ها با evidence معتبر تکمیل شده است.

مثال:
- B01 کامل = 3%
- B02 کامل = 6%
- B03 نیمه‌کامل = 2% از 4%
- سایر موارد = 0%

پیشرفت Baseline = **11%**

برای فعالیت‌های در حال انجام، درصد باید بر اساس evidence واقعی و قابل ردیابی ثبت شود؛ صرفاً بر اساس زمان سپری‌شده محاسبه نمی‌شود.

## 8. Schedule performance

برای گزارش‌های بعدی این شاخص‌ها نسبت به Baseline گزارش شوند:

- Planned % = درصد برنامه‌ریزی‌شده بر اساس Baseline در تاریخ گزارش
- Actual % = پیشرفت واقعی evidence-based
- Variance = Actual − Planned
- Remaining = 100 − Actual
- Status = On Track / Behind / Ahead بر اساس اختلاف عددی، بدون تغییر وزن Baseline

## 9. Baseline completion target

هدف این Baseline در پایان 30 روز کاری:

**100% تکمیل برنامه Baseline و آماده‌بودن Release Candidate/Pilot نسخه Web، مشروط به عبور موفق از Acceptance و Regression.**

این Baseline به‌تنهایی ادعای کامل‌شدن تمام قابلیت‌های آینده محصول را ایجاد نمی‌کند؛ قابلیت‌های P2/P3 خارج از Scope این Baseline هستند مگر اینکه بعداً Baseline جدید تصویب شود.
