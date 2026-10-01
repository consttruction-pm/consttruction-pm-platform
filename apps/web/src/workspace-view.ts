import type { WorkspaceActivityRow, WorkspaceCellValue, WorkspaceState } from "./workspace-model.js";
import { createGanttBarGeometry, createGanttScale } from "./workspace-gantt.js";
import { getWorkspaceNavigation, getWorkspaceNavigationLabel, getWorkspaceNavigationStatusLabel } from "./workspace-navigation.js";
import type { P6FormulaEditorState } from "./p6-formula-editor.js";
import { renderP6FormulaEditor } from "./p6-formula-editor-view.js";
import { renderP6ReportPrintFieldSelection } from "./p6-report-print-field-selection-view.js";
import type { P6GridFilter, P6GridGroup, P6GridSort } from "./p6-activity-wbs-grid.js";
import type { ColumnPresentation } from "./p6-field-layout-foundation.js";

const labels = {
  en: {
    project: "Project", schedule: "Schedule", progress: "Progress", resources: "Resources", cost: "Cost", documents: "Documents", procurement: "Procurement", reports: "Reports", control: "Control", settings: "Settings",
    wbs: "Project / WBS", activities: "Activity Grid", gantt: "Gantt Chart", details: "Details", issues: "Field Issues", assurance: "Field Assurance", noActivities: "No activities loaded", noSchedule: "No scheduled activities", revision: "Revision", critical: "Critical", smartGuide: "Smart Guide", controlSummary: "Control Summary", findings: "Findings", metrics: "Metrics", commercial: "Changes & Claims", siteLogs: "Daily Field Logs", attendance: "Attendance", equipment: "Equipment",
  },
  fa: {
    project: "پروژه", schedule: "زمان‌بندی", progress: "پیشرفت", resources: "منابع", cost: "هزینه", documents: "اسناد", procurement: "تدارکات", reports: "گزارش‌ها", control: "کنترل", settings: "تنظیمات",
    wbs: "پروژه / WBS", activities: "جدول فعالیت‌ها", gantt: "گانت", details: "جزئیات", issues: "مسائل کارگاه", assurance: "کنترل کیفیت و ایمنی", noActivities: "فعالیتی بارگذاری نشده است", noSchedule: "فعالیت زمان‌بندی‌شده‌ای وجود ندارد", revision: "نسخه", critical: "بحرانی", smartGuide: "راهنمای هوشمند", controlSummary: "خلاصه کنترل", findings: "یافته‌ها", metrics: "شاخص‌ها", commercial: "تغییرات و ادعاها", siteLogs: "گزارش‌های روزانه کارگاه", attendance: "حضور و غیاب", equipment: "ماشین‌آلات",
  },
} as const;

type WorkspaceLabels = Record<keyof typeof labels.en, string>;

export type WorkspaceRendererOptions = {
  onMenuSelect?: (menu: WorkspaceState["activeMenu"]) => void;
  onWbsSelect?: (wbsId: string) => void;
  onActivitySelect?: (activityId: string) => void;
  onP6FieldAdd?: (fieldId: string) => void;
  onP6FieldRemove?: (fieldId: string) => void;
  onP6FieldReorder?: (orderedFieldIds: readonly string[]) => void;
  onP6FieldPresentationChange?: (fieldId: string, patch: Partial<Omit<ColumnPresentation, "field_id">>) => void;
  p6FormulaEditorState?: P6FormulaEditorState | null;
  p6ReportPrintSelection?: { field_ids: readonly string[] } | null;
  onP6ReportPrintSelectionChange?: (fieldIds: readonly string[]) => void;
  onP6ReportPrintReset?: () => void;
  p6GridPresentation?: { sorts: readonly P6GridSort[]; groups: readonly P6GridGroup[]; filters: readonly P6GridFilter[] } | null;
  onP6GridSortChange?: (sorts: readonly P6GridSort[]) => void;
  onP6GridGroupChange?: (groups: readonly P6GridGroup[]) => void;
  onP6GridFilterChange?: (filters: readonly P6GridFilter[]) => void;
};

