# Voice Interaction Boundary

## Scope

Voice input is a client capability and adapter concern. Speech recognition providers must produce a versioned `voice-command.v1` envelope before the command enters project-control workflows.

## Authoritative rules

- The voice layer never calculates Scheduling/P6, Progress/EVM, Resource/Cost or financial values.
- The command scope must match the authoritative tenant/project/project revision supplied by the calling client/application context.
- The installed AI language capability must explicitly allow voice input.
- The transcript, language, timestamp, source and confidence are preserved as provenance.
- Voice commands are normalized deterministically before being converted to `schedule-query.v1`.
- A scenario or consequential action produced from voice remains a proposal; application-layer authorization and human approval remain authoritative.
- Offline voice support is capability-driven by the installed language/AI pack. A missing verified capability fails closed.
- Actual ASR/TTS providers, microphone permissions, audio codecs, cloud endpoints and device APIs remain behind provider-specific adapters.

## Current implementation

- `shared/contracts/voice-command.v1.schema.json`
- `apps/client-sync/src/voice-command.ts`
- `apps/client-sync/src/ai-language-contract.ts`

The current gate intentionally stops at normalized transcript -> query request. Provider-specific audio/ASR integrations are subsequent adapters.