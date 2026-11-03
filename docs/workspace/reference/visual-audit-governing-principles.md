# CUBI Visual Audit — Governing Principles (Mandatory)

Status: **Binding acceptance policy** for every CUBI visual workspace page and component.
Target reference: **P6 Professional desktop Version 26**, using the current official Version 26 Help and User Guide as the controlling evidence set.
Scope: every workspace page/window, menu, submenu, toolbar, dialog, tab, panel, table, chart, Gantt view, calendar picker, context menu, popover, status/layout bar and responsive state.
This policy applies to all future visual-audit and implementation work. It is not optional and must not be silently weakened or replaced by a general design-system or theme task.

## 1. Non-negotiable rule

Audit and implement **the complete visual and interaction surface**, page by page and control by control, against the corresponding Version 26 desktop documentation. A page is not complete because its title, menu item, empty shell or static mockup exists. Every documented component, option, field, menu/submenu, visual state, default, colour control, geometry and context-dependent behaviour must be accounted for.

The same rule applies to colours and appearance. Do not postpone Gantt/chart colour configuration, bar styling, table/group formatting, menu/window visual details, fonts, borders, selection states, line styles or legends to the later CUBI theme phase. The later theme phase may choose a cohesive CUBI-wide theme, but it must not be used as a reason to omit or defer the Version 26 visual controls and their behaviour.

## 2. Page-by-page GitHub evidence is mandatory

Every audited page/window/component must have its own traceable record in the GitHub audit ledger (or a clearly identified row/section in the relevant page inventory). Do not record only a general statement that the workspace was checked.

Each record must include:
1. CUBI page/window/component name and route or registry key.
2. Exact Version 26 reference page/topic and edition/context qualifier.
3. Inventory of the visible regions, menus/submenus, tabs, fields, options, icons, buttons, charts, legends, colour/style controls and states applicable to that page.
4. Reference default appearance and behaviour, plus user-configurable choices. Distinguish documented facts from screenshot observations and from CUBI-only decisions.
5. Current CUBI implementation path(s), component/registry identifiers and the precise gap.
6. Action taken (implemented, corrected, removed, or intentionally disabled) and why.
7. Test evidence (unit/runtime, interaction/E2E, RTL/LTR, locale and viewport as applicable).
8. Screenshot/evidence path and review date.
9. Status: **Not audited / Evidence incomplete / Gap found / Implemented-unverified / Verified / Blocked**. Only **Verified** may count toward completion. A disabled control is not Verified unless the reference semantics and the reason for disabling it are both documented and tested.

## 3. Required visual comparison dimensions

For every page, inspect and record all applicable dimensions; mark a dimension N/A only with a reason supported by the reference:
- Window geometry, title/header, split panes, panel order, sizing, splitters, docking, scrolling and resize behaviour.
- Main menu and contextual menu hierarchy, submenu nesting, toolbar membership/order, icons, captions, separators, shortcuts, hover/focus/pressed/disabled/selected states and context-sensitive enablement.
- Tabs, tab order, selected state, lower-pane configuration, labels, field order, units, required/read-only states, validation and empty/no-selection states.
- Typography, font size/weight, row height, spacing, alignment, borders, gridlines, fills, selection/highlight, focus rings and status indicators.
- Colour values and colour pickers wherever documented; distinguish reference defaults from configurable values. Do not invent a global reference palette when the documentation does not specify one.
- Every chart-specific visual property: chart type, axes, timescale, series, bar/line/marker shape, colour, pattern, thickness, labels, legends, background/grid lines, thresholds, data-date/progress indicators, relationship lines, stacking, grouping, collapsed/summary states and print/export appearance.
- Keyboard, pointer and accessibility states; RTL/LTR mirroring; language/date/number formatting; Jalali/Gregorian presentation where CUBI supports it; desktop and responsive layout behaviour.

## 4. Gantt and chart requirements — complete in this phase

Gantt and chart visual functionality is **in scope now**, not deferred to theme design. The audit must cover the complete documented configuration surfaces and the resulting rendered chart.

