import { FetchApiTransport, type ProjectContext } from "./client.js";
import {
  createP6FieldRegistryProvider,
  createP6LayoutPersistence,
  loadP6DefaultLayout,
  loadP6LayoutRevisions,
  loadP6Presentation,
} from "./p6-api.js";
import type { LayoutDefinition } from "./p6-field-layout-foundation.js";
import { openP6ColumnsDialog } from "./p6-columns-dialog.js";
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
  setActivitySortLevels,
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
  type WorkspaceMenuKey,
  type WorkspaceState,
} from "./workspace-model.js";
import {
  invalidateWorkspaceRender,
  isWorkspaceTopLayoutAvailable,
  isWorkspaceTraceLogicAvailable,
  readWorkspaceBottomLayout,
  readWorkspaceTopLayout,
  renderMainWorkspace,
  storeWorkspaceBottomLayout,
  storeWorkspaceTopLayout,
} from "./workspace-view.js";
import { collapseAllWbsIds, setCollapsedWbsIds } from "./workspace-wbs-display.js";
import { renderWorkspaceStartup } from "./workspace-startup.js";
import {
  getBootstrapLabels,
  getBootstrapErrorCopy,
  isSessionBootstrapError,
} from "./bootstrap-labels.js";
import { formatJalaliDateInput, isValidCanonicalIsoDate, parseJalaliDateInput } from "./workspace-jalali-entry.js";
import {
  readRequestedProjectId,
  readWorkspaceLocalePreference,
  readWorkspaceMenuPreference,
  readWorkspaceProjectPreference,
  rememberWorkspaceLocale,
  rememberWorkspaceMenu,
  rememberWorkspaceProject,
} from "./workspace-preferences.js";
import { getWorkspaceShellLabels } from "./shell-labels.js";
import { renderLandingPage } from "./landing.js";
import { getAvailableWorkspaceLocales, getWorkspaceLocaleDirection, getWorkspaceLocaleDisplayName, translateWorkspaceUiText } from "./workspace-localization.js";
import { createWorkspaceLanguageSelect } from "./workspace-language-switch.js";
import { mountAIActionPanel } from "./ai-action-panel.js";
import { mountAIAssistantChatPanel } from "./ai-assistant-chat.js";
import { mountScheduleCyclePanels } from "./schedule-cycle.js";
import { mountWorkspaceCalendarPage } from "./workspace-calendars.js";
import { mountWorkspaceAssignmentsPage } from "./workspace-assignments.js";
import { mountWorkspaceResourcesPage } from "./workspace-resources.js";
import {
  LAYOUT_SELECTION_STORAGE_PREFIX,
  layoutDisplayName,
  loadLayoutCatalog,
  mountWorkspaceLayoutSelector,
  parseLayoutSelections,
  readLayoutSelection,
  writeLayoutSelection,
  type LayoutSelection,
  type StoredLayoutScope,
} from "./workspace-layout-selector.js";
import { mountWorkspaceExpensesPage } from "./workspace-expenses.js";
import { mountWorkspaceRisksPage } from "./workspace-risks.js";
import { mountWorkspaceReportsPage } from "./workspace-reports.js";
import { mountWorkspaceAdministrationPage } from "./workspace-administration.js";
import { mountWorkspaceThresholdsPage } from "./workspace-thresholds.js";
import { mountWorkspaceIssuesPage } from "./workspace-issues.js";
import { mountWorkspaceDocumentsPage } from "./workspace-documents.js";
import { mountWorkspaceCostPage } from "./workspace-cost.js";
import { mountWorkspaceProgressPage } from "./workspace-progress.js";
import { mountWorkspaceRolesPage } from "./workspace-roles.js";
import { mountFormulaEditorPanel } from "./p6-formula-panel.js";
import { mountInterchangePanel } from "./p6-interchange-panel.js";
import { mountCapacityPanel } from "./p6-capacity-panel.js";
import { openDesktopDialog, renderDesktopShell, WINDOW_TITLES, type DesktopCommand } from "./workspace-desktop-shell.js";
import { renderStatusBar, type ChromeLayoutState } from "./workspace-chrome.js";
import { enhanceActivityDetails } from "./workspace-activity-details.js";
import { enhanceWorkspaceComments } from "./workspace-comments.js";
import { mountWorkspaceMobile } from "./workspace-mobile.js";
import { openFormBuilder, type FormBuilderHandle } from "./workspace-forms.js";
import type { DesktopLayoutPatch } from "./workspace-dialogs.js";
import {
  DEFAULT_PRESENTATION,
  normalizePresentation,
  presentationDataAvailability,
  presentationFontFamily,
  type WorkspacePresentation,
} from "./workspace-presentation.js";
import {
  closeWorkspaceWindow,
  openWorkspaceWindow,
  readWorkspaceWindows,
  rememberWorkspaceWindowOrder,
  rememberWorkspaceWindows,
} from "./workspace-windows.js";
import {
  isWorkspaceToolbarGroup,
  readHiddenToolbarGroups,
  rememberHiddenToolbarGroups,
  toggleToolbarGroup,
} from "./workspace-toolbars.js";
import {
  readWorkspaceDetailsVisible,
  rememberWorkspaceDetailsVisible,
} from "./workspace-details-preference.js";
import {
  applyWorkspaceTheme,
  isWorkspaceTheme,
  WORKSPACE_THEME_IDS,
  readWorkspaceTheme,
  rememberWorkspaceTheme,
  workspaceThemeLabels,
  type WorkspaceTheme,
} from "./workspace-theme.js";
import { liveWorkspaceProjectHref, workspaceLoginNextPath } from "./workspace-visual-demo-route.js";

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
/** Authoritative metadata of the open project, read from the session service. */
let activeProjectSummary: ProjectSummary | null = null;
let activeProjectSummaryProjectId: string | null = null;
/** Open windows and deferred focus are browser-local shell state, not project data. */
let openWindowKeys: WorkspaceMenuKey[] | null = null;
/** Signed-in user for browser-local preferences that must not leak between profiles. */
let activeWorkspaceUserId = "";
/** Roles from the authenticated session; administration menus are gated by these. */
let activeWorkspaceRoles: readonly string[] = [];
/** Active presentation skin; token-only, never part of project state. */
let activeWorkspaceTheme: WorkspaceTheme = readWorkspaceTheme();
let pendingDesktopFocusSelector: string | null = null;
let pendingDesktopAction: (() => void) | null = null;
/** Progress edits re-render the workspace; keep the edited activity selected. */
let progressSelection: string | null = null;

/**
 * Visual preferences are browser-local and deliberately outside project state:
 * they never travel to the server and never alter schedule numbers.
 */
type VisualPreferences = {
  density: ChromeLayoutState["density"];
  presentation: WorkspacePresentation;
  /** Wall-clock time of the last local edit; layout metadata carries the same stamp. */
  updatedAt: number;
};

const VISUAL_PREFERENCES_KEY = "cubi:workspace-visual-preferences";
const DEFAULT_VISUAL_PREFERENCES: VisualPreferences = { density: "compact", presentation: DEFAULT_PRESENTATION, updatedAt: 0 };

function readVisualPreferences(): VisualPreferences {
  try {
    const raw = window.localStorage.getItem(VISUAL_PREFERENCES_KEY);
    if (!raw) return DEFAULT_VISUAL_PREFERENCES;
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    // Migrate the earlier flat preference shape (rowHeight/fontSize) into the
    // presentation model without discarding the stored values.
    const legacy = parsed.presentation && typeof parsed.presentation === "object"
      ? parsed
      : {
        presentation: {
          ...DEFAULT_PRESENTATION,
          table: {
            ...DEFAULT_PRESENTATION.table,
            rowHeight: parsed.rowHeight,
            fontSize: parsed.fontSize,
          },
        },
      };
    const updatedAt = typeof parsed.updatedAt === "number" && Number.isFinite(parsed.updatedAt) ? parsed.updatedAt : 0;
    return {
      density: parsed.density === "comfortable" ? "comfortable" : "compact",
      presentation: normalizePresentation((legacy as Record<string, unknown>).presentation),
      updatedAt,
    };
  } catch {
    return DEFAULT_VISUAL_PREFERENCES;
  }
}

let visualPreferences = readVisualPreferences();

function rememberVisualPreferences(next: Omit<VisualPreferences, "updatedAt"> & { updatedAt?: number }): void {
  visualPreferences = {
    density: next.density,
    presentation: next.presentation,
    updatedAt: next.updatedAt ?? Date.now(),
  };
  try {
    window.localStorage.setItem(VISUAL_PREFERENCES_KEY, JSON.stringify(visualPreferences));
  } catch {
    // Preferences are optional; the current session keeps the value in memory.
  }
}

/**
 * The saved project layout is authoritative for presentation when it carries
 * presentation metadata. Adopting it once per layout revision keeps a reload
 * and another machine consistent without overwriting a newer local edit.
 */
let hydratedPresentationKey: string | null = null;
function hydratePresentationFromLayout(state: WorkspaceState): void {
  const layout = state.p6Layout;
  const raw = layout?.metadata?.presentation;
  if (!layout || !raw) return;
  const key = `${state.context.tenant_id}:${state.context.project_id}:${layout.revision}`;
  if (key === hydratedPresentationKey) return;
  const savedAt = typeof layout.metadata?.presentationUpdatedAt === "number"
    ? layout.metadata.presentationUpdatedAt
    : 0;
  // An older saved layout must not roll back a newer browser-local edit. A
  // layout saved before presentation stamps existed is only adopted when this
  // browser has no presentation edit of its own.
  if (savedAt < visualPreferences.updatedAt || (savedAt === 0 && visualPreferences.updatedAt > 0)) {
    hydratedPresentationKey = key;
    return;
  }
  hydratedPresentationKey = key;
  rememberVisualPreferences({
    density: visualPreferences.density,
    presentation: normalizePresentation(raw),
    updatedAt: savedAt || visualPreferences.updatedAt,
  });
}

