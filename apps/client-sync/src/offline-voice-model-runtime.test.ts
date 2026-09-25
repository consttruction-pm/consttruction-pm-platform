import assert from "node:assert/strict";
import test from "node:test";

import { InMemoryOfflineModelArtifactStore } from "./offline-ai-model-artifact-store.ts";
import { InMemoryOfflineModelStore } from "./offline-ai-model-store.ts";
import { OfflineAIModelRuntime } from "./offline-ai-model-runtime.ts";
import { OfflineVoiceModelRuntime } from "./offline-voice-model-runtime.ts";

test("prepares both offline voice directions for the preferred language", async () => {
  const metadata = new InMemoryOfflineModelStore();
  const artifacts = new InMemoryOfflineModelArtifactStore();

  const base = {
    languageTag: "fa",
    minAppVersion: "0.1.0",
    maxAppVersion: null,
    sizeBytes: 2,
    checksum: "sha256:x",
    signature: "sig",
    offline: true,
    minRamMb: 1,
    minStorageMb: 1,
    verified: true,
  };

  await metadata.put({
    ...base,
    packageId: "construction-pm.voice-in.fa",
    modelType: "voice_input",
    version: "1.0.0",
  });
  await metadata.put({
    ...base,
    packageId: "construction-pm.voice-out.fa",
    modelType: "voice_output",
    version: "1.0.0",
  });

  await artifacts.put({
    packageId: "construction-pm.voice-in.fa",
    languageTag: "fa",
    modelType: "voice_input",
    version: "1.0.0",
    artifact: new Uint8Array([1, 2]),
    verified: true,
  });
  await artifacts.put({
    packageId: "construction-pm.voice-out.fa",
    languageTag: "fa",
    modelType: "voice_output",
    version: "1.0.0",
    artifact: new Uint8Array([3, 4]),
    verified: true,
  });

  const loaded: string[] = [];
  const voice = new OfflineVoiceModelRuntime(
    new OfflineAIModelRuntime(metadata, "fa"),
    artifacts,
    {
      async loadInput(packageId, artifact) {
        loaded.push("in:" + packageId + ":" + artifact.length);
      },
      async loadOutput(packageId, artifact) {
        loaded.push("out:" + packageId + ":" + artifact.length);
      },
    },
  );

  const prepared = await voice.prepare("0.2.0", {
    ramMb: 2048,
    storageFreeMb: 100,
    offlineAiAllowed: true,
  });

  assert.equal(prepared.inputModelPackageId, "construction-pm.voice-in.fa");
  assert.equal(prepared.outputModelPackageId, "construction-pm.voice-out.fa");
  assert.deepEqual(loaded, [
    "in:construction-pm.voice-in.fa:2",
    "out:construction-pm.voice-out.fa:2",
  ]);
});

test("does not load voice models when offline policy is disabled", async () => {
  const metadata = new InMemoryOfflineModelStore();
  const artifacts = new InMemoryOfflineModelArtifactStore();

  await metadata.put({
    packageId: "construction-pm.voice-in.fa",
    languageTag: "fa",
    modelType: "voice_input",
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
  await artifacts.put({
    packageId: "construction-pm.voice-in.fa",
    languageTag: "fa",
    modelType: "voice_input",
    version: "1.0.0",
    artifact: new Uint8Array([1]),
    verified: true,
  });

  const voice = new OfflineVoiceModelRuntime(
    new OfflineAIModelRuntime(metadata, "fa"),
    artifacts,
    {
      async loadInput() {
        throw new Error("SHOULD_NOT_LOAD");
      },
      async loadOutput() {
        throw new Error("SHOULD_NOT_LOAD");
      },
    },
  );

  const prepared = await voice.prepare("0.2.0", {
    ramMb: 2048,
    storageFreeMb: 100,
    offlineAiAllowed: false,
  });

  assert.deepEqual(prepared, {
    inputModelPackageId: null,
    outputModelPackageId: null,
  });
});
