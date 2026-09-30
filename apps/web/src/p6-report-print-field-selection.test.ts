import test from "node:test";
import assert from "node:assert/strict";
import { createP6ReportPrintFieldSelection } from "./p6-report-print-field-selection.js";
import type { FieldRegistry, LayoutDefinition } from "./p6-field-layout-foundation.js";

const registry: FieldRegistry = {
  registry_version: "p6-field-registry.v1",
  reference_product: "Oracle Primavera P6 Professional",
  reference_version: "P6-compatible",
  status: "active",
  fields: [
    { field_id: "activity-id", subject_area: "activity", p6_field: "Activity ID", display_name: "Activity ID", data_type: "string", writable: true, computed: false, disposition: "standard" },
    { field_id: "activity-name", subject_area: "activity", p6_field: "Activity Name", display_name: "Activity Name", data_type: "string", writable: true, computed: false, disposition: "standard" },
    { field_id: "activity-cost", subject_area: "activity", p6_field: "Activity Cost", display_name: "Activity Cost", data_type: "cost", writable: false, computed: true, disposition: "standard" },
  ],
};

const layout: LayoutDefinition = {
  schema_version: "p6-layout.v1",
  scope: "user",
  view_id: "activity",
  revision: 2,
  columns: [
    { field_id: "activity-id", visible: true, order: 0, width: 120, alignment: "start", pinned: false, frozen: false },
    { field_id: "activity-name", visible: false, order: 1, width: 180, alignment: "start", pinned: false, frozen: false },
    { field_id: "activity-cost", visible: true, order: 2, width: 140, alignment: "end", pinned: false, frozen: false },
  ],
};

test("defaults report/print selection to visible layout fields", () => {
  const model = createP6ReportPrintFieldSelection(layout, registry.fields);
  assert.deepEqual(model.getSelection().field_ids, ["activity-id", "activity-cost"]);
});

test("keeps selection registry/layout-backed and deterministic", () => {
  const model = createP6ReportPrintFieldSelection(layout, registry.fields, [
    "activity-cost", "missing", "activity-cost", "activity-name",
  ]);
  assert.deepEqual(model.getSelection().field_ids, ["activity-cost", "activity-name"]);
});

test("resets selection from the current layout visibility", () => {
  const model = createP6ReportPrintFieldSelection(layout, registry.fields, []);
  const next = {
    ...layout,
    columns: layout.columns.map((column) => ({ ...column, visible: column.field_id === "activity-id" })),
  };
  assert.deepEqual(model.resetToVisible(next).field_ids, ["activity-id"]);
});

test("rejects layouts containing fields outside the registry", () => {
  const invalid = { ...layout, columns: [...layout.columns, { ...layout.columns[0], field_id: "client-only" }] };
  assert.throws(() => createP6ReportPrintFieldSelection(invalid, registry.fields), /UNKNOWN_FIELD/);
});
