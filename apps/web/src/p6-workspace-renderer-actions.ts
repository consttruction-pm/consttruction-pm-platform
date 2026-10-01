import type { WorkspaceRendererOptions } from "./workspace-view.js";
import type { WorkspaceState } from "./workspace-model.js";
import {
  addP6Field,
  removeP6Field,
  reorderP6Fields,
  updateP6FieldPresentation,
  updateP6ActivityCell,
  setP6GridFilters,
  setP6GridGroups,
  setP6GridSorts,
  addP6GridFilter,
  addP6GridGroup,
  addP6GridSort,
} from "./workspace-model.js";

export type P6WorkspaceStateSink = (state: WorkspaceState) => void;

export function createP6WorkspaceRendererActions(
  getState: () => WorkspaceState,
  setState: P6WorkspaceStateSink,
): Pick<
  WorkspaceRendererOptions,
  | "onP6FieldAdd"
  | "onP6FieldRemove"
  | "onP6FieldReorder"
  | "onP6FieldPresentationChange"
  | "onP6CellValueChange"
  | "onP6GridSortChange"
  | "onP6GridSortAdd"
  | "onP6GridGroupChange"
  | "onP6GridGroupAdd"
  | "onP6GridFilterChange"
  | "onP6GridFilterAdd"
> {
  const commit = (mutate: (state: WorkspaceState) => WorkspaceState): void => {
    setState(mutate(getState()));
  };

  return {
    onP6FieldAdd: (fieldId) => commit((state) => addP6Field(state, fieldId)),
    onP6FieldRemove: (fieldId) => commit((state) => removeP6Field(state, fieldId)),
    onP6FieldReorder: (fieldIds) => commit((state) => reorderP6Fields(state, fieldIds)),
    onP6FieldPresentationChange: (fieldId, patch) =>
      commit((state) => updateP6FieldPresentation(state, fieldId, patch)),
    onP6CellValueChange: (activityId, fieldId, value) =>
      commit((state) => updateP6ActivityCell(state, activityId, fieldId, value)),
    onP6GridSortChange: (sorts) => commit((state) => setP6GridSorts(state, sorts)),
    onP6GridSortAdd: () => commit((state) => addP6GridSort(state)),
    onP6GridGroupChange: (groups) => commit((state) => setP6GridGroups(state, groups)),
    onP6GridGroupAdd: () => commit((state) => addP6GridGroup(state)),
    onP6GridFilterChange: (filters) => commit((state) => setP6GridFilters(state, filters)),
    onP6GridFilterAdd: () => commit((state) => addP6GridFilter(state)),
  };
}