function presentationMetadata(layout: LayoutDefinition): LayoutDefinition {
  return {
    ...layout,
    metadata: {
      ...(layout.metadata ?? {}),
      presentation: visualPreferences.presentation,
      presentationUpdatedAt: visualPreferences.updatedAt,
    },
  };
}

/**
 * Activities layout selection.
 *
 * The window shows one stored layout at a time. Choosing another one previews
 * it in place; nothing is written until Save, and Cancel puts the previous
 * stored definition back. The selection itself is a per-user preference keyed
 * by project, which is how a reload returns to the layout the user last used.
 */
let layoutPreviewBase: LayoutDefinition | null = null;
let layoutPreviewScope: StoredLayoutScope | null = null;
let layoutPreviewContextKey: string | null = null;

function layoutSelectionStorageKey(): string | null {
  return activeWorkspaceUserId ? `${LAYOUT_SELECTION_STORAGE_PREFIX}:${activeWorkspaceUserId}` : null;
}

function readStoredLayoutSelection(context: ProjectContext): LayoutSelection | null {
  const key = layoutSelectionStorageKey();
  if (!key) return null;
  try {
    return readLayoutSelection(parseLayoutSelections(window.localStorage.getItem(key)), context.tenant_id, context.project_id);
  } catch {
    return null;
  }
}

function rememberStoredLayoutSelection(context: ProjectContext, layout: LayoutDefinition): void {
  const key = layoutSelectionStorageKey();
  if (!key) return;
  try {
    const store = parseLayoutSelections(window.localStorage.getItem(key));
    window.localStorage.setItem(
      key,
      writeLayoutSelection(store, context.tenant_id, context.project_id, {
        scope: layout.scope === "user" ? "user" : "project",
        viewId: layout.view_id,
        revision: layout.revision,
      }),
    );
  } catch {
    // A browser that refuses storage simply keeps the layout for this render.
  }
}

function getOpenWindows(): WorkspaceMenuKey[] {
  if (!openWindowKeys) openWindowKeys = readWorkspaceWindows();
  return openWindowKeys;
}

function rememberOpenWindows(next: readonly WorkspaceMenuKey[]): void {
  openWindowKeys = [...next];
  rememberWorkspaceWindows(openWindowKeys);
}

/**
 * Panels mount asynchronously (schedule options, formula editor), so a command
 * that targets a control inside them may run before that control exists. Retry
 * briefly instead of failing without feedback.
 */
function focusWhenReady(selector: string, attempts = 20): void {
  window.setTimeout(() => {
    const element = document.querySelector<HTMLElement>(selector);
    if (!element) {
      if (attempts > 1) focusWhenReady(selector, attempts - 1);
      return;
    }
    element.scrollIntoView({ block: "center", inline: "nearest" });
    element.focus({ preventScroll: true });
  }, 25);
}

