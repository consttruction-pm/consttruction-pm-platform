# PostgreSQL Production Hardening Boundary

The application owns transaction boundaries. PostgreSQL safety limits are therefore applied with `SET LOCAL`, so they expire with the current transaction and cannot silently leak into a pooled connection.

Default limits:
- statement timeout: 30s
- lock timeout: 5s
- idle-in-transaction timeout: 60s

The policy is explicit, validated, parameterized, and does not change domain calculations or persistence semantics. Deployment-specific infrastructure may override the policy through application configuration.
