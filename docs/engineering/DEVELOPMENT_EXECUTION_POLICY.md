# Development Execution Policy

## Canonical development and test environment

The primary environment for project development, code execution, and automated testing is **GitHub/Codex**.

ChatGPT is used for project coordination, analysis, specification, review, troubleshooting guidance, and other support tasks. It is **not** the canonical runtime/test environment for the project.

GitHub/Codex must remain the authoritative working environment because the project requires SQL/PostgreSQL, GitHub Actions, and the complete runtime/tooling stack for reliable integration and runtime verification.

## Working rule

1. Developers perform implementation, execution, debugging, and testing in GitHub/Codex.
2. ChatGPT may inspect, analyze, explain, review, and coordinate changes, but missing local/runtime dependencies must not cause the project workstream to move to a ChatGPT-only execution model.
3. GitHub remains the source-controlled project workspace and the location for committed implementation artifacts and test results.
4. This policy applies to all project developers and agents, including Jalal, Hassan, and Javad.
5. Any earlier project rule that made ChatGPT the exclusive coding/testing environment is superseded by this policy.

## Rationale

A previous ChatGPT-only execution attempt was stopped because the required SQL runtime was not available. The project therefore returns to the established GitHub/Codex workflow so database-backed and full-stack tests can execute in the intended environment.
