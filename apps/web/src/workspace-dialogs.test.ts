import assert from "node:assert/strict";
import test from "node:test";

import { defaultLayoutPatch, readLayoutPatch, renderLayoutDialogs } from "./workspace-dialogs.js";

function form(entries: Record<string, string>): FormData {
  const data = new FormData();
  for (const [key, value] of Object.entries(entries)) data.append(key, value);
  return data;
}

test("Table Font and Row reads a real row height and font size", () => {
  const patch = readLayoutPatch(form({ rowHeight: "29", fontSize: "12" }));
  assert.equal(patch.rowHeight, 29);
  assert.equal(patch.fontSize, 12);
});

test("Table Font and Row clamps out-of-range values instead of applying them", () => {
  const small = readLayoutPatch(form({ rowHeight: "4", fontSize: "2" }));
  assert.equal(small.rowHeight, 18);
  assert.equal(small.fontSize, 10);

  const large = readLayoutPatch(form({ rowHeight: "99", fontSize: "40" }));
  assert.equal(large.rowHeight, 34);
  assert.equal(large.fontSize, 13);
});

test("Table Font and Row dialog exposes the persisted row height and font size", () => {
  const html = renderLayoutDialogs({
    locale: "en",
    layout: { groupBy: "wbs", ganttScale: "day", showRelationships: true, density: "compact" },
    sortColumns: [{ id: "name", label: "Activity Name" }],
    sortColumnId: "name",
    sortDirection: "asc",
    rowHeight: 26,
    fontSize: 12,
    barHeight: 16,
    barTone: "crimson",
  });

  assert.match(html, /name="rowHeight" min="18" max="34"[^>]*value="26"/);
  assert.match(html, /name="fontSize"/);
  assert.match(html, /<option value="12" selected>12 px<\/option>/);
  assert.doesNotMatch(html, /Primavera|Oracle|P6/);
});

test("a dialog without numeric fields does not reset visual preferences", () => {
  const patch = readLayoutPatch(form({ groupBy: "wbs", sortColumnId: "name", sortDirection: "asc" }));
  assert.equal(patch.groupBy, "wbs");
  assert.equal(patch.sortColumnId, "name");
  assert.equal(patch.rowHeight, undefined);
  assert.equal(patch.fontSize, undefined);
  assert.equal(patch.barHeight, undefined);
});

test("default layout patch keeps the professional compact defaults", () => {
  assert.deepEqual(defaultLayoutPatch(), {
    groupBy: "wbs",
    sortColumnId: "wbs",
    sortDirection: "asc",
    ganttScale: "day",
    showRelationships: true,
    density: "compact",
    rowHeight: 22,
    fontSize: 11,
    barHeight: 16,
    barTone: "crimson",
  });
});
