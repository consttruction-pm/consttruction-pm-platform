import type { ProjectContext } from "./client.js";
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
