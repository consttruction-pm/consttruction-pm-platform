import assert from "node:assert/strict";
import test from "node:test";

import { InMemoryOfflineModelStore } from "./offline-ai-model-store.ts";
import { LanguageBoundAIService } from "./language-bound-ai-service.ts";

const request = {
  input_language: "fa",
  output_language: "fa",
  project_language: "fa",
  terminology_profile: "construction-p6",
  locale: "fa-IR",
  voice_language: null,
  text_capable: true,
  voice_input_capable: false,
  voice_output_capable: false,
  offline_ai_capable: true,
};

const model = {
  packageId: "construction-pm.ai.fa",
  languageTag: "fa",
  modelType: "ai_text" as const,
  version: "1.0.0",
  minAppVersion: "0.1.0",
  maxAppVersion: null,
  sizeBytes: 100,
  checksum: "sha256:x",
  signature: "sig",
  offline: true,
  minRamMb: 1024,
  minStorageMb: 100,
  verified: true,
};

test("uses local AI when a compatible verified preferred-language model exists", async () => {
  const store = new InMemoryOfflineModelStore();
  await store.put(model);

  const service = new LanguageBoundAIService(
    store,
    {
      async complete(_request, modelPackageId) {
        return "local:" + modelPackageId;
      },
    },
    {
      async complete() {
        return "online";
      },
    },
    "fa",
  );

  const result = await service.complete(
    request,
    "0.2.0",
    { ramMb: 4096, storageFreeMb: 1000, offlineAiAllowed: true },
  );

  assert.equal(result.mode, "offline");
  assert.equal(result.text, "local:construction-pm.ai.fa");
});

test("falls back to online AI when offline model is unavailable", async () => {
  const service = new LanguageBoundAIService(
    new InMemoryOfflineModelStore(),
    {
      async complete() {
        return "local";
      },
    },
    {
      async complete() {
        return "online";
      },
    },
    "fa",
  );

  const result = await service.complete(
    request,
    "0.2.0",
    { ramMb: 512, storageFreeMb: 100, offlineAiAllowed: true },
  );

  assert.equal(result.mode, "online");
  assert.equal(result.text, "online");
});

test("offline policy disabled forces online execution", async () => {
  const store = new InMemoryOfflineModelStore();
  await store.put(model);

  const service = new LanguageBoundAIService(
    store,
    {
      async complete() {
        return "local";
      },
    },
    {
      async complete() {
        return "online";
      },
    },
    "fa",
  );

  assert.deepEqual(
    await service.decide("0.2.0", {
      ramMb: 4096,
      storageFreeMb: 1000,
      offlineAiAllowed: false,
    }),
    {
      mode: "online",
      language: "fa",
      modelPackageId: null,
      modelVersion: null,
      reason: "offline_policy_disabled",
    },
  );
});
