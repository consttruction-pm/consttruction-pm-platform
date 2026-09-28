# V1 Web Menu / Submenu Matrix — 2026-09-28

## Rule
This is the product navigation taxonomy for V1, derived from the project's implemented domains and the P6 Release 26 capability inventory. It is **not** presented as a verbatim copy of Oracle P6 desktop menu labels. Every entry must map to a real screen, route or functional panel with an explicit status.

## Status
- Implemented: usable V1 behavior exists.
- Partial: real route/function exists but material capability is incomplete.
- Preview: navigation and explanatory surface exist; business operation is intentionally limited.
- Planned: not yet exposed.

| Main menu | V1 submenu / screen | Owner | Target status | Core/API dependency |
|---|---|---|---|---|
| Project | Open Project | Javad + Hasan | Implemented/Partial | Project context |
| Project | Project Details | Javad + Hasan | Partial | Project API |
| Project | WBS | Javad + Hasan | Partial | WBS persistence |
| Project | EPS / Portfolio | Javad + Hasan | Preview | Portfolio API |
| Project | Codes / UDF | Javad + Hasan | Partial | Field Registry/UDF |
| Project | Baselines | Javad + Hasan + Jalal | Partial | Baseline + schedule core |
| Schedule | Activities | Javad | Partial | Activity API + Field Registry |
| Schedule | Relationships | Javad + Hasan | Partial | Dependency Graph + Core |
| Schedule | Calendars | Javad + Hasan + Jalal | Partial | Shared Calendar Core |
| Schedule | Schedule Options | Javad + Hasan + Jalal | Partial | Calculation options registry |
| Schedule | Schedule / Recalculate | Javad + Jalal | Partial | Scheduling Core |
| Schedule | Float / Critical Path | Javad | Partial | Scheduling Core |
| Schedule | Gantt | Javad | Partial | Schedule result contract |
| Progress | Update Progress | Javad + Hasan | Partial | Progress Core/API |
| Progress | Activity Steps | Javad + Hasan | Preview/Partial | ActivityStep contract |
| Progress | Earned Value | Javad + Jalal | Partial | EVM Core |
| Progress | Earned Schedule | Javad + Jalal | Partial | Earned Schedule Core |
| Progress | Schedule Performance | Javad + Jalal | Partial | SPI/SV Core |
| Resources | Resource Dictionary | Javad + Hasan | Partial | Resource API |
| Resources | Resource Assignments | Javad + Hasan + Jalal | Partial | Assignment + Schedule Core |
| Resources | Roles / Rates | Javad + Hasan | Partial | Resource API |
| Resources | Resource Calendars | Javad + Hasan + Jalal | Partial | Calendar Core |
| Cost | Cost Accounts | Javad + Hasan | Preview | Cost API |
| Cost | Planned / Actual / Remaining | Javad + Hasan + Jalal | Partial | Cost Core |
| Cost | Forecast / Variance | Javad + Hasan + Jalal | Partial | Cost/EVM Core |
| Documents | Document Register | Javad + Hasan | Partial | Document API |
| Documents | Drawings / Contracts | Javad + Hasan | Partial | Document service |
| Documents | RFI / Submittal | Javad + Hasan | Preview/Partial | Document/Control API |
| Documents | Claims / Evidence | Javad + Hasan + Jalal | Partial | Change/Claim + evidence |
| Reports | Schedule Reports | Javad + Hasan | Partial | Typed report dataset |
| Reports | Progress / EVM Reports | Javad + Jalal + Hasan | Partial | Core/report API |
| Reports | Cost Reports | Javad + Hasan | Partial | Typed cost dataset |
| Reports | Custom Report / Columns | Javad + Hasan + Jalal | Partial | Field Registry + Formula Core |
| Control | Project Control Room | Javad + Jalal + Hasan | Partial | Cross-domain read model |
| Control | Change / Claims | Javad + Hasan | Partial | Change/Claim Core |
| Control | Field Operations | Javad + Hasan | Preview/Partial | Field Operations API |
| Control | Quality / Safety | Javad + Hasan | Preview | Future V1 depth gate |
| Settings | Language | Javad | Implemented/Partial | Language registry |
| Settings | Calendar Display | Javad | Implemented/Partial | Jalali/Gregorian mode |
| Settings | Schedule Options | Javad + Hasan + Jalal | Partial | Shared calculation options |
| Settings | Units / Currency | Javad + Hasan | Partial | Typed units |
| Settings | Users / Roles / Permissions | Javad + Hasan | Partial | Authorization API |
| Settings | Import / Export | Javad + Hasan | Partial | Interchange adapters |
| Settings | Audit / Revision | Javad + Hasan | Partial | Revision/audit contracts |

## Global UI commands
These are shared interaction capabilities and should not be reimplemented per module:
- Add / Edit / Delete
- Undo/Redo where supported by the authoritative mutation model
- Save / Refresh / Recalculate
- Filter / Sort / Group
- Columns / Field Chooser
- Freeze / Pin / Resize / Reorder
- Formula / Calculated Column
- Search
- Export
- Print / Print Layout
- View/Layout save and restore
- Permissions-aware action availability

## V1 acceptance rule
A menu item is complete only when the route/panel loads, consumes the authoritative API/domain contract, respects locale/permissions, and has at least one meaningful success and failure test. Preview items are visible but cannot be represented as fully implemented.
