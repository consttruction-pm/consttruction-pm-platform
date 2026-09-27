import { strict as assert } from "node:assert";
import { test } from "node:test";
import type { AILanguageContext } from "../../client-sync/src/ai-language-contract.ts";
import { voiceCommandToScheduleQuery } from "../../client-sync/src/voice-command.ts";
import { createMobileVoiceAdapters, normalizeMobileVoiceCapture, requireMobileVoiceOutput } from "./voice-adapters.ts";

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
  return createMobileVoiceAdapters({
    input: {
      capabilities: { input, output: false },
      async capture() {
        return { snapshot: {
          contract_version: "voice-command.v1",
          voice_command_id: "mobile-1",
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

test("mobile voice adapter preserves shared command and query contracts", async () => {
  const value = adapters();
  const command = normalizeMobileVoiceCapture(value, await value.input.capture({ aiLanguage, expectedScope: scope }), aiLanguage, scope);
  const query = voiceCommandToScheduleQuery(command);
  assert.equal(command.voice_command_id, "mobile-1");
  assert.equal(query.contract_version, "schedule-query.v1");
  assert.equal(query.query_text, command.transcript);
  assert.deepEqual(query.scope, scope);
  assert.doesNotThrow(() => requireMobileVoiceOutput(value, "fa-IR", scope));
});

test("mobile voice adapter fails closed when provider input is unavailable", async () => {
  const value = adapters(false);
  await assert.rejects(
    async () => normalizeMobileVoiceCapture(value, await value.input.capture({ aiLanguage, expectedScope: scope }), aiLanguage, scope),
    /VOICE_INPUT_UNAVAILABLE/,
  );
});

test("mobile voice adapter propagates shared scope and contract validation", async () => {
  const value = adapters();
  const capture = await value.input.capture({ aiLanguage, expectedScope: scope });
  assert.throws(
    () => normalizeMobileVoiceCapture(value, capture, aiLanguage, { ...scope, project_revision: 8 }),
    /VOICE_COMMAND_SCOPE_MISMATCH/,
  );
  assert.throws(
    () => normalizeMobileVoiceCapture(value, { snapshot: { ...capture.snapshot, contract_version: "voice-command.v99" as never } }, aiLanguage, scope),
    /UNSUPPORTED_VOICE_COMMAND_CONTRACT/,
  );
});

test("mobile voice adapter enforces output capability", () => {
  const value = adapters(true, false);
  assert.throws(() => requireMobileVoiceOutput(value, "fa-IR", scope), /VOICE_OUTPUT_UNAVAILABLE/);
});
