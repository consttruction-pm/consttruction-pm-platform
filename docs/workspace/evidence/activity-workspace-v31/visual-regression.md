# V31 — Visual evidence

- Viewport: 1366 × 768, English (LTR), Classic Schedule Layout, local preview.
- Theme: default Classic. Screenshots are real browser captures from `activity-v31-renumber-copy.mjs`; they are not mockups.

## Captures

| File | What it proves |
|---|---|
| `screenshots/01-renumber-preview-en-1366.png` | Renumber dialog: method radios, Increment value, baseline checkbox, live preview row `V31A… → V31A…`, “1 activity ID(s) will change”, enabled Renumber button |
| `screenshots/02-renumber-complete-en-1366.png` | Grid after apply; new ID selected; old row removed |
| `screenshots/03-copy-options-en-1366.png` | Pasted activity row after Copy Options apply |
| `screenshots/04-fill-down-preview-en-1366.png` | Fill Down dialog with the exact Original Duration value and target count |
| `screenshots/05-fill-down-complete-en-1366.png` | Target row after Fill Down |
| `screenshots/06-curtains-hidden-en-1366.png` | Attachments dialog and chart after Hide All |
| `screenshots/07-curtains-shown-reload-en-1366.png` | Curtains restored after Show All and workspace reload |

The V30 suites were re-run at the same SHA and refreshed their screenshots under `activity-workspace-v30/screenshots/`. The V30 Edit menu now also shows “Renumber Activity IDs…”.

## Layout checks performed

- Dialog width and readable form flow after the new `.cp-activity-copy-dialog`, `.cp-activity-renumber-dialog` and `.cp-activity-fill-dialog` rules.
- Mode-specific fields hide and show with the selected radio.
- Preview input column is editable and conflicts are styled red.
- Curtain bulk buttons disable when no curtain needs the action.
- The Paste dialog appears before any write and closes before the grid refresh.

## Not covered

- Six themes, three screen sizes and Persian RTL for the three new dialogs. V30’s 84-capture matrix remains the visual baseline; extending it to the new dialogs is listed in `remaining-items.md`.
