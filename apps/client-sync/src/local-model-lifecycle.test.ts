import assert from "node:assert/strict";
import test from "node:test";

import { LocalTextModelLifecycleManager } from "./local-model-lifecycle.js";

const model = {
  packageId: "ai.fa.text",
  languageTag: "fa",
  modelType: "ai_text" as const,
  version: "2.0.0",
  minAppVersion: "0.1.0",
  maxAppVersion: null,
  sizeBytes: 60,
  checksum: "sha256:" + "a".repeat(64),
  signature: "sig",
  offline: true,
  minRamMb: 1024,
  minStorageMb: 100,
  verified: true,
};

const modelV1 = { ...model, version: "1.0.0", sizeBytes: 40 };

const device = {
  ramMb: 8192,
  storageFreeMb: 8192,
  offlineAiAllowed: true,
};

test("local model lifecycle loads the selected model and exposes active provenance", async () => {
  const loaded: string[] = [];
  const unloaded: string[] = [];
  const engine = {
    async load(packageId: string, version: string) {
      loaded.push(packageId + "@" + version);
    },
    async unload(packageId: string, version: string) {
      unloaded.push(packageId + "@" + version);
    },
    isLoaded: () => true,
    async complete() {
      return { text: "ok", modelPackageId: "ai.fa.text", modelVersion: "2.0.0" };
    },
  };

  const manager = new LocalTextModelLifecycleManager(
    { async select() { return { aiText: model, voiceInput: null, voiceOutput: null }; } } as never,
    { async get() { return { ...model, artifact: new Uint8Array([1]), verified: true }; } } as never,
    engine,
    { maxLoadedModelBytes: 100, maxConcurrentModels: 2 },
  );

  const state = await manager.prepare("0.1.0", device);
  assert.equal(state.activePackageId, "ai.fa.text");
  assert.equal(state.activeVersion, "2.0.0");
  assert.deepEqual(loaded, ["ai.fa.text@2.0.0"]);
  assert.deepEqual(unloaded, []);
});

test("local model lifecycle evicts the least-recently-used inactive model before loading a third model", async () => {
  const unloaded: string[] = [];
  const engine = {
    async load() {},
    async unload(packageId: string, version: string) {
      unloaded.push(packageId + "@" + version);
    },
    isLoaded: () => true,
    async complete() {
      return { text: "ok", modelPackageId: "x", modelVersion: "1.0.0" };
    },
  };

  const models = [
    modelV1,
    { ...model, packageId: "ai.en.text", languageTag: "en", version: "1.0.0", sizeBytes: 50 },
    { ...model, packageId: "ai.de.text", languageTag: "de", version: "1.0.0", sizeBytes: 30 },
  ];
  let selectedIndex = 0;

  const manager = new LocalTextModelLifecycleManager(
    {
      async select() {
        return {
          aiText: models[selectedIndex]!,
          voiceInput: null,
          voiceOutput: null,
        };
      },
    } as never,
    {
      async get(packageId: string, version: string) {
        const selectedModel = models.find(
          (item) => item.packageId === packageId && item.version === version,
        ) ?? model;
        return {
          ...selectedModel,
          artifact: new Uint8Array([1]),
          verified: true,
        };
      },
    } as never,
    engine,
    { maxLoadedModelBytes: 100, maxConcurrentModels: 3 },
    () => 1,
  );

  await manager.prepare("0.1.0", device);
  selectedIndex = 1;
  await manager.prepare("0.1.0", device);
  selectedIndex = 2;
  await manager.prepare("0.1.0", device);

  assert.deepEqual(unloaded, ["ai.fa.text@1.0.0"]);
  assert.equal(manager.snapshot().activePackageId, "ai.de.text");
});

test("local model lifecycle preserves active model if replacement cannot be loaded", async () => {
  let selected = modelV1;
  const engine = {
    async load(_packageId: string, version: string) {
      if (version === "2.0.0") {
        throw new Error("ENGINE_LOAD_FAILED");
      }
    },
    async unload() {},
    isLoaded: () => true,
    async complete() {
      return { text: "ok", modelPackageId: "x", modelVersion: "1.0.0" };
    },
  };

  const manager = new LocalTextModelLifecycleManager(
    {
      async select() {
        return { aiText: selected, voiceInput: null, voiceOutput: null };
      },
    } as never,
    {
      async get(_packageId: string, version: string) {
        return {
          ...(version === "2.0.0" ? model : modelV1),
          artifact: new Uint8Array([1]),
          verified: true,
        };
      },
    } as never,
    engine,
    { maxLoadedModelBytes: 100, maxConcurrentModels: 2 },
  );

  await manager.prepare("0.1.0", device);
  assert.equal(manager.snapshot().activeVersion, "1.0.0");

  selected = model;
  await assert.rejects(
    manager.prepare("0.1.0", device),
    /ENGINE_LOAD_FAILED/,
  );

  assert.equal(manager.snapshot().activePackageId, "ai.fa.text");
  assert.equal(manager.snapshot().activeVersion, "1.0.0");
});
