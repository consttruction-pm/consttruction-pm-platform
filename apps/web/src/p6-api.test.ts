import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { createP6FieldRegistryProvider, createP6LayoutPersistence, loadP6Presentation } from "./p6-api.js";
import { createWorkspaceState } from "./workspace-model.js";
import type { ApiTransport } from "./client.js";

const context = { tenant_id: "t1", project_id: "p1", revision: 7 };

function transport(): ApiTransport {
  return {
    async get(path) {
      if (path.includes("/p6/fields/")) {
        return {
          ok: true,
          data: {
            registry_version: "p6-field-registry.v1",
            reference_product: "Oracle Primavera P6 Professional",
            reference_version: "26 / 26.4",
            status: "seeded_not_certified",
            fields: [{
              field_id: "activity_name",
              subject_area: "Activity",
              p6_field: "ActivityName",
              display_name: "Activity Name",
              data_type: "string",
              writable: true,
              computed: false,
              disposition: "implemented",
            }],
          },
        } as { ok: true; data: any };
      }
      return {
        ok: false,
        error: {
          code: "P6_LAYOUT_NOT_FOUND",
          retryable: false,
          message_key: "error.p6.layout.not_found",
          available_actions: [],
        },
      } as any;
    },
    async post<TRequest, TResponse>(path: string, request: TRequest): Promise<{ ok: true; data: TResponse }> {
      assert.equal(path, "/api/projects/p1/p6/layouts/project/activity");
      const payload = request as { revision: number; columns: unknown; metadata?: unknown };
      const response = {
        schema_version: "p6-layout.v1",
        scope: "project",
        view_id: "activity",
        revision: payload.revision,
        columns: payload.columns,
        metadata: payload.metadata,
      };
      return { ok: true, data: response as TResponse };
    },
  };
}

describe("P6 Web API adapters", () => {
  it("loads the authoritative registry and filters Activity fields", async () => {
    const provider = createP6FieldRegistryProvider(transport(), context);
    assert.equal((await provider.getFields("Activity")).length, 1);
    assert.equal((await provider.getRegistry()).reference_product, "Oracle Primavera P6 Professional");
  });

  it("maps a missing persisted layout to an empty presentation layout", async () => {
    const state = await loadP6Presentation(createWorkspaceState(context), transport(), context);
    assert.equal(state.p6FieldRegistry?.registry_version, "p6-field-registry.v1");
    assert.deepEqual(state.p6Layout?.columns, []);
  });

  it("persists through the authenticated project-scoped layout route", async () => {
    const persistence = createP6LayoutPersistence(transport(), context);
    const layout = {
      schema_version: "p6-layout.v1" as const,
      scope: "project" as const,
      view_id: "activity",
      revision: 1,
      columns: [],
      metadata: { source: "user-layout" },
    };
    const saved = await persistence.save(layout);
    assert.equal(saved.revision, 1);
    assert.deepEqual(saved.metadata, { source: "user-layout" });
  });
});
