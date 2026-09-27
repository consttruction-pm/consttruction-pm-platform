import type { WorkspaceState } from "./workspace-model.js";

const labels = {
  en: {
    project: "Project",
    schedule: "Schedule",
    progress: "Progress",
    resources: "Resources",
    cost: "Cost",
    documents: "Documents",
    reports: "Reports",
    control: "Control",
    settings: "Settings",
    wbs: "Project / WBS",
    activities: "Activity Grid",
    gantt: "Gantt Chart",
    details: "Details",
    noActivities: "No activities loaded",
  },
  fa: {
    project: "پروژه",
    schedule: "زمان‌بندی",
    progress: "پیشرفت",
    resources: "منابع",
    cost: "هزینه",
    documents: "اسناد",
    reports: "گزارش‌ها",
    control: "کنترل",
    settings: "تنظیمات",
    wbs: "پروژه / WBS",
    activities: "جدول فعالیت‌ها",
    gantt: "گانت",
    details: "جزئیات",
    noActivities: "فعالیتی بارگذاری نشده است",
  },
} as const;

export type WorkspaceRendererOptions = {
  onMenuSelect?: (menu: WorkspaceState["activeMenu"]) => void;
  onActivitySelect?: (activityId: string) => void;
};

export function renderMainWorkspace(
  container: HTMLElement,
  state: WorkspaceState,
  options: WorkspaceRendererOptions = {},
): void {
  const t = labels[state.locale];

  container.innerHTML = `
    <section class="cp-workspace" dir="${state.direction}" data-project="${escapeAttribute(state.context.project_id)}">
      <header class="cp-header">
        <div class="cp-brand">Construction PM</div>
        <div class="cp-project">${escapeHtml(state.context.project_id)}</div>
        <div class="cp-revision">R${state.context.revision}</div>
      </header>

      <nav class="cp-menu" aria-label="Main Menu">
        ${menuButton("project", t.project, state)}
        ${menuButton("schedule", t.schedule, state)}
        ${menuButton("progress", t.progress, state)}
        ${menuButton("resources", t.resources, state)}
        ${menuButton("cost", t.cost, state)}
        ${menuButton("documents", t.documents, state)}
        ${menuButton("reports", t.reports, state)}
        ${menuButton("control", t.control, state)}
        ${menuButton("settings", t.settings, state)}
      </nav>

      <main class="cp-main">
        <aside class="cp-panel cp-wbs">
          <h2>${t.wbs}</h2>
          <div class="cp-empty">WBS tree is API-backed</div>
        </aside>

        <section class="cp-center">
          <section class="cp-panel cp-grid">
            <h2>${t.activities}</h2>
            <div class="cp-table-wrap">
              <table>
                <thead>
                  <tr>
                    ${state.columns.map((column) => `
                      <th data-column-type="${column.dataType}">
                        ${escapeHtml(column.label)}
                        ${column.formula ? '<span aria-label="formula column">ƒx</span>' : ""}
                      </th>`).join("")}
                  </tr>
                </thead>
                <tbody>
                  ${state.activities.length
                    ? state.activities.map((activity) => `
                      <tr data-activity-id="${escapeAttribute(activity.id)}" tabindex="0">
                        <td>${escapeHtml(activity.id)}</td>
                        <td>${escapeHtml(activity.name)}</td>
                        <td colspan="${Math.max(0, state.columns.length - 2)}">—</td>
                      </tr>`).join("")
                    : `<tr><td colspan="${Math.max(1, state.columns.length)}">${t.noActivities}</td></tr>`}
                </tbody>
              </table>
            </div>
          </section>

          <section class="cp-panel cp-gantt">
            <h2>${t.gantt}</h2>
            <div class="cp-gantt-placeholder" role="img" aria-label="${escapeAttribute(t.gantt)}">
              Gantt rendering is fed by authoritative schedule results.
            </div>
          </section>
        </section>

        <aside class="cp-panel cp-details">
          <h2>${t.details}</h2>
          <div>${state.selectedActivityId ? escapeHtml(state.selectedActivityId) : "—"}</div>
        </aside>
      </main>
    </section>
  `;

  container.querySelectorAll<HTMLElement>("[data-menu]").forEach((button) => {
    button.addEventListener("click", () => {
      options.onMenuSelect?.(button.dataset.menu as WorkspaceState["activeMenu"]);
    });
  });

  container.querySelectorAll<HTMLElement>("[data-activity-id]").forEach((row) => {
    row.addEventListener("click", () => {
      const id = row.dataset.activityId;
      if (id) options.onActivitySelect?.(id);
    });
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        const id = row.dataset.activityId;
        if (id) options.onActivitySelect?.(id);
      }
    });
  });
}

function menuButton(
  key: WorkspaceState["activeMenu"],
  label: string,
  state: WorkspaceState,
): string {
  return `<button type="button" data-menu="${key}" aria-current="${key === state.activeMenu ? "page" : "false"}">${escapeHtml(label)}</button>`;
}

function escapeHtml(value: string): string {
  return value.replace(
    /[&<>"']/g,
    (character) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[character]!,
  );
}

function escapeAttribute(value: string): string {
  return escapeHtml(value);
}
