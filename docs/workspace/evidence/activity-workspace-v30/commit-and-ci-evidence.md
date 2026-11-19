# V30 — Commit and CI evidence

## Branch and commits

- Repository: `consttruction-pm/consttruction-pm-platform`
- Branch: `feat/2047-activity-workspace-v26`
- PR: #2048 (no merge, no deploy)
- V29 baseline HEAD: `af1ec41e01a6b540e952ed0ada1577a9187d10a6`
- **V30 implementation and tested code SHA: `48f2f0c1b7d2e83427b549af0803563fea100ccc`**
- Evidence/docs commit: the commit containing this file (pushed after the implementation).

Working tree before the implementation commit contained only the V30 files listed in
`changed-files.md`; no V29 evidence or other author’s change was deleted or rewritten.

## Local browser runs at `48f2f0c1b…`

Dedicated preview: `PYTHONPATH=src py -3 -m construction_pm.preview --web-root apps/web
--database .preview/v30-final.sqlite3 --port 4200 --reset` (fresh database). The server was
stopped after the runs.

| Suite | Exit | Duration | Result |
|---|---:|---:|---|
| `gantt-attachments-v30.mjs` | 0 | 26 s | pass, 11 steps, 8 screenshots |
| `activity-edit-v30.mjs` | 0 | 47 s | pass, 10 steps, 6 screenshots |
| `visual-matrix-v30.mjs` | 0 | 74 s | pass, 36 cells, 12 dialog cells, 84 screenshots |

Each JSON records `testedCodeSha=48f2f0c1b7d2e83427b549af0803563fea100ccc`.

## Local unit/static at the same tree

- `npx tsc --noEmit`: pass.
- `npm run build`: pass.
- `npx tsx --test src/*.test.ts`: 1200 pass, 0 fail.
- Python relevant suites: 15 new tests pass; full suite 4707 pass / 224 skipped / 4 Windows-only
  environment failures (documented in `test-matrix.md`).

## GitHub Actions at `48f2f0c1b…`

| Workflow | Run | Status |
|---|---|---:|
| ConstructionPM CI | [44451257127](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/44451257127) | success (3.11 and 3.12 jobs) |
| ConstructionPM Web CI | [44451257359](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/44451257359) | success |
| PostgreSQL Integration | [44451257172](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/44451257172) | success |
| Client Typecheck | [44451257111](https://github.com/consttruction-pm/consttruction-pm-platform/actions/runs/44451257111) | success |

All four workflows completed successfully for the implementation SHA.

## Prohibitions honoured

No merge, no deploy, no Vercel preview/deployment, no production database, no force push, no
history rewrite, no deletion of another author’s branch or changes.
