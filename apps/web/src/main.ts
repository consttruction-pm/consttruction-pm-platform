import { FetchApiTransport, type ProjectContext } from "./client.js";
import { createP6LayoutPersistence, loadP6LayoutRevisions, loadP6Presentation } from "./p6-api.js";
import type { LayoutDefinition } from "./p6-field-layout-foundation.js";
import { ProjectBootstrap, type ProjectBootstrapState } from "./project-bootstrap.js";
import { FetchSessionApi } from "./session-api.js";
import { WebSyncRuntime } from "./sync-runtime.js";
import { WorkspaceReadClient } from "./workspace-read-api.js";
import {
  addP6Field,
  applyAuthoritativeScheduleFacts,
  removeP6Field,
  reorderP6Fields,
  setActivityFilter,
  setActivitySort,
  toggleActivitySortDirection,
  updateP6FieldPresentation,
  selectActivity,
  selectWbs,
  setP6Presentation,
  setLocale,
  setCalendarMode,
  type WorkspaceLocale,
  type WorkspaceState,
} from "./workspace-model.js";
import { renderMainWorkspace } from "./workspace-view.js";
import { getBootstrapLabels } from "./bootstrap-labels.js";
import { getWorkspaceShellLabels } from "./shell-labels.js";
import { renderLandingPage } from "./landing.js";
import { getAvailableWorkspaceLocales, getWorkspaceLocaleDisplayName } from "./workspace-localization.js";
import { mountAIActionPanel } from "./ai-action-panel.js";
import { mountAIAssistantChatPanel } from "./ai-assistant-chat.js";
import { mountScheduleCyclePanels } from "./schedule-cycle.js";
import { mountFormulaEditorPanel } from "./p6-formula-panel.js";
import { mountInterchangePanel } from "./p6-interchange-panel.js";
import { mountCapacityPanel } from "./p6-capacity-panel.js";

type LayoutHistoryNotice = "undone" | "redone" | "restored" | "empty" | "failed" | "conflict";

type LayoutHistoryState = {
  undo: LayoutDefinition[];
  redo: LayoutDefinition[];
  noticeKey: LayoutHistoryNotice | null;
  revisions: LayoutDefinition[] | null;
  revisionRequest: Promise<LayoutDefinition[]> | null;
  revisionEpoch: number;
  revisionLoadFailed: boolean;
};

const layoutHistoryStore = new Map<string, LayoutHistoryState>();
let currentWorkspaceState: WorkspaceState | null = null;

function layoutHistoryKey(context: ProjectContext, layout: LayoutDefinition): string {
  return [
    context.tenant_id,
    context.project_id,
    String(context.revision),
    layout.scope,
    layout.view_id,
  ].join("::");
}

function getLayoutHistory(context: ProjectContext, layout: LayoutDefinition): LayoutHistoryState {
  const key = layoutHistoryKey(context, layout);
  const existing = layoutHistoryStore.get(key);
  if (existing) return existing;
  const created: LayoutHistoryState = {
    undo: [],
    redo: [],
    noticeKey: null,
    revisions: null,
    revisionRequest: null,
    revisionEpoch: 0,
    revisionLoadFailed: false,
  };
  layoutHistoryStore.set(key, created);
  return created;
}

