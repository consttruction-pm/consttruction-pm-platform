# AI Workbench conversation on the canonical assistant — 2026-11-21

## What changed

The command panel previously only called `POST .../workbench/command`, the
deterministic keyword router. It now asks the canonical assistant endpoint
first, through the same `AIActionClient` the workspace chat uses:

| Layer | File | Contract |
| --- | --- | --- |
| Client | `apps/web/src/workbench/api.ts` | `assistantTurn()` delegates to `AIActionClient.sendAssistantTurn` |
| View | `apps/web/src/workbench/render.ts` | `renderAssistantTranscript()` renders server messages only |
| Wiring | `apps/web/src/workbench/mount.ts` | assistant turn → transcript; provider-unavailable → planner |
| Fallback rule | `apps/web/src/workbench/model.ts` | `assistantUnavailable()` accepts only provider/config codes |
| Styles | `apps/web/ai-workbench.css` | `.aiw-transcript`, `.aiw-chat-*` |

No new HTTP route, no new prompt format, no client-side proposal creation and no
approval control in the transcript. An `action_proposal` turn links to Decision
& Approval, where the existing revision-guarded decision and execution routes
remain the only way to act.

## Why a fallback exists

`POST /api/projects/{id}/ai/assistant/turn` returns `503
AI_ASSISTANT_NOT_CONFIGURED` when the runtime has no orchestrator or provider.
That is a deployment state, not a user error. The Workbench then says so in the
transcript and routes the same sentence through the read-only deterministic
planner, so studios stay reachable. The browser test reads the response body and
tolerates exactly `503` + `AI_ASSISTANT_NOT_CONFIGURED` on that route; any other
5xx still fails the run.

## Verification

- `npx tsx --test src/workbench-model.test.ts src/workbench-render.test.ts` — 39 passed
- `npm test` — 1296 + 16 passed
- `npm run typecheck`, `npm run build` — clean
- `CUBI_CHROME_NO_SANDBOX=1 npm run test:e2e:preview` — 116 recorded checks:
  - `assistant turn is attempted first and degrades to the command planner`
    (`user: "Show project risks"`, fallback notice recorded, `messages: 1`,
    `controls: 0`)
  - `no uncaught browser exceptions or unexpected API 5xx responses`
    (`assistant_not_configured_503: 1`)

## Not claimed

No provider was configured, so no free-form answer and no model-generated
proposal were exercised here. That path still needs a deployment with a
configured provider; the transcript has no local substitute for it.
