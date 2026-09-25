import assert from "node:assert/strict";
import test from "node:test";

import { displayLanguageName } from "./language-display-name.ts";

test("returns a localized language display name", () => {
  const value = displayLanguageName("fa", "en-US");
  assert.ok(value);
  assert.notEqual(value, "undefined");
});

test("falls back to the language tag for invalid locales", () => {
  assert.equal(displayLanguageName("zzzz", "en-US"), "zzzz");
});
