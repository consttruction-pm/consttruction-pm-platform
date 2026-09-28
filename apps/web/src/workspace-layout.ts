import type { P6FieldCatalogEntry } from "./p6-field-registry-client.js";

export const WORKSPACE_LAYOUT_VERSION = "workspace-layout.v1" as const;

export type WorkspaceColumnAlignment = "start" | "center" | "end";
export type WorkspaceColumnState = Readonly<{
  fieldId: string;
  visible: boolean;
  order: number;
  width: number;
  alignment: WorkspaceColumnAlignment;
  pinned: boolean;
  frozen: boolean;
  labelOverride: string | null;
}>;

export type WorkspaceLayout = Readonly<{
  contract_version: typeof WORKSPACE_LAYOUT_VERSION;
  layout_id: string;
  subject_area: string;
  scope: "global" | "project" | "user";
  revision: number;
  columns: readonly WorkspaceColumnState[];
}>;

export type WorkspaceLayoutStore = {
  load(key: string): WorkspaceLayout | null;
  save(key: string, layout: WorkspaceLayout): void;
};

export class MemoryWorkspaceLayoutStore implements WorkspaceLayoutStore {
  private readonly values = new Map<string, WorkspaceLayout>();

  load(key: string): WorkspaceLayout | null {
    return this.values.get(key) ?? null;
  }

  save(key: string, layout: WorkspaceLayout): void {
    this.values.set(key, layout);
  }
}

export function createDefaultLayout(
  layoutId: string,
  subjectArea: string,
  scope: WorkspaceLayout["scope"],
  revision: number,
  catalog: readonly P6FieldCatalogEntry[],
): WorkspaceLayout {
  assertRevision(revision);
  return Object.freeze({
    contract_version: WORKSPACE_LAYOUT_VERSION,
    layout_id: layoutId,
    subject_area: subjectArea,
    scope,
    revision,
    columns: Object.freeze(catalog.map((field, order) => Object.freeze({
      fieldId: field.id,
      visible: true,
      order,
      width: defaultWidth(field.dataType),
      alignment: defaultAlignment(field.dataType),
      pinned: false,
      frozen: false,
      labelOverride: null,
    }))),
  });
}

export function migrateWorkspaceLayout(
  input: unknown,
  catalog: readonly P6FieldCatalogEntry[],
  expectedRevision: number,
): WorkspaceLayout {
  assertRevision(expectedRevision);
  if (!isRecord(input)) throw new Error("INVALID_WORKSPACE_LAYOUT");
  const legacy = input as Record<string, unknown>;
  const contractVersion = legacy.contract_version;
  if (contractVersion !== undefined && contractVersion !== WORKSPACE_LAYOUT_VERSION && contractVersion !== "workspace-layout.legacy") {
    throw new Error("UNSUPPORTED_WORKSPACE_LAYOUT_VERSION");
  }

  const layoutId = stringValue(legacy.layout_id, "INVALID_WORKSPACE_LAYOUT_ID");
  const subjectArea = stringValue(legacy.subject_area, "INVALID_WORKSPACE_LAYOUT_SUBJECT");
  const scope = legacy.scope;
  if (scope !== "global" && scope !== "project" && scope !== "user") throw new Error("INVALID_WORKSPACE_LAYOUT_SCOPE");

  const rawColumns = Array.isArray(legacy.columns) ? legacy.columns : [];
  const known = new Map(catalog.map((field) => [field.id, field]));
  const migrated = rawColumns
    .filter(isRecord)
    .map((column, index) => normalizeColumn(column, index))
    .filter((column) => known.has(column.fieldId));

  const byId = new Map(migrated.map((column) => [column.fieldId, column]));
  const columns = catalog.map((field, catalogIndex) => {
    const existing = byId.get(field.id);
    return existing ?? {
      fieldId: field.id,
      visible: false,
      order: migrated.length + catalogIndex,
      width: defaultWidth(field.dataType),
      alignment: defaultAlignment(field.dataType),
      pinned: false,
      frozen: false,
      labelOverride: null,
    };
  });

  return Object.freeze({
    contract_version: WORKSPACE_LAYOUT_VERSION,
    layout_id: layoutId,
    subject_area: subjectArea,
    scope,
    revision: expectedRevision,
    columns: Object.freeze(reindexColumns(columns)),
  });
}

export function addColumn(layout: WorkspaceLayout, field: P6FieldCatalogEntry): WorkspaceLayout {
  if (field.subjectArea !== layout.subject_area) throw new Error("FIELD_SUBJECT_AREA_MISMATCH");
  if (layout.columns.some((column) => column.fieldId === field.id)) return layout;
  return updateColumns(layout, [
    ...layout.columns,
    {
      fieldId: field.id,
      visible: true,
      order: layout.columns.length,
      width: defaultWidth(field.dataType),
      alignment: defaultAlignment(field.dataType),
      pinned: false,
      frozen: false,
      labelOverride: null,
    },
  ]);
}

