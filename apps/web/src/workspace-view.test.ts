import assert from "node:assert/strict";
import test from "node:test";

import { renderMainWorkspace } from "./workspace-view.js";
import type { WorkspaceMenuKey } from "./workspace-model.js";
import { createWorkspaceState } from "./workspace-model.js";
import type { P6FormulaEditorState } from "./p6-formula-editor.js";
import type { FieldRegistry, LayoutDefinition } from "./p6-field-layout-foundation.js";

type RenderContainer = {
  innerHTML: string;
  querySelectorAll: () => HTMLElement[];
};

function render(locale: "en" | "fa", activeMenu: WorkspaceMenuKey): string {
  const state = {
    ...createWorkspaceState(
      { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
      locale,
    ),
    activeMenu,
  };
  const container: RenderContainer = {
    innerHTML: "",
    querySelectorAll: () => [],
  };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  return container.innerHTML;
}

test("rendered schedule surface exposes localized label and implemented status", () => {
  const html = render("en", "schedule");

  assert.match(html, /<strong>Schedule<\/strong>/);
  assert.match(html, /data-surface-status="implemented">Implemented<\/span>/);
  assert.match(html, /Activity Grid/);
  assert.match(html, /Gantt Chart/);
});

test("rendered preview surfaces remain explicitly marked", () => {
  const html = render("en", "reports");

  assert.match(html, /<strong>Reports<\/strong>/);
  assert.match(html, /data-surface-status="preview">Preview<\/span>/);
  assert.match(html, /Reports/);
  assert.match(html, /Print/);
});

test("rendered navigation surface follows Persian locale and RTL direction", () => {
  const html = render("fa", "schedule");

  assert.match(html, /dir="rtl"/);
  assert.match(html, /<strong>زمان‌بندی<\/strong>/);
  assert.match(html, /جدول فعالیت‌ها/);
  assert.match(html, /گانت/);
  assert.match(html, /data-surface-status="implemented">پیاده‌سازی‌شده<\/span>/);
});


test("menu selection wiring forwards the selected workspace surface", () => {
  const state = createWorkspaceState(
    { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
    "en",
  );
  const selected: WorkspaceMenuKey[] = [];
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  const listeners = new Map<string, () => void>();
  const buttons = ["schedule", "reports"].map((menu) => ({
    dataset: { menu },
    addEventListener: (_event: string, listener: () => void) => listeners.set(menu, listener),
  }));
  container.querySelectorAll = ((selector: string) => selector === "[data-menu]" ? buttons as unknown as HTMLElement[] : []) as RenderContainer["querySelectorAll"];
  renderMainWorkspace(container as unknown as HTMLElement, state, {
    onMenuSelect: (menu) => selected.push(menu),
  });
  listeners.get("reports")?.();
  assert.deepEqual(selected, ["reports"]);
});


test("renders the authoritative formula editor in the Activity workspace when supplied", () => {
  const state = createWorkspaceState(
    { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
    "en",
  );
  const formulaState: P6FormulaEditorState = {
    field_id: "activity-cost",
    expression: "Original Duration * Units",
    validating: false,
    authoritative: {
      validation: { valid: true, error_code: null, message_key: null },
      dependencies: { field_ids: ["activity-duration", "activity-units"] },
      result_type: { data_type: "double" },
    },
  };
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, state, { p6FormulaEditorState: formulaState });
  assert.match(container.innerHTML, /cp-p6-formula-editor/);
  assert.match(container.innerHTML, /activity-duration, activity-units/);
  assert.match(container.innerHTML, /data-p6-formula-result-type>double/);
});

test("keeps the formula editor out of the workspace when no authoritative editor state is supplied", () => {
  const html = render("en", "schedule");
  assert.doesNotMatch(html, /cp-p6-formula-editor/);
});


test("renders the report/print field selection from authoritative registry and layout", () => {
  const state = {
    ...createWorkspaceState(
      { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
      "en",
    ),
    p6FieldRegistry: {
      registry_version: "p6-field-registry.v1",
      reference_product: "Oracle Primavera P6 Professional",
      reference_version: "test",
      status: "active",
      fields: [
        { field_id: "activity_id", subject_area: "Activity", p6_field: "Activity ID", display_name: "Activity ID", data_type: "string", writable: false, computed: false, disposition: "standard" },
        { field_id: "duration", subject_area: "Activity", p6_field: "Original Duration", display_name: "Original Duration", data_type: "duration", writable: false, computed: false, disposition: "standard" },
      ],
    } as FieldRegistry,
    p6Layout: {
      schema_version: "p6-layout.v1", scope: "project", view_id: "activity", revision: 2,
      columns: [
        { field_id: "activity_id", visible: true, order: 0, width: 120, alignment: "start", pinned: false, frozen: false },
        { field_id: "duration", visible: false, order: 1, width: 120, alignment: "end", pinned: false, frozen: false },
      ],
    } as LayoutDefinition,
  };
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, state, {
    p6ReportPrintSelection: { field_ids: ["activity_id"] },
  });
  assert.match(container.innerHTML, /cp-p6-report-print-fields/);
  assert.match(container.innerHTML, /Selected: 1/);
  assert.match(container.innerHTML, /data-p6-report-field-id="activity_id" checked/);
});
