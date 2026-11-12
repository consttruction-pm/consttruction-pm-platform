import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import type {
  WorkspaceCalendarCatalog,
  WorkspaceCalendarRecord,
} from "./workspace-model.js";

export type { WorkspaceCalendarRecord } from "./workspace-model.js";
import {
  formatJalaliDateInput,
  isValidCanonicalIsoDate,
  parseJalaliDateInput,
} from "./workspace-jalali-entry.js";

export const CALENDAR_CATALOG_CONTRACT = "p6-calendar-read-api.v1";
export const CALENDAR_API_CONTRACT = "p6-calendar.v1";
export const CALENDAR_USAGE_CONTRACT = "p6-calendar-usage-api.v1";

export type CalendarFactorSet = {
  hours_per_day: string | null;
  hours_per_week: string | null;
  hours_per_month: string | null;
  hours_per_year: string | null;
};

export type CalendarSnapshot = {
  kind: "working-day" | "working-time" | null;
  system: string | null;
  workingWeekdays: readonly number[];
  holidays: readonly string[];
  dailyIntervals: Readonly<Record<string, readonly (readonly string[])[]>>;
  factors: CalendarFactorSet;
};

export type CalendarSnapshotPayload = {
  contractVersion: string;
  calendar: WorkspaceCalendarRecord;
  snapshot: CalendarSnapshot;
};

export type CalendarException = {
  calendarId: string;
  calendarVersion: string;
  date: string;
  mode: string;
  system: string;
  totalWorkHours: string | null;
  intervals: readonly (readonly string[])[];
  recordRevision: number;
};

export type CalendarPageOptions = {
  transport: ApiTransport;
  context: ProjectContext;
  locale: string;
  catalog: WorkspaceCalendarCatalog;
};

const WEEKDAYS: readonly { index: number; en: string; fa: string }[] = [
  { index: 0, en: "Monday", fa: "دوشنبه" },
  { index: 1, en: "Tuesday", fa: "سه‌شنبه" },
  { index: 2, en: "Wednesday", fa: "چهارشنبه" },
  { index: 3, en: "Thursday", fa: "پنجشنبه" },
  { index: 4, en: "Friday", fa: "جمعه" },
  { index: 5, en: "Saturday", fa: "شنبه" },
  { index: 6, en: "Sunday", fa: "یکشنبه" },
];

const EXCEPTION_MODE_LABELS: readonly { value: string; en: string; fa: string }[] = [
  { value: "nonwork", en: "Non-working day", fa: "روز غیرکاری" },
  { value: "total-work-hours", en: "Total working hours", fa: "مجموع ساعات کاری" },
  { value: "detailed-work-hours", en: "Detailed working hours", fa: "ساعات کاری تفصیلی" },
  { value: "reset-standard", en: "Reset to standard", fa: "بازگشت به استاندارد" },
];

const CALENDAR_TYPES = ["global", "project", "resource"] as const;

const SHIFT_PATTERN = /^([01]\d|2[0-3]):([0-5]\d)-([01]\d|2[0-3]):([0-5]\d)$/;

/**
 * Parses a comma-separated split-shift list such as "08:00-12:00, 13:00-17:00".
 * Returns null for malformed, overlapping or empty shifts so the caller can
 * refuse the write instead of storing a workweek the resolver would reject.
 */
export function parseWorkdayShifts(value: string): readonly (readonly string[])[] | null {
  const parts = value.split(",").map((part) => part.trim()).filter(Boolean);
  if (!parts.length) return null;
  const intervals: string[][] = [];
  for (const part of parts) {
    const match = SHIFT_PATTERN.exec(part);
    if (!match) return null;
    const start = `${match[1]}:${match[2]}`;
    const end = `${match[3]}:${match[4]}`;
    if (start >= end) return null;
    intervals.push([start, end]);
  }
  const ordered = [...intervals].sort((left, right) => (left[0] < right[0] ? -1 : left[0] > right[0] ? 1 : 0));
  for (let index = 1; index < ordered.length; index += 1) {
    if (ordered[index][0] < ordered[index - 1][1]) return null;
  }
  return intervals;
}

function clockText(value: string): string {
  // Snapshots serialize times with seconds; the editor and the API contract
  // use HH:MM, so the display is normalized instead of rejected.
  return value.slice(0, 5);
}

export function formatWorkdayShifts(intervals: readonly (readonly string[])[]): string {
  return intervals.map((pair) => `${clockText(pair[0])}-${clockText(pair[1])}`).join(", ");
}

function shiftHours(intervals: readonly (readonly string[])[]): string {
  let minutes = 0;
  for (const pair of intervals) {
    const [startHour, startMinute] = clockText(pair[0]).split(":").map(Number);
    const [endHour, endMinute] = clockText(pair[1]).split(":").map(Number);
    minutes += (endHour * 60 + endMinute) - (startHour * 60 + startMinute);
  }
  return (minutes / 60).toFixed(2).replace(/\.?0+$/, "");
}

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

