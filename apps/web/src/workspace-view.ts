import type { WorkspaceActivityRow, WorkspaceCellValue, WorkspaceColumn, WorkspaceState } from "./workspace-model.js";
import { createGanttBarGeometry, createGanttScale } from "./workspace-gantt.js";
import { getWorkspaceNavigation, getWorkspaceNavigationLabel, getWorkspaceNavigationStatusLabel } from "./workspace-navigation.js";

const labels = {
  en: {
    project: "Project", schedule: "Schedule", progress: "Progress", resources: "Resources", cost: "Cost", documents: "Documents", procurement: "Procurement", reports: "Reports", control: "Control", settings: "Settings", mainMenu: "Main Menu", currentSurface: "Current workspace surface", submenu: "submenu", formulaColumn: "formula column", fieldChooser: "Field Chooser", fields: "Fields", add: "Add", remove: "Remove", moveUp: "Move up", moveDown: "Move down", narrower: "Narrower", wider: "Wider", alignStart: "Align left", alignCenter: "Align center", alignEnd: "Align right", pin: "Pin", unpin: "Unpin", freeze: "Freeze", unfreeze: "Unfreeze", hide: "Hide", show: "Show", rename: "Rename", findings: "Findings", proposedActions: "Proposed Actions", traceability: "Traceability", sources: "Sources", approvalRequired: "Approval Required", humanApprovalRequired: "Human approval required", noApprovalFlag: "No approval flag", sourceUnit: "source(s)", activityLinkUnit: "activity link(s)", evidenceUnit: "evidence", inspections: "Inspections", qualityNcr: "Quality / NCR", safety: "Safety", punchCloseout: "Punch / Closeout", due: "Due", supplier: "Supplier", reference: "Ref", amount: "Amount", itemUnit: "item(s)", linkedReferenceUnit: "linked reference(s)", stored: "stored", noStorage: "no storage", approval: "Approval", date: "Date", notices: "Notices", changeCases: "Change Cases", claims: "Claims", impactLinks: "Impact Links", scheduleLabel: "Schedule", costLabel: "Cost", noticeLabel: "Notice", changeLabel: "Change", entitlement: "Entitlement", decision: "Decision", impactLinkLabel: "Impact links",
    wbs: "Project / WBS", activities: "Activity Grid", gantt: "Gantt Chart", details: "Details", issues: "Field Issues", assurance: "Field Assurance", noActivities: "No activities loaded", noSchedule: "No scheduled activities", revision: "Revision", critical: "Critical", smartGuide: "Smart Guide", controlSummary: "Control Summary", metrics: "Metrics", commercial: "Changes & Claims", siteLogs: "Daily Field Logs", attendance: "Attendance", equipment: "Equipment",
    
  },
  fa: {
    project: "پروژه", schedule: "زمان‌بندی", progress: "پیشرفت", resources: "منابع", cost: "هزینه", documents: "اسناد", procurement: "تدارکات", reports: "گزارش‌ها", control: "کنترل", settings: "تنظیمات", mainMenu: "منوی اصلی", currentSurface: "سطح فعلی محیط کار", submenu: "زیرمنو", formulaColumn: "ستون فرمول", fieldChooser: "انتخاب‌گر فیلد", fields: "فیلدها", add: "افزودن", remove: "حذف", moveUp: "جابجایی به بالا", moveDown: "جابجایی به پایین", narrower: "باریک‌تر", wider: "عریض‌تر", alignStart: "تراز چپ", alignCenter: "تراز وسط", alignEnd: "تراز راست", pin: "سنجاق کردن", unpin: "برداشتن سنجاق", freeze: "ثابت کردن", unfreeze: "لغو ثابت‌سازی", hide: "پنهان کردن", show: "نمایش", rename: "تغییر نام", findings: "یافته‌ها", proposedActions: "اقدامات پیشنهادی", traceability: "ردیابی", sources: "منابع", approvalRequired: "نیازمند تأیید", humanApprovalRequired: "نیازمند تأیید انسانی", noApprovalFlag: "بدون پرچم تأیید", sourceUnit: "منبع", activityLinkUnit: "پیوند فعالیت", evidenceUnit: "مستند", inspections: "بازرسی‌ها", qualityNcr: "کیفیت / NCR", safety: "ایمنی", punchCloseout: "پانچ / بستن موارد", due: "سررسید", supplier: "تأمین‌کننده", reference: "مرجع", amount: "مبلغ", itemUnit: "مورد", linkedReferenceUnit: "مرجع پیوندشده", stored: "ذخیره‌شده", noStorage: "بدون ذخیره‌سازی", approval: "تأیید", date: "تاریخ", notices: "اعلان‌ها", changeCases: "موارد تغییر", claims: "ادعاها", impactLinks: "پیوندهای اثر", scheduleLabel: "زمان‌بندی", costLabel: "هزینه", noticeLabel: "اعلان", changeLabel: "تغییر", entitlement: "استحقاق", decision: "تصمیم", impactLinkLabel: "پیوندهای اثر",
    wbs: "پروژه / WBS", activities: "جدول فعالیت‌ها", gantt: "گانت", details: "جزئیات", issues: "مسائل کارگاه", assurance: "کنترل کیفیت و ایمنی", noActivities: "فعالیتی بارگذاری نشده است", noSchedule: "فعالیت زمان‌بندی‌شده‌ای وجود ندارد", revision: "نسخه", critical: "بحرانی", smartGuide: "راهنمای هوشمند", controlSummary: "خلاصه کنترل", metrics: "شاخص‌ها", commercial: "تغییرات و ادعاها", siteLogs: "گزارش‌های روزانه کارگاه", attendance: "حضور و غیاب", equipment: "ماشین‌آلات",
  },
} as const;

