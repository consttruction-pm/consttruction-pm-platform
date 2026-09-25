import assert from "node:assert/strict";
import test from "node:test";

import { LanguageCatalogService, isNewerPackAvailable } from "./language-catalog.ts";
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
    installedPackageId: "construction-pm.language.fa",
    installedVersion: "1.0.0",
    verified: true,
    offlineReady: true,
    capabilities,
  });
  assert.equal(catalog[1]?.installedVersion, null);
  assert.equal(catalog[1]?.offlineReady, false);
});


test("detects only a genuinely newer compatible pack", () => {
  assert.equal(isNewerPackAvailable("1.0.0", "1.1.0"), true);
  assert.equal(isNewerPackAvailable("1.1.0", "1.1.0"), false);
  assert.equal(isNewerPackAvailable("1.2.0", "1.1.0"), false);
  assert.equal(isNewerPackAvailable(null, "1.0.0"), true);
  assert.equal(isNewerPackAvailable("1.0.0", null), false);
});
