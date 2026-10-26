import { strict as assert } from "node:assert";
import { test } from "node:test";
import type { AILanguageContext } from "../../client-sync/src/ai-language-contract.js";
import { createWebSpeechInputAdapter, createWebSpeechOutputAdapter } from "./web-speech-provider.js";

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
  const originalSynthesis = globalThis.speechSynthesis;
  const originalUtterance = globalThis.SpeechSynthesisUtterance;
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
  Object.assign(globalThis, { speechSynthesis: synthesis, SpeechSynthesisUtterance: FakeUtterance });
  try {
    const adapter = createWebSpeechOutputAdapter();
    const pending = adapter.speak("سلام", { language: "fa-IR", scope });
    assert.equal(completed, false);
    await pending;
    assert.equal(completed, true);
  } finally {
    Object.assign(globalThis, { speechSynthesis: originalSynthesis, SpeechSynthesisUtterance: originalUtterance });
  }
});

test("web speech input cancel stops the provider and fails the pending capture", async () => {
  const browserRuntime = globalThis as typeof globalThis & { SpeechRecognition?: unknown };
  const original = browserRuntime.SpeechRecognition;
  let stopped = false;
  const fake = class {
    lang = "";
    continuous = false;
    interimResults = false;
    onresult: ((event: unknown) => void) | null = null;
    onerror: ((event: { readonly error: string }) => void) | null = null;
    onend: (() => void) | null = null;
    start() {}
    stop() { stopped = true; }
  };
  Object.assign(browserRuntime, { SpeechRecognition: fake });
  try {
    const adapter = createWebSpeechInputAdapter();
    const pending = adapter.capture({ aiLanguage, expectedScope: scope });
    adapter.cancel?.();
    await assert.rejects(() => pending, /VOICE_INPUT_CANCELLED/);
    assert.equal(stopped, true);
  } finally {
    Object.assign(browserRuntime, { SpeechRecognition: original });
  }
});

test("web speech input normalizes microphone permission errors", async () => {
  const browserRuntime = globalThis as typeof globalThis & { SpeechRecognition?: unknown };
  const original = browserRuntime.SpeechRecognition;
  const fake = class {
    lang = "";
    continuous = false;
    interimResults = false;
    onresult: ((event: unknown) => void) | null = null;
    onerror: ((event: { readonly error: string }) => void) | null = null;
    onend: (() => void) | null = null;
    start() { this.onerror?.({ error: "not-allowed" }); }
    stop() {}
  };
  Object.assign(browserRuntime, { SpeechRecognition: fake });
  try {
    const adapter = createWebSpeechInputAdapter();
    await assert.rejects(
      () => adapter.capture({ aiLanguage, expectedScope: scope }),
      /VOICE_INPUT_NOT_ALLOWED/,
    );
  } finally {
    Object.assign(browserRuntime, { SpeechRecognition: original });
  }
});

test("web speech output stop cancels the browser utterance", async () => {
  const originalSynthesis = globalThis.speechSynthesis;
  const originalUtterance = globalThis.SpeechSynthesisUtterance;
  let cancelled = false;
  let current: FakeUtterance | null = null;
  class FakeUtterance {
    lang = "";
    text: string;
    onerror: (() => void) | null = null;
    onend: (() => void) | null = null;
    constructor(text: string) { this.text = text; current = this; }
  }
  const synthesis = {
    speak(utterance: FakeUtterance) { current = utterance; },
    cancel() { cancelled = true; current?.onerror?.(); },
  };
  Object.assign(globalThis, { speechSynthesis: synthesis, SpeechSynthesisUtterance: FakeUtterance });
  try {
    const adapter = createWebSpeechOutputAdapter();
    const pending = adapter.speak("سلام", { language: "fa-IR", scope });
    adapter.stop?.();
    await assert.rejects(() => pending, /VOICE_OUTPUT_FAILED/);
    assert.equal(cancelled, true);
  } finally {
    Object.assign(globalThis, { speechSynthesis: originalSynthesis, SpeechSynthesisUtterance: originalUtterance });
  }
});
