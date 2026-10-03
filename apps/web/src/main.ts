import { FetchApiTransport } from "./client.js";
import { createP6LayoutPersistence, loadP6Presentation } from "./p6-api.js";
import { ProjectBootstrap, type ProjectBootstrapState } from "./project-bootstrap.js";
import { FetchSessionApi } from "./session-api.js";
import { WebSyncRuntime } from "./sync-runtime.js";
import { WorkspaceReadClient } from "./workspace-read-api.js";
import {
  addP6Field,
  removeP6Field,
  reorderP6Fields,
  updateP6FieldPresentation,
  selectActivity,
  selectWbs,
  setP6Presentation,
  setLocale,
  type WorkspaceLocale,
  type WorkspaceState,
} from "./workspace-model.js";
import { renderMainWorkspace } from "./workspace-view.js";

function renderApp(container: HTMLElement, state: WorkspaceState, p6Persistence?: ReturnType<typeof createP6LayoutPersistence>): void {
  const persistence = p6Persistence ?? createP6LayoutPersistence(new FetchApiTransport(window.location.origin), state.context);
  container.innerHTML = '<div class="cp-app-shell"><div id="workspace"></div></div>';
  const workspace = container.querySelector<HTMLElement>("#workspace");
  if (!workspace) throw new Error("WORKSPACE_ROOT_NOT_FOUND");

  renderMainWorkspace(workspace, state, {
    onMenuSelect: (menu) => {
      renderApp(container, { ...state, activeMenu: menu }, persistence);
    },
    onWbsSelect: (wbsId) => {
      renderApp(container, selectWbs(state, wbsId), persistence);
    },
    onActivitySelect: (activityId) => {
      renderApp(container, selectActivity(state, activityId), persistence);
    },
    onGanttActivitySelect: (activityId) => {
      renderApp(container, selectActivity(state, activityId), persistence);
    },
    onP6FieldAdd: async (fieldId) => {
      try {
        const next = addP6Field(state, fieldId);
        if (!next.p6Layout || !next.p6FieldRegistry) return;
        const saved = await persistence.save(next.p6Layout);
        renderApp(container, setP6Presentation(next, next.p6FieldRegistry, saved), persistence);
      } catch (error) {
        console.error("P6 layout save failed", error);
      }
    },
    onP6FieldReorder: async (orderedFieldIds) => {
      try {
        const next = reorderP6Fields(state, orderedFieldIds);
        if (!next.p6Layout || !next.p6FieldRegistry) return;
        const saved = await persistence.save(next.p6Layout);
        renderApp(container, setP6Presentation(next, next.p6FieldRegistry, saved), persistence);
      } catch (error) {
        console.error("P6 layout save failed", error);
      }
    },
    onP6FieldWidthChange: async (fieldId, width) => {
      try {
        const next = updateP6FieldPresentation(state, fieldId, { width });
        if (!next.p6Layout || !next.p6FieldRegistry) return;
        const saved = await persistence.save(next.p6Layout);
        renderApp(container, setP6Presentation(next, next.p6FieldRegistry, saved), persistence);
      } catch (error) {
        console.error("P6 layout save failed", error);
      }
    },
    onP6FieldRemove: async (fieldId) => {
      try {
        const next = removeP6Field(state, fieldId);
        if (!next.p6Layout || !next.p6FieldRegistry) return;
        const saved = await persistence.save(next.p6Layout);
        renderApp(container, setP6Presentation(next, next.p6FieldRegistry, saved), persistence);
      } catch (error) {
        console.error("P6 layout save failed", error);
      }
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
    renderApp(container, setLocale(state, next), persistence);
  });

  const status = document.createElement("div");
  status.className = "cp-app-status";
  status.append("Web shell · Authenticated workspace");
  status.append(languageButton);
  container.prepend(status);
}

function renderBootstrapState(
  container: HTMLElement,
  state: ProjectBootstrapState,
  bootstrap: ProjectBootstrap,
): void {
  if (state.status === "ready") {
    renderApp(container, state.workspace);
    return;
  }

  container.innerHTML = "";

  if (state.status === "loading" || state.status === "opening") {
    const message = state.status === "opening"
      ? "Opening project…"
      : "Loading workspace…";
    const loading = document.createElement("main");
    loading.className = "cp-shell-loading";
    loading.textContent = message;
    container.append(loading);
    return;
  }

  if (state.status === "selecting") {
    const main = document.createElement("main");
    main.className = "cp-project-selection";

    const heading = document.createElement("h1");
    heading.textContent = "Select project";
    main.append(heading);

    for (const project of state.projects) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = project.name;
      button.dataset.projectId = project.project_id;
      button.addEventListener("click", async () => {
        renderBootstrapState(container, { status: "opening", projectId: project.project_id }, bootstrap);
        const next = await bootstrap.selectProject(project.project_id);
        if (next) renderBootstrapState(container, next, bootstrap);
      });
      main.append(button);
    }

    container.append(main);
    return;
  }

  const error = document.createElement("main");
  error.className = "cp-shell-error";

  const heading = document.createElement("h1");
  heading.textContent = "Construction PM";
  error.append(heading);

  const message = document.createElement("p");
  message.textContent = state.error.message_key;
  error.append(message);

  if (state.error.available_actions.includes("retry") || state.error.retryable) {
    const retry = document.createElement("button");
    retry.type = "button";
    retry.textContent = "Retry";
    retry.addEventListener("click", async () => {
      renderBootstrapState(container, { status: "loading" }, bootstrap);
      const next = await bootstrap.start();
      if (next) renderBootstrapState(container, next, bootstrap);
    });
    error.append(retry);
  }

  container.append(error);
}

async function boot(): Promise<void> {
  const container = document.getElementById("app");
  if (!container) throw new Error("APP_ROOT_NOT_FOUND");

  const sessionApi = new FetchSessionApi(window.location.origin);
  const syncRuntime = new WebSyncRuntime();
  const workspaceReadClient = new WorkspaceReadClient(
    new FetchApiTransport(window.location.origin),
  );
  const bootstrap = new ProjectBootstrap({
    sessionApi,
    syncRuntime,
    workspaceReadClient,
    p6PresentationLoader: (state, context) =>
      loadP6Presentation(state, new FetchApiTransport(window.location.origin), context),
  });

  renderBootstrapState(container, { status: "loading" }, bootstrap);

  try {
    const state = await bootstrap.start();
    if (state) renderBootstrapState(container, state, bootstrap);
  } catch (error) {
    container.innerHTML = '<main class="cp-shell-error"><h1>Construction PM</h1><p>Unable to initialize the Web workspace.</p></main>';
    console.error(error);
  }
}

void boot();
