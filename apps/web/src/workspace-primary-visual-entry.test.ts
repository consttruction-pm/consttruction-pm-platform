import assert from "node:assert/strict";
import test from "node:test";
import { createVisualDemoState, renderVisualDemo } from "./workspace-visual-demo.js";

test("the primary visual workspace renders Activities with WBS grouping in the default state", () => {
  const html = renderVisualDemo(createVisualDemoState("en"));
  assert.match(html, /data-visual-demo/);
  assert.match(html, /CUBI-DEMO-001/);
  assert.match(html, /Activities/);
  assert.match(html, /WBS/);
  assert.match(html, /Visual demo · sample data/);
  assert.doesNotMatch(html, /data-vd-exit|Return to workspace|Help → Visual workspace demo/);
});

test("the primary visual workspace renders Persian RTL without exposing a second shell", () => {
  const html = renderVisualDemo(createVisualDemoState("fa"));
  assert.match(html, /dir="rtl"/);
  assert.match(html, /محیط کار حرفه‌ای/);
  assert.match(html, /نمایش بصری · دادهٔ نمونه/);
  assert.doesNotMatch(html, /بازگشت به محیط کار|data-vd-exit/);
});
