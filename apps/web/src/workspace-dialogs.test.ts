import assert from "node:assert/strict";
import test from "node:test";

import { defaultLayoutPatch, readLayoutPatch, renderLayoutDialogs, type DialogOptions } from "./workspace-dialogs.js";
import { DEFAULT_PRESENTATION } from "./workspace-presentation.js";

function form(entries: Record<string, string>): FormData {
  const data = new FormData();
  for (const [key, value] of Object.entries(entries)) data.append(key, value);
  return data;
}

function dialogOptions(patch: Partial<DialogOptions> = {}): DialogOptions {
  return {
    locale: "en",
    layout: { groupBy: "wbs", ganttScale: "day", showRelationships: true, density: "compact" },
    sortColumns: [{ id: "name", label: "Activity Name" }],
    sortColumnId: "name",
    sortDirection: "asc",
    rowHeight: 26,
    fontSize: 12,
    barHeight: 16,
    barTone: "crimson",
    presentation: DEFAULT_PRESENTATION,
    dataAvailability: { actual: true, baseline: false },
    ...patch,
  };
}

test("Table Font and Row reads a real row height and font size", () => {
  const patch = readLayoutPatch(form({ rowHeight: "29", fontSize: "12" }));
  assert.equal(patch.rowHeight, 29);
  assert.equal(patch.fontSize, 12);
  assert.equal(patch.presentation?.table.rowHeight, 29);
  assert.equal(patch.presentation?.table.fontSize, 12);
});

test("Table Font and Row clamps out-of-range values instead of applying them", () => {
  const small = readLayoutPatch(form({ rowHeight: "4", fontSize: "2" }));
  assert.equal(small.rowHeight, 18);
  assert.equal(small.fontSize, 9);

  const large = readLayoutPatch(form({ rowHeight: "99", fontSize: "40" }));
  assert.equal(large.rowHeight, 40);
  assert.equal(large.fontSize, 16);
});

test("Table Font and Row reads font family, colours, row mode and icons", () => {
  const patch = readLayoutPatch(form({
    fontFamily: "cairo",
    textColor: "#123abc",
    backgroundColor: "#f4f6f9",
    rowHeightMode: "content",
    showIcons: "on",
    lineNumbers: "on",
  }));
  const table = patch.presentation?.table;
  assert.equal(table?.fontFamily, "cairo");
  assert.equal(table?.textColor, "#123abc");
  assert.equal(table?.backgroundColor, "#f4f6f9");
  assert.equal(table?.rowHeightMode, "content");
  assert.equal(table?.showIcons, true);
  assert.equal(table?.lineNumbers, true);
});

test("invalid colours are ignored instead of replacing the saved appearance", () => {
  const patch = readLayoutPatch(form({ textColor: "red", backgroundColor: "#12" }));
  assert.equal(patch.textColor, undefined);
  assert.equal(patch.backgroundColor, undefined);
  assert.equal(patch.presentation, undefined);
});

test("Table Font and Row dialog exposes the real controls and persisted values", () => {
  const html = renderLayoutDialogs(dialogOptions());

  assert.match(html, /name="rowHeight" min="18" max="40"[^>]*value="22"/);
  assert.match(html, /name="fontSize"/);
  assert.match(html, /<option value="11" selected>11 px<\/option>/);
  assert.match(html, /name="fontFamily"/);
  assert.match(html, /name="textColor" value="#000000"/);
  assert.match(html, /name="backgroundColor" value="#ffffff"/);
  assert.match(html, /name="rowHeightMode" value="keep"/);
  assert.match(html, /name="rowHeightMode" value="content"/);
  assert.match(html, /name="rowHeightMode" value="fixed" checked/);
  assert.match(html, /name="showIcons"/);
  assert.match(html, /name="lineNumbers"/);
  assert.doesNotMatch(html, /Primavera|Oracle|P6/);
});

test("Bar Styles exposes an independent editor for every bar kind", () => {
  const html = renderLayoutDialogs(dialogOptions());
  for (const kind of ["task", "critical", "summary", "milestone", "progress", "actual", "baseline"]) {
    assert.match(html, new RegExp(`data-bar-style="${kind}"`));
    assert.match(html, new RegExp(`name="bar\\.${kind}\\.bodyColor"`));
    assert.match(html, new RegExp(`name="bar\\.${kind}\\.bodyShape"`));
    assert.match(html, new RegExp(`name="bar\\.${kind}\\.filter"`));
    assert.match(html, new RegExp(`name="bar\\.${kind}\\.row"`));
    assert.match(html, new RegExp(`name="bar\\.${kind}\\.labelField"`));
    assert.match(html, new RegExp(`name="bar\\.${kind}\\.labelPosition"`));
  }
  // Baseline dates are absent in this fixture, so that editor is explicitly
  // unavailable instead of pretending to draw a bar without data.
  assert.match(html, /No baseline dates are loaded/);
  assert.match(html, /data-bar-style="baseline"[^>]*>\s*<summary[\s\S]*?disabled/);
});

