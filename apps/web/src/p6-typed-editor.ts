import type { P6FieldCatalogEntry, P6FieldDataType } from "./p6-field-registry-client.js";

export type TypedEditorValue =
  | { kind: "text"; value: string | null }
  | { kind: "number"; value: number | null }
  | { kind: "date"; value: string | null }
  | { kind: "duration"; value: number | null }
  | { kind: "boolean"; value: boolean | null }
  | { kind: "enum"; value: string | null }
  | { kind: "object"; value: string | null };

export function parseTypedEditorValue(
  field: P6FieldCatalogEntry,
  raw: string,
): TypedEditorValue {
  if (!field.writable || field.computed) throw new Error("FIELD_NOT_EDITABLE");
  switch (field.dataType) {
    case "date":
    case "datetime":
      return { kind: "date", value: raw.trim() || null };
    case "duration":
      return { kind: "duration", value: parseFiniteNumber(raw) };
    case "decimal":
    case "double":
    case "integer":
    case "percentage":
    case "cost":
    case "unit":
      return { kind: "number", value: parseFiniteNumber(raw) };
    case "boolean":
      if (raw === "") return { kind: "boolean", value: null };
      if (raw === "true") return { kind: "boolean", value: true };
      if (raw === "false") return { kind: "boolean", value: false };
      throw new Error("INVALID_BOOLEAN");
    case "enum":
      return { kind: "enum", value: raw.trim() || null };
    case "object-id":
    case "object-id-array":
    case "complex":
    case "spread":
      return { kind: "object", value: raw.trim() || null };
    default:
      return { kind: "text", value: raw };
  }
}

export function validateTypedEditorValue(
  field: P6FieldCatalogEntry,
  value: TypedEditorValue,
): void {
  if (!field.writable || field.computed) throw new Error("FIELD_NOT_EDITABLE");
  if (value.kind === "number" || value.kind === "duration") {
    if (value.value !== null && !Number.isFinite(value.value)) throw new Error("INVALID_NUMERIC_VALUE");
    if (field.dataType === "percentage" && value.value !== null && (value.value < 0 || value.value > 100)) {
      throw new Error("INVALID_PERCENTAGE");
    }
  }
  if (value.kind === "date" && value.value !== null && Number.isNaN(Date.parse(value.value))) {
    throw new Error("INVALID_DATE");
  }
}

function parseFiniteNumber(raw: string): number | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const value = Number(trimmed);
  if (!Number.isFinite(value)) throw new Error("INVALID_NUMERIC_VALUE");
  return value;
}

export type { P6FieldDataType };
