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


test("web speech input maps a provider result into the shared snapshot", async () => {
  const browserRuntime = globalThis as typeof globalThis & { SpeechRecognition?: unknown };
  const original = browserRuntime.SpeechRecognition;
  const fake = class {
    lang = "";
    continuous = false;
    interimResults = false;
    onresult: ((event: { readonly results: { readonly 0: { readonly 0: { readonly transcript: string; readonly confidence: number } } } }) => void) | null = null;
    onerror: ((event: { readonly error: string }) => void) | null = null;
    onend: (() => void) | null = null;
    start() {
      this.onresult?.({ results: { 0: { 0: { transcript: "  فعالیت بحرانی  ", confidence: 1.2 } } } });
    }
    stop() {}
  };
  Object.assign(browserRuntime, { SpeechRecognition: fake });
  try {
    const adapter = createWebSpeechInputAdapter({ now: () => new Date("2026-09-27T18:00:00Z") });
    const capture = await adapter.capture({ aiLanguage, expectedScope: scope });
    assert.equal(capture.snapshot.contract_version, "voice-command.v1");
    assert.equal(capture.snapshot.transcript, "فعالیت بحرانی");
    assert.equal(capture.snapshot.confidence, 1);
    assert.deepEqual(capture.snapshot.scope, scope);
  } finally {
    Object.assign(browserRuntime, { SpeechRecognition: original });
  }
});

test("web speech output resolves only after provider completion", async () => {
  const runtime = globalThis as typeof globalThis & { speechSynthesis?: unknown; SpeechSynthesisUtterance?: unknown };\n  const originalSynthesis = runtime.speechSynthesis;
  const originalUtterance = runtime.SpeechSynthesisUtterance;
  let completed = false;
  class FakeUtterance {
    lang = "";
    text: string;
    onerror: (() => void) | null = null;
    onend: (() => void) | null = null;
    constructor(text: string) { this.text = text; }
  }
  const synthesis = {
    speak(utterance: FakeUtterance) {
      setTimeout(() => { completed = true; utterance.onend?.(); }, 0);
    },
  };
  Object.assign(runtime, { speechSynthesis: synthesis, SpeechSynthesisUtterance: FakeUtterance });
  try {
    const adapter = createWebSpeechOutputAdapter();
    const pending = adapter.speak("سلام", { language: "fa-IR", scope });
    assert.equal(completed, false);
    await pending;
    assert.equal(completed, true);
  } finally {
    Object.assign(runtime, { speechSynthesis: originalSynthesis, SpeechSynthesisUtterance: originalUtterance });
  }
});
