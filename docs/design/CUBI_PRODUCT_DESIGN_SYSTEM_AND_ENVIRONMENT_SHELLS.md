# CUBI Product Design System & Environment Shells

**Document ID:** CUBI-DESIGN-SYSTEM-001  
**Status:** Product-owner direction / design-system specification baseline  
**Date:** 2026-11-14  
**Applies to:** CUBI platform, CUBI Engineering, CUBI Enterprise and the personal workbench entry surface  
**Governed by:** `CUBI-ARCH-ENV-001`

## 1. Product design objective

CUBI must look and behave like one professionally designed, coherent software product. Engineering and Enterprise are distinct work environments with different users, workflows, information density and navigation needs, but they must share one CUBI visual identity and one interaction language.

The objective is not to imitate the appearance of Primavera, Microsoft, Autodesk, Planview or another reference product. Those products may inform functional research and usability analysis; their vendor-specific palettes, isolated component conventions and visual identities must not be copied into individual CUBI modules.

## 2. Product hierarchy

The visual and navigation hierarchy is:

1. **CUBI platform identity** — the stable brand, typography, design tokens and global interaction principles.
2. **Personal workbench / entry surface** — the user's personal starting point and authorized environment switch; it is not a third work environment.
3. **CUBI Engineering shell** — the specialist engineering workspace, preserving its existing approved visual workspace and behavior.
4. **CUBI Enterprise shell** — the organizational and project-management workspace, built with the same CUBI design language.

Engineering and Enterprise may have different navigation structures and work surfaces. They must not look like unrelated applications.

## 3. Single source of truth: design tokens

Create a centrally governed token system with semantic names. Components must consume semantic tokens rather than hard-coded colors, spacing, radii or shadows.

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

- CUBI has one centrally managed color system.
- Colors communicate semantic meaning consistently across every module. For example, danger must not mean a neutral status in one module and success in another.
- Engineering and Enterprise may use a restrained environment-context accent to help users recognize where they are. This accent is a tokenized context cue, not a separate brand palette.
- Module owners cannot invent their own unrelated palette or assign arbitrary colors to imitate the source product from which a feature was researched.
- Charts, badges, buttons, status indicators, alerts and navigation states must follow the same semantic rules.
- Theme variants must derive from the same token definitions and pass contrast checks.

## 5. Complete shell requirements

Each environment shell must be specified as a complete product frame, not as a collection of independent pages.

### Shared shell grammar

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

- Use the CUBI visual language from the first real implementation.
- Organize the eight Enterprise modules and cross-cutting capabilities within one coherent information architecture.
- Support role- and permission-aware navigation without exposing unauthorized destinations.
- Use dashboard, portfolio, project, workflow and operational surfaces with consistent page anatomy and component behavior.
- Do not create a new palette or bespoke button/table/form language for each module.

### Personal workbench

- Remains the common entry and personal coordination surface.
- Provides the authorized environment choice and personal work context.
- Must visually connect to both environment shells without becoming a third shell with a separate identity.

## 6. Component and interaction standards

The design-system library must define shared specifications and usage rules for:

- Buttons, icon buttons, links and destructive actions.
- Inputs, text areas, selects, date/time controls and validation messages.
- Menus, command menus, tabs, segmented controls and navigation items.
- Tables, trees, data grids, filters, sorting, pagination and bulk actions.
- Cards, panels, dashboards, portlets and summary metrics.
- Dialogs, drawers, popovers, tooltips and confirmation patterns.
- Status indicators, badges, alerts, toasts and notifications.
- Charts, timelines, Gantt-adjacent summaries and data legends.
- Empty states, skeleton/loading states, errors, retry and permission-denied states.

Components must have consistent interaction states, keyboard behavior, focus visibility, accessible labels and documented responsive rules. Color must never be the only carrier of status or meaning.

## 7. Localization, RTL and accessibility

- Persian/RTL and English/LTR are first-class supported layout directions.
- Direction-sensitive spacing, alignment, navigation, icons, tables, forms and chart labels must adapt correctly.
- Use appropriate Persian and Latin font fallbacks with consistent hierarchy and legibility.
- Numeric values, dates, units and mixed-direction identifiers must have documented formatting rules.
- Meet WCAG-aligned contrast and keyboard-accessibility expectations; include focus, hover and selected states in review.
- Respect reduced-motion preferences and avoid interaction that depends solely on hover.

## 8. Design governance and change control

- This document and the centrally maintained token/component specification are the source of truth.
- New screens and modules must be reviewed against the design system before acceptance.
- A visual exception requires a documented reason, owner and expiry/review point; it must not become an undocumented local theme.
- Functional references and screenshots from competitors are research evidence only.
- Changes to shared components must include impact analysis for both environments.
- Changes that touch Engineering must not proceed under the Enterprise workstream alone; they require separate Engineering scope, compatibility tests and explicit approval.
- Do not claim the design system is implemented merely because this specification exists. Implementation requires token definitions, component inventory, shell implementation, visual regression coverage, accessibility checks and verified RTL/LTR behavior.

## 9. Recommended design-system deliverables

1. CUBI brand and visual-direction brief.
2. Semantic token catalog and theme mapping.
3. Typography and localization specification.
4. Shared component inventory with states and usage guidance.
5. Personal workbench shell specification.
6. Engineering shell compatibility map (documentation only unless separately approved).
7. Enterprise shell information architecture and layout specification.
8. RTL/LTR and accessibility review checklist.
9. Visual regression and design acceptance criteria.

## 10. Acceptance criteria

- [ ] One CUBI product identity is visible across the platform.
- [ ] Engineering and Enterprise are distinct environments but share one design language.
- [ ] Semantic tokens are the only approved source for shared color, typography, spacing, shape and state values.
- [ ] No module copies a vendor palette or creates an unrelated local visual identity.
- [ ] Complete shell specifications exist for the personal workbench and both environments.
- [ ] Enterprise modules use shared components and interaction rules.
- [ ] Persian/RTL and English/LTR are covered.
- [ ] Accessibility, keyboard behavior and contrast are reviewed.
- [ ] Existing Engineering shell is protected; no redesign is implied or authorized.
- [ ] Implementation status is reported separately from specification status.
