import assert from "node:assert/strict";
import test from "node:test";

import { renderMainWorkspace } from "./workspace-view.js";
import type { WorkspaceState } from "./workspace-model.js";
import type { WorkspaceMenuKey } from "./workspace-model.js";
import type { P6GridFilter, P6GridSort } from "./p6-activity-wbs-grid.js";
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

test("report/print field selection forwards checkbox changes and reset", () => {
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
  const changes: string[][] = [];
  let resetCount = 0;
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  const inputs = [
    { dataset: { p6ReportFieldId: "activity_id" }, checked: true, addEventListener: (_event: string, listener: () => void) => listener() },
    { dataset: { p6ReportFieldId: "duration" }, checked: false, addEventListener: () => undefined },
  ];
  const reset = { dataset: {}, addEventListener: (_event: string, listener: () => void) => listener() };
  container.querySelectorAll = ((selector: string) => {
    if (selector === "[data-p6-report-field-id]") return inputs as unknown as HTMLElement[];
    if (selector === "[data-p6-report-field-id]:checked") return inputs.filter((input) => input.checked) as unknown as HTMLElement[];
    if (selector === "[data-p6-report-reset]") return [reset] as unknown as HTMLElement[];
    return [];
  }) as RenderContainer["querySelectorAll"];
  renderMainWorkspace(container as unknown as HTMLElement, state, {
    p6ReportPrintSelection: { field_ids: ["activity_id"] },
    onP6ReportPrintSelectionChange: (fieldIds) => changes.push([...fieldIds]),
    onP6ReportPrintReset: () => { resetCount += 1; },
  });
  assert.deepEqual(changes, [["activity_id"]]);
  assert.equal(resetCount, 1);
});

test("grid presentation forwards sort, group, and filter changes", () => {
  const state = {
    ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    p6FieldRegistry: {
      registry_version: "p6-field-registry.v1",
      reference_product: "Oracle Primavera P6 Professional",
      reference_version: "test",
      status: "active",
      fields: [
        { field_id: "activity_id", subject_area: "Activity", p6_field: "Activity ID", display_name: "Activity ID", data_type: "string", writable: false, computed: false, disposition: "standard" },
        { field_id: "duration", subject_area: "Activity", p6_field: "Original Duration", display_name: "Duration", data_type: "duration", writable: false, computed: false, disposition: "standard" },
      ],
    } as FieldRegistry,
  };
  const sorts: unknown[] = [];
  const groups: unknown[] = [];
  const filters: unknown[] = [];
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  const sortField = { value: "duration", closest: () => ({ dataset: { order: "0" } }), addEventListener: (_event: string, listener: () => void) => listener() };
  const sortDirection = { value: "descending", closest: () => ({ dataset: { order: "0" } }), addEventListener: (_event: string, listener: () => void) => listener() };
  const groupField = { value: "duration", closest: () => ({ dataset: { order: "0" } }), addEventListener: (_event: string, listener: () => void) => listener() };
  const filterField = { value: "duration", closest: () => ({ dataset: { order: "0" } }), addEventListener: (_event: string, listener: () => void) => listener() };
  const filterOperator = { value: "contains", closest: () => ({ dataset: { order: "0" } }), addEventListener: (_event: string, listener: () => void) => listener() };
  const filterValue = { value: "10", closest: () => ({ dataset: { order: "0" } }), addEventListener: (_event: string, listener: () => void) => listener() };
  const filterRemove = { closest: () => ({ dataset: { order: "0" } }), addEventListener: (_event: string, listener: () => void) => listener() };
  const sortRemove = { closest: () => ({ dataset: { order: "0" } }), addEventListener: (_event: string, listener: () => void) => listener() };
  const groupRemove = { closest: () => ({ dataset: { order: "0" } }), addEventListener: (_event: string, listener: () => void) => listener() };
  container.querySelectorAll = ((selector: string) => {
    if (selector === "[data-p6-grid-sort-field]") return [sortField] as unknown as HTMLElement[];
    if (selector === "[data-p6-grid-sort-direction]") return [sortDirection] as unknown as HTMLElement[];
    if (selector === "[data-p6-grid-sort-remove]") return [sortRemove] as unknown as HTMLElement[];
    if (selector === "[data-p6-grid-group-field]") return [groupField] as unknown as HTMLElement[];
    if (selector === "[data-p6-grid-group-remove]") return [groupRemove] as unknown as HTMLElement[];
    if (selector === "[data-p6-grid-filter-field]") return [filterField] as unknown as HTMLElement[];
    if (selector === "[data-p6-grid-filter-operator]") return [filterOperator] as unknown as HTMLElement[];
    if (selector === "[data-p6-grid-filter-value]") return [filterValue] as unknown as HTMLElement[];
    if (selector === "[data-p6-grid-filter-remove]") return [filterRemove] as unknown as HTMLElement[];
    return [];
  }) as RenderContainer["querySelectorAll"];
  renderMainWorkspace(container as unknown as HTMLElement, state, {
    p6GridPresentation: {
      sorts: [{ field_id: "activity_id", direction: "ascending", order: 0 }],
      groups: [{ field_id: "activity_id", order: 0 }],
      filters: [{ field_id: "activity_id", operator: "equals", value: "1" }],
    },
    onP6GridSortChange: (value) => sorts.push(value),
    onP6GridGroupChange: (value) => groups.push(value),
    onP6GridFilterChange: (value) => filters.push(value),
  });
  assert.deepEqual(sorts[0], []);
  assert.equal((sorts[1] as Array<{ field_id: string }>)[0].field_id, "duration");
  assert.equal((sorts[2] as Array<{ direction: string }>)[0].direction, "descending");
  assert.deepEqual(groups[0], []);
  assert.equal((groups[1] as Array<{ field_id: string }>)[0].field_id, "duration");
  assert.equal((filters[0] as Array<{ field_id: string }>)[0].field_id, "duration");
  assert.equal((filters[1] as Array<{ operator: string }>)[0].operator, "contains");
  assert.equal((filters[2] as Array<{ value: string }>)[0].value, "10");
  assert.deepEqual(filters[3], []);
});