test("bar styles are read independently and keep unrelated styles untouched", () => {
  const previous = DEFAULT_PRESENTATION;
  const patch = readLayoutPatch(form({
    "bar.task.height": "18",
    "bar.task.bodyShape": "diamond",
    "bar.task.bodyColor": "#123456",
    "bar.task.labelField": "activity-name",
    "bar.task.labelPosition": "right",
  }), previous);
  const task = patch.presentation?.bars.task;
  assert.equal(task?.height, 18);
  assert.equal(task?.bodyShape, "diamond");
  assert.equal(task?.bodyColor, "#123456");
  assert.equal(task?.labelField, "activity-name");
  assert.equal(task?.labelPosition, "right");
  assert.deepEqual(patch.presentation?.bars.critical, previous.bars.critical);
});

test("a hidden bar remains hidden when its editor row is absent from the form", () => {
  const patch = readLayoutPatch(form({ "bar.task.height": "10" }), DEFAULT_PRESENTATION);
  assert.equal(patch.presentation?.bars.task.visible, false);
});

test("a dialog without numeric fields does not reset visual preferences", () => {
  const patch = readLayoutPatch(form({ groupBy: "wbs", sortColumnId: "name", sortDirection: "asc" }));
  assert.equal(patch.groupBy, "wbs");
  assert.equal(patch.sortColumnId, "name");
  assert.equal(patch.rowHeight, undefined);
  assert.equal(patch.fontSize, undefined);
  assert.equal(patch.barHeight, undefined);
  assert.equal(patch.presentation, undefined);
});

test("default layout patch keeps the professional compact defaults", () => {
  const defaults = defaultLayoutPatch();
  assert.equal(defaults.rowHeight, 22);
  assert.equal(defaults.fontSize, 11);
  assert.equal(defaults.rowHeightMode, "fixed");
  assert.equal(defaults.showIcons, true);
  assert.equal(defaults.lineNumbers, false);
  assert.deepEqual(defaults.presentation, DEFAULT_PRESENTATION);
  assert.equal(defaults.groupBy, "wbs");
  assert.equal(defaults.ganttScale, "day");
});

test("Filters dialog exposes predefined filters and a real criteria builder", () => {
  const html = renderLayoutDialogs(dialogOptions());
  assert.match(html, /data-desktop-dialog="filters"/);
  assert.match(html, /name="filterActiveId"/);
  assert.match(html, /value="builtin:in-progress"/);
  assert.match(html, /value="builtin:completed"/);
  assert.match(html, /value="builtin:critical"/);
  assert.match(html, /name="filterName"/);
  assert.match(html, /name="filterMatch"/);
  for (let index = 0; index < 4; index += 1) {
    assert.match(html, new RegExp(`name="filter\.field\.${index}"`));
    assert.match(html, new RegExp(`name="filter\.operator\.${index}"`));
    assert.match(html, new RegExp(`name="filter\.value\.${index}"`));
  }
});

test("a custom filter is saved with the presentation and becomes active", () => {
  const patch = readLayoutPatch(form({
    filterActiveId: "",
    filterName: "Civil open",
    filterMatch: "all",
    "filter.field.0": "wbs",
    "filter.operator.0": "contains",
    "filter.value.0": "Civil",
    "filter.field.1": "activity_status",
    "filter.operator.1": "not-equals",
    "filter.value.1": "Completed",
    "filter.field.2": "activity_name",
    "filter.operator.2": "contains",
    "filter.value.2": "",
    "filter.field.3": "activity_name",
    "filter.operator.3": "contains",
    "filter.value.3": "",
  }), DEFAULT_PRESENTATION);
  assert.equal(patch.presentation?.filters.activeId, "custom:civil-open");
  assert.equal(patch.presentation?.filters.saved.length, 1);
  assert.equal(patch.presentation?.filters.saved[0].criteria.length, 2);
});

test("choosing a predefined filter applies it without creating a custom filter", () => {
  const patch = readLayoutPatch(form({
    filterActiveId: "builtin:completed",
    filterName: "",
    filterMatch: "all",
    "filter.field.0": "wbs",
    "filter.operator.0": "contains",
    "filter.value.0": "",
    "filter.field.1": "activity_name",
    "filter.operator.1": "contains",
    "filter.value.1": "",
    "filter.field.2": "activity_name",
    "filter.operator.2": "contains",
    "filter.value.2": "",
    "filter.field.3": "activity_name",
    "filter.operator.3": "contains",
    "filter.value.3": "",
  }), DEFAULT_PRESENTATION);
  assert.equal(patch.presentation?.filters.activeId, "builtin:completed");
  assert.equal(patch.presentation?.filters.saved.length, 0);
});

test("the active saved filter can be deleted from the dialog", () => {
  const saved = {
    ...DEFAULT_PRESENTATION,
    filters: {
      saved: [{
        id: "custom:civil-open",
        name: "Civil open",
        match: "all" as const,
        criteria: [{ fieldId: "wbs" as const, operator: "contains" as const, value: "Civil" }],
      }],
      activeId: "custom:civil-open",
    },
  };
  const patch = readLayoutPatch(form({
    filterActiveId: "custom:civil-open",
    filterName: "Civil open",
    filterMatch: "all",
    filterDelete: "on",
    "filter.field.0": "wbs",
    "filter.operator.0": "contains",
    "filter.value.0": "Civil",
  }), saved);
  assert.equal(patch.presentation?.filters.activeId, null);
  assert.equal(patch.presentation?.filters.saved.length, 0);
});
