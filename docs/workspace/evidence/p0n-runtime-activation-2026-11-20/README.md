# P0-N.2 runtime activation — evidence index (2026-11-20)

Feature branch: `feat/p0n2-runtime-activation`
Base: `ae6e72e4` (`main`)
Feature commits: `dd11d6c7` (registry builder), `21140510` (runtime wiring),
`180b8e7d` (worker), `8fdb06a9` (live tests), `ca123a5b` (evidence),
`5b4cfb71` (process-executor IPC fix).
No merge to `main` and no deployment was performed.

| Artifact | Content |
| --- | --- |
| `final-acceptance-report.md` | The 12 exit criteria, each with evidence and status |
| `runtime-composition-map.md` | Web/worker composition, routes, data flow, invariants |
| `calendar-registry-traceability.md` | Blocker removal, builder algorithm, fail-closed codes, tests |
| `professional-help-traceability.md` | 21-row Professional V26 matrix with PDF pages and exact HTML URLs |
| `eppm-help-traceability.md` | 21-row EPPM V26 matrix with exact HTML URLs |
| `two-environment-reference-map.md` | Authority, identity, non-substitution rules, capability crosswalk |
| `job-lifecycle-evidence.md` | Durable submit→execute→retrieve proof, cancellation, recovery, failure |
| `multi-project-budget-evidence.md` | Budget/scheduler design and measured concurrency |
| `performance-benchmarks.md` | Real engine matrix: sizes, shapes, capacity, projects, worker e2e |
| `test-matrix.md` | Required test families, targeted and full-suite results |
| `known-limitations.md` | Honest product/evidence limits and infra-vs-product distinction |
| `environment.json` | Commit, tree, Python, CPU, memory, PostgreSQL, PDF hash |
| `logs/` | Targeted suite, full suite, reference extraction, live thread/process runs |
| `results/` | Raw benchmark and worker JSON; `professional-pdf-html-map.csv` (topic → URL → PDF page) |
| `screenshots/` | Why no browser screenshots apply |

## Reproduce

```
cd /data/work/repo
export P6_TEST_POSTGRES_DSN=postgresql://postgres@127.0.0.1:55432/postgres
export CONSTRUCTION_PM_POSTGRES_DSN="$P6_TEST_POSTGRES_DSN"
PYTHONPATH=src python -m pytest -q \
  tests/integration/test_p0n2_runtime_activation.py \
  tests/test_calendar_registry_production_builder.py
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python scripts/p0n2_runtime_matrix.py run \
  --out-dir docs/workspace/evidence/p0n-runtime-activation-2026-11-20/results
PYTHONPATH=src python scripts/p0n2_runtime_matrix.py report \
  --matrix results/matrix-20261120T035930Z.json \
  --worker results/worker-e2e-20261120T035930Z.json \
  --md docs/workspace/evidence/p0n-runtime-activation-2026-11-20/performance-benchmarks.md
```
