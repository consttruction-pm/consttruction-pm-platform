import type { P6Field, P6FieldDataType } from "./p6-field-layout-foundation.js";

export type P6TypedEditorValue = string | number | boolean | null;

export type P6TypedFieldEditorOptions = {
  locale?: "fa" | "en";
  disabled?: boolean;
};

export function coerceP6TypedFieldValue(
  field: P6Field,
  rawValue: string | boolean | null,
): P6TypedEditorValue {
  if (rawValue === null) return null;
  if (field.data_type === "boolean") return typeof rawValue === "boolean" ? rawValue : rawValue === "true";
  if (typeof rawValue === "boolean") return rawValue;
  if (isNumericType(field.data_type)) {
    if (rawValue.trim() === "") return null;
    const value = Number(rawValue);
    return Number.isFinite(value) ? value : null;
  }
  return rawValue;
}

export function renderP6TypedFieldEditor(
  field: P6Field,
  value: P6TypedEditorValue,
  options: P6TypedFieldEditorOptions = {},
): string {
  const locale = options.locale ?? "en";
  const disabled = options.disabled || !field.writable || field.computed ? " disabled" : "";
  const label = escapeHtml(field.display_name);
  const fieldId = escapeAttribute(field.field_id);
  const valueText = value === null ? "" : escapeAttribute(String(value));

  if (field.data_type === "boolean") {
    const checked = value === true ? " checked" : "";
    return `<label data-p6-typed-editor data-field-id="${fieldId}">
      <span>${label}</span>
      <input data-p6-typed-value="${fieldId}" type="checkbox"${checked}${disabled} aria-label="${escapeAttribute(label)}">
    </label>`;
  }

  const inputType = inputTypeFor(field.data_type);
  const step = isNumericType(field.data_type) ? (field.data_type === "integer" ? "1" : "any") : "";
  const stepAttribute = step ? ` step="${step}"` : "";
  const unit = field.unit ? ` <span data-p6-typed-unit>${escapeHtml(field.unit)}</span>` : "";
  const hint = locale === "fa" ? "ویرایش مقدار" : "Edit value";

  return `<label data-p6-typed-editor data-field-id="${fieldId}">
    <span>${label}</span>
    <input data-p6-typed-value="${fieldId}" type="${inputType}" value="${valueText}"${stepAttribute}${disabled} aria-label="${escapeAttribute(hint + " " + field.display_name)}">${unit}
  </label>`;
}

export function getP6TypedEditorDataType(field: P6Field): P6FieldDataType {
  return field.data_type;
}

function inputTypeFor(dataType: P6FieldDataType): "text" | "number" | "date" | "datetime-local" {
  if (dataType === "date") return "date";
  if (dataType === "datetime") return "datetime-local";
  if (isNumericType(dataType)) return "number";
  return "text";
}

function isNumericType(dataType: P6FieldDataType): boolean {
  return dataType === "integer"
    || dataType === "double"
    || dataType === "decimal"
    || dataType === "percentage"
    || dataType === "cost"
    || dataType === "duration"
    || dataType === "unit";
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]!);
}

function escapeAttribute(value: string): string {
  return escapeHtml(value);
}
