import type { ApiTransport, ApiResult, ProjectContext } from "./client.js";
import {
  createP6LayoutPersistence,
  type P6LayoutPersistenceTransport,
} from "./p6-layout-persistence-adapter.js";
import type {
  FieldRegistry,
  LayoutDefinition,
  P6Field,
  P6FieldRegistryProvider,
  P6LayoutPersistence,
} from "./p6-field-layout-foundation.js";

export type P6FieldRegistryResponse = FieldRegistry;

function registryPath(context: ProjectContext): string {
  return `/api/projects/${encodeURIComponent(context.project_id)}/p6/fields/p6-field-registry.v1`;
}

function layoutPath(context: ProjectContext, scope: LayoutDefinition["scope"], viewId: string): string {
  return `/api/projects/${encodeURIComponent(context.project_id)}/p6/layouts/${encodeURIComponent(scope)}/${encodeURIComponent(viewId)}`;
}

function unwrap<T>(result: ApiResult<T>): T {
  if (!result.ok) throw new Error(result.error.code);
  return result.data;
}

function assertRegistry(value: unknown): FieldRegistry {
  if (!value || typeof value !== "object") throw new Error("INVALID_P6_FIELD_REGISTRY_RESPONSE");
  const registry = value as Partial<FieldRegistry>;
  if (registry.registry_version !== "p6-field-registry.v1") throw new Error("INVALID_P6_FIELD_REGISTRY_VERSION");
  if (typeof registry.reference_product !== "string" || typeof registry.reference_version !== "string") {
    throw new Error("INVALID_P6_FIELD_REGISTRY_METADATA");
  }
  if (!Array.isArray(registry.fields)) throw new Error("INVALID_P6_FIELD_REGISTRY_FIELDS");
  return registry as FieldRegistry;
}

function assertLayout(value: unknown): LayoutDefinition {
  if (!value || typeof value !== "object") throw new Error("INVALID_P6_LAYOUT_RESPONSE");
  const layout = value as Partial<LayoutDefinition>;
  if (layout.schema_version !== "p6-layout.v1") throw new Error("INVALID_P6_LAYOUT_SCHEMA");
  if (layout.scope !== "global" && layout.scope !== "project" && layout.scope !== "user") {
    throw new Error("INVALID_P6_LAYOUT_SCOPE");
  }
  if (typeof layout.view_id !== "string" || !layout.view_id) throw new Error("INVALID_P6_LAYOUT_VIEW");
  if (!Number.isInteger(layout.revision) || (layout.revision ?? -1) < 0) {
    throw new Error("INVALID_P6_LAYOUT_REVISION");
  }
  if (!Array.isArray(layout.columns)) throw new Error("INVALID_P6_LAYOUT_COLUMNS");
  return layout as LayoutDefinition;
}

export function createP6FieldRegistryProvider(
  transport: ApiTransport,
  context: ProjectContext,
): P6FieldRegistryProvider & { getRegistry(): Promise<FieldRegistry> } {
  return {
    async getRegistry() {
      return assertRegistry(unwrap(await transport.get<P6FieldRegistryResponse>(
        registryPath(context),
        context,
      )));
    },
    async getFields(subjectArea?: string): Promise<readonly P6Field[]> {
      const registry = await this.getRegistry();
      return subjectArea
        ? registry.fields.filter((field) => field.subject_area === subjectArea)
        : registry.fields;
    },
  };
}

export function createP6LayoutPersistence(
  transport: ApiTransport,
  context: ProjectContext,
): P6LayoutPersistence {
  const adapterTransport: P6LayoutPersistenceTransport = {
    async load(scope, viewId) {
      const result = await transport.get<LayoutDefinition>(
        layoutPath(context, scope, viewId),
        context,
      );
      if (!result.ok) {
        if (result.error.code === "P6_LAYOUT_NOT_FOUND") return null;
        throw new Error(result.error.code);
      }
      return assertLayout(result.data);
    },
    async save(layout) {
      const result = await transport.post<
        Pick<LayoutDefinition, "revision" | "columns"> & { metadata?: Record<string, unknown> },
        LayoutDefinition
      >(
        layoutPath(context, layout.scope, layout.view_id),
        {
          revision: layout.revision,
          columns: layout.columns,
          metadata: layout.metadata ?? {},
        },
        context,
      );
      return assertLayout(unwrap(result));
    },
  };
  return createP6LayoutPersistence(adapterTransport);
}

export async function loadP6Presentation(
  state: import("./workspace-model.js").WorkspaceState,
  transport: ApiTransport,
  context: ProjectContext,
): Promise<import("./workspace-model.js").WorkspaceState> {
  const registry = await createP6FieldRegistryProvider(transport, context).getRegistry();
  const persistence = createP6LayoutPersistence(transport, context);
  const layout = await persistence.load("project", "activity");
  const initialLayout: LayoutDefinition = layout ?? {
    schema_version: "p6-layout.v1",
    scope: "project",
    view_id: "activity",
    revision: 0,
    columns: [],
  };
  const { setP6Presentation } = await import("./workspace-model.js");
  return setP6Presentation(state, registry, initialLayout);
}
