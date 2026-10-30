# CUBI Workspace Navigation Map

Status: Phase 3 blueprint.
Companion to `workspace-information-architecture.md`. This file defines where every user-facing entry point goes. Implementation status is tracked in `workspace-window-inventory.md`; no entry may be rendered without a target.

## Vocabulary

`window:` opens/activates a window tab. `dialog:` opens a modal. `route:` changes the URL without leaving the workspace. `action:` executes a command. `toggle:` changes client display state. `disabled:` exists but is not available in the current build (with a reason at runtime).

## Menu bar

### Workspace
| Item | Target | Shortcut | Notes |
| --- | --- | --- | --- |
| New Project | `route:/app?new=1` → creation flow step 1 | Ctrl+N | Requires planner/admin |
| Open Project | `dialog:open-project` | Ctrl+O | Lists projects for the session |
| Close Project | `action:close-project` | — | Confirmation when unsaved |
| Save | `action:commit-layout` | Ctrl+S | Persists layout and pending cell edits |
| Refresh Data | `action:refresh-workspace` | F5 | Re-reads workspace v2 snapshot |
| Import | `dialog:import` | — | Wired to existing interchange panel |
| Export | `dialog:export` | — | Wired to existing interchange panel |
| Print Preview | `dialog:print-preview` | — | Implement after print profile exists |
| Print | `dialog:print` | Ctrl+P | Disabled until print is wired |
| Recent Projects | `submenu:recent` | — | Max 5, from local preferences |
| Sign Out | `route:/preview/logout` / `/logout` | — | Server endpoint |

### Edit
| Item | Target | Shortcut | Notes |
| --- | --- | --- | --- |
| Undo / Redo | `action:layout-undo` / `redo` | Ctrl+Z / Ctrl+Y | Layout-level undo exists today |
| Cut / Copy / Paste | `action:clipboard-*` | Ctrl+X/C/V | Table selection scope |
| Add Activity / WBS / Relationship | `dialog:new-*` | Insert | Context by active window |
| Delete | `action:delete-selection` | Delete | Confirmation with count |
| Dissolve Activity | `action:dissolve-activity` | — | Activities with pred+succ |
| Assign → Resources / Roles / Codes / Predecessors / Successors | `dialog:assign-*` | — | Planner+ |
| Link / Unlink Activities | `action:link` / `unlink` | Ctrl+L | Multi-row selection |
| Renumber Activity IDs | `dialog:renumber` | — | Preview before apply |
| Fill Down | `action:fill-down` | Ctrl+D | Multi-cell selection |
| Select All | `action:select-all` | Ctrl+A | Active table |
| Find / Find Next | `dialog:find` / `action:find-next` | Ctrl+F / F3 | Table and Gantt scope |
| User Preferences | `dialog:user-preferences` | — | Locale, calendar, digits, startup tab |

### View
| Item | Target | Shortcut | Notes |
| --- | --- | --- | --- |
| Layout → New / Open / Save / Save As | `dialog:layout-*` | — | User/project scope |
| Show on Top → Table / Gantt / Network | `toggle:top-layout` | — | Activities window |
| Show on Bottom → Details / Profiles / Trace Logic / None | `toggle:bottom-layout` | — | Activities window |
| Bottom Layout Options | `dialog:activity-details-tabs` | — | Choose/order detail tabs |
| Columns | `dialog:columns` | — | Layout toolbar |
| Filter By | `dialog:filters` | — | Predefined + custom |
| Group and Sort By | `dialog:group-sort` | — | Default WBS |
| Timescale | `dialog:timescale` | — | Gantt |
| Bars / Bar Chart Options | `dialog:bars` / `dialog:barchart-options` | — | Gantt |
| Progress Line | `toggle:progress-line` | — | Gantt |
| Line Numbers | `toggle:line-numbers` | — | Table |
| Table Font and Row | `dialog:table-font-row` | — | Row height/font scale |
| Zoom In / Out / Best Fit | `action:zoom-*` | Ctrl+ / Ctrl- / Ctrl+0 | Gantt |
| Expand All / Collapse All | `action:expand-all` / `collapse-all` | — | Grouped table |
| Toolbars | `submenu:toolbars` | — | Show/hide each toolbar |
| Tab Groups | `action:tab-group-*` | — | Horizontal/vertical/merge |

### Project
| Item | Target | Notes |
| --- | --- | --- |
| Activities | `window:activities` | Primary workspace |
| Additional Activities View | `window:activities-2` | Compare project/baseline |
| WBS | `window:wbs` | Hierarchy editing |
| Resource Assignments | `window:resource-assignments` | Grouped by resource |
| Baselines → Assign / Maintain | `dialog:assign-baselines` / `dialog:maintain-baselines` | Disabled until baseline UI lands |
| Expenses | `window:expenses` | Project expense register |
| Documents | `window:documents` | WPs & Docs equivalent |
| Thresholds | `window:thresholds` | Disabled until threshold API exists |
| Issues | `window:issues` | Site/field issues are separate; project issue register to be unified |
| Risks | `window:risks` | Disabled until risk API exists |
| Set Default Project | `dialog:default-project` | Per-user preference |

