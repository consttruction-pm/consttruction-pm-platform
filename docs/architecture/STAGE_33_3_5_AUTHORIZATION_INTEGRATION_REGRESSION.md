# Stage 33.3.5 — Authorization Integration Regression

## Purpose
Harden the Stage 33.3.4 Application authorization boundary with fail-closed validation and explicit regression coverage.

## Required behavior
- Blank or whitespace-only tenant, project, or user identifiers are rejected before policy evaluation.
- Malformed or mutable role collections are rejected rather than treated as trusted effective roles.
- Unknown roles and roles with no configured permissions grant no access.
- Denials do not disclose tenant, project, or user identifiers.
- The policy remains provider/framework-neutral and outside Shared Domain/Calculation Core.
- This is an authorization policy boundary only. It is not proof that HTTP endpoints, login, token validation, or production identity-provider integration are wired.

## Regression tests
`tests/integration/test_authorization_boundary.py` covers the role matrix, additive roles, unknown roles, denied-error stability, context secrecy, invalid identifiers and malformed roles.

## Exit gate
1. Run the full repository test suite through GitHub Actions.
2. Resolve all failures.
3. Record the exact successful workflow run and commit in `docs/roadmap/STAGE_STATUS.md`.
4. Do not mark the stage runtime-verified based solely on file creation or a workflow definition.
