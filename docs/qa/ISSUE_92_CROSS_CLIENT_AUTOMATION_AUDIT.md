# Issue #92 — Cross-client automation audit

Status: audit complete; implementation not started.

## Evidence
- The current `Client Typecheck` workflow runs typecheck + package runtime tests for client-sync, web, desktop and mobile.
- Web package tests compile TypeScript tests and execute Node workspace tests; this is runtime regression coverage, not browser UI automation.
- Desktop and Mobile package tests likewise run TypeScript/Node tests; no native host rendering automation is established by the current workflow.
- The current Issue #92 acceptance list explicitly requires cross-client automated UI regression, accessibility automation, product-scale translation coverage, performance benchmarks, end-to-end shell/native-engine tests, and release certification.

## Boundary decision
Do not add a browser/native UI framework or host dependency speculatively. First implementation slice should be the smallest repository-native executable UI-adjacent regression seam that can run in existing CI without changing authoritative Shared Core semantics.

## Not yet verified
- Real browser DOM interaction in CI.
- Windows native shell rendering.
- Mobile native host rendering.
- Accessibility tree/keyboard automation.
- Product-scale translation corpus coverage.
- Language-pack/model performance benchmarks.
- Native STT/TTS/local inference engines.

## Next evidence requirement
A concrete test harness/entry point must be identified in current main before source implementation. If none exists, the missing infrastructure itself must be treated as an explicit scope decision rather than silently introducing a framework.
