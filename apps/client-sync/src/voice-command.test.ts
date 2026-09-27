import assert from "node:assert/strict";
import test from "node:test";

import {
  normalizeVoiceCommand,
  voiceCommandToScheduleQuery,
  VOICE_COMMAND_VERSION,
} from "./voice-command.ts";
import type { AILanguageContext } from "./ai-language-contract.ts";

const scope = {
  tenant_id: "tenant-1",
  project_id: "project-1",
  project_revision: 7,
};

const capable: AILanguageContext = {
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

function snapshot() {
  return {
    contract_version: VOICE_COMMAND_VERSION,
    voice_command_id: "voice-1",
    scope,
    requested_by: "planner-1",
    input_language: "fa-IR",
    transcript: "کدام فعالیت های بحرانی با تاخیر مواجه هستند؟",
    query_kind: "fact" as const,
    captured_at: "2026-09-27T09:00:00+04:00",
    source: "microphone" as const,
    confidence: 0.94,
    provenance: { asr_model: "reference-asr", model_version: "1.0" },
  };
}

test("voice command normalizes with capability and authoritative scope", () => {
  const command = normalizeVoiceCommand(snapshot(), capable, scope);

  assert.equal(command.voice_command_id, "voice-1");
  assert.equal(command.transcript, snapshot().transcript);
  assert.equal(command.confidence, 0.94);
  assert.equal(command.scope.project_revision, 7);
});

test("voice command converts deterministically into schedule-query.v1", () => {
  const command = normalizeVoiceCommand(snapshot(), capable, scope);
  const query = voiceCommandToScheduleQuery(command);

  assert.equal(query.contract_version, "schedule-query.v1");
  assert.equal(query.query_id, "voice-1");
  assert.equal(query.query_text, command.transcript);
  assert.equal(query.kind, "fact");
  assert.equal(query.language, "fa-IR");
  assert.deepEqual(query.scope, scope);
});

test("voice command fails closed when voice input is unavailable", () => {
  assert.throws(
    () =>
      normalizeVoiceCommand(
        snapshot(),
        { ...capable, voice_input_capable: false },
        scope,
      ),
    /AI_VOICE_INPUT_UNAVAILABLE/,
  );
});

test("voice command rejects scope mismatch and invalid confidence", () => {
  assert.throws(
    () =>
      normalizeVoiceCommand(
        snapshot(),
        capable,
        { ...scope, project_revision: 6 },
      ),
    /VOICE_COMMAND_SCOPE_MISMATCH/,
  );

  assert.throws(
    () =>
      normalizeVoiceCommand(
        { ...snapshot(), confidence: 1.1 },
        capable,
        scope,
      ),
    /INVALID_VOICE_COMMAND_CONFIDENCE/,
  );
});

test("voice command rejects unsupported timestamp and contract version", () => {
  assert.throws(
    () =>
      normalizeVoiceCommand(
        { ...snapshot(), captured_at: "2026-09-27T09:00:00" },
        capable,
        scope,
      ),
    /INVALID_VOICE_COMMAND_TIMESTAMP/,
  );

  assert.throws(
    () =>
      normalizeVoiceCommand(
        { ...snapshot(), contract_version: "voice-command.v99" as never },
        capable,
        scope,
      ),
    /UNSUPPORTED_VOICE_COMMAND_CONTRACT/,
  );
});
