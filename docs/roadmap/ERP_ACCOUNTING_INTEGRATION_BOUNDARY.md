# ERP / Accounting Integration Boundary

This boundary defines a vendor-neutral server integration seam for ERP/accounting synchronization.

- Operations are tenant/project scoped and carry an opaque operation identity.
- The adapter returns only the platform-level outcome: accepted, rejected, or retry.
- External references remain opaque; vendor-specific identifiers and SDKs stay behind adapters.
- No financial formulas, cost calculations, AP/AR semantics, or authoritative project-control calculations are implemented here.
- A future production adapter may translate the contract to a specific ERP/accounting provider.
