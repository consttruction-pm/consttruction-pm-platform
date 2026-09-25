import assert from "node:assert/strict";
import test from "node:test";

import { InMemoryLanguagePackStore } from "./language-pack-store.ts";
import { ClientLanguageRuntime } from "./language-runtime.ts";
import { LanguageManagerController } from "./language-manager-controller.ts";

test("controller exposes catalog and selection through shared runtime", async () => {
  const store = new InMemoryLanguagePackStore();
  const capabilities = {
    ui: true,
    help: true,
    aiText: true,
    voiceInput: false,
    voiceOutput: false,
    offlineAi: false,
  };
  const runtime = new ClientLanguageRuntime(store, {
    async load() {
      return null;
    },
    async save() {},
  });

  runtime.configure(
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
    "en",
    {
      preferredLanguage: "en",
      fallbackChain: ["fa"],
      installedPacks: [],
    },
  );

  const controller = new LanguageManagerController(
    runtime,
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
  );

  const initial = await controller.refresh();
  assert.equal(initial.selectedLanguage, "en");
  assert.equal(initial.items.length, 2);

  const selected = controller.select("fa");
  assert.equal(selected.languageTag, "fa");
});


test("removes a non-active verified language pack", async () => {
  const store = new InMemoryLanguagePackStore();
  await store.put({
    packageId: "construction-pm.language.fa",
    languageTag: "fa",
    version: "1.0.0",
    verified: true,
    artifact: new Uint8Array([1]),
  });

  const runtime = new ClientLanguageRuntime(store);
  runtime.configure(
    [
      {
        languageTag: "en",
        direction: "ltr",
        locale: "en-US",
        fallbackChain: [],
        capabilities: {
          ui: true,
          help: true,
          aiText: true,
          voiceInput: false,
          voiceOutput: false,
          offlineAi: false,
        },
      },
    ],
    "en",
    {
      preferredLanguage: "en",
      fallbackChain: [],
      installedPacks: [],
    },
  );

  const controller = new LanguageManagerController(runtime, [], store);
  await controller.removeInstalledPack(
    "construction-pm.language.fa",
    "1.0.0",
  );

  assert.equal((await store.list()).length, 0);
});

test("blocks removal of the active language pack", async () => {
  const store = new InMemoryLanguagePackStore();
  await store.put({
    packageId: "construction-pm.language.en",
    languageTag: "en",
    version: "1.0.0",
    verified: true,
    artifact: new Uint8Array([1]),
  });

  const runtime = new ClientLanguageRuntime(store);
  runtime.configure(
    [
      {
        languageTag: "en",
        direction: "ltr",
        locale: "en-US",
        fallbackChain: [],
        capabilities: {
          ui: true,
          help: true,
          aiText: true,
          voiceInput: false,
          voiceOutput: false,
          offlineAi: false,
        },
      },
    ],
    "en",
    {
      preferredLanguage: "en",
      fallbackChain: [],
      installedPacks: [],
    },
  );

  const controller = new LanguageManagerController(runtime, [], store);

  await assert.rejects(
    controller.removeInstalledPack(
      "construction-pm.language.en",
      "1.0.0",
    ),
    /CANNOT_REMOVE_ACTIVE_LANGUAGE_PACK/,
  );
  assert.equal((await store.list()).length, 1);
});
