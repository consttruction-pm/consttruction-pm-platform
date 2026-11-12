import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import { loadCalendarCatalogue, type WorkspaceCalendarRecord } from "./workspace-calendars.js";

export const ASSIGNMENT_READ_API_VERSION = "p6-resource-read-api.v1";
export const ASSIGNMENT_WRITE_API_VERSION = "p6-resource-write-api.v1";

export type AssignmentRecord = {
  assignmentId: string;
  activityId: string;
  resourceId: string;
  roleId: string | null;
  units: string | null;
  actualUnits: string | null;
  remainingUnits: string | null;
  plannedCost: string | null;
  actualCost: string | null;
  remainingCost: string | null;
  unit: string | null;
  currency: string | null;
  calendarId: string | null;
  calendarVersion: string | null;
  note: string | null;
  isDriving: boolean | null;
  unitsPerTime: string | null;
  unitsPerTimePeriod: string | null;
  hoursPerUnitsTimePeriod: string | null;
};

export type AssignmentPeriod = {
  assignmentId: string;
  activityId: string;
  resourceId: string;
  periodStart: string;
  units: string;
  cost: string;
};

export type AssignmentPeriodInput = {
  assignmentId: string;
  activityId: string;
  resourceId: string;
  periodStart: string;
  units: string;
  cost: string;
};

export type AssignmentActivityOption = {
  id: string;
  code: string;
  name: string;
};

export type AssignmentInput = {
  assignmentId: string;
  activityId: string;
  resourceId: string;
  roleId: string | null;
  units: string | null;
  unit: string | null;
  plannedCost: string | null;
  currency: string | null;
  calendarId: string | null;
  calendarVersion: string | null;
  note: string | null;
};

export type AssignmentColumnKey =
  | "assignment"
  | "activity"
  | "resource"
  | "role"
  | "units"
  | "actualUnits"
  | "remainingUnits"
  | "unit"
  | "unitsPerTime"
  | "plannedCost"
  | "actualCost"
  | "remainingCost"
  | "currency"
  | "calendar"
  | "driving"
  | "note";

export type AssignmentGroupBy = "none" | "resource" | "activity" | "role";

export type AssignmentSort = { column: AssignmentColumnKey; dir: "asc" | "desc" } | null;

export type AssignmentFilters = {
  query: string;
  resourceId: string;
  activityId: string;
};

export type AssignmentViewPrefs = {
  groupBy: AssignmentGroupBy;
  sort: AssignmentSort;
  columns: AssignmentColumnKey[];
};

export type AssignmentGroupTotals = {
  units: string | null;
  plannedCost: string | null;
  actualCost: string | null;
};

export type AssignmentGroup = {
  key: string;
  label: string;
  rows: AssignmentRecord[];
  totals: AssignmentGroupTotals;
};

export type AssignmentProfilePoint = {
  periodStart: string;
  units: string;
  cost: string;
};

export type AssignmentProfile = {
  points: AssignmentProfilePoint[];
  totalUnits: string | null;
  totalCost: string | null;
  maxUnits: string | null;
};

export type AssignmentPageOptions = {
  transport: ApiTransport;
  context: ProjectContext;
  locale: string;
  activities: readonly AssignmentActivityOption[];
  canWrite: boolean;
};

export const ASSIGNMENT_STORAGE_KEY = "cubi.assignments.view.v1";

type ColumnDefinition = {
  key: AssignmentColumnKey;
  en: string;
  fa: string;
  numeric: boolean;
};

export const ASSIGNMENT_COLUMNS: readonly ColumnDefinition[] = [
  { key: "assignment", en: "Assignment ID", fa: "شناسه تخصیص", numeric: false },
  { key: "activity", en: "Activity", fa: "فعالیت", numeric: false },
  { key: "resource", en: "Resource", fa: "منبع", numeric: false },
  { key: "role", en: "Role", fa: "نقش", numeric: false },
  { key: "units", en: "Budgeted Units", fa: "واحد بودجه", numeric: true },
  { key: "actualUnits", en: "Actual Units", fa: "واحد واقعی", numeric: true },
  { key: "remainingUnits", en: "Remaining Units", fa: "واحد باقی‌مانده", numeric: true },
  { key: "unit", en: "Unit", fa: "واحد", numeric: false },
  { key: "unitsPerTime", en: "Units / Time", fa: "واحد / زمان", numeric: true },
  { key: "plannedCost", en: "Planned Cost", fa: "هزینه برنامه‌ای", numeric: true },
  { key: "actualCost", en: "Actual Cost", fa: "هزینه واقعی", numeric: true },
  { key: "remainingCost", en: "Remaining Cost", fa: "هزینه باقی‌مانده", numeric: true },
  { key: "currency", en: "Currency", fa: "ارز", numeric: false },
  { key: "calendar", en: "Calendar", fa: "تقویم", numeric: false },
  { key: "driving", en: "Driving", fa: "تعیین‌کننده", numeric: false },
  { key: "note", en: "Note", fa: "یادداشت", numeric: false },
];

const NUMERIC_COLUMNS = new Set<AssignmentColumnKey>(
  ASSIGNMENT_COLUMNS.filter((column) => column.numeric).map((column) => column.key),
);

const DEFAULT_COLUMNS: AssignmentColumnKey[] = [
  "assignment", "activity", "resource", "role", "units", "unit", "plannedCost", "currency",
];

const GROUP_BY_VALUES: readonly AssignmentGroupBy[] = ["none", "resource", "activity", "role"];

function text(locale: string, en: string, fa: string): string {
  return locale.split("-")[0] === "fa" ? fa : en;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function localError(code: string): ApiResult<never> {
  return {
    ok: false,
    error: { code, retryable: false, message_key: "error.request.invalid", available_actions: [] },
  };
}

function assignmentPath(context: ProjectContext, assignmentId?: string): string {
  const base = `/api/projects/${encodeURIComponent(context.project_id)}/p6/resource-assignments`;
  return assignmentId ? `${base}/${encodeURIComponent(assignmentId)}` : base;
}

function periodPath(context: ProjectContext): string {
  return `/api/projects/${encodeURIComponent(context.project_id)}/p6/resource-assignment-periods`;
}

function optionalText(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== "string") throw new Error("INVALID_ASSIGNMENT_RECORD");
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function decimalText(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== "string" && typeof value !== "number") {
    throw new Error("INVALID_ASSIGNMENT_RECORD");
  }
  const trimmed = String(value).trim();
  if (!trimmed) return null;
  if (!/^-?\d+(\.\d+)?$/.test(trimmed)) throw new Error("INVALID_ASSIGNMENT_RECORD");
  return trimmed;
}

