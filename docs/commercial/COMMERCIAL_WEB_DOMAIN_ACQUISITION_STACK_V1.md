# Commercial Web, Domain & Free Acquisition Stack v1.0

Date: 2026-09-25
Status: Planning baseline

## 1. Objective
Define the lowest-cost credible technology stack for the public commercial website, bilingual marketing, lead capture, early access, SEO, launch-directory presence, and organic community acquisition.

## 2. Recommended architecture

### Public marketing site
Primary recommendation: Netlify Free initially.
- Netlify states that its Free plan can host commercial projects.
- Current published Free plan is $0 and includes custom domains with SSL and a global CDN.
- Current pricing uses a 300-credit monthly model; limits must be rechecked before launch.

### Alternative
Cloudflare Pages + Cloudflare DNS.
- Current Pages Free limits include 500 builds/month, up to 100 custom domains/project and 20,000 files/site.
- Static asset requests are free; dynamic Functions consume Workers quota.

### Not selected for public commercial launch
Vercel Hobby.
- Vercel's official Fair Use Guidelines and Terms restrict Hobby to personal/non-commercial use.
- Commercial use requires Pro or Enterprise.

## 3. Domain strategy
Primary: BRAND.com as the canonical public domain.
Secondary: BRAND.app as a defensive/app-oriented domain when available and affordable.
Optional: BRAND.ai only when justified by the final AI positioning and cost.

Recommended URL structure:
- brand.com/fa
- brand.com/en
- app.brand.com
- docs.brand.com
- status.brand.com
- blog.brand.com

## 4. Domain acquisition rules
Before purchase: exact spelling, live registrar/RDAP, active software/company collision, GitHub/social handles, trademark databases, Persian transliteration, pronunciation and negative-meaning checks.
A search-engine result with no match is not proof of domain availability; live registrar/RDAP verification is required at purchase time.

## 5. Current naming screening
Rejected/avoid based on current web collision screening:
- PEYVARA / پیوارا — collision risk with PVARA/Peyvara terminology.
- CONSTRIVO — active AI renovation product and app.
- CONSTRENA / Constréna — active construction company.
- PROJEVA — active logistics company.
- PROJORA — active project platform/services.
- PLANVERO — active B2B production planning service.
- PLANVORA — active automation/AI site.
- SCHEDORA — active booking software and multiple domains.
- STRUCTORA — active enterprise document-intelligence and construction-related products.
- BUILDARO — active services/marketplace and other construction-related uses.
- PIVARA — active business-management software.

A final brand must pass a dedicated naming/legal screening before any public commitment.

## 6. Website technical stack
Use the existing Web application technology where practical. The current apps/web package is only a minimal private package with TypeScript typecheck, so the final marketing framework is not yet fixed.
Marketing UI must remain a bounded Web/client surface and must not implement authoritative scheduling, EVM, resource or cost calculations independently from Shared Core.
Lead/demo forms should cross the Backend/API boundary rather than storing sensitive commercial data only in the static frontend.
Analytics baseline: Google Search Console, privacy-conscious web analytics, UTM conventions and conversion event tracking.
Operational baseline: DNS/CDN, transactional email with SPF/DKIM/DMARC, project-backend lead storage initially, support mailbox/knowledge base and a status page before enterprise onboarding.

## 7. Free/low-cost acquisition channels
Tier A — must use:
- Product Hunt: free launch; global product discovery.
- G2: free profile tier for product identity and reviews.
- SaaSworthy: basic listing currently advertised at zero cost.
- Capterra: organic provider listing; sponsored visibility is paid.
- AlternativeTo: free new-application submission after email verification/review.
- LinkedIn: free Company Page; primary organic B2B channel.
- YouTube: free channel; primary demo/education repository.

Tier B — targeted community:
- Indie Hackers for product-building exposure and early feedback.
- Selected Reddit communities with transparent value-first participation.
- Hacker News / Show HN only when visitors can genuinely try the product; landing pages alone do not qualify.

Tier C — optional directories:
Use selected reputable launch/discovery sites only after Tier A. Avoid mass submission to low-quality directories.

## 8. Content-to-lead
Every public channel should point to Demo, Early Access, Start a Project or Migration Assessment.
Core content families: P6/MS Project migration, scheduling, EVM/Earned Schedule, resource/cost, field reporting, RFI/Submittal/Documents, change/claims, AI project controls, Excel interoperability and offline-first workflows.

## 9. Free launch sequence
90-60 days: canonical domain, landing page, Search Console, analytics, LinkedIn, YouTube, G2/SaaSworthy/Capterra/AlternativeTo profiles, Early Access list.
60-30 days: weekly technical articles, demo videos, private beta, first pilots, migration content, specialist webinars.
30-7 days: Product Hunt preparation, demo refinement, evidence-backed case studies, launch email sequence, role-specific landing pages.
Launch week: Product Hunt, LinkedIn, YouTube, beta/customer invitations, relevant community discussions, demo sessions.
30 days after: customer review collection, case studies, comparison pages, SEO expansion and referral loop.

## 10. Anti-spam
Do not publish identical promotional copy everywhere.
Working mix: 70% educational/useful, 20% product evidence/demo, 10% direct promotion. Community rules always override this generic ratio.

## 11. Cost-control
Start with one canonical domain, one production marketing host, one DNS/CDN layer, one lead backend and one analytics stack. Organic acquisition first. Paid directory placements only after organic profile, reviews and conversion tracking exist.

## 12. Release governance
The marketing site may go live before the full application as a pre-launch site. Roadmap items must be labelled as roadmap; released-feature claims require evidence; customer logos/testimonials require permission; security certifications must not be implied before certification.

## 13. Recommended baseline
Domain: final-brand.com
Optional defense: final-brand.app and/or final-brand.ai
Hosting: Netlify Free initially
DNS/CDN: Cloudflare where practical
Lead API: Backend owned by Hasan
Web implementation: Javad
Product truth/specialist claims: Jalal
Acquisition core: LinkedIn + Product Hunt + G2 + SaaSworthy + Capterra + AlternativeTo + YouTube
Community: Indie Hackers + selected Reddit + Show HN only when genuinely playable
Pre-launch CTA: Join Early Access
Launch CTA: Book a Demo / Start a Project