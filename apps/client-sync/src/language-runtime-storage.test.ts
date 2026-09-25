import assert from "node:assert/strict";
import test from "node:test";

import { ClientLanguageRuntime } from "./language-runtime.ts";
import { InMemoryLanguagePackStore } from "./language-pack-store.ts";

test("runtime can cache and enumerate verified local language packs", async () => {
  const store = new InMemoryLanguagePackStore();
  const runtime = new ClientLanguageRuntime(store);

  await runtime.cacheVerifiedPack({
    packageId: "construction-pm.language.en",
    languageTag: "en",
    version: "1.0.0",
    verified: true,
    artifact: new Uint8Array([1, 2]),
  });

  const packs = await runtime.installedPacks();
  assert.equal(packs.length, 1);
  assert.equal(packs[0]?.languageTag, "en");
  assert.deepEqual([...packs[0]!.artifact], [1, 2]);
});


test("downloads and caches a verified language pack through the shared runtime", async () => {
  const store = new InMemoryLanguagePackStore();
  const runtime = new ClientLanguageRuntime(store);
  const phases: string[] = [];

  runtime.configure(
    [
      {
        languageTag: "fa",
        direction: "rtl",
        locale: "fa-IR",
        fallbackChain: ["en"],
        capabilities: {
          ui: true,
          help: true,
          aiText: true,
          voiceInput: true,
          voiceOutput: true,
          offlineAi: false,
        },
      },
      {
        languageTag: "en",
        direction: "ltr",
        locale: "en-US",
        fallbackChain: [],
        capabilities: {
          ui: true,
          help: true,
          aiText: true,
          voiceInput: true,
          voiceOutput: true,
          offlineAi: false,
        },
      },
    ],
    "en",
    {
      preferredLanguage: "fa",
      fallbackChain: ["en"],
      installedPacks: [],
    },
  );

  await runtime.downloadAndCacheLanguagePack(
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
        const data = new Uint8Array([4, 5]);
        onChunk?.(data);
        return data;
      },
    },
    {
      async verify(artifact) {
        return artifact.length === 2;
      },
    },
    (progress) => phases.push(progress.phase),
  );

  assert.deepEqual(phases, ["downloading", "downloading", "verifying", "cached"]);
  assert.equal(runtime.current().languageTag, "fa");
  assert.equal(runtime.current().offline, true);
});


test("persists and restores preferred language through a shared preference store", async () => {
  const store = new InMemoryLanguagePackStore();
  const values: { value: string | null } = { value: null };
  const preferenceStore = {
    async load() {
      return values.value;
    },
    async save(languageTag: string) {
      values.value = languageTag;
    },
  };
  const runtime = new ClientLanguageRuntime(store, preferenceStore);

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
          voiceInput: true,
          voiceOutput: true,
          offlineAi: false,
        },
      },
      {
        languageTag: "fa",
        direction: "rtl",
        locale: "fa-IR",
        fallbackChain: ["en"],
        capabilities: {
          ui: true,
          help: true,
          aiText: true,
          voiceInput: true,
          voiceOutput: true,
          offlineAi: false,
        },
      },
    ],
    "en",
    {
      preferredLanguage: "en",
      fallbackChain: ["fa"],
      installedPacks: [],
    },
  );

  await runtime.persistPreferredLanguage("fa");
  assert.equal(values.value, "fa");
  assert.equal((await runtime.restorePreferredLanguage()).languageTag, "fa");
});
