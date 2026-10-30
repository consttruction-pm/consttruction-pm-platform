import type { WorkspaceMenuKey } from "./workspace-model.js";

/**
 * Desktop chrome for the professional workspace: the application menu bar, the
 * main command toolbar, window tabs and the shortcuts/about dialogs. Every
 * entry either opens a real workspace surface, runs a command the shell is
 * given, or states why it is unavailable. Nothing is rendered as decoration.
 */
export type LocalizedLabel = { en: string; fa: string };

export type DesktopCommand =
  | "project.settings"
  | "project.close"
  | "project.interchange"
  | "edit.undo"
  | "edit.redo"
  | "edit.find"
  | "edit.group-wbs"
  | "edit.sort-toggle"
  | "project.add-wbs"
  | "project.add-activity"
  | "project.edit-activity"
  | "view.fields"
  | "tools.run-schedule"
  | "tools.formula"
  | "tools.reference"
  | "admin.language"
  | "admin.calendar"
  | "help.shortcuts"
  | "help.about";

export type DesktopShellCapabilities = {
  canUndoLayout: boolean;
  canRedoLayout: boolean;
  hasWbs: boolean;
  hasSelectedActivity: boolean;
  hasMultipleWindows: boolean;
  canOpenFieldChooser: boolean;
  groupByWbs: boolean;
};

export type DesktopMenuItem = {
  id: string;
  label: LocalizedLabel;
  shortcut?: string;
  window?: WorkspaceMenuKey;
  command?: DesktopCommand;
  disabledReason?: LocalizedLabel;
  checked?: boolean;
};

export type DesktopMenu = {
  id: DesktopMenuId;
  label: LocalizedLabel;
  items: DesktopMenuItem[];
};

export type DesktopMenuId =
  | "workspace"
  | "edit"
  | "view"
  | "project"
  | "organization"
  | "tools"
  | "administration"
  | "help";

export type DesktopToolbarItem = {
  id: string;
  label: LocalizedLabel;
  title: LocalizedLabel;
  shortcut?: string;
  window?: WorkspaceMenuKey;
  command?: DesktopCommand;
  disabledReason?: LocalizedLabel;
  active?: boolean;
};

export type DesktopShellState = {
  locale: string;
  activeWindow: WorkspaceMenuKey;
  openWindows: readonly WorkspaceMenuKey[];
  capabilities: DesktopShellCapabilities;
};

export type DesktopShellHandlers = {
  onWindowOpen: (window: WorkspaceMenuKey) => void;
  onWindowClose: (window: WorkspaceMenuKey) => void;
  onCommand: (command: DesktopCommand) => void;
};

export const WINDOW_TITLES: Record<WorkspaceMenuKey, LocalizedLabel> = {
  project: { en: "Projects", fa: "پروژه‌ها" },
  schedule: { en: "Activities", fa: "فعالیت‌ها" },
  progress: { en: "Tracking", fa: "پیگیری" },
  resources: { en: "Resources", fa: "منابع" },
  cost: { en: "Cost", fa: "هزینه" },
  documents: { en: "Documents", fa: "اسناد" },
  reports: { en: "Reports", fa: "گزارش‌ها" },
  control: { en: "Control", fa: "کنترل" },
  settings: { en: "Administration", fa: "مدیریت" },
};

const WINDOW_ORDER: readonly WorkspaceMenuKey[] = [
  "project",
  "schedule",
  "progress",
  "resources",
  "cost",
  "documents",
  "reports",
  "control",
  "settings",
];

function language(locale: string): "en" | "fa" {
  return locale.split("-")[0] === "fa" ? "fa" : "en";
}

function pick(label: LocalizedLabel, locale: string): string {
  return label[language(locale)] ?? label.en;
}

function unavailable(reason: LocalizedLabel, locale: string): LocalizedLabel {
  // The reason is already localized; this keeps the shape uniform for tests.
  return reason[language(locale)] ? reason : { en: reason.en, fa: reason.fa };
}

