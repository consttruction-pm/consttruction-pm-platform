# P6 Professional Desktop v26 Menu Reference

Status: Phase 1 inventory. Source: official Oracle P6 Professional v26 client help (see `oracle-p6-reference-index.md`).
Purpose: preserve the complete desktop menu surface so CUBI can map or explicitly retire each command. This file uses the reference product's names for traceability; user-facing CUBI labels are defined in `../architecture/p6-to-cubi-mapping-matrix.md`.

Legend for target: **W** = main window, **D** = dialog, **T** = toggle/command without dialog, **N/A** = not applicable to CUBI.

## File (Alt+F)

| Command | Shortcut | Enabled when | Target | Effect |
| --- | --- | --- | --- | --- |
| New | — | All | Wizard or Projects W | Creates a project (wizard or `NEWPROJ-n`) |
| Open | — | All | Open Project D | Select and open projects |
| Close All | — | All | — | Closes all projects and their project windows |
| Page Setup | — | All | Page Setup D | Page size, orientation, scaling, margins, header/footer |
| Print Setup | — | All | Print Setup D | Printer selection and properties |
| Print Preview | — | All | Print Preview W | Preview, publish to HTML, print |
| Print | — | All | Print D | Print active window |
| Import | — | All | Import wizard | Import projects/resources/roles (Oracle, MS Project, Excel) |
| Export | — | All | Export wizard | Export projects/resources/roles (Oracle, MS Project, Excel, UN/CEFACT, IPMDAR, CPP) |
| Send Project | — | Project open | Email client | XER export attached to email |
| Exchange Data > | — | All | Integration-specific | Exchange with integrated applications |
| Check In | — | All | Check In wizard | Check in checked-out projects |
| Check Out | — | All | Check Out wizard | Check out open projects |
| Select Project Portfolio | — | All | Select a Portfolio D | Open portfolio, close open projects |
| Commit Changes | — | All | — | Commit to database |
| Refresh Data | — | All | — | Reload current data |
| Recent Projects > | — | All | — | Three most recent projects |
| Exit | — | All | — | Close module |

## Edit (Alt+E)

| Command | Shortcut | Enabled when | Target | Effect |
| --- | --- | --- | --- | --- |
| Undo | Alt+E, U | Activities, Resources, Resource Assignments | — | Revert last change |
| Cut | Alt+E, X | All except Tracking/Resource Assignments | — | Cut selection |
| Copy | Alt+E, C | All | — | Copy selection |
| Paste | Alt+E, V | After copy/cut | — | Paste |
| Add | Alt+E, A | All | — | Add item in active window |
| Delete | Alt+E, D | All except Tracking | — | Delete selection |
| Dissolve | Alt+E, O | Activities with predecessor and successor | — | Delete activity, join neighbours FS |
| Assign > Resources | Alt+E, R | Activities | Assign Resources D | Assign/remove/replace resources |
| Assign > Resources by Role | Alt+E, L | Activities | Assign Resources by Role D | Assign by role |
| Assign > Roles | Alt+E, G | Activities | Assign Roles D | Assign/remove/replace roles |
| Assign > Activity Codes | Alt+E, Y | Activities | Assign Activity Codes D | Assign code values |
| Assign > Predecessors | Alt+E, P | Activities | Assign Predecessors D | Add/remove predecessors |
| Assign > Successors | Alt+E, S | Activities | Assign Successors D | Add/remove successors |
| Link Activities | Alt+E, K | Multiple activities selected | — | Create FS links in listed order |
| Unlink Activities | Alt+E, U | Activities | — | Remove links between selected |
| Renumber Activity IDs | Alt+E, I | Activities | Renumber Activity IDs D | Renumber selected IDs |
| Fill Down | Alt+E, F | Table views | — | Copy cell value down selected rows |
| Select All | Alt+E, A | All | — | Select all rows/items |
| Find | Alt+E, F | All | Find D | Search active window |
| Find Next | Alt+E, N | All | — | Next match |
| Replace | Alt+E, R | All | — | Replace text |
| Spell Check | Alt+E, S | All | — | Check spelling |
| User Preferences | Alt+E, P | All | User Preferences D | Time/date/currency, email, startup, password |

