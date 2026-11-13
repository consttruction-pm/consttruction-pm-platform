/**
 * Activities layout selector.
 *
 * The stored layout definitions are the only source of truth for what a layout
 * contains: the project and user layout scopes are read from the same
 * `/p6/layouts/{scope}/activity` contract that Save writes to. There is no
 * separate client catalogue, so a layout that is not stored cannot be offered,
 * and a name that is not stored falls back to its scope label instead of a
 * fabricated title.
 */
import type { ApiTransport, ProjectContext } from "./client.js";
import { createP6LayoutPersistence } from "./p6-api.js";
import { normalizeLayout, validateLayout } from "./p6-field-layout-foundation.js";
import type { FieldRegistry, LayoutDefinition } from "./p6-field-layout-foundation.js";
import { translateWorkspaceUiText } from "./workspace-localization.js";
import { readGroupSortMetadata } from "./workspace-layout-settings.js";
import { normalizePresentation } from "./workspace-presentation.js";

export const LAYOUT_SELECTION_STORAGE_PREFIX = "cubi:workspace-layout-selection";

/** File format for Layout > Export / Import. Presentation only, never project data. */
export const LAYOUT_EXCHANGE_FORMAT = "cubi-layout.v1";

export type LayoutExchangeDocument = {
  format: typeof LAYOUT_EXCHANGE_FORMAT;
  name: string;
  layout: {
    schema_version: string;
    view_id: string;
    columns: LayoutDefinition["columns"];
    metadata: Readonly<Record<string, unknown>>;
  };
};

export type StoredLayoutScope = "project" | "user";

export type LayoutCatalog = {
  project: LayoutDefinition | null;
  user: LayoutDefinition | null;
};

export type LayoutCatalogEntry = {
  scope: StoredLayoutScope;
  layout: LayoutDefinition;
  name: string;
  revision: number;
};

type Locale = string;

function t(locale: Locale, english: string, persian: string): string {
  return translateWorkspaceUiText(locale, english, persian);
}

export function layoutScopeLabel(scope: StoredLayoutScope, locale: Locale): string {
  return scope === "user"
    ? t(locale, "User layout", "چیدمان کاربر")
    : t(locale, "Project layout", "چیدمان پروژه");
}

/**
 * A layout name is whatever the stored definition carries. The scope label is
 * used when the definition has no name, so the control never invents a title.
 */
export function layoutDisplayName(layout: LayoutDefinition | null | undefined, locale: Locale): string {
  const raw = layout?.metadata?.layoutName;
  if (typeof raw === "string" && raw.trim()) return raw.trim();
  if (!layout) return t(locale, "No layout", "بدون چیدمان");
  return layoutScopeLabel(layout.scope === "user" ? "user" : "project", locale);
}

/** Stored layouts in display order; absent scopes are omitted rather than faked. */
export function layoutCatalogEntries(catalog: LayoutCatalog, locale: Locale): LayoutCatalogEntry[] {
  const entries: LayoutCatalogEntry[] = [];
  for (const scope of ["project", "user"] as const) {
    const layout = catalog[scope];
    if (!layout || layout.scope !== scope) continue;
    entries.push({ scope, layout, name: layoutDisplayName(layout, locale), revision: layout.revision });
  }
  return entries;
}

export async function loadLayoutCatalog(
  transport: ApiTransport,
  context: ProjectContext,
  viewId = "activity",
): Promise<LayoutCatalog> {
  const persistence = createP6LayoutPersistence(transport, context);
  const [project, user] = await Promise.all([
    persistence.load("project", viewId),
    persistence.load("user", viewId),
  ]);
  return { project, user };
}

export type LayoutSelection = {
  scope: StoredLayoutScope;
  viewId: string;
  revision: number;
};

export type LayoutSelectionStore = Record<string, LayoutSelection>;

function selectionKey(tenantId: string, projectId: string): string {
  return `${tenantId}:${projectId}`;
}

export function parseLayoutSelections(raw: string | null): LayoutSelectionStore {
  if (!raw) return {};
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    const store: LayoutSelectionStore = {};
    for (const [key, value] of Object.entries(parsed as Record<string, unknown>)) {
      if (!value || typeof value !== "object") continue;
      const entry = value as Partial<LayoutSelection>;
      if (entry.scope !== "project" && entry.scope !== "user") continue;
      if (typeof entry.viewId !== "string" || !entry.viewId) continue;
      if (!Number.isInteger(entry.revision) || (entry.revision ?? -1) < 0) continue;
      store[key] = { scope: entry.scope, viewId: entry.viewId, revision: entry.revision as number };
    }
    return store;
  } catch {
    return {};
  }
}

