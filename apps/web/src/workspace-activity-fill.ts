/**
 * Edit > Fill Down for any editable activity table column.
 *
 * Reference: Primavera P6 Professional Help G57535-02, "Quickly enter the same
 * text in multiple table rows": select the row that holds the value and the
 * rows to receive it, then choose Edit > Fill Down. P6 applies this to table
 * columns that support direct entry, not only to Activity Name.
 *
 * The table remains a projection of the Activity Master. Fill Down therefore
 * reads the source through the Activity Master GET contract, validates the
 * value for the chosen column, and PATCHes each target with its record
 * revision. Nothing is changed only in the browser.
 */

export type FillableColumn = {
  columnId: string;
  apiField: string;
  label: { en: string; fa: string };
  kind: "text" | "decimal" | "integer" | "percent" | "enum";
  allowed?: readonly string[];
};

export const FILLABLE_COLUMNS: readonly FillableColumn[] = [
  { columnId: "activity_name", apiField: "name", label: { en: "Activity Name", fa: "نام فعالیت" }, kind: "text" },
  { columnId: "activity.name", apiField: "name", label: { en: "Activity Name", fa: "نام فعالیت" }, kind: "text" },
  { columnId: "duration", apiField: "duration_value", label: { en: "Duration", fa: "مدت" }, kind: "decimal" },
  { columnId: "progress", apiField: "percent_complete", label: { en: "Progress", fa: "پیشرفت" }, kind: "percent" },
  { columnId: "activity.planned_duration", apiField: "duration_value", label: { en: "Original Duration", fa: "مدت اولیه" }, kind: "decimal" },
  { columnId: "activity.remaining_duration", apiField: "remaining_duration", label: { en: "Remaining Duration", fa: "مدت باقی‌مانده" }, kind: "integer" },
  { columnId: "activity.duration_percent_complete", apiField: "percent_complete", label: { en: "Schedule % Complete", fa: "درصد پیشرفت زمان‌بندی" }, kind: "percent" },
  {
    columnId: "activity.type", apiField: "activity_type", label: { en: "Activity Type", fa: "نوع فعالیت" }, kind: "enum",
    allowed: ["Task Dependent", "Resource Dependent", "Level of Effort", "Start Milestone", "Finish Milestone", "WBS Summary"],
  },
  {
    columnId: "activity_type", apiField: "activity_type", label: { en: "Activity Type", fa: "نوع فعالیت" }, kind: "enum",
    allowed: ["Task Dependent", "Resource Dependent", "Level of Effort", "Start Milestone", "Finish Milestone", "WBS Summary"],
  },
  {
    columnId: "activity.status", apiField: "status", label: { en: "Status", fa: "وضعیت" }, kind: "enum",
    allowed: ["Not Started", "In Progress", "Completed"],
  },
  {
    columnId: "status", apiField: "status", label: { en: "Status", fa: "وضعیت" }, kind: "enum",
    allowed: ["Not Started", "In Progress", "Completed"],
  },
  {
    columnId: "activity.status_code", apiField: "status_code", label: { en: "Status Code", fa: "کد وضعیت" }, kind: "enum",
    allowed: ["Planned", "Active", "Inactive"],
  },
  {
    columnId: "status_code", apiField: "status_code", label: { en: "Status Code", fa: "کد وضعیت" }, kind: "enum",
    allowed: ["Planned", "Active", "Inactive"],
  },
  {
    columnId: "activity.leveling_priority", apiField: "leveling_priority", label: { en: "Leveling Priority", fa: "اولویت تسطیح" }, kind: "enum",
    allowed: ["Highest", "High", "Normal", "Low", "Lowest"],
  },
  {
    columnId: "leveling_priority", apiField: "leveling_priority", label: { en: "Leveling Priority", fa: "اولویت تسطیح" }, kind: "enum",
    allowed: ["Highest", "High", "Normal", "Low", "Lowest"],
  },
];

const BY_COLUMN = new Map(FILLABLE_COLUMNS.map((column) => [column.columnId, column]));

/** The active column is fillable only when the layout actually shows it. */
export function fillableColumnFor(
  columnId: string | null,
  visibleColumnIds: readonly string[],
): FillableColumn | null {
  if (!columnId) return null;
  const column = BY_COLUMN.get(columnId);
  if (!column) return null;
  return visibleColumnIds.includes(columnId) ? column : null;
}

export function fillableColumnsFor(visibleColumnIds: readonly string[]): readonly FillableColumn[] {
  return FILLABLE_COLUMNS.filter((column) => visibleColumnIds.includes(column.columnId));
}

export type FillDownEdit = {
  activityId: string;
  payload: Record<string, unknown>;
};

