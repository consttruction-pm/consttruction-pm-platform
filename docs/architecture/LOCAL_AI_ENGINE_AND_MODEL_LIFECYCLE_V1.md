# Local AI Engine & Model Lifecycle Specification v1

## Scope

The Shared Core owns model selection semantics, execution decision semantics, provenance and lifecycle orchestration. Host platforms supply the actual inference/STT/TTS engine implementation.

## Text inference lifecycle

1. Select the newest verified compatible model for the preferred language.
2. Verify the artifact is present and verified.
3. Enforce model RAM/storage compatibility and local policy.
4. Load the selected package/version through the host engine.
5. Keep the previous active model until replacement loading succeeds.
6. Expose the active package/version and loaded-model state.
7. Evict only inactive models when the memory/concurrency budget requires it.
8. Unload by package **and version**.
9. Refuse replacement when retaining the active model is required but capacity is insufficient.

## Voice lifecycle

Voice input and output models are independently selected and loaded. The same verified-artifact, preferred-language and offline-policy constraints apply to both directions.

## Execution provenance

Every LanguageBoundAIService execution result carries its AIExecutionDecision:
- mode: offline/online
- language
- model package ID
- model version
- reason

This receipt is intended to be attached to the existing AI audit/provenance trail.

## Persistence

Concrete artifact stores are now available for:
- Web: IndexedDB
- Desktop: filesystem binary + metadata
- Mobile: host-provided binary storage + metadata storage

The Mobile adapter intentionally separates large binary model data from lightweight metadata so the native shell can use an OS-appropriate file/object store.

## Security

Private model-signing keys are never present in client runtimes. Model artifacts are accepted only through the existing verified-pack pipeline. Engine adapters receive verified artifacts and exact package/version identity.

## Current implementation boundary

The Shared Core and client persistence/lifecycle contracts are implemented. Actual local inference engines, STT/TTS engines, device-specific memory/thermal policies and production performance benchmarks remain host-specific release work.
