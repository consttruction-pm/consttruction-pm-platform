# Canonical WBS Master Persistence Contract — 2026-10-23

## Status and scope

This contract defines the first persistence boundary for CUBI's canonical Work Breakdown Structure (WBS) nodes. It does **not** claim that the end-to-end workspace read model, Activity-to-WBS linkage, HTTP API, production composition, or Web hierarchy is complete. Issues #1384, #1359, and #1515 remain open until those separate gates are demonstrated.

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
7. SQLite repository writes leave an application-owned transaction open; the PostgreSQL adapter never commits an application transaction.
8. WorkPackage is intentionally not modeled as an alias for WBS. Activity-to-WBS reference persistence and distinct WorkPackage metadata require their own reviewed contract.

## Explicitly not implemented by this persistence slice

- Mapping the internal project-parent reference to a numeric P6 ParentObjectId; the REST adapter must reconcile this against the authoritative project ObjectId rather than guessing from a CUBI project string.
- Activity-to-WBS foreign-key/contract integration.
- WBS CRUD HTTP endpoints and production API composition.
- Persistence-backed workspace-control-room-read.v1 projection.
- Versioned Web read-contract extension and nested WBS renderer.
- WorkPackage identity or WBS summary/EVM roll-up calculations.

No schedule/CPM, calendar, resource, cost, progress/EVM, or financial calculation semantics are changed by this contract.
