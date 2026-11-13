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
  "not-contains",
  "equals",
  "not-equals",
  "greater-than",
  "less-than",
  "within-range",
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
  "start",
  "finish",
  "progress",
  "duration",
  "total_float",
  "is_critical",
] as const;
export type ActivityFilterFieldId = (typeof ACTIVITY_FILTER_FIELDS)[number];

/** Value domain of a filter parameter; drives the editor's typed control. */
export type ActivityFilterFieldType = "text" | "number" | "date" | "boolean" | "choice";

const FIELD_TYPES: Record<ActivityFilterFieldId, ActivityFilterFieldType> = {
  activity_id: "text",
  activity_name: "text",
  wbs: "text",
  activity_status: "choice",
  activity_type: "choice",
  start: "date",
  finish: "date",
  progress: "number",
  duration: "number",
  total_float: "number",
  is_critical: "boolean",
};

export function activityFilterFieldType(fieldId: ActivityFilterFieldId): ActivityFilterFieldType {
  return FIELD_TYPES[fieldId];
}

/**
 * Version 26 list parameters present their stored values in a picker instead
 * of a free-text box. Values stay exactly as the database stores them so a
 * saved filter keeps matching after a reload in either language.
 */
const CHOICE_VALUES: Partial<Record<ActivityFilterFieldId, readonly string[]>> = {
  activity_status: ["Not Started", "In Progress", "Completed"],
  activity_type: [
    "Task Dependent",
    "Resource Dependent",
    "Level of Effort",
    "Start Milestone",
    "Finish Milestone",
    "WBS Summary",
  ],
  is_critical: ["true", "false"],
};

export function activityFilterChoiceValues(fieldId: ActivityFilterFieldId): readonly string[] | null {
  return CHOICE_VALUES[fieldId] ?? null;
}

/** Operators offered for a parameter type, in Version 26 order. */
export function activityFilterOperatorsFor(fieldId: ActivityFilterFieldId): readonly ActivityFilterOperator[] {
  const type = activityFilterFieldType(fieldId);
  if (type === "date" || type === "number") {
    return ["equals", "not-equals", "less-than", "greater-than", "within-range", "is-empty", "is-not-empty"];
  }
  if (type === "boolean") return ["equals", "not-equals"];
  return ["contains", "not-contains", "equals", "not-equals", "is-empty", "is-not-empty"];
}

/** Authoritative project dates that relative tokens resolve against. */
export type ActivityFilterDateContext = {
  /** Current date, normally the project Data Date. */
  currentDate: string | null;
  projectStart: string | null;
  projectFinish: string | null;
};

export type ActivityFilterCriterion = {
  fieldId: ActivityFilterFieldId;
  operator: ActivityFilterOperator;
  value: string;
  /** Upper bound for the "is within range of" operator. */
  highValue?: string;
};

/**
 * Version 26 Filters dialog categories: Default, Global, Layout, User-Defined.
 * A default filter ships with the product and cannot be edited; a layout filter
 * is saved with the layout it was created in; a global filter is available to
 * every layout; a user-defined filter belongs to the signed-in user.
 */
export type ActivityFilterScope = "default" | "global" | "layout" | "user";

export const ACTIVITY_FILTER_SCOPES: readonly ActivityFilterScope[] = ["default", "global", "layout", "user"];

export type ActivityFilterDefinition = {
  /** `builtin:*` for the documented defaults, `custom:<slug>` for saved filters. */
  id: string;
  name: string;
  match: "all" | "any";
  criteria: readonly ActivityFilterCriterion[];
  builtin?: boolean;
  scope?: ActivityFilterScope;
};

export type ActivityFilterState = {
  saved: readonly ActivityFilterDefinition[];
  /** Legacy single-selection field; equals the first entry of selectedIds. */
  activeId: string | null;
  /** Version 26 Select column: every checked filter applies to the layout. */
  selectedIds?: readonly string[];
  /** "All selected filters" versus "Any selected filter". */
  combine?: "all" | "any";
  /** Matches the All Activities checkbox in the Filters dialog. */
  allActivities?: boolean;
  /** Replace the activities shown, or keep them and highlight matches. */
  applyMode?: "replace" | "highlight";
};

