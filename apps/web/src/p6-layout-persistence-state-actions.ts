import type { P6LayoutPersistence } from "./p6-field-layout-foundation.js";
import type { WorkspaceState } from "./workspace-model.js";
import type { P6LayoutPersistenceController } from "./p6-layout-persistence-controller.js";
import { createP6LayoutPersistenceController } from "./p6-layout-persistence-controller.js";

export type P6LayoutPersistenceStateActions = {
  load(): Promise<WorkspaceState>;
  save(): Promise<WorkspaceState>;
};

export function createP6LayoutPersistenceStateActions(
  persistence: P6LayoutPersistence,
  scope: Parameters<P6LayoutPersistenceController["load"]>[0] extends never ? never : "global" | "project" | "user",
  viewId: string,
  getState: () => WorkspaceState,
  setState: (state: WorkspaceState) => void,
): P6LayoutPersistenceStateActions {
  const controller = createP6LayoutPersistenceController(persistence, scope, viewId);

  return {
    async load() {
      const next = await controller.load(getState());
      setState(next);
      return next;
    },
    async save() {
      const next = await controller.save(getState());
      setState(next);
      return next;
    },
  };
}
