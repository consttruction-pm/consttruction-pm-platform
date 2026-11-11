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
import type { LayoutDefinition } from "./p6-field-layout-foundation.js";
import { translateWorkspaceUiText } from "./workspace-localization.js";

export const LAYOUT_SELECTION_STORAGE_PREFIX = "cubi:workspace-layout-selection";

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

export type LayoutSelectorOptions = {
  locale: Locale;
  current: LayoutDefinition | null;
  /** Scope of the layout that is previewed but not saved, if any. */
  previewScope: StoredLayoutScope | null;
  canSave: boolean;
  saveReason?: string;
  loadCatalog: () => Promise<LayoutCatalog>;
  onPreview: (entry: LayoutCatalogEntry) => void;
  onApply: () => void;
  onCancel: () => void;
  onSave: () => void;
  onSaveAs: (name: string) => void;
  onReload: (scope: StoredLayoutScope) => void;
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
  return `<div class="cp-layout-selector" role="group" aria-label="${escapeHtml(t(locale, "Layout", "چیدمان"))}" data-layout-selector data-preview="${previewing ? "true" : "false"}">
    <span class="cp-layout-selector-key">${escapeHtml(t(locale, "Layout", "چیدمان"))}</span>
    <button type="button" class="cp-layout-selector-trigger" data-layout-trigger aria-haspopup="menu" aria-expanded="false" ${disabled ? "disabled" : ""} title="${escapeHtml(
      current ? `${name} · ${layoutScopeLabel(scope, locale)} · r${revision}` : t(locale, "No stored layout", "چیدمانی ذخیره نشده"),
    )}">
      <span class="cp-layout-selector-name" data-layout-name>${escapeHtml(name)}</span>
      <span class="cp-layout-selector-scope" data-layout-scope>${escapeHtml(layoutScopeLabel(scope, locale))} · r${revision}</span>
      <span class="cp-layout-selector-caret" aria-hidden="true">▾</span>
    </button>
    ${previewMarkup}
    <div class="cp-layout-menu" data-layout-menu role="menu" hidden aria-label="${escapeHtml(t(locale, "Available layouts", "چیدمان‌های در دسترس"))}">
      <div class="cp-layout-menu-heading">${escapeHtml(t(locale, "Stored layouts for this project", "چیدمان‌های ذخیره‌شدهٔ این پروژه"))}</div>
      ${loadingMarkup}${emptyMarkup}${optionMarkup}
      <div class="cp-layout-menu-separator" role="separator"></div>
      <div class="cp-layout-menu-actions">
        <button type="button" data-layout-action="apply" ${previewing ? "" : "disabled"} title="${escapeHtml(t(locale, "Keep the previewed layout in this window", "نگه‌داشتن چیدمان پیش‌نمایش در این پنجره"))}">${escapeHtml(t(locale, "Apply", "اعمال"))}</button>
        <button type="button" data-layout-action="cancel" ${previewing ? "" : "disabled"} title="${escapeHtml(t(locale, "Discard the preview and restore the saved layout", "دور ریختن پیش‌نمایش و بازگردانی چیدمان ذخیره‌شده"))}">${escapeHtml(t(locale, "Cancel", "انصراف"))}</button>
        <button type="button" data-layout-action="save" ${saveDisabled ? "disabled" : ""} title="${escapeHtml(canSave && current ? t(locale, "Write this layout to the server", "نوشتن این چیدمان روی سرور") : saveReason)}">${escapeHtml(t(locale, "Save", "ذخیره"))}</button>
        <button type="button" data-layout-action="save-as" ${saveDisabled ? "disabled" : ""} title="${escapeHtml(canSave && current ? t(locale, "Save a copy under its own layout name", "ذخیرهٔ نسخه‌ای با نام چیدمان خودش") : saveReason)}">${escapeHtml(t(locale, "Save As…", "ذخیره با نام…"))}</button>
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
  const rerender = (state: {
    entries: LayoutCatalogEntry[];
    loaded: boolean;
    error: string | null;
  }): void => {
    host.innerHTML = renderLayoutSelectorMarkup({
      locale: options.locale,
      current: options.current,
      previewScope: options.previewScope,
      canSave: options.canSave,
      saveReason: options.saveReason,
      entries: state.entries,
      loaded: state.loaded,
      error: state.error,
    });
  };

  rerender({ entries: [], loaded: false, error: null });

  const trigger = host.querySelector<HTMLButtonElement>("[data-layout-trigger]");
  const menu = host.querySelector<HTMLElement>("[data-layout-menu]");
  if (!trigger || !menu) return;

  let entries: LayoutCatalogEntry[] = [];
  let loaded = false;
  let error: string | null = null;
  let requested = false;

  const closeMenu = (): void => {
    menu.hidden = true;
    trigger.setAttribute("aria-expanded", "false");
  };

  const openMenu = async (): Promise<void> => {
    menu.hidden = false;
    trigger.setAttribute("aria-expanded", "true");
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
    const wasOpen = !menu.hidden;
    rerender({ entries, loaded, error });
    if (wasOpen) {
      const nextTrigger = host.querySelector<HTMLButtonElement>("[data-layout-trigger]");
      const nextMenu = host.querySelector<HTMLElement>("[data-layout-menu]");
      if (nextTrigger && nextMenu) {
        nextMenu.hidden = false;
        nextTrigger.setAttribute("aria-expanded", "true");
      }
    }
  };

  trigger.addEventListener("click", () => {
    if (menu.hidden) void openMenu();
    else closeMenu();
  });

  host.addEventListener("click", (event) => {
    const target = event.target as HTMLElement | null;
    if (!target) return;
    const option = target.closest<HTMLElement>("[data-layout-option]");
    if (option) {
      const scope = option.dataset.layoutOption as StoredLayoutScope | undefined;
      const entry = entries.find((item) => item.scope === scope);
      if (entry) {
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
      const suggested = options.current ? layoutDisplayName(options.current, options.locale) : "";
      const name = window.prompt(
        translateWorkspaceUiText(options.locale, "Name for the saved layout", "نام چیدمان ذخیره‌شده"),
        suggested,
      );
      const trimmed = name?.trim();
      if (trimmed) options.onSaveAs(trimmed);
    } else if (action === "reload") options.onReload(currentScope(options.current));
  });

  menu.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      closeMenu();
      trigger.focus();
    }
  });
  host.addEventListener("focusout", (event) => {
    const next = event.relatedTarget as Node | null;
    if (next && host.contains(next)) return;
    closeMenu();
  });
}
