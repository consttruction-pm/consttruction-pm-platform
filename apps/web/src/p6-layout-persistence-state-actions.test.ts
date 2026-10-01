import test from "node:test";
import assert from "node:assert/strict";
import type { FieldRegistry, LayoutDefinition, P6LayoutPersistence } from "./p6-field-layout-foundation.js";
import type { WorkspaceState } from "./workspace-model.js";
import { createP6LayoutPersistenceStateActions } from "./p6-layout-persistence-state-actions.js";

const registry: FieldRegistry = {
  registry_version: "p6-field-registry.v1",
  reference_product: "Oracle Primavera P6 Professional",
  reference_version: "test",
  status: "active",
  fields: [{
    field_id: "activity_id",
    subject_area: "activity",
    p6_field: "activity_id",
    display_name: "Activity ID",
    data_type: "string",
    writable: false,
    computed: false,
    disposition: "standard",
  }],
};

const layout: LayoutDefinition = {
  schema_version: "p6-layout.v1",
  scope: "project",
  view_id: "activity",
  revision: 1,
  columns: [{
    field_id: "activity_id",
    visible: true,
    order: 0,
    label: "Activity ID",
    width: 180,
    alignment: "start",
    pinned: false,
    frozen: false,
  }],
};

function state(): WorkspaceState {
  return { p6FieldRegistry: registry, p6Layout: layout } as WorkspaceState;
}

test("P6 layout persistence state actions commit loaded state", async () => {
  let current = state();
  const loaded = { ...layout, revision: 2, columns: [{ ...layout.columns[0], width: 240 }] };
  const persistence: P6LayoutPersistence = {
    async load() { return loaded; },
    async save(value) { return value; },
  };
  const actions = createP6LayoutPersistenceStateActions(
    persistence,
    "project",
    "activity",
    () => current,
    (next) => { current = next; },
  );

  const result = await actions.load();

  assert.equal(result, current);
  assert.equal(current.p6Layout?.revision, 2);
  assert.equal(current.p6Layout?.columns[0]?.width, 240);
});

test("P6 layout persistence state actions commit saved state", async () => {
  let current = state();
  const saved = { ...layout, revision: 3, columns: [{ ...layout.columns[0], width: 260 }] };
  const persistence: P6LayoutPersistence = {
    async load() { return null; },
    async save() { return saved; },
  };
  const actions = createP6LayoutPersistenceStateActions(
    persistence,
    "project",
    "activity",
    () => current,
    (next) => { current = next; },
  );

  const result = await actions.save();

  assert.equal(result, current);
  assert.equal(current.p6Layout?.revision, 3);
  assert.equal(current.p6Layout?.columns[0]?.width, 260);
});
