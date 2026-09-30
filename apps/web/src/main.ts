import {
  createWorkspaceState,
  selectActivity,
  selectWbs,
  setLocale,
  type WorkspaceLocale,
  type WorkspaceState,
} from "./workspace-model.js";
import { renderMainWorkspace } from "./workspace-view.js";

const DEFAULT_CONTEXT = {
  tenant_id: "demo-tenant",
  project_id: "demo-project",
  revision: 0,
};

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

function boot(): void {
  const container = document.getElementById("app");
  if (!container) throw new Error("APP_ROOT_NOT_FOUND");

  try {
    renderApp(container, createWorkspaceState(DEFAULT_CONTEXT));
  } catch (error) {
    container.innerHTML = '<main class="cp-shell-error"><h1>Construction PM</h1><p>Unable to initialize the Web workspace.</p></main>';
    console.error(error);
  }
}

boot();
