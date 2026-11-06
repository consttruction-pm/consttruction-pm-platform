/**
 * Layout option dialogs for the Activities window. They edit the same state the
 * inline controls use (grouping, sorting, timescale, relationships) plus the
 * browser-local presentation model: table font/colours/row height and the Gantt
 * bar-style definitions. Every control applies immediately; there is no
 * decorative option without an effect.
 */
import type { ChromeLayoutState } from "./workspace-chrome.js";
import {
  DEFAULT_PRESENTATION,
  GANTT_BAR_FILTERS,
  GANTT_BAR_KINDS,
  GANTT_BAR_PATTERNS,
  GANTT_BAR_SHAPES,
  GANTT_LABEL_FIELDS,
  GANTT_LABEL_POSITIONS,
  TABLE_FONT_FAMILIES,
  isHexColor,
  normalizeBarStyle,
  normalizePresentation,
  type GanttBarKind,
  type GanttBarStyle,
  type GanttBarStyleSet,
  type TableFontFamily,
  type TablePresentation,
  type WorkspacePresentation,
} from "./workspace-presentation.js";
import { translateWorkspaceUiText } from "./workspace-localization.js";
import {
  ACTIVITY_FILTER_FIELDS,
  ACTIVITY_FILTER_OPERATORS,
  activityFilterFieldLabel,
  activityFilterOperatorLabel,
  deleteActivityFilter,
  findActivityFilter,
  getBuiltinActivityFilters,
  normalizeActivityFilter,
  setActiveActivityFilter,
  upsertActivityFilter,
  type ActivityFilterCriterion,
  type ActivityFilterOperator,
} from "./workspace-activity-filters.js";

export type DesktopSortColumn = { id: string; label: string };

export type DesktopLayoutPatch = {
  groupBy?: "wbs" | "none";
  sortColumnId?: string | null;
  sortDirection?: "asc" | "desc";
  /** Ordered multi-level sort from the Group and Sort dialog. */
  sortLevels?: readonly { columnId: string; direction: "asc" | "desc" }[];
  ganttScale?: ChromeLayoutState["ganttScale"];
  showRelationships?: boolean;
  density?: ChromeLayoutState["density"];
  rowHeight?: number;
  fontSize?: number;
  barHeight?: number;
  barTone?: "crimson" | "vermilion" | "amber";
  fontFamily?: TableFontFamily;
  textColor?: string;
  backgroundColor?: string;
  rowHeightMode?: TablePresentation["rowHeightMode"];
  showIcons?: boolean;
  lineNumbers?: boolean;
  bars?: GanttBarStyleSet;
  presentation?: WorkspacePresentation;
};

