import assert from "node:assert/strict";
import test from "node:test";

import type { P6Field } from "./p6-field-layout-foundation.js";
import {
  getFormulaPanelLabels,
  renderFormulaAuthoritativeResult,
  renderFormulaEditorForm,
} from "./p6-formula-panel.js";

function field(fieldId: string, displayName: string): P6Field {
  return {
    field_id: fieldId,
    subject_area: "Activity",
    p6_field: fieldId,
    display_name: displayName,
    data_type: "double",
    writable: false,
    computed: false,
    disposition: "registered",
  };
}

test("formula panel renders registered fields and bilingual labels", () => {
  const html = renderFormulaEditorForm(
    [field("activity.planned_duration", "Planned Duration")],
    getFormulaPanelLabels("en"),
  );
  assert.match(html, /Formula editor|Context field/);
  assert.match(html, /activity\.planned_duration/);
  assert.match(html, /data-formula-field/);
  assert.match(html, /data-formula-validate/);
  assert.match(html, /\[activity\.duration_percent_complete\] \/ 100/);
  assert.doesNotMatch(html, /Oracle|Primavera|\bP6\b|https?:\/\//i);

  const fa = renderFormulaEditorForm(
    [field("activity.planned_duration", "Planned Duration")],
    getFormulaPanelLabels("fa"),
  );
  assert.match(fa, /فیلد زمینه/);
  assert.match(fa, /اعتبارسنجی/);
});

test("formula panel shows an explicit empty state when no fields are registered", () => {
  const html = renderFormulaEditorForm([], getFormulaPanelLabels("en"));
  assert.match(html, /No registered fields/);
  assert.doesNotMatch(html, /data-formula-form/);
});

test("formula panel reports authoritative dependencies and result type", () => {
  const html = renderFormulaAuthoritativeResult(
    {
      expression: "planned_duration * 2",
      validating: false,
      validation: { valid: true, error_code: null, message_key: null },
      dependencyFieldIds: ["activity.planned_duration"],
      resultDataType: "double",
    },
    "activity.total_float",
    getFormulaPanelLabels("en"),
  );
  assert.match(html, /Valid expression/);
  assert.match(html, /activity\.planned_duration/);
  assert.match(html, /double/);
  assert.doesNotMatch(html, /undefined|null/);
});

test("invalid formula results show the authoritative error code and no invented type", () => {
  const html = renderFormulaAuthoritativeResult(
    {
      expression: "planned_duration + 1",
      validating: false,
      validation: {
        valid: false,
        error_code: "FORMULA_SELF_REFERENCE",
        message_key: "p6.formula.validation.error",
      },
      dependencyFieldIds: [],
      resultDataType: null,
    },
    "activity.planned_duration",
    getFormulaPanelLabels("en"),
  );
  assert.match(html, /Expression is not valid/);
  assert.match(html, /FORMULA_SELF_REFERENCE/);
  assert.doesNotMatch(html, /Result type/);
});
