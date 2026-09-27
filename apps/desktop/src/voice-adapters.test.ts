import assert from "node:assert/strict";
import test from "node:test";
import { createDesktopVoiceAdapters, normalizeDesktopVoiceCapture, requireDesktopVoiceOutput } from "./voice-adapters.ts";
import type { AILanguageContext } from "../../client-sync/src/ai-language-contract.ts";

const scope = { tenant_id: "tenant-1", project_id: "project-1", project_revision: 7 } as const;
const aiLanguage: AILanguageContext = {
  language_tag: "fa-IR",
  capabilities: { voice_input: true, voice_output: true, offline_ai: true },
};

function adapters(input = true, output = true) {
  return createDesktopVoiceAdapters({
    input: {
      capabilities: { input, output: false },
      async capture() {
        return {
          snapshot: {
            contract_version: "voice-command.v1",
            voice_command_id: "desktop-1",
            scope,
            requested_by: "u1",
            input_language: "fa-IR",
            transcript: "برنامه را بررسی کن",
            query_kind: "fact",
            captured_at: "2026-09-27T18:00:00Z",
            source: "microphone",
            confidence: 1,
          },
        };
      },
    },
    output: {
      capabilities: { input: false, output },
      async speak() {},
    },
  });
}

test("Desktop voice adapter uses shared normalization boundary", async () => {
  const value = adapters();
  const command = normalizeDesktopVoiceCapture(
    value,
    await value.input.capture({ aiLanguage, expectedScope: scope }),
    aiLanguage,
    scope,
  );
  assert.equal(command.voice_command_id, "desktop-1");
  assert.equal(command.transcript, "برنامه را بررسی کن");
  assert.doesNotThrow(() => requireDesktopVoiceOutput(value, "fa-IR", scope));
});

test("Desktop voice adapter fails closed when input or output capability is unavailable", async () => {
  const noInput = adapters(false, true);
  await assert.rejects(
    noInput.input.capture({ aiLanguage, expectedScope: scope }).then((capture) =>
      normalizeDesktopVoiceCapture(noInput, capture, aiLanguage, scope),
    ),
    /VOICE_INPUT_UNAVAILABLE/,
  );
  assert.throws(() => requireDesktopVoiceOutput(adapters(true, false), "fa-IR", scope), /VOICE_OUTPUT_UNAVAILABLE/);
});

test("Desktop voice adapter preserves shared scope validation", async () => {
  const value = adapters();
  const capture = await value.input.capture({ aiLanguage, expectedScope: scope });
  await assert.rejects(async () => normalizeDesktopVoiceCapture(
    value,
    capture,
    aiLanguage,
    { ...scope, project_id: "other-project" },
  ), /VOICE_COMMAND_SCOPE_MISMATCH/);
});