export function renderMainWorkspace(container: HTMLElement, state: WorkspaceState, options: WorkspaceRendererOptions = {}): void {
  const t = labels[state.locale];
  const wbsIds = [...new Set(state.activities.map((activity) => activity.wbsId))];
  const scale = createGanttScale(state.activities);

  container.innerHTML = `
    <section class="cp-workspace" dir="${state.direction}" data-project="${escapeAttribute(state.context.project_id)}">
      <header class="cp-header">
        <div class="cp-brand">Construction PM</div>
        <div class="cp-project">${escapeHtml(state.context.project_id)}</div>
        <div class="cp-revision">${escapeHtml(t.revision)} R${state.context.revision}</div>
      </header>
      <nav class="cp-menu" aria-label="Main Menu">
        ${menuButton("project", t.project, state)} ${menuButton("schedule", t.schedule, state)} ${menuButton("progress", t.progress, state)} ${menuButton("resources", t.resources, state)} ${menuButton("cost", t.cost, state)} ${menuButton("documents", t.documents, state)} ${menuButton("reports", t.reports, state)} ${menuButton("control", t.control, state)} ${menuButton("settings", t.settings, state)}
      </nav>
      ${renderNavigationSurface(state)}
      <main class="cp-main">
        ${renderSmartGuide(state.smartGuide, t.smartGuide)}
        ${renderControlSummary(state.controlSummary, t.controlSummary, t.metrics, t.findings)}
        ${renderSiteDailyLogs(state.siteDailyLogs, t.siteLogs)}
        ${renderFieldOperations(state.fieldIssues, state.timecards, state.equipmentReports, t)}
        ${renderFieldAssurance(state.inspections, state.qualityRecords, state.safetyObservations, state.punchItems, t.assurance)}
        ${renderChangeClaimControl(state.changeNotices, state.changeCases, state.claims, state.changeClaimImpacts, t.commercial)}
        ${renderProcurement(state.procurementRecords, t.procurement)}
        <aside class="cp-panel cp-wbs" aria-label="${escapeAttribute(t.wbs)}">
          <h2>${t.wbs}</h2>
          ${wbsIds.length ? wbsIds.map((wbsId) => `<button type="button" class="cp-wbs-node${state.selectedWbsId === wbsId ? " is-selected" : ""}" data-wbs-id="${escapeAttribute(wbsId)}" aria-current="${state.selectedWbsId === wbsId ? "true" : "false"}">${escapeHtml(wbsId)}</button>`).join("") : `<div class="cp-empty">${t.noActivities}</div>`}
        </aside>
        <section class="cp-center">
          <section class="cp-panel cp-grid">
            <h2>${t.activities}</h2>
            ${renderP6FieldChooser(state)}
            ${renderP6ColumnPresentation(state, options)}
            ${renderWorkspaceFormulaEditor(options.p6FormulaEditorState, state.locale)}
            ${renderWorkspaceReportPrintSelection(state, options.p6ReportPrintSelection)}
            ${renderWorkspaceGridPresentation(state, options)}
            <div class="cp-table-wrap">
              <table>
                <thead><tr>${state.columns.map((column) => `<th data-column-type="${column.dataType}" style="width:${column.width}px">${escapeHtml(column.label)}${column.formula ? '<span aria-label="formula column">ƒx</span>' : ""}</th>`).join("")}</tr></thead>
                <tbody>${state.activities.length ? state.activities.map((activity) => renderActivityRow(activity, state)).join("") : `<tr><td colspan="${Math.max(1, state.columns.length)}">${t.noActivities}</td></tr>`}</tbody>
              </table>
            </div>
          </section>
          <section class="cp-panel cp-gantt"><h2>${t.gantt}</h2>${renderGantt(state.activities, scale, t.gantt, t.noSchedule, t.critical)}</section>
        </section>
        <aside class="cp-panel cp-details"><h2>${t.details}</h2>${state.selectedActivityId ? `<div class="cp-detail-selected">${escapeHtml(state.selectedActivityId)}</div>` : `<div class="cp-empty">—</div>`}</aside>
      </main>
    </section>
  `;

  container.querySelectorAll<HTMLElement>("[data-menu]").forEach((button) => button.addEventListener("click", () => options.onMenuSelect?.(button.dataset.menu as WorkspaceState["activeMenu"])));
  container.querySelectorAll<HTMLElement>("[data-wbs-id]").forEach((button) => button.addEventListener("click", () => { const wbsId = button.dataset.wbsId; if (wbsId) options.onWbsSelect?.(wbsId); }));
  container.querySelectorAll<HTMLElement>("[data-p6-field-add]").forEach((button) => button.addEventListener("click", () => {
    const fieldId = button.dataset.p6FieldAdd;
    if (fieldId) options.onP6FieldAdd?.(fieldId);
  }));
  container.querySelectorAll<HTMLElement>("[data-p6-field-remove]").forEach((button) => button.addEventListener("click", () => {
    const fieldId = button.dataset.p6FieldRemove;
    if (fieldId) options.onP6FieldRemove?.(fieldId);
  }));
  container.querySelectorAll<HTMLElement>("[data-p6-field-move-up], [data-p6-field-move-down]").forEach((button) => button.addEventListener("click", () => {
    const fieldId = button.dataset.p6FieldMoveUp ?? button.dataset.p6FieldMoveDown;
    if (!fieldId || !state.p6Layout) return;
    const orderedFieldIds = state.p6Layout.columns.slice().sort((a, b) => a.order - b.order).map((column) => column.field_id);
    const index = orderedFieldIds.indexOf(fieldId);
    if (index < 0) return;
    const delta = button.dataset.p6FieldMoveUp !== undefined ? -1 : 1;
    const target = index + delta;
    if (target < 0 || target >= orderedFieldIds.length) return;
    [orderedFieldIds[index], orderedFieldIds[target]] = [orderedFieldIds[target], orderedFieldIds[index]];
    options.onP6FieldReorder?.(orderedFieldIds);
  }));
  container.querySelectorAll<HTMLInputElement>("[data-p6-column-label]").forEach((input) => input.addEventListener("change", () => {
    const fieldId = input.dataset.p6ColumnLabel;
    if (fieldId) options.onP6FieldPresentationChange?.(fieldId, { label: input.value });
  }));
  container.querySelectorAll<HTMLInputElement>("[data-p6-column-width]").forEach((input) => input.addEventListener("change", () => {
    const fieldId = input.dataset.p6ColumnWidth;
    const width = Number(input.value);
    if (fieldId && Number.isFinite(width) && width > 0) options.onP6FieldPresentationChange?.(fieldId, { width });
  }));
  container.querySelectorAll<HTMLSelectElement>("[data-p6-column-alignment]").forEach((select) => select.addEventListener("change", () => {
    const fieldId = select.dataset.p6ColumnAlignment;
    if (fieldId) options.onP6FieldPresentationChange?.(fieldId, { alignment: select.value as ColumnPresentation["alignment"] });
  }));
  container.querySelectorAll<HTMLInputElement>("[data-p6-column-pinned]").forEach((input) => input.addEventListener("change", () => {
    const fieldId = input.dataset.p6ColumnPinned;
    if (fieldId) options.onP6FieldPresentationChange?.(fieldId, { pinned: input.checked });
  }));
  container.querySelectorAll<HTMLInputElement>("[data-p6-column-frozen]").forEach((input) => input.addEventListener("change", () => {
    const fieldId = input.dataset.p6ColumnFrozen;
    if (fieldId) options.onP6FieldPresentationChange?.(fieldId, { frozen: input.checked });
  }));

  container.querySelectorAll<HTMLElement>("[data-p6-grid-sort-remove]").forEach((button) => button.addEventListener("click", () => {
    const row = button.closest<HTMLElement>("[data-p6-grid-sort-row]");
    if (!row) return;
    const order = Number(row.dataset.order ?? "0");
    const current = getWorkspaceGridPresentation(state, options)?.sorts ?? [];
    options.onP6GridSortChange?.(current.filter((_sort, index) => index !== order));
  }));
  container.querySelectorAll<HTMLElement>("[data-p6-grid-group-remove]").forEach((button) => button.addEventListener("click", () => {
    const row = button.closest<HTMLElement>("[data-p6-grid-group-row]");
    if (!row) return;
    const order = Number(row.dataset.order ?? "0");
    const current = getWorkspaceGridPresentation(state, options)?.groups ?? [];
    options.onP6GridGroupChange?.(current.filter((_group, index) => index !== order));
  }));

  container.querySelectorAll<HTMLSelectElement>("[data-p6-grid-sort-field]").forEach((select) => select.addEventListener("change", () => {
    const row = select.closest<HTMLElement>("[data-p6-grid-sort-row]");
    if (!row) return;
    const order = Number(row.dataset.order ?? "0");
    const current = getWorkspaceGridPresentation(state, options)?.sorts ?? [];
    options.onP6GridSortChange?.(current.map((sort) => sort.order === order ? { ...sort, field_id: select.value } : sort));
  }));
  container.querySelectorAll<HTMLSelectElement>("[data-p6-grid-sort-direction]").forEach((select) => select.addEventListener("change", () => {
    const row = select.closest<HTMLElement>("[data-p6-grid-sort-row]");
    if (!row) return;
    const order = Number(row.dataset.order ?? "0");
    const current = getWorkspaceGridPresentation(state, options)?.sorts ?? [];
    options.onP6GridSortChange?.(current.map((sort) => sort.order === order ? { ...sort, direction: select.value as P6GridSort["direction"] } : sort));
  }));
  container.querySelectorAll<HTMLSelectElement>("[data-p6-grid-group-field]").forEach((select) => select.addEventListener("change", () => {
    const row = select.closest<HTMLElement>("[data-p6-grid-group-row]");
    if (!row) return;
    const order = Number(row.dataset.order ?? "0");
    const current = getWorkspaceGridPresentation(state, options)?.groups ?? [];
    options.onP6GridGroupChange?.(current.map((group) => group.order === order ? { ...group, field_id: select.value } : group));
  }));
  container.querySelectorAll<HTMLSelectElement>("[data-p6-grid-filter-field]").forEach((select) => select.addEventListener("change", () => {
    const row = select.closest<HTMLElement>("[data-p6-grid-filter-row]");
    if (!row) return;
    const order = Number(row.dataset.order ?? "0");
    const current = getWorkspaceGridPresentation(state, options)?.filters ?? [];
    options.onP6GridFilterChange?.(current.map((filter, index) => index === order
      ? { ...filter, field_id: select.value }
      : filter));
  }));

  container.querySelectorAll<HTMLSelectElement>("[data-p6-grid-filter-operator]").forEach((select) => select.addEventListener("change", () => {
    const row = select.closest<HTMLElement>("[data-p6-grid-filter-row]");
    if (!row) return;
    const order = Number(row.dataset.order ?? "0");
    const current = getWorkspaceGridPresentation(state, options)?.filters ?? [];
    options.onP6GridFilterChange?.(current.map((filter, index) => index === order ? { ...filter, operator: select.value as P6GridFilter["operator"] } : filter));
  }));

  container.querySelectorAll<HTMLInputElement>("[data-p6-grid-filter-value]").forEach((input) => input.addEventListener("change", () => {
    const row = input.closest<HTMLElement>("[data-p6-grid-filter-row]");
    if (!row) return;
    const order = Number(row.dataset.order ?? "0");
    const current = getWorkspaceGridPresentation(state, options)?.filters ?? [];
    options.onP6GridFilterChange?.(current.map((filter, index) => index === order ? { ...filter, value: input.value } : filter));
  }));
  container.querySelectorAll<HTMLElement>("[data-p6-grid-filter-remove]").forEach((button) => button.addEventListener("click", () => {
    const row = button.closest<HTMLElement>("[data-p6-grid-filter-row]");
    if (!row) return;
    const order = Number(row.dataset.order ?? "0");
    const current = getWorkspaceGridPresentation(state, options)?.filters ?? [];
    options.onP6GridFilterChange?.(current.filter((_filter, index) => index !== order));
  }));

  container.querySelectorAll<HTMLInputElement>("[data-p6-report-field-id]").forEach((input) => input.addEventListener("change", () => {
    const fieldIds = Array.from(container.querySelectorAll<HTMLInputElement>("[data-p6-report-field-id]:checked"))
      .map((field) => field.dataset.p6ReportFieldId)
      .filter((fieldId): fieldId is string => Boolean(fieldId));
    options.onP6ReportPrintSelectionChange?.(fieldIds);
  }));
  container.querySelectorAll<HTMLElement>("[data-p6-report-reset]").forEach((button) => button.addEventListener("click", () => options.onP6ReportPrintReset?.()));

  container.querySelectorAll<HTMLElement>("[data-activity-id]").forEach((row) => {
    const select = () => { const id = row.dataset.activityId; if (id) options.onActivitySelect?.(id); };
    row.addEventListener("click", select);
    row.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); select(); } });
  });
}

