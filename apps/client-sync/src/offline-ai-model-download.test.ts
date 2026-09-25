import assert from "node:assert/strict";
import test from "node:test";

import { InMemoryOfflineModelStore } from "./offline-ai-model-store.ts";
import { OfflineModelDownloadService } from "./offline-ai-model-download.ts";

const model = {
  packageId: "construction-pm.ai.fa",
  languageTag: "fa",
  modelType: "ai_text" as const,
  version: "1.0.0",
  minAppVersion: "0.1.0",
  maxAppVersion: null,
  sizeBytes: 3,
  checksum: "sha256:test",
  signature: "sig",
  offline: true,
  minRamMb: 1024,
  minStorageMb: 100,
  verified: false,
};

test("downloads verifies and installs an offline AI model", async () => {
  const store = new InMemoryOfflineModelStore();
  const phases: string[] = [];

  const service = new OfflineModelDownloadService(
    {
      async download(_uri, onChunk) {
        const data = new Uint8Array([1, 2, 3]);
        onChunk?.(data);
        return data;
      },
    },
    {
      async verify(artifact) {
        return artifact.length === 3;
      },
    },
    store,
  );

  await service.downloadAndInstall(
    { model, downloadUri: "https://example.invalid/model.bin" },
    (progress) => phases.push(progress.phase),
  );

  assert.deepEqual(phases, ["downloading", "downloading", "verifying", "installed"]);
  assert.equal((await store.list())[0]?.verified, true);
});

test("rejects an unverified model download", async () => {
  const service = new OfflineModelDownloadService(
    {
      async download() {
        return new Uint8Array([1]);
      },
    },
    {
      async verify() {
        return false;
      },
    },
    new InMemoryOfflineModelStore(),
  );

  await assert.rejects(
    service.downloadAndInstall(
      { model: { ...model, sizeBytes: 1 }, downloadUri: "https://example.invalid/model.bin" },
    ),
    /OFFLINE_MODEL_VERIFICATION_FAILED/,
  );
});
