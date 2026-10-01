import assert from "node:assert/strict";
import test from "node:test";
import type { P6Field } from "./p6-field-layout-foundation.js";
import { coerceP6TypedFieldValue, renderP6TypedFieldEditor } from "./p6-typed-field-editor.js";

const field = (data_type: P6Field["data_type"], overrides: Partial<P6Field> = {}): P6Field => ({
  field_id: "activity_id",
  subject_area: "Activity",
  p6_field: "Activity ID",
  display_name: "Activity ID",
  data_type,
  writable: true,
  computed: false,
  disposition: "standard",
  ...overrides,
});

test("renders numeric P6 fields with typed number input", () => {
  const html = renderP6TypedFieldEditor(field("duration", { field_id: "duration", display_name: "Duration", unit: "h" }), 12);
  assert.match(html, /type="number"/);
  assert.match(html, /step="any"/);
  assert.match(html, /data-p6-typed-value="duration"/);
  assert.match(html, /data-p6-typed-unit/);
});

test("renders dates and booleans from registry metadata", () => {
  assert.match(renderP6TypedFieldEditor(field("date", { field_id: "start" }), null), /type="date"/);
  assert.match(renderP6TypedFieldEditor(field("boolean", { field_id: "critical" }), true), /type="checkbox"/);
  assert.match(renderP6TypedFieldEditor(field("boolean", { field_id: "critical" }), true), /checked/);
});

test("respects non-writable and computed registry metadata", () => {
  const html = renderP6TypedFieldEditor(field("string", { writable: false }), "A");
  assert.match(html, /disabled/);
  assert.match(renderP6TypedFieldEditor(field("string", { computed: true }), "A"), /disabled/);
});

test("coerces typed editor values without evaluating formulas", () => {
  assert.equal(coerceP6TypedFieldValue(field("integer"), "42"), 42);
  assert.equal(coerceP6TypedFieldValue(field("decimal"), "4.5"), 4.5);
  assert.equal(coerceP6TypedFieldValue(field("boolean"), "true"), true);
  assert.equal(coerceP6TypedFieldValue(field("string"), "4+5"), "4+5");
  assert.equal(coerceP6TypedFieldValue(field("decimal"), "not-a-number"), null);
});

test("supports custom and UDF fields through the same registry contract", () => {
  const custom = field("string", { field_id: "custom_text", disposition: "custom", display_name: "Custom Text" });
  const udf = field("decimal", { field_id: "udf_001", disposition: "udf", display_name: "UDF 001" });
  assert.match(renderP6TypedFieldEditor(custom, "x"), /data-p6-typed-value="custom_text"/);
  assert.match(renderP6TypedFieldEditor(udf, 3.5), /data-p6-typed-value="udf_001"/);
});


test("renders datetime and localized editable controls from registry metadata", () => {
  const datetime = field("datetime", { field_id: "actual_start", display_name: "Actual Start" });
  const boolean = field("boolean", { field_id: "critical", display_name: "Critical" });
  assert.match(renderP6TypedFieldEditor(datetime, "2026-10-01T08:30"), /type="datetime-local"/);
  assert.match(renderP6TypedFieldEditor(boolean, false, { locale: "fa" }), /ویرایش مقدار Critical/);
  assert.match(renderP6TypedFieldEditor(boolean, false), /data-p6-typed-value="critical"/);
});

test("renders integer editors with integer step and preserves null values as empty", () => {
  const html = renderP6TypedFieldEditor(field("integer", { field_id: "count" }), null);
  assert.match(html, /type="number"/);
  assert.match(html, /step="1"/);
  assert.match(html, /value=""/);
});
