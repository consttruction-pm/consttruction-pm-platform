import test from "node:test";
import assert from "node:assert/strict";
import type { FieldRegistry, LayoutDefinition, P6LayoutPersistence } from "./p6-field-layout-foundation.js";
import type { WorkspaceState } from "./workspace-model.js";
import { createP6LayoutPersistenceController } from "./p6-layout-persistence-controller.js";

const registry: FieldRegistry = {
  registry_version: "p6-field-registry.v1",
  reference_product: "Oracle Primavera P6 Professional",
  reference_version: "test",
  status: "active",
  fields: [
    {
      field_id: "activity_id",
      subject_area: "activity",
      p6_field: "activity_id",
      display_name: "Activity ID",
      data_type: "string",
      writable: false,
      computed: false,
      disposition: "standard",
    },
  ],
};

const layout: LayoutDefinition = {
  schema_version: "p6-layout.v1",
  scope: "project",
  view_id: "activity",
  revision: 3,
  columns: [
    {
      field_id: "activity_id",
      visible: true,
      order: 0,
      label: "Activity ID",
      width: 180,
      alignment: "start",
      pinned: true,
      frozen: false,
    },
  ],
};

function stateWithLayout(currentLayout: LayoutDefinition | null): WorkspaceState {
  return {
    p6FieldRegistry: registry,
    p6Layout: currentLayout,
  } as WorkspaceState;
}

test("P6 layout persistence controller loads through the workspace authority", async () => {
  let loadedScope = "";
  let loadedView = "";
  const persistence: P6LayoutPersistence = {
    async load(scope, viewId) {
      loadedScope = scope;
      loadedView = viewId;
      return layout;
    },
    async save(value) {
      return value;
    },
  };

  const controller = createP6LayoutPersistenceController(persistence, "project", "activity");
  const state = await controller.load(stateWithLayout(null));

  assert.equal(loadedScope, "project");
  assert.equal(loadedView, "activity");
  assert.equal(state.p6Layout?.revision, 3);
  assert.equal(state.p6Layout?.columns[0]?.width, 180);
});

test("P6 layout persistence controller preserves state when no persisted layout exists", async () => {
  const existing = { ...layout, revision: 4 };
  const persistence: P6LayoutPersistence = {
    async load() {
      return null;
    },
    async save(value) {
      return value;
    },
  };

  const state = stateWithLayout(existing);
  const controller = createP6LayoutPersistenceController(persistence, "project", "activity");
  const result = await controller.load(state);

  assert.equal(result, state);
  assert.equal(result.p6Layout?.revision, 4);
});

test("P6 layout persistence controller saves and consumes the authoritative response", async () => {
  const saved = { ...layout, revision: 5, columns: [{ ...layout.columns[0], width: 220 }] };
  let received: LayoutDefinition | null = null;
  const persistence: P6LayoutPersistence = {
    async load() {
      return null;
    },
    async save(value) {
      received = value;
      return saved;
    },
  };

  const controller = createP6LayoutPersistenceController(persistence, "project", "activity");
  const result = await controller.save(stateWithLayout(layout));

  assert.equal(received, layout);
  assert.equal(result.p6Layout?.revision, 5);
  assert.equal(result.p6Layout?.columns[0]?.width, 220);
});

test("P6 layout persistence controller rejects load before registry initialization", async () => {
  const persistence: P6LayoutPersistence = {
    async load() {
      throw new Error("SHOULD_NOT_LOAD");
    },
    async save(value) {
      return value;
    },
  };
  const controller = createP6LayoutPersistenceController(persistence, "project", "activity");

  await assert.rejects(
    () => controller.load({ p6FieldRegistry: null, p6Layout: null } as WorkspaceState),
    /P6_PRESENTATION_NOT_INITIALIZED/,
  );
});

test("P6 layout persistence controller rejects save without an authoritative layout", async () => {
  const persistence: P6LayoutPersistence = {
    async load() {
      return null;
    },
    async save() {
      throw new Error("SHOULD_NOT_SAVE");
    },
  };
  const controller = createP6LayoutPersistenceController(persistence, "project", "activity");

  await assert.rejects(
    () => controller.save({ p6FieldRegistry: registry, p6Layout: null } as WorkspaceState),
    /P6_PRESENTATION_NOT_INITIALIZED/,
  );
});

test("P6 layout persistence controller rejects a loaded layout for another target", async () => {
  const persistence: P6LayoutPersistence = {
    async load() {
      return { ...layout, view_id: "wbs" };
    },
    async save(value) {
      return value;
    },
  };
  const controller = createP6LayoutPersistenceController(persistence, "project", "activity");

  await assert.rejects(
    () => controller.load(stateWithLayout(null)),
    /P6_LAYOUT_VIEW_MISMATCH/,
  );
});

test("P6 layout persistence controller rejects a save response for another scope", async () => {
  const persistence: P6LayoutPersistence = {
    async load() {
      return null;
    },
    async save(value) {
      return { ...value, scope: "user" };
    },
  };
  const controller = createP6LayoutPersistenceController(persistence, "project", "activity");

  await assert.rejects(
    () => controller.save(stateWithLayout(layout)),
    /P6_LAYOUT_SCOPE_MISMATCH/,
  );
});

test("P6 layout persistence controller rejects a loaded layout for another scope", async () => {
  const persistence: P6LayoutPersistence = {
    async load() {
      return { ...layout, scope: "user" };
    },
    async save(value) {
      return value;
    },
  };
  const controller = createP6LayoutPersistenceController(persistence, "project", "activity");

  await assert.rejects(
    () => controller.load(stateWithLayout(null)),
    /P6_LAYOUT_SCOPE_MISMATCH/,
  );
});

test("P6 layout persistence controller rejects a save response for another view", async () => {
  const persistence: P6LayoutPersistence = {
    async load() {
      return null;
    },
    async save(value) {
      return { ...value, view_id: "wbs" };
    },
  };
  const controller = createP6LayoutPersistenceController(persistence, "project", "activity");

  await assert.rejects(
    () => controller.save(stateWithLayout(layout)),
    /P6_LAYOUT_VIEW_MISMATCH/,
  );
});
