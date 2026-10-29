import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  formatJalaliDateInput,
  isValidCanonicalIsoDate,
  parseJalaliDateInput,
} from "./workspace-jalali-entry.js";

export type CalendarExceptionRecord = {
  calendar_id: string;
  calendar_version: string;
  date: string;
  mode: string;
  system: string;
  total_work_hours: string | null;
  intervals: readonly (readonly string[])[];
};

export type CalendarExceptionList = {
  contract_version: string;
  exceptions: CalendarExceptionRecord[];
};

export type CalendarHolidayLabels = {
  title: string;
  intro: string;
  date: string;
  add: string;
  adding: string;
  added: string;
  failed: string;
  forbidden: string;
  alreadyRecorded: string;
  invalidDate: string;
  reading: string;
  readFailed: string;
  empty: string;
  noCalendar: string;
  nonwork: string;
  totalHours: string;
  detailedHours: string;
  resetStandard: string;
  canonicalDate: string;
};

export type CalendarHolidayInput = {
  /** Canonical ISO Gregorian day the server must persist. */
  date: string;
  /** System the user actually typed, so the stored record keeps that origin. */
  system: "gregorian" | "jalali";
};

function exceptionsPath(context: ProjectContext, calendarId: string, calendarVersion: string): string {
  return (
    `/api/projects/${encodeURIComponent(context.project_id)}/p6/calendars/` +
    `${encodeURIComponent(calendarId)}/${encodeURIComponent(calendarVersion)}/exceptions`
  );
}

function localError(code: string): ApiResult<never> {
  return {
    ok: false,
    error: {
      code,
      retryable: false,
      message_key: "error.request.invalid",
      available_actions: [],
    },
  };
}

export async function loadCalendarExceptions(
  transport: ApiTransport,
  context: ProjectContext,
  calendarId: string,
  calendarVersion: string,
): Promise<ApiResult<CalendarExceptionList>> {
  if (!calendarId || !calendarVersion) return localError("CALENDAR_REFERENCE_REQUIRED");
  return transport.get<CalendarExceptionList>(
    exceptionsPath(context, calendarId, calendarVersion),
    context,
  );
}

/**
 * Persist a non-working-day exception for one project calendar.
 *
 * The browser only validates and canonicalizes the typed entry; schedule
 * arithmetic stays in the shared calculation core. A Jalali project sends the
 * Jalali day it was typed in and the server stores the canonical Gregorian
 * date, so no display conversion can shift the persisted day.
 */
export async function addCalendarHoliday(
  transport: ApiTransport,
  context: ProjectContext,
  calendarId: string,
  calendarVersion: string,
  input: CalendarHolidayInput,
): Promise<ApiResult<CalendarExceptionRecord>> {
  if (!calendarId || !calendarVersion) return localError("CALENDAR_REFERENCE_REQUIRED");
  if (!isValidCanonicalIsoDate(input.date)) return localError("HOLIDAY_DATE_INVALID");
  let date = input.date;
  if (input.system === "jalali") {
    const typed = formatJalaliDateInput(input.date).replaceAll("/", "-");
    if (!parseJalaliDateInput(typed)) return localError("HOLIDAY_DATE_INVALID");
    date = typed;
  }
  return transport.post<Record<string, unknown>, CalendarExceptionRecord>(
    exceptionsPath(context, calendarId, calendarVersion),
    {
      date,
      mode: "nonwork",
      system: input.system,
      total_work_hours: null,
      intervals: [],
    },
    context,
    crypto.randomUUID(),
  );
}

export function calendarExceptionModeLabel(
  mode: string,
  labels: CalendarHolidayLabels,
): string {
  if (mode === "nonwork") return labels.nonwork;
  if (mode === "total-work-hours") return labels.totalHours;
  if (mode === "detailed-work-hours") return labels.detailedHours;
  if (mode === "reset-standard") return labels.resetStandard;
  return mode;
}

export type CalendarHolidayEditor = {
  element: HTMLElement;
  setCalendar(calendarId: string, calendarVersion: string, system: "gregorian" | "jalali"): void;
  reload(): Promise<void>;
};