const REASONS = {
  undo: { en: "No earlier layout change is available", fa: "تغییر قبلی چیدمان در دسترس نیست" },
  redo: { en: "No layout change to reapply", fa: "تغییری برای اعمال دوباره وجود ندارد" },
  singleWindow: { en: "The last open window cannot be closed", fa: "آخرین پنجرهٔ باز را نمی‌توان بست" },
  noWbs: { en: "Create a WBS element before adding activities", fa: "پیش از افزودن فعالیت، یک عنصر WBS بسازید" },
  noSelection: { en: "Select an activity in the grid first", fa: "ابتدا یک فعالیت را در جدول انتخاب کنید" },
  noFields: { en: "No saved field layout is available for this project", fa: "چیدمان فیلد ذخیره‌شده‌ای برای این پروژه در دسترس نیست" },
  calendarAdmin: { en: "Calendar administration is not available in this workspace yet", fa: "مدیریت تقویم هنوز در این محیط کار در دسترس نیست" },
  roles: { en: "Role administration is not available in this workspace yet", fa: "مدیریت نقش‌ها هنوز در این محیط کار در دسترس نیست" },
} satisfies Record<string, LocalizedLabel>;

export function getDesktopMenus(state: DesktopShellState): DesktopMenu[] {
  const { capabilities: caps, locale } = state;
  const window = (key: WorkspaceMenuKey, shortcut: string): DesktopMenuItem => ({
    id: `window.${key}`,
    label: WINDOW_TITLES[key],
    shortcut,
    window: key,
  });
  return [
    {
      id: "workspace",
      label: { en: "Workspace", fa: "محیط کار" },
      items: [
        { id: "workspace.settings", label: { en: "Project settings…", fa: "تنظیمات پروژه…" }, command: "project.settings", shortcut: "Alt+P" },
        { id: "workspace.projects", label: WINDOW_TITLES.project, window: "project" },
        { id: "workspace.interchange", label: { en: "Import / Export", fa: "ورود / خروجی" }, command: "project.interchange" },
        {
          id: "workspace.close",
          label: { en: "Close window", fa: "بستن پنجره" },
          command: "project.close",
          shortcut: "Ctrl+W",
          disabledReason: caps.hasMultipleWindows ? undefined : unavailable(REASONS.singleWindow, locale),
        },
      ],
    },
    {
      id: "edit",
      label: { en: "Edit", fa: "ویرایش" },
      items: [
        {
          id: "edit.undo",
          label: { en: "Undo layout change", fa: "بازگردانی تغییر چیدمان" },
          command: "edit.undo",
          shortcut: "Ctrl+Z",
          disabledReason: caps.canUndoLayout ? undefined : unavailable(REASONS.undo, locale),
        },
        {
          id: "edit.redo",
          label: { en: "Redo layout change", fa: "اعمال دوبارهٔ تغییر چیدمان" },
          command: "edit.redo",
          shortcut: "Ctrl+Y",
          disabledReason: caps.canRedoLayout ? undefined : unavailable(REASONS.redo, locale),
        },
        { id: "edit.find", label: { en: "Find activities", fa: "یافتن فعالیت‌ها" }, command: "edit.find", shortcut: "Ctrl+F" },
        {
          id: "edit.group-wbs",
          label: { en: "Group by WBS", fa: "گروه‌بندی بر اساس WBS" },
          command: "edit.group-wbs",
          checked: caps.groupByWbs,
        },
        { id: "edit.sort-toggle", label: { en: "Reverse sort direction", fa: "معکوس کردن جهت ترتیب" }, command: "edit.sort-toggle" },
      ],
    },
    {
      id: "view",
      label: { en: "View", fa: "نما" },
      items: [
        ...WINDOW_ORDER.map((key, index) => window(key, `Alt+${index + 1}`)),
        {
          id: "view.fields",
          label: { en: "Activity fields…", fa: "فیلدهای فعالیت…" },
          command: "view.fields",
          disabledReason: caps.canOpenFieldChooser ? undefined : unavailable(REASONS.noFields, locale),
        },
      ],
    },
    {
      id: "project",
      label: { en: "Project", fa: "پروژه" },
      items: [
        { id: "project.settings", label: { en: "Project properties…", fa: "مشخصات پروژه…" }, command: "project.settings" },
        { id: "project.add-wbs", label: { en: "Add WBS element", fa: "افزودن عنصر WBS" }, command: "project.add-wbs" },
        {
          id: "project.add-activity",
          label: { en: "Add activity", fa: "افزودن فعالیت" },
          command: "project.add-activity",
          disabledReason: caps.hasWbs ? undefined : unavailable(REASONS.noWbs, locale),
        },
        {
          id: "project.edit-activity",
          label: { en: "Edit selected activity", fa: "ویرایش فعالیت انتخاب‌شده" },
          command: "project.edit-activity",
          shortcut: "Enter",
          disabledReason: caps.hasSelectedActivity ? undefined : unavailable(REASONS.noSelection, locale),
        },
        { id: "project.relationships", label: { en: "Relationships", fa: "روابط" }, window: "schedule" },
      ],
    },
    {
      id: "organization",
      label: { en: "Organization", fa: "سازمان" },
      items: [
        { id: "organization.resources", label: WINDOW_TITLES.resources, window: "resources" },
        { id: "organization.capacity", label: { en: "Resource capacity", fa: "ظرفیت منابع" }, window: "resources" },
        {
          id: "organization.calendars",
          label: { en: "Calendars", fa: "تقویم‌ها" },
          disabledReason: unavailable(REASONS.calendarAdmin, locale),
        },
        {
          id: "organization.roles",
          label: { en: "Roles", fa: "نقش‌ها" },
          disabledReason: unavailable(REASONS.roles, locale),
        },
      ],
    },
    {
      id: "tools",
      label: { en: "Tools", fa: "ابزارها" },
      items: [
        { id: "tools.run-schedule", label: { en: "Schedule activities", fa: "زمان‌بندی فعالیت‌ها" }, command: "tools.run-schedule", shortcut: "F9" },
        { id: "tools.formula", label: { en: "Formula editor", fa: "ویرایشگر فرمول" }, command: "tools.formula" },
        { id: "tools.reference", label: { en: "Scheduling reference", fa: "مرجع زمان‌بندی" }, command: "tools.reference" },
        { id: "tools.fields", label: { en: "Layout fields", fa: "فیلدهای چیدمان" }, command: "view.fields" },
      ],
    },
    {
      id: "administration",
      label: { en: "Administration", fa: "مدیریت" },
      items: [
        { id: "administration.language", label: { en: "Switch language", fa: "تغییر زبان" }, command: "admin.language" },
        { id: "administration.calendar", label: { en: "Switch calendar system", fa: "تغییر تقویم" }, command: "admin.calendar" },
        { id: "administration.settings", label: { en: "Workspace settings", fa: "تنظیمات محیط کار" }, window: "settings" },
      ],
    },
    {
      id: "help",
      label: { en: "Help", fa: "راهنما" },
      items: [
        { id: "help.shortcuts", label: { en: "Keyboard shortcuts", fa: "کلیدهای میانبر" }, command: "help.shortcuts", shortcut: "F1" },
        { id: "help.about", label: { en: "About CUBI Workspace", fa: "دربارهٔ محیط کار CUBI" }, command: "help.about" },
      ],
    },
  ];
}

