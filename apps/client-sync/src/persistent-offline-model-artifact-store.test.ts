import assert from "node:assert/strict";
import test from "node:test";

import {
  PersistentOfflineModelArtifactStore,
  type PersistentOfflineModelArtifactBackend,
} from "./persistent-offline-model-artifact-store.ts";

class Backend implements PersistentOfflineModelArtifactBackend {
  private value: Uint8Array | null = null;

  async get() {
    return this.value
      ? {
          packageId: "construction-pm.ai.fa",
          languageTag: "fa",
          modelType: "ai_text" as const,
          version: "1.0.0",
          artifact: new Uint8Array(this.value),
          verified: true,
        }
      : null;
  }

  async put(model: Parameters<PersistentOfflineModelArtifactBackend["put"]>[0]) {
    this.value = new Uint8Array(model.artifact);
  }

  async remove() {
    this.value = null;
  }
}

test("persists and clones a verified model artifact", async () => {
  const backend = new Backend();
  const store = new PersistentOfflineModelArtifactStore(backend);

  await store.put({
    packageId: "construction-pm.ai.fa",
    languageTag: "fa",
    modelType: "ai_text",
    version: "1.0.0",
    artifact: new Uint8Array([1, 2]),
    verified: true,
  });

  const loaded = await store.get("construction-pm.ai.fa", "1.0.0");
  loaded!.artifact[0] = 9;

  const reread = await store.get("construction-pm.ai.fa", "1.0.0");
  assert.deepEqual([...reread!.artifact], [1, 2]);
});

test("rejects empty model artifacts", async () => {
  const store = new PersistentOfflineModelArtifactStore(new Backend());
  await assert.rejects(
    store.put({
      packageId: "construction-pm.ai.fa",
      languageTag: "fa",
      modelType: "ai_text",
      version: "1.0.0",
      artifact: new Uint8Array(),
      verified: true,
    }),
    /EMPTY_OFFLINE_MODEL_ARTIFACT/,
  );
});
