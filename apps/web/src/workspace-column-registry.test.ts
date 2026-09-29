import test from "node:test";
import assert from "node:assert/strict";
import { applyWorkspaceLayout, buildWorkspaceColumnCatalog, buildWorkspaceColumnsFromFieldCatalog, dataTypeToEditorKind, layoutKey } from "./workspace-column-registry.js";
import { createDefaultLayout, reorderColumn, setColumnLabel, setColumnState } from "./workspace-layout.js";
import { createWorkspaceState } from "./workspace-model.js";
import type { P6FieldCatalogEntry } from "./p6-field-registry-client.js";

const fields: readonly P6FieldCatalogEntry[] = [
  { id: "activity_id", source: "standard", subjectArea: "activity", label: "Activity ID", dataType: "string", writable: false, computed: false, unit: null, nullable: null, allowedValues: [], p6Field: "ActivityId", filterable: true, orderable: true },
  { id: "duration", source: "standard", subjectArea: "activity", label: "Duration", dataType: "duration", writable: false, computed: true, unit: "day", nullable: null, allowedValues: [], p6Field: "Duration", filterable: true, orderable: true },
  { id: "cost", source: "standard", subjectArea: "project", label: "Cost", dataType: "cost", writable: true, computed: false, unit: "USD", nullable: null, allowedValues: [], p6Field: "Cost", filterable: true, orderable: true },
];

test("catalog is scoped to requested subject area and derives editability from authority", () => {
  const catalog = buildWorkspaceColumnCatalog("activity", fields);
  assert.deepEqual(catalog.map((x) => x.fieldId), ["activity_id", "duration"]);
  assert.equal(catalog[0].editable, false);
  assert.equal(catalog[1].computed, true);
});

test("editor kind follows the shared field data type", () => {
  assert.equal(dataTypeToEditorKind("percentage"), "number");
  assert.equal(dataTypeToEditorKind("duration"), "duration");
  assert.equal(dataTypeToEditorKind("date"), "date");
  assert.equal(dataTypeToEditorKind("boolean"), "boolean");
  assert.equal(dataTypeToEditorKind("enum"), "enum");
});

test("layout key isolates tenant/project/subject/scope/user", () => {
  const context = { tenant_id: "t1", project_id: "p1", revision: 7 };
  assert.equal(layoutKey(context, "activity", "project"), "t1:p1:activity:project");
  assert.equal(layoutKey(context, "activity", "user", "u1"), "t1:p1:activity:user:u1");
});

test("workspace columns are projected from the authoritative field catalog", () => {
  const columns = buildWorkspaceColumnsFromFieldCatalog(fields);
  assert.deepEqual(columns.map((x) => x.id), ["activity_id", "duration", "cost"]);
  assert.equal(columns[1].dataType, "duration");
  assert.equal(columns[2].dataType, "decimal");
  assert.equal(columns[2].editable, true);
  assert.equal(columns[0].formula, null);
});


test("persisted layout is applied to workspace state before rendering", () => {
  const context = { tenant_id: "t1", project_id: "p1", revision: 7 };
  const state = createWorkspaceState(context, "en", "gregorian", fields);
  let layout = createDefaultLayout("activity-main", "activity", "project", 7, fields);
  layout = setColumnState(layout, "duration", { visible: true, width: 180, pinned: true, frozen: true });
  layout = setColumnLabel(layout, "duration", "Dur.");
  layout = reorderColumn(layout, "duration", 0);

  const next = applyWorkspaceLayout(state, layout, fields);

  assert.deepEqual(next.columns.map((column) => column.id), ["duration", "activity_id"]);
  assert.equal(next.columns[0].label, "Dur.");
  assert.equal(next.columns[0].width, 180);
  assert.equal(next.columns[0].editable, false);
});

test("workspace layout cannot be applied across project revisions", () => {
  const state = createWorkspaceState({ tenant_id: "t1", project_id: "p1", revision: 7 }, "en", "gregorian", fields);
  const layout = createDefaultLayout("activity-main", "activity", "project", 8, fields);
  assert.throws(() => applyWorkspaceLayout(state, layout, fields), /WORKSPACE_LAYOUT_REVISION_MISMATCH/);
});
