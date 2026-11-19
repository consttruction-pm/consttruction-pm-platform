/**
 * Edit > Renumber Activity IDs.
 *
 * Reference: Primavera P6 Professional Help G57535-02, "Renumber Activity IDs
 * dialog box" and "Renumber activity IDs in the Activity Table".
 *
 * The dialog plans new identities in the browser so the operator can review
 * every change, then posts one revision-checked renumber request. The server
 * moves the activity and keeps relationships, assignments, codes, notebook,
 * steps, expenses, period actuals, documents and baseline links attached.
 */
import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";

export const ACTIVITY_RENUMBER_CONTRACT = "p6-activity-master-api.v1";

export type RenumberMode = "increment" | "auto-number" | "replace";
export type RenumberableActivity = { id: string; name?: string };

export type RenumberOptions = {
  mode: RenumberMode;
  increment: number;
  prefix: string;
  suffix: number;
  replaceWith: string;
  replaceCount: number;
};

export type RenumberRow = {
  sourceId: string;
  nextId: string;
  /** True when the planned identity is empty, unchanged, or already owned. */
  conflict: boolean;
  reason: "COLLISION" | "UNCHANGED" | "NO_NUMERIC_SUFFIX" | "INVALID" | null;
};

export type RenumberPlan = {
  rows: readonly RenumberRow[];
  conflicts: readonly RenumberRow[];
};

export const DEFAULT_RENUMBER_OPTIONS: RenumberOptions = {
  mode: "increment",
  increment: 10,
  prefix: "",
  suffix: 100,
  replaceWith: "",
  replaceCount: 2,
};

const TRAILING_NUMBER = /^(.*?)(\d+)$/;

function splitActivityId(id: string): { base: string; digits: string; value: number } | null {
  const match = TRAILING_NUMBER.exec(id);
  if (!match) return null;
  return { base: match[1], digits: match[2], value: Number(match[2]) };
}

function padded(base: string, value: number, width: number): string {
  const text = String(value);
  return base + (width > text.length ? text.padStart(width, "0") : text);
}

function positiveInteger(value: number, fallback: number): number {
  return Number.isFinite(value) && value > 0 ? Math.trunc(value) : fallback;
}

function uniqueCandidate(
  candidate: string,
  outside: ReadonlySet<string>,
  used: Set<string>,
): boolean {
  return !outside.has(candidate) && !used.has(candidate);
}

/**
 * Plan every selected identity. A planned ID may take the place of another
 * selected activity's old ID (the server stages each move), but never an ID
 * owned by an activity outside the selection.
 */
