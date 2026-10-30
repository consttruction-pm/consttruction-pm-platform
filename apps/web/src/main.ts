import { FetchApiTransport, type ProjectContext } from "./client.js";
import { createP6LayoutPersistence, loadP6LayoutRevisions, loadP6Presentation } from "./p6-api.js";
import type { LayoutDefinition } from "./p6-field-layout-foundation.js";
import { ProjectBootstrap, type ProjectBootstrapState } from "./project-bootstrap.js";
import { FetchSessionApi, type ProjectSummary } from "./session-api.js";
import { WebSyncRuntime } from "./sync-runtime.js";
import { WorkspaceReadClient } from "./workspace-read-api.js";
import {
  addP6Field,
  applyAuthoritativeScheduleFacts,
  removeP6Field,
  reorderP6Fields,
  setActivityFilter,
  setActivityGroupBy,
  setActivitySort,
  toggleActivitySortDirection,
  updateP6FieldPresentation,
  selectActivity,
  selectWbs,
  setP6Presentation,
  setLocale,
  setCalendarMode,
  setGanttScale,
  setGanttRelationshipsVisible,
  type WorkspaceLocale,
  type WorkspaceState,
} from "./workspace-model.js";
import { renderMainWorkspace } from "./workspace-view.js";
import { renderWorkspaceStartup } from "./workspace-startup.js";
import { getBootstrapLabels, getBootstrapErrorCopy } from "./bootstrap-labels.js";
import { formatJalaliDateInput, isValidCanonicalIsoDate, parseJalaliDateInput } from "./workspace-jalali-entry.js";
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
let currentBootstrap: ProjectBootstrap | null = null;

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

