# CUBI Assistant Provider Configuration — Local-Only Product Profile

**Effective product decision:** 2026-10-28  
**Status:** Local-inference adapter implemented on the Engineering Intelligence feature branch; runtime/model provisioning and end-to-end product acceptance remain open.  
**Canonical implementation gate:** [#1423](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1423).  
**No-key architecture:** [CUBI Engineering Intelligence Toolchain and Acceptance Plan](CUBI_ENGINEERING_INTELLIGENCE_TOOLCHAIN_AND_ACCEPTANCE.md).

## 1. Product rule: no external AI provider key

The CUBI product profile uses local inference. A user/operator must not need to connect CUBI to another company's AI API, paste an external AI key, or configure a remote model URL to use the assistant. CUBI must not make an outbound model request or silently switch to a cloud provider when the local model is missing, slow or unavailable.

Deterministic CUBI capabilities—project persistence, structured file parsing, input validation, ID allocation, approved calculation services, typed report datasets, authorization and audit—must remain available without a language model where their relevant services are implemented. Flexible natural-language synthesis is available only when the configured local model/runtime is actually provisioned.

The legacy `OpenAICompatibleChatProvider` class is not selected by CUBI's product environment factory. `build_ai_chat_provider_from_environment()` accepts only `local-ollama`; any other provider selection fails closed. CUBI's production and local preview composition must use that factory. There is no remote fallback.

## 2. Local runtime configuration

For a private authenticated deployment that intentionally enables assistant turns, configure these server-side environment variables:

- `CUBI_AI_ENABLED=true`
- `CUBI_AI_PROVIDER=local-ollama` (optional; this is the default and only accepted product provider)
- `CUBI_AI_LOCAL_MODEL` — exact model name already installed in the local Ollama runtime; required
- `CUBI_AI_LOCAL_BASE_URL` — optional; defaults to `http://127.0.0.1:11434`
- `CUBI_AI_LOCAL_TIMEOUT_SECONDS` — optional; defaults to `120`, valid range `1..300`

No `CUBI_AI_API_KEY`, external provider URL, or remote-model credential is required. The implementation only permits loopback hosts (`localhost`, `127.0.0.1`, or `::1`) and rejects path/query/user-info changes in the configured base URL. It uses the local `/api/chat` endpoint without an Authorization header and rejects HTTP redirects.

Before enabling the assistant, install and provision Ollama (or a compatible local service that implements this endpoint) in the same trusted host/network namespace, download the exact model assets, verify the model starts, and run the Persian/English construction-domain golden test set. Model weights, memory, CPU/GPU needs, license, startup health, concurrency and upgrade/rollback must be covered by deployment operations; this code does not download model assets or prove a model is already installed.

If model configuration is absent, an enabled deployment leaves the assistant route unavailable (HTTP 503 with a stable not-configured error) while the rest of the site continues running; it does not contact any external service. If the configured local endpoint/model is unavailable, the assistant turn returns a sanitized stable runtime/model error. Do not enable the assistant in a public demo or bypass the demo's read-only guard to test it.

## 3. Current implementation boundary

The versioned adapter supports local JSON chat inference and plugs into the existing proposal-only orchestrator. Existing tool calls still require the authenticated application context, current grants and project revision, real typed handlers, explicit approval, persistent audit and fresh read-back. The model cannot approve or execute a proposal by itself.

The current production composition's real AI action runtime and tool registration remain incomplete for full assistant V1. In the documented provider slice, supported actions are limited; full WBS/activity/relationship/calendar construction, resource/equipment and quantity estimation tools, risk mitigation, Form Builder, file/Excel/document/voice intake, report/chart grounding, memory retrieval/research/publishing, backup/restore and golden benchmarks must not be claimed complete until independently implemented and verified.

The current local adapter does not by itself certify Desktop offline operation. Desktop must package/provision a real local inference runtime and model assets, run without Internet for its declared offline capabilities, and have no hidden cloud fallback under the separate offline AI release gate.

## 4. Security and data boundaries

- Model credentials, if an application-local service ever requires local authentication, remain server-side; do not place them in browser code, browser storage, source control, exports or knowledge bundles.
- The configured model URL must be loopback. Do not weaken that rule to allow a public host or route prompts to a public endpoint.
- Retrieved files, project notes and source pages remain untrusted instructions/data; they cannot grant permissions or change the tool policy.
- No raw prompt or project content is promoted to shared/general learning by default.
- All mutations go through typed CUBI application use cases and Shared Core; no model-side calculation engine is allowed.
- A missing provider, unsupported action, unavailable model or rejected proposal must fail clearly. Never display a successful mutation unless a fresh authoritative read-back confirms it.

## 5. Required exact-head verification

Before release, test on one exact commit:

1. Local chat works with `CUBI_AI_API_KEY` absent and with no outbound network access.
2. A request uses only the configured loopback endpoint; no Authorization header is sent and redirects are rejected.
3. Missing model, missing runtime, malformed JSON, oversized input/output and timeout return sanitized stable errors.
4. Non-mutating turns work; mutations create persisted proposals only; approving/executing remains a separate authenticated action.
5. Read-only user, revoked grant, cross-project/tenant request, stale revision, duplicate execution and uncertain partial failure are denied/reconciled and audited.
6. Local inference does not start in the public read-only preview unless the private authenticated configuration explicitly permits it.
7. ConstructionPM CI, Web CI, PostgreSQL Integration, Client Typecheck and applicable browser/E2E tests pass on the exact tested SHA.

Do not treat a model adapter, passing unit test, documentation or open PR as proof of the complete production assistant.
