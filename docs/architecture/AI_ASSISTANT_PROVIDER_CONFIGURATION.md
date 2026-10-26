# AI Assistant Provider Configuration

**Status:** Server-side natural-language turn path with a real browser chat/voice client and permission-scoped project grounding. This is not certification of complete assistant V1 and no live provider response has been verified in this checkout.

## Explicit opt-in

The assistant provider is disabled by default. In the server's secret/environment configuration, set:

- `CUBI_AI_ENABLED=true`
- `CUBI_AI_API_KEY` — secret credential for the selected provider
- `CUBI_AI_BASE_URL` — HTTPS base URL for an OpenAI-compatible Chat Completions API, normally including its version path (for example, `https://provider.example/v1`)
- `CUBI_AI_MODEL` — model identifier supported by that endpoint
- `CUBI_AI_TIMEOUT_SECONDS` — optional; defaults to `20`, valid range `1..60`

The server appends `/chat/completions` to the configured base URL. The base URL must use HTTPS and cannot include user information, a query, or a fragment. Do not place API keys in source control, static files, browser storage, HTML, or client-side environment variables.

When `CUBI_AI_ENABLED` is not explicitly true/1/yes, this provider is not initialized and the assistant route fails closed. When it is enabled, production composition requires an already configured authenticated AI action runtime with real current-grant, repository, and transaction dependencies. Missing configuration does not create a mock runtime or auto-allow grant. The Web panel probes `GET /api/projects/{project_id}/ai/assistant/capabilities` and shows a localized "provider not configured" notice; no sample answer is displayed as a real conversation.

## Request and data boundary

The authenticated endpoint is:

`POST /api/projects/{project_id}/ai/assistant/turn`

The request includes the current project revision, message, language, and up to 12 prior user/assistant messages (12,000 total history characters). System/tool roles, unknown history fields, stale revisions, and oversized input are rejected. The request is scoped from the authenticated session; client-supplied history is conversational context, never identity, permission, approval, or engineering evidence.

A voice-originated request may include `input: {channel: "voice", source, confidence}`. This provenance is audit-only; the transcript is still the message, and identity, tenant, project, revision and permissions always come from the authenticated session. Raw audio is not sent to this endpoint by the CUBI client. The browser's speech-recognition service may process audio under its own terms; only the recognized text is submitted.

Before calling the provider, the server reads a bounded project context for the authenticated tenant/project/revision:

- at most 50 persisted activities and 100 persisted relationships, with exact total/truncated counts and a 48 KB serialized limit;
- at most 50 activities from the latest published Shared Core schedule projection, including its project finish and calculation-run identity when calculation succeeds;
- a stable reason code when no published snapshot or calculation is available. The assistant must state that the authoritative calculation is unavailable rather than invent dates.

The context is read with `PROJECT_READ` authorization and cannot contain another tenant/project/revision. Failure to read it fails the turn closed before the model is called. The selected provider receives the user's message, recent conversation, and this authorized project context. Configure only a provider endpoint approved to process that information. Conversation text and project values are not written to the action audit log; the server records message length/language, input channel/source/confidence, grounding counts/flags, status, failure code, and any proposal ID.

## Safety and current capability

- Only server-registered tools that expose a JSON schema are described to the model.
- The registered model-facing actions are `activity.create` and `activity.update`; missing/ambiguous required data should be answered with a clarification.
- Tool payloads pass through the existing authoritative runtime validator and exact-scope grant checks. Model-generated evidence references are discarded.
- A model response can create a persisted proposal only. Human approval and explicit execution remain separate authenticated requests; the model cannot set identity, grants, approval policy, or execute an action.
- Project context and conversation history are marked untrusted as instructions; names or other stored values cannot change rules, identity, permissions or approval policy.
- Model/provider errors return stable sanitized codes, without echoing API keys or raw provider response bodies. Request size, response size, timeout and provider failure handling are bounded.

The Web panel supports typed chat, browser speech input into the same reviewed text area (with audit provenance), read-aloud and per-message playback where the browser supports it, EN/FA labels and RTL. The committed preview E2E uses a deterministic browser speech fixture, not a physical microphone or a provider voice; the local preview has no provider configured, so it verifies the localized fail-closed notice and request plumbing, not a live model answer.

This configuration does not yet provide persisted conversation transcripts, document/Excel intake, WBS/relationship/calendar/resource/cost model tools, report generation from grounded imports, local Desktop inference, or full end-to-end V1 acceptance. Those release criteria remain open in #1423, #1530 and #1540.