function renderP6ColumnPresentation(state: WorkspaceState, options: WorkspaceRendererOptions): string {
  if (!state.p6Layout || !state.p6FieldRegistry) return "";
  const fields = new Map(state.p6FieldRegistry.fields.map((field) => [field.field_id, field]));
  const title = state.locale === "fa" ? "تنظیمات ستون‌ها" : "Column Presentation";
  const alignmentLabels = state.locale === "fa"
    ? { start: "ابتدا", center: "وسط", end: "انتها" }
    : { start: "Start", center: "Center", end: "End" };
  const rows = state.p6Layout.columns
    .slice()
    .sort((a, b) => a.order - b.order)
    .map((column) => {
      const field = fields.get(column.field_id);
      if (!field) return "";
      const label = column.label ?? field.display_name;
      return `<div data-p6-column-presentation-row data-field-id="${escapeAttribute(column.field_id)}">
        <strong>${escapeHtml(field.display_name)}</strong>
        <input data-p6-column-label="${escapeAttribute(column.field_id)}" aria-label="${escapeAttribute(state.locale === "fa" ? "عنوان ستون" : "Column label")}" value="${escapeAttribute(label)}">
        <input data-p6-column-width="${escapeAttribute(column.field_id)}" aria-label="${escapeAttribute(state.locale === "fa" ? "عرض ستون" : "Column width")}" type="number" min="1" value="${column.width}">
        <select data-p6-column-alignment="${escapeAttribute(column.field_id)}" aria-label="${escapeAttribute(state.locale === "fa" ? "تراز ستون" : "Column alignment")}">
          ${(["start", "center", "end"] as const).map((alignment) => `<option value="${alignment}"${column.alignment === alignment ? " selected" : ""}>${escapeHtml(alignmentLabels[alignment])}</option>`).join("")}
        </select>
        <label><input data-p6-column-pinned="${escapeAttribute(column.field_id)}" type="checkbox"${column.pinned ? " checked" : ""}> ${state.locale === "fa" ? "ثابت" : "Pinned"}</label>
        <label><input data-p6-column-frozen="${escapeAttribute(column.field_id)}" type="checkbox"${column.frozen ? " checked" : ""}> ${state.locale === "fa" ? "منجمد" : "Frozen"}</label>
      </div>`;
    }).join("");
  return `<section class="cp-panel cp-p6-column-presentation" aria-label="${escapeAttribute(title)}"><h3>${escapeHtml(title)}</h3>${rows || '<div class="cp-empty">—</div>'}</section>`;
}