function openProjectSettings(
  container: HTMLElement,
  state: WorkspaceState,
  persistence: ReturnType<typeof createP6LayoutPersistence> | undefined,
): void {
  const bootstrap = currentBootstrap;
  if (!bootstrap) return;
  const labels = getBootstrapLabels(state.locale);
  container.querySelector<HTMLElement>("[data-project-settings-panel]")?.remove();

  const panel = document.createElement("section");
  panel.className = "cp-project-settings-panel";
  panel.dataset.projectSettingsPanel = "true";
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-modal", "true");
  panel.setAttribute("aria-label", labels.settingsTitle);

  const heading = document.createElement("h2");
  heading.textContent = labels.settingsTitle;
  const close = document.createElement("button");
  close.type = "button";
  close.className = "cp-project-settings-close";
  close.dataset.projectSettingsClose = "true";
  close.textContent = labels.settingsClose;
  close.addEventListener("click", () => panel.remove());

  const revision = document.createElement("p");
  revision.className = "cp-project-settings-revision";
  revision.dataset.projectSettingsRevision = "true";

  const status = document.createElement("p");
  status.className = "cp-project-settings-status";
  status.dataset.projectSettingsStatus = "true";
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");

  const setStatus = (text: string, kind: "info" | "success" | "error" | "conflict"): void => {
    status.textContent = text;
    status.dataset.state = kind;
  };

  const form = document.createElement("form");
  form.dataset.projectSettingsForm = "true";
  form.noValidate = true;

  const labelled = (
    text: string,
    control: HTMLElement,
    hint?: string,
  ): HTMLElement => {
    const label = document.createElement("label");
    label.textContent = text;
    label.append(control);
    const wrapper = document.createElement("div");
    wrapper.className = "cp-project-settings-field";
    wrapper.append(label);
    if (hint) {
      const small = document.createElement("small");
      small.className = "cp-form-hint";
      small.textContent = hint;
      wrapper.append(small);
    }
    return wrapper;
  };

  const nameInput = document.createElement("input");
  nameInput.name = "name";
  nameInput.required = true;
  nameInput.minLength = 2;
  nameInput.maxLength = 120;
  nameInput.autocomplete = "organization";

  const descriptionInput = document.createElement("textarea");
  descriptionInput.name = "description";
  descriptionInput.rows = 3;
  descriptionInput.maxLength = 2000;
  descriptionInput.placeholder = labels.projectDescriptionPlaceholder;

  const startDateInput = document.createElement("input");
  startDateInput.name = "start_date";
  startDateInput.type = "date";

  const dateSystemSelect = document.createElement("select");
  dateSystemSelect.name = "date_system";
  for (const [value, text] of [
    ["gregorian", labels.dateSystemGregorian],
    ["jalali", labels.dateSystemJalali],
  ] as const) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = text;
    dateSystemSelect.append(option);
  }

  const calendarInput = document.createElement("input");
  calendarInput.name = "primary_calendar_id";
  calendarInput.maxLength = 200;
  calendarInput.autocomplete = "off";

  const save = document.createElement("button");
  save.type = "submit";
  save.dataset.projectSettingsSave = "true";
  save.textContent = labels.settingsSave;

  const retry = document.createElement("button");
  retry.type = "button";
  retry.dataset.projectSettingsRetry = "true";
  retry.textContent = labels.settingsRetry;
  retry.hidden = true;

  const reloadLatest = document.createElement("button");
  reloadLatest.type = "button";
  reloadLatest.dataset.projectSettingsReload = "true";
  reloadLatest.textContent = labels.settingsReloadLatest;
  reloadLatest.hidden = true;

  form.append(
    labelled(labels.projectName, nameInput),
    labelled(labels.projectDescription, descriptionInput, labels.projectDescriptionPlaceholder),
    labelled(labels.projectStartDate, startDateInput),
    labelled(labels.projectDateSystem, dateSystemSelect),
    labelled(labels.settingsPrimaryCalendar, calendarInput, labels.settingsPrimaryCalendarHint),
  );
  const actions = document.createElement("div");
  actions.className = "cp-project-settings-actions";
  actions.append(save, retry, reloadLatest, close);

  panel.append(heading, revision, status, form, actions);
  const shell = container.querySelector<HTMLElement>(".cp-app-shell");
  (shell ?? container).append(panel);

  let loadedRevision = state.context.revision;
  let saving = false;

  const applyLoaded = (project: ProjectSummary): void => {
    // Metadata edits use their own optimistic token; ``project.revision`` is
    // the workspace data revision that persisted rows are stamped with.
    loadedRevision = project.settings_revision ?? 0;
    nameInput.value = project.name ?? "";
    descriptionInput.value = project.description ?? "";
    startDateInput.value = project.start_date ?? "";
    dateSystemSelect.value = project.date_system === "jalali" ? "jalali" : "gregorian";
    calendarInput.value = project.primary_calendar_id ?? "";
    revision.textContent = `${labels.settingsRevision} R${loadedRevision}`;
  };

  const load = async (): Promise<void> => {
    setStatus(labels.loading, "info");
    const result = await bootstrap.loadProjectSummary(state.context.project_id);
    if (!result.ok) {
      setStatus(`${labels.settingsFailed} (${result.error.code})`, "error");
      retry.hidden = false;
      return;
    }
    applyLoaded(result.data.project);
    setStatus("", "info");
    retry.hidden = true;
  };

  const submit = async (): Promise<void> => {
    if (saving) return;
    const name = nameInput.value.trim();
    if (name.length < 2 || name.length > 120) {
      setStatus(labels.validationNameLength, "error");
      nameInput.focus();
      return;
    }
    if (descriptionInput.value.length > 2000) {
      setStatus(labels.settingsFailed, "error");
      descriptionInput.focus();
      return;
    }
    const startDate = startDateInput.value.trim();
    if (startDate && !/^\d{4}-\d{2}-\d{2}$/.test(startDate)) {
      setStatus(labels.settingsFailed, "error");
      startDateInput.focus();
      return;
    }
    saving = true;
    save.disabled = true;
    retry.hidden = true;
    reloadLatest.hidden = true;
    save.textContent = labels.settingsSaving;
    setStatus(labels.settingsSaving, "info");
    const result = await bootstrap.saveProjectMetadata(
      state.context.project_id,
      {
        name,
        description: descriptionInput.value.trim(),
        start_date: startDate || null,
        date_system: dateSystemSelect.value === "jalali" ? "jalali" : "gregorian",
        primary_calendar_id: calendarInput.value.trim() || null,
      },
      loadedRevision,
    );
    saving = false;
    save.disabled = false;
    save.textContent = labels.settingsSave;
    if (result.ok) {
      applyLoaded(result.data.project);
      setStatus(
        `${labels.settingsSaved} R${result.data.project.settings_revision ?? 0}.`,
        "success",
      );
      const latest = currentWorkspaceState;
      if (latest) {
        const next = {
          ...latest,
          context: { ...latest.context, revision: result.data.project.revision },
        };
        renderApp(container, next, persistence);
      }
      return;
    }
    if (result.error.code === "PROJECT_REVISION_CONFLICT") {
      setStatus(labels.settingsConflict, "conflict");
      reloadLatest.hidden = false;
      return;
    }
    if (result.error.code.includes("project.admin")) {
      setStatus(labels.settingsForbidden, "error");
      return;
    }
    if (result.error.code === "PROJECT_START_DATE_INVALID" || result.error.code === "PROJECT_DESCRIPTION_TOO_LONG") {
      setStatus(labels.settingsFailed, "error");
      return;
    }
    setStatus(`${labels.settingsFailed} (${result.error.code})`, "error");
    retry.hidden = false;
  };

  retry.addEventListener("click", () => { void submit(); });
  reloadLatest.addEventListener("click", () => { void load(); });
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    void submit();
  });

  void load();
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
  const reportRelationshipError = (error: unknown): void => {
    console.error("Relationship mutation failed", error);
    const message = error instanceof Error ? error.message : "RELATIONSHIP_MUTATION_FAILED";
    const panel = container.querySelector<HTMLElement>("#cp-logic");
    if (panel) {
      let notice = panel.querySelector<HTMLElement>("[data-relationship-error]");
      if (!notice) { notice = document.createElement("p"); notice.dataset.relationshipError = "true"; notice.setAttribute("role", "alert"); panel.prepend(notice); }
      notice.textContent = message;
    }
    const currentStatus = container.querySelector<HTMLElement>(".cp-app-status");
    if (currentStatus) currentStatus.dataset.relationshipError = message;
  };
  const refreshWorkspaceAfterWbsMutation = async (selectedWbsId: string | null): Promise<void> => {    const refreshed = await new WorkspaceReadClient(aiTransport).load(state.context, {
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
    {
      // Execution writes through the authoritative API; the grid and Gantt must
      // show that persisted result instead of leaving the pre-execution view.
      onExecuted: async () => { await refreshWorkspaceAfterWbsMutation(null); },
    },
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
    onActivityCreate: async (input) => {
      try {
        const response = await aiTransport.post<
          { contract_version: string; activity_id: string; name: string; duration_value: number; duration_unit: string; wbs_id: string; activity_type: string; status: string; status_code: string; percent_complete_type: string; leveling_priority: string },
          { activity: { activity_id: string } }
        >(`/api/projects/${encodeURIComponent(state.context.project_id)}/p6/activities`, {
          contract_version: "p6-activity-master-api.v1",
          activity_id: input.activityId,
          name: input.name,
          duration_value: input.durationValue,
          duration_unit: input.durationUnit,
          wbs_id: input.wbsId,
          activity_type: input.activityType,
          status: input.status,
          status_code: input.statusCode,
          percent_complete_type: input.percentCompleteType,
          leveling_priority: input.levelingPriority,
        }, state.context);
        if (!response.ok) throw new Error(response.error.code);
        await refreshWorkspaceAfterWbsMutation(input.wbsId);
      } catch (error) {
        console.error("Activity creation failed", error);
        const message = error instanceof Error ? error.message : "ACTIVITY_CREATE_FAILED";
        const panel = container.querySelector<HTMLElement>("#cp-activity-grid");
        if (panel) {
          let notice = panel.querySelector<HTMLElement>("[data-activity-error]");
          if (!notice) { notice = document.createElement("p"); notice.dataset.activityError = "true"; notice.setAttribute("role", "alert"); panel.prepend(notice); }
          notice.textContent = message;
        }
      }
    },
    onRelationshipCreate: async (input) => {
      try {
        const response = await aiTransport.post<
          { relationship_id: string; predecessor_id: string; successor_id: string; relationship_type: string; lag_value: string; lag_unit: string },
          { relationship: { relationship_id: string } }
        >(`/api/projects/${encodeURIComponent(state.context.project_id)}/p6/relationships`, {
          relationship_id: `REL-${Date.now().toString(36).toUpperCase()}-${Math.random().toString(36).slice(2, 8).toUpperCase()}`,
          predecessor_id: input.predecessorId,
          successor_id: input.successorId,
          relationship_type: input.type,
          lag_value: input.lagValue,
          lag_unit: input.lagUnit,
        }, state.context);
        if (!response.ok) throw new Error(response.error.code);
        await refreshWorkspaceAfterWbsMutation(state.selectedWbsId);
      } catch (error) {
        reportRelationshipError(error);
      }
    },
    onRelationshipDelete: async (relationshipId, recordRevision) => {
      try {
        if (!aiTransport.delete) throw new Error("DELETE_TRANSPORT_UNAVAILABLE");
        const response = await aiTransport.delete<{ expected_revision: number }, unknown>(
          `/api/projects/${encodeURIComponent(state.context.project_id)}/p6/relationships/${encodeURIComponent(relationshipId)}`,
          { expected_revision: recordRevision }, state.context,
        );
        if (!response.ok) throw new Error(response.error.code);
        await refreshWorkspaceAfterWbsMutation(state.selectedWbsId);
      } catch (error) {
        reportRelationshipError(error);
      }
    },
    onActivityEdit: async (activityId) => {
      const panel = container.querySelector<HTMLElement>("#cp-activity-grid");
      if (!panel) return;
      try {
        const response = await aiTransport.get<{
          activity: {
            activity_id: string;
            name: string;
            duration_value: string | number;
            duration_unit: string;
            wbs_id: string | null;
            record_revision: number;
          };
        }>(`/api/projects/${encodeURIComponent(state.context.project_id)}/p6/activities/${encodeURIComponent(activityId)}`, state.context);
        if (!response.ok) throw new Error(response.error.code);
        const activity = response.data.activity;
        const old = panel.querySelector<HTMLElement>("[data-activity-update-form]");
        old?.remove();
        const form = document.createElement("form");
        form.dataset.activityUpdateForm = activity.activity_id;
        form.setAttribute("aria-label", state.locale === "fa" ? "ویرایش فعالیت" : "Edit activity");
        form.innerHTML = "";
        const heading = document.createElement("h3");
        heading.textContent = state.locale === "fa" ? "ویرایش فعالیت" : "Edit activity";
        form.append(heading);
        const addInput = (name: string, labelText: string, value: string, type = "text") => {
          const label = document.createElement("label");
          label.append(document.createTextNode(labelText + " "));
          const input = document.createElement("input");
          input.name = name;
          input.type = type;
          input.value = value;
          input.required = true;
          if (name === "duration_value") { input.min = "0"; input.step = "any"; }
          if (name === "name") input.maxLength = 180;
          label.append(input);
          form.append(label);
        };
        const isFa = state.locale === "fa";
        addInput("name", isFa ? "نام فعالیت" : "Activity name", activity.name);
        addInput("duration_value", isFa ? "مدت" : "Duration", String(activity.duration_value), "number");
        const unitLabel = document.createElement("label");
        unitLabel.append(document.createTextNode((isFa ? "واحد مدت" : "Duration unit") + " "));
        const unit = document.createElement("select");
        unit.name = "duration_unit";
        for (const [value, labelText] of [["working-day", isFa ? "روز کاری" : "Working day"], ["working-hour", isFa ? "ساعت کاری" : "Working hour"]] as const) {
          const option = document.createElement("option");
          option.value = value;
          option.textContent = labelText;
          option.selected = activity.duration_unit === value;
          unit.append(option);
        }
        unitLabel.append(unit);
        form.append(unitLabel);
        const wbsLabel = document.createElement("label");
        wbsLabel.append(document.createTextNode("WBS "));
        const wbsSelect = document.createElement("select");
        wbsSelect.name = "wbs_id";
        wbsSelect.required = true;
        for (const node of state.wbsNodes) {
          const option = document.createElement("option");
          option.value = node.id;
          option.textContent = node.localCode + " — " + node.name;
          option.selected = node.id === activity.wbs_id;
          wbsSelect.append(option);
        }
        wbsLabel.append(wbsSelect);
        form.append(wbsLabel);
        const save = document.createElement("button");
        save.type = "submit";
        save.textContent = isFa ? "ذخیره تغییرات" : "Save changes";
        form.append(save);
        panel.querySelector("[data-activity-create-form]")?.after(form);
        form.addEventListener("submit", async (event) => {
          event.preventDefault();
          const name = (form.elements.namedItem("name") as HTMLInputElement).value.trim();
          const durationValue = Number((form.elements.namedItem("duration_value") as HTMLInputElement).value);
          const wbsId = (form.elements.namedItem("wbs_id") as HTMLSelectElement).value;
          if (!name || !Number.isFinite(durationValue) || durationValue < 0 || !wbsId) return;
          try {
            if (!aiTransport.patch) throw new Error("PATCH_TRANSPORT_UNAVAILABLE");
            const updated = await aiTransport.patch<
              { contract_version: string; expected_revision: number; name: string; duration_value: number; duration_unit: string; wbs_id: string },
              { activity: { activity_id: string } }
            >(`/api/projects/${encodeURIComponent(state.context.project_id)}/p6/activities/${encodeURIComponent(activity.activity_id)}`, {
              contract_version: "p6-activity-master-api.v1",
              expected_revision: activity.record_revision,
              name,
              duration_value: durationValue,
              duration_unit: unit.value,
              wbs_id: wbsId,
            }, state.context);
            if (!updated.ok) throw new Error(updated.error.code);
            await refreshWorkspaceAfterWbsMutation(wbsId);
          } catch (error) {
            let notice = form.querySelector<HTMLElement>("[data-activity-error]");
            if (!notice) {
              notice = document.createElement("p");
              notice.dataset.activityError = "true";
              notice.setAttribute("role", "alert");
              form.prepend(notice);
            }
            notice.textContent = error instanceof Error ? error.message : "ACTIVITY_UPDATE_FAILED";
          }
        });
        form.querySelector<HTMLInputElement>('[name="name"]')?.focus();
      } catch (error) {
        let notice = panel.querySelector<HTMLElement>("[data-activity-error]");
        if (!notice) {
          notice = document.createElement("p");
          notice.dataset.activityError = "true";
          notice.setAttribute("role", "alert");
          panel.prepend(notice);
        }
        notice.textContent = error instanceof Error ? error.message : "ACTIVITY_LOAD_FAILED";
      }
    },
    onActivitySelect: (activityId) => {
      renderApp(container, selectActivity(state, activityId), persistence);
    },
    onGanttActivitySelect: (activityId) => {
      renderApp(container, selectActivity(state, activityId), persistence);
    },
    onGanttScaleChange: (ganttScale) => {
      renderApp(container, setGanttScale(state, ganttScale), persistence);
    },
    onGanttRelationshipsChange: (visible) => {
      renderApp(container, setGanttRelationshipsVisible(state, visible), persistence);
    },
    onProjectSettings: () => {
      openProjectSettings(container, state, persistence);
    },
    onActivityFilterChange: (filterText) => {
      renderApp(container, setActivityFilter(state, filterText), persistence);
    },
    onActivityGroupByChange: (groupBy) => {
      renderApp(container, setActivityGroupBy(state, groupBy), persistence);
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
      // A schedule query can finish after another render has replaced this
      // panel's captured state. Project the authoritative result onto the
      // latest state for the same project revision so the grid and Gantt stay
      // synchronized after repeated schedule runs.
      const latest = currentWorkspaceState;
      if (
        !latest ||
        latest.context.tenant_id !== state.context.tenant_id ||
        latest.context.project_id !== state.context.project_id ||
        latest.context.revision !== state.context.revision
      ) return;
      const next = applyAuthoritativeScheduleFacts(latest, facts);
      if (next !== latest) renderApp(container, next, persistence);
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
    currentBootstrap = bootstrap;
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

    const descriptionLabel = document.createElement("label");
    descriptionLabel.textContent = t.projectDescription;
    const descriptionInput = document.createElement("textarea");
    descriptionInput.name = "projectDescription";
    descriptionInput.id = "cp-project-description";
    descriptionInput.rows = 3;
    descriptionInput.maxLength = 2000;
    descriptionInput.placeholder = t.projectDescriptionPlaceholder;
    descriptionLabel.append(descriptionInput);

    const startDateLabel = document.createElement("label");
    startDateLabel.textContent = t.projectStartDate;
    const startDateInput = document.createElement("input");
    startDateInput.name = "projectStartDate";
    startDateInput.id = "cp-project-start-date";
    startDateInput.type = "date";
    startDateLabel.append(startDateInput);

    const dateSystemLabel = document.createElement("label");
    dateSystemLabel.textContent = t.projectDateSystem;
    const dateSystemSelect = document.createElement("select");
    dateSystemSelect.name = "projectDateSystem";
    dateSystemSelect.id = "cp-project-date-system";
    for (const [value, text] of [
      ["gregorian", t.dateSystemGregorian],
      ["jalali", t.dateSystemJalali],
    ] as const) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = text;
      dateSystemSelect.append(option);
    }
    dateSystemLabel.append(dateSystemSelect);

    const dateErrorId = `cp-project-start-date-error-${idSuffix}`;
    startDateInput.setAttribute("aria-describedby", dateErrorId);
    const dateError = document.createElement("p");
    dateError.id = dateErrorId;
    dateError.className = "cp-form-error";
    dateError.setAttribute("role", "alert");
    dateError.hidden = true;
    const showDateError = (): void => {
      dateError.textContent = t.validationStartDateInvalid;
      dateError.hidden = false;
      startDateInput.setAttribute("aria-invalid", "true");
    };
    const clearDateError = (): void => {
      dateError.hidden = true;
      dateError.textContent = "";
      startDateInput.removeAttribute("aria-invalid");
    };
    const syncStartDateInput = (): void => {
      const raw = startDateInput.value.trim();
      if (dateSystemSelect.value === "jalali") {
        const canonical = isValidCanonicalIsoDate(raw) ? raw : null;
        startDateInput.type = "text";
        startDateInput.inputMode = "numeric";
        startDateInput.placeholder = t.projectStartDateJalaliPlaceholder;
        startDateInput.value = canonical ? formatJalaliDateInput(canonical) : raw;
        clearDateError();
        return;
      }

      let canonical = raw;
      if (raw) {
        canonical = parseJalaliDateInput(raw)
          ?? (isValidCanonicalIsoDate(raw) ? raw : "");
        if (!canonical) {
          // Never discard invalid typed input by coercing it to a native date
          // field. Keep the user's value and the selected Jalali mode instead.
          dateSystemSelect.value = "jalali";
          showDateError();
          return;
        }
      }
      startDateInput.type = "date";
      startDateInput.inputMode = "";
      startDateInput.placeholder = "";
      startDateInput.value = canonical;
      clearDateError();
    };
    dateSystemSelect.addEventListener("change", syncStartDateInput);
    startDateInput.addEventListener("input", clearDateError);

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

    form.append(label, hint, descriptionLabel, startDateLabel, dateSystemLabel, dateError, errorMessage);

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
      const rawStartDate = startDateInput.value.trim();
      const selectedDateSystem = dateSystemSelect.value === "jalali" ? "jalali" : "gregorian";
      const canonicalStartDate = rawStartDate
        ? selectedDateSystem === "jalali"
          ? parseJalaliDateInput(rawStartDate)
          : isValidCanonicalIsoDate(rawStartDate) ? rawStartDate : null
        : null;
      if (rawStartDate && !canonicalStartDate) {
        showDateError();
        startDateInput.focus();
        return;
      }

      submit.disabled = true;
      input.disabled = true;
      descriptionInput.disabled = true;
      startDateInput.disabled = true;
      dateSystemSelect.disabled = true;
      submit.textContent = t.creating;
      form.setAttribute("aria-busy", "true");
      const next = await bootstrap.createProject(createProjectId(), name, locale, {
        description: descriptionInput.value.trim(),
        start_date: canonicalStartDate,
        date_system: selectedDateSystem,
      });
      form.removeAttribute("aria-busy");
      if (!next) return;
      if (next.status === "ready") {
        renderBootstrapState(container, next, bootstrap, locale);
        return;
      }
      submit.disabled = false;
      input.disabled = false;
      descriptionInput.disabled = false;
      startDateInput.disabled = false;
      dateSystemSelect.disabled = false;
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

  const startupTimer = window.setTimeout(() => {
    renderWorkspaceStartup(container, initialLocale, "slow");
  }, 20000);
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
  } finally {
    window.clearTimeout(startupTimer);
  }
}

void boot().catch((error: unknown) => {
  const container = document.getElementById("app");
  const locale = getInitialLocale();
  console.error("CUBI workspace startup failed unexpectedly", error);
  if (container) renderWorkspaceStartup(container, locale, "failed");
});
