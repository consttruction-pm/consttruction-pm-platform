import {
  createWorkspaceState,
  selectActivity,
  selectWbs,
  setCalendarMode,
  setLocale,
  withActivities,
  type WorkspaceCalendarMode,
  type WorkspaceState,
} from "./workspace-model.js";
import { renderMainWorkspace } from "./workspace-view.js";
import { getBetaMenu, getBetaSubmenuLabel, type BetaSubmenu } from "./beta-navigation.js";

const context = {
  tenant_id: "demo-tenant",
  project_id: "DEMO-CONSTRUCTION-001",
  revision: 1,
};

const demoActivities = [
  {
    id: "A-1000",
    wbsId: "WBS-01",
    code: "01-01",
    name: "Site Preparation",
    gantt: { start: "2026-09-28T07:00:00Z", finish: "2026-10-01T15:00:00Z", progressPercent: 65, critical: true },
    cells: { planned_duration: 4, remaining_duration: 1.5, progress: 65 },
  },
  {
    id: "A-1010",
    wbsId: "WBS-01",
    code: "01-02",
    name: "Foundation",
    gantt: { start: "2026-10-02T07:00:00Z", finish: "2026-10-08T15:00:00Z", progressPercent: 35, critical: true },
    cells: { planned_duration: 7, remaining_duration: 4.5, progress: 35 },
  },
  {
    id: "A-1020",
    wbsId: "WBS-02",
    code: "02-01",
    name: "Structure",
    gantt: { start: "2026-10-09T07:00:00Z", finish: "2026-10-24T15:00:00Z", progressPercent: 10, critical: false },
    cells: { planned_duration: 16, remaining_duration: 14.5, progress: 10 },
  },
] as const;

const appRoot = document.getElementById("app");
const routeStatus = document.getElementById("beta-route");
const submenuRoot = document.getElementById("beta-submenu");

if (!appRoot || !routeStatus || !submenuRoot) {
  throw new Error("BETA_ROOT_NOT_FOUND");
}

let state: WorkspaceState = withActivities(
  createWorkspaceState(context, "en", "gregorian"),
  demoActivities,
);

function syncRoute(): void {
  const menu = getBetaMenu(state.activeMenu);
  routeStatus.textContent =
    `Beta module: ${menu.label} · status: ${currentMenuStatus(menu.items)} · context: ${context.project_id} · calendar: ${state.calendarMode} · locale: ${state.locale}`;
}

function renderSubmenu(): void {
  const menu = getBetaMenu(state.activeMenu);
  submenuRoot.innerHTML = menu.items.map((item) =>
    `<button type="button" data-submenu-id="${escapeAttribute(item.id)}">${escapeHtml(getBetaSubmenuLabel(item, state.locale))} <span class="beta-status">[${item.status}]</span></button>`
  ).join("");
  submenuRoot.querySelectorAll<HTMLButtonElement>("[data-submenu-id]").forEach((button) => {
    button.addEventListener("click", () => {
      const item = menu.items.find((candidate) => candidate.id === button.dataset.submenuId);
      if (!item) return;
      window.location.hash = item.id;
      routeStatus.textContent =
        `Beta screen: ${menu.label} / ${getBetaSubmenuLabel(item, state.locale)} · status: ${item.status} · context: ${context.project_id}`;
    });
  });
}

function currentMenuStatus(items: readonly BetaSubmenu[]): string {
  if (items.some((item) => item.status === "Implemented")) return "Implemented";
  if (items.every((item) => item.status === "Preview")) return "Preview";
  return "Partial";
}

function render(): void {
  syncRoute();
  renderSubmenu();
  renderMainWorkspace(appRoot, state, {
    onMenuSelect: (menu) => {
      state = { ...state, activeMenu: menu };
      render();
    },
    onWbsSelect: (wbsId) => {
      state = selectWbs(state, wbsId);
      render();
    },
    onActivitySelect: (activityId) => {
      state = selectActivity(state, activityId);
      render();
    },
  });
}

function installToolbar(): void {
  document.getElementById("locale-en")?.addEventListener("click", () => {
    state = setLocale(state, "en");
    render();
  });
  document.getElementById("locale-fa")?.addEventListener("click", () => {
    state = setLocale(state, "fa");
    render();
  });
  document.getElementById("calendar-gregorian")?.addEventListener("click", () => {
    state = setCalendarMode(state, "gregorian");
    render();
  });
  document.getElementById("calendar-jalali")?.addEventListener("click", () => {
    state = setCalendarMode(state, "jalali");
    render();
  });
}

installToolbar();
render();

function escapeHtml(value: string): string {
  return value.replace(/[&<>"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[character]!);
}

function escapeAttribute(value: string): string {
  return escapeHtml(value).replace(/'/g, "&#39;");
}
