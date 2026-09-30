import test from "node:test";
import assert from "node:assert/strict";
import { createP6FormulaGridBinding } from "./p6-formula-grid-binding.js";
import type {
  FieldRegistry,
  FormulaAuthoritativeResult,
  LayoutDefinition,
} from "./p6-field-layout-foundation.js";

const registry: FieldRegistry = {
  registry_version: "p6-field-registry.v1",
  reference_product: "Oracle Primavera P6 Professional",
  reference_version: "P6-compatible",
  status: "active",
  fields: [{
    field_id: "activity-cost",
    subject_area: "activity",
    p6_field: "Activity Cost",
    display_name: "Activity Cost",
    data_type: "cost",
    writable: false,
    computed: true,
    disposition: "standard",
  }],
};

const layout: LayoutDefinition = {
  schema_version: "p6-layout.v1",
  scope: "user",
  view_id: "activity",
  revision: 1,
  columns: [{
    field_id: "activity-cost",
    visible: true,
    order: 0,
    width: 160,
    alignment: "end",
    pinned: false,
    frozen: false,
  }],
};

const result: FormulaAuthoritativeResult = {
  validation: { valid: true, error_code: null, message_key: null },
  dependencies: { field_ids: ["activity-duration"] },
  result_type: { data_type: "cost" },
};

test("binds formula editor state to authoritative grid field metadata and presentation", async () => {
  const binding = createP6FormulaGridBinding(
    registry,
    layout,
    "activity-cost",
    { validate: async () => result },
    "Original Duration * Rate",
  );

  assert.equal(binding.getState().field.computed, true);
  assert.equal(binding.getState().presentation.width, 160);
  assert.equal(binding.getState().editor.authoritative, null);

  const state = await binding.validate();
  assert.equal(state.editor.authoritative?.validation.valid, true);
  assert.deepEqual(state.editor.authoritative?.dependencies.field_ids, ["activity-duration"]);
  assert.equal(state.editor.authoritative?.result_type.data_type, "cost");
});

test("rejects a field missing from the authoritative registry or layout", () => {
  assert.throws(
    () => createP6FormulaGridBinding(registry, layout, "missing", { validate: async () => result }),
    /UNKNOWN_FIELD/,
  );

  const missingPresentation = { ...layout, columns: [] };
  assert.throws(
    () => createP6FormulaGridBinding(registry, missingPresentation, "activity-cost", { validate: async () => result }),
    /FIELD_NOT_IN_LAYOUT/,
  );
});
