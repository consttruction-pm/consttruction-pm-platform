/**
 * Edit > Copy / Paste — Copy Activity Options.
 *
 * Reference: Primavera P6 Professional Help G57535-02, "Copy Activity Options
 * dialog box": resource & role assignments (including future period values),
 * relationships (optionally only between copied activities), expenses,
 * activity codes, WPs & Docs, notebook, steps, financial period data and the
 * "do not show this dialog again" preference.
 *
 * The dialog owns only the choice. Paste creates new Activity Master rows and
 * then replays the chosen child records through the services that already own
 * them; relationships are planned here and created through the relationship
 * API so the scheduling core still validates every link.
 */

export type ActivityCopyOptions = {
  resourceRoleAssignments: boolean;
  relationships: boolean;
  onlyBetweenCopied: boolean;
  expenses: boolean;
  activityCodes: boolean;
  wpsAndDocs: boolean;
  notebook: boolean;
  steps: boolean;
  financialPeriodData: boolean;
};

export const DEFAULT_ACTIVITY_COPY_OPTIONS: ActivityCopyOptions = {
  resourceRoleAssignments: true,
  relationships: true,
  onlyBetweenCopied: false,
  expenses: true,
  activityCodes: true,
  wpsAndDocs: true,
  notebook: true,
  steps: true,
  financialPeriodData: true,
};

export const ACTIVITY_COPY_PREFERENCE_KEY = "cubi.activity-copy-options.v1";

export type ActivityCopyPreference = {
  options: ActivityCopyOptions;
  skipDialog: boolean;
};

type StorageLike = Pick<Storage, "getItem" | "setItem">;

function normalizeOptions(value: unknown): ActivityCopyOptions | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const record = value as Record<string, unknown>;
  const next: ActivityCopyOptions = { ...DEFAULT_ACTIVITY_COPY_OPTIONS };
  for (const key of Object.keys(DEFAULT_ACTIVITY_COPY_OPTIONS) as Array<keyof ActivityCopyOptions>) {
    if (typeof record[key] === "boolean") next[key] = record[key] as boolean;
  }
  return next;
}