export function planRenumber(
  activities: readonly RenumberableActivity[],
  selectedIds: readonly string[],
  options: RenumberOptions,
  overrides: Readonly<Record<string, string>> = {},
): RenumberPlan {
  const selected = new Set(selectedIds.filter((id) => activities.some((activity) => activity.id === id)));
  const ordered = activities.filter((activity) => selected.has(activity.id)).map((activity) => activity.id);
  const outside = new Set(activities.filter((activity) => !selected.has(activity.id)).map((activity) => activity.id));
  const increment = positiveInteger(options.increment, 1);
  const used = new Set<string>();
  const rows: RenumberRow[] = [];

  // Auto-number's reference behaviour allocates above any existing ID that
  // already shares the prefix, so the first generated value is never below a
  // populated range.
  let autoCursor = Number.isFinite(options.suffix) ? Math.trunc(options.suffix) : 100;
  if (options.mode === "auto-number" && options.prefix) {
    const prefixPattern = new RegExp(`^${escapeRegExp(options.prefix)}(\\d+)$`);
    let highest = -1;
    for (const id of outside) {
      const match = prefixPattern.exec(id);
      if (match) highest = Math.max(highest, Number(match[1]));
    }
    if (highest >= autoCursor) autoCursor = highest + increment;
  }

  for (const sourceId of ordered) {
    const override = overrides[sourceId];
    if (typeof override === "string" && override.trim()) {
      const nextId = override.trim();
      const conflict = outside.has(nextId) || used.has(nextId);
      rows.push({ sourceId, nextId, conflict, reason: conflict ? "COLLISION" : null });
      if (!conflict) used.add(nextId);
      continue;
    }
    let nextId = sourceId;
    let reason: RenumberRow["reason"] = null;
    if (options.mode === "increment") {
      const parts = splitActivityId(sourceId);
      if (!parts) {
        reason = "NO_NUMERIC_SUFFIX";
      } else {
        let value = parts.value + increment;
        nextId = padded(parts.base, value, parts.digits.length);
        while (!uniqueCandidate(nextId, outside, used)) {
          value += increment;
          nextId = padded(parts.base, value, parts.digits.length);
        }
      }
    } else if (options.mode === "auto-number") {
      let value = autoCursor;
      nextId = `${options.prefix}${value}`;
      while (!uniqueCandidate(nextId, outside, used)) {
        value += increment;
        nextId = `${options.prefix}${value}`;
      }
      autoCursor = value + increment;
    } else {
      const count = Math.max(0, Math.trunc(options.replaceCount));
      if (!Number.isFinite(count) || count < 0) {
        reason = "INVALID";
      } else {
        nextId = `${options.replaceWith}${sourceId.slice(count)}`;
      }
    }
    const conflict = reason !== null || nextId === sourceId || outside.has(nextId) || used.has(nextId);
    if (nextId !== sourceId && !outside.has(nextId) && !used.has(nextId) && reason === null) {
      used.add(nextId);
    }
    rows.push({
      sourceId,
      nextId,
      conflict,
      reason: reason ?? (nextId === sourceId ? "UNCHANGED" : conflict ? "COLLISION" : null),
    });
  }
  return { rows, conflicts: rows.filter((row) => row.conflict) };
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function escapeHtml(value: string): string {
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

export type RenumberEntry = { activityId: string; newActivityId: string; expectedRevision?: number };

export async function renumberActivityIds(
  transport: ApiTransport,
  context: ProjectContext,
  entries: readonly RenumberEntry[],
  renumberBaselines: boolean,
): Promise<ApiResult<{ mappings: readonly { activityId: string; newActivityId: string }[] }>> {
  if (!transport.post) {
    return { ok: false, error: { code: "TRANSPORT_POST_UNSUPPORTED", retryable: false, message_key: "error.request.invalid", available_actions: [] } };
  }
  const result = await transport.post<Record<string, unknown>, Record<string, unknown>>(
    `/api/projects/${encodeURIComponent(context.project_id)}/p6/activities/renumber`,
    {
      contract_version: ACTIVITY_RENUMBER_CONTRACT,
      entries: entries.map((entry) => ({
        activity_id: entry.activityId,
        new_activity_id: entry.newActivityId,
        expected_revision: entry.expectedRevision,
      })),
      renumber_baselines: renumberBaselines,
    },
    context,
  );
  if (!result.ok) return result;
  const raw = Array.isArray(result.data?.mappings) ? result.data.mappings as Array<Record<string, unknown>> : [];
  return {
    ok: true,
    data: {
      mappings: raw.map((item) => ({
        activityId: String(item.activity_id ?? ""),
        newActivityId: String(item.new_activity_id ?? ""),
      })),
    },
  };
}

export type RenumberDialogInput = {
  locale: string;
  activities: readonly RenumberableActivity[];
  selectedIds: readonly string[];
  defaultRenumberBaselines: boolean;
  onApply: (entries: readonly (RenumberEntry & { expectedRevision: number })[], renumberBaselines: boolean) => Promise<void>;
};

/**
 * P6's Renumber Activity IDs dialog. Preview and validation are local; the
 * apply callback owns the revision reads and the single server transaction.
 */
export function mountActivityRenumberDialog(input: RenumberDialogInput): HTMLDialogElement {
  const fa = input.locale.split("-")[0] === "fa";
  const say = (en: string, persian: string): string => (fa ? persian : en);
  const dialog = document.createElement("dialog");
  dialog.className = "cp-desktop-dialog cp-activity-renumber-dialog";
  dialog.setAttribute("data-activity-renumber-dialog", "");
  const selected = new Set(input.selectedIds);
  const orderedSelected = input.activities.filter((activity) => selected.has(activity.id)).map((activity) => activity.id);
  dialog.innerHTML = `
    <h2>${escapeHtml(say("Renumber Activity IDs", "شماره‌گذاری دوبارهٔ شناسه‌های فعالیت"))}</h2>
    <form method="dialog" data-renumber-form novalidate>
      <fieldset class="cp-dialog-radios">
        <legend>${escapeHtml(say("New ID method", "روش شناسهٔ جدید"))}</legend>
        <label><input type="radio" name="mode" value="increment" checked> ${escapeHtml(say("Increment Activity ID based on selected activities", "افزایش شناسه بر اساس فعالیت‌های انتخاب‌شده"))}</label>
        <label><input type="radio" name="mode" value="auto-number"> ${escapeHtml(say("Auto-number", "شماره‌گذاری خودکار"))}</label>
        <label><input type="radio" name="mode" value="replace"> ${escapeHtml(say("Replace beginning characters", "جایگزینی نویسه‌های آغازین"))}</label>
      </fieldset>
      <div class="cp-detail-form-grid">
        <label class="cp-detail-form-field" data-renumber-field="increment"><span>${escapeHtml(say("Increment value", "مقدار افزایش"))}</span><input name="increment" type="number" min="1" step="1" value="10"></label>
        <label class="cp-detail-form-field" data-renumber-field="auto-number"><span>${escapeHtml(say("Prefix", "پیشوند"))}</span><input name="prefix" type="text" autocomplete="off"></label>
        <label class="cp-detail-form-field" data-renumber-field="auto-number"><span>${escapeHtml(say("Suffix (start number)", "پسوند (شمارهٔ شروع)"))}</span><input name="suffix" type="number" step="1" value="100"></label>
        <label class="cp-detail-form-field" data-renumber-field="replace"><span>${escapeHtml(say("Replace with", "جایگزینی با"))}</span><input name="replaceWith" type="text" autocomplete="off"></label>
        <label class="cp-detail-form-field" data-renumber-field="replace"><span>${escapeHtml(say("Number of characters", "تعداد نویسه‌ها"))}</span><input name="replaceCount" type="number" min="0" step="1" value="2"></label>
      </div>
      <label class="cp-detail-check"><input name="renumberBaselines" type="checkbox" ${input.defaultRenumberBaselines ? "checked" : ""}> ${escapeHtml(say("Renumber selected activities in baselines", "شماره‌گذاری دوبارهٔ فعالیت‌های انتخاب‌شده در خطوط مبنا"))}</label>
      <div class="cp-detail-table-wrap"><table class="cp-detail-table" data-renumber-preview><thead><tr><th>${escapeHtml(say("Activity ID", "شناسهٔ فعالیت"))}</th><th>${escapeHtml(say("New ID", "شناسهٔ جدید"))}</th><th>${escapeHtml(say("State", "وضعیت"))}</th></tr></thead><tbody></tbody></table></div>
      <p class="cp-detail-hint" data-renumber-status role="status"></p>
      <div class="cp-detail-form-actions">
        <button type="submit" class="cp-detail-action" data-renumber-apply>${escapeHtml(say("Renumber", "شماره‌گذاری دوباره"))}</button>
        <button type="button" class="cp-detail-action" data-renumber-cancel>${escapeHtml(say("Cancel", "لغو"))}</button>
      </div>
    </form>`;
  const form = dialog.querySelector<HTMLFormElement>("[data-renumber-form]");
  const preview = dialog.querySelector<HTMLTableSectionElement>("[data-renumber-preview] tbody");
  const status = dialog.querySelector<HTMLElement>("[data-renumber-status]");
  const apply = dialog.querySelector<HTMLButtonElement>("[data-renumber-apply]");
  const overrides: Record<string, string> = {};
  const readOptions = (): RenumberOptions => ({
    mode: (form?.querySelector<HTMLInputElement>('input[name="mode"]:checked')?.value as RenumberMode) ?? "increment",
    increment: Number(form?.querySelector<HTMLInputElement>('[name="increment"]')?.value ?? 10),
    prefix: form?.querySelector<HTMLInputElement>('[name="prefix"]')?.value ?? "",
    suffix: Number(form?.querySelector<HTMLInputElement>('[name="suffix"]')?.value ?? 100),
    replaceWith: form?.querySelector<HTMLInputElement>('[name="replaceWith"]')?.value ?? "",
    replaceCount: Number(form?.querySelector<HTMLInputElement>('[name="replaceCount"]')?.value ?? 2),
  });
  const syncModeFields = (): void => {
    const mode = readOptions().mode;
    for (const field of dialog.querySelectorAll<HTMLElement>("[data-renumber-field]")) {
      field.hidden = field.dataset.renumberField !== mode;
    }
  };
  const renderPreview = (): RenumberPlan => {
    const plan = planRenumber(input.activities, orderedSelected, readOptions(), overrides);
    if (preview) {
      preview.innerHTML = plan.rows.length
        ? plan.rows.map((row) => `<tr data-renumber-row="${escapeHtml(row.sourceId)}" data-conflict="${row.conflict ? "true" : "false"}">
            <td>${escapeHtml(row.sourceId)}</td>
            <td><input type="text" data-renumber-next="${escapeHtml(row.sourceId)}" value="${escapeHtml(row.nextId)}" maxlength="80" autocomplete="off" aria-label="${escapeHtml(say("New activity ID", "شناسهٔ جدید فعالیت"))}"></td>
            <td>${escapeHtml(row.conflict ? renumberReasonText(row, fa) : say("Ready", "آماده"))}</td>
          </tr>`).join("")
        : `<tr><td colspan="3" class="cp-detail-none">${escapeHtml(say("Select at least one activity.", "حداقل یک فعالیت را انتخاب کنید."))}</td></tr>`;
    }
    const changed = plan.rows.filter((row) => !row.conflict && row.nextId !== row.sourceId).length;
    if (status) {
      status.dataset.state = plan.conflicts.length ? "error" : "ready";
      status.textContent = plan.conflicts.length
        ? say(`${plan.conflicts.length} duplicate or invalid ID(s) must be resolved.`, `${plan.conflicts.length} شناسهٔ تکراری یا نامعتبر باید اصلاح شود.`)
        : say(`${changed} activity ID(s) will change.`, `${changed} شناسهٔ فعالیت تغییر می‌کند.`);
    }
    if (apply) apply.disabled = plan.conflicts.length > 0 || changed === 0;
    return plan;
  };
  const refresh = (): void => {
    syncModeFields();
    renderPreview();
  };
  form?.addEventListener("input", (event) => {
    const target = event.target as HTMLInputElement | null;
    const sourceId = target?.dataset.renumberNext;
    if (sourceId && target) {
      overrides[sourceId] = target.value;
      // Repaint only the state/count so the field being typed keeps focus.
      const plan = planRenumber(input.activities, orderedSelected, readOptions(), overrides);
      for (const row of plan.rows) {
        const tr = dialog.querySelector<HTMLElement>(`[data-renumber-row="${cssEscape(row.sourceId)}"]`);
        if (!tr) continue;
        tr.dataset.conflict = row.conflict ? "true" : "false";
        const stateCell = tr.lastElementChild;
        if (stateCell) stateCell.textContent = row.conflict ? renumberReasonText(row, fa) : say("Ready", "آماده");
      }
      const changed = plan.rows.filter((row) => !row.conflict && row.nextId !== row.sourceId).length;
      if (status) {
        status.dataset.state = plan.conflicts.length ? "error" : "ready";
        status.textContent = plan.conflicts.length
          ? say(`${plan.conflicts.length} duplicate or invalid ID(s) must be resolved.`, `${plan.conflicts.length} شناسهٔ تکراری یا نامعتبر باید اصلاح شود.`)
          : say(`${changed} activity ID(s) will change.`, `${changed} شناسهٔ فعالیت تغییر می‌کند.`);
      }
      if (apply) apply.disabled = plan.conflicts.length > 0 || changed === 0;
      return;
    }
    refresh();
  });
  form?.addEventListener("change", refresh);
  dialog.querySelector("[data-renumber-cancel]")?.addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", () => dialog.remove());
  form?.addEventListener("submit", (event) => {
    event.preventDefault();
    const plan = renderPreview();
    if (plan.conflicts.length) return;
    const entries = plan.rows
      .filter((row) => row.nextId !== row.sourceId)
      .map((row) => ({ activityId: row.sourceId, newActivityId: row.nextId, expectedRevision: 0 }));
    if (!entries.length) return;
    if (apply) apply.disabled = true;
    if (status) status.textContent = say("Renumbering…", "در حال شماره‌گذاری دوباره…");
    const baselines = form?.querySelector<HTMLInputElement>('[name="renumberBaselines"]')?.checked ?? true;
    void input.onApply(entries, baselines).then(() => dialog.close()).catch((error: unknown) => {
      if (apply) apply.disabled = false;
      if (status) {
        status.dataset.state = "error";
        status.textContent = error instanceof Error ? error.message : "RENUMBER_FAILED";
      }
    });
  });
  document.body.append(dialog);
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
  refresh();
  return dialog;
}

function renumberReasonText(row: RenumberRow, fa: boolean): string {
  switch (row.reason) {
    case "COLLISION": return fa ? "شناسه تکراری است" : "Duplicate ID";
    case "UNCHANGED": return fa ? "بدون تغییر" : "Unchanged";
    case "NO_NUMERIC_SUFFIX": return fa ? "شناسه بخش عددی ندارد" : "No numeric suffix";
    default: return fa ? "نامعتبر" : "Invalid";
  }
}

function cssEscape(value: string): string {
  return typeof CSS !== "undefined" && typeof CSS.escape === "function" ? CSS.escape(value) : value.replace(/["\\]/g, "\\$&");
}
