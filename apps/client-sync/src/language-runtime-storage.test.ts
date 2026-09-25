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