/**
 * Normalize the source value for the target column. An invalid source is
 * rejected before any target is written.
 */
export function buildFillDownPayload(column: FillableColumn, raw: unknown): Record<string, unknown> {
  switch (column.kind) {
    case "text": {
      const value = typeof raw === "string" ? raw.trim() : "";
      if (!value) throw new Error("FILL_DOWN_EMPTY_VALUE");
      return { [column.apiField]: value };
    }
    case "decimal": {
      const value = typeof raw === "number" ? String(raw) : String(raw ?? "").trim();
      if (!/^\d+(\.\d+)?$/.test(value)) throw new Error("FILL_DOWN_INVALID_NUMBER");
      return { [column.apiField]: value };
    }
    case "integer": {
      const value = typeof raw === "number" ? raw : Number(String(raw ?? "").trim());
      if (!Number.isInteger(value) || value < 0) throw new Error("FILL_DOWN_INVALID_INTEGER");
      return { [column.apiField]: value };
    }
    case "percent": {
      const value = typeof raw === "number" ? raw : Number(String(raw ?? "").trim());
      if (!Number.isFinite(value) || value < 0 || value > 100) throw new Error("FILL_DOWN_INVALID_PERCENT");
      return { [column.apiField]: value };
    }
    case "enum": {
      const value = typeof raw === "string" ? raw.trim() : "";
      if (!column.allowed?.includes(value)) throw new Error("FILL_DOWN_INVALID_OPTION");
      return { [column.apiField]: value };
    }
  }
}

/** Extract the authoritative value for the column from an Activity Master DTO. */
export function sourceValueFor(column: FillableColumn, dto: unknown): unknown {
  if (!dto || typeof dto !== "object" || Array.isArray(dto)) return undefined;
  const envelope = dto as Record<string, unknown>;
  const activity = envelope.activity && typeof envelope.activity === "object" && !Array.isArray(envelope.activity)
    ? envelope.activity as Record<string, unknown>
    : envelope;
  return activity[column.apiField];
}

function escapeHtml(value: string): string {
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

export type FillDownDialogInput = {
  locale: string;
  column: FillableColumn;
  sourceId: string;
  valueText: string;
  targetCount: number;
  onApply: () => Promise<void>;
};

/**
 * The confirmation step. P6 writes on Edit > Fill Down, but the table is a
 * projection here; showing the exact value and affected row count keeps a
 * destructive bulk write reviewable before it reaches the server.
 */
export function mountActivityFillDownDialog(input: FillDownDialogInput): HTMLDialogElement {
  const fa = input.locale.split("-")[0] === "fa";
  const say = (en: string, persian: string): string => (fa ? persian : en);
  const dialog = document.createElement("dialog");
  dialog.className = "cp-desktop-dialog cp-activity-fill-dialog";
  dialog.setAttribute("data-activity-fill-dialog", "");
  dialog.innerHTML = `
    <h2>${escapeHtml(say("Fill Down", "پرکردن به پایین"))}</h2>
    <p class="cp-detail-hint">${escapeHtml(say(
      `Copy the ${input.column.label.en} value of ${input.sourceId} to ${input.targetCount} selected activity(ies).`,
      `مقدار ${input.column.label.fa} از ${input.sourceId} به ${input.targetCount} فعالیت انتخاب‌شده منتقل می‌شود.`,
    ))}</p>
    <p class="cp-fill-preview"><span>${escapeHtml(say("Value", "مقدار"))}</span><strong data-fill-value>${escapeHtml(input.valueText)}</strong></p>
    <p class="cp-detail-hint" data-fill-status role="status"></p>
    <div class="cp-detail-form-actions">
      <button type="button" class="cp-detail-action" data-fill-apply>${escapeHtml(say("Fill Down", "پرکردن به پایین"))}</button>
      <button type="button" class="cp-detail-action" data-fill-cancel>${escapeHtml(say("Cancel", "لغو"))}</button>
    </div>`;
  const apply = dialog.querySelector<HTMLButtonElement>("[data-fill-apply]");
  const status = dialog.querySelector<HTMLElement>("[data-fill-status]");
  dialog.querySelector("[data-fill-cancel]")?.addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", () => dialog.remove());
  apply?.addEventListener("click", () => {
    if (apply) apply.disabled = true;
    if (status) status.textContent = say("Saving…", "در حال ذخیره…");
    void input.onApply().then(() => dialog.close()).catch((error: unknown) => {
      if (apply) apply.disabled = false;
      if (status) {
        status.dataset.state = "error";
        status.textContent = error instanceof Error ? error.message : "FILL_DOWN_FAILED";
      }
    });
  });
  document.body.append(dialog);
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
  return dialog;
}