## View (Alt+V)

| Command | Enabled when | Target | Effect |
| --- | --- | --- | --- |
| Layout > (New/Open/Save/Save As) | Activities, Projects, Resource Assignments, WBS, Tracking | Layout D | Manage layouts |
| Show on Top > | Activities, Projects, Resources, Resource Assignments, WBS | — | Choose top layout (table, Gantt, network, chart) |
| Show on Bottom > | All | — | Choose bottom layout (details, profiles, spreadsheets, trace logic, none) |
| Bottom Layout Options | Activities | Customize Activity Details D | Show/order Activity Details tabs |
| Bars | Activities/Projects/Tracking/WBS | Bars D | Gantt bar styles and labels |
| Barchart Options | Activities | Bar Chart Options D | Gantt display options |
| Columns | All except Reports | Columns D | Add/remove/reorder/width/align columns |
| Timescale | Activities/Projects/Resource Assignments/Tracking/WBS | Timescale D | Timescale format and range |
| Filter By > | All except Project Expenses/WBS | Filters D | Predefined/custom filter |
| Group and Sort By > | All | Group and Sort D | Grouping bands and sort levels |
| Progress Line | Activities | T | Show/hide progress line |
| Progress Spotlight | Activities | T | Highlight period since previous data date |
| Attachments | Activities with Gantt | T/D | Curtain and text attachments |
| Line Numbers | Activities | T | Row numbers |
| Activity Critical Path | Activities table/Gantt | T | Filter to critical path of selected activity |
| Check Schedule | Activities table/Gantt | T | Filter to activities failing schedule checks |
| Table Font and Row | All | Table, Font and Row D | Font, colour, row height |
| Activity Network > | Activities (network top layout) | D/T | Network options/layout |
| Arrange Children | Projects/Resources/WBS chart | T | Horizontal/vertical arrangement |
| Align Children | Projects/Resources/WBS chart | T | Left/right/centre alignment |
| Chart Box Template | Projects/Resources/WBS chart | D/T | Box template |
| Chart Font and Colors | Projects/Resources/WBS chart | D | Chart fonts/colours |
| Launch | WPs & Docs with file location | — | Open document |
| Hint Help | All | T | Toggle hint help |
| Zoom > | Timescaled windows | T | In/out/best fit |
| Expand | All | T | Expand grouped/hierarchical rows |
| Collapse All | All | T | Collapse all |
| Collapse To | Grouped windows | Collapse To D | Collapse to band |
| Toolbars > | All | T | Show/hide toolbars |
| Reset All Toolbars | All | T | Factory reset |
| Lock All Toolbars | All | T | Lock positions |
| Tab Groups > | All | T | New horizontal/vertical group, merge |

## Project (Alt+P)

| Command | Target | Effect |
| --- | --- | --- |
| Activities | Activities W | Open activities |
| Additional Activities View | Activities W (second) | Open a second independently configured activities view |
| Resource Assignments | Resource Assignments W | Assignments grouped by resource across open projects |
| WBS | WBS W | Create/edit project WBS |
| Assign Baselines | Assign Baselines D | Assign primary/secondary/tertiary baselines |
| Maintain Baselines | Maintain Baselines D | Create/delete/copy/restore baselines |
| Expenses | Project Expenses W | Expense items per activity |
| Work Products and Documents | WPs & Docs W | Work products and documents |
| Thresholds | Project Thresholds W | WBS/activity thresholds |
| Issues | Project Issues W | Project issues |
| Risks | Risks view | Professional-database only |
| Set Default Project | Set Default Project D | Default open/scheduling/leveling project |

## Enterprise (Alt+N)