export function parseAssignment(value: unknown): AssignmentRecord {
  if (!isRecord(value)) throw new Error("INVALID_ASSIGNMENT_RECORD");
  if (value.contract_version !== ASSIGNMENT_READ_API_VERSION && value.contract_version !== ASSIGNMENT_WRITE_API_VERSION) {
    throw new Error("INVALID_ASSIGNMENT_RESPONSE");
  }
  if (value.kind !== "resource_assignment") {
    throw new Error("INVALID_ASSIGNMENT_RESPONSE");
  }
  const payload = value.assignment;
  if (!isRecord(payload)) throw new Error("INVALID_ASSIGNMENT_RESPONSE");
  const { assignment_id, activity_id, resource_id, is_driving } = payload;
  if (
    typeof assignment_id !== "string" || !assignment_id.trim() ||
    typeof activity_id !== "string" || !activity_id.trim() ||
    typeof resource_id !== "string" || !resource_id.trim()
  ) {
    throw new Error("INVALID_ASSIGNMENT_RECORD");
  }
  if (is_driving !== undefined && is_driving !== null && typeof is_driving !== "boolean") {
    throw new Error("INVALID_ASSIGNMENT_RECORD");
  }
  return {
    assignmentId: assignment_id,
    activityId: activity_id,
    resourceId: resource_id,
    roleId: optionalText(payload.role_id),
    units: decimalText(payload.units),
    actualUnits: decimalText(payload.actual_units),
    remainingUnits: decimalText(payload.remaining_units),
    plannedCost: decimalText(payload.planned_cost),
    actualCost: decimalText(payload.actual_cost),
    remainingCost: decimalText(payload.remaining_cost),
    unit: optionalText(payload.unit),
    currency: optionalText(payload.currency),
    calendarId: optionalText(payload.calendar_id),
    calendarVersion: optionalText(payload.calendar_version),
    note: optionalText(payload.note),
    isDriving: typeof is_driving === "boolean" ? is_driving : null,
    unitsPerTime: decimalText(payload.units_per_time),
    unitsPerTimePeriod: optionalText(payload.units_per_time_period),
    hoursPerUnitsTimePeriod: decimalText(payload.hours_per_units_time_period),
  };
}

