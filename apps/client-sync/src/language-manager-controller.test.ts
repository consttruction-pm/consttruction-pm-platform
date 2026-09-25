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
