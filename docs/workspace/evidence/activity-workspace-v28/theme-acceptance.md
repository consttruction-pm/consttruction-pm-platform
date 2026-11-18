# V28 Theme Acceptance — Six Skins

- Tested code: `2b7d035a1fc459ea71f8563bb8e285b218aa957f` (filter fix and dark-skin row fix).
- Browser: local full-stack preview, headless Chrome, 1366×768, English.
- Evidence: `theme-acceptance.json` + `theme-<skin>-en-1366.png` in this directory.

## Result

| Skin | Captured | Distinct tokens | Row contrast | Reload | Overflow |
|---|---|---|---|---|---|
| CUBI Classic — Version 26 Reference | `theme-classic-en-1366.png` | yes | n/a (light) | — | 0 px |
| CUBI Modern 3D | `theme-modern-en-1366.png` | yes | n/a (light) | — | 0 px |
| CUBI Graphite — Dark | `theme-graphite-en-1366.png` | yes | **13.65 : 1** | — | 0 px |
| CUBI Arctic — Light | `theme-arctic-en-1366.png` | yes | n/a (light) | — | 0 px |
| CUBI Copper — Warm | `theme-copper-en-1366.png` | yes | n/a (light) | — | 0 px |
| CUBI Midnight — Deep | `theme-midnight-en-1366.png` | yes | **14.14 : 1** | **persisted (`midnight`)** | 0 px |

The suite asserts:

- the select value matches the requested skin;
- no horizontal document overflow;
- the titlebar, grid header and task bar exist;
- the six skins produce six distinct token signatures (titlebar, menubar, header,
  data row, details);
- dark skins do not inherit the light layout row background and meet WCAG AA
  contrast for body text;
- the chosen skin survives a full reload;
- CUBI Classic is restored at the end;
- zero browser exceptions, console errors and API 5xx.

## Defect found and fixed

The first theme run exposed a real visual defect: **CUBI Midnight and Graphite
rendered activity rows with near-white text on a white cell background**, because
the persisted layout table background overrode the dark surface. The screenshot
`theme-midnight-en-1366.png` before the fix showed effectively invisible activity
names.

Fix: a dark-skin-only CSS rule keeps task rows on `--skin-surface` with
`--skin-grid-text`, uses distinct even/hover/selected/filter surfaces, and leaves
WBS band/summary colours untouched. Applies to `styles.css` and
`public/styles.css` (shared-file change disclosed in the PR).

After the fix the measured contrast is 13.65:1 (Graphite) and 14.14:1 (Midnight)
and the rows are readable in the captured screenshots.

## Limits

- The suite measures the name-cell contrast; it does not compute contrast for
  every control in every skin.
- No vendor screenshot comparison: themes are CUBI identity, not a rebuild of the
  vendor palette (the PDF defines structure/behaviour, not CUBI colours).
- Persian/RTL theme screenshots are not part of this run; RTL is covered by the
  responsive suite in Classic.
