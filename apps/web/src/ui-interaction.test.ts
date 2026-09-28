import assert from "node:assert/strict";
import test from "node:test";

import { interactivePolicy, resolveTextDirection } from "./ui-interaction.js";

test("text direction resolves by language tag and can be explicitly overridden", () => {
  assert.equal(resolveTextDirection("fa-IR"), "rtl");
  assert.equal(resolveTextDirection("ar"), "rtl");
  assert.equal(resolveTextDirection("en-US"), "ltr");
  assert.equal(resolveTextDirection("he-IL"), "rtl");
  assert.equal(resolveTextDirection("ja-JP"), "ltr");
  assert.equal(resolveTextDirection("ja-JP", "rtl"), "rtl");
});

test("all interactive surfaces use left activation and right context-menu behavior", () => {
  for (const kind of ["menu", "field", "help", "action"] as const) {
    assert.deepEqual(interactivePolicy(kind), {
      kind,
      leftClick: "activate",
      rightClick: "context-menu",
      keyboardEquivalent: "enter-or-space",
    });
  }
});
