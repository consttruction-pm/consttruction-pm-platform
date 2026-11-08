/**
 * Activity filter definitions and matching for the Activities window.
 *
 * Filters are a display concern: they never recalculate schedule facts and
 * never mutate the persisted activity rows. Predefined filters mirror the
 * P6 Professional Help table (Completed, Critical, In Progress, ...), and a
 * saved custom filter is stored with the project layout presentation so the
 * same selection returns after a reload or in another browser session.
 */
import type { WorkspaceActivityRow, WorkspaceCellValue } from "./workspace-model.js";

export const ACTIVITY_FILTER_OPERATORS = [
  "contains",
  "equals",
  "not-equals",
  "greater-than",
  "less-than",
  "is-empty",
  "is-not-empty",
] as const;
export type ActivityFilterOperator = (typeof ACTIVITY_FILTER_OPERATORS)[number];

export const ACTIVITY_FILTER_FIELDS = [
  "activity_id",
  "activity_name",
  "wbs",
  "activity_status",
  "activity_type",
  "progress",
  "duration",
  "total_float",
  "is_critical",
] as const;
export type ActivityFilterFieldId = (typeof ACTIVITY_FILTER_FIELDS)[number];

export type ActivityFilterCriterion = {
  fieldId: ActivityFilterFieldId;
  operator: ActivityFilterOperator;
  value: string;
};

export type ActivityFilterDefinition = {
  /** `builtin:*` for the documented defaults, `custom:<slug>` for saved filters. */
  id: string;
  name: string;
  match: "all" | "any";
  criteria: readonly ActivityFilterCriterion[];
  builtin?: boolean;
};

export type ActivityFilterState = {
  saved: readonly ActivityFilterDefinition[];
  activeId: string | null;
};

export const EMPTY_ACTIVITY_FILTERS: ActivityFilterState = Object.freeze({
  saved: Object.freeze([]),
  activeId: null,
});

function builtin(
  id: string,
  name: string,
  criteria: ActivityFilterCriterion[],
  match: "all" | "any" = "all",
): ActivityFilterDefinition {
  return Object.freeze({
    id,
    name,
    match,
    criteria: Object.freeze(criteria.map((criterion) => Object.freeze({ ...criterion }))),
    builtin: true,
  });
}

const BUILTIN_FILTERS: readonly ActivityFilterDefinition[] = Object.freeze([
  builtin("builtin:in-progress", "In Progress", [
    { fieldId: "activity_status", operator: "equals", value: "In Progress" },
  ]),
  builtin("builtin:not-started", "Not Started", [
    { fieldId: "activity_status", operator: "equals", value: "Not Started" },
  ]),
  builtin("builtin:completed", "Completed", [
    { fieldId: "activity_status", operator: "equals", value: "Completed" },
  ]),
  builtin("builtin:critical", "Critical", [
    { fieldId: "is_critical", operator: "equals", value: "true" },
  ]),
  builtin("builtin:non-critical", "Non Critical", [
    { fieldId: "is_critical", operator: "equals", value: "false" },
  ]),
  builtin("builtin:negative-float", "Negative Float", [
    { fieldId: "total_float", operator: "less-than", value: "0" },
  ]),
  builtin("builtin:milestones", "Milestone", [
    { fieldId: "activity_type", operator: "contains", value: "milestone" },
  ]),
]);

export function getBuiltinActivityFilters(): readonly ActivityFilterDefinition[] {
  return BUILTIN_FILTERS;
}

export function findActivityFilter(
  state: ActivityFilterState,
  id: string | null | undefined,
): ActivityFilterDefinition | null {
  if (!id) return null;
  return state.saved.find((filter) => filter.id === id)
    ?? BUILTIN_FILTERS.find((filter) => filter.id === id)
    ?? null;
}

export function getActiveActivityFilter(state: ActivityFilterState): ActivityFilterDefinition | null {
  return findActivityFilter(state, state.activeId);
}