type WorkspaceLabels = Record<keyof typeof labels.en, string>;

type WorkspaceRenderRecord = { state: WorkspaceState; options: WorkspaceRendererOptions };
const workspaceRenderRecords = new WeakMap<HTMLElement, WorkspaceRenderRecord>();
const workspaceEventDelegation = new WeakSet<HTMLElement>();
const workspaceWbsIdsCache = new WeakMap<readonly WorkspaceActivityRow[], readonly string[]>();
const workspaceStickyOffsetsCache = new WeakMap<readonly WorkspaceColumn[], ReadonlyMap<string, number>>();

function bindWorkspaceEvents(container: HTMLElement): void {
  if (typeof container.addEventListener !== "function" || workspaceEventDelegation.has(container)) return;
  workspaceEventDelegation.add(container);
  container.addEventListener("click", (event) => {
    const target = event.target && typeof (event.target as { closest?: unknown }).closest === "function" ? (event.target as HTMLElement).closest<HTMLElement>("[data-menu],[data-wbs-id],[data-p6-field-add],[data-p6-field-remove],[data-p6-field-visibility],[data-p6-field-width],[data-p6-field-alignment],[data-p6-field-pin],[data-p6-field-freeze],[data-p6-field-move],[data-gantt-activity-id],[data-activity-id]") : null;
    if (!target) return;
    const record = workspaceRenderRecords.get(container);
    if (!record) return;
    const { state, options } = record;
    if (target.dataset.menu) return void options.onMenuSelect?.(target.dataset.menu as WorkspaceState["activeMenu"]);
    if (target.dataset.wbsId) return void options.onWbsSelect?.(target.dataset.wbsId);
    if (target.dataset.p6FieldAdd) return void options.onP6FieldAdd?.(target.dataset.p6FieldAdd);
    if (target.dataset.p6FieldRemove) return void options.onP6FieldRemove?.(target.dataset.p6FieldRemove);
    if (target.dataset.p6FieldVisibility) return void options.onP6FieldVisibilityChange?.(target.dataset.p6FieldVisibility, target.dataset.p6FieldVisible === "true");
    if (target.dataset.p6FieldWidth) {
      const delta = target.dataset.p6FieldWidthDelta;
      if (delta !== "increase" && delta !== "decrease") return;
      const column = state.p6Layout?.columns.find((item) => item.field_id === target.dataset.p6FieldWidth);
      if (column) options.onP6FieldWidthChange?.(target.dataset.p6FieldWidth, Math.max(40, column.width + (delta === "increase" ? 20 : -20)));
      return;
    }
    if (target.dataset.p6FieldAlignment) {
      const alignment = target.dataset.p6FieldAlignmentValue;
      if (alignment === "start" || alignment === "center" || alignment === "end") options.onP6FieldPresentationChange?.(target.dataset.p6FieldAlignment, { alignment });
      return;
    }
    if (target.dataset.p6FieldPin) return void options.onP6FieldPresentationChange?.(target.dataset.p6FieldPin, { pinned: target.dataset.p6FieldPinned !== "true" });
    if (target.dataset.p6FieldFreeze) return void options.onP6FieldPresentationChange?.(target.dataset.p6FieldFreeze, { frozen: target.dataset.p6FieldFrozen !== "true" });
    if (target.dataset.p6FieldMove) {
      const direction = target.dataset.p6FieldDirection;
      if (direction !== "up" && direction !== "down") return;
      const fieldId = target.dataset.p6FieldMove;
      const visible = state.p6Layout?.columns.filter((column) => column.visible).sort((a, b) => a.order - b.order) ?? [];
      const ordered = state.p6Layout?.columns.slice().sort((a, b) => a.order - b.order).map((column) => column.field_id) ?? [];
      const index = ordered.indexOf(fieldId);
      const visibleIndex = visible.findIndex((column) => column.field_id === fieldId);
      const nextVisibleIndex = direction === "up" ? visibleIndex - 1 : visibleIndex + 1;
      if (visibleIndex < 0 || nextVisibleIndex < 0 || nextVisibleIndex >= visible.length || index < 0) return;
      const adjacentIndex = ordered.indexOf(visible[nextVisibleIndex].field_id);
      if (adjacentIndex < 0) return;
      [ordered[index], ordered[adjacentIndex]] = [ordered[adjacentIndex], ordered[index]];
      options.onP6FieldReorder?.(ordered);
      return;
    }
    if (target.dataset.ganttActivityId) return void options.onGanttActivitySelect?.(target.dataset.ganttActivityId);
    if (target.dataset.activityId) options.onActivitySelect?.(target.dataset.activityId);
  });
  container.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const target = event.target && typeof (event.target as { closest?: unknown }).closest === "function" ? (event.target as HTMLElement).closest<HTMLElement>("[data-gantt-activity-id],[data-activity-id]") : null;
    if (!target) return;
    event.preventDefault();
    const record = workspaceRenderRecords.get(container);
    if (!record) return;
    if (target.dataset.ganttActivityId) record.options.onGanttActivitySelect?.(target.dataset.ganttActivityId);
    else if (target.dataset.activityId) record.options.onActivitySelect?.(target.dataset.activityId);
  });
  container.addEventListener("change", (event) => {
    const target = event.target && typeof (event.target as { closest?: unknown }).closest === "function" ? (event.target as HTMLInputElement).closest<HTMLInputElement>("[data-p6-field-rename]") : null;
    if (!target) return;
    const fieldId = target.dataset.p6FieldRename;
    const label = target.value.trim();
    if (fieldId && label) workspaceRenderRecords.get(container)?.options.onP6FieldPresentationChange?.(fieldId, { label });
  });
}

