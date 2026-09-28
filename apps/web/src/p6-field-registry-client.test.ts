import test from "node:test";
import assert from "node:assert/strict";
import { projectFieldCatalogEntry, projectUdfCatalogEntry } from "./p6-field-registry-client.js";

const scope = { tenant_id: "t1", project_id: "p1", project_revision: 7 };

test("field projection preserves authoritative P6 field identity", () => {
  const entry = projectFieldCatalogEntry({
    contract_version: "p6-field-registry-api.v1",
    kind: "field",
    scope,
    registry_version: "p6-field-registry.v1",
    field: {
      field_id: "activity.planned_start",
      subject_area: "Activity",
      p6_field: "PlannedStartDate",
      display_name: "Planned Start",
      data_type: "date",
      writable: true,
      computed: false,
      unit: null,
    },
  });

  assert.equal(entry.id, "activity.planned_start");
  assert.equal(entry.p6Field, "PlannedStartDate");
  assert.equal(entry.nullable, null);
  assert.deepEqual(entry.allowedValues, []);
});

test("UDF projection preserves nullable and allowed-value metadata", () => {
  const entry = projectUdfCatalogEntry({
    contract_version: "p6-field-registry-api.v1",
    kind: "user_defined_field",
    scope,
    registry_version: "p6-field-registry.v1",
    udf: {
      udf_id: "udf.activity.phase",
      subject_area: "Activity",
      display_name: "Phase",
      data_type: "enum",
      writable: true,
      nullable: false,
      unit: null,
      allowed_values: ["A", "B"],
    },
  });

  assert.equal(entry.p6Field, "udf.activity.phase");
  assert.equal(entry.nullable, false);
  assert.deepEqual(entry.allowedValues, ["A", "B"]);
});