function openWorkspaceDrawer(container: HTMLElement, selector: string): void {
  container.querySelectorAll<HTMLElement>("[data-tools-drawer],[data-wbs-drawer],[data-nav-flyout]").forEach((drawer) => {
    drawer.hidden = drawer.matches(selector) ? false : true;
  });
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
    const href = liveWorkspaceProjectHref(window.location.href, projectId);
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
): HTMLSelectElement {
  const t = getBootstrapLabels(locale);
  const select = document.createElement("select");
  select.className = "cp-bootstrap-language";
  select.dataset.bootstrapLanguage = locale;
  select.setAttribute("aria-label", t.languageLabel);
  select.title = t.languageLabel;
  for (const available of getAvailableWorkspaceLocales()) {
    const option = document.createElement("option");
    option.value = available;
    option.lang = available;
    option.dir = getWorkspaceLocaleDirection(available);
    option.textContent = getWorkspaceLocaleDisplayName(available);
    if (available === locale) option.selected = true;
    select.append(option);
  }
  select.addEventListener("change", () => onSelect(select.value as WorkspaceLocale));
  return select;
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

let formBuilderHandle: FormBuilderHandle | null = null;

/**
 * The Form Builder is mounted inside the existing application shell as a
 * modal surface, so the P6 workspace underneath keeps its state. Every
 * template, version, submission and approval it shows comes from the server.
 */
function openFormsSurface(container: HTMLElement, state: WorkspaceState): void {
  if (formBuilderHandle?.isOpen()) {
    formBuilderHandle.close();
    return;
  }
  const host = container.querySelector<HTMLElement>(".cp-app-shell") ?? container;
  formBuilderHandle = openFormBuilder({
    host,
    context: state.context,
    locale: state.locale,
    calendarMode: state.calendarMode,
    onClose: () => {
      formBuilderHandle = null;
    },
  });
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
    activeProjectSummary = project;
    activeProjectSummaryProjectId = project.project_id;
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

type WorkspaceDraft = { key: string; value: string; checked?: boolean };

/** Stable identity for an entered value across a full locale re-render. */
function workspaceDraftKey(field: HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement): string {
  const form = field.closest("form");
  const formKey = form
    ? Array.from(form.attributes)
        .filter(({ name }) => name.startsWith("data-") && name !== "data-workspace-menu")
        .map(({ name, value }) => `${name}=${value}`)
        .join("&") || `form.${form.className}`
    : "formless";
  const base = field.name || field.id || (field.getAttribute("data-activity-filter") !== null ? "activity-filter" : "");
  const choice = field instanceof HTMLInputElement && ["checkbox", "radio"].includes(field.type) ? `=${field.value}` : "";
  return `${formKey}::${base}${choice}`;
}

/**
 * Language switching re-renders every panel. Unsaved values in filters, editors
 * and dialogs belong to the user, not to the locale, so they are captured and
 * restored instead of being silently discarded.
 */
function captureWorkspaceDrafts(container: HTMLElement): WorkspaceDraft[] {
  const drafts: WorkspaceDraft[] = [];
  container.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>(
    "input, select, textarea",
  ).forEach((field) => {
    if (field.matches("[data-workspace-language], [data-bootstrap-language]")) return;
    if (field instanceof HTMLInputElement && ["hidden", "file", "submit", "button", "reset"].includes(field.type)) return;
    const key = workspaceDraftKey(field);
    if (!key.split("::")[1]) return;
    drafts.push({
      key,
      value: field.value,
      checked: field instanceof HTMLInputElement && ["checkbox", "radio"].includes(field.type) ? field.checked : undefined,
    });
  });
  return drafts;
}

function restoreWorkspaceDrafts(container: HTMLElement, drafts: readonly WorkspaceDraft[]): void {
  const remaining = new Map(drafts.map((draft) => [draft.key, draft]));
  container.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>(
    "input, select, textarea",
  ).forEach((field) => {
    if (field.matches("[data-workspace-language], [data-bootstrap-language]")) return;
    const draft = remaining.get(workspaceDraftKey(field));
    if (!draft) return;
    field.value = draft.value;
    if (draft.checked !== undefined && field instanceof HTMLInputElement) field.checked = draft.checked;
    // The reference search narrows already rendered entries in place, so it
    // needs its handler to run again. The activity filter is part of the
    // workspace state and is already applied by the render itself.
    if (field.matches("[data-reference-search-input]")) {
      field.dispatchEvent(new Event("input", { bubbles: true }));
    }
  });
}

/**
 * Unsaved in-progress edits in the rendered workspace: an open settings panel,
 * an inline activity editor, or typed-but-unsubmitted create/edit values.
 */
function workspaceHasPendingEdits(container: HTMLElement): boolean {
  if (container.querySelector("[data-project-settings-panel]")) return true;
  if (container.querySelector("[data-activity-update-form]")) return true;
  const entered = container.querySelectorAll<HTMLInputElement>(
    "[data-activity-create-form] input, [data-wbs-create-form] input, [data-wbs-edit-form] input",
  );
  return Array.from(entered).some((input) => input.value.trim().length > 0);
}

/**
 * The dirty marker belongs to the active tab only: other windows keep their
 * saved state, and switching away does not pretend they hold unsaved edits.
 */
function syncWindowDirtyIndicator(container: HTMLElement): void {
  const dirty = workspaceHasPendingEdits(container);
  for (const tab of container.querySelectorAll<HTMLElement>("[data-window-tab]")) {
    const value = dirty && tab.classList.contains("is-active");
    tab.classList.toggle("is-dirty", value);
    if (value) tab.setAttribute("data-window-dirty", "true");
    else tab.removeAttribute("data-window-dirty");
  }
}

function bindWindowDirtyIndicators(container: HTMLElement): void {
  if (container.dataset.dirtyIndicators === "bound") return;
  container.dataset.dirtyIndicators = "bound";
  const sync = (): void => syncWindowDirtyIndicator(container);
  container.addEventListener("input", sync);
  container.addEventListener("change", sync);
}

/**
 * Renders that are not initiated by the field owner (locale switch, async
 * layout history, authoritative schedule projection) must not discard values
 * the user has already entered but not submitted.
 */
function renderAppPreservingDrafts(
  container: HTMLElement,
  state: WorkspaceState,
  persistence?: ReturnType<typeof createP6LayoutPersistence>,
  preserveLayoutNotice = false,
): void {
  const drafts = captureWorkspaceDrafts(container);
  renderApp(container, state, persistence, preserveLayoutNotice);
  restoreWorkspaceDrafts(container, drafts);
}

function renderApp(
  container: HTMLElement,
  state: WorkspaceState,
  p6Persistence?: ReturnType<typeof createP6LayoutPersistence>,
  preserveLayoutNotice = false,
): void {
  // The bottom Details pane keeps its own per-user, per-window visibility
  // preference. Applying it before the first paint keeps the layout from
  // flashing a pane the user previously hid (and the reverse on restore).
  if (activeWorkspaceUserId) {
    const storedDetailsVisible = readWorkspaceDetailsVisible(state, activeWorkspaceUserId);
    if (storedDetailsVisible !== null && storedDetailsVisible !== state.visiblePanels.details) {
      state = { ...state, visiblePanels: { ...state.visiblePanels, details: storedDetailsVisible } };
    }
  }
  currentWorkspaceState = state;
  bindWindowDirtyIndicators(container);
  // The skin is a token set on the document root; applying it before paint
  // avoids a flash of the other theme and keeps both themes on one DOM.
  applyWorkspaceTheme(activeWorkspaceTheme);
  // Apply saved layout presentation before the chrome and grid read it.
  hydratePresentationFromLayout(state);
  // The workspace language belongs to the document, not only to the panels:
  // assistive technology, the floating assistant and every CSS logical direction
  // read it from the root element.
  applyDocumentLocale(state.locale);
  const shellLabels = getWorkspaceShellLabels(state.locale);
  const persistence = p6Persistence ?? createP6LayoutPersistence(new FetchApiTransport(window.location.origin), state.context);

  let appShell = container.querySelector<HTMLElement>(".cp-app-shell");
  let status = container.querySelector<HTMLElement>(".cp-app-status");
  let desktopHost = container.querySelector<HTMLElement>("[data-desktop-host]");
  let desktopStatus = container.querySelector<HTMLElement>("[data-desktop-status]");
  let workspace = container.querySelector<HTMLElement>("#workspace");

  if (!appShell || !status || !workspace || !desktopHost || !desktopStatus) {
    container.innerHTML = '<div class="cp-app-shell cp-p6"><div class="cp-app-status"></div><div class="cp-desktop-host" data-desktop-host></div><div id="workspace"></div><div class="cp-desktop-status" data-desktop-status></div></div>';
    appShell = container.querySelector<HTMLElement>(".cp-app-shell");
    status = container.querySelector<HTMLElement>(".cp-app-status");
    desktopHost = container.querySelector<HTMLElement>("[data-desktop-host]");
    desktopStatus = container.querySelector<HTMLElement>("[data-desktop-status]");
    workspace = container.querySelector<HTMLElement>("#workspace");
  }

  if (!appShell || !status || !workspace || !desktopHost || !desktopStatus) throw new Error("WORKSPACE_ROOT_NOT_FOUND");
  appShell.classList.add("cp-p6");
  mountWorkspaceMobile(container, state.locale);
  // The inline activity editor is created on demand. A background render (layout
  // history, authoritative schedule facts) must not close it under the user's
  // hands, so the same live form node is reattached after the workspace render.
  const activityEditor = container.querySelector<HTMLFormElement>("form[data-activity-update-form]");
  const activityEditorId = activityEditor?.dataset.activityUpdateForm ?? null;

  const availableLocales = getAvailableWorkspaceLocales();
  const changeLocale = (nextLocale: WorkspaceLocale): void => {
    if (!availableLocales.includes(nextLocale) || nextLocale === state.locale) return;
    rememberWorkspaceLocale(nextLocale, availableLocales);
    renderAppPreservingDrafts(container, setLocale(state, nextLocale), persistence);
  };

  const setDetailsVisible = (visible: boolean): void => {
    if (visible && state.activeMenu === "schedule" && readWorkspaceBottomLayout(state) === "none") {
      // Showing the pane again restores the Activity Details surface instead of
      // leaving the "Show on Bottom: None" preference in force.
      storeWorkspaceBottomLayout(state, "details");
    }
    if (activeWorkspaceUserId) rememberWorkspaceDetailsVisible(state, activeWorkspaceUserId, visible);
    renderApp(
      container,
      { ...state, visiblePanels: { ...state.visiblePanels, details: visible } },
      persistence,
    );
  };

  // Switching skins only changes the central token set. It does not re-render
  // the project, so the active window, selection, columns, filters, Gantt
  // viewport and Details state stay exactly as they were.
  const setTheme = (theme: WorkspaceTheme): void => {
    activeWorkspaceTheme = theme;
    rememberWorkspaceTheme(theme);
    applyWorkspaceTheme(theme);
    const select = status?.querySelector<HTMLSelectElement>("[data-workspace-theme]");
    if (select) select.value = theme;
    container.querySelectorAll<HTMLElement>("[data-desktop-item^='view.theme-']").forEach((item) => {
      item.setAttribute("aria-checked", String(item.dataset.desktopItem === `view.theme-${theme}`));
    });
  };

  const nextCalendarMode = state.calendarMode === "jalali" ? "gregorian" : "jalali";
  const calendarButton = document.createElement("button");
  calendarButton.type = "button";
  calendarButton.dataset.calendarMode = nextCalendarMode;
  calendarButton.textContent = state.calendarMode === "jalali"
    ? translateWorkspaceUiText(state.locale, "Gregorian", "میلادی")
    : translateWorkspaceUiText(state.locale, "Jalali", "شمسی");
  const calendarLabel = nextCalendarMode === "jalali" ? shellLabels.switchToJalali : shellLabels.switchToGregorian;
  calendarButton.setAttribute("aria-label", calendarLabel);
  calendarButton.setAttribute("title", calendarLabel);
  const toggleCalendar = (): void => {
    renderApp(container, setCalendarMode(state, nextCalendarMode), persistence);
  };
  calendarButton.onclick = toggleCalendar;
  // The bottom bar owns the global Details switch. It shares the exact state
  // and command as View > Show/Hide Details, so both entry points agree and
  // the toggle survives navigation through the per-user window preference.
  const detailsVisible = state.visiblePanels.details;
  const detailsButton = document.createElement("button");
  detailsButton.type = "button";
  detailsButton.className = `cp-details-toggle${detailsVisible ? " is-active" : ""}`;
  detailsButton.dataset.detailsToggle = "true";
  detailsButton.dataset.detailsVisible = String(detailsVisible);
  detailsButton.setAttribute("aria-pressed", String(detailsVisible));
  const detailsLabel = translateWorkspaceUiText(
    state.locale,
    detailsVisible ? "Hide Details" : "Show Details",
    detailsVisible ? "پنهان کردن جزئیات" : "نمایش جزئیات",
  );
  detailsButton.setAttribute("aria-label", detailsLabel);
  detailsButton.setAttribute("title", detailsLabel);
  detailsButton.innerHTML = '<svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true" focusable="false"><rect x="1.5" y="1.5" width="13" height="13" rx="1" fill="none" stroke="currentColor"/><rect x="3" y="10.25" width="10" height="2.75" fill="currentColor"/></svg>';
  detailsButton.onclick = () => setDetailsVisible(!detailsVisible);
  const themeLabels = workspaceThemeLabels(state.locale);
  const themeSelect = document.createElement("select");
  themeSelect.className = "cp-workspace-theme";
  themeSelect.dataset.workspaceTheme = "true";
  const themeLabel = translateWorkspaceUiText(state.locale, "Workspace theme", "پوستهٔ محیط کار");
  themeSelect.setAttribute("aria-label", themeLabel);
  themeSelect.setAttribute("title", themeLabel);
  for (const theme of WORKSPACE_THEME_IDS) {
    const option = document.createElement("option");
    option.value = theme;
    option.textContent = themeLabels[theme];
    option.selected = activeWorkspaceTheme === theme;
    themeSelect.append(option);
  }
  themeSelect.value = activeWorkspaceTheme;
  themeSelect.onchange = () => {
    if (isWorkspaceTheme(themeSelect.value)) setTheme(themeSelect.value);
  };
  const languageSelect = createWorkspaceLanguageSelect(state.locale, changeLocale);
  status.replaceChildren(document.createTextNode(shellLabels.status), languageSelect, calendarButton, detailsButton, themeSelect);
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

  const activateWindow = (menu: WorkspaceMenuKey): void => {
    rememberWorkspaceMenu(menu);
    rememberOpenWindows(openWorkspaceWindow(getOpenWindows(), menu));
    // Switching windows keeps typed-but-unsubmitted values in this window.
    renderAppPreservingDrafts(
      container,
      menu === state.activeMenu ? state : { ...state, activeMenu: menu },
      persistence,
    );
  };

  /** Tabs keep the user's order in memory and in the per-browser preference. */
  const reorderDesktopWindows = (open: readonly WorkspaceMenuKey[]): void => {
    const next = [...open];
    openWindowKeys = next;
    rememberWorkspaceWindows(next);
    rememberWorkspaceWindowOrder(next);
    renderAppPreservingDrafts(container, state, persistence);
  };

  const closeDesktopWindow = (menu: WorkspaceMenuKey): void => {
    // Closing the window that holds unsaved work asks before discarding it.
    // There is no generic save path for half-typed forms, so the prompt never
    // offers a Save action it could not actually perform.
    if (menu === state.activeMenu && workspaceHasPendingEdits(container)) {
      const prompt = translateWorkspaceUiText(
        state.locale,
        "This window has unsaved changes. Discard them and close it?",
        "این پنجره تغییرات ذخیره‌نشده دارد. آن‌ها را دور بریزیم و پنجره بسته شود؟",
      );
      if (!window.confirm(prompt)) return;
    }
    const result = closeWorkspaceWindow(getOpenWindows(), menu, state.activeMenu);
    rememberOpenWindows(result.open);
    if (result.active !== state.activeMenu) rememberWorkspaceMenu(result.active);
    renderApp(
      container,
      result.active === state.activeMenu ? state : { ...state, activeMenu: result.active },
      persistence,
    );
  };

  const runDesktopCommand = (command: DesktopCommand): void => {
    // Toolbar family visibility: hiding a family never disables its commands,
    // so the same entries remain reachable from the menus and the shortcuts.
    if (command.startsWith("view.toolbar-")) {
      const group = command.slice("view.toolbar-".length);
      if (activeWorkspaceUserId && isWorkspaceToolbarGroup(group)) {
        const hidden = readHiddenToolbarGroups(activeWorkspaceUserId);
        rememberHiddenToolbarGroups(activeWorkspaceUserId, toggleToolbarGroup(hidden, group));
        renderAppPreservingDrafts(container, state, persistence);
      }
      return;
    }
    switch (command) {
      case "workspace.refresh":
        // Re-read the authoritative project from the server instead of
        // re-rendering whatever is already in memory.
        void (async () => {
          if (!currentBootstrap) return;
          const next = await currentBootstrap.start(state.context.project_id, state.locale);
          if (next) renderBootstrapState(container, next, currentBootstrap, state.locale);
        })();
        return;
      case "forms.open":
        openFormsSurface(container, state);
        return;
      case "project.settings":
        openProjectSettings(container, state, persistence);
        return;
      case "project.close":
        closeDesktopWindow(state.activeMenu);
        return;
      case "project.interchange":
        pendingDesktopFocusSelector = "#cp-interchange";
        activateWindow("project");
        openWorkspaceDrawer(container, "[data-tools-drawer]");
        return;
      case "file.print":
        window.print();
        return;
      case "edit.undo":
        void undoLayout();
        return;
      case "edit.redo":
        void redoLayout();
        return;
      case "edit.find":
        pendingDesktopFocusSelector = "[data-activity-filter]";
        activateWindow("schedule");
        return;
      case "edit.group-wbs":
        if (state.activityGroupBy !== "wbs") {
          renderApp(container, setActivityGroupBy(state, "wbs"), persistence);
        }
        return;
      case "edit.sort-toggle":
        renderApp(container, toggleActivitySortDirection(state), persistence);
        return;
      case "project.add-wbs":
        pendingDesktopFocusSelector = "[data-wbs-create-form] input[name='code']";
        activateWindow("project");
        openWorkspaceDrawer(container, "[data-wbs-drawer]");
        return;
      case "project.add-activity":
        pendingDesktopFocusSelector = "[data-activity-create-form] input[name='activity_id']";
        activateWindow("schedule");
        openWorkspaceDrawer(container, "[data-tools-drawer]");
        return;
      case "project.edit-activity": {
        const activityId = state.selectedActivityId;
        if (!activityId) return;
        pendingDesktopAction = () => {
          for (const button of document.querySelectorAll<HTMLButtonElement>("[data-activity-edit]")) {
            if (button.dataset.activityEdit === activityId) {
              button.click();
              return;
            }
          }
        };
        activateWindow("schedule");
        return;
      }
      case "project.schedule-options":
        pendingDesktopFocusSelector = "#cp-schedule-options input, #cp-schedule-options select, #cp-schedule-options button";
        activateWindow("schedule");
        openWorkspaceDrawer(container, "[data-tools-drawer]");
        return;
      case "activity.assign-resources":
        pendingDesktopFocusSelector = "#cp-resource-capacity input, #cp-resource-capacity select, #cp-resource-capacity button";
        activateWindow("resources");
        openWorkspaceDrawer(container, "[data-tools-drawer]");
        return;
      case "activity.predecessors":
      case "activity.successors":
        pendingDesktopFocusSelector = "#cp-logic select[name='predecessor_id'], #cp-logic select[name='successor_id'], #cp-logic button";
        activateWindow("schedule");
        openWorkspaceDrawer(container, "[data-tools-drawer]");
        return;
      case "view.fields":
        activateWindow("schedule");
        openColumnsDialog();
        return;
      case "view.line-numbers": {
        const table = visualPreferences.presentation.table;
        rememberVisualPreferences({
          density: visualPreferences.density,
          presentation: normalizePresentation({
            ...visualPreferences.presentation,
            table: { ...table, lineNumbers: !table.lineNumbers },
          }),
        });
        renderApp(container, state, persistence);
        void saveCurrentLayout();
        return;
      }
      case "layout.open":
        activateWindow("schedule");
        openColumnsDialog();
        return;
      case "layout.save":
        void saveCurrentLayout();
        return;
      case "layout.save-as": {
        const name = window.prompt(
          translateWorkspaceUiText(state.locale, "Name for the saved layout", "نام چیدمان ذخیره‌شده"),
          state.p6Layout?.metadata?.layoutName ? String(state.p6Layout.metadata.layoutName) : "",
        );
        if (name && name.trim()) void saveCurrentLayout(name.trim());
        return;
      }
      case "view.zoom-in":
      case "view.zoom-out": {
        const order: WorkspaceState["ganttScale"][] = ["year", "quarter", "month", "week", "day"];
        const index = order.indexOf(state.ganttScale);
        const nextIndex = Math.min(order.length - 1, Math.max(0, index + (command === "view.zoom-in" ? 1 : -1)));
        renderApp(container, setGanttScale(state, order[nextIndex]), persistence);
        return;
      }
      case "view.fit":
        renderApp(container, setGanttScale(state, "month"), persistence);
        return;
      case "view.expand-all":
        setCollapsedWbsIds(state.context.project_id, []);
        invalidateWorkspaceRender(container);
        renderApp(container, state, persistence);
        return;
      case "view.collapse-all":
        setCollapsedWbsIds(state.context.project_id, collapseAllWbsIds(state.activities, state.wbsNodes));
        invalidateWorkspaceRender(container);
        renderApp(container, state, persistence);
        return;
      case "view.toggle-wbs":
        openWorkspaceDrawer(container, "[data-wbs-drawer]");
        return;
      case "view.toggle-gantt":
        renderApp(container, { ...state, visiblePanels: { ...state.visiblePanels, gantt: !state.visiblePanels.gantt } }, persistence);
        return;
      case "view.toggle-details":
        setDetailsVisible(!state.visiblePanels.details);
        return;
      case "view.top-table":
      case "view.top-table-gantt":
      case "view.top-network": {
        const layout = command === "view.top-table" ? "table-only" : command === "view.top-network" ? "activity-network" : "table-gantt";
        if (state.activeMenu !== "schedule" || !isWorkspaceTopLayoutAvailable(layout, state)) return;
        storeWorkspaceTopLayout(state, layout);
        renderApp(container, state, persistence);
        return;
      }
      case "view.bottom-details":
      case "view.bottom-trace":
      case "view.bottom-none": {
        const layout = command === "view.bottom-details" ? "details" : command === "view.bottom-trace" ? "trace-logic" : "none";
        if (state.activeMenu !== "schedule") return;
        if (layout === "trace-logic" && !isWorkspaceTraceLogicAvailable(state)) return;
        storeWorkspaceBottomLayout(state, layout);
        const reveal = layout !== "none" && !state.visiblePanels.details;
        if (reveal && activeWorkspaceUserId) rememberWorkspaceDetailsVisible(state, activeWorkspaceUserId, true);
        renderApp(container, reveal ? { ...state, visiblePanels: { ...state.visiblePanels, details: true } } : state, persistence);
        return;
      }
      case "view.theme-classic":
        setTheme("classic");
        return;
      case "view.theme-modern":
        setTheme("modern");
        return;
      case "view.theme-midnight":
        setTheme("midnight");
        return;
      case "view.theme-copper":
        setTheme("copper");
        return;
      case "view.theme-arctic":
        setTheme("arctic");
        return;
      case "view.theme-graphite":
        setTheme("graphite");
        return;
      case "tools.run-schedule":
        pendingDesktopFocusSelector = "#cp-schedule-run input, #cp-schedule-run select, #cp-schedule-run button";
        activateWindow("schedule");
        openWorkspaceDrawer(container, "[data-tools-drawer]");
        return;
      case "tools.formula":
        pendingDesktopFocusSelector = "#cp-formula-editor input, #cp-formula-editor select, #cp-formula-editor button";
        activateWindow("schedule");
        openWorkspaceDrawer(container, "[data-tools-drawer]");
        return;
      case "tools.reference":
        pendingDesktopFocusSelector = "#cp-schedule-reference input, #cp-schedule-reference button";
        activateWindow("schedule");
        openWorkspaceDrawer(container, "[data-tools-drawer]");
        return;
      case "admin.language": {
        const current = availableLocales.indexOf(state.locale);
        const next = availableLocales[(current + 1) % availableLocales.length] ?? "en";
        changeLocale(next);
        return;
      }
      case "admin.calendar":
        toggleCalendar();
        return;
      default:
        return;
    }
  };

  const openTabs = getOpenWindows();
  const tabsWithActive = openWorkspaceWindow(openTabs, state.activeMenu);
  if (tabsWithActive.length !== openTabs.length) rememberOpenWindows(tabsWithActive);

  const t = (en: string, persian: string): string => translateWorkspaceUiText(state.locale, en, persian);
  const chromeProject = {
    name: activeProjectLabel(state.context.project_id),
    dataDate: "—",
    baseline: "—",
    user: "—",
    database: t("Preview", "پیش‌نمایش"),
    layout: layoutDisplayName(state.p6Layout, state.locale),
    filter: state.activityFilter.trim() || t("All Activities", "همهٔ فعالیت‌ها"),
  };
  const chromeLayout = {
    groupBy: state.activityGroupBy,
    ganttScale: state.ganttScale,
    showRelationships: state.showGanttRelationships,
    density: visualPreferences.density,
  } as const;
  const applyDesktopVisuals = (): void => {
    const table = visualPreferences.presentation.table;
    desktopHost.dataset.density = visualPreferences.density;
    // Table presentation styles the workspace below the chrome, so it is
    // applied at the document root where both regions inherit it.
    document.documentElement.dataset.tableDensity = visualPreferences.density;
    document.documentElement.dataset.tableRowMode = table.rowHeightMode;
    document.documentElement.dataset.showIcons = String(table.showIcons);
    document.documentElement.dataset.lineNumbers = String(table.lineNumbers);
    document.documentElement.style.setProperty("--cp-p6-row-height", `${table.rowHeight}px`);
    document.documentElement.style.setProperty("--cp-p6-font-size", `${table.fontSize}px`);
    document.documentElement.style.setProperty("--cp-p6-font-family", presentationFontFamily(table.fontFamily));
    document.documentElement.style.setProperty("--cp-p6-text-color", table.textColor);
    document.documentElement.style.setProperty("--cp-p6-bg-color", table.backgroundColor);
  };
  applyDesktopVisuals();

  const applyLayoutOptions = (patch: DesktopLayoutPatch): void => {
    let next = state;
    if (patch.groupBy) next = setActivityGroupBy(next, patch.groupBy);
    if (patch.sortLevels) {
      next = setActivitySortLevels(next, patch.sortLevels);
    } else if (patch.sortColumnId !== undefined) {
      next = setActivitySort(next, patch.sortColumnId, patch.sortDirection ?? next.activitySort?.direction ?? "asc");
    } else if (patch.sortDirection && next.activitySort) {
      next = setActivitySort(next, next.activitySort.columnId, patch.sortDirection);
    }
    if (patch.ganttScale) next = setGanttScale(next, patch.ganttScale);
    if (patch.showRelationships !== undefined) next = setGanttRelationshipsVisible(next, patch.showRelationships);

    let presentationChanged = false;
    if (patch.presentation) {
      rememberVisualPreferences({
        density: patch.density ?? visualPreferences.density,
        presentation: normalizePresentation(patch.presentation),
      });
      presentationChanged = true;
    } else if (
      patch.density
      || patch.rowHeight !== undefined
      || patch.fontSize !== undefined
      || patch.fontFamily !== undefined
      || patch.textColor !== undefined
      || patch.backgroundColor !== undefined
      || patch.rowHeightMode !== undefined
      || patch.showIcons !== undefined
      || patch.lineNumbers !== undefined
      || patch.bars !== undefined
    ) {
      const base = visualPreferences.presentation;
      const table = { ...base.table };
      if (patch.rowHeight !== undefined) table.rowHeight = patch.rowHeight;
      if (patch.fontSize !== undefined) table.fontSize = patch.fontSize;
      if (patch.fontFamily) table.fontFamily = patch.fontFamily;
      if (patch.textColor) table.textColor = patch.textColor;
      if (patch.backgroundColor) table.backgroundColor = patch.backgroundColor;
      if (patch.rowHeightMode) table.rowHeightMode = patch.rowHeightMode;
      if (patch.showIcons !== undefined) table.showIcons = patch.showIcons;
      if (patch.lineNumbers !== undefined) table.lineNumbers = patch.lineNumbers;
      rememberVisualPreferences({
        density: patch.density ?? visualPreferences.density,
        presentation: normalizePresentation({ ...base, table, bars: patch.bars ?? base.bars }),
      });
      presentationChanged = true;
    }
    applyDesktopVisuals();
    if (presentationChanged) {
      // Show the change immediately, then publish it with the saved layout so a
      // reload or another session reads the same table and bar presentation.
      renderApp(container, next, persistence);
      if (next.p6Layout && next.p6FieldRegistry) {
        const base = next.p6Layout;
        const bumped: LayoutDefinition = {
          ...base,
          revision: base.revision + 1,
          metadata: {
            ...(base.metadata ?? {}),
            presentation: visualPreferences.presentation,
            presentationUpdatedAt: visualPreferences.updatedAt,
          },
        };
        void commitLayout(setP6Presentation(next, next.p6FieldRegistry, bumped));
      }
      return;
    }
    if (next !== state) renderApp(container, next, persistence);
  };

  const goWorkspaceHome = (): void => {
    if (workspaceHasPendingEdits(container)) {
      const prompt = translateWorkspaceUiText(
        state.locale,
        "You have unsaved changes in this workspace. Leave without saving?",
        "شما تغییرات ذخیره‌نشده در این محیط کار دارید. بدون ذخیره خارج می‌شوید؟",
      );
      if (!window.confirm(prompt)) return;
    }
    if (document.fullscreenElement) {
      void document.exitFullscreen?.().catch(() => undefined);
    }
    // Navigation only: the authenticated session and every saved project
    // revision stay untouched. The Home page re-opens this workspace later.
    window.location.assign(publicHomeHref());
  };

  renderDesktopShell(
    desktopHost,
    {
      locale: state.locale,
      activeWindow: state.activeMenu,
      openWindows: getOpenWindows(),
      capabilities: {
        canUndoLayout: Boolean(historyView?.canUndo),
        canRedoLayout: Boolean(historyView?.canRedo),
        hasWbs: state.wbsNodes.length > 0,
        hasSelectedActivity: Boolean(state.selectedActivityId),
        hasRelationships: state.relationships.length > 0,
        hasMultipleWindows: getOpenWindows().length > 1,
        canOpenFieldChooser: Boolean(state.p6Layout && state.p6FieldRegistry),
        hasLayout: Boolean(state.p6Layout),
        groupByWbs: state.activityGroupBy === "wbs",
        canAdminister: activeWorkspaceRoles.includes("project_admin"),
      },
      hiddenToolbarGroups: activeWorkspaceUserId ? readHiddenToolbarGroups(activeWorkspaceUserId) : [],
      ganttVisible: state.visiblePanels.gantt,
      dirtyWindows: workspaceHasPendingEdits(container) ? [state.activeMenu] : [],
      project: chromeProject,
      layout: chromeLayout,
      sortColumns: state.columns.map((column) => ({ id: column.id, label: column.label })),
      sortColumnId: state.activitySort?.columnId ?? null,
      sortDirection: state.activitySort?.direction ?? "asc",
      sortLevels: state.activitySortLevels,
      presentation: visualPreferences.presentation,
      detailsVisible: state.visiblePanels.details && !(state.activeMenu === "schedule" && readWorkspaceBottomLayout(state) === "none"),
      activityTopLayout: state.activeMenu === "schedule" ? readWorkspaceTopLayout(state) : undefined,
      activityBottomLayout: state.activeMenu === "schedule" ? readWorkspaceBottomLayout(state) : undefined,
      theme: activeWorkspaceTheme,
      dataAvailability: presentationDataAvailability(state.activities),
      dataDate: chromeProject.dataDate === "—" ? null : chromeProject.dataDate,
    },
    {
      onWindowOpen: activateWindow,
      onWindowClose: closeDesktopWindow,
      onWindowReorder: reorderDesktopWindows,
      onCommand: runDesktopCommand,
      onLayoutOptions: applyLayoutOptions,
      onLocaleChange: (locale) => changeLocale(locale),
      onHome: goWorkspaceHome,
    },
  );
  const activeTitle = WINDOW_TITLES[state.activeMenu];
  desktopStatus.innerHTML = renderStatusBar({
    locale: state.locale,
    project: chromeProject,
    layout: chromeLayout,
    activeWindowTitle: translateWorkspaceUiText(state.locale, activeTitle.en, activeTitle.fa),
    openWindowCount: getOpenWindows().length,
  });

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

  const commitLayout = async (next: WorkspaceState): Promise<LayoutDefinition | null> => {
    if (!next.p6Layout || !next.p6FieldRegistry) return null;
    try {
      const saved = await persistence.save(presentationMetadata(next.p6Layout));
      const savedHistory = getLayoutHistory(next.context, saved);
      const previous = currentWorkspaceState?.p6Layout ?? state.p6Layout;
      if (previous) savedHistory.undo.push(previous);
      savedHistory.redo.length = 0;
      savedHistory.noticeKey = null;
      invalidateLayoutRevisions(savedHistory);
      renderApp(container, setP6Presentation(next, next.p6FieldRegistry, saved), persistence);
      return saved;
    } catch (error) {
      await reportLayoutFailure(error);
      return null;
    }
  };

  const saveCurrentLayout = async (name?: string): Promise<void> => {
    if (!state.p6Layout || !state.p6FieldRegistry) return;
    const base = state.p6Layout;
    const bumped: LayoutDefinition = {
      ...base,
      revision: base.revision + 1,
      metadata: {
        ...(base.metadata ?? {}),
        ...(name ? { layoutName: name } : {}),
        presentation: visualPreferences.presentation,
        presentationUpdatedAt: visualPreferences.updatedAt,
      },
    };
    const saved = await commitLayout(setP6Presentation(state, state.p6FieldRegistry, bumped));
    if (saved) {
      layoutPreviewBase = null;
      layoutPreviewScope = null;
      layoutPreviewContextKey = null;
      rememberStoredLayoutSelection(state.context, saved);
    }
  };

  /**
   * Save As copies the current columns and presentation into the user layout
   * scope under a new name, so the project layout is never overwritten. It is a
   * real write: the server assigns the next revision. The store keys layouts by
   * project and scope, so "user" names the scope, not a per-user partition.
   */
  const saveLayoutAs = async (name: string): Promise<void> => {
    const base = currentWorkspaceState?.p6Layout ?? state.p6Layout;
    const registry = currentWorkspaceState?.p6FieldRegistry ?? state.p6FieldRegistry;
    if (!base || !registry) return;
    const targetScope: StoredLayoutScope = "user";
    try {
      const catalog = await loadLayoutCatalog(aiTransport, state.context, base.view_id);
      const existing = catalog[targetScope];
      const saved = await persistence.save({
        schema_version: base.schema_version,
        scope: targetScope,
        view_id: base.view_id,
        revision: existing ? existing.revision + 1 : 0,
        columns: base.columns,
        metadata: {
          ...(base.metadata ?? {}),
          layoutName: name,
          presentation: visualPreferences.presentation,
          presentationUpdatedAt: visualPreferences.updatedAt,
        },
      });
      layoutPreviewBase = null;
      layoutPreviewScope = null;
      layoutPreviewContextKey = null;
      rememberStoredLayoutSelection(state.context, saved);
      const latest = currentWorkspaceState ?? state;
      renderApp(container, setP6Presentation(latest, registry, saved), persistence);
    } catch (error) {
      await reportLayoutFailure(error);
    }
  };

  const reloadStoredLayout = async (scope: StoredLayoutScope): Promise<void> => {
    const base = currentWorkspaceState?.p6Layout ?? state.p6Layout;
    const registry = currentWorkspaceState?.p6FieldRegistry ?? state.p6FieldRegistry;
    if (!base || !registry) return;
    try {
      const layout = await persistence.load(scope, base.view_id);
      if (!layout) return;
      layoutPreviewBase = null;
      layoutPreviewScope = null;
      layoutPreviewContextKey = null;
      rememberStoredLayoutSelection(state.context, layout);
      renderApp(container, setP6Presentation(currentWorkspaceState ?? state, registry, layout), persistence);
    } catch (error) {
      await reportLayoutFailure(error);
    }
  };

  /**
   * A stored user-layout selection survives a reload and a project switch. The
   * project layout loads first, so this read restores the user layout without
   * a second stored pointer on the server. An open preview owns the window,
   * and a layout that is already the user layout needs no second render, so
   * neither case can loop.
   */
  const restoreStoredLayoutSelection = (): void => {
    if (!activeWorkspaceUserId) return;
    if (layoutPreviewScope !== null) return;
    const selection = readStoredLayoutSelection(state.context);
    if (!selection || selection.scope !== "user" || selection.viewId !== "activity") return;
    if (state.p6Layout?.scope === "user") return;
    void persistence.load("user", selection.viewId).then((layout) => {
      const latest = currentWorkspaceState;
      if (!layout || !latest || !latest.p6FieldRegistry) return;
      if (latest.context.project_id !== state.context.project_id) return;
      renderApp(container, setP6Presentation(latest, latest.p6FieldRegistry, layout), persistence);
    }).catch((error: unknown) => console.error("Stored layout selection could not be restored", error));
  };

  const mutateLayout = (mutate: () => WorkspaceState): void => {
    try {
      void commitLayout(mutate());
    } catch (error) {
      void reportLayoutFailure(error);
    }
  };

  /**
   * The Columns dialog edits a local draft and publishes it through the same
   * layout contract as the inline chooser. Defaults are read from the server so
   * the browser does not keep a second definition of the default layout.
   */
  const openColumnsDialog = (): void => {
    if (!state.p6FieldRegistry || !state.p6Layout) return;
    const initial = state.p6Layout;
    openP6ColumnsDialog({
      registry: state.p6FieldRegistry,
      layout: initial,
      locale: state.locale,
      loadDefaults: () => loadP6DefaultLayout(aiTransport, state.context, initial.scope, initial.view_id),
      commit: async (draft) => {
        const latest = currentWorkspaceState ?? state;
        if (!latest.p6FieldRegistry || !latest.p6Layout) return null;
        return commitLayout(setP6Presentation(latest, latest.p6FieldRegistry, {
          ...draft,
          scope: latest.p6Layout.scope,
          view_id: latest.p6Layout.view_id,
          metadata: latest.p6Layout.metadata ?? {},
        }));
      },
    });
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
      const saved = await persistence.save(presentationMetadata({ ...target, revision: layout.revision + 1 }));
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
      const saved = await persistence.save(presentationMetadata({ ...target, revision: layout.revision + 1 }));
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
      const saved = await persistence.save(presentationMetadata({ ...target, revision: layout.revision + 1 }));
      history.undo.push(layout);
      history.redo.length = 0;
      history.noticeKey = "restored";
      invalidateLayoutRevisions(history);
      renderApp(container, setP6Presentation(state, registry, saved), persistence);
    } catch (error) {
      await reportLayoutFailure(error);
    }
  };

  // The workspace read model exposes no project Data Date, so the Gantt must
  // not invent one; the line stays absent until an authoritative date exists.
  const projectDataDate = chromeProject.dataDate === "—" ? null : chromeProject.dataDate;
  renderMainWorkspace(workspace, state, {
    openWindows: getOpenWindows(),
    presentation: visualPreferences.presentation,
    dataDate: projectDataDate,
    // The Projects window renders the session's own project list and the
    // authoritative metadata row; both come from the server, never from a guess.
    projects: currentBootstrap?.openableProjects() ?? [],
    projectSummary: activeProjectSummary,
    onProjectOpen: (projectId) => {
      if (!currentBootstrap) return;
      void currentBootstrap.selectProject(projectId, state.locale).then((next) => {
        if (next) renderBootstrapState(container, next, currentBootstrap!, state.locale);
      });
    },
    // The interactive Details surface may only replace the pane while it is
    // actually showing Details; Trace Logic and a hidden pane are untouched.
    enhanceActivityDetails: (host, detailsState) => {
      if (detailsState.activeMenu !== "schedule" || readWorkspaceBottomLayout(detailsState) !== "details") return;
      enhanceActivityDetails(
        host,
        {
          locale: detailsState.locale,
          activities: detailsState.activities,
          selectedActivityId: detailsState.selectedActivityId,
          relationships: detailsState.relationships,
          projectName: activeProjectLabel(detailsState.context.project_id),
          dataDate: "—",
          calendarMode: detailsState.calendarMode,
          state: detailsState,
        },
        (activityId) => renderApp(container, selectActivity(detailsState, activityId), persistence),
      );
    },
    onGanttCommand: (command) => openDesktopDialog(desktopHost, command),
    onActivityContextCommand: (command) => {
      switch (command) {
        case "details":
          if (!state.visiblePanels.details) {
            activateWindow("schedule");
            pendingDesktopFocusSelector = "#cp-details";
            setDetailsVisible(true);
          } else {
            pendingDesktopFocusSelector = "#cp-details";
            activateWindow("schedule");
          }
          return;
        case "add":
          runDesktopCommand("project.add-activity");
          return;
        case "link":
          runDesktopCommand("activity.predecessors");
          return;
        case "columns":
          runDesktopCommand("view.fields");
          return;
        case "line-numbers":
          runDesktopCommand("view.line-numbers");
          return;
        case "font-row":
          openDesktopDialog(desktopHost, "font-row");
          return;
        case "group-sort":
          openDesktopDialog(desktopHost, "group-sort");
          return;
      }
    },
    onWindowClose: (menu) => closeDesktopWindow(menu),
    onMenuSelect: (menu) => {
      rememberWorkspaceMenu(menu);
      rememberOpenWindows(openWorkspaceWindow(getOpenWindows(), menu));
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
    onRelationshipUpdate: async (relationshipId, recordRevision, input) => {
      try {
        if (!aiTransport.patch) throw new Error("PATCH_TRANSPORT_UNAVAILABLE");
        const response = await aiTransport.patch<
          {
            expected_revision: number;
            predecessor_id: string;
            successor_id: string;
            relationship_type: string;
            lag_value: string;
            lag_unit: string;
          },
          unknown
        >(
          `/api/projects/${encodeURIComponent(state.context.project_id)}/p6/relationships/${encodeURIComponent(relationshipId)}`,
          {
            expected_revision: recordRevision,
            predecessor_id: input.predecessorId,
            successor_id: input.successorId,
            relationship_type: input.type,
            lag_value: input.lagValue,
            lag_unit: input.lagUnit,
          },
          state.context,
        );
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
        form.className = "cp-p6-inline-activity-editor";
        form.dataset.activityUpdateForm = activity.activity_id;
        const editTitle = t("Edit activity", "ویرایش فعالیت");
        form.setAttribute("aria-label", editTitle);
        form.innerHTML = "";
        const heading = document.createElement("h3");
        heading.textContent = editTitle;
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
        addInput("name", t("Activity name", "نام فعالیت"), activity.name);
        addInput("duration_value", t("Duration", "مدت"), String(activity.duration_value), "number");
        const unitLabel = document.createElement("label");
        unitLabel.append(document.createTextNode(t("Duration unit", "واحد مدت") + " "));
        const unit = document.createElement("select");
        unit.name = "duration_unit";
        for (const [value, labelText] of [["working-day", t("Working day", "روز کاری")], ["working-hour", t("Working hour", "ساعت کاری")]] as const) {
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
        save.textContent = t("Save changes", "ذخیره تغییرات");
        form.append(save);
        const createForm = panel.querySelector("[data-activity-create-form]");
        if (createForm) createForm.after(form);
        else panel.append(form);
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
            // The edit is committed; the refreshed grid must not resurrect the
            // closed editor with its pre-save values.
            form.remove();
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
    onActivitySortSet: (columnId, direction) => {
      renderApp(container, setActivitySort(state, columnId, direction), persistence);
    },
    onActivitySortDirectionToggle: () => {
      renderApp(container, toggleActivitySortDirection(state), persistence);
    },
    onP6FieldAdd: (fieldId) => mutateLayout(() => addP6Field(state, fieldId)),
    onP6FieldReorder: (orderedFieldIds) => mutateLayout(() => reorderP6Fields(state, orderedFieldIds)),
    onP6FieldWidthChange: (fieldId, width) => mutateLayout(() => updateP6FieldPresentation(state, fieldId, { width })),
    onP6ColumnWidthsReset: (widths) => mutateLayout(() => {
      if (!state.p6Layout || !state.p6FieldRegistry) return state;
      return setP6Presentation(state, state.p6FieldRegistry, {
        ...state.p6Layout,
        revision: state.p6Layout.revision + 1,
        columns: state.p6Layout.columns.map((column) =>
          widths[column.field_id] === undefined ? column : { ...column, width: widths[column.field_id] }),
      });
    }),
    onP6FieldPresentationChange: (fieldId, patch) => mutateLayout(() => updateP6FieldPresentation(state, fieldId, patch)),
    onP6FieldVisibilityChange: (fieldId, visible) => mutateLayout(() => updateP6FieldPresentation(state, fieldId, { visible })),
    onP6FieldRemove: (fieldId) => mutateLayout(() => removeP6Field(state, fieldId)),
    onP6LayoutUndo: () => { void undoLayout(); },
    onP6LayoutRedo: () => { void redoLayout(); },
    onP6LayoutRestore: (revision) => { void restoreLayout(revision); },
    onRailAction: (action) => {
      switch (action) {
        case "projects":
        case "eps":
          activateWindow("project");
          return;
        case "wbs":
          openWorkspaceDrawer(container, "[data-wbs-drawer]");
          return;
        case "activities":
          activateWindow("schedule");
          return;
        case "resources":
        case "assignments":
          activateWindow("resources");
          openWorkspaceDrawer(container, "[data-tools-drawer]");
          return;
        case "reports":
          activateWindow("reports");
          return;
        case "documents":
          activateWindow("documents");
          return;
        case "expenses":
          activateWindow("cost");
          return;
        case "risks":
        case "issues":
          activateWindow("control");
          return;
        case "forms":
          openFormsSurface(container, state);
          return;
        case "settings":
          activateWindow("settings");
          return;
        case "tools":
          openWorkspaceDrawer(container, "[data-tools-drawer]");
          return;
        case "notebook": {
          const openNotebook = (): void => {
            const tab = document.querySelector<HTMLElement>("#cp-details [data-detail-tab='notebook']");
            if (tab) tab.click();
          };
          if (state.activeMenu === "schedule" || state.activeMenu === "project") {
            openNotebook();
          } else {
            pendingDesktopAction = openNotebook;
            activateWindow("schedule");
          }
          return;
        }
        default:
          return;
      }
    },
    layoutHistory: historyView,
  });
  if (
    activityEditor
    && !activityEditor.isConnected
    && activityEditorId
    && state.activities.some((activity) => activity.id === activityEditorId)
  ) {
    const panel = workspace.querySelector<HTMLElement>("#cp-activity-grid");
    if (panel) {
      const createForm = panel.querySelector("[data-activity-create-form]");
      if (createForm) createForm.after(activityEditor);
      else panel.append(activityEditor);
    }
  }
  if (
    state.p6Layout
    && layoutHistory
    && layoutHistory.revisions === null
    && !layoutHistory.revisionRequest
    && !layoutHistory.revisionLoadFailed
  ) {
    void requestLayoutRevisions(state.p6Layout)
      .then(() => {
        renderAppPreservingDrafts(container, currentWorkspaceState ?? state, persistence, true);
      })
      .catch((error) => {
        console.error("P6 layout history read failed", error);
        layoutHistory.revisionLoadFailed = true;
        renderAppPreservingDrafts(container, currentWorkspaceState ?? state, persistence, true);
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
      if (next !== latest) renderAppPreservingDrafts(container, next, persistence);
    } catch (error) {
      console.error("Authoritative schedule result projection failed", error);
    }
  });

  const calendarPage = workspace.querySelector<HTMLElement>("[data-calendar-page]");
  if (calendarPage) {
    mountWorkspaceCalendarPage(calendarPage, {
      transport: aiTransport,
      context: state.context,
      locale: state.locale,
      catalog: state.calendarCatalog,
    });
  }

  const rolesPage = workspace.querySelector<HTMLElement>("[data-roles-page]");
  if (rolesPage) {
    mountWorkspaceRolesPage(rolesPage, {
      transport: aiTransport,
      context: state.context,
      locale: state.locale,
    });
  }

  // A layout preview belongs to the project it was opened in. Switching project
  // must not carry the preview (or its Cancel target) into the new workspace.
  const layoutContextKey = `${state.context.tenant_id}:${state.context.project_id}`;
  if (layoutPreviewContextKey && layoutPreviewContextKey !== layoutContextKey) {
    layoutPreviewBase = null;
    layoutPreviewScope = null;
    layoutPreviewContextKey = null;
  }
  const layoutSelectorHost = workspace.querySelector<HTMLElement>("[data-layout-selector-host]");
  if (layoutSelectorHost && state.activeMenu === "schedule") {
    mountWorkspaceLayoutSelector(layoutSelectorHost, {
      locale: state.locale,
      current: state.p6Layout,
      previewScope: layoutPreviewScope,
      // The default policy grants layout writes (PROJECT_WRITE) to these roles
      // and to none else, so the control mirrors the server gate.
      canSave: activeWorkspaceRoles.includes("planner") || activeWorkspaceRoles.includes("project_admin"),
      loadCatalog: () => loadLayoutCatalog(aiTransport, state.context, "activity"),
      onPreview: (entry) => {
        if (!state.p6FieldRegistry) return;
        if (!layoutPreviewBase) {
          layoutPreviewBase = state.p6Layout;
          layoutPreviewContextKey = layoutContextKey;
        }
        layoutPreviewScope = entry.scope;
        renderApp(container, setP6Presentation(state, state.p6FieldRegistry, entry.layout), persistence);
      },
      onApply: () => {
        if (state.p6Layout) rememberStoredLayoutSelection(state.context, state.p6Layout);
        layoutPreviewBase = null;
        layoutPreviewScope = null;
        layoutPreviewContextKey = null;
        renderApp(container, state, persistence);
      },
      onCancel: () => {
        const base = layoutPreviewBase;
        layoutPreviewBase = null;
        layoutPreviewScope = null;
        layoutPreviewContextKey = null;
        if (base && state.p6FieldRegistry) {
          renderApp(container, setP6Presentation(state, state.p6FieldRegistry, base), persistence);
        } else {
          renderApp(container, state, persistence);
        }
      },
      onSave: () => {
        void saveCurrentLayout();
      },
      onSaveAs: (name) => {
        void saveLayoutAs(name);
      },
      onReload: (scope) => {
        void reloadStoredLayout(scope);
      },
    });
    restoreStoredLayoutSelection();
  }

  const assignmentsPage = workspace.querySelector<HTMLElement>("[data-assignments-page]");
  if (assignmentsPage) {
    mountWorkspaceAssignmentsPage(assignmentsPage, {
      transport: aiTransport,
      context: state.context,
      locale: state.locale,
      canWrite: activeWorkspaceRoles.includes("planner") || activeWorkspaceRoles.includes("project_admin"),
      activities: state.activities.map((activity) => ({
        id: activity.id,
        code: activity.code,
        name: activity.name,
      })),
    });
  }

  const resourcesPage = workspace.querySelector<HTMLElement>("[data-resources-page]");
  if (resourcesPage) {
    mountWorkspaceResourcesPage(resourcesPage, {
      transport: aiTransport,
      context: state.context,
      locale: state.locale,
    });
  }

  const expensesPage = workspace.querySelector<HTMLElement>("[data-expenses-page]");
  if (expensesPage) {
    mountWorkspaceExpensesPage(expensesPage, {
      transport: aiTransport,
      context: state.context,
      locale: state.locale,
      canWrite: activeWorkspaceRoles.includes("planner") || activeWorkspaceRoles.includes("project_admin"),
      activities: state.activities.map((activity) => ({
        id: activity.id,
        code: activity.code,
        name: activity.name,
      })),
      wbsNodes: state.wbsNodes.map((node) => ({
        id: node.id,
        code: node.localCode,
        name: node.name,
      })),
    });
  }

  const thresholdsPage = workspace.querySelector<HTMLElement>("[data-thresholds-page]");
  if (thresholdsPage) {
    mountWorkspaceThresholdsPage(thresholdsPage, {
      transport: aiTransport,
      context: state.context,
      locale: state.locale,
      canWrite: activeWorkspaceRoles.includes("planner") || activeWorkspaceRoles.includes("project_admin"),
    });
  }

  const risksPage = workspace.querySelector<HTMLElement>("[data-risks-page]");
  if (risksPage) {
    mountWorkspaceRisksPage(risksPage, {
      transport: aiTransport,
      context: state.context,
      locale: state.locale,
      canWrite: activeWorkspaceRoles.includes("planner") || activeWorkspaceRoles.includes("project_admin"),
    });
  }

  const reportsPage = workspace.querySelector<HTMLElement>("[data-reports-page]");
  if (reportsPage) {
    mountWorkspaceReportsPage(reportsPage, {
      transport: aiTransport,
      context: state.context,
      locale: state.locale,
      canWrite: activeWorkspaceRoles.includes("planner") || activeWorkspaceRoles.includes("project_admin"),
    });
  }

  const administrationPage = workspace.querySelector<HTMLElement>("[data-administration-page]");
  if (administrationPage) {
    mountWorkspaceAdministrationPage(administrationPage, {
      transport: aiTransport,
      context: state.context,
      locale: state.locale,
      canAdmin: activeWorkspaceRoles.includes("project_admin"),
    });
  }

  const issuesPage = workspace.querySelector<HTMLElement>("[data-issues-page]");
  if (issuesPage) {
    mountWorkspaceIssuesPage(issuesPage, {
      transport: aiTransport,
      context: state.context,
      locale: state.locale,
      activities: state.activities.map((activity) => ({
        id: activity.id,
        code: activity.code,
        name: activity.name,
      })),
      wbsNodes: state.wbsNodes.map((node) => ({
        id: node.id,
        code: node.localCode,
        name: node.name,
      })),
    });
  }

  const documentsPage = workspace.querySelector<HTMLElement>("[data-documents-page]");
  if (documentsPage) {
    mountWorkspaceDocumentsPage(documentsPage, {
      transport: aiTransport,
      context: state.context,
      locale: state.locale,
      // PROJECT_WRITE is granted to planner and project_admin by the default
      // policy, so the register mirrors that server gate exactly.
      canWrite: activeWorkspaceRoles.includes("planner") || activeWorkspaceRoles.includes("project_admin"),
      canApprove: activeWorkspaceRoles.includes("project_admin"),
    });
  }

  const costPage = workspace.querySelector<HTMLElement>("[data-cost-page]");
  if (costPage) {
    mountWorkspaceCostPage(costPage, {
      transport: aiTransport,
      context: state.context,
      locale: state.locale,
      onNavigate: (menu) => activateWindow(menu),
      canWrite: activeWorkspaceRoles.includes("planner") || activeWorkspaceRoles.includes("project_admin"),
      canApprove: activeWorkspaceRoles.includes("project_admin"),
    });
  }

  const progressPage = workspace.querySelector<HTMLElement>("[data-progress-page]");
  if (progressPage) {
    mountWorkspaceProgressPage(progressPage, {
      transport: aiTransport,
      context: state.context,
      locale: state.locale,
      initialActivityId: progressSelection,
      onUpdated: async (activity) => {
        // Progress is stored by the shared activity service. Re-read the
        // workspace so the activity grid and Gantt show the same persisted
        // values, while keeping the Progress window and selection in place.
        progressSelection = activity.activityId;
        const refreshed = await new WorkspaceReadClient(aiTransport).load(state.context, {
          locale: state.locale,
          calendarMode: state.calendarMode,
        });
        if (!refreshed.ok) return;
        const nextState = await loadP6Presentation(refreshed.data, aiTransport, state.context);
        renderApp(container, { ...nextState, activeMenu: "progress" }, persistence);
      },
    });
  }

  // Comments are scoped to the item currently selected in the workspace: an
  // activity, the selected WBS element, or the project as a whole. They are
  // browser-local notes and must never look like project database records.
  const selectedWbsNode = state.wbsNodes.find((node) => node.id === state.selectedWbsId);
  const commentsEntity =
    state.activeMenu === "schedule" && state.selectedActivityId
      ? { entityKind: "activity" as const, entityId: state.selectedActivityId, entityLabel: state.selectedActivityId }
      : state.activeMenu === "project" && selectedWbsNode
        ? { entityKind: "wbs" as const, entityId: selectedWbsNode.id, entityLabel: `${selectedWbsNode.localCode} — ${selectedWbsNode.name}` }
        : {
            entityKind: (state.activeMenu === "schedule" ? "project" : state.activeMenu) as "project" | "progress" | "resources" | "cost" | "documents" | "reports" | "control" | "settings",
            entityId: state.context.project_id,
            entityLabel: state.context.project_id,
          };
  enhanceWorkspaceComments(workspace, {
    projectId: state.context.project_id,
    locale: state.locale,
    ...commentsEntity,
  });

  mountFormulaEditorPanel(
    workspace,
    aiTransport,
    state.context,
    state.locale,
    state.p6FieldRegistry?.fields ?? [],
    {
      onCreated: async (record) => {
        // The registry route now projects the persisted formula as a computed
        // Activity field. Add that field to the saved layout, then reload the
        // workspace read so the grid shows server-evaluated cells.
        const registry = await createP6FieldRegistryProvider(
          aiTransport,
          state.context,
        ).getRegistry();
        let next: WorkspaceState = { ...state, p6FieldRegistry: registry };
        let layoutChanged = false;
        try {
          next = addP6Field(next, record.formula.formula_id);
          layoutChanged = true;
        } catch (error) {
          if (!(error instanceof Error) || error.message !== "FIELD_ALREADY_IN_LAYOUT") {
            throw error;
          }
        }
        if (layoutChanged) await commitLayout(next);
        await refreshWorkspaceAfterWbsMutation(state.selectedWbsId);
      },
    },
  );
  mountInterchangePanel(
    workspace,
    aiTransport,
    state.context,
    state.locale,
    state.activities,
  );
  mountCapacityPanel(workspace, aiTransport, state.context, state.locale);
  if (pendingDesktopFocusSelector) {
    const selector = pendingDesktopFocusSelector;
    pendingDesktopFocusSelector = null;
    focusWhenReady(selector);
  }
  if (pendingDesktopAction) {
    const action = pendingDesktopAction;
    pendingDesktopAction = null;
    window.setTimeout(action, 0);
  }
  syncWindowDirtyIndicator(container);
}
/**
 * Reads the authoritative project row once per opened project. The Projects
 * window and the title bar show its real name, start date and calendar; a
 * failed read leaves them blank instead of inventing values.
 */
async function loadActiveProjectSummary(
  container: HTMLElement,
  bootstrap: ProjectBootstrap,
  projectId: string,
): Promise<void> {
  const result = await bootstrap.loadProjectSummary(projectId);
  if (!result.ok) return;
  const current = currentWorkspaceState;
  if (!current || current.context.project_id !== projectId) return;
  activeProjectSummary = result.data.project;
  activeProjectSummaryProjectId = projectId;
  // Only the Projects window and the chrome consume this record. Re-rendering
  // any other surface would discard an editor the user opened while this read
  // was in flight, so the render waits until something visible depends on it.
  const listedName = currentBootstrap?.openableProjects()
    .find((project) => project.project_id === projectId)?.name;
  if (current.activeMenu === "project" || (result.data.project.name && result.data.project.name !== listedName)) {
    renderAppPreservingDrafts(container, current);
  }
}

/** The name the server already gave us for this project, from record or session list. */
function activeProjectLabel(projectId: string): string {
  if (activeProjectSummary && activeProjectSummaryProjectId === projectId && activeProjectSummary.name) {
    return activeProjectSummary.name;
  }
  const listed = currentBootstrap?.openableProjects()
    .find((project) => project.project_id === projectId)?.name;
  return listed || projectId;
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
    activeWorkspaceUserId = state.userId;
    activeWorkspaceRoles = state.roles;
    rememberOpenedProject(state.userId, state.context.project_id);
    if (activeProjectSummaryProjectId !== state.context.project_id) activeProjectSummary = null;
    activeProjectSummaryProjectId = state.context.project_id;
    renderApp(container, applyRememberedMenu(state.workspace));
    void loadActiveProjectSummary(container, bootstrap, state.context.project_id);
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

  if (isSessionBootstrapError(error)) {
    const signIn = document.createElement("button");
    signIn.type = "button";
    signIn.textContent = t.errorSignIn;
    signIn.addEventListener("click", () => {
      const rememberedProject = new URLSearchParams(window.location.search).get("project");
      const nextPath = workspaceLoginNextPath(rememberedProject);
      window.location.assign(
        `/preview/login?next=${encodeURIComponent(nextPath)}`,
      );
    });
    actions.append(signIn);
  }

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
  const language = navigator.language.toLowerCase();
  const detected = language.startsWith("fa")
    ? "fa"
    : language.startsWith("ar")
      ? "ar"
      : language.startsWith("de")
        ? "de"
        : language.startsWith("fr")
          ? "fr"
          : language.startsWith("ja")
            ? "ja"
            : language.startsWith("ko")
              ? "ko"
              : language.startsWith("ru")
                ? "ru"
                : language.startsWith("zh")
                  ? "zh"
                  : "en";
  return available.includes(detected) ? detected : "en";
}

async function boot(): Promise<void> {
  const container = document.getElementById("app");
  if (!container) throw new Error("APP_ROOT_NOT_FOUND");

  if (window.location.pathname === "/" || window.location.pathname === "/index.html") {
    renderLandingPage(container);
    return;
  }

  // Canonicalize legacy visual-demo URLs to the single authenticated workspace.
  // The old demo module remains in the repository as a migration reference only;
  // it is never mounted as a second application shell.
  if (window.location.pathname === "/app") {
    const parameters = new URLSearchParams(window.location.search);
    if (parameters.get("view") !== "live") {
      parameters.set("view", "live");
      window.history.replaceState({}, "", `/app?${parameters.toString()}`);
    }
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