function getWorkspaceGridPresentation(state: WorkspaceState, options: WorkspaceRendererOptions): { sorts: readonly P6GridSort[]; groups: readonly P6GridGroup[]; filters: readonly P6GridFilter[] } | null {
  return options.p6GridPresentation ?? (state.p6FieldRegistry ? { sorts: state.p6GridSorts, groups: state.p6GridGroups, filters: state.p6GridFilters } : null);
}

function renderWorkspaceGridPresentation(state: WorkspaceState, options: WorkspaceRendererOptions): string {
  const locale = state.locale;
  const presentation = getWorkspaceGridPresentation(state, options);
  if (!presentation || !state.p6FieldRegistry) return "";
  const fields = state.p6FieldRegistry.fields;
  const sortRows = presentation.sorts.map((sort) => `<div data-p6-grid-sort-row data-order="${sort.order}"><select data-p6-grid-sort-field>${fields.map((field) => `<option value="${escapeAttribute(field.field_id)}"${field.field_id === sort.field_id ? " selected" : ""}>${escapeHtml(field.display_name)}</option>`).join("")}</select><select data-p6-grid-sort-direction><option value="ascending"${sort.direction === "ascending" ? " selected" : ""}>Ascending</option><option value="descending"${sort.direction === "descending" ? " selected" : ""}>Descending</option></select><button type="button" data-p6-grid-sort-remove aria-label="${locale === "fa" ? "حذف مرتب‌سازی" : "Remove sort"}">${locale === "fa" ? "حذف" : "Remove"}</button></div>`).join("");
  const groupRows = presentation.groups.map((group) => `<div data-p6-grid-group-row data-order="${group.order}"><select data-p6-grid-group-field>${fields.map((field) => `<option value="${escapeAttribute(field.field_id)}"${field.field_id === group.field_id ? " selected" : ""}>${escapeHtml(field.display_name)}</option>`).join("")}</select><button type="button" data-p6-grid-group-remove aria-label="${locale === "fa" ? "حذف گروه‌بندی" : "Remove group"}">${locale === "fa" ? "حذف" : "Remove"}</button></div>`).join("");
  const operatorLabels: Record<P6GridFilter["operator"], string> = locale === "fa"
    ? { "equals": "برابر", "not-equals": "نابرابر", "contains": "شامل", "starts-with": "شروع با", "ends-with": "پایان با", "greater-than": "بزرگ‌تر", "greater-than-or-equal": "بزرگ‌تر یا برابر", "less-than": "کوچک‌تر", "less-than-or-equal": "کوچک‌تر یا برابر", "is-empty": "خالی است", "is-not-empty": "خالی نیست" }
    : { "equals": "Equals", "not-equals": "Not equals", "contains": "Contains", "starts-with": "Starts with", "ends-with": "Ends with", "greater-than": "Greater than", "greater-than-or-equal": "Greater than or equal", "less-than": "Less than", "less-than-or-equal": "Less than or equal", "is-empty": "Is empty", "is-not-empty": "Is not empty" };
  const sortDirectionLabels = locale === "fa" ? { ascending: "صعودی", descending: "نزولی" } : { ascending: "Ascending", descending: "Descending" };
  const filterRows = presentation.filters.map((filter, index) => `<div data-p6-grid-filter-row data-order="${index}"><select data-p6-grid-filter-field>${fields.map((field) => `<option value="${escapeAttribute(field.field_id)}"${field.field_id === filter.field_id ? " selected" : ""}>${escapeHtml(field.display_name)}</option>`).join("")}</select><select data-p6-grid-filter-operator>${Object.entries(operatorLabels).map(([operator, label]) => `<option value="${escapeAttribute(operator)}"${operator === filter.operator ? " selected" : ""}>${escapeHtml(label)}</option>`).join("")}</select><input data-p6-grid-filter-value value="${escapeAttribute(String(filter.value ?? ""))}"><button type="button" data-p6-grid-filter-remove aria-label="${locale === "fa" ? "حذف فیلتر" : "Remove filter"}">${locale === "fa" ? "حذف" : "Remove"}</button></div>`).join("");
  const title = locale === "fa" ? "ارائه گرید" : "Grid Presentation";
  const sortsLabel = locale === "fa" ? "مرتب‌سازی" : "Sorts";
  const groupsLabel = locale === "fa" ? "گروه‌بندی" : "Groups";
  const filtersLabel = locale === "fa" ? "فیلترها" : "Filters";
  const ascending = sortDirectionLabels.ascending;
  const descending = sortDirectionLabels.descending;
  const localizedSortRows = sortRows.replaceAll("Ascending", ascending).replaceAll("Descending", descending);
  return `<section class="cp-panel cp-p6-grid-presentation" aria-label="${escapeAttribute(title)}"><h3>${escapeHtml(title)}</h3><div data-p6-grid-sort-count>${escapeHtml(sortsLabel)}: ${presentation.sorts.length}</div><div data-p6-grid-group-count>${escapeHtml(groupsLabel)}: ${presentation.groups.length}</div><div data-p6-grid-filter-count>${escapeHtml(filtersLabel)}: ${presentation.filters.length}</div>${localizedSortRows}${groupRows}${filterRows}</section>`;
}
function renderNavigationSurface(state: WorkspaceState): string {
  const item = getWorkspaceNavigation(state.activeMenu);
  const statusLabel = getWorkspaceNavigationStatusLabel(item, state.locale);
  const label = getWorkspaceNavigationLabel(item, state.locale);
  return `<section class="cp-panel cp-navigation-surface" aria-label="Current workspace surface">
    <div><strong>${escapeHtml(label)}</strong><span data-surface-status="${item.status}">${statusLabel}</span></div>
    <nav aria-label="${escapeAttribute(label)} submenu">
      ${item.submenus.map((submenu) => `<span class="cp-submenu-item">${escapeHtml(submenu[state.locale])}</span>`).join("")}
    </nav>
  </section>`;
}

