import assert from "node:assert/strict";
import test from "node:test";
import type { FieldRegistry, LayoutDefinition } from "./p6-field-layout-foundation.js";
import { createWorkspaceState, setP6Presentation } from "./workspace-model.js";
import { createP6WorkspaceRendererActions } from "./p6-workspace-renderer-actions.js";

const registry: FieldRegistry = {
  registry_version: "p6-field-registry.v1",
  reference_product: "Oracle Primavera P6 Professional",
  reference_version: "test",
  status: "active",
  fields: [
    { field_id: "activity_id", subject_area: "Activity", p6_field: "Activity ID", display_name: "Activity ID", data_type: "string", writable: false, computed: false, disposition: "standard" },
    { field_id: "duration", subject_area: "Activity", p6_field: "Original Duration", display_name: "Duration", data_type: "duration", writable: true, computed: false, disposition: "standard" },
  ],
};

const layout: LayoutDefinition = {
  schema_version: "p6-layout.v1",
  scope: "project",
  view_id: "activity",
  revision: 1,
  columns: [
    { field_id: "activity_id", visible: true, order: 0, width: 120, alignment: "start", pinned: false, frozen: false },
    { field_id: "duration", visible: true, order: 1, width: 120, alignment: "end", pinned: false, frozen: false },
  ],
};

function initialState() {
  return setP6Presentation(
    createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 1 }),
    registry,
    layout,
  );
}

test("renderer actions delegate hide/show and field mutations to workspace authority", () => {
  let state = initialState();
  const actions = createP6WorkspaceRendererActions(() => state, (next) => { state = next; });

  actions.onP6FieldPresentationChange?.("duration", { visible: false });
  assert.equal(state.p6Layout?.columns.find((column) => column.field_id === "duration")?.visible, false);

  actions.onP6FieldPresentationChange?.("duration", { visible: true });
  actions.onP6FieldRemove?.("duration");
  assert.equal(state.p6Layout?.columns.length, 1);

  actions.onP6FieldAdd?.("duration");
  assert.equal(state.p6Layout?.columns.length, 2);

  actions.onP6FieldReorder?.(["duration", "activity_id"]);
  assert.equal(state.p6Layout?.columns[0].field_id, "duration");
});

test("renderer grid actions preserve authoritative field validation", () => {
  let state = initialState();
  const actions = createP6WorkspaceRendererActions(() => state, (next) => { state = next; });

  actions.onP6GridSortChange?.([{ field_id: "duration", direction: "descending", order: 4 }]);
  actions.onP6GridGroupChange?.([{ field_id: "activity_id", order: 8 }]);
  actions.onP6GridFilterChange?.([{ field_id: "duration", operator: "greater-than", value: 10 }]);

  assert.deepEqual(state.p6GridSorts, [{ field_id: "duration", direction: "descending", order: 0 }]);
  assert.deepEqual(state.p6GridGroups, [{ field_id: "activity_id", order: 0 }]);
  assert.deepEqual(state.p6GridFilters, [{ field_id: "duration", operator: "greater-than", value: 10 }]);
});


test("renderer cell edit action delegates typed value to workspace authority", () => {
  let state = initialState();
  state = {
    ...state,
    activities: [{ id: "A-1", wbsId: "W-1", code: "01", name: "Foundation" }],
  };
  const actions = createP6WorkspaceRendererActions(() => state, (next) => { state = next; });
  actions.onP6CellValueChange?.("A-1", "duration", "7.5");
  assert.equal(state.activities[0]?.cells?.duration, 7.5);
});


test("renderer presentation action delegates column metadata changes to workspace authority", () => {
  let state = initialState();
  const actions = createP6WorkspaceRendererActions(() => state, (next) => { state = next; });
  actions.onP6FieldPresentationChange?.("activity_id", { label: "Activity", width: 240, alignment: "center", pinned: true, frozen: true });
  const column = state.p6Layout?.columns.find((item) => item.field_id === "activity_id");
  assert.equal(column?.label, "Activity");
  assert.equal(column?.width, 240);
  assert.equal(column?.alignment, "center");
  assert.equal(column?.pinned, true);
  assert.equal(column?.frozen, true);
});
