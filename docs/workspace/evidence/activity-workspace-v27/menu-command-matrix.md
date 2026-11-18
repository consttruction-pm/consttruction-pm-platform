# V27 Menu and Command Matrix — Activities Workspace

- Tested head: `b71cd61f46ebe358d1b15eee21068977b03493cf`
- Source of truth: `getDesktopMenus()` in `apps/web/src/workspace-desktop-shell.ts`
- Counts: **8 menus, 118 commands** (separators excluded), capability set "all available"
  except where the contract or the current project state forbids a command.
- Every command is either a real action, a window selector, or is disabled with a
  localized reason. Nothing is decorative.

State legend:
- `available` — executes in the reference capability set.
- `unavailable (reason shown)` — disabled with a localized explanation. Causes:
  no clipboard contract (Cut/Copy/Paste), activity deletion contract absent
  (Delete), fill/dissolve not contracted, no grouped WBS in the reference state
  (Expand/Collapse/Collapse To), no leveling/ baseline/ progress-view contract,
  admin role-gated services, or one-layout server limit.
- Conditional commands (Expand/Collapse) become available when the layout is
  grouped by WBS; the unit tests cover both states.

### File (f) — 10 commands
| Command | Shortcut | State |
|---|---|---|
| New project… | Ctrl+N | available |
| Open project… | Ctrl+O | available |
| Open Layout… | — | available |
| Save Layout | Ctrl+S | available |
| Save Layout As… | — | available |
| Project properties… | — | available |
| Import / Export… | — | available |
| Print… | Ctrl+P | available |
| Refresh data | F5 | available |
| Close window | Ctrl+W | available |

### Edit (e) — 14 commands
| Command | Shortcut | State |
|---|---|---|
| Undo layout change | Ctrl+Z | available |
| Redo layout change | Ctrl+Y | available |
| Cut | Ctrl+X | unavailable (reason shown) |
| Copy | Ctrl+C | unavailable (reason shown) |
| Paste | Ctrl+V | unavailable (reason shown) |
| Delete | Del | unavailable (reason shown) |
| Find activities… | Ctrl+F | available |
| Group by WBS | — | available |
| Reverse sort direction | — | available |
| Select All Activities | Ctrl+A | available |
| Link Activities… | — | available |
| Unlink Activities… | — | available |
| Fill Down | Ctrl+E | unavailable (reason shown) |
| Dissolve | — | unavailable (reason shown) |

### View (v) — 46 commands
| Command | Shortcut | State |
|---|---|---|
| Columns… | — | available |
| Filters… | — | available |
| Group and Sort… | — | available |
| Timescale… | — | available |
| Bar Styles… | — | available |
| Table Font and Row… | — | available |
| User Preferences… | — | available |
| Line Numbers | — | available |
| Expand All | Ctrl+Num + | unavailable (reason shown; conditional on WBS grouping) |
| Collapse All | Ctrl+Num - | unavailable (reason shown; conditional on WBS grouping) |
| Collapse To… | — | unavailable (reason shown; conditional on WBS grouping) |
| Zoom in | — | available |
| Zoom out | — | available |
| Fit to window | — | available |
| Show project WBS | — | available |
| Show Gantt Chart | — | available |
| Hide Details | — | available |
| Show on Top: Activity Table | — | available |
| Show on Top: Table + Gantt Chart | — | available |
| Show on Top: Activity Network | — | available |
| Show on Bottom: Activity Details | — | available |
| Show on Bottom: Trace Logic | — | available |
| Show on Bottom: Activity Usage Spreadsheet | — | available |
| Show on Bottom: Activity Usage Profile | — | available |
| Show on Bottom: None | — | available |
| Switch calendar display | — | available |
| Toolbar: Workspace | — | available |
| Toolbar: Edit | — | available |
| Toolbar: Layout | — | available |
| Toolbar: View | — | available |
| Toolbar: Project | — | available |
| Toolbar: Activities | — | available |
| Toolbar: WBS | — | available |
| Toolbar: Gantt / Charts | — | available |
| Toolbar: Resources | — | available |
| Toolbar: Reports | — | available |
| Toolbar: Tools | — | available |
| CUBI Classic — Version 26 Reference | — | available |
| CUBI Modern 3D | — | available |
| CUBI Graphite | — | available |
| CUBI Arctic | — | available |
| CUBI Copper | — | available |
| CUBI Midnight | — | available |
| Projects | Alt+1 | available |
| Activities | Alt+2 | available |
| Close current window | — | available |

### Project (p) — 17 commands
| Command | Shortcut | State |
|---|---|---|
| Project properties… | — | available |
| Add WBS element | — | available |
| Add activity | Insert | available |
| Edit selected activity | Enter | available |
| Relationships | — | available |
| Additional Activities View | — | unavailable (reason shown) |
| Schedule activities | F9 | available |
| Schedule options | — | available |
| Formula editor | — | available |
| Scheduling reference | — | available |
| Assign resources… | — | available |
| Assign predecessors… | — | available |
| Assign successors… | — | available |
| Level resources… | — | unavailable (reason shown) |
| Baselines… | — | unavailable (reason shown) |
| Compare baselines… | — | unavailable (reason shown) |
| Update progress… | — | unavailable (reason shown) |

### Enterprise (n) — 7 commands
| Command | Shortcut | State |
|---|---|---|
| Projects | — | available |
| Resources | — | available |
| Resource assignments | — | available |
| Roles… | — | available |
| Calendars… | — | available |
| User defined fields… | — | unavailable (reason shown) |
| Forms & Workflows… | — | available |

### Tools (t) — 10 commands
| Command | Shortcut | State |
|---|---|---|
| Forms & Workflows… | — | available |
| Search activities | Ctrl+F | available |
| User Preferences… | — | available |
| Reports | — | available |
| Project CSV Import / Export… | — | available |
| Project Backup / Recovery… | — | available |
| Print preview | — | available |
| Report wizard… | — | unavailable (reason shown) |
| Switch language | — | available |
| Keyboard shortcuts | F1 | available |

### Admin (a) — 12 commands
| Command | Shortcut | State |
|---|---|---|
| Settings | — | available |
| User Preferences… | — | available |
| Language | — | available |
| Calendar display | — | available |
| Users… | — | unavailable (reason shown) |
| Security profiles… | — | unavailable (reason shown) |
| Permission matrix… | — | available |
| Categories… | — | available |
| Currencies… | — | unavailable (reason shown) |
| Financial period calendars… | — | available |
| Audit history… | — | unavailable (reason shown) |
| Recovery… | — | available |

### Help (h) — 2 commands
| Command | Shortcut | State |
|---|---|---|
| Keyboard shortcuts | F1 | available |
| About CUBI Workspace | — | available |

## Verification

| Check | Evidence |
|---|---|
| Menu labels in EN and FA, access keys, single menu bar | `workspace-desktop-shell.test.ts` |
| Shortcut uniqueness and executability | same |
| Menus stay inside 1280/1366/1920 and RTL viewports | `workspace-responsive-v26` scenario 05 |
| Command execution routes to a handler | `toolbars-v26` 6/6, `workspace-shell-v26` 7/7 |
| Context menus reuse the same registry | `context-menus-v26`, `register-context-menus-v26` |

## Environmental note

The official Help menu pages (`49093.htm`–`49100.htm`) are held in the crosswalk
but could not be re-fetched on 2026-11-18 (HTTP 403). Command coverage is verified
against the recorded crosswalk and the running registry, not against a fresh Help read.