function canIncrementallyUpdate(previous: WorkspaceState, next: WorkspaceState): boolean {
  return previous.context === next.context && previous.locale === next.locale && previous.direction === next.direction && previous.calendarMode === next.calendarMode && previous.visiblePanels === next.visiblePanels && previous.columns === next.columns && previous.activities === next.activities && previous.controlSummary === next.controlSummary && previous.smartGuide === next.smartGuide && previous.siteDailyLogs === next.siteDailyLogs && previous.timecards === next.timecards && previous.equipmentReports === next.equipmentReports && previous.fieldIssues === next.fieldIssues && previous.changeNotices === next.changeNotices && previous.changeCases === next.changeCases && previous.claims === next.claims && previous.changeClaimImpacts === next.changeClaimImpacts && previous.documents === next.documents && previous.procurementRecords === next.procurementRecords && previous.inspections === next.inspections && previous.qualityRecords === next.qualityRecords && previous.safetyObservations === next.safetyObservations && previous.punchItems === next.punchItems && previous.p6FieldRegistry === next.p6FieldRegistry && previous.p6Layout === next.p6Layout;
}

function applyIncrementalWorkspaceUpdate(container: HTMLElement, previous: WorkspaceState, next: WorkspaceState): boolean {
  if (!canIncrementallyUpdate(previous, next)) return false;
  const menuChanged = previous.activeMenu !== next.activeMenu;
  const wbsChanged = previous.selectedWbsId !== next.selectedWbsId;
  const activityChanged = previous.selectedActivityId !== next.selectedActivityId;
  if (Number(menuChanged) + Number(wbsChanged) + Number(activityChanged) !== 1) return false;
  if (menuChanged) {
    container.querySelectorAll<HTMLElement>("[data-menu]").forEach((button) => button.setAttribute("aria-current", button.dataset.menu === next.activeMenu ? "page" : "false"));
    const navigation = container.querySelector<HTMLElement>(".cp-navigation-surface");
    if (navigation) navigation.outerHTML = renderNavigationSurface(next);
    return true;
  }
  if (wbsChanged) {
    container.querySelectorAll<HTMLElement>("[data-wbs-id]").forEach((button) => {
      const selected = button.dataset.wbsId === next.selectedWbsId;
      button.classList.toggle("is-selected", selected);
      button.setAttribute("aria-current", selected ? "true" : "false");
    });
    return true;
  }
  container.querySelectorAll<HTMLElement>("[data-activity-id]").forEach((row) => {
    const selected = row.dataset.activityId === next.selectedActivityId;
    row.classList.toggle("is-selected", selected);
    row.setAttribute("aria-selected", selected ? "true" : "false");
  });
  container.querySelectorAll<HTMLElement>("[data-gantt-activity-id]").forEach((row) => {
    const selected = row.dataset.ganttActivityId === next.selectedActivityId;
    row.classList.toggle("is-selected", selected);
    row.setAttribute("aria-pressed", selected ? "true" : "false");
  });
  const details = container.querySelector<HTMLElement>("#cp-details");
  if (details) {
    const t = labels[next.locale];
    details.innerHTML = `<h2 id="cp-details-heading">${escapeHtml(t.details)}</h2>${next.selectedActivityId ? `<div class="cp-detail-selected">${escapeHtml(next.selectedActivityId)}</div>` : `<div class="cp-empty">—</div>`}`;
  }
  return true;
}


export type WorkspaceRendererOptions = {
  onMenuSelect?: (menu: WorkspaceState["activeMenu"]) => void;
  onWbsSelect?: (wbsId: string) => void;
  onActivitySelect?: (activityId: string) => void;
  onGanttActivitySelect?: (activityId: string) => void;
  onP6FieldAdd?: (fieldId: string) => void;
  onP6FieldRemove?: (fieldId: string) => void;
  onP6FieldReorder?: (orderedFieldIds: readonly string[]) => void;
  onP6FieldWidthChange?: (fieldId: string, width: number) => void;
  onP6FieldVisibilityChange?: (fieldId: string, visible: boolean) => void;
  onP6FieldPresentationChange?: (fieldId: string, patch: { label?: string; alignment?: "start" | "center" | "end"; pinned?: boolean; frozen?: boolean }) => void;
};