export function createCalendarHolidayEditor(options: {
  transport: ApiTransport;
  context: ProjectContext;
  labels: CalendarHolidayLabels;
  calendarId: string;
  calendarVersion: string;
  system: "gregorian" | "jalali";
  onSaved?: (record: CalendarExceptionRecord) => void;
}): CalendarHolidayEditor {
  const { transport, context, labels } = options;
  let calendarId = options.calendarId;
  let calendarVersion = options.calendarVersion;
  let system = options.system;
  let records: CalendarExceptionRecord[] = [];

  const section = document.createElement("section");
  section.className = "cp-calendar-holidays";
  section.dataset.calendarHolidays = "true";

  const heading = document.createElement("h3");
  heading.textContent = labels.title;
  const intro = document.createElement("p");
  intro.className = "cp-muted";
  intro.textContent = labels.intro;

  const list = document.createElement("ul");
  list.className = "cp-calendar-holiday-list";
  list.dataset.calendarHolidayList = "true";

  const form = document.createElement("form");
  form.dataset.calendarHolidayForm = "true";
  form.noValidate = true;
  const label = document.createElement("label");
  label.textContent = labels.date;
  const dateInput = document.createElement("input");
  dateInput.dataset.holidayDate = "true";
  dateInput.autocomplete = "off";
  dateInput.required = true;
  label.append(dateInput);
  const add = document.createElement("button");
  add.type = "submit";
  add.dataset.holidayAdd = "true";
  add.textContent = labels.add;
  form.append(label, add);

  const status = document.createElement("p");
  status.className = "cp-calendar-holiday-status";
  status.dataset.holidayStatus = "true";
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");

  section.append(heading, intro, list, form, status);

  const setStatus = (text: string, state: "idle" | "info" | "success" | "error" | "forbidden" | "conflict"): void => {
    status.textContent = text;
    status.dataset.state = state;
  };

  const syncInput = (): void => {
    if (system === "jalali") {
      dateInput.type = "text";
      dateInput.placeholder = "۱۴۰۵/۰۷/۱۵";
      dateInput.inputMode = "numeric";
    } else {
      dateInput.type = "date";
      dateInput.removeAttribute("placeholder");
      dateInput.removeAttribute("inputmode");
    }
  };

  const displayDate = (iso: string, recordedSystem: string): string => {
    if (!isValidCanonicalIsoDate(iso)) return iso;
    if (recordedSystem !== "jalali") return iso;
    return `${formatJalaliDateInput(iso)} (${iso})`;
  };

  const render = (): void => {
    list.replaceChildren();
    if (records.length === 0) {
      const empty = document.createElement("li");
      empty.className = "cp-muted";
      empty.dataset.holidayEmpty = "true";
      empty.textContent = labels.empty;
      list.append(empty);
      return;
    }
    for (const record of records) {
      const item = document.createElement("li");
      item.dataset.holidayRecord = record.date;
      const day = document.createElement("span");
      day.className = "cp-calendar-holiday-date";
      day.textContent = displayDate(record.date, record.system);
      const mode = document.createElement("span");
      mode.className = "cp-calendar-holiday-mode";
      mode.textContent = calendarExceptionModeLabel(record.mode, labels);
      const canonical = document.createElement("small");
      canonical.className = "cp-muted";
      canonical.textContent = `${labels.canonicalDate}: ${record.date}`;
      item.append(day, mode, canonical);
      list.append(item);
    }
  };

  const reload = async (): Promise<void> => {
    syncInput();
    if (!calendarId || !calendarVersion) {
      records = [];
      list.replaceChildren();
      add.disabled = true;
      dateInput.disabled = true;
      const empty = document.createElement("li");
      empty.className = "cp-muted";
      empty.dataset.holidayEmpty = "true";
      empty.textContent = labels.noCalendar;
      list.append(empty);
      setStatus("", "idle");
      return;
    }
    add.disabled = false;
    dateInput.disabled = false;
    setStatus(labels.reading ?? "", "idle");
    const result = await loadCalendarExceptions(transport, context, calendarId, calendarVersion);
    if (!result.ok) {
      records = [];
      list.replaceChildren();
      const failed = document.createElement("li");
      failed.className = "cp-muted";
      failed.dataset.holidayEmpty = "true";
      failed.textContent = labels.readFailed;
      list.append(failed);
      setStatus(`${labels.readFailed} (${result.error.code})`, "error");
      return;
    }
    records = Array.isArray(result.data.exceptions) ? result.data.exceptions : [];
    render();
    setStatus("", "idle");
  };

  const submit = async (): Promise<void> => {
    if (!calendarId || !calendarVersion) return;
    const raw = dateInput.value.trim();
    let canonical = "";
    if (system === "jalali") {
      const parsed = parseJalaliDateInput(raw);
      if (!parsed) {
        setStatus(labels.invalidDate, "error");
        dateInput.focus();
        return;
      }
      canonical = parsed;
    } else {
      canonical = raw.slice(0, 10);
      if (!isValidCanonicalIsoDate(canonical)) {
        setStatus(labels.invalidDate, "error");
        dateInput.focus();
        return;
      }
    }
    if (records.some((record) => record.date === canonical && record.mode === "nonwork")) {
      setStatus(labels.alreadyRecorded, "conflict");
      return;
    }
    add.disabled = true;
    setStatus(labels.adding, "info");
    const result = await addCalendarHoliday(
      transport,
      context,
      calendarId,
      calendarVersion,
      { date: canonical, system },
    );
    add.disabled = false;
    if (!result.ok) {
      if (result.error.code.includes("project.write") || result.error.code.includes("authorization denied")) {
        setStatus(labels.forbidden, "forbidden");
        return;
      }
      if (result.error.code === "P6_CALENDAR_REQUEST_INVALID") {
        setStatus(labels.alreadyRecorded, "conflict");
        return;
      }
      setStatus(`${labels.failed} (${result.error.code})`, "error");
      return;
    }
    dateInput.value = "";
    setStatus(labels.added, "success");
    options.onSaved?.(result.data);
    await reload();
    setStatus(labels.added, "success");
  };

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    void submit();
  });

  syncInput();
  void reload();

  return {
    element: section,
    setCalendar(nextId: string, nextVersion: string, nextSystem: "gregorian" | "jalali"): void {
      const changed = nextId !== calendarId || nextVersion !== calendarVersion;
      calendarId = nextId;
      calendarVersion = nextVersion;
      system = nextSystem;
      syncInput();
      if (changed) void reload();
    },
    reload,
  };
}
