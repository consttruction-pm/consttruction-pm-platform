# P6 External Project Relationship Boundary

## Implemented boundary

`resolve_project_relationships()` is the Shared-Core boundary for selecting relationships for a project schedule.

- With `IgnoreOtherProjectRelationships=true`, cross-project relationships are excluded.
- With the option false, a relationship crossing the current project boundary is retained when one endpoint belongs to the scheduled project.
- Relationships belonging entirely to unrelated projects are not injected into the current schedule.
- Missing endpoint project identity raises an explicit error; the core never guesses project membership.

## Still intentionally open

`ExternalProjectPriorityLimit` and the multi-project float-reference semantics are not implemented by this change. They require an authoritative scheduling-batch project model and scheduled-finish/priority inputs. Until that model exists, the option remains an explicit capability gap rather than silently changing CPM behavior.

## External resource assignments

`ExternalResourceAssignment` and `select_resource_assignments_for_scheduling()` now provide the Shared-Core boundary for `IncludeExternalResAss`. The boundary consumes an authoritative assignment source and includes assignments from other projects only when the option is enabled. It does not fabricate external demand, capacities, or CPM dates. Backend/API adapters remain responsible for supplying the authoritative assignment records.
