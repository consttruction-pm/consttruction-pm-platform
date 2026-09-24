# Client Conflict Resolution UI Boundary

## Shared action model

Web, Desktop, and Mobile may render different controls, but they must expose the same semantic actions for a deferred conflict:

- **Discard**: explicitly remove the original queued mutation.
- **Refresh and Retry**: obtain current authoritative state, let the user review/edit the intended change, then enqueue a replacement mutation with a new idempotency key and current expected revision.
- **Defer**: keep the conflict pending without retrying it.

The shared client layer owns action validation and queue transitions. Presentation layers own confirmation dialogs, forms, navigation, and localization.

## Required invariants

1. A replacement mutation must use a new idempotency key.
2. A replacement mutation must carry the current expected revision.
3. The client never changes a revision merely to bypass a conflict.
4. No local scheduling, cost, Progress, or calendar recalculation is performed as part of conflict resolution.
5. Discard requires explicit user intent in the presentation layer.
6. Deferred conflicts are not returned by normal sync polling.
7. Web, Desktop, and Mobile must preserve equivalent semantics even when UX differs.

## API boundary

`ConflictResolutionRequest` and `ConflictResolutionService` provide the framework-neutral client boundary. UI adapters should translate user interaction into these actions rather than manipulating queue internals directly.

`ClientConflictPresentation` provides the framework-neutral view state for Web/Desktop/Mobile. It carries operation, original idempotency key, expected revision, stable error code, retryability, and the shared action set. It deliberately does not carry localized button labels or server error message text; those remain presentation-layer concerns.

The presentation model contract is `client-conflict-presentation.v1`.


## Refresh-and-retry session boundary

The refresh-and-retry action may use `ConflictResolutionService.refresh_and_retry_from_session()` only after the `ClientProjectSession.revision` has been established from an authoritative refresh/read response. A missing session revision is rejected. The service requires a fresh idempotency key and preserves the original project context; it does not infer, increment, or rewrite the revision locally.
