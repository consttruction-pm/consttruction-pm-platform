/**
 * The Columns dialog from the Activities window.
 *
 * The reference dialog transfers fields between Available Columns and Selected
 * Options, reorders them, opens an Edit Column dialog for title/width/alignment
 * and can restore the layout defaults. This implementation edits a local draft
 * so Cancel discards every change; OK/Apply publish the draft through the same
 * persisted layout contract the inline field chooser uses.
 */
import type {
  ColumnPresentation,
  FieldRegistry,
  LayoutDefinition,
  P6Field,
} from "./p6-field-layout-foundation.js";
import {
  createColumnPresentation,
  normalizeLayout,
} from "./p6-field-layout-foundation.js";
import { translateWorkspaceUiText } from "./workspace-localization.js";

export type P6ColumnsDraft = {
  registry: FieldRegistry;
  columns: readonly ColumnPresentation[];
  search: string;
  subject_area: string | null;
  available_selection: string | null;
  selected_selection: string | null;
};

/** A saved layout the Columns dialog can copy its column set from. */
export type P6ColumnsCopySource = {
  scope: "project" | "user";
  name: string;
  layout: LayoutDefinition;
};

export type P6ColumnsDialogOptions = {
  registry: FieldRegistry;
  layout: LayoutDefinition;
  locale: string;
  /** The session may persist a layout; false keeps OK/Apply disabled. */
  canWrite?: boolean;
  /** Authoritative default columns for this view, or null when none exists. */
  loadDefaults: () => Promise<LayoutDefinition | null>;
  /** Other saved layouts for Copy From; omitted when the view has none. */
  loadCopySources?: () => Promise<readonly P6ColumnsCopySource[]>;
  /** Persist the draft and return the saved layout, or null on failure. */
  commit: (draft: LayoutDefinition) => Promise<LayoutDefinition | null>;
  onClosed?: () => void;
};

function t(locale: string, en: string, persian: string): string {
  return translateWorkspaceUiText(locale, en, persian);
}