export function removeColumn(layout: WorkspaceLayout, fieldId: string): WorkspaceLayout {
  if (!layout.columns.some((column) => column.fieldId === fieldId)) return layout;
  return updateColumns(layout, layout.columns.filter((column) => column.fieldId !== fieldId));
}

export function setColumnState(
  layout: WorkspaceLayout,
  fieldId: string,
  patch: Partial<Omit<WorkspaceColumnState, "fieldId">>,
): WorkspaceLayout {
  const found = layout.columns.find((column) => column.fieldId === fieldId);
  if (!found) throw new Error("COLUMN_NOT_FOUND");
  if (patch.alignment !== undefined && !["start", "center", "end"].includes(patch.alignment)) throw new Error("INVALID_COLUMN_ALIGNMENT");
  return updateColumns(layout, layout.columns.map((column) =>
    column.fieldId === fieldId ? { ...column, ...patch } : column,
  ));
}

export function reorderColumn(layout: WorkspaceLayout, fieldId: string, targetOrder: number): WorkspaceLayout {
  if (!Number.isInteger(targetOrder) || targetOrder < 0) throw new Error("INVALID_COLUMN_ORDER");
  const columns = [...layout.columns].sort((a, b) => a.order - b.order);
  const index = columns.findIndex((column) => column.fieldId === fieldId);
  if (index < 0) throw new Error("COLUMN_NOT_FOUND");
  const [moved] = columns.splice(index, 1);
  columns.splice(Math.min(targetOrder, columns.length), 0, moved);
  return updateColumns(layout, columns.map((column, order) => ({ ...column, order })));
}

export function setColumnLabel(layout: WorkspaceLayout, fieldId: string, label: string | null): WorkspaceLayout {
  if (label !== null && !label.trim()) throw new Error("INVALID_COLUMN_LABEL");
  return setColumnState(layout, fieldId, { labelOverride: label });
}

function updateColumns(layout: WorkspaceLayout, columns: readonly WorkspaceColumnState[]): WorkspaceLayout {
  return Object.freeze({
    ...layout,
    columns: Object.freeze(reindexColumns(columns)),
  });
}

function reindexColumns(columns: readonly WorkspaceColumnState[]): WorkspaceColumnState[] {
  return [...columns]
    .sort((a, b) => a.order - b.order)
    .map((column, index) => Object.freeze({ ...column, order: index, width: normalizeWidth(column.width) }));
}

function normalizeColumn(input: Record<string, unknown>, index: number): WorkspaceColumnState {
  const fieldId = stringValue(input.fieldId ?? input.field_id, "INVALID_COLUMN_FIELD_ID");
  const visible = typeof input.visible === "boolean" ? input.visible : false;
  const order = integerValue(input.order, index);
  const width = normalizeWidth(typeof input.width === "number" ? input.width : 120);
  const alignment = input.alignment === "center" || input.alignment === "end" ? input.alignment : "start";
  const pinned = input.pinned === true;
  const frozen = input.frozen === true;
  const labelOverride = input.labelOverride === null || input.labelOverride === undefined
    ? null
    : stringValue(input.labelOverride, "INVALID_COLUMN_LABEL");
  return { fieldId, visible, order, width, alignment, pinned, frozen, labelOverride };
}

function defaultWidth(type: P6FieldCatalogEntry["dataType"]): number {
  if (type === "duration") return 110;
  if (type === "date" || type === "datetime") return 120;
  if (type === "percentage" || type === "decimal" || type === "double" || type === "cost") return 110;
  return 140;
}

function defaultAlignment(type: P6FieldCatalogEntry["dataType"]): WorkspaceColumnAlignment {
  if (type === "integer" || type === "decimal" || type === "double" || type === "percentage" || type === "cost" || type === "duration") return "end";
  return "start";
}

function normalizeWidth(value: number): number {
  if (!Number.isFinite(value)) throw new Error("INVALID_COLUMN_WIDTH");
  return Math.min(800, Math.max(48, Math.round(value)));
}

function assertRevision(revision: number): void {
  if (!Number.isInteger(revision) || revision < 0) throw new Error("INVALID_WORKSPACE_LAYOUT_REVISION");
}

function stringValue(value: unknown, code: string): string {
  if (typeof value !== "string" || !value.trim()) throw new Error(code);
  return value;
}

function integerValue(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isInteger(value) && value >= 0 ? value : fallback;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
