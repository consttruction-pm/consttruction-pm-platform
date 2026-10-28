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
import { getBootstrapLabels, getBootstrapErrorCopy } from "./bootstrap-labels.js";
import {
  readRequestedProjectId,
  readWorkspaceLocalePreference,
  readWorkspaceMenuPreference,
  readWorkspaceProjectPreference,
  rememberWorkspaceLocale,
  rememberWorkspaceMenu,
  rememberWorkspaceProject,
  requestedProjectHref,
} from "./workspace-preferences.js";
import { getWorkspaceShellLabels } from "./shell-labels.js";
import { renderLandingPage } from "./landing.js";
import { getAvailableWorkspaceLocales, getWorkspaceLocaleDirection, getWorkspaceLocaleDisplayName } from "./workspace-localization.js";
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

/** The next locale the shell can actually serve, never a route that does not exist. */
function nextWorkspaceLocale(locale: WorkspaceLocale): WorkspaceLocale {
  const available = getAvailableWorkspaceLocales();
  const index = available.indexOf(locale);
  return available[(index + 1) % available.length] ?? "en";
}

function applyDocumentLocale(locale: WorkspaceLocale, title?: string): void {
  document.documentElement.lang = locale;
  document.documentElement.dir = getWorkspaceLocaleDirection(locale);
  document.title = title ?? getBootstrapLabels(locale).workspaceTitle;
}

/**
 * A project choice becomes part of the address only after the server has
 * confirmed it. The address then reopens the same workspace without asking the
 * visitor to choose again, while a stale link still falls back to the project
 * selection instead of opening data the user cannot access.
 */
function rememberOpenedProject(userId: string, projectId: string): void {
  rememberWorkspaceProject(userId, projectId);
  try {
    const href = requestedProjectHref(window.location.href, projectId);
    const next = new URL(href);
    if (next.href !== window.location.href) {
      window.history.replaceState(null, "", next.href);
    }
  } catch {
    // History may be unavailable in a sandboxed frame; storage still keeps the choice.
  }
}

function applyRememberedMenu(workspace: WorkspaceState): WorkspaceState {
  const menu = readWorkspaceMenuPreference();
  return menu ? { ...workspace, activeMenu: menu } : workspace;
}