function renderSmartGuide(
  guide: WorkspaceState["smartGuide"],
  label: string,
): string {
  if (!guide) return "";

  const findings = guide.findings.length
    ? guide.findings
        .slice(0, 5)
        .map((finding) =>
          `<article class="cp-control-finding is-${escapeAttribute(finding.severity)}">
            <div class="cp-control-finding-title">${escapeHtml(finding.title_key)}</div>
            <div class="cp-control-finding-detail">${escapeHtml(finding.detail_key)}</div>
          </article>`,
        )
        .join("")
    : '<div class="cp-empty">—</div>';

  const actions = guide.proposedActions.length
    ? guide.proposedActions
        .map(
          (action) =>
            `<article class="cp-field-card" data-ai-action-id="${escapeAttribute(action.actionId)}">
              <strong>${escapeHtml(action.titleKey)}</strong>
              <span>${escapeHtml(action.actionType)}</span>
              <span>${action.requiresApproval ? "Human approval required" : "No approval flag"}</span>
              <span>${action.sourceCount} source(s)</span>
            </article>`,
        )
        .join("")
    : '<div class="cp-empty">—</div>';

  return `
    <section class="cp-panel cp-smart-guide" aria-label="${escapeAttribute(label)}">
      <div class="cp-control-heading">
        <div>
          <h2>${escapeHtml(label)}</h2>
          <div class="cp-control-result">${escapeHtml(guide.summaryKey)}</div>
        </div>
        <span>${escapeHtml(guide.locale)} · ${escapeHtml(guide.module)}</span>
      </div>
      <div class="cp-field-grid">
        <div>
          <h3>Findings</h3>
          <div class="cp-field-list">${findings}</div>
        </div>
        <div>
          <h3>Proposed Actions</h3>
          <div class="cp-field-list">${actions}</div>
        </div>
        <div>
          <h3>Traceability</h3>
          <div class="cp-control-metrics">
            <div class="cp-control-metric"><span>Sources</span><strong>${guide.sourceCount}</strong></div>
            <div class="cp-control-metric"><span>Approval Required</span><strong>${guide.approvalRequiredCount}</strong></div>
          </div>
        </div>
      </div>
    </section>
  `;
}

function renderControlSummary(
  summary: WorkspaceState["controlSummary"],
  summaryLabel: string,
  metricsLabel: string,
  findingsLabel: string,
): string {
  if (!summary) return "";

  const metrics = Object.entries(summary.metrics)
    .map(([key, value]) => `<div class="cp-control-metric"><span>${escapeHtml(key)}</span><strong>${escapeHtml(String(value))}</strong></div>`)
    .join("");

  const findings = summary.findings.length
    ? summary.findings.map((finding) => `
        <article class="cp-control-finding is-${finding.severity}">
          <div class="cp-control-finding-title">${escapeHtml(finding.title_key)}</div>
          <div class="cp-control-finding-detail">${escapeHtml(finding.detail_key)}</div>
        </article>`).join("")
    : "<div class=\"cp-empty\">—</div>";

  return `
    <section class="cp-panel cp-control-summary" aria-label="${escapeAttribute(summaryLabel)}">
      <div class="cp-control-heading">
        <div>
          <h2>${escapeHtml(summaryLabel)}</h2>
          <div class="cp-control-result">${escapeHtml(summary.resultId)}</div>
        </div>
        <time datetime="${escapeAttribute(summary.generatedAt)}">${escapeHtml(summary.generatedAt)}</time>
      </div>
      <div class="cp-control-section">
        <h3>${escapeHtml(metricsLabel)}</h3>
        <div class="cp-control-metrics">${metrics || '<div class="cp-empty">—</div>'}</div>
      </div>
      <div class="cp-control-section">
        <h3>${escapeHtml(findingsLabel)}</h3>
        <div class="cp-control-findings">${findings}</div>
      </div>
    </section>
  `;
}

