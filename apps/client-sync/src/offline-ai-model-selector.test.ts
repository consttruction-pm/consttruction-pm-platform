import assert from "node:assert/strict";
import test from "node:test";

import {
  selectOfflineModels,
  type OfflineModelPack,
} from "./offline-ai-model-selector.ts";

const base = {
  packageId: "construction-pm.ai.fa",
  languageTag: "fa",
  minAppVersion: "0.1.0",
  maxAppVersion: null,
  sizeBytes: 10,
  checksum: "sha256:x",
  signature: "sig",
  offline: true,
  minRamMb: 1024,
  minStorageMb: 100,
  verified: true,
} satisfies Omit<OfflineModelPack, "modelType" | "version">;

test("selects newest compatible offline AI model for preferred language", () => {
  const installed: OfflineModelPack[] = [
    { ...base, modelType: "ai_text", version: "1.0.0" },
    { ...base, modelType: "ai_text", version: "1.2.0" },
    { ...base, modelType: "voice_input", version: "1.1.0" },
    { ...base, modelType: "voice_output", version: "1.1.0" },
  ];

  const selected = selectOfflineModels(
    "fa",
    "0.2.0",
    { ramMb: 4096, storageFreeMb: 1000, offlineAiAllowed: true },
    installed,
  );

  assert.equal(selected.aiText?.version, "1.2.0");
  assert.equal(selected.voiceInput?.version, "1.1.0");
  assert.equal(selected.voiceOutput?.version, "1.1.0");
});

test("does not select unverified or incompatible models", () => {
  const installed: OfflineModelPack[] = [
    { ...base, modelType: "ai_text", version: "2.0.0", verified: false },
    { ...base, modelType: "ai_text", version: "3.0.0", minRamMb: 8192 },
    { ...base, modelType: "ai_text", version: "4.0.0", minAppVersion: "9.0.0" },
  ];

  const selected = selectOfflineModels(
    "fa",
    "0.2.0",
    { ramMb: 4096, storageFreeMb: 1000, offlineAiAllowed: true },
    installed,
  );

  assert.equal(selected.aiText, null);
});

test("voice offline capability can be disabled independently", () => {
  const installed: OfflineModelPack[] = [
    { ...base, modelType: "voice_input", version: "1.0.0" },
    { ...base, modelType: "voice_output", version: "1.0.0" },
  ];

  const selected = selectOfflineModels(
    "fa",
    "0.2.0",
    { ramMb: 4096, storageFreeMb: 1000, offlineAiAllowed: false },
    installed,
  );

  assert.equal(selected.voiceInput, null);
  assert.equal(selected.voiceOutput, null);
});