export function getDesktopToolbar(state: DesktopShellState): DesktopToolbarItem[] {
  const { capabilities: caps, locale } = state;
  return [
    {
      id: "toolbar.settings",
      label: { en: "Settings", fa: "تنظیمات" },
      title: { en: "Project settings", fa: "تنظیمات پروژه" },
      command: "project.settings",
    },
    {
      id: "toolbar.add-wbs",
      label: { en: "WBS", fa: "WBS" },
      title: { en: "Add WBS element", fa: "افزودن عنصر WBS" },
      command: "project.add-wbs",
    },
    {
      id: "toolbar.add-activity",
      label: { en: "Activity", fa: "فعالیت" },
      title: { en: "Add activity", fa: "افزودن فعالیت" },
      command: "project.add-activity",
      disabledReason: caps.hasWbs ? undefined : unavailable(REASONS.noWbs, locale),
    },
    {
      id: "toolbar.edit-activity",
      label: { en: "Edit", fa: "ویرایش" },
      title: { en: "Edit selected activity", fa: "ویرایش فعالیت انتخاب‌شده" },
      command: "project.edit-activity",
      disabledReason: caps.hasSelectedActivity ? undefined : unavailable(REASONS.noSelection, locale),
    },
    {
      id: "toolbar.find",
      label: { en: "Find", fa: "یافتن" },
      title: { en: "Find activities", fa: "یافتن فعالیت‌ها" },
      command: "edit.find",
      shortcut: "Ctrl+F",
    },
    {
      id: "toolbar.group-wbs",
      label: { en: "Group WBS", fa: "گروه WBS" },
      title: { en: "Group activities by WBS", fa: "گروه‌بندی فعالیت‌ها بر اساس WBS" },
      command: "edit.group-wbs",
      active: caps.groupByWbs,
    },
    {
      id: "toolbar.undo",
      label: { en: "Undo", fa: "بازگردانی" },
      title: { en: "Undo layout change", fa: "بازگردانی تغییر چیدمان" },
      command: "edit.undo",
      disabledReason: caps.canUndoLayout ? undefined : unavailable(REASONS.undo, locale),
    },
    {
      id: "toolbar.redo",
      label: { en: "Redo", fa: "تکرار" },
      title: { en: "Redo layout change", fa: "اعمال دوبارهٔ تغییر چیدمان" },
      command: "edit.redo",
      disabledReason: caps.canRedoLayout ? undefined : unavailable(REASONS.redo, locale),
    },
    {
      id: "toolbar.fields",
      label: { en: "Fields", fa: "فیلدها" },
      title: { en: "Activity field layout", fa: "چیدمان فیلدهای فعالیت" },
      command: "view.fields",
      disabledReason: caps.canOpenFieldChooser ? undefined : unavailable(REASONS.noFields, locale),
    },
    {
      id: "toolbar.schedule",
      label: { en: "Schedule", fa: "زمان‌بندی" },
      title: { en: "Open the activities workspace", fa: "بازکردن محیط فعالیت‌ها" },
      command: "tools.run-schedule",
    },
  ];
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderMenuItem(item: DesktopMenuItem, locale: string): string {
  const disabled = Boolean(item.disabledReason);
  const reason = item.disabledReason ? pick(item.disabledReason, locale) : "";
  const target = item.window
    ? ` data-desktop-window="${escapeHtml(item.window)}"`
    : item.command
      ? ` data-desktop-command="${escapeHtml(item.command)}"`
      : "";
  return `<button type="button" role="menuitem" class="cp-menubar-item${disabled ? " is-disabled" : ""}"${target}${disabled ? ' disabled aria-disabled="true"' : ""}${item.checked ? ' aria-checked="true"' : ""}${reason ? ` title="${escapeHtml(reason)}"` : ""}>
    <span class="cp-menubar-item-label">${escapeHtml(pick(item.label, locale))}</span>
    ${reason ? `<span class="cp-menubar-item-reason">${escapeHtml(reason)}</span>` : item.shortcut ? `<span class="cp-menubar-item-shortcut">${escapeHtml(item.shortcut)}</span>` : ""}
  </button>`;
}

function renderMenus(state: DesktopShellState): string {
  const locale = state.locale;
  const menus = getDesktopMenus(state);
  return `<div class="cp-menubar" role="menubar" aria-label="${escapeHtml(locale.startsWith("fa") ? "منوی برنامه" : "Application menu")}">
    ${menus.map((menu) => `<div class="cp-menubar-group">
      <button type="button" class="cp-menubar-trigger" role="menuitem" aria-haspopup="true" aria-expanded="false" data-desktop-menu="${escapeHtml(menu.id)}">${escapeHtml(pick(menu.label, locale))}</button>
      <div class="cp-menubar-popup" role="menu" data-desktop-popup="${escapeHtml(menu.id)}" aria-label="${escapeHtml(pick(menu.label, locale))}" hidden>
        ${menu.items.map((item) => renderMenuItem(item, locale)).join("")}
      </div>
    </div>`).join("")}
  </div>`;
}

function renderToolbar(state: DesktopShellState): string {
  const locale = state.locale;
  return `<div class="cp-toolbar" role="toolbar" aria-label="${escapeHtml(locale.startsWith("fa") ? "نوار ابزار اصلی" : "Main toolbar")}">
    ${getDesktopToolbar(state).map((item) => {
      const disabled = Boolean(item.disabledReason);
      const title = item.disabledReason ? pick(item.disabledReason, locale) : pick(item.title, locale);
      const target = item.window
        ? ` data-desktop-window="${escapeHtml(item.window)}"`
        : item.command
          ? ` data-desktop-command="${escapeHtml(item.command)}"`
          : "";
      return `<button type="button" class="cp-toolbar-button" data-toolbar-command="${escapeHtml(item.id)}"${target} title="${escapeHtml(title)}"${item.active ? ' aria-pressed="true"' : ""}${disabled ? ' disabled aria-disabled="true"' : ""}>${escapeHtml(pick(item.label, locale))}</button>`;
    }).join("")}
  </div>`;
}

function renderTabs(state: DesktopShellState): string {
  const locale = state.locale;
  const closable = state.openWindows.length > 1;
  return `<div class="cp-window-tabs" role="tablist" aria-label="${escapeHtml(locale.startsWith("fa") ? "پنجره‌های باز" : "Open windows")}">
    ${state.openWindows.map((key) => {
      const selected = key === state.activeWindow;
      const title = pick(WINDOW_TITLES[key], locale);
      return `<span class="cp-window-tab${selected ? " is-active" : ""}" role="tab" aria-selected="${selected ? "true" : "false"}" data-window-tab="${escapeHtml(key)}" tabindex="${selected ? "0" : "-1"}">
        <button type="button" class="cp-window-tab-label" data-window-open="${escapeHtml(key)}">${escapeHtml(title)}</button>
        ${closable ? `<button type="button" class="cp-window-tab-close" data-window-close="${escapeHtml(key)}" aria-label="${escapeHtml((locale.startsWith("fa") ? "بستن " : "Close ") + title)}" title="${escapeHtml((locale.startsWith("fa") ? "بستن " : "Close ") + title)}">×</button>` : ""}
      </span>`;
    }).join("")}
  </div>`;
}

function renderShortcutsDialog(state: DesktopShellState): string {
  const locale = state.locale;
  const rows = getDesktopMenus(state).flatMap((menu) => menu.items.filter((item) => item.shortcut));
  return `<dialog class="cp-desktop-dialog" data-desktop-dialog="shortcuts" aria-labelledby="cp-shortcuts-heading">
    <h2 id="cp-shortcuts-heading">${escapeHtml(locale.startsWith("fa") ? "کلیدهای میانبر" : "Keyboard shortcuts")}</h2>
    <table><thead><tr><th>${escapeHtml(locale.startsWith("fa") ? "فرمان" : "Command")}</th><th>${escapeHtml(locale.startsWith("fa") ? "میانبر" : "Shortcut")}</th></tr></thead>
    <tbody>${rows.map((item) => `<tr><td>${escapeHtml(pick(item.label, locale))}</td><td><kbd>${escapeHtml(item.shortcut ?? "")}</kbd></td></tr>`).join("")}</tbody></table>
    <form method="dialog"><button type="submit">${escapeHtml(locale.startsWith("fa") ? "بستن" : "Close")}</button></form>
  </dialog>`;
}

function renderAboutDialog(state: DesktopShellState): string {
  const locale = state.locale;
  return `<dialog class="cp-desktop-dialog" data-desktop-dialog="about" aria-labelledby="cp-about-heading">
    <h2 id="cp-about-heading">${escapeHtml(locale.startsWith("fa") ? "دربارهٔ محیط کار CUBI" : "About CUBI Workspace")}</h2>
    <p>${escapeHtml(locale.startsWith("fa")
      ? "محیط کار کنترل پروژهٔ CUBI: ساختار پروژه، ساختار شکست کار، فعالیت‌ها، روابط، زمان‌بندی و نمایش گرافیکی."
      : "The CUBI project controls workspace: project structure, work breakdown, activities, relationships, scheduling and graphical views.")}</p>
    <p>${escapeHtml(locale.startsWith("fa")
      ? "داده‌ها از سرور پروژهٔ همین نشست خوانده می‌شوند؛ صفحهٔ راهنما هیچ عدد یا وضعیت ساختگی نمایش نمی‌دهد."
      : "Data is read from this session's project server; the workspace never reports invented figures or states.")}</p>
    <form method="dialog"><button type="submit">${escapeHtml(locale.startsWith("fa") ? "بستن" : "Close")}</button></form>
  </dialog>`;
}

export function renderDesktopShell(
  host: HTMLElement,
  state: DesktopShellState,
  handlers: DesktopShellHandlers,
): void {
  runtimeByHost.set(host, { state, handlers });
  host.innerHTML = `<section class="cp-desktop" data-desktop-shell>
    ${renderMenus(state)}
    ${renderToolbar(state)}
    ${renderTabs(state)}
  </section>
  ${renderShortcutsDialog(state)}
  ${renderAboutDialog(state)}`;
  bindHost(host);
}

type ShellRuntime = { state: DesktopShellState; handlers: DesktopShellHandlers };
const runtimeByHost = new WeakMap<HTMLElement, ShellRuntime>();
const boundHosts = new WeakSet<HTMLElement>();
let documentBound = false;

function popupFor(host: HTMLElement, menuId: string): HTMLElement | null {
  return host.querySelector<HTMLElement>(`[data-desktop-popup="${menuId}"]`);
}

function triggerFor(host: HTMLElement, menuId: string): HTMLElement | null {
  return host.querySelector<HTMLElement>(`[data-desktop-menu="${menuId}"]`);
}

function closeMenus(host: HTMLElement, restoreFocus = false): void {
  let restored = false;
  host.querySelectorAll<HTMLElement>("[data-desktop-menu]").forEach((trigger) => {
    const wasOpen = trigger.getAttribute("aria-expanded") === "true";
    trigger.setAttribute("aria-expanded", "false");
    const menuId = trigger.dataset.desktopMenu;
    if (menuId) {
      const popup = popupFor(host, menuId);
      if (popup) popup.hidden = true;
    }
    if (restoreFocus && wasOpen && !restored) {
      trigger.focus();
      restored = true;
    }
  });
}

function openMenu(host: HTMLElement, menuId: string, focusFirst = false): void {
  closeMenus(host);
  const trigger = triggerFor(host, menuId);
  const popup = popupFor(host, menuId);
  if (!trigger || !popup) return;
  trigger.setAttribute("aria-expanded", "true");
  popup.hidden = false;
  if (focusFirst) {
    popup.querySelector<HTMLElement>("button:not([disabled])")?.focus();
  }
}

function openDialog(host: HTMLElement, name: "shortcuts" | "about"): void {
  const dialog = host.querySelector<HTMLDialogElement>(`[data-desktop-dialog="${name}"]`);
  if (!dialog) return;
  closeMenus(host);
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
}

function commandForTarget(target: HTMLElement): { command?: string; window?: string } {
  const command = target.closest<HTMLElement>("[data-desktop-command]")?.dataset.desktopCommand;
  const windowKey = target.closest<HTMLElement>("[data-desktop-window]")?.dataset.desktopWindow;
  return { command, window: windowKey };
}

function bindHost(host: HTMLElement): void {
  if (boundHosts.has(host)) return;
  boundHosts.add(host);
  host.addEventListener("click", (event) => {
    const target = event.target as HTMLElement | null;
    if (!target || typeof target.closest !== "function") return;
    const runtime = runtimeByHost.get(host);
    if (!runtime) return;

    const closeWindow = target.closest<HTMLElement>("[data-window-close]");
    if (closeWindow?.dataset.windowClose) {
      event.stopPropagation();
      runtime.handlers.onWindowClose(closeWindow.dataset.windowClose as WorkspaceMenuKey);
      return;
    }
    const openTab = target.closest<HTMLElement>("[data-window-open]");
    if (openTab?.dataset.windowOpen) {
      runtime.handlers.onWindowOpen(openTab.dataset.windowOpen as WorkspaceMenuKey);
      return;
    }
    const tab = target.closest<HTMLElement>("[data-window-tab]");
    if (tab?.dataset.windowTab) {
      runtime.handlers.onWindowOpen(tab.dataset.windowTab as WorkspaceMenuKey);
      return;
    }
    const trigger = target.closest<HTMLElement>("[data-desktop-menu]");
    if (trigger?.dataset.desktopMenu) {
      event.stopPropagation();
      const expanded = trigger.getAttribute("aria-expanded") === "true";
      if (expanded) closeMenus(host);
      else openMenu(host, trigger.dataset.desktopMenu);
      return;
    }
    const commandTarget = target.closest<HTMLElement>("[data-desktop-command], [data-desktop-window]");
    if (commandTarget) {
      if (commandTarget.hasAttribute("disabled")) return;
      const { command, window: windowKey } = commandForTarget(target);
      closeMenus(host);
      if (command === "help.shortcuts") { openDialog(host, "shortcuts"); return; }
      if (command === "help.about") { openDialog(host, "about"); return; }
      if (windowKey) { runtime.handlers.onWindowOpen(windowKey as WorkspaceMenuKey); return; }
      if (command) runtime.handlers.onCommand(command as DesktopCommand);
      return;
    }
    if (host.contains(target)) closeMenus(host);
  });

  host.addEventListener("keydown", (event) => {
    const target = event.target as HTMLElement | null;
    if (!target) return;
    if (event.key === "Escape") {
      closeMenus(host, true);
      return;
    }
    const trigger = target.closest<HTMLElement>("[data-desktop-menu]");
    if (!trigger) return;
    const triggers = Array.from(host.querySelectorAll<HTMLElement>("[data-desktop-menu]"));
    const index = triggers.indexOf(trigger);
    if (event.key === "ArrowDown") {
      event.preventDefault();
      openMenu(host, trigger.dataset.desktopMenu ?? "", true);
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      triggers[(index + 1) % triggers.length]?.focus();
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      triggers[(index - 1 + triggers.length) % triggers.length]?.focus();
    }
  });

  host.addEventListener("keydown", (event) => {
    const runtime = runtimeByHost.get(host);
    if (!runtime) return;
    const target = event.target as HTMLElement | null;
    const typing = Boolean(target?.closest("input, textarea, select, [contenteditable=true]"));
    if (event.key === "F1") { event.preventDefault(); openDialog(host, "shortcuts"); return; }
    if (event.altKey && /^[1-9]$/.test(event.key)) {
      const key = WINDOW_ORDER[Number(event.key) - 1];
      if (key && runtime.state.openWindows.includes(key)) {
        event.preventDefault();
        runtime.handlers.onWindowOpen(key);
      }
      return;
    }
    if (!(event.ctrlKey || event.metaKey) || typing) return;
    const lower = event.key.toLowerCase();
    if (lower === "f") { event.preventDefault(); runtime.handlers.onCommand("edit.find"); return; }
    if (lower === "z") {
      if (runtime.state.capabilities.canUndoLayout) {
        event.preventDefault();
        runtime.handlers.onCommand("edit.undo");
      }
      return;
    }
    if (lower === "y") { event.preventDefault(); if (runtime.state.capabilities.canRedoLayout) runtime.handlers.onCommand("edit.redo"); return; }
    if (lower === "w") {
      if (runtime.state.capabilities.hasMultipleWindows) {
        event.preventDefault();
        runtime.handlers.onCommand("project.close");
      }
    }
  });
}

function bindDocument(): void {
  if (documentBound || typeof document === "undefined") return;
  documentBound = true;
  document.addEventListener("click", (event) => {
    const target = event.target as Node | null;
    document.querySelectorAll<HTMLElement>("[data-desktop-shell]").forEach((shell) => {
      const host = shell.parentElement;
      if (!host) return;
      if (!target || !host.contains(target)) closeMenus(host);
    });
  });
}

if (typeof document !== "undefined") bindDocument();