export function readLayoutSelection(
  store: LayoutSelectionStore,
  tenantId: string,
  projectId: string,
): LayoutSelection | null {
  return store[selectionKey(tenantId, projectId)] ?? null;
}

export function writeLayoutSelection(
  store: LayoutSelectionStore,
  tenantId: string,
  projectId: string,
  selection: LayoutSelection,
): string {
  return JSON.stringify({ ...store, [selectionKey(tenantId, projectId)]: selection });
}

export type LayoutViewSnapshot = {
  layout: LayoutDefinition | null;
  groupBy: "wbs" | "none";
  /** Ordered group plan; when omitted it is derived from ``groupBy``. */
  groupLevels?: readonly { fieldId: string; direction: "asc" | "desc" }[];
  sortLevels: readonly { columnId: string; direction: "asc" | "desc" }[];
  presentation: unknown;
};

/**
 * True when the window holds view changes that are not part of the stored
 * layout revision yet.
 *
 * Column edits are appended by the layout service as they happen, so the only
 * local-only state is the group/sort plan and the table/Gantt presentation,
 * which Save publishes with the layout metadata. A stored revision that never
 * carried a plan is compared against the Activities defaults, so a freshly
 * loaded layout is not reported as dirty.
 */
export function layoutHasUnsavedChanges(view: LayoutViewSnapshot): boolean {
  const layout = view.layout;
  if (!layout) return false;
  const saved = readGroupSortMetadata(layout.metadata) ?? {
    groupBy: "wbs" as const,
    groupLevels: [{ fieldId: "wbs", direction: "asc" as const }],
    sortLevels: [{ columnId: "wbs", direction: "asc" as const }],
  };
  if (saved.groupBy !== view.groupBy) return true;
  const currentLevels = view.groupLevels
    ?? (view.groupBy === "wbs" ? [{ fieldId: "wbs", direction: "asc" as const }] : []);
  if (saved.groupLevels.length !== currentLevels.length) return true;
  for (let index = 0; index < saved.groupLevels.length; index += 1) {
    const stored = saved.groupLevels[index];
    const current = currentLevels[index];
    if (!current || stored.fieldId !== current.fieldId || stored.direction !== current.direction) return true;
  }
  if (saved.sortLevels.length !== view.sortLevels.length) return true;
  for (let index = 0; index < saved.sortLevels.length; index += 1) {
    const stored = saved.sortLevels[index];
    const current = view.sortLevels[index];
    if (!current || stored.columnId !== current.columnId || stored.direction !== current.direction) return true;
  }
  const savedPresentation = layout.metadata?.presentation;
  if (savedPresentation && typeof savedPresentation === "object") {
    const stored = JSON.stringify(normalizePresentation(savedPresentation));
    const current = JSON.stringify(normalizePresentation(view.presentation));
    if (stored !== current) return true;
  }
  return false;
}


function exchangeName(layout: LayoutDefinition | null, locale: Locale): string {
  return layoutDisplayName(layout, locale);
}

/** Serializes the stored layout for download; scope and revision stay server-owned. */
export function serializeLayoutDocument(layout: LayoutDefinition, name: string): string {
  const document: LayoutExchangeDocument = {
    format: LAYOUT_EXCHANGE_FORMAT,
    name: name.trim(),
    layout: {
      schema_version: layout.schema_version,
      view_id: layout.view_id,
      columns: layout.columns,
      metadata: layout.metadata ?? {},
    },
  };
  return JSON.stringify(document, null, 2);
}

/**
 * Parses an exported layout into a user-scope draft. The target revision is
 * left at zero because the catalog decides the next revision on save; an
 * imported file can never overwrite a project layout or pin a revision.
 */
