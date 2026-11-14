# Exclusive project checkout across every write domain — 2026-11-14

## Tested code

- Merge commit: `41aaf874` (`feat(project): enforce the exclusive checkout across every write domain`, PR #1958)
- Code commit: `f2460bee`
- Prerequisite schema fix: `e8c4e5bd` (repairs the broken PostgreSQL lifecycle schema statement found during this slice)

## What changed

Only metadata/status and canonical schedule-settings writes previously consulted
the exclusive checkout. Activity, WBS, relationship and cost-account writes still
mutated data for a user who did not hold the lease.

One shared guard now runs immediately before every such repository write:

- `src/construction_pm/project_checkout.py` — `ProjectCheckoutLease`,
  `ProjectCheckoutConflict` (`PROJECT_CHECKED_OUT_BY_OTHER`) and
  `require_project_write_ownership`.
- `P6ActivityMasterAPI` create/update (also covers progress updates and AI
  activity creation), `P6WBSMasterAPI` create/update/delete/copy/replace
  milestones, `P6RelationshipAPI` create/update/delete and
  `P6CostAccountAPI` create.
- All four HTTP route blocks return `409` with code
  `PROJECT_CHECKED_OUT_BY_OTHER` and the checkout-conflict message key.
- Preview reads the SQLite checkout row; production reads the request-scoped
  PostgreSQL connection, so the ownership check and the guarded mutation share
  one transaction.

## Verification at `41aaf874`

| Check | Result | Log |
|---|---|---|
| Targeted Python suites (checkout, activity/WBS/cost/relationship HTTP, preview runtime, schedule-settings checkout, AI tools) | 169 passed | `tests.txt` |
| Live PostgreSQL lifecycle + checkout-lease reader | 6 passed | `postgres-live.txt` |
| Full Python suite (no external DSN) | 4290 passed, 194 skipped | run at the merge SHA |
| Web `npm test` | 1148 + 14 passed, `tsc --noEmit` clean | — |
| Web `npm run build` | clean | — |
| `project-details-v26.mjs` E2E (fresh SQLite, real preview server) | 9/9 scenarios | `e2e-project-details.txt` |

Screenshots from the same fresh run:

- `04-project-checked-out.png` — exclusive lease is stored and shown.
- `04b-schedule-settings-checkout-lease.png` — another user's schedule-settings
  write is rejected while the admin holds the lease.

The browser suite does not exercise activity/WBS/relationship/cost conflicts;
`tests/test_preview_runtime.py::test_preview_checkout_blocks_every_write_domain_for_other_users`
does, through the real preview WSGI application and two real demo sessions:
all four writes return `409 PROJECT_CHECKED_OUT_BY_OTHER`, nothing is persisted,
and the holder can still create an activity.

## Remaining gaps

- No checkout-aware bulk/import write path beyond the listed APIs exists yet.
- The responsibility-structure management window and Apply Actuals remain open;
  see the ledger.