### Organization
| Item | Target | Notes |
| --- | --- | --- |
| Projects | `window:projects` | Business-domain tree + project list |
| Business Domains | `dialog:business-domains` | EPS-level classification |
| Portfolios | `dialog:portfolios` | Optional grouping |
| Resources | `window:resources` | Resource hierarchy |
| Roles | `dialog:roles` | Dictionary |
| Responsibility Structure | `dialog:responsibility-structure` | OBS equivalent |
| Calendars | `window:calendars` | Global/project/resource calendars |
| Codes → Activity / Resource / Role / Project | `dialog:codes-*` | Dictionaries |
| User Defined Fields | `dialog:udfs` | Field definitions |
| Resource Shifts | `dialog:resource-shifts` | Disabled until shift model exists |
| Cost Accounts | `dialog:cost-accounts` | Backend exists; UI pending |
| Funding Sources | `dialog:funding-sources` | Disabled until funding API exists |
| Resource Curves | `dialog:resource-curves` | Disabled until curve UI exists |
| Stored Images | `dialog:images` | Low priority |
| External Applications | `dialog:external-apps` | Disabled |

### Tools
| Item | Target | Shortcut | Notes |
| --- | --- | --- | --- |
| Schedule | `dialog:schedule` | F9 | Reuses existing schedule options + run |
| Level Resources | `dialog:level-resources` | Shift+F9 | Disabled until leveling UI is wired |
| Apply Actuals | `dialog:apply-actuals` | — | Backend exists; UI pending |
| Update Progress | `dialog:update-progress` | — | Disabled until progress dialog exists |
| Recalculate Assignment Costs | `action:recalculate-costs` | — | Backend dependent |
| Summarize | `action:summarize` | — | After schedule |
| Store Period Performance | `dialog:period-performance` | — | Backend exists |
| Global Change | `dialog:global-change` | — | Disabled until bulk-change API |
| Monitor Thresholds | `action:monitor-thresholds` | — | Disabled |
| Issue Navigator | `dialog:issue-navigator` | — | Disabled |
| Reports → Reports / Groups / Batches | `window:reports` / `dialog:report-groups` / `dialog:batch-reports` | — | Reports window is currently a preview |
| Publish | `dialog:publish` | — | Disabled in local preview |

### Administration
| Item | Target | Notes |
| --- | --- | --- |
| Users | `dialog:users` | Admin only |
| Security Profiles | `dialog:security-profiles` | Admin only |
| Preferences | `dialog:admin-preferences` | Admin only |
| Categories | `dialog:admin-categories` | Admin only |
| Currencies | `dialog:currencies` | Admin only |
| Financial Periods | `dialog:financial-periods` | Admin only |

### Help
| Item | Target | Notes |
| --- | --- | --- |
| Workspace Guide | `dialog:help` | Context-aware in-app guide |
| Keyboard Shortcuts | `dialog:shortcuts` | Generated from command registry |
| What's New | `dialog:whats-new` | Release notes |
| About CUBI | `dialog:about` | Version, build SHA |

## Navigation tree (left)

```
Project
├── Activities            → window:activities
├── WBS                   → window:wbs
├── Resource Assignments  → window:resource-assignments
├── Documents             → window:documents
├── Expenses              → window:expenses
├── Issues                → window:issues
└── Risks                 → window:risks (disabled until API)
Organization
├── Projects              → window:projects
├── Resources             → window:resources
├── Calendars             → window:calendars
└── Reports               → window:reports
```

The tree is collapsible; the active window is highlighted. The tree never replaces the menu bar; both exist.

## Window tab behaviour

| Action | Result |
| --- | --- |
| Open a closed window | New tab at the end, activated |
| Open an open window | Activate its tab, no duplicate |
| Close tab | `X`, middle-click or Ctrl+W; confirmation if dirty |
| Reorder | Drag tab |
| Cycle | Ctrl+Tab / Ctrl+Shift+Tab |
| Close all | Workspace > Close All; closes project windows together |
| Project switch | Reload project windows; keep enterprise windows |
| Deep link | `?project={id}&window={key}` opens the project and window |

## Keyboard map (minimum)

| Key | Action |
| --- | --- |
| Alt+W / E / V / P / O / T / A / H | Focus menu: Workspace, Edit, View, Project, Organization, Tools, Administration, Help |
| F5 | Refresh |
| F9 | Schedule |
| Shift+F9 | Level resources |
| Ctrl+F / F3 | Find / Find next |
| Ctrl+S | Save layout |
| Ctrl+P | Print |
| Ctrl+Z / Ctrl+Y | Undo/redo layout changes |
| Ctrl+Tab | Next window |
| Delete | Delete selection |
| Insert | Add in active window |

## First-run default

1. Open the last project (or the project picker if none).
2. Open **Activities** with WBS grouping and WBS sort.
3. Top layout: table + Gantt. Bottom layout: Activity Details (General tab).
4. Status bar shows project, data date, baseline (or None), layout, user, sync state.
