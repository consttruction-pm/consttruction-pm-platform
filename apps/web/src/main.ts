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
import { getBootstrapLabels } from "./bootstrap-labels.js";

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
    onP6FieldPresentationChange: async (fieldId, patch) => {
      try {
        const next = updateP6FieldPresentation(state, fieldId, patch);
        if (!next.p6Layout || !next.p6FieldRegistry) return;
        const saved = await persistence.save(next.p6Layout);
        renderApp(container, setP6Presentation(next, next.p6FieldRegistry, saved), persistence);
      } catch (error) {
        console.error("P6 layout save failed", error);
      }
    },
    onP6FieldVisibilityChange: async (fieldId, visible) => {
      try {
        const next = updateP6FieldPresentation(state, fieldId, { visible });
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
  locale: WorkspaceLocale = getInitialLocale(),
): void {
  const t = getBootstrapLabels(locale);
  if (state.status === "ready") {
    renderApp(container, state.workspace);
    return;
  }

  container.innerHTML = "";

  if (state.status === "loading" || state.status === "opening" || state.status === "creating") {
    const message = state.status === "opening"
      ? t.opening
      : state.status === "creating"
        ? t.creating
        : t.loading;
    const loading = document.createElement("main");
    loading.className = "cp-shell-loading";
    loading.textContent = message;
    container.append(loading);
    return;
  }

  const appendCreateProjectForm = (main: HTMLElement): void => {
    const section = document.createElement("section");
    section.className = "cp-project-create";
    section.dir = locale === "fa" ? "rtl" : "ltr";

    const heading = document.createElement("h2");
    heading.textContent = t.createProject;
    section.append(heading);

    const form = document.createElement("form");
    form.className = "cp-project-create-form";

    const label = document.createElement("label");
    label.textContent = t.projectName;
    const input = document.createElement("input");
    input.name = "projectName";
    input.type = "text";
    input.required = true;
    input.autocomplete = "organization";
    input.placeholder = t.projectNamePlaceholder;
    label.append(input);
    form.append(label);

    const submit = document.createElement("button");
    submit.type = "submit";
    submit.textContent = t.createAndOpen;
    form.append(submit);

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const name = input.value.trim();
      if (!name) {
        input.focus();
        return;
      }
      submit.disabled = true;
      renderBootstrapState(container, { status: "creating", projectId: "pending" }, bootstrap, locale);
      const next = await bootstrap.createProject(crypto.randomUUID(), name);
      if (next) renderBootstrapState(container, next, bootstrap);
    });

    section.append(form);
    main.append(section);
  };

  if (state.status === "selecting") {
    const main = document.createElement("main");
    main.className = "cp-project-selection";
    main.dir = locale === "fa" ? "rtl" : "ltr";

    const heading = document.createElement("h1");
    heading.textContent = t.selectProject;
    main.append(heading);

    for (const project of state.projects) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = project.name;
      button.dataset.projectId = project.project_id;
      button.addEventListener("click", async () => {
        renderBootstrapState(container, { status: "opening", projectId: project.project_id }, bootstrap, locale);
        const next = await bootstrap.selectProject(project.project_id);
        if (next) renderBootstrapState(container, next, bootstrap);
      });
      main.append(button);
    }

    appendCreateProjectForm(main);
    container.append(main);
    return;
  }

  const error = document.createElement("main");
  error.className = "cp-shell-error";
  error.dir = locale === "fa" ? "rtl" : "ltr";

  if (state.error.code === "NO_PROJECTS_AVAILABLE") {
    const main = document.createElement("main");
    main.className = "cp-project-selection";
    main.dir = locale === "fa" ? "rtl" : "ltr";
    const heading = document.createElement("h1");
    heading.textContent = t.createFirstProject;
    main.append(heading);
    const message = document.createElement("p");
    message.textContent = t.noProjects;
    main.append(message);
    appendCreateProjectForm(main);
    container.append(main);
    return;
  }

  const heading = document.createElement("h1");
  heading.textContent = t.constructionPm;
  error.append(heading);

  const message = document.createElement("p");
  message.textContent = state.error.message_key;
  error.append(message);

  if (state.error.available_actions.includes("retry") || state.error.retryable) {
    const retry = document.createElement("button");
    retry.type = "button";
    retry.textContent = t.retry;
    retry.addEventListener("click", async () => {
      renderBootstrapState(container, { status: "loading" }, bootstrap, locale);
      const next = await bootstrap.start();
      if (next) renderBootstrapState(container, next, bootstrap);
    });
    error.append(retry);
  }

  if (state.error.available_actions.includes("refresh")) {
    const refresh = document.createElement("button");
    refresh.type = "button";
    refresh.textContent = t.refresh;
    refresh.addEventListener("click", async () => {
      renderBootstrapState(container, { status: "loading" }, bootstrap, getInitialLocale());
      const next = await bootstrap.start();
      if (next) renderBootstrapState(container, next, bootstrap);
    });
    error.append(refresh);
  }

  container.append(error);
}

function getInitialLocale(): WorkspaceLocale {
  return navigator.language.toLowerCase().startsWith("fa") ? "fa" : "en";
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
    const t = getBootstrapLabels(getInitialLocale());
    container.innerHTML = `<main class="cp-shell-error" dir="${getInitialLocale() === "fa" ? "rtl" : "ltr"}"><h1>${t.constructionPm}</h1><p>${t.unableToInitialize}</p></main>`;
    console.error(error);
  }
}

void boot();