function renderSiteDailyLogs(
  logs: WorkspaceState["siteDailyLogs"],
  label: string,
): string {
  if (!logs.length) return "";

  return `
    <section class="cp-panel cp-site-logs" aria-label="${escapeAttribute(label)}">
      <div class="cp-control-heading">
        <div><h2>${escapeHtml(label)}</h2></div>
      </div>
      <div class="cp-site-log-list">
        ${logs.map((log) => `
          <article class="cp-site-log" data-log-id="${escapeAttribute(log.logId)}">
            <div class="cp-site-log-meta">
              <strong>${escapeHtml(log.locationKey)}</strong>
              <span>${escapeHtml(log.logDate)}</span>
              <span>${escapeHtml(log.status)}</span>
            </div>
            <div class="cp-site-log-entries">
              ${log.entries.map((entry) => `
                <div class="cp-site-log-entry">
                  <span>${escapeHtml(entry.category)}</span>
                  <span>${escapeHtml(entry.text_key)}</span>
                  ${entry.quantity !== null ? `<span>${escapeHtml(entry.quantity)} ${escapeHtml(entry.unit ?? "")}</span>` : ""}
                </div>`).join("")}
            </div>
          </article>`).join("")}
      </div>
    </section>
  `;
}

function renderFieldOperations(
  fieldIssues: WorkspaceState["fieldIssues"],
  timecards: WorkspaceState["timecards"],
  equipmentReports: WorkspaceState["equipmentReports"],
  t: WorkspaceLabels,
): string {
  if (!fieldIssues.length && !timecards.length && !equipmentReports.length) return "";

  const issues = fieldIssues.length
    ? fieldIssues.map((issue) => `
        <div class="cp-field-card" data-field-issue-id="${escapeAttribute(issue.issueId)}">
          <strong>${escapeHtml(issue.titleKey)}</strong>
          <span>${escapeHtml(issue.category)}</span>
          <span>${escapeHtml(issue.severity)} · ${escapeHtml(issue.status)}</span>
          <span>${escapeHtml(issue.locationKey ?? "—")}</span>
          <span>${issue.activityIds.length} activity link(s) · ${issue.evidenceCount} evidence</span>
        </div>`).join("")
    : '<div class="cp-empty">—</div>';

  const attendance = timecards.length
    ? timecards.map((card) => `
        <div class="cp-field-card" data-timecard-id="${escapeAttribute(card.timecardId)}">
          <strong>${escapeHtml(card.personId)}</strong>
          <span>${escapeHtml(card.workplaceKey)}</span>
          <span>${escapeHtml(card.attendanceStatus)}</span>
          <span>${escapeHtml(card.logDate)}</span>
        </div>`).join("")
    : '<div class="cp-empty">—</div>';

  const equipment = equipmentReports.length
    ? equipmentReports.map((report) => `
        <div class="cp-field-card" data-equipment-report-id="${escapeAttribute(report.reportId)}">
          <strong>${escapeHtml(report.equipmentId)}</strong>
          <span>${escapeHtml(report.workplaceKey)}</span>
          <span>${escapeHtml(report.status)}</span>
          ${report.breakdownCauseKey ? `<span>${escapeHtml(report.breakdownCauseKey)}</span>` : ""}
          ${report.meterHours !== null ? `<span>${escapeHtml(report.meterHours)} h</span>` : ""}
        </div>`).join("")
    : '<div class="cp-empty">—</div>';

  return `
    <section class="cp-panel cp-field-ops" aria-label="${escapeAttribute(t.issues + " / " + t.attendance + " / " + t.equipment)}">
      <div class="cp-field-grid">
        <div>
          <h2>${escapeHtml(t.issues)}</h2>
          <div class="cp-field-list">${issues}</div>
        </div>
        <div>
          <h2>${escapeHtml(t.attendance)}</h2>
          <div class="cp-field-list">${attendance}</div>
        </div>
        <div>
          <h2>${escapeHtml(t.equipment)}</h2>
          <div class="cp-field-list">${equipment}</div>
        </div>
      </div>
    </section>
  `;
}

