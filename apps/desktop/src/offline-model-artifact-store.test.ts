import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import { DesktopFileOfflineModelArtifactStore } from "./offline-model-artifact-store.js";

test("desktop persists and reloads verified offline model artifact bytes", async () => {
  const directory = await mkdtemp(join(tmpdir(), "construction-pm-ai-"));
  try {
    const store = new DesktopFileOfflineModelArtifactStore(directory);
    const model = {
      packageId: "construction-pm.ai.fa",
      languageTag: "fa",
      modelType: "ai_text" as const,
      version: "1.0.0",
      verified: true,
      artifact: new Uint8Array([1, 2, 3, 255]),
    };

    await store.put(model);
    const loaded = await store.get(model.packageId, model.version);
    assert.equal(loaded?.verified, true);
    assert.deepEqual([...loaded!.artifact], [1, 2, 3, 255]);

    await store.remove(model.packageId, model.version);
    assert.equal(await store.get(model.packageId, model.version), null);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});
