import test from "node:test";
import { createWorkspaceState } from "./workspace-model.js";
import { loadP6FieldRegistryIntoWorkspace } from "./p6-api.js";
import assert from "node:assert/strict";
import { createP6FieldRegistryProvider, createP6ReadOnlyLayoutPersistence } from "./p6-api.js";
import type { ApiTransport } from "./client.js";

function transport(result: unknown): ApiTransport {
  return {
    get: async () => result as any,
    post: async () => { throw new Error("UNUSED"); },
  };
}

const context = { tenant_id: "t1", project_id: "p1", revision: 2 };

test("P6 registry bootstrap installs authoritative registry without layout", async () => {
  const context = { tenant_id: "tenant-1", project_id: "project-1", revision: 4 };
  const registry = {
    registry_version: "p6-field-registry.v1" as const,
    reference_product: "Oracle Primavera P6 Professional" as const,
    reference_version: "test",
    status: "seeded_not_certified",
    fields: [],
  };
  const state = await loadP6FieldRegistryIntoWorkspace(createWorkspaceState(context), {
    async getFields() { return []; },
    async getRegistry() { return registry; },
  });
  assert.equal(state.p6FieldRegistry?.reference_product, "Oracle Primavera P6 Professional");
  assert.equal(state.p6Layout, null);
});

test("P6 API adapters load and filter the authoritative field registry", async () => {
  const provider = createP6FieldRegistryProvider(transport({ ok: true, data: {
    registry_version: "p6-field-registry.v1",
    reference_product: "Oracle Primavera P6 Professional",
    reference_version: "26 / 26.4",
    status: "seeded_not_certified",
    fields: [
      { field_id: "activity.id", subject_area: "Activity", p6_field: "ActivityId", display_name: "Activity ID", data_type: "string", writable: true, computed: false, disposition: "seeded_not_certified" },
      { field_id: "wbs.id", subject_area: "WBS", p6_field: "WBSCode", display_name: "WBS Code", data_type: "string", writable: true, computed: false, disposition: "seeded_not_certified" },
    ],
  }}), context);
  assert.equal((await provider.getFields()).length, 1);
  assert.equal((await provider.getRegistry()).reference_product, "Oracle Primavera P6 Professional");
});

test("P6 field registry adapter rejects malformed field metadata", async () => {
  const provider = createP6FieldRegistryProvider(transport({ ok: true, data: {
    registry_version: "p6-field-registry.v1",
    reference_product: "Oracle Primavera P6 Professional",
    reference_version: "26 / 26.4",
    status: "seeded_not_certified",
    fields: [{
      field_id: "activity.id",
      subject_area: "Activity",
      p6_field: "ActivityId",
      display_name: "Activity ID",
      data_type: "unknown",
      writable: true,
      computed: false,
      disposition: "seeded_not_certified",
    }],
  }}), context);

  await assert.rejects(() => provider.getRegistry(), /INVALID_P6_FIELD_REGISTRY/);
});

test("P6 API adapters map missing layouts and reject unsupported saves", async () => {
  const persistence = createP6ReadOnlyLayoutPersistence(transport({ ok: false, error: { code: "P6_LAYOUT_NOT_FOUND", retryable: false, message_key: "error.p6.layout.not_found", available_actions: [] } }), context);
  assert.equal(await persistence.load("project", "activity"), null);
  await assert.rejects(persistence.save({} as any), /P6_LAYOUT_SAVE_UNSUPPORTED/);
});

test("P6 field registry adapter rejects duplicate field ids", async () => {
  const provider = createP6FieldRegistryProvider(transport({ ok: true, data: {
    registry_version: "p6-field-registry.v1",
    reference_product: "Oracle Primavera P6 Professional",
    reference_version: "26 / 26.4",
    status: "seeded_not_certified",
    fields: [
      { field_id: "activity.id", subject_area: "Activity", p6_field: "ActivityId", display_name: "Activity ID", data_type: "string", writable: true, computed: false, disposition: "seeded_not_certified" },
      { field_id: "activity.id", subject_area: "Activity", p6_field: "OtherId", display_name: "Other ID", data_type: "string", writable: true, computed: false, disposition: "seeded_not_certified" },
    ],
  }}), context);

  await assert.rejects(() => provider.getRegistry(), /INVALID_P6_FIELD_REGISTRY/);
});

