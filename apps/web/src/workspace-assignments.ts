import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";

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
  note: string | null;
};

export type AssignmentPageOptions = {
  transport: ApiTransport;
  context: ProjectContext;
  locale: string;
  activities: readonly AssignmentActivityOption[];
};

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

type PageState = {
  status: "loading" | "loaded" | "error";
  errorCode: string | null;
  assignments: readonly AssignmentRecord[];
  selectedId: string | null;
  mode: "browse" | "create";
  draft: AssignmentInput;
  busy: boolean;
  notice: { kind: "ok" | "error"; message: string } | null;
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
    note: null,
  };
}

export function mountWorkspaceAssignmentsPage(host: HTMLElement, options: AssignmentPageOptions): void {
  if (host.dataset.assignmentsMounted === "true") return;
  host.dataset.assignmentsMounted = "true";
  const { transport, context, locale, activities } = options;
  const state: PageState = {
    status: "loading",
    errorCode: null,
    assignments: [],
    selectedId: null,
    mode: "browse",
    draft: emptyDraft(),
    busy: false,
    notice: null,
  };

  const say = (en: string, fa: string): string => text(locale, en, fa);
  const selected = (): AssignmentRecord | null =>
    state.assignments.find((item) => item.assignmentId === state.selectedId) ?? null;
  const activityLabel = (id: string): string => {
    const activity = activities.find((item) => item.id === id);
    return activity ? `${activity.code} ${activity.name}` : id;
  };

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
    const rows = state.assignments.map((item) => {
      const active = item.assignmentId === state.selectedId;
      return `<tr data-assignment-row data-assignment-id="${escapeHtml(item.assignmentId)}" tabindex="0" role="button" aria-selected="${active}" class="${active ? "is-selected" : ""}"><td><strong>${escapeHtml(item.assignmentId)}</strong></td><td>${escapeHtml(activityLabel(item.activityId))}</td><td>${escapeHtml(item.resourceId)}</td><td>${escapeHtml(item.roleId ?? "—")}</td><td>${escapeHtml(item.units ?? "—")}</td><td>${escapeHtml(item.unit ?? "—")}</td><td>${escapeHtml(item.plannedCost ?? "—")}</td><td>${escapeHtml(item.currency ?? "—")}</td></tr>`;
    }).join("");
    return `<div class="cp-register-table-wrap"><table><thead><tr><th>${escapeHtml(say("Assignment ID", "شناسه تخصیص"))}</th><th>${escapeHtml(say("Activity", "فعالیت"))}</th><th>${escapeHtml(say("Resource", "منبع"))}</th><th>${escapeHtml(say("Role", "نقش"))}</th><th>${escapeHtml(say("Budgeted Units", "واحد بودجه"))}</th><th>${escapeHtml(say("Unit", "واحد"))}</th><th>${escapeHtml(say("Planned Cost", "هزینه برنامه‌ای"))}</th><th>${escapeHtml(say("Currency", "ارز"))}</th></tr></thead><tbody>${rows}</tbody></table></div>`;
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
      <label class="cp-assignment-note">${escapeHtml(say("Note", "یادداشت"))}<input name="note" value="${escapeHtml(draft.note ?? "")}"></label>
      <div class="cp-calendar-panel-actions"><button type="submit" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Create assignment", "ایجاد تخصیص"))}</button><button type="button" data-assignment-action="cancel">${escapeHtml(say("Cancel", "لغو"))}</button></div>
      <datalist id="cp-assignment-resources">${knownResources.map((id) => `<option value="${escapeHtml(id)}"></option>`).join("")}</datalist>
      <datalist id="cp-assignment-roles">${knownRoles.map((id) => `<option value="${escapeHtml(id)}"></option>`).join("")}</datalist>
    </form>`;
  }

  function renderDetails(): string {
    const item = selected();
    if (state.mode === "create") return renderForm();
    if (!item) {
      return `<p>${escapeHtml(say("Select an assignment from the register to read its stored values.", "برای خواندن مقادیر ذخیره‌شده، یک تخصیص را از فهرست انتخاب کنید."))}</p>`;
    }
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
    <p class="cp-register-notice">${escapeHtml(say("Stored assignments are immutable. Create a new assignment ID to record a changed assignment.", "تخصیص‌های ذخیره‌شده تغییرناپذیرند. برای ثبت تخصیص تغییرکرده، شناسه تخصیص جدید ایجاد کنید."))}</p>`;
  }

  function render(): void {
    host.innerHTML = `<div class="cp-register-toolbar"><strong>${escapeHtml(say("Resource Assignments", "تخصیص منابع"))}</strong><div><button type="button" data-assignment-action="new" ${state.busy ? "disabled" : ""}>${escapeHtml(say("New Assignment", "تخصیص جدید"))}</button><button type="button" data-assignment-action="reload" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Refresh", "به‌روزرسانی"))}</button></div></div>
      ${renderRegister()}
      <section class="cp-register-details"><header><strong>${escapeHtml(say("Assignment Details", "جزئیات تخصیص"))}</strong><span>${selected() ? escapeHtml(selected()?.assignmentId ?? "") : escapeHtml(say("No selection", "بدون انتخاب"))}</span></header><div class="cp-register-detail-content">${renderDetails()}</div></section>
      ${state.notice ? `<p class="cp-calendar-notice" data-assignment-notice data-state="${state.notice.kind}" role="status">${escapeHtml(state.notice.message)}</p>` : ""}`;
  }

  async function reload(keepSelection: string | null): Promise<void> {
    state.status = "loading";
    render();
    const result = await loadAssignments(transport, context);
    if (result.ok) {
      state.status = "loaded";
      state.errorCode = null;
      state.assignments = result.data;
      state.selectedId = keepSelection && result.data.some((item) => item.assignmentId === keepSelection) ? keepSelection : null;
    } else {
      state.status = "error";
      state.errorCode = result.error.code;
    }
    render();
  }

  host.addEventListener("click", (event) => {
    const target = event.target as HTMLElement;
    const row = target.closest<HTMLElement>("[data-assignment-row]");
    if (row?.dataset.assignmentId) {
      state.selectedId = row.dataset.assignmentId;
      state.mode = "browse";
      state.notice = null;
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
    if (!target.name) return;
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
    const target = event.target as HTMLSelectElement;
    if (target.name === "activity-id") state.draft.activityId = target.value;
  });

  host.addEventListener("submit", (event) => {
    const form = event.target as HTMLFormElement;
    if (!form.matches("[data-assignment-form]")) return;
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
  });

  void reload(null);
}
