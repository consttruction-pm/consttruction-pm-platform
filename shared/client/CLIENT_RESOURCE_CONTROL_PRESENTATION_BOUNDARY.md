# Resource Control Client Presentation Boundary

`ClientResourceControlDTO` presents authoritative Resource/Cost control totals to Web/Desktop/Mobile as canonical decimal strings.

The client boundary includes planned, actual, remaining, unit variance, and cost variance. Clients render and localize these values but do not recompute them. Resource rates, utilization, capacity, cost, variance, and financial calculations remain authoritative in the Resource/Application/Core layers.

The presentation contract is `resource-control-presentation.v1`. Numeric JSON values are rejected at the client boundary to prevent loss of decimal semantics.
