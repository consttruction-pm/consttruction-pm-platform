import type { P6Field, LayoutDefinition } from "./p6-field-layout-foundation.js";
import { renderP6TypedFieldEditor } from "./p6-typed-field-editor.js";

export type P6GridCellValue = string | number | boolean | null;

export type P6GridCellViewOptions = {
  locale?: "fa" | "en";
  editing?: boolean;
};

export function renderP6GridCell(
  field: P6Field,
  layout: LayoutDefinition,
  value: P6GridCellValue,
  options: P6GridCellViewOptions = {},
): string {
  const column = layout.columns.find((candidate) => candidate.field_id === field.field_id);
  if (!column || !column.visible) return "";
  if (options.editing && field.writable && !field.computed) {
    return renderP6TypedFieldEditor(field, value, { locale: options.locale, disabled: false });
  }
  return `<span data-p6-grid-cell data-field-id="${escapeAttribute(field.field_id)}" data-disposition="${escapeAttribute(field.disposition)}">${renderDisplayValue(field, value)}</span>`;
}

function renderDisplayValue(field: P6Field, value: P6GridCellValue): string {
  if (value === null || value === undefined || value === "") return "—";
  if (field.data_type === "boolean") return value === true ? "✓" : "—";
  if (field.data_type === "percentage" && typeof value === "number") return `${value}%`;
  if (field.unit) return `${escapeHtml(String(value))} ${escapeHtml(field.unit)}`;
  return escapeHtml(String(value));
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]!);
}

function escapeAttribute(value: string): string {
  return escapeHtml(value);
}
