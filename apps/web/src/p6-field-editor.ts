import type { P6Field, P6FieldDataType } from "./p6-field-layout-foundation.js";

export type P6FieldEditorControl =
  | "text" | "number" | "date" | "duration" | "boolean";

export type P6FieldEditorDescriptor = {
  fieldId: string;
  label: string;
  dataType: P6FieldDataType;
  control: P6FieldEditorControl;
  editable: boolean;
  nullable: boolean;
  computed: boolean;
  writable: boolean;
};

const NUMERIC_TYPES: ReadonlySet<P6FieldDataType> = new Set([
  "decimal", "double", "integer", "percentage", "cost", "unit",
]);

export function getP6FieldEditorDescriptor(field: P6Field): P6FieldEditorDescriptor {
  return {
    fieldId: field.field_id,
    label: field.display_name,
    dataType: field.data_type,
    control: toEditorControl(field.data_type),
    editable: field.writable && !field.computed,
    nullable: field.nullable === true,
    computed: field.computed,
    writable: field.writable,
  };
}

function toEditorControl(dataType: P6FieldDataType): P6FieldEditorControl {
  if (NUMERIC_TYPES.has(dataType)) return "number";
  switch (dataType) {
    case "date":
    case "datetime":
      return "date";
    case "duration":
      return "duration";
    case "boolean":
      return "boolean";
    default:
      return "text";
  }
}
