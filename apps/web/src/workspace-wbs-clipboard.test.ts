import assert from "node:assert/strict";
import test from "node:test";

import {
  nextWbsCopyCode,
  wbsClipboardLabels,
  wbsClipboardText,
} from "./workspace-wbs-clipboard.js";

const nodes = [
  { id: "W-ROOT", parentKind: "project" as const, parentWbsId: null, localCode: "1" },
  { id: "W-CIVIL", parentKind: "wbs" as const, parentWbsId: "W-ROOT", localCode: "1.1" },
  { id: "W-PM", parentKind: "wbs" as const, parentWbsId: "W-ROOT", localCode: "1.2" },
  { id: "W-PM-OLD", parentKind: "wbs" as const, parentWbsId: "W-PM", localCode: "1.1" },
  { id: "W-PM-OLD-COPY", parentKind: "wbs" as const, parentWbsId: "W-PM", localCode: "1.1 (copy)" },
];

test("copy code keeps the source code when the target has no such sibling", () => {
  assert.equal(nextWbsCopyCode(nodes, "W-ROOT", "9.9"), "9.9");
});

test("copy code derives a sibling-unique suffix and ignores other parents", () => {
  assert.equal(nextWbsCopyCode(nodes, "W-PM", "1.1"), "1.1 (copy 2)");
  assert.equal(nextWbsCopyCode(nodes, "W-PM-OLD", "1.1"), "1.1");
  assert.equal(nextWbsCopyCode(nodes, "W-ROOT", "1.1"), "1.1 (copy)");
});

test("clipboard text names the copied or cut element and localizes", () => {
  assert.equal(wbsClipboardText("en", null), "Clipboard empty");
  assert.equal(wbsClipboardText("fa", null), "حافظهٔ موقت خالی است");
  assert.equal(
    wbsClipboardText("en", { mode: "copy", wbsId: "W-CIVIL", code: "1.1", name: "Civil" }),
    "Clipboard: copy — Civil (1.1)",
  );
  assert.equal(
    wbsClipboardText("fa", { mode: "cut", wbsId: "W-CIVIL", code: "1.1", name: "عمرانی" }),
    "حافظهٔ موقت: برش — عمرانی (1.1)",
  );
});

test("clipboard labels explain the delete precondition instead of a persistence code", () => {
  const en = wbsClipboardLabels("en");
  assert.equal(en.cut, "Cut");
  assert.match(en.deleteGuidance, /child elements or activity assignments/);
  assert.doesNotMatch(en.deleteGuidance, /WBS_IN_USE/);
  assert.match(wbsClipboardLabels("fa").deleteGuidance, /زیرعنصر یا تخصیص فعالیت/);
});
