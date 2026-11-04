import assert from "node:assert/strict";
import test from "node:test";

import {
  ENGINEERING_SHELLS,
  isEngineeringShellWindow,
  renderEngineeringShell,
} from "./workspace-engineering-shells.js";
import { createVisualDemoState, renderVisualDemo } from "./workspace-visual-demo.js";

test("engineering shell catalogue contains the 16 new reusable window shells", () => {
  assert.equal(ENGINEERING_SHELLS.length, 16);
  assert.equal(new Set(ENGINEERING_SHELLS.map((item) => item.id)).size, 16);
  for (const item of ENGINEERING_SHELLS) {
    assert.equal(isEngineeringShellWindow(item.id), true);
    assert.ok(item.columns.length >= 4);
    assert.ok(item.methods.length >= 3);
    assert.ok(item.inputs.length >= 2);
    assert.ok(item.outputs.length >= 2);
    assert.ok(item.details.some((tab) => tab.id === "general"));
  }
});

test("each shell renders a titled page, page toolbar, empty table and engine-specific details", () => {
  for (const item of ENGINEERING_SHELLS) {
    const html = renderEngineeringShell(item.id, "en", "general");
    assert.match(html, /class="cp-vd-windowbody cp-vd-engine-shell"/, item.id);
    assert.ok(html.includes(item.id), item.id);
    assert.match(html, /Planned · shell only/, item.id);
    assert.match(html, /No records to display/, item.id);
    assert.match(html, /No sample project values/, item.id);
    assert.match(html, /data-vd-engine-tab="general"/, item.id);
    assert.match(html, /Engine commands/, item.id);
    assert.match(html, /disabled title=/, item.id);
  }
});

test("method, input and output detail tabs expose the engine-specific method catalogue", () => {
  const item = ENGINEERING_SHELLS.find((entry) => entry.id === "optimization-studio");
  assert.ok(item);
  const methods = renderEngineeringShell(item.id, "en", "methods");
  assert.match(methods, /data-vd-engine-tab="methods"/);
  assert.match(methods, /Linear and mixed-integer programming/);
  assert.match(methods, /Pareto analysis/);

  const inputs = renderEngineeringShell(item.id, "en", "inputs");
  assert.match(inputs, /data-vd-engine-tab="inputs"/);
  assert.match(inputs, /Decision variables and objective weights/);

  const outputs = renderEngineeringShell(item.id, "en", "outputs");
  assert.match(outputs, /data-vd-engine-tab="outputs"/);
  assert.match(outputs, /Feasible candidate solutions/);
});

test("Persian engine shell preserves RTL direction and Persian control labels", () => {
  const item = ENGINEERING_SHELLS.find((entry) => entry.id === "project-watchdog");
  assert.ok(item);
  const html = renderEngineeringShell(item.id, "fa", "methods");
  assert.match(html, /ناظر هوشمند پروژه/);
  assert.match(html, /قواعد پایش/);
  assert.match(html, /در انتظار اتصال داده/);
});

test("visual workspace exposes every new engine shell in tabs, navigation and Tools menu", () => {
  const html = renderVisualDemo(createVisualDemoState("en"));
  assert.match(html, /Engineering Intelligence/);
  assert.match(html, /data-vd-nav-group="engineering"/);
  for (const item of ENGINEERING_SHELLS) {
    assert.ok(html.includes('data-vd-window="' + item.id + '"'), item.id + " navigation");
    assert.ok(html.includes('"window":"' + item.id + '"'), item.id + " Tools menu");
  }
});

test("each engineering shell opens through the visual workspace window router and has local details tabs", () => {
  for (const item of ENGINEERING_SHELLS) {
    const state = createVisualDemoState("fa");
    state.window = item.id;
    state.engineDetailTab = "methods";
    const html = renderVisualDemo(state);
    assert.ok(html.includes('data-engine-window="' + item.id + '"'), item.id);
    assert.match(html, /aria-selected="true" data-vd-engine-tab="methods"/, item.id);
    assert.match(html, /پوسته بصری/, item.id);
  }
});

test("existing Risks, Changes & Claims and Smart Guide windows remain distinct existing surfaces", () => {
  for (const id of ["risks", "changes-claims", "smart-guide"] as const) {
    assert.equal(isEngineeringShellWindow(id), false);
    const state = createVisualDemoState("en");
    state.window = id;
    const html = renderVisualDemo(state);
    assert.ok(html.includes('data-vd-window="' + id + '"'));
    assert.doesNotMatch(html, /data-engine-window=/);
  }
});

test("unconnected engine shells disable the generic context action rail", () => {
  const state = createVisualDemoState("en");
  state.window = "engineering-analysis";
  const html = renderVisualDemo(state);
  const rail = html.match(/<aside class="cp-vd-right-rail"[\s\S]*?<\/aside>/)?.[0] ?? "";
  assert.ok(rail.includes("disabled"));
  assert.equal((rail.match(/disabled/g) ?? []).length, 5);
});
