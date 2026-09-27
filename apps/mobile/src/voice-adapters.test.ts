import { strict as assert } from "node:assert";
import { test } from "node:test";
import { createMobileVoiceAdapters, normalizeMobileVoiceCapture, requireMobileVoiceOutput } from "./voice-adapters.ts";

const scope = { tenant_id: "tenant-1", project_id: "project-1", project_revision: 7 } as const;
const aiLanguage = {
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

test("mobile voice adapter uses shared normalization boundary", async () => {
  const adapters = createMobileVoiceAdapters({
    input: {
      capabilities: { input: true, output: false },
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
    output: { capabilities: { input: false, output: true }, async speak() {} },
  });

  const command = normalizeMobileVoiceCapture(
    adapters,
    await adapters.input.capture({ aiLanguage, expectedScope: scope }),
    aiLanguage,
    scope,
  );

  assert.equal(command.voice_command_id, "mobile-1");
  assert.equal(command.scope.project_revision, 7);
  assert.doesNotThrow(() => requireMobileVoiceOutput(adapters, "fa-IR", scope));
});