const FIELD_LABELS: Record<ActivityFilterFieldId, { en: string; fa: string }> = {
  activity_id: { en: "Activity ID", fa: "شناسه فعالیت" },
  activity_name: { en: "Activity Name", fa: "نام فعالیت" },
  wbs: { en: "WBS", fa: "ساختار شکست" },
  activity_status: { en: "Activity Status", fa: "وضعیت فعالیت" },
  activity_type: { en: "Activity Type", fa: "نوع فعالیت" },
  progress: { en: "Progress %", fa: "درصد پیشرفت" },
  duration: { en: "Duration", fa: "مدت" },
  total_float: { en: "Total Float", fa: "شناوری کل" },
  is_critical: { en: "Critical", fa: "بحرانی" },
};

const OPERATOR_LABELS: Record<ActivityFilterOperator, { en: string; fa: string }> = {
  contains: { en: "contains", fa: "شامل" },
  equals: { en: "equals", fa: "برابر" },
  "not-equals": { en: "is not equal to", fa: "برابر نیست" },
  "greater-than": { en: "is greater than", fa: "بزرگ‌تر از" },
  "less-than": { en: "is less than", fa: "کوچک‌تر از" },
  "is-empty": { en: "is empty", fa: "خالی است" },
  "is-not-empty": { en: "is not empty", fa: "خالی نیست" },
};

export function activityFilterFieldLabel(fieldId: ActivityFilterFieldId, locale: string): string {
  const label = FIELD_LABELS[fieldId];
  return /^fa\b/i.test(locale) ? label.fa : label.en;
}

export function activityFilterOperatorLabel(operator: ActivityFilterOperator, locale: string): string {
  const label = OPERATOR_LABELS[operator];
  return /^fa\b/i.test(locale) ? label.fa : label.en;
}

/** Minimal WBS node shape needed to turn a WBS id into the name users see. */
export type WbsLabelNode = { id: string; localCode?: string; name?: string };

function buildWbsLabels(nodes: readonly WbsLabelNode[]): ReadonlyMap<string, string> {
  const labels = new Map<string, string>();
  for (const node of nodes) {
    const label = [node.localCode, node.name]
      .filter((part): part is string => typeof part === "string" && part.trim() !== "")
      .join(" ")
      .trim();
    if (label) labels.set(node.id, label);
  }
  return labels;
}

function fieldValue(
  activity: WorkspaceActivityRow,
  fieldId: ActivityFilterFieldId,
  wbsLabels?: ReadonlyMap<string, string>,
): WorkspaceCellValue {
  const cells = activity.cells ?? {};
  switch (fieldId) {
    case "activity_id": return activity.id || activity.code || cells["activity.id"] || null;
    case "activity_name": return activity.name || cells["activity.name"] || null;
    // Filtering by WBS must match the code and name shown in the table, not
    // the internal node id (which is a database key, not a user value).
    case "wbs": return (activity.wbsId ? wbsLabels?.get(activity.wbsId) : null) || activity.wbsId || cells["activity.wbs"] || null;
    case "activity_status": return cells["activity.status"] ?? cells["activity.activity_status"] ?? null;
    case "activity_type": return cells["activity.type"] ?? cells["activity.activity_type"] ?? null;
    case "progress": return cells["progress"] ?? cells["activity.duration_percent_complete"] ?? null;
    case "duration": return cells["duration"] ?? cells["activity.planned_duration"] ?? null;
    case "total_float": return cells["activity.total_float"] ?? null;
    case "is_critical": return cells["activity.is_critical"] ?? activity.gantt?.critical ?? null;
    default: return null;
  }
}

function isEmptyValue(value: WorkspaceCellValue): boolean {
  return value === null || value === undefined || (typeof value === "string" && value.trim() === "");
}