export function renderMainWorkspace(container: HTMLElement, state: WorkspaceState, options: WorkspaceRendererOptions = {}): void {
  const previous = workspaceRenderRecords.get(container);
  if (previous && applyIncrementalWorkspaceUpdate(container, previous.state, state)) {
    workspaceRenderRecords.set(container, { state, options });
    return;
  }
  const t = labels[state.locale];
  const cachedWbsIds = workspaceWbsIdsCache.get(state.activities);
  const wbsIds = cachedWbsIds ?? [...new Set(state.activities.map((activity) => activity.wbsId))];
  if (!cachedWbsIds) workspaceWbsIdsCache.set(state.activities, wbsIds);
  const scale = createGanttScale(state.activities);
  let stickyOffsets = workspaceStickyOffsetsCache.get(state.columns);
  if (!stickyOffsets) {
    const nextStickyOffsets = new Map<string, number>();
    let stickyOffset = 0;
    for (const column of state.columns) {
      if (column.pinned || column.frozen) {
        nextStickyOffsets.set(column.id, stickyOffset);
        stickyOffset += column.width;
      }
    }
    stickyOffsets = nextStickyOffsets;
    workspaceStickyOffsetsCache.set(state.columns, stickyOffsets);
  }

  container.innerHTML = `
    <section class="cp-workspace" dir="${state.direction}" data-project="${escapeAttribute(state.context.project_id)}">
      <header class="cp-header">
        <div class="cp-brand">Construction PM</div>
        <div class="cp-project">${escapeHtml(state.context.project_id)}</div>
        <div class="cp-revision">${escapeHtml(t.revision)} R${state.context.revision}</div>
      </header>
      <nav class="cp-menu" aria-label="${escapeAttribute(t.mainMenu)}">
        ${menuButton("project", t.project, state)} ${menuButton("schedule", t.schedule, state)} ${menuButton("progress", t.progress, state)} ${menuButton("resources", t.resources, state)} ${menuButton("cost", t.cost, state)} ${menuButton("documents", t.documents, state)} ${menuButton("reports", t.reports, state)} ${menuButton("control", t.control, state)} ${menuButton("settings", t.settings, state)}
      </nav>
      ${renderNavigationSurface(state)}
      <main class="cp-main">
        ${renderSmartGuide(state.smartGuide, t.smartGuide, t)}
        ${renderControlSummary(state.controlSummary, t.controlSummary, t.metrics, t.findings)}
        ${renderSiteDailyLogs(state.siteDailyLogs, t.siteLogs)}
        ${renderFieldOperations(state.fieldIssues, state.timecards, state.equipmentReports, t)}
        ${renderFieldAssurance(state.inspections, state.qualityRecords, state.safetyObservations, state.punchItems, t.assurance, t)}
        ${renderChangeClaimControl(state.changeNotices, state.changeCases, state.claims, state.changeClaimImpacts, t.commercial, [], t)}
        ${renderProcurement(state.procurementRecords, t.procurement, t)}
        <aside id="cp-project-wbs" class="cp-panel cp-wbs" ${!state.visiblePanels.project_wbs ? "hidden" : ""} aria-label="${escapeAttribute(t.wbs)}">
          <h2>${t.wbs}</h2>
          ${wbsIds.length ? wbsIds.map((wbsId) => `<button type="button" class="cp-wbs-node${state.selectedWbsId === wbsId ? " is-selected" : ""}" data-wbs-id="${escapeAttribute(wbsId)}" aria-current="${state.selectedWbsId === wbsId ? "true" : "false"}">${escapeHtml(wbsId)}</button>`).join("") : `<div class="cp-empty">${t.noActivities}</div>`}
        </aside>
        <section class="cp-center">
          <section id="cp-activity-grid" class="cp-panel cp-grid" ${!state.visiblePanels.activity_grid ? "hidden" : ""}>
            <h2>${t.activities}</h2>
            ${renderP6FieldChooser(state)}
            <div class="cp-table-wrap">
              <table role="grid" aria-label="${escapeAttribute(t.activities)}" aria-multiselectable="false">
                <thead><tr role="row">${state.columns.map((column) => `<th role="columnheader" scope="col" data-column-type="${column.dataType}" data-column-alignment="${column.alignment}" data-column-pinned="${column.pinned}" data-column-frozen="${column.frozen}" class="cp-p6-column${column.pinned ? " is-pinned" : ""}${column.frozen ? " is-frozen" : ""}" style="width:${column.width}px;text-align:${column.alignment}${stickyOffsets.has(column.id) ? `;--cp-p6-sticky-offset:${stickyOffsets.get(column.id)}px` : ""}">${escapeHtml(column.label)}${column.formula ? `<span aria-label="${escapeAttribute(t.formulaColumn)}">ƒx</span>` : ""}</th>`).join("")}</tr></thead>
                <tbody>${state.activities.length ? state.activities.map((activity) => renderActivityRow(activity, state, stickyOffsets)).join("") : `<tr role="row"><td role="gridcell" colspan="${Math.max(1, state.columns.length)}">${t.noActivities}</td></tr>`}</tbody>
              </table>
            </div>
          </section>
          <section id="cp-gantt" class="cp-panel cp-gantt" ${!state.visiblePanels.gantt ? "hidden" : ""}><h2>${t.gantt}</h2>${renderGantt(state.activities, scale, t.gantt, t.noSchedule, t.critical, state.selectedActivityId)}</section>
        </section>
        <aside id="cp-details" class="cp-panel cp-details" ${!state.visiblePanels.details ? "hidden" : ""} aria-labelledby="cp-details-heading"><h2 id="cp-details-heading">${t.details}</h2>${state.selectedActivityId ? `<div class="cp-detail-selected">${escapeHtml(state.selectedActivityId)}</div>` : `<div class="cp-empty">—</div>`}</aside>
      </main>
    </section>
  `;

  workspaceRenderRecords.set(container, { state, options });
  if (!workspaceEventDelegation.has(container)) bindWorkspaceEvents(container);
}

