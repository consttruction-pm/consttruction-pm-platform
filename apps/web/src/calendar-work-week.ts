import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";

export type CalendarWorkWeekSnapshot = {
  contract_version: string;
  kind: "calendar_snapshot";
  calendar: {
    calendar_id: string;
    calendar_version: string;
    kind: "working-day" | "working-time";
    calendar_type: string;
    name: string;
    record_revision: number;
  };
  snapshot: {
    working_weekdays?: number[];
    [key: string]: unknown;
  };
};

export type CalendarWorkWeekRevision = {
  contract_version: string;
  calendar_id: string;
  calendar_version: string;
  source_calendar_version: string;
  kind: "working-day" | "working-time";
  calendar_type: string;
  name: string;
  record_revision: number;
  working_weekdays: number[];
};

export type CalendarWorkWeekLabels = {
  title: string;
  intro: string;
  weekdays: string;
  reading: string;
  readFailed: string;
  save: string;
  saving: string;
  saved: string;
  failed: string;
  noCalendar: string;
  weekdayRequired: string;
  applyHint: string;
  dayNames: readonly string[];
};

export type CalendarWorkWeekEditor = {
  element: HTMLElement;
  setCalendar(calendarId: string, calendarVersion: string): void;
  reload(): Promise<void>;
};

function snapshotPath(context: ProjectContext, calendarId: string, calendarVersion: string): string {
  return (
    `/api/projects/${encodeURIComponent(context.project_id)}/p6/calendars/` +
    `${encodeURIComponent(calendarId)}/${encodeURIComponent(calendarVersion)}/snapshot`
  );
}

function revisionPath(context: ProjectContext, calendarId: string, calendarVersion: string): string {
  return (
    `/api/projects/${encodeURIComponent(context.project_id)}/p6/calendars/` +
    `${encodeURIComponent(calendarId)}/${encodeURIComponent(calendarVersion)}/work-week`
  );
}

function nextVersion(current: string, availableVersions: readonly string[]): string {
  const numeric = availableVersions
    .filter((value) => /^\\d+$/.test(value))
    .map((value) => Number(value))
    .filter((value) => Number.isSafeInteger(value) && value > 0);
  if (/^\\d+$/.test(current)) {
    let candidate = Math.max(Number(current), ...numeric) + 1;
    const used = new Set(availableVersions);
    while (used.has(String(candidate))) candidate += 1;
    return String(candidate);
  }
  let suffix = 2;
  const used = new Set(availableVersions);
  while (used.has(`${current}-rev-${suffix}`)) suffix += 1;
  return `${current}-rev-${suffix}`;
}

