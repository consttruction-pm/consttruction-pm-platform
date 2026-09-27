import { strict as assert } from "node:assert";
import { test } from "node:test";
import type { AILanguageContext } from "../../client-sync/src/ai-language-contract.js";
import { voiceCommandToScheduleQuery } from "../../client-sync/src/voice-command.js";
import { createWebVoiceAdapters, normalizeWebVoiceCapture, requireWebVoiceOutput } from "./voice-adapters.js";

const scope = { tenant_id: "tenant-1", project_id: "project-1", project_revision: 7 } as const;
const aiLanguage: AILanguageContext = {
  input_language: "fa-IR",
  output_language: "fa-IR",
  project_language: "fa-IR",
  terminology_profile: "construction-default",
  locale: "fa-IR",
  voice_language: "fa-IR",
  text_capable: true,
  voice_input_capable: true,
  voice_output_capable: true,
  offline_ai_capable: true,
};

function adapters(input = true, output = true) {
  return createWebVoiceAdapters({
    input: {
      capabilities: { input, output: false },
      async capture() {
        return { snapshot: {
          contract_version: "voice-command.v1",
          voice_command_id: "web-1",
          scope,
          requested_by: "u1",
          input_language: "fa-IR",
          transcript: "برنامه را بررسی کن",
          query_kind: "fact",
          captured_at: "2026-09-27T18:00:00Z",
          source: "microphone",
          confidence: 1,
        } };
      },
    },
    output: { capabilities: { input: false, output }, async speak() {} },
  });
}

test("web voice adapter preserves shared command and query contracts", async () => {
  const value = adapters();
  const command = normalizeWebVoiceCapture(value, await value.input.capture({ aiLanguage, expectedScope: scope }), aiLanguage, scope);
  const query = voiceCommandToScheduleQuery(command);
  assert.equal(command.voice_command_id, "web-1");
  assert.equal(query.contract_version, "schedule-query.v1");
  assert.equal(query.query_text, command.transcript);
  assert.deepEqual(query.scope, scope);
  assert.doesNotThrow(() => requireWebVoiceOutput(value, "fa-IR", scope));
});

test("web voice adapter fails closed when provider input is unavailable", async () => {
  const value = adapters(false);
  await assert.rejects(
    async () => normalizeWebVoiceCapture(value, await value.input.capture({ aiLanguage, expectedScope: scope }), aiLanguage, scope),
    /VOICE_INPUT_UNAVAILABLE/,
  );
});

test("web voice adapter propagates shared scope and contract validation", async () => {
  const value = adapters();
  const capture = await value.input.capture({ aiLanguage, expectedScope: scope });
  assert.throws(
    () => normalizeWebVoiceCapture(value, capture, aiLanguage, { ...scope, project_revision: 8 }),
    /VOICE_COMMAND_SCOPE_MISMATCH/,
  );
  assert.throws(
    () => normalizeWebVoiceCapture(value, { snapshot: { ...capture.snapshot, contract_version: "voice-command.v99" as never } }, aiLanguage, scope),
    /UNSUPPORTED_VOICE_COMMAND_CONTRACT/,
  );
});

test("web voice adapter enforces output capability", () => {
  const value = adapters(true, false);
  assert.throws(() => requireWebVoiceOutput(value, "fa-IR", scope), /VOICE_OUTPUT_UNAVAILABLE/);
});
