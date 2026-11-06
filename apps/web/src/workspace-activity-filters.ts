import type { WorkspaceActivityRow, WorkspaceCellValue } from "./workspace-model.js";
import type {
  ActivityFilterCriterion,
  ActivityFilterOperator,
  SavedActivityFilter,
} from "./p6-activity-filter-api.js";

export type ActivityFilterField = {
  field_id: string;
  display_name: string;
  data_type: string;
  filterable?: boolean | null;
  unit?: string | null;
};

export type ActivityFilterDraft = {
  filter_id: string;
  name: string;
  category: "layout" | "user-defined";
  expected_revision: number;
  match_mode: "all" | "any";
  criteria: ActivityFilterCriterion[];
};

const TEXT_OPERATORS: ActivityFilterOperator[] = [
  "equals", "not-equals", "contains", "not-contains", "starts-with", "ends-with", "is-empty", "is-not-empty",
];
const ORDER_OPERATORS: ActivityFilterOperator[] = [
  "equals", "not-equals", "greater-than", "greater-than-or-equal",
  "less-than", "less-than-or-equal", "between", "not-between", "is-empty", "is-not-empty",
];
const BOOLEAN_OPERATORS: ActivityFilterOperator[] = ["equals", "not-equals", "is-empty", "is-not-empty"];

export function operatorsForActivityField(dataType: string): readonly ActivityFilterOperator[] {
  if (dataType === "string") return TEXT_OPERATORS;
  if (dataType === "boolean") return BOOLEAN_OPERATORS;
  if (["date", "datetime", "integer", "double", "decimal", "percentage", "cost", "duration", "unit"].includes(dataType)) {
    return ORDER_OPERATORS;
  }
  if (dataType === "enum") {
    return ["equals", "not-equals", "contains", "starts-with", "ends-with", "is-empty", "is-not-empty"];
  }
  return [];
}

export function createActivityFilterDraft(
  fields: readonly ActivityFilterField[],
  existing?: SavedActivityFilter,
): ActivityFilterDraft {
  const firstField = fields.find((field) => field.filterable !== false && operatorsForActivityField(field.data_type).length > 0);
  return {
    filter_id: existing?.filter_id ?? "activity.filter." + slugify(firstField?.field_id ?? "new-filter"),
    name: existing?.name ?? "",
    category: existing?.category ?? "user-defined",
    expected_revision: existing?.revision ?? 0,
    match_mode: existing?.match_mode ?? "all",
    criteria: existing
      ? existing.criteria.map((item) => ({ ...item }))
      : [{
          connector: "where",
          field_id: firstField?.field_id ?? "",
          operator: firstField ? operatorsForActivityField(firstField.data_type)[0] : "equals",
          value: "",
          high_value: null,
        }],
  };
}

export function validateActivityFilterDraft(
  draft: ActivityFilterDraft,
  fields: readonly ActivityFilterField[],
): string | null {
  if (!draft.name.trim()) return "FILTER_NAME_REQUIRED";
  if (draft.name.trim().length > 80) return "FILTER_NAME_TOO_LONG";
  if (!draft.filter_id.startsWith("activity.filter.")) return "INVALID_FILTER_ID";
  if (!draft.criteria.length || draft.criteria.length > 100) return "FILTER_CRITERIA_REQUIRED";
  if (draft.criteria[0].connector !== "where") return "FILTER_FIRST_ROW_MUST_BE_WHERE";
  const byId = new Map(fields.map((field) => [field.field_id, field]));
  for (let index = 0; index < draft.criteria.length; index += 1) {
    const item = draft.criteria[index];
    const field = byId.get(item.field_id);
    if (!field || field.filterable === false) return "FILTER_FIELD_NOT_AVAILABLE";
    if (!operatorsForActivityField(field.data_type).includes(item.operator)) return "FILTER_OPERATOR_NOT_SUPPORTED";
    if (index > 0 && item.connector === "where") return "FILTER_CONNECTOR_INVALID";
    if (item.operator === "is-empty" || item.operator === "is-not-empty") continue;
    if (item.value === null || String(item.value).trim() === "") return "FILTER_VALUE_REQUIRED";
    if (item.operator === "between" || item.operator === "not-between") {
      if (item.high_value === null || String(item.high_value).trim() === "") return "FILTER_HIGH_VALUE_REQUIRED";
    } else if (item.high_value !== undefined && item.high_value !== null && item.high_value !== "") {
      return "FILTER_HIGH_VALUE_NOT_ALLOWED";
    }
    if (["integer", "double", "decimal", "percentage", "cost"].includes(field.data_type)) {
      if (!Number.isFinite(Number(item.value))) return "FILTER_NUMERIC_VALUE_INVALID";
      if ((item.operator === "between" || item.operator === "not-between") && !Number.isFinite(Number(item.high_value))) {
        return "FILTER_NUMERIC_HIGH_VALUE_INVALID";
      }
    }
    if (field.data_type === "date" && !isDateOrRelativeReference(String(item.value))) return "FILTER_DATE_VALUE_INVALID";
  }
  return null;
}