For Gantt this includes, where supported by the Version 26 reference: bar list and bar definitions; Display/Name/Timescale/Filter; Bar Style including start/body/finish shapes, colour and pattern; Bar Settings including row/stacking/summary/collapsed/necking behaviour; Bar Labels and label positions; relationship lines; background lines; legend; data date line; progress line; timescale rows, intervals, calendars and fonts/colours; nonworking periods; activity/table row alignment; attachments/curtains and all documented display toggles.

For Activity Network, Trace Logic, Activity/Resource Usage Profiles and Tracking charts, audit each distinct layout family and its own documented options: node/box layout, fields, fonts/colours, connectors, direction/arrangement, axes, timescale, histogram/profile mode, data fields, availability/overallocation/limits/overtime, past actuals, legends, background lines, grouping/filtering and lower-pane controls. Do not treat these as one generic chart.

Every colour/style option must be represented in the UI at the correct configuration surface and affect the corresponding chart state. A decorative colour swatch that does not change the rendered chart is not implementation.

## 5. Reference and truth rules

- Use the current **desktop Professional Version 26** documentation. Record EPPM/server-only qualifiers and do not import those features into the desktop target without an explicit CUBI product decision.
- Do not infer a control from a similar title or from another edition/version. If the source does not establish it, mark **Evidence incomplete** and investigate; do not fabricate.
- Keep a distinction between documented menu commands, related-topic links, toolbar actions and dialog options. A topic title is not automatically a menu item.
- Use current-release screenshots for pixel-level/default-colour claims. If screenshots are unavailable, record structural/behavioural parity only and explicitly mark pixel/default-colour verification incomplete.
- Oracle/Primavera branding, names, logos and external source URLs must never appear in the user-facing CUBI interface. They may appear in internal engineering reference documents only.
- No fake functionality: preview-only controls must be visibly and accurately marked/disabled, with their implementation state and reason. Do not report them as complete.

## 6. Change safety and completion gates

1. Inspect the existing implementation and prior audit record before editing. Preserve completed work; do not replace whole pages or apply broad CSS overrides without evidence.
2. Make scoped changes tied to specific reference gaps. Keep shared CSS source/public copies synchronized.
3. Add or update tests for every corrected behaviour and for both English/Persian plus RTL/LTR where applicable.
4. Run the relevant local checks and GitHub CI on the exact final commit. Fix failures before marking Verified.
5. Re-open the rendered page and inspect the actual result; passing text assertions alone do not prove visual parity.
6. Keep the PR open and unmerged while any required page is unverified or CI is failing. Never claim full completion based on inventory/documentation alone.
7. Update the page's GitHub audit record in the same work unit as the code change, including commit SHA, tests and evidence path.

## 7. Required audit sequence

Work in controlled slices: shell and menus; each window; each dialog and tab; each table; each chart family; Gantt configuration and rendered states; toolbars/context menus; print/export; then responsive and multilingual states. Within each slice: **reference → inventory → inspect current CUBI → implement/correct → test → screenshot review → update GitHub record**. Do not skip ahead or mark an entire page complete while subcomponents remain unverified.

## 8. Theme phase boundary

The later CUBI theme phase may harmonize brand tokens and offer user-selectable themes. It must preserve the controls, per-element overrides, reference defaults, and chart-rendering semantics verified here. The existence of a future theme phase does not excuse missing colour pickers, bar styles, chart palettes, fonts, line styles or appearance settings in this phase.

## 9. Required per-page audit record template

Use this template for every page/window or chart family:

| Field | Required entry |
|---|---|
| Page/window/component | Exact CUBI name + route/registry key |
| Version 26 source | Exact topic/page + edition/context |
| Subcomponents | Menus, tabs, panels, fields, chart layers, controls |
| Appearance | Geometry, typography, colours, shapes, borders, states |
| Defaults vs options | Reference defaults and all documented user choices |
| CUBI implementation | File paths + component/registry keys |
| Gaps and changes | Each gap, correction/removal and rationale |
| Verification | Test names/results, locales, RTL/LTR, viewports |
| Visual evidence | Screenshot path(s), review date |
| Commit | Exact commit SHA |
| Status | One of the defined audit states; Verified only after all gates |

This document is the governing rule. All workspace visual inventories, reference indexes, implementation logs and future page audits must link back to it and follow it.
