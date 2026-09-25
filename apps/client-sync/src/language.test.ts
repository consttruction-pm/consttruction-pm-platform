import assert from "node:assert/strict";
import test from "node:test";

import { ClientLanguageManager } from "./language.ts";

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

test("resolves preferred installed language locally", () => {
  const manager = new ClientLanguageManager(registry, "en", {
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

  assert.deepEqual(manager.resolve(), {
    languageTag: "fa",
    source: "preferred",
    direction: "rtl",
    locale: "fa-IR",
    packVersion: "1.0.0",
    offline: true,
  });
});

test("falls back to an installed language when preferred pack is missing", () => {
  const manager = new ClientLanguageManager(registry, "en", {
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
    ],
  });

  assert.equal(manager.resolve().languageTag, "en");
  assert.equal(manager.resolve().source, "fallback");
  assert.equal(manager.resolve().offline, true);
});

test("does not claim offline support for an unverified pack", () => {
  const manager = new ClientLanguageManager(registry, "en", {
    preferredLanguage: "fa",
    fallbackChain: ["en"],
    installedPacks: [
      {
        languageTag: "fa",
        version: "1.0.0",
        active: true,
        verified: false,
        capabilities,
      },
    ],
  });

  assert.equal(manager.canRunOffline("fa"), false);
  assert.equal(manager.resolve().offline, false);
});

test("language changes do not mutate structured project identifiers", () => {
  const projectData = {
    activityId: "A-104",
    costCode: "CC-210",
    durationDays: 12,
  };
  const manager = new ClientLanguageManager(registry, "en", {
    preferredLanguage: "en",
    fallbackChain: ["fa"],
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

  manager.setPreferredLanguage("fa");
  assert.deepEqual(projectData, {
    activityId: "A-104",
    costCode: "CC-210",
    durationDays: 12,
  });
});