function renderNavigationSurface(state: WorkspaceState): string {
  const t = labels[state.locale];
  const item = getWorkspaceNavigation(state.activeMenu);
  const statusLabel = getWorkspaceNavigationStatusLabel(item, state.locale);
  const label = getWorkspaceNavigationLabel(item, state.locale);
  const links = navigationAnchors(item.key);

  return `<section class="cp-panel cp-navigation-surface" aria-label="${escapeAttribute(t.currentSurface)}">
    <div><strong>${escapeHtml(label)}</strong><span data-surface-status="${item.status}">${statusLabel}</span></div>
    <nav aria-label="${escapeAttribute(label + " " + t.submenu)}">
      ${item.submenus.map((submenu, index) => {
        const anchor = links[index];
        return anchor
          ? `<a class="cp-submenu-item" href="${escapeAttribute(anchor)}">${escapeHtml(submenu[state.locale])}</a>`
          : `<span class="cp-submenu-item" aria-disabled="true" data-submenu-status="preview">${escapeHtml(submenu[state.locale])}</span>`;
      }).join("")}
    </nav>
  </section>`;
}

function navigationAnchors(menu: WorkspaceState["activeMenu"]): readonly (string | null)[] {
  switch (menu) {
    case "project":
      return ["#cp-project-wbs", "#cp-details"];
    case "schedule":
      return ["#cp-activity-grid", "#cp-gantt"];
    default:
      return [];
  }
}

