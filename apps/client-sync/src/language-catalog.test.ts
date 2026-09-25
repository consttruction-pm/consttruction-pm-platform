import assert from "node:assert/strict";
import test from "node:test";

import { LanguageCatalogService } from "./language-catalog.ts";
import { InMemoryLanguagePackStore } from "./language-pack-store.ts";

test("catalog reports installed and offline-ready languages", async () => {
  const capabilities = {
    ui: true,
    help: true,
    aiText: true,
    voiceInput: true,
    voiceOutput: true,
    offlineAi: false,
  };
  const store = new InMemoryLanguagePackStore();

  await store.put({
    packageId: "construction-pm.language.fa",
    languageTag: "fa",
    version: "1.0.0",
    verified: true,
    artifact: new Uint8Array([1]),
  });

  const service = new LanguageCatalogService(
    [
      {
        languageTag: "fa",
        direction: "rtl",
        locale: "fa-IR",
        fallbackChain: ["en"],
        capabilities,
      },
      {
        languageTag: "en",
        direction: "ltr",
        locale: "en-US",
        fallbackChain: [],
        capabilities,
      },
    ],
    store,
  );

  const catalog = await service.list();
  assert.equal(catalog.length, 2);
  assert.deepEqual(catalog[0], {
    languageTag: "fa",
    direction: "rtl",
    locale: "fa-IR",
    installedVersion: "1.0.0",
    verified: true,
    offlineReady: true,
    capabilities,
  });
  assert.equal(catalog[1]?.installedVersion, null);
  assert.equal(catalog[1]?.offlineReady, false);
});
