import assert from "node:assert/strict";
import test from "node:test";

import type { AILanguageContext } from "./ai-language-contract.js";
import { EngineBackedLocalAIProvider, LocalAIEngineRuntime, EngineBackedLocalVoiceRuntime } from "./local-ai-engine-providers.js";
import type { DeviceCapabilityProfile } from "./offline-ai-model-selector.js";

const device: DeviceCapabilityProfile = {
  ramMb: 8192,
  storageFreeMb: 8192,
  offlineAiAllowed: true,
};

const selected = {
  aiText: {
    packageId: "ai.fa.text",
    languageTag: "fa",
    modelType: "ai_text" as const,
    version: "2.0.0",
    minAppVersion: "0.1.0",
    maxAppVersion: null,
    sizeBytes: 10,
    checksum: "sha256:" + "a".repeat(64),
    signature: "sig",
    offline: true,
    minRamMb: 1024,
    minStorageMb: 100,
    verified: true,
  },
  voiceInput: null,
  voiceOutput: null,
};

test("engine-backed local AI provider requires the selected model to be loaded", async () => {
  const engine = {
    async load() {},
    async unload() {},
    isLoaded() { return false; },
    async complete() {
      return { text: "ok", modelPackageId: "ai.fa.text", modelVersion: "2.0.0" };
    },
  };
  const provider = new EngineBackedLocalAIProvider(engine);

  const request: AILanguageContext = {
    text_capable: true,
    language_tag: "fa",
    preferred_language: "fa",
    user_text: "سلام",
  };

  await assert.rejects(
    provider.complete(request, "ai.fa.text"),
    /LOCAL_AI_MODEL_NOT_LOADED/,
  );
});

test("local AI engine runtime loads a verified selected artifact with version provenance", async () => {
  const engine = {
    loaded: [] as string[],
    async load(packageId: string, version: string) {
      this.loaded.push(packageId + "@" + version);
    },
    async unload() {},
    isLoaded() { return true; },
    async complete() {
      return { text: "ok", modelPackageId: "ai.fa.text", modelVersion: "2.0.0" };
    },
  };

  const modelRuntime = {
    async select() { return selected; },
  };
  const artifactStore = {
    async get() {
      return { packageId: "ai.fa.text", version: "2.0.0", verified: true, artifact: new Uint8Array([1, 2]) };
    },
  };

  const runtime = new LocalAIEngineRuntime(
    modelRuntime as never,
    artifactStore as never,
    engine,
  );
  const result = await runtime.prepare("0.1.0", device);
  assert.equal(result.aiText?.version, "2.0.0");
  assert.deepEqual(engine.loaded, ["ai.fa.text@2.0.0"]);
});

test("voice runtime rejects execution until the selected input model is loaded", async () => {
  const voice = {
    async loadInput() {},
    async loadOutput() {},
    async unloadInput() {},
    async unloadOutput() {},
    isInputLoaded() { return false; },
    isOutputLoaded() { return false; },
    async transcribe() { return { text: "x", modelPackageId: "voice.fa.in", modelVersion: "1.0.0" }; },
    async synthesize() { return new Uint8Array([1]); },
  };

  const runtime = new EngineBackedLocalVoiceRuntime(
    { async select() {
      return {
        aiText: null,
        voiceInput: {
          packageId: "voice.fa.in",
          languageTag: "fa",
          modelType: "voice_input",
          version: "1.0.0",
          minAppVersion: "0.1.0",
          maxAppVersion: null,
          sizeBytes: 10,
          checksum: "sha256:" + "a".repeat(64),
          signature: "sig",
          offline: true,
          minRamMb: 1024,
          minStorageMb: 100,
          verified: true,
        },
        voiceOutput: null,
      };
    }} as never,
    { async get() { return { verified: true, artifact: new Uint8Array([1]) }; } } as never,
    voice,
  );

  const selectedModels = await runtime.prepare("0.1.0", device);
  voice.isInputLoaded = () => false;
  await assert.rejects(
    runtime.transcribe({ audio: new Uint8Array([1]), languageTag: "fa" }, selectedModels),
    /LOCAL_VOICE_INPUT_MODEL_NOT_LOADED/,
  );
});
