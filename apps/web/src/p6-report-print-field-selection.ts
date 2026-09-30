import type { LayoutDefinition, P6Field } from "./p6-field-layout-foundation.js";

export type P6ReportPrintSelection = {
  field_ids: readonly string[];
};

export type P6ReportPrintFieldSelectionModel = {
  getSelection(): P6ReportPrintSelection;
  setSelection(field_ids: readonly string[]): P6ReportPrintSelection;
  resetToVisible(layout: LayoutDefinition): P6ReportPrintSelection;
};

function normalizeSelection(layout: LayoutDefinition, field_ids: readonly string[]): P6ReportPrintSelection {
  const available = new Set(layout.columns.map((column) => column.field_id));
  const seen = new Set<string>();
  const normalized = field_ids.filter((fieldId) => available.has(fieldId) && !seen.has(fieldId));
  return { field_ids: normalized };
}

export function createP6ReportPrintFieldSelection(
  layout: LayoutDefinition,
  fields: readonly P6Field[],
  initial: readonly string[] = layout.columns.filter((column) => column.visible).map((column) => column.field_id),
): P6ReportPrintFieldSelectionModel {
  const registryIds = new Set(fields.map((field) => field.field_id));
  if (layout.columns.some((column) => !registryIds.has(column.field_id))) {
    throw new Error("UNKNOWN_FIELD");
  }

  let selection = normalizeSelection(layout, initial);

  return {
    getSelection() {
      return { field_ids: [...selection.field_ids] };
    },
    setSelection(field_ids) {
      selection = normalizeSelection(layout, field_ids);
      return { field_ids: [...selection.field_ids] };
    },
    resetToVisible(currentLayout) {
      selection = {
        field_ids: currentLayout.columns
          .filter((column) => column.visible)
          .map((column) => column.field_id),
      };
      return { field_ids: [...selection.field_ids] };
    },
  };
}
