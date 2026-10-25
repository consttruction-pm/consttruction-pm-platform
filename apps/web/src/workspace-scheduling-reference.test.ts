import assert from "node:assert/strict";
import testCase from "node:test";

import { SCHEDULING_REFERENCE_CATALOG } from "./scheduling-reference-catalog.generated.js";
import { renderMainWorkspace } from "./workspace-view.js";
import { createWorkspaceState } from "./workspace-model.js";
import { getWorkspaceNavigation } from "./workspace-navigation.js";

function renderReference(locale = "en", activeMenu: "schedule" | "reports" = "schedule"): string {
  let html = "";
  const container = {
    get innerHTML() { return html; },
    set innerHTML(value: string) { html = value; },
  };
  const state = createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 7 }, locale);
  renderMainWorkspace(
    container as unknown as HTMLElement,
    { ...state, activeMenu },
  );
  return html;
}

testCase("the Web reference catalog includes every registered requirement, formula, and documentation track", () => {
  assert.equal(SCHEDULING_REFERENCE_CATALOG.requirements.length, 72);
  assert.equal(SCHEDULING_REFERENCE_CATALOG.formulas.length, 18);
  assert.equal(SCHEDULING_REFERENCE_CATALOG.documentation.length, 16);

  const html = renderReference();
  const panel = html.slice(html.indexOf('<section id="cp-scheduling-reference"'));
  assert.ok(panel.startsWith('<section id="cp-scheduling-reference"'));
  for (const item of SCHEDULING_REFERENCE_CATALOG.requirements) {
    assert.ok(panel.includes("<code>" + item.id + "</code>"), "missing requirement " + item.id);
  }
  for (const item of SCHEDULING_REFERENCE_CATALOG.formulas) {
    assert.ok(panel.includes("<code>" + item.id + "</code>"), "missing formula " + item.id);
  }
  for (const item of SCHEDULING_REFERENCE_CATALOG.documentation) {
    assert.ok(panel.includes("<code>" + item.id + "</code>"), "missing documentation track " + item.id);
  }
});

testCase("the visible reference panel does not expose source-brand names, URLs, or repository paths", () => {
  const html = renderReference();
  const panel = html.slice(html.indexOf('<section id="cp-scheduling-reference"'));
  assert.doesNotMatch(panel, /\bP6\b|Primavera|Oracle|https?:\/\//i);
  assert.doesNotMatch(panel, /src\/construction_pm|tests\/test_|docs\.oracle/i);
});

testCase("schedule submenu entries have matching target sections in the reference view", () => {
  const item = getWorkspaceNavigation("schedule");
  assert.equal(item.submenus.length, 12);
  const html = renderReference();
  for (const target of [
    "#cp-activity-grid",
    "#cp-gantt",
    "#cp-reference-relationships",
    "#cp-reference-calendars",
    "#cp-reference-options",
    "#cp-reference-resources",
    "#cp-reference-progress",
    "#cp-scheduling-reference-formulas",
    "#cp-scheduling-reference-documentation",
  ]) {
    assert.ok(html.includes('href="' + target + '"'), "missing link to " + target);
    assert.ok(html.includes('id="' + target.slice(1) + '"'), "missing target " + target);
  }
});

testCase("the reference catalogue is hidden outside the Schedule workspace", () => {
  assert.match(renderReference("en", "schedule"), /id="cp-scheduling-reference"/);
  assert.match(renderReference("en", "reports"), /id="cp-scheduling-reference"[^>]*hidden/);
});

testCase("the reference view is localized at the navigation and section-label level", () => {
  const fa = renderReference("fa");
  assert.match(fa, /مرجع منطق و پیاده‌سازی زمان‌بندی/);
  assert.match(fa, /قراردادهای محاسباتی/);
  assert.match(fa, /جست‌وجو در مرجع/);
  assert.match(fa, /روابط و وقفه‌ها/);
});