| Command | Target | Notes |
| --- | --- | --- |
| Projects | Projects W | EPS and project management |
| Enterprise Project Structure | EPS D | Professional database only |
| Tracking | Tracking W | Progress layouts |
| Project Portfolios | Project Portfolios D | Portfolio dictionary |
| Resources | Resources W | Resource hierarchy and details |
| Roles | Roles D | Role dictionary, rates, limits |
| OBS | OBS D | Professional database only |
| Resource Codes | Resource Codes D | Dictionary |
| Role Codes | Role Codes D | Dictionary |
| Project Codes | Project Codes D | Professional database only |
| Activity Codes | Activity Codes D | Global/project/EPS codes |
| User Defined Fields | UDF D | Custom fields |
| Calendars | Calendars D | Global/project/resource calendars |
| Resource Shifts | Resource Shifts D | Shift calendars |
| Activity Step Templates | Activity Step Templates D | Professional database only |
| Cost Accounts | Cost Accounts D | Professional database only |
| Funding Sources | Funding Sources D | Professional database only |
| Stored Images | Images Manager D | Report images |
| Resource Curves | Resource Curves D | Allocation curves |
| External Applications | External Applications D | Integration links |

## Tools (Alt+T)

| Command | Shortcut | Target | Effect |
| --- | --- | --- | --- |
| Schedule | F9 | Schedule D | Schedule open projects |
| Level Resources | Shift+F9 | Level Resources D | Level resources |
| Apply Actuals | — | Apply Actuals D | Apply actuals to data date |
| Update Progress | — | Update Progress D | Estimate progress for spotlighted/selected activities |
| Recalculate Assignment Costs | — | Recalculate Assignment Costs D | Recompute costs |
| Summarize > | — | T | Open/all projects |
| Job Services | — | Job Services D | Professional database only |
| Store Period Performance | — | Store Period Performance D | Store period actuals |
| Job Status | — | Job Status D | EPPM only |
| Disable Auto-Reorganization | Shift+F2 | T | Toggle auto-reorder |
| Global Change | — | Global Change D | Bulk change |
| Monitor Thresholds | — | Monitor Thresholds D | Evaluate thresholds |
| Issue Navigator | — | Issue Navigator D | Track issues |
| Visualizer | — | Visualizer app | Activities only |
| Approvals > Timesheets | — | Timesheets W | Timesheet approval |
| Reports > Reports | — | Reports W | Reports |
| Reports > Report Groups | — | Report Groups D | Groups |
| Reports > Batch Reports | — | Batch Reports D | Batches |
| Reports > Report Preferences | — | Report Preferences D | Defaults (Professional database only) |
| Report Wizard | — | Report Wizard | Build/modify wizard report |
| Publish > Project Web Site | — | Publish D | HTML site |
| Publish > Activity Layouts | — | Select layouts D | Publish activity layouts |
| Publish > Tracking Layouts | — | Select layouts D | Publish tracking layouts |
| Schedule Comparison | — | Visualizer | Compare revisions/baseline |

## Admin (Alt+A, Professional only)

| Command | Target | Effect |
| --- | --- | --- |
| Users | Users D | Add/remove users, profiles |
| Security Profiles | Security Profiles D | Create/edit/delete profiles |
| Admin Preferences | Admin Preferences D | Global defaults, help location |
| Admin Categories | Admin Categories D | Global categories/values |
| Currencies | Currencies D | Currency dictionary |
| Financial Period Calendars | Financial Period Calendars D | Period calendars for period performance |

## Help (Alt+H)

| Command | Target | Effect |
| --- | --- | --- |
| Local Help | Local help | Context-sensitive local help |
| Online Help | Configured URL | Context-sensitive online help |
| About | About D | Product/version information |
| What's New | Web page | Cumulative features overview |
| Share Your Feedback | Survey | Visible only while the survey is open |

## Cross-cutting rules observed

1. Commands are enabled or disabled by the **active window and its layout**, not only by permissions. CUBI must reproduce this with an explicit command-availability model.
2. Layout commands (Columns, Filter, Group and Sort, Timescale, Bars) act on the active layout and can be saved with it.
3. Window-opening commands are idempotent: opening an already open window activates its tab instead of duplicating it, except Additional Activities View.
4. Project windows close with the last open project; enterprise windows stay open.
5. Keyboard access: every top-level menu has an Alt mnemonic; common commands add second-level mnemonics and function keys (F5, F9, Shift+F9, F3, Ctrl+F, Ctrl+P, Ctrl+F1).
