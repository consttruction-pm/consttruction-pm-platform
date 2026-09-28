import test from "node:test";
import assert from "node:assert/strict";
import { buildWorkspaceColumnCatalog, dataTypeToEditorKind, layoutKey } from "./workspace-column-registry.js";
import type { P6FieldCatalogEntry } from "./p6-field-registry-client.js";

const fields: readonly P6FieldCatalogEntry[] = [
  { id: "activity_id", source: "standard", subjectArea: "activity", label: "Activity ID", dataType: "string", writable: false, computed: false, unit: null, filterable: true, orderable: true },
  { id: "duration", source: "standard", subjectArea: "activity", label: "Duration", dataType: "duration", writable: false, computed: true, unit: "day", filterable: true, orderable: true },
  { id: "cost", source: "standard", subjectArea: "project", label: "Cost", dataType: "cost", writable: true, computed: false, unit: "USD", filterable: true, orderable: true },
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
