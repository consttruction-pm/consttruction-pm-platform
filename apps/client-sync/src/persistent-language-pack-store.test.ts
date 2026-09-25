import assert from "node:assert/strict";
import test from "node:test";

import {
  PersistentLanguagePackStore,
  type PersistentLanguagePackBackend,
} from "./persistent-language-pack-store.ts";

class MemoryBackend implements PersistentLanguagePackBackend {
  private packs: Uint8Array[] = [];

  async load() {
    return this.packs.map((artifact, index) => ({
      packageId: "construction-pm.language.fa",
      languageTag: "fa",
      version: String(index + 1) + ".0.0",
      verified: true,
      artifact: new Uint8Array(artifact),
    }));
  }

  async save(packs: Parameters<PersistentLanguagePackBackend["save"]>[0]) {
    this.packs = packs.map((pack) => new Uint8Array(pack.artifact));
  }
}

test("persists and reloads verified packs through a host backend", async () => {
  const backend = new MemoryBackend();
  const first = new PersistentLanguagePackStore(backend);

  await first.put({
    packageId: "construction-pm.language.fa",
    languageTag: "fa",
    version: "1.0.0",
    verified: true,
    artifact: new Uint8Array([1, 2, 3]),
  });

  const second = new PersistentLanguagePackStore(backend);
  const pack = await second.get("construction-pm.language.fa", "1.0.0");
  assert.deepEqual([...pack!.artifact], [1, 2, 3]);
});

test("backend cannot persist an unverified pack", async () => {
  const backend = new MemoryBackend();
  const store = new PersistentLanguagePackStore(backend);

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
