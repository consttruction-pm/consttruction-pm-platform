import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  addGridField, createP6GridPresentation, reorderGridFields,
  setGridFilters, setGridGroups, setGridSorts, updateGridField,
} from "./p6-activity-wbs-grid.js";
import type { FieldRegistry, LayoutDefinition } from "./p6-field-layout-foundation.js";

const registry: FieldRegistry = {
  registry_version: "p6-field-registry.v1",
  reference_product: "Oracle Primavera P6 Professional",
  reference_version: "P6-compatible",
  status: "active",
  fields: [
    { field_id: "activity_id", subject_area: "Activity", p6_field: "ActivityID", display_name: "Activity ID", data_type: "string", writable: true, computed: false, disposition: "implemented" },
    { field_id: "activity_name", subject_area: "Activity", p6_field: "ActivityName", display_name: "Activity Name", data_type: "string", writable: true, computed: false, disposition: "implemented" },
    { field_id: "start", subject_area: "Activity", p6_field: "StartDate", display_name: "Start", data_type: "date", writable: false, computed: true, disposition: "implemented" },
  ],
};
const layout: LayoutDefinition = {
  schema_version: "p6-layout.v1", scope: "project", view_id: "activity", revision: 1,
  columns: [{ field_id: "activity_id", visible: true, order: 0, label: "Activity ID", width: 120, alignment: "start", pinned: false, frozen: false }],
};

describe("P6 Activity/WBS grid integration", () => {
  it("builds an activity presentation from the authoritative registry", () => {
    const model = createP6GridPresentation("activity", registry, layout);
    assert.deepEqual(model.fields.map((field) => field.field_id), ["activity_id"]);
  });
  it("adds and updates a registry-backed field without changing identity", () => {
    const added = addGridField(registry, layout, "activity_name");
    const updated = updateGridField(registry, added, "activity_name", { width: 240, alignment: "start", pinned: true });
    assert.equal(updated.columns[1].field_id, "activity_name");
    assert.equal(updated.columns[1].width, 240);
    assert.equal(updated.columns[1].pinned, true);
  });
  it("reorders only requested layout fields", () => {
    const added = addGridField(registry, layout, "activity_name");
    const reordered = reorderGridFields(registry, added, ["activity_name", "activity_id"]);
    assert.deepEqual(reordered.columns.map((column) => column.field_id), ["activity_name", "activity_id"]);
  });
  it("requires sort/group/filter fields to exist in the shared registry", () => {
    assert.deepEqual(setGridSorts(registry, [
      { field_id: "activity_name", direction: "ascending", order: 9 },
      { field_id: "activity_id", direction: "descending", order: 2 },
    ]), [
      { field_id: "activity_id", direction: "descending", order: 0 },
      { field_id: "activity_name", direction: "ascending", order: 1 },
    ]);
    assert.deepEqual(setGridGroups(registry, [{ field_id: "activity_name", order: 4 }]), [{ field_id: "activity_name", order: 0 }]);
    assert.equal(setGridFilters(registry, [{ field_id: "activity_name", operator: "contains", value: "pump" }]).length, 1);
    assert.throws(() => setGridSorts(registry, [{ field_id: "missing", direction: "ascending", order: 0 }]), /Unknown P6 field: missing/);
  });
});
