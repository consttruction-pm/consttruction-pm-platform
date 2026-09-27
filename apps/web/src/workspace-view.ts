import type { WorkspaceActivityRow, WorkspaceCellValue, WorkspaceState } from "./workspace-model.js";
import { createGanttBarGeometry, createGanttScale } from "./workspace-gantt.js";

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
  container.querySelectorAll<HTMLElement>("[data-activity-id]").forEach((row) => {
    const select = () => { const id = row.dataset.activityId; if (id) options.onActivitySelect?.(id); };
    row.addEventListener("click", select);
    row.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); select(); } });
  });
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
