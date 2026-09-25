import assert from "node:assert/strict";
import test from "node:test";

import { DEFAULT_ENGLISH_LANGUAGE_MANAGER_COPY } from "./language-manager-copy.ts";

test("default language manager copy is complete and non-empty", () => {
  const values = Object.values(DEFAULT_ENGLISH_LANGUAGE_MANAGER_COPY);
  for (const value of values) {
    if (typeof value === "string") assert.ok(value.length > 0);
  }
  assert.ok(DEFAULT_ENGLISH_LANGUAGE_MANAGER_COPY.downloading("French"));
  assert.ok(DEFAULT_ENGLISH_LANGUAGE_MANAGER_COPY.action);
  assert.ok(DEFAULT_ENGLISH_LANGUAGE_MANAGER_COPY.downloadProgress);
});
