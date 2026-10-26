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
- `apps/client-sync/src/voice-provider-adapter.ts` — capability-declared input/output adapters with optional capture cancellation and speech stop.
- `apps/web/src/web-speech-provider.ts` — browser `SpeechRecognition`/`speechSynthesis` adapters. Missing APIs, denied microphone permission and recognition errors fail closed with stable codes; speech resolves only after provider completion and can be stopped.
- `apps/web/src/voice-adapters.ts` — shared `voice-command.v1` normalization, explicit fa→`fa-IR` / en→`en-US` speech languages, capability-derived `AILanguageContext`, and lifecycle cancellation.
- `apps/web/src/ai-assistant-chat.ts` — microphone capture fills the same reviewed text area used by typing. The transcript is not auto-sent; the user edits/sends it. Voice provenance (`channel`, `source`, `confidence`) is attached only while the text still matches the captured transcript, and it is audit metadata only. The server still derives identity, scope, revision and permissions from the session.
- Speech output is opt-in: a read-aloud toggle speaks new assistant replies, each assistant message has a Play control, and a Stop control cancels playback. A remount or project/language change cancels input and output so a late callback cannot write into another panel.

## Privacy and lifecycle

The CUBI client does not upload raw audio to the CUBI server. Browser speech recognition may send audio to the browser/vendor service under that service's terms; only the recognized text becomes the assistant message. The UI states this before the microphone control is used.

The committed browser E2E injects a deterministic `SpeechRecognition`/`speechSynthesis` fixture before page load. It verifies the real panel request path, provenance audit, Persian RTL and read-aloud controls, but **not** a physical microphone, a real vendor recognizer, or audible TTS quality. Those remain device/provider verification work.