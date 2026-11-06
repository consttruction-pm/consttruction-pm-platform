import type { WorkspaceState } from "./workspace-model.js";
import type { ActivityFilterDraft, ActivityFilterField } from "./workspace-activity-filters.js";
import { operatorsForActivityField, validateActivityFilterDraft } from "./workspace-activity-filters.js";
import type { ActivityFilterCriterion, ActivityFilterOperator, SavedActivityFilter } from "./p6-activity-filter-api.js";

export type ActivityFilterDialogLabels = {
  filters: string; allActivities: string; showActivities: string; allSelected: string; anySelected: string;
  filter: string; select: string; default: string; global: string; layout: string; userDefined: string;
  applying: string; replace: string; highlight: string; ok: string; cancel: string; apply: string;
  new: string; delete: string; copy: string; paste: string; modify: string; makeGlobal: string;
  copyAsLayout: string; help: string; filterName: string; displayFilter: string; displayAllRows: string;
  parameter: string; is: string; value: string; highValue: string; where: string; and: string; or: string;
  add: string; cut: string; moveUp: string; moveDown: string; noFilters: string; noFields: string;
  noSelection: string; noCriteria: string; save: string; defaultLocked: string; selectFilterToModify: string;
};

export function getActivityFilterDialogLabels(locale: string): ActivityFilterDialogLabels {
  const fa = locale.toLowerCase().startsWith("fa");
  return fa ? {
    filters: "فیلترها", allActivities: "همهٔ فعالیت‌ها", showActivities: "نمایش فعالیت‌هایی که با فیلترهای زیر مطابقت دارند",
    allSelected: "همهٔ فیلترهای انتخاب‌شده", anySelected: "هر یک از فیلترهای انتخاب‌شده",
    filter: "فیلتر", select: "انتخاب", default: "پیش‌فرض", global: "سراسری", layout: "چیدمان", userDefined: "تعریف‌شده توسط کاربر",
    applying: "هنگام اعمال فیلترهای انتخاب‌شده", replace: "جایگزینی فعالیت‌های نمایش‌داده‌شده در چیدمان جاری",
    highlight: "برجسته‌کردن فعالیت‌های منطبق در چیدمان جاری", ok: "تأیید", cancel: "انصراف", apply: "اعمال",
    new: "جدید", delete: "حذف", copy: "کپی", paste: "چسباندن", modify: "ویرایش", makeGlobal: "سراسری‌کردن",
    copyAsLayout: "کپی به‌عنوان چیدمان", help: "راهنما", filterName: "نام فیلتر", displayFilter: "نمایش: فیلتر",
    displayAllRows: "نمایش همهٔ ردیف‌های منطبق", parameter: "پارامتر", is: "شرط", value: "مقدار",
    highValue: "مقدار بالا", where: "Where", and: "And", or: "Or", add: "افزودن", cut: "برش",
    moveUp: "انتقال به بالا", moveDown: "انتقال به پایین", noFilters: "فیلتر ذخیره‌شده‌ای در این گروه وجود ندارد.",
    noFields: "فیلد قابل فیلتر در Activity ثبت نشده است.", noSelection: "ابتدا یک فیلتر را انتخاب کنید.",
    noCriteria: "هنوز شرطی تعریف نشده است.", save: "ذخیره",
    defaultLocked: "فیلترهای پیش‌فرض فقط برای خواندن هستند؛ برای تغییر، یک نسخه کپی کنید.",
    selectFilterToModify: "برای ویرایش یک فیلتر انتخاب کنید.",
  } : {
    filters: "Filters", allActivities: "All Activities", showActivities: "Show activities that match",
    allSelected: "All selected filters", anySelected: "Any selected filter",
    filter: "Filter", select: "Select", default: "Default", global: "Global", layout: "Layout", userDefined: "User-Defined",
    applying: "When applying the selected filter(s)", replace: "Replace activities shown in current layout",
    highlight: "Highlight activities in current layout which match criteria", ok: "OK", cancel: "Cancel",
    apply: "Apply", new: "New", delete: "Delete", copy: "Copy", paste: "Paste", modify: "Modify",
    makeGlobal: "Make Global", copyAsLayout: "Copy as Layout", help: "Help", filterName: "Filter Name",
    displayFilter: "Display: Filter", displayAllRows: "Display all rows", parameter: "Parameter", is: "Is",
    value: "Value", highValue: "High Value", where: "Where", and: "And", or: "Or", add: "Add", cut: "Cut",
    moveUp: "Move Up", moveDown: "Move Down", noFilters: "There are no saved filters in this group.",
    noFields: "No filterable Activity fields are registered.", noSelection: "Select a filter first.",
    noCriteria: "No criteria have been added yet.", save: "Save",
    defaultLocked: "Default filters are read-only. Copy a filter before editing it.",
    selectFilterToModify: "Select one filter to modify.",
  };
}

