# AI Action / Approval Boundary

This boundary governs proposed AI tool actions at the application layer.

- Every proposal is tenant/project scoped and carries an opaque proposal identity.
- Tool permission is evaluated through an explicit adapter.
- Actions requiring human approval cannot be approved without an actor identity.
- Approved and rejected decisions produce a stable audit event.
- Evidence references remain opaque IDs; this boundary does not interpret project-control calculations.
- AI model/provider execution, token verification, tool implementations and P6/Progress/EVM/Resource/Cost calculations remain outside this boundary.