function numericValue(value: WorkspaceCellValue): number | null {
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value === "boolean") return value ? 1 : 0;
  if (typeof value === "string") {
    const match = /-?\d+(?:\.\d+)?/.exec(value);
    if (!match) return null;
    const parsed = Number(match[0]);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function booleanValue(value: WorkspaceCellValue): boolean | null {
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return value !== 0;
  if (typeof value === "string") {
    const normalized = value.trim().toLocaleLowerCase();
    if (normalized === "true" || normalized === "yes" || normalized === "1") return true;
    if (normalized === "false" || normalized === "no" || normalized === "0") return false;
  }
  return null;
}

export function criterionIsComplete(criterion: ActivityFilterCriterion): boolean {
  if (criterion.operator === "is-empty" || criterion.operator === "is-not-empty") return true;
  return criterion.value.trim().length > 0;
}

/** Matches one criterion; incomplete criteria never match anything. */
export function activityMatchesCriterion(
  activity: WorkspaceActivityRow,
  criterion: ActivityFilterCriterion,
  wbsLabels?: ReadonlyMap<string, string>,
): boolean {
  if (!criterionIsComplete(criterion)) return false;
  const value = fieldValue(activity, criterion.fieldId, wbsLabels);
  const empty = isEmptyValue(value);
  if (criterion.operator === "is-empty") return empty;
  if (criterion.operator === "is-not-empty") return !empty;
  if (empty) return false;

  if (criterion.fieldId === "is_critical") {
    const actual = booleanValue(value);
    const expected = booleanValue(criterion.value);
    if (actual === null || expected === null) return false;
    return criterion.operator === "not-equals" ? actual !== expected : actual === expected;
  }

  const expectedText = criterion.value.trim();
  if (criterion.operator === "contains") {
    return String(value).toLocaleLowerCase().includes(expectedText.toLocaleLowerCase());
  }
  if (criterion.operator === "equals" || criterion.operator === "not-equals") {
    const actualNumber = numericValue(value);
    const expectedNumber = numericValue(expectedText);
    const equal = typeof value === "number" || typeof value === "boolean" || /^-?\d+(?:\.\d+)?$/.test(expectedText)
      ? actualNumber !== null && expectedNumber !== null && actualNumber === expectedNumber
      : String(value).trim().toLocaleLowerCase() === expectedText.toLocaleLowerCase();
    return criterion.operator === "not-equals" ? !equal : equal;
  }

  const actualNumber = numericValue(value);
  const expectedNumber = numericValue(expectedText);
  if (actualNumber === null || expectedNumber === null) return false;
  return criterion.operator === "greater-than"
    ? actualNumber > expectedNumber
    : actualNumber < expectedNumber;
}

export function activityMatchesFilter(
  activity: WorkspaceActivityRow,
  filter: ActivityFilterDefinition | null,
  wbsLabels?: ReadonlyMap<string, string>,
): boolean {
  if (!filter) return true;
  const criteria = filter.criteria.filter(criterionIsComplete);
  if (criteria.length === 0) return true;
  return filter.match === "any"
    ? criteria.some((criterion) => activityMatchesCriterion(activity, criterion, wbsLabels))
    : criteria.every((criterion) => activityMatchesCriterion(activity, criterion, wbsLabels));
}

/**
 * Applies one saved/predefined filter without changing row order. Passing the
 * WBS nodes lets a `wbs` criterion match the displayed code and name instead of
 * the internal node id.
 */
export function filterActivitiesByDefinition(
  activities: readonly WorkspaceActivityRow[],
  filter: ActivityFilterDefinition | null,
  wbsNodes: readonly WbsLabelNode[] = [],
): readonly WorkspaceActivityRow[] {
  if (!filter) return activities;
  const wbsLabels = buildWbsLabels(wbsNodes);
  return activities.filter((activity) => activityMatchesFilter(activity, filter, wbsLabels));
}

const MAX_SAVED_FILTERS = 20;
const MAX_CRITERIA = 8;
const MAX_NAME = 60;
const MAX_VALUE = 120;

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function slug(value: string): string {
  return value
    .trim()
    .toLocaleLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48);
}

