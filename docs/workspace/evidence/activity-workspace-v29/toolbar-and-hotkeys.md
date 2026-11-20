# V29 — Toolbars, commands and two-step accelerators

## Toolbar families

The reference (PDF pp. 16–17 and the toolbar chapters) records 18 toolbar families.
CUBI now registers **21 right-rail families**: the 18 reference families are all
represented by name/role, and three earlier CUBI-specific rails remain because they
own working commands (Activity, Critical Check, Schedule). No empty family was created
and no button exists without a command or a disabled reason.

| # | Reference family | CUBI family id | Buttons |
|---:|---|---|---:|
| 1 | Action | `action` | 6 |
| 2 | Administrator | `administrator` | 6 |
| 3 | Assign | `assign` | 3 |
| 4 | Bottom Layout | `bottom-layout` | 5 |
| 5 | Dictionaries | `dictionaries` | 4 |
| 6 | Display | `display` | 9 |
| 7 | Edit | `edit` | 7 |
| 8 | Enterprise | `enterprise` | 5 |
| 9 | Find | `find` | 3 |
| 10 | Layout | `layout` | 12 |
| 11 | Move | `move` (new) | 4 |
| 12 | Print | `print` | 2 |
| 13 | Project | `project-tools` (label Project) | 4 |
| 14 | Publish | `publish` | 3 |
| 15 | Reports | `standard-reports` (label Reports) | 4 |
| 16 | Standard | `standard` (new) | 12 |
| 17 | Tools | `tools` | 7 |
| 18 | Top Layout | `top-layout` (new) | 3 |
| — | CUBI Activity | `activity` | 6 |
| — | CUBI Critical Check | `critical-check` | 5 |
| — | CUBI Schedule | `schedule` | 4 |

130 commands are registered in total. The new Standard family exposes New, Open,
Save Layout, Print, Undo, Redo, Cut, Copy, Paste, Delete Activity, Find and Help; Cut,
Copy, Paste and Delete are **disabled with a stated reason** because the clipboard and
activity deletion have no server contract. Move exposes Move Up/Down/Outdent/Indent and
is disabled with a reason: row reordering is not stored by the project service, so the
control must not look operational. Top Layout runs the real `view.top-table`,
`view.top-table-gantt` and `view.top-network` commands.

Reports is no longer an empty toolbar: it owns Reports, Tracking, Report Wizard and
Print. The Report Wizard is disabled with the existing report-renderer reason.

## Two-step Alt accelerators

A pure, testable dispatcher (`advanceAltSequence` / `matchAltSequence`) was added in
`workspace-desktop-shell.ts`:

- first chord starts a 2,000 ms waiting state and still opens the menu;
- a visible status hint states "press the second key (Esc cancels)" and is cleared on
  match, mismatch, Escape or timeout;
- typing in input/textarea/select/contenteditable and modal dialogs keep precedence;
- the second key must not carry Ctrl/Meta; Alt may be held or released;
- a match prevents the menu's first-letter navigation and runs the binding.

Recorded bindings:

| Keys | Command | Status |
|---|---|---|
| Alt+F, N | File > New (project window) | works |
| Alt+F, O | File > Open (project window) | works |
| Alt+E, Z | Edit > Undo | works when a layout change exists |
| Alt+E, T | Edit > Cut | disabled — clipboard not connected |
| Alt+E, C | Edit > Copy | disabled — clipboard not connected |
| Alt+E, P | Edit > Paste | disabled — clipboard not connected |
| Alt+E, A | Edit > Add activity | works |
| Alt+E, D | Edit > Delete | disabled — deletion not implemented |
| Alt+E, F | Edit > Find | works |
| Alt+E, R | Edit > Replace | disabled — replace not implemented |
| Alt+V, O | View > Options | **no such View command** in the reference menu; disabled with that reason (nothing guessed) |
| Alt+P, A | Project > Activities | works |
| Alt+H, L | Help > Local Help | opens Keyboard shortcuts |
| Alt+H, A | Help > About | works |
| Alt+H, O | Help > Online Help | disabled — needs network; local preview does not open it |

PDF "Using Shortcut Keys" (pp. 16–17) was used to correct the single-key catalogue:

| PDF | Before | Now |
|---|---|---|
| F7 Spell Check | F7 was "Level resources" | F7 Spell check, disabled with reason |
| Shift+F9 Level Resources | Shift+F9 was "Schedule options" | Shift+F9 Level resources, disabled with reason |
| Shift+F12 Disable Auto-Reorganization | Shift+F12 was "About" | Shift+F12 Disable auto-reorganization, disabled with reason; About is Alt+H,A |
| F10 Commit Changes | already documented | unchanged, disabled with reason |
| Ctrl+R Replace | missing | added, disabled with reason |
| Alt+F1 Hint Help | missing | added, disabled with reason |

`Ctrl+W` remains "Close window" in CUBI, while the reference labels it "Close All";
the difference is recorded in `remaining-items.md` and was not silently rewired.
