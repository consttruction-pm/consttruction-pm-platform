import { describe, expect, it } from "vitest";
import { createP6FieldRegistryProvider, createP6ReadOnlyLayoutPersistence } from "./p6-api.js";
import type { ApiTransport } from "./client.js";

function transport(result: unknown): ApiTransport {
  return {
    get: async () => result as any,
    post: async () => { throw new Error("UNUSED"); },
  };
}

const context = { tenant_id: "t1", project_id: "p1", revision: 2 };

describe("P6 API adapters", () => {
  it("loads and filters the authoritative field registry", async () => {
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
    expect(await provider.getFields()).toHaveLength(1);
    expect((await provider.getRegistry()).reference_product).toBe("Oracle Primavera P6 Professional");
  });

  it("maps missing persisted layouts to null and rejects unsupported saves", async () => {
    const persistence = createP6ReadOnlyLayoutPersistence(transport({ ok: false, error: { code: "P6_LAYOUT_NOT_FOUND", retryable: false, message_key: "error.p6.layout.not_found", available_actions: [] } }), context);
    expect(await persistence.load("project", "activity")).toBeNull();
    await expect(persistence.save({} as any)).rejects.toThrow("P6_LAYOUT_SAVE_UNSUPPORTED");
  });
});
