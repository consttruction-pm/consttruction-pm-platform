import { describe, expect, it } from "vitest";
import {
  addGridField,
  createP6GridPresentation,
  reorderGridFields,
  setGridFilters,
  setGridGroups,
  setGridSorts,
  updateGridField,
} from "./p6-activity-wbs-grid";
import { FieldRegistry, LayoutDefinition } from "./p6-field-layout-foundation";

const registry: FieldRegistry = {
  registry_version: "p6-field-registry.v1",
  reference_product: "Oracle Primavera P6 Professional",
  fields: [
    { field_id: "activity_id", label: "Activity ID", data_type: "string" },
    { field_id: "activity_name", label: "Activity Name", data_type: "string" },
    { field_id: "start", label: "Start", data_type: "date" },
  ],
};

const layout: LayoutDefinition = {
  schema_version: "p6-layout.v1",
  scope: "project",
  view_id: "activity",
  revision: 1,
  columns: [
    {
      field_id: "activity_id",
      visible: true,
      order: 0,
      label: "Activity ID",
      width: 120,
      alignment: "left",
      pinned: false,
      frozen: false,
    },
  ],
};

describe("P6 Activity/WBS grid integration", () => {
  it("builds an activity presentation from the authoritative registry", () => {
    const model = createP6GridPresentation("activity", registry, layout);
    expect(model.fields.map((field) => field.field_id)).toEqual(["activity_id"]);
  });

  it("adds and updates a registry-backed field without changing field identity", () => {
    const added = addGridField(registry, layout, "activity_name");
    const updated = updateGridField(registry, added, "activity_name", {
      width: 240,
      alignment: "left",
      pinned: true,
    });
    expect(updated.columns[1].field_id).toBe("activity_name");
    expect(updated.columns[1].width).toBe(240);
    expect(updated.columns[1].pinned).toBe(true);
  });

  it("reorders only the requested layout fields", () => {
    const added = addGridField(registry, layout, "activity_name");
    const reordered = reorderGridFields(registry, added, [
      "activity_name",
      "activity_id",
    ]);
    expect(reordered.columns.map((column) => column.field_id)).toEqual([
      "activity_name",
      "activity_id",
    ]);
  });

  it("requires sort/group/filter fields to exist in the shared registry", () => {
    expect(setGridSorts(registry, [
      { field_id: "activity_name", direction: "ascending", order: 9 },
      { field_id: "activity_id", direction: "descending", order: 2 },
    ])).toEqual([
      { field_id: "activity_id", direction: "descending", order: 0 },
      { field_id: "activity_name", direction: "ascending", order: 1 },
    ]);

    expect(setGridGroups(registry, [
      { field_id: "activity_name", order: 4 },
    ])).toEqual([{ field_id: "activity_name", order: 0 }]);

    expect(setGridFilters(registry, [
      { field_id: "activity_name", operator: "contains", value: "pump" },
    ])).toHaveLength(1);

    expect(() => setGridSorts(registry, [
      { field_id: "missing", direction: "ascending", order: 0 },
    ])).toThrow("Unknown P6 field: missing");
  });
});