function escapeAttribute(value: string): string {
  return escapeHtml(value);
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

function calendarPath(context: ProjectContext, calendarId?: string, calendarVersion?: string, suffix?: string): string {
  const base = `/api/projects/${encodeURIComponent(context.project_id)}/p6/calendars`;
  if (!calendarId || !calendarVersion) return base;
  const reference = `${base}/${encodeURIComponent(calendarId)}/${encodeURIComponent(calendarVersion)}`;
  return suffix ? `${reference}/${suffix}` : reference;
}

function stringOrNull(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function parseFactors(value: unknown): CalendarFactorSet {
  if (!isRecord(value)) {
    return { hours_per_day: null, hours_per_week: null, hours_per_month: null, hours_per_year: null };
  }
  return {
    hours_per_day: stringOrNull(value.hours_per_day),
    hours_per_week: stringOrNull(value.hours_per_week),
    hours_per_month: stringOrNull(value.hours_per_month),
    hours_per_year: stringOrNull(value.hours_per_year),
  };
}

function parseSnapshotPayload(payload: unknown, calendarId: string, calendarVersion: string): CalendarSnapshotPayload {
  if (!isRecord(payload) || payload.contract_version !== CALENDAR_CATALOG_CONTRACT || payload.kind !== "calendar_snapshot") {
    throw new Error("INVALID_CALENDAR_SNAPSHOT");
  }
  const calendar = parseCalendarRecord(payload.calendar);
  if (calendar.calendarId !== calendarId || calendar.calendarVersion !== calendarVersion) {
    throw new Error("CALENDAR_REFERENCE_MISMATCH");
  }
  if (!isRecord(payload.snapshot)) throw new Error("INVALID_CALENDAR_SNAPSHOT");
  const snapshot = payload.snapshot;
  const kind = snapshot.kind === "working-time" ? "working-time" : snapshot.kind === "working-day" || snapshot.kind === undefined ? "working-day" : null;
  if (kind === null) throw new Error("INVALID_CALENDAR_SNAPSHOT");
  const weekdays = snapshot.working_weekdays;
  if (weekdays !== undefined && (!Array.isArray(weekdays) || weekdays.some((day) => !Number.isInteger(day) || day < 0 || day > 6))) {
    throw new Error("INVALID_CALENDAR_SNAPSHOT");
  }
  const holidays = snapshot.holidays;
  if (holidays !== undefined && (!Array.isArray(holidays) || holidays.some((day) => typeof day !== "string"))) {
    throw new Error("INVALID_CALENDAR_SNAPSHOT");
  }
  const intervals: Record<string, readonly (readonly string[])[]> = {};
  if (snapshot.daily_intervals !== undefined) {
    if (!isRecord(snapshot.daily_intervals)) throw new Error("INVALID_CALENDAR_SNAPSHOT");
    for (const [key, value] of Object.entries(snapshot.daily_intervals)) {
      if (!Array.isArray(value) || value.some((pair) => !Array.isArray(pair) || pair.length !== 2 || pair.some((item) => typeof item !== "string"))) {
        throw new Error("INVALID_CALENDAR_SNAPSHOT");
      }
      intervals[key] = value as readonly (readonly string[])[];
    }
  }
  return {
    contractVersion: CALENDAR_CATALOG_CONTRACT,
    calendar,
    snapshot: {
      kind,
      system: stringOrNull(snapshot.system),
      workingWeekdays: (weekdays as number[] | undefined) ?? [],
      holidays: (holidays as string[] | undefined) ?? [],
      dailyIntervals: intervals,
      factors: parseFactors(snapshot.time_period_factors),
    },
  };
}

function parseCalendarRecord(value: unknown): WorkspaceCalendarRecord {
  if (!isRecord(value)) throw new Error("INVALID_CALENDAR_RECORD");
  const { calendar_id, calendar_version, kind, calendar_type, name, record_revision } = value;
  if (
    typeof calendar_id !== "string" || !calendar_id ||
    typeof calendar_version !== "string" || !calendar_version ||
    typeof kind !== "string" || !kind ||
    typeof calendar_type !== "string" || !calendar_type ||
    typeof name !== "string" ||
    typeof record_revision !== "number" || !Number.isInteger(record_revision) || record_revision < 0
  ) {
    throw new Error("INVALID_CALENDAR_RECORD");
  }
  return {
    calendarId: calendar_id,
    calendarVersion: calendar_version,
    name,
    kind,
    calendarType: calendar_type,
    recordRevision: record_revision,
    ...(typeof value.base_calendar_id === "string" ? { baseCalendarId: value.base_calendar_id } : {}),
    ...(typeof value.base_calendar_version === "string" ? { baseCalendarVersion: value.base_calendar_version } : {}),
  };
}

export async function loadCalendarSnapshot(
  transport: ApiTransport,
  context: ProjectContext,
  calendarId: string,
  calendarVersion: string,
): Promise<ApiResult<CalendarSnapshotPayload>> {
  if (!calendarId || !calendarVersion) return localError("CALENDAR_REFERENCE_REQUIRED");
  const result = await transport.get<unknown>(calendarPath(context, calendarId, calendarVersion, "snapshot"), context);
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseSnapshotPayload(result.data, calendarId, calendarVersion) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_CALENDAR_SNAPSHOT");
  }
}

export async function loadCalendarCatalogue(
  transport: ApiTransport,
  context: ProjectContext,
): Promise<ApiResult<readonly WorkspaceCalendarRecord[]>> {
  const result = await transport.get<unknown>(calendarPath(context), context);
  if (!result.ok) return result;
  const payload = result.data;
  if (!isRecord(payload) || payload.contract_version !== CALENDAR_CATALOG_CONTRACT || payload.kind !== "calendar_catalog" || !Array.isArray(payload.calendars)) {
    return localError("INVALID_CALENDAR_CATALOG");
  }
  try {
    return { ok: true, data: payload.calendars.map((item) => parseCalendarRecord(item)) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_CALENDAR_CATALOG");
  }
}

export async function loadCalendarExceptions(
  transport: ApiTransport,
  context: ProjectContext,
  calendarId: string,
  calendarVersion: string,
): Promise<ApiResult<readonly CalendarException[]>> {
  if (!calendarId || !calendarVersion) return localError("CALENDAR_REFERENCE_REQUIRED");
  const result = await transport.get<unknown>(calendarPath(context, calendarId, calendarVersion, "exceptions"), context);
  if (!result.ok) return result;
  const payload = result.data;
  if (!isRecord(payload) || !Array.isArray(payload.exceptions)) return localError("INVALID_CALENDAR_EXCEPTIONS");
  try {
    const exceptions = payload.exceptions.map((item): CalendarException => {
      if (!isRecord(item) || typeof item.date !== "string" || typeof item.mode !== "string") throw new Error("INVALID_CALENDAR_EXCEPTIONS");
      const intervals = Array.isArray(item.intervals)
        ? item.intervals.map((pair) => {
            if (!Array.isArray(pair) || pair.length !== 2 || pair.some((value) => typeof value !== "string")) {
              throw new Error("INVALID_CALENDAR_EXCEPTIONS");
            }
            return pair as string[];
          })
        : [];
      return {
        calendarId: typeof item.calendar_id === "string" ? item.calendar_id : calendarId,
        calendarVersion: typeof item.calendar_version === "string" ? item.calendar_version : calendarVersion,
        date: item.date,
        mode: item.mode,
        system: typeof item.system === "string" ? item.system : "gregorian",
        totalWorkHours: typeof item.total_work_hours === "string" ? item.total_work_hours : null,
        intervals,
        recordRevision: Number.isInteger(item.record_revision) && Number(item.record_revision) >= 1
          ? Number(item.record_revision)
          : 1,
      };
    });
    return { ok: true, data: exceptions };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_CALENDAR_EXCEPTIONS");
  }
}

export type CalendarUsageEntry = {
  kind: string;
  referenceId: string;
  details: Record<string, unknown>;
};

export type CalendarUsage = {
  calendarId: string;
  calendarVersion: string;
  total: number;
  counts: Record<string, number>;
  usages: readonly CalendarUsageEntry[];
};

export function parseCalendarUsage(payload: unknown, calendarId: string, calendarVersion: string): CalendarUsage {
  if (!isRecord(payload) || payload.contract_version !== CALENDAR_USAGE_CONTRACT || payload.kind !== "calendar_usage") {
    throw new Error("INVALID_CALENDAR_USAGE");
  }
  const calendar = payload.calendar;
  if (!isRecord(calendar) || calendar.calendar_id !== calendarId || calendar.calendar_version !== calendarVersion) {
    throw new Error("INVALID_CALENDAR_USAGE");
  }
  if (!Array.isArray(payload.usages) || !Number.isInteger(payload.total) || payload.total !== payload.usages.length) {
    throw new Error("INVALID_CALENDAR_USAGE");
  }
  if (!isRecord(payload.counts)) throw new Error("INVALID_CALENDAR_USAGE");
  const usages = payload.usages.map((item): CalendarUsageEntry => {
    if (!isRecord(item) || typeof item.kind !== "string" || !item.kind || typeof item.reference_id !== "string" || !item.reference_id) {
      throw new Error("INVALID_CALENDAR_USAGE");
    }
    const details = isRecord(item.details) ? item.details : {};
    return { kind: item.kind, referenceId: item.reference_id, details };
  });
  const counts: Record<string, number> = {};
  for (const [kind, value] of Object.entries(payload.counts)) {
    if (!Number.isInteger(value) || Number(value) < 0) throw new Error("INVALID_CALENDAR_USAGE");
    counts[kind] = Number(value);
  }
  return {
    calendarId,
    calendarVersion,
    total: Number(payload.total),
    counts,
    usages,
  };
}

export async function loadCalendarUsage(
  transport: ApiTransport,
  context: ProjectContext,
  calendarId: string,
  calendarVersion: string,
): Promise<ApiResult<CalendarUsage>> {
  if (!calendarId || !calendarVersion) return localError("CALENDAR_REFERENCE_REQUIRED");
  const result = await transport.get<unknown>(calendarPath(context, calendarId, calendarVersion, "uses"), context);
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseCalendarUsage(result.data, calendarId, calendarVersion) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_CALENDAR_USAGE");
  }
}

export type CalendarUpdateInput = {
  name: string;
  calendarType: string;
};

export async function updateCalendar(
  transport: ApiTransport,
  context: ProjectContext,
  calendar: WorkspaceCalendarRecord,
  input: CalendarUpdateInput,
): Promise<ApiResult<WorkspaceCalendarRecord>> {
  if (!input.name.trim()) return localError("CALENDAR_NAME_REQUIRED");
  if (!CALENDAR_TYPES.includes(input.calendarType as (typeof CALENDAR_TYPES)[number])) return localError("INVALID_CALENDAR_TYPE");
  const request = {
    contract_version: CALENDAR_API_CONTRACT,
    calendar_id: calendar.calendarId,
    calendar_version: calendar.calendarVersion,
    calendar_type: input.calendarType,
    kind: calendar.kind,
    name: input.name.trim(),
    expected_revision: calendar.recordRevision,
    base_calendar_id: calendar.baseCalendarId ?? null,
    base_calendar_version: calendar.baseCalendarVersion ?? null,
  };
  if (!transport.patch) return localError("CALENDAR_UPDATE_TRANSPORT_UNAVAILABLE");
  const result = await transport.patch<typeof request, unknown>(
    calendarPath(context, calendar.calendarId, calendar.calendarVersion),
    request,
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseCalendarRecord(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_CALENDAR_RECORD");
  }
}

export async function deleteCalendar(
  transport: ApiTransport,
  context: ProjectContext,
  calendar: WorkspaceCalendarRecord,
): Promise<ApiResult<{ deleted: boolean }>> {
  if (!transport.delete) return localError("CALENDAR_DELETE_TRANSPORT_UNAVAILABLE");
  const result = await transport.delete<{ expected_revision: number }, unknown>(
    calendarPath(context, calendar.calendarId, calendar.calendarVersion),
    { expected_revision: calendar.recordRevision },
    context,
  );
  if (!result.ok) return result;
  if (!isRecord(result.data) || result.data.deleted !== true) return localError("INVALID_CALENDAR_DELETE_RESPONSE");
  return { ok: true, data: { deleted: true } };
}

export async function copyCalendar(
  transport: ApiTransport,
  context: ProjectContext,
  source: WorkspaceCalendarRecord,
  targetId: string,
  targetVersion: string,
): Promise<ApiResult<WorkspaceCalendarRecord>> {
  if (!targetId.trim() || !targetVersion.trim()) return localError("CALENDAR_TARGET_REQUIRED");
  if (targetId.trim() === source.calendarId && targetVersion.trim() === source.calendarVersion) {
    return localError("CALENDAR_TARGET_ALREADY_SELECTED");
  }
  const result = await transport.post<Record<string, string>, unknown>(
    calendarPath(context, source.calendarId, source.calendarVersion, "copy"),
    { target_calendar_id: targetId.trim(), target_calendar_version: targetVersion.trim() },
    context,
    crypto.randomUUID(),
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseCalendarRecord(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_CALENDAR_RECORD");
  }
}

export type CalendarWorkHourKind =
  | "standard_work_week"
  | "standard_detailed_work_hours"
  | "detailed_work_hours"
  | "total_work_hours";

const WORK_HOUR_KINDS: readonly CalendarWorkHourKind[] = [
  "standard_work_week",
  "standard_detailed_work_hours",
  "detailed_work_hours",
  "total_work_hours",
];

export type CalendarWorkHourRule = {
  kind: CalendarWorkHourKind;
  weekday: number | null;
  isWorkingDay: boolean | null;
  totalWorkHours: string | null;
  intervals: readonly (readonly string[])[];
};

export type CalendarCreateInput = {
  calendarId: string;
  calendarVersion: string;
  calendarType: string;
  kind: string;
  name: string;
  baseCalendarId: string;
  baseCalendarVersion: string;
  system: "gregorian" | "jalali";
};

function parseWorkHourRule(value: unknown): CalendarWorkHourRule {
  if (!isRecord(value) || typeof value.kind !== "string" || !WORK_HOUR_KINDS.includes(value.kind as CalendarWorkHourKind)) {
    throw new Error("INVALID_CALENDAR_WORK_HOURS");
  }
  const weekday = value.weekday;
  if (weekday !== null && weekday !== undefined && (!Number.isInteger(weekday) || (weekday as number) < 0 || (weekday as number) > 6)) {
    throw new Error("INVALID_CALENDAR_WORK_HOURS");
  }
  if (value.is_working_day !== null && value.is_working_day !== undefined && typeof value.is_working_day !== "boolean") {
    throw new Error("INVALID_CALENDAR_WORK_HOURS");
  }
  if (value.total_work_hours !== null && value.total_work_hours !== undefined && typeof value.total_work_hours !== "string") {
    throw new Error("INVALID_CALENDAR_WORK_HOURS");
  }
  const intervals = Array.isArray(value.intervals)
    ? value.intervals.map((pair) => {
        if (!Array.isArray(pair) || pair.length !== 2 || pair.some((item) => typeof item !== "string")) {
          throw new Error("INVALID_CALENDAR_WORK_HOURS");
        }
        return pair as string[];
      })
    : [];
  return {
    kind: value.kind as CalendarWorkHourKind,
    weekday: weekday === undefined ? null : (weekday as number | null),
    isWorkingDay: value.is_working_day === undefined ? null : (value.is_working_day as boolean | null),
    totalWorkHours: value.total_work_hours === undefined ? null : (value.total_work_hours as string | null),
    intervals,
  };
}

export async function loadCalendarWorkHours(
  transport: ApiTransport,
  context: ProjectContext,
  calendarId: string,
  calendarVersion: string,
): Promise<ApiResult<readonly CalendarWorkHourRule[]>> {
  if (!calendarId || !calendarVersion) return localError("CALENDAR_REFERENCE_REQUIRED");
  const result = await transport.get<unknown>(calendarPath(context, calendarId, calendarVersion, "work-hours"), context);
  if (!result.ok) return result;
  const payload = result.data;
  if (!isRecord(payload) || !Array.isArray(payload.work_hours)) return localError("INVALID_CALENDAR_WORK_HOURS");
  try {
    return { ok: true, data: payload.work_hours.map((item) => parseWorkHourRule(item)) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_CALENDAR_WORK_HOURS");
  }
}

export async function saveCalendarWorkHourRule(
  transport: ApiTransport,
  context: ProjectContext,
  calendar: WorkspaceCalendarRecord,
  rule: CalendarWorkHourRule,
  replace: boolean,
): Promise<ApiResult<CalendarWorkHourRule>> {
  if (!WORK_HOUR_KINDS.includes(rule.kind)) return localError("INVALID_WORK_HOUR_KIND");
  if (rule.kind !== "total_work_hours" && rule.weekday === null) return localError("WEEKDAY_REQUIRED");
  const request: Record<string, unknown> = {
    kind: rule.kind,
    weekday: rule.weekday,
    is_working_day: rule.isWorkingDay,
    total_work_hours: rule.totalWorkHours,
    intervals: rule.intervals,
  };
  if (replace) {
    request.replace = true;
    request.expected_revision = calendar.recordRevision;
  }
  const result = await transport.post<Record<string, unknown>, unknown>(
    calendarPath(context, calendar.calendarId, calendar.calendarVersion, "work-hours"),
    request,
    context,
    crypto.randomUUID(),
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseWorkHourRule(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_CALENDAR_WORK_HOURS");
  }
}

export async function createCalendar(
  transport: ApiTransport,
  context: ProjectContext,
  input: CalendarCreateInput,
): Promise<ApiResult<WorkspaceCalendarRecord>> {
  const id = input.calendarId.trim();
  const version = input.calendarVersion.trim();
  if (!id || !version) return localError("CALENDAR_REFERENCE_REQUIRED");
  if (!input.name.trim()) return localError("CALENDAR_NAME_REQUIRED");
  if (!CALENDAR_TYPES.includes(input.calendarType as (typeof CALENDAR_TYPES)[number])) return localError("INVALID_CALENDAR_TYPE");
  if (input.kind !== "working-day" && input.kind !== "working-time") return localError("INVALID_CALENDAR_KIND");
  if (!input.baseCalendarId || !input.baseCalendarVersion) return localError("CALENDAR_BASE_REQUIRED");
  if (input.system !== "gregorian" && input.system !== "jalali") return localError("INVALID_CALENDAR_SYSTEM");
  const request = {
    contract_version: CALENDAR_API_CONTRACT,
    calendar_id: id,
    calendar_version: version,
    calendar_type: input.calendarType,
    kind: input.kind,
    name: input.name.trim(),
    expected_revision: 0,
    base_calendar_id: input.baseCalendarId,
    base_calendar_version: input.baseCalendarVersion,
    system: input.system,
  };
  const result = await transport.post<typeof request, unknown>(
    calendarPath(context),
    request,
    context,
    crypto.randomUUID(),
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseCalendarRecord(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_CALENDAR_RECORD");
  }
}

export async function deleteCalendarException(
  transport: ApiTransport,
  context: ProjectContext,
  calendar: WorkspaceCalendarRecord,
  exceptionDate: string,
): Promise<ApiResult<{ deleted: boolean }>> {
  if (!isValidCanonicalIsoDate(exceptionDate)) return localError("INVALID_EXCEPTION_DATE");
  if (!transport.delete) return localError("CALENDAR_DELETE_TRANSPORT_UNAVAILABLE");
  const result = await transport.delete<Record<string, never>, unknown>(
    calendarPath(context, calendar.calendarId, calendar.calendarVersion, `exceptions/${encodeURIComponent(exceptionDate)}`),
    {},
    context,
  );
  if (!result.ok) return result;
  if (!isRecord(result.data) || typeof result.data.deleted !== "boolean") return localError("INVALID_CALENDAR_DELETE_RESPONSE");
  return { ok: true, data: { deleted: result.data.deleted } };
}

export type CalendarExceptionInput = {
  date: string;
  mode: string;
  totalWorkHours: string | null;
  start: string | null;
  end: string | null;
};

export function buildExceptionRequest(
  input: CalendarExceptionInput,
  system: "gregorian" | "jalali",
): Record<string, unknown> | null {
  if (!isValidCanonicalIsoDate(input.date)) return null;
  if (!EXCEPTION_MODE_LABELS.some((item) => item.value === input.mode)) return null;
  let requestDate = input.date;
  if (system === "jalali") {
    const typed = formatJalaliDateInput(input.date).replaceAll("/", "-");
    if (!parseJalaliDateInput(typed)) return null;
    requestDate = typed;
  }
  if (input.mode === "nonwork" || input.mode === "reset-standard") {
    return { date: requestDate, mode: input.mode, system, total_work_hours: null, intervals: [] };
  }
  if (input.mode === "total-work-hours") {
    if (!input.totalWorkHours || !/^\d+(?:\.\d+)?$/.test(input.totalWorkHours)) return null;
    return { date: requestDate, mode: input.mode, system, total_work_hours: input.totalWorkHours, intervals: [] };
  }
  if (!input.start || !input.end || input.start >= input.end) return null;
  return {
    date: requestDate,
    mode: input.mode,
    system,
    total_work_hours: null,
    intervals: [[input.start, input.end]],
  };
}

export async function saveCalendarException(
  transport: ApiTransport,
  context: ProjectContext,
  calendar: WorkspaceCalendarRecord,
  snapshotSystem: string | null,
  input: CalendarExceptionInput,
): Promise<ApiResult<CalendarException>> {
  const system = snapshotSystem === "jalali" ? "jalali" : "gregorian";
  const request = buildExceptionRequest(input, system);
  if (!request) return localError("CALENDAR_EXCEPTION_INVALID");
  const result = await transport.post<Record<string, unknown>, unknown>(
    calendarPath(context, calendar.calendarId, calendar.calendarVersion, "exceptions"),
    request,
    context,
    crypto.randomUUID(),
  );
  if (!result.ok) return result;
  const payload = result.data;
  if (!isRecord(payload)) return localError("INVALID_CALENDAR_EXCEPTION_RESPONSE");
  return {
    ok: true,
    data: {
      calendarId: calendar.calendarId,
      calendarVersion: calendar.calendarVersion,
      date: typeof payload.date === "string" ? payload.date : input.date,
      mode: typeof payload.mode === "string" ? payload.mode : input.mode,
      system: typeof payload.system === "string" ? payload.system : system,
      totalWorkHours: typeof payload.total_work_hours === "string" ? payload.total_work_hours : null,
      intervals: Array.isArray(payload.intervals)
        ? payload.intervals.filter((pair): pair is string[] => Array.isArray(pair) && pair.every((item) => typeof item === "string")).map((pair) => pair as string[])
        : [],
      recordRevision: Number.isInteger(payload.record_revision) && Number(payload.record_revision) >= 1
        ? Number(payload.record_revision)
        : 1,
    },
  };
}

export async function reviseCalendarException(
  transport: ApiTransport,
  context: ProjectContext,
  calendar: WorkspaceCalendarRecord,
  exception: CalendarException,
  input: CalendarExceptionInput,
): Promise<ApiResult<CalendarException>> {
  if (!transport.put) return localError("CALENDAR_UPDATE_TRANSPORT_UNAVAILABLE");
  if (exception.recordRevision < 1) return localError("EXCEPTION_REVISION_REQUIRED");
  const system = exception.system === "jalali" ? "jalali" : "gregorian";
  const request = buildExceptionRequest({ ...input, date: exception.date }, system);
  if (!request) return localError("CALENDAR_EXCEPTION_INVALID");
  const result = await transport.put<Record<string, unknown>, unknown>(
    calendarPath(context, calendar.calendarId, calendar.calendarVersion, `exceptions/${encodeURIComponent(exception.date)}`),
    {
      contract_version: CALENDAR_API_CONTRACT,
      mode: request.mode,
      total_work_hours: request.total_work_hours,
      intervals: request.intervals,
      expected_revision: exception.recordRevision,
    },
    context,
  );
  if (!result.ok) return result;
  const payload = result.data;
  if (!isRecord(payload) || !Number.isInteger(payload.record_revision)) return localError("INVALID_CALENDAR_EXCEPTION_RESPONSE");
  return {
    ok: true,
    data: {
      calendarId: calendar.calendarId,
      calendarVersion: calendar.calendarVersion,
      date: typeof payload.date === "string" ? payload.date : exception.date,
      mode: typeof payload.mode === "string" ? payload.mode : input.mode,
      system: typeof payload.system === "string" ? payload.system : system,
      totalWorkHours: typeof payload.total_work_hours === "string" ? payload.total_work_hours : null,
      intervals: Array.isArray(payload.intervals)
        ? payload.intervals.filter((pair): pair is string[] => Array.isArray(pair) && pair.every((item) => typeof item === "string")).map((pair) => pair as string[])
        : [],
      recordRevision: Number(payload.record_revision),
    },
  };
}

type PageState = {
  catalog: readonly WorkspaceCalendarRecord[];
  catalogStatus: WorkspaceCalendarCatalog["status"] | "error";
  catalogError: string | null;
  selected: { id: string; version: string } | null;
  snapshot: CalendarSnapshot | null;
  snapshotError: string | null;
  snapshotLoading: boolean;
  exceptions: readonly CalendarException[];
  exceptionsError: string | null;
  editingException: CalendarException | null;
  workHours: readonly CalendarWorkHourRule[];
  workHoursError: string | null;
  workHoursLoading: boolean;
  usage: CalendarUsage | null;
  usageError: string | null;
  usageLoading: boolean;
  tab: "general" | "workweek" | "exceptions" | "usage";
  dialog: "none" | "copy" | "delete" | "new";
  busy: boolean;
  notice: { kind: "ok" | "error"; message: string } | null;
  draftName: string | null;
  draftType: string | null;
};

function selectedRecord(state: PageState): WorkspaceCalendarRecord | null {
  if (!state.selected) return null;
  return state.catalog.find((item) => item.calendarId === state.selected?.id && item.calendarVersion === state.selected?.version) ?? null;
}

export function mountWorkspaceCalendarPage(host: HTMLElement, options: CalendarPageOptions): void {
  if (host.dataset.calendarMounted === "true") return;
  host.dataset.calendarMounted = "true";
  const { transport, context, locale, catalog } = options;
  const state: PageState = {
    catalog: catalog.calendars,
    catalogStatus: catalog.status,
    catalogError: catalog.errorCode,
    selected: null,
    snapshot: null,
    snapshotError: null,
    snapshotLoading: false,
    exceptions: [],
    exceptionsError: null,
    editingException: null,
    workHours: [],
    workHoursError: null,
    workHoursLoading: false,
    usage: null,
    usageError: null,
    usageLoading: false,
    tab: "general",
    dialog: "none",
    busy: false,
    notice: null,
    draftName: null,
    draftType: null,
  };

  const say = (en: string, fa: string): string => text(locale, en, fa);

  function renderCatalogue(): string {
    if (state.catalogStatus === "unavailable" || state.catalogStatus === "error") {
      return `<div class="cp-calendar-empty" role="status">${escapeHtml(say("Calendar catalogue unavailable", "فهرست تقویم‌ها در دسترس نیست"))} (${escapeHtml(state.catalogError ?? "unknown")})</div>`;
    }
    if (state.catalogStatus !== "loaded") {
      return `<div class="cp-calendar-empty">${escapeHtml(say("Calendar catalogue has not been loaded.", "فهرست تقویم‌ها هنوز بارگذاری نشده است."))}</div>`;
    }
    if (!state.catalog.length) {
      return `<div class="cp-calendar-empty">${escapeHtml(say("No calendar records exist for this project.", "برای این پروژه رکورد تقویمی وجود ندارد."))}</div>`;
    }
    const heads = [
      say("Calendar", "تقویم"),
      say("Type", "نوع"),
      say("Version", "نسخه"),
      say("Revision", "ویرایش"),
    ].map((label) => `<th>${escapeHtml(label)}</th>`).join("");
    const rows = state.catalog.map((calendar) => {
      const active = state.selected?.id === calendar.calendarId && state.selected?.version === calendar.calendarVersion;
      return `<tr data-calendar-row data-calendar-id="${escapeHtml(calendar.calendarId)}" data-calendar-version="${escapeHtml(calendar.calendarVersion)}" tabindex="0" role="button" aria-selected="${active}" class="${active ? "is-selected" : ""}"><td><strong>${escapeHtml(calendar.calendarId)}</strong><br><span>${escapeHtml(calendar.name)}</span></td><td>${escapeHtml(calendar.calendarType)}</td><td>${escapeHtml(calendar.calendarVersion)}</td><td>${calendar.recordRevision}</td></tr>`;
    }).join("");
    return `<div class="cp-register-table-wrap"><table><thead><tr>${heads}</tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function renderGeneral(record: WorkspaceCalendarRecord): string {
    const snapshot = state.snapshot;
    const editable = state.draftName !== null;
    const name = state.draftName ?? record.name;
    const type = state.draftType ?? record.calendarType;
    const factor = (value: string | null): string => value ?? say("Not provided", "ارائه نشده");
    return `<section class="cp-calendar-editor-panel" data-calendar-panel="general">
      <div class="cp-calendar-fields">
        <label>${escapeHtml(say("Calendar Name", "نام تقویم"))}<input data-calendar-name value="${escapeHtml(name)}" ${editable ? "" : "readonly"}></label>
        <label>${escapeHtml(say("Calendar Type", "نوع تقویم"))}<select data-calendar-type ${editable ? "" : "disabled"}>${CALENDAR_TYPES.map((value) => `<option value="${value}" ${value === type ? "selected" : ""}>${value}</option>`).join("")}</select></label>
        <label>${escapeHtml(say("Calendar ID", "شناسه تقویم"))}<input readonly value="${escapeHtml(record.calendarId)}"></label>
        <label>${escapeHtml(say("Version", "نسخه"))}<input readonly value="${escapeHtml(record.calendarVersion)}"></label>
        <label>${escapeHtml(say("Calendar Kind", "ماهیت تقویم"))}<input readonly value="${escapeHtml(record.kind)}"></label>
        <label>${escapeHtml(say("Record Revision", "ویرایش رکورد"))}<input readonly value="${record.recordRevision}"></label>
        <label>${escapeHtml(say("Date System", "مبنای تاریخ"))}<input readonly value="${escapeHtml(snapshot?.system ?? say("Not provided", "ارائه نشده"))}"></label>
        <label>${escapeHtml(say("Hours per Day", "ساعت در روز"))}<input readonly value="${escapeHtml(factor(snapshot?.factors.hours_per_day ?? null))}"></label>
        <label>${escapeHtml(say("Hours per Week", "ساعت در هفته"))}<input readonly value="${escapeHtml(factor(snapshot?.factors.hours_per_week ?? null))}"></label>
        <label>${escapeHtml(say("Hours per Month", "ساعت در ماه"))}<input readonly value="${escapeHtml(factor(snapshot?.factors.hours_per_month ?? null))}"></label>
        <label>${escapeHtml(say("Hours per Year", "ساعت در سال"))}<input readonly value="${escapeHtml(factor(snapshot?.factors.hours_per_year ?? null))}"></label>
      </div>
      <div class="cp-calendar-panel-actions">
        ${editable
          ? `<button type="button" data-calendar-action="save" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Save changes", "ذخیره تغییرات"))}</button><button type="button" data-calendar-action="cancel-edit">${escapeHtml(say("Cancel", "لغو"))}</button>`
          : `<button type="button" data-calendar-action="edit">${escapeHtml(say("Edit calendar", "ویرایش تقویم"))}</button>`}
      </div>
    </section>`;
  }

  function renderWorkweek(record: WorkspaceCalendarRecord): string {
    const snapshot = state.snapshot;
    if (!snapshot) {
      return `<div class="cp-calendar-empty">${escapeHtml(say("Select a calendar to read its working time.", "برای خواندن ساعات کاری، یک تقویم انتخاب کنید."))}</div>`;
    }
    if (state.workHoursError) {
      return `<div class="cp-calendar-empty" role="alert">${escapeHtml(say("Calendar work hours could not be read", "خواندن ساعات کاری تقویم ناموفق بود"))} (${escapeHtml(state.workHoursError)})</div>`;
    }
    const showShifts = record.kind === "working-time";
    const standardFor = (weekday: number) => state.workHours.find((item) => item.kind === "standard_work_week" && item.weekday === weekday) ?? null;
    const detailedFor = (weekday: number) => state.workHours.find((item) => item.kind === "standard_detailed_work_hours" && item.weekday === weekday) ?? null;
    const rows = WEEKDAYS.map((day) => {
      const standard = standardFor(day.index);
      const detailed = detailedFor(day.index);
      const working = standard?.isWorkingDay ?? snapshot.workingWeekdays.includes(day.index);
      const intervals = detailed?.intervals.length ? detailed.intervals : snapshot.dailyIntervals[String(day.index)] ?? [];
      const hours = standard?.totalWorkHours ?? snapshot.factors.hours_per_day ?? "";
      return `<tr data-calendar-workday="${day.index}">
        <th>${escapeHtml(say(day.en, day.fa))}</th>
        <td><input type="checkbox" data-workday-working ${working ? "checked" : ""} aria-label="${escapeAttribute(`${say(day.en, day.fa)} ${say("working day", "روز کاری")}`)}"></td>
        <td><input type="text" inputmode="decimal" data-workday-hours value="${escapeAttribute(hours)}" ${showShifts ? "" : "readonly"} title="${escapeAttribute(showShifts ? say("Hours derived from the shift ranges are stored with the day.", "ساعت از بازه‌های شیفت محاسبه و با روز ذخیره می‌شود.") : say("A working-day calendar uses one hours-per-day factor; only the working-day flag is stored per weekday.", "تقویم روزکاری یک ضریب ساعت در روز دارد؛ برای هر روز فقط وضعیت کاری ذخیره می‌شود."))}" aria-label="${escapeAttribute(`${say(day.en, day.fa)} ${say("hours", "ساعت")}`)}"></td>
        ${showShifts ? `<td><input type="text" data-workday-shifts value="${escapeAttribute(formatWorkdayShifts(intervals))}" placeholder="08:00-12:00, 13:00-17:00" aria-label="${escapeAttribute(`${say(day.en, day.fa)} ${say("shifts", "بازه‌های کاری")}`)}"></td>` : ""}
        <td><button type="button" data-workday-save="${day.index}">${escapeHtml(say("Save day", "ذخیره روز"))}</button></td>
      </tr>`;
    }).join("");
    const holidays = snapshot.holidays.length
      ? `<ul class="cp-calendar-holiday-list">${snapshot.holidays.map((day) => `<li><span class="cp-calendar-holiday-date">${escapeHtml(day)}</span></li>`).join("")}</ul>`
      : `<p class="cp-calendar-hint">${escapeHtml(say("No non-working days are stored in this calendar snapshot.", "هیچ روز غیرکاری در این نسخه تقویم ذخیره نشده است."))}</p>`;
    return `<section class="cp-calendar-editor-panel" data-calendar-panel="workweek">
      <div class="cp-calendar-table-wrap"><table class="cp-calendar-workweek"><thead><tr><th>${escapeHtml(say("Day", "روز"))}</th><th>${escapeHtml(say("Working Day", "روز کاری"))}</th><th>${escapeHtml(say("Hours per Day", "ساعت در روز"))}</th>${showShifts ? `<th>${escapeHtml(say("Shifts", "بازه‌های کاری"))}</th>` : ""}<th>${escapeHtml(say("Action", "اقدام"))}</th></tr></thead><tbody>${rows}</tbody></table></div>
      <div class="cp-calendar-section-head"><strong>${escapeHtml(say("Stored non-working days", "روزهای غیرکاری ذخیره‌شده"))}</strong></div>${holidays}
      <p class="cp-calendar-hint">${escapeHtml(say("Saved days are written as calendar work-hour rules and the calendar revision is increased. Split shifts must not overlap; run the schedule again to use the edited capacity. Stored non-working days come from the calendar snapshot and are changed through Exceptions.", "روزهای ذخیره‌شده به‌صورت قواعد ساعات کاری تقویم نوشته می‌شوند و ویرایش تقویم افزایش می‌یابد. بازه‌های شیفتی نباید هم‌پوشانی داشته باشند؛ برای استفاده از ظرفیت ویرایش‌شده، زمان‌بندی را دوباره اجرا کنید. روزهای غیرکاری از نسخه تقویم خوانده می‌شوند و از طریق استثناها تغییر می‌کنند."))}</p>
    </section>`;
  }

  function exceptionDateLabel(item: CalendarException): string {
    // The stored date is always canonical ISO; a Jalali calendar shows the
    // equivalent Jalali date next to it so entry and display agree.
    return item.system === "jalali" ? formatJalaliDateInput(item.date) : item.date;
  }

  function renderExceptions(record: WorkspaceCalendarRecord): string {
    if (state.exceptionsError) {
      return `<div class="cp-calendar-empty" role="alert">${escapeHtml(say("Calendar exceptions could not be read", "خواندن استثناهای تقویم ناموفق بود"))} (${escapeHtml(state.exceptionsError)})</div>`;
    }
    const edit = state.editingException;
    const rows = state.exceptions.map((item) => {
      const active = edit?.date === item.date;
      return `<li class="${active ? "is-editing" : ""}"><span class="cp-calendar-holiday-date">${escapeHtml(exceptionDateLabel(item))}${item.system === "jalali" ? ` <small>(${escapeHtml(item.date)})</small>` : ""}</span><span class="cp-calendar-holiday-mode">${escapeHtml(item.mode)}${item.totalWorkHours ? ` · ${escapeHtml(item.totalWorkHours)} h` : ""}${item.intervals.length ? ` · ${item.intervals.map((pair) => `${pair[0]}–${pair[1]}`).join(", ")}` : ""} · r${item.recordRevision}</span><button type="button" data-calendar-exception-edit="${escapeAttribute(item.date)}" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Edit", "ویرایش"))}</button><button type="button" data-calendar-exception-delete="${escapeAttribute(item.date)}" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Remove", "حذف"))}</button></li>`;
    }).join("");
    const list = state.exceptions.length
      ? `<ul class="cp-calendar-holiday-list">${rows}</ul>`
      : `<div class="cp-calendar-empty">${escapeHtml(say("No exceptions are stored for this calendar.", "هیچ استثنایی برای این تقویم ذخیره نشده است."))}</div>`;
    const modeOptions = EXCEPTION_MODE_LABELS.map((mode) => `<option value="${mode.value}" ${edit?.mode === mode.value ? "selected" : ""}>${escapeHtml(say(mode.en, mode.fa))}</option>`).join("");
    const detailInterval = edit?.intervals[0] ?? null;
    const jalaliHint = edit && edit.system === "jalali"
      ? `<p class="cp-calendar-hint" data-calendar-exception-jalali>${escapeHtml(say("Jalali date", "تاریخ جلالی"))}: ${escapeHtml(formatJalaliDateInput(edit.date))}</p>`
      : "";
    const jalaliSystem = state.snapshot?.system === "jalali";
    const dateControl = jalaliSystem
      ? `<input type="text" name="date" required inputmode="numeric" placeholder="1405/10/01" value="${escapeAttribute(edit ? formatJalaliDateInput(edit.date) : "")}" ${edit ? "readonly" : ""}>`
      : `<input type="date" name="date" required value="${escapeAttribute(edit?.date ?? "")}" ${edit ? "readonly" : ""}>`;
    return `<section class="cp-calendar-editor-panel" data-calendar-panel="exceptions">
      ${list}
      <form data-calendar-exception-form data-editing="${edit ? "true" : "false"}">
        <label>${escapeHtml(say("Date", "تاریخ"))}${dateControl}</label>
        <label>${escapeHtml(say("Mode", "حالت"))}<select name="mode">${modeOptions}</select></label>
        <label data-calendar-exception-hours ${edit?.mode === "total-work-hours" ? "" : "hidden"}>${escapeHtml(say("Total hours", "مجموع ساعات"))}<input type="number" name="hours" min="0" step="0.25" value="${escapeAttribute(edit?.mode === "total-work-hours" ? edit.totalWorkHours ?? "" : "")}"></label>
        <label data-calendar-exception-interval ${edit?.mode === "detailed-work-hours" ? "" : "hidden"}>${escapeHtml(say("Start", "شروع"))}<input type="time" name="start" value="${escapeAttribute(detailInterval?.[0] ?? "")}"></label>
        <label data-calendar-exception-interval ${edit?.mode === "detailed-work-hours" ? "" : "hidden"}>${escapeHtml(say("Finish", "پایان"))}<input type="time" name="end" value="${escapeAttribute(detailInterval?.[1] ?? "")}"></label>
        <button type="submit" ${state.busy ? "disabled" : ""}>${escapeHtml(edit ? say("Save changes", "ذخیره تغییرات") : say("Add exception", "افزودن استثنا"))}</button>
        ${edit ? `<button type="button" data-calendar-exception-cancel>${escapeHtml(say("Cancel", "لغو"))}</button>` : ""}
      </form>
      ${jalaliHint}
      <p class="cp-calendar-hint">${escapeHtml(say("Exceptions are persisted through the calendar API. Editing keeps the stored date and raises the exception record revision; a saved exception invalidates the previous schedule result, so run the schedule again to see authoritative dates.", "استثناها از طریق API تقویم ذخیره می‌شوند. ویرایش، تاریخ ذخیره‌شده را حفظ و ویرایش رکورد استثنا را افزایش می‌دهد؛ استثنای ذخیره‌شده نتیجه زمان‌بندی قبلی را باطل می‌کند؛ برای مشاهده تاریخ‌های مرجع، زمان‌بندی را دوباره اجرا کنید."))}</p>
      <input type="hidden" data-calendar-exception-calendar value="${escapeHtml(record.calendarId)}">
    </section>`;
  }

  function usageKindLabel(kind: string): string {
    const labels: Record<string, [string, string]> = {
      activity_calendar_assignment: ["Activity", "فعالیت"],
      relationship_lag_calendar_assignment: ["Relationship lag", "تأخیر رابطه"],
      resource_calendar_assignment: ["Resource master", "مستر منبع"],
      resource_assignment_calendar: ["Resource assignment", "تخصیص منبع"],
    };
    const label = labels[kind];
    return label ? say(label[0], label[1]) : kind;
  }

  function renderUsage(): string {
    if (state.usageLoading) {
      return `<div class="cp-calendar-empty" role="status" data-calendar-usage-loading>${escapeHtml(say("Reading stored references to this calendar…", "در حال خواندن ارجاع‌های ذخیره‌شده به این تقویم…"))}</div>`;
    }
    if (state.usageError) {
      return `<div class="cp-calendar-empty" role="alert" data-calendar-usage-error>${escapeHtml(say("Calendar references could not be read", "خواندن ارجاع‌های تقویم ناموفق بود"))} (${escapeHtml(state.usageError)})</div>`;
    }
    const usage = state.usage;
    if (!usage) {
      return `<div class="cp-calendar-empty">${escapeHtml(say("Select a calendar to read its stored references.", "برای خواندن ارجاع‌های ذخیره‌شده، یک تقویم انتخاب کنید."))}</div>`;
    }
    const heads = [say("Used By", "استفاده‌کننده"), say("Reference", "مرجع"), say("Details", "جزئیات")]
      .map((label) => `<th>${escapeHtml(label)}</th>`)
      .join("");
    const rows = usage.usages.map((item) => {
      const detail = Object.entries(item.details)
        .map(([key, value]) => `${key}=${value === null ? "—" : String(value)}`)
        .join(" · ");
      return `<tr data-calendar-usage-row data-usage-kind="${escapeAttribute(item.kind)}" data-usage-reference="${escapeAttribute(item.referenceId)}"><td>${escapeHtml(usageKindLabel(item.kind))}</td><td><code>${escapeHtml(item.referenceId)}</code></td><td>${escapeHtml(detail || "—")}</td></tr>`;
    }).join("");
    const counts = Object.entries(usage.counts)
      .map(([kind, count]) => `${usageKindLabel(kind)} ${count}`)
      .join(" · ");
    const table = usage.usages.length
      ? `<div class="cp-register-table-wrap"><table><thead><tr>${heads}</tr></thead><tbody>${rows}</tbody></table></div>`
      : `<div class="cp-calendar-empty" data-calendar-usage-empty>${escapeHtml(say("No stored activity, resource or assignment reference uses this calendar version yet.", "هنوز هیچ ارجاع ذخیره‌شدهٔ فعالیت، منبع یا تخصیصی از این نسخهٔ تقویم استفاده نمی‌کند."))}</div>`;
    return `<section class="cp-calendar-editor-panel" data-calendar-panel="usage" data-calendar-usage>
      <div class="cp-calendar-section-head"><strong>${escapeHtml(say("Calendar References", "ارجاع‌های تقویم"))}</strong><span data-calendar-usage-total>${usage.total}</span></div>
      ${table}
      <p class="cp-calendar-hint" data-calendar-usage-summary>${escapeHtml(counts || say("No references.", "بدون ارجاع."))}</p>
      <p class="cp-calendar-hint">${escapeHtml(say("A resource master stores a calendar id without a version, so it is matched by id only. Resource assignments store the exact id and version.", "مستر منبع شناسهٔ تقویم را بدون نسخه ذخیره می‌کند، بنابراین فقط با شناسه تطبیق داده می‌شود. تخصیص‌های منبع شناسه و نسخهٔ دقیق را ذخیره می‌کنند."))}</p>
    </section>`;
  }

  function renderDetails(): string {
    const record = selectedRecord(state);
    if (!record) {
      return `<div class="cp-calendar-empty">${escapeHtml(say("Select a calendar from the register to read its persisted definition.", "برای خواندن تعریف ذخیره‌شده، یک تقویم را از فهرست انتخاب کنید."))}</div>`;
    }
    if (state.snapshotLoading) {
      return `<div class="cp-calendar-empty" role="status">${escapeHtml(say("Reading the calendar snapshot…", "در حال خواندن نسخه تقویم…"))}</div>`;
    }
    const tabs = [
      ["general", say("General", "عمومی")],
      ["workweek", say("Workweek", "هفته کاری")],
      ["exceptions", say("Exceptions", "استثناها")],
      ["usage", say("Used By", "استفاده‌کنندگان")],
    ].map(([key, label]) => `<button type="button" role="tab" data-calendar-tab="${key}" aria-selected="${state.tab === key}" class="${state.tab === key ? "is-active" : ""}">${escapeHtml(label)}</button>`).join("");
    const panel = state.tab === "general" ? renderGeneral(record) : state.tab === "workweek" ? renderWorkweek(record) : state.tab === "exceptions" ? renderExceptions(record) : renderUsage();
    const snapshotFailure = state.snapshotError
      ? `<p class="cp-calendar-notice" role="alert">${escapeHtml(say("Calendar snapshot could not be read", "خواندن نسخه تقویم ناموفق بود"))} (${escapeHtml(state.snapshotError)}). ${escapeHtml(say("Dates and durations must not be inferred without it.", "بدون آن، تاریخ و مدت نباید استنتاج شود."))}</p>`
      : "";
    return `${snapshotFailure}<div class="cp-calendar-editor-tabs" role="tablist">${tabs}</div><div class="cp-calendar-editor-content">${panel}</div>`;
  }

  function renderDialog(record: WorkspaceCalendarRecord | null): string {
    if (state.dialog === "new") {
      const bases = state.catalog.map((item) => `<option value="${escapeAttribute(`${item.calendarId}|${item.calendarVersion}`)}">${escapeHtml(`${item.calendarId} @ ${item.calendarVersion} — ${item.kind} (${item.calendarType})`)}</option>`).join("");
      return `<div class="cp-calendar-dialog" role="dialog" aria-label="${escapeHtml(say("New calendar", "تقویم جدید"))}">
        <strong>${escapeHtml(say("Create a calendar from a base", "ایجاد تقویم از یک تقویم پایه"))}</strong>
        <p>${escapeHtml(say("The new calendar receives the base definition, work-hour rules and exceptions in one transaction, so it is usable immediately.", "تقویم جدید تعریف، قواعد ساعات کاری و استثناهای تقویم پایه را در یک تراکنش دریافت می‌کند و بلافاصله قابل استفاده است."))}</p>
        <div class="cp-calendar-fields">
          <label>${escapeHtml(say("Base calendar", "تقویم پایه"))}<select data-calendar-new-base required>${bases}</select></label>
          <label>${escapeHtml(say("Calendar ID", "شناسه تقویم"))}<input data-calendar-new-id required maxlength="80" autocomplete="off"></label>
          <label>${escapeHtml(say("Version", "نسخه"))}<input data-calendar-new-version value="1" required maxlength="40" autocomplete="off"></label>
          <label>${escapeHtml(say("Calendar Name", "نام تقویم"))}<input data-calendar-new-name required maxlength="180" autocomplete="off"></label>
          <label>${escapeHtml(say("Calendar Type", "نوع تقویم"))}<select data-calendar-new-type>${CALENDAR_TYPES.map((value) => `<option value="${value}">${value}</option>`).join("")}</select></label>
          <label>${escapeHtml(say("Date System", "مبنای تاریخ"))}<select data-calendar-new-system><option value="gregorian">gregorian</option><option value="jalali">jalali</option></select></label>
        </div>
        <p>${escapeHtml(say("A Jalali calendar keeps ISO Gregorian dates in storage and uses Jalali values for exception entry and display.", "تقویم جلالی تاریخ‌ها را به‌صورت ISO میلادی ذخیره می‌کند و برای ورود و نمایش استثناها از مقدار جلالی استفاده می‌کند."))}</p>
        <div class="cp-calendar-panel-actions"><button type="button" data-calendar-action="new-submit" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Create calendar", "ایجاد تقویم"))}</button><button type="button" data-calendar-action="dialog-cancel">${escapeHtml(say("Cancel", "لغو"))}</button></div>
      </div>`;
    }
    if (state.dialog === "copy" && record) {
      return `<div class="cp-calendar-dialog" role="dialog" aria-label="${escapeHtml(say("Copy calendar", "کپی تقویم"))}">
        <strong>${escapeHtml(say("Copy calendar definition", "کپی تعریف تقویم"))}</strong>
        <p>${escapeHtml(say("The copy receives the same snapshot, work hours and exceptions with a new reference.", "کپی، همان نسخه، ساعات کاری و استثناها را با شناسه جدید دریافت می‌کند."))}</p>
        <div class="cp-calendar-fields">
          <label>${escapeHtml(say("Target ID", "شناسه مقصد"))}<input data-calendar-target-id required></label>
          <label>${escapeHtml(say("Target version", "نسخه مقصد"))}<input data-calendar-target-version value="1" required></label>
        </div>
        <div class="cp-calendar-panel-actions"><button type="button" data-calendar-action="copy-submit" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Create copy", "ایجاد کپی"))}</button><button type="button" data-calendar-action="dialog-cancel">${escapeHtml(say("Cancel", "لغو"))}</button></div>
      </div>`;
    }
    if (state.dialog === "delete" && record) {
      return `<div class="cp-calendar-dialog" role="alertdialog" aria-label="${escapeHtml(say("Delete calendar", "حذف تقویم"))}">
        <strong>${escapeHtml(say("Delete this calendar?", "این تقویم حذف شود؟"))}</strong>
        <p>${escapeHtml(record.calendarId)} / ${escapeHtml(record.calendarVersion)} — ${escapeHtml(say("The master, snapshot, work hours and exceptions are removed.", "مستر، نسخه، ساعات کاری و استثناها حذف می‌شوند."))}</p>
        <div class="cp-calendar-panel-actions"><button type="button" data-calendar-action="delete-confirm" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Delete", "حذف"))}</button><button type="button" data-calendar-action="dialog-cancel">${escapeHtml(say("Cancel", "لغو"))}</button></div>
      </div>`;
    }
    return "";
  }

  function render(): void {
    const record = selectedRecord(state);
    host.innerHTML = `<div class="cp-calendar-window-toolbar">
        <strong>${escapeHtml(say("Calendar Register", "فهرست تقویم‌ها"))}</strong>
        <div>
          <button type="button" data-calendar-action="new" ${state.catalog.length ? "" : "disabled"} title="${escapeAttribute(say("Create a calendar from a base calendar", "ایجاد تقویم از یک تقویم پایه"))}">${escapeHtml(say("New", "جدید"))}</button>
          <button type="button" data-calendar-action="copy" ${record ? "" : "disabled"}>${escapeHtml(say("Copy", "کپی"))}</button>
          <button type="button" data-calendar-action="delete" ${record ? "" : "disabled"}>${escapeHtml(say("Delete", "حذف"))}</button>
          <button type="button" data-calendar-action="reload" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Refresh", "به‌روزرسانی"))}</button>
        </div>
      </div>
      <div class="cp-calendar-window-layout">
        <section class="cp-calendar-register">
          <div class="cp-calendar-section-head"><strong>${escapeHtml(say("Available Calendars", "تقویم‌های موجود"))}</strong><span>${state.catalog.length}</span></div>
          ${renderCatalogue()}
        </section>
        <section class="cp-calendar-editor">
          <div class="cp-calendar-section-head"><strong>${escapeHtml(say("Calendar Details", "جزئیات تقویم"))}</strong><span>${record ? `${escapeHtml(record.calendarId)} / ${escapeHtml(record.calendarVersion)}` : escapeHtml(say("No selection", "بدون انتخاب"))}</span></div>
          ${renderDetails()}
          ${renderDialog(record)}
          ${state.notice ? `<p class="cp-calendar-notice" data-calendar-notice data-state="${state.notice.kind}" role="status">${escapeHtml(state.notice.message)}</p>` : ""}
        </section>
      </div>`;
  }

  async function selectCalendar(id: string, version: string, tab: PageState["tab"] = "general"): Promise<void> {
    state.selected = { id, version };
    state.snapshot = null;
    state.snapshotError = null;
    state.exceptions = [];
    state.exceptionsError = null;
    state.editingException = null;
    state.workHours = [];
    state.workHoursError = null;
    state.usage = null;
    state.usageError = null;
    state.tab = tab;
    state.dialog = "none";
    state.draftName = null;
    state.draftType = null;
    state.notice = null;
    state.snapshotLoading = true;
    state.workHoursLoading = true;
    state.usageLoading = true;
    render();
    const [snapshotResult, exceptionResult, workHourResult, usageResult] = await Promise.all([
      loadCalendarSnapshot(transport, context, id, version),
      loadCalendarExceptions(transport, context, id, version),
      loadCalendarWorkHours(transport, context, id, version),
      loadCalendarUsage(transport, context, id, version),
    ]);
    if (state.selected?.id !== id || state.selected?.version !== version) return;
    state.snapshotLoading = false;
    state.workHoursLoading = false;
    state.usageLoading = false;
    if (snapshotResult.ok) {
      state.snapshot = snapshotResult.data.snapshot;
    } else {
      state.snapshotError = snapshotResult.error.code;
    }
    if (exceptionResult.ok) {
      state.exceptions = exceptionResult.data;
    } else {
      state.exceptionsError = exceptionResult.error.code;
    }
    if (workHourResult.ok) {
      state.workHours = workHourResult.data;
    } else {
      state.workHoursError = workHourResult.error.code;
    }
    if (usageResult.ok) {
      state.usage = usageResult.data;
    } else {
      state.usageError = usageResult.error.code;
    }
    render();
  }

  async function reloadCatalogue(keepSelection: { id: string; version: string } | null): Promise<void> {
    const result = await loadCalendarCatalogue(transport, context);
    if (result.ok) {
      state.catalog = result.data;
      state.catalogStatus = "loaded";
      state.catalogError = null;
      if (keepSelection && result.data.some((item) => item.calendarId === keepSelection.id && item.calendarVersion === keepSelection.version)) {
        state.selected = keepSelection;
      } else {
        state.selected = null;
        state.snapshot = null;
        state.exceptions = [];
        state.workHours = [];
        state.tab = "general";
      }
    } else {
      state.catalogStatus = result.error.code === "CALENDAR_CATALOG_UNAVAILABLE" ? "unavailable" : "error";
      state.catalogError = result.error.code;
    }
    render();
  }

  function findExceptionFields(form: HTMLFormElement) {
    return {
      date: form.querySelector<HTMLInputElement>("[name=date]"),
      mode: form.querySelector<HTMLSelectElement>("[name=mode]"),
      hours: form.querySelector<HTMLInputElement>("[name=hours]"),
      start: form.querySelector<HTMLInputElement>("[name=start]"),
      end: form.querySelector<HTMLInputElement>("[name=end]"),
    };
  }

  async function saveWorkday(record: WorkspaceCalendarRecord, weekday: number): Promise<void> {
    const row = host.querySelector<HTMLElement>(`[data-calendar-workday="${weekday}"]`);
    if (!row) return;
    const working = row.querySelector<HTMLInputElement>("[data-workday-working]")?.checked ?? false;
    const hoursText = record.kind === "working-time"
      ? (row.querySelector<HTMLInputElement>("[data-workday-hours]")?.value ?? "").trim()
      : "";
    if (hoursText && !/^\d+(?:\.\d+)?$/.test(hoursText)) {
      state.notice = { kind: "error", message: say("Hours must be a non-negative number.", "ساعت باید عددی نامنفی باشد.") };
      render();
      return;
    }
    let intervals: readonly (readonly string[])[] = [];
    let hours = hoursText;
    if (record.kind === "working-time" && working) {
      const parsed = parseWorkdayShifts(row.querySelector<HTMLInputElement>("[data-workday-shifts]")?.value ?? "");
      if (!parsed) {
        state.notice = { kind: "error", message: say("Shifts must be non-overlapping HH:MM-HH:MM ranges.", "بازه‌ها باید به شکل HH:MM-HH:MM و بدون هم‌پوشانی باشند.") };
        render();
        return;
      }
      intervals = parsed;
      hours = shiftHours(parsed);
    }
    if (!working) hours = "";
    let revision = record.recordRevision;
    const standardExists = state.workHours.some((item) => item.kind === "standard_work_week" && item.weekday === weekday);
    state.busy = true;
    render();
    const standard: CalendarWorkHourRule = {
      kind: "standard_work_week", weekday, isWorkingDay: working,
      totalWorkHours: hours || null, intervals: [],
    };
    let result = await saveCalendarWorkHourRule(transport, context, record, standard, standardExists);
    if (result.ok && standardExists) revision += 1;
    if (result.ok && record.kind === "working-time" && working) {
      const detailedExists = state.workHours.some((item) => item.kind === "standard_detailed_work_hours" && item.weekday === weekday);
      const detailed: CalendarWorkHourRule = {
        kind: "standard_detailed_work_hours", weekday, isWorkingDay: working,
        totalWorkHours: null, intervals,
      };
      result = await saveCalendarWorkHourRule(transport, context, { ...record, recordRevision: revision }, detailed, detailedExists);
      if (result.ok && detailedExists) revision += 1;
    }
    state.busy = false;
    if (!result.ok) {
      state.notice = { kind: "error", message: `${say("Workday was not saved", "روز کاری ذخیره نشد")} (${result.error.code})` };
      render();
      return;
    }
    await reloadCatalogue({ id: record.calendarId, version: record.calendarVersion });
    await selectCalendar(record.calendarId, record.calendarVersion, "workweek");
    state.notice = { kind: "ok", message: say("Workday saved. Run the schedule again to use it.", "روز کاری ذخیره شد. برای استفاده، زمان‌بندی را دوباره اجرا کنید.") };
    render();
  }

  async function removeException(record: WorkspaceCalendarRecord, exceptionDate: string): Promise<void> {
    state.busy = true;
    render();
    const result = await deleteCalendarException(transport, context, record, exceptionDate);
    state.busy = false;
    if (!result.ok) {
      state.notice = { kind: "error", message: `${say("Exception was not removed", "استثنا حذف نشد")} (${result.error.code})` };
      render();
      return;
    }
    state.notice = { kind: "ok", message: say("Exception removed. Run the schedule again to use it.", "استثنا حذف شد. برای استفاده، زمان‌بندی را دوباره اجرا کنید.") };
    if (state.editingException?.date === exceptionDate) state.editingException = null;
    const refreshed = await loadCalendarExceptions(transport, context, record.calendarId, record.calendarVersion);
    if (refreshed.ok) state.exceptions = refreshed.data;
    state.tab = "exceptions";
    render();
  }

  host.addEventListener("click", (event) => {
    const target = event.target as HTMLElement;
    const workdayButton = target.closest<HTMLElement>("[data-workday-save]");
    if (workdayButton?.dataset.workdaySave) {
      const record = selectedRecord(state);
      if (record && !state.busy) void saveWorkday(record, Number(workdayButton.dataset.workdaySave));
      return;
    }
    const exceptionEdit = target.closest<HTMLElement>("[data-calendar-exception-edit]");
    if (exceptionEdit?.dataset.calendarExceptionEdit) {
      const item = state.exceptions.find((entry) => entry.date === exceptionEdit.dataset.calendarExceptionEdit) ?? null;
      if (item) {
        state.editingException = item;
        state.tab = "exceptions";
        state.notice = null;
        render();
      }
      return;
    }
    if (target.closest<HTMLElement>("[data-calendar-exception-cancel]")) {
      state.editingException = null;
      render();
      return;
    }
    const exceptionDelete = target.closest<HTMLElement>("[data-calendar-exception-delete]");
    if (exceptionDelete?.dataset.calendarExceptionDelete) {
      const record = selectedRecord(state);
      if (record && !state.busy) void removeException(record, exceptionDelete.dataset.calendarExceptionDelete);
      return;
    }
    const row = target.closest<HTMLElement>("[data-calendar-row]");
    if (row) {
      const id = row.dataset.calendarId;
      const version = row.dataset.calendarVersion;
      if (id && version) void selectCalendar(id, version);
      return;
    }
    const tab = target.closest<HTMLElement>("[data-calendar-tab]");
    if (tab?.dataset.calendarTab) {
      state.tab = tab.dataset.calendarTab as PageState["tab"];
      render();
      return;
    }
    const action = target.closest<HTMLElement>("[data-calendar-action]")?.dataset.calendarAction;
    if (!action) return;
    const record = selectedRecord(state);
    if (action === "edit" && record) {
      state.draftName = record.name;
      state.draftType = record.calendarType;
      render();
      return;
    }
    if (action === "cancel-edit") {
      state.draftName = null;
      state.draftType = null;
      render();
      return;
    }
    if (action === "new") {
      state.dialog = "new";
      state.notice = null;
      render();
      return;
    }
    if (action === "new-submit") {
      const baseValue = host.querySelector<HTMLSelectElement>("[data-calendar-new-base]")?.value ?? "";
      const base = state.catalog.find((item) => `${item.calendarId}|${item.calendarVersion}` === baseValue);
      if (!base) return;
      const input = {
        calendarId: host.querySelector<HTMLInputElement>("[data-calendar-new-id]")?.value ?? "",
        calendarVersion: host.querySelector<HTMLInputElement>("[data-calendar-new-version]")?.value ?? "",
        calendarType: host.querySelector<HTMLSelectElement>("[data-calendar-new-type]")?.value ?? "project",
        kind: base.kind,
        name: host.querySelector<HTMLInputElement>("[data-calendar-new-name]")?.value ?? "",
        baseCalendarId: base.calendarId,
        baseCalendarVersion: base.calendarVersion,
        system: (host.querySelector<HTMLSelectElement>("[data-calendar-new-system]")?.value === "jalali" ? "jalali" : "gregorian") as "gregorian" | "jalali",
      };
      void (async () => {
        state.busy = true;
        render();
        const result = await createCalendar(transport, context, input);
        state.busy = false;
        if (!result.ok) {
          state.notice = { kind: "error", message: `${say("Calendar was not created", "ایجاد تقویم ناموفق بود")} (${result.error.code})` };
          render();
          return;
        }
        state.dialog = "none";
        state.notice = { kind: "ok", message: say("Calendar created from the base definition.", "تقویم از تعریف پایه ایجاد شد.") };
        await reloadCatalogue({ id: result.data.calendarId, version: result.data.calendarVersion });
        await selectCalendar(result.data.calendarId, result.data.calendarVersion);
      })();
      return;
    }
    if (action === "copy" && record) {
      state.dialog = "copy";
      render();
      return;
    }
    if (action === "delete" && record) {
      state.dialog = "delete";
      render();
      return;
    }
    if (action === "dialog-cancel") {
      state.dialog = "none";
      render();
      return;
    }
    if (action === "reload") {
      void reloadCatalogue(state.selected);
      return;
    }
    if (action === "save" && record && state.draftName !== null) {
      void (async () => {
        state.busy = true;
        render();
        const result = await updateCalendar(transport, context, record, {
          name: state.draftName ?? record.name,
          calendarType: state.draftType ?? record.calendarType,
        });
        state.busy = false;
        if (!result.ok) {
          state.notice = { kind: "error", message: `${say("Save failed", "ذخیره ناموفق بود")} (${result.error.code})` };
          render();
          return;
        }
        state.catalog = state.catalog.map((item) => item.calendarId === result.data.calendarId && item.calendarVersion === result.data.calendarVersion ? result.data : item);
        state.draftName = null;
        state.draftType = null;
        state.notice = { kind: "ok", message: say("Calendar saved.", "تقویم ذخیره شد.") };
        render();
      })();
      return;
    }
    if (action === "copy-submit" && record) {
      const targetId = host.querySelector<HTMLInputElement>("[data-calendar-target-id]")?.value ?? "";
      const targetVersion = host.querySelector<HTMLInputElement>("[data-calendar-target-version]")?.value ?? "";
      void (async () => {
        state.busy = true;
        render();
        const result = await copyCalendar(transport, context, record, targetId, targetVersion);
        state.busy = false;
        if (!result.ok) {
          state.notice = { kind: "error", message: `${say("Copy failed", "کپی ناموفق بود")} (${result.error.code})` };
          render();
          return;
        }
        state.dialog = "none";
        state.notice = { kind: "ok", message: say("Calendar copied.", "تقویم کپی شد.") };
        await reloadCatalogue({ id: result.data.calendarId, version: result.data.calendarVersion });
        void selectCalendar(result.data.calendarId, result.data.calendarVersion);
      })();
      return;
    }
    if (action === "delete-confirm" && record) {
      void (async () => {
        state.busy = true;
        render();
        const result = await deleteCalendar(transport, context, record);
        state.busy = false;
        if (!result.ok) {
          state.notice = { kind: "error", message: `${say("Delete failed", "حذف ناموفق بود")} (${result.error.code})` };
          render();
          return;
        }
        state.dialog = "none";
        state.notice = { kind: "ok", message: say("Calendar deleted.", "تقویم حذف شد.") };
        await reloadCatalogue(null);
      })();
    }
  });

  host.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const row = (event.target as HTMLElement).closest<HTMLElement>("[data-calendar-row]");
    if (!row) return;
    event.preventDefault();
    const id = row.dataset.calendarId;
    const version = row.dataset.calendarVersion;
    if (id && version) void selectCalendar(id, version);
  });

  host.addEventListener("input", (event) => {
    const target = event.target as HTMLElement;
    if (target.matches("[data-calendar-name]")) {
      state.draftName = (target as HTMLInputElement).value;
    }
    if (target.matches("[data-calendar-type]")) {
      state.draftType = (target as HTMLSelectElement).value;
    }
  });

  host.addEventListener("change", (event) => {
    const target = event.target as HTMLElement;
    if (target.matches("[data-calendar-type]")) {
      state.draftType = (target as HTMLSelectElement).value;
    }
    const form = target.closest<HTMLFormElement>("[data-calendar-exception-form]");
    if (form && target.matches("[name=mode]")) {
      const fields = findExceptionFields(form);
      const mode = fields.mode?.value ?? "nonwork";
      const hoursField = form.querySelector<HTMLElement>("[data-calendar-exception-hours]");
      const intervalFields = form.querySelectorAll<HTMLElement>("[data-calendar-exception-interval]");
      if (hoursField) hoursField.hidden = mode !== "total-work-hours";
      intervalFields.forEach((field) => { field.hidden = mode !== "detailed-work-hours"; });
    }
  });

  host.addEventListener("submit", (event) => {
    const form = event.target as HTMLFormElement;
    if (!form.matches("[data-calendar-exception-form]")) return;
    event.preventDefault();
    const record = selectedRecord(state);
    if (!record || state.busy) return;
    const fields = findExceptionFields(form);
    const editing = state.editingException;
    const jalaliSystem = state.snapshot?.system === "jalali";
    const rawDate = fields.date?.value ?? "";
    const canonicalDate = jalaliSystem && !editing ? parseJalaliDateInput(rawDate) : rawDate;
    if (!canonicalDate) {
      state.notice = { kind: "error", message: say("Enter a valid Jalali date such as 1405/10/01.", "یک تاریخ جلالی معتبر مانند 1405/10/01 وارد کنید.") };
      render();
      return;
    }
    const input: CalendarExceptionInput = {
      date: canonicalDate,
      mode: fields.mode?.value ?? "nonwork",
      totalWorkHours: fields.hours?.value || null,
      start: fields.start?.value || null,
      end: fields.end?.value || null,
    };
    void (async () => {
      state.busy = true;
      render();
      const result = editing
        ? await reviseCalendarException(transport, context, record, editing, input)
        : await saveCalendarException(transport, context, record, state.snapshot?.system ?? null, input);
      state.busy = false;
      if (!result.ok) {
        state.notice = { kind: "error", message: `${say("Exception was not saved", "استثنا ذخیره نشد")} (${result.error.code})` };
        render();
        return;
      }
      state.editingException = null;
      state.notice = {
        kind: "ok",
        message: editing
          ? say("Exception updated at record revision " + result.data.recordRevision + ". Run the schedule again to use it.", "استثنا در ویرایش رکورد " + result.data.recordRevision + " به‌روزرسانی شد. برای استفاده، زمان‌بندی را دوباره اجرا کنید.")
          : say("Exception saved. Run the schedule again to use it.", "استثنا ذخیره شد. برای استفاده از آن، زمان‌بندی را دوباره اجرا کنید."),
      };
      const refreshed = await loadCalendarExceptions(transport, context, record.calendarId, record.calendarVersion);
      if (refreshed.ok) state.exceptions = refreshed.data;
      state.tab = "exceptions";
      render();
    })();
  });

  render();
}
