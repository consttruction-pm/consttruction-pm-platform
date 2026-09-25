import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import { DesktopFileLanguagePackResourceManifestStore } from "./language-storage.ts";

test("desktop persists language pack resource manifests", async () => {
  const directory = await mkdtemp(join(tmpdir(), "construction-pm-language-"));
  try {
    const store = new DesktopFileLanguagePackResourceManifestStore(directory);
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
    assert.equal(loaded?.resources.translation, "translations.json");

    await store.remove("construction-pm.language.fa", "1.0.0");
    assert.equal(
      await store.get("construction-pm.language.fa", "1.0.0"),
      null,
    );
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});
