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


test("caching a verified pack updates the runtime offline state", async () => {
  const store = new InMemoryLanguagePackStore();
  const runtime = new ClientLanguageRuntime(store);
  const caps = {
    ui: true,
    help: true,
    aiText: true,
    voiceInput: true,
    voiceOutput: true,
    offlineAi: false,
  };

  runtime.configure(
    [
      {
        languageTag: "fa",
        direction: "rtl",
        locale: "fa-IR",
        fallbackChain: ["en"],
        capabilities: caps,
      },
      {
        languageTag: "en",
        direction: "ltr",
        locale: "en-US",
        fallbackChain: [],
        capabilities: caps,
      },
    ],
    "en",
    {
      preferredLanguage: "fa",
      fallbackChain: ["en"],
      installedPacks: [],
    },
  );

  assert.equal(runtime.current().offline, false);

  await runtime.cacheVerifiedPack({
    packageId: "construction-pm.language.fa",
    languageTag: "fa",
    version: "1.0.0",
    verified: true,
    artifact: new Uint8Array([7, 8]),
  });

  assert.equal(runtime.current().languageTag, "fa");
  assert.equal(runtime.current().packVersion, "1.0.0");
  assert.equal(runtime.current().offline, true);
});
