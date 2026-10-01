import type { LayoutScope, P6LayoutPersistence } from "./p6-field-layout-foundation.js";
import type { WorkspaceState } from "./workspace-model.js";
import { setP6Presentation } from "./workspace-model.js";

export type P6LayoutPersistenceController = {
  load(state: WorkspaceState): Promise<WorkspaceState>;
  save(state: WorkspaceState): Promise<WorkspaceState>;
};

export function createP6LayoutPersistenceController(
  persistence: P6LayoutPersistence,
  scope: LayoutScope,
  viewId: string,
): P6LayoutPersistenceController {
  return {
    async load(state) {
      if (!state.p6FieldRegistry) {
        throw new Error("P6_PRESENTATION_NOT_INITIALIZED");
      }
      const layout = await persistence.load(scope, viewId);
      if (!layout) return state;
      return setP6Presentation(state, state.p6FieldRegistry, layout);
    },
    async save(state) {
      if (!state.p6FieldRegistry || !state.p6Layout) {
        throw new Error("P6_PRESENTATION_NOT_INITIALIZED");
      }
      const persisted = await persistence.save(state.p6Layout);
      return setP6Presentation(state, state.p6FieldRegistry, persisted);
    },
  };
}
