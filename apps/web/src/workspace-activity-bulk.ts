/**
 * Find and Replace for the Activities table (Edit > Replace, Ctrl+R).
 *
 * The plan is computed in the browser from the displayed activity names, but
 * every change is written through the Activity Master PATCH contract with the
 * record revision the server last returned.
 */
export type ReplaceableActivity = { id: string; name: string };
export type ReplacementEdit = { id: string; name: string; next: string };

export type ReplacementOptions = {
  find: string;
  replace: string;
  matchCase: boolean;
  onlySelected: boolean;
  selectedIds?: readonly string[];
};

function normalize(value: string, matchCase: boolean): string {
  return matchCase ? value : value.toLocaleLowerCase();
}

export function planActivityReplacements(
  activities: readonly ReplaceableActivity[],
  options: ReplacementOptions,
): readonly ReplacementEdit[] {
  const find = options.find;
  if (!find) return [];
  const selected = new Set(options.selectedIds ?? []);
  const needle = normalize(find, options.matchCase);
  const edits: ReplacementEdit[] = [];
  for (const activity of activities) {
    if (options.onlySelected && !selected.has(activity.id)) continue;
    const haystack = normalize(activity.name, options.matchCase);
    if (!haystack.includes(needle)) continue;
    let cursor = 0;
    let next = "";
    while (cursor < activity.name.length) {
      const index = normalize(activity.name, options.matchCase).indexOf(needle, cursor);
      if (index < 0) {
        next += activity.name.slice(cursor);
        break;
      }
      next += activity.name.slice(cursor, index) + options.replace;
      cursor = index + find.length;
    }
    if (next !== activity.name) edits.push({ id: activity.id, name: activity.name, next });
  }
  return edits;
}

