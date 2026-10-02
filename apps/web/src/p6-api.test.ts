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

test("P6 API adapters map missing layouts and reject unsupported saves", async () => {
    const persistence = createP6ReadOnlyLayoutPersistence(transport({ ok: false, error: { code: "P6_LAYOUT_NOT_FOUND", retryable: false, message_key: "error.p6.layout.not_found", available_actions: [] } }), context);
    assert.equal(await persistence.load("project", "activity"), null);
    await assert.rejects(persistence.save({} as any), /P6_LAYOUT_SAVE_UNSUPPORTED/);
});
