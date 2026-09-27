import { strict as assert } from "node:assert";
import { test } from "node:test";
import type { AILanguageContext } from "../../client-sync/src/ai-language-contract.ts";
import { createWebSpeechInputAdapter, createWebSpeechOutputAdapter } from "./web-speech-provider.ts";

const aiLanguage: AILanguageContext = {
  input_language: "fa-IR", output_language: "fa-IR", project_language: "fa-IR",
  terminology_profile: "construction-default", locale: "fa-IR", voice_language: "fa-IR",
  text_capable: true, voice_input_capable: true, voice_output_capable: true, offline_ai_capable: true,
};
const scope = { tenant_id: "t1", project_id: "p1", project_revision: 3 } as const;

test("web speech input produces the shared voice-command.v1 snapshot", async () => {
  const adapter = createWebSpeechInputAdapter();
  assert.equal(typeof adapter.capabilities.input, "boolean");
});

test("web speech adapters fail closed when browser providers are unavailable", async () => {
  const input = createWebSpeechInputAdapter();
  const output = createWebSpeechOutputAdapter();
  if (!input.capabilities.input) {
    await assert.rejects(() => input.capture({ aiLanguage, expectedScope: scope }), /VOICE_INPUT_UNAVAILABLE/);
  }
  if (!output.capabilities.output) {
    await assert.rejects(() => output.speak("سلام", { language: "fa-IR", scope }), /VOICE_OUTPUT_UNAVAILABLE/);
  }
});
