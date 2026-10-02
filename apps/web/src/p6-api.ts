import type { ApiTransport, ProjectContext } from "./client.js";
import { setP6FieldRegistry, type WorkspaceState } from "./workspace-model.js";
import type { FieldRegistry, LayoutDefinition, LayoutScope, P6Field, P6FieldRegistryProvider, P6LayoutPersistence } from "./p6-field-layout-foundation.js";

export async function loadP6FieldRegistryIntoWorkspace(
  state: WorkspaceState,
  provider: P6FieldRegistryProvider & { getRegistry(): Promise<FieldRegistry> },
): Promise<WorkspaceState> {
  const registry = await provider.getRegistry();
  return setP6FieldRegistry(state, registry);
}

export function createP6FieldRegistryProvider(transport: ApiTransport, context: ProjectContext, registryVersion: FieldRegistry["registry_version"] = "p6-field-registry.v1"): P6FieldRegistryProvider & { getRegistry(): Promise<FieldRegistry> } {
  let registry: FieldRegistry | null = null;
  const getRegistry = async (): Promise<FieldRegistry> => {
    const result = await transport.get<FieldRegistry>(`/api/projects/${encodeURIComponent(context.project_id)}/p6/fields/${encodeURIComponent(registryVersion)}`, context);
    if (!result.ok) throw new Error(result.error.code);
    if (result.data.registry_version !== registryVersion) throw new Error("P6_FIELD_REGISTRY_VERSION_MISMATCH");
    validateP6FieldRegistry(result.data);
    registry = result.data;
    return registry;
  };
  return {
    async getFields(subjectArea = "Activity"): Promise<readonly P6Field[]> {
      const current = registry ?? await getRegistry();
      return current.fields.filter((field) => field.subject_area === subjectArea);
    },
    getRegistry,
  };
}

export function createP6ReadOnlyLayoutPersistence(transport: ApiTransport, context: ProjectContext): P6LayoutPersistence {
  return {
    async load(scope: LayoutScope, viewId: string): Promise<LayoutDefinition | null> {
      const result = await transport.get<LayoutDefinition>(`/api/projects/${encodeURIComponent(context.project_id)}/p6/layouts/${encodeURIComponent(scope)}/${encodeURIComponent(viewId)}`, context);
      if (!result.ok) {
        if (result.error.code === "P6_LAYOUT_NOT_FOUND") return null;
        throw new Error(result.error.code);
      }
      if (result.data.schema_version !== "p6-layout.v1") {
        throw new Error("P6_LAYOUT_SCHEMA_VERSION_MISMATCH");
      }
      validateP6Layout(result.data);
      return result.data;
    },
    async save(): Promise<LayoutDefinition> {
      throw new Error("P6_LAYOUT_SAVE_UNSUPPORTED");
    },
  };
}

function validateP6FieldRegistry(registry: FieldRegistry): void {
  if (
    !registry ||
    registry.reference_product !== "Oracle Primavera P6 Professional" ||
    !Array.isArray(registry.fields)
  ) {
    throw new Error("INVALID_P6_FIELD_REGISTRY");
  }

  const validDataTypes = new Set([
    "string", "date", "datetime", "duration", "decimal", "percentage",
    "boolean", "enum", "integer", "double", "cost", "unit",
    "object-id", "object-id-array", "string-array", "complex", "spread",
  ]);
  const fieldIds = new Set<string>();
  for (const field of registry.fields) {
    if (
      !field ||
      typeof field.field_id !== "string" ||
      !field.field_id.trim() ||
      typeof field.subject_area !== "string" ||
      !field.subject_area.trim() ||
      typeof field.p6_field !== "string" ||
      !field.p6_field.trim() ||
      typeof field.display_name !== "string" ||
      !field.display_name.trim() ||
      typeof field.writable !== "boolean" ||
      typeof field.computed !== "boolean" ||
      typeof field.disposition !== "string" ||
      !validDataTypes.has(field.data_type)
    ) {
      throw new Error("INVALID_P6_FIELD_REGISTRY");
    }
    if (fieldIds.has(field.field_id)) {
      throw new Error("INVALID_P6_FIELD_REGISTRY");
    }
    fieldIds.add(field.field_id);
  }
}


function validateP6Layout(layout: LayoutDefinition): void {
  if (
    !layout ||
    !["global", "project", "user"].includes(layout.scope) ||
    typeof layout.view_id !== "string" ||
    !layout.view_id.trim() ||
    !Array.isArray(layout.columns) ||
    !Number.isInteger(layout.revision) ||
    layout.revision < 0
  ) {
    throw new Error("INVALID_P6_LAYOUT");
  }

  const fieldIds = new Set<string>();
  for (const column of layout.columns) {
    if (
      !column ||
      typeof column.field_id !== "string" ||
      !column.field_id.trim() ||
      fieldIds.has(column.field_id) ||
      typeof column.visible !== "boolean" ||
      !Number.isInteger(column.order) ||
      column.order < 0 ||
      typeof column.width !== "number" ||
      !Number.isFinite(column.width) ||
      column.width < 0 ||
      !["start", "center", "end"].includes(column.alignment) ||
      typeof column.pinned !== "boolean" ||
      typeof column.frozen !== "boolean" ||
      (column.label !== undefined && column.label !== null && typeof column.label !== "string")
    ) {
      throw new Error("INVALID_P6_LAYOUT");
    }
    fieldIds.add(column.field_id);
  }

  if (!layout.columns.every((column, index) => column.order === index)) {
    throw new Error("INVALID_P6_LAYOUT");
  }
}