export function parseLayoutDocument(
  text: string,
  registry?: FieldRegistry,
): { name: string; layout: LayoutDefinition } {
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new Error("INVALID_LAYOUT_DOCUMENT");
  }
  if (!parsed || typeof parsed !== "object") throw new Error("INVALID_LAYOUT_DOCUMENT");
  const document = parsed as Partial<LayoutExchangeDocument>;
  if (document.format !== LAYOUT_EXCHANGE_FORMAT) throw new Error("INVALID_LAYOUT_DOCUMENT");
  const name = typeof document.name === "string" ? document.name.trim() : "";
  if (!name) throw new Error("INVALID_LAYOUT_DOCUMENT_NAME");
  const raw = document.layout;
  if (!raw || typeof raw !== "object") throw new Error("INVALID_LAYOUT_DOCUMENT");
  const layout = validateLayout(
    {
      schema_version: raw.schema_version as LayoutDefinition["schema_version"],
      scope: "user",
      view_id: String(raw.view_id ?? ""),
      revision: 0,
      columns: Array.isArray(raw.columns) ? raw.columns : [],
      metadata: raw.metadata && typeof raw.metadata === "object" ? raw.metadata : {},
    },
    registry,
  );
  return { name, layout: normalizeLayout(layout) };
}

export type LayoutSelectorOptions = {
  locale: Locale;
  current: LayoutDefinition | null;
  /** Scope of the layout that is previewed but not saved, if any. */
  previewScope: StoredLayoutScope | null;
  canSave: boolean;
  saveReason?: string;
  /** The window holds group/sort or presentation changes not yet saved. */
  dirty?: boolean;
  /** False while the layout service has no delete route. */
  canDelete?: boolean;
  deleteReason?: string;
  loadCatalog: () => Promise<LayoutCatalog>;
  onPreview: (entry: LayoutCatalogEntry) => void;
  onApply: () => void;
  onCancel: () => void;
  onSave: () => void;
  onSaveAs: (name: string) => void;
  onRename: (name: string) => void;
  onNew: (name: string) => void;
  onResetDefault: () => void;
  onDelete?: () => void;
  onExport: () => void;
  onImport: (text: string) => void;
  onReload: (scope: StoredLayoutScope) => void;
  /** Returns true when the user accepts discarding unsaved layout changes. */
  confirmDiscard?: (message: string) => boolean;
  onError?: (message: string) => void;
};

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function currentScope(layout: LayoutDefinition | null): StoredLayoutScope {
  return layout?.scope === "user" ? "user" : "project";
}

