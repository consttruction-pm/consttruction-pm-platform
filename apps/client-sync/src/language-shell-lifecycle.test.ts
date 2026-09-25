import assert from "node:assert/strict";
import test from "node:test";

import { ClientLanguageShellLifecycle } from "./language-shell-lifecycle.js";
import { ClientLanguageRuntime } from "./language-runtime.js";
import {
  InMemoryLanguagePreferenceStore,
} from "./language-preference-store.js";
import {
  InMemoryLanguagePackStore,
} from "./language-pack-store.js";

const registry = [
  {
    languageTag: "en",
    direction: "ltr" as const,
    locale: "en-US",
    fallbackChain: [],
    capabilities: {
      ui: true,
      help: true,
      aiText: true,
      voiceInput: false,
      voiceOutput: false,
      offlineAi: true,
    },
  },
  {
    languageTag: "fa",
    direction: "rtl" as const,
    locale: "fa-IR",
    fallbackChain: ["en"],
    capabilities: {
      ui: true,
      help: true,
      aiText: true,
      voiceInput: true,
      voiceOutput: true,
      offlineAi: true,
    },
  },
];

const pack = {
  packageId: "construction-pm.language.fa",
  languageTag: "fa",
  version: "1.2.0",
  verified: true,
  artifact: new Uint8Array([1, 2, 3]),
};

test("language shell lifecycle restores preference and activates cached resources atomically", async () => {
  const packs = new InMemoryLanguagePackStore();
  await packs.put(pack);
  const preferenceStore = new InMemoryLanguagePreferenceStore();
  await preferenceStore.save("fa");

  const runtime = new ClientLanguageRuntime(packs, preferenceStore);
  runtime.configure(registry, "en", {
    preferredLanguage: "en",
    fallbackChain: ["en"],
    installedPacks: [],
  });

  const activated: string[] = [];
  const shell = new ClientLanguageShellLifecycle(
    runtime,
    async (packageId, version) => {
      activated.push(packageId + "@" + version);
    },
  );

  const result = await shell.initialize();

  assert.equal(result.language.languageTag, "fa");
  assert.equal(result.language.direction, "rtl");
  assert.equal(result.activation, "activated");
  assert.deepEqual(activated, ["construction-pm.language.fa@1.2.0"]);
});

test("language shell lifecycle does not claim activation when no verified pack exists", async () => {
  const packs = new InMemoryLanguagePackStore();
  const preferenceStore = new InMemoryLanguagePreferenceStore();
  await preferenceStore.save("fa");

  const runtime = new ClientLanguageRuntime(packs, preferenceStore);
  runtime.configure(registry, "en", {
    preferredLanguage: "en",
    fallbackChain: ["en"],
    installedPacks: [],
  });

  let called = false;
  const shell = new ClientLanguageShellLifecycle(
    runtime,
    async () => {
      called = true;
    },
  );

  const result = await shell.initialize();

  assert.equal(result.language.languageTag, "en");
  assert.equal(result.language.offline, false);
  assert.equal(result.activation, "not-required");
  assert.equal(called, false);
});

test("language shell lifecycle reports missing resource manifest without changing preference", async () => {
  const packs = new InMemoryLanguagePackStore();
  await packs.put(pack);
  const preferenceStore = new InMemoryLanguagePreferenceStore();
  await preferenceStore.save("fa");

  const runtime = new ClientLanguageRuntime(packs, preferenceStore);
  runtime.configure(registry, "en", {
    preferredLanguage: "en",
    fallbackChain: ["en"],
    installedPacks: [],
  });

  const shell = new ClientLanguageShellLifecycle(
    runtime,
    async () => {
      throw new Error("LANGUAGE_PACK_RESOURCE_MANIFEST_NOT_FOUND");
    },
  );

  const result = await shell.initialize();

  assert.equal(result.language.languageTag, "fa");
  assert.equal(result.activation, "resource-manifest-missing");
  assert.equal(runtime.current().languageTag, "fa");
});


test("language shell installed switch leaves preference unchanged when activation fails", async () => {
  const packs = new InMemoryLanguagePackStore();
  await packs.put({
    ...pack,
    version: "1.10.0",
  });

  const preferenceStore = new InMemoryLanguagePreferenceStore();
  await preferenceStore.save("en");

  const runtime = new ClientLanguageRuntime(packs, preferenceStore);
  runtime.configure(registry, "en", {
    preferredLanguage: "en",
    fallbackChain: ["en"],
    installedPacks: [],
  });

  const shell = new ClientLanguageShellLifecycle(
    runtime,
    async () => {
      throw new Error("LANGUAGE_RESOURCE_MANIFEST_NOT_FOUND");
    },
  );

  await assert.rejects(
    shell.switchToInstalledLanguage("fa"),
    /LANGUAGE_RESOURCE_MANIFEST_NOT_FOUND/,
  );
  assert.equal(runtime.current().languageTag, "en");
});

test("language shell reports an explicit not-installed state without changing current language", async () => {
  const runtime = new ClientLanguageRuntime(
    new InMemoryLanguagePackStore(),
    new InMemoryLanguagePreferenceStore(),
  );
  runtime.configure(registry, "en", {
    preferredLanguage: "en",
    fallbackChain: ["en"],
    installedPacks: [],
  });

  const shell = new ClientLanguageShellLifecycle(
    runtime,
    async () => {
      throw new Error("NOT_EXPECTED");
    },
  );

  const result = await shell.switchToInstalledLanguage("fa");

  assert.equal(result.activation, "not-installed");
  assert.equal(result.language.languageTag, "en");
});