function renderApp(
  container: HTMLElement,
  state: WorkspaceState,
  p6Persistence?: ReturnType<typeof createP6LayoutPersistence>,
  preserveLayoutNotice = false,
): void {
  currentWorkspaceState = state;
  const shellLabels = getWorkspaceShellLabels(state.locale);
  const persistence = p6Persistence ?? createP6LayoutPersistence(new FetchApiTransport(window.location.origin), state.context);

  let appShell = container.querySelector<HTMLElement>(".cp-app-shell");
  let status = container.querySelector<HTMLElement>(".cp-app-status");
  let workspace = container.querySelector<HTMLElement>("#workspace");

  if (!appShell || !status || !workspace) {
    container.innerHTML = '<div class="cp-app-shell"><div class="cp-app-status"></div><div id="workspace"></div></div>';
    appShell = container.querySelector<HTMLElement>(".cp-app-shell");
    status = container.querySelector<HTMLElement>(".cp-app-status");
    workspace = container.querySelector<HTMLElement>("#workspace");
  }

  if (!appShell || !status || !workspace) throw new Error("WORKSPACE_ROOT_NOT_FOUND");

  const languageButton = document.createElement("button");
  languageButton.type = "button";
  languageButton.dataset.languageToggle = "true";
  const availableLocales = getAvailableWorkspaceLocales();
  const currentLocaleIndex = availableLocales.indexOf(state.locale);
  const nextLocale = availableLocales[(currentLocaleIndex + 1) % availableLocales.length] ?? "en";
  languageButton.textContent = getWorkspaceLocaleDisplayName(nextLocale);
  languageButton.setAttribute("aria-label", `Switch language to ${getWorkspaceLocaleDisplayName(nextLocale)}`);
  languageButton.onclick = () => {
    const next: WorkspaceLocale = nextLocale;
    renderApp(container, setLocale(state, next), persistence);
  };

  const nextCalendarMode = state.calendarMode === "jalali" ? "gregorian" : "jalali";
  const calendarButton = document.createElement("button");
  calendarButton.type = "button";
  calendarButton.dataset.calendarMode = nextCalendarMode;
  calendarButton.textContent = state.calendarMode === "jalali" ? "Gregorian" : "Jalali";
  const calendarLabel = nextCalendarMode === "jalali" ? shellLabels.switchToJalali : shellLabels.switchToGregorian;
  calendarButton.setAttribute("aria-label", calendarLabel);
  calendarButton.setAttribute("title", calendarLabel);
  calendarButton.onclick = () => {
    renderApp(container, setCalendarMode(state, nextCalendarMode), persistence);
  };
  status.replaceChildren(document.createTextNode(shellLabels.status), calendarButton, languageButton);
  const aiTransport = new FetchApiTransport(window.location.origin);
  let refreshAIProposals: (() => Promise<void>) | undefined;
  mountAIAssistantChatPanel(
    appShell,
    aiTransport,
    state.context,
    state.locale,
    () => { if (refreshAIProposals) void refreshAIProposals(); },
  );
  refreshAIProposals = mountAIActionPanel(
    appShell, aiTransport, state.context, state.locale,
  );

  const layoutHistory = state.p6Layout ? getLayoutHistory(state.context, state.p6Layout) : null;
  const historyView = state.p6Layout && layoutHistory
    ? {
        canUndo: layoutHistory.undo.length > 0 || state.p6Layout.revision > 0,
        canRedo: layoutHistory.redo.length > 0,
        noticeKey: layoutHistory.noticeKey,
        revisions: layoutHistory.revisions?.map((revision) => ({
          revision: revision.revision,
          columnCount: revision.columns.length,
        })),
      }
    : undefined;

  const requestLayoutRevisions = (layout: LayoutDefinition): Promise<LayoutDefinition[]> => {
    const history = getLayoutHistory(state.context, layout);
    if (history.revisions) return Promise.resolve(history.revisions);
    if (!history.revisionRequest) {
      const epoch = history.revisionEpoch;
      const request = loadP6LayoutRevisions(aiTransport, state.context, layout.scope, layout.view_id)
        .then((loaded) => {
          if (history.revisionEpoch === epoch) {
            history.revisions = loaded;
            history.revisionLoadFailed = false;
          }
          return loaded;
        });
      history.revisionRequest = request;
      const release = () => {
        if (history.revisionRequest === request) history.revisionRequest = null;
      };
      void request.then(release, release);
    }
    return history.revisionRequest;
  };

  const invalidateLayoutRevisions = (history: LayoutHistoryState): void => {
    history.revisionEpoch += 1;
    history.revisions = null;
    history.revisionRequest = null;
    history.revisionLoadFailed = false;
  };

  const reloadLatestLayout = async (scope: LayoutDefinition["scope"], viewId: string): Promise<boolean> => {
    const latest = await persistence.load(scope, viewId);
    if (!latest || !state.p6FieldRegistry) return false;
    const latestHistory = getLayoutHistory(state.context, latest);
    latestHistory.noticeKey = "conflict";
    invalidateLayoutRevisions(latestHistory);
    renderApp(container, setP6Presentation(state, state.p6FieldRegistry, latest), persistence);
    return true;
  };

  const reportLayoutFailure = async (error: unknown): Promise<void> => {
    const code = error instanceof Error ? error.message : "";
    console.error("P6 layout save failed", error);
    const failedLayout = state.p6Layout;
    if (failedLayout) {
      const failedHistory = getLayoutHistory(state.context, failedLayout);
      failedHistory.undo.length = 0;
      failedHistory.redo.length = 0;
      // Both codes mean the client's base no longer matches the stored head:
      // another writer published this revision (immutable) or moved further
      // ahead (conflict). Reloading the head is the only safe recovery.
      const staleBase = code === "REVISION_CONFLICT" || code === "IMMUTABLE_LAYOUT_REVISION";
      failedHistory.noticeKey = staleBase ? "conflict" : "failed";
      if (staleBase) {
        try {
          if (await reloadLatestLayout(failedLayout.scope, failedLayout.view_id)) return;
        } catch (reloadError) {
          console.error("P6 layout reload failed", reloadError);
        }
      }
    }
    renderApp(container, state, persistence);
  };

  const commitLayout = async (next: WorkspaceState): Promise<void> => {
    if (!next.p6Layout || !next.p6FieldRegistry) return;
    try {
      const saved = await persistence.save(next.p6Layout);
      const savedHistory = getLayoutHistory(next.context, saved);
      if (state.p6Layout) savedHistory.undo.push(state.p6Layout);
      savedHistory.redo.length = 0;
      savedHistory.noticeKey = null;
      invalidateLayoutRevisions(savedHistory);
      renderApp(container, setP6Presentation(next, next.p6FieldRegistry, saved), persistence);
    } catch (error) {
      await reportLayoutFailure(error);
    }
  };

  const mutateLayout = (mutate: () => WorkspaceState): void => {
    try {
      void commitLayout(mutate());
    } catch (error) {
      void reportLayoutFailure(error);
    }
  };

  const undoLayout = async (): Promise<void> => {
    const layout = state.p6Layout;
    const registry = state.p6FieldRegistry;
    if (!layout || !registry) return;
    const history = getLayoutHistory(state.context, layout);
    if (!history.undo.length) {
      try {
        const revisions = await requestLayoutRevisions(layout);
        const currentIndex = revisions.findIndex((revision) => revision.revision === layout.revision);
        const older = currentIndex < 0 ? [] : revisions.slice(currentIndex + 1);
        if (!older.length) {
          history.noticeKey = "empty";
          renderApp(container, state, persistence);
          return;
        }
        for (const revision of older.slice().reverse()) history.undo.push(revision);
      } catch (error) {
        console.error("P6 layout history read failed", error);
        history.noticeKey = "failed";
        renderApp(container, state, persistence);
        return;
      }
    }
    const target = history.undo.pop();
    if (!target) return;
    try {
      const saved = await persistence.save({ ...target, revision: layout.revision + 1 });
      history.redo.push(layout);
      history.noticeKey = "undone";
      invalidateLayoutRevisions(history);
      renderApp(container, setP6Presentation(state, registry, saved), persistence);
    } catch (error) {
      await reportLayoutFailure(error);
    }
  };

  const redoLayout = async (): Promise<void> => {
    const layout = state.p6Layout;
    const registry = state.p6FieldRegistry;
    if (!layout || !registry) return;
    const history = getLayoutHistory(state.context, layout);
    const target = history.redo.pop();
    if (!target) return;
    try {
      const saved = await persistence.save({ ...target, revision: layout.revision + 1 });
      history.undo.push(layout);
      history.noticeKey = "redone";
      invalidateLayoutRevisions(history);
      renderApp(container, setP6Presentation(state, registry, saved), persistence);
    } catch (error) {
      await reportLayoutFailure(error);
    }
  };

  const restoreLayout = async (revision: number): Promise<void> => {
    const layout = state.p6Layout;
    const registry = state.p6FieldRegistry;
    if (!layout || !registry) return;
    const history = getLayoutHistory(state.context, layout);
    let revisions: LayoutDefinition[];
    try {
      revisions = await requestLayoutRevisions(layout);
    } catch (error) {
      console.error("P6 layout history read failed", error);
      history.noticeKey = "failed";
      renderApp(container, state, persistence);
      return;
    }
    const target = revisions.find((item) => item.revision === revision);
    if (!target || target.revision >= layout.revision) {
      history.noticeKey = "empty";
      renderApp(container, state, persistence);
      return;
    }
    try {
      const saved = await persistence.save({ ...target, revision: layout.revision + 1 });
      history.undo.push(layout);
      history.redo.length = 0;
      history.noticeKey = "restored";
      invalidateLayoutRevisions(history);
      renderApp(container, setP6Presentation(state, registry, saved), persistence);
    } catch (error) {
      await reportLayoutFailure(error);
    }
  };

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
    onActivityFilterChange: (filterText) => {
      renderApp(container, setActivityFilter(state, filterText), persistence);
    },
    onActivitySortChange: (columnId) => {
      const direction = state.activitySort?.columnId === columnId
        ? state.activitySort.direction
        : "asc";
      renderApp(container, setActivitySort(state, columnId, direction), persistence);
    },
    onActivitySortDirectionToggle: () => {
      renderApp(container, toggleActivitySortDirection(state), persistence);
    },
    onP6FieldAdd: (fieldId) => mutateLayout(() => addP6Field(state, fieldId)),
    onP6FieldReorder: (orderedFieldIds) => mutateLayout(() => reorderP6Fields(state, orderedFieldIds)),
    onP6FieldWidthChange: (fieldId, width) => mutateLayout(() => updateP6FieldPresentation(state, fieldId, { width })),
    onP6FieldPresentationChange: (fieldId, patch) => mutateLayout(() => updateP6FieldPresentation(state, fieldId, patch)),
    onP6FieldVisibilityChange: (fieldId, visible) => mutateLayout(() => updateP6FieldPresentation(state, fieldId, { visible })),
    onP6FieldRemove: (fieldId) => mutateLayout(() => removeP6Field(state, fieldId)),
    onP6LayoutUndo: () => { void undoLayout(); },
    onP6LayoutRedo: () => { void redoLayout(); },
    onP6LayoutRestore: (revision) => { void restoreLayout(revision); },
    layoutHistory: historyView,
  });
  if (
    state.p6Layout
    && layoutHistory
    && layoutHistory.revisions === null
    && !layoutHistory.revisionRequest
    && !layoutHistory.revisionLoadFailed
  ) {
    void requestLayoutRevisions(state.p6Layout)
      .then(() => {
        renderApp(container, currentWorkspaceState ?? state, persistence, true);
      })
      .catch((error) => {
        console.error("P6 layout history read failed", error);
        layoutHistory.revisionLoadFailed = true;
        renderApp(container, currentWorkspaceState ?? state, persistence, true);
      });
  }
  if (layoutHistory && !preserveLayoutNotice && !layoutHistory.revisionRequest) {
    layoutHistory.noticeKey = null;
  }
  void mountScheduleCyclePanels(workspace, aiTransport, state.context, state.locale, (facts) => {
    try {
      const next = applyAuthoritativeScheduleFacts(state, facts);
      if (next !== state) renderApp(container, next, persistence);
    } catch (error) {
      console.error("Authoritative schedule result projection failed", error);
    }
  });
  mountFormulaEditorPanel(
    workspace,
    aiTransport,
    state.context,
    state.locale,
    state.p6FieldRegistry?.fields ?? [],
  );
  mountInterchangePanel(
    workspace,
    aiTransport,
    state.context,
    state.locale,
    state.activities,
  );
  mountCapacityPanel(workspace, aiTransport, state.context, state.locale);
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

  if (window.location.pathname === "/" || window.location.pathname === "/index.html") {
    renderLandingPage(container);
    return;
  }

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