export function renderLayoutSelectorMarkup(options: {
  locale: Locale;
  current: LayoutDefinition | null;
  previewScope: StoredLayoutScope | null;
  canSave: boolean;
  saveReason?: string;
  dirty?: boolean;
  canDelete?: boolean;
  deleteReason?: string;
  entries: LayoutCatalogEntry[];
  loaded: boolean;
  error: string | null;
}): string {
  const { locale, current, previewScope, canSave } = options;
  const name = layoutDisplayName(current, locale);
  const scope = currentScope(current);
  const revision = current ? current.revision : 0;
  const disabled = options.entries.length === 0 && options.loaded;
  const previewing = previewScope !== null;
  const optionMarkup = options.entries
    .map((entry) => {
      const checked = current ? entry.scope === current.scope : false;
      const isPreview = previewScope === entry.scope;
      return `<button type="button" class="cp-layout-option${checked ? " is-current" : ""}${isPreview ? " is-preview" : ""}" role="menuitemradio" aria-checked="${checked ? "true" : "false"}" data-layout-option="${entry.scope}" title="${escapeHtml(
        `${layoutScopeLabel(entry.scope, locale)} · ${t(locale, "revision", "ویرایش")} ${entry.revision}`,
      )}">
        <span class="cp-layout-option-mark" aria-hidden="true">${checked || isPreview ? "●" : "○"}</span>
        <span class="cp-layout-option-name">${escapeHtml(entry.name)}</span>
        <span class="cp-layout-option-meta">${escapeHtml(layoutScopeLabel(entry.scope, locale))} · r${entry.revision}</span>
      </button>`;
    })
    .join("");
  const emptyMarkup = options.loaded && !options.entries.length
    ? `<p class="cp-layout-empty">${escapeHtml(t(locale, "No stored layout is available for this project.", "چیدمان ذخیره‌شده‌ای برای این پروژه در دسترس نیست."))}</p>`
    : "";
  const loadingMarkup = options.loaded ? "" : `<p class="cp-layout-empty">${escapeHtml(t(locale, "Reading stored layouts…", "در حال خواندن چیدمان‌های ذخیره‌شده…"))}</p>`;
  const saveDisabled = !canSave || !current;
  const saveReason = !current
    ? t(locale, "No stored layout to write", "چیدمان ذخیره‌شده‌ای برای نوشتن نیست")
    : options.saveReason ?? t(locale, "Your role cannot save layouts", "نقش شما اجازهٔ ذخیرهٔ چیدمان را ندارد");
  const previewMarkup = previewing
    ? `<span class="cp-layout-state" data-layout-state="preview">${escapeHtml(t(locale, "Preview — not saved", "پیش‌نمایش — ذخیره نشده"))}</span>`
    : "";
  const dirtyMarkup = options.dirty && !previewing
    ? `<span class="cp-layout-state" data-layout-state="dirty">${escapeHtml(t(locale, "Unsaved changes", "تغییرات ذخیره‌نشده"))}</span>`
    : "";
  const deleteDisabled = !options.canDelete;
  const deleteReason = options.deleteReason
    ?? t(locale, "The layout service does not support deleting a stored layout yet", "سرویس چیدمان هنوز حذف چیدمان ذخیره‌شده را پشتیبانی نمی‌کند");
  return `<div class="cp-layout-selector" role="group" aria-label="${escapeHtml(t(locale, "Layout", "چیدمان"))}" data-layout-selector data-preview="${previewing ? "true" : "false"}">
    <span class="cp-layout-selector-key">${escapeHtml(t(locale, "Layout", "چیدمان"))}</span>
    <button type="button" class="cp-layout-selector-trigger" data-layout-trigger aria-haspopup="menu" aria-expanded="false" ${disabled ? "disabled" : ""} title="${escapeHtml(
      current ? `${name} · ${layoutScopeLabel(scope, locale)} · r${revision}` : t(locale, "No stored layout", "چیدمانی ذخیره نشده"),
    )}">
      <span class="cp-layout-selector-name" data-layout-name>${escapeHtml(name)}</span>
      <span class="cp-layout-selector-scope" data-layout-scope>${escapeHtml(layoutScopeLabel(scope, locale))} · r${revision}</span>
      <span class="cp-layout-selector-caret" aria-hidden="true">▾</span>
    </button>
    ${previewMarkup}${dirtyMarkup}
    <div class="cp-layout-menu" data-layout-menu role="menu" hidden aria-label="${escapeHtml(t(locale, "Available layouts", "چیدمان‌های در دسترس"))}">
      <div class="cp-layout-menu-heading">${escapeHtml(t(locale, "Stored layouts for this project", "چیدمان‌های ذخیره‌شدهٔ این پروژه"))}</div>
      ${loadingMarkup}${emptyMarkup}${optionMarkup}
      <div class="cp-layout-menu-separator" role="separator"></div>
      <div class="cp-layout-menu-actions">
        <button type="button" data-layout-action="apply" ${previewing ? "" : "disabled"} title="${escapeHtml(t(locale, "Keep the previewed layout in this window", "نگه‌داشتن چیدمان پیش‌نمایش در این پنجره"))}">${escapeHtml(t(locale, "Apply", "اعمال"))}</button>
        <button type="button" data-layout-action="cancel" ${previewing ? "" : "disabled"} title="${escapeHtml(t(locale, "Discard the preview and restore the saved layout", "دور ریختن پیش‌نمایش و بازگردانی چیدمان ذخیره‌شده"))}">${escapeHtml(t(locale, "Cancel", "انصراف"))}</button>
        <button type="button" data-layout-action="save" ${saveDisabled ? "disabled" : ""} title="${escapeHtml(canSave && current ? t(locale, "Write this layout to the server", "نوشتن این چیدمان روی سرور") : saveReason)}">${escapeHtml(t(locale, "Save", "ذخیره"))}</button>
        <button type="button" data-layout-action="save-as" ${saveDisabled ? "disabled" : ""} title="${escapeHtml(canSave && current ? t(locale, "Save a copy under its own layout name", "ذخیرهٔ نسخه‌ای با نام چیدمان خودش") : saveReason)}">${escapeHtml(t(locale, "Save As…", "ذخیره با نام…"))}</button>
        <button type="button" data-layout-action="rename" ${saveDisabled ? "disabled" : ""} title="${escapeHtml(canSave && current ? t(locale, "Rename this stored layout", "تغییر نام این چیدمان ذخیره‌شده") : saveReason)}">${escapeHtml(t(locale, "Rename…", "تغییر نام…"))}</button>
        <button type="button" data-layout-action="new" ${canSave ? "" : "disabled"} title="${escapeHtml(canSave ? t(locale, "Create a new layout from the canonical default columns", "ساخت چیدمان تازه از ستون‌های پیش‌فرض") : saveReason)}">${escapeHtml(t(locale, "New…", "تازه…"))}</button>
        <button type="button" data-layout-action="reset-default" ${saveDisabled ? "disabled" : ""} title="${escapeHtml(canSave && current ? t(locale, "Reset the window to the canonical default layout", "بازنشانی پنجره به چیدمان پیش‌فرض") : saveReason)}">${escapeHtml(t(locale, "Reset to Default", "بازنشانی به پیش‌فرض"))}</button>
        <button type="button" data-layout-action="delete" ${deleteDisabled ? "disabled" : ""} title="${escapeHtml(deleteDisabled ? deleteReason : t(locale, "Delete this stored layout", "حذف این چیدمان ذخیره‌شده"))}">${escapeHtml(t(locale, "Delete…", "حذف…"))}</button>
        <button type="button" data-layout-action="export" ${current ? "" : "disabled"} title="${escapeHtml(t(locale, "Download this layout as a file", "بارگیری این چیدمان به‌صورت پرونده"))}">${escapeHtml(t(locale, "Export…", "برون‌بری…"))}</button>
        <button type="button" data-layout-action="import" ${saveDisabled ? "disabled" : ""} title="${escapeHtml(canSave && current ? t(locale, "Save an exported layout file into the user scope", "ذخیرهٔ پروندهٔ چیدمان برون‌بری‌شده در دامنهٔ کاربر") : saveReason)}">${escapeHtml(t(locale, "Import…", "درون‌ریزی…"))}</button>
        <input type="file" accept="application/json,.json" data-layout-import hidden aria-hidden="true" tabindex="-1">
        <button type="button" data-layout-action="reload" ${current ? "" : "disabled"} title="${escapeHtml(t(locale, "Re-read the stored layout from the server", "خواندن دوبارهٔ چیدمان ذخیره‌شده از سرور"))}">${escapeHtml(t(locale, "Reload", "بازخوانی"))}</button>
      </div>
      ${options.error ? `<p class="cp-layout-error" role="alert">${escapeHtml(options.error)}</p>` : ""}
      <p class="cp-layout-hint">${escapeHtml(
        t(
          locale,
          "A stored layout holds columns, widths and presentation only. Switching never changes activities, relationships, WBS or dates.",
          "چیدمان ذخیره‌شده فقط ستون‌ها، عرض‌ها و نمایش را نگه می‌دارد. تغییر آن هرگز فعالیت‌ها، روابط، ساختار شکست یا تاریخ‌ها را تغییر نمی‌دهد.",
        ),
      )}</p>
    </div>
  </div>`;
}

