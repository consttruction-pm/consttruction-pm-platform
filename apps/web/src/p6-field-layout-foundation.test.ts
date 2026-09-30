import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  addField,
  applyFormulaAuthority,
  createColumnPresentation,
  removeField,
  reorderFields,
  updateFieldPresentation,
  type FormulaEditorModel,
  type LayoutDefinition,
  type P6Field,
} from "./p6-field-layout-foundation.js";

const name: P6Field = {
  field_id: "activity_name",
  subject_area: "Activity",
  p6_field: "ActivityName",
  display_name: "Activity Name",
  data_type: "string",
  writable: true,
  computed: false,
  disposition: "implemented",
};

const start: P6Field = {
  ...name,
  field_id: "start",
  p6_field: "StartDate",
  display_name: "Start",
  data_type: "date",
  writable: false,
  computed: true,
};

function layout(): LayoutDefinition {
  return {
    schema_version: "p6-layout.v1",
    scope: "project",
    view_id: "activity-grid",
    revision: 0,
    columns: [createColumnPresentation(name, 0)],
  };
}

describe("P6 field/layout foundation", () => {
  it("adds, removes and reorders registry-backed fields", () => {
    const added = addField(layout(), start);
    assert.deepEqual(added.columns.map((x) => x.field_id), ["activity_name", "start"]);

    const reordered = reorderFields(added, ["start", "activity_name"]);
    assert.deepEqual(reordered.columns.map((x) => x.field_id), ["start", "activity_name"]);

    const removed = removeField(reordered, "start");
    assert.deepEqual(removed.columns.map((x) => x.field_id), ["activity_name"]);
  });

  it("updates presentation without changing field identity", () => {
    const updated = updateFieldPresentation(layout(), "activity_name", {
      label: "نام فعالیت",
      width: 280,
      alignment: "start",
      pinned: true,
      frozen: true,
      visible: false,
    });
    assert.equal(updated.columns[0].field_id, "activity_name");
    assert.equal(updated.columns[0].width, 280);
    assert.equal(updated.columns[0].pinned, true);
    assert.equal(updated.columns[0].frozen, true);
    assert.equal(updated.columns[0].visible, false);
  });

  it("accepts authoritative formula validation/dependency/type results only", () => {
    const model: FormulaEditorModel = {
      field_id: "custom_01",
      expression: "[Start] + 1",
      authoritative: null,
    };
    const result = {
      validation: { valid: true, error_code: null, message_key: null },
      dependencies: { field_ids: ["start"] },
      result_type: { data_type: "date" as const },
    };
    const next = applyFormulaAuthority(model, result);
    assert.equal(next.authoritative?.validation.valid, true);
    assert.deepEqual(next.authoritative?.dependencies.field_ids, ["start"]);
    assert.equal(next.authoritative?.result_type.data_type, "date");
  });

  it("rejects duplicate or incomplete reorder operations", () => {
    assert.throws(() => addField(layout(), name), /FIELD_ALREADY_IN_LAYOUT/);
    assert.throws(() => reorderFields(layout(), ["missing"]), /INVALID_LAYOUT_ORDER/);
  });
});
