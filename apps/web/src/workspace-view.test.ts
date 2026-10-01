import assert from "node:assert/strict";
import test from "node:test";

import { renderMainWorkspace } from "./workspace-view.js";
import type { WorkspaceMenuKey } from "./workspace-model.js";
import { createWorkspaceState } from "./workspace-model.js";
import type { P6FormulaEditorState } from "./p6-formula-editor.js";

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