export async function loadAssignments(
  transport: ApiTransport,
  context: ProjectContext,
): Promise<ApiResult<readonly AssignmentRecord[]>> {
  const result = await transport.get<unknown>(assignmentPath(context), context);
  if (!result.ok) return result;
  const payload = result.data;
  if (!isRecord(payload) || payload.contract_version !== ASSIGNMENT_READ_API_VERSION || !Array.isArray(payload.assignments)) {
    return localError("INVALID_ASSIGNMENT_LIST");
  }
  try {
    return { ok: true, data: payload.assignments.map((item) => parseAssignment(item)) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ASSIGNMENT_LIST");
  }
}

export function parseAssignmentPeriod(value: unknown): AssignmentPeriod {
  if (!isRecord(value)) throw new Error("INVALID_ASSIGNMENT_PERIOD_RECORD");
  if (value.contract_version !== ASSIGNMENT_READ_API_VERSION && value.contract_version !== ASSIGNMENT_WRITE_API_VERSION) {
    throw new Error("INVALID_ASSIGNMENT_PERIOD_RESPONSE");
  }
  if (value.kind !== "resource_assignment_period") {
    throw new Error("INVALID_ASSIGNMENT_PERIOD_RESPONSE");
  }
  const payload = value.period;
  if (!isRecord(payload)) throw new Error("INVALID_ASSIGNMENT_PERIOD_RESPONSE");
  const { assignment_id, activity_id, resource_id, period_start } = payload;
  if (
    typeof assignment_id !== "string" || !assignment_id.trim() ||
    typeof activity_id !== "string" || !activity_id.trim() ||
    typeof resource_id !== "string" || !resource_id.trim() ||
    typeof period_start !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(period_start)
  ) {
    throw new Error("INVALID_ASSIGNMENT_PERIOD_RECORD");
  }
  let units: string | null;
  let cost: string | null;
  try {
    units = decimalText(payload.units);
    cost = decimalText(payload.cost);
  } catch {
    throw new Error("INVALID_ASSIGNMENT_PERIOD_RECORD");
  }
  if (units === null || cost === null) throw new Error("INVALID_ASSIGNMENT_PERIOD_RECORD");
  return {
    assignmentId: assignment_id,
    activityId: activity_id,
    resourceId: resource_id,
    periodStart: period_start,
    units,
    cost,
  };
}

export async function loadAssignmentPeriods(
  transport: ApiTransport,
  context: ProjectContext,
): Promise<ApiResult<readonly AssignmentPeriod[]>> {
  const result = await transport.get<unknown>(periodPath(context), context);
  if (!result.ok) return result;
  const payload = result.data;
  if (!isRecord(payload) || payload.contract_version !== ASSIGNMENT_READ_API_VERSION || !Array.isArray(payload.periods)) {
    return localError("INVALID_ASSIGNMENT_PERIOD_LIST");
  }
  try {
    return { ok: true, data: payload.periods.map((item) => parseAssignmentPeriod(item)) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ASSIGNMENT_PERIOD_LIST");
  }
}

function normalizedDecimal(raw: string): string | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  if (!/^-?\d+(\.\d+)?$/.test(trimmed)) throw new Error("INVALID_ASSIGNMENT_NUMBER");
  return trimmed;
}

export function buildAssignmentPayload(input: AssignmentInput): Record<string, unknown> {
  if (!input.assignmentId.trim() || !input.activityId.trim() || !input.resourceId.trim()) {
    throw new Error("ASSIGNMENT_FIELDS_REQUIRED");
  }
  const calendarId = input.calendarId?.trim() ? input.calendarId.trim() : null;
  const calendarVersion = input.calendarVersion?.trim() ? input.calendarVersion.trim() : null;
  if ((calendarId === null) !== (calendarVersion === null)) {
    throw new Error("INCOMPLETE_CALENDAR_REFERENCE");
  }
  return {
    contract_version: ASSIGNMENT_WRITE_API_VERSION,
    assignment_id: input.assignmentId.trim(),
    activity_id: input.activityId.trim(),
    resource_id: input.resourceId.trim(),
    role_id: input.roleId?.trim() ? input.roleId.trim() : null,
    units: normalizedDecimal(input.units ?? ""),
    unit: input.unit?.trim() ? input.unit.trim() : null,
    planned_cost: normalizedDecimal(input.plannedCost ?? ""),
    currency: input.currency?.trim() ? input.currency.trim() : null,
    calendar_id: calendarId,
    calendar_version: calendarVersion,
    note: input.note?.trim() ? input.note.trim() : null,
  };
}

export async function saveAssignment(
  transport: ApiTransport,
  context: ProjectContext,
  input: AssignmentInput,
): Promise<ApiResult<AssignmentRecord>> {
  let payload: Record<string, unknown>;
  try {
    payload = buildAssignmentPayload(input);
  } catch (error) {
    return localError(error instanceof Error ? error.message : "ASSIGNMENT_FIELDS_REQUIRED");
  }
  const result = await transport.post<Record<string, unknown>, unknown>(
    assignmentPath(context),
    payload,
    context,
    crypto.randomUUID(),
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseAssignment(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ASSIGNMENT_RESPONSE");
  }
}

export function buildAssignmentPeriodPayload(input: AssignmentPeriodInput): Record<string, unknown> {
  if (!input.assignmentId.trim() || !input.activityId.trim() || !input.resourceId.trim()) {
    throw new Error("ASSIGNMENT_PERIOD_FIELDS_REQUIRED");
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(input.periodStart.trim())) {
    throw new Error("INVALID_ASSIGNMENT_PERIOD_START");
  }
  const units = normalizedDecimal(input.units);
  const cost = normalizedDecimal(input.cost);
  if (units === null || cost === null) throw new Error("ASSIGNMENT_PERIOD_VALUES_REQUIRED");
  return {
    assignment_id: input.assignmentId.trim(),
    activity_id: input.activityId.trim(),
    resource_id: input.resourceId.trim(),
    period_start: input.periodStart.trim(),
    units,
    cost,
  };
}

export async function saveAssignmentPeriod(
  transport: ApiTransport,
  context: ProjectContext,
  input: AssignmentPeriodInput,
): Promise<ApiResult<AssignmentPeriod>> {
  let payload: Record<string, unknown>;
  try {
    payload = buildAssignmentPeriodPayload(input);
  } catch (error) {
    return localError(error instanceof Error ? error.message : "ASSIGNMENT_PERIOD_FIELDS_REQUIRED");
  }
  const result = await transport.post<Record<string, unknown>, unknown>(
    periodPath(context),
    payload,
    context,
    crypto.randomUUID(),
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseAssignmentPeriod(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ASSIGNMENT_PERIOD_RESPONSE");
  }
}

type DecimalParts = { negative: boolean; whole: string; fraction: string };

function decimalParts(value: string): DecimalParts {
  const negative = value.startsWith("-");
  const body = negative ? value.slice(1) : value;
  const [whole = "0", fraction = ""] = body.split(".");
  return {
    negative: negative && (whole !== "0" || /[1-9]/.test(fraction)),
    whole,
    fraction,
  };
}

function scaledDecimal(value: string, scale: number): bigint {
  const parts = decimalParts(value);
  const magnitude = BigInt(`${parts.whole}${parts.fraction.padEnd(scale, "0")}`);
  return parts.negative ? -magnitude : magnitude;
}

function formatScaledDecimal(total: bigint, scale: number): string {
  const negative = total < 0n;
  const digits = (negative ? -total : total).toString().padStart(scale + 1, "0");
  const whole = digits.slice(0, digits.length - scale) || "0";
  const fraction = scale > 0 ? digits.slice(digits.length - scale).replace(/0+$/, "") : "";
  return `${negative ? "-" : ""}${whole}${fraction ? `.${fraction}` : ""}`;
}

/** Exact decimal sum over stored API strings; null when no value is present. */
export function addDecimalText(values: readonly (string | null | undefined)[]): string | null {
  const usable = values.filter((value): value is string => typeof value === "string" && value.trim() !== "");
  if (!usable.length) return null;
  const scale = Math.max(...usable.map((value) => decimalParts(value).fraction.length));
  let total = 0n;
  for (const value of usable) total += scaledDecimal(value, scale);
  return formatScaledDecimal(total, scale);
}

export function compareDecimalText(left: string | null, right: string | null): number {
  if (left === null && right === null) return 0;
  if (left === null) return 1;
  if (right === null) return -1;
  const scale = Math.max(decimalParts(left).fraction.length, decimalParts(right).fraction.length);
  const a = scaledDecimal(left, scale);
  const b = scaledDecimal(right, scale);
  return a === b ? 0 : a < b ? -1 : 1;
}

export function cellValue(
  row: AssignmentRecord,
  key: AssignmentColumnKey,
  activityLabel: (id: string) => string,
  drivingLabels: { yes: string; no: string },
): string | null {
  switch (key) {
    case "assignment": return row.assignmentId;
    case "activity": return activityLabel(row.activityId);
    case "resource": return row.resourceId;
    case "role": return row.roleId;
    case "units": return row.units;
    case "actualUnits": return row.actualUnits;
    case "remainingUnits": return row.remainingUnits;
    case "unit": return row.unit;
    case "unitsPerTime": return row.unitsPerTime;
    case "plannedCost": return row.plannedCost;
    case "actualCost": return row.actualCost;
    case "remainingCost": return row.remainingCost;
    case "currency": return row.currency;
    case "calendar": return row.calendarId;
    case "driving": return row.isDriving === null ? null : row.isDriving ? drivingLabels.yes : drivingLabels.no;
    case "note": return row.note;
    default: return null;
  }
}

export function filterAssignments(
  rows: readonly AssignmentRecord[],
  filters: AssignmentFilters,
  activityLabel: (id: string) => string = (id) => id,
): AssignmentRecord[] {
  const query = filters.query.trim().toLowerCase();
  return rows.filter((row) => {
    if (filters.resourceId && row.resourceId !== filters.resourceId) return false;
    if (filters.activityId && row.activityId !== filters.activityId) return false;
    if (!query) return true;
    const haystack = [
      row.assignmentId,
      row.activityId,
      activityLabel(row.activityId),
      row.resourceId,
      row.roleId ?? "",
      row.note ?? "",
    ].join(" ").toLowerCase();
    return haystack.includes(query);
  });
}

export function sortAssignments(
  rows: readonly AssignmentRecord[],
  sort: AssignmentSort,
  activityLabel: (id: string) => string = (id) => id,
  drivingLabels: { yes: string; no: string } = { yes: "Yes", no: "No" },
): AssignmentRecord[] {
  if (!sort) return [...rows];
  const direction = sort.dir === "desc" ? -1 : 1;
  return rows
    .map((row, index) => ({ row, index }))
    .sort((a, b) => {
      if (NUMERIC_COLUMNS.has(sort.column)) {
        const compared = compareDecimalText(
          cellValue(a.row, sort.column, activityLabel, drivingLabels),
          cellValue(b.row, sort.column, activityLabel, drivingLabels),
        );
        if (compared !== 0) return compared * direction;
      } else {
        const left = cellValue(a.row, sort.column, activityLabel, drivingLabels) ?? "";
        const right = cellValue(b.row, sort.column, activityLabel, drivingLabels) ?? "";
        const compared = left.localeCompare(right, "en", { numeric: true, sensitivity: "base" });
        if (compared !== 0) return compared * direction;
      }
      return a.index - b.index;
    })
    .map((entry) => entry.row);
}

export function groupAssignments(
  rows: readonly AssignmentRecord[],
  groupBy: AssignmentGroupBy,
  activityLabel: (id: string) => string = (id) => id,
  unassignedLabel = "Unassigned",
): AssignmentGroup[] {
  if (groupBy === "none") return [];
  const groups = new Map<string, AssignmentGroup>();
  for (const row of rows) {
    const key = groupBy === "resource"
      ? row.resourceId
      : groupBy === "activity"
        ? row.activityId
        : row.roleId ?? "";
    const label = key
      ? groupBy === "activity" ? activityLabel(key) : key
      : unassignedLabel;
    let group = groups.get(key);
    if (!group) {
      group = { key, label, rows: [], totals: { units: null, plannedCost: null, actualCost: null } };
      groups.set(key, group);
    }
    group.rows.push(row);
  }
  return [...groups.values()]
    .map((group) => ({
      ...group,
      totals: {
        units: addDecimalText(group.rows.map((row) => row.units)),
        plannedCost: addDecimalText(group.rows.map((row) => row.plannedCost)),
        actualCost: addDecimalText(group.rows.map((row) => row.actualCost)),
      },
    }))
    .sort((a, b) => a.label.localeCompare(b.label, "en", { numeric: true, sensitivity: "base" }));
}

export function buildAssignmentProfile(
  periods: readonly AssignmentPeriod[],
  assignmentId: string,
): AssignmentProfile {
  const points = periods
    .filter((period) => period.assignmentId === assignmentId)
    .slice()
    .sort((a, b) => a.periodStart.localeCompare(b.periodStart))
    .map((period) => ({ periodStart: period.periodStart, units: period.units, cost: period.cost }));
  const unitValues = points.map((point) => point.units);
  return {
    points,
    totalUnits: addDecimalText(unitValues),
    totalCost: addDecimalText(points.map((point) => point.cost)),
    maxUnits: points.length
      ? unitValues.reduce((max, value) => (compareDecimalText(value, max) > 0 ? value : max), unitValues[0])
      : null,
  };
}

export function reviseAssignmentId(baseId: string, existingIds: Iterable<string>): string {
  const existing = new Set(existingIds);
  const match = /^(.*)-R(\d+)$/.exec(baseId);
  const stem = match ? match[1] : baseId;
  let revision = match ? Number(match[2]) + 1 : 2;
  let candidate = `${stem}-R${revision}`;
  while (existing.has(candidate)) {
    revision += 1;
    candidate = `${stem}-R${revision}`;
  }
  return candidate;
}

export function defaultAssignmentViewPrefs(): AssignmentViewPrefs {
  return { groupBy: "none", sort: null, columns: [...DEFAULT_COLUMNS] };
}

export function loadAssignmentViewPrefs(
  storage: Pick<Storage, "getItem"> | null,
  projectId: string,
): AssignmentViewPrefs {
  const defaults = defaultAssignmentViewPrefs();
  if (!storage) return defaults;
  try {
    const raw = storage.getItem(`${ASSIGNMENT_STORAGE_KEY}.${projectId}`);
    if (!raw) return defaults;
    const parsed: unknown = JSON.parse(raw);
    if (!isRecord(parsed)) return defaults;
    const groupBy = GROUP_BY_VALUES.includes(parsed.groupBy as AssignmentGroupBy)
      ? (parsed.groupBy as AssignmentGroupBy)
      : defaults.groupBy;
    let sort: AssignmentSort = null;
    if (isRecord(parsed.sort)) {
      const column = parsed.sort.column;
      const dir = parsed.sort.dir;
      if (
        typeof column === "string" &&
        ASSIGNMENT_COLUMNS.some((entry) => entry.key === column) &&
        (dir === "asc" || dir === "desc")
      ) {
        sort = { column: column as AssignmentColumnKey, dir };
      }
    }
    const columns: AssignmentColumnKey[] = [];
    if (Array.isArray(parsed.columns)) {
      for (const key of parsed.columns) {
        if (
          typeof key === "string" &&
          ASSIGNMENT_COLUMNS.some((entry) => entry.key === key) &&
          !columns.includes(key as AssignmentColumnKey)
        ) {
          columns.push(key as AssignmentColumnKey);
        }
      }
    }
    return {
      groupBy,
      sort,
      columns: columns.length ? columns : defaults.columns,
    };
  } catch {
    return defaults;
  }
}

export function saveAssignmentViewPrefs(
  storage: Pick<Storage, "setItem"> | null,
  projectId: string,
  prefs: AssignmentViewPrefs,
): void {
  if (!storage) return;
  try {
    storage.setItem(`${ASSIGNMENT_STORAGE_KEY}.${projectId}`, JSON.stringify(prefs));
  } catch {
    // A blocked storage quota must not break the window.
  }
}

type PageState = {
  status: "loading" | "loaded" | "error";
  errorCode: string | null;
  assignments: readonly AssignmentRecord[];
  periods: readonly AssignmentPeriod[];
  periodsStatus: "loading" | "loaded" | "error";
  periodsErrorCode: string | null;
  selectedId: string | null;
  tab: "general" | "spreadsheet" | "profile";
  mode: "browse" | "create";
  draft: AssignmentInput;
  busy: boolean;
  notice: { kind: "ok" | "error"; message: string } | null;
  groupBy: AssignmentGroupBy;
  collapsed: Set<string>;
  sort: AssignmentSort;
  filters: AssignmentFilters;
  columns: Set<AssignmentColumnKey>;
  periodDraft: { periodStart: string; units: string; cost: string };
  periodBusy: boolean;
  periodNotice: { kind: "ok" | "error"; message: string } | null;
  calendars: readonly WorkspaceCalendarRecord[];
  calendarError: string | null;
};

function emptyDraft(): AssignmentInput {
  return {
    assignmentId: "",
    activityId: "",
    resourceId: "",
    roleId: null,
    units: null,
    unit: null,
    plannedCost: null,
    currency: null,
    calendarId: null,
    calendarVersion: null,
    note: null,
  };
}

function emptyPeriodDraft(): { periodStart: string; units: string; cost: string } {
  return { periodStart: "", units: "", cost: "" };
}

function draftFromAssignment(record: AssignmentRecord, assignmentId: string): AssignmentInput {
  return {
    assignmentId,
    activityId: record.activityId,
    resourceId: record.resourceId,
    roleId: record.roleId,
    units: record.units,
    unit: record.unit,
    plannedCost: record.plannedCost,
    currency: record.currency,
    calendarId: record.calendarId,
    calendarVersion: record.calendarVersion,
    note: record.note,
  };
}

function storageOrNull(): Storage | null {
  try {
    return typeof localStorage === "undefined" ? null : localStorage;
  } catch {
    return null;
  }
}

export function mountWorkspaceAssignmentsPage(host: HTMLElement, options: AssignmentPageOptions): void {
  if (host.dataset.assignmentsMounted === "true") return;
  host.dataset.assignmentsMounted = "true";
  const { transport, context, locale, activities, canWrite } = options;
  const prefs = loadAssignmentViewPrefs(storageOrNull(), context.project_id);
  const state: PageState = {
    status: "loading",
    errorCode: null,
    assignments: [],
    periods: [],
    periodsStatus: "loading",
    periodsErrorCode: null,
    selectedId: null,
    tab: "general",
    mode: "browse",
    draft: emptyDraft(),
    busy: false,
    notice: null,
    groupBy: prefs.groupBy,
    collapsed: new Set(),
    sort: prefs.sort,
    filters: { query: "", resourceId: "", activityId: "" },
    columns: new Set(prefs.columns),
    periodDraft: emptyPeriodDraft(),
    periodBusy: false,
    periodNotice: null,
    calendars: [],
    calendarError: null,
  };

  const say = (en: string, fa: string): string => text(locale, en, fa);
  const selected = (): AssignmentRecord | null =>
    state.assignments.find((item) => item.assignmentId === state.selectedId) ?? null;
  const activityLabel = (id: string): string => {
    const activity = activities.find((item) => item.id === id);
    return activity ? `${activity.code} ${activity.name}` : id;
  };
  const drivingLabels = { yes: say("Yes", "بله"), no: say("No", "خیر") };
  const columnLabel = (column: ColumnDefinition): string => say(column.en, column.fa);
  const visibleColumns = (): ColumnDefinition[] =>
    ASSIGNMENT_COLUMNS.filter((column) => state.columns.has(column.key));

  function currentPrefs(): AssignmentViewPrefs {
    return {
      groupBy: state.groupBy,
      sort: state.sort,
      columns: ASSIGNMENT_COLUMNS.filter((column) => state.columns.has(column.key)).map((column) => column.key),
    };
  }

  function persistPrefs(): void {
    saveAssignmentViewPrefs(storageOrNull(), context.project_id, currentPrefs());
  }

  function filteredRows(): AssignmentRecord[] {
    const filtered = filterAssignments(state.assignments, state.filters, activityLabel);
    return sortAssignments(filtered, state.sort, activityLabel, drivingLabels);
  }

  function renderRegister(): string {
    if (state.status === "loading") {
      return `<div class="cp-calendar-empty" role="status">${escapeHtml(say("Reading resource assignments…", "در حال خواندن تخصیص‌های منابع…"))}</div>`;
    }
    if (state.status === "error") {
      return `<div class="cp-calendar-empty" role="alert">${escapeHtml(say("Resource assignments could not be read", "خواندن تخصیص‌های منابع ناموفق بود"))} (${escapeHtml(state.errorCode ?? "unknown")})</div>`;
    }
    if (!state.assignments.length) {
      return `<div class="cp-calendar-empty">${escapeHtml(say("No resource assignments are stored for this project.", "هیچ تخصیص منبعی برای این پروژه ذخیره نشده است."))}</div>`;
    }
    const rows = filteredRows();
    if (!rows.length) {
      return `<div class="cp-calendar-empty" data-assignment-filtered-empty>${escapeHtml(say("No assignment matches the current filter.", "هیچ تخصیصی با فیلتر فعلی مطابقت ندارد."))}</div>`;
    }
    const columns = visibleColumns();
    const header = columns.map((column) => {
      const active = state.sort?.column === column.key;
      const indicator = active ? (state.sort?.dir === "desc" ? " ▼" : " ▲") : "";
      const ariaSort = active ? (state.sort?.dir === "desc" ? "descending" : "ascending") : "none";
      return `<th data-assignment-sort="${column.key}" aria-sort="${ariaSort}" tabindex="0">${escapeHtml(columnLabel(column))}${indicator}</th>`;
    }).join("");
    const rowHtml = (item: AssignmentRecord): string => {
      const active = item.assignmentId === state.selectedId;
      return `<tr data-assignment-row data-assignment-id="${escapeHtml(item.assignmentId)}" tabindex="0" role="button" aria-selected="${active}" class="${active ? "is-selected" : ""}">${columns.map((column) => `<td>${escapeHtml(cellValue(item, column.key, activityLabel, drivingLabels) ?? "—")}</td>`).join("")}</tr>`;
    };
    let body: string;
    if (state.groupBy === "none") {
      body = rows.map(rowHtml).join("");
    } else {
      const groups = groupAssignments(rows, state.groupBy, activityLabel, say("Unassigned", "بدون نقش"));
      body = groups.map((group) => {
        const collapsed = state.collapsed.has(`${state.groupBy}:${group.key}`);
        const totals = [
          `${say("Units", "واحد")}: ${group.totals.units ?? "—"}`,
          `${say("Planned Cost", "هزینه برنامه‌ای")}: ${group.totals.plannedCost ?? "—"}`,
          `${say("Actual Cost", "هزینه واقعی")}: ${group.totals.actualCost ?? "—"}`,
        ].join(" · ");
        const groupRow = `<tr class="cp-assignment-group-row" data-assignment-group-row="${escapeHtml(group.key)}"><td colspan="${columns.length}"><button type="button" class="cp-assignment-group-toggle" data-assignment-group-toggle="${escapeHtml(group.key)}" aria-expanded="${!collapsed}">${collapsed ? "▸" : "▾"}</button> <strong>${escapeHtml(group.label)}</strong> <span data-assignment-group-count>(${group.rows.length})</span> <span class="cp-assignment-group-totals" data-assignment-group-totals>${escapeHtml(totals)}</span></td></tr>`;
        return groupRow + (collapsed ? "" : group.rows.map(rowHtml).join(""));
      }).join("");
    }
    return `<div class="cp-register-table-wrap"><table><thead><tr>${header}</tr></thead><tbody>${body}</tbody></table></div>`;
  }

  function renderToolbar(): string {
    const resourceOptions = [...new Set(state.assignments.map((item) => item.resourceId))]
      .sort((a, b) => a.localeCompare(b, "en", { numeric: true }));
    const resourceSelect = `<select data-assignment-filter="resource" aria-label="${escapeHtml(say("Filter by resource", "فیلتر بر اساس منبع"))}"><option value="">${escapeHtml(say("All resources", "همه منابع"))}</option>${resourceOptions.map((id) => `<option value="${escapeHtml(id)}"${state.filters.resourceId === id ? " selected" : ""}>${escapeHtml(id)}</option>`).join("")}</select>`;
    const activityOptions = [...new Set(state.assignments.map((item) => item.activityId))]
      .sort((a, b) => activityLabel(a).localeCompare(activityLabel(b), "en", { numeric: true }));
    const activitySelect = `<select data-assignment-filter="activity" aria-label="${escapeHtml(say("Filter by activity", "فیلتر بر اساس فعالیت"))}"><option value="">${escapeHtml(say("All activities", "همه فعالیت‌ها"))}</option>${activityOptions.map((id) => `<option value="${escapeHtml(id)}"${state.filters.activityId === id ? " selected" : ""}>${escapeHtml(activityLabel(id))}</option>`).join("")}</select>`;
    const groupOptions = GROUP_BY_VALUES.map((value) => `<option value="${value}"${state.groupBy === value ? " selected" : ""}>${escapeHtml(value === "none" ? say("None", "بدون گروه") : value === "resource" ? say("Resource", "منبع") : value === "activity" ? say("Activity", "فعالیت") : say("Role", "نقش"))}</option>`).join("");
    const columnChecks = ASSIGNMENT_COLUMNS.map((column) => `<label><input type="checkbox" data-assignment-column="${column.key}"${state.columns.has(column.key) ? " checked" : ""}> ${escapeHtml(columnLabel(column))}</label>`).join("");
    return `<div class="cp-register-toolbar">
      <strong>${escapeHtml(say("Resource Assignments", "تخصیص منابع"))}</strong>
      <div class="cp-assignment-toolbar-controls">
        <label>${escapeHtml(say("Group by", "گروه‌بندی بر اساس"))} <select data-assignment-group>${groupOptions}</select></label>
        <input type="search" data-assignment-filter="query" value="${escapeHtml(state.filters.query)}" placeholder="${escapeHtml(say("Search assignments", "جستجوی تخصیص‌ها"))}" aria-label="${escapeHtml(say("Search assignments", "جستجوی تخصیص‌ها"))}">
        ${resourceSelect}
        ${activitySelect}
        <details class="cp-assignment-columns"><summary>${escapeHtml(say("Columns", "ستون‌ها"))}</summary><div class="cp-assignment-columns-panel" data-assignment-columns>${columnChecks}</div></details>
        ${canWrite ? `<button type="button" data-assignment-action="new" ${state.busy ? "disabled" : ""}>${escapeHtml(say("New Assignment", "تخصیص جدید"))}</button>
        <button type="button" data-assignment-action="revise" ${state.busy || !selected() ? "disabled" : ""} title="${escapeHtml(say("Copy the selected assignment into a new revision", "رونوشت تخصیص انتخاب‌شده در یک بازنگری جدید"))}">${escapeHtml(say("Revise", "بازنگری"))}</button>` : ""}
        <button type="button" data-assignment-action="reload" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Refresh", "به‌روزرسانی"))}</button>
      </div>
    </div>`;
  }

  function activityOptions(current: string): string {
    const known = activities.some((item) => item.id === current);
    const first = current && !known
      ? `<option value="${escapeHtml(current)}" selected>${escapeHtml(current)}</option>`
      : `<option value="">${escapeHtml(say("Select an activity", "یک فعالیت انتخاب کنید"))}</option>`;
    return first + activities.map((item) => {
      const label = `${item.code} ${item.name}`;
      return `<option value="${escapeHtml(item.id)}"${item.id === current ? " selected" : ""}>${escapeHtml(label)}</option>`;
    }).join("");
  }

  function renderForm(): string {
    const draft = state.draft;
    const knownResources = [...new Set(state.assignments.map((item) => item.resourceId))];
    const knownRoles = [...new Set(state.assignments.map((item) => item.roleId).filter((item): item is string => !!item))];
    return `<form data-assignment-form class="cp-assignment-fields">
      <label>${escapeHtml(say("Assignment ID", "شناسه تخصیص"))}<input name="assignment-id" value="${escapeHtml(draft.assignmentId)}" required></label>
      <label>${escapeHtml(say("Activity", "فعالیت"))}<select name="activity-id" required>${activityOptions(draft.activityId)}</select></label>
      <label>${escapeHtml(say("Resource", "منبع"))}<input name="resource-id" value="${escapeHtml(draft.resourceId)}" list="cp-assignment-resources" required></label>
      <label>${escapeHtml(say("Role", "نقش"))}<input name="role-id" value="${escapeHtml(draft.roleId ?? "")}" list="cp-assignment-roles"></label>
      <label>${escapeHtml(say("Budgeted Units", "واحد بودجه"))}<input name="units" value="${escapeHtml(draft.units ?? "")}" inputmode="decimal"></label>
      <label>${escapeHtml(say("Unit", "واحد"))}<input name="unit" value="${escapeHtml(draft.unit ?? "")}"></label>
      <label>${escapeHtml(say("Planned Cost", "هزینه برنامه‌ای"))}<input name="planned-cost" value="${escapeHtml(draft.plannedCost ?? "")}" inputmode="decimal"></label>
      <label>${escapeHtml(say("Currency", "ارز"))}<input name="currency" value="${escapeHtml(draft.currency ?? "")}"></label>
      <label>${escapeHtml(say("Calendar", "تقویم"))}<select name="calendar"><option value="">${escapeHtml(say("Project default", "پیش‌فرض پروژه"))}</option>${state.calendars.map((calendar) => {
        const value = `${calendar.calendarId}|${calendar.calendarVersion}`;
        const selected = calendar.calendarId === draft.calendarId && calendar.calendarVersion === draft.calendarVersion;
        return `<option value="${escapeHtml(value)}"${selected ? " selected" : ""}>${escapeHtml(`${calendar.calendarId} @ ${calendar.calendarVersion} — ${calendar.name}`)}</option>`;
      }).join("")}</select></label>
      <label class="cp-assignment-note">${escapeHtml(say("Note", "یادداشت"))}<input name="note" value="${escapeHtml(draft.note ?? "")}"></label>
      <div class="cp-calendar-panel-actions"><button type="submit" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Create assignment", "ایجاد تخصیص"))}</button><button type="button" data-assignment-action="cancel">${escapeHtml(say("Cancel", "لغو"))}</button></div>
      ${state.calendarError ? `<p class="cp-register-notice" data-assignment-calendar-error>${escapeHtml(say("Stored calendars could not be read", "خواندن تقویم‌های ذخیره‌شده ناموفق بود"))} (${escapeHtml(state.calendarError)})</p>` : ""}
      <datalist id="cp-assignment-resources">${knownResources.map((id) => `<option value="${escapeHtml(id)}"></option>`).join("")}</datalist>
      <datalist id="cp-assignment-roles">${knownRoles.map((id) => `<option value="${escapeHtml(id)}"></option>`).join("")}</datalist>
    </form>
    <p class="cp-register-notice">${escapeHtml(say("Stored assignments are immutable facts. A revision is stored as a new assignment ID so the previous fact stays auditable.", "تخصیص‌های ذخیره‌شده حقایق تغییرناپذیرند. بازنگری با شناسهٔ تخصیص جدید ذخیره می‌شود تا حقیقت قبلی قابل حسابرسی بماند."))}</p>`;
  }

  function renderGeneral(item: AssignmentRecord): string {
    const row = (label: string, value: string | null): string =>
      `<label>${escapeHtml(label)}<input readonly value="${escapeHtml(value ?? say("Not provided", "ارائه نشده"))}"></label>`;
    return `<div class="cp-assignment-fields">
      ${row(say("Assignment ID", "شناسه تخصیص"), item.assignmentId)}
      ${row(say("Activity", "فعالیت"), activityLabel(item.activityId))}
      ${row(say("Resource", "منبع"), item.resourceId)}
      ${row(say("Role", "نقش"), item.roleId)}
      ${row(say("Budgeted Units", "واحد بودجه"), item.units)}
      ${row(say("Actual Units", "واحد واقعی"), item.actualUnits)}
      ${row(say("Remaining Units", "واحد باقی‌مانده"), item.remainingUnits)}
      ${row(say("Planned Cost", "هزینه برنامه‌ای"), item.plannedCost)}
      ${row(say("Actual Cost", "هزینه واقعی"), item.actualCost)}
      ${row(say("Remaining Cost", "هزینه باقی‌مانده"), item.remainingCost)}
      ${row(say("Units / Time", "واحد / زمان"), item.unitsPerTime)}
      ${row(say("Units / Time Period", "دوره واحد / زمان"), item.unitsPerTimePeriod)}
      ${row(say("Hours / Units Time Period", "ساعت / دوره واحد زمان"), item.hoursPerUnitsTimePeriod)}
      ${row(say("Calendar", "تقویم"), item.calendarId)}
      ${row(say("Driving", "تعیین‌کننده"), item.isDriving === null ? null : item.isDriving ? say("Yes", "بله") : say("No", "خیر"))}
      ${row(say("Note", "یادداشت"), item.note)}
    </div>
    <p class="cp-register-notice">${escapeHtml(say("Stored assignments are immutable. Revise copies this fact into a new assignment ID so the previous fact stays auditable.", "تخصیص‌های ذخیره‌شده تغییرناپذیرند. بازنگری این حقیقت را در شناسهٔ تخصیص جدید رونوشت می‌کند تا حقیقت قبلی قابل حسابرسی بماند."))}</p>`;
  }

  function selectedPeriods(item: AssignmentRecord): AssignmentPeriod[] {
    return state.periods
      .filter((period) => period.assignmentId === item.assignmentId)
      .slice()
      .sort((a, b) => a.periodStart.localeCompare(b.periodStart));
  }

  function renderSpreadsheet(item: AssignmentRecord): string {
    const heading = `<strong>${escapeHtml(say("Spreadsheet", "صفحه‌گسترده"))}</strong>`;
    if (state.periodsStatus === "loading") {
      return `<div data-assignment-panel="spreadsheet">${heading}<div class="cp-calendar-empty" role="status">${escapeHtml(say("Reading stored assignment periods…", "در حال خواندن دوره‌های ذخیره‌شدهٔ تخصیص…"))}</div></div>`;
    }
    if (state.periodsStatus === "error") {
      return `<div data-assignment-panel="spreadsheet">${heading}<div class="cp-calendar-empty" role="alert">${escapeHtml(say("Stored assignment periods could not be read", "خواندن دوره‌های ذخیره‌شدهٔ تخصیص ناموفق بود"))} (${escapeHtml(state.periodsErrorCode ?? "unknown")})</div></div>`;
    }
    const periods = selectedPeriods(item);
    const table = periods.length
      ? `<div class="cp-register-table-wrap"><table><thead><tr><th>${escapeHtml(say("Period Start", "شروع دوره"))}</th><th>${escapeHtml(say("Units", "واحد"))}</th><th>${escapeHtml(say("Cost", "هزینه"))}</th></tr></thead><tbody>${periods.map((period) => `<tr data-assignment-period-row data-period-start="${escapeHtml(period.periodStart)}"><td>${escapeHtml(period.periodStart)}</td><td>${escapeHtml(period.units)}</td><td>${escapeHtml(period.cost)}</td></tr>`).join("")}<tr class="cp-assignment-group-row" data-assignment-period-totals><td>${escapeHtml(say("Total", "جمع"))}</td><td>${escapeHtml(addDecimalText(periods.map((period) => period.units)) ?? "—")}</td><td>${escapeHtml(addDecimalText(periods.map((period) => period.cost)) ?? "—")}</td></tr></tbody></table></div>`
      : `<div class="cp-calendar-empty" data-assignment-period-empty>${escapeHtml(say("No time-phased period is stored for this assignment.", "هیچ دورهٔ زمان‌محوری برای این تخصیص ذخیره نشده است."))}</div>`;
    return `<div data-assignment-panel="spreadsheet">
      ${heading}
      ${table}
      <form data-assignment-period-form class="cp-assignment-period-fields">
        <label>${escapeHtml(say("Period Start", "شروع دوره"))}<input type="date" name="period-start" value="${escapeHtml(state.periodDraft.periodStart)}" required></label>
        <label>${escapeHtml(say("Units", "واحد"))}<input name="period-units" value="${escapeHtml(state.periodDraft.units)}" inputmode="decimal" required></label>
        <label>${escapeHtml(say("Cost", "هزینه"))}<input name="period-cost" value="${escapeHtml(state.periodDraft.cost)}" inputmode="decimal" required></label>
        <div class="cp-calendar-panel-actions"><button type="submit" ${state.periodBusy ? "disabled" : ""}>${escapeHtml(say("Add period", "افزودن دوره"))}</button></div>
      </form>
      ${state.periodNotice ? `<p class="cp-calendar-notice" data-assignment-period-notice data-state="${state.periodNotice.kind}" role="status">${escapeHtml(state.periodNotice.message)}</p>` : ""}
    </div>`;
  }

  function renderProfile(item: AssignmentRecord): string {
    const profile = buildAssignmentProfile(state.periods, item.assignmentId);
    const heading = `<strong>${escapeHtml(say("Profile", "نیم‌رخ"))}</strong>`;
    if (!profile.points.length) {
      return `<div data-assignment-panel="profile">${heading}<div class="cp-calendar-empty" data-assignment-profile-empty>${escapeHtml(say("The profile needs stored assignment periods for this assignment.", "نیم‌رخ به دوره‌های ذخیره‌شدهٔ این تخصیص نیاز دارد."))}</div></div>`;
    }
    const max = profile.maxUnits === null ? 0 : Number(profile.maxUnits);
    const bars = profile.points.map((point) => {
      const value = Number(point.units);
      const height = max > 0 && Number.isFinite(value) ? Math.max(2, Math.round((value / max) * 100)) : 0;
      return `<div class="cp-assignment-profile-bar" data-assignment-profile-bar data-period-start="${escapeHtml(point.periodStart)}" data-units="${escapeHtml(point.units)}" title="${escapeHtml(`${point.periodStart}: ${point.units} / ${point.cost}`)}"><b style="height:${height}%"></b><em>${escapeHtml(point.periodStart.slice(5))}</em></div>`;
    }).join("");
    return `<div data-assignment-panel="profile">
      ${heading}
      <p class="cp-calendar-hint" data-assignment-profile-summary>${escapeHtml(say(
        `Units ${profile.totalUnits ?? "—"} · Cost ${profile.totalCost ?? "—"} · Peak ${profile.maxUnits ?? "—"} over ${profile.points.length} period(s)`,
        `واحد ${profile.totalUnits ?? "—"} · هزینه ${profile.totalCost ?? "—"} · اوج ${profile.maxUnits ?? "—"} در ${profile.points.length} دوره`,
      ))}</p>
      <div class="cp-assignment-profile-bars" role="img" aria-label="${escapeHtml(say("Stored units by period", "واحدهای ذخیره‌شده به تفکیک دوره"))}">${bars}</div>
    </div>`;
  }

  function renderDetails(): string {
    if (state.mode === "create") return renderForm();
    const item = selected();
    if (!item) {
      return `<p>${escapeHtml(say("Select an assignment from the register to read its stored values.", "برای خواندن مقادیر ذخیره‌شده، یک تخصیص را از فهرست انتخاب کنید."))}</p>`;
    }
    if (state.tab === "spreadsheet") return renderSpreadsheet(item);
    if (state.tab === "profile") return renderProfile(item);
    return renderGeneral(item);
  }

  function render(): void {
    host.innerHTML = `${renderToolbar()}
      ${renderRegister()}
      <section class="cp-register-details"><header><strong>${escapeHtml(say("Assignment Details", "جزئیات تخصیص"))}</strong><span>${selected() ? escapeHtml(selected()?.assignmentId ?? "") : escapeHtml(say("No selection", "بدون انتخاب"))}</span></header>
        <div class="cp-register-detail-tabs" role="tablist" aria-label="${escapeHtml(say("Assignment detail tabs", "زبانه‌های جزئیات تخصیص"))}">
          ${([["general", "General", "عمومی"], ["spreadsheet", "Spreadsheet", "صفحه‌گسترده"], ["profile", "Profile", "نیم‌رخ"]] as const).map(([key, en, fa]) => `<button type="button" role="tab" aria-selected="${state.tab === key}" class="${state.tab === key ? "is-active" : ""}" data-assignment-tab="${key}">${escapeHtml(say(en, fa))}</button>`).join("")}
        </div>
        <div class="cp-register-detail-content">${renderDetails()}</div>
      </section>
      ${state.notice ? `<p class="cp-calendar-notice" data-assignment-notice data-state="${state.notice.kind}" role="status">${escapeHtml(state.notice.message)}</p>` : ""}`;
  }

  async function reload(keepSelection: string | null): Promise<void> {
    state.status = "loading";
    state.periodsStatus = "loading";
    render();
    const [assignmentResult, periodResult] = await Promise.all([
      loadAssignments(transport, context),
      loadAssignmentPeriods(transport, context),
    ]);
    if (assignmentResult.ok) {
      state.status = "loaded";
      state.errorCode = null;
      state.assignments = assignmentResult.data;
      state.selectedId = keepSelection && assignmentResult.data.some((item) => item.assignmentId === keepSelection) ? keepSelection : null;
    } else {
      state.status = "error";
      state.errorCode = assignmentResult.error.code;
    }
    if (periodResult.ok) {
      state.periodsStatus = "loaded";
      state.periodsErrorCode = null;
      state.periods = periodResult.data;
    } else {
      state.periodsStatus = "error";
      state.periodsErrorCode = periodResult.error.code;
    }
    render();
  }

  host.addEventListener("click", (event) => {
    const target = event.target as HTMLElement;
    const groupToggle = target.closest<HTMLElement>("[data-assignment-group-toggle]");
    if (groupToggle?.dataset.assignmentGroupToggle !== undefined) {
      const key = `${state.groupBy}:${groupToggle.dataset.assignmentGroupToggle}`;
      if (state.collapsed.has(key)) state.collapsed.delete(key);
      else state.collapsed.add(key);
      render();
      return;
    }
    const sortHeader = target.closest<HTMLElement>("[data-assignment-sort]");
    if (sortHeader?.dataset.assignmentSort) {
      const column = sortHeader.dataset.assignmentSort as AssignmentColumnKey;
      state.sort = state.sort?.column === column
        ? { column, dir: state.sort.dir === "asc" ? "desc" : "asc" }
        : { column, dir: "asc" };
      persistPrefs();
      render();
      return;
    }
    const tab = target.closest<HTMLElement>("[data-assignment-tab]")?.dataset.assignmentTab;
    if (tab === "general" || tab === "spreadsheet" || tab === "profile") {
      state.tab = tab;
      state.notice = null;
      render();
      return;
    }
    const row = target.closest<HTMLElement>("[data-assignment-row]");
    if (row?.dataset.assignmentId) {
      state.selectedId = row.dataset.assignmentId;
      state.mode = "browse";
      state.notice = null;
      state.periodNotice = null;
      state.periodDraft = emptyPeriodDraft();
      render();
      return;
    }
    const action = target.closest<HTMLElement>("[data-assignment-action]")?.dataset.assignmentAction;
    if (!action) return;
    if (action === "new") {
      state.mode = "create";
      state.draft = emptyDraft();
      state.notice = null;
      render();
      return;
    }
    if (action === "revise") {
      const item = selected();
      if (!item) return;
      state.mode = "create";
      state.draft = draftFromAssignment(item, reviseAssignmentId(item.assignmentId, state.assignments.map((entry) => entry.assignmentId)));
      state.notice = null;
      render();
      return;
    }
    if (action === "cancel") {
      state.mode = "browse";
      state.notice = null;
      render();
      return;
    }
    if (action === "reload") {
      void reload(state.selectedId);
    }
  });

  host.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const header = (event.target as HTMLElement).closest<HTMLElement>("[data-assignment-sort]");
    if (header?.dataset.assignmentSort) {
      event.preventDefault();
      header.click();
      return;
    }
    const row = (event.target as HTMLElement).closest<HTMLElement>("[data-assignment-row]");
    if (!row?.dataset.assignmentId) return;
    event.preventDefault();
    state.selectedId = row.dataset.assignmentId;
    state.mode = "browse";
    state.notice = null;
    render();
  });

  host.addEventListener("input", (event) => {
    const target = event.target as HTMLInputElement;
    if (target.dataset.assignmentFilter === "query") {
      state.filters.query = target.value;
      const existing = host.querySelector<HTMLElement>(".cp-register-table-wrap") ?? host.querySelector<HTMLElement>("[data-assignment-filtered-empty]");
      const replacement = document.createElement("div");
      replacement.innerHTML = renderRegister();
      const next = replacement.firstElementChild;
      if (!next) return;
      if (existing) existing.replaceWith(next);
      else host.querySelector(".cp-register-toolbar")?.insertAdjacentElement("afterend", next);
      return;
    }
    if (!target.name) return;
    if (target.name === "period-start") state.periodDraft.periodStart = target.value;
    if (target.name === "period-units") state.periodDraft.units = target.value;
    if (target.name === "period-cost") state.periodDraft.cost = target.value;
    if (target.name === "assignment-id") state.draft.assignmentId = target.value;
    if (target.name === "resource-id") state.draft.resourceId = target.value;
    if (target.name === "role-id") state.draft.roleId = target.value;
    if (target.name === "units") state.draft.units = target.value;
    if (target.name === "unit") state.draft.unit = target.value;
    if (target.name === "planned-cost") state.draft.plannedCost = target.value;
    if (target.name === "currency") state.draft.currency = target.value;
    if (target.name === "note") state.draft.note = target.value;
  });

  host.addEventListener("change", (event) => {
    const target = event.target as HTMLInputElement | HTMLSelectElement;
    if (target.matches("select[data-assignment-group]")) {
      state.groupBy = target.value as AssignmentGroupBy;
      state.collapsed.clear();
      persistPrefs();
      render();
      return;
    }
    if (target.dataset.assignmentColumn) {
      const key = target.dataset.assignmentColumn as AssignmentColumnKey;
      if ((target as HTMLInputElement).checked) state.columns.add(key);
      else state.columns.delete(key);
      if (!state.columns.size) state.columns.add("assignment");
      persistPrefs();
      render();
      return;
    }
    if (target.dataset.assignmentFilter === "resource") {
      state.filters.resourceId = target.value;
      render();
      return;
    }
    if (target.dataset.assignmentFilter === "activity") {
      state.filters.activityId = target.value;
      render();
      return;
    }
    if (target.name === "activity-id") state.draft.activityId = target.value;
    if (target.name === "calendar") {
      const [calendarId, calendarVersion] = target.value.split("|");
      state.draft.calendarId = calendarId || null;
      state.draft.calendarVersion = calendarVersion || null;
    }
  });

  host.addEventListener("submit", (event) => {
    const form = event.target as HTMLFormElement;
    if (form.matches("[data-assignment-form]")) {
      event.preventDefault();
      if (state.busy) return;
      void (async () => {
        state.busy = true;
        render();
        const result = await saveAssignment(transport, context, state.draft);
        state.busy = false;
        if (!result.ok) {
          state.notice = {
            kind: "error",
            message: `${say("Assignment was not saved", "تخصیص ذخیره نشد")} (${result.error.code})`,
          };
          render();
          return;
        }
        state.notice = { kind: "ok", message: say("Assignment saved.", "تخصیص ذخیره شد.") };
        state.mode = "browse";
        await reload(result.data.assignmentId);
      })();
      return;
    }
    if (form.matches("[data-assignment-period-form]")) {
      event.preventDefault();
      const item = selected();
      if (!item || state.periodBusy) return;
      void (async () => {
        state.periodBusy = true;
        state.periodNotice = null;
        render();
        const result = await saveAssignmentPeriod(transport, context, {
          assignmentId: item.assignmentId,
          activityId: item.activityId,
          resourceId: item.resourceId,
          periodStart: state.periodDraft.periodStart,
          units: state.periodDraft.units,
          cost: state.periodDraft.cost,
        });
        state.periodBusy = false;
        if (!result.ok) {
          state.periodNotice = {
            kind: "error",
            message: `${say("Period was not saved", "دوره ذخیره نشد")} (${result.error.code})`,
          };
          render();
          return;
        }
        state.periodDraft = emptyPeriodDraft();
        state.periodNotice = { kind: "ok", message: say("Period saved.", "دوره ذخیره شد.") };
        await reload(state.selectedId);
      })();
    }
  });

  async function loadCalendars(): Promise<void> {
    const result = await loadCalendarCatalogue(transport, context);
    if (result.ok) {
      state.calendars = result.data;
      state.calendarError = null;
    } else {
      state.calendars = [];
      state.calendarError = result.error.code;
    }
    render();
  }

  void reload(null);
  void loadCalendars();
}