function createLanguageSwitch(
  locale: WorkspaceLocale,
  onSelect: (locale: WorkspaceLocale) => void,
): HTMLButtonElement {
  const t = getBootstrapLabels(locale);
  const next = nextWorkspaceLocale(locale);
  const nextName = getWorkspaceLocaleDisplayName(next);
  const button = document.createElement("button");
  button.type = "button";
  button.className = "cp-bootstrap-language";
  button.dataset.bootstrapLanguage = next;
  button.lang = next;
  button.dir = getWorkspaceLocaleDirection(next);
  button.textContent = nextName;
  button.setAttribute("aria-label", t.switchLanguage.replace("{language}", nextName));
  button.addEventListener("click", () => onSelect(next));
  return button;
}

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
  // The workspace language belongs to the document, not only to the panels:
  // assistive technology, the floating assistant and every CSS logical direction
  // read it from the root element.
  applyDocumentLocale(state.locale);
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
  languageButton.setAttribute(
    "aria-label",
    getBootstrapLabels(state.locale).switchLanguage.replace(
      "{language}",
      getWorkspaceLocaleDisplayName(nextLocale),
    ),
  );
  languageButton.onclick = () => {
    const next: WorkspaceLocale = nextLocale;
    rememberWorkspaceLocale(next, availableLocales);
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
  const reportWbsMutationError = (error: unknown): void => {
    console.error("WBS mutation failed", error);
    const message = error instanceof Error ? error.message : "WBS_MUTATION_FAILED";
    const currentStatus = container.querySelector<HTMLElement>(".cp-app-status");
    const panel = container.querySelector<HTMLElement>("#cp-project-wbs");
    if (panel) {
      let notice = panel.querySelector<HTMLElement>("[data-wbs-error]");
      if (!notice) { notice = document.createElement("p"); notice.dataset.wbsError = "true"; notice.setAttribute("role", "alert"); panel.append(notice); }
      notice.textContent = message;
    }
    if (currentStatus) currentStatus.dataset.wbsError = message;
  };
  const refreshWorkspaceAfterWbsMutation = async (selectedWbsId: string | null): Promise<void> => {
    const refreshed = await new WorkspaceReadClient(aiTransport).load(state.context, {
      locale: state.locale,
      calendarMode: state.calendarMode,
    });
    if (!refreshed.ok) throw new Error(refreshed.error.code);
    let nextState = await loadP6Presentation(refreshed.data, aiTransport, state.context);
    if (selectedWbsId && nextState.wbsNodes.some((node) => node.id === selectedWbsId)) {
      nextState = selectWbs(nextState, selectedWbsId);
    }
    renderApp(container, nextState, persistence);
  };
  const projectWbsPath = (wbsId?: string): string =>
    `/api/projects/${encodeURIComponent(state.context.project_id)}/p6/wbs${wbsId ? `/${encodeURIComponent(wbsId)}` : ""}`;
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
      rememberWorkspaceMenu(menu);
      renderApp(container, { ...state, activeMenu: menu }, persistence);
    },
    onWbsSelect: (wbsId) => {
      renderApp(container, selectWbs(state, wbsId), persistence);
    },
    onWbsCreate: async (input) => {
      try {
        const parent = input.parentWbsId && input.parentWbsId !== "__project__" ? state.wbsNodes.find((node) => node.id === input.parentWbsId) : null;
        const response = await aiTransport.post<
          { wbs_id: string; parent_kind: "project" | "wbs"; parent_wbs_id: string | null; code: string; name: string; sequence_number: number },
          { wbs: { wbs_id: string } }
        >(projectWbsPath(), {
          wbs_id: `WBS-${Date.now().toString(36).toUpperCase()}-${Math.random().toString(36).slice(2, 8).toUpperCase()}`,
          parent_kind: parent ? "wbs" : "project",
          parent_wbs_id: parent?.id ?? null,
          code: input.code,
          name: input.name,
          sequence_number: input.sequenceNumber,
        }, state.context);
        if (!response.ok) throw new Error(response.error.code);
        await refreshWorkspaceAfterWbsMutation(response.data.wbs.wbs_id);
      } catch (error) {
        reportWbsMutationError(error);
      }
    },
    onWbsUpdate: async (wbsId, input) => {
      try {
        const node = state.wbsNodes.find((item) => item.id === wbsId);
        if (!node) throw new Error("WBS_NOT_FOUND");
        if (!aiTransport.patch) throw new Error("PATCH_TRANSPORT_UNAVAILABLE");
        const response = await aiTransport.patch<
          { expected_revision: number; parent_kind: "project" | "wbs"; parent_wbs_id: string | null; code: string; name: string; sequence_number: number },
          unknown
        >(projectWbsPath(wbsId), {
          expected_revision: node.recordRevision,
          parent_kind: node.parentKind,
          parent_wbs_id: node.parentWbsId,
          code: input.code,
          name: input.name,
          sequence_number: input.sequenceNumber,
        }, state.context);
        if (!response.ok) throw new Error(response.error.code);
        await refreshWorkspaceAfterWbsMutation(wbsId);
      } catch (error) {
        reportWbsMutationError(error);
      }
    },
    onWbsDelete: async (wbsId) => {
      if (!wbsId) return;
      try {
        const node = state.wbsNodes.find((item) => item.id === wbsId);
        if (!node) throw new Error("WBS_NOT_FOUND");
        if (!aiTransport.delete) throw new Error("DELETE_TRANSPORT_UNAVAILABLE");
        const response = await aiTransport.delete<{ expected_revision: number }, unknown>(
          projectWbsPath(wbsId), { expected_revision: node.recordRevision }, state.context,
        );
        if (!response.ok) throw new Error(response.error.code);
        await refreshWorkspaceAfterWbsMutation(null);
      } catch (error) {
        reportWbsMutationError(error);
      }
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
  applyDocumentLocale(locale);
  const t = getBootstrapLabels(locale);
  if (state.status === "ready") {
    // The server confirmed this context, so it is safe to remember it and to
    // reopen the same project and menu after a refresh.
    rememberOpenedProject(state.userId, state.context.project_id);
    renderApp(container, applyRememberedMenu(state.workspace));
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
    loading.setAttribute("role", "status");
    loading.setAttribute("aria-live", "polite");
    loading.append(createBootstrapHeader(locale, (next) => {
      rememberWorkspaceLocale(next, getAvailableWorkspaceLocales());
      renderBootstrapState(container, state, bootstrap, next);
    }, t.workspaceTitle));
    const text = document.createElement("p");
    text.textContent = message;
    loading.append(text);
    container.append(loading);
    return;
  }

  const renderWithLocale = (next: WorkspaceLocale): void => {
    const available = getAvailableWorkspaceLocales();
    rememberWorkspaceLocale(next, available);
    renderBootstrapState(container, state, bootstrap, next);
  };

  const page = document.createElement("main");
  page.dir = getWorkspaceLocaleDirection(locale);
  page.className = state.status === "empty" || state.status === "selecting"
    ? "cp-project-selection"
    : "cp-shell-error";
  page.append(createBootstrapHeader(locale, renderWithLocale, t.workspaceTitle));

  const appendCreateProjectForm = (): void => {
    const idSuffix = state.status;
    const hintId = `cp-project-name-hint-${idSuffix}`;
    const errorId = `cp-project-name-error-${idSuffix}`;

    const section = document.createElement("section");
    section.className = "cp-project-create";

    const heading = document.createElement("h2");
    heading.textContent = t.createProject;
    section.append(heading);

    const form = document.createElement("form");
    form.className = "cp-project-create-form";
    form.noValidate = true;

    const label = document.createElement("label");
    label.textContent = t.projectName;
    const input = document.createElement("input");
    input.name = "projectName";
    input.id = "cp-project-name";
    input.type = "text";
    input.required = true;
    input.minLength = 2;
    input.maxLength = 120;
    input.autocomplete = "organization";
    input.placeholder = t.projectNamePlaceholder;
    input.setAttribute("aria-describedby", `${hintId} ${errorId}`);
    label.append(input);

    const hint = document.createElement("small");
    hint.id = hintId;
    hint.className = "cp-form-hint";
    hint.textContent = t.projectNameHint;

    const errorMessage = document.createElement("p");
    errorMessage.id = errorId;
    errorMessage.className = "cp-form-error";
    errorMessage.setAttribute("role", "alert");
    errorMessage.hidden = true;

    const showError = (message: string): void => {
      errorMessage.textContent = message;
      errorMessage.hidden = false;
      input.setAttribute("aria-invalid", "true");
    };
    const clearError = (): void => {
      errorMessage.hidden = true;
      errorMessage.textContent = "";
      input.removeAttribute("aria-invalid");
    };

    form.append(label, hint, errorMessage);

    const submit = document.createElement("button");
    submit.type = "submit";
    submit.textContent = t.createAndOpen;
    form.append(submit);

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      clearError();
      const name = input.value.trim();
      if (!name) {
        showError(t.validationNameRequired);
        input.focus();
        return;
      }
      if (name.length < 2 || name.length > 120) {
        showError(t.validationNameLength);
        input.focus();
        return;
      }
      submit.disabled = true;
      input.disabled = true;
      submit.textContent = t.creating;
      form.setAttribute("aria-busy", "true");
      const next = await bootstrap.createProject(createProjectId(), name, locale);
      form.removeAttribute("aria-busy");
      if (!next) return;
      if (next.status === "ready") {
        renderBootstrapState(container, next, bootstrap, locale);
        return;
      }
      submit.disabled = false;
      input.disabled = false;
      submit.textContent = t.createAndOpen;
      if (next.status === "error") {
        const copy = getBootstrapErrorCopy(locale, next.error);
        showError(`${t.createFailed} (${copy.reference})`);
        input.focus();
        return;
      }
      renderBootstrapState(container, next, bootstrap, locale);
    });

    section.append(form);
    page.append(section);
  };

  if (state.status === "empty" || (state.status === "error" && state.error.code === "NO_PROJECTS_AVAILABLE")) {
    const heading = document.createElement("h1");
    heading.textContent = t.createFirstProject;
    page.append(heading);

    const message = document.createElement("p");
    message.textContent = t.noProjects;
    page.append(message);

    appendCreateProjectForm();
    container.append(page);
    return;
  }

  if (state.status === "selecting") {
    const heading = document.createElement("h1");
    heading.textContent = t.selectProject;
    page.append(heading);

    const description = document.createElement("p");
    description.textContent = t.selectProjectDescription;
    page.append(description);

    const list = document.createElement("div");
    list.className = "cp-project-list";
    list.setAttribute("role", "list");
    list.setAttribute("aria-label", t.projectListAria);

    for (const project of state.projects) {
      const button = document.createElement("button");
      button.type = "button";
      button.setAttribute("role", "listitem");
      button.className = "cp-project-option";
      button.dataset.projectId = project.project_id;
      const name = document.createElement("strong");
      name.textContent = project.name;
      const revision = document.createElement("span");
      revision.textContent = `R${project.revision}`;
      button.append(name, revision);
      button.addEventListener("click", async () => {
        list.querySelectorAll("button").forEach((item) => { item.disabled = true; });
        button.setAttribute("aria-busy", "true");
        const next = await bootstrap.selectProject(project.project_id, locale);
        if (next) renderBootstrapState(container, next, bootstrap, locale);
      });
      list.append(button);
    }

    page.append(list);
    appendCreateProjectForm();
    container.append(page);
    return;
  }

  const error = state.status === "error" ? state.error : null;
  if (!error) {
    container.append(page);
    return;
  }
  const copy = getBootstrapErrorCopy(locale, error);

  const heading = document.createElement("h1");
  heading.textContent = copy.title;
  page.append(heading);

  const message = document.createElement("p");
  message.className = "cp-error-message";
  message.textContent = copy.message;
  page.append(message);

  const reference = document.createElement("p");
  reference.className = "cp-error-reference";
  reference.append(document.createTextNode(`${t.errorReference}: `));
  const code = document.createElement("code");
  code.textContent = copy.reference;
  reference.append(code);
  page.append(reference);

  const actions = document.createElement("div");
  actions.className = "cp-error-actions";

  const retryStart = async (): Promise<void> => {
    renderBootstrapState(container, { status: "loading" }, bootstrap, locale);
    const next = await bootstrap.start(readRequestedProjectId(window.location.search), locale);
    if (next) renderBootstrapState(container, next, bootstrap, locale);
  };

  if (error.available_actions.includes("retry") || error.retryable) {
    const retry = document.createElement("button");
    retry.type = "button";
    retry.textContent = t.retry;
    retry.addEventListener("click", () => { void retryStart(); });
    actions.append(retry);
  }

  if (error.available_actions.includes("refresh")) {
    const refresh = document.createElement("button");
    refresh.type = "button";
    refresh.textContent = t.refresh;
    refresh.addEventListener("click", () => { void retryStart(); });
    actions.append(refresh);
  }

  page.append(actions);
  container.append(page);
}

