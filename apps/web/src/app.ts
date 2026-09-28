import {
  createWorkspaceState,
  selectActivity,
  selectWbs,
  setCalendarMode,
  setLocale,
  withActivities,
  type WorkspaceCalendarMode,
  type WorkspaceLocale,
  type WorkspaceState,
} from "./workspace-model.js";
import { renderMainWorkspace } from "./workspace-view.js";

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

const moduleStatus: Record<WorkspaceState["activeMenu"], { status: "Implemented" | "Partial" | "Preview"; label: string }> = {
  project: { status: "Partial", label: "Project / WBS" },
  schedule: { status: "Partial", label: "Schedule / Activities / Gantt" },
  progress: { status: "Partial", label: "Progress / EVM" },
  resources: { status: "Partial", label: "Resources / Assignments" },
  cost: { status: "Partial", label: "Cost / Forecast" },
  documents: { status: "Partial", label: "Documents / Evidence" },
  reports: { status: "Partial", label: "Reports / Typed datasets" },
  control: { status: "Partial", label: "Control / Change / Claims" },
  settings: { status: "Partial", label: "Settings / Language / Permissions" },
};

const appRoot = document.getElementById("app");
const routeStatus = document.getElementById("beta-route");

if (!appRoot || !routeStatus) {
  throw new Error("BETA_ROOT_NOT_FOUND");
}

let state: WorkspaceState = withActivities(
  createWorkspaceState(context, "en", "gregorian"),
  demoActivities,
);

function syncRoute(): void {
  const module = moduleStatus[state.activeMenu];
  routeStatus.textContent = `Beta module: ${module.label} · status: ${module.status} · context: ${context.project_id} · calendar: ${state.calendarMode} · locale: ${state.locale}`;
}

function render(): void {
  syncRoute();
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
    state = setCalendarMode(state, "gregorian" as WorkspaceCalendarMode);
    render();
  });
  document.getElementById("calendar-jalali")?.addEventListener("click", () => {
    state = setCalendarMode(state, "jalali" as WorkspaceCalendarMode);
    render();
  });
}

installToolbar();
render();

void (document as Document & { __constructionPmBetaReady?: boolean }).constructor;
