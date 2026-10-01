import type { LayoutScope, P6LayoutPersistence } from "./p6-field-layout-foundation.js";
import type { WorkspaceState } from "./workspace-model.js";
import { createP6LayoutPersistenceController } from "./p6-layout-persistence-controller.js";

export type P6LayoutPersistenceState = {
  busy: boolean;
  error: Error | null;
};

export type P6LayoutPersistenceStateActions = {
  getState(): P6LayoutPersistenceState;
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
  let persistenceState: P6LayoutPersistenceState = { busy: false, error: null };
  let pending: Promise<void> = Promise.resolve();

  const enqueue = <T>(operation: () => Promise<T>): Promise<T> => {
    const result = pending.then(operation);
    pending = result.then(() => undefined, () => undefined);
    return result;
  };

  const run = <T>(operation: () => Promise<T>): Promise<T> => enqueue(async () => {
    persistenceState = { busy: true, error: null };
    try {
      return await operation();
    } catch (error) {
      persistenceState = { busy: false, error: error instanceof Error ? error : new Error(String(error)) };
      throw error;
    } finally {
      persistenceState = { ...persistenceState, busy: false };
    }
  });

  return {
    getState: () => persistenceState,
    load: () => run(async () => {
      const next = await controller.load(getState());
      setState(next);
      return next;
    }),
    save: () => run(async () => {
      const next = await controller.save(getState());
      setState(next);
      return next;
    }),
  };
}
