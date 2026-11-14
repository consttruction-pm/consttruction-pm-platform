# CUBI Product Design System & Environment Shells

**Document ID:** CUBI-DESIGN-SYSTEM-001  
**Status:** Exploratory design brief — non-binding; requires product design, compatibility review, tests and explicit approval before adoption  
**Date:** 2026-11-14  
**Applies to:** CUBI platform, CUBI Engineering, CUBI Enterprise and the personal workbench entry surface  
**Governed by:** `CUBI-ARCH-ENV-001`

## 1. Product design objective

CUBI should deliver a professional and coherent overall experience. At this stage, however, a shared visual identity implementation, shared shell, shared tokens or shared component library is a hypothesis to evaluate—not a mandatory constraint. Engineering and Enterprise may require different visual and interaction decisions based on their users, workflows, information density and existing technical foundations.

The objective is not to imitate the appearance of Primavera, Microsoft, Autodesk, Planview or another reference product. Those products may inform functional research and usability analysis; their vendor-specific palettes, isolated component conventions and visual identities must not be copied into individual CUBI modules.

## 2. Product hierarchy

The visual and navigation hierarchy is:

1. **CUBI platform identity** — the stable product brand; shared typography, design tokens and global interaction principles may be explored later, but are not required for initial environment delivery.
2. **Personal workbench / entry surface** — the user's personal starting point and authorized environment switch; it is not a third work environment.
3. **CUBI Engineering shell** — the specialist engineering workspace, preserving its existing approved visual workspace and behavior.
4. **CUBI Enterprise shell** — the organizational and project-management workspace, designed initially around its own validated product needs.

Engineering and Enterprise may have different navigation structures, visual treatments and work surfaces during initial design. Potential commonality should be evaluated from real screens and user journeys rather than imposed in advance.

## 3. Candidate semantic token system (optional future convergence)

A semantic token system is a candidate future shared foundation. Do not require initial screens or components in either environment to consume a common token system before design exploration and compatibility validation are complete.

Required token families:

- **Color:** product canvas, elevated surface, primary text, secondary text, muted text, border, divider, primary action, secondary action, focus, selected, information, success, warning, danger, disabled and environment-context accent.
- **Typography:** font families and fallbacks, language-specific font selection, size scale, weight scale, line heights, numeric/data typography and heading hierarchy.
- **Spacing and sizing:** spacing scale, control heights, icon sizes, content widths, navigation widths and responsive breakpoints.
- **Shape and depth:** corner radii, border widths, elevation/shadow levels and overlay layering.
- **Motion:** transition durations, easing and reduced-motion behavior.
- **Interaction:** hover, pressed, selected, focused, disabled, loading, validation, success, warning and error states.
- **Data visualization:** categorical, sequential and diverging chart palettes with accessible contrast and consistent meaning.

Do not finalize raw hex palettes, typography choices or visual assets by copying a competitor. Establish the CUBI brand direction and test token combinations across both environments, light/dark themes if supported, data-dense screens and RTL/LTR layouts before approving concrete values.

## 4. Color governance and environment distinction

- A centrally managed CUBI color system may be considered after the initial environment designs are reviewed.
- If shared semantic colors are adopted, their meanings must remain consistent across the scopes where they are used.
- Engineering and Enterprise may use a restrained environment-context accent to help users recognize where they are. This accent is a tokenized context cue, not a separate brand palette.
- During initial design, environment-specific palettes are permitted. Avoid arbitrary or inaccessible choices; do not copy a vendor's brand palette as CUBI identity.
- Within each environment, charts, badges, buttons, status indicators, alerts and navigation states should use consistent semantic rules.
- If an environment supports theme variants, each variant should pass contrast and accessibility checks; a shared token source is optional.

## 5. Independent environment shell design

Engineering and Enterprise may each define a complete product frame suited to their users, workflows, information density and technical foundations. The following common patterns are optional design candidates, not shared-shell requirements or acceptance gates.

### Optional common patterns to evaluate

- Product identity and environment/context indicator.
- Consistent global header and account/notification affordances where applicable.
- Predictable primary navigation and secondary navigation patterns.
- Breadcrumbs or equivalent location context for deep information architectures.
- Main workspace/content region with consistent width and density rules.
- Contextual action/tool area with predictable placement.
- Shared search, filtering and command/action patterns where supported.
- Consistent empty, loading, error, permission-denied and offline states.
- Responsive behavior and accessible keyboard/focus navigation.

### Engineering shell

