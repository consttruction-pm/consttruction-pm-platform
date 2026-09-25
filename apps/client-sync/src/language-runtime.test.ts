import assert from "node:assert/strict";
import test from "node:test";

import { ClientLanguageRuntime } from "./language-runtime.ts";

const capabilities = {
  ui: true,
  help: true,
  aiText: true,
  voiceInput: true,
  voiceOutput: true,
  offlineAi: false,
};

const registry = [
  {
    languageTag: "en",
    direction: "ltr" as const,
    locale: "en-US",
    fallbackChain: [],
    capabilities,
  },
  {
    languageTag: "fa",
    direction: "rtl" as const,
    locale: "fa-IR",
    fallbackChain: ["en"],
    capabilities,
  },
];

test("shared client binding switches preferred language without duplicating resolver logic", () => {
  const runtime = new ClientLanguageRuntime();

  assert.equal(runtime.isConfigured(), false);

  const configured = runtime.configure(registry, "en", {
    preferredLanguage: "fa",
    fallbackChain: ["en"],
    installedPacks: [
      {
        languageTag: "en",
        version: "1.0.0",
        active: true,
        verified: true,
        capabilities,
      },
      {
        languageTag: "fa",
        version: "1.0.0",
        active: true,
        verified: true,
        capabilities,
      },
    ],
  });

  assert.equal(configured.languageTag, "fa");
  assert.equal(configured.offline, true);
  assert.equal(runtime.canRunOffline("fa"), true);

  const english = runtime.setPreferredLanguage("en");
  assert.equal(english.languageTag, "en");
  assert.equal(english.direction, "ltr");
});
