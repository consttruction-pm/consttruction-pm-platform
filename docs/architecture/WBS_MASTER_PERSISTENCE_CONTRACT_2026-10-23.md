# Canonical WBS Master Persistence Contract — 2026-10-23

## Status and scope

This contract defines CUBI's canonical Work Breakdown Structure (WBS) identity and the current WBS/Activity persistence and authenticated API boundary. The repository now stores tenant/project-scoped WBS nodes, persists an optional backwards-compatible Activity-to-WBS reference, enforces a valid same-scope WBS at authenticated Activity create/update, and exposes authenticated WBS CRUD-read routes through explicit production composition. This does **not** claim the persistence-backed workspace read model, versioned workspace node collection, Web tree renderer, or authenticated `/app/` runtime journey is complete. Issues #1384, #1359, and #1515 remain open until those gates are demonstrated.

## Source-derived model rules

Oracle Primavera P6 EPPM Release 26 describes WBS as a hierarchy: a WBS element may contain more WBS elements, activities, or both. The REST WBS object exposes project identity, parent identity, code, name, and sequence ordering. Oracle documents Code as the node's code concatenated with its parents' codes, and documents SequenceNumber for sorting. It separately describes IsWorkPackage as an Oracle Prime work-package flag; this is not a license to equate a generic CUBI WorkPackage with a WBS node.

Official references:
- [WBS REST endpoints — P6 EPPM Release 26](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/api-wbs.html)
- [Read WBS — P6 EPPM Release 26](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-wbs-get.html)
- [Create WBS — P6 EPPM Release 26](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-project/26/rest-api/op-wbs-post.html)
- [Creating a WBS — P6 EPPM User Guide, version 26](https://docs.oracle.com/cd/G48897_01/p6help/en/7875.htm)

## Canonical fields

- Stable wbs_id, unique within tenant/project; it is not inferred from code or display name.
- parent_kind explicitly distinguishes project from wbs. A project-root WBS is a real node whose parent is the project aggregate; a child node points to a WBS node. A missing WBS parent is not silently interpreted as an unspecified parent kind.
- parent_wbs_id is null only when parent_kind = project; it is required when parent_kind = wbs.
- code stores the node-local code, not only the concatenated hierarchical display code.
- name stores the node name.
- sequence_number stores sibling ordering; list order is made deterministic with stable-ID tie-breaking.
- record_revision provides optimistic concurrency. Every read/write remains tenant/project/revision scoped through BackendScope.

## Persistence invariants

1. At most one project-root WBS exists for one tenant/project.
2. A child parent must exist in the same tenant and project and match the requested project revision.
3. Self-parenting and ancestry cycles are rejected before a change is stored.
4. Sibling node-local codes must be unique under a WBS parent. The same local code may exist under different parents because those nodes have different hierarchical codes.
5. Stale or mixed project revisions fail closed; list must not quietly omit stale nodes and return a partial hierarchy.
6. SQLite foreign keys and PostgreSQL foreign keys/unique indexes enforce scope and identity constraints at the storage layer as well as in application checks.
7. The canonical WBS repositories preserve the established transaction-ownership rule: SQLite only commits when it began the transaction; PostgreSQL leaves commit/rollback to its caller. Activity Master assignment writes are persisted atomically with the Activity record in each adapter's existing transaction policy.
8. Activity-to-WBS assignment is stored separately from Activity payload data, tied to the same tenant/project/activity, and validated against a persisted WBS at the requested project revision. Unassigned legacy records remain readable; authenticated Activity creation/update requires an explicit non-empty WBS reference.
9. WorkPackage is intentionally not modeled as an alias for WBS. Distinct WorkPackage identity and semantics require their own reviewed contract.

## Explicitly not implemented by this persistence/API slice

- Mapping the internal project-parent reference to a numeric P6 ParentObjectId, or the internal `wbs_id` to external numeric `WBSObjectId`; any P6 integration adapter must reconcile those values against authoritative project/WBS ObjectIds rather than guessing.
- A certified P6 `Code`/`WBSCode` and `WBSNamePath`/`WBSPath` projection, including project-specific separators and path semantics. `code` in the canonical CUBI node remains the node-local code; it must not be mislabeled as the concatenated external P6 display code.
- Persistence-backed `workspace-control-room-read.v1` projection and a reviewed/versioned workspace contract that includes full WBS nodes.
- Web workspace tree consuming those authoritative nodes, including parent-child navigation and nodes with zero activities.
- Authenticated Web `/app/` runtime proof with a real persisted project.
- WorkPackage identity or WBS summary/EVM roll-up calculations.

No schedule/CPM, calendar, resource, cost, progress/EVM, or financial calculation semantics are changed by this contract.
