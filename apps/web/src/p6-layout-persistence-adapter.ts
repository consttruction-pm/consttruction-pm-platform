import type {
  LayoutDefinition,
  LayoutScope,
  P6LayoutPersistence,
} from "./p6-field-layout-foundation.js";

export interface P6LayoutMigration {
  migrate(value: unknown): unknown;
}

export interface P6LayoutPersistenceTransport {
  load(scope: LayoutScope, viewId: string): Promise<unknown>;
  save(layout: LayoutDefinition): Promise<unknown>;
}

function assertLayout(value: unknown): LayoutDefinition {
  if (!value || typeof value !== "object") throw new Error("INVALID_LAYOUT_RESPONSE");
  const layout = value as Partial<LayoutDefinition>;
  if (layout.schema_version !== "p6-layout.v1") throw new Error("INVALID_LAYOUT_SCHEMA");
  if (layout.scope !== "global" && layout.scope !== "project" && layout.scope !== "user") throw new Error("INVALID_LAYOUT_SCOPE");
  if (typeof layout.view_id !== "string" || layout.view_id.length === 0) throw new Error("INVALID_LAYOUT_VIEW");
  const revision = layout.revision;
  if (typeof revision !== "number" || !Number.isInteger(revision) || revision < 0) throw new Error("INVALID_LAYOUT_REVISION");
  if (!Array.isArray(layout.columns)) throw new Error("INVALID_LAYOUT_COLUMNS");

  const ids = new Set<string>();
  layout.columns.forEach((column, index) => {
    if (!column || typeof column !== "object") throw new Error("INVALID_LAYOUT_COLUMN");
    const item = column as Record<string, unknown>;
    if (typeof item.field_id !== "string" || item.field_id.length === 0) throw new Error("INVALID_LAYOUT_FIELD");
    if (ids.has(item.field_id)) throw new Error("DUPLICATE_LAYOUT_FIELD");
    ids.add(item.field_id);
    if (item.order !== index) throw new Error("NON_NORMALIZED_LAYOUT");
    if (typeof item.visible !== "boolean" || typeof item.width !== "number") throw new Error("INVALID_LAYOUT_PRESENTATION");
  });
  return { ...layout, revision } as LayoutDefinition;
}

export function createP6LayoutPersistence(
  transport: P6LayoutPersistenceTransport,
  migration?: P6LayoutMigration,
): P6LayoutPersistence {
  return {
    async load(scope, viewId) {
      const value = await transport.load(scope, viewId);
      if (value == null) return null;
      return assertLayout(migration ? migration.migrate(value) : value);
    },
    async save(layout) {
      return assertLayout(await transport.save(assertLayout(layout)));
    },
  };
}
