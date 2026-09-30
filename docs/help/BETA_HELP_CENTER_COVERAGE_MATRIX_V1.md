# Beta Help Center — Coverage Matrix v1

This matrix tracks documentation coverage without claiming unsupported runtime behavior.

| Area | Topic family | Current evidence | Initial status |
|---|---|---|---|
| Getting Started | Workspace/navigation | Existing product/client surface | Planned → verify |
| Projects | Project setup | Shared project contracts | Planned → verify |
| WBS/Activities | Activity/WBS grid | p6-activity-wbs-grid | Contract/Implemented |
| WBS/Activities | Field Chooser | p6-field-chooser | Implemented |
| WBS/Activities | Layout | p6-field-layout-foundation | Implemented |
| WBS/Activities | Layout persistence | p6-layout-persistence-adapter | Implemented |
| WBS/Activities | Layout migration | migration boundary | Implemented |
| Scheduling | OOS policies | Shared Core OOS modules | Implemented |
| Scheduling | Relationship matrix | Shared Core + reference tests | Beta verification pending |
| Scheduling | Multiple float paths | Shared scheduler/tests | Implemented |
| Scheduling | Start-to-start lag | Shared scheduler/tests | Implemented |
| Scheduling | Expected finish | Shared scheduler/tests | Implemented |
| Scheduling | Float based on finish date | Shared scheduler/tests | Implemented |
| Scheduling | Resource leveling | Shared Core contract | Integration pending |
| Calendars | Working time | Calendar/WorkingTimeResolver | Implemented |
| Resources | Resource assignment | Resource API/repository contracts | Integration verify |
| Formula | Formula editor | p6-formula-editor | Implemented |
| Formula | Formula/grid binding | p6-formula-grid-binding | Implemented |
| Reports | Print field selection | p6-report-print-field-selection | Implemented |
| Import/Export | Typed exchange | P6/API workstream | Verify before publishing |
| Documents | Document controls | Product backlog/contracts | Planned |
| AI | Smart Guide/AI | AI contracts/backlog | Planned/integration verify |
| Security | Users/permissions/audit | Backend contracts | Verify before publishing |
| Localization | Persian/English | Language contracts | Verify current-head evidence |
| Troubleshooting | Error catalog | Cross-module | Planned |
| Reference | Glossary | Product terminology | Planned |

## Release rule
A row moves to Beta-verified only after a current-main user journey has executable evidence. Historical PR evidence is not sufficient by itself.

## Role guidance
Role-specific documentation must use the current authorization model. Execution responsibilities must not be inferred from documentation ownership. The project supervisor is not an execution worker.
