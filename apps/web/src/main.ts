import {
  addP6Field,
  addP6GridFilter,
  addP6GridGroup,
  addP6GridSort,
  createWorkspaceState,
  removeP6Field,
  reorderP6Fields,
  reorderP6GridFilters,
  reorderP6GridGroups,
  reorderP6GridSorts,
  selectActivity,
  selectWbs,
  setLocale,
  setP6GridFilters,
  setP6GridGroups,
  setP6GridSorts,
  updateP6ActivityCell,
  updateP6FieldPresentation,
  type WorkspaceLocale,
  type WorkspaceState,
} from "./workspace-model.js";
import { FetchApiTransport, FetchProjectLifecycleClient } from "./client.js";
import { WorkspaceReadClient } from "./workspace-read-api.js";
import { createP6ReadOnlyLayoutPersistence } from "./p6-api.js";
import { createP6LayoutPersistenceController } from "./p6-layout-persistence-controller.js";
import { renderMainWorkspace } from "./workspace-view.js";
import { selectProjectId } from "./project-bootstrap.js";

function renderApp(container: HTMLElement, state: WorkspaceState): void {
  container.innerHTML = '<div class="cp-app-shell"><div id="workspace"></div></div>';
  const workspace = container.querySelector<HTMLElement>("#workspace");
  if (!workspace) throw new Error("WORKSPACE_ROOT_NOT_FOUND");

  renderMainWorkspace(workspace, state, {
    onMenuSelect: (menu) => {
      renderApp(container, { ...state, activeMenu: menu });
    },
    onWbsSelect: (wbsId) => {
      renderApp(container, selectWbs(state, wbsId));
    },
    onActivitySelect: (activityId) => {
      renderApp(container, selectActivity(state, activityId));
    },
    onP6FieldAdd: (fieldId) => {
      renderApp(container, addP6Field(state, fieldId));
    },
    onP6FieldRemove: (fieldId) => {
      renderApp(container, removeP6Field(state, fieldId));
    },
    onP6FieldReorder: (orderedFieldIds) => {
      renderApp(container, reorderP6Fields(state, orderedFieldIds));
    },
    onP6FieldPresentationChange: (fieldId, patch) => {
      renderApp(container, updateP6FieldPresentation(state, fieldId, patch));
    },
    onP6CellValueChange: (activityId, fieldId, value) => {
      renderApp(container, updateP6ActivityCell(state, activityId, fieldId, value));
    },
    p6GridPresentation: {
      sorts: state.p6GridSorts,
      groups: state.p6GridGroups,
      filters: state.p6GridFilters,
    },
    onP6GridSortChange: (sorts) => {
      renderApp(container, setP6GridSorts(state, sorts));
    },
    onP6GridSortAdd: () => {
      renderApp(container, addP6GridSort(state));
    },
    onP6GridSortReorder: (orderedFieldIds) => {
      renderApp(container, reorderP6GridSorts(state, orderedFieldIds));
    },
    onP6GridGroupChange: (groups) => {
      renderApp(container, setP6GridGroups(state, groups));
    },
    onP6GridGroupAdd: () => {
      renderApp(container, addP6GridGroup(state));
    },
    onP6GridGroupReorder: (orderedFieldIds) => {
      renderApp(container, reorderP6GridGroups(state, orderedFieldIds));
    },
    onP6GridFilterChange: (filters) => {
      renderApp(container, setP6GridFilters(state, filters));
    },
    onP6GridFilterAdd: () => {
      renderApp(container, addP6GridFilter(state));
    },
    onP6GridFilterReorder: (orderedIndexes) => {
      renderApp(container, reorderP6GridFilters(state, orderedIndexes));
    },
  });

  const shell = container.querySelector<HTMLElement>(".cp-workspace");
  if (!shell) return;

  const languageButton = document.createElement("button");
  languageButton.type = "button";
  languageButton.textContent = state.locale === "fa" ? "English" : "فارسی";
  languageButton.setAttribute("aria-label", state.locale === "fa" ? "Switch to English" : "تغییر به فارسی");
  languageButton.addEventListener("click", () => {
    const next: WorkspaceLocale = state.locale === "fa" ? "en" : "fa";
    renderApp(container, setLocale(state, next));
  });

  const status = document.createElement("div");
  status.className = "cp-app-status";
  status.append("Web shell · Main integration baseline");
  status.append(languageButton);
  container.prepend(status);
}

async function boot(): Promise<void> {
  const container = document.getElementById("app");
  if (!container) throw new Error("APP_ROOT_NOT_FOUND");

  try {
    const baseUrl = window.location.origin;
    const lifecycle = new FetchProjectLifecycleClient(baseUrl);
    const projects = await lifecycle.listProjects();
    if (!projects.ok) throw new Error(projects.error.code);
    const requestedProjectId = new URLSearchParams(window.location.search).get("project_id");
    const projectId = selectProjectId(projects.data.projects, requestedProjectId);

    const opened = await lifecycle.openProject(projectId);
    if (!opened.ok) throw new Error(opened.error.code);

    const workspaceRead = new WorkspaceReadClient(new FetchApiTransport(baseUrl));
    const workspace = await workspaceRead.load(opened.data.context);
    if (!workspace.ok) throw new Error(workspace.error.code);

    const layoutPersistence = createP6ReadOnlyLayoutPersistence(
      new FetchApiTransport(baseUrl),
      opened.data.context,
    );
    const layoutController = createP6LayoutPersistenceController(
      layoutPersistence,
      "project",
      "activity",
    );
    const hydratedWorkspace = await layoutController.load(workspace.data);

    renderApp(container, hydratedWorkspace);
  } catch (error) {
    container.innerHTML = '<main class="cp-shell-error"><h1>Construction PM</h1><p>Unable to initialize the Web workspace.</p></main>';
    console.error(error);
  }
}

void boot();
