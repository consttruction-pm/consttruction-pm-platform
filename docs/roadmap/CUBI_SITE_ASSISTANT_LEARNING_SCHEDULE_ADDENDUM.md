# CUBI SITE — Interactive Engineering Assistant Learning Schedule Addendum

**Created:** 2026-10-23  
**Purpose:** Add the approved interactive engineering learning, reusable engineering knowledge, and durable-memory capability to the **CUBI SITE / Website execution schedule**.  
**Scope boundary:** This is a site-specific schedule addendum. It is **not Jalal 5**, does not revise the CUBI master schedule, and must not replace or reduce any existing site or product requirement.

## 1. Baseline reconciliation rule

A separately named, authoritative CUBI SITE schedule file was not identifiable in the current repository/library search. The repository does contain website route/SEO requirements and website workstream rows in other planning artifacts, but the product owner explicitly requires this work to be managed against the CUBI SITE schedule—not the Jalal 5 master schedule.

Therefore:
- The work package below has an internally normalized weight of **100.00%**.
- These weights are **not yet the percentage contribution to the entire CUBI SITE schedule**. That contribution must be calculated only after the authoritative site schedule and its existing weight denominator/formulas are located and reconciled.
- Do not claim that the website schedule itself has been updated, rebaselined, or accepted until the actual authoritative schedule file has been edited and its total-weight/formula checks pass.
- No existing task weight or requirement may be removed, reduced, or overwritten to make room for this addition.

## 2. Weighted work package — internal total 100.00%

| ID | Work package / deliverable | Internal weight | Primary dependency | Completion evidence required |
|---|---|---:|---|---|
| SITE-AI-01 | Wire real assistant conversations to feedback, correction, clarifying questions, and revised recommendations | 12.00% | Existing V1 assistant contract and real conversation orchestration | End-to-end tests show that the assistant can discuss alternatives, ask the user, revise reasoning, and explain changes; raw feedback is not automatically published as shared knowledge |
| SITE-AI-02 | Persist candidate lessons and interaction outcomes with review status and lineage | 12.00% | Existing engineering-memory domain/repository | Save → restart → read-back verified; versions/statuses and source conversation references are traceable without exposing private transcripts to the general index |
| SITE-AI-03 | Retrieve relevant, validated methods for a newly recognized project type and adapt explanation depth | 14.00% | Persistent memory and retrieval/orchestration | Comparable-project scenarios retrieve generalized methods, formulas with units/assumptions/limits, checklists, and recommendations; response grounds claims and flags missing information |
| SITE-AI-04 | Admin-controlled internet research and recurring/manual knowledge refresh in the site admin panel | 14.00% | Admin identity and authorization | Search requires explicit valid permission; topic/domain/period/source scope and run logs are visible; permission to search is separate from permission to publish |
| SITE-AI-05 | Source review, contradiction handling, validation, rights/privacy checks, approval, versioned publish and rollback | 14.00% | SITE-AI-04 | Auditable candidate → review → validation → human approval → publish lifecycle; provenance, rationale, version and rollback are tested |
| SITE-AI-06 | Enforce private user/project/org memory boundaries and privacy-safe generalization | 14.00% | Existing repository scope model and authorization | Negative cross-user/cross-tenant tests pass; other users never receive or reconstruct project names, quantities, costs, dates, schedules, documents, transcripts, staffing figures or outputs; only genuinely generalized methods can enter general knowledge |
| SITE-AI-07 | Durable backup/restore, integrity verification, export/import, and forward migration for later versions | 10.00% | Versioned memory records and schema | Backup integrity is checked and restore is tested in an isolated environment; migration is idempotent, logged, and recoverable/rollback-capable |
| SITE-AI-08 | Site/workspace UX for actionable suggestions on reports, WBS/activities, resources, risks, and next actions | 5.00% | Existing real tools, action grants, and approval boundary | UI suggestions are not mistaken for executed changes; mutations require the right permission, required confirmation, revision checks, and durable audit |
| SITE-AI-09 | Golden project/conversation benchmarks, security/privacy regression, and exact-SHA end-to-end acceptance | 5.00% | All preceding packages | Repeatable benchmarks cover retrieval, grounding, interaction quality, privacy, backup/restore and migration; material regressions block release |
| **TOTAL** |  | **100.00%** |  | **Formula check: sum of internal weights = 100.00%** |

## 3. Dependencies and implementation rules

1. Inspect current main, current tests, the real assistant orchestration, repository adapters, site routes, admin authorization and existing tests before coding. Reuse existing implementation; do not rebuild merged foundations.
2. Map each SITE-AI package to actual existing CUBI SITE schedule activity IDs after locating the authoritative site schedule. Record the source file, version, row IDs and formula used.
3. Owners must be assigned by verified code boundaries and team responsibility, not assumed from labels. Record actual remaining effort and dates only after owner/dependency/capacity review.
4. No earned progress for issue text, documentation, open PRs, mock-only controls, or a passing general CI run alone. Progress requires accepted behavior and linked evidence on the exact tested SHA.
5. Keep personal memory, project-private memory, organization knowledge, and general engineering knowledge isolated in storage, retrieval, authorization and export paths.
6. A user's expertise level must not be inferred as a credential from writing style. The assistant should ask clarifying questions, discuss alternatives, invite critique, adapt explanation depth, and revise recommendations based on evidence.
7. Shared learning may transfer generalized methods, reasoning patterns, formulas with assumptions/units/limits, checklists and processes—not another user's project values or identifiable details.
8. Admin research must use separate permission gates for search/collection, validation and publication. A scheduled refresh must stop if the required permission is absent or revoked.
9. Learning and memory may improve recommendations; they must not autonomously change the authoritative Shared Domain/Calculation Core, schedule logic, project records, or permission model.
10. Keep all previously approved CUBI SITE and product requirements additive and binding.

## 4. Acceptance gate

This addendum is accepted into the CUBI SITE schedule only when:
- the actual authoritative CUBI SITE schedule file is identified and updated;
- existing website/workspace tasks are cross-referenced without omissions or duplicate credit;
- the schedule's original total-weight rules and formulas are preserved and rechecked;
- the new package's internal weights sum to exactly 100.00%;
- the package's contribution to the site-wide total is calculated from the real baseline, not guessed;
- dependencies, owners, effort, and dates are evidence-based;
- the site-specific schedule update and its acceptance evidence are linked from the execution issue.

## 5. Canonical requirements

- Cumulative assistant V1 contract: docs/architecture/AI_ASSISTANT_V1_REQUIREMENTS.md
- Interactive learning and durable memory: docs/architecture/INTERACTIVE_ENGINEERING_LEARNING_MEMORY.md
- Product/security/privacy principles: docs/architecture/PRODUCT_PRINCIPLES.md
- Implementation tracking: Issue #1540
- CUBI SITE schedule integration and weighting: Issue #1544
- Website page/SEO audit: Issue #1436
