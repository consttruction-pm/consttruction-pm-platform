import assert from "node:assert/strict";
import test from "node:test";

import { InMemoryOfflineModelStore } from "./offline-ai-model-store.ts";
import { OfflineAIModelRuntime } from "./offline-ai-model-runtime.ts";
import { InMemoryLanguagePackStore } from "./language-pack-store.ts";
import { ClientLanguageRuntime } from "./language-runtime.ts";
import { LanguageBoundAIService } from "./language-bound-ai-service.ts";
import { MultilingualCapabilityCoordinator } from "./multilingual-capability-coordinator.ts";

test("changing preferred language updates AI capability routing together", async () => {
  const languageRuntime = new ClientLanguageRuntime(new InMemoryLanguagePackStore());
  languageRuntime.configure(
    [
      {
        languageTag: "en",
        direction: "ltr",
        locale: "en-US",
        fallbackChain: [],
        capabilities: {
          ui: true, help: true, aiText: true,
          voiceInput: true, voiceOutput: true, offlineAi: false,
        },
      },
      {
        languageTag: "fa",
        direction: "rtl",
        locale: "fa-IR",
        fallbackChain: ["en"],
        capabilities: {
          ui: true, help: true, aiText: true,
          voiceInput: true, voiceOutput: true, offlineAi: false,
        },
      },
    ],
    "en",
    {
      preferredLanguage: "en",
      fallbackChain: ["fa"],
      installedPacks: [],
    },
  );

  const modelStore = new InMemoryOfflineModelStore();
  await modelStore.put({
    packageId: "construction-pm.ai.fa",
    languageTag: "fa",
    modelType: "ai_text",
    version: "1.0.0",
    minAppVersion: "0.1.0",
    maxAppVersion: null,
    sizeBytes: 1,
    checksum: "sha256:x",
    signature: "sig",
    offline: true,
    minRamMb: 1,
    minStorageMb: 1,
    verified: true,
  });

  const ai = new LanguageBoundAIService(
    modelStore,
    { async complete() { return "local"; } },
    { async complete() { return "online"; } },
    "en",
  );

  const offline = new OfflineAIModelRuntime(modelStore, "en");
  const coordinator = new MultilingualCapabilityCoordinator(
    languageRuntime,
    offline,
    ai,
  );

  const state = await coordinator.setLanguage(
    "fa",
    "0.2.0",
    { ramMb: 1024, storageFreeMb: 100, offlineAiAllowed: true },
  );

  assert.equal(state.language, "fa");
  assert.equal(state.offlineModels.aiText?.languageTag, "fa");
  assert.equal(await ai.decide("0.2.0", {
    ramMb: 1024,
    storageFreeMb: 100,
    offlineAiAllowed: true,
  }).then((result) => result.mode), "offline");
});
