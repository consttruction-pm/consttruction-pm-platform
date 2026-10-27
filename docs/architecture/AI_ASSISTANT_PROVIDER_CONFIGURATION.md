# AI Assistant Provider Configuration

**Status:** Initial server-side natural-language turn path; not certification of complete assistant V1.

## Explicit opt-in

The assistant provider is disabled by default. In the server's secret/environment configuration, set:

- `CUBI_AI_ENABLED=true`
- `CUBI_AI_API_KEY` — secret credential for the selected provider
- `CUBI_AI_BASE_URL` — HTTPS base URL for an OpenAI-compatible Chat Completions API, normally including its version path (for example, `https://provider.example/v1`)
- `CUBI_AI_MODEL` — model identifier supported by that endpoint
- `CUBI_AI_TIMEOUT_SECONDS` — optional; defaults to `20`, valid range `1..60`

The server appends `/chat/completions` to the configured base URL. The base URL must use HTTPS and cannot include user information, a query, or a fragment. Do not place API keys in source control, static files, browser storage, HTML, or client-side environment variables.

When `CUBI_AI_ENABLED` is not explicitly true/1/yes, this provider is not initialized and the assistant route fails closed. When it is enabled, production composition requires an already configured authenticated AI action runtime with real current-grant, repository, and transaction dependencies. Missing configuration does not create a mock runtime or auto-allow grant.

## Request and data boundary

The authenticated endpoint is:

`POST /api/projects/{project_id}/ai/assistant/turn`

The request includes the current project revision, message, language, and up to 12 prior user/assistant messages (12,000 total history characters). System/tool roles, unknown history fields, stale revisions, and oversized input are rejected. The request is scoped from the authenticated session; client-supplied history is conversational context, never identity, permission, approval, or engineering evidence.

The selected provider receives the user's current message and the supplied conversation history. Configure only a provider endpoint approved to process that information. The conversation text is not written to the action audit log; the server records request length/language, status, failure code, and any proposal ID.

## Safety and current capability

- Only server-registered tools that expose a JSON schema are described to the model.
- The initial registered model-facing action is `activity.create`; missing/ambiguous required data should be answered with a clarification.
- Tool payloads pass through the existing authoritative runtime validator and exact-scope grant checks. Model-generated evidence references are discarded.
- A model response can create a persisted proposal only. Human approval and explicit execution remain separate authenticated requests; the model cannot set identity, grants, approval policy, or execute an action.
- Model/provider errors return stable sanitized codes, without echoing API keys or raw provider response bodies. Request size, response size, timeout and provider failure handling are bounded.

This configuration does not yet provide persisted conversation transcripts, voice/document/Excel intake, WBS/relationship/calendar/resource/cost tools, authoritative Shared Core recalculation and report grounding, full result reconciliation, local Desktop inference, or full end-to-end V1 acceptance. Those release criteria remain open in #1423, #1530 and #1540.

## Hosted preview limitation and activation checklist

The shared Render workspace preview (`cubi-workspace-preview-2026`) is a public demo and is intentionally read-only. Its current composition does not provide an AI assistant provider or action runtime, so the assistant-turn endpoint is unavailable there. Do not disable the public-demo read-only guard or expose planner/admin demo identities to make this endpoint work.

Setting only `CUBI_AI_ENABLED=true` is not a complete fix. The server also requires a configured AI action runtime with current-grant checks, durable proposal/audit storage, transaction handling, and real application-tool handlers. Enabling the provider without that runtime can prevent this preview composition from starting. Do not add credentials until those dependencies are wired and tested in a private, authenticated staging deployment.

The currently documented model-facing mutation is `activity.create`; a complete project-creation workflow (`project.create`, WBS/activity/relationship/calendar construction, and authoritative schedule recalculation) is not yet exposed as one supported assistant action. Do not expect the assistant to build an entire project on this preview until that end-to-end capability has been implemented and verified.

Once a private deployment has the provider and runtime wired, configure the five server-side variables described above in its hosting dashboard. Keep the API key in the host secret store, never in source control or browser variables. Then verify a non-mutating assistant turn, a persisted proposal, explicit approval/execution, permission denial for a Viewer, stale-revision rejection, and fresh read-back before using it for real project data.
