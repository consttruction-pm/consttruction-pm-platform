import assert from "node:assert/strict";
import test from "node:test";

import {
  requireOfflineAi,
  requireTextOutput,
  requireVoiceInput,
  requireVoiceOutput,
  type AILanguageContext,
} from "./ai-language-contract.ts";

const context: AILanguageContext = {
  input_language: "fa-IR",
  output_language: "fa-IR",
  project_language: "fa-IR",
  terminology_profile: "construction",
  locale: "fa-IR",
  voice_language: "fa-IR",
  text_capable: true,
  voice_input_capable: true,
  voice_output_capable: true,
  offline_ai_capable: true,
};

test("AI language capability guards accept configured capabilities", () => {
  assert.doesNotThrow(() => requireTextOutput(context));
  assert.doesNotThrow(() => requireVoiceInput(context));
  assert.doesNotThrow(() => requireVoiceOutput(context));
  assert.doesNotThrow(() => requireOfflineAi(context));
});

test("voice input/output guards fail closed", () => {
  assert.throws(
    () => requireVoiceInput({ ...context, voice_input_capable: false }),
    /AI_VOICE_INPUT_UNAVAILABLE/,
  );
  assert.throws(
    () => requireVoiceOutput({ ...context, voice_output_capable: false }),
    /AI_VOICE_OUTPUT_UNAVAILABLE/,
  );
  assert.throws(
    () => requireOfflineAi({ ...context, offline_ai_capable: false }),
    /AI_OFFLINE_UNAVAILABLE/,
  );
});

test("text guard remains independent from voice capability", () => {
  assert.throws(
    () => requireTextOutput({ ...context, text_capable: false }),
    /AI_TEXT_OUTPUT_UNAVAILABLE/,
  );
});
