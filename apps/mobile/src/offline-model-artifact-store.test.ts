import assert from "node:assert/strict";
import test from "node:test";

import { MobileBinaryOfflineModelArtifactStore } from "./offline-model-artifact-store.js";

class MemoryBinaryStorage {
  readonly values = new Map<string, Uint8Array>();
  async get(key: string) { return this.values.get(key) ? new Uint8Array(this.values.get(key)!) : null; }
  async set(key: string, value: Uint8Array) { this.values.set(key, new Uint8Array(value)); }
  async remove(key: string) { this.values.delete(key); }
}

class MemoryMetadataStorage {
  readonly values = new Map<string, string>();
  async get(key: string) { return this.values.get(key) ?? null; }
  async set(key: string, value: string) { this.values.set(key, value); }
  async remove(key: string) { this.values.delete(key); }
}

test("mobile binary artifact store separates model bytes from metadata", async () => {
  const binaries = new MemoryBinaryStorage();
  const metadata = new MemoryMetadataStorage();
  const store = new MobileBinaryOfflineModelArtifactStore(binaries, metadata);
  const model = {
    packageId: "construction-pm.ai.fa",
    languageTag: "fa",
    modelType: "ai_text" as const,
    version: "1.0.0",
    verified: true,
    artifact: new Uint8Array([5, 6, 7]),
  };

  await store.put(model);
  const loaded = await store.get(model.packageId, model.version);
  assert.equal(loaded?.languageTag, "fa");
  assert.deepEqual([...loaded!.artifact], [5, 6, 7]);

  await store.remove(model.packageId, model.version);
  assert.equal(await store.get(model.packageId, model.version), null);
  assert.equal(binaries.values.size, 0);
  assert.equal(metadata.values.size, 0);
});
