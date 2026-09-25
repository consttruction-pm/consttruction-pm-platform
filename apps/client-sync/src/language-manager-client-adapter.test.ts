import assert from "node:assert/strict";
import test from "node:test";

import { LanguageManagerClientAdapter } from "./language-manager-client-adapter.ts";
import { LanguageManagerController } from "./language-manager-controller.ts";
import { ClientLanguageRuntime } from "./language-runtime.ts";
import { InMemoryLanguagePackStore } from "./language-pack-store.ts";

test("select uses controller refresh and preserves authoritative catalog capabilities", async () => {
  const store = new InMemoryLanguagePackStore();
  const capabilities = {
    ui: true,
    help: true,
    aiText: true,
    voiceInput: false,
    voiceOutput: true,
    offlineAi: true,
  };

  const runtime = new ClientLanguageRuntime(store);
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
      fallbackChain: [],
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

  const adapter = new LanguageManagerClientAdapter(controller);
  const state = await adapter.select("fa");

  assert.equal(state.selectedLanguage, "fa");
  assert.equal(state.rows[0]?.offlineAi, true);
  assert.equal(state.rows[0]?.voiceOutput, true);
  assert.equal(state.rows[1]?.direction, "rtl");
});
