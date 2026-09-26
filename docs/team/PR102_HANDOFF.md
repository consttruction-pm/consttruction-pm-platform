# PR #102 handoff — Stage 33.4.70

## Current state

- Branch: `feature/hasan/stage-33-4-70-api-revision-boundary`
- Pull request: #102
- Current branch head: tracked directly by PR #102; verify the PR head SHA before handoff/review.
- Stage: 33.4.70
- Merge: not performed
- Stage status: runtime verification pending

## What is implemented

The sync revision boundary now enforces the JavaScript-safe integer maximum
`9007199254740991` in the versioned contracts and Application/API integration
regressions. Unsafe authoritative revisions are rejected with
`INVALID_PROJECT_REVISION`, and unsafe mutation `expected_revision` values are
rejected with `INVALID_EXPECTED_REVISION`. The same client-safe upper bound is
enforced again at the `OfflineMutation` domain boundary so internal callers
cannot construct an unsafe revision object around the API validation.

The existing Stage 33.4.70 flow remains:

1. mutation reaches the versioned API boundary;
2. stale revision produces the conflict outcome;
3. client refreshes the authoritative revision;
4. client rotates the mutation idempotency key;
5. explicit retry uses the refreshed revision;
6. successful retry reaches ACKNOWLEDGED.

## Verification blocker

The latest GitHub Actions runs for the current branch head complete within
seconds with `runner_id=0`, an empty `runner_name`, zero workflow steps, and no
downloadable job logs. This signature has repeated across the repository's
Python, PostgreSQL and TypeScript workflows, so it is recorded as a hosted
runner allocation/infrastructure blocker rather than as an application test
failure. Runtime verification must remain pending until executable steps run.

## Help requested

Please inspect the GitHub Actions runner/workflow execution path for PR #102 and
confirm why jobs terminate before the first workflow step. Do not mark
Stage 33.4.70 runtime-verified until the required Python and TypeScript checks
actually execute and pass.


## Runner isolation test — 2026-09-26

A minimal runner-only diagnostic was executed from this branch using three GitHub-hosted labels: ubuntu-latest, ubuntu-24.04, and ubuntu-slim. All three job objects were created but terminated before the first step with empty step arrays and no job logs. This isolates the current CI blocker to GitHub-hosted runner allocation/provisioning rather than the Stage 33.4.70 implementation or its dependencies.

Diagnostic run: 36218453294
Jobs: 108339028751, 108339028861, 108339028885
