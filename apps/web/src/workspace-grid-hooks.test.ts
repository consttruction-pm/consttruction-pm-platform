import test from "node:test";
import assert from "node:assert/strict";
import {
  createEmptyGridQuery,
  createReportPrintSelection,
  normalizeGridQuery,
  projectGridColumns,
} from "./workspace-grid-hooks.js";
import { projectFieldCatalogEntry } from "./p6-field-registry-client.js";
import { createDefaultLayout, setColumnLabel, setColumnState, reorderColumn } from "./workspace-layout.js";
import { createWorkspaceState, withActivities } from "./workspace-model.js";

const catalog = [
  projectFieldCatalogEntry({
    contract_version: "p6-field-registry-api.v1",
    kind: "field",
    scope: { tenant_id: "t1", project_id: "p1", project_revision: 1 },
    registry_version: "1",
    field: {
      field_id: "activity_id",
      subject_area: "activity",
      p6_field: "TASK_ID",
      display_name: "Activity ID",
      data_type: "string",
      writable: false,
      computed: false,
      unit: null,
    },
  }),
  projectFieldCatalogEntry({
    contract_version: "p6-field-registry-api.v1",
    kind: "field",
    scope: { tenant_id: "t1", project_id: "p1", project_revision: 1 },
    registry_version: "1",
    field: {
      field_id: "duration",
      subject_area: "activity",
      p6_field: "TARGET_DUR",
      display_name: "Duration",
      data_type: "duration",
      writable: false,
      computed: true,
      unit: "day",
    },
  }),
];

test("grid query drops fields outside the authoritative workspace catalog", () => {
  const state = createWorkspaceState({ tenant_id: "t1", project_id: "p1", revision: 1 });
  const query = normalizeGridQuery(state, {
    sort: [{ fieldId: "activity_name", direction: "asc" }, { fieldId: "removed", direction: "desc" }],
    group: [{ fieldId: "activity_id" }],
    filters: [{ fieldId: "removed", operator: "equals", value: "x" }],
  });
  assert.deepEqual(query.sort.map((x) => x.fieldId), ["activity_name"]);
  assert.deepEqual(query.group.map((x) => x.fieldId), ["activity_id"]);
  assert.equal(query.filters.length, 0);
  assert.deepEqual(createEmptyGridQuery().filters, []);
});

test("grid projection follows authoritative layout visibility, order, width, pin/freeze and label override", () => {
  const layout = reorderColumn(
    setColumnLabel(
      setColumnState(createDefaultLayout("activity-main", "activity", "project", 1, catalog), "duration", {
        visible: true,
        pinned: true,
        frozen: true,
        width: 180,
      }),
      "duration",
      "Dur.",
    ),
    "duration",
    0,
  );
  const columns = projectGridColumns(layout, catalog);
  assert.deepEqual(columns.map((column) => column.id), ["duration", "activity_id"]);
  assert.equal(columns[0].label, "Dur.");
  assert.equal(columns[0].width, 180);
  assert.equal(columns[0].pinned, true);
  assert.equal(columns[0].frozen, true);
});

test("authoritative catalog controls sort/filter eligibility", () => {
  const state = createWorkspaceState({ tenant_id: "t1", project_id: "p1", revision: 1 }, "en", "gregorian", catalog);
  const restrictedCatalog = catalog.map((field) =>
    field.id === "duration" ? { ...field, filterable: false, orderable: false } : field,
  );
  const query = normalizeGridQuery(state, {
    sort: [{ fieldId: "duration", direction: "asc" }, { fieldId: "activity_id", direction: "asc" }],
    group: [{ fieldId: "duration" }],
    filters: [
      { fieldId: "duration", operator: "gt", value: 2 },
      { fieldId: "activity_id", operator: "equals", value: "A1" },
    ],
  }, restrictedCatalog);
  assert.deepEqual(query.sort.map((x) => x.fieldId), ["activity_id"]);
  assert.deepEqual(query.group, []);
  assert.deepEqual(query.filters.map((x) => x.fieldId), ["activity_id"]);
});

test("report/print selection follows visible persisted layout", () => {
  let state = createWorkspaceState({ tenant_id: "t1", project_id: "p1", revision: 1 });
  state = withActivities(state, [
    { id: "a1", wbsId: "w1", code: "A1", name: "One" },
    { id: "a2", wbsId: "w1", code: "A2", name: "Two" },
  ]);
  const layout = createDefaultLayout("activity-main", "activity", "project", 1, catalog);
  const hidden = setColumnState(layout, "activity_id", { visible: false });
  const selection = createReportPrintSelection(state, [], ["a2"], false, hidden);
  assert.deepEqual(selection.columns.map((x) => x.id), ["duration"]);
  assert.deepEqual(selection.activityIds, ["a2"]);
  assert.equal(selection.includeGantt, false);
});
