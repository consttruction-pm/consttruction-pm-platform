import assert from "node:assert/strict";
import test from "node:test";
import type { FieldRegistry, LayoutDefinition, P6Field } from "./p6-field-layout-foundation.js";
import { renderP6GridCell } from "./p6-grid-cell-view.js";

const registry: FieldRegistry = {
  registry_version: "p6-field-registry.v1",
  reference_product: "Oracle Primavera P6 Professional",
  reference_version: "test",
  status: "active",
  fields: [],
};

const layout: LayoutDefinition = {
  schema_version: "p6-layout.v1",
  scope: "project",
  view_id: "activity",
  revision: 1,
  columns: [
    { field_id: "activity_id", visible: true, order: 0, width: 120, alignment: "start", pinned: false, frozen: false },
    { field_id: "duration", visible: true, order: 1, width: 120, alignment: "end", pinned: false, frozen: false },
    { field_id: "hidden", visible: false, order: 2, width: 120, alignment: "start", pinned: false, frozen: false },
  ],
};

const field = (field_id: string, data_type: P6Field["data_type"], overrides: Partial<P6Field> = {}): P6Field => ({
  field_id, subject_area: "Activity", p6_field: field_id, display_name: field_id, data_type,
  writable: false, computed: false, disposition: "standard", ...overrides,
});

test("renders read-only standard cells from authoritative field metadata", () => {
  const html = renderP6GridCell(field("duration", "duration", { unit: "h" }), layout, 8);
  assert.match(html, /data-p6-grid-cell/);
  assert.match(html, /8 h/);
  assert.match(html, /data-disposition="standard"/);
});

test("renders editable custom and UDF cells through the shared typed editor", () => {
  const custom = field("custom_text", "string", { writable: true, disposition: "custom" });
  const udf = field("udf_001", "decimal", { writable: true, disposition: "udf" });
  const customLayout: LayoutDefinition = { ...layout, columns: [...layout.columns, { field_id: "custom_text", visible: true, order: 3, width: 120, alignment: "start", pinned: false, frozen: false }] };
  const udfLayout: LayoutDefinition = { ...layout, columns: [...layout.columns, { field_id: "udf_001", visible: true, order: 3, width: 120, alignment: "end", pinned: false, frozen: false }] };
  assert.match(renderP6GridCell(custom, customLayout, "x", { editing: true }), /data-p6-typed-editor/);
  assert.match(renderP6GridCell(udf, udfLayout, 2.5, { editing: true }), /type="number"/);
});

test("does not render hidden columns", () => {
  assert.equal(renderP6GridCell(field("hidden", "string"), layout, "secret"), "");
});

test("computed fields remain display-only even when editing is requested", () => {
  const computed = field("calc", "decimal", { computed: true });
  const calcLayout: LayoutDefinition = { ...layout, columns: [...layout.columns, { field_id: "calc", visible: true, order: 3, width: 120, alignment: "end", pinned: false, frozen: false }] };
  const html = renderP6GridCell(computed, calcLayout, 12, { editing: true });
  assert.match(html, /data-p6-grid-cell/);
  assert.doesNotMatch(html, /data-p6-typed-editor/);
});


test("editable boolean and datetime cells use the shared typed editor", () => {
  const booleanField = field("critical", "boolean", { writable: true });
  const datetimeField = field("actual_start", "datetime", { writable: true });
  const booleanLayout: LayoutDefinition = { ...layout, columns: [...layout.columns, { field_id: "critical", visible: true, order: 3, width: 120, alignment: "center", pinned: false, frozen: false }] };
  const datetimeLayout: LayoutDefinition = { ...layout, columns: [...layout.columns, { field_id: "actual_start", visible: true, order: 3, width: 160, alignment: "start", pinned: false, frozen: false }] };
  assert.match(renderP6GridCell(booleanField, booleanLayout, true, { editing: true }), /type="checkbox"/);
  assert.match(renderP6GridCell(datetimeField, datetimeLayout, "2026-10-01T08:30", { editing: true }), /type="datetime-local"/);
});


test("renders custom and UDF values through the same display path when not editing", () => {
  const custom = field("custom_text", "string", { disposition: "custom" });
  const udf = field("udf_percent", "percentage", { disposition: "udf" });
  const customLayout: LayoutDefinition = { ...layout, columns: [...layout.columns, { field_id: "custom_text", visible: true, order: 3, width: 120, alignment: "start", pinned: false, frozen: false }] };
  const udfLayout: LayoutDefinition = { ...layout, columns: [...layout.columns, { field_id: "udf_percent", visible: true, order: 3, width: 120, alignment: "end", pinned: false, frozen: false }] };
  assert.match(renderP6GridCell(custom, customLayout, "Custom value"), /data-disposition="custom"/);
  assert.match(renderP6GridCell(udf, udfLayout, 25), /25%/);
  assert.match(renderP6GridCell(udf, udfLayout, 25), /data-disposition="udf"/);
});
