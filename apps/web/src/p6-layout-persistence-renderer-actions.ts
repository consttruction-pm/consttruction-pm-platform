import type { WorkspaceRendererOptions } from "./workspace-view.js";
import type { P6LayoutPersistenceStateActions } from "./p6-layout-persistence-state-actions.js";

export type P6LayoutPersistenceRendererActions = Pick<
  WorkspaceRendererOptions,
  "onP6LayoutLoad" | "onP6LayoutSave"
>;

export function createP6LayoutPersistenceRendererActions(
  actions: P6LayoutPersistenceStateActions,
): P6LayoutPersistenceRendererActions {
  return {
    onP6LayoutLoad: () => {
      void actions.load();
    },
    onP6LayoutSave: () => {
      void actions.save();
    },
  };
}
