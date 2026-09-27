import { strict as assert } from "node:assert";
import { test } from "node:test";
import {
  normalizeVoiceCapture,
  requireVoiceOutput,
  type VoiceInputAdapter,
  type VoiceOutputAdapter,
} from "./voice-provider-adapter.ts";
import type { AILanguageContext } from "./ai-language-contract.ts";

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

const scope = {
  tenant_id: "tenant-1",
  project_id: "project-1",
  project_revision: 7,
} as const;

const snapshot = {
  contract_version: "voice-command.v1" as const,
  voice_command_id: "voice-1",
  scope,
  requested_by: "user-1",
  input_language: "fa-IR",
  transcript: "فعالیت های بحرانی را نشان بده",
  query_kind: "fact" as const,
  captured_at: "2026-09-27T18:00:00Z",
  source: "microphone" as const,
  confidence: 0.98,
};

test("provider capture is normalized only through the shared voice contract", async () => {
  const adapter: VoiceInputAdapter = {
    capabilities: { input: true, output: false },
    async capture() {
      return { snapshot };
    },
  };

  const command = normalizeVoiceCapture(
    await adapter.capture({ aiLanguage, expectedScope: scope }),
    aiLanguage,
    scope,
  );

  assert.equal(command.contract_version, "voice-command.v1");
  assert.equal(command.scope.project_revision, 7);
  assert.equal(command.transcript, snapshot.transcript);
});

test("provider output capability is checked before presentation", () => {
  const adapter: VoiceOutputAdapter = {
    capabilities: { input: false, output: false },
    async speak() {},
  };

  assert.throws(
    () => requireVoiceOutput(adapter, "fa-IR", scope),
    /VOICE_OUTPUT_UNAVAILABLE/,
  );
});

test("provider output requires a valid language and project scope", () => {
  const adapter: VoiceOutputAdapter = {
    capabilities: { input: false, output: true },
    async speak() {},
  };

  assert.doesNotThrow(() => requireVoiceOutput(adapter, "fa-IR", scope));
  assert.throws(
    () => requireVoiceOutput(adapter, "", scope),
    /INVALID_VOICE_OUTPUT_LANGUAGE/,
  );
  assert.throws(
    () =>
      requireVoiceOutput(adapter, "fa-IR", {
        tenant_id: "",
        project_id: scope.project_id,
        project_revision: scope.project_revision,
      }),
    /INVALID_VOICE_OUTPUT_SCOPE/,
  );
});