- Preserve the existing Engineering Visual Workspace, navigation, route behavior and approved interaction model.
- This specification does not authorize an Engineering shell redesign, route migration, broad CSS replacement or layout refactor.
- Any future adoption of shared tokens or components in Engineering must be proposed as a separate, narrowly scoped change with before/after evidence, regression tests and explicit Engineering-owner approval.

### Enterprise shell

- Establish an Enterprise visual direction appropriate to its validated workflows; it may be designed independently and need not adopt shared tokens or Engineering components.
- Organize the eight Enterprise modules and cross-cutting capabilities within one coherent information architecture.
- Support role- and permission-aware navigation without exposing unauthorized destinations.
- Use dashboard, portfolio, project, workflow and operational surfaces with consistent page anatomy and component behavior.
- Keep Enterprise modules internally coherent where usability testing supports it; module-level differences may be retained when they serve a clear workflow need.

### Personal workbench

- Remains the common entry and personal coordination surface.
- Provides the authorized environment choice and personal work context.
- May share selected brand cues with either environment where useful, without requiring visual convergence or becoming a third work environment.

## 6. Component and interaction standards (environment-owned initially)

Each environment may define the components and interaction rules required by its own product. The following inventory is a useful review checklist; it does not require a shared component library:

- Buttons, icon buttons, links and destructive actions.
- Inputs, text areas, selects, date/time controls and validation messages.
- Menus, command menus, tabs, segmented controls and navigation items.
- Tables, trees, data grids, filters, sorting, pagination and bulk actions.
- Cards, panels, dashboards, portlets and summary metrics.
- Dialogs, drawers, popovers, tooltips and confirmation patterns.
- Status indicators, badges, alerts, toasts and notifications.
- Charts, timelines, Gantt-adjacent summaries and data legends.
- Empty states, skeleton/loading states, errors, retry and permission-denied states.

Within each environment, components should have documented interaction states, keyboard behavior, focus visibility, accessible labels and responsive rules. Color must never be the only carrier of status or meaning.

## 7. Localization, RTL and accessibility

- Persian/RTL and English/LTR are first-class supported layout directions.
- Direction-sensitive spacing, alignment, navigation, icons, tables, forms and chart labels must adapt correctly.
- Use appropriate Persian and Latin font fallbacks with consistent hierarchy and legibility.
- Numeric values, dates, units and mixed-direction identifiers must have documented formatting rules.
- Meet WCAG-aligned contrast and keyboard-accessibility expectations; include focus, hover and selected states in review.
- Respect reduced-motion preferences and avoid interaction that depends solely on hover.

## 8. Design governance and change control

- This document is an exploratory reference, not a binding design-system source of truth.
- Each environment may approve and evolve its own initial screen and component specifications.
- A later shared-system proposal must include evidence of value, usability and compatibility; it is optional and requires explicit product-owner approval.
- Functional references and screenshots from competitors are research evidence only.
- If a shared component is proposed later, its impact must be evaluated for every environment that adopts it.
- Changes that touch Engineering must not proceed under the Enterprise workstream alone; they require separate Engineering scope, compatibility tests and explicit approval.
- Do not claim the design system is implemented merely because this specification exists. Implementation requires token definitions, component inventory, shell implementation, visual regression coverage, accessibility checks and verified RTL/LTR behavior.

## 9. Recommended design-system deliverables

1. CUBI brand and visual-direction brief.
2. Semantic token catalog and theme mapping.
3. Typography and localization specification.
4. Candidate shared component inventory, only if later evaluation supports convergence.
5. Personal workbench shell specification.
6. Engineering shell compatibility map (documentation only unless separately approved).
7. Enterprise shell information architecture and layout specification.
8. RTL/LTR and accessibility review checklist.
9. Visual regression and design acceptance criteria.

## 10. Future evaluation criteria (not current release gates)

The following are evaluation criteria for a possible later shared design system. They are not requirements that must be satisfied before either environment can progress independently.

- [ ] Initial Engineering and Enterprise designs have been reviewed in their actual product contexts.
- [ ] Candidate shared identity, tokens, components and shell patterns have demonstrated measurable value.
- [ ] Usability and responsive behavior have been evaluated across representative user journeys.
- [ ] Persian/RTL and English/LTR behavior has been tested.
- [ ] Accessibility, keyboard behavior and contrast have been reviewed.
- [ ] Regression and compatibility tests pass for every environment affected by a proposed shared element.
- [ ] Existing Engineering behavior and shell remain protected unless a separately approved change explicitly says otherwise.
- [ ] Product owners explicitly approve the scope and timing of any shared-system adoption.
- [ ] Implementation and validation status are reported separately from this exploratory specification.
