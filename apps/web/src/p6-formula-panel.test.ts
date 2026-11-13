import assert from "node:assert/strict";
import test from "node:test";

import type { P6Field } from "./p6-field-layout-foundation.js";
import type { P6FormulaColumnRecord } from "./p6-formula-api.js";
import {
  describeFormulaValidationError,
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

function savedColumn(overrides: Partial<P6FormulaColumnRecord["formula"]> = {}): P6FormulaColumnRecord {
  return {
    contract_version: "p6-formula-column-api.v1",
    kind: "formula_column",
    scope: { tenant_id: "t1", project_id: "p1", project_revision: 3 },
    formula: {
      formula_id: "formula.double_progress",
      version: "4",
      title: "Double Progress",
      expression: "[activity.percent_complete] * 2",
      result_type: "number",
      data_type: "double",
      result_unit: null,
      dependencies: ["activity.percent_complete"],
      ...overrides,
    },
  };
}

test("read-only formula panel keeps validation but explains why it cannot save", () => {
  const html = renderFormulaEditorForm(
    [field("activity.planned_duration", "Planned Duration")],
    getFormulaPanelLabels("en"),
    { canWrite: false },
  );
  assert.match(html, /data-formula-form/);
  assert.doesNotMatch(html, /data-formula-save-form/);
  assert.match(html, /data-formula-readonly/);
  assert.match(html, /planner or project administrator/);
});

test("saved catalogue shows definition version, data type, unit and dependencies", () => {
  const html = renderFormulaColumnList(
    [savedColumn({ result_unit: "days" })],
    getFormulaPanelLabels("en"),
    { canWrite: true },
  );
  assert.match(html, /data-formula-version>Definition version 4/);
  assert.match(html, /data-formula-data-type>Data type: double/);
  assert.match(html, /data-formula-result-type>Result type: number/);
  assert.match(html, /data-formula-unit>days/);
  assert.match(html, /data-formula-dependencies>Referenced fields: <code>activity\.percent_complete<\/code>/);
  assert.match(html, /data-formula-apply="formula\.double_progress"/);
  assert.doesNotMatch(html, /data-formula-in-layout/);
});

test("a column already present in the layout shows an in-layout marker instead of apply", () => {
  const html = renderFormulaColumnList(
    [savedColumn()],
    getFormulaPanelLabels("en"),
    { canWrite: true, layoutFieldIds: ["formula.double_progress"] },
  );
  assert.match(html, /data-formula-in-layout>In layout/);
  assert.doesNotMatch(html, /data-formula-apply=/);
});

test("read-only catalogue never offers the layout apply action", () => {
  const html = renderFormulaColumnList(
    [savedColumn()],
    getFormulaPanelLabels("en"),
    { canWrite: false },
  );
  assert.doesNotMatch(html, /data-formula-apply=/);
  assert.doesNotMatch(html, /data-formula-in-layout/);
});

test("validation errors carry a plain-language message plus the authoritative code", () => {
  assert.equal(
    describeFormulaValidationError("DIVISION_BY_ZERO", "en"),
    "The expression divides by zero. Guard the divisor before saving.",
  );
  assert.match(describeFormulaValidationError("DIVISION_BY_ZERO", "fa"), /صفر تقسیم/);
  assert.match(describeFormulaValidationError("SOMETHING_NEW", "en"), /shared calculation core/);
  assert.equal(
    describeFormulaValidationError("FIELD_NOT_FOUND:activity.nope", "en"),
    'The expression references the field "activity.nope", which is not registered for this view.',
  );
  assert.match(
    describeFormulaValidationError("EXPECTED_EXPRESSION_AT_29", "en"),
    /incomplete \(expected expression\)/,
  );
  assert.match(
    describeFormulaValidationError("NUMERIC_OPERANDS_REQUIRED", "en"),
    /needs numeric operands/,
  );
  assert.match(
    describeFormulaValidationError("UNSUPPORTED_P6_FORMULA_FIELD_TYPE:duration", "en"),
    /Fields of type "duration"/,
  );

  const html = renderFormulaAuthoritativeResult(
    {
      expression: "[activity.planned_duration] / 0",
      validating: false,
      validation: { valid: false, error_code: "DIVISION_BY_ZERO", message_key: null },
      dependencyFieldIds: [],
      resultDataType: null,
    },
    "activity.planned_duration",
    getFormulaPanelLabels("en"),
    "en",
  );
  assert.match(html, /data-formula-error-message>The expression divides by zero/);
  assert.match(html, /DIVISION_BY_ZERO/);
  assert.doesNotMatch(html, /Result type/);
});