test("grid presentation exposes add sort, group, and filter controls", () => {
  const state = {
    ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    p6FieldRegistry: {
      registry_version: "p6-field-registry.v1", reference_product: "Oracle Primavera P6 Professional", reference_version: "test", status: "active",
      fields: [{ field_id: "activity_id", subject_area: "Activity", p6_field: "Activity ID", display_name: "Activity ID", data_type: "string", writable: false, computed: false, disposition: "standard" }],
    } as FieldRegistry,
  };
  const calls: string[] = [];
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  const controls = (name: string) => ({ dataset: {}, addEventListener: (_event: string, listener: () => void) => { listener(); calls.push(name); } });
  container.querySelectorAll = ((selector: string) => {
    if (selector === "[data-p6-grid-sort-add]") return [controls("sort")] as unknown as HTMLElement[];
    if (selector === "[data-p6-grid-group-add]") return [controls("group")] as unknown as HTMLElement[];
    if (selector === "[data-p6-grid-filter-add]") return [controls("filter")] as unknown as HTMLElement[];
    return [];
  }) as RenderContainer["querySelectorAll"];
  renderMainWorkspace(container as unknown as HTMLElement, state, {
    p6GridPresentation: { sorts: [], groups: [], filters: [] },
    onP6GridSortAdd: () => calls.push("sort-callback"),
    onP6GridGroupAdd: () => calls.push("group-callback"),
    onP6GridFilterAdd: () => calls.push("filter-callback"),
  });
  assert.deepEqual(calls, ["sort-callback", "sort", "group-callback", "group", "filter-callback", "filter"]);
  assert.match(container.innerHTML, /data-p6-grid-sort-add/);
  assert.match(container.innerHTML, /data-p6-grid-group-add/);
  assert.match(container.innerHTML, /data-p6-grid-filter-add/);
});

test("keeps the formula editor out of the workspace when no authoritative editor state is supplied", () => {
  const html = render("en", "schedule");
  assert.doesNotMatch(html, /cp-p6-formula-editor/);
});


test("localizes P6 grid presentation labels and filter operators", () => {
  const state = {
    ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "fa"),
    p6FieldRegistry: {
      registry_version: "p6-field-registry.v1", reference_product: "Oracle Primavera P6 Professional", reference_version: "test", status: "active",
      fields: [{ field_id: "activity_id", subject_area: "Activity", p6_field: "Activity ID", display_name: "شناسه فعالیت", data_type: "string", writable: false, computed: false, disposition: "standard" }],
    } as FieldRegistry,
    p6GridSorts: [{ field_id: "activity_id", direction: "ascending", order: 0 } satisfies P6GridSort],
    p6GridFilters: [{ field_id: "activity_id", operator: "contains", value: "A" } satisfies P6GridFilter],
  };
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  assert.match(container.innerHTML, /ارائه گرید/);
  assert.match(container.innerHTML, /مرتب‌سازی: 1/);
  assert.match(container.innerHTML, /شامل/);
  assert.match(container.innerHTML, /صعودی/);
});

test("P6 field chooser forwards hide without removing the layout column", () => {
  const state = {
    ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    p6FieldRegistry: {
      registry_version: "p6-field-registry.v1", reference_product: "Oracle Primavera P6 Professional", reference_version: "test", status: "active",
      fields: [{ field_id: "activity_id", subject_area: "Activity", p6_field: "Activity ID", display_name: "Activity ID", data_type: "string", writable: false, computed: false, disposition: "standard" }],
    } as FieldRegistry,
    p6Layout: {
      schema_version: "p6-layout.v1", scope: "project", view_id: "activity", revision: 2,
      columns: [{ field_id: "activity_id", visible: true, order: 0, width: 120, alignment: "start", pinned: false, frozen: false }],
    } as LayoutDefinition,
  };
  const hide = { dataset: { p6FieldHide: "activity_id" }, addEventListener: (_event: string, listener: () => void) => listener() };
  const changes: Array<{ fieldId: string; patch: { visible?: boolean } }> = [];
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  container.querySelectorAll = ((selector: string) => (
    selector === "[data-p6-field-hide]" ? [hide] as unknown as HTMLElement[] : []
  )) as RenderContainer["querySelectorAll"];
  renderMainWorkspace(container as unknown as HTMLElement, state, {
    onP6FieldPresentationChange: (fieldId, patch) => changes.push({ fieldId, patch }),
  });
  assert.match(container.innerHTML, /data-p6-field-hide="activity_id"/);
  assert.match(container.innerHTML, /Hide/);
  assert.deepEqual(changes, [{ fieldId: "activity_id", patch: { visible: false } }]);
});

