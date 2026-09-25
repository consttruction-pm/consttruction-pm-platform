import assert from "node:assert/strict";
import test from "node:test";

import { InMemoryOfflineModelArtifactStore } from "./offline-ai-model-artifact-store.ts";

test("stores verified model artifacts as local binary data", async () => {
  const store = new InMemoryOfflineModelArtifactStore();
  const source = new Uint8Array([1, 2, 3]);

  await store.put({
    packageId: "construction-pm.ai.fa",
    languageTag: "fa",
    modelType: "ai_text",
    version: "1.0.0",
    artifact: source,
    verified: true,
  });

  source[0] = 9;
  const loaded = await store.get("construction-pm.ai.fa", "1.0.0");
  assert.deepEqual([...loaded!.artifact], [1, 2, 3]);
});

test("rejects unverified artifacts", async () => {
  const store = new InMemoryOfflineModelArtifactStore();
  await assert.rejects(
    store.put({
      packageId: "construction-pm.ai.fa",
      languageTag: "fa",
      modelType: "ai_text",
      version: "1.0.0",
      artifact: new Uint8Array([1]),
      verified: false,
    }),
    /UNVERIFIED_OFFLINE_MODEL_ARTIFACT/,
  );
});
