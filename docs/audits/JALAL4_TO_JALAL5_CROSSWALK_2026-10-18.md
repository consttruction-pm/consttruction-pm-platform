# Jalal 4 → Jalal 5 crosswalk — coverage mapping proposal

**Date:** 2026-10-18  
**Source snapshot:** Jalal4 58-activity workbook last-computed snapshot dated 2026-10-13; Jalal5 130-activity schedule prepared 2026-10-18.  
**Status:** mapping for owner review; not yet accepted as progress-transfer evidence.

## Binding interpretation

- All 58 Jalal 4 scope rows are represented below and map to one or more Jalal 5 activity IDs.
- This is a **scope coverage map**, not an automatic transfer of completion percentages, weights, earned points or dates. The two plans have different granularity and changed scope.
- Each Jalal 5 activity retains its independent weight in the 100-point Jalal 5 denominator. Shared work is credited once, not once per contributing historical row.
- Jalal 4 completion may only carry forward after the mapped capability is found on current `main`, the exact commit/test/runtime evidence is accepted, and the Jalal 5 row's own Definition of Done is met. Documentation-only PRs, comments and open PRs get no implementation credit.
- Rows whose new IDs include `J11` or `J12` are final gates. Logo verification remains deliberately low-priority and late; it must not block product implementation or reopen the approved brand design.
- Native mobile delivery remains out of the present Jalal 5 V1 baseline per the previously accepted Web-first/Desktop-next decision; shared contracts remain reusable for later mobile work. Issue #1133 currently states a contradictory mobile-V1 requirement and requires governance reconciliation before it is treated as scope.

## Complete 58-row coverage mapping