function renderFieldAssurance(
  inspections: WorkspaceState["inspections"],
  qualityRecords: WorkspaceState["qualityRecords"],
  safetyObservations: WorkspaceState["safetyObservations"],
  punchItems: WorkspaceState["punchItems"],
  label: string,
): string {
  if (!inspections.length && !qualityRecords.length && !safetyObservations.length && !punchItems.length) return "";

  return `
    <section class="cp-panel cp-field-assurance" aria-label="${escapeAttribute(label)}">
      <h2>${escapeHtml(label)}</h2>
      <div class="cp-field-assurance-grid">
        <div>
          <h3>Inspections</h3>
          ${inspections.length ? inspections.map((item) => `
            <article class="cp-field-card">
              <strong>${escapeHtml(item.inspectionTypeKey)}</strong>
              <span>${escapeHtml(item.subjectId)}</span>
              <span>${escapeHtml(item.result)} · ${escapeHtml(item.status)}</span>
              <span>${item.checklist.length} checklist item(s)</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
        <div>
          <h3>Quality / NCR</h3>
          ${qualityRecords.length ? qualityRecords.map((item) => `
            <article class="cp-field-card is-${escapeAttribute(item.severity)}">
              <strong>${escapeHtml(item.titleKey)}</strong>
              <span>${escapeHtml(item.categoryKey)}</span>
              <span>${escapeHtml(item.severity)} · ${escapeHtml(item.status)}</span>
              <span>${item.evidenceCount} evidence · ${escapeHtml(item.correctiveActionKey ?? "—")}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
        <div>
          <h3>Safety</h3>
          ${safetyObservations.length ? safetyObservations.map((item) => `
            <article class="cp-field-card is-${escapeAttribute(item.severity)}">
              <strong>${escapeHtml(item.titleKey)}</strong>
              <span>${escapeHtml(item.categoryKey)}</span>
              <span>${escapeHtml(item.severity)} · ${escapeHtml(item.status)}</span>
              <span>${escapeHtml(item.locationKey ?? "—")}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
        <div>
          <h3>Punch / Closeout</h3>
          ${punchItems.length ? punchItems.map((item) => `
            <article class="cp-field-card">
              <strong>${escapeHtml(item.titleKey)}</strong>
              <span>${escapeHtml(item.priority)} · ${escapeHtml(item.status)}</span>
              <span>${escapeHtml(item.locationKey ?? "—")}</span>
              <span>Due: ${escapeHtml(item.dueDate ?? "—")}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
      </div>
    </section>
  `;
}

function renderProcurement(
  records: WorkspaceState["procurementRecords"],
  label: string,
): string {
  if (!records.length) return "";

  return `
    <section class="cp-panel cp-procurement" aria-label="${escapeAttribute(label)}">
      <div class="cp-control-heading">
        <div><h2>${escapeHtml(label)}</h2></div>
      </div>
      <div class="cp-field-list">
        ${records.map((record) => `
          <article class="cp-field-card" data-procurement-id="${escapeAttribute(record.id)}">
            <div class="cp-field-card-meta">
              <strong>${escapeHtml(record.id)}</strong>
              <span>${escapeHtml(record.type)}</span>
              <span>${escapeHtml(record.status)}</span>
            </div>
            ${record.supplierId ? `<div>Supplier: ${escapeHtml(record.supplierId)}</div>` : ""}
            ${record.referenceId ? `<div>Ref: ${escapeHtml(record.referenceId)}</div>` : ""}
            ${record.amount !== null ? `<div>Amount: ${escapeHtml(record.amount)} ${escapeHtml(record.currency ?? "")}</div>` : ""}
            <div>${record.itemCount} item(s) · ${record.activityIds.length} activity link(s) · ${record.evidenceCount} evidence</div>
            ${record.approvalRef ? `<div>Approval: ${escapeHtml(record.approvalRef)}</div>` : ""}
            ${record.date ? `<div>Date: ${escapeHtml(record.date)}</div>` : ""}
          </article>`).join("")}
      </div>
    </section>
  `;
}

function renderChangeClaimControl(
  notices: WorkspaceState["changeNotices"],
  changes: WorkspaceState["changeCases"],
  claims: WorkspaceState["claims"],
  impacts: WorkspaceState["changeClaimImpacts"],
  label: string,
  documents: WorkspaceState["documents"] = [],
): string {
  if (!notices.length && !changes.length && !claims.length && !impacts.length) return "";

  const documentSection = documents.length === 0
    ? ""
    : `<section class="control-room-section" data-section="documents">
      <h2>Documents</h2>
      <div class="control-room-cards">
        ${documents.map((document) => `<article class="control-room-card">
          <strong>${escapeHtml(document.documentId)}</strong>
          <span>${escapeHtml(document.title)}</span>
          <span>${escapeHtml(document.resourceType)} · ${escapeHtml(document.status)} · Rev ${document.revision}</span>
          <small>${document.linkedEntityRefs.length} linked reference(s) · ${document.hasStorageRef ? "stored" : "no storage"}</small>
        </article>`).join("")}
      </div>
    </section>`;

  const renderRefs = (values: readonly string[]) =>
    values.length ? values.map((value) => `<span class="cp-ref">${escapeHtml(value)}</span>`).join(" ") : "—";

  return `
    <section class="cp-panel cp-change-claim" aria-label="${escapeAttribute(label)}">
      <h2>${escapeHtml(label)}</h2>
      <div class="cp-change-claim-grid">
        <div>
          <h3>Notices</h3>
          ${notices.length ? notices.map((item) => `
            <article class="cp-field-card">
              <strong>${escapeHtml(item.titleKey)}</strong>
              <span>${escapeHtml(item.noticeType)} · ${escapeHtml(item.status)}</span>
              <span>Schedule: ${renderRefs(item.scheduleRefs)}</span>
              <span>Cost: ${renderRefs(item.costRefs)}</span>
              <span>${item.evidenceCount} evidence · Approval: ${item.approvalRequired ? "required" : "no"}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
        <div>
          <h3>Change Cases</h3>
          ${changes.length ? changes.map((item) => `
            <article class="cp-field-card">
              <strong>${escapeHtml(item.titleKey)}</strong>
              <span>${escapeHtml(item.changeType)} · ${escapeHtml(item.status)}</span>
              <span>Notice: ${escapeHtml(item.originatingNoticeId ?? "—")}</span>
              <span>Schedule: ${renderRefs(item.scheduleRefs)}</span>
              <span>Impact links: ${item.impactLinkIds.length} · Approval: ${item.approvalRequired ? "required" : "no"}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
        <div>
          <h3>Claims</h3>
          ${claims.length ? claims.map((item) => `
            <article class="cp-field-card">
              <strong>${escapeHtml(item.titleKey)}</strong>
              <span>${escapeHtml(item.claimType)} · ${escapeHtml(item.status)}</span>
              <span>Change: ${escapeHtml(item.changeId ?? "—")}</span>
              <span>Entitlement: ${escapeHtml(item.entitlementReference ?? "—")}</span>
              <span>Decision: ${escapeHtml(item.decisionReference ?? "—")}</span>
              <span>${item.evidenceCount} evidence</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
        <div>
          <h3>Impact Links</h3>
          ${impacts.length ? impacts.map((item) => `
            <article class="cp-field-card">
              <strong>${escapeHtml(item.recordType)} · ${escapeHtml(item.recordId)}</strong>
              <span>${escapeHtml(item.impactedDomain)} / ${escapeHtml(item.impactedEntityType)} / ${escapeHtml(item.impactedEntityId)}</span>
              <span>${escapeHtml(item.impactType)}</span>
              <span>Schedule: ${escapeHtml(item.scheduleReference ?? "—")}</span>
              <span>Cost: ${escapeHtml(item.costReference ?? "—")}</span>
              <span>Approval: ${item.requiresApplicationApproval ? "required" : "no"}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
      </div>
    </section>
  `;
}

function renderWorkspaceFormulaEditor(state: P6FormulaEditorState | null | undefined, locale: WorkspaceState["locale"]): string {
  if (!state) return "";
  return renderP6FormulaEditor(state, locale === "fa"
    ? {
        title: "ویرایشگر فرمول", expression: "عبارت", validating: "در حال اعتبارسنجی…",
        valid: "معتبر", invalid: "نامعتبر", dependencies: "وابستگی‌ها", resultType: "نوع نتیجه",
      }
    : {
        title: "Formula Editor", expression: "Expression", validating: "Validating…",
        valid: "Valid", invalid: "Invalid", dependencies: "Dependencies", resultType: "Result type",
      });
}

function renderWorkspaceReportPrintSelection(state: WorkspaceState, selection: { field_ids: readonly string[] } | null | undefined): string {
  if (!selection || !state.p6FieldRegistry || !state.p6Layout) return "";
  return renderP6ReportPrintFieldSelection(state.p6Layout, state.p6FieldRegistry.fields, selection, state.locale === "fa"
    ? { title: "فیلدهای گزارش / چاپ", selected: "انتخاب‌شده", visible: "قابل نمایش", reset: "بازنشانی به فیلدهای قابل نمایش" }
    : { title: "Report / Print Fields", selected: "Selected", visible: "Visible", reset: "Reset to visible" });
}

function renderP6FieldChooser(state: WorkspaceState): string {
  const registry = state.p6FieldRegistry;
  const layout = state.p6Layout;
  if (!registry || !layout) return "";
  const inLayout = new Set(layout.columns.map((column) => column.field_id));
  const available = registry.fields.filter((field) => !inLayout.has(field.field_id));
  return `<section class="cp-p6-field-chooser" aria-label="P6 Field Chooser">
    <div class="cp-p6-field-chooser-heading">
      <strong>Fields</strong><span>${escapeHtml(registry.registry_version)} · ${layout.scope} · R${layout.revision}</span>
    </div>
    <div class="cp-p6-field-list">
      ${layout.columns.filter((column) => column.visible).sort((a,b) => a.order-b.order).map((column, index, visibleColumns) => {
        const field = registry.fields.find((item) => item.field_id === column.field_id);
        if (!field) return "";
        const label = escapeHtml(column.label ?? field.display_name);
        const fieldId = escapeAttribute(field.field_id);
        const upDisabled = index === 0 ? " disabled" : "";
        const downDisabled = index === visibleColumns.length - 1 ? " disabled" : "";
        return `<div data-p6-field-row data-field-id="${fieldId}"><span>${label}</span><button type="button" data-p6-field-move-up="${fieldId}" title="Move up" aria-label="Move up"${upDisabled}>↑</button><button type="button" data-p6-field-move-down="${fieldId}" title="Move down" aria-label="Move down"${downDisabled}>↓</button><button type="button" data-p6-field-remove="${fieldId}" title="Remove">Remove</button></div>`;
      }).join("")}
      ${available.map((field) => `<button type="button" data-p6-field-add="${escapeAttribute(field.field_id)}" title="Add">${escapeHtml(field.display_name)}</button>`).join("")}
    </div>
  </section>`;
}

function renderActivityRow(activity: WorkspaceActivityRow, state: WorkspaceState): string {
  const selected = activity.id === state.selectedActivityId;
  return `<tr data-activity-id="${escapeAttribute(activity.id)}" tabindex="0" aria-selected="${selected ? "true" : "false"}" class="${selected ? "is-selected" : ""}">${state.columns.map((column) => `<td>${renderCell(column.id, activity)}</td>`).join("")}</tr>`;
}

function renderCell(columnId: string, activity: WorkspaceActivityRow): string {
  if (columnId === "activity_id") return escapeHtml(activity.id);
  if (columnId === "activity_code") return escapeHtml(activity.code);
  if (columnId === "activity_name") return escapeHtml(activity.name);
  return renderCellValue(columnId, activity.cells?.[columnId] ?? null);
}

function renderCellValue(columnId: string, value: WorkspaceCellValue): string {
  if (value === null || value === undefined) return "—";
  if (columnId === "progress" && typeof value === "number") return `${value}%`;
  if (typeof value === "boolean") return value ? "✓" : "—";
  return escapeHtml(String(value));
}

function renderGantt(activities: readonly WorkspaceActivityRow[], scale: ReturnType<typeof createGanttScale>, ariaLabel: string, noScheduleLabel: string, criticalLabel: string): string {
  if (!scale) return `<div class="cp-gantt-placeholder" role="img" aria-label="${escapeAttribute(ariaLabel)}">${noScheduleLabel}</div>`;
  const bars = activities.map((activity) => createGanttBarGeometry(activity, scale)).filter((bar): bar is NonNullable<typeof bar> => Boolean(bar));
  if (!bars.length) return `<div class="cp-gantt-placeholder" role="img" aria-label="${escapeAttribute(ariaLabel)}">${noScheduleLabel}</div>`;
  return `<div class="cp-gantt-board" role="img" aria-label="${escapeAttribute(ariaLabel)}">${bars.map((bar) => `<div class="cp-gantt-row" data-gantt-activity-id="${escapeAttribute(bar.activityId)}"><span class="cp-gantt-label">${escapeHtml(bar.activityId)}</span><div class="cp-gantt-track"><div class="cp-gantt-bar${bar.critical ? " is-critical" : ""}" style="left:${bar.leftPercent}%;width:${bar.widthPercent}%" title="${escapeAttribute(bar.activityId + " — " + bar.progressPercent + "%" + (bar.critical ? " — " + criticalLabel : ""))}"><span class="cp-gantt-progress" style="width:${bar.progressPercent}%"></span></div></div></div>`).join("")}</div>`;
}

function menuButton(key: WorkspaceState["activeMenu"], label: string, state: WorkspaceState): string {
  return `<button type="button" data-menu="${key}" aria-current="${key === state.activeMenu ? "page" : "false"}">${escapeHtml(label)}</button>`;
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]!);
}

function escapeAttribute(value: string): string { return escapeHtml(value); }
