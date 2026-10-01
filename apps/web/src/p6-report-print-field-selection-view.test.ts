import test from "node:test";
import assert from "node:assert/strict";
import { renderP6ReportPrintFieldSelection } from "./p6-report-print-field-selection-view.js";
import type { LayoutDefinition, P6Field } from "./p6-field-layout-foundation.js";

const fields: P6Field[] = [
  { field_id: "activity_id", subject_area: "Activity", p6_field: "Activity ID", display_name: "Activity ID", data_type: "string", writable: false, computed: false, disposition: "standard" },
  { field_id: "duration", subject_area: "Activity", p6_field: "Original Duration", display_name: "Original Duration", data_type: "duration", writable: false, computed: false, disposition: "standard" },
];
const layout: LayoutDefinition = {
  schema_version: "p6-layout.v1", scope: "project", view_id: "activity", revision: 2,
  columns: [
    { field_id: "activity_id", visible: true, order: 0, width: 120, alignment: "start", pinned: false, frozen: false },
    { field_id: "duration", visible: false, order: 1, width: 120, alignment: "end", pinned: false, frozen: false },
  ],
};
const labels = { title: "Report / Print Fields", selected: "Selected", visible: "Visible", reset: "Reset to visible" };

test("renders selected and unselected fields from the authoritative layout", () => {
  const html = renderP6ReportPrintFieldSelection(layout, fields, { field_ids: ["activity_id"] }, labels);
  assert.match(html, /Report \/ Print Fields/);
  assert.match(html, /data-p6-report-selected>Selected: 1/);
  assert.match(html, /data-p6-report-visible>Visible: 1/);
  assert.match(html, /data-p6-report-field-id="activity_id" checked/);
  assert.match(html, /data-p6-report-field-id="duration"/);
});

test("does not invent fields outside the layout", () => {
  const html = renderP6ReportPrintFieldSelection(layout, fields, { field_ids: [] }, labels);
  assert.doesNotMatch(html, /data-p6-report-field-id="unknown"/);
});
