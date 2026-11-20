# V30 — Visual comparison matrix

## Scope

`apps/web/e2e/visual-matrix-v30.mjs` captured the real preview at:

- themes: classic, modern, graphite, arctic, copper, midnight (6)
- sizes: 1280×720, 1366×768, 1920×1080 (3)
- languages: English LTR, Persian RTL (2)

That is **36 main-window cells** plus **12 dialog cells** (6 themes × 2 languages at 1366×768),
each dialog cell containing the Edit menu, the Gantt Attachments dialog, the Replace dialog and
the Spell Check dialog. **84 screenshots** are stored under `visual/`.

## Assertions

For every main-window cell:

- theme select shows the requested theme;
- document horizontal overflow ≤ 1 px (observed maximum: **0 px**);
- toolbar rail, Details pane, menu bar, Gantt bar layer and Attachments button are present;
- `dir=rtl` for Persian and not RTL for English;
- graphite/midnight activity-row contrast ≥ 4.5:1 (observed 13.65:1 and 14.14:1 in the sampled
  cells);
- theme signatures are distinct (at least six distinct row/header style pairs).

For every dialog cell:

- the dialog opened (`open` attribute / `showModal`);
- the dialog rectangle is fully inside the viewport (no clipping at 1366×768);
- the Spell Check inputs carry `spellcheck="true"`;
- the Edit menu renders with the new Replace/Spell/Fill Down/Dissolve entries.

## Result

- `visual-matrix-v30.json`: `result=pass`, 36 cells, 12 dialog cells, 84 screenshots.
- No JS exception and no API ≥500 response during the run.
- Classic theme and English locale were restored at the end.

## What this does not prove

Screenshots are evidence of layout and state, not proof of every interaction. Functional proof is
in `activity-edit-v30.json` and `gantt-attachments-v30.json`. The matrix does not enumerate every
menu item or every Activity Details field; the menu/toolbar and dialog audits list what was
checked by tests and what remains `verify` in the 264-topic disposition.
