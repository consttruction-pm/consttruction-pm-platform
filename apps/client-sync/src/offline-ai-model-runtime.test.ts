import assert from "node:assert/strict";
import test from "node:test";

import { InMemoryOfflineModelStore } from "./offline-ai-model-store.ts";
import { OfflineAIModelRuntime } from "./offline-ai-model-runtime.ts";

test("preferred language drives offline AI model selection", async () => {
  const store = new InMemoryOfflineModelStore();
  const runtime = new OfflineAIModelRuntime(store, "fa");

  await runtime.installVerifiedModel({
    packageId: "construction-pm.ai.fa",
    languageTag: "fa",
    modelType: "ai_text",
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
  });

  assert.equal(
    (await runtime.select("0.2.0", {
      ramMb: 4096,
      storageFreeMb: 1000,
      offlineAiAllowed: true,
    })).aiText?.languageTag,
    "fa",
  );

  runtime.setPreferredLanguage("en");
  assert.equal(
    (await runtime.select("0.2.0", {
      ramMb: 4096,
      storageFreeMb: 1000,
      offlineAiAllowed: true,
    })).aiText,
    null,
  );
});

test("unverified model cannot be installed", async () => {
  const runtime = new OfflineAIModelRuntime(
    new InMemoryOfflineModelStore(),
    "fa",
  );

  await assert.rejects(
    runtime.installVerifiedModel({
      packageId: "construction-pm.ai.fa",
      languageTag: "fa",
      modelType: "ai_text",
      version: "1.0.0",
      minAppVersion: "0.1.0",
      maxAppVersion: null,
      sizeBytes: 100,
      checksum: "sha256:x",
      signature: "sig",
      offline: true,
      minRamMb: 1024,
      minStorageMb: 100,
      verified: false,
    }),
    /UNVERIFIED_OFFLINE_MODEL/,
  );
});