export const EMPTY_ACTIVITY_FILTERS: ActivityFilterState = Object.freeze({
  saved: Object.freeze([]),
  activeId: null,
  selectedIds: Object.freeze([]),
  combine: "all",
  allActivities: false,
  applyMode: "replace",
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
    scope: "default" as const,
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

/** Checked filters in display order, de-duplicated; falls back to the legacy id. */
export function getSelectedActivityFilters(state: ActivityFilterState): ActivityFilterDefinition[] {
  const ids = state.selectedIds?.length ? state.selectedIds : state.activeId ? [state.activeId] : [];
  const seen = new Set<string>();
  const filters: ActivityFilterDefinition[] = [];
  for (const id of ids) {
    if (seen.has(id)) continue;
    seen.add(id);
    const filter = findActivityFilter(state, id);
    if (filter) filters.push(filter);
  }
  return filters;
}

/** Version 26 only deletes and modifies global and layout filters. */
export function canDeleteActivityFilter(filter: ActivityFilterDefinition | null): boolean {
  if (!filter || filter.builtin) return false;
  return (filter.scope ?? "layout") !== "default";
}

export function filterScopeLabel(scope: ActivityFilterScope, locale: string): string {
  const labels: Record<ActivityFilterScope, { en: string; fa: string }> = {
    default: { en: "Default", fa: "پیش‌فرض" },
    global: { en: "Global", fa: "سراسری" },
    layout: { en: "Layout", fa: "چیدمان" },
    user: { en: "User Defined", fa: "کاربر" },
  };
  return /^fa\b/i.test(locale) ? labels[scope].fa : labels[scope].en;
}

const FIELD_LABELS: Record<ActivityFilterFieldId, { en: string; fa: string }> = {
  activity_id: { en: "Activity ID", fa: "شناسه فعالیت" },
  activity_name: { en: "Activity Name", fa: "نام فعالیت" },
  wbs: { en: "WBS", fa: "ساختار شکست" },
  activity_status: { en: "Activity Status", fa: "وضعیت فعالیت" },
  activity_type: { en: "Activity Type", fa: "نوع فعالیت" },
  start: { en: "Start", fa: "شروع" },
  finish: { en: "Finish", fa: "پایان" },
  progress: { en: "Progress %", fa: "درصد پیشرفت" },
  duration: { en: "Duration", fa: "مدت" },
  total_float: { en: "Total Float", fa: "شناوری کل" },
  is_critical: { en: "Critical", fa: "بحرانی" },
};

const OPERATOR_LABELS: Record<ActivityFilterOperator, { en: string; fa: string }> = {
  contains: { en: "contains", fa: "شامل" },
  "not-contains": { en: "does not contain", fa: "شامل نیست" },
  equals: { en: "equals", fa: "برابر" },
  "not-equals": { en: "is not equal to", fa: "برابر نیست" },
  "greater-than": { en: "is greater than", fa: "بزرگ‌تر از" },
  "less-than": { en: "is less than", fa: "کوچک‌تر از" },
  "within-range": { en: "is within range of", fa: "در بازهٔ" },
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
    case "start": return cells.start ?? cells["activity.start"] ?? null;
    case "finish": return cells.finish ?? cells["activity.finish"] ?? null;
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
  if (criterion.operator === "within-range") {
    return criterion.value.trim().length > 0 && (criterion.highValue ?? "").trim().length > 0;
  }
  return criterion.value.trim().length > 0;
}

function sameCriterion(left: ActivityFilterCriterion, right: ActivityFilterCriterion): boolean {
  const normalize = (value: string | undefined): string =>
    (value ?? "").trim().toLocaleLowerCase();
  return left.fieldId === right.fieldId
    && left.operator === right.operator
    && normalize(left.value) === normalize(right.value)
    && normalize(left.highValue) === normalize(right.highValue);
}

/**
 * Every row that satisfies `narrow` also satisfies `broad`. Only the text
 * containment family can be compared without evaluating actual rows:
 * `equals X` and `contains Y` are implied by `contains X` when Y is part of X,
 * while `not-contains X` implies `not-equals X` for the same value.
 */
function criterionImplies(narrow: ActivityFilterCriterion, broad: ActivityFilterCriterion): boolean {
  if (narrow.fieldId !== broad.fieldId) return false;
  if (sameCriterion(narrow, broad)) return true;
  const narrowValue = narrow.value.trim().toLocaleLowerCase();
  const broadValue = broad.value.trim().toLocaleLowerCase();
  if (narrowValue === "" || broadValue === "") return false;
  if (narrow.operator === "contains" && broad.operator === "contains") {
    return narrowValue.includes(broadValue);
  }
  if (narrow.operator === "not-contains" && broad.operator === "not-contains") {
    return broadValue.includes(narrowValue);
  }
  if (narrow.operator === "equals" && broad.operator === "contains") {
    return narrowValue.includes(broadValue);
  }
  if (narrow.operator === "not-contains" && broad.operator === "not-equals") {
    return narrowValue === broadValue;
  }
  return false;
}

export type ActivityFilterOptimization = {
  criteria: readonly ActivityFilterCriterion[];
  /** How many rows the review removed (duplicates, blanks or implied rows). */
  removed: number;
};

/**
 * The Version 26 Optimize review: eliminate redundant criteria without
 * changing what the filter matches. Blank rows are dropped only when a
 * complete criterion remains, exact duplicates collapse to one, and with
 * All (AND) a criterion implied by another is removed; with Any (OR) a
 * criterion that implies another is removed. Nothing is ever silently
 * widened or narrowed.
 */
export function optimizeActivityFilterCriteria(
  criteria: readonly ActivityFilterCriterion[],
  match: "all" | "any" = "all",
): ActivityFilterOptimization {
  const complete = criteria.filter(criterionIsComplete);
  if (complete.length === 0) return { criteria: [...criteria], removed: 0 };
  let removed = criteria.length - complete.length;

  const unique: ActivityFilterCriterion[] = [];
  for (const criterion of complete) {
    if (unique.some((kept) => sameCriterion(kept, criterion))) {
      removed += 1;
      continue;
    }
    unique.push(criterion);
  }

  const redundant = new Set<number>();
  for (let index = 0; index < unique.length; index += 1) {
    for (let other = 0; other < unique.length; other += 1) {
      if (index === other || redundant.has(index) || redundant.has(other)) continue;
      const implied = match === "all"
        ? criterionImplies(unique[other], unique[index])
        : criterionImplies(unique[index], unique[other]);
      if (implied) {
        redundant.add(index);
        break;
      }
    }
  }
  const kept = unique.filter((_, index) => !redundant.has(index));
  return {
    criteria: kept.length > 0 ? kept : unique.slice(0, 1),
    removed: removed + redundant.size,
  };
}

const DAY_MS = 24 * 60 * 60 * 1000;
/** Relative token grammar from the Help: CD, CS, CF plus ±n<d|w|m|y>. */
const RELATIVE_DATE = /^(CD|CS|CF)(?:([+-])(\d{1,3})([dwmy]))?$/i;

export function isDateFilterField(fieldId: ActivityFilterFieldId): boolean {
  return activityFilterFieldType(fieldId) === "date";
}

/**
 * Resolves a filter date value. A plain ISO date is accepted as-is; the
 * documented relative tokens resolve against the project Data Date (CD), the
 * earliest persisted start (CS) and the latest persisted finish (CF).
 */
export function resolveFilterDateValue(
  raw: string,
  context: ActivityFilterDateContext | undefined,
): number | null {
  const text = raw.trim();
  if (!text) return null;
  const iso = /^\d{4}-\d{2}-\d{2}/.test(text) ? Date.parse(text) : Number.NaN;
  if (Number.isFinite(iso)) return iso;
  const token = RELATIVE_DATE.exec(text);
  if (!token || !context) return null;
  const anchorRaw = token[1].toUpperCase() === "CD"
    ? context.currentDate
    : token[1].toUpperCase() === "CS" ? context.projectStart : context.projectFinish;
  if (!anchorRaw) return null;
  const anchor = Date.parse(anchorRaw);
  if (!Number.isFinite(anchor)) return null;
  if (!token[2]) return anchor;
  const amount = Number(token[3]) * (token[2] === "-" ? -1 : 1);
  const unit = token[4].toLowerCase();
  const days = unit === "d" ? amount
    : unit === "w" ? amount * 7
      : unit === "m" ? amount * 30
        : amount * 365;
  return anchor + days * DAY_MS;
}

/** Same calendar day in UTC, so date equality is not a millisecond compare. */
function sameUtcDay(left: number, right: number): boolean {
  return Math.floor(left / DAY_MS) === Math.floor(right / DAY_MS);
}

/** Derives CS/CF from the persisted rows; CD comes from the Data Date. */
export function createActivityFilterDateContext(
  activities: readonly WorkspaceActivityRow[],
  currentDate: string | null,
): ActivityFilterDateContext {
  let start = Number.POSITIVE_INFINITY;
  let finish = Number.NEGATIVE_INFINITY;
  for (const activity of activities) {
    const rawStart = activity.gantt?.start ?? (typeof activity.cells?.start === "string" ? activity.cells.start : null);
    const rawFinish = activity.gantt?.finish ?? (typeof activity.cells?.finish === "string" ? activity.cells.finish : null);
    const startMs = typeof rawStart === "string" ? Date.parse(rawStart) : Number.NaN;
    const finishMs = typeof rawFinish === "string" ? Date.parse(rawFinish) : Number.NaN;
    if (Number.isFinite(startMs)) start = Math.min(start, startMs);
    if (Number.isFinite(finishMs)) finish = Math.max(finish, finishMs);
  }
  const iso = (value: number): string | null => Number.isFinite(value) ? new Date(value).toISOString().slice(0, 10) : null;
  return { currentDate, projectStart: iso(start), projectFinish: iso(finish) };
}

export type ActivityFilterCriterionValidation = {
  ok: boolean;
  /** Stable machine-readable code for the editor and assertions. */
  code: "OK" | "FILTER_VALUE_REQUIRED" | "FILTER_RANGE_INCOMPLETE" | "FILTER_VALUE_INVALID_DATE" | "FILTER_RANGE_INVALID";
};

export function validateActivityFilterCriterion(
  criterion: ActivityFilterCriterion,
  context?: ActivityFilterDateContext,
): ActivityFilterCriterionValidation {
  if (criterion.operator === "is-empty" || criterion.operator === "is-not-empty") return { ok: true, code: "OK" };
  if (!criterion.value.trim()) return { ok: false, code: "FILTER_VALUE_REQUIRED" };
  if (criterion.operator === "within-range" && !(criterion.highValue ?? "").trim()) {
    return { ok: false, code: "FILTER_RANGE_INCOMPLETE" };
  }
  if (isDateFilterField(criterion.fieldId)) {
    const low = resolveFilterDateValue(criterion.value, context);
    if (low === null) return { ok: false, code: "FILTER_VALUE_INVALID_DATE" };
    if (criterion.operator === "within-range") {
      const high = resolveFilterDateValue(criterion.highValue ?? "", context);
      if (high === null) return { ok: false, code: "FILTER_VALUE_INVALID_DATE" };
      if (high < low) return { ok: false, code: "FILTER_RANGE_INVALID" };
    }
  }
  return { ok: true, code: "OK" };
}

/** Matches one criterion; incomplete criteria never match anything. */
export function activityMatchesCriterion(
  activity: WorkspaceActivityRow,
  criterion: ActivityFilterCriterion,
  wbsLabels?: ReadonlyMap<string, string>,
  dateContext?: ActivityFilterDateContext,
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

  if (isDateFilterField(criterion.fieldId)) {
    const actual = resolveFilterDateValue(String(value), dateContext);
    const low = resolveFilterDateValue(criterion.value, dateContext);
    if (actual === null || low === null) return false;
    const high = criterion.operator === "within-range"
      ? resolveFilterDateValue(criterion.highValue ?? "", dateContext)
      : low;
    if (high === null) return false;
    switch (criterion.operator) {
      case "equals": return sameUtcDay(actual, low);
      case "not-equals": return !sameUtcDay(actual, low);
      case "greater-than": return actual > low;
      case "less-than": return actual < low;
      case "within-range": return actual >= low && actual <= high;
      default: return false;
    }
  }

  const expectedText = criterion.value.trim();
  if (criterion.operator === "contains" || criterion.operator === "not-contains") {
    const contains = String(value).toLocaleLowerCase().includes(expectedText.toLocaleLowerCase());
    return criterion.operator === "not-contains" ? !contains : contains;
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
  if (criterion.operator === "within-range") {
    const highNumber = numericValue(criterion.highValue ?? "");
    return highNumber !== null && actualNumber >= expectedNumber && actualNumber <= highNumber;
  }
  return criterion.operator === "greater-than"
    ? actualNumber > expectedNumber
    : actualNumber < expectedNumber;
}

export function activityMatchesFilter(
  activity: WorkspaceActivityRow,
  filter: ActivityFilterDefinition | null,
  wbsLabels?: ReadonlyMap<string, string>,
  dateContext?: ActivityFilterDateContext,
): boolean {
  if (!filter) return true;
  const criteria = filter.criteria.filter(criterionIsComplete);
  if (criteria.length === 0) return true;
  return filter.match === "any"
    ? criteria.some((criterion) => activityMatchesCriterion(activity, criterion, wbsLabels, dateContext))
    : criteria.every((criterion) => activityMatchesCriterion(activity, criterion, wbsLabels, dateContext));
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
  dateContext?: ActivityFilterDateContext,
): readonly WorkspaceActivityRow[] {
  if (!filter) return activities;
  const wbsLabels = buildWbsLabels(wbsNodes);
  return activities.filter((activity) => activityMatchesFilter(activity, filter, wbsLabels, dateContext));
}

export type ActivityFilterApplication = {
  /** Rows that stay visible: all rows in highlight mode. */
  activities: readonly WorkspaceActivityRow[];
  /** Every row that satisfies the checked filters. */
  matchedIds: ReadonlySet<string>;
  highlight: boolean;
  filters: readonly ActivityFilterDefinition[];
};

/**
 * Applies the version 26 selection model: All Activities bypasses filtering,
 * "All selected filters" requires every checked filter to match, "Any selected
 * filter" requires one, and highlight mode keeps the rows on screen.
 */
export function applyActivityFilterState(
  activities: readonly WorkspaceActivityRow[],
  state: ActivityFilterState,
  wbsNodes: readonly WbsLabelNode[] = [],
  dateContext?: ActivityFilterDateContext,
): ActivityFilterApplication {
  const filters = getSelectedActivityFilters(state);
  const allIds = new Set(activities.map((activity) => activity.id));
  if (state.allActivities || filters.length === 0) {
    return { activities, matchedIds: allIds, highlight: false, filters: [] };
  }
  const wbsLabels = buildWbsLabels(wbsNodes);
  const combine = state.combine === "any" ? "any" : "all";
  const matchedIds = new Set<string>();
  for (const activity of activities) {
    const matches = combine === "any"
      ? filters.some((filter) => activityMatchesFilter(activity, filter, wbsLabels, dateContext))
      : filters.every((filter) => activityMatchesFilter(activity, filter, wbsLabels, dateContext));
    if (matches) matchedIds.add(activity.id);
  }
  const highlight = state.applyMode === "highlight";
  return {
    activities: highlight ? activities : activities.filter((activity) => matchedIds.has(activity.id)),
    matchedIds,
    highlight,
    filters,
  };
}

export type ActivityFilterPreview = {
  total: number;
  matched: number;
  valid: boolean;
  code: ActivityFilterCriterionValidation["code"];
};

/**
 * Validates a draft filter and counts the activities it would match. The
 * editor shows this before Apply, so an incomplete or inverted range is visible
 * instead of silently matching nothing.
 */
export function previewActivityFilter(
  activities: readonly WorkspaceActivityRow[],
  filter: ActivityFilterDefinition,
  wbsNodes: readonly WbsLabelNode[] = [],
  dateContext?: ActivityFilterDateContext,
): ActivityFilterPreview {
  const invalid = filter.criteria
    .map((criterion) => validateActivityFilterCriterion(criterion, dateContext))
    .find((validation) => !validation.ok);
  if (invalid) return { total: activities.length, matched: 0, valid: false, code: invalid.code };
  const wbsLabels = buildWbsLabels(wbsNodes);
  const matched = activities.filter((activity) => activityMatchesFilter(activity, filter, wbsLabels, dateContext)).length;
  return { total: activities.length, matched, valid: true, code: "OK" };
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
  const rawHigh = value.highValue;
  if (rawHigh !== null && rawHigh !== undefined && typeof rawHigh !== "string") return null;
  const criterion: ActivityFilterCriterion = {
    fieldId: fieldId as ActivityFilterFieldId,
    operator: operator as ActivityFilterOperator,
    value: String(rawValue ?? "").slice(0, MAX_VALUE),
  };
  if (operator === "within-range") criterion.highValue = String(rawHigh ?? "").slice(0, MAX_VALUE);
  return criterion;
}

export function normalizeActivityFilter(value: unknown): ActivityFilterDefinition | null {
  if (!isRecord(value)) return null;
  const name = typeof value.name === "string" ? value.name.trim().slice(0, MAX_NAME) : "";
  if (!name) return null;
  const explicitId = typeof value.id === "string" && /^custom:[^\s:]{1,80}$/u.test(value.id) ? value.id : null;
  const idPart = explicitId ? explicitId.slice("custom:".length) : slug(name);
  if (!idPart) return null;
  const criteriaInput = Array.isArray(value.criteria) ? value.criteria.slice(0, MAX_CRITERIA) : [];
  const criteria = criteriaInput
    .map(normalizeCriterion)
    .filter((criterion): criterion is ActivityFilterCriterion => criterion !== null);
  const complete = criteria.filter(criterionIsComplete);
  if (complete.length === 0) return null;
  const scope: ActivityFilterScope = value.scope === "global" || value.scope === "user" ? value.scope : "layout";
  return {
    id: explicitId ?? `custom:${idPart}`,
    name,
    match: value.match === "any" ? "any" : "all",
    criteria: complete,
    scope,
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
  const known = (id: unknown): id is string => typeof id === "string"
    && findActivityFilter({ saved: normalized, activeId: null }, id) !== null;
  const legacyActive = known(value.activeId) ? value.activeId : null;
  const selectedRaw = Array.isArray(value.selectedIds) ? value.selectedIds : legacyActive ? [legacyActive] : [];
  const selectedIds: string[] = [];
  const selectedSeen = new Set<string>();
  for (const id of selectedRaw) {
    if (!known(id) || selectedSeen.has(id)) continue;
    selectedSeen.add(id);
    selectedIds.push(id);
  }
  return {
    saved: normalized,
    activeId: selectedIds[0] ?? legacyActive,
    selectedIds,
    combine: value.combine === "any" ? "any" : "all",
    allActivities: value.allActivities === true,
    applyMode: value.applyMode === "highlight" ? "highlight" : "replace",
  };
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
    ...state,
    saved: saved.slice(0, MAX_SAVED_FILTERS),
    activeId: normalized.id,
    selectedIds: [normalized.id],
    allActivities: false,
  };
}

export function deleteActivityFilter(
  state: ActivityFilterState,
  id: string,
): ActivityFilterState {
  const target = findActivityFilter(state, id);
  // Version 26 only deletes global and layout filters.
  if (!canDeleteActivityFilter(target)) return state;
  const saved = state.saved.filter((item) => item.id !== id);
  if (saved.length === state.saved.length) return state;
  const selectedIds = (state.selectedIds ?? []).filter((item) => item !== id);
  return {
    ...state,
    saved,
    selectedIds,
    activeId: state.activeId === id ? selectedIds[0] ?? null : state.activeId,
  };
}

export function setActiveActivityFilter(
  state: ActivityFilterState,
  id: string | null,
): ActivityFilterState {
  const activeId = findActivityFilter(state, id) ? id : null;
  return {
    ...state,
    activeId,
    selectedIds: activeId ? [activeId] : [],
    allActivities: false,
  };
}

export function selectActivityFilter(
  state: ActivityFilterState,
  id: string,
  selected: boolean,
): ActivityFilterState {
  if (!findActivityFilter(state, id)) return state;
  const current = state.selectedIds ?? (state.activeId ? [state.activeId] : []);
  const next = selected
    ? current.includes(id) ? current : [...current, id]
    : current.filter((item) => item !== id);
  return { ...state, selectedIds: next, activeId: next[0] ?? null };
}

export function setActivityFilterCombine(
  state: ActivityFilterState,
  combine: "all" | "any",
): ActivityFilterState {
  return state.combine === combine ? state : { ...state, combine };
}

export function setActivityFilterAllActivities(
  state: ActivityFilterState,
  allActivities: boolean,
): ActivityFilterState {
  return state.allActivities === allActivities ? state : { ...state, allActivities };
}

export function setActivityFilterApplyMode(
  state: ActivityFilterState,
  applyMode: "replace" | "highlight",
): ActivityFilterState {
  return state.applyMode === applyMode ? state : { ...state, applyMode };
}

function uniqueFilterId(state: ActivityFilterState, base: string): string {
  const taken = new Set([
    ...state.saved.map((filter) => filter.id),
    ...getBuiltinActivityFilters().map((filter) => filter.id),
  ]);
  let candidate = base;
  let suffix = 2;
  while (taken.has(candidate)) candidate = `${base}-${suffix++}`;
  return candidate;
}

/** Makes a layout filter global; other categories are unchanged. */
export function makeGlobalActivityFilter(
  state: ActivityFilterState,
  id: string,
): ActivityFilterState {
  const target = state.saved.find((filter) => filter.id === id);
  if (!target || target.scope !== "layout") return state;
  return {
    ...state,
    saved: state.saved.map((filter) => (filter.id === id ? { ...filter, scope: "global" as const } : filter)),
  };
}

/** Copy as Layout: a default or global filter becomes a layout filter. */
export function copyActivityFilterAsLayout(
  state: ActivityFilterState,
  id: string,
): ActivityFilterState {
  const source = findActivityFilter(state, id);
  if (!source) return state;
  const copy: ActivityFilterDefinition = {
    ...source,
    id: uniqueFilterId(state, `custom:${slug(source.name)}-layout`),
    name: source.name.slice(0, MAX_NAME),
    builtin: false,
    scope: "layout",
  };
  return { ...state, saved: [copy, ...state.saved].slice(0, MAX_SAVED_FILTERS) };
}

/** Paste: store a copied filter in the given category with a unique id. */
export function pasteActivityFilter(
  state: ActivityFilterState,
  source: ActivityFilterDefinition,
  scope: ActivityFilterScope = "layout",
): ActivityFilterState {
  if (scope === "default") return state;
  const copy: ActivityFilterDefinition = {
    ...source,
    id: uniqueFilterId(state, `custom:${slug(source.name)}`),
    builtin: false,
    scope,
  };
  return { ...state, saved: [copy, ...state.saved].slice(0, MAX_SAVED_FILTERS) };
}

/**
 * Duplicate keeps the saved filter intact and stores a second copy in the same
 * category, so a user can vary one criterion without retyping the filter.
 * Built-in filters are read-only and are copied with Copy as Layout instead.
 */
export function duplicateActivityFilter(
  state: ActivityFilterState,
  id: string,
): ActivityFilterState {
  const source = findActivityFilter(state, id);
  if (!source || source.builtin) return state;
  const scope: ActivityFilterScope =
    source.scope === "global" || source.scope === "user" ? source.scope : "layout";
  const baseName = source.name.slice(0, Math.max(0, MAX_NAME - " (copy)".length));
  const name = `${baseName} (copy)`.slice(0, MAX_NAME);
  const copy: ActivityFilterDefinition = {
    ...source,
    id: uniqueFilterId(state, `custom:${slug(name)}`),
    name,
    builtin: false,
    scope,
  };
  return { ...state, saved: [copy, ...state.saved].slice(0, MAX_SAVED_FILTERS) };
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
    if (!showValue) return `${field} ${operator}`;
    if (criterion.operator === "within-range") {
      const separator = /^fa\b/i.test(locale) ? " تا " : " and ";
      return `${field} ${operator} ${criterion.value}${separator}${criterion.highValue ?? ""}`;
    }
    return `${field} ${operator} ${criterion.value}`;
  }).join(filter.match === "any" ? " | " : " & ");
}
