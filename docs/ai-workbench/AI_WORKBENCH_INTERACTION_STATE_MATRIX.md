# AI Workbench — Interaction & State Matrix

Every studio must implement the states below. `SOURCE_NOT_CONNECTED`,
`INSUFFICIENT_DATA` and `CALCULATION_BLOCKED` are first-class states, never
replaced with sample numbers.

| Interaction | Trigger | Required server call | Loading | Empty | Error | Forbidden | Stale revision | Success |
|---|---|---|---|---|---|---|---|---|
| Open studio | Command routes to a studio | context + studio read | skeleton | honest empty | retry + reference | 403 message | revision badge | studio renders pinned scope |
| Switch scenario | Select A/B/C | scenario read | overlay | no scenarios yet | retry | deny | conflict banner | all views update together |
| Run scenario | Run/Recalculate | scenario run | progress + cancel | n/a | failed run, no data | deny | refuse, re-pin | new immutable run ID |
| Compare | Compare | comparison | skeleton | fewer than two runs | failed comparison | deny | stale compare blocked | variance table + navigation |
| Refine | Follow-up command | plan + scenario duplicate/run | progress | missing input question | failed run | deny | stale conflict | new version, delta shown |
| Approve | Approve exact proposal | approval + reauthorize | progress | n/a | partial failure surfaced | deny | stop and re-plan | fresh read-back + audit |
| Reject | Reject with reason | approval | n/a | n/a | retry | deny | n/a | decision recorded |
| Import preview | Select file | staging preview | parse progress | unsupported format | blocking errors | deny | source digest mismatch | inventory + validation |
| Correct mapping | Choose mapping | staging mapping patch | n/a | no ambiguous fields | validation error | deny | n/a | revalidation |
| Apply import | Review and Import | import apply + verify | progress | n/a | rollback/recoverable state | deny | target revision changed | created project verified |
| Filter/sort/group | Toolbar | none (client) | n/a | zero rows message | n/a | n/a | n/a | same scoped dataset |
| Select row | Grid/Gantt | none | n/a | n/a | n/a | n/a | n/a | Gantt, grid, inspector synchronized |
| Keyboard | Arrow/Enter/Space/Shift+F10 | none | n/a | n/a | n/a | n/a | n/a | focus and selection move together |

## State vocabulary

| Code | Meaning |
|---|---|
| `SOURCE_NOT_CONNECTED` | The authoritative source is not mounted; no substitute value exists |
| `INSUFFICIENT_DATA` | The source exists but required inputs are missing |
| `CALCULATION_BLOCKED` | A calculation cannot run under current constraints/validation |
| `STALE_REVISION` | The pinned revision no longer matches the server |
| `PARTIAL_FAILURE` | A multi-step execution did not fully apply; recovery is required |
| `READ_ONLY_ROLE` | The role may inspect but not propose or execute |

## Separation rule

Each response panel must label four lists independently: verified facts,
calculated results, user assumptions/constraints, AI recommendations. The
command layer currently returns empty calculated/recommendation lists until an
authoritative run is attached.
