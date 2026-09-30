import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { createP6LayoutPersistence } from "./p6-layout-persistence-adapter.js";
import type { LayoutDefinition } from "./p6-field-layout-foundation.js";

const layout: LayoutDefinition = {
  schema_version: "p6-layout.v1",
  scope: "project",
  view_id: "activity",
  revision: 2,
  columns: [
    { field_id: "activity_id", visible: true, order: 0, width: 120, alignment: "start", pinned: false, frozen: false },
  ],
};

describe("P6 layout persistence adapter", () => {
  it("loads null and validates persisted layouts", async () => {
    const persistence = createP6LayoutPersistence({
      async load() { return layout; },
      async save(value) { return value; },
    });

    assert.deepEqual(await persistence.load("project", "activity"), layout);
  });

  it("rejects malformed persisted layouts", async () => {
    const persistence = createP6LayoutPersistence({
      async load() {
        return { ...layout, columns: [{ ...layout.columns[0], order: 4 }] };
      },
      async save(value) { return value; },
    });

    await assert.rejects(() => persistence.load("project", "activity"), /NON_NORMALIZED_LAYOUT/);
  });

  it("validates the payload before delegating save", async () => {
    let saved: LayoutDefinition | null = null;
    const persistence = createP6LayoutPersistence({
      async load() { return null; },
      async save(value) { saved = value; return value; },
    });

    const result = await persistence.save(layout);
    assert.deepEqual(saved, layout);
    assert.deepEqual(result, layout);
  });
});
