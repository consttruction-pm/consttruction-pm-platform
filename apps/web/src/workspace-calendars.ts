import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import type {
  WorkspaceCalendarCatalog,
  WorkspaceCalendarRecord,
} from "./workspace-model.js";
import {
  formatJalaliDateInput,
  isValidCanonicalIsoDate,
  parseJalaliDateInput,
} from "./workspace-jalali-entry.js";

export const CALENDAR_CATALOG_CONTRACT = "p6-calendar-read-api.v1";
export const CALENDAR_API_CONTRACT = "p6-calendar.v1";

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
      };
    });
    return { ok: true, data: exceptions };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_CALENDAR_EXCEPTIONS");
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
  tab: "general" | "workweek" | "exceptions";
  dialog: "none" | "copy" | "delete";
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

  function renderWorkweek(): string {
    const snapshot = state.snapshot;
    if (!snapshot) {
      return `<div class="cp-calendar-empty">${escapeHtml(say("Select a calendar to read its working time.", "برای خواندن ساعات کاری، یک تقویم انتخاب کنید."))}</div>`;
    }
    const rows = WEEKDAYS.map((day) => {
      const working = snapshot.workingWeekdays.includes(day.index);
      const intervals = snapshot.dailyIntervals[String(day.index)] ?? [];
      const intervalsText = intervals.length
        ? intervals.map((pair) => `${pair[0]}–${pair[1]}`).join(", ")
        : working ? say("Standard day", "روز استاندارد") : "—";
      return `<tr><th>${escapeHtml(say(day.en, day.fa))}</th><td>${escapeHtml(working ? say("Working", "کاری") : say("Non-working", "غیرکاری"))}</td><td>${escapeHtml(intervalsText)}</td></tr>`;
    }).join("");
    const holidays = snapshot.holidays.length
      ? `<ul class="cp-calendar-holiday-list">${snapshot.holidays.map((day) => `<li><span class="cp-calendar-holiday-date">${escapeHtml(day)}</span></li>`).join("")}</ul>`
      : `<p class="cp-calendar-hint">${escapeHtml(say("No non-working days are stored in this calendar snapshot.", "هیچ روز غیرکاری در این نسخه تقویم ذخیره نشده است."))}</p>`;
    return `<section class="cp-calendar-editor-panel" data-calendar-panel="workweek">
      <div class="cp-calendar-table-wrap"><table><thead><tr><th>${escapeHtml(say("Day", "روز"))}</th><th>${escapeHtml(say("Working Day", "روز کاری"))}</th><th>${escapeHtml(say("Intervals", "بازه‌ها"))}</th></tr></thead><tbody>${rows}</tbody></table></div>
      <div class="cp-calendar-section-head"><strong>${escapeHtml(say("Stored non-working days", "روزهای غیرکاری ذخیره‌شده"))}</strong></div>${holidays}
      <p class="cp-calendar-hint">${escapeHtml(say("Working time is read from the persisted calendar snapshot. Changes to the workweek are made through the calendar copy contract until a workweek write route is exposed; this page does not invent hours.", "ساعات کاری از نسخه تقویم ذخیره‌شده خوانده می‌شود. تغییر هفته کاری از طریق قرارداد کپی تقویم انجام می‌شود تا مسیر نوشتن هفته کاری ارائه شود؛ این صفحه ساعتی نمی‌سازد."))}</p>
    </section>`;
  }

  function renderExceptions(record: WorkspaceCalendarRecord): string {
    if (state.exceptionsError) {
      return `<div class="cp-calendar-empty" role="alert">${escapeHtml(say("Calendar exceptions could not be read", "خواندن استثناهای تقویم ناموفق بود"))} (${escapeHtml(state.exceptionsError)})</div>`;
    }
    const list = state.exceptions.length
      ? `<ul class="cp-calendar-holiday-list">${state.exceptions.map((item) => `<li><span class="cp-calendar-holiday-date">${escapeHtml(item.date)}</span><span class="cp-calendar-holiday-mode">${escapeHtml(item.mode)}${item.totalWorkHours ? ` · ${escapeHtml(item.totalWorkHours)} h` : ""}${item.intervals.length ? ` · ${item.intervals.map((pair) => `${pair[0]}–${pair[1]}`).join(", ")}` : ""}</span></li>`).join("")}</ul>`
      : `<div class="cp-calendar-empty">${escapeHtml(say("No exceptions are stored for this calendar.", "هیچ استثنایی برای این تقویم ذخیره نشده است."))}</div>`;
    const modeOptions = EXCEPTION_MODE_LABELS.map((mode) => `<option value="${mode.value}">${escapeHtml(say(mode.en, mode.fa))}</option>`).join("");
    return `<section class="cp-calendar-editor-panel" data-calendar-panel="exceptions">
      ${list}
      <form data-calendar-exception-form>
        <label>${escapeHtml(say("Date", "تاریخ"))}<input type="date" name="date" required></label>
        <label>${escapeHtml(say("Mode", "حالت"))}<select name="mode">${modeOptions}</select></label>
        <label data-calendar-exception-hours hidden>${escapeHtml(say("Total hours", "مجموع ساعات"))}<input type="number" name="hours" min="0" step="0.25"></label>
        <label data-calendar-exception-interval hidden>${escapeHtml(say("Start", "شروع"))}<input type="time" name="start"></label>
        <label data-calendar-exception-interval hidden>${escapeHtml(say("Finish", "پایان"))}<input type="time" name="end"></label>
        <button type="submit" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Add exception", "افزودن استثنا"))}</button>
      </form>
      <p class="cp-calendar-hint">${escapeHtml(say("Exceptions are persisted through the calendar API. A saved exception invalidates the previous schedule result; run the schedule again to see authoritative dates.", "استثناها از طریق API تقویم ذخیره می‌شوند. استثنای ذخیره‌شده نتیجه زمان‌بندی قبلی را باطل می‌کند؛ برای مشاهده تاریخ‌های مرجع، زمان‌بندی را دوباره اجرا کنید."))}</p>
      <input type="hidden" data-calendar-exception-calendar value="${escapeHtml(record.calendarId)}">
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
    ].map(([key, label]) => `<button type="button" role="tab" data-calendar-tab="${key}" aria-selected="${state.tab === key}" class="${state.tab === key ? "is-active" : ""}">${escapeHtml(label)}</button>`).join("");
    const panel = state.tab === "general" ? renderGeneral(record) : state.tab === "workweek" ? renderWorkweek() : renderExceptions(record);
    const snapshotFailure = state.snapshotError
      ? `<p class="cp-calendar-notice" role="alert">${escapeHtml(say("Calendar snapshot could not be read", "خواندن نسخه تقویم ناموفق بود"))} (${escapeHtml(state.snapshotError)}). ${escapeHtml(say("Dates and durations must not be inferred without it.", "بدون آن، تاریخ و مدت نباید استنتاج شود."))}</p>`
      : "";
    return `${snapshotFailure}<div class="cp-calendar-editor-tabs" role="tablist">${tabs}</div><div class="cp-calendar-editor-content">${panel}</div>`;
  }

  function renderDialog(record: WorkspaceCalendarRecord | null): string {
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

  async function selectCalendar(id: string, version: string): Promise<void> {
    state.selected = { id, version };
    state.snapshot = null;
    state.snapshotError = null;
    state.exceptions = [];
    state.exceptionsError = null;
    state.tab = "general";
    state.dialog = "none";
    state.draftName = null;
    state.draftType = null;
    state.notice = null;
    state.snapshotLoading = true;
    render();
    const [snapshotResult, exceptionResult] = await Promise.all([
      loadCalendarSnapshot(transport, context, id, version),
      loadCalendarExceptions(transport, context, id, version),
    ]);
    if (state.selected?.id !== id || state.selected?.version !== version) return;
    state.snapshotLoading = false;
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

  host.addEventListener("click", (event) => {
    const target = event.target as HTMLElement;
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
    const input: CalendarExceptionInput = {
      date: fields.date?.value ?? "",
      mode: fields.mode?.value ?? "nonwork",
      totalWorkHours: fields.hours?.value || null,
      start: fields.start?.value || null,
      end: fields.end?.value || null,
    };
    void (async () => {
      state.busy = true;
      render();
      const result = await saveCalendarException(transport, context, record, state.snapshot?.system ?? null, input);
      state.busy = false;
      if (!result.ok) {
        state.notice = { kind: "error", message: `${say("Exception was not saved", "استثنا ذخیره نشد")} (${result.error.code})` };
        render();
        return;
      }
      state.notice = { kind: "ok", message: say("Exception saved. Run the schedule again to use it.", "استثنا ذخیره شد. برای استفاده از آن، زمان‌بندی را دوباره اجرا کنید.") };
      const refreshed = await loadCalendarExceptions(transport, context, record.calendarId, record.calendarVersion);
      if (refreshed.ok) state.exceptions = refreshed.data;
      state.tab = "exceptions";
      render();
    })();
  });

  render();
}