function renderSmartGuide(
  guide: WorkspaceState["smartGuide"],
  label: string,
  t: WorkspaceLabels,
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
              <span>${action.requiresApproval ? t.humanApprovalRequired : t.noApprovalFlag}</span>
              <span>${action.sourceCount} ${escapeHtml(t.sourceUnit)}</span>
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
          <h3>${escapeHtml(t.findings)}</h3>
          <div class="cp-field-list">${findings}</div>
        </div>
        <div>
          <h3>${escapeHtml(t.proposedActions)}</h3>
          <div class="cp-field-list">${actions}</div>
        </div>
        <div>
          <h3>${escapeHtml(t.traceability)}</h3>
          <div class="cp-control-metrics">
            <div class="cp-control-metric"><span>${escapeHtml(t.sources)}</span><strong>${guide.sourceCount}</strong></div>
            <div class="cp-control-metric"><span>${escapeHtml(t.approvalRequired)}</span><strong>${guide.approvalRequiredCount}</strong></div>
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
          <span>${issue.activityIds.length} ${escapeHtml(t.activityLinkUnit)} · ${issue.evidenceCount} ${escapeHtml(t.evidenceUnit)}</span>
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
  t: WorkspaceLabels,
): string {
  if (!inspections.length && !qualityRecords.length && !safetyObservations.length && !punchItems.length) return "";

  return `
    <section class="cp-panel cp-field-assurance" aria-label="${escapeAttribute(label)}">
      <h2>${escapeHtml(label)}</h2>
      <div class="cp-field-assurance-grid">
        <div>
          <h3>${escapeHtml(t.inspections)}</h3>
          ${inspections.length ? inspections.map((item) => `
            <article class="cp-field-card">
              <strong>${escapeHtml(item.inspectionTypeKey)}</strong>
              <span>${escapeHtml(item.subjectId)}</span>
              <span>${escapeHtml(item.result)} · ${escapeHtml(item.status)}</span>
              <span>${item.checklist.length} ${escapeHtml(t.itemUnit)}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
        <div>
          <h3>${escapeHtml(t.qualityNcr)}</h3>
          ${qualityRecords.length ? qualityRecords.map((item) => `
            <article class="cp-field-card is-${escapeAttribute(item.severity)}">
              <strong>${escapeHtml(item.titleKey)}</strong>
              <span>${escapeHtml(item.categoryKey)}</span>
              <span>${escapeHtml(item.severity)} · ${escapeHtml(item.status)}</span>
              <span>${item.evidenceCount} ${escapeHtml(t.evidenceUnit)} · ${escapeHtml(item.correctiveActionKey ?? "—")}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
        <div>
          <h3>${escapeHtml(t.safety)}</h3>
          ${safetyObservations.length ? safetyObservations.map((item) => `
            <article class="cp-field-card is-${escapeAttribute(item.severity)}">
              <strong>${escapeHtml(item.titleKey)}</strong>
              <span>${escapeHtml(item.categoryKey)}</span>
              <span>${escapeHtml(item.severity)} · ${escapeHtml(item.status)}</span>
              <span>${escapeHtml(item.locationKey ?? "—")}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
        <div>
          <h3>${escapeHtml(t.punchCloseout)}</h3>
          ${punchItems.length ? punchItems.map((item) => `
            <article class="cp-field-card">
              <strong>${escapeHtml(item.titleKey)}</strong>
              <span>${escapeHtml(item.priority)} · ${escapeHtml(item.status)}</span>
              <span>${escapeHtml(item.locationKey ?? "—")}</span>
              <span>${escapeHtml(t.due)}: ${escapeHtml(item.dueDate ?? "—")}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
      </div>
    </section>
  `;
}

function renderProcurement(
  records: WorkspaceState["procurementRecords"],
  label: string,
  t: WorkspaceLabels,
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
            ${record.supplierId ? `<div>${escapeHtml(t.supplier)}: ${escapeHtml(record.supplierId)}</div>` : ""}
            ${record.referenceId ? `<div>${escapeHtml(t.reference)}: ${escapeHtml(record.referenceId)}</div>` : ""}
            ${record.amount !== null ? `<div>${escapeHtml(t.amount)}: ${escapeHtml(record.amount)} ${escapeHtml(record.currency ?? "")}</div>` : ""}
            <div>${record.itemCount} ${escapeHtml(t.itemUnit)} · ${record.activityIds.length} ${escapeHtml(t.activityLinkUnit)} · ${record.evidenceCount} ${escapeHtml(t.evidenceUnit)}</div>
            ${record.approvalRef ? `<div>${escapeHtml(t.approval)}: ${escapeHtml(record.approvalRef)}</div>` : ""}
            ${record.date ? `<div>${escapeHtml(t.date)}: ${escapeHtml(record.date)}</div>` : ""}
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
  t: WorkspaceLabels,
): string {
  if (!notices.length && !changes.length && !claims.length && !impacts.length) return "";

  const documentSection = documents.length === 0
    ? ""
    : `<section class="control-room-section" data-section="documents">
      <h2>${escapeHtml(t.documents)}</h2>
      <div class="control-room-cards">
        ${documents.map((document) => `<article class="control-room-card">
          <strong>${escapeHtml(document.documentId)}</strong>
          <span>${escapeHtml(document.title)}</span>
          <span>${escapeHtml(document.resourceType)} · ${escapeHtml(document.status)} · Rev ${document.revision}</span>
          <small>${document.linkedEntityRefs.length} ${escapeHtml(t.linkedReferenceUnit)} · ${document.hasStorageRef ? t.stored : t.noStorage}</small>
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
          <h3>${escapeHtml(t.notices)}</h3>
          ${notices.length ? notices.map((item) => `
            <article class="cp-field-card">
              <strong>${escapeHtml(item.titleKey)}</strong>
              <span>${escapeHtml(item.noticeType)} · ${escapeHtml(item.status)}</span>
              <span>${escapeHtml(t.scheduleLabel)}: ${renderRefs(item.scheduleRefs)}</span>
              <span>${escapeHtml(t.costLabel)}: ${renderRefs(item.costRefs)}</span>
              <span>${item.evidenceCount} ${escapeHtml(t.evidenceUnit)} · ${escapeHtml(t.approval)}: ${item.approvalRequired ? escapeHtml(t.approvalRequired) : escapeHtml(t.noApprovalFlag)}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
        <div>
          <h3>${escapeHtml(t.changeCases)}</h3>
          ${changes.length ? changes.map((item) => `
            <article class="cp-field-card">
              <strong>${escapeHtml(item.titleKey)}</strong>
              <span>${escapeHtml(item.changeType)} · ${escapeHtml(item.status)}</span>
              <span>${escapeHtml(t.noticeLabel)}: ${escapeHtml(item.originatingNoticeId ?? "—")}</span>
              <span>${escapeHtml(t.scheduleLabel)}: ${renderRefs(item.scheduleRefs)}</span>
              <span>${escapeHtml(t.impactLinkLabel)}: ${item.impactLinkIds.length} · ${escapeHtml(t.approval)}: ${item.approvalRequired ? escapeHtml(t.approvalRequired) : escapeHtml(t.noApprovalFlag)}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
        <div>
          <h3>${escapeHtml(t.claims)}</h3>
          ${claims.length ? claims.map((item) => `
            <article class="cp-field-card">
              <strong>${escapeHtml(item.titleKey)}</strong>
              <span>${escapeHtml(item.claimType)} · ${escapeHtml(item.status)}</span>
              <span>${escapeHtml(t.changeLabel)}: ${escapeHtml(item.changeId ?? "—")}</span>
              <span>${escapeHtml(t.entitlement)}: ${escapeHtml(item.entitlementReference ?? "—")}</span>
              <span>${escapeHtml(t.decision)}: ${escapeHtml(item.decisionReference ?? "—")}</span>
              <span>${item.evidenceCount} ${escapeHtml(t.evidenceUnit)}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
        <div>
          <h3>${escapeHtml(t.impactLinks)}</h3>
          ${impacts.length ? impacts.map((item) => `
            <article class="cp-field-card">
              <strong>${escapeHtml(item.recordType)} · ${escapeHtml(item.recordId)}</strong>
              <span>${escapeHtml(item.impactedDomain)} / ${escapeHtml(item.impactedEntityType)} / ${escapeHtml(item.impactedEntityId)}</span>
              <span>${escapeHtml(item.impactType)}</span>
              <span>${escapeHtml(t.scheduleLabel)}: ${escapeHtml(item.scheduleReference ?? "—")}</span>
              <span>${escapeHtml(t.costLabel)}: ${escapeHtml(item.costReference ?? "—")}</span>
              <span>${escapeHtml(t.approval)}: ${item.requiresApplicationApproval ? escapeHtml(t.approvalRequired) : escapeHtml(t.noApprovalFlag)}</span>
            </article>`).join("") : '<div class="cp-empty">—</div>'}
        </div>
      </div>
    </section>
  `;
}

function renderP6FieldChooser(state: WorkspaceState): string {
  const t = labels[state.locale];
  const registry = state.p6FieldRegistry;
  const layout = state.p6Layout;
  if (!registry || !layout) return "";
  const inLayout = new Set(layout.columns.map((column) => column.field_id));
  const available = registry.fields.filter((field) => !inLayout.has(field.field_id));
  const orderedColumns = layout.columns.slice().sort((a, b) => a.order - b.order);
  const visibleColumns = orderedColumns.filter((column) => column.visible);
  const hiddenColumns = orderedColumns.filter((column) => !column.visible);
  return `<section class="cp-p6-field-chooser" aria-label="${escapeAttribute(t.fieldChooser)}">
    <div class="cp-p6-field-chooser-heading">
      <strong>${escapeHtml(t.fields)}</strong><span>Field Registry · ${layout.scope} · R${layout.revision}</span>
    </div>
    <div class="cp-p6-field-list">
      ${visibleColumns.map((column, index) => {
        const field = registry.fields.find((item) => item.field_id === column.field_id);
        if (!field) return "";
        return `<span class="cp-p6-field-item"><input type="text" data-p6-field-rename="${escapeAttribute(field.field_id)}" value="${escapeAttribute(column.label ?? field.display_name)}" aria-label="${escapeAttribute(t.rename)}" title="${escapeAttribute(t.rename)}"><button type="button" data-p6-field-remove="${escapeAttribute(field.field_id)}" title="${escapeAttribute(t.remove + ": " + (column.label ?? field.display_name))}" aria-label="${escapeAttribute(t.remove + ": " + (column.label ?? field.display_name))}">${escapeHtml(t.remove)}</button><button type="button" data-p6-field-visibility="${escapeAttribute(field.field_id)}" title="${escapeAttribute(t.hide + ": " + (column.label ?? field.display_name))}" aria-label="${escapeAttribute(t.hide + ": " + (column.label ?? field.display_name))}">◌</button><button type="button" data-p6-field-move="${escapeAttribute(field.field_id)}" data-p6-field-direction="up" title="${escapeAttribute(t.moveUp)}" aria-label="${escapeAttribute(t.moveUp)}" ${index === 0 ? "disabled" : ""}>↑</button><button type="button" data-p6-field-move="${escapeAttribute(field.field_id)}" data-p6-field-direction="down" title="${escapeAttribute(t.moveDown)}" aria-label="${escapeAttribute(t.moveDown)}" ${index === visibleColumns.length - 1 ? "disabled" : ""}>↓</button><button type="button" data-p6-field-width="${escapeAttribute(field.field_id)}" data-p6-field-width-delta="decrease" title="${escapeAttribute(t.narrower)}" aria-label="${escapeAttribute(t.narrower)}">−</button><button type="button" data-p6-field-width="${escapeAttribute(field.field_id)}" data-p6-field-width-delta="increase" title="${escapeAttribute(t.wider)}" aria-label="${escapeAttribute(t.wider)}">+</button><button type="button" data-p6-field-alignment="${escapeAttribute(field.field_id)}" data-p6-field-alignment-value="start" title="${escapeAttribute(t.alignStart)}" aria-label="${escapeAttribute(t.alignStart)}" aria-pressed="${column.alignment === "start" ? "true" : "false"}">L</button><button type="button" data-p6-field-alignment="${escapeAttribute(field.field_id)}" data-p6-field-alignment-value="center" title="${escapeAttribute(t.alignCenter)}" aria-label="${escapeAttribute(t.alignCenter)}" aria-pressed="${column.alignment === "center" ? "true" : "false"}">C</button><button type="button" data-p6-field-alignment="${escapeAttribute(field.field_id)}" data-p6-field-alignment-value="end" title="${escapeAttribute(t.alignEnd)}" aria-label="${escapeAttribute(t.alignEnd)}" aria-pressed="${column.alignment === "end" ? "true" : "false"}">R</button><button type="button" data-p6-field-pin="${escapeAttribute(field.field_id)}" data-p6-field-pinned="${column.pinned ? "true" : "false"}" title="${escapeAttribute(column.pinned ? t.unpin : t.pin)}" aria-label="${escapeAttribute(column.pinned ? t.unpin : t.pin)}" aria-pressed="${column.pinned ? "true" : "false"}">📌</button><button type="button" data-p6-field-freeze="${escapeAttribute(field.field_id)}" data-p6-field-frozen="${column.frozen ? "true" : "false"}" title="${escapeAttribute(column.frozen ? t.unfreeze : t.freeze)}" aria-label="${escapeAttribute(column.frozen ? t.unfreeze : t.freeze)}" aria-pressed="${column.frozen ? "true" : "false"}">❄</button></span>`;
      }).join("")}
      ${hiddenColumns.map((column) => {
        const field = registry.fields.find((item) => item.field_id === column.field_id);
        if (!field) return "";
        return `<span class="cp-p6-field-item is-hidden"><button type="button" data-p6-field-visibility="${escapeAttribute(field.field_id)}" data-p6-field-visible="true" title="${escapeAttribute(t.show + ": " + (column.label ?? field.display_name))}" aria-label="${escapeAttribute(t.show + ": " + (column.label ?? field.display_name))}">${escapeHtml(column.label ?? field.display_name)}</button><button type="button" data-p6-field-remove="${escapeAttribute(field.field_id)}" title="${escapeAttribute(t.remove + ": " + (column.label ?? field.display_name))}" aria-label="${escapeAttribute(t.remove + ": " + (column.label ?? field.display_name))}">${escapeHtml(t.remove)}</button></span>`;
      }).join("")}
      ${available.map((field) => `<button type="button" data-p6-field-add="${escapeAttribute(field.field_id)}" title="${escapeAttribute(t.add)}">${escapeHtml(field.display_name)}</button>`).join("")}
    </div>
  </section>`;
}

function renderActivityRow(activity: WorkspaceActivityRow, state: WorkspaceState, stickyOffsets: ReadonlyMap<string, number>): string {
  const selected = activity.id === state.selectedActivityId;
  return `<tr role="row" data-activity-id="${escapeAttribute(activity.id)}" tabindex="0" aria-selected="${selected ? "true" : "false"}" aria-label="${escapeAttribute(activity.id)}" class="${selected ? "is-selected" : ""}">${state.columns.map((column) => `<td role="gridcell" data-column-alignment="${column.alignment}" data-column-pinned="${column.pinned}" data-column-frozen="${column.frozen}" class="cp-p6-column${column.pinned ? " is-pinned" : ""}${column.frozen ? " is-frozen" : ""}" style="text-align:${column.alignment};width:${column.width}px${stickyOffsets.has(column.id) ? `;--cp-p6-sticky-offset:${stickyOffsets.get(column.id)}px` : ""}">${renderCell(column.id, activity)}</td>`).join("")}</tr>`;
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

function renderGantt(activities: readonly WorkspaceActivityRow[], scale: ReturnType<typeof createGanttScale>, ariaLabel: string, noScheduleLabel: string, criticalLabel: string, selectedActivityId: string | null): string {
  if (!scale) return `<div class="cp-gantt-placeholder" role="img" aria-label="${escapeAttribute(ariaLabel)}">${noScheduleLabel}</div>`;
  const bars = activities.map((activity) => createGanttBarGeometry(activity, scale)).filter((bar): bar is NonNullable<typeof bar> => Boolean(bar));
  if (!bars.length) return `<div class="cp-gantt-placeholder" role="img" aria-label="${escapeAttribute(ariaLabel)}">${noScheduleLabel}</div>`;
  return `<div class="cp-gantt-board" role="region" aria-label="${escapeAttribute(ariaLabel)}">${bars.map((bar) => `<div class="cp-gantt-row${bar.activityId === selectedActivityId ? " is-selected" : ""}" role="button" data-gantt-activity-id="${escapeAttribute(bar.activityId)}" tabindex="0" aria-pressed="${bar.activityId === selectedActivityId ? "true" : "false"}" aria-label="${escapeAttribute(bar.activityId)}"><span class="cp-gantt-label">${escapeHtml(bar.activityId)}</span><div class="cp-gantt-track"><div class="cp-gantt-bar${bar.critical ? " is-critical" : ""}" style="left:${bar.leftPercent}%;width:${bar.widthPercent}%" title="${escapeAttribute(bar.activityId + " — " + bar.progressPercent + "%" + (bar.critical ? " — " + criticalLabel : ""))}"><span class="cp-gantt-progress" style="width:${bar.progressPercent}%"></span></div></div></div>`).join("")}</div>`;
}

function menuButton(key: WorkspaceState["activeMenu"], label: string, state: WorkspaceState): string {
  return `<button type="button" data-menu="${key}" aria-current="${key === state.activeMenu ? "page" : "false"}">${escapeHtml(label)}</button>`;
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]!);
}

function escapeAttribute(value: string): string { return escapeHtml(value); }