function localFailure<T>(code: string): ApiResult<T> {
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

export function createCalendarWorkWeekEditor(options: {
  transport: ApiTransport;
  context: ProjectContext;
  labels: CalendarWorkWeekLabels;
  calendarId: string;
  calendarVersion: string;
  availableVersions: () => readonly string[];
  onSaved?: (record: CalendarWorkWeekRevision) => void;
}): CalendarWorkWeekEditor {
  const { transport, context, labels } = options;
  let calendarId = options.calendarId;
  let calendarVersion = options.calendarVersion;
  let sourceRevision = 0;
  let workingWeekdays = new Set<number>();
  let loading = false;
  let saving = false;

  const section = document.createElement("section");
  section.className = "cp-calendar-work-week";
  section.dataset.calendarWorkWeek = "true";

  const heading = document.createElement("h3");
  heading.textContent = labels.title;
  const intro = document.createElement("p");
  intro.className = "cp-muted";
  intro.textContent = labels.intro;

  const status = document.createElement("p");
  status.className = "cp-calendar-work-week-status";
  status.dataset.workWeekStatus = "true";
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");

  const form = document.createElement("form");
  form.dataset.workWeekForm = "true";
  form.noValidate = true;
  const fieldset = document.createElement("fieldset");
  const legend = document.createElement("legend");
  legend.textContent = labels.weekdays;
  fieldset.append(legend);
  const days = new Map<number, HTMLInputElement>();
  const dayOrder = options.context && labels.dayNames.length === 7
    ? (labels.dayNames[0] === "Monday" ? [0, 1, 2, 3, 4, 5, 6] : [5, 6, 0, 1, 2, 3, 4])
    : [0, 1, 2, 3, 4, 5, 6];
  for (const weekday of dayOrder) {
    const label = document.createElement("label");
    label.className = "cp-calendar-work-week-day";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = String(weekday);
    input.dataset.calendarWorkingWeekday = String(weekday);
    input.addEventListener("change", () => {
      if (input.checked) workingWeekdays.add(weekday);
      else workingWeekdays.delete(weekday);
      setStatus("", false);
    });
    const name = document.createElement("span");
    name.textContent = labels.dayNames[weekday] ?? String(weekday);
    label.append(input, name);
    fieldset.append(label);
    days.set(weekday, input);
  }

  const submit = document.createElement("button");
  submit.type = "submit";
  submit.dataset.workWeekSave = "true";
  submit.textContent = labels.save;
  form.append(fieldset, submit);
  section.append(heading, intro, form, status);

  const setStatus = (message: string, error: boolean): void => {
    status.textContent = message;
    status.dataset.state = error ? "error" : message ? "info" : "idle";
  };

  const setBusy = (busy: boolean): void => {
    loading = busy;
    for (const input of days.values()) input.disabled = busy || !calendarId || !calendarVersion;
    submit.disabled = busy || !calendarId || !calendarVersion;
  };

  const renderDays = (): void => {
    for (const [weekday, input] of days) input.checked = workingWeekdays.has(weekday);
  };

  const reload = async (): Promise<void> => {
    if (!calendarId || !calendarVersion) {
      sourceRevision = 0;
      workingWeekdays = new Set<number>();
      renderDays();
      setBusy(false);
      for (const input of days.values()) input.disabled = true;
      submit.disabled = true;
      setStatus(labels.noCalendar, true);
      return;
    }
    setBusy(true);
    setStatus(labels.reading, false);
    const result = await transport.get<CalendarWorkWeekSnapshot>(
      snapshotPath(context, calendarId, calendarVersion),
      context,
    );
    if (!result.ok) {
      sourceRevision = 0;
      workingWeekdays = new Set<number>();
      renderDays();
      setBusy(false);
      setStatus(`${labels.readFailed} (${result.error.code})`, true);
      return;
    }
    const rawWeekdays = result.data.snapshot.working_weekdays;
    if (!Array.isArray(rawWeekdays) ||
        rawWeekdays.some((day) => !Number.isInteger(day) || day < 0 || day > 6)) {
      sourceRevision = 0;
      workingWeekdays = new Set<number>();
      renderDays();
      setBusy(false);
      setStatus(`${labels.readFailed} (INVALID_CALENDAR_WEEKDAYS)`, true);
      return;
    }
    sourceRevision = result.data.calendar.record_revision;
    workingWeekdays = new Set<number>(rawWeekdays);
    renderDays();
    setBusy(false);
    setStatus("", false);
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (loading || saving) return;
    if (workingWeekdays.size === 0) {
      setStatus(labels.weekdayRequired, true);
      return;
    }
    if (!calendarId || !calendarVersion || sourceRevision < 1) {
      setStatus(labels.noCalendar, true);
      return;
    }
    saving = true;
    setBusy(true);
    submit.textContent = labels.saving;
    const available = options.availableVersions();
    const targetVersion = nextVersion(calendarVersion, available);
    const result = await transport.post<
      { target_calendar_version: string; working_weekdays: number[]; expected_revision: number },
      CalendarWorkWeekRevision
    >(
      revisionPath(context, calendarId, calendarVersion),
      {
        target_calendar_version: targetVersion,
        working_weekdays: [...workingWeekdays].sort((a, b) => a - b),
        expected_revision: sourceRevision,
      },
      context,
      crypto.randomUUID(),
    );
    saving = false;
    submit.textContent = labels.save;
    if (!result.ok) {
      setBusy(false);
      setStatus(`${labels.failed} (${result.error.code})`, true);
      return;
    }
    calendarVersion = result.data.calendar_version;
    sourceRevision = result.data.record_revision;
    workingWeekdays = new Set<number>(result.data.working_weekdays);
    renderDays();
    setBusy(false);
    setStatus(`${labels.saved} ${calendarVersion}. ${labels.applyHint}`, false);
    options.onSaved?.(result.data);
  });

  return {
    element: section,
    setCalendar(nextId, nextVersionValue) {
      if (calendarId === nextId && calendarVersion === nextVersionValue) return;
      calendarId = nextId;
      calendarVersion = nextVersionValue;
      void reload();
    },
    reload,
  };
}
