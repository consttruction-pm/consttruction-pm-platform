import type { ProjectContext } from "./client.js";
import type { WorkspaceColumn, WorkspaceState } from "./workspace-model.js";
import type { P6FieldCatalogEntry, P6FieldDataType } from "./p6-field-registry-client.js";
import { createDefaultLayout, type WorkspaceLayout, type WorkspaceLayoutStore } from "./workspace-layout.js";

export type WorkspaceFieldView = "activity" | "wbs" | "project" | "resource";

export type WorkspaceColumnDescriptor = Readonly<{
  fieldId: string;
  label: string;
  dataType: P6FieldDataType;
  editable: boolean;
  computed: boolean;
  unit: string | null;
}>;

export function buildWorkspaceColumnsFromFieldCatalog(
  fields: readonly P6FieldCatalogEntry[],
): readonly WorkspaceColumn[] {
  return Object.freeze(
    fields.map((field) => Object.freeze({
      id: field.id,
      label: field.label,
      dataType: field.dataType === "integer" ? "integer" : field.dataType === "decimal" || field.dataType === "double" || field.dataType === "percentage" || field.dataType === "cost" || field.dataType === "unit" ? "decimal" : field.dataType === "date" || field.dataType === "datetime" ? "date" : field.dataType === "duration" ? "duration" : field.dataType === "boolean" ? "boolean" : "text",
      editable: field.writable && !field.computed,
      formula: null,
      width: field.dataType === "duration" ? 110 : field.dataType === "date" || field.dataType === "datetime" ? 120 : 140,
    })),
  );
}

export function buildWorkspaceColumnsFromLayout(
  layout: WorkspaceLayout,
  fields: readonly P6FieldCatalogEntry[],
): readonly WorkspaceColumn[] {
  const byId = new Map(
    fields
      .filter((field) => field.subjectArea === layout.subject_area)
      .map((field) => [field.id, field]),
  );

  return Object.freeze(
    [...layout.columns]
      .filter((column) => column.visible)
      .sort((a, b) => a.order - b.order)
      .flatMap((column) => {
        const field = byId.get(column.fieldId);
        if (!field) return [];
        return [Object.freeze({
          id: field.id,
          label: column.labelOverride ?? field.label,
          dataType:
            field.dataType === "integer"
              ? "integer"
              : field.dataType === "decimal" ||
                  field.dataType === "double" ||
                  field.dataType === "percentage" ||
                  field.dataType === "cost" ||
                  field.dataType === "unit"
                ? "decimal"
                : field.dataType === "date" || field.dataType === "datetime"
                  ? "date"
                  : field.dataType === "duration"
                    ? "duration"
                    : field.dataType === "boolean"
                      ? "boolean"
                      : "text",
          editable: field.writable && !field.computed,
          formula: null,
          width: column.width,
        })];
      }),
  );
}

export function applyWorkspaceLayout(
  state: WorkspaceState,
  layout: WorkspaceLayout,
  fields: readonly P6FieldCatalogEntry[],
): WorkspaceState {
  if (state.context.revision !== layout.revision) {
    throw new Error("WORKSPACE_LAYOUT_REVISION_MISMATCH");
  }
  return {
    ...state,
    columns: buildWorkspaceColumnsFromLayout(layout, fields),
  };
}

export function buildWorkspaceColumnCatalog(
  subjectArea: string,
  fields: readonly P6FieldCatalogEntry[],
): readonly WorkspaceColumnDescriptor[] {
  return Object.freeze(
    fields
      .filter((field) => field.subjectArea === subjectArea)
      .map((field) => Object.freeze({
        fieldId: field.id,
        label: field.label,
        dataType: field.dataType,
        editable: field.writable && !field.computed,
        computed: field.computed,
        unit: field.unit,
      })),
  );
}

export function layoutKey(
  context: ProjectContext,
  subjectArea: string,
  scope: "global" | "project" | "user",
  userId?: string,
): string {
  const suffix = scope === "user" ? `:${userId ?? "anonymous"}` : "";
  return `${context.tenant_id}:${context.project_id}:${subjectArea}:${scope}${suffix}`;
}

export function loadOrCreateLayout(
  store: WorkspaceLayoutStore,
  key: string,
  layoutId: string,
  subjectArea: string,
  scope: "global" | "project" | "user",
  context: ProjectContext,
  catalog: readonly P6FieldCatalogEntry[],
): WorkspaceLayout {
  const existing = store.load(key);
  return existing ?? createDefaultLayout(layoutId, subjectArea, scope, context.revision, catalog);
}

export function dataTypeToEditorKind(dataType: P6FieldDataType): "text" | "number" | "date" | "duration" | "boolean" | "enum" | "object" {
  switch (dataType) {
    case "date":
    case "datetime":
      return "date";
    case "duration":
      return "duration";
    case "decimal":
    case "double":
    case "integer":
    case "percentage":
    case "cost":
    case "unit":
      return "number";
    case "boolean":
      return "boolean";
    case "enum":
      return "enum";
    case "object-id":
    case "object-id-array":
    case "complex":
    case "spread":
      return "object";
    default:
      return "text";
  }
}
