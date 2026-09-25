import assert from "node:assert/strict";
import test from "node:test";

import {
  MobileKeyValueLanguagePackResourceManifestStore,
  type MobileKeyValueStorage,
} from "./language-storage.ts";

class MemoryStorage implements MobileKeyValueStorage {
  private readonly values = new Map<string, string>();

  async get(key: string): Promise<string | null> {
    return this.values.get(key) ?? null;
  }

  async set(key: string, value: string): Promise<void> {
    this.values.set(key, value);
  }

  async remove(key: string): Promise<void> {
    this.values.delete(key);
  }
}

test("mobile persists language pack resource manifests", async () => {
  const storage = new MemoryStorage();
  const store = new MobileKeyValueLanguagePackResourceManifestStore(storage);

  await store.put({
    packageId: "construction-pm.language.fa",
    languageTag: "fa",
    version: "1.0.0",
    resources: {
      translation: "translations.json",
      glossary: "glossary.json",
      help: "help.json",
      reports: "reports.json",
    },
  });

  const loaded = await store.get("construction-pm.language.fa", "1.0.0");
  assert.equal(loaded?.languageTag, "fa");
  assert.equal(loaded?.resources.help, "help.json");

  await store.remove("construction-pm.language.fa", "1.0.0");
  assert.equal(
    await store.get("construction-pm.language.fa", "1.0.0"),
    null,
  );
});
