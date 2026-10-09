# CUBI Platform — Canonical Brand Asset

## Single source of truth
The user-approved CUBI logo sheet supplied on 2026-10-06 is the visual authority. The single master logo is `apps/web/public/cubi-platform-logo-primary.svg`; this is the only approved runtime logo file.

The master SVG preserves the connected C-shaped isometric mark, distinct teal center cube, CUBI Platform wordmark, and `PLAN. CONTROL. BUILD SMARTER.` tagline. Web, Desktop, Mobile, homepage header/dashboard/footer, favicon and social metadata must resolve to this canonical asset. Light/dark client variants share the same asset path; do not create alternate logo files, redraw the mark, or point runtime surfaces at legacy assets.

The canonical file is the source artwork; deployed web pages reference its copied public URL `./cubi-platform-logo-primary.svg`. Repository-relative source paths and deployed browser URLs are different representations of the same asset and must not be confused.

## Approved identity
Keep the blue/cyan/teal mark colors within the logo. The rest of the application retains the calm, data-first UI palette. Do not substitute a generic cube, a different C mark, or a dark-only/light-only alternate logo.

## Legacy cleanup
`logo.svg`, `logo-dark.svg`, and `cubi-platform-logo-primary-dark.svg` are deprecated. They must not be used by runtime code or shipped in the Pages artifact. Deployment assertions that check these files are absent are intentional safeguards and must remain. Tests enforce one canonical path and validate the canonical SVG lockup.

## Change record
- 2026-10-06: user-approved CUBI logo sheet recorded as visual authority.
- 2026-10-09: consolidated client light/dark references to one master asset.
- 2026-10-09: refined the canonical SVG toward the approved connected-C/cube lockup and added asset-content regression coverage.
