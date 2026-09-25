import assert from "node:assert/strict";
import test from "node:test";

import { InMemoryLanguagePreferenceStore } from "./language-preference-store.ts";

test("persists the preferred language", async () => {
  const store = new InMemoryLanguagePreferenceStore();
  assert.equal(await store.load(), null);
  await store.save("fa");
  assert.equal(await store.load(), "fa");
});

test("rejects an empty language preference", async () => {
  const store = new InMemoryLanguagePreferenceStore();
  await assert.rejects(store.save("   "), /INVALID_LANGUAGE_PREFERENCE/);
});
