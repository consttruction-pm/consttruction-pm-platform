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
> Manage your projects in a secure and always-accessible environment.
>
> With cloud infrastructure, security capabilities, and backup services, CUBI helps you manage your project information and records with greater confidence.

### Exact approved homepage copy (Persian)

> **Your Projects. Securely Connected. Reliably Protected.**
>
> مدیریت پروژه‌های خود را به محیطی امن و همیشه در دسترس بسپارید.
>
> CUBI با بهره‌گیری از زیرساخت ابری، امکانات امنیتی و خدمات پشتیبان‌گیری، به شما کمک می‌کند اطلاعات و سوابق پروژه‌های خود را با اطمینان بیشتری مدیریت کنید.
>
> **Secure SSL Connection**  
> ارتباط امن و رمزنگاری‌شده با CUBI.
>
> **Cloud Firewall Protection**  
> محافظت زیرساخت در برابر دسترسی‌های غیرمجاز.
>
> **DDoS Protection**  
> محافظت در برابر حملات مختل‌کننده سرویس.
>
> **Automatic Cloud Backup**  
> پشتیبان‌گیری خودکار برای کاهش خطر از دست رفتن اطلاعات.
>
> **Infrastructure Monitoring**  
> پایش سلامت و عملکرد زیرساخت.
>
> **Data Recovery**  
> امکان بازیابی اطلاعات از نسخه‌های پشتیبان.
>
> CUBI؛ تمرکز شما بر مدیریت پروژه، حفاظت از اطلاعات بر عهده زیرساخت ابری.

### Homepage feature cards

1. **Secure SSL Connection**  
   Encrypted connection between the user's browser and CUBI.

2. **Cloud Firewall Protection**  
   Infrastructure protection against unauthorized access.

3. **DDoS Protection**  
   Protection against attacks that disrupt service availability.

4. **Automatic Cloud Backup**  
   Automatic backups to reduce the risk of losing project information.

5. **Infrastructure Monitoring**  
   Monitoring of infrastructure health and performance.

6. **Data Recovery**  
   Recovery of information from available backup copies.

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
