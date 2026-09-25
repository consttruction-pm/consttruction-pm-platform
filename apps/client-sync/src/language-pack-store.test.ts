import assert from "node:assert/strict";
import test from "node:test";

import { InMemoryLanguagePackStore } from "./language-pack-store.ts";

test("stores only verified language packs and returns copies", async () => {
  const store = new InMemoryLanguagePackStore();
  const artifact = new Uint8Array([1, 2, 3]);

  await store.put({
    packageId: "construction-pm.language.fa",
    languageTag: "fa",
    version: "1.0.0",
    verified: true,
    artifact,
  });

  artifact[0] = 9;

  const cached = await store.get("construction-pm.language.fa", "1.0.0");
  assert.deepEqual([...cached!.artifact], [1, 2, 3]);

  const list = await store.list();
  assert.equal(list.length, 1);
});

test("rejects unverified packs", async () => {
  const store = new InMemoryLanguagePackStore();

  await assert.rejects(
    store.put({
      packageId: "construction-pm.language.fa",
      languageTag: "fa",
      version: "1.0.0",
      verified: false,
      artifact: new Uint8Array([1]),
    }),
    /UNVERIFIED_LANGUAGE_PACK/,
  );
});