export function normalizeCriterion(value: unknown): ActivityFilterCriterion | null {
  if (!isRecord(value)) return null;
  const fieldId = value.fieldId;
  const operator = value.operator;
  if (typeof fieldId !== "string" || !(ACTIVITY_FILTER_FIELDS as readonly string[]).includes(fieldId)) return null;
  if (typeof operator !== "string" || !(ACTIVITY_FILTER_OPERATORS as readonly string[]).includes(operator)) return null;
  const rawValue = value.value;
  if (rawValue !== null && rawValue !== undefined && typeof rawValue !== "string") return null;
  return {
    fieldId: fieldId as ActivityFilterFieldId,
    operator: operator as ActivityFilterOperator,
    value: String(rawValue ?? "").slice(0, MAX_VALUE),
  };
}

export function normalizeActivityFilter(value: unknown): ActivityFilterDefinition | null {
  if (!isRecord(value)) return null;
  const name = typeof value.name === "string" ? value.name.trim().slice(0, MAX_NAME) : "";
  if (!name) return null;
  const idPart = slug(name);
  if (!idPart) return null;
  const criteriaInput = Array.isArray(value.criteria) ? value.criteria.slice(0, MAX_CRITERIA) : [];
  const criteria = criteriaInput
    .map(normalizeCriterion)
    .filter((criterion): criterion is ActivityFilterCriterion => criterion !== null);
  const complete = criteria.filter(criterionIsComplete);
  if (complete.length === 0) return null;
  return {
    id: `custom:${idPart}`,
    name,
    match: value.match === "any" ? "any" : "all",
    criteria: complete,
  };
}

export function normalizeActivityFilterState(value: unknown): ActivityFilterState {
  if (!isRecord(value)) return EMPTY_ACTIVITY_FILTERS;
  const saved = Array.isArray(value.saved) ? value.saved : [];
  const normalized: ActivityFilterDefinition[] = [];
  const seen = new Set<string>();
  for (const item of saved.slice(0, MAX_SAVED_FILTERS)) {
    const filter = normalizeActivityFilter(item);
    if (!filter || seen.has(filter.id)) continue;
    seen.add(filter.id);
    normalized.push(filter);
  }
  const activeId = typeof value.activeId === "string"
    && (findActivityFilter({ saved: normalized, activeId: null }, value.activeId) !== null)
    ? value.activeId
    : null;
  return { saved: normalized, activeId };
}

export function upsertActivityFilter(
  state: ActivityFilterState,
  filter: ActivityFilterDefinition,
): ActivityFilterState {
  const normalized = normalizeActivityFilter(filter);
  if (!normalized) return state;
  const saved = state.saved.filter((item) => item.id !== normalized.id);
  saved.unshift(normalized);
  return {
    saved: saved.slice(0, MAX_SAVED_FILTERS),
    activeId: normalized.id,
  };
}

export function deleteActivityFilter(
  state: ActivityFilterState,
  id: string,
): ActivityFilterState {
  const saved = state.saved.filter((item) => item.id !== id);
  if (saved.length === state.saved.length) return state;
  return { saved, activeId: state.activeId === id ? null : state.activeId };
}

export function setActiveActivityFilter(
  state: ActivityFilterState,
  id: string | null,
): ActivityFilterState {
  const activeId = findActivityFilter(state, id) ? id : null;
  if (activeId === state.activeId) return state;
  return { ...state, activeId };
}

/** Human-readable criterion summary used by the layout bar and captures. */
export function describeActivityFilter(
  filter: ActivityFilterDefinition,
  locale: string,
): string {
  return filter.criteria.map((criterion) => {
    const field = activityFilterFieldLabel(criterion.fieldId, locale);
    const operator = activityFilterOperatorLabel(criterion.operator, locale);
    const showValue = criterion.operator !== "is-empty" && criterion.operator !== "is-not-empty";
    return showValue ? `${field} ${operator} ${criterion.value}` : `${field} ${operator}`;
  }).join(filter.match === "any" ? " | " : " & ");
}
