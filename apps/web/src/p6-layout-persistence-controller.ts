import type { LayoutDefinition, LayoutScope, P6LayoutPersistence } from "./p6-field-layout-foundation.js";
import type { WorkspaceState } from "./workspace-model.js";
import { setP6Presentation } from "./workspace-model.js";

export type P6LayoutPersistenceController = {
  load(state: WorkspaceState): Promise<WorkspaceState>;
  save(state: WorkspaceState): Promise<WorkspaceState>;
};

function assertLayoutTarget(
  layout: LayoutDefinition,
  scope: LayoutScope,
  viewId: string,
): LayoutDefinition {
  if (layout.scope !== scope) throw new Error("P6_LAYOUT_SCOPE_MISMATCH");
  if (layout.view_id !== viewId) throw new Error("P6_LAYOUT_VIEW_MISMATCH");
  return layout;
}

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
      return setP6Presentation(
        state,
        state.p6FieldRegistry,
        assertLayoutTarget(layout, scope, viewId),
      );
    },
    async save(state) {
      if (!state.p6FieldRegistry || !state.p6Layout) {
        throw new Error("P6_PRESENTATION_NOT_INITIALIZED");
      }
      const currentLayout = assertLayoutTarget(state.p6Layout, scope, viewId);
      const persisted = assertLayoutTarget(await persistence.save(currentLayout), scope, viewId);
      return setP6Presentation(state, state.p6FieldRegistry, persisted);
    },
  };
}
