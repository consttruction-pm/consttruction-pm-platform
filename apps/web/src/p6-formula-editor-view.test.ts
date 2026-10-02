import test from "node:test";
import assert from "node:assert/strict";
import { getP6FormulaEditorPresentation } from "./p6-formula-editor-view.js";
import type { P6FormulaEditorState } from "./p6-formula-editor.js";

function state(
  overrides: Partial<P6FormulaEditorState> = {},
): P6FormulaEditorState {
  return {
    field_id: "activity-cost",
    expression: "Original Duration * Units",
    validating: false,
    authoritative: {
      validation: { valid: true, error_code: null, message_key: null },
      dependencies: { field_ids: ["activity-duration", "activity-units"] },
      result_type: { data_type: "double" },
    },
    ...overrides,
  };
}

test("projects authoritative formula results for presentation without evaluating them", () => {
  assert.deepEqual(getP6FormulaEditorPresentation(state()), {
    expression: "Original Duration * Units",
    validating: false,
    validation: { valid: true, error_code: null, message_key: null },
    dependencyFieldIds: ["activity-duration", "activity-units"],
    resultDataType: "double",
  });
});

test("preserves authoritative invalid validation details", () => {
  const presentation = getP6FormulaEditorPresentation(
    state({
      authoritative: {
        validation: {
          valid: false,
          error_code: "UNKNOWN_FIELD",
          message_key: "formula.unknown_field",
        },
        dependencies: { field_ids: [] },
        result_type: { data_type: "double" },
      },
    }),
  );

  assert.equal(presentation.validation?.valid, false);
  assert.equal(presentation.validation?.error_code, "UNKNOWN_FIELD");
  assert.equal(presentation.validation?.message_key, "formula.unknown_field");
  assert.deepEqual(presentation.dependencyFieldIds, []);
  assert.equal(presentation.resultDataType, "double");
});

test("does not expose stale authoritative data before validation", () => {
  const presentation = getP6FormulaEditorPresentation(
    state({ authoritative: null }),
  );

  assert.equal(presentation.validation, null);
  assert.deepEqual(presentation.dependencyFieldIds, []);
  assert.equal(presentation.resultDataType, null);
});

test("returns defensive dependency and validation copies", () => {
  const original = state();
  const presentation = getP6FormulaEditorPresentation(original);

  (presentation.dependencyFieldIds as string[]).push("unexpected");
  assert.deepEqual(original.authoritative?.dependencies.field_ids, [
    "activity-duration",
    "activity-units",
  ]);
});
