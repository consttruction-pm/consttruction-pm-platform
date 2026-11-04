import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import { translateUiString } from "./workspace-ui-translations.js";

export const ACTIVITY_API_VERSION = "p6-activity-master-api.v1";

export const PROGRESS_STATUSES = ["Not Started", "In Progress", "Completed"] as const;
export type ProgressStatus = (typeof PROGRESS_STATUSES)[number];

export type ProgressActivity = {
  activityId: string;
  name: string;
  status: string;
  statusCode: string;
  percentComplete: number | null;
  actualStart: string | null;
  actualFinish: string | null;
  remainingDuration: number | null;
  recordRevision: number;
};

export type ProgressInput = {
  percentComplete: string;
  actualStart: string;
  actualFinish: string;
  remainingDuration: string;
  status: string;
};

export type ProgressPageOptions = {
  transport: ApiTransport;
  context: ProjectContext;
  locale: string;
  initialActivityId?: string | null;
  onUpdated?: (activity: ProgressActivity) => void | Promise<void>;
};

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

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

function optionalText(value: unknown, code: string): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== "string") throw new Error(code);
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function optionalPercent(value: unknown, code: string): number | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0 || value > 100) {
    throw new Error(code);
  }
  return value;
}

function optionalDuration(value: unknown, code: string): number | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0) throw new Error(code);
  return value;
}

function activitiesPath(context: ProjectContext, activityId?: string): string {
  const base = `/api/projects/${encodeURIComponent(context.project_id)}/p6/activities`;
  return activityId ? `${base}/${encodeURIComponent(activityId)}` : base;
}

export function parseProgressActivity(value: unknown): ProgressActivity {
  if (!isRecord(value)) throw new Error("INVALID_ACTIVITY_RECORD");
  if (value.contract_version !== ACTIVITY_API_VERSION) throw new Error("INVALID_ACTIVITY_RESPONSE");
  if (value.kind !== "p6_activity_master") throw new Error("INVALID_ACTIVITY_RESPONSE");
  const payload = value.activity;
  if (!isRecord(payload)) throw new Error("INVALID_ACTIVITY_RESPONSE");
  const { activity_id, name, status, status_code, record_revision } = payload;
  if (
    typeof activity_id !== "string" || !activity_id.trim() ||
    typeof name !== "string" ||
    typeof status !== "string" || !status.trim() ||
    typeof status_code !== "string" || !status_code.trim()
  ) {
    throw new Error("INVALID_ACTIVITY_RECORD");
  }
  if (typeof record_revision !== "number" || !Number.isInteger(record_revision) || record_revision < 1) {
    throw new Error("INVALID_ACTIVITY_RECORD");
  }
  return {
    activityId: activity_id,
    name,
    status,
    statusCode: status_code,
    percentComplete: optionalPercent(payload.percent_complete, "INVALID_ACTIVITY_RECORD"),
    actualStart: optionalText(payload.actual_start, "INVALID_ACTIVITY_RECORD"),
    actualFinish: optionalText(payload.actual_finish, "INVALID_ACTIVITY_RECORD"),
    remainingDuration: optionalDuration(payload.remaining_duration, "INVALID_ACTIVITY_RECORD"),
    recordRevision: record_revision,
  };
}

export async function loadProgressActivities(
  transport: ApiTransport,
  context: ProjectContext,
): Promise<ApiResult<readonly ProgressActivity[]>> {
  const result = await transport.get<unknown>(activitiesPath(context), context);
  if (!result.ok) return result;
  const payload = result.data;
  if (
    !isRecord(payload) ||
    payload.contract_version !== ACTIVITY_API_VERSION ||
    !Array.isArray(payload.activities)
  ) {
    return localError("INVALID_ACTIVITY_LIST");
  }
  try {
    return { ok: true, data: payload.activities.map((item) => parseProgressActivity(item)) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ACTIVITY_LIST");
  }
}

function validDate(value: string, code: string): string {
  if (!ISO_DATE.test(value)) throw new Error(code);
  const parsed = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== value) {
    throw new Error(code);
  }
  return value;
}

function resolvedDate(raw: string, original: string | null, code: string): string | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  validDate(trimmed, code);
  // Preserve a stored timestamp when the date part was not changed; the form
  // only edits the calendar day, and the server must not lose the time part.
  if (original && original.slice(0, 10) === trimmed) return original;
  return trimmed;
}

