import assert from "node:assert/strict";
import test from "node:test";

import { InMemoryOfflineModelArtifactStore } from "./offline-ai-model-artifact-store.ts";
import { InMemoryOfflineModelStore } from "./offline-ai-model-store.ts";
import { OfflineAIModelRuntime } from "./offline-ai-model-runtime.ts";
import { LocalAIArtifactRuntime } from "./local-ai-artifact-runtime.ts";

test("prepares the selected local model from its persisted artifact", async () => {
  const metadata = new InMemoryOfflineModelStore();
  const artifacts = new InMemoryOfflineModelArtifactStore();
  await metadata.put({
    packageId: "construction-pm.ai.fa",
    languageTag: "fa",
    modelType: "ai_text",
    version: "1.0.0",
    minAppVersion: "0.1.0",
    maxAppVersion: null,
    sizeBytes: 3,
    checksum: "sha256:x",
    signature: "sig",
    offline: true,
    minRamMb: 1,
    minStorageMb: 1,
    verified: true,
  });
  await artifacts.put({
    packageId: "construction-pm.ai.fa",
    languageTag: "fa",
    modelType: "ai_text",
    version: "1.0.0",
    artifact: new Uint8Array([1, 2, 3]),
    verified: true,
  });

  const runtime = new OfflineAIModelRuntime(metadata, "fa");
  let loadedId = "";
  const loader = new LocalAIArtifactRuntime(
    artifacts,
    runtime,
    {
      async load(packageId, artifact) {
        loadedId = packageId + ":" + artifact.length;
      },
    },
  );

  assert.equal(
    await loader.prepareTextModel("0.2.0", {
      ramMb: 1024,
      storageFreeMb: 100,
      offlineAiAllowed: true,
    }),
    "construction-pm.ai.fa",
  );
  assert.equal(loadedId, "construction-pm.ai.fa:3");
});

test("does not prepare a model when its artifact is missing", async () => {
  const metadata = new InMemoryOfflineModelStore();
  await metadata.put({
    packageId: "construction-pm.ai.fa",
    languageTag: "fa",
    modelType: "ai_text",
    version: "1.0.0",
    minAppVersion: "0.1.0",
    maxAppVersion: null,
    sizeBytes: 3,
    checksum: "sha256:x",
    signature: "sig",
    offline: true,
    minRamMb: 1,
    minStorageMb: 1,
    verified: true,
  });

  const loader = new LocalAIArtifactRuntime(
    new InMemoryOfflineModelArtifactStore(),
    new OfflineAIModelRuntime(metadata, "fa"),
    { async load() {} },
  );

  assert.equal(
    await loader.prepareTextModel("0.2.0", {
      ramMb: 1024,
      storageFreeMb: 100,
      offlineAiAllowed: true,
    }),
    null,
  );
});