/**
 * Mounts the selector into its host. The host is re-created by each workspace
 * render, so the menu is rebuilt from the current stored state every time.
 */
export function mountWorkspaceLayoutSelector(host: HTMLElement, options: LayoutSelectorOptions): void {
  let entries: LayoutCatalogEntry[] = [];
  let loaded = false;
  let error: string | null = null;
  let requested = false;
  let open = false;

  // Every rerender replaces the host's children, so elements are looked up on
  // demand and all listeners live on the host itself.
  const rerender = (): void => {
    host.innerHTML = renderLayoutSelectorMarkup({
      locale: options.locale,
      current: options.current,
      previewScope: options.previewScope,
      canSave: options.canSave,
      saveReason: options.saveReason,
      dirty: options.dirty,
      canDelete: options.canDelete,
      deleteReason: options.deleteReason,
      entries,
      loaded,
      error,
    });
    const trigger = host.querySelector<HTMLButtonElement>("[data-layout-trigger]");
    const menu = host.querySelector<HTMLElement>("[data-layout-menu]");
    if (!trigger || !menu) return;
    menu.hidden = !open;
    trigger.setAttribute("aria-expanded", open ? "true" : "false");
  };

  rerender();

  const closeMenu = (): void => {
    open = false;
    const trigger = host.querySelector<HTMLButtonElement>("[data-layout-trigger]");
    const menu = host.querySelector<HTMLElement>("[data-layout-menu]");
    if (menu) menu.hidden = true;
    if (trigger) trigger.setAttribute("aria-expanded", "false");
  };

  const confirmDiscard = (): boolean => {
    if (!options.dirty) return true;
    const message = translateWorkspaceUiText(
      options.locale,
      "This layout has changes that are not saved. Discard them?",
      "این چیدمان تغییرات ذخیره‌نشده دارد. آن‌ها دور ریخته شوند؟",
    );
    return options.confirmDiscard ? options.confirmDiscard(message) : window.confirm(message);
  };

  const openMenu = async (): Promise<void> => {
    open = true;
    const trigger = host.querySelector<HTMLButtonElement>("[data-layout-trigger]");
    const menu = host.querySelector<HTMLElement>("[data-layout-menu]");
    if (menu) menu.hidden = false;
    if (trigger) trigger.setAttribute("aria-expanded", "true");
    if (requested) return;
    requested = true;
    try {
      const catalog = await options.loadCatalog();
      entries = layoutCatalogEntries(catalog, options.locale);
      loaded = true;
      error = null;
    } catch (loadError) {
      requested = false;
      loaded = true;
      error = `${translateWorkspaceUiText(options.locale, "Layouts could not be read", "خواندن چیدمان‌ها انجام نشد")}: ${
        loadError instanceof Error ? loadError.message : String(loadError)
      }`;
      options.onError?.(error);
    }
    rerender();
  };

  host.addEventListener("click", (event) => {
    const target = event.target as HTMLElement | null;
    if (!target) return;
    if (target.closest("[data-layout-trigger]")) {
      if (open) closeMenu();
      else void openMenu();
      return;
    }
    const option = target.closest<HTMLElement>("[data-layout-option]");
    if (option) {
      const scope = option.dataset.layoutOption as StoredLayoutScope | undefined;
      const entry = entries.find((item) => item.scope === scope);
      if (entry) {
        if (!confirmDiscard()) {
          closeMenu();
          return;
        }
        closeMenu();
        options.onPreview(entry);
      }
      return;
    }
    const action = target.closest<HTMLElement>("[data-layout-action]")?.dataset.layoutAction;
    if (!action) return;
    closeMenu();
    if (action === "apply") options.onApply();
    else if (action === "cancel") options.onCancel();
    else if (action === "save") options.onSave();
    else if (action === "save-as") {
      const suggested = exchangeName(options.current, options.locale);
      const name = window.prompt(
        translateWorkspaceUiText(options.locale, "Name for the saved layout", "نام چیدمان ذخیره‌شده"),
        suggested,
      );
      const trimmed = name?.trim();
      if (trimmed) options.onSaveAs(trimmed);
    } else if (action === "rename") {
      const suggested = exchangeName(options.current, options.locale);
      const name = window.prompt(
        translateWorkspaceUiText(options.locale, "New name for this layout", "نام تازه برای این چیدمان"),
        suggested,
      );
      const trimmed = name?.trim();
      if (trimmed && trimmed !== suggested) options.onRename(trimmed);
    } else if (action === "new") {
      if (!confirmDiscard()) return;
      const name = window.prompt(
        translateWorkspaceUiText(options.locale, "Name for the new layout", "نام چیدمان تازه"),
        translateWorkspaceUiText(options.locale, "New layout", "چیدمان تازه"),
      );
      const trimmed = name?.trim();
      if (trimmed) options.onNew(trimmed);
    } else if (action === "reset-default") {
      if (!confirmDiscard()) return;
      options.onResetDefault();
    } else if (action === "delete") {
      options.onDelete?.();
    } else if (action === "export") {
      options.onExport();
    } else if (action === "import") {
      host.querySelector<HTMLInputElement>("[data-layout-import]")?.click();
    } else if (action === "reload") {
      if (!confirmDiscard()) return;
      options.onReload(currentScope(options.current));
    }
  });

  host.addEventListener("change", (event) => {
    const input = (event.target as HTMLElement | null)?.closest<HTMLInputElement>("[data-layout-import]");
    if (!input) return;
    const file = input.files?.[0];
    if (!file) return;
    void file.text().then((text) => options.onImport(text)).catch(() => options.onError?.(translateWorkspaceUiText(options.locale, "The layout file could not be read", "خواندن پروندهٔ چیدمان انجام نشد")));
    input.value = "";
  });

  host.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    event.preventDefault();
    closeMenu();
    host.querySelector<HTMLButtonElement>("[data-layout-trigger]")?.focus();
  });
  host.addEventListener("focusout", (event) => {
    const next = event.relatedTarget as Node | null;
    if (next && host.contains(next)) return;
    closeMenu();
  });
}
