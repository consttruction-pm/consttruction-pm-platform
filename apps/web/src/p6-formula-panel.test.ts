import assert from "node:assert/strict";
import test from "node:test";

import type { P6Field } from "./p6-field-layout-foundation.js";
import {
  getFormulaPanelLabels,
  renderFormulaAuthoritativeResult,
  renderFormulaColumnList,
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

test("formula panel exposes the persistence form and an honest empty catalogue", () => {
  const html = renderFormulaEditorForm(
    [field("activity.planned_duration", "Planned Duration")],
    getFormulaPanelLabels("en"),
  );
  assert.match(html, /data-formula-save-form/);
  assert.match(html, /data-formula-title/);
  assert.match(html, /data-formula-id/);
  assert.match(html, /formula\.my_column/);
  assert.match(html, /No formula columns are saved/);
});

test("saved formula columns render title, id, result type and expression", () => {
  const html = renderFormulaColumnList(
    [
      {
        contract_version: "p6-formula-column-api.v1",
        kind: "formula_column",
        scope: { tenant_id: "t1", project_id: "p1", project_revision: 1 },
        formula: {
          formula_id: "formula.double_progress",
          version: "1",
          title: "Double Progress",
          expression: "[activity.percent_complete] * 2",
          result_type: "number",
          data_type: "double",
          result_unit: null,
          dependencies: ["activity.percent_complete"],
        },
      },
    ],
    getFormulaPanelLabels("en"),
  );
  assert.match(html, /data-formula-column="formula.double_progress"/);
  assert.match(html, /Double Progress/);
  assert.match(html, /\[activity\.percent_complete\] \* 2/);
  assert.match(html, /double/);
  assert.doesNotMatch(html, /Oracle|Primavera/i);
});

test("formula catalogue escapes stored values", () => {
  const html = renderFormulaColumnList(
    [
      {
        contract_version: "p6-formula-column-api.v1",
        kind: "formula_column",
        scope: { tenant_id: "t1", project_id: "p1", project_revision: 1 },
        formula: {
          formula_id: "formula.bad",
          version: "1",
          title: "<script>alert(1)</script>",
          expression: "\"><img src=x>",
          result_type: "text",
          data_type: "string",
          result_unit: null,
          dependencies: [],
        },
      },
    ],
    getFormulaPanelLabels("en"),
  );
  assert.doesNotMatch(html, /<script>/);
  assert.doesNotMatch(html, /<img/);
});
