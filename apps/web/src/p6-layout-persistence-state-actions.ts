import type { LayoutScope, P6LayoutPersistence } from "./p6-field-layout-foundation.js";
import type { WorkspaceState } from "./workspace-model.js";
import { createP6LayoutPersistenceController } from "./p6-layout-persistence-controller.js";

export type P6LayoutPersistenceStateActions = {
  load(): Promise<WorkspaceState>;
  save(): Promise<WorkspaceState>;
};

export function createP6LayoutPersistenceStateActions(
  persistence: P6LayoutPersistence,
  scope: LayoutScope,
  viewId: string,
  getState: () => WorkspaceState,
  setState: (state: WorkspaceState) => void,
): P6LayoutPersistenceStateActions {
  const controller = createP6LayoutPersistenceController(persistence, scope, viewId);
  let pending: Promise<void> = Promise.resolve();

  const enqueue = <T>(operation: () => Promise<T>): Promise<T> => {
    const result = pending.then(operation);
    pending = result.then(() => undefined, () => undefined);
    return result;
  };

  return {
    load() {
      return enqueue(async () => {
        const next = await controller.load(getState());
        setState(next);
        return next;
      });
    },
    save() {
      return enqueue(async () => {
        const next = await controller.save(getState());
        setState(next);
        return next;
      });
    },
  };
}
