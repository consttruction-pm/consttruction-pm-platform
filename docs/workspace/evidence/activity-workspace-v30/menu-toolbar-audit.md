# V30 — Menu, toolbar and shortcut audit

## What changed in V30

The V29 audit left the clipboard, Delete, Dissolve, Fill Down, Replace and Spell Check as
visible-but-disabled controls. V30 connected all of them to real behaviour. No button was
enabled without a server contract or a working command.

### Edit menu

| Item | Shortcut | Enabled when | Behaviour |
|---|---|---|---|
| Cut | Ctrl+X | ≥1 activity selected | Stores authoritative source IDs; Paste creates first, then deletes the sources with their record revisions |
| Copy | Ctrl+C | ≥1 activity selected | Stores authoritative source IDs; Paste re-reads each source and creates new Activity Master rows |
| Paste | Ctrl+V | A clipboard exists for the current project | Creates a row per source with a collision-free ID (`-C1`, `-C2`, …), starts it planned, copies codes/notebook/steps, refreshes the grid |
| Delete | Del | ≥1 activity selected | Confirmation, then a revision-checked DELETE; refused when relationships/children/assignments/documents exist |
| Dissolve | — (menu/toolbar) | Selected activity has a predecessor **and** a successor | Joins every predecessor to every successor (first half + second half), removes the old links and the activity |
| Fill Down | Ctrl+E | ≥2 activities selected | Copies the first selected activity name down the selected rows |
| Replace… | Ctrl+R | Activities loaded | Find/replace over displayed activity names with preview count, match-case and selection scope |
| Spell Check… | F7 | Activities loaded | Review dialog with browser spellcheck-enabled fields; saves corrected names under record revisions |

The Edit toolbar buttons use the same commands and the same preconditions. Toolbar and menu
states are computed in the desktop shell from capabilities (`hasSelectedActivity`,
`hasActivityClipboard`, `hasMultiSelection`, `canDissolveActivity`), not from a client guess.

### Alt sequences

`Alt+E, T` / `Alt+E, C` / `Alt+E, P` / `Alt+E, D` / `Alt+E, R` are now live bindings. The
dispatcher still waits, cancels on Escape, times out after 2 s and never fires while typing in
a field. The reference’s three-step `Alt+E, I, L`-style Dissolve accelerator is not present in
the two-step table and is therefore not invented; Dissolve is reachable from the menu and the
toolbar.

### Toolbar rails

- The Version 26 family list from V29 is unchanged (6 left, 21 right).
- `edit.fill-down`, `edit.dissolve`, `standard.cut`, `standard.copy`, `standard.paste` and
  `standard.delete` now target the real commands; previously several targeted
  `edit.select-all` or `view.collapse-to` only to keep an icon visible.
- Gantt toolbar: a new **Attachments** button with a live count opens the curtain/text/notebook
  dialog.
- Commands with no service remain disabled with a reason: enterprise users, security profiles,
  currencies, audit, baselines, reports and the other long-tail items listed in V29.

### Shortcut catalogue

`Ctrl+X`, `Ctrl+C`, `Ctrl+V`, `Del`, `Ctrl+R`, `F7` and `Ctrl+E` are executable or explicitly
unavailable with a reason. `F3` (Find Next) and `F10` remain unavailable; `F5` refreshes.
Shortcut matching is tested for modifiers, availability gates, typing protection and the
two-step Alt transcript.

### Known deviation

`Ctrl+W` closes the current window, while the reference labels it “Close All”. The V29 reason
still stands: closing every project window would discard other unsaved layouts and needs an
explicit owner decision.
