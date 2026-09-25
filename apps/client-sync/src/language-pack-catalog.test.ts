import assert from "node:assert/strict";
import test from "node:test";

import { selectCompatiblePack, type LanguagePackCatalog } from "./language-pack-catalog.ts";

const catalog: LanguagePackCatalog = {
  schemaVersion: "1.0",
  generatedAt: "2026-09-25T00:00:00Z",
  defaultLanguage: "en",
  items: [
    {
      packageId: "construction-pm.language.fa",
      languageTag: "fa",
      version: "1.0.0",
      minAppVersion: "0.1.0",
      maxAppVersion: null,
      compressedSizeBytes: 100,
      downloadUri: "https://example.invalid/fa-1.zip",
      checksum: "sha256:a",
      signature: "s1",
      capabilities: {
        ui: true,
        help: true,
        aiText: true,
        voiceInput: true,
        voiceOutput: true,
        offlineAi: false,
      },
    },
    {
      packageId: "construction-pm.language.fa",
      languageTag: "fa",
      version: "1.1.0",
      minAppVersion: "0.2.0",
      maxAppVersion: null,
      compressedSizeBytes: 110,
      downloadUri: "https://example.invalid/fa-1-1.zip",
      checksum: "sha256:b",
      signature: "s2",
      capabilities: {
        ui: true,
        help: true,
        aiText: true,
        voiceInput: true,
        voiceOutput: true,
        offlineAi: true,
      },
    },
  ],
};

test("selects newest compatible language pack", () => {
  assert.equal(
    selectCompatiblePack(catalog, "fa", "0.2.0")?.version,
    "1.1.0",
  );
});

test("selects older compatible pack for older app versions", () => {
  assert.equal(
    selectCompatiblePack(catalog, "fa", "0.1.5")?.version,
    "1.0.0",
  );
});

test("returns null for unsupported language", () => {
  assert.equal(selectCompatiblePack(catalog, "de", "0.2.0"), null);
});