export type DialogOptions = {
  locale: string;
  layout: ChromeLayoutState;
  sortColumns: DesktopSortColumn[];
  sortColumnId: string | null;
  sortDirection: "asc" | "desc";
  sortLevels: readonly { columnId: string; direction: "asc" | "desc" }[];
  rowHeight: number;
  fontSize: number;
  barHeight: number;
  barTone: DesktopLayoutPatch["barTone"];
  presentation: WorkspacePresentation;
  dataAvailability: { actual: boolean; baseline: boolean };
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

type Label = [string, string];
const BAR_KIND_LABELS: Record<GanttBarKind, Label> = {
  task: ["Task", "فعالیت"],
  critical: ["Critical", "بحرانی"],
  summary: ["Summary", "خلاصه"],
  milestone: ["Milestone", "نقطه عطف"],
  progress: ["Progress", "پیشرفت"],
  actual: ["Actual", "واقعی"],
  baseline: ["Baseline", "خط مبنا"],
};
const SHAPE_LABELS: Record<string, Label> = {
  bar: ["Bar", "میله"],
  line: ["Line", "خط"],
  "triangle-up": ["Triangle up", "مثلث رو به بالا"],
  "triangle-down": ["Triangle down", "مثلث رو به پایین"],
  diamond: ["Diamond", "لوزی"],
  circle: ["Circle", "دایره"],
  none: ["None", "بدون شکل"],
};
const PATTERN_LABELS: Record<string, Label> = {
  solid: ["Solid", "توپر"],
  striped: ["Striped", "راه‌راه"],
  hatched: ["Hatched", "هاشور"],
  outline: ["Outline", "قاب‌دار"],
};
const FILTER_LABELS: Record<string, Label> = {
  all: ["All activities", "همهٔ فعالیت‌ها"],
  task: ["Tasks and LOE", "فعالیت‌ها و سطح تلاش"],
  critical: ["Critical only", "فقط بحرانی"],
  noncritical: ["Non-critical", "غیربحرانی"],
  milestone: ["Milestones", "نقاط عطف"],
  summary: ["WBS summaries", "خلاصه‌های WBS"],
  "in-progress": ["In progress", "در حال اجرا"],
  completed: ["Completed", "تکمیل‌شده"],
  "not-started": ["Not started", "شروع‌نشده"],
};
const LABEL_FIELD_LABELS: Record<string, Label> = {
  none: ["No label", "بدون برچسب"],
  "activity-id": ["Activity ID", "شناسه فعالیت"],
  "activity-name": ["Activity name", "نام فعالیت"],
  duration: ["Duration", "مدت"],
  progress: ["Progress %", "درصد پیشرفت"],
};
const LABEL_POSITION_LABELS: Record<string, Label> = {
  "inside-left": ["Inside left", "داخل چپ"],
  "inside-center": ["Inside centre", "داخل وسط"],
  "inside-right": ["Inside right", "داخل راست"],
  above: ["Above", "بالا"],
  below: ["Below", "پایین"],
  right: ["Right", "راست"],
};
const FONT_FAMILY_LABELS: Record<TableFontFamily, Label> = {
  system: ["System UI", "قلم سیستم"],
  segoe: ["Segoe UI", "Segoe UI"],
  cairo: ["Cairo", "Cairo"],
  tahoma: ["Tahoma", "Tahoma"],
  consolas: ["Consolas", "Consolas"],
};

function selectOptions(values: readonly string[], labels: Record<string, Label>, selected: string, locale: string): string {
  return values.map((value) => {
    const label = labels[value] ?? [value, value];
    return `<option value="${esc(value)}"${value === selected ? " selected" : ""}>${esc(t(locale, label[0], label[1]))}</option>`;
  }).join("");
}

function buttons(locale: string, includeDefault = false): string {
  return `<div class="cp-dialog-buttons">
    <button type="submit" class="cp-dialog-primary" data-dialog-ok>${esc(t(locale, "OK", "تأیید"))}</button>
    <button type="button" data-dialog-cancel>${esc(t(locale, "Cancel", "لغو"))}</button>
    ${includeDefault ? `<button type="button" data-dialog-default>${esc(t(locale, "Default", "پیش‌فرض"))}</button>` : ""}
    <button type="button" data-dialog-help title="${esc(t(locale, "Keyboard help", "راهنمای کلیدها"))}">${esc(t(locale, "Help", "راهنما"))}</button>
  </div>`;
}

function shell(locale: string, id: string, title: string, body: string, includeDefault = false): string {
  return `<dialog class="cp-desktop-dialog cp-option-dialog" data-desktop-dialog="${id}" aria-labelledby="cp-dialog-${id}-heading">
    <form method="dialog" data-dialog-form="${id}">
      <h2 id="cp-dialog-${id}-heading">${esc(title)}</h2>
      <div class="cp-dialog-body">${body}</div>
      ${buttons(locale, includeDefault)}
    </form>
  </dialog>`;
}

function tableEditor(optionsInput: DialogOptions, includeDisplayOptions: boolean): string {
  const { locale, presentation } = optionsInput;
  const table = presentation.table;
  return `<fieldset class="cp-dialog-group">
      <legend>${esc(t(locale, "Table font and colour", "قلم و رنگ جدول"))}</legend>
      <label class="cp-dialog-row"><span>${esc(t(locale, "Font family", "خانوادهٔ قلم"))}</span>
        <select name="fontFamily">${selectOptions(TABLE_FONT_FAMILIES, FONT_FAMILY_LABELS, table.fontFamily, locale)}</select>
      </label>
      <label class="cp-dialog-row"><span>${esc(t(locale, "Font size", "اندازهٔ قلم"))}</span>
        <select name="fontSize">${[9, 10, 11, 12, 13, 14, 15, 16].map((size) => `<option value="${size}"${table.fontSize === size ? " selected" : ""}>${size} px</option>`).join("")}</select>
      </label>
      <label class="cp-dialog-row"><span>${esc(t(locale, "Text colour", "رنگ متن"))}</span>
        <input type="color" name="textColor" value="${esc(table.textColor)}">
      </label>
      <label class="cp-dialog-row"><span>${esc(t(locale, "Background colour", "رنگ پس‌زمینه"))}</span>
        <input type="color" name="backgroundColor" value="${esc(table.backgroundColor)}">
      </label>
    </fieldset>
    <fieldset class="cp-dialog-group">
      <legend>${esc(t(locale, "Row height", "ارتفاع ردیف"))}</legend>
      <div class="cp-dialog-radios" role="radiogroup" aria-label="${esc(t(locale, "Row height mode", "حالت ارتفاع ردیف"))}">
        <label><input type="radio" name="rowHeightMode" value="keep"${table.rowHeightMode === "keep" ? " checked" : ""}> ${esc(t(locale, "Keep Current", "حفظ وضعیت فعلی"))}</label>
        <label><input type="radio" name="rowHeightMode" value="content"${table.rowHeightMode === "content" ? " checked" : ""}> ${esc(t(locale, "Optimize by content", "تنظیم بر اساس محتوا"))}</label>
        <label><input type="radio" name="rowHeightMode" value="fixed"${table.rowHeightMode === "fixed" ? " checked" : ""}> ${esc(t(locale, "Fixed height for all rows", "ارتفاع ثابت برای همهٔ ردیف‌ها"))}</label>
      </div>
      <label class="cp-dialog-row"><span>${esc(t(locale, "Fixed height", "ارتفاع ثابت"))}</span>
        <input type="number" name="rowHeight" min="18" max="40" step="1" value="${table.rowHeight}">
      </label>
      <label class="cp-dialog-check"><input type="checkbox" name="showIcons"${table.showIcons ? " checked" : ""}> ${esc(t(locale, "Show activity type icons", "نمایش نماد نوع فعالیت"))}</label>
      ${includeDisplayOptions ? `<label class="cp-dialog-check"><input type="checkbox" name="lineNumbers"${table.lineNumbers ? " checked" : ""}> ${esc(t(locale, "Show line numbers", "نمایش شمارهٔ ردیف"))}</label>` : ""}
    </fieldset>`;
}

function barEditor(kind: GanttBarKind, style: GanttBarStyle, locale: string, availability: DialogOptions["dataAvailability"]): string {
  const label = BAR_KIND_LABELS[kind];
  const unavailable = (kind === "actual" && !availability.actual) || (kind === "baseline" && !availability.baseline);
  const note = unavailable
    ? `<p class="cp-dialog-note">${esc(kind === "actual"
      ? t(locale, "No actual start/finish dates are loaded, so this bar cannot be drawn.", "تاریخ واقعی شروع/پایان بارگذاری نشده است؛ این میله رسم نمی‌شود.")
      : t(locale, "No baseline dates are loaded, so this bar cannot be drawn.", "تاریخ خط مبنا بارگذاری نشده است؛ این میله رسم نمی‌شود."))}</p>`
    : "";
  return `<details class="cp-bar-style" data-bar-style="${kind}"${kind === "task" ? " open" : ""}>
    <summary><span class="cp-bar-swatch" style="background:${esc(style.bodyColor)};border-color:${esc(style.borderColor)}"></span><strong>${esc(t(locale, label[0], label[1]))}</strong><label class="cp-dialog-check"><input type="checkbox" name="bar.${kind}.visible"${style.visible && !unavailable ? " checked" : ""}${unavailable ? " disabled" : ""}> ${esc(t(locale, "Show", "نمایش"))}</label></summary>
    <fieldset class="cp-dialog-group"${unavailable ? " disabled" : ""}>
      ${note}
      <div class="cp-dialog-grid">
        <label class="cp-dialog-row"><span>${esc(t(locale, "Filter", "فیلتر"))}</span><select name="bar.${kind}.filter">${selectOptions(GANTT_BAR_FILTERS, FILTER_LABELS, style.filter, locale)}</select></label>
        <label class="cp-dialog-row"><span>${esc(t(locale, "Row", "ردیف"))}</span><select name="bar.${kind}.row">${[1, 2, 3].map((row) => `<option value="${row}"${style.row === row ? " selected" : ""}>${esc(t(locale, `Row ${row}`, `ردیف ${row}`))}</option>`).join("")}</select></label>
        <label class="cp-dialog-row"><span>${esc(t(locale, "Height", "ارتفاع"))}</span><input type="number" name="bar.${kind}.height" min="3" max="24" step="1" value="${style.height}"></label>
        <label class="cp-dialog-row"><span>${esc(t(locale, "Pattern", "الگو"))}</span><select name="bar.${kind}.pattern">${selectOptions(GANTT_BAR_PATTERNS, PATTERN_LABELS, style.pattern, locale)}</select></label>
        <label class="cp-dialog-row"><span>${esc(t(locale, "Start shape", "شکل شروع"))}</span><select name="bar.${kind}.startShape">${selectOptions(GANTT_BAR_SHAPES, SHAPE_LABELS, style.startShape, locale)}</select></label>
        <label class="cp-dialog-row"><span>${esc(t(locale, "Body shape", "شکل بدنه"))}</span><select name="bar.${kind}.bodyShape">${selectOptions(GANTT_BAR_SHAPES, SHAPE_LABELS, style.bodyShape, locale)}</select></label>
        <label class="cp-dialog-row"><span>${esc(t(locale, "Finish shape", "شکل پایان"))}</span><select name="bar.${kind}.finishShape">${selectOptions(GANTT_BAR_SHAPES, SHAPE_LABELS, style.finishShape, locale)}</select></label>
        <label class="cp-dialog-row"><span>${esc(t(locale, "Start colour", "رنگ شروع"))}</span><input type="color" name="bar.${kind}.startColor" value="${esc(style.startColor)}"></label>
        <label class="cp-dialog-row"><span>${esc(t(locale, "Body colour", "رنگ بدنه"))}</span><input type="color" name="bar.${kind}.bodyColor" value="${esc(style.bodyColor)}"></label>
        <label class="cp-dialog-row"><span>${esc(t(locale, "Finish colour", "رنگ پایان"))}</span><input type="color" name="bar.${kind}.finishColor" value="${esc(style.finishColor)}"></label>
        <label class="cp-dialog-row"><span>${esc(t(locale, "Border colour", "رنگ حاشیه"))}</span><input type="color" name="bar.${kind}.borderColor" value="${esc(style.borderColor)}"></label>
        <label class="cp-dialog-row"><span>${esc(t(locale, "Label", "برچسب"))}</span><select name="bar.${kind}.labelField">${selectOptions(GANTT_LABEL_FIELDS, LABEL_FIELD_LABELS, style.labelField, locale)}</select></label>
        <label class="cp-dialog-row"><span>${esc(t(locale, "Label position", "جای برچسب"))}</span><select name="bar.${kind}.labelPosition">${selectOptions(GANTT_LABEL_POSITIONS, LABEL_POSITION_LABELS, style.labelPosition, locale)}</select></label>
      </div>
    </fieldset>
  </details>`;
}

function filterEditor(optionsInput: DialogOptions): string {
  const { locale, presentation } = optionsInput;
  const filters = presentation.filters;
  const active = findActivityFilter(filters, filters.activeId);
  const editingCustom = active && !active.builtin ? active : null;
  const rows = Array.from({ length: 4 }, (_, index) => {
    const criterion = editingCustom?.criteria[index];
    const fieldId = criterion?.fieldId ?? "activity_name";
    const operator = criterion?.operator ?? "contains";
    const value = criterion?.value ?? "";
    return `<div class="cp-filter-row" data-filter-row="${index}">
      <select name="filter.field.${index}" aria-label="${esc(t(locale, "Filter field", "فیلد فیلتر"))}">
        ${ACTIVITY_FILTER_FIELDS.map((id) => `<option value="${id}"${id === fieldId ? " selected" : ""}>${esc(activityFilterFieldLabel(id, locale))}</option>`).join("")}
      </select>
      <select name="filter.operator.${index}" aria-label="${esc(t(locale, "Filter operator", "عملگر فیلتر"))}">
        ${ACTIVITY_FILTER_OPERATORS.map((id) => `<option value="${id}"${id === operator ? " selected" : ""}>${esc(activityFilterOperatorLabel(id, locale))}</option>`).join("")}
      </select>
      <input type="text" name="filter.value.${index}" value="${esc(value)}" aria-label="${esc(t(locale, "Filter value", "مقدار فیلتر"))}" autocomplete="off" spellcheck="false"${operator === "is-empty" || operator === "is-not-empty" ? " disabled" : ""}>
    </div>`;
  }).join("");
  const builtin = getBuiltinActivityFilters();
  const saved = filters.saved;
  const groups = [
    `<option value=""${filters.activeId ? "" : " selected"}>${esc(t(locale, "All activities", "همهٔ فعالیت‌ها"))}</option>`,
    `<optgroup label="${esc(t(locale, "Predefined filters", "فیلترهای پیش‌فرض"))}">${builtin.map((filter) => `<option value="${esc(filter.id)}"${filters.activeId === filter.id ? " selected" : ""}>${esc(t(locale, filter.name, filter.name))}</option>`).join("")}</optgroup>`,
    saved.length > 0 ? `<optgroup label="${esc(t(locale, "Saved filters", "فیلترهای ذخیره‌شده"))}">${saved.map((filter) => `<option value="${esc(filter.id)}"${filters.activeId === filter.id ? " selected" : ""}>${esc(filter.name)}</option>`).join("")}</optgroup>` : "",
  ].join("");
  return `<fieldset class="cp-dialog-group">
      <legend>${esc(t(locale, "Apply a filter", "اعمال فیلتر"))}</legend>
      <label class="cp-dialog-row"><span>${esc(t(locale, "Filter", "فیلتر"))}</span>
        <select name="filterActiveId">${groups}</select>
      </label>
      <p class="cp-dialog-note">${esc(t(locale, "Predefined filters match the documented activity criteria. A filter only narrows the rows on screen; it never changes schedule data.", "فیلترهای پیش‌فرض با معیارهای مستند فعالیت مطابقت دارند. فیلتر فقط ردیف‌های روی صفحه را محدود می‌کند و داده‌های زمان‌بندی را تغییر نمی‌دهد."))}</p>
    </fieldset>
    <fieldset class="cp-dialog-group">
      <legend>${esc(t(locale, "Create or edit a custom filter", "ساخت یا ویرایش فیلتر سفارشی"))}</legend>
      <div class="cp-dialog-grid">
        <label class="cp-dialog-row"><span>${esc(t(locale, "Filter name", "نام فیلتر"))}</span>
          <input type="text" name="filterName" maxlength="60" value="${esc(editingCustom?.name ?? "")}" autocomplete="off">
        </label>
        <label class="cp-dialog-row"><span>${esc(t(locale, "Match", "تطبیق"))}</span>
          <select name="filterMatch">
            <option value="all"${editingCustom?.match !== "any" ? " selected" : ""}>${esc(t(locale, "All criteria (AND)", "همهٔ معیارها (و)"))}</option>
            <option value="any"${editingCustom?.match === "any" ? " selected" : ""}>${esc(t(locale, "Any criterion (OR)", "هر یک از معیارها (یا)"))}</option>
          </select>
        </label>
      </div>
      <div class="cp-filter-criteria" role="group" aria-label="${esc(t(locale, "Filter criteria", "معیارهای فیلتر"))}">
        <div class="cp-filter-head"><span>${esc(t(locale, "Field", "فیلد"))}</span><span>${esc(t(locale, "Is", "است"))}</span><span>${esc(t(locale, "Value", "مقدار"))}</span></div>
        ${rows}
      </div>
      ${editingCustom ? `<label class="cp-dialog-check"><input type="checkbox" name="filterDelete"> ${esc(t(locale, "Delete this saved filter", "این فیلتر ذخیره‌شده حذف شود"))}</label>` : ""}
    </fieldset>`;
}

/**
 * Clears the custom-filter builder when the Apply selection changes. Choosing a
 * predefined or saved entry then applies that selection instead of resaving the
 * criteria still loaded in the form.
 */
export function resetFilterEditor(dialog: HTMLElement): void {
  const name = dialog.querySelector<HTMLInputElement>('input[name="filterName"]');
  if (name) name.value = "";
  const match = dialog.querySelector<HTMLSelectElement>('select[name="filterMatch"]');
  if (match) match.value = "all";
  for (const select of dialog.querySelectorAll<HTMLSelectElement>('select[name^="filter.field."]')) {
    if (select.querySelector('option[value="activity_name"]')) select.value = "activity_name";
  }
  for (const select of dialog.querySelectorAll<HTMLSelectElement>('select[name^="filter.operator."]')) {
    select.value = "contains";
  }
  for (const input of dialog.querySelectorAll<HTMLInputElement>('input[name^="filter.value."]')) {
    input.value = "";
    input.disabled = false;
  }
  dialog.querySelector('input[name="filterDelete"]')?.closest("label")?.remove();
}

export function renderLayoutDialogs(optionsInput: DialogOptions): string {
  const { locale, layout } = optionsInput;
  const sortColumns = optionsInput.sortColumns.some((column) => column.id === "wbs")
    ? optionsInput.sortColumns
    : [{ id: "wbs", label: "WBS" }, ...optionsInput.sortColumns];
  const sortRows = [0, 1, 2].map((index) => {
    const level = optionsInput.sortLevels[index];
    const field = level?.columnId ?? "";
    const direction = level?.direction ?? "asc";
    return `<div class="cp-filter-row cp-sort-row">
      <label><span>${esc(t(locale, `Sort ${index + 1}`, `ترتیب ${index + 1}`))}</span>
        <select name="sort.field.${index}" aria-label="${esc(t(locale, `Sort field ${index + 1}`, `فیلد ترتیب ${index + 1}`))}">
          <option value=""${field ? "" : " selected"}>${esc(t(locale, "No field", "بدون فیلد"))}</option>
          ${sortColumns.map((column) => `<option value="${esc(column.id)}"${field === column.id ? " selected" : ""}>${esc(column.label)}</option>`).join("")}
        </select>
      </label>
      <label><span>${esc(t(locale, "Order", "جهت"))}</span>
        <select name="sort.direction.${index}" aria-label="${esc(t(locale, `Sort order ${index + 1}`, `جهت ترتیب ${index + 1}`))}">
          <option value="asc"${direction === "asc" ? " selected" : ""}>${esc(t(locale, "Ascending", "صعودی"))}</option>
          <option value="desc"${direction === "desc" ? " selected" : ""}>${esc(t(locale, "Descending", "نزولی"))}</option>
        </select>
      </label>
    </div>`;
  }).join("");
  const groupSort = `<fieldset class="cp-dialog-group">
      <legend>${esc(t(locale, "Group by", "گروه‌بندی بر اساس"))}</legend>
      <label class="cp-dialog-row"><span>${esc(t(locale, "Group levels", "سطوح گروه"))}</span>
        <select name="groupBy">
          <option value="wbs"${layout.groupBy === "wbs" ? " selected" : ""}>WBS</option>
          <option value="none"${layout.groupBy === "none" ? " selected" : ""}>${esc(t(locale, "No grouping", "بدون گروه‌بندی"))}</option>
        </select>
      </label>
      <p class="cp-dialog-note">${esc(t(locale, "WBS is the only grouping hierarchy persisted for this project. Other group categories are not loaded by this runtime.", "سلسله‌مراتب WBS تنها گروه‌بندی ذخیره‌شدهٔ این پروژه است. دسته‌های گروه‌بندی دیگر در این محیط بارگذاری نشده‌اند."))}</p>
    </fieldset>
    <fieldset class="cp-dialog-group">
      <legend>${esc(t(locale, "Sort", "ترتیب"))}</legend>
      <p class="cp-dialog-note">${esc(t(locale, "Up to three fields apply in order; the first field also drives the toolbar sort. Empty rows are ignored.", "حداکثر سه فیلد به‌ترتیب اعمال می‌شود؛ فیلد اول ترتیب نوار ابزار را نیز تعیین می‌کند. ردیف‌های خالی نادیده گرفته می‌شوند."))}</p>
      ${sortRows}
    </fieldset>`;

  const timescale = `<fieldset class="cp-dialog-group">
      <legend>${esc(t(locale, "Timescale format", "قالب مقیاس زمانی"))}</legend>
      <label class="cp-dialog-row"><span>${esc(t(locale, "Scale", "مقیاس"))}</span>
        <select name="ganttScale">
          ${(["year", "quarter", "month", "week", "day"] as const).map((scale) => `<option value="${scale}"${layout.ganttScale === scale ? " selected" : ""}>${esc(t(locale, scale[0].toUpperCase() + scale.slice(1), { year: "سال", quarter: "فصل", month: "ماه", week: "هفته", day: "روز" }[scale]))}</option>`).join("")}
        </select>
      </label>
      <label class="cp-dialog-check"><input type="checkbox" name="showRelationships"${layout.showRelationships ? " checked" : ""}> ${esc(t(locale, "Show relationship lines", "نمایش خطوط روابط"))}</label>
    </fieldset>`;

  const bars = `<p class="cp-dialog-note">${esc(t(locale, "Each bar type has independent shape, colour, pattern, filter, row and label settings. Bar geometry still comes from the saved schedule dates.", "هر نوع میله شکل، رنگ، الگو، فیلتر، ردیف و برچسب مستقل دارد. هندسهٔ میله همچنان از تاریخ‌های ذخیره‌شدهٔ زمان‌بندی می‌آید."))}</p>
    <div class="cp-bar-style-list">${GANTT_BAR_KINDS.map((kind) => barEditor(kind, optionsInput.presentation.bars[kind], locale, optionsInput.dataAvailability)).join("")}</div>`;

  const fontRow = tableEditor(optionsInput, false);
  const preferences = `${tableEditor(optionsInput, true)}
    <fieldset class="cp-dialog-group">
      <legend>${esc(t(locale, "Display", "نمایش"))}</legend>
      <p class="cp-dialog-note">${esc(t(locale, "Preferences are stored with the saved layout for this project. They do not change schedule data.", "تنظیمات به‌همراه چیدمان ذخیره‌شدهٔ این پروژه نگهداری می‌شود و داده‌های زمان‌بندی را تغییر نمی‌دهد."))}</p>
    </fieldset>`;

  return [
    shell(locale, "filters", t(locale, "Filters", "فیلترها"), filterEditor(optionsInput), true),
    shell(locale, "group-sort", t(locale, "Group and Sort", "گروه‌بندی و ترتیب"), groupSort, true),
    shell(locale, "timescale", t(locale, "Timescale", "مقیاس زمانی"), timescale),
    shell(locale, "bars", t(locale, "Bar Styles", "سبک میله‌ها"), bars),
    shell(locale, "font-row", t(locale, "Table Font and Row", "قلم و ردیف جدول"), fontRow),
    shell(locale, "user-preferences", t(locale, "User Preferences", "ترجیحات کاربر"), preferences, true),
  ].join("");
}

export function readLayoutPatch(form: HTMLFormElement | FormData, previous?: WorkspacePresentation): DesktopLayoutPatch {
  const data = form instanceof FormData ? form : new FormData(form);
  const patch: DesktopLayoutPatch = {};
  const groupBy = data.get("groupBy");
  if (groupBy === "wbs" || groupBy === "none") patch.groupBy = groupBy;
  if (data.has("sort.field.0")) {
    const sortLevels: { columnId: string; direction: "asc" | "desc" }[] = [];
    for (const index of [0, 1, 2]) {
      const field = String(data.get(`sort.field.${index}`) ?? "");
      if (!field) continue;
      const direction = data.get(`sort.direction.${index}`) === "desc" ? "desc" : "asc";
      sortLevels.push({ columnId: field, direction });
    }
    patch.sortLevels = sortLevels;
    patch.sortColumnId = sortLevels[0]?.columnId ?? null;
    patch.sortDirection = sortLevels[0]?.direction ?? "asc";
  } else if (data.has("sortColumnId")) {
    const value = String(data.get("sortColumnId") ?? "");
    patch.sortColumnId = value || null;
    const direction = data.get("sortDirection");
    if (direction === "asc" || direction === "desc") patch.sortDirection = direction;
  }
  const scale = data.get("ganttScale");
  if (scale === "day" || scale === "week" || scale === "month" || scale === "quarter" || scale === "year") {
    patch.ganttScale = scale;
  }
  if (data.has("showRelationships")) patch.showRelationships = data.get("showRelationships") === "on";
  const density = data.get("density");
  if (density === "compact" || density === "comfortable") patch.density = density;

  const presentation = normalizePresentation(previous ?? DEFAULT_PRESENTATION);
  let presentationChanged = false;

  const rowHeightValue = data.get("rowHeight");
  const rowHeight = Number(rowHeightValue);
  if (typeof rowHeightValue === "string" && rowHeightValue.trim() !== "" && Number.isFinite(rowHeight)) {
    patch.rowHeight = Math.min(40, Math.max(18, Math.round(rowHeight)));
    presentation.table.rowHeight = patch.rowHeight;
    presentationChanged = true;
  }
  const fontSizeValue = data.get("fontSize");
  const fontSize = Number(fontSizeValue);
  if (typeof fontSizeValue === "string" && fontSizeValue.trim() !== "" && Number.isFinite(fontSize)) {
    patch.fontSize = Math.min(16, Math.max(9, Math.round(fontSize)));
    presentation.table.fontSize = patch.fontSize;
    presentationChanged = true;
  }
  const family = data.get("fontFamily");
  if (typeof family === "string" && (TABLE_FONT_FAMILIES as readonly string[]).includes(family)) {
    patch.fontFamily = family as TableFontFamily;
    presentation.table.fontFamily = patch.fontFamily;
    presentationChanged = true;
  }
  const textColor = data.get("textColor");
  if (isHexColor(textColor)) {
    patch.textColor = textColor.toLowerCase();
    presentation.table.textColor = patch.textColor;
    presentationChanged = true;
  }
  const backgroundColor = data.get("backgroundColor");
  if (isHexColor(backgroundColor)) {
    patch.backgroundColor = backgroundColor.toLowerCase();
    presentation.table.backgroundColor = patch.backgroundColor;
    presentationChanged = true;
  }
  const rowHeightMode = data.get("rowHeightMode");
  if (rowHeightMode === "keep" || rowHeightMode === "fixed" || rowHeightMode === "content") {
    patch.rowHeightMode = rowHeightMode;
    presentation.table.rowHeightMode = rowHeightMode;
    presentationChanged = true;
  }
  if (data.has("showIcons")) {
    patch.showIcons = data.get("showIcons") === "on";
    presentation.table.showIcons = patch.showIcons;
    presentationChanged = true;
  }
  if (data.has("lineNumbers")) {
    patch.lineNumbers = data.get("lineNumbers") === "on";
    presentation.table.lineNumbers = patch.lineNumbers;
    presentationChanged = true;
  }

  const keys = Array.from(data.keys());
  if (keys.some((key) => key.startsWith("bar."))) {    const bars = { ...presentation.bars };
    for (const kind of GANTT_BAR_KINDS) {
      const prefix = `bar.${kind}.`;
      if (!keys.some((key) => key.startsWith(prefix))) continue;
      bars[kind] = normalizeBarStyle({
        visible: data.get(`${prefix}visible`) === "on",
        filter: data.get(`${prefix}filter`),
        row: data.get(`${prefix}row`),
        height: data.get(`${prefix}height`),
        pattern: data.get(`${prefix}pattern`),
        startShape: data.get(`${prefix}startShape`),
        bodyShape: data.get(`${prefix}bodyShape`),
        finishShape: data.get(`${prefix}finishShape`),
        startColor: data.get(`${prefix}startColor`),
        bodyColor: data.get(`${prefix}bodyColor`),
        finishColor: data.get(`${prefix}finishColor`),
        borderColor: data.get(`${prefix}borderColor`),
        labelField: data.get(`${prefix}labelField`),
        labelPosition: data.get(`${prefix}labelPosition`),
      }, bars[kind]);
      // A disabled Actual/Baseline fieldset never reaches FormData. Keep its
      // saved appearance, but never draw a bar without authoritative dates.
      if (!data.has(`${prefix}filter`)) bars[kind].visible = false;
    }
    patch.bars = bars;
    presentation.bars = bars;
    presentationChanged = true;
  }

  if (keys.some((key) => key.startsWith("filter.") || key.startsWith("filterActiveId") || key.startsWith("filterName"))) {
    const previousFilters = presentation.filters;
    const previousActive = findActivityFilter(previousFilters, previousFilters.activeId);
    const selectedId = String(data.get("filterActiveId") ?? "");
    const deleteRequested = data.get("filterDelete") === "on";
    const criteria: ActivityFilterCriterion[] = [];
    for (let index = 0; index < 4; index += 1) {
      const fieldId = data.get(`filter.field.${index}`);
      const operator = data.get(`filter.operator.${index}`);
      if (typeof fieldId !== "string" || typeof operator !== "string") continue;
      const value = String(data.get(`filter.value.${index}`) ?? "");
      criteria.push({
        fieldId: fieldId as ActivityFilterCriterion["fieldId"],
        operator: operator as ActivityFilterOperator,
        value,
      });
    }
    const draft = normalizeActivityFilter({
      name: String(data.get("filterName") ?? ""),
      match: data.get("filterMatch"),
      criteria,
    });
    let filters = previousFilters;
    if (deleteRequested && selectedId.startsWith("custom:")) {
      filters = deleteActivityFilter(filters, selectedId);
    } else if (draft) {
      const unchanged = previousActive
        && !previousActive.builtin
        && previousActive.id === draft.id
        && previousActive.match === draft.match
        && JSON.stringify(previousActive.criteria) === JSON.stringify(draft.criteria);
      if (unchanged && selectedId && selectedId !== draft.id) {
        filters = setActiveActivityFilter(filters, selectedId);
      } else {
        filters = upsertActivityFilter(filters, draft);
      }
    } else {
      filters = setActiveActivityFilter(filters, selectedId || null);
    }
    presentation.filters = filters;
    presentationChanged = true;
  }

  if (presentationChanged) patch.presentation = presentation;
  return patch;
}

export function defaultLayoutPatch(): DesktopLayoutPatch {
  return {
    groupBy: "wbs",
    sortColumnId: "wbs",
    sortDirection: "asc",
    sortLevels: [{ columnId: "wbs", direction: "asc" }],
    ganttScale: "day",
    showRelationships: true,
    density: "compact",
    rowHeight: DEFAULT_PRESENTATION.table.rowHeight,
    fontSize: DEFAULT_PRESENTATION.table.fontSize,
    barHeight: 16,
    barTone: "crimson",
    rowHeightMode: DEFAULT_PRESENTATION.table.rowHeightMode,
    fontFamily: DEFAULT_PRESENTATION.table.fontFamily,
    textColor: DEFAULT_PRESENTATION.table.textColor,
    backgroundColor: DEFAULT_PRESENTATION.table.backgroundColor,
    showIcons: DEFAULT_PRESENTATION.table.showIcons,
    lineNumbers: DEFAULT_PRESENTATION.table.lineNumbers,
    bars: DEFAULT_PRESENTATION.bars,
    presentation: DEFAULT_PRESENTATION,
  };
}
