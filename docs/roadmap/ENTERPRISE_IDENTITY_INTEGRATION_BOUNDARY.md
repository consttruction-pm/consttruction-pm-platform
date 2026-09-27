# Enterprise Identity Integration Boundary

This boundary normalizes enterprise identity claims before application authorization.

- OIDC and SAML are represented by one provider-neutral platform contract.
- Tenant identity is explicit and carried into application authorization context.
- Subject and issuer remain the authoritative external identity references.
- Roles are normalized deterministically and duplicates are removed.
- Provider SDKs, token verification, key discovery and credential handling remain outside Shared Core and this adapter.
- This boundary does not grant permissions by itself; application authorization remains authoritative.
