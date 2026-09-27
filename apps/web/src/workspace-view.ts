import type { WorkspaceActivityRow, WorkspaceCellValue, WorkspaceState } from "./workspace-model.js";
import { createGanttBarGeometry, createGanttScale } from "./workspace-gantt.js";

const labels = {
  en: {
    project: "Project", schedule: "Schedule", progress: "Progress", resources: "Resources", cost: "Cost", documents: "Documents", reports: "Reports", control: "Control", settings: "Settings",
    wbs: "Project / WBS", activities: "Activity Grid", gantt: "Gantt Chart", details: "Details", noActivities: "No activities loaded", noSchedule: "No scheduled activities", revision: "Revision", critical: "Critical",
  },
  fa: {
    project: "پروژه", schedule: "زمان‌بندی", progress: "پیشرفت", resources: "منابع", cost: "هزینه", documents: "اسناد", reports: "گزارش‌ها", control: "کنترل", settings: "تنظیمات",
    wbs: "پروژه / WBS", activities: "جدول فعالیت‌ها", gantt: "گانت", details: "جزئیات", noActivities: "فعالیتی بارگذاری نشده است", noSchedule: "فعالیت زمان‌بندی‌شده‌ای وجود ندارد", revision: "نسخه", critical: "بحرانی",
  },
} as const;

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
