# Jalal151 — CUBI Homepage Reference Decomposition

Source: 1440×1536 visual reference supplied in the task.

## Purpose
Build the CUBI Platform homepage from the supplied reference, with the logo and every major symbol/icon treated as an independent component rather than as one flattened screenshot.

## Section-by-section contract

### 01 — Header
- White compact navigation bar.
- CUBI Platform wordmark at left.
- Navigation: Home, Features, Solutions, Pricing, Resources, About.
- Right controls: language selector, Sign In, Get Started.
- Keep logo independent from navigation.

### 02 — Hero
- Full-width construction-site photographic background.
- Left column: eyebrow, headline, tagline, supporting paragraph, two CTAs.
- Right column: independent project-dashboard visual.
- Dashboard must remain a replaceable component; do not bake text into the background image.

### 03 — Capability strip
Six independent cards:
1. Project Controls — calendar/control icon.
2. AI Assistant — intelligence/spark icon.
3. Resources & Cost — database/cost icon.
4. Documents & Contracts — document icon.
5. Collaboration — people icon.
6. Cloud & Scalability — cloud icon.

Each icon is an independent reusable asset/component.

### 04 — Technology section
- Light blue background.
- Left copy: Powered by Leading Technologies.
- Technology references: Primavera P6, PostgreSQL, AI.
- Right: layered CUBI platform illustration.
- Four independent callouts: Project Controls & Scheduling, AI & Analytics, Data & Integration, Security & Reliability.

### 05 — CTA band
- Dark blue technology/construction background.
- Heading: Ready to Build Smarter?
- Supporting line.
- Actions: Start Free Trial, Contact Sales.

### 06 — Footer
- Independent CUBI logo.
- Product, Resources and Company link groups.
- Independent social icons.
- Copyright.

## Responsive contract
- Desktop: two-column hero and technology section.
- Tablet: capability cards reduce columns without changing content order.
- Mobile: hero and technology sections stack; capability cards collapse to 2/1 columns.
- EN uses LTR; FA uses RTL.
- Language switching must preserve the same component structure.

## Asset/component separation
- logo-header: brand asset only.
- logo-footer: brand asset only.
- hero-background: photo only.
- hero-dashboard: dashboard visual only.
- feature-01 through feature-06: one capability icon/card reference per file.
- tech-stack-illustration: central technology illustration.
- cta-background: CTA decorative background only.

## Production rule
The screenshot is a visual reference. Production homepage must be HTML/CSS/components with the repository's approved SVG logo/brand assets. Raster crops are references for composition and review, not a replacement for semantic UI.

## Scope guard
This task is visual/product presentation only. Do not alter CPM, P6, EVM, scheduling, database, API, or persistence logic.
