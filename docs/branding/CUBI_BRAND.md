# CUBI Platform — Canonical Brand Asset

## Single source of truth
The user-approved CUBI logo sheet supplied on 2026-10-06 is the visual authority. The current runtime logo asset is `apps/web/public/cubi-platform-logo-primary.svg`.

Web, Desktop, Mobile, homepage header/footer, favicon and social metadata should resolve to the canonical asset or its deployment copy. Light/dark client variants must not silently introduce a different logo. Do not point runtime surfaces at legacy assets.

## Approved identity and validation status
The intended identity is the connected blue/cyan C-shaped isometric mark, distinct teal center cube, CUBI Platform wordmark, and “PLAN. CONTROL. BUILD SMARTER.” tagline. Logo-specific colors stay inside the logo; the rest of the application retains its calm, data-first UI palette.

**Visual acceptance is still pending.** Source-level tests for text, colors, and SVG path tokens do not prove that the rendered logo matches the approved image. Before replacing the runtime SVG with a redesigned version, compare a rendered candidate against the approved reference sheet at matching scale and aspect ratio, record the comparison/reference asset reproducibly, and run exact-head CI. Do not claim pixel-level or exact-reference fidelity without that check.

## Legacy cleanup
`logo.svg`, `logo-dark.svg`, and `cubi-platform-logo-primary-dark.svg` must not be introduced as alternate canonical lockups. Keep deployment safeguards and tests that prevent legacy runtime references.

## Change record
- 2026-10-06: user-approved CUBI logo sheet recorded as visual authority.
- 2026-10-09: canonical asset references consolidated; visual equivalence to the approved source remains a separate acceptance gate.