| Jalal 4 ID | Jalal 4 activity | Jalal 5 coverage IDs |
|---|---|---|
| J4-01 | ثبت مرز V1، V2، اصول پایه و معیار خروج | A01; A04; A05 |
| J4-02 | فهرست جامع P6 26.4: فیلدها، منوها، گزینه‌ها، فرم‌ها و خروجی‌ها | A02; B01-B20; F01; F04-F09; F13 |
| J4-03 | ماتریس ردیابی نیاز→قرارداد→پیاده‌سازی→آزمون→شاهد | A02; A03; A05; B19; C09; D22; E15-E18; F16; J12 |
| J4-04 | تثبیت Shared Domain/Calculation Core و قرارداد CalculationContext | B01; B20; G03; G04 |
| J4-05 | CPM: forward/backward pass، روابط FS/SS/FF/SF، early/late و مسیر بحرانی | B03; B04; B14; F03; F05; J03 |
| J4-06 | تقویم پایه/پروژه/منبع، exceptions، مدت، lag/lead، قیدها و data date | B03; B05; B06; B14; F06; G03; J03 |
| J4-07 | Progress، actual dates، out-of-sequence، float و remaining logic | B06; B07; B13; F07; J03 |
| J4-08 | Baselineها، actual/remaining dates، constraints/open activities و تغییر Data Date | B06; B13; B14; B16; F07; J03 |
| J4-09 | Resource/Role/Assignment، resource calendar، capacity و leveling | B08; B09; B18; F08; G03; J01; J03 |
| J4-10 | Formula Dependency DAG، field formulas، ترتیب محاسبه و خطا/rounding | B12; C03; C04; F04; J04 |
| J4-11 | Progress/EVM و Earned Schedule، SPI(t)، هزینه زمان‌مند و cash-flow calculations | B10; B11; B13; C08; F07; F09; J04 |
| J4-12 | گواهی محاسبات P6: golden fixtures، field/options mapping و no-silent-omission | B01-B19; J03; J12 |
| J4-13 | مرز Backend HTTP/Application API | G01; G02; G04 |
| J4-14 | قراردادهای DTO/API نوع‌دار، نسخه‌دار، خطاها و optimistic locking | G04; G09; D05; D11 |
| J4-15 | PostgreSQL persistence، transaction boundaries، tenant/project isolation و replay | G02; G04; G09; J02 |
| J4-16 | قرارداد پایدار WBS/WorkPackage/Activity و خواندن workspace از داده ذخیره‌شده | G02; G03; F02 |
| J4-17 | P6 interchange: XER/XML/Excel/MPP/MPX و typed import/export round-trip | B16; G08; I05; J08 |
| J4-18 | هویت، مجوزهای ریزدانه، audit durable، idempotency و خطای fail-closed | G01; G04; G09; D05; D11; J05; J09 |
| J4-19 | Web P6 Workspace / Field Registry / layout shell | F01; F04; F15 |
| J4-20 | ساخت/ویرایش Project، WBS، WorkPackage، Activity، Relationships و calendar UI | F02; F03; F06; G02; G03 |
| J4-21 | Gantt، CPM، مسیر بحرانی، float، فیلتر/گروه‌بندی و داده‌های schedule | B04; F05; J03 |
| J4-22 | Dashboard، ناوبری، UX، responsive states و loading/error/empty states | E04; E17; E18; F15; F16 |
| J4-23 | گزارش‌ها، نمودارها، A4 قابل ویرایش، export و cash-flow views | E15; F13; G08; J04 |
| J4-24 | صفحات/کنترل‌های Resource، Cost، Progress، EVM، payment/contract KPIs | B09-B11; C08; F07-F09 |
| J4-25 | Website/product entry، مسیر ورود فارسی/انگلیسی و پیوند به فضای پروژه | E01; E04; E14-E18; G01; H01; H08 |
| J4-26 | تثبیت نیازمندی‌های دستیار V1، سناریوها، مجوزها و معیار پذیرش | A02; A03; D01; D07; D22 |
| J4-27 | Model/provider runtime و orchestration امن سمت سرور | D02; D03; D14; D22 |
| J4-28 | Typed tools برای project/WBS/activity/relationship/calendar و عملیات ذخیره واقعی | D04; D05; D09; G02; G04 |
| J4-29 | ورودی زبان طبیعی، صوت/متن، Excel و سند با preview/reconcile پیش از نوشتن | D07; D08; D21; E09; H05 |
| J4-30 | پیشنهاد→تأیید/رد، permission scopes، audit، stale revision و idempotency | D05; D11; D18; D19; G04; G09; J05 |
| J4-31 | محاسبه مجدد از Shared Core، fresh-read، پاسخ grounded و ساخت گزارش/نمودار | B20; D06; D10; D12; F13; J10 |
| J4-32 | تست سرتاسری دستیار: ساخت پروژه، اصلاح، ذخیره، محاسبه، گزارش و سناریوهای منفی | D22; J05; J10 |
| J4-33 | Desktop shell / local project foundation و lifecycle | I01; I06; I08 |
| J4-34 | اتصال Desktop به Shared Core/API، persistence، authentication و error handling | G01; G02; G04; I01; I03 |
| J4-35 | مدیریت Project/WBS/Activity/Relationships/Gantt و صفحات اصلی Desktop | F02-F06; F13; I03 |
| J4-36 | Import/export، offline operation، localization/help و recoverability Desktop | H06; H07; I02; I05; I06 |
| J4-37 | حالت self-test و مرز مجوز: همه قابلیت‌ها 60 روز؛ بدون enforcement آنلاین V1 | G01; I04; I08 |
| J4-38 | مدل و رابط مدیریت منابع/تخصیص/تقویم منبع/ظرفیت | B08; B09; B18; F08; G03; J03 |
| J4-39 | Cost/budget/progress/EVM/cash flow/payment forecast و report model | B10; B11; F07; F09; G08; J04 |
| J4-40 | Commercial: قرارداد، BOQ، تغییرات، claims، procurement و payment workflow | C05; C07; D08; D12; F12; G07 |
| J4-41 | Document management: drawing revisions، RFI، submittals، correspondence و change log | D06; D08; F10; G05; I05 |
| J4-42 | فرم‌های ISO، لایه اختیاری PMBOK 8 و گزارش AI قابل‌ویرایش | C01-C09; D12; F14; J04 |
| J4-43 | tenant isolation، project roles، operation permissions، audit log و data privacy | D05; D14; D19; G01; G09; J09 |
| J4-44 | فارسی/انگلیسی و multilingual UI + project data، RTL/LTR و Jalali/Gregorian | H01-H05; H08 |
| J4-45 | language packs آفلاین، font fallback، ترجمه درخواستی، AI/voice offline boundaries | D15-D21; H06; I02; I06 |
| J4-46 | Help Center کامل، راهنمای هر بخش، راهنمای هوشمند و محتوای چندزبانه | D13; F15; H07; I07 |
| J4-47 | اتصال هویت/ورود سایت به Desktop و مدیریت session امن | G01; I01; I04 |
| J4-48 | Subscription/pricing/payment tiers و کنترل entitlement بدون قفل‌کردن self-test | E11; G01; G10 |
| J4-49 | صفحات معرفی قابلیت، SEO چندزبانه، performance و accessibility پایه | E01-E18; H08; J06 |
| J4-50 | کنترل نهایی یک مرجع لوگو/CUBI و تطبیق homepage در آخر کار | E03; E04; J11 (final low-priority verification only) |
| J4-51 | آزمون سرتاسری persistence واقعی: create→commit→fresh read برای WBS/activity | G02; J02 |
| J4-52 | P6 calculation conformance suite و گزارش تفاوت/بدون حذف | B19; J03; J12 |
| J4-53 | AI security/negative E2E: denial، cross-tenant، stale, rejected, malformed, retries | D22; J05 |
| J4-54 | Web↔Desktop end-to-end روی یک پروژه، Core، identity، persistence و revisions | I03; I08; J10 |
| J4-55 | Regression، import/export round-trip، migration، backup/restore و error recovery | G04; G11; I05; J08 |
| J4-56 | QA چندزبانه، RTL/LTR، accessibility، browser/device، performance و offline | H08; J06; J07 |
| J4-57 | بسته‌بندی Desktop، setup/self-test، runbook، Help completeness و release operations | I06; I08; J11 |
| J4-58 | Release Acceptance Gate نهایی، امضای تیم و عدم وجود omission/blocker | A06; J11; J12 |

