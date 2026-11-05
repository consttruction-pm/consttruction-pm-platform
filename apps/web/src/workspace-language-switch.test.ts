import assert from "node:assert/strict";
import test from "node:test";

import { getWorkspaceLanguageOptions } from "./workspace-language-switch.js";

test("authenticated Visual Workspace exposes all eight approved languages", () => {
  assert.deepEqual(
    getWorkspaceLanguageOptions().map(({ value, label, direction }) => [value, label, direction]),
    [
      ["en", "English", "ltr"],
      ["fa", "فارسی", "rtl"],
      ["de", "Deutsch", "ltr"],
      ["zh", "中文", "ltr"],
      ["ar", "العربية", "rtl"],
      ["fr", "Français", "ltr"],
      ["ja", "日本語", "ltr"],
      ["ko", "한국어", "ltr"],
    ],
  );
});
