/**
 * Group-field catalog for the Activities table.
 *
 * Grouping is a presentation plan only: it reads values the project read model
 * already returned, never recalculates a date, duration or progress value and
 * never writes to an activity. The catalog is deliberately small — it offers
 * the fields this runtime can group reliably without inventing a value.
 */
import type {
  WorkspaceActivityGroupLevel,
  WorkspaceActivityRow,
  WorkspaceCellValue,
} from "./workspace-model.js";

export type WorkspaceGroupField = {
  readonly id: string;
  readonly en: string;
  readonly fa: string;
  /** Value style used by the band label and by sibling-band ordering. */
  readonly kind: "wbs" | "text" | "number" | "boolean";
};

export const WORKSPACE_GROUP_FIELDS: readonly WorkspaceGroupField[] = Object.freeze([
  Object.freeze({ id: "wbs", en: "WBS", fa: "ساختار شکست", kind: "wbs" as const }),
  Object.freeze({ id: "activity_status", en: "Activity Status", fa: "وضعیت فعالیت", kind: "text" as const }),
  Object.freeze({ id: "activity_type", en: "Activity Type", fa: "نوع فعالیت", kind: "text" as const }),
  Object.freeze({ id: "is_critical", en: "Critical", fa: "بحرانی", kind: "boolean" as const }),
  Object.freeze({ id: "activity_code", en: "Activity Code", fa: "کد فعالیت", kind: "text" as const }),
  Object.freeze({ id: "total_float", en: "Total Float", fa: "شناوری کل", kind: "number" as const }),
]);

export const MAX_GROUP_LEVELS = 3;

/**
 * Column ids that carry the same value as a group field. P6 field columns and
 * the filter catalog use different ids for the same activity fact, so a sort
 * plan must not re-order a band by a field the plan already groups.
 */
const GROUP_FIELD_ALIASES: Readonly<Record<string, readonly string[]>> = Object.freeze({
  wbs: ["wbs", "activity.wbs"],
  activity_status: ["activity_status", "activity.status"],
  activity_type: ["activity_type", "activity.type"],
  is_critical: ["is_critical", "activity.is_critical"],
  activity_code: ["activity_code", "activity.code"],
  total_float: ["total_float", "activity.total_float"],
});

export function groupFieldAliases(fieldId: string): readonly string[] {
  return GROUP_FIELD_ALIASES[fieldId] ?? [fieldId];
}

export function workspaceGroupField(fieldId: string): WorkspaceGroupField | null {
  return WORKSPACE_GROUP_FIELDS.find((field) => field.id === fieldId) ?? null;
}

export function isWorkspaceGroupFieldId(fieldId: string): boolean {
  return workspaceGroupField(fieldId) !== null;
}

/** Trims a plan to the known, unique, non-empty fields this runtime groups. */
export function normalizeGroupLevels(
  levels: readonly WorkspaceActivityGroupLevel[],
): readonly WorkspaceActivityGroupLevel[] {
  const seen = new Set<string>();
  const normalized: WorkspaceActivityGroupLevel[] = [];
  for (const level of levels) {
    if (normalized.length >= MAX_GROUP_LEVELS) break;
    const fieldId = typeof level.fieldId === "string" ? level.fieldId.trim() : "";
    if (fieldId === "" || seen.has(fieldId) || !isWorkspaceGroupFieldId(fieldId)) continue;
    seen.add(fieldId);
    normalized.push(Object.freeze({ fieldId, direction: level.direction === "desc" ? "desc" : "asc" }));
  }
  return Object.freeze(normalized);
}

/**
 * Reads the grouped value from the persisted row. A value this runtime cannot
 * read stays ``null`` and is shown in the trailing "No value" band instead of
 * being guessed.
 */