function escapeHtml(value: string): string {
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

/**
 * P6 Edit > Fill Down copies the value of the first selected row down the
 * selected rows in the same column. CUBI applies it to the Activity Name, the
 * one table field with an editable contract shared by every row.
 */
export function planFillDown(
  activities: readonly ReplaceableActivity[],
  selectedIds: readonly string[],
): readonly ReplacementEdit[] {
  const ordered = selectedIds
    .map((id) => activities.find((activity) => activity.id === id))
    .filter((activity): activity is ReplaceableActivity => Boolean(activity));
  if (ordered.length < 2) return [];
  const source = ordered[0];
  return ordered.slice(1)
    .filter((activity) => activity.name !== source.name)
    .map((activity) => ({ id: activity.id, name: activity.name, next: source.name }));
}

export type SpellDialogInput = {
  locale: string;
  activities: readonly ReplaceableActivity[];
  onApply: (edits: readonly ReplacementEdit[]) => Promise<void>;
};

/**
 * P6 Edit > Spell Check. Detection is delegated to the browser's own
 * spellchecker (the inputs carry spellcheck="true"); CUBI adds the review and
 * the revision-checked save instead of shipping a private word list.
 */
export function mountActivitySpellCheckDialog(input: SpellDialogInput): HTMLDialogElement {
  const fa = input.locale.split("-")[0] === "fa";
  const say = (en: string, persian: string): string => (fa ? persian : en);
  const dialog = document.createElement("dialog");
  dialog.className = "cp-desktop-dialog cp-activity-bulk-dialog cp-activity-spell-dialog";
  dialog.setAttribute("data-activity-spell-dialog", "");
  dialog.innerHTML = `
    <h2>${escapeHtml(say("Spell Check Activity Names", "غلط‌یابی نام فعالیت‌ها"))}</h2>
    <p class="cp-detail-hint">${escapeHtml(say(
      "The browser highlights misspellings in these fields. Correct a name and save; every write carries the record revision.",
      "مرورگر غلط‌های املایی این فیلدها را نشان می‌دهد. نام را اصلاح و ذخیره کنید؛ هر نوشتن نسخهٔ رکورد را همراه دارد.",
    ))}</p>
    <div class="cp-activity-spell-list">
      ${input.activities.map((activity) => `<label class="cp-detail-form-field"><span>${escapeHtml(activity.id)}</span><input type="text" spellcheck="true" data-spell-id="${escapeHtml(activity.id)}" value="${escapeHtml(activity.name)}"></label>`).join("")}
    </div>
    <p class="cp-detail-hint" data-spell-status role="status"></p>
    <div class="cp-detail-form-actions">
      <button type="button" class="cp-detail-action" data-spell-save>${escapeHtml(say("Save corrected names", "ذخیرهٔ نام‌های اصلاح‌شده"))}</button>
      <button type="button" class="cp-detail-action" data-spell-cancel>${escapeHtml(say("Cancel", "لغو"))}</button>
    </div>`;
  const status = dialog.querySelector<HTMLElement>("[data-spell-status]");
  const save = dialog.querySelector<HTMLButtonElement>("[data-spell-save]");
  dialog.querySelector("[data-spell-cancel]")?.addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", () => dialog.remove());
  save?.addEventListener("click", () => {
    const edits: ReplacementEdit[] = [];
    for (const field of dialog.querySelectorAll<HTMLInputElement>("[data-spell-id]")) {
      const id = field.dataset.spellId ?? "";
      const original = input.activities.find((activity) => activity.id === id);
      const next = field.value.trim();
      if (!original || !next || next === original.name) continue;
      edits.push({ id, name: original.name, next });
    }
    if (!edits.length) {
      if (status) status.textContent = say("No name was changed.", "هیچ نامی تغییر نکرد.");
      return;
    }
    if (save) save.disabled = true;
    if (status) status.textContent = say("Saving…", "در حال ذخیره…");
    void input.onApply(edits).then(() => dialog.close()).catch((error: unknown) => {
      if (save) save.disabled = false;
      if (status) {
        status.dataset.state = "error";
        status.textContent = error instanceof Error ? error.message : "SPELL_SAVE_FAILED";
      }
    });
  });
  document.body.append(dialog);
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
  return dialog;
}

export type ReplaceDialogInput = {
  locale: string;
  activities: readonly ReplaceableActivity[];
  selectedIds: readonly string[];
  onApply: (edits: readonly ReplacementEdit[]) => Promise<void>;
};

/**
 * P6's Edit > Replace dialog. The preview count updates before applying so the
 * operator never replaces across a larger set than the one they reviewed.
 */
export function mountActivityReplaceDialog(input: ReplaceDialogInput): HTMLDialogElement {
  const fa = input.locale.split("-")[0] === "fa";
  const say = (en: string, persian: string): string => (fa ? persian : en);
  const dialog = document.createElement("dialog");
  dialog.className = "cp-desktop-dialog cp-activity-bulk-dialog";
  dialog.setAttribute("data-activity-replace-dialog", "");
  dialog.innerHTML = `
    <h2>${escapeHtml(say("Replace in Activity Names", "جایگزینی در نام فعالیت‌ها"))}</h2>
    <form method="dialog" data-activity-replace-form novalidate>
      <label class="cp-detail-form-field"><span>${escapeHtml(say("Find what", "یافتن"))}</span><input name="find" type="text" required autocomplete="off"></label>
      <label class="cp-detail-form-field"><span>${escapeHtml(say("Replace with", "جایگزینی با"))}</span><input name="replace" type="text" autocomplete="off"></label>
      <label class="cp-detail-check"><input name="matchCase" type="checkbox"> ${escapeHtml(say("Match case", "تطبیق بزرگی و کوچکی حروف"))}</label>
      <fieldset class="cp-dialog-radios">
        <legend>${escapeHtml(say("Scope", "دامنه"))}</legend>
        <label><input type="radio" name="scope" value="all" checked> ${escapeHtml(say("All displayed activities", "همهٔ فعالیت‌های نمایش‌داده‌شده"))}</label>
        <label><input type="radio" name="scope" value="selected"> ${escapeHtml(say("Selected activities only", "فقط فعالیت‌های انتخاب‌شده"))}</label>
      </fieldset>
      <p class="cp-detail-hint" data-activity-replace-status role="status"></p>
      <div class="cp-detail-form-actions">
        <button type="submit" class="cp-detail-action" data-activity-replace-apply>${escapeHtml(say("Replace All", "جایگزینی همه"))}</button>
        <button type="button" class="cp-detail-action" data-activity-replace-cancel>${escapeHtml(say("Cancel", "لغو"))}</button>
      </div>
    </form>`;
  const form = dialog.querySelector<HTMLFormElement>("[data-activity-replace-form]");
  const status = dialog.querySelector<HTMLElement>("[data-activity-replace-status]");
  const apply = dialog.querySelector<HTMLButtonElement>("[data-activity-replace-apply]");
  const read = (): ReplacementOptions => ({
    find: form?.querySelector<HTMLInputElement>('[name="find"]')?.value ?? "",
    replace: form?.querySelector<HTMLInputElement>('[name="replace"]')?.value ?? "",
    matchCase: form?.querySelector<HTMLInputElement>('[name="matchCase"]')?.checked ?? false,
    onlySelected: form?.querySelector<HTMLInputElement>('input[name="scope"][value="selected"]')?.checked ?? false,
    selectedIds: input.selectedIds,
  });
  const preview = (): readonly ReplacementEdit[] => planActivityReplacements(input.activities, read());
  const refresh = (): void => {
    if (!status) return;
    const edits = preview();
    status.textContent = edits.length
      ? say(`${edits.length} activity name(s) will change.`, `${edits.length} نام فعالیت تغییر می‌کند.`)
      : say("No displayed activity name matches.", "هیچ نام فعالیت نمایش‌داده‌شده‌ای مطابقت ندارد.");
  };
  form?.addEventListener("input", refresh);
  form?.addEventListener("change", refresh);
  dialog.querySelector("[data-activity-replace-cancel]")?.addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", () => dialog.remove());
  form?.addEventListener("submit", (event) => {
    event.preventDefault();
    const edits = preview();
    if (!edits.length) {
      refresh();
      return;
    }
    if (apply) apply.disabled = true;
    if (status) status.textContent = say("Replacing…", "در حال جایگزینی…");
    void input.onApply(edits).then(() => dialog.close()).catch((error: unknown) => {
      if (apply) apply.disabled = false;
      if (status) {
        status.dataset.state = "error";
        status.textContent = error instanceof Error ? error.message : "REPLACE_FAILED";
      }
    });
  });
  document.body.append(dialog);
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
  refresh();
  return dialog;
}