export function buildProgressPayload(
  activity: ProgressActivity,
  input: ProgressInput,
  origin: { actualStart: string | null; actualFinish: string | null } = {
    actualStart: activity.actualStart,
    actualFinish: activity.actualFinish,
  },
): Record<string, unknown> {
  if (!Number.isInteger(activity.recordRevision) || activity.recordRevision < 1) {
    throw new Error("EXPECTED_REVISION_REQUIRED");
  }
  if (!(PROGRESS_STATUSES as readonly string[]).includes(input.status)) {
    throw new Error("INVALID_ACTIVITY_STATUS");
  }
  const percentRaw = input.percentComplete.trim();
  let percent: number | null = null;
  if (percentRaw) {
    if (!/^\d+(\.\d+)?$/.test(percentRaw)) throw new Error("INVALID_PERCENT_COMPLETE");
    percent = Number(percentRaw);
    if (!Number.isFinite(percent) || percent > 100) throw new Error("INVALID_PERCENT_COMPLETE");
  }
  const remainingRaw = input.remainingDuration.trim();
  let remaining: number | null = null;
  if (remainingRaw) {
    if (!/^\d+$/.test(remainingRaw)) throw new Error("INVALID_REMAINING_DURATION");
    remaining = Number(remainingRaw);
    if (!Number.isSafeInteger(remaining)) throw new Error("INVALID_REMAINING_DURATION");
  }
  const actualStart = resolvedDate(input.actualStart, origin.actualStart, "INVALID_ACTUAL_START");
  const actualFinish = resolvedDate(input.actualFinish, origin.actualFinish, "INVALID_ACTUAL_FINISH");
  if (actualFinish && !actualStart) throw new Error("FINISH_REQUIRES_START");
  if (actualStart && actualFinish && actualFinish.slice(0, 10) < actualStart.slice(0, 10)) {
    throw new Error("FINISH_BEFORE_START");
  }
  if (actualFinish && remaining !== null && remaining !== 0) {
    throw new Error("COMPLETED_REMAINING_DURATION");
  }
  if (actualFinish && percent !== null && percent !== 100) {
    throw new Error("COMPLETED_PERCENT_REQUIRED");
  }
  return {
    contract_version: ACTIVITY_API_VERSION,
    expected_revision: activity.recordRevision,
    percent_complete: percent,
    actual_start: actualStart,
    actual_finish: actualFinish,
    remaining_duration: remaining,
    status: input.status,
  };
}

