# CUBI Homepage: Cloud Security, Reliability & Automatic Backup

**Status:** Approved marketing direction; implementation is tracked separately.  
**Recorded:** 2026-11-12  
**Scope:** Public homepage messaging and a future expanded Security & Reliability page. This document does not change the hosting provider, infrastructure, backup configuration, or production homepage by itself.

## Product and marketing decision

CUBI should present cloud hosting security and reliability as a visible customer benefit on the public homepage. The message should translate familiar infrastructure capabilities into plain-language reassurance for non-technical project managers and company users.

The positioning is especially relevant when comparing cloud-based project access with traditional desktop-only workflows that can depend on a particular workstation, local storage, manual saving, and manual backup practices.

The message must remain accurate: describe capabilities included and enabled in the actual hosting plan. Do not imply that cloud hosting eliminates every risk, guarantees zero data loss, or prevents all outages.

## Homepage content direction

Use a prominent, visually polished homepage section with concise cards, clear icons, and user-friendly explanations. Include **Cloud Firewall Protection** explicitly; it must not be omitted from the primary marketing copy.

### Approved English headline and introduction

> **Your Projects. Securely Connected. Reliably Protected.**
>
> Manage your projects in a cloud environment designed to support secure access, infrastructure protection, and dependable data backup.
>
> CUBI uses cloud hosting services and their available security and reliability capabilities to help protect access to your workspace and reduce the risk of losing project information.

### Homepage feature cards

1. **SSL/TLS Secure Connection**  
   Encrypted connection between the user's browser and CUBI.

2. **Cloud Firewall Protection**  
   Network-level filtering that helps block unauthorized or unwanted traffic.

3. **DDoS Protection**  
   Protection designed to help keep the website available during denial-of-service attacks.

4. **Automatic Cloud Backup**  
   Scheduled backups that help reduce the risk of losing project information.

5. **Secure Cloud Storage**  
   Cloud-based storage for website and project data, subject to the selected provider's storage and encryption capabilities.

6. **Infrastructure Monitoring**  
   Monitoring of hosting infrastructure health and service status.

7. **Data Recovery**  
   Recovery from available backups when supported by the selected hosting and backup services.

### Suggested short homepage closing line

> **Focus on managing your projects. CUBI's cloud infrastructure helps protect the services and information you rely on.**

## Suggested Persian meaning for localization

### عنوان
**پروژه‌های شما؛ ارتباط امن، حفاظت قابل‌اعتماد**

### معرفی
پروژه‌های خود را در محیطی ابری مدیریت کنید که برای دسترسی امن، محافظت از زیرساخت و پشتیبان‌گیری مطمئن طراحی شده است.

### کارت‌ها
- **ارتباط امن SSL/TLS:** ارتباط رمزنگاری‌شده میان مرورگر شما و CUBI.
- **محافظت فایروال ابری:** فیلتر ترافیک شبکه برای کمک به جلوگیری از دسترسی‌های غیرمجاز.
- **محافظت DDoS:** کمک به حفظ دسترس‌پذیری سایت در برابر حملات ازکاراندازی سرویس.
- **پشتیبان‌گیری خودکار ابری:** تهیه نسخه پشتیبان زمان‌بندی‌شده برای کاهش خطر از دست رفتن اطلاعات پروژه.
- **ذخیره‌سازی امن ابری:** نگهداری اطلاعات در فضای ابری، متناسب با قابلیت‌های سرویس‌دهنده انتخاب‌شده.
- **پایش سلامت زیرساخت:** بررسی وضعیت و سلامت سرویس میزبانی.
- **بازیابی اطلاعات:** بازیابی اطلاعات از نسخه‌های پشتیبان موجود، در محدوده امکانات سرویس انتخاب‌شده.

## Accuracy and claim controls

Before publishing each specific claim, verify the selected provider, purchased plan, configuration, and operational status:

- SSL/TLS certificate is active and HTTPS is enforced.
- Cloud/network firewall is enabled and its scope is understood.
- DDoS protection is included and its coverage/limits are understood.
- Automatic backups are enabled, their schedule and retention are known, and backup failures are monitored.
- Backup copies are stored separately from the primary server where the plan supports it.
- Encryption-at-rest and backup encryption are claimed only if confirmed for the relevant services.
- Infrastructure monitoring is active and its coverage is understood.
- Data recovery is advertised only with a documented restore process and tested backup availability.

Do not claim "100% secure", "zero data loss", "always available", "unhackable", or guaranteed recovery without a substantiated contractual and technical basis. Avoid presenting provider features as CUBI-built technology; describe them as capabilities of the cloud hosting infrastructure used by CUBI.

## Follow-up Security & Reliability page

After the hosting provider and service plan are selected, expand this homepage section into a dedicated **Security & Reliability** page. It should explain, using verified facts:

- Hosting provider and relevant data-center region(s), where appropriate to disclose.
- SSL/TLS, firewall, and DDoS protection coverage.
- Automatic backup schedule, retention, and independent storage arrangements.
- Storage and backup encryption details, if confirmed.
- Monitoring and incident communication approach.
- Backup restoration and disaster-recovery scope.
- Relevant certifications or compliance statements only when independently verified.

## Implementation notes

- Add this section to the public homepage in the existing CUBI visual language; do not create a duplicate homepage or alternate workspace entry point.
- Keep the content concise on the homepage; place technical details on the future Security & Reliability page.
- Localize it consistently with the homepage locale system.
- Use clear, recognizable icons and responsive cards that remain legible on mobile and desktop.
- Do not alter hosting, DNS, deployment, or backup settings as part of the content implementation.
- Keep the copy provider-neutral until the production hosting provider and plan are confirmed.
