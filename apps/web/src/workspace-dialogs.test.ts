import assert from "node:assert/strict";
import test from "node:test";

import { defaultLayoutPatch, filterCriterionRowMarkup, readLayoutPatch, renderLayoutDialogs, type DialogOptions } from "./workspace-dialogs.js";
import { DEFAULT_PRESENTATION, normalizePresentation } from "./workspace-presentation.js";

function form(entries: Record<string, string | string[]>): FormData {
  const data = new FormData();
  for (const [key, value] of Object.entries(entries)) {
    if (Array.isArray(value)) for (const item of value) data.append(key, item);
    else data.append(key, value);
  }
  return data;
}

function dialogOptions(patch: Partial<DialogOptions> = {}): DialogOptions {
  return {
    locale: "en",
    layout: { groupBy: "wbs", ganttScale: "day", showRelationships: true, density: "compact" },
    sortColumns: [{ id: "name", label: "Activity Name" }],
    sortColumnId: "name",
    sortDirection: "asc",
    sortLevels: [{ columnId: "name", direction: "asc" }],
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
    tableFields: "1",
    tableLineNumbers: "1",
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

  assert.match(html, /name="rowHeight" min="18" max="40"[^>]*value="18"/);
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

test("a format-only Timescale edit does not reset the zoom picked from the toolbar", () => {
  const patch = readLayoutPatch(form({
    "timescale.interval": DEFAULT_PRESENTATION.timescale.interval,
    "timescale.fontSize": "12",
    "timescale.textColor": "#445566",
  }), DEFAULT_PRESENTATION);
  assert.equal(patch.ganttScale, undefined);
  assert.equal(patch.presentation?.timescale.fontSize, 12);
});

test("the Timescale dialog no longer duplicates the toolbar scale control", () => {
  const html = renderLayoutDialogs(dialogOptions());
  assert.doesNotMatch(html, /name="ganttScale"/);
  assert.match(html, /set by the Gantt scale buttons/);
});

test("Timescale dialog persists the header format and derives the tick scale", () => {
  const patch = readLayoutPatch(form({
    "timescale.interval": "week-day",
    "timescale.lines": "3",
    "timescale.dateFormat": "ordinal",
    "timescale.type": "week-of-year",
    "timescale.ordinalStart": "2026-01-05",
    "timescale.ordinalInterval": "day",
    "timescale.fontSize": "13",
    "timescale.textColor": "#102030",
    "timescale.backgroundColor": "#e0e6ee",
  }), DEFAULT_PRESENTATION);
  assert.equal(patch.ganttScale, "day");
  const timescale = patch.presentation?.timescale;
  assert.equal(timescale?.interval, "week-day");
  assert.equal(timescale?.lines, 3);
  assert.equal(timescale?.dateFormat, "ordinal");
  assert.equal(timescale?.type, "week-of-year");
  assert.equal(timescale?.ordinalStart, "2026-01-05");
  assert.equal(timescale?.ordinalInterval, "day");
  assert.equal(timescale?.fontSize, 13);
  assert.equal(timescale?.textColor, "#102030");
  assert.equal(timescale?.backgroundColor, "#e0e6ee");
});

test("WBS level colours are read per level and kept independent", () => {
  const patch = readLayoutPatch(form({
    "wbs.color.0": "#112233",
    "wbs.color.2": "#445566",
  }), DEFAULT_PRESENTATION);
  const colors = patch.presentation?.wbs.levelColors ?? [];
  assert.equal(colors[0], "#112233");
  assert.equal(colors[1], DEFAULT_PRESENTATION.wbs.levelColors[1]);
  assert.equal(colors[2], "#445566");
  assert.equal(patch.presentation?.table.rowHeight, DEFAULT_PRESENTATION.table.rowHeight);
});

test("Timescale and User Preferences dialogs expose the persisted controls", () => {
  const html = renderLayoutDialogs(dialogOptions());
  assert.match(html, /name="timescale.interval"[\s\S]*?value="quarter-month" selected/);
  assert.match(html, /name="timescale.lines"/);
  assert.match(html, /name="timescale.dateFormat"/);
  assert.match(html, /name="timescale.ordinalInterval"/);
  assert.match(html, /name="timescale.textColor" value="#000000"/);
  assert.match(html, /name="wbs.color.0" value="#0000ff"/);
  assert.match(html, /name="wbs.color.5" value="#d9b3ff"/);
  assert.match(html, /Fiscal year, shift and hour intervals are not rendered/);
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

test("Bar Settings reads the calendar nonwork necking toggle per bar", () => {
  const off = readLayoutPatch(form({ "bar.task.filter": "task" }), DEFAULT_PRESENTATION);
  assert.equal(off.presentation?.bars.task.necking, false);
  const on = readLayoutPatch(form({ "bar.critical.filter": "critical", "bar.critical.necking": "on" }), DEFAULT_PRESENTATION);
  assert.equal(on.presentation?.bars.critical.necking, true);
});

test("Gantt chart options persist labels, legend, sight lines and lines", () => {
  const patch = readLayoutPatch(form({
    "gantt.showBarLabels": "on",
    "gantt.labelFontSize": "13",
    "gantt.labelColor": "#223344",
    "gantt.legend.visible": "on",
    "gantt.legend.position": "top",
    "gantt.sightLines.beforeSummaries": "on",
    "gantt.sightLines.rowInterval": "4",
    "gantt.sightLines.minorVertical": "on",
    "gantt.dataDateLine.visible": "on",
    "gantt.dataDateLine.style": "dashed",
    "gantt.dataDateLine.thickness": "3",
    "gantt.dataDateLine.color": "#00aa55",
    "gantt.progressLine.visible": "on",
    "gantt.progressLine.thickness": "2",
    "gantt.progressLine.color": "#ff8800",
  }), DEFAULT_PRESENTATION);
  const gantt = patch.presentation?.gantt;
  assert.equal(gantt?.showBarLabels, true);
  assert.equal(gantt?.labelFontSize, 13);
  assert.equal(gantt?.labelColor, "#223344");
  assert.deepEqual(gantt?.legend, { visible: true, position: "top" });
  assert.deepEqual(gantt?.sightLines, { beforeSummaries: true, rowInterval: 4, minorVertical: true });
  assert.deepEqual(gantt?.dataDateLine, { visible: true, style: "dashed", thickness: 3, color: "#00aa55" });
  assert.deepEqual(gantt?.progressLine, { visible: true, thickness: 2, color: "#ff8800" });
});

test("a disabled Data Date fieldset keeps the saved line settings", () => {
  const previous = normalizePresentation({
    gantt: { dataDateLine: { visible: true, style: "dotted", thickness: 2, color: "#112233" } },
  });
  const patch = readLayoutPatch(form({
    "gantt.legend.visible": "on",
    "gantt.legend.position": "bottom",
    "gantt.progressLine.thickness": "1",
    "gantt.progressLine.color": "#7030a0",
  }), previous);
  assert.deepEqual(patch.presentation?.gantt.dataDateLine, previous.gantt.dataDateLine);
  assert.equal(patch.presentation?.gantt.legend.visible, true);
});

test("Gantt chart options clamp out-of-range values and reject invalid colours", () => {
  const patch = readLayoutPatch(form({
    "gantt.labelFontSize": "40",
    "gantt.labelColor": "purple",
    "gantt.sightLines.rowInterval": "99",
    "gantt.dataDateLine.style": "dashed",
    "gantt.dataDateLine.thickness": "0",
    "gantt.progressLine.thickness": "0",
  }), DEFAULT_PRESENTATION);
  const gantt = patch.presentation?.gantt;
  assert.equal(gantt?.labelFontSize, 16);
  assert.equal(gantt?.labelColor, DEFAULT_PRESENTATION.gantt.labelColor);
  assert.equal(gantt?.sightLines.rowInterval, 10);
  assert.equal(gantt?.dataDateLine.thickness, 1);
  assert.equal(gantt?.progressLine.thickness, 1);
});

test("Gantt chart options render with an honest Data Date state", () => {
  const withoutDate = renderLayoutDialogs(dialogOptions());
  assert.match(withoutDate, /data-gantt-options/);
  assert.match(withoutDate, /name="gantt\.showBarLabels"/);
  assert.match(withoutDate, /name="gantt\.legend\.position"/);
  assert.match(withoutDate, /name="gantt\.sightLines\.rowInterval"/);
  assert.match(withoutDate, /name="gantt\.progressLine\.color"/);
  assert.match(withoutDate, /This project&#39;s read model exposes no Data Date/);
  assert.match(withoutDate, /<fieldset class="cp-dialog-group" disabled>\s*<legend>Data Date line/);

  const withDate = renderLayoutDialogs(dialogOptions({ dataDate: "2026-09-03" }));
  assert.match(withDate, /The Data Date line marks the project data date/);
  assert.match(withDate, /<fieldset class="cp-dialog-group">\s*<legend>Data Date line/);
  assert.match(withDate, /name="gantt\.dataDateLine\.style"/);
});

test("every bar editor exposes the necking checkbox", () => {
  const html = renderLayoutDialogs(dialogOptions());
  for (const kind of ["task", "critical", "summary", "milestone", "progress", "actual", "baseline"]) {
    assert.match(html, new RegExp(`name="bar\\.${kind}\\.necking"`));
  }
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

test("Group and Sort exposes three ordered sort levels and reads them in order", () => {
  const html = renderLayoutDialogs(dialogOptions({
    sortColumns: [{ id: "name", label: "Activity Name" }, { id: "progress", label: "Progress" }],
    sortLevels: [
      { columnId: "name", direction: "desc" },
      { columnId: "progress", direction: "asc" },
    ],
  }));
  for (const index of [0, 1, 2]) {
    assert.match(html, new RegExp(`name="sort\\.field\\.${index}"`));
    assert.match(html, new RegExp(`name="sort\\.direction\\.${index}"`));
  }
  assert.match(html, /name="sort\.field\.0"[\s\S]*?<option value="name" selected>/);
  assert.match(html, /name="sort\.field\.1"[\s\S]*?<option value="progress" selected>/);

  const patch = readLayoutPatch(form({
    "sort.field.0": "name",
    "sort.direction.0": "desc",
    "sort.field.1": "progress",
    "sort.direction.1": "asc",
    "sort.field.2": "",
  }));
  assert.deepEqual(patch.sortLevels, [
    { columnId: "name", direction: "desc" },
    { columnId: "progress", direction: "asc" },
  ]);
  assert.equal(patch.sortColumnId, "name");
  assert.equal(patch.sortDirection, "desc");
});

test("default layout patch keeps the professional compact defaults", () => {
  const defaults = defaultLayoutPatch();
  assert.equal(defaults.rowHeight, 18);
  assert.equal(defaults.fontSize, 11);
  assert.equal(defaults.rowHeightMode, "fixed");
  assert.equal(defaults.showIcons, true);
  assert.equal(defaults.lineNumbers, false);
  assert.deepEqual(defaults.presentation, DEFAULT_PRESENTATION);
  assert.equal(defaults.groupBy, "wbs");
  assert.equal(defaults.ganttScale, "month");
});

test("Filters dialog exposes the version 26 list, scope categories and actions", () => {
  const html = renderLayoutDialogs(dialogOptions());
  assert.match(html, /data-desktop-dialog="filters"/);
  assert.match(html, /name="filterAllActivities"/);
  assert.match(html, /name="filterCombine" value="all"/);
  assert.match(html, /name="filterCombine" value="any"/);
  assert.match(html, /name="filterApplyMode" value="replace"/);
  assert.match(html, /name="filterApplyMode" value="highlight"/);
  assert.match(html, /name="filterSelected" value="builtin:in-progress"/);
  assert.match(html, /name="filterSelected" value="builtin:completed"/);
  assert.match(html, /name="filterSelected" value="builtin:critical"/);
  assert.match(html, /data-filter-group="default"/);
  assert.match(html, /data-filter-group="global"/);
  assert.match(html, /data-filter-group="layout"/);
  assert.match(html, /data-filter-group="user"/);
  assert.match(html, /data-filter-new/);
  assert.match(html, /data-filter-modify/);
  for (const action of ["apply", "delete", "copy", "paste", "make-global", "copy-as-layout"]) {
    assert.match(html, new RegExp(`name="filterAction" value="${action}"`));
  }
  assert.match(html, /name="filterName"/);
  assert.match(html, /name="filterScope"/);
  assert.match(html, /name="filterMatch"/);
  assert.match(html, /name="filterEditingId"/);
  for (let index = 0; index < 2; index += 1) {
    assert.match(html, new RegExp(`name="filter\\.field\\.${index}"`));
    assert.match(html, new RegExp(`name="filter\\.operator\\.${index}"`));
    assert.match(html, new RegExp(`name="filter\\.value\\.${index}"`));
    assert.match(html, new RegExp(`name="filter\\.high\\.${index}"`));
  }
  assert.match(html, /data-filter-row-add/);
  assert.match(html, /data-filter-high/);
  assert.match(html, /data-filter-preview/);
  assert.match(html, /id="cp-filter-date-tokens"/);
  assert.match(html, /data-filter-field-type="text"/);
  assert.match(html, /does not contain/);
  assert.match(html, /data-filter-row-move="up"/);
  assert.match(html, /data-filter-row-remove/);
});

test("checking predefined filters applies every checked filter", () => {
  const patch = readLayoutPatch(form({
    filterList: "v26",
    filterSelected: ["builtin:completed", "builtin:critical"],
    filterCombine: "any",
    filterApplyMode: "highlight",
  }), DEFAULT_PRESENTATION);
  const filters = patch.presentation?.filters;
  assert.deepEqual(filters?.selectedIds, ["builtin:completed", "builtin:critical"]);
  assert.equal(filters?.activeId, "builtin:completed");
  assert.equal(filters?.combine, "any");
  assert.equal(filters?.applyMode, "highlight");
  assert.equal(filters?.allActivities, false);
  assert.equal(filters?.saved.length, 0);
});

test("All Activities clears the visible selection without deleting filters", () => {
  const previous = {
    ...DEFAULT_PRESENTATION,
    filters: {
      saved: [{
        id: "custom:civil-open",
        name: "Civil open",
        match: "all" as const,
        scope: "layout" as const,
        criteria: [{ fieldId: "wbs" as const, operator: "contains" as const, value: "Civil" }],
      }],
      activeId: "custom:civil-open",
      selectedIds: ["custom:civil-open"],
    },
  };
  const patch = readLayoutPatch(form({ filterList: "v26", filterAllActivities: "on" }), previous);
  assert.equal(patch.presentation?.filters.allActivities, true);
  assert.deepEqual(patch.presentation?.filters.selectedIds, ["custom:civil-open"]);
});

test("a custom filter is saved with its category and becomes selected", () => {
  const patch = readLayoutPatch(form({
    filterList: "v26",
    filterName: "Civil open",
    filterScope: "global",
    filterMatch: "all",
    "filter.field.0": "wbs",
    "filter.operator.0": "contains",
    "filter.value.0": "Civil",
    "filter.field.1": "activity_status",
    "filter.operator.1": "not-equals",
    "filter.value.1": "Completed",
  }), DEFAULT_PRESENTATION);
  const filters = patch.presentation?.filters;
  assert.equal(filters?.activeId, "custom:civil-open");
  assert.equal(filters?.saved.length, 1);
  assert.equal(filters?.saved[0].scope, "global");
  assert.equal(filters?.saved[0].criteria.length, 2);
  assert.deepEqual(filters?.selectedIds, ["custom:civil-open"]);
});

test("Modify keeps the saved filter id instead of creating a duplicate", () => {
  const previous = {
    ...DEFAULT_PRESENTATION,
    filters: {
      saved: [{
        id: "custom:civil-open",
        name: "Civil open",
        match: "all" as const,
        scope: "layout" as const,
        criteria: [{ fieldId: "wbs" as const, operator: "contains" as const, value: "Civil" }],
      }],
      activeId: "custom:civil-open",
      selectedIds: ["custom:civil-open"],
    },
  };
  const patch = readLayoutPatch(form({
    filterList: "v26",
    filterSelected: "custom:civil-open",
    filterEditingId: "custom:civil-open",
    filterName: "Civil open",
    filterScope: "layout",
    filterMatch: "all",
    "filter.field.0": "wbs",
    "filter.operator.0": "contains",
    "filter.value.0": "Civil works",
  }), previous);
  const filters = patch.presentation?.filters;
  assert.equal(filters?.saved.length, 1);
  assert.equal(filters?.saved[0].id, "custom:civil-open");
  assert.equal(filters?.saved[0].criteria[0].value, "Civil works");
});

test("choosing a predefined filter applies it without creating a custom filter (legacy payload)", () => {
  const patch = readLayoutPatch(form({
    filterActiveId: "builtin:completed",
    filterName: "",
    filterMatch: "all",
    "filter.field.0": "wbs",
    "filter.operator.0": "contains",
    "filter.value.0": "",
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
        scope: "layout" as const,
        criteria: [{ fieldId: "wbs" as const, operator: "contains" as const, value: "Civil" }],
      }],
      activeId: "custom:civil-open",
    },
  };
  const patch = readLayoutPatch(form({
    filterList: "v26",
    filterSelected: "custom:civil-open",
    filterAction: "delete",
  }), saved);
  assert.equal(patch.presentation?.filters.activeId, null);
  assert.equal(patch.presentation?.filters.saved.length, 0);
});

test("Delete refuses default filters", () => {
  const patch = readLayoutPatch(form({
    filterList: "v26",
    filterSelected: "builtin:critical",
    filterAction: "delete",
  }), DEFAULT_PRESENTATION);
  // The selection still applies; the default filter itself is never removed.
  assert.equal(patch.presentation?.filters.selectedIds?.[0], "builtin:critical");
  assert.equal(patch.presentation?.filters.saved.length, 0);
});

test("Make Global converts a layout filter and Copy as Layout adds a layout copy", () => {
  const layoutFilter = {
    ...DEFAULT_PRESENTATION,
    filters: {
      saved: [{
        id: "custom:civil-open",
        name: "Civil open",
        match: "all" as const,
        scope: "layout" as const,
        criteria: [{ fieldId: "wbs" as const, operator: "contains" as const, value: "Civil" }],
      }],
      activeId: "custom:civil-open",
      selectedIds: ["custom:civil-open"],
    },
  };
  const global = readLayoutPatch(form({
    filterList: "v26",
    filterSelected: "custom:civil-open",
    filterAction: "make-global",
  }), layoutFilter).presentation?.filters;
  assert.equal(global?.saved[0].scope, "global");

  const copy = readLayoutPatch(form({
    filterList: "v26",
    filterSelected: "builtin:critical",
    filterAction: "copy-as-layout",
  }), DEFAULT_PRESENTATION).presentation?.filters;
  assert.equal(copy?.saved.length, 1);
  assert.equal(copy?.saved[0].scope, "layout");
  assert.equal(copy?.saved[0].criteria[0].fieldId, "is_critical");
  assert.deepEqual(copy?.selectedIds, [copy?.saved[0].id]);
});

test("Copy and Paste move a filter into the chosen category", () => {
  const previous = {
    ...DEFAULT_PRESENTATION,
    filters: {
      saved: [{
        id: "custom:civil-open",
        name: "Civil open",
        match: "all" as const,
        scope: "layout" as const,
        criteria: [{ fieldId: "wbs" as const, operator: "contains" as const, value: "Civil" }],
      }],
      activeId: "custom:civil-open",
      selectedIds: ["custom:civil-open"],
    },
  };
  const copied = readLayoutPatch(form({
    filterList: "v26",
    filterSelected: "custom:civil-open",
    filterAction: "copy",
  }), previous);
  // Copy alone only fills the clipboard, so the layout is unchanged.
  assert.equal(copied.presentation, undefined);
  const pasted = readLayoutPatch(form({
    filterList: "v26",
    filterSelected: "custom:civil-open",
    filterAction: "paste",
    filterScope: "global",
  }), previous);
  const filters = pasted.presentation?.filters;
  assert.equal(filters?.saved.length, 2);
  assert.equal(filters?.saved[0].scope, "global");
  assert.equal(filters?.saved[0].name, "Civil open");
  assert.deepEqual(filters?.selectedIds, [filters?.saved[0].id]);
});

test("a filter draft reads dynamic criterion rows, their order and the high value", () => {
  const patch = readLayoutPatch(form({
    filterList: "v26",
    filterName: "Lookahead",
    filterScope: "layout",
    filterMatch: "all",
    "filter.field.0": "start",
    "filter.operator.0": "within-range",
    "filter.value.0": "CD",
    "filter.high.0": "CD+6w",
    "filter.field.2": "progress",
    "filter.operator.2": "less-than",
    "filter.value.2": "100",
  }), DEFAULT_PRESENTATION);
  const saved = patch.presentation?.filters.saved ?? [];
  assert.equal(saved.length, 1);
  assert.equal(saved[0].name, "Lookahead");
  assert.deepEqual(saved[0].criteria, [
    { fieldId: "start", operator: "within-range", value: "CD", highValue: "CD+6w" },
    { fieldId: "progress", operator: "less-than", value: "100" },
  ]);
  assert.equal(saved[0].match, "all");
  assert.equal(saved[0].scope, "layout");
});

test("criterion rows render typed operators, the High value column and local row actions", () => {
  const range = filterCriterionRowMarkup(2, "fa", { fieldId: "start", operator: "within-range", value: "CD", highValue: "CF" });
  assert.match(range, /data-filter-row="2"/);
  assert.match(range, /data-filter-field-type="date"/);
  assert.match(range, /name="filter\.field\.2"/);
  assert.match(range, /name="filter\.high\.2"[^>]*value="CF"/);
  assert.match(range, /list="cp-filter-date-tokens"/);
  assert.match(range, /در بازهٔ/);
  assert.match(range, /data-filter-row-move="up"/);
  assert.match(range, /data-filter-row-remove/);
  assert.doesNotMatch(range, /name="filter\.high\.2"[^>]* hidden/);

  const text = filterCriterionRowMarkup(0, "en");
  assert.match(text, /data-filter-field-type="text"/);
  assert.match(text, /does not contain/);
  assert.doesNotMatch(text, /is within range of/);
  assert.doesNotMatch(text, /data-filter-join(?![^>]*hidden)/);
});

test("Table Font and Row resets every table value to the shipped defaults", () => {
  const patch = readLayoutPatch(form({
    rowHeight: "33",
    fontSize: "15",
    fontFamily: "cairo",
    textColor: "#123abc",
    backgroundColor: "#000000",
    rowHeightMode: "content",
    showIcons: "on",
    lineNumbers: "on",
    tableFields: "1",
    tableLineNumbers: "1",
    tableReset: "1",
  }));
  assert.deepEqual(patch.presentation?.table, DEFAULT_PRESENTATION.table);
  assert.deepEqual(
    JSON.parse(JSON.stringify(patch.presentation?.timescale)),
    JSON.parse(JSON.stringify(DEFAULT_PRESENTATION.timescale)),
  );
  assert.deepEqual(
    JSON.parse(JSON.stringify(patch.presentation?.bars)),
    JSON.parse(JSON.stringify(DEFAULT_PRESENTATION.bars)),
  );
  const html = renderLayoutDialogs(dialogOptions());
  assert.match(html, /name="tableReset" value="1"/);
  assert.match(html, /Reset to defaults/);
});

test("clearing Show activity type icons is persisted, not dropped as an unchecked box", () => {
  const patch = readLayoutPatch(form({ tableFields: "1" }));
  assert.equal(patch.showIcons, false);
  assert.equal(patch.presentation?.table.showIcons, false);
  const preferences = readLayoutPatch(form({ tableFields: "1", tableLineNumbers: "1" }));
  assert.equal(preferences.lineNumbers, false);
  assert.equal(preferences.presentation?.table.lineNumbers, false);
});
