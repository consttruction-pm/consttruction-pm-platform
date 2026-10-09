# CUBI Platform — Jalal Handoff

## Saved reference package

- [CUBI website reference — SVG](./CUBI-website-reference.svg)
- [Logo reference notes](./CUBI-logo-reference.md)
- [Website reference notes](./CUBI-website-reference.md)

## Implementation reference

- Current canonical runtime logo: `apps/web/public/cubi-platform-logo-primary.svg`
- Public CUBI homepage: `/`
- Existing project workspace: `/app`
- Homepage implementation is maintained on `main`.

## Handoff rule

The user-approved logo sheet is the visual authority (Library image `1000044285.png`, uploaded 2026-10-06). The runtime SVG is the implemented asset, but its exact visual match to the source sheet must not be assumed from source-token tests alone. Before replacing it, keep a reproducible reference and record a rendered visual comparison plus exact-head CI results. Do not add alternate runtime logo files or change CPM/P6 engineering logic for branding work.

## Latest saved reference commits

- Logo SVG reference history: `c844f72acc15f63ccd4cb564a748567a16598422`
- Website SVG: `3b344213e009a12acaeca82388ba16fc8df052c9`