export function matchesSavedActivityFilter(
  activity: WorkspaceActivityRow,
  filter: SavedActivityFilter,
): boolean {
  if (!filter.criteria.length) return true;
  const values = filter.criteria.map((criterion) => evaluateCriterion(activity, criterion));
  let completedGroup = false;
  let currentGroup = values[0] ?? true;
  for (let index = 1; index < values.length; index += 1) {
    const connector = filter.criteria[index].connector;
    if (connector === "or") {
      completedGroup = completedGroup || currentGroup;
      currentGroup = values[index];
    } else {
      currentGroup = currentGroup && values[index];
    }
  }
  return completedGroup || currentGroup;
}

export function matchingActivityIds(
  activities: readonly WorkspaceActivityRow[],
  filters: readonly SavedActivityFilter[],
  combination: "all" | "any",
): ReadonlySet<string> {
  const ids = new Set<string>();
  if (!filters.length) return ids;
  for (const activity of activities) {
    const results = filters.map((filter) => matchesSavedActivityFilter(activity, filter));
    const matches = combination === "all" ? results.every(Boolean) : results.some(Boolean);
    if (matches) ids.add(activity.id);
  }
  return ids;
}

function evaluateCriterion(activity: WorkspaceActivityRow, criterion: ActivityFilterCriterion): boolean {
  const actual = activityFieldValue(activity, criterion.field_id);
  const missing = actual === null || actual === undefined || actual === "";
  if (criterion.operator === "is-empty") return missing;
  if (criterion.operator === "is-not-empty") return !missing;
  if (missing) return false;

  const compare = (left: WorkspaceCellValue, right: string | number | boolean | null): number | null => {
    if (left === null || right === null) return null;
    if (typeof left === "boolean" || typeof right === "boolean") {
      if (typeof left !== "boolean" || typeof right !== "boolean") return null;
      return left === right ? 0 : left ? 1 : -1;
    }
    if (typeof left === "number" || typeof right === "number") {
      const a = Number(left);
      const b = Number(right);
      if (!Number.isFinite(a) || !Number.isFinite(b)) return null;
      return a === b ? 0 : a < b ? -1 : 1;
    }
    const leftDate = Date.parse(String(left));
    const rightDate = Date.parse(String(right));
    if (Number.isFinite(leftDate) && Number.isFinite(rightDate) && isDateValue(String(right))) {
      return leftDate === rightDate ? 0 : leftDate < rightDate ? -1 : 1;
    }
    const a = String(left).toLocaleLowerCase();
    const b = String(right).toLocaleLowerCase();
    return a === b ? 0 : a < b ? -1 : 1;
  };

  const expected = criterion.value;
  const actualText = String(actual).toLocaleLowerCase();
  const expectedText = String(expected ?? "").toLocaleLowerCase();
  if (criterion.operator === "contains") return actualText.includes(expectedText);
  if (criterion.operator === "not-contains") return !actualText.includes(expectedText);
  if (criterion.operator === "starts-with") return actualText.startsWith(expectedText);
  if (criterion.operator === "ends-with") return actualText.endsWith(expectedText);

  const low = compare(actual, expected);
  if (low === null) return false;
  switch (criterion.operator) {
    case "equals": return low === 0;
    case "not-equals": return low !== 0;
    case "greater-than": return low > 0;
    case "greater-than-or-equal": return low >= 0;
    case "less-than": return low < 0;
    case "less-than-or-equal": return low <= 0;
    case "between":
    case "not-between": {
      const high = compare(actual, criterion.high_value ?? null);
      if (high === null) return false;
      const inside = low >= 0 && high <= 0;
      return criterion.operator === "between" ? inside : !inside;
    }
    default: return false;
  }
}

function activityFieldValue(activity: WorkspaceActivityRow, fieldId: string): WorkspaceCellValue {
  switch (fieldId) {
    case "activity.activity_id": return activity.id;
    case "activity.activity_name": return activity.name;
    case "activity.wbs": return activity.wbsId;
    case "activity.activity_code": return activity.code;
    default:
      return activity.cells?.[fieldId] ?? activity.cells?.[fieldId.replace(/^activity\\./u, "")] ?? null;
  }
}

function isDateValue(value: string): boolean {
  return /^\\d{4}-\\d{2}-\\d{2}(?:T.*)?$/u.test(value);
}

function isDateOrRelativeReference(value: string): boolean {
  return isDateValue(value) || /^(?:CD|CF)(?:[+-]\\d+(?:d|w|m|y))?$/iu.test(value.trim());
}

function slugify(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/gu, "-").replace(/^-|-$/gu, "").slice(0, 60) || "new-filter";
}