test("localizes P6 field chooser hide control", () => {
  const state = {
    ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "fa"),
    p6FieldRegistry: {
      registry_version: "p6-field-registry.v1", reference_product: "Oracle Primavera P6 Professional", reference_version: "test", status: "active",
      fields: [{ field_id: "activity_id", subject_area: "Activity", p6_field: "Activity ID", display_name: "شناسه فعالیت", data_type: "string", writable: false, computed: false, disposition: "standard" }],
    } as FieldRegistry,
    p6Layout: {
      schema_version: "p6-layout.v1", scope: "project", view_id: "activity", revision: 2,
      columns: [{ field_id: "activity_id", visible: true, order: 0, width: 120, alignment: "start", pinned: false, frozen: false }],
    } as LayoutDefinition,
  };
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  assert.match(container.innerHTML, /data-p6-field-hide="activity_id"/);
  assert.match(container.innerHTML, /مخفی‌کردن/);
});

test("localizes P6 hidden field show control", () => {
  const state = {
    ...createWorkspaceState(
      { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
      "fa",
    ),
    p6FieldRegistry: {
      registry_version: "p6-field-registry.v1",
      reference_product: "Oracle Primavera P6 Professional",
      reference_version: "test",
      status: "active",
      fields: [
        { field_id: "activity_id", subject_area: "Activity", p6_field: "Activity ID", display_name: "شناسه فعالیت", data_type: "string", writable: false, computed: false, disposition: "standard" },
        { field_id: "duration", subject_area: "Activity", p6_field: "Original Duration", display_name: "مدت", data_type: "duration", writable: false, computed: false, disposition: "standard" },
      ],
    } as FieldRegistry,
    p6Layout: {
      schema_version: "p6-layout.v1",
      scope: "project",
      view_id: "activity",
      revision: 2,
      columns: [
        { field_id: "activity_id", visible: true, order: 0, width: 120, alignment: "start", pinned: false, frozen: false },
        { field_id: "duration", visible: false, order: 1, width: 120, alignment: "end", pinned: false, frozen: false },
      ],
    } as LayoutDefinition,
  };
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  const show = {
    dataset: { p6FieldShow: "duration" },
    addEventListener: (_event: string, listener: () => void) => listener(),
  };
  const changes: Array<{ fieldId: string; patch: { visible?: boolean } }> = [];
  container.querySelectorAll = ((selector: string) => (
    selector === "[data-p6-field-show]" ? [show] as unknown as HTMLElement[] : []
  )) as RenderContainer["querySelectorAll"];
  renderMainWorkspace(container as unknown as HTMLElement, state, {
    onP6FieldPresentationChange: (fieldId, patch) => changes.push({ fieldId, patch }),
  });
  assert.match(container.innerHTML, /نمایش/);
  assert.deepEqual(changes, [{ fieldId: "duration", patch: { visible: true } }]);
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


test("column presentation controls forward authoritative layout patches", () => {
  const state = {
    ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    p6FieldRegistry: {
      registry_version: "p6-field-registry.v1", reference_product: "Oracle Primavera P6 Professional", reference_version: "test", status: "active",
      fields: [{ field_id: "activity_id", subject_area: "Activity", p6_field: "Activity ID", display_name: "Activity ID", data_type: "string", writable: false, computed: false, disposition: "standard" }],
    } as FieldRegistry,
    p6Layout: {
      schema_version: "p6-layout.v1", scope: "project", view_id: "activity", revision: 2,
      columns: [{ field_id: "activity_id", visible: true, order: 0, label: "Activity ID", width: 120, alignment: "start", pinned: false, frozen: false }],
    } as LayoutDefinition,
  };
  const changes: Array<[string, Record<string, unknown>]> = [];
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  const label = { dataset: { p6ColumnLabel: "activity_id" }, value: "ID", addEventListener: (_event: string, listener: () => void) => listener() };
  const width = { dataset: { p6ColumnWidth: "activity_id" }, value: "180", addEventListener: (_event: string, listener: () => void) => listener() };
  const alignment = { dataset: { p6ColumnAlignment: "activity_id" }, value: "center", addEventListener: (_event: string, listener: () => void) => listener() };
  const pinned = { dataset: { p6ColumnPinned: "activity_id" }, checked: true, addEventListener: (_event: string, listener: () => void) => listener() };
  const frozen = { dataset: { p6ColumnFrozen: "activity_id" }, checked: true, addEventListener: (_event: string, listener: () => void) => listener() };
  container.querySelectorAll = ((selector: string) => {
    if (selector === "[data-p6-column-label]") return [label] as unknown as HTMLElement[];
    if (selector === "[data-p6-column-width]") return [width] as unknown as HTMLElement[];
    if (selector === "[data-p6-column-alignment]") return [alignment] as unknown as HTMLElement[];
    if (selector === "[data-p6-column-pinned]") return [pinned] as unknown as HTMLElement[];
    if (selector === "[data-p6-column-frozen]") return [frozen] as unknown as HTMLElement[];
    return [];
  }) as RenderContainer["querySelectorAll"];
  renderMainWorkspace(container as unknown as HTMLElement, state, {
    onP6FieldPresentationChange: (fieldId, patch) => changes.push([fieldId, patch]),
  });
  assert.deepEqual(changes, [
    ["activity_id", { label: "ID" }],
    ["activity_id", { width: 180 }],
    ["activity_id", { alignment: "center" }],
    ["activity_id", { pinned: true }],
    ["activity_id", { frozen: true }],
  ]);
});

test("localizes P6 column presentation controls", () => {
  const state = {
    ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "fa"),
    p6FieldRegistry: {
      registry_version: "p6-field-registry.v1", reference_product: "Oracle Primavera P6 Professional", reference_version: "test", status: "active",
      fields: [{ field_id: "activity_id", subject_area: "Activity", p6_field: "Activity ID", display_name: "شناسه فعالیت", data_type: "string", writable: false, computed: false, disposition: "standard" }],
    } as FieldRegistry,
    p6Layout: {
      schema_version: "p6-layout.v1", scope: "project", view_id: "activity", revision: 2,
      columns: [{ field_id: "activity_id", visible: true, order: 0, label: "شناسه", width: 120, alignment: "start", pinned: false, frozen: false }],
    } as LayoutDefinition,
  };
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  assert.match(container.innerHTML, /تنظیمات ستون‌ها/);
  assert.match(container.innerHTML, /شناسه/);
  assert.match(container.innerHTML, /ابتدا/);
});


test("P6 field chooser forwards field reorder changes", () => {
  const state = {
    ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    p6FieldRegistry: {
      registry_version: "p6-field-registry.v1",
      reference_product: "Oracle Primavera P6 Professional",
      reference_version: "test",
      status: "active",
      fields: [
        { field_id: "activity_id", subject_area: "Activity", p6_field: "Activity ID", display_name: "Activity ID", data_type: "string", writable: false, computed: false, disposition: "standard" },
        { field_id: "duration", subject_area: "Activity", p6_field: "Original Duration", display_name: "Duration", data_type: "duration", writable: false, computed: false, disposition: "standard" },
      ],
    } as FieldRegistry,
    p6Layout: {
      schema_version: "p6-layout.v1", scope: "project", view_id: "activity", revision: 2,
      columns: [
        { field_id: "activity_id", visible: true, order: 0, width: 120, alignment: "start", pinned: false, frozen: false },
        { field_id: "duration", visible: true, order: 1, width: 120, alignment: "end", pinned: false, frozen: false },
      ],
    } as LayoutDefinition,
  };
  const reorderChanges: string[][] = [];
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  const moveDown = {
    dataset: { p6FieldMoveDown: "activity_id" },
    addEventListener: (_event: string, listener: () => void) => listener(),
  };
  container.querySelectorAll = ((selector: string) => {
    if (selector === "[data-p6-field-move-up], [data-p6-field-move-down]") return [moveDown] as unknown as HTMLElement[];
    return [];
  }) as RenderContainer["querySelectorAll"];
  renderMainWorkspace(container as unknown as HTMLElement, state, {
    onP6FieldReorder: (fieldIds) => reorderChanges.push([...fieldIds]),
  });
  assert.deepEqual(reorderChanges, [["duration", "activity_id"]]);
  assert.match(container.innerHTML, /data-p6-field-move-up="activity_id"/);
  assert.match(container.innerHTML, /data-p6-field-move-down="activity_id"/);
});



test("P6 field chooser forwards add and remove changes", () => {
  const state = {
    ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    p6FieldRegistry: {
      registry_version: "p6-field-registry.v1",
      reference_product: "Oracle Primavera P6 Professional",
      reference_version: "test",
      status: "active",
      fields: [
        { field_id: "activity_id", subject_area: "Activity", p6_field: "Activity ID", display_name: "Activity ID", data_type: "string", writable: false, computed: false, disposition: "standard" },
        { field_id: "duration", subject_area: "Activity", p6_field: "Original Duration", display_name: "Duration", data_type: "duration", writable: false, computed: false, disposition: "standard" },
      ],
    } as FieldRegistry,
    p6Layout: {
      schema_version: "p6-layout.v1", scope: "project", view_id: "activity", revision: 2,
      columns: [{ field_id: "activity_id", visible: true, order: 0, width: 120, alignment: "start", pinned: false, frozen: false }],
    } as LayoutDefinition,
  };
  const added: string[] = [];
  const removed: string[] = [];
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  const add = {
    dataset: { p6FieldAdd: "duration" },
    addEventListener: (_event: string, listener: () => void) => listener(),
  };
  const remove = {
    dataset: { p6FieldRemove: "activity_id" },
    addEventListener: (_event: string, listener: () => void) => listener(),
  };
  container.querySelectorAll = ((selector: string) => {
    if (selector === "[data-p6-field-add]") return [add] as unknown as HTMLElement[];
    if (selector === "[data-p6-field-remove]") return [remove] as unknown as HTMLElement[];
    return [];
  }) as RenderContainer["querySelectorAll"];
  renderMainWorkspace(container as unknown as HTMLElement, state, {
    onP6FieldAdd: (fieldId) => added.push(fieldId),
    onP6FieldRemove: (fieldId) => removed.push(fieldId),
  });
  assert.deepEqual(added, ["duration"]);
  assert.deepEqual(removed, ["activity_id"]);
  assert.match(container.innerHTML, /duration.*Add/);
  assert.match(container.innerHTML, /data-p6-field-remove="activity_id"/);
});


test("P6 field chooser forwards hidden field show changes", () => {
  const state = {
    ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    p6FieldRegistry: {
      registry_version: "p6-field-registry.v1",
      reference_product: "Oracle Primavera P6 Professional",
      reference_version: "test",
      status: "active",
      fields: [
        { field_id: "activity_id", subject_area: "Activity", p6_field: "Activity ID", display_name: "Activity ID", data_type: "string", writable: false, computed: false, disposition: "standard" },
        { field_id: "duration", subject_area: "Activity", p6_field: "Original Duration", display_name: "Duration", data_type: "duration", writable: false, computed: false, disposition: "standard" },
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
  const changes: Array<[string, Record<string, unknown>]> = [];
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  const show = {
    dataset: { p6FieldShow: "duration" },
    addEventListener: (_event: string, listener: () => void) => listener(),
  };
  container.querySelectorAll = ((selector: string) => {
    if (selector === "[data-p6-field-show]") return [show] as unknown as HTMLElement[];
    return [];
  }) as RenderContainer["querySelectorAll"];
  renderMainWorkspace(container as unknown as HTMLElement, state, {
    onP6FieldPresentationChange: (fieldId, patch) => changes.push([fieldId, patch]),
  });
  assert.deepEqual(changes, [["duration", { visible: true }]]);
  assert.match(container.innerHTML, /data-p6-field-show="duration"/);
  assert.match(container.innerHTML, /duration.*Show/);
});

test("P6 field chooser localizes reorder controls for Persian", () => {
  const state = {
    ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "fa"),
    p6FieldRegistry: {
      registry_version: "p6-field-registry.v1", reference_product: "Oracle Primavera P6 Professional", reference_version: "test", status: "active",
      fields: [{ field_id: "activity_id", subject_area: "Activity", p6_field: "Activity ID", display_name: "شناسه فعالیت", data_type: "string", writable: false, computed: false, disposition: "standard" }],
    } as FieldRegistry,
    p6Layout: { schema_version: "p6-layout.v1", scope: "project", view_id: "activity", revision: 2, columns: [{ field_id: "activity_id", visible: true, order: 0, width: 120, alignment: "start", pinned: false, frozen: false }] } as LayoutDefinition,
  };
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  assert.match(container.innerHTML, /انتخابگر فیلدهای P6/);
  assert.match(container.innerHTML, /انتقال به بالا/);
  assert.match(container.innerHTML, /انتقال به پایین/);
  assert.match(container.innerHTML, /حذف/);
});


test("P6 activity grid renders authoritative visible fields with typed cell values", () => {
  const state = {
    ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    p6FieldRegistry: {
      registry_version: "p6-field-registry.v1",
      reference_product: "Oracle Primavera P6 Professional",
      reference_version: "test",
      status: "active",
      fields: [
        { field_id: "activity_id", subject_area: "Activity", p6_field: "Activity ID", display_name: "Activity ID", data_type: "string", writable: false, computed: false, disposition: "standard" },
        { field_id: "duration", subject_area: "Activity", p6_field: "Original Duration", display_name: "Duration", data_type: "duration", writable: false, computed: false, disposition: "standard", unit: "h" },
        { field_id: "progress", subject_area: "Activity", p6_field: "Physical % Complete", display_name: "Progress", data_type: "percentage", writable: false, computed: false, disposition: "standard" },
      ],
    } as FieldRegistry,
    p6Layout: {
      schema_version: "p6-layout.v1", scope: "project", view_id: "activity", revision: 2,
      columns: [
        { field_id: "activity_id", visible: true, order: 0, width: 120, alignment: "start", pinned: false, frozen: false },
        { field_id: "duration", visible: true, order: 1, width: 120, alignment: "end", pinned: false, frozen: false },
        { field_id: "progress", visible: false, order: 2, width: 100, alignment: "end", pinned: false, frozen: false },
      ],
    } as LayoutDefinition,
    activities: [{
      id: "A-100",
      wbsId: "WBS-1",
      code: "A100",
      name: "Excavate",
      cells: { duration: 12, progress: 45 },
    }],
  };
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  assert.match(container.innerHTML, /data-p6-activity-grid/);
  assert.match(container.innerHTML, /data-p6-grid-field-id="activity_id"/);
  assert.match(container.innerHTML, /data-p6-grid-field-id="duration"/);
  assert.doesNotMatch(container.innerHTML, /data-p6-grid-field-id="progress"/);
  assert.match(container.innerHTML, /12 h/);
  assert.match(container.innerHTML, /A-100/);
});

test("P6 activity grid consumes column alignment, pinning, and freezing presentation", () => {
  const state = {
    ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    p6FieldRegistry: {
      registry_version: "p6-field-registry.v1", reference_product: "Oracle Primavera P6 Professional", reference_version: "test", status: "active",
      fields: [
        { field_id: "activity_id", subject_area: "Activity", p6_field: "Activity ID", display_name: "Activity ID", data_type: "string", writable: false, computed: false, disposition: "standard" },
      ],
    } as FieldRegistry,
    p6Layout: {
      schema_version: "p6-layout.v1", scope: "project", view_id: "activity", revision: 2,
      columns: [{ field_id: "activity_id", visible: true, order: 0, width: 120, alignment: "center", pinned: true, frozen: true }],
    } as LayoutDefinition,
    activities: [{ id: "A-100", wbsId: "WBS-1", code: "A100", name: "Excavate" }],
  };
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  assert.match(container.innerHTML, /data-p6-grid-alignment="center"/);
  assert.match(container.innerHTML, /data-p6-grid-pinned="true"/);
  assert.match(container.innerHTML, /data-p6-grid-frozen="true"/);
  assert.match(container.innerHTML, /text-align:center/);
});



test("P6 column presentation controls forward label, width, alignment, pin, and freeze changes", () => {
  const state = {
    ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    p6FieldRegistry: {
      registry_version: "p6-field-registry.v1", reference_product: "Oracle Primavera P6 Professional", reference_version: "test", status: "active",
      fields: [{ field_id: "activity_id", subject_area: "Activity", p6_field: "Activity ID", display_name: "Activity ID", data_type: "string", writable: false, computed: false, disposition: "standard" }],
    } as FieldRegistry,
    p6Layout: {
      schema_version: "p6-layout.v1", scope: "project", view_id: "activity", revision: 2,
      columns: [{ field_id: "activity_id", visible: true, order: 0, width: 120, alignment: "start", pinned: false, frozen: false }],
    } as LayoutDefinition,
  };
  const changes: Array<{ fieldId: string; patch: Record<string, unknown> }> = [];
  const listeners = new Map<string, () => void>();
  const makeInput = (dataset: Record<string, string>, value = "", checked = false) => ({
    dataset, value, checked,
    addEventListener: (_event: string, listener: () => void) => listeners.set(Object.keys(dataset)[0]!, listener),
  });
  const label = makeInput({ p6ColumnLabel: "activity_id" }, "Activity ID Updated");
  const width = makeInput({ p6ColumnWidth: "activity_id" }, "240");
  const alignment = makeInput({ p6ColumnAlignment: "activity_id" }, "center");
  const pinned = makeInput({ p6ColumnPinned: "activity_id" }, "", true);
  const frozen = makeInput({ p6ColumnFrozen: "activity_id" }, "", true);
  const controls: Record<string, unknown[]> = {
    "[data-p6-column-label]": [label], "[data-p6-column-width]": [width],
    "[data-p6-column-alignment]": [alignment], "[data-p6-column-pinned]": [pinned],
    "[data-p6-column-frozen]": [frozen],
  };
  const container: RenderContainer = {
    innerHTML: "",
    querySelectorAll: ((selector: string) => (controls[selector] ?? []) as HTMLElement[]) as RenderContainer["querySelectorAll"],
  };
  renderMainWorkspace(container as unknown as HTMLElement, state, {
    onP6FieldPresentationChange: (fieldId, patch) => changes.push({ fieldId, patch: patch as Record<string, unknown> }),
  });
  listeners.get("p6ColumnLabel")?.();
  listeners.get("p6ColumnWidth")?.();
  listeners.get("p6ColumnAlignment")?.();
  listeners.get("p6ColumnPinned")?.();
  listeners.get("p6ColumnFrozen")?.();
  assert.deepEqual(changes, [
    { fieldId: "activity_id", patch: { label: "Activity ID Updated" } },
    { fieldId: "activity_id", patch: { width: 240 } },
    { fieldId: "activity_id", patch: { alignment: "center" } },
    { fieldId: "activity_id", patch: { pinned: true } },
    { fieldId: "activity_id", patch: { frozen: true } },
  ]);
});


test("P6 column presentation ignores invalid width input and forwards unchecked pin/freeze state", () => {
  const state = {
    ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    p6FieldRegistry: {
      registry_version: "p6-field-registry.v1", reference_product: "Oracle Primavera P6 Professional", reference_version: "test", status: "active",
      fields: [{ field_id: "activity_id", subject_area: "Activity", p6_field: "Activity ID", display_name: "Activity ID", data_type: "string", writable: false, computed: false, disposition: "standard" }],
    } as FieldRegistry,
    p6Layout: {
      schema_version: "p6-layout.v1", scope: "project", view_id: "activity", revision: 2,
      columns: [{ field_id: "activity_id", visible: true, order: 0, width: 120, alignment: "start", pinned: true, frozen: true }],
    } as LayoutDefinition,
  };
  const changes: Array<{ fieldId: string; patch: Record<string, unknown> }> = [];
  const listeners = new Map<string, () => void>();
  const width = { dataset: { p6ColumnWidth: "activity_id" }, value: "0", addEventListener: (_event: string, listener: () => void) => listeners.set("width", listener) };
  const pinned = { dataset: { p6ColumnPinned: "activity_id" }, checked: false, addEventListener: (_event: string, listener: () => void) => listeners.set("pinned", listener) };
  const frozen = { dataset: { p6ColumnFrozen: "activity_id" }, checked: false, addEventListener: (_event: string, listener: () => void) => listeners.set("frozen", listener) };
  const controls: Record<string, unknown[]> = {
    "[data-p6-column-width]": [width], "[data-p6-column-pinned]": [pinned], "[data-p6-column-frozen]": [frozen],
  };
  const container: RenderContainer = {
    innerHTML: "",
    querySelectorAll: ((selector: string) => (controls[selector] ?? []) as HTMLElement[]) as RenderContainer["querySelectorAll"],
  };
  renderMainWorkspace(container as unknown as HTMLElement, state, {
    onP6FieldPresentationChange: (fieldId, patch) => changes.push({ fieldId, patch: patch as Record<string, unknown> }),
  });
  listeners.get("width")?.();
  listeners.get("pinned")?.();
  listeners.get("frozen")?.();
  assert.deepEqual(changes, [
    { fieldId: "activity_id", patch: { pinned: false } },
    { fieldId: "activity_id", patch: { frozen: false } },
  ]);
});


test("P6 activity grid keeps presentation metadata on every rendered visible column", () => {
  const state = {
    ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    p6FieldRegistry: {
      registry_version: "p6-field-registry.v1", reference_product: "Oracle Primavera P6 Professional", reference_version: "test", status: "active",
      fields: [{ field_id: "activity_id", subject_area: "Activity", p6_field: "Activity ID", display_name: "Activity ID", data_type: "string", writable: false, computed: false, disposition: "standard" }],
    } as FieldRegistry,
    p6Layout: {
      schema_version: "p6-layout.v1", scope: "project", view_id: "activity", revision: 2,
      columns: [
        { field_id: "activity_id", visible: true, order: 0, width: 120, alignment: "end", pinned: true, frozen: false },
      ],
    } as LayoutDefinition,
    activities: [{ id: "A-100", wbsId: "WBS-1", code: "A100", name: "Excavate" }],
  };
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  assert.match(container.innerHTML, /<th[^>]*data-p6-grid-field-id="activity_id"[^>]*data-p6-grid-alignment="end"[^>]*data-p6-grid-pinned="true"[^>]*data-p6-grid-frozen="false"/);
  assert.match(container.innerHTML, /<td[^>]*data-p6-grid-field-id="activity_id"[^>]*data-p6-grid-alignment="end"[^>]*data-p6-grid-pinned="true"[^>]*data-p6-grid-frozen="false"/);
});


test("formula editor expression changes are forwarded without client-side evaluation", () => {
  const state = createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en");
  const formulaState: P6FormulaEditorState = {
    field_id: "activity-cost", expression: "Original Duration", validating: false, authoritative: null,
  };
  const container: RenderContainer = { innerHTML: "", querySelectorAll: () => [] };
  const listeners = new Map<string, () => void>();
  const textarea = {
    value: "Original Duration * Units",
    addEventListener: (_event: string, listener: () => void) => listeners.set("formula", listener),
  };
  container.querySelectorAll = ((selector: string) => selector === "[data-p6-formula-expression]" ? [textarea] as unknown as HTMLElement[] : []) as RenderContainer["querySelectorAll"];
  const expressions: string[] = [];
  renderMainWorkspace(container as unknown as HTMLElement, state, {
    p6FormulaEditorState: formulaState,
    onP6FormulaExpressionChange: (expression) => expressions.push(expression),
  });
  listeners.get("formula")?.();
  assert.deepEqual(expressions, ["Original Duration * Units"]);
});


test("P6 grid presentation reorder controls forward authoritative ordering", () => {
  const state = {
    ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    p6FieldRegistry: {
      registry_version: "p6-field-registry.v1", reference_product: "Oracle Primavera P6 Professional", reference_version: "test", status: "active",
      fields: [
        { field_id: "activity_id", subject_area: "Activity", p6_field: "Activity ID", display_name: "Activity ID", data_type: "string", writable: false, computed: false, disposition: "standard" },
        { field_id: "duration", subject_area: "Activity", p6_field: "Original Duration", display_name: "Duration", data_type: "duration", writable: false, computed: false, disposition: "standard" },
      ],
    } as FieldRegistry,
    p6GridSorts: [
      { field_id: "activity_id", direction: "ascending", order: 0 },
      { field_id: "duration", direction: "descending", order: 1 },
    ] as P6GridSort[],
    p6GridGroups: [
      { field_id: "activity_id", order: 0 },
      { field_id: "duration", order: 1 },
    ] as WorkspaceState["p6GridGroups"],
    p6GridFilters: [
      { field_id: "activity_id", operator: "equals", value: "A-1" },
      { field_id: "duration", operator: "greater-than", value: 10 },
    ] as P6GridFilter[],
  };
  const listeners = new Map<string, () => void>();
  const buttons = [
    { dataset: { p6GridSortMoveDown: "duration" }, closest: () => ({ dataset: { order: "0" } }), addEventListener: (_event: string, listener: () => void) => listeners.set("sort", listener) },
    { dataset: { p6GridGroupMoveDown: "duration" }, closest: () => ({ dataset: { order: "0" } }), addEventListener: (_event: string, listener: () => void) => listeners.set("group", listener) },
    { dataset: { p6GridFilterMoveDown: "1" }, closest: () => ({ dataset: { order: "0" } }), addEventListener: (_event: string, listener: () => void) => listeners.set("filter", listener) },
  ];
  const controls: Record<string, unknown[]> = {
    "[data-p6-grid-sort-move-up], [data-p6-grid-sort-move-down]": [buttons[0]],
    "[data-p6-grid-group-move-up], [data-p6-grid-group-move-down]": [buttons[1]],
    "[data-p6-grid-filter-move-up], [data-p6-grid-filter-move-down]": [buttons[2]],
  };
  const container: RenderContainer = {
    innerHTML: "",
    querySelectorAll: ((selector: string) => (controls[selector] ?? []) as HTMLElement[]) as RenderContainer["querySelectorAll"],
  };
  const changes: Record<string, readonly (string | number)[]> = {};
  renderMainWorkspace(container as unknown as HTMLElement, state, {
    onP6GridSortReorder: (fieldIds) => { changes.sort = fieldIds; },
    onP6GridGroupReorder: (fieldIds) => { changes.group = fieldIds; },
    onP6GridFilterReorder: (indexes) => { changes.filter = indexes; },
  });
  listeners.get("sort")?.();
  listeners.get("group")?.();
  listeners.get("filter")?.();
  assert.deepEqual(changes, {
    sort: ["duration", "activity_id"],
    group: ["duration", "activity_id"],
    filter: [1, 0],
  });
  assert.match(container.innerHTML, /data-p6-grid-sort-move-down/);
  assert.match(container.innerHTML, /data-p6-grid-group-move-down/);
  assert.match(container.innerHTML, /data-p6-grid-filter-move-down/);
});

test("P6 grid filter values use field-typed controls and coercion", () => {
  const state = {
    ...createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en"),
    p6FieldRegistry: {
      registry_version: "p6-field-registry.v1", reference_product: "Oracle Primavera P6 Professional", reference_version: "test", status: "active",
      fields: [
        { field_id: "duration", subject_area: "Activity", p6_field: "Original Duration", display_name: "Duration", data_type: "duration", writable: true, computed: false, disposition: "standard" },
        { field_id: "critical", subject_area: "Activity", p6_field: "Critical", display_name: "Critical", data_type: "boolean", writable: true, computed: false, disposition: "standard" },
      ],
    } as FieldRegistry,
    p6GridFilters: [
      { field_id: "duration", operator: "greater-than", value: 10 },
      { field_id: "critical", operator: "equals", value: true },
    ] as P6GridFilter[],
  };
  const listeners = new Map<string, (event?: unknown) => void>();
  const controls: Record<string, unknown[]> = {};
  const container: RenderContainer = {
    innerHTML: "",
    querySelectorAll: ((selector: string) => {
      if (selector === "[data-p6-grid-filter-value]") return [
        { type: "number", value: "12.5", checked: false, closest: () => ({ dataset: { order: "0" } }), addEventListener: (_event: string, listener: (event?: unknown) => void) => listeners.set("duration", listener) },
        { type: "checkbox", value: "", checked: false, closest: () => ({ dataset: { order: "1" } }), addEventListener: (_event: string, listener: (event?: unknown) => void) => listeners.set("critical", listener) },
      ] as unknown as HTMLElement[];
      return (controls[selector] ?? []) as HTMLElement[];
    }) as RenderContainer["querySelectorAll"],
  };
  const changes: P6GridFilter[][] = [];
  renderMainWorkspace(container as unknown as HTMLElement, state, {
    onP6GridFilterChange: (filters) => changes.push(filters as P6GridFilter[]),
  });
  listeners.get("duration")?.();
  listeners.get("critical")?.();
  assert.match(container.innerHTML, /type="number"[^>]*data-p6-grid-filter-value/);
  assert.match(container.innerHTML, /type="checkbox"[^>]*data-p6-grid-filter-value/);
  assert.equal(changes[0]?.[0]?.value, 12.5);

});
