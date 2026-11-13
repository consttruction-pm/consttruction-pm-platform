import assert from "node:assert/strict";
import test from "node:test";
import {
  activitiesForExport,
  activitiesToCsv,
  activityCellValue,
  activityExportFileName,
  activityExportScopeCount,
  computeActivityCounts,
} from "./workspace-activity-scope.js";
import type { WorkspaceActivityRow, WorkspaceColumn } from "./workspace-model.js";

const rows: WorkspaceActivityRow[] = [
  { id: "A100", wbsId: "W1", code: "A100", name: "Design, civil", cells: { activity_status: "In Progress", total_float: 5, is_critical: true } },
  { id: "A110", wbsId: "W1", code: "A110", name: "Procure", cells: { activity_status: "Not Started", total_float: 12, is_critical: false } },
  { id: "A120", wbsId: "W2", code: "A120", name: 'Say "go"', cells: { activity_status: "Completed", total_float: 0, is_critical: false } },
  { id: "A130", wbsId: "W2", code: "A130", name: "Line\nbreak", cells: { activity_status: "In Progress", total_float: null, is_critical: true } },
  { id: "A140", wbsId: "W3", code: "A140", name: "Commission", cells: { activity_status: "Not Started", total_float: 3, is_critical: false } },
];

const columns: WorkspaceColumn[] = [
  { id: "activity_id", label: "Activity ID", dataType: "text", editable: false, formula: null, width: 80, alignment: "start", pinned: true, frozen: false },
  { id: "activity_name", label: "Activity Name", dataType: "text", editable: false, formula: null, width: 160, alignment: "start", pinned: false, frozen: false },
  { id: "is_critical", label: "Critical", dataType: "boolean", editable: false, formula: null, width: 60, alignment: "center", pinned: false, frozen: false },
];

test("counts distinguish project, filter, search, visible, selected and in-scope selection", () => {
  const counts = computeActivityCounts({
    activities: rows,
    filterMatchedIds: new Set(["A100", "A130"]),
    scopeActivities: [rows[0], rows[3]],
    visibleIds: ["A100"],
    selectedIds: ["A100", "A110", "A999"],
  });
  assert.deepEqual(counts, {
    total: 5,
    filterMatched: 2,
    searchMatched: 2,
    visible: 1,
    selected: 2,
    selectedInScope: 1,
  });
});

test("collapsed rows stay in the filtered export scope", () => {
  const filtered = rows.slice(0, 2);
  const exported = activitiesForExport("filtered", {
    activities: rows,
    filtered,
    selectedIds: [],
  });
  assert.deepEqual(exported.map((row) => row.id), ["A100", "A110"]);
});

test("selected export is the in-memory selection, ordered like the scope", () => {
  const exported = activitiesForExport("selected", {
    activities: rows,
    filtered: [rows[2], rows[0], rows[4]],
    selectedIds: ["A120", "A100", "A999"],
  });
  assert.deepEqual(exported.map((row) => row.id), ["A120", "A100"]);
});

test("all export is exactly the authoritative read model", () => {
  const exported = activitiesForExport("all", {
    activities: rows,
    filtered: [rows[0]],
    selectedIds: ["A110"],
  });
  assert.equal(exported.length, rows.length);
  assert.deepEqual(exported.map((row) => row.id), rows.map((row) => row.id));
});

test("CSV escapes commas, quotes and newlines and never drops a stored value", () => {
  const csv = activitiesToCsv(rows, columns);
  const lines = csv.split("\r\n");
  assert.equal(lines[0], "Activity ID,Activity Name,Critical");
  assert.equal(lines[1], "A100,\"Design, civil\",true");
  assert.equal(lines[2], "A110,Procure,false");
  assert.equal(lines[3], "A120,\"Say \"\"go\"\"\",false");
  assert.equal(lines[4], "A130,\"Line\nbreak\",true");
  assert.equal(lines[5], "A140,Commission,false");
  assert.equal(lines.length, rows.length + 1);
});

test("identity aliases and stored cells resolve for export", () => {
  assert.equal(activityCellValue(rows[0], "activity_code"), "A100");
  assert.equal(activityCellValue(rows[0], "wbs"), "W1");
  assert.equal(activityCellValue(rows[0], "total_float"), 5);
  assert.equal(activityCellValue(rows[0], "missing_field"), null);
});

test("export file names are stable and project scoped", () => {
  assert.equal(activityExportFileName("filtered", "preview-rps-01"), "preview-rps-01-activities-filtered.csv");
  assert.equal(activityExportFileName("selected", "project / unsaved"), "project-unsaved-activities-selected.csv");
});

test("scope counts match the values shown in the export dialog", () => {
  const counts = { total: 5, filterMatched: 2, searchMatched: 2, visible: 1, selected: 2, selectedInScope: 1 };
  assert.equal(activityExportScopeCount("all", counts), 5);
  assert.equal(activityExportScopeCount("filtered", counts), 2);
  assert.equal(activityExportScopeCount("selected", counts), 2);
});