function html(value: unknown): string {
  return String(value ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

export function activityFilterFields(state: WorkspaceState): ActivityFilterField[] {
  return (state.p6FieldRegistry?.fields ?? [])
    .filter((field) => ["activity", "activities"].includes(field.subject_area.toLowerCase()) && field.filterable !== false)
    .map((field) => ({
      field_id: field.field_id,
      display_name: field.display_name || field.field_id,
      data_type: field.data_type,
      filterable: field.filterable,
      unit: field.unit,
    }))
    .filter((field) => operatorsForActivityField(field.data_type).length > 0);
}

function groupRows(
  filters: readonly SavedActivityFilter[],
  category: "layout" | "user-defined",
  selected: ReadonlySet<string>,
  labels: ActivityFilterDialogLabels,
): string {
  const title = category === "layout" ? labels.layout : labels.userDefined;
  const rows = filters.filter((item) => item.category === category);
  const content = rows.length ? rows.map((item) =>
    '<tr data-filter-register-row="' + html(item.filter_id) + '">' +
    '<td><button type="button" class="cp-filter-name" data-activity-filter-modify="' + html(item.filter_id) + '">' + html(item.name) + '</button></td>' +
    '<td><input type="checkbox" data-activity-filter-select="' + html(item.filter_id) + '" aria-label="' + html(labels.select + " " + item.name) + '"' +
    (selected.has(item.filter_id) ? " checked" : "") + '></td></tr>'
  ).join("") : '<tr class="cp-filter-empty-row"><td colspan="2">' + html(labels.noFilters) + '</td></tr>';
  return '<tr class="cp-filter-category-row"><th colspan="2">' + html(title) + '</th></tr>' + content;
}

export function renderActivityFilterManagerDialog(state: WorkspaceState): string {
  const t = getActivityFilterDialogLabels(state.locale);
  const selected = new Set(state.selectedActivityFilterIds);
  const selectedCount = selected.size;
  const filters = state.activityFilters;
  const countText = state.locale.toLowerCase().startsWith("fa") ? "فیلتر ذخیره‌شده" : "saved filters";
  return '<dialog class="cp-activity-filter-manager" data-activity-filter-manager aria-labelledby="cp-activity-filter-manager-title">' +
    '<header class="cp-activity-filter-dialog-title"><strong id="cp-activity-filter-manager-title">' + html(t.filters) + '</strong>' +
    '<button type="button" data-activity-filter-manager-close aria-label="' + html(t.cancel) + '">×</button></header>' +
    '<div class="cp-filter-manager-body"><section class="cp-filter-manager-main">' +
    '<fieldset class="cp-filter-radio-group"><legend>' + html(t.showActivities) + '</legend>' +
    '<label><input type="radio" name="activity-filter-combination" value="all"' + (state.activityFilterCombination === "all" ? " checked" : "") + '>' + html(t.allSelected) + '</label>' +
    '<label><input type="radio" name="activity-filter-combination" value="any"' + (state.activityFilterCombination === "any" ? " checked" : "") + '>' + html(t.anySelected) + '</label></fieldset>' +
    '<div class="cp-filter-register-wrap"><table class="cp-filter-register" aria-label="' + html(t.filters) + '">' +
    '<thead><tr><th>' + html(t.filter) + ' <span aria-hidden="true">↕</span></th><th>' + html(t.select) + ' <span aria-hidden="true">↕</span></th></tr></thead><tbody>' +
    '<tr class="cp-filter-category-row"><th colspan="2">' + html(t.default) + '</th></tr>' +
    '<tr data-filter-register-row="all-activities"><td><button type="button" class="cp-filter-name" data-activity-filter-all>' + html(t.allActivities) + '</button></td><td><input type="checkbox" aria-label="' + html(t.select + " " + t.allActivities) + '" disabled></td></tr>' +
    '<tr class="cp-filter-category-row"><th colspan="2">' + html(t.global) + '</th></tr>' +
    '<tr class="cp-filter-empty-row"><td colspan="2">' + html(t.noFilters) + '</td></tr>' +
    groupRows(filters, "layout", selected, t) + groupRows(filters, "user-defined", selected, t) +
    '</tbody></table></div>' +
    '<fieldset class="cp-filter-radio-group cp-filter-apply-mode"><legend>' + html(t.applying) + '</legend>' +
    '<label><input type="radio" name="activity-filter-application" value="replace"' + (state.activityFilterApplication === "replace" ? " checked" : "") + '>' + html(t.replace) + '</label>' +
    '<label><input type="radio" name="activity-filter-application" value="highlight"' + (state.activityFilterApplication === "highlight" ? " checked" : "") + '>' + html(t.highlight) + '</label></fieldset></section>' +
    '<aside class="cp-filter-command-strip" aria-label="' + html(t.filters) + '">' +
    '<button type="button" data-activity-filter-manager-ok>' + html(t.ok) + '</button>' +
    '<button type="button" data-activity-filter-manager-close>' + html(t.cancel) + '</button>' +
    '<button type="button" data-activity-filter-apply>' + html(t.apply) + '</button><span class="cp-filter-command-separator"></span>' +
    '<button type="button" data-activity-filter-new>' + html(t.new) + '</button>' +
    '<button type="button" data-activity-filter-delete' + (selectedCount === 1 ? "" : " disabled") + '>' + html(t.delete) + '</button>' +
    '<button type="button" data-activity-filter-copy' + (selectedCount === 1 ? "" : " disabled") + '>' + html(t.copy) + '</button>' +
    '<button type="button" data-activity-filter-paste disabled>' + html(t.paste) + '</button>' +
    '<button type="button" data-activity-filter-modify-selected' + (selectedCount === 1 ? "" : " disabled") + '>' + html(t.modify) + '</button>' +
    '<button type="button" data-activity-filter-make-global disabled>' + html(t.makeGlobal) + '</button>' +
    '<button type="button" data-activity-filter-copy-layout disabled>' + html(t.copyAsLayout) + '</button>' +
    '<span class="cp-filter-command-separator"></span><button type="button" data-activity-filter-help>' + html(t.help) + '</button></aside></div>' +
    '<footer class="cp-filter-manager-status"><span>' + filters.length + " " + html(countText) + '</span></footer></dialog>';
}

function fieldOptions(fields: readonly ActivityFilterField[], current: string): string {
  return '<option value="">—</option>' + fields.map((field) =>
    '<option value="' + html(field.field_id) + '"' + (field.field_id === current ? " selected" : "") + '>' +
    html(field.display_name) + ' · ' + html(field.field_id) + '</option>'
  ).join("");
}

function operatorOptions(field: ActivityFilterField | undefined, current: string): string {
  if (!field) return '<option value="equals">' + html(current || "equals") + '</option>';
  const names: Record<string, string> = {
    equals: "is equal to", "not-equals": "is not equal to", contains: "contains", "not-contains": "does not contain",
    "starts-with": "starts with", "ends-with": "ends with", "greater-than": "is greater than",
    "greater-than-or-equal": "is greater than or equal to", "less-than": "is less than",
    "less-than-or-equal": "is less than or equal to", between: "is between", "not-between": "is not between",
    "is-empty": "is empty", "is-not-empty": "is not empty",
  };
  return operatorsForActivityField(field.data_type).map((operator) =>
    '<option value="' + operator + '"' + (operator === current ? " selected" : "") + '>' +
    html(names[operator] ?? operator) + '</option>'
  ).join("");
}

export function renderActivityFilterEditorContents(
  state: WorkspaceState,
  draft: ActivityFilterDraft,
  selectedRow = 0,
  errorMessage = "",
): string {
  const t = getActivityFilterDialogLabels(state.locale);
  const fields = activityFilterFields(state);
  const rows = draft.criteria.map((item, index) => {
    const field = fields.find((candidate) => candidate.field_id === item.field_id);
    const range = item.operator === "between" || item.operator === "not-between";
    const emptyOperator = item.operator === "is-empty" || item.operator === "is-not-empty";
    const connector = index === 0 ? "where" : item.connector;
    return '<tr tabindex="0" data-activity-filter-criterion-row="' + index + '" class="' + (selectedRow === index ? "is-selected" : "") +
      '" aria-selected="' + String(selectedRow === index) + '">' +
      '<td><select data-filter-connector="' + index + '" aria-label="' + html(t.displayAllRows) + '"' + (index === 0 ? " disabled" : "") + '>' +
      '<option value="where"' + (connector === "where" ? " selected" : "") + '>' + html(t.where) + '</option>' +
      '<option value="and"' + (connector === "and" ? " selected" : "") + '>' + html(t.and) + '</option>' +
      '<option value="or"' + (connector === "or" ? " selected" : "") + '>' + html(t.or) + '</option></select></td>' +
      '<td><select data-filter-field="' + index + '" aria-label="' + html(t.parameter) + '">' + fieldOptions(fields, item.field_id) + '</select></td>' +
      '<td><select data-filter-operator="' + index + '" aria-label="' + html(t.is) + '">' + operatorOptions(field, item.operator) + '</select></td>' +
      '<td><input type="text" data-filter-value="' + index + '" value="' + html(emptyOperator ? "" : item.value ?? "") + '" aria-label="' + html(t.value) + '"' + (emptyOperator ? " disabled" : "") + '></td>' +
      '<td><input type="text" data-filter-high-value="' + index + '" value="' + html(item.high_value ?? "") + '" aria-label="' + html(t.highValue) + '"' + (range ? "" : " disabled") + '></td></tr>';
  }).join("");
  return '<form data-activity-filter-editor-form novalidate>' +
    '<header class="cp-filter-editor-name-row"><label>' + html(t.filterName) +
    ' <input type="text" name="activity_filter_name" maxlength="80" required value="' + html(draft.name) + '"></label>' +
    '<span class="cp-filter-editor-kind">' + html(draft.category === "layout" ? t.layout : t.userDefined) + ' · R' + draft.expected_revision + '</span></header>' +
    '<details class="cp-filter-editor-display" open><summary>' + html(t.displayFilter) + '</summary><label>' + html(t.displayAllRows) +
    '<select name="activity_filter_match_mode" data-filter-match-mode><option value="all"' + (draft.match_mode === "all" ? " selected" : "") +
    '>[All of the following]</option><option value="any"' + (draft.match_mode === "any" ? " selected" : "") +
    '>[Any of the following]</option></select></label></details>' +
    '<div class="cp-filter-editor-layout"><div class="cp-filter-criteria-scroll"><table class="cp-filter-criteria-grid" aria-label="' + html(t.displayFilter) + '">' +
    '<thead><tr><th>' + html(t.displayAllRows) + '</th><th>' + html(t.parameter) + '</th><th>' + html(t.is) + '</th><th>' + html(t.value) + '</th><th>' + html(t.highValue) +
    '</th></tr></thead><tbody>' + (rows || '<tr><td colspan="5" class="cp-filter-no-criteria">' + html(t.noCriteria) + '</td></tr>') + '</tbody></table></div>' +
    '<aside class="cp-filter-editor-command-strip" aria-label="' + html(t.displayFilter) + '">' +
    '<button type="submit" data-activity-filter-editor-save>' + html(t.ok) + '</button><button type="button" data-activity-filter-editor-cancel>' + html(t.cancel) + '</button>' +
    '<span class="cp-filter-command-separator"></span><button type="button" data-activity-filter-add-criterion>' + html(t.add) + '</button>' +
    '<button type="button" data-activity-filter-delete-criterion' + (draft.criteria.length > 1 ? "" : " disabled") + '>' + html(t.delete) + '</button>' +
    '<button type="button" data-activity-filter-cut-criterion disabled>' + html(t.cut) + '</button>' +
    '<button type="button" data-activity-filter-copy-criterion disabled>' + html(t.copy) + '</button>' +
    '<button type="button" data-activity-filter-paste-criterion disabled>' + html(t.paste) + '</button>' +
    '<button type="button" data-activity-filter-move-criterion="up"' + (selectedRow > 0 ? "" : " disabled") + ' title="' + html(t.moveUp) + '">↑</button>' +
    '<button type="button" data-activity-filter-move-criterion="down"' + (selectedRow >= 0 && selectedRow < draft.criteria.length - 1 ? "" : " disabled") + ' title="' + html(t.moveDown) + '">↓</button>' +
    '<span class="cp-filter-command-separator"></span><button type="button" data-activity-filter-help>' + html(t.help) + '</button></aside></div>' +
    '<output class="cp-filter-editor-error" data-activity-filter-editor-error role="alert">' + html(errorMessage) + '</output></form>';
}

export function readActivityFilterDraftFromForm(form: HTMLFormElement, template: ActivityFilterDraft): ActivityFilterDraft {
  const name = form.querySelector<HTMLInputElement>('[name="activity_filter_name"]')?.value ?? "";
  const matchMode = form.querySelector<HTMLSelectElement>('[name="activity_filter_match_mode"]')?.value === "any" ? "any" : "all";
  const rows = Array.from(form.querySelectorAll<HTMLTableRowElement>("[data-activity-filter-criterion-row]"));
  const criteria: ActivityFilterCriterion[] = rows.map((row, index) => {
    const connector = row.querySelector<HTMLSelectElement>("[data-filter-connector]")?.value;
    const fieldId = row.querySelector<HTMLSelectElement>("[data-filter-field]")?.value ?? "";
    const operator = row.querySelector<HTMLSelectElement>("[data-filter-operator]")?.value ?? "equals";
    const value = row.querySelector<HTMLInputElement>("[data-filter-value]")?.value ?? "";
    const highValue = row.querySelector<HTMLInputElement>("[data-filter-high-value]")?.value ?? "";
    return {
      connector: index === 0 ? "where" : connector === "or" ? "or" : "and",
      field_id: fieldId,
      operator: operator as ActivityFilterOperator,
      value: operator === "is-empty" || operator === "is-not-empty" ? null : value,
      high_value: operator === "between" || operator === "not-between" ? highValue : null,
    };
  });
  return { ...template, name, match_mode: matchMode, criteria };
}

export function activityFilterDraftError(draft: ActivityFilterDraft, fields: readonly ActivityFilterField[]): string | null {
  return validateActivityFilterDraft(draft, fields);
}

export function criterionForNewRow(fields: readonly ActivityFilterField[], draft: ActivityFilterDraft): ActivityFilterCriterion {
  const last = draft.criteria[draft.criteria.length - 1];
  const field = fields.find((candidate) => candidate.field_id === last?.field_id) ??
    fields.find((candidate) => candidate.filterable !== false && operatorsForActivityField(candidate.data_type).length > 0);
  return {
    connector: draft.match_mode === "all" ? "and" : "or",
    field_id: field?.field_id ?? "",
    operator: field ? operatorsForActivityField(field.data_type)[0] : "equals",
    value: "",
    high_value: null,
  };
}
