# ERP / Accounting Integration Boundary

This boundary defines a vendor-neutral server integration seam for ERP/accounting synchronization.

- Operations are tenant/project scoped and carry an opaque operation identity.
- The adapter returns only the platform-level outcome: accepted, rejected, or retry.
- External references remain opaque; vendor-specific identifiers and SDKs stay behind adapters.
- No financial formulas, cost calculations, AP/AR semantics, or authoritative project-control calculations are implemented here.
- A future production adapter may translate the contract to a specific ERP/accounting provider.


## BI integration boundary
A provider-neutral BI adapter now belongs beside the ERP/accounting boundary. It transports tenant/project/operation identity and opaque payloads to a BI provider and returns accepted/rejected/retry status plus an opaque external reference. It does not calculate schedule, Progress/EVM, Resource/Cost, financial or portfolio metrics; authoritative metrics remain supplied by Shared Core/read models. Vendor SDKs, authentication, transport and warehouse-specific schemas remain behind explicit adapters.
