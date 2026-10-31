import assert from "node:assert/strict";
import test from "node:test";

import { createVisualDemoState, renderVisualDemo } from "./workspace-visual-demo.js";

test("visual workspace exposes language, full-screen and sign-out controls without a second workspace link", () => {
  const html = renderVisualDemo(createVisualDemoState("en"));

  assert.match(html, /<select data-vd-locale/);
  assert.match(html, /<option value="en" selected>English<\/option>/);
  assert.match(html, /<option value="fa">فارسی<\/option>/);
  assert.doesNotMatch(html, /Open live workspace/);
  assert.match(html, /data-vd-fullscreen/);
  assert.match(html, />Full screen<\/button>/);
  assert.match(html, />Sign out<\/button>/);
  assert.match(html, /data-vd-action='\{"command":"sign-out"\}'/);
  assert.match(html, /Sign out/);
});

test("visual workspace language selector respects Persian direction and label", () => {
  const html = renderVisualDemo(createVisualDemoState("fa"));

  assert.match(html, /data-visual-demo dir="rtl"/);
  assert.match(html, /<option value="fa" selected>فارسی<\/option>/);
  assert.match(html, /تمام‌صفحه/);
  assert.match(html, /خروج از حساب/);
  assert.match(html, /خروج از حساب/);
});

test("full-screen control changes to return-to-normal-view while active", () => {
  const state = createVisualDemoState("en");
  state.fullscreen = true;
  const html = renderVisualDemo(state);

  assert.match(html, /aria-pressed="true"/);
  assert.match(html, />Return to normal view<\/button>/);
});
