import assert from "node:assert/strict";
import test from "node:test";

import { InMemoryLanguagePackStore } from "./language-pack-store.ts";
import { LanguageManagerViewModel } from "./language-manager-view-model.ts";

test("view model exposes language catalog and download state", async () => {
  const store = new InMemoryLanguagePackStore();
  const capabilities = {
    ui: true,
    help: true,
    aiText: true,
    voiceInput: true,
    voiceOutput: true,
    offlineAi: false,
  };
  const vm = new LanguageManagerViewModel(
    [
      {
        languageTag: "en",
        direction: "ltr",
        locale: "en-US",
        fallbackChain: [],
        capabilities,
      },
      {
        languageTag: "fa",
        direction: "rtl",
        locale: "fa-IR",
        fallbackChain: ["en"],
        capabilities,
      },
    ],
    store,
    "en",
  );

  const before = await vm.refresh();
  assert.equal(before.items.find((item) => item.languageTag === "fa")?.offlineReady, false);

  const selected = vm.select("fa");
  assert.equal(selected.selectedLanguage, "fa");

  await vm.download(
    {
      packageId: "construction-pm.language.fa",
      languageTag: "fa",
      version: "1.0.0",
      minAppVersion: "0.1.0",
      maxAppVersion: null,
      compressedSizeBytes: 2,
      downloadUri: "https://example.invalid/fa.zip",
      checksum: "sha256:test",
      signature: "sig",
    },
    {
      async download(_uri, onChunk) {
        const data = new Uint8Array([1, 2]);
        onChunk?.(data);
        return data;
      },
    },
    {
      async verify(artifact) {
        return artifact.length === 2;
      },
    },
  );

  const after = vm.snapshot();
  const fa = after.items.find((item) => item.languageTag === "fa");
  assert.equal(fa?.installedVersion, "1.0.0");
  assert.equal(fa?.offlineReady, true);
  assert.equal(after.downloading, null);
});

test("view model rejects unknown language selection", () => {
  const vm = new LanguageManagerViewModel([], new InMemoryLanguagePackStore(), "en");
  assert.throws(() => vm.select("xx"), /UNSUPPORTED_LANGUAGE/);
});