function createBootstrapHeader(
  locale: WorkspaceLocale,
  onLocaleChange: (locale: WorkspaceLocale) => void,
  title: string,
): HTMLElement {
  const header = document.createElement("header");
  header.className = "cp-bootstrap-bar";

  const brand = document.createElement("a");
  brand.className = "cp-bootstrap-brand";
  brand.href = publicHomeHref();
  brand.textContent = "CUBI";
  brand.setAttribute("aria-label", "CUBI Platform");
  brand.title = title;

  header.append(brand, createLanguageSwitch(locale, onLocaleChange));
  return header;
}

function publicHomeHref(): string {
  const path = window.location.pathname.replace(/\/?app(?:\/index\.html)?\/?$/, "/");
  return path || "/";
}

function createProjectId(): string {
  try {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
      return crypto.randomUUID();
    }
  } catch {
    // Fall through to a time-based id when the crypto API is unavailable.
  }
  return `project-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function getInitialLocale(): WorkspaceLocale {
  const available = getAvailableWorkspaceLocales();
  const remembered = readWorkspaceLocalePreference(available);
  if (remembered) return remembered;
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
    preferredProjectIdForUser: (userId) => readWorkspaceProjectPreference(userId),
  });

  const initialLocale = getInitialLocale();
  renderBootstrapState(container, { status: "loading" }, bootstrap, initialLocale);

  try {
    const state = await bootstrap.start(
      readRequestedProjectId(window.location.search),
      initialLocale,
    );
    if (state) renderBootstrapState(container, state, bootstrap, initialLocale);
  } catch (error) {
    const locale = getInitialLocale();
    const t = getBootstrapLabels(locale);
    applyDocumentLocale(locale);
    container.innerHTML = `<main class="cp-shell-error" dir="${getWorkspaceLocaleDirection(locale)}"><h1>${t.errorTitle}</h1><p>${t.unableToInitialize}</p></main>`;
    console.error(error);
  }
}

void boot();