test("P6 read-only layout adapter requests the selected project activity layout", async () => {
  let requestedPath = "";
  let requestedContext: unknown = null;
  const persistence = createP6ReadOnlyLayoutPersistence({
    get: async (path, receivedContext) => {
      requestedPath = path;
      requestedContext = receivedContext;
      return {
        ok: true,
        data: {
          schema_version: "p6-layout.v1",
          scope: "project",
          view_id: "activity",
          revision: 4,
          columns: [],
        },
      } as any;
    },
    post: async () => { throw new Error("UNUSED"); },
  }, context);

  const layout = await persistence.load("project", "activity");
  assert.equal(requestedPath, "/api/projects/p1/p6/layouts/project/activity");
  assert.equal(layout?.revision, 4);
  assert.deepEqual(requestedContext, context);
});

test("P6 read-only layout adapter rejects an unsupported schema version", async () => {
  const persistence = createP6ReadOnlyLayoutPersistence({
    get: async () => ({
      ok: true,
      data: {
        schema_version: "p6-layout.v2",
        scope: "project",
        view_id: "activity",
        revision: 4,
        columns: [],
      },
    } as any),
    post: async () => { throw new Error("UNUSED"); },
  }, context);

  await assert.rejects(
    () => persistence.load("project", "activity"),
    /P6_LAYOUT_SCHEMA_VERSION_MISMATCH/,
  );
});

test("P6 read-only layout adapter rejects an invalid revision", async () => {
  const persistence = createP6ReadOnlyLayoutPersistence({
    get: async () => ({
      ok: true,
      data: {
        schema_version: "p6-layout.v1",
        scope: "project",
        view_id: "activity",
        revision: -1,
        columns: [],
      },
    } as any),
    post: async () => { throw new Error("UNUSED"); },
  }, context);

  await assert.rejects(
    () => persistence.load("project", "activity"),
    /INVALID_P6_LAYOUT_REVISION/,
  );
});

test("P6 read-only layout adapter rejects malformed layout presentation", async () => {
  const persistence = createP6ReadOnlyLayoutPersistence({
    get: async () => ({
      ok: true,
      data: {
        schema_version: "p6-layout.v1",
        scope: "project",
        view_id: "activity",
        revision: 4,
        columns: [{
          field_id: "activity.id",
          visible: true,
          order: 0,
          label: null,
          width: Number.NaN,
          alignment: "start",
          pinned: false,
          frozen: false,
        }],
      },
    } as any),
    post: async () => { throw new Error("UNUSED"); },
  }, context);

  await assert.rejects(
    () => persistence.load("project", "activity"),
    /INVALID_P6_LAYOUT/,
  );
});

test("P6 read-only layout adapter accepts nullable and custom column labels", async () => {
  const persistence = createP6ReadOnlyLayoutPersistence({
    get: async () => ({
      ok: true,
      data: {
        schema_version: "p6-layout.v1",
        scope: "project",
        view_id: "activity",
        revision: 4,
        columns: [
          { field_id: "activity.id", visible: true, order: 0, label: null, width: 120, alignment: "start", pinned: false, frozen: false },
          { field_id: "activity.name", visible: true, order: 1, label: "Activity Name", width: 180, alignment: "start", pinned: false, frozen: false },
        ],
      },
    } as any),
    post: async () => { throw new Error("UNUSED"); },
  }, context);

  const layout = await persistence.load("project", "activity");
  assert.equal(layout?.columns[0]?.label, null);
  assert.equal(layout?.columns[1]?.label, "Activity Name");
});

test("P6 read-only layout adapter rejects duplicate layout field ids", async () => {
  const persistence = createP6ReadOnlyLayoutPersistence({
    get: async () => ({
      ok: true,
      data: {
        schema_version: "p6-layout.v1",
        scope: "project",
        view_id: "activity",
        revision: 4,
        columns: [
          { field_id: "activity.id", visible: true, order: 0, label: null, width: 120, alignment: "start", pinned: false, frozen: false },
          { field_id: "activity.id", visible: true, order: 1, label: null, width: 120, alignment: "start", pinned: false, frozen: false },
        ],
      },
    } as any),
    post: async () => { throw new Error("UNUSED"); },
  }, context);

  await assert.rejects(
    () => persistence.load("project", "activity"),
    /INVALID_P6_LAYOUT/,
  );
});
