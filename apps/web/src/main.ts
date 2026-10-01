import {
  createWorkspaceState,
  selectActivity,
  selectWbs,
  setLocale,
  type WorkspaceLocale,
  type WorkspaceState,
} from "./workspace-model.js";
import { renderMainWorkspace } from "./workspace-view.js";
import {
  FetchSessionApi,
  toWorkspaceContext,
  type ProjectSummary,
  type SessionApi,
} from "./session-api.js";

function renderMessage(container: HTMLElement, message: string): void {
  container.innerHTML = "";
  const main = document.createElement("main");
  main.className = "cp-shell-error";
  const title = document.createElement("h1");
  title.textContent = "Construction PM";
  const text = document.createElement("p");
  text.textContent = message;
  main.append(title, text);
  container.append(main);
}

function renderProjectSelector(
  container: HTMLElement,
  api: SessionApi,
  projects: readonly ProjectSummary[],
  errorMessage?: string,
): void {
  container.innerHTML = "";
  const main = document.createElement("main");
  main.className = "cp-shell-error";

  const title = document.createElement("h1");
  title.textContent = "Construction PM";
  const heading = document.createElement("p");
  heading.textContent = projects.length
    ? "Select a project to open."
    : "No projects are available for this account.";
  main.append(title, heading);

  if (errorMessage) {
    const error = document.createElement("p");
    error.textContent = errorMessage;
    main.append(error);
  }

  for (const project of projects) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = `${project.name} · revision ${project.revision}`;
    button.addEventListener("click", async () => {
      button.disabled = true;
      const result = await api.openProject(project.project_id);
      if (!result.ok) {
        button.disabled = false;
        renderProjectSelector(container, api, projects, result.error.message_key);
        return;
      }
      renderWorkspace(container, result.data.context);
    });
    main.append(button);
  }

  container.append(main);
}

function renderWorkspace(
  container: HTMLElement,
  context: Parameters<typeof toWorkspaceContext>[0],
): void {
  const state = createWorkspaceState(toWorkspaceContext(context));
  renderApp(container, state);
}

function renderApp(container: HTMLElement, state: WorkspaceState): void {
  container.innerHTML = '<div class="cp-app-shell"><div id="workspace"></div></div>';
  const workspace = container.querySelector<HTMLElement>("#workspace");
  if (!workspace) throw new Error("WORKSPACE_ROOT_NOT_FOUND");

  renderMainWorkspace(workspace, state, {
    onMenuSelect: (menu) => renderApp(container, { ...state, activeMenu: menu }),
    onWbsSelect: (wbsId) => renderApp(container, selectWbs(state, wbsId)),
    onActivitySelect: (activityId) => renderApp(container, selectActivity(state, activityId)),
  });

  const languageButton = document.createElement("button");
  languageButton.type = "button";
  languageButton.textContent = state.locale === "fa" ? "English" : "فارسی";
  languageButton.setAttribute(
    "aria-label",
    state.locale === "fa" ? "Switch to English" : "تغییر به فارسی",
  );
  languageButton.addEventListener("click", () => {
    const next: WorkspaceLocale = state.locale === "fa" ? "en" : "fa";
    document.documentElement.lang = next;
    document.documentElement.dir = next === "fa" ? "rtl" : "ltr";
    renderApp(container, setLocale(state, next));
  });

  const status = document.createElement("div");
  status.className = "cp-app-status";
  status.append("Web shell · authenticated project context", languageButton);
  container.prepend(status);
}

async function boot(): Promise<void> {
  const container = document.getElementById("app");
  if (!container) throw new Error("APP_ROOT_NOT_FOUND");

  const api = new FetchSessionApi(window.location.origin);
  renderMessage(container, "Loading authenticated session…");

  try {
    const session = await api.getSession();
    if (!session.ok) {
      renderMessage(container, "Please sign in to continue.");
      return;
    }

    const projects = await api.listProjects();
    if (!projects.ok) {
      renderMessage(container, projects.error.message_key);
      return;
    }

    if (projects.data.projects.length === 1) {
      const opened = await api.openProject(projects.data.projects[0].project_id);
      if (opened.ok) {
        renderWorkspace(container, opened.data.context);
        return;
      }
      renderProjectSelector(container, api, projects.data.projects, opened.error.message_key);
      return;
    }

    renderProjectSelector(container, api, projects.data.projects);
  } catch (error) {
    renderMessage(container, "Unable to initialize the Web application.");
    console.error(error);
  }
}

void boot();