## Explicit Jalal 5 added scope with no one-to-one Jalal 4 equivalent

These rows must not be forced into an inaccurate historical mapping merely to fill a cell. In the Jalal 5 workbook's `Crosswalk جلال۴` column, label each as **Added scope — no J4 equivalent** and keep the current scope requirement/source visible.

| Jalal 5 ID | Added capability | Governing source / acceptance |
|---|---|---|
| F11 | Field operations and assurance screens: daily logs, attendance, equipment, issues, inspections, quality, safety and punch closeout | Product completeness Principle 2; Issue #459; real page/action and workflow acceptance. Native mobile-only work remains deferred to V2. |
| G06 | Field operations backend persistence and validation | Product completeness Principle 2; Issue #459; tenant/project-scoped persisted read/write, validation, audit and fresh-read tests. |
| A06 | Current baseline confirmation and immediate blocker register is mapped to J4-58 for the gate/omission concept, but the new current-main cut-off and blocker evidence are Jalal 5-specific. Keep it marked as current-main re-baselining work, not a transferred percentage. |

The reverse map now classifies 127 of the 130 Jalal 5 tasks against existing Jalal 4 scope; F11 and G06 are explicit added scope, while A06 has both its J4-58 gate linkage and its distinct current-main re-baselining role. This classification is about traceability, not accepted completion.

## Acceptance procedure for finalizing the crosswalk

1. Jalal checks semantic equivalence and whether any mapped J5 item lacks an acceptance criterion or an applicable P6/PMBOK source.
2. Hasan confirms the real persistence/API/transaction/service implementation mappings for backend and AI tool rows.
3. Farmj22002 confirms actual website routes, root menus, child actions, navigation edges, language coverage and built-artifact test mappings.
4. For each J4 row, classify coverage as `Mapped / Partially mapped / Added scope / Explicitly deferred / Gap`. A row can be considered covered only if every relevant requirement is assigned to a J5 ID or has an explicit approved disposition.
5. Complete the matching IDs in `Jalal5_Weighted_Master_Schedule_2026-10-18.xlsx` column `Crosswalk جلال۴`, then reconcile all 58 rows and confirm the sum of J5 weights remains 100.00.
6. Keep earned completion `Pending` until this review and current-main evidence are accepted. The last Jalal4 48.13% remains historical; do not label it a current Jalal5 percentage.

## Scope conflict requiring explicit governance reconciliation

Accepted product delivery intent is Web first and Desktop next; native Mobile is deferred to V2. Repository issue #1133 presently labels Mobile V1 mandatory. Do not silently blend that older issue text into Jalal 5. Preserve the V1 scope above and update/close/re-scope the conflicting issue after product-owner acknowledgement. This is a scope-record conflict, not a reason to redesign approved Web/Desktop capability.

## Source-of-truth references

- [Jalal 4 progress control](https://github.com/consttruction-pm/consttruction-pm-platform/blob/main/docs/audits/JALAL4_PROGRESS_CONTROL_2026-10-18.md)
- [Jalal 5 schedule PR](https://github.com/consttruction-pm/consttruction-pm-platform/pull/1484)
- [V1 governance/reconciliation issue](https://github.com/consttruction-pm/consttruction-pm-platform/issues/680)
- [Master V1 audit](https://github.com/consttruction-pm/consttruction-pm-platform/issues/459)
- [Mobile V1 scope conflict](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1133)