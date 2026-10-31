import assert from "node:assert/strict";
import test from "node:test";

import { createVisualDemoState, renderVisualDemo } from "./workspace-visual-demo.js";

test("visual workspace exposes language selection and keeps live navigation separate from sign out", () => {
  const html = renderVisualDemo(createVisualDemoState("en"));

  assert.match(html, /<select data-vd-locale/);
  assert.match(html, /<option value="en" selected>English<\/option>/);
  assert.match(html, /<option value="fa">فارسی<\/option>/);
  assert.match(html, /Open live workspace/);
  assert.match(html, /data-vd-action='\{"command":"sign-out"\}'/);
  assert.match(html, /Sign out/);
});

test("visual workspace language selector respects Persian direction and label", () => {
  const html = renderVisualDemo(createVisualDemoState("fa"));

  assert.match(html, /data-visual-demo dir="rtl"/);
  assert.match(html, /<option value="fa" selected>فارسی<\/option>/);
  assert.match(html, /بازگشت به محیط واقعی پروژه/);
  assert.match(html, /خروج از حساب/);
});
