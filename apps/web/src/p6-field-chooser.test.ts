import test from "node:test";
import assert from "node:assert/strict";
import { createP6FieldChooser } from "./p6-field-chooser.js";
import type { FieldRegistry, LayoutDefinition } from "./p6-field-layout-foundation.js";

const registry: FieldRegistry = {
  registry_version: "p6-field-registry.v1",
  reference_product: "Oracle Primavera P6 Professional",
  reference_version: "P6-compatible",
  status: "active",
  fields: [
    {
      field_id: "activity-id",
      subject_area: "activity",
      p6_field: "Activity ID",
      display_name: "Activity ID",
      data_type: "string",
      writable: true,
      computed: false,
      disposition: "standard",
    },
    {
      field_id: "activity-name",
      subject_area: "activity",
      p6_field: "Activity Name",
      display_name: "Activity Name",
      data_type: "string",
      writable: true,
      computed: false,
      disposition: "standard",
    },
    {
      field_id: "activity-duration",
      subject_area: "activity",
      p6_field: "Original Duration",
      display_name: "Original Duration",
      data_type: "duration",
      writable: true,
      computed: false,
      disposition: "standard",
    },
    {
      field_id: "wbs-code",
      subject_area: "wbs",
      p6_field: "WBS Code",
      display_name: "WBS Code",
      data_type: "string",
      writable: true,
      computed: false,
      disposition: "standard",
    },
  ],
};

const layout: LayoutDefinition = {
  schema_version: "p6-layout.v1",
  scope: "user",
  view_id: "activity",
  revision: 1,
  columns: [
    {
      field_id: "activity-id",
      visible: true,
      order: 0,
      width: 120,
      alignment: "start",
      pinned: false,
      frozen: false,
    },
  ],
};

test("filters registry-backed fields by search and subject area", () => {
  const chooser = createP6FieldChooser(registry, layout);

  assert.deepEqual(
    chooser.getAvailableFields().map((field) => field.field_id),
    ["activity-id", "activity-name", "activity-duration", "wbs-code"],
  );

  chooser.setSubjectArea("activity");
  chooser.setSearch("duration");

  assert.deepEqual(
    chooser.getAvailableFields().map((field) => field.field_id),
    ["activity-duration"],
  );
});

test("adds, removes, reorders, and updates presentation through shared layout contracts", () => {
  const chooser = createP6FieldChooser(registry, layout);

  chooser.add("activity-name");
  assert.deepEqual(
    chooser.getSelectedFields().map((field) => field.field_id),
    ["activity-id", "activity-name"],
  );

  chooser.updatePresentation("activity-name", {
    label: "Name",
    width: 240,
    alignment: "start",
    pinned: true,
    frozen: false,
  });

  assert.equal(chooser.getSelectedFields()[1].display_name, "Activity Name");

  chooser.reorder(["activity-name", "activity-id"]);
  assert.deepEqual(
    chooser.getSelectedFields().map((field) => field.field_id),
    ["activity-name", "activity-id"],
  );

  chooser.remove("activity-id");
  assert.deepEqual(
    chooser.getSelectedFields().map((field) => field.field_id),
    ["activity-name"],
  );
});

test("rejects a field outside the authoritative registry", () => {
  const chooser = createP6FieldChooser(registry, layout);

  assert.throws(() => chooser.add("client-only-field"), /UNKNOWN_FIELD/);
});