export function groupFieldValue(activity: WorkspaceActivityRow, fieldId: string): WorkspaceCellValue {
  const cells = activity.cells ?? {};
  switch (fieldId) {
    case "wbs": return activity.wbsId || cells["activity.wbs"] || null;
    case "activity_status": return cells["activity.status"] ?? cells["activity.activity_status"] ?? null;
    case "activity_type": return cells["activity.type"] ?? cells["activity.activity_type"] ?? null;
    case "is_critical": return cells["activity.is_critical"] ?? activity.gantt?.critical ?? null;
    case "activity_code": return activity.code || null;
    case "total_float": return cells["activity.total_float"] ?? null;
    default: return cells[fieldId] ?? null;
  }
}

export const EMPTY_GROUP_KEY = "e:";

/**
 * Stable key for a grouped value; also the persisted collapse-band token. The
 * type prefix keeps a text "1" apart from the number 1 and guarantees the key
 * is safe inside an HTML attribute and a layout metadata string.
 */
export function groupValueKey(value: WorkspaceCellValue): string {
  if (value === null || value === undefined) return EMPTY_GROUP_KEY;
  if (typeof value === "boolean") return value ? "b:true" : "b:false";
  if (typeof value === "number") return Number.isFinite(value) ? `n:${value}` : EMPTY_GROUP_KEY;
  const text = value.trim();
  return text === "" ? EMPTY_GROUP_KEY : `s:${text}`;
}

export function groupValueIsEmpty(value: WorkspaceCellValue): boolean {
  return groupValueKey(value) === EMPTY_GROUP_KEY;
}

/** Localized band label; stored choice values stay in their project language. */
export function groupValueLabel(
  fieldId: string,
  value: WorkspaceCellValue,
  locale: string,
): string {
  if (groupValueIsEmpty(value)) return locale.toLowerCase().startsWith("fa") ? "بدون مقدار" : "No value";
  if (fieldId === "is_critical") {
    const critical = value === true || String(value).toLowerCase() === "true";
    return locale.toLowerCase().startsWith("fa")
      ? (critical ? "بحرانی" : "غیربحرانی")
      : (critical ? "Critical" : "Non-critical");
  }
  return String(value);
}

export function groupFieldLabel(fieldId: string, locale: string): string {
  const field = workspaceGroupField(fieldId);
  if (!field) return fieldId;
  return locale.toLowerCase().startsWith("fa") ? field.fa : field.en;
}

/** Natural, numeric-aware comparison of two present values. */
export function compareGroupValues(left: WorkspaceCellValue, right: WorkspaceCellValue): number {
  if (typeof left === "number" && typeof right === "number") {
    return left === right ? 0 : left < right ? -1 : 1;
  }
  if (typeof left === "boolean" && typeof right === "boolean") {
    return left === right ? 0 : left ? -1 : 1;
  }
  return naturalCompare(String(left), String(right));
}

/**
 * Orders sibling bands. "No value" is always the last band, whatever the
 * direction; the direction only reverses comparisons between real values.
 */
export function compareGroupBands(
  left: WorkspaceCellValue,
  right: WorkspaceCellValue,
  direction: "asc" | "desc",
): number {
  const leftEmpty = groupValueIsEmpty(left);
  const rightEmpty = groupValueIsEmpty(right);
  if (leftEmpty || rightEmpty) return leftEmpty === rightEmpty ? 0 : leftEmpty ? 1 : -1;
  return (direction === "desc" ? -1 : 1) * compareGroupValues(left, right);
}

export function naturalCompare(left: string, right: string): number {
  const leftParts = left.match(/\d+|\D+/gu) ?? [];
  const rightParts = right.match(/\d+|\D+/gu) ?? [];
  const length = Math.max(leftParts.length, rightParts.length);
  for (let index = 0; index < length; index += 1) {
    const a = leftParts[index];
    const b = rightParts[index];
    if (a === undefined) return -1;
    if (b === undefined) return 1;
    const aNumeric = /^\d+$/u.test(a);
    const bNumeric = /^\d+$/u.test(b);
    if (aNumeric && bNumeric) {
      const difference = Number(a) - Number(b);
      if (difference !== 0) return difference < 0 ? -1 : 1;
      continue;
    }
    const comparison = a.localeCompare(b, undefined, { sensitivity: "base" });
    if (comparison !== 0) return comparison < 0 ? -1 : 1;
  }
  return 0;
}
