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
      return result.data;
    },
    async save(): Promise<LayoutDefinition> {
      throw new Error("P6_LAYOUT_SAVE_UNSUPPORTED");
    },
  };
}
