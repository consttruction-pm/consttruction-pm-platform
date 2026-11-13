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
  GANTT_ORDINAL_INTERVALS,
  GANTT_TIMESCALE_INTERVALS,
  TABLE_FONT_FAMILIES,
  isHexColor,
  isIsoDate,
  normalizeBarStyle,
  normalizeGanttSettings,
  normalizePresentation,
  normalizeTimescale,
  normalizeWbs,
  type GanttBarKind,
  type GanttBarStyle,
  type GanttBarStyleSet,
  type GanttTimescale,
  type TableFontFamily,
  type TablePresentation,
  type WorkspacePresentation,
} from "./workspace-presentation.js";
import { timescaleTickScale } from "./workspace-gantt.js";
import { translateWorkspaceUiText } from "./workspace-localization.js";
import {
  ACTIVITY_FILTER_FIELDS,
  ACTIVITY_FILTER_SCOPES,
  activityFilterFieldLabel,
  activityFilterFieldType,
  activityFilterOperatorLabel,
  activityFilterOperatorsFor,
  copyActivityFilterAsLayout,
  deleteActivityFilter,
  filterScopeLabel,
  findActivityFilter,
  getBuiltinActivityFilters,
  makeGlobalActivityFilter,
  normalizeActivityFilter,
  pasteActivityFilter,
  selectActivityFilter,
  setActiveActivityFilter,
  setActivityFilterAllActivities,
  setActivityFilterApplyMode,
  setActivityFilterCombine,
  upsertActivityFilter,
  type ActivityFilterCriterion,
  type ActivityFilterDefinition,
  type ActivityFilterOperator,
  type ActivityFilterScope,
  type ActivityFilterState,
  type ActivityFilterPreview,
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
  /** Authoritative project Data Date; null when the read model exposes none. */
  dataDate?: string | null;
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
  "finish-id-name": ["Finish, ID, Name", "پایان، شناسه، نام"],
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

function shell(locale: string, id: string, title: string, body: string, includeDefault = false, footer?: string): string {
  return `<dialog class="cp-desktop-dialog cp-option-dialog" data-desktop-dialog="${id}" data-locale="${esc(locale)}" aria-labelledby="cp-dialog-${id}-heading">
    <form method="dialog" data-dialog-form="${id}">
      <h2 id="cp-dialog-${id}-heading">${esc(title)}</h2>
      <div class="cp-dialog-body">${body}</div>
      ${footer ?? buttons(locale, includeDefault)}
    </form>
  </dialog>`;
}

function tableEditor(optionsInput: DialogOptions, includeDisplayOptions: boolean): string {
  const { locale, presentation } = optionsInput;
  const table = presentation.table;
  return `${includeDisplayOptions ? '<input type="hidden" name="tableLineNumbers" value="1">' : ""}
    <input type="hidden" name="tableFields" value="1">
    <fieldset class="cp-dialog-group">
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
    </fieldset>
    ${includeDisplayOptions ? "" : `<button type="submit" class="cp-dialog-reset" name="tableReset" value="1" data-dialog-reset>${esc(t(locale, "Reset to defaults", "بازنشانی به پیش‌فرض"))}</button>`}`;
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
      <label class="cp-dialog-check"><input type="checkbox" name="bar.${kind}.necking"${style.necking ? " checked" : ""}> ${esc(t(locale, "Calendar nonwork time (neck the bar)", "زمان غیرکاری تقویم (باریک‌شدن میله)"))}</label>
    </fieldset>
  </details>`;
}

const BUILTIN_FILTER_NAMES_FA: Record<string, string> = {
  "In Progress": "در جریان",
  "Not Started": "شروع‌نشده",
  Completed: "تکمیل‌شده",
  Critical: "بحرانی",
  "Non Critical": "غیربحرانی",
  "Negative Float": "شناوری منفی",
  Milestone: "نقطه عطف",
};

function filterDisplayName(filter: ActivityFilterDefinition, locale: string): string {
  return filter.builtin ? t(locale, filter.name, BUILTIN_FILTER_NAMES_FA[filter.name] ?? filter.name) : filter.name;
}

/**
 * One row of the version 26 Filter list. The category is carried by the tbody
 * header, so the row only needs the name in the Filter column and the checkbox
 * in the Select column.
 */
function filterListRow(filter: ActivityFilterDefinition, locale: string, selected: boolean, current: boolean, disableList: boolean): string {
  const scope = filter.scope ?? "layout";
  const name = filterDisplayName(filter, locale);
  return `<tr data-filter-id="${esc(filter.id)}" data-filter-name="${esc(name.toLocaleLowerCase())}" data-filter-scope="${esc(scope)}"${filter.builtin ? ' data-filter-builtin="true"' : ""}${current ? ' class="is-current"' : ""}>
      <td class="cp-filter-name"><button type="button" data-filter-row-select="${esc(filter.id)}" aria-pressed="${current}">${esc(name)}</button></td>
      <td class="cp-filter-select"><input type="checkbox" name="filterSelected" value="${esc(filter.id)}" aria-label="${esc(t(locale, `Select ${name}`, `انتخاب ${name}`))}"${selected ? " checked" : ""}${disableList ? " disabled" : ""}></td>
    </tr>`;
}

function filterList(state: DialogOptions["presentation"]["filters"], locale: string): string {
  const selected = new Set(state.selectedIds?.length ? state.selectedIds : state.activeId ? [state.activeId] : []);
  const currentId = state.selectedIds?.[0] ?? state.activeId ?? null;
  const saved = state.saved;
  const list = getBuiltinActivityFilters();
  const header = `<div class="cp-dialog-row cp-dialog-check">
      <label><input type="checkbox" name="filterAllActivities"${state.allActivities ? " checked" : ""}> ${esc(t(locale, "All Activities", "همهٔ فعالیت‌ها"))}</label>
    </div>`;
  const groups = ACTIVITY_FILTER_SCOPES.map((scope) => {
    const items = scope === "default"
      ? list
      : saved.filter((filter) => (filter.scope ?? "layout") === scope);
    const rows = items.map((filter) => filterListRow(filter, locale, selected.has(filter.id), filter.id === currentId, Boolean(state.allActivities))).join("");
    const empty = scope === "user"
      ? `<tr class="cp-filter-empty"><td colspan="2">${esc(t(locale, "User-defined filters are stored per user in the project database; this runtime keeps its saved filters with the layout.", "فیلترهای کاربر در پایگاه دادهٔ پروژه برای هر کاربر نگهداری می‌شوند؛ این محیط فیلترهای ذخیره‌شده را همراه چیدمان نگه می‌دارد."))}</td></tr>`
      : items.length === 0
        ? `<tr class="cp-filter-empty"><td colspan="2">${esc(t(locale, "No filters in this category", "فیلتری در این دسته نیست"))}</td></tr>`
        : "";
    return `<tbody data-filter-group="${scope}">
        <tr class="cp-filter-group"><th colspan="2">${esc(filterScopeLabel(scope, locale))}</th></tr>
        ${rows}${empty}
      </tbody>`;
  }).join("");
  return `<fieldset class="cp-dialog-group">
      <legend>${esc(t(locale, "Filters", "فیلترها"))}</legend>
      ${header}
      <div class="cp-dialog-radios" role="radiogroup" aria-label="${esc(t(locale, "Show activities that match", "نمایش فعالیت‌هایی که مطابق‌اند با"))}">
        <span>${esc(t(locale, "Show activities that match", "نمایش فعالیت‌هایی که مطابق‌اند با"))}</span>
        <label><input type="radio" name="filterCombine" value="all"${state.combine !== "any" ? " checked" : ""}> ${esc(t(locale, "All selected filters", "همهٔ فیلترهای انتخاب‌شده"))}</label>
        <label><input type="radio" name="filterCombine" value="any"${state.combine === "any" ? " checked" : ""}> ${esc(t(locale, "Any selected filter", "هر یک از فیلترهای انتخاب‌شده"))}</label>
      </div>
      <input type="hidden" name="filterList" value="v26">
      <input type="hidden" name="filterRowId" value="${esc(currentId ?? "")}">
      <table class="cp-filter-list">
        <thead><tr>
          <th scope="col"><button type="button" data-filter-sort="name">${esc(t(locale, "Filter", "فیلتر"))}</button></th>
          <th scope="col"><button type="button" data-filter-sort="select">${esc(t(locale, "Select", "انتخاب"))}</button></th>
        </tr></thead>
        ${groups}
      </table>
      <div class="cp-dialog-radios" role="radiogroup" aria-label="${esc(t(locale, "When applying the selected filter(s)", "هنگام اعمال فیلترهای انتخاب‌شده"))}">
        <label><input type="radio" name="filterApplyMode" value="replace"${state.applyMode !== "highlight" ? " checked" : ""}> ${esc(t(locale, "Replace activities shown in current layout", "فعالیت‌های نمایش‌داده‌شده در چیدمان جاری جایگزین شوند"))}</label>
        <label><input type="radio" name="filterApplyMode" value="highlight"${state.applyMode === "highlight" ? " checked" : ""}> ${esc(t(locale, "Highlight activities in current layout which match criteria", "فعالیت‌های مطابق در چیدمان جاری برجسته شوند"))}</label>
      </div>
    </fieldset>`;
}

const FILTER_DATE_TOKENS = ["CD", "CS", "CF", "CD+7d", "CD-7d", "CD+1w", "CF+6w"] as const;

/** One editable criterion row; indices are renumbered after every mutation. */
export function filterCriterionRowMarkup(index: number, locale: string, criterion?: ActivityFilterCriterion): string {
  const fieldId = criterion?.fieldId ?? "activity_name";
  const type = activityFilterFieldType(fieldId);
  const operator = criterion?.operator ?? (activityFilterOperatorsFor(fieldId)[0] ?? "contains");
  const operators = activityFilterOperatorsFor(fieldId);
  const range = operator === "within-range";
  const blank = operator === "is-empty" || operator === "is-not-empty";
  const dateList = type === "date" ? ` list="cp-filter-date-tokens"` : "";
  return `<div class="cp-filter-row" data-filter-row="${index}" data-filter-field-type="${type}">
      <span class="cp-filter-join" data-filter-join${index === 0 ? " hidden" : ""}>${esc(t(locale, "And", "و"))}</span>
      <select name="filter.field.${index}" aria-label="${esc(t(locale, "Filter field", "فیلد فیلتر"))}">
        ${ACTIVITY_FILTER_FIELDS.map((id) => `<option value="${id}"${id === fieldId ? " selected" : ""}>${esc(activityFilterFieldLabel(id, locale))}</option>`).join("")}
      </select>
      <select name="filter.operator.${index}" aria-label="${esc(t(locale, "Filter operator", "عملگر فیلتر"))}">
        ${operators.map((id) => `<option value="${id}"${id === operator ? " selected" : ""}>${esc(activityFilterOperatorLabel(id, locale))}</option>`).join("")}
      </select>
      <input type="text" name="filter.value.${index}" value="${esc(criterion?.value ?? "")}"${dateList} aria-label="${esc(t(locale, "Filter value", "مقدار فیلتر"))}" autocomplete="off" spellcheck="false"${blank ? " disabled" : ""}>
      <input type="text" name="filter.high.${index}" value="${esc(criterion?.highValue ?? "")}"${dateList} data-filter-high aria-label="${esc(t(locale, "High value", "مقدار بالا"))}" autocomplete="off" spellcheck="false"${range ? "" : " hidden disabled"}>
      <span class="cp-filter-row-actions">
        <button type="button" data-filter-row-move="up" title="${esc(t(locale, "Move up", "بالا بردن"))}" aria-label="${esc(t(locale, "Move criterion up", "جابه‌جایی معیار به بالا"))}">↑</button>
        <button type="button" data-filter-row-move="down" title="${esc(t(locale, "Move down", "پایین آوردن"))}" aria-label="${esc(t(locale, "Move criterion down", "جابه‌جایی معیار به پایین"))}">↓</button>
        <button type="button" data-filter-row-remove title="${esc(t(locale, "Remove criterion", "حذف معیار"))}" aria-label="${esc(t(locale, "Remove criterion", "حذف معیار"))}">×</button>
      </span>
    </div>`;
}

function filterBuilder(locale: string): string {
  const rows = [0, 1].map((index) => filterCriterionRowMarkup(index, locale)).join("");
  return `<fieldset class="cp-dialog-group">
      <legend>${esc(t(locale, "Filter details", "جزئیات فیلتر"))}</legend>
      <p class="cp-dialog-note">${esc(t(locale, "New starts a global filter; Modify loads a saved filter for editing. Default filters cannot be modified. Date values accept an ISO date or the relative tokens CD (current date), CS (project start) and CF (project finish) with a ±n d/w/m/y offset. A filter only narrows or highlights rows on screen; it never changes schedule data.", "New یک فیلتر سراسری آغاز می‌کند و Modify یک فیلتر ذخیره‌شده را برای ویرایش بار می‌کند. فیلترهای پیش‌فرض قابل ویرایش نیستند. مقدار تاریخ می‌تواند تاریخ ISO یا نشانه‌های نسبی CD (تاریخ جاری)، CS (شروع پروژه) و CF (پایان پروژه) با جابه‌جایی ±n d/w/m/y باشد. فیلتر فقط ردیف‌های روی صفحه را محدود یا برجسته می‌کند و داده‌های زمان‌بندی را تغییر نمی‌دهد."))}</p>
      <input type="hidden" name="filterEditingId" value="">
      <div class="cp-dialog-grid">
        <label class="cp-dialog-row"><span>${esc(t(locale, "Filter name", "نام فیلتر"))}</span>
          <input type="text" name="filterName" maxlength="60" value="" autocomplete="off">
        </label>
        <label class="cp-dialog-row"><span>${esc(t(locale, "Category", "دسته"))}</span>
          <select name="filterScope">
            <option value="layout" selected>${esc(filterScopeLabel("layout", locale))}</option>
            <option value="global">${esc(filterScopeLabel("global", locale))}</option>
            <option value="user">${esc(filterScopeLabel("user", locale))}</option>
          </select>
        </label>
        <label class="cp-dialog-row"><span>${esc(t(locale, "Match", "تطبیق"))}</span>
          <select name="filterMatch">
            <option value="all" selected>${esc(t(locale, "All criteria (AND)", "همهٔ معیارها (و)"))}</option>
            <option value="any">${esc(t(locale, "Any criterion (OR)", "هر یک از معیارها (یا)"))}</option>
          </select>
        </label>
      </div>
      <div class="cp-filter-criteria" role="group" aria-label="${esc(t(locale, "Where", "شرط"))}">
        <div class="cp-filter-head"><span>${esc(t(locale, "Where", "شرط"))}</span><span>${esc(t(locale, "Field", "فیلد"))}</span><span>${esc(t(locale, "Is", "است"))}</span><span>${esc(t(locale, "Value", "مقدار"))}</span><span>${esc(t(locale, "High value", "مقدار بالا"))}</span><span></span></div>
        <div class="cp-filter-rows" data-filter-rows>${rows}</div>
        <datalist id="cp-filter-date-tokens">${FILTER_DATE_TOKENS.map((token) => `<option value="${token}"></option>`).join("")}</datalist>
        <button type="button" class="cp-filter-add" data-filter-row-add>${esc(t(locale, "Add criterion", "افزودن معیار"))}</button>
      </div>
      <p class="cp-filter-preview" data-filter-preview aria-live="polite">${esc(t(locale, "Preview: choose a parameter and a value to see how many activities match.", "پیش‌نمایش: پارامتر و مقدار را انتخاب کنید تا شمار فعالیت‌های مطابق دیده شود."))}</p>
    </fieldset>`;
}

function filterFooter(locale: string): string {
  const button = (en: string, fa: string, attrs: string): string => `<button ${attrs}>${esc(t(locale, en, fa))}</button>`;
  return `<div class="cp-dialog-buttons cp-filter-buttons">
    ${button("Apply", "اعمال", 'type="submit" data-dialog-apply name="filterAction" value="apply"')}
    ${button("New", "جدید", 'type="button" data-filter-new')}
    ${button("Delete", "حذف", 'type="submit" data-dialog-apply name="filterAction" value="delete"')}
    ${button("Copy", "کپی", 'type="submit" data-dialog-apply name="filterAction" value="copy"')}
    ${button("Paste", "جای‌گذاری", 'type="submit" data-dialog-apply name="filterAction" value="paste"')}
    ${button("Modify", "ویرایش", 'type="button" data-filter-modify')}
    ${button("Make Global", "سراسری کن", 'type="submit" data-dialog-apply name="filterAction" value="make-global"')}
    ${button("Copy as Layout", "کپی به چیدمان", 'type="submit" data-dialog-apply name="filterAction" value="copy-as-layout"')}
    <span class="cp-dialog-buttons-spacer" aria-hidden="true"></span>
    ${button("OK", "تأیید", 'type="submit" class="cp-dialog-primary" data-dialog-ok')}
    ${button("Cancel", "لغو", 'type="button" data-dialog-cancel')}
    ${button("Default", "پیش‌فرض", 'type="button" data-dialog-default')}
    ${button("Help", "راهنما", 'type="button" data-dialog-help')}
  </div>`;
}

function filterEditor(optionsInput: DialogOptions): string {
  const { locale, presentation } = optionsInput;
  return `${filterList(presentation.filters, locale)}${filterBuilder(locale)}`;
}

/** Enables or disables the Select column when All Activities is checked. */
export function setFilterListEnabled(dialog: HTMLElement, enabled: boolean): void {
  for (const input of dialog.querySelectorAll<HTMLInputElement>('input[name="filterSelected"]')) {
    input.disabled = !enabled;
  }
}

/**
 * Clears the filter builder. Version 26's New button creates a global filter,
 * so the scope defaults to the requested category and the name starts empty.
 */
export function resetFilterEditor(dialog: HTMLElement, scope: ActivityFilterScope = "layout"): void {
  const name = dialog.querySelector<HTMLInputElement>('input[name="filterName"]');
  if (name) name.value = "";
  const match = dialog.querySelector<HTMLSelectElement>('select[name="filterMatch"]');
  if (match) match.value = "all";
  const scopeSelect = dialog.querySelector<HTMLSelectElement>('select[name="filterScope"]');
  if (scopeSelect) scopeSelect.value = scope === "default" ? "layout" : scope;
  const editing = dialog.querySelector<HTMLInputElement>('input[name="filterEditingId"]');
  if (editing) editing.value = "";
  setFilterCriterionRows(dialog, [{ fieldId: "activity_name", operator: "contains", value: "" }]);
  dialog.querySelector('input[name="filterDelete"]')?.closest("label")?.remove();
}

/** Loads a saved filter into the builder for the Modify action. */
export function loadFilterEditor(dialog: HTMLElement, filter: ActivityFilterDefinition): void {
  resetFilterEditor(dialog, filter.scope ?? "layout");
  const name = dialog.querySelector<HTMLInputElement>('input[name="filterName"]');
  if (name) name.value = filter.name;
  const match = dialog.querySelector<HTMLSelectElement>('select[name="filterMatch"]');
  if (match) match.value = filter.match;
  const editing = dialog.querySelector<HTMLInputElement>('input[name="filterEditingId"]');
  if (editing) editing.value = filter.builtin ? "" : filter.id;
  const scopeSelect = dialog.querySelector<HTMLSelectElement>('select[name="filterScope"]');
  if (scopeSelect) scopeSelect.value = filter.scope === "global" || filter.scope === "user" ? filter.scope : "layout";
  setFilterCriterionRows(dialog, filter.criteria.length > 0 ? filter.criteria : [{ fieldId: "activity_name", operator: "contains", value: "" }]);
}

/** Reads the builder rows in display order, including the High value column. */
export function filterCriterionRows(dialog: HTMLElement): ActivityFilterCriterion[] {
  const rows = dialog.querySelectorAll<HTMLElement>("[data-filter-rows] .cp-filter-row");
  return Array.from(rows).map((row) => {
    const read = (prefix: string): string => row.querySelector<HTMLInputElement | HTMLSelectElement>(`[name^="${prefix}"]`)?.value ?? "";
    const criterion: ActivityFilterCriterion = {
      fieldId: read("filter.field.") as ActivityFilterCriterion["fieldId"],
      operator: read("filter.operator.") as ActivityFilterCriterion["operator"],
      value: read("filter.value."),
    };
    if (criterion.operator === "within-range") criterion.highValue = read("filter.high.");
    return criterion;
  });
}

/** Rebuilds the builder rows; names are renumbered from zero after the write. */
export function setFilterCriterionRows(dialog: HTMLElement, criteria: readonly ActivityFilterCriterion[]): void {
  const container = dialog.querySelector<HTMLElement>("[data-filter-rows]");
  if (!container) return;
  const locale = dialog.dataset.locale ?? "en";
  const rows = criteria.length > 0 ? criteria : [{ fieldId: "activity_name" as const, operator: "contains" as const, value: "" }];
  container.innerHTML = rows.map((criterion, index) => filterCriterionRowMarkup(index, locale, criterion)).join("");
  renumberFilterRows(dialog);
}

/** Renumbers row names and join labels after an insert, delete or move. */
export function renumberFilterRows(dialog: HTMLElement): void {
  const container = dialog.querySelector<HTMLElement>("[data-filter-rows]");
  if (!container) return;
  const locale = dialog.dataset.locale ?? "en";
  Array.from(container.querySelectorAll<HTMLElement>(".cp-filter-row")).forEach((row, index) => {
    row.dataset.filterRow = String(index);
    row.querySelector<HTMLSelectElement>('select[name^="filter.field."]')?.setAttribute("name", `filter.field.${index}`);
    row.querySelector<HTMLSelectElement>('select[name^="filter.operator."]')?.setAttribute("name", `filter.operator.${index}`);
    row.querySelector<HTMLInputElement>('input[name^="filter.value."]')?.setAttribute("name", `filter.value.${index}`);
    row.querySelector<HTMLInputElement>('input[name^="filter.high."]')?.setAttribute("name", `filter.high.${index}`);
    const join = row.querySelector<HTMLElement>("[data-filter-join]");
    if (join) {
      const any = dialog.querySelector<HTMLSelectElement>('select[name="filterMatch"]')?.value === "any";
      join.hidden = index === 0;
      join.textContent = any
        ? translateWorkspaceUiText(locale, "Or", "یا")
        : translateWorkspaceUiText(locale, "And", "و");
    }
  });
}

/** Appends one criterion row and returns it. */
export function addFilterCriterion(dialog: HTMLElement): HTMLElement | null {
  const container = dialog.querySelector<HTMLElement>("[data-filter-rows]");
  if (!container) return null;
  const count = container.querySelectorAll(".cp-filter-row").length;
  if (count >= 8) return null;
  const locale = dialog.dataset.locale ?? "en";
  container.insertAdjacentHTML("beforeend", filterCriterionRowMarkup(count, locale));
  renumberFilterRows(dialog);
  return container.querySelector<HTMLElement>(`.cp-filter-row[data-filter-row="${count}"]`);
}

/** Removes a criterion row; the last row is kept so the editor stays usable. */
export function removeFilterCriterion(row: HTMLElement): boolean {
  const container = row.closest<HTMLElement>("[data-filter-rows]");
  if (!container || container.querySelectorAll(".cp-filter-row").length <= 1) return false;
  row.remove();
  const dialog = container.closest<HTMLElement>("dialog");
  if (dialog) renumberFilterRows(dialog);
  return true;
}

/** Moves a criterion row one place and returns true when it moved. */
export function moveFilterCriterion(row: HTMLElement, direction: "up" | "down"): boolean {
  const sibling = direction === "up" ? row.previousElementSibling : row.nextElementSibling;
  if (!sibling || !sibling.classList.contains("cp-filter-row")) return false;
  if (direction === "up") row.parentElement?.insertBefore(row, sibling);
  else row.parentElement?.insertBefore(sibling, row);
  const dialog = row.closest<HTMLElement>("dialog");
  if (dialog) renumberFilterRows(dialog);
  return true;
}

/** Keeps the value and High value boxes in step with the chosen operator. */
export function syncFilterOperator(select: HTMLSelectElement): void {
  const row = select.closest<HTMLElement>(".cp-filter-row");
  const input = row?.querySelector<HTMLInputElement>('input[name^="filter.value."]');
  if (!input) return;
  const blank = select.value === "is-empty" || select.value === "is-not-empty";
  input.disabled = blank;
  if (blank) input.value = "";
  const high = row?.querySelector<HTMLInputElement>("[data-filter-high]");
  if (high) {
    const range = select.value === "within-range";
    high.hidden = !range;
    high.disabled = !range;
    if (!range) high.value = "";
  }
}

/** Swaps the operator list when the parameter type changes. */
export function syncFilterField(select: HTMLSelectElement): void {
  const row = select.closest<HTMLElement>(".cp-filter-row");
  if (!row) return;
  const fieldId = select.value as ActivityFilterCriterion["fieldId"];
  const type = activityFilterFieldType(fieldId);
  row.dataset.filterFieldType = type;
  const locale = (row.closest<HTMLElement>("dialog")?.dataset.locale) ?? "en";
  const operator = row.querySelector<HTMLSelectElement>('select[name^="filter.operator."]');
  if (!operator) return;
  const current = operator.value;
  const allowed = activityFilterOperatorsFor(fieldId);
  operator.innerHTML = allowed
    .map((id) => `<option value="${id}">${esc(activityFilterOperatorLabel(id, locale))}</option>`)
    .join("");
  operator.value = allowed.includes(current as ActivityFilterOperator) ? current : allowed[0];
  const value = row.querySelector<HTMLInputElement>('input[name^="filter.value."]');
  if (value) {
    value.value = "";
    if (type === "date") value.setAttribute("list", "cp-filter-date-tokens");
    else value.removeAttribute("list");
    if (type === "number") value.setAttribute("inputmode", "decimal");
    else value.removeAttribute("inputmode");
  }
  const high = row.querySelector<HTMLInputElement>("[data-filter-high]");
  if (high) {
    high.value = "";
    if (type === "date") high.setAttribute("list", "cp-filter-date-tokens");
    else high.removeAttribute("list");
  }
  syncFilterOperator(operator);
}

/** Renders the editor's validation/preview line. */
export function formatFilterPreview(preview: ActivityFilterPreview, locale: string): string {
  if (!preview.valid) {
    const messages: Record<string, { en: string; fa: string }> = {
      FILTER_VALUE_REQUIRED: { en: "Enter a value for every criterion.", fa: "برای هر معیار مقداری وارد کنید." },
      FILTER_RANGE_INCOMPLETE: { en: "A range needs both a value and a high value.", fa: "بازه به مقدار و مقدار بالا نیاز دارد." },
      FILTER_VALUE_INVALID_DATE: { en: "Use an ISO date or a relative token such as CD+7d.", fa: "از تاریخ ISO یا نشانهٔ نسبی مانند CD+7d استفاده کنید." },
      FILTER_RANGE_INVALID: { en: "The high value must not be before the value.", fa: "مقدار بالا نباید پیش از مقدار باشد." },
    };
    const message = messages[preview.code] ?? messages.FILTER_VALUE_REQUIRED;
    return translateWorkspaceUiText(locale, message.en, message.fa);
  }
  return translateWorkspaceUiText(
    locale,
    `${preview.matched} of ${preview.total} activities match.`,
    `${preview.matched} از ${preview.total} فعالیت مطابق است.`,
  );
}

/** Sorts one Filter list category in place; used by the column headers. */
export function sortFilterList(dialog: HTMLElement, column: "name" | "select", descending: boolean): void {
  for (const body of dialog.querySelectorAll<HTMLTableSectionElement>("tbody[data-filter-group]")) {
    const rows = Array.from(body.querySelectorAll<HTMLTableRowElement>("tr[data-filter-id]"));
    rows.sort((a, b) => {
      const left = column === "select"
        ? (a.querySelector<HTMLInputElement>('input[name="filterSelected"]')?.checked ? 0 : 1)
        : a.dataset.filterName ?? "";
      const right = column === "select"
        ? (b.querySelector<HTMLInputElement>('input[name="filterSelected"]')?.checked ? 0 : 1)
        : b.dataset.filterName ?? "";
      const order = typeof left === "number" && typeof right === "number"
        ? left - right
        : String(left).localeCompare(String(right), undefined, { sensitivity: "base" });
      return descending ? -order : order;
    });
    const empty = body.querySelector("tr.cp-filter-empty");
    for (const row of rows) body.insertBefore(row, empty);
  }
}

/**
 * Gantt chart options shared by every bar style: labels, legend, sight lines,
 * the Data Date line and the progress-point line. Version 26 keeps these on the
 * Bars dialog's Bar Settings / Bar Labels tabs and in the Sight Lines and Data
 * Date options; here they group into one fieldset so each control is reachable.
 */
function ganttChartEditor(optionsInput: DialogOptions): string {
  const locale = optionsInput.locale;
  const gantt = optionsInput.presentation.gantt;
  const dataDate = optionsInput.dataDate ?? null;
  const dataDateNote = dataDate
    ? `<p class="cp-dialog-note">${esc(t(locale, "The Data Date line marks the project data date on the chart.", "خط تاریخ داده، تاریخ دادهٔ پروژه را روی نمودار نشان می‌دهد."))}</p>`
    : `<p class="cp-dialog-note">${esc(t(locale, "This project's read model exposes no Data Date, so the line is not drawn. The saved line settings will apply as soon as an authoritative date exists.", "مدل خواندنی این پروژه تاریخ داده ارائه نمی‌کند؛ بنابراین خط رسم نمی‌شود. تنظیمات ذخیره‌شده به‌محض وجود تاریخ معتبر اعمال خواهد شد."))}</p>`;
  const dataDateDisabled = dataDate ? "" : " disabled";
  return `<fieldset class="cp-dialog-group" data-gantt-options>
      <legend>${esc(t(locale, "Gantt chart options", "تنظیمات نمودار گانت"))}</legend>
      <p class="cp-dialog-note">${esc(t(locale, "These options change drawing only. Bar geometry still comes from the saved schedule dates.", "این تنظیمات فقط رسم نمودار را تغییر می‌دهد و هندسهٔ میله همچنان از تاریخ‌های ذخیره‌شدهٔ زمان‌بندی می‌آید."))}</p>
      <div class="cp-dialog-grid">
        <label class="cp-dialog-check"><input type="checkbox" name="gantt.showBarLabels"${gantt.showBarLabels ? " checked" : ""}> ${esc(t(locale, "Show bar labels", "نمایش برچسب میله‌ها"))}</label>
        <label class="cp-dialog-row"><span>${esc(t(locale, "Label font size", "اندازهٔ قلم برچسب"))}</span>
          <input type="number" name="gantt.labelFontSize" min="8" max="16" step="1" value="${gantt.labelFontSize}" aria-label="${esc(t(locale, "Bar label font size", "اندازهٔ قلم برچسب میله"))}">
        </label>
        <label class="cp-dialog-row"><span>${esc(t(locale, "Label colour", "رنگ برچسب"))}</span>
          <input type="color" name="gantt.labelColor" value="${esc(gantt.labelColor)}" aria-label="${esc(t(locale, "Bar label colour", "رنگ برچسب میله"))}">
        </label>
      </div>
      <fieldset class="cp-dialog-group">
        <legend>${esc(t(locale, "Legend", "راهنما"))}</legend>
        <div class="cp-dialog-grid">
          <label class="cp-dialog-check"><input type="checkbox" name="gantt.legend.visible"${gantt.legend.visible ? " checked" : ""}> ${esc(t(locale, "Show legend", "نمایش راهنما"))}</label>
          <label class="cp-dialog-row"><span>${esc(t(locale, "Position", "موقعیت"))}</span>
            <select name="gantt.legend.position">
              <option value="bottom"${gantt.legend.position === "bottom" ? " selected" : ""}>${esc(t(locale, "Below the chart", "زیر نمودار"))}</option>
              <option value="top"${gantt.legend.position === "top" ? " selected" : ""}>${esc(t(locale, "Above the chart", "بالای نمودار"))}</option>
            </select>
          </label>
        </div>
        <p class="cp-dialog-note">${esc(t(locale, "Only bar styles that are currently shown appear in the legend.", "فقط سبک‌های میله‌ای که اکنون نمایش داده می‌شوند در راهنما می‌آیند."))}</p>
      </fieldset>
      <fieldset class="cp-dialog-group">
        <legend>${esc(t(locale, "Sight lines", "خطوط راهنمای دید"))}</legend>
        <label class="cp-dialog-check"><input type="checkbox" name="gantt.sightLines.beforeSummaries"${gantt.sightLines.beforeSummaries ? " checked" : ""}> ${esc(t(locale, "Major horizontal line above every summary", "خط افقی اصلی بالای هر خلاصه"))}</label>
        <div class="cp-dialog-grid">
          <label class="cp-dialog-row"><span>${esc(t(locale, "Minor horizontal line interval (rows, 0 = off)", "فاصلهٔ خط افقی فرعی (ردیف، ۰ = خاموش)"))}</span>
            <input type="number" name="gantt.sightLines.rowInterval" min="0" max="10" step="1" value="${gantt.sightLines.rowInterval}" aria-label="${esc(t(locale, "Minor horizontal line interval", "فاصلهٔ خط افقی فرعی"))}">
          </label>
          <label class="cp-dialog-check"><input type="checkbox" name="gantt.sightLines.minorVertical"${gantt.sightLines.minorVertical ? " checked" : ""}> ${esc(t(locale, "Minor vertical line at every timescale tick", "خط عمودی فرعی در هر نشانهٔ مقیاس زمانی"))}</label>
        </div>
      </fieldset>
      <fieldset class="cp-dialog-group"${dataDateDisabled}>
        <legend>${esc(t(locale, "Data Date line", "خط تاریخ داده"))}</legend>
        ${dataDateNote}
        <div class="cp-dialog-grid">
          <label class="cp-dialog-check"><input type="checkbox" name="gantt.dataDateLine.visible"${gantt.dataDateLine.visible ? " checked" : ""}> ${esc(t(locale, "Show Data Date line", "نمایش خط تاریخ داده"))}</label>
          <label class="cp-dialog-row"><span>${esc(t(locale, "Style", "سبک"))}</span>
            <select name="gantt.dataDateLine.style">
              <option value="solid"${gantt.dataDateLine.style === "solid" ? " selected" : ""}>${esc(t(locale, "Solid", "توپر"))}</option>
              <option value="dashed"${gantt.dataDateLine.style === "dashed" ? " selected" : ""}>${esc(t(locale, "Dashed", "خط‌چین"))}</option>
              <option value="dotted"${gantt.dataDateLine.style === "dotted" ? " selected" : ""}>${esc(t(locale, "Dotted", "نقطه‌چین"))}</option>
            </select>
          </label>
          <label class="cp-dialog-row"><span>${esc(t(locale, "Thickness", "ضخامت"))}</span>
            <input type="number" name="gantt.dataDateLine.thickness" min="1" max="10" step="1" value="${gantt.dataDateLine.thickness}" aria-label="${esc(t(locale, "Data Date line thickness", "ضخامت خط تاریخ داده"))}">
          </label>
          <label class="cp-dialog-row"><span>${esc(t(locale, "Colour", "رنگ"))}</span>
            <input type="color" name="gantt.dataDateLine.color" value="${esc(gantt.dataDateLine.color)}" aria-label="${esc(t(locale, "Data Date line colour", "رنگ خط تاریخ داده"))}">
          </label>
        </div>
        <p class="cp-dialog-note">${esc(t(locale, "A thickness above 1 is painted as a solid line; dashed and dotted lines stay 1 pixel wide.", "ضخامت بیش از ۱ به‌صورت خط توپر رسم می‌شود؛ خطوط خط‌چین و نقطه‌چین با ضخامت ۱ می‌مانند."))}</p>
      </fieldset>
      <fieldset class="cp-dialog-group">
        <legend>${esc(t(locale, "Progress point line", "خط نقاط پیشرفت"))}</legend>
        <div class="cp-dialog-grid">
          <label class="cp-dialog-check"><input type="checkbox" name="gantt.progressLine.visible"${gantt.progressLine.visible ? " checked" : ""}> ${esc(t(locale, "Show progress point line", "نمایش خط نقاط پیشرفت"))}</label>
          <label class="cp-dialog-row"><span>${esc(t(locale, "Thickness", "ضخامت"))}</span>
            <input type="number" name="gantt.progressLine.thickness" min="1" max="10" step="1" value="${gantt.progressLine.thickness}" aria-label="${esc(t(locale, "Progress line thickness", "ضخامت خط پیشرفت"))}">
          </label>
          <label class="cp-dialog-row"><span>${esc(t(locale, "Colour", "رنگ"))}</span>
            <input type="color" name="gantt.progressLine.color" value="${esc(gantt.progressLine.color)}" aria-label="${esc(t(locale, "Progress line colour", "رنگ خط پیشرفت"))}">
          </label>
        </div>
        <p class="cp-dialog-note">${esc(t(locale, "Joins the saved progress point of each drawn activity. Ahead/behind colouring is not offered because it needs the project Data Date, which this read model does not expose.", "نقاط پیشرفت ذخیره‌شدهٔ هر فعالیت رسم‌شده را به هم وصل می‌کند. رنگ‌بندی جلو/عقب ارائه نشده است زیرا به تاریخ دادهٔ پروژه نیاز دارد و مدل خواندنی فعلی آن را ارائه نمی‌کند."))}</p>
      </fieldset>
    </fieldset>`;
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

  const timescaleState = optionsInput.presentation.timescale;
  const timescale = `<fieldset class="cp-dialog-group">
      <legend>${esc(t(locale, "Timescale format", "قالب مقیاس زمانی"))}</legend>
      <p class="cp-dialog-note">${esc(t(locale, "The chart scale (Day, Week, Month, Quarter, Year) is set by the Gantt scale buttons. This dialog controls the header intervals and their format; changing an interval also picks the tick density that matches it.", "مقیاس نمودار (روز، هفته، ماه، فصل، سال) با دکمه‌های مقیاس گانت تعیین می‌شود. این گفت‌وگو فاصله‌های سربرگ و قالب آن‌ها را کنترل می‌کند؛ تغییر فاصله، چگالی نشانه‌ها را نیز متناسب با آن انتخاب می‌کند."))}</p>
      <div class="cp-dialog-grid">
        <label class="cp-dialog-row"><span>${esc(t(locale, "Date interval", "فاصلهٔ تاریخ"))}</span>
          <select name="timescale.interval">
            ${GANTT_TIMESCALE_INTERVALS.map((interval) => `<option value="${interval}"${timescaleState.interval === interval ? " selected" : ""}>${esc(t(locale, {
              "year-quarter": "Year / Quarter",
              "year-month": "Year / Month",
              "quarter-month": "Quarter / Month",
              "month-week": "Month / Week",
              "week-day": "Week / Day",
            }[interval], {
              "year-quarter": "سال / فصل",
              "year-month": "سال / ماه",
              "quarter-month": "فصل / ماه",
              "month-week": "ماه / هفته",
              "week-day": "هفته / روز",
            }[interval]))}</option>`).join("")}
          </select>
        </label>
        <label class="cp-dialog-row"><span>${esc(t(locale, "Header rows", "ردیف‌های سربرگ"))}</span>
          <select name="timescale.lines">
            <option value="2"${timescaleState.lines === 2 ? " selected" : ""}>2</option>
            <option value="3"${timescaleState.lines === 3 ? " selected" : ""}>3</option>
          </select>
        </label>
        <label class="cp-dialog-row"><span>${esc(t(locale, "Date format", "قالب تاریخ"))}</span>
          <select name="timescale.dateFormat">
            <option value="primary"${timescaleState.dateFormat === "primary" ? " selected" : ""}>${esc(t(locale, "Calendar date", "تاریخ تقویمی"))}</option>
            <option value="ordinal"${timescaleState.dateFormat === "ordinal" ? " selected" : ""}>${esc(t(locale, "Ordinal number", "شمارهٔ ترتیبی"))}</option>
          </select>
        </label>
        <label class="cp-dialog-row"><span>${esc(t(locale, "Date type", "نوع تاریخ"))}</span>
          <select name="timescale.type">
            <option value="calendar"${timescaleState.type === "calendar" ? " selected" : ""}>${esc(t(locale, "Calendar", "تقویمی"))}</option>
            <option value="week-of-year"${timescaleState.type === "week-of-year" ? " selected" : ""}>${esc(t(locale, "Week of year", "هفتهٔ سال"))}</option>
          </select>
        </label>
        <label class="cp-dialog-row"><span>${esc(t(locale, "Ordinal start", "شروع ترتیبی"))}</span>
          <input type="date" name="timescale.ordinalStart" value="${esc(timescaleState.ordinalStart ?? "")}" aria-label="${esc(t(locale, "Ordinal start date", "تاریخ شروع شمارهٔ ترتیبی"))}">
        </label>
        <label class="cp-dialog-row"><span>${esc(t(locale, "Ordinal interval", "فاصلهٔ ترتیبی"))}</span>
          <select name="timescale.ordinalInterval">
            ${GANTT_ORDINAL_INTERVALS.map((unit) => `<option value="${unit}"${timescaleState.ordinalInterval === unit ? " selected" : ""}>${esc(t(locale, unit[0].toUpperCase() + unit.slice(1), { day: "روز", week: "هفته", month: "ماه", quarter: "فصل", year: "سال" }[unit]))}</option>`).join("")}
          </select>
        </label>
        <label class="cp-dialog-row"><span>${esc(t(locale, "Header font size", "اندازهٔ قلم سربرگ"))}</span>
          <input type="number" name="timescale.fontSize" min="8" max="16" step="1" value="${timescaleState.fontSize}" aria-label="${esc(t(locale, "Header font size", "اندازهٔ قلم سربرگ"))}">
        </label>
        <label class="cp-dialog-row"><span>${esc(t(locale, "Header text", "متن سربرگ"))}</span>
          <input type="color" name="timescale.textColor" value="${esc(timescaleState.textColor)}" aria-label="${esc(t(locale, "Header text colour", "رنگ متن سربرگ"))}">
        </label>
        <label class="cp-dialog-row"><span>${esc(t(locale, "Header background", "پس‌زمینهٔ سربرگ"))}</span>
          <input type="color" name="timescale.backgroundColor" value="${esc(timescaleState.backgroundColor)}" aria-label="${esc(t(locale, "Header background colour", "رنگ پس‌زمینهٔ سربرگ"))}">
        </label>
      </div>
      <label class="cp-dialog-check"><input type="checkbox" name="showRelationships"${layout.showRelationships ? " checked" : ""}> ${esc(t(locale, "Show relationship lines", "نمایش خطوط روابط"))}</label>
      <p class="cp-dialog-note">${esc(t(locale, "Fiscal year, shift and hour intervals are not rendered by this runtime, so they are not offered here.", "فاصله‌های سال مالی، شیفت و ساعت در این محیط رندر نمی‌شوند و به همین دلیل ارائه نشده‌اند."))}</p>
    </fieldset>`;

  const bars = `<p class="cp-dialog-note">${esc(t(locale, "Each bar type has independent shape, colour, pattern, filter, row and label settings. Bar geometry still comes from the saved schedule dates.", "هر نوع میله شکل، رنگ، الگو، فیلتر، ردیف و برچسب مستقل دارد. هندسهٔ میله همچنان از تاریخ‌های ذخیره‌شدهٔ زمان‌بندی می‌آید."))}</p>
    <div class="cp-bar-style-list">${GANTT_BAR_KINDS.map((kind) => barEditor(kind, optionsInput.presentation.bars[kind], locale, optionsInput.dataAvailability)).join("")}</div>
    ${ganttChartEditor(optionsInput)}`;

  const fontRow = tableEditor(optionsInput, false);
  const wbs = optionsInput.presentation.wbs;
  const inkOptions = [
    { value: "auto", label: t(locale, "Automatic contrast", "کنتراست خودکار") },
    { value: "custom", label: t(locale, "Custom colour", "رنگ سفارشی") },
  ] as const;
  const wbsColors = `<fieldset class="cp-dialog-group">
      <legend>${esc(t(locale, "WBS band format", "قالب باند WBS"))}</legend>
      <input type="hidden" name="wbsFields" value="1">
      <p class="cp-dialog-note">${esc(t(locale, "Band fonts, colours and height are independent of the activity table. Each level colour paints the hierarchy cell, its guide rails and the level icon; it never fills the whole activity row, so selection and critical-path colours stay independent.", "قلم، رنگ و ارتفاع باند مستقل از جدول فعالیت‌هاست. رنگ هر سطح فقط در ستون سلسله‌مراتب، خطوط راهنمای آن و نماد سطح اعمال می‌شود و کل ردیف فعالیت را پر نمی‌کند؛ بنابراین رنگ انتخاب و مسیر بحرانی مستقل باقی می‌ماند."))}</p>
      <div class="cp-wbs-color-grid">${wbs.levelColors.map((color, index) => `<label class="cp-dialog-row"><span>${esc(t(locale, `Level ${index + 1}`, `سطح ${index + 1}`))}</span><input type="color" name="wbs.color.${index}" value="${esc(color)}" aria-label="${esc(t(locale, `WBS level ${index + 1} colour`, `رنگ سطح ${index + 1} WBS`))}"></label>`).join("")}</div>
      <label class="cp-dialog-row"><span>${esc(t(locale, "Band font", "قلم باند"))}</span>
        <select name="wbs.fontFamily">${selectOptions(TABLE_FONT_FAMILIES, FONT_FAMILY_LABELS, wbs.fontFamily, locale)}</select>
      </label>
      <label class="cp-dialog-row"><span>${esc(t(locale, "Band font size", "اندازهٔ قلم باند"))}</span>
        <select name="wbs.fontSize">${[9, 10, 11, 12, 13, 14, 15, 16].map((size) => `<option value="${size}"${wbs.fontSize === size ? " selected" : ""}>${size} px</option>`).join("")}</select>
      </label>
      <label class="cp-dialog-row"><span>${esc(t(locale, "Band text", "متن باند"))}</span>
        <select name="wbs.inkMode">${inkOptions.map((option) => `<option value="${option.value}"${wbs.inkMode === option.value ? " selected" : ""}>${esc(option.label)}</option>`).join("")}</select>
      </label>
      <label class="cp-dialog-row"><span>${esc(t(locale, "Band text colour", "رنگ متن باند"))}</span>
        <input type="color" name="wbs.textColor" value="${esc(wbs.textColor)}" aria-label="${esc(t(locale, "WBS band text colour", "رنگ متن باند WBS"))}">
      </label>
      <label class="cp-dialog-row"><span>${esc(t(locale, "Band height", "ارتفاع باند"))}</span>
        <input type="number" name="wbs.rowHeight" min="18" max="40" step="1" value="${wbs.rowHeight}" aria-label="${esc(t(locale, "WBS band height", "ارتفاع باند WBS"))}">
      </label>
      <div class="cp-dialog-radios" role="group" aria-label="${esc(t(locale, "Band text fields", "فیلدهای متن باند"))}">
        <label><input type="checkbox" name="wbs.label.title"${wbs.labels.title ? " checked" : ""}> ${esc(t(locale, "Show Title", "نمایش عنوان"))}</label>
        <label><input type="checkbox" name="wbs.label.code"${wbs.labels.code ? " checked" : ""}> ${esc(t(locale, "Show ID/Code", "نمایش شناسه/کد"))}</label>
        <label><input type="checkbox" name="wbs.label.name"${wbs.labels.name ? " checked" : ""}> ${esc(t(locale, "Show Name", "نمایش نام"))}</label>
      </div>
      <button type="submit" class="cp-dialog-reset" name="wbsReset" value="1" data-dialog-reset>${esc(t(locale, "Reset band format", "بازنشانی قالب باند"))}</button>
    </fieldset>`;
  const preferences = `${tableEditor(optionsInput, true)}${wbsColors}
    <fieldset class="cp-dialog-group">
      <legend>${esc(t(locale, "Display", "نمایش"))}</legend>
      <p class="cp-dialog-note">${esc(t(locale, "Preferences are stored with the saved layout for this project. They do not change schedule data.", "تنظیمات به‌همراه چیدمان ذخیره‌شدهٔ این پروژه نگهداری می‌شود و داده‌های زمان‌بندی را تغییر نمی‌دهد."))}</p>
    </fieldset>`;

  return [
    shell(locale, "filters", t(locale, "Filters", "فیلترها"), filterEditor(optionsInput), true, filterFooter(locale)),
    shell(locale, "group-sort", t(locale, "Group and Sort", "گروه‌بندی و ترتیب"), groupSort, true),
    shell(locale, "timescale", t(locale, "Timescale", "مقیاس زمانی"), timescale),
    shell(locale, "bars", t(locale, "Bar Styles", "سبک میله‌ها"), bars),
    shell(locale, "font-row", t(locale, "Table Font and Row", "قلم و ردیف جدول"), fontRow),
    shell(locale, "user-preferences", t(locale, "User Preferences", "ترجیحات کاربر"), preferences, true),
  ].join("");
}

/** Copied filter criteria; Version 26 Copy/Paste stays inside this session. */
let filterClipboard: ActivityFilterDefinition | null = null;

function selectManyActivityFilters(state: ActivityFilterState, ids: readonly string[]): ActivityFilterState {
  const known = ids.filter((id) => findActivityFilter(state, id) !== null);
  const current = state.selectedIds ?? (state.activeId ? [state.activeId] : []);
  if (known.length === current.length && known.every((id, index) => id === current[index])) return state;
  return { ...state, selectedIds: known, activeId: known[0] ?? null };
}

/** Selects the entry that paste/copy-as-layout just pushed to the front. */
function selectNewestActivityFilter(state: ActivityFilterState): ActivityFilterState {
  const newest = state.saved[0];
  if (!newest) return state;
  return { ...state, selectedIds: [newest.id], activeId: newest.id, allActivities: false };
}

function buildFilterDraft(data: FormData, editingId: string, scope: ActivityFilterScope): ActivityFilterDefinition | null {
  const name = String(data.get("filterName") ?? "").trim();
  if (!name) return null;
  // The editor can add, delete and reorder criterion rows; read every index the
  // form actually carries and keep DOM order so And/Or reads top to bottom.
  const indexes = new Set<number>();
  for (const key of data.keys()) {
    const match = /^filter\.field\.(\d+)$/.exec(key);
    if (match) indexes.add(Number(match[1]));
  }
  const criteria: ActivityFilterCriterion[] = [];
  for (const index of [...indexes].sort((left, right) => left - right)) {
    const fieldId = data.get(`filter.field.${index}`);
    const operator = data.get(`filter.operator.${index}`);
    if (typeof fieldId !== "string" || typeof operator !== "string") continue;
    const criterion: ActivityFilterCriterion = {
      fieldId: fieldId as ActivityFilterCriterion["fieldId"],
      operator: operator as ActivityFilterOperator,
      value: String(data.get(`filter.value.${index}`) ?? ""),
    };
    if (operator === "within-range") criterion.highValue = String(data.get(`filter.high.${index}`) ?? "");
    criteria.push(criterion);
  }
  return normalizeActivityFilter({
    id: /^custom:/.test(editingId) ? editingId : undefined,
    name,
    match: data.get("filterMatch"),
    scope,
    criteria,
  });
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
  if (data.has("tableFields")) {
    // An unchecked checkbox is absent from FormData, so the table fieldset
    // carries a marker input and both flags are read as booleans.
    patch.showIcons = data.get("showIcons") === "on";
    presentation.table.showIcons = patch.showIcons;
    if (data.has("tableLineNumbers")) {
      patch.lineNumbers = data.get("lineNumbers") === "on";
      presentation.table.lineNumbers = patch.lineNumbers;
    }
    presentationChanged = true;
  }

  const keys = Array.from(data.keys());

  if (keys.some((key) => key.startsWith("timescale."))) {
    const nextTimescale = normalizeTimescale({
      lines: Number(data.get("timescale.lines")),
      dateFormat: data.get("timescale.dateFormat"),
      type: data.get("timescale.type"),
      interval: data.get("timescale.interval"),
      ordinalStart: String(data.get("timescale.ordinalStart") ?? "").trim() || null,
      ordinalInterval: data.get("timescale.ordinalInterval"),
      fontSize: Number(data.get("timescale.fontSize")),
      textColor: data.get("timescale.textColor"),
      backgroundColor: data.get("timescale.backgroundColor"),
    }, presentation.timescale);
    const intervalChanged = nextTimescale.interval !== presentation.timescale.interval;
    presentation.timescale = nextTimescale;
    // Tick density follows the chosen interval so header groups, ticks and
    // bar geometry stay on the same date range. Only an actual interval change
    // moves the chart scale; opening the dialog and changing a colour or font
    // must not silently reset the zoom the user picked from the toolbar.
    if (intervalChanged) {
      patch.ganttScale = timescaleTickScale(nextTimescale.interval);
    }
    presentationChanged = true;
  }

  // WBS band format: level colours plus the band's own typeface, ink, height
  // and label selection. Every value is presentation-only and saved with the
  // layout; none of it reaches the schedule model.
  const wbsKeys = keys.filter((key) => key.startsWith("wbs."));
  if (wbsKeys.length || data.has("wbsFields")) {
    const levelColors: unknown[] = [];
    for (const key of wbsKeys.filter((key) => /^wbs\.color\.\d+$/.test(key))) {
      levelColors[Number(key.slice("wbs.color.".length))] = data.get(key);
    }
    presentation.wbs = normalizeWbs({
      ...(levelColors.length ? { levelColors } : {}),
      fontFamily: data.get("wbs.fontFamily"),
      fontSize: data.get("wbs.fontSize"),
      inkMode: data.get("wbs.inkMode"),
      textColor: data.get("wbs.textColor"),
      rowHeight: data.get("wbs.rowHeight"),
      // An unchecked checkbox is absent from FormData, so the label toggles are
      // read as booleans only when the band fieldset submitted its marker.
      labels: data.has("wbsFields")
        ? {
          title: data.get("wbs.label.title") === "on",
          code: data.get("wbs.label.code") === "on",
          name: data.get("wbs.label.name") === "on",
        }
        : undefined,
    }, presentation.wbs);
    presentationChanged = true;
  }

  if (data.get("wbsReset") === "1") {
    // Reset restores the band format only; the activity table, timescale, bars,
    // Gantt settings and filters keep their saved values.
    presentation.wbs = {
      ...DEFAULT_PRESENTATION.wbs,
      levelColors: [...DEFAULT_PRESENTATION.wbs.levelColors],
      labels: { ...DEFAULT_PRESENTATION.wbs.labels },
    };
    presentationChanged = true;
  }

  if (keys.some((key) => key.startsWith("gantt."))) {
    const current = presentation.gantt;
    presentation.gantt = normalizeGanttSettings({
      showBarLabels: data.get("gantt.showBarLabels") === "on",
      labelFontSize: data.get("gantt.labelFontSize"),
      labelColor: data.get("gantt.labelColor"),
      legend: {
        visible: data.get("gantt.legend.visible") === "on",
        position: data.get("gantt.legend.position"),
      },
      sightLines: {
        beforeSummaries: data.get("gantt.sightLines.beforeSummaries") === "on",
        rowInterval: data.get("gantt.sightLines.rowInterval"),
        minorVertical: data.get("gantt.sightLines.minorVertical") === "on",
      },
      // A disabled Data Date fieldset submits nothing; keep the saved line
      // settings rather than resetting them to the fallback.
      dataDateLine: data.has("gantt.dataDateLine.style")
        ? {
            visible: data.get("gantt.dataDateLine.visible") === "on",
            style: data.get("gantt.dataDateLine.style"),
            thickness: data.get("gantt.dataDateLine.thickness"),
            color: data.get("gantt.dataDateLine.color"),
          }
        : current.dataDateLine,
      progressLine: {
        visible: data.get("gantt.progressLine.visible") === "on",
        thickness: data.get("gantt.progressLine.thickness"),
        color: data.get("gantt.progressLine.color"),
      },
    }, current);
    presentationChanged = true;
  }

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
        necking: data.get(`${prefix}necking`) === "on",
      }, bars[kind]);
      // A disabled Actual/Baseline fieldset never reaches FormData. Keep its
      // saved appearance, but never draw a bar without authoritative dates.
      if (!data.has(`${prefix}filter`)) bars[kind].visible = false;
    }
    patch.bars = bars;
    presentation.bars = bars;
    presentationChanged = true;
  }

  if (keys.some((key) => key.startsWith("filter"))) {
    const previousFilters = presentation.filters;
    let filters = previousFilters;
    // The version 26 form carries the list marker; older payloads only have
    // filterActiveId and keep the single-selection behaviour.
    const v26 = data.get("filterList") === "v26";
    const action = String(data.get("filterAction") ?? "");
    const selectedIds = data.getAll("filterSelected").map((value) => String(value)).filter(Boolean);
    const allActivities = data.get("filterAllActivities") === "on";
    const scopeRaw = data.get("filterScope");
    const scope: ActivityFilterScope = scopeRaw === "global" || scopeRaw === "user" ? scopeRaw : "layout";
    const editingId = String(data.get("filterEditingId") ?? "");
    const rowId = String(data.get("filterRowId") ?? "");
    // List actions apply to the highlighted row; the builder only owns edits.
    const targetId = rowId || editingId || selectedIds[0] || "";

    if (v26) {
      filters = setActivityFilterAllActivities(filters, allActivities);
      // Disabled Select checkboxes are absent from FormData; keep the saved
      // selection while All Activities is checked instead of clearing it.
      if (!allActivities) filters = selectManyActivityFilters(filters, selectedIds);
      filters = setActivityFilterCombine(filters, data.get("filterCombine") === "any" ? "any" : "all");
      filters = setActivityFilterApplyMode(filters, data.get("filterApplyMode") === "highlight" ? "highlight" : "replace");
    }

    if (!v26) {
      const selectedId = String(data.get("filterActiveId") ?? "");
      const deleteRequested = data.get("filterDelete") === "on";
      if (deleteRequested) {
        filters = deleteActivityFilter(filters, selectedId);
      } else {
        const draft = buildFilterDraft(data, "", scope);
        filters = draft ? upsertActivityFilter(filters, draft) : setActiveActivityFilter(filters, selectedId || null);
      }
    } else if (action === "delete") {
      filters = deleteActivityFilter(filters, targetId);
    } else if (action === "copy") {
      const source = findActivityFilter(filters, targetId);
      if (source) filterClipboard = source;
    } else if (action === "paste") {
      if (filterClipboard) {
        filters = pasteActivityFilter(filters, filterClipboard, scope);
        filters = selectNewestActivityFilter(filters);
      }
    } else if (action === "make-global") {
      filters = makeGlobalActivityFilter(filters, targetId);
    } else if (action === "copy-as-layout") {
      filters = copyActivityFilterAsLayout(filters, targetId);
      filters = selectNewestActivityFilter(filters);
    } else {
      const draft = buildFilterDraft(data, editingId, scope);
      if (draft) filters = upsertActivityFilter(filters, draft);
    }

    const signature = (state: typeof filters): string => JSON.stringify({
      saved: state.saved,
      selectedIds: state.selectedIds ?? (state.activeId ? [state.activeId] : []),
      combine: state.combine ?? "all",
      allActivities: Boolean(state.allActivities),
      applyMode: state.applyMode ?? "replace",
    });
    if (signature(filters) !== signature(previousFilters)) {
      presentation.filters = filters;
      presentationChanged = true;
    }
  }

  if (data.get("tableReset") === "1") {
    // Reset replaces only the table presentation; timescale, bars, Gantt
    // settings, WBS colours and filters keep their saved values.
    presentation.table = { ...DEFAULT_PRESENTATION.table };
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
    // The axis density must follow the default timescale, otherwise Restore
    // Defaults leaves a default header over day-density ticks.
    ganttScale: timescaleTickScale(DEFAULT_PRESENTATION.timescale.interval),
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
