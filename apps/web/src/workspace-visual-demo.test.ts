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

test("WBS window renders a selectable hierarchy and a dedicated details inspector", () => {
  const state = createVisualDemoState("en");
  state.window = "wbs";
  state.selectedWbsCode = "1.2";
  const html = renderVisualDemo(state);

  assert.match(html, /cp-vd-wbs-layout/);
  assert.match(html, /data-vd-wbs="1\.2"/);
  assert.match(html, /Engineering/);
  assert.match(html, /data-vd-wbs-toggle="1"/);
  assert.match(html, /data-vd-wbs-dtab="general"/);
  assert.match(html, /Selected WBS element/);
  assert.match(html, /Parent code/);
  assert.match(html, /Visual sample only/);
  assert.doesNotMatch(html, /data-vd-wbs="1\.2\.1"[^>]*aria-selected="true"/);
});

test("WBS detail tab state is rendered as the active accessible tab", () => {
  const state = createVisualDemoState("fa");
  state.window = "wbs";
  state.selectedWbsCode = "1.2.1";
  state.wbsDetailTab = "dates";
  const html = renderVisualDemo(state);

  assert.match(html, /data-visual-demo dir="rtl"/);
  assert.match(html, /data-vd-wbs="1\.2\.1"[^>]*aria-selected="true"/);
  assert.match(html, /data-vd-wbs-dtab="dates" aria-selected="true" class="is-active"/);
  assert.match(html, /Not available in this visual sample/);
});

test("calendar editor presents properties, workweek and exception panes", () => {
  const html = renderVisualDemo(createVisualDemoState("en"));
  assert.match(html, /data-vd-dialog="calendar"/);
  assert.match(html, /cp-vd-calendar-editor/);
  assert.match(html, /Calendar properties/);
  assert.match(html, /Workweek/);
  assert.match(html, /Exceptions and holidays/);
  assert.match(html, /2027-03-20/);
  assert.match(html, /not saved or used for scheduling/);
});