export async function saveProgress(
  transport: ApiTransport,
  context: ProjectContext,
  activity: ProgressActivity,
  input: ProgressInput,
): Promise<ApiResult<ProgressActivity>> {
  let payload: Record<string, unknown>;
  try {
    payload = buildProgressPayload(activity, input);
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_PROGRESS_INPUT");
  }
  if (!transport.patch) return localError("PROGRESS_TRANSPORT_UNAVAILABLE");
  // Call the optional method on the transport itself: the fetch transport uses
  // `this.request`, so a detached function reference would lose its receiver.
  const result = await transport.patch<Record<string, unknown>, unknown>(
    activitiesPath(context, activity.activityId),
    payload,
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseProgressActivity(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ACTIVITY_RESPONSE");
  }
}

type PageState = {
  status: "loading" | "loaded" | "error";
  errorCode: string | null;
  activities: readonly ProgressActivity[];
  selectedActivityId: string | null;
  origin: { actualStart: string | null; actualFinish: string | null };
  busy: boolean;
  notice: { kind: "ok" | "error"; message: string } | null;
};

function statusLabel(locale: string, status: string): string {
  const base = locale.split("-")[0];
  if (base === "fa") {
    if (status === "Not Started") return "شروع‌نشده";
    if (status === "In Progress") return "در حال اجرا";
    if (status === "Completed") return "تکمیل‌شده";
    return status;
  }
  return translateUiString(locale, status) ?? status;
}

function displayValue(value: string | number | null, missing: string): string {
  return value === null || value === "" ? missing : String(value);
}

export function mountWorkspaceProgressPage(host: HTMLElement, options: ProgressPageOptions): void {
  if (host.dataset.progressMounted === "true") return;
  host.dataset.progressMounted = "true";
  const { transport, context, locale, onUpdated } = options;
  const state: PageState = {
    status: "loading",
    errorCode: null,
    activities: [],
    selectedActivityId: null,
    origin: { actualStart: null, actualFinish: null },
    busy: false,
    notice: null,
  };
  const say = (en: string, fa: string): string => text(locale, en, fa);
  const missing = say("Not recorded", "ثبت نشده");
  const selectedActivity = (): ProgressActivity | null =>
    state.activities.find((item) => item.activityId === state.selectedActivityId) ?? null;

  function select(activity: ProgressActivity): void {
    state.selectedActivityId = activity.activityId;
    state.origin = { actualStart: activity.actualStart, actualFinish: activity.actualFinish };
    state.notice = null;
  }

  function renderRegister(): string {
    if (state.status === "loading") {
      return `<div class="cp-calendar-empty" role="status">${escapeHtml(say("Reading activity progress…", "در حال خواندن پیشرفت فعالیت‌ها…"))}</div>`;
    }
    if (state.status === "error") {
      return `<div class="cp-calendar-empty" role="alert">${escapeHtml(say("Activity progress could not be read", "خواندن پیشرفت فعالیت‌ها ناموفق بود"))} (${escapeHtml(state.errorCode ?? "unknown")})</div>`;
    }
    if (!state.activities.length) {
      return `<div class="cp-calendar-empty">${escapeHtml(say("No activities are stored for this project.", "هیچ فعالیتی برای این پروژه ذخیره نشده است."))}</div>`;
    }
    const rows = state.activities.map((item) => {
      const active = item.activityId === state.selectedActivityId;
      return `<tr data-progress-row data-activity-id="${escapeHtml(item.activityId)}" tabindex="0" role="button" aria-selected="${active}" class="${active ? "is-selected" : ""}"><td><strong>${escapeHtml(item.activityId)}</strong></td><td>${escapeHtml(item.name)}</td><td>${escapeHtml(statusLabel(locale, item.status))}</td><td>${escapeHtml(displayValue(item.percentComplete, missing))}</td><td>${escapeHtml(displayValue(item.actualStart, missing))}</td><td>${escapeHtml(displayValue(item.actualFinish, missing))}</td><td>${escapeHtml(displayValue(item.remainingDuration, missing))}</td><td>${escapeHtml(String(item.recordRevision))}</td></tr>`;
    }).join("");
    return `<div class="cp-register-table-wrap"><table><thead><tr><th>${escapeHtml(say("Activity ID", "شناسه فعالیت"))}</th><th>${escapeHtml(say("Activity Name", "نام فعالیت"))}</th><th>${escapeHtml(say("Status", "وضعیت"))}</th><th>${escapeHtml(say("% Complete", "درصد پیشرفت"))}</th><th>${escapeHtml(say("Actual Start", "شروع واقعی"))}</th><th>${escapeHtml(say("Actual Finish", "پایان واقعی"))}</th><th>${escapeHtml(say("Remaining Duration", "مدت باقی‌مانده"))}</th><th>${escapeHtml(say("Revision", "ویرایش"))}</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function renderEditor(): string {
    const item = selectedActivity();
    if (!item) {
      return `<p>${escapeHtml(say("Select an activity from the register to update its stored progress.", "برای به‌روزرسانی پیشرفت ذخیره‌شده، یک فعالیت را از فهرست انتخاب کنید."))}</p>`;
    }
    const statusOptions = PROGRESS_STATUSES.map((value) =>
      `<option value="${escapeHtml(value)}"${value === item.status ? " selected" : ""}>${escapeHtml(statusLabel(locale, value))}</option>`
    ).join("");
    return `<form data-progress-form class="cp-progress-fields">
      <label>${escapeHtml(say("Activity", "فعالیت"))}<input readonly value="${escapeHtml(`${item.activityId} — ${item.name}`)}"></label>
      <label>${escapeHtml(say("Status", "وضعیت"))}<select name="status">${statusOptions}</select></label>
      <label>${escapeHtml(say("% Complete", "درصد پیشرفت"))}<input name="percent-complete" inputmode="decimal" value="${escapeHtml(item.percentComplete === null ? "" : String(item.percentComplete))}" placeholder="${escapeHtml(missing)}"></label>
      <label>${escapeHtml(say("Actual Start", "شروع واقعی"))}<input name="actual-start" type="date" value="${escapeHtml(item.actualStart ? item.actualStart.slice(0, 10) : "")}"></label>
      <label>${escapeHtml(say("Actual Finish", "پایان واقعی"))}<input name="actual-finish" type="date" value="${escapeHtml(item.actualFinish ? item.actualFinish.slice(0, 10) : "")}"></label>
      <label>${escapeHtml(say("Remaining Duration", "مدت باقی‌مانده"))}<input name="remaining-duration" inputmode="numeric" value="${escapeHtml(item.remainingDuration === null ? "" : String(item.remainingDuration))}" placeholder="${escapeHtml(missing)}"></label>
      <div class="cp-calendar-panel-actions"><button type="submit" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Save progress", "ذخیره پیشرفت"))}</button><button type="button" data-progress-action="reload" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Reload stored values", "بارگذاری مقادیر ذخیره‌شده"))}</button></div>
    </form>`;
  }

  function render(): void {
    host.innerHTML = `<div class="cp-register-toolbar"><strong>${escapeHtml(say("Activity Progress", "پیشرفت فعالیت‌ها"))}</strong><div><button type="button" data-progress-action="refresh" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Refresh", "به‌روزرسانی"))}</button><button type="button" data-rail-action="activities">${escapeHtml(say("Open Schedule", "بازکردن زمان‌بندی"))}</button></div></div>
      ${renderRegister()}
      <section class="cp-register-details"><header><strong>${escapeHtml(say("Progress Details", "جزئیات پیشرفت"))}</strong><span>${escapeHtml(state.selectedActivityId ?? say("No selection", "بدون انتخاب"))}</span></header><div class="cp-register-detail-content">${renderEditor()}</div></section>
      <p class="cp-register-notice">${escapeHtml(say("Progress values are validated and stored by the shared activity service. Schedule dates are recalculated only by Run Schedule on the Schedule page; this page does not compute dates.", "مقادیر پیشرفت توسط سرویس مشترک فعالیت اعتبارسنجی و ذخیره می‌شوند. تاریخ‌های زمان‌بندی فقط با اجرای زمان‌بندی در صفحهٔ زمان‌بندی بازمحاسبه می‌شوند؛ این صفحه تاریخ محاسبه نمی‌کند."))}</p>
      ${state.notice ? `<p class="cp-calendar-notice" data-progress-notice data-state="${state.notice.kind}" role="status">${escapeHtml(state.notice.message)}</p>` : ""}`;
  }

  function readForm(form: HTMLFormElement): ProgressInput {
    const read = (name: string): string =>
      form.querySelector<HTMLInputElement | HTMLSelectElement>(`[name="${name}"]`)?.value ?? "";
    return {
      status: read("status"),
      percentComplete: read("percent-complete"),
      actualStart: read("actual-start"),
      actualFinish: read("actual-finish"),
      remainingDuration: read("remaining-duration"),
    };
  }

  async function reload(keepSelection: string | null): Promise<void> {
    state.status = "loading";
    render();
    const result = await loadProgressActivities(transport, context);
    if (result.ok) {
      state.status = "loaded";
      state.errorCode = null;
      state.activities = result.data;
      const next = keepSelection
        ? result.data.find((item) => item.activityId === keepSelection) ?? null
        : null;
      if (next) select(next);
      else {
        state.selectedActivityId = null;
        state.origin = { actualStart: null, actualFinish: null };
      }
    } else {
      state.status = "error";
      state.errorCode = result.error.code;
    }
    render();
  }

  host.addEventListener("click", (event) => {
    const target = event.target as HTMLElement;
    const row = target.closest<HTMLElement>("[data-progress-row]");
    if (row?.dataset.activityId) {
      const activity = state.activities.find((item) => item.activityId === row.dataset.activityId);
      if (activity) {
        select(activity);
        render();
      }
      return;
    }
    const action = target.closest<HTMLElement>("[data-progress-action]")?.dataset.progressAction;
    if (!action) return;
    if (action === "refresh") void reload(state.selectedActivityId);
    if (action === "reload") {
      const item = selectedActivity();
      if (item) {
        select(item);
        render();
      }
    }
  });

  host.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const target = event.target as HTMLElement;
    const row = target.closest<HTMLElement>("[data-progress-row]");
    if (!row?.dataset.activityId) return;
    event.preventDefault();
    const activity = state.activities.find((item) => item.activityId === row.dataset.activityId);
    if (activity) {
      select(activity);
      render();
    }
  });

  host.addEventListener("submit", (event) => {
    const form = event.target as HTMLFormElement;
    if (!form.matches("[data-progress-form]")) return;
    event.preventDefault();
    const item = selectedActivity();
    if (!item || state.busy) return;
    const input = readForm(form);
    void (async () => {
      state.busy = true;
      state.notice = null;
      render();
      try {
        const result = await saveProgress(transport, context, item, input);
        state.busy = false;
        if (!result.ok) {
          state.notice = {
            kind: "error",
            message: `${say("Progress was not saved", "پیشرفت ذخیره نشد")} (${result.error.code})`,
          };
          render();
          return;
        }
        state.notice = { kind: "ok", message: say("Progress saved.", "پیشرفت ذخیره شد.") };
        await reload(result.data.activityId);
        if (onUpdated) await onUpdated(result.data);
      } catch (error) {
        state.busy = false;
        state.notice = {
          kind: "error",
          message: `${say("Progress was not saved", "پیشرفت ذخیره نشد")} (${error instanceof Error ? error.message : "PROGRESS_SAVE_FAILED"})`,
        };
        render();
      }
    })();
  });

  void reload(options.initialActivityId ?? null);
}
