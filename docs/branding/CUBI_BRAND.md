# CUBI Platform — Canonical Brand Asset

## Single source of truth
The approved CUBI logo sheet supplied on 2026-10-06 is the visual authority. The one implemented master logo is `apps/web/public/cubi-platform-logo-primary.svg`.

This is the only runtime logo asset. Web, Desktop, Mobile, homepage header/footer, favicon and social metadata must reference this file. Light/dark client variants resolve to the same canonical path; do not create alternate logo files, redraw the mark, or point surfaces at legacy assets.

## Approved identity
Preserve the connected C-shaped cube mark, blue/cyan/teal facets, CUBI Platform wordmark, and “PLAN. CONTROL. BUILD SMARTER.” tagline from the supplied reference. Logo-specific colors stay inside the logo; the rest of the application retains its calm, data-first UI palette.

## Legacy cleanup
`logo.svg`, `logo-dark.svg`, and `cubi-platform-logo-primary-dark.svg` are deprecated and must not be referenced by runtime code or deployment workflows. The single-source change removes them. Tests enforce one canonical path.

## Change record
- 2026-10-06: user-approved CUBI logo sheet recorded as visual authority.
- 2026-10-09: replaced simplified cube/wordmark with the connected C-shaped logo lockup and established one canonical runtime asset for all clients.
