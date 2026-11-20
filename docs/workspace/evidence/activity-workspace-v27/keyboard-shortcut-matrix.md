# V27 Keyboard Shortcut Matrix — Activities Workspace

- Tested head: `b71cd61f46ebe358d1b15eee21068977b03493cf`
- Registry: `getDesktopShortcuts()` — **24 catalog shortcuts + Alt+1…9 window bindings**
  (2 windows open in the reference run → 26 total).
- Matching rules: chords are matched against `key`/`code`, with Ctrl-or-Meta,
  Alt and Shift modifiers; typing inside an input/textarea/select never triggers
  an application chord. Shortcuts with `unavailable` or a failed capability
  precondition are consumed but explain why instead of acting.
- F1 is reserved for the shortcut dialog; Shift+F12 for About.

| Action | Keys | State in reference run | Reason when unavailable |
|---|---|---|---|
| New project | Ctrl+N | executable | — |
| Open project | Ctrl+O | executable | — |
| Close window | Ctrl+W | executable (2 windows) | Needs more than one window if single |
| Print | Ctrl+P | executable | — |
| Save layout | Ctrl+S | executable (layout loaded) | Needs a loaded layout |
| Undo layout change | Ctrl+Z | executable (history) | No undoable step otherwise |
| Redo layout change | Ctrl+Y | executable (history) | No redoable step otherwise |
| Cut | Ctrl+X | **blocked** | Activity clipboard contract absent |
| Copy | Ctrl+C | **blocked** | Activity clipboard contract absent |
| Paste | Ctrl+V | **blocked** | Activity clipboard contract absent |
| Delete activity | Del | **blocked** | Activity delete contract absent |
| Insert activity | Ins | executable (WBS present) | Needs a WBS |
| Find activities | Ctrl+F | executable | — |
| Select all visible activities | Ctrl+A | executable (rows loaded) | Needs activities |
| Find next | F3 | **blocked** | Needs a result set from the current filter |
| Refresh project data | F5 | executable | — |
| Schedule activities | F9 | executable | — |
| Schedule options | Shift+F9 | executable | — |
| Level resources | F7 | **blocked** | Leveling contract absent in this workspace |
| Commit changes | F10 | **blocked** | No staged edit to commit |
| Expand all WBS bands | Ctrl+Num + | capability-blocked in reference run | Group by WBS to enable |
| Collapse all WBS bands | Ctrl+Num - | capability-blocked in reference run | Group by WBS to enable |
| Keyboard shortcuts | F1 | executable | — |
| About CUBI Workspace | Shift+F12 | executable | — |
| Open window 1…9 | Alt+1…Alt+9 | executable per open tab | Only for open windows |

## Non-shortcut keyboard behavior (browser-verified)

| Surface | Behavior | Evidence |
|---|---|---|
| Activity Grid | Arrows, Home/End, PageUp/PageDown, Enter/Space, Shift+F10 / ContextMenu; roving tabindex | `activity-grid-keyboard-v26` |
| Details tablist | ArrowLeft/Right, Home/End, wrap-around, one tab in tab order; RTL follows direction | `activity-details-v26` keyboard EN + FA |
| Menu bar | Access keys, arrow navigation, Escape, type-ahead | `workspace-shell-v26`, responsive 05 |
| Grid Ctrl+A from body | Selects all visible rows without stealing text-field chords | responsive 06 |
| Dialog focus | Initial focus, Tab containment, Enter/Escape, validation focus | dialog suites |
| Full screen | Escape exits | responsive 07 (headless limitation recorded) |

## Known deviations

- Seven catalog shortcuts are intentionally blocked because their backend
  contracts do not exist (clipboard ×3, delete, find-next, leveling, commit).
  They are not silently ignored and are not faked. See `deviation-register.md`.
- `Ctrl+Num +/−` are conditionally executable; the reference run did not group by
  WBS, so they report the grouping reason. Unit tests cover the grouped state.