export function loadActivityCopyPreference(storage: StorageLike): ActivityCopyPreference | null {
  try {
    const raw = storage.getItem(ACTIVITY_COPY_PREFERENCE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    const options = normalizeOptions(parsed.options);
    if (!options) return null;
    return { options, skipDialog: parsed.skipDialog === true };
  } catch {
    return null;
  }
}

export function saveActivityCopyPreference(
  storage: StorageLike,
  options: ActivityCopyOptions,
  skipDialog: boolean,
): void {
  try {
    storage.setItem(ACTIVITY_COPY_PREFERENCE_KEY, JSON.stringify({ options, skipDialog }));
  } catch {
    // A blocked storage area only means the dialog is shown again.
  }
}

export type CopyableRelationship = {
  id: string;
  predecessorId: string;
  successorId: string;
  type: string;
  lagValue: string;
  lagUnit: string;
};

export type CopiedRelationship = {
  predecessorId: string;
  successorId: string;
  type: string;
  lagValue: string;
  lagUnit: string;
};

/**
 * Relationships of a copied activity follow the new activity. A link to an
 * activity outside the copied set is kept when "Only between copied
 * activities" is clear and dropped when it is marked.
 */
export function planCopiedRelationships(
  relationships: readonly CopyableRelationship[],
  sourceIds: readonly string[],
  newIdBySource: ReadonlyMap<string, string>,
  onlyBetweenCopied: boolean,
): readonly CopiedRelationship[] {
  const source = new Set(sourceIds);
  const planned: CopiedRelationship[] = [];
  const seen = new Set<string>();
  for (const relationship of relationships) {
    const predecessorCopied = source.has(relationship.predecessorId);
    const successorCopied = source.has(relationship.successorId);
    if (!predecessorCopied && !successorCopied) continue;
    if (onlyBetweenCopied && !(predecessorCopied && successorCopied)) continue;
    const predecessorId = newIdBySource.get(relationship.predecessorId) ?? relationship.predecessorId;
    const successorId = newIdBySource.get(relationship.successorId) ?? relationship.successorId;
    if (predecessorId === successorId) continue;
    const key = `${predecessorId}|${successorId}|${relationship.type}`;
    if (seen.has(key)) continue;
    seen.add(key);
    planned.push({
      predecessorId,
      successorId,
      type: relationship.type,
      lagValue: relationship.lagValue,
      lagUnit: relationship.lagUnit,
    });
  }
  return planned;
}

/** Deterministic, collision-free child identity derived from a source ID. */
export function nextCopyId(base: string, taken: ReadonlySet<string>, suffix = "-C"): string {
  for (let index = 1; index < 10000; index += 1) {
    const candidate = `${base}${suffix}${index}`;
    if (!taken.has(candidate)) return candidate;
  }
  return `${base}${suffix}${Date.now()}`;
}

function escapeHtml(value: string): string {
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

export type CopyOptionsDialogInput = {
  locale: string;
  options: ActivityCopyOptions;
  activityCount: number;
  onApply: (options: ActivityCopyOptions, skipDialog: boolean) => void;
};

/**
 * P6's Copy Activity Options dialog. The sub-option for relationships is only
 * meaningful while relationships are selected, so it follows that checkbox.
 */
export function mountActivityCopyOptionsDialog(input: CopyOptionsDialogInput): HTMLDialogElement {
  const fa = input.locale.split("-")[0] === "fa";
  const say = (en: string, persian: string): string => (fa ? persian : en);
  const dialog = document.createElement("dialog");
  dialog.className = "cp-desktop-dialog cp-activity-copy-dialog";
  dialog.setAttribute("data-activity-copy-dialog", "");
  const checked = (value: boolean): string => (value ? " checked" : "");
  dialog.innerHTML = `
    <h2>${escapeHtml(say("Copy Activity Options", "گزینه‌های کپی فعالیت"))}</h2>
    <p class="cp-detail-hint">${escapeHtml(say(
      `${input.activityCount} activity(ies) will be pasted with the selected records.`,
      `${input.activityCount} فعالیت با رکوردهای انتخاب‌شده چسبانده می‌شود.`,
    ))}</p>
    <form method="dialog" data-activity-copy-form novalidate>
      <label class="cp-detail-check"><input name="resourceRoleAssignments" type="checkbox"${checked(input.options.resourceRoleAssignments)}> ${escapeHtml(say("Resource & Role Assignments", "تخصیص منابع و نقش‌ها"))}</label>
      <label class="cp-detail-check"><input name="relationships" type="checkbox" data-copy-relationship-master${checked(input.options.relationships)}> ${escapeHtml(say("Relationships", "روابط"))}</label>
      <label class="cp-detail-check cp-detail-check-nested"><input name="onlyBetweenCopied" type="checkbox"${checked(input.options.onlyBetweenCopied)}> ${escapeHtml(say("Only between copied activities", "فقط بین فعالیت‌های کپی‌شده"))}</label>
      <label class="cp-detail-check"><input name="expenses" type="checkbox"${checked(input.options.expenses)}> ${escapeHtml(say("Expenses", "هزینه‌ها"))}</label>
      <label class="cp-detail-check"><input name="activityCodes" type="checkbox"${checked(input.options.activityCodes)}> ${escapeHtml(say("Activity Codes", "کدهای فعالیت"))}</label>
      <label class="cp-detail-check"><input name="wpsAndDocs" type="checkbox"${checked(input.options.wpsAndDocs)}> ${escapeHtml(say("WPs & Docs", "محصولات کاری و اسناد"))}</label>
      <label class="cp-detail-check"><input name="notebook" type="checkbox"${checked(input.options.notebook)}> ${escapeHtml(say("Notebook", "دفترچه"))}</label>
      <label class="cp-detail-check"><input name="steps" type="checkbox"${checked(input.options.steps)}> ${escapeHtml(say("Steps", "گام‌ها"))}</label>
      <label class="cp-detail-check"><input name="financialPeriodData" type="checkbox"${checked(input.options.financialPeriodData)}> ${escapeHtml(say("Financial Period Data", "داده‌های دوره مالی"))}</label>
      <label class="cp-detail-check"><input name="skipDialog" type="checkbox"> ${escapeHtml(say("Do not show this dialog again", "این دیالوگ دیگر نمایش داده نشود"))}</label>
      <p class="cp-detail-hint" data-copy-status role="status"></p>
      <div class="cp-detail-form-actions">
        <button type="submit" class="cp-detail-action" data-copy-apply>${escapeHtml(say("Paste", "چسباندن"))}</button>
        <button type="button" class="cp-detail-action" data-copy-cancel>${escapeHtml(say("Cancel", "لغو"))}</button>
      </div>
    </form>`;
  const form = dialog.querySelector<HTMLFormElement>("[data-activity-copy-form]");
  const master = dialog.querySelector<HTMLInputElement>("[data-copy-relationship-master]");
  const nested = dialog.querySelector<HTMLInputElement>('[name="onlyBetweenCopied"]');
  const syncNested = (): void => {
    if (!master || !nested) return;
    nested.disabled = !master.checked;
    if (!master.checked) nested.checked = false;
  };
  const read = (): { options: ActivityCopyOptions; skipDialog: boolean } => {
    const value = (name: string): boolean => FormQuery.checked(form, name);
    return {
      options: {
        resourceRoleAssignments: value("resourceRoleAssignments"),
        relationships: value("relationships"),
        onlyBetweenCopied: value("onlyBetweenCopied") && value("relationships"),
        expenses: value("expenses"),
        activityCodes: value("activityCodes"),
        wpsAndDocs: value("wpsAndDocs"),
        notebook: value("notebook"),
        steps: value("steps"),
        financialPeriodData: value("financialPeriodData"),
      },
      skipDialog: value("skipDialog"),
    };
  };
  master?.addEventListener("change", syncNested);
  dialog.querySelector("[data-copy-cancel]")?.addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", () => dialog.remove());
  form?.addEventListener("submit", (event) => {
    event.preventDefault();
    const { options, skipDialog } = read();
    dialog.close();
    input.onApply(options, skipDialog);
  });
  syncNested();
  document.body.append(dialog);
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
  return dialog;
}

const FormQuery = {
  checked(form: HTMLFormElement | null, name: string): boolean {
    return form?.querySelector<HTMLInputElement>(`[name="${name}"]`)?.checked ?? false;
  },
};
