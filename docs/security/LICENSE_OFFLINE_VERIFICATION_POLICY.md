# License and Offline Verification Policy

## Status
Approved product policy for the Construction Project Management Platform.

## Verification schedule
- Initial activation: online verification is required once.
- Normal license verification: once every 30 calendar days.
- Offline grace period: 30 additional calendar days after a missed verification.
- Verification should run in the background where possible and must not interrupt active project work.

## Offline behavior
The desktop application must remain usable offline.
Core Primavera/CPM scheduling and project calculations must never depend on an internet connection.

If verification is overdue:
1. Show a non-blocking warning before the normal verification window expires.
2. Continue normal core scheduling/project calculations during the grace period.
3. After the grace period, restrict only license-gated capabilities; do not corrupt, delete, or lock project data.

## Events requiring online verification
Online verification is required for:
- First activation.
- Reinstallation when device identity cannot be restored.
- Device transfer/change.
- Subscription/plan changes.
- Payment or entitlement changes.
- License recovery or revocation checks.

## Security requirements
- License tokens must be digitally signed.
- License entitlement must be bound to the user/account and authorized device identity.
- Valuable server-authorized operations may require online entitlement validation.
- Revoked licenses must be rejected at the next successful verification.
- Verification must not expose or depend on the internal Primavera/CPM calculation engine.

## Implementation boundary
This policy belongs to the License/Activation infrastructure layer and must remain isolated from the shared Primavera/CPM calculation core.
