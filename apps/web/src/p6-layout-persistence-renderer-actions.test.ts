import test from "node:test";
import assert from "node:assert/strict";
import { createP6LayoutPersistenceRendererActions } from "./p6-layout-persistence-renderer-actions.js";

test("P6 layout persistence renderer actions delegate load and save", async () => {
  const calls: string[] = [];
  const actions = createP6LayoutPersistenceRendererActions({
    getState: () => ({ busy: false, error: null }),
    load: async () => {
      calls.push("load");
      return {} as never;
    },
    save: async () => {
      calls.push("save");
      return {} as never;
    },
  });

  actions.onP6LayoutLoad?.();
  actions.onP6LayoutSave?.();
  await Promise.resolve();

  assert.deepEqual(calls, ["load", "save"]);
});

test("P6 layout persistence renderer actions contain rejected event operations", async () => {
  const calls: string[] = [];
  const actions = createP6LayoutPersistenceRendererActions({
    getState: () => ({ busy: false, error: null }),
    load: async () => {
      calls.push("load");
      throw new Error("LOAD_FAILED");
    },
    save: async () => {
      calls.push("save");
      throw new Error("SAVE_FAILED");
    },
  });

  actions.onP6LayoutLoad?.();
  actions.onP6LayoutSave?.();
  await new Promise<void>((resolve) => setImmediate(resolve));

  assert.deepEqual(calls, ["load", "save"]);
});
