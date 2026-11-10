# CUBI Workspace — Theme and Localization Coverage (2026-11-09)

This note records the implemented surface, the measured layout behaviour and the
verification actually executed for the workspace master-order increment. It is
an evidence index, not a substitute for the automated checks.

## 1. One workspace, two token systems

| Item | Implementation |
| --- | --- |
| Renderer | One workspace renderer in `apps/web/src/workspace-view.ts`; no duplicate shell. |
| Commands | One registry in `apps/web/src/workspace-desktop-shell.ts`; both skins share every command id. |
| Menus | One menu model; `View` carries `view.toggle-details`, `view.theme-classic`, `view.theme-modern`. |
| Skins | Six selectable CUBI themes: Classic (default), Modern 3D, Graphite (dark), Arctic (light), Copper (warm), and Midnight (deep dark). |
| Tokens | Classic retains its flat reference surface; the five layered themes share one structural renderer and use independent palette tokens. `apps/web/styles.css` and `apps/web/public/styles.css` remain byte-identical. |
| Persistence | `cubi:workspace-theme` in `localStorage`, read at boot and written on change. |
| Branding | All six themes use CUBI identity and typography; no third-party logo or product claim is introduced in the customer-facing workspace. |

The selected theme changes only palette, surface treatment and native color scheme. All six themes retain the same data, scheduling, permissions, dialog behavior and command availability.

## 2. Details visibility and collapse

The bottom-bar control `[data-details-toggle]` (beside the calendar selector) and
`View > Hide Details / Show Details` call the same command and share one state.
The pane is scoped per user, tenant, project and workspace window through
`cubi:workspace:details-visible:<user>:<tenant>:<project>:<menu>`.

When hidden, the container applies `data-details-collapsed="true"`; the CSS
grid becomes a single row, the splitter and `#cp-details` are `display:none`, and
no reserved strip remains. Measured on the live preview (Chromium, DPR 1):

| Viewport | Details shown height | Primary height shown | Primary height hidden | Details hidden height | Toggle / calendar row |
| --- | --- | --- | --- | --- | --- |
| 1280x800 | 187 px | 450 px | 643 px | 0 px | y=741 for both |
| 1440x900 | 217 px | 520 px | 743 px | 0 px | y=841 for both |
| 1920x1080 | 271 px | 646 px | 923 px | 0 px | y=1021 for both |

Reopening restores the previous height (187 / 217 / 271 px) and splitter. The
toggle stays above the fixed preview banner at every viewport. The same state is
covered by reload persistence and by the View menu command in
`apps/web/e2e/workspace-master-order.mjs`.

## 3. Localization registry

All nine launch languages resolve through one workspace registry
(`apps/web/src/workspace-localization.ts`). Direction and display name are
declared once; translation lookup order is: packed `ui.*` keys, the Persian
inline dictionary, the documented German/Chinese table, the catalog map, then
English.

| Locale | Direction | Translation source | Measured coverage |
| --- | --- | --- | --- |
| en | LTR | source strings | baseline |
| fa | RTL | inline Persian dictionary | existing hand-authored coverage |
| de | LTR | `UI_TRANSLATIONS` | 535 UI strings + 26 column labels |
| zh | LTR | `UI_TRANSLATIONS` | 535 UI strings + 26 column labels |
| ar | RTL | `workspace-locale-catalogs.ts` | 225 keys (command surface, dialogs, details, columns) |
| fr | LTR | `workspace-locale-catalogs.ts` | 225 keys |
| ja | LTR | `workspace-locale-catalogs.ts` | 225 keys |
| ko | LTR | `workspace-locale-catalogs.ts` | 225 keys |
| ru | LTR | `workspace-locale-catalogs.ts` | 225 keys |

The browser language is detected at first boot (including `ru`), and the chosen
language persists in `cubi:workspace-locale`. Menus, toolbar labels, dialogs,
detail tabs, the theme selector, the Details tooltip and activity-grid column
headers are translated; Arabic and Persian switch the document to RTL. The
localization test asserts that every catalog locale resolves the command
surface and that `ar` is RTL while `ru` is LTR.

Known limit: catalogs cover the workspace command and table surface enumerated
in the test, not arbitrary user or project data. Untranslated free text falls
back to English by design rather than showing a placeholder.

## 4. Executed verification

| Command | Result |
| --- | --- |
| `npx tsc --noEmit` | pass |
| `npm test` | 680 source tests + 14 preview-server tests pass, 0 fail |
| `npm run build` | pass (`tsc -p tsconfig.build.json` + esbuild 0.28.2) |
| `npm run test:e2e:preview` (isolated runtime, `--reset`, random port) | 98 recorded checks pass |
| `node e2e/workspace-master-order.mjs` | 14 recorded checks pass |
| `node e2e/context-menus-v26.mjs` | 84 checks pass (fresh runtime) |
| `node e2e/activities-v26-scenarios.mjs` | 18 scenarios pass (fresh runtime) |

The master-order run records `e2e/artifacts/master-order/report.json` with
contract `cubi-workspace-master-order.v1`, the layout numbers above, and
screenshots at 1280x800, 1440x900 and 1920x1080 for both Details states and
all six themes, plus Russian/Arabic locale captures. Each added theme is checked
for a distinct visual token fingerprint while retaining the same activity rows,
Gantt bars and Details tabs; Midnight persistence is checked across reload. The page-by-page Version 26 parity
matrix for the Activities window remains
`docs/qa/ACTIVITIES_V26_COMPLIANCE_MATRIX_2026-11-08.md`; this increment does not
change that scope.

The live preview database accumulates layout revisions across manual runs. The
revision-history API caps a listing at 50 entries, so the long-lived preview can
exceed the history window expected by an older assertion. The full preview suite
is therefore run with its own isolated `--reset` database, which is the
documented CI path; this is an environment limit, not a product defect.


## 5. Six-theme visual contract

- **Classic** — compact reference workstation appearance and default.
- **Modern 3D** — light layered surfaces, elevated cards and engineering-blue highlights.
- **Graphite** — charcoal/slate dark workspace with a crisp teal accent.
- **Arctic** — cool bright workspace with restrained teal and frosted surfaces.
- **Copper** — warm ivory workspace with copper accents and deep bronze chrome.
- **Midnight** — deep navy workspace with clear blue highlights for low-light work.

All non-Classic themes use one shared layered component renderer. Their palette
tokens cover background, chrome, text, borders, selection, hover, grid header,
row states, navigation, Details pane, dialogs, focus rings, shadows and native
light/dark color scheme. Activity, WBS, Gantt and relationship logic are not
reimplemented by a theme.