function esc(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function orderedColumns(layout: LayoutDefinition): ColumnPresentation[] {
  return [...layout.columns].sort((a, b) => a.order - b.order).map((column, index) => ({
    ...column,
    order: index,
  }));
}

function requireField(registry: FieldRegistry, fieldId: string): P6Field {
  const field = registry.fields.find((candidate) => candidate.field_id === fieldId);
  if (!field) throw new Error("UNKNOWN_FIELD");
  return field;
}

export function createP6ColumnsDraft(
  registry: FieldRegistry,
  layout: LayoutDefinition,
): P6ColumnsDraft {
  return {
    registry,
    columns: orderedColumns(layout),
    search: "",
    subject_area: null,
    available_selection: null,
    selected_selection: null,
  };
}

export function availableColumns(draft: P6ColumnsDraft): readonly P6Field[] {
  const selected = new Set(draft.columns.map((column) => column.field_id));
  const query = draft.search.trim().toLocaleLowerCase();
  return draft.registry.fields.filter((field) => {
    if (selected.has(field.field_id)) return false;
    if (draft.subject_area !== null && field.subject_area !== draft.subject_area) return false;
    if (!query) return true;
    return [field.field_id, field.p6_field, field.display_name]
      .some((value) => value.toLocaleLowerCase().includes(query));
  });
}

export function availableSubjects(draft: P6ColumnsDraft): readonly string[] {
  return [...new Set(draft.registry.fields.map((field) => field.subject_area))].sort();
}

export function columnTitle(draft: P6ColumnsDraft, column: ColumnPresentation): string {
  const field = draft.registry.fields.find((item) => item.field_id === column.field_id);
  return column.label ?? field?.display_name ?? column.field_id;
}

export function defaultColumnTitle(draft: P6ColumnsDraft, column: ColumnPresentation): string {
  return draft.registry.fields.find((item) => item.field_id === column.field_id)?.display_name ?? column.field_id;
}

export function columnHasCustomTitle(draft: P6ColumnsDraft, column: ColumnPresentation): boolean {
  return Boolean(column.label) && column.label !== defaultColumnTitle(draft, column);
}

export function setColumnSearch(draft: P6ColumnsDraft, search: string): P6ColumnsDraft {
  return { ...draft, search, available_selection: null };
}

export function setColumnSubjectArea(draft: P6ColumnsDraft, subjectArea: string | null): P6ColumnsDraft {
  return { ...draft, subject_area: subjectArea, available_selection: null };
}

export function selectAvailableColumn(draft: P6ColumnsDraft, fieldId: string | null): P6ColumnsDraft {
  return { ...draft, available_selection: fieldId };
}

export function selectSelectedColumn(draft: P6ColumnsDraft, fieldId: string | null): P6ColumnsDraft {
  return { ...draft, selected_selection: fieldId };
}

export function addAvailableColumn(draft: P6ColumnsDraft, fieldId: string): P6ColumnsDraft {
  const field = requireField(draft.registry, fieldId);
  if (draft.columns.some((column) => column.field_id === fieldId)) return draft;
  const column = createColumnPresentation(field, draft.columns.length);
  return {
    ...draft,
    columns: [...draft.columns, column],
    available_selection: null,
    selected_selection: fieldId,
  };
}

export function addAllAvailableColumns(draft: P6ColumnsDraft): P6ColumnsDraft {
  // Add all adds exactly what the available pane currently lists, so a search
  // or subject filter is never silently bypassed.
  const additions = availableColumns(draft)
    .map((field, index) => createColumnPresentation(field, draft.columns.length + index));
  if (!additions.length) return draft;
  return {
    ...draft,
    columns: [...draft.columns, ...additions],
    available_selection: null,
    selected_selection: additions[additions.length - 1]?.field_id ?? draft.selected_selection,
  };
}

export function removeSelectedColumn(draft: P6ColumnsDraft, fieldId: string): P6ColumnsDraft {
  if (draft.columns.length <= 1) throw new Error("LAST_COLUMN_REQUIRED");
  const index = draft.columns.findIndex((column) => column.field_id === fieldId);
  if (index < 0) return draft;
  const columns = draft.columns.filter((column) => column.field_id !== fieldId);
  return {
    ...draft,
    columns: columns.map((column, order) => ({ ...column, order })),
    selected_selection: columns[Math.min(index, columns.length - 1)]?.field_id ?? null,
  };
}

export function removeAllColumns(draft: P6ColumnsDraft): P6ColumnsDraft {
  if (draft.columns.length <= 1) throw new Error("LAST_COLUMN_REQUIRED");
  // The reference dialog requires at least one displayed column, so Remove All
  // keeps the first column instead of publishing an unusable empty grid.
  const kept = draft.columns[0];
  return {
    ...draft,
    columns: [{ ...kept, order: 0 }],
    available_selection: null,
    selected_selection: kept.field_id,
  };
}

export function moveSelectedColumn(
  draft: P6ColumnsDraft,
  fieldId: string,
  direction: -1 | 1,
): P6ColumnsDraft {
  const index = draft.columns.findIndex((column) => column.field_id === fieldId);
  const target = index + direction;
  if (index < 0 || target < 0 || target >= draft.columns.length) return draft;
  const columns = [...draft.columns];
  const current = columns[index];
  const adjacent = columns[target];
  if (!current || !adjacent) return draft;
  columns[index] = { ...adjacent, order: index };
  columns[target] = { ...current, order: target };
  return { ...draft, columns };
}

export function updateColumnDraft(
  draft: P6ColumnsDraft,
  fieldId: string,
  patch: Partial<Pick<ColumnPresentation, "label" | "width" | "alignment" | "visible" | "pinned" | "frozen">>,
): P6ColumnsDraft {
  let found = false;
  const columns = draft.columns.map((column) => {
    if (column.field_id !== fieldId) return column;
    found = true;
    return { ...column, ...patch };
  });
  if (!found) throw new Error("FIELD_NOT_IN_LAYOUT");
  return { ...draft, columns };
}

/** Restore the default title while keeping width/alignment from the draft. */
export function restoreDefaultTitle(draft: P6ColumnsDraft, fieldId: string): P6ColumnsDraft {
  return updateColumnDraft(draft, fieldId, { label: undefined });
}

export function resetDraftColumns(
  draft: P6ColumnsDraft,
  defaults: readonly ColumnPresentation[],
): P6ColumnsDraft {
  const selected = new Set<ColumnPresentation["field_id"]>();
  const columns: ColumnPresentation[] = [];
  for (const column of defaults) {
    if (selected.has(column.field_id)) continue;
    if (!draft.registry.fields.some((field) => field.field_id === column.field_id)) continue;
    selected.add(column.field_id);
    columns.push({ ...column, order: columns.length });
  }
  if (!columns.length) throw new Error("NO_DEFAULT_COLUMNS");
  return {
    ...draft,
    columns,
    available_selection: null,
    selected_selection: columns[0]?.field_id ?? null,
  };
}

/**
 * Replace the draft column set with another saved layout's columns. Unknown
 * fields are dropped and duplicate ids collapse, so a source from an older
 * registry cannot publish a column the current view does not have.
 */
export function copyColumnsFrom(
  draft: P6ColumnsDraft,
  source: readonly ColumnPresentation[],
): P6ColumnsDraft {
  const seen = new Set<ColumnPresentation["field_id"]>();
  const columns: ColumnPresentation[] = [];
  for (const column of [...source].sort((a, b) => a.order - b.order)) {
    if (seen.has(column.field_id)) continue;
    if (!draft.registry.fields.some((field) => field.field_id === column.field_id)) continue;
    seen.add(column.field_id);
    columns.push({ ...column, order: columns.length });
  }
  if (!columns.length) throw new Error("NO_SOURCE_COLUMNS");
  return {
    ...draft,
    columns,
    available_selection: null,
    selected_selection: columns[0]?.field_id ?? null,
  };
}

export function draftToLayout(draft: P6ColumnsDraft, base: LayoutDefinition): LayoutDefinition {
  return normalizeLayout({ ...base, columns: draft.columns });
}

type DialogUi = {
  dialogTitle: string;
  search: string;
  subject: string;
  allSubjects: string;
  transfer: string;
  availableEmpty: string;
  availableColumns: string;
  selectedOptions: string;
  add: string;
  addAll: string;
  remove: string;
  removeAll: string;
  moveUp: string;
  moveDown: string;
  editColumn: string;
  copyFrom: string;
  copyFromReason: string;
  copyFromHint: string;
  copyFromEmpty: string;
  copyFromTitle: string;
  copySourceProject: string;
  copySourceUser: string;
  copy: string;
  copying: string;
  copyDone: string;
  copyFailed: string;
  defaultAction: string;
  defaultsLoading: string;
  defaultsUnavailable: string;
  readonlyReason: string;
  apply: string;
  ok: string;
  cancel: string;
  help: string;
  title: string;
  width: string;
  alignment: string;
  defaultTitle: string;
  restoreDefault: string;
  hide: string;
  show: string;
  hidden: string;
  lastColumn: string;
  applied: string;
  failed: string;
  start: string;
  center: string;
  end: string;
  close: string;
};

function labels(locale: string): DialogUi {
  return {
    dialogTitle: t(locale, "Columns", "ستون‌ها"),
    search: t(locale, "Search available columns", "جستجوی ستون‌های در دسترس"),
    subject: t(locale, "Subject area", "حوزهٔ موضوعی"),
    allSubjects: t(locale, "All subject areas", "همهٔ حوزه‌ها"),
    transfer: t(locale, "Transfer", "انتقال"),
    availableEmpty: t(locale, "No available columns match.", "هیچ ستون در دسترسی با این جستجو مطابقت ندارد."),
    availableColumns: t(locale, "Available Columns", "ستون‌های در دسترس"),
    selectedOptions: t(locale, "Selected Options", "گزینه‌های انتخاب‌شده"),
    add: t(locale, "Add", "افزودن"),
    addAll: t(locale, "Add all", "افزودن همه"),
    remove: t(locale, "Remove", "حذف"),
    removeAll: t(locale, "Remove all", "حذف همه"),
    moveUp: t(locale, "Move up", "جابه‌جایی به بالا"),
    moveDown: t(locale, "Move down", "جابه‌جایی به پایین"),
    editColumn: t(locale, "Edit Column…", "ویرایش ستون…"),
    copyFrom: t(locale, "Copy From…", "رونوشت از…"),
    copyFromReason: t(
      locale,
      "Copy From needs a second saved activity layout. Save the current columns as a user layout first.",
      "رونوشت از به یک چیدمان ذخیره‌شدهٔ دوم نیاز دارد. ابتدا ستون‌های کنونی را به‌عنوان چیدمان کاربر ذخیره کنید.",
    ),
    copyFromHint: t(
      locale,
      "Copy From replaces the draft with the column set of another saved layout; OK or Apply saves it.",
      "رونوشت از، پیش‌نویس را با مجموعهٔ ستون‌های یک چیدمان ذخیره‌شدهٔ دیگر جایگزین می‌کند؛ تأیید یا اعمال آن را ذخیره می‌کند.",
    ),
    copyFromEmpty: t(
      locale,
      "No other saved activity layout is available to copy from.",
      "هیچ چیدمان ذخیره‌شدهٔ دیگری برای رونوشت وجود ندارد.",
    ),
    copyFromTitle: t(locale, "Copy columns from", "رونوشت ستون‌ها از"),
    copySourceProject: t(locale, "Project layout", "چیدمان پروژه"),
    copySourceUser: t(locale, "User layout", "چیدمان کاربر"),
    copy: t(locale, "Copy", "رونوشت"),
    copying: t(locale, "Reading saved layouts…", "در حال خواندن چیدمان‌های ذخیره‌شده…"),
    copyDone: t(
      locale,
      "Columns copied into the draft. OK or Apply saves them.",
      "ستون‌ها در پیش‌نویس رونوشت شدند. تأیید یا اعمال آن‌ها را ذخیره می‌کند.",
    ),
    copyFailed: t(locale, "The saved layouts could not be read.", "چیدمان‌های ذخیره‌شده خوانده نشدند."),
    readonlyReason: t(
      locale,
      "Your role can inspect columns but cannot save an activity layout.",
      "نقش شما می‌تواند ستون‌ها را ببیند اما نمی‌تواند چیدمان فعالیت را ذخیره کند.",
    ),
    defaultAction: t(locale, "Default", "پیش‌فرض"),
    defaultsLoading: t(locale, "Loading default columns…", "در حال بارگذاری ستون‌های پیش‌فرض…"),
    defaultsUnavailable: t(locale, "The server has no default column definition for this view.", "سرور برای این نما تعریف ستون پیش‌فرض ندارد."),
    apply: t(locale, "Apply", "اعمال"),
    ok: t(locale, "OK", "تأیید"),
    cancel: t(locale, "Cancel", "لغو"),
    help: t(locale, "Help", "راهنما"),
    title: t(locale, "Column title", "عنوان ستون"),
    width: t(locale, "Width", "عرض"),
    alignment: t(locale, "Alignment", "تراز"),
    defaultTitle: t(locale, "Default title", "عنوان پیش‌فرض"),
    restoreDefault: t(locale, "Default", "پیش‌فرض"),
    hide: t(locale, "Hide column", "پنهان‌کردن ستون"),
    show: t(locale, "Show column", "نمایش ستون"),
    hidden: t(locale, "Hidden", "پنهان"),
    lastColumn: t(locale, "At least one column must remain selected.", "دست‌کم یک ستون باید انتخاب‌شده باقی بماند."),
    applied: t(locale, "Columns applied.", "ستون‌ها اعمال شد."),
    failed: t(locale, "The server rejected the columns change; the saved layout was reloaded.", "سرور تغییر ستون‌ها را نپذیرفت؛ چیدمان ذخیره‌شده دوباره بارگذاری شد."),
    start: t(locale, "Left", "چپ"),
    center: t(locale, "Center", "وسط"),
    end: t(locale, "Right", "راست"),
    close: t(locale, "Close", "بستن"),
  };
}

function renderAvailable(draft: P6ColumnsDraft, ui: DialogUi): string {
  const fields = availableColumns(draft);
  if (!fields.length) {
    return `<li class="cp-columns-empty">${esc(ui.availableEmpty)}</li>`;
  }
  return fields.map((field) => {
    const selected = draft.available_selection === field.field_id;
    const title = field.display_name;
    return `<li role="option" tabindex="-1" class="cp-columns-option${selected ? " is-selected" : ""}" data-columns-available-id="${esc(field.field_id)}" aria-selected="${selected ? "true" : "false"}" title="${esc(field.field_id)}">
      <span class="cp-columns-option-title">${esc(title)}</span>
      <small>${esc(field.subject_area)}</small>
    </li>`;
  }).join("");
}

function renderSelected(draft: P6ColumnsDraft, ui: DialogUi): string {
  return draft.columns.map((column) => {
    const selected = draft.selected_selection === column.field_id;
    const title = columnTitle(draft, column);
    const defaultTitle = defaultColumnTitle(draft, column);
    const custom = columnHasCustomTitle(draft, column);
    const field = draft.registry.fields.find((item) => item.field_id === column.field_id);
    const badge = column.visible
      ? esc(field?.subject_area ?? "")
      : `${esc(ui.hidden)} · ${esc(field?.subject_area ?? "")}`;
    return `<li role="option" tabindex="-1" class="cp-columns-option${selected ? " is-selected" : ""}${column.visible ? "" : " is-hidden"}" data-columns-selected-id="${esc(column.field_id)}" aria-selected="${selected ? "true" : "false"}" title="${esc(column.field_id)}">
      <span class="cp-columns-option-title">${esc(title)}${custom ? ` <small class="cp-columns-default-title">(${esc(defaultTitle)})</small>` : ""}</span>
      <small>${badge}</small>
      <button type="button" class="cp-columns-visibility" data-columns-visibility="${esc(column.field_id)}" data-columns-visible="${column.visible ? "true" : "false"}" title="${esc(column.visible ? ui.hide : ui.show)}" aria-label="${esc(column.visible ? ui.hide : ui.show)}">${column.visible ? "◌" : "◉"}</button>
    </li>`;
  }).join("");
}

function subjectOptions(draft: P6ColumnsDraft, ui: DialogUi): string {
  return `<option value="">${esc(ui.allSubjects)}</option>${availableSubjects(draft).map((subject) =>
    `<option value="${esc(subject)}"${draft.subject_area === subject ? " selected" : ""}>${esc(subject)}</option>`,
  ).join("")}`;
}

function renderDialogBody(
  draft: P6ColumnsDraft,
  ui: DialogUi,
  canWrite: boolean,
  hasCopySources: boolean,
): string {
  const available = availableColumns(draft);
  const selected = draft.selected_selection;
  const selectedIndex = selected ? draft.columns.findIndex((column) => column.field_id === selected) : -1;
  const canRemove = selectedIndex >= 0 && draft.columns.length > 1;
  const canRemoveAll = draft.columns.length > 1;
  const copyTitle = hasCopySources ? ui.copyFrom : ui.copyFromReason;
  return `<form method="dialog" data-columns-form>
    <h2 id="cp-columns-heading">${esc(ui.dialogTitle)}</h2>
    ${canWrite ? "" : `<p class="cp-columns-readonly" role="status" data-columns-readonly>${esc(ui.readonlyReason)}</p>`}
    <div class="cp-columns-body">
      <section class="cp-columns-pane cp-columns-available" aria-label="${esc(ui.availableColumns)}">
        <label class="cp-columns-search"><span>${esc(ui.search)}</span>
          <input type="search" data-columns-search value="${esc(draft.search)}" autocomplete="off" spellcheck="false" aria-label="${esc(ui.search)}">
        </label>
        <label class="cp-columns-subject"><span>${esc(ui.subject)}</span>
          <select data-columns-subject aria-label="${esc(ui.subject)}">${subjectOptions(draft, ui)}</select>
        </label>
        <ul class="cp-columns-list" role="listbox" aria-label="${esc(ui.availableColumns)}" data-columns-available>
          ${renderAvailable(draft, ui)}
        </ul>
      </section>
      <div class="cp-columns-transfer" role="group" aria-label="${esc(ui.transfer)}">
        <button type="button" data-columns-action="add" title="${esc(ui.add)}" aria-label="${esc(ui.add)}" ${draft.available_selection ? "" : "disabled"}>›</button>
        <button type="button" data-columns-action="add-all" title="${esc(ui.addAll)}" aria-label="${esc(ui.addAll)}" ${available.length ? "" : "disabled"}>»</button>
        <button type="button" data-columns-action="remove" title="${esc(ui.remove)}" aria-label="${esc(ui.remove)}" ${canRemove ? "" : "disabled"}>‹</button>
        <button type="button" data-columns-action="remove-all" title="${esc(ui.removeAll)}" aria-label="${esc(ui.removeAll)}" ${canRemoveAll ? "" : "disabled"}>«</button>
        <span class="cp-columns-transfer-gap"></span>
        <button type="button" data-columns-action="move-up" title="${esc(ui.moveUp)}" aria-label="${esc(ui.moveUp)}" ${selectedIndex > 0 ? "" : "disabled"}>↑</button>
        <button type="button" data-columns-action="move-down" title="${esc(ui.moveDown)}" aria-label="${esc(ui.moveDown)}" ${selectedIndex >= 0 && selectedIndex < draft.columns.length - 1 ? "" : "disabled"}>↓</button>
      </div>
      <section class="cp-columns-pane cp-columns-selected" aria-label="${esc(ui.selectedOptions)}">
        <header class="cp-columns-pane-head"><strong>${esc(ui.selectedOptions)}</strong><small>${draft.columns.length}</small></header>
        <ul class="cp-columns-list" role="listbox" aria-label="${esc(ui.selectedOptions)}" data-columns-selected>
          ${renderSelected(draft, ui)}
        </ul>
      </section>
    </div>
    <div class="cp-columns-footer">
      <button type="button" data-columns-action="edit" ${selectedIndex >= 0 ? "" : "disabled"}>${esc(ui.editColumn)}</button>
      <button type="button" data-columns-action="copy-from" title="${esc(copyTitle)}" ${hasCopySources ? "" : "disabled"} aria-describedby="cp-columns-copy-note">${esc(ui.copyFrom)}</button>
      <button type="button" data-columns-action="default">${esc(ui.defaultAction)}</button>
      <span class="cp-columns-notice" role="status" aria-live="polite" data-columns-notice></span>
      <span class="cp-dialog-buttons">
        <button type="submit" class="cp-dialog-primary" data-columns-ok ${canWrite ? "" : `disabled title="${esc(ui.readonlyReason)}"`}>${esc(ui.ok)}</button>
        <button type="button" data-columns-apply ${canWrite ? "" : `disabled title="${esc(ui.readonlyReason)}"`}>${esc(ui.apply)}</button>
        <button type="button" data-columns-cancel>${esc(ui.cancel)}</button>
        <button type="button" data-columns-help title="${esc(t("", "Columns help", "راهنمای ستون‌ها"))}">${esc(ui.help)}</button>
      </span>
    </div>
    <p class="cp-dialog-note" id="cp-columns-copy-note">${esc(ui.copyFromHint)}</p>
  </form>`;
}

function helpText(locale: string): string {
  return t(
    locale,
    "Select a field, then use the transfer buttons to add or remove it. Move Up/Down changes the display order. Edit Column changes the title, width and alignment; Default restores the server's default column set. OK saves and closes; Apply saves without closing; Cancel discards the draft.",
    "یک فیلد را انتخاب کنید و با دکمه‌های انتقال آن را اضافه یا حذف کنید. بالا/پایین ترتیب نمایش را تغییر می‌دهد. ویرایش ستون عنوان، عرض و تراز را تغییر می‌دهد؛ پیش‌فرض مجموعهٔ ستون‌های پیش‌فرض سرور را بازمی‌گرداند. تأیید ذخیره و بستن، اعمال ذخیره بدون بستن و لغو دورانداختن پیش‌نویس است.",
  );
}

/**
 * Mount the modal dialog. The dialog lives in the document body so a workspace
 * re-render cannot discard the draft while the user is transferring columns.
 */
export function openP6ColumnsDialog(options: P6ColumnsDialogOptions): void {
  document.querySelectorAll<HTMLElement>("[data-p6-columns-dialog], [data-p6-edit-column-dialog]").forEach((element) => element.remove());
  const ui = labels(options.locale);
  const canWrite = options.canWrite !== false;
  const hasCopySources = typeof options.loadCopySources === "function";
  let draft = createP6ColumnsDraft(options.registry, options.layout);
  let base = options.layout;
  let busy = false;

  const dialog = document.createElement("dialog");
  dialog.className = "cp-desktop-dialog cp-columns-dialog";
  dialog.dataset.p6ColumnsDialog = "";
  dialog.setAttribute("aria-labelledby", "cp-columns-heading");
  document.body.append(dialog);

  const notice = (message: string, isError = false): void => {
    const element = dialog.querySelector<HTMLElement>("[data-columns-notice]");
    if (!element) return;
    element.textContent = message;
    element.dataset.state = isError ? "error" : "ok";
  };

  const render = (focusSearch = false): void => {
    const active = document.activeElement as HTMLElement | null;
    const preserveSearch = Boolean(active?.matches("[data-columns-search]"));
    const caret = preserveSearch ? (active as HTMLInputElement).selectionStart : null;
    dialog.innerHTML = renderDialogBody(draft, ui, canWrite, hasCopySources);
    if (preserveSearch || focusSearch) {
      const search = dialog.querySelector<HTMLInputElement>("[data-columns-search]");
      if (search) {
        search.focus({ preventScroll: true });
        if (caret !== null) {
          const end = Math.min(caret, search.value.length);
          search.setSelectionRange(end, end);
        }
      }
    }
  };

  const close = (): void => {
    if (typeof dialog.close === "function" && dialog.open) {
      // The close event owns removal so Escape and OK follow one path.
      dialog.close();
      return;
    }
    dialog.remove();
    options.onClosed?.();
  };

  const commit = async (closeAfter: boolean): Promise<void> => {
    if (busy || !canWrite) return;
    busy = true;
    const target = draftToLayout(draft, base);
    let saved: LayoutDefinition | null = null;
    try {
      saved = await options.commit({ ...target, revision: base.revision + 1 });
    } catch (error) {
      console.error("P6 columns save failed", error);
      saved = null;
    }
    busy = false;
    if (!saved) {
      notice(ui.failed, true);
      close();
      return;
    }
    base = saved;
    if (closeAfter) {
      close();
    } else {
      notice(ui.applied);
    }
  };

  const openEdit = (fieldId: string): void => {
    const column = draft.columns.find((item) => item.field_id === fieldId);
    if (!column) return;
    const defaultTitle = defaultColumnTitle(draft, column);
    const editor = document.createElement("dialog");
    editor.className = "cp-desktop-dialog cp-edit-column-dialog";
    editor.dataset.p6EditColumnDialog = "";
    editor.innerHTML = `<form method="dialog" data-edit-column-form>
      <h2>${esc(ui.editColumn.replace("…", ""))}</h2>
      <label class="cp-dialog-row"><span>${esc(ui.title)}</span>
        <input type="text" name="title" value="${esc(column.label ?? defaultTitle)}" maxlength="120" autocomplete="off">
      </label>
      <p class="cp-dialog-note">${esc(ui.defaultTitle)}: <strong data-edit-default-title>${esc(defaultTitle)}</strong></p>
      <label class="cp-dialog-row"><span>${esc(ui.width)}</span>
        <input type="number" name="width" min="40" max="800" step="1" value="${esc(String(Math.round(column.width)))}">
      </label>
      <label class="cp-dialog-row"><span>${esc(ui.alignment)}</span>
        <select name="alignment">
          <option value="start"${column.alignment === "start" ? " selected" : ""}>${esc(ui.start)}</option>
          <option value="center"${column.alignment === "center" ? " selected" : ""}>${esc(ui.center)}</option>
          <option value="end"${column.alignment === "end" ? " selected" : ""}>${esc(ui.end)}</option>
        </select>
      </label>
      <div class="cp-dialog-buttons">
        <button type="submit" class="cp-dialog-primary">${esc(ui.ok)}</button>
        <button type="button" data-edit-column-default>${esc(ui.restoreDefault)}</button>
        <button type="button" data-edit-column-cancel>${esc(ui.cancel)}</button>
      </div>
    </form>`;
    document.body.append(editor);
    const removeEditor = (): void => editor.remove();
    editor.addEventListener("close", removeEditor);
    editor.addEventListener("click", (event) => {
      const target = event.target as HTMLElement | null;
      if (target?.closest("[data-edit-column-cancel]")) {
        if (editor.open) editor.close();
        else removeEditor();
        return;
      }
      if (target?.closest("[data-edit-column-default]")) {
        const input = editor.querySelector<HTMLInputElement>('input[name="title"]');
        if (input) input.value = defaultTitle;
      }
    });
    editor.querySelector("form")?.addEventListener("submit", (event) => {
      event.preventDefault();
      const form = editor.querySelector("form");
      if (!form) return;
      const data = new FormData(form);
      const rawTitle = String(data.get("title") ?? "").trim();
      const widthValue = Number(data.get("width"));
      const alignment = data.get("alignment");
      draft = updateColumnDraft(draft, fieldId, {
        label: rawTitle && rawTitle !== defaultTitle ? rawTitle : undefined,
        width: Number.isFinite(widthValue) ? Math.min(800, Math.max(40, Math.round(widthValue))) : column.width,
        alignment: alignment === "center" || alignment === "end" ? alignment : "start",
      });
      if (editor.open) editor.close();
      else removeEditor();
      render();
    });
    if (typeof editor.showModal === "function") editor.showModal();
    else editor.setAttribute("open", "");
    editor.querySelector<HTMLInputElement>('input[name="title"]')?.select();
  };

  /**
   * Copy From lists the other saved layout scopes for this view. It only
   * replaces the draft; persistence still goes through OK/Apply so Cancel
   * always wins.
   */
  const openCopyFrom = async (): Promise<void> => {
    if (!options.loadCopySources) {
      notice(ui.copyFromReason, true);
      return;
    }
    notice(ui.copying);
    let sources: readonly P6ColumnsCopySource[] = [];
    try {
      sources = await options.loadCopySources();
    } catch (error) {
      console.error("P6 layout catalog read failed", error);
      notice(ui.copyFailed, true);
      return;
    }
    if (!sources.length) {
      notice(ui.copyFromEmpty, true);
      return;
    }
    notice("");
    const picker = document.createElement("dialog");
    picker.className = "cp-desktop-dialog cp-copy-columns-dialog";
    picker.dataset.p6CopyColumnsDialog = "";
    const scopeLabel = (scope: P6ColumnsCopySource["scope"]): string =>
      scope === "user" ? ui.copySourceUser : ui.copySourceProject;
    picker.innerHTML = `<form method="dialog" data-copy-columns-form>
      <h2>${esc(ui.copyFromTitle)}</h2>
      <div class="cp-columns-copy-list" role="radiogroup" aria-label="${esc(ui.copyFromTitle)}">
        ${sources.map((source, index) => `<label class="cp-columns-copy-option">
          <input type="radio" name="source" value="${index}"${index === 0 ? " checked" : ""}>
          <span>${esc(source.name || scopeLabel(source.scope))}</span>
          <small>${esc(scopeLabel(source.scope))} · r${source.layout.revision} · ${source.layout.columns.length}</small>
        </label>`).join("")}
      </div>
      <div class="cp-dialog-buttons">
        <button type="submit" class="cp-dialog-primary" data-copy-columns-accept>${esc(ui.copy)}</button>
        <button type="button" data-copy-columns-cancel>${esc(ui.cancel)}</button>
      </div>
    </form>`;
    document.body.append(picker);
    const removePicker = (): void => picker.remove();
    picker.addEventListener("close", removePicker);
    picker.addEventListener("click", (event) => {
      const target = event.target as HTMLElement | null;
      if (target?.closest("[data-copy-columns-cancel]")) {
        if (picker.open) picker.close();
        else removePicker();
      }
    });
    picker.querySelector("form")?.addEventListener("submit", (event) => {
      event.preventDefault();
      const form = picker.querySelector("form");
      const raw = form ? new FormData(form).get("source") : null;
      const source = sources[Number(raw)];
      if (!source) return;
      try {
        draft = copyColumnsFrom(draft, source.layout.columns);
        if (picker.open) picker.close();
        else removePicker();
        render();
        notice(ui.copyDone);
      } catch (error) {
        if (error instanceof Error && error.message === "NO_SOURCE_COLUMNS") notice(ui.copyFromEmpty, true);
        else console.error("P6 copy columns failed", error);
      }
    });
    if (typeof picker.showModal === "function") picker.showModal();
    else picker.setAttribute("open", "");
  };

  dialog.addEventListener("click", (event) => {
    const target = event.target as HTMLElement | null;
    if (!target) return;
    const availableOption = target.closest<HTMLElement>("[data-columns-available-id]");
    if (availableOption?.dataset.columnsAvailableId) {
      draft = selectAvailableColumn(draft, availableOption.dataset.columnsAvailableId);
      render();
      return;
    }
    const visibility = target.closest<HTMLElement>("[data-columns-visibility]");
    if (visibility?.dataset.columnsVisibility) {
      const fieldId = visibility.dataset.columnsVisibility;
      const column = draft.columns.find((item) => item.field_id === fieldId);
      if (column) draft = updateColumnDraft(draft, fieldId, { visible: !column.visible });
      render();
      return;
    }
    const selectedOption = target.closest<HTMLElement>("[data-columns-selected-id]");
    if (selectedOption?.dataset.columnsSelectedId) {
      draft = selectSelectedColumn(draft, selectedOption.dataset.columnsSelectedId);
      render();
      return;
    }
    const action = target.closest<HTMLElement>("[data-columns-action]")?.dataset.columnsAction;
    if (!action) {
      if (target.closest("[data-columns-cancel]")) close();
      else if (target.closest("[data-columns-apply]")) void commit(false);
      else if (target.closest("[data-columns-help]")) notice(helpText(options.locale));
      return;
    }
    try {
      switch (action) {
        case "add":
          if (draft.available_selection) draft = addAvailableColumn(draft, draft.available_selection);
          break;
        case "add-all":
          draft = addAllAvailableColumns(draft);
          break;
        case "remove":
          if (draft.selected_selection) draft = removeSelectedColumn(draft, draft.selected_selection);
          break;
        case "remove-all":
          draft = removeAllColumns(draft);
          break;
        case "move-up":
          if (draft.selected_selection) draft = moveSelectedColumn(draft, draft.selected_selection, -1);
          break;
        case "move-down":
          if (draft.selected_selection) draft = moveSelectedColumn(draft, draft.selected_selection, 1);
          break;
        case "edit":
          if (draft.selected_selection) openEdit(draft.selected_selection);
          return;
        case "copy-from":
          void openCopyFrom();
          return;
        case "default":
          void applyDefaults();
          return;
        default:
          return;
      }
      render();
    } catch (error) {
      if (error instanceof Error && error.message === "LAST_COLUMN_REQUIRED") notice(ui.lastColumn, true);
      else console.error("Columns dialog action failed", error);
    }
  });

  const applyDefaults = async (): Promise<void> => {
    if (busy) return;
    busy = true;
    notice(ui.defaultsLoading);
    try {
      const defaults = await options.loadDefaults();
      if (!defaults) {
        notice(ui.defaultsUnavailable, true);
        return;
      }
      draft = resetDraftColumns(draft, defaults.columns);
      render();
      notice("");
    } catch (error) {
      console.error("P6 default columns read failed", error);
      notice(ui.defaultsUnavailable, true);
    } finally {
      busy = false;
    }
  };

  dialog.addEventListener("input", (event) => {
    const target = event.target as HTMLElement | null;
    const search = target?.closest<HTMLInputElement>("[data-columns-search]");
    if (search) {
      draft = setColumnSearch(draft, search.value);
      render(true);
    }
  });
  dialog.addEventListener("change", (event) => {
    const target = event.target as HTMLElement | null;
    const subject = target?.closest<HTMLSelectElement>("[data-columns-subject]");
    if (subject) {
      draft = setColumnSubjectArea(draft, subject.value || null);
      render();
    }
  });
  dialog.addEventListener("submit", (event) => {
    event.preventDefault();
    void commit(true);
  });
  dialog.addEventListener("close", () => {
    dialog.remove();
    options.onClosed?.();
  });

  render(true);
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
}
