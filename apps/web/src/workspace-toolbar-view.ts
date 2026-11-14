import { workspaceIcon } from "./workspace-icons.js";
import {
  TOOLBAR_COMMANDS,
  TOOLBAR_FAMILIES,
  toolbarCommand,
  toolbarCommandActive,
  toolbarCommandDisabledReason,
  toolbarCommandsForFamily,
  type ToolbarCommandDefinition,
  type ToolbarContext,
} from "./workspace-toolbar-registry.js";
import {
  createCustomFamily,
  deleteCustomFamily,
  familiesForRail,
  familyDisplayName,
  findToolbarFamily,
  isCustomFamilyId,
  moveButton,
  renameButton,
  renameCustomFamily,
  resetAllToolbars,
  resetFamily,
  setButtonVisible,
  setFamilyRail,
  setFamilyStyle,
  setFamilyVisible,
  setToolbarsLocked,
  toggleSeparator,
  type ToolbarFamilyState,
  type ToolbarIconStyle,
  type ToolbarRail,
  type ToolbarWorkspaceConfig,
} from "./workspace-toolbar-config.js";

/**
 * Renders and drives both tool rails. The rails are not navigation menus with
 * icons: each family is an independently configurable toolbar that supports
 * add/remove, reordering, cross-rail moves, docking, custom toolbars and a
 * persisted per-user, per-workspace configuration.
 */

export type ToolbarRailSession = {
  config: ToolbarWorkspaceConfig;
  context: ToolbarContext;
  translate: (english: string, persian: string) => string;
  onChange: (next: ToolbarWorkspaceConfig) => void;
  direction: "ltr" | "rtl";
};

const sessions = new WeakMap<HTMLElement, ToolbarRailSession>();
const boundContainers = new WeakSet<HTMLElement>();

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function tr(session: ToolbarRailSession, english: string, persian: string): string {
  return session.translate(english, persian);
}

function familyName(family: ToolbarFamilyState, session: ToolbarRailSession): string {
  return familyDisplayName(family, (en, fa) => tr(session, en, fa));
}

function buttonLabel(
  family: ToolbarFamilyState,
  command: ToolbarCommandDefinition,
  session: ToolbarRailSession,
): string {
  const override = family.buttons.find((button) => button.id === command.id)?.label;
  return override || tr(session, command.label.en, command.label.fa);
}

function targetAttributes(command: ToolbarCommandDefinition, disabled: boolean): string {
  if (disabled) return "";
  switch (command.target.kind) {
    case "command": return ` data-desktop-command="${escapeHtml(command.target.command)}"`;
    case "window": return ` data-desktop-window="${escapeHtml(command.target.window)}"`;
    case "rail": return ` data-rail-action="${escapeHtml(command.target.action)}"${command.target.action === "navigation" ? " data-nav-flyout-toggle" : ""}`;
    case "fullscreen": return ' data-fullscreen-toggle="true"';
    default: return "";
  }
}

function renderButton(
  family: ToolbarFamilyState,
  command: ToolbarCommandDefinition,
  session: ToolbarRailSession,
): string {
  const reason = toolbarCommandDisabledReason(command, session.context);
  const active = toolbarCommandActive(command, session.context);
  const disabled = Boolean(reason);
  const label = buttonLabel(family, command, session);
  const title = disabled && reason
    ? tr(session, reason.en, reason.fa)
    : tr(session, command.tooltip.en, command.tooltip.fa);
  const icon = family.style === "text" ? "" : workspaceIcon(command.icon);
  const text = family.style === "icon" ? "" : `<span class="cp-tool-label">${escapeHtml(label)}</span>`;
  return `<button type="button" class="cp-tool-btn cp-rail-button${active ? " is-active" : ""}${family.style !== "icon" ? " has-text" : ""}" data-tool-rail-button data-tool-family-id="${escapeHtml(family.id)}" data-tool-command-id="${escapeHtml(command.id)}" data-tool-style="${family.style}"${targetAttributes(command, disabled)} title="${escapeHtml(title)}" aria-label="${escapeHtml(label)}" aria-describedby="cp-tool-reason-${escapeHtml(family.id)}-${escapeHtml(command.id)}"${active ? ' aria-pressed="true"' : ""}${disabled ? ' aria-disabled="true" data-tool-disabled="true"' : ""}>
    <span class="cp-tool-grip" data-tool-grip aria-hidden="true">${workspaceIcon("grip")}</span>
    ${icon}${text}
    ${disabled && reason ? `<span class="cp-tool-reason" id="cp-tool-reason-${escapeHtml(family.id)}-${escapeHtml(command.id)}" hidden>${escapeHtml(tr(session, reason.en, reason.fa))}</span>` : ""}
  </button>`;
}

function renderFamily(
  family: ToolbarFamilyState,
  session: ToolbarRailSession,
  rail: ToolbarRail,
): string {
  const name = familyName(family, session);
  const custom = Boolean(family.custom) || isCustomFamilyId(family.id);
  const visibleButtons = family.buttons.filter((button) => button.visible);
  const buttons = visibleButtons.map((button) => {
    const command = toolbarCommand(button.id);
    if (!command) return "";
    const separator = family.separators.includes(button.id)
      ? '<span class="cp-tool-separator" role="separator" aria-orientation="vertical"></span>'
      : "";
    return `${separator}${renderButton(family, command, session)}`;
  }).join("");
  const addRemove = tr(session, "Add or Remove Buttons", "افزودن یا حذف دکمه‌ها");
  const moveName = tr(session, `Move ${name}`, `جابه‌جایی ${name}`);
  const horizontal = rail === "floating";
  const showName = horizontal || family.style !== "icon";
  return `<div class="cp-tool-family${horizontal ? " is-horizontal" : ""}${custom ? " is-custom" : ""}" data-tool-family="${escapeHtml(family.id)}" data-tool-family-rail="${escapeHtml(family.rail)}"${custom ? ' data-tool-custom="true"' : ""} role="group" aria-label="${escapeHtml(name)}" title="${escapeHtml(name)}">
    <div class="cp-tool-family-head">
      <button type="button" class="cp-tool-family-handle" data-tool-family-handle title="${escapeHtml(moveName)}" aria-label="${escapeHtml(moveName)}">${workspaceIcon("grip")}</button>
      ${showName ? `<span class="cp-tool-family-name">${escapeHtml(name)}</span>` : ""}
    </div>
    <div class="cp-tool-family-buttons">
      ${buttons || `<span class="cp-tool-family-empty" data-tool-family-empty>${escapeHtml(tr(session, "No buttons", "بدون دکمه"))}</span>`}
    </div>
    <button type="button" class="cp-tool-add-remove" data-tool-add-remove aria-haspopup="menu" aria-expanded="false" title="${escapeHtml(`${addRemove} — ${name}`)}" aria-label="${escapeHtml(`${addRemove} — ${name}`)}">${workspaceIcon("chevronDown")}</button>
  </div>`;
}

function visibleFamilies(session: ToolbarRailSession, rail: ToolbarRail): ToolbarFamilyState[] {
  return familiesForRail(session.config, rail).filter((family) => family.visible);
}

function railHtml(
  rail: Exclude<ToolbarRail, "floating">,
  session: ToolbarRailSession,
): string {
  const side = rail === "left" ? tr(session, "Left tool rail", "ریل ابزار چپ") : tr(session, "Right tool rail", "ریل ابزار راست");
  const customize = tr(session, "Customize toolbars", "سفارشی‌سازی نوارهای ابزار");
  const families = visibleFamilies(session, rail);
  const locked = session.config.locked;
  return `<div class="cp-tool-rail-scroll">
    ${families.map((family) => renderFamily(family, session, rail)).join("")}
    <button type="button" class="cp-tool-rail-menu" data-tool-rail-menu title="${escapeHtml(customize)}" aria-label="${escapeHtml(customize)}" aria-haspopup="menu">${workspaceIcon(locked ? "lock" : "settings")}</button>
  </div>`;
}

export type ToolbarRailMarkup = {
  left: string;
  right: string;
  floating: string;
  hasFloating: boolean;
  leftWide: boolean;
  rightWide: boolean;
};

/** Render the inner markup of both rails and the docked horizontal toolbars. */
export function renderToolbarRails(container: HTMLElement, session: ToolbarRailSession): ToolbarRailMarkup {
  sessions.set(container, session);
  bindToolbarEvents(container);
  const left = railHtml("left", session);
  const right = railHtml("right", session);
  const floatingFamilies = visibleFamilies(session, "floating");
  const dockLabel = tr(session, "Docked toolbars", "نوارهای ابزار لنگرانداخته");
  const dropLabel = tr(session, "Drop a toolbar here to dock it above the workspace", "برای لنگرانداختن بالای محیط کار، نوار ابزار را اینجا رها کنید");
  const floating = `<div class="cp-toolbar-dock" data-toolbar-dock aria-label="${escapeHtml(dockLabel)}">
    <span class="cp-toolbar-dock-hint" data-toolbar-dock-hint hidden>${escapeHtml(dropLabel)}</span>
    ${floatingFamilies.map((family) => renderFamily(family, session, "floating")).join("")}
  </div>`;
  return {
    left,
    right,
    floating,
    hasFloating: floatingFamilies.length > 0,
    leftWide: visibleFamilies(session, "left").some((family) => family.style !== "icon"),
    rightWide: visibleFamilies(session, "right").some((family) => family.style !== "icon"),
  };
}

/** True when the family has a visible button for the command (used by tests). */
export function toolbarButtonVisible(
  config: ToolbarWorkspaceConfig,
  familyId: string,
  commandId: string,
): boolean {
  return Boolean(findToolbarFamily(config, familyId)?.buttons.find((button) => button.id === commandId && button.visible));
}

// ---------------------------------------------------------------------------
// Popover menus
// ---------------------------------------------------------------------------

type MenuKind = "rail" | "family" | "button" | "add-remove";

type OpenMenu = {
  element: HTMLDivElement;
  container: HTMLElement;
  kind: MenuKind;
  rail: ToolbarRail;
  familyId?: string;
  commandId?: string;
  focusKey?: string;
  anchor: DOMRect | { left: number; top: number; right: number; bottom: number };
};

let openMenuState: OpenMenu | null = null;
let outsideHandler: ((event: MouseEvent) => void) | null = null;
let escapeHandler: ((event: KeyboardEvent) => void) | null = null;

function currentSession(container: HTMLElement): ToolbarRailSession | null {
  return sessions.get(container) ?? null;
}

function applyConfig(container: HTMLElement, next: ToolbarWorkspaceConfig): void {
  const record = currentSession(container);
  if (!record) return;
  record.config = next;
  record.onChange(next);
  // The customize dialog is body-level and survives the workspace re-render;
  // repaint it from the new configuration so its check marks stay truthful.
  if (customizeDialog) renderCustomizeDialog();
}

function closeMenu(): void {
  if (!openMenuState) return;
  openMenuState.element.remove();
  openMenuState = null;
  if (outsideHandler) document.removeEventListener("mousedown", outsideHandler, true);
  if (escapeHandler) document.removeEventListener("keydown", escapeHandler, true);
  outsideHandler = null;
  escapeHandler = null;
  document.querySelectorAll("[data-tool-add-remove][aria-expanded='true'], [data-tool-rail-menu][aria-expanded='true']").forEach((button) => {
    button.setAttribute("aria-expanded", "false");
  });
}

function menuItem(
  label: string,
  action: string,
  options: {
    key?: string;
    checked?: boolean;
    disabled?: boolean;
    dataset?: Record<string, string>;
    hint?: string;
    separatorBefore?: boolean;
  } = {},
): string {
  const attrs = Object.entries(options.dataset ?? {})
    .map(([key, value]) => ` data-${escapeHtml(key)}="${escapeHtml(value)}"`)
    .join("");
  const check = options.checked === undefined ? "" : `<span class="cp-tool-menu-check" aria-hidden="true">${options.checked ? "✓" : ""}</span>`;
  return `${options.separatorBefore ? '<div class="cp-tool-menu-separator" role="separator"></div>' : ""}<button type="button" class="cp-tool-menu-item${options.checked ? " is-checked" : ""}" role="${options.checked === undefined ? "menuitem" : "menuitemcheckbox"}"${options.checked === undefined ? "" : ` aria-checked="${options.checked}"`} data-tool-menu-action="${escapeHtml(action)}"${options.key ? ` data-tool-focus-key="${escapeHtml(options.key)}"` : ""}${attrs}${options.disabled ? ' disabled aria-disabled="true"' : ""}>
    ${check}<span class="cp-tool-menu-label">${escapeHtml(label)}</span>${options.hint ? `<span class="cp-tool-menu-hint">${escapeHtml(options.hint)}</span>` : ""}
  </button>`;
}

function menuHeading(label: string): string {
  return `<div class="cp-tool-menu-heading">${escapeHtml(label)}</div>`;
}

function familiesByRail(session: ToolbarRailSession, rail: ToolbarRail): ToolbarFamilyState[] {
  return familiesForRail(session.config, rail);
}

function railLabel(session: ToolbarRailSession, rail: ToolbarRail): string {
  if (rail === "left") return tr(session, "Left rail", "ریل چپ");
  if (rail === "right") return tr(session, "Right rail", "ریل راست");
  return tr(session, "Docked above workspace", "لنگرانداخته بالای محیط کار");
}

function addRemoveContent(session: ToolbarRailSession, family: ToolbarFamilyState): string {
  const name = familyName(family, session);
  const commands = family.custom
    ? TOOLBAR_COMMANDS
    : toolbarCommandsForFamily(family.id);
  const groups = new Map<string, ToolbarCommandDefinition[]>();
  for (const command of commands) {
    const key = family.custom ? command.families[0] ?? "tools" : family.id;
    const list = groups.get(key) ?? [];
    list.push(command);
    groups.set(key, list);
  }
  const sections: string[] = [];
  for (const [groupId, list] of groups) {
    const definition = TOOLBAR_FAMILIES.find((item) => item.id === groupId);
    if (family.custom && definition) {
      sections.push(menuHeading(tr(session, definition.label.en, definition.label.fa)));
    }
    for (const command of list) {
      const state = family.buttons.find((button) => button.id === command.id);
      const checked = Boolean(state?.visible);
      const blocked = command.adminOnly && !session.context.capabilities.canAdminister;
      sections.push(menuItem(
        tr(session, command.label.en, command.label.fa),
        "toggle-button",
        {
          key: `cmd:${command.id}`,
          checked,
          disabled: blocked,
          dataset: { "tool-command": command.id, "tool-family": family.id },
        },
      ));
    }
  }
  const reset = tr(session, "Reset Toolbar", "بازنشانی نوار ابزار");
  return `${menuHeading(tr(session, `Add or Remove Buttons — ${name}`, `افزودن یا حذف دکمه‌ها — ${name}`))}
    <div class="cp-tool-menu-scroll" data-tool-menu-scroll>${sections.join("")}</div>
    <div class="cp-tool-menu-separator" role="separator"></div>
    ${menuItem(reset, "reset-family", { key: "reset-family", dataset: { "tool-family": family.id }, hint: tr(session, "Restores this toolbar only", "فقط این نوار ابزار را بازمی‌گرداند") })}`;
}

function railContent(session: ToolbarRailSession, rail: ToolbarRail): string {
  const families = familiesByRail(session, rail);
  const visibility = families.map((family) => menuItem(
    familyName(family, session),
    "toggle-family",
    {
      key: `family:${family.id}`,
      checked: family.visible,
      dataset: { "tool-family": family.id },
    },
  )).join("");
  const addSections = families.map((family) => menuItem(
    tr(session, `Add or Remove Buttons — ${familyName(family, session)}`, `افزودن یا حذف دکمه‌ها — ${familyName(family, session)}`),
    "open-add-remove",
    { key: `add:${family.id}`, dataset: { "tool-family": family.id } },
  )).join("");
  const locked = session.config.locked;
  const create = tr(session, "Create Custom Toolbar…", "ایجاد نوار ابزار سفارشی…");
  return `${menuHeading(tr(session, "Customize Toolbars", "سفارشی‌سازی نوارهای ابزار"))}
    ${menuHeading(railLabel(session, rail))}
    ${visibility}
    <div class="cp-tool-menu-separator" role="separator"></div>
    ${menuHeading(tr(session, "Add or Remove Buttons", "افزودن یا حذف دکمه‌ها"))}
    ${addSections}
    <div class="cp-tool-menu-separator" role="separator"></div>
    ${menuItem(tr(session, "Customize…", "سفارشی‌سازی…"), "open-customize", { key: "customize" })}
    ${menuItem(locked ? tr(session, "Unlock Toolbars", "بازکردن قفل نوارهای ابزار") : tr(session, "Lock Toolbars", "قفل نوارهای ابزار"), "toggle-lock", { key: "lock", checked: locked })}
    ${menuItem(tr(session, "Reset All Toolbars", "بازنشانی همهٔ نوارهای ابزار"), "reset-all", { key: "reset-all" })}
    ${menuItem(create, "create-custom", { key: "create-custom" })}
    ${customToolbarActions(session, session.config.families)}`;
}

function customToolbarActions(session: ToolbarRailSession, families: readonly ToolbarFamilyState[]): string {
  const custom = families.filter((family) => family.custom);
  if (!custom.length) return "";
  return `<div class="cp-tool-menu-separator" role="separator"></div>
    ${menuHeading(tr(session, "Custom toolbars", "نوارهای ابزار سفارشی"))}
    ${custom.map((family) => menuItem(
      familyName(family, session),
      "rename-custom",
      { key: `rename:${family.id}`, dataset: { "tool-family": family.id }, hint: tr(session, "Rename", "تغییر نام") },
    )).join("")}`;
}

function buttonContent(
  session: ToolbarRailSession,
  family: ToolbarFamilyState,
  command: ToolbarCommandDefinition,
): string {
  const label = buttonLabel(family, command, session);
  const index = family.buttons.findIndex((button) => button.id === command.id);
  const isCustom = Boolean(family.custom);
  const currentLabel = family.buttons.find((button) => button.id === command.id)?.label ?? "";
  const actions = command.actions ?? ["move", "hide", "rename", "style", "group", "reset"];
  const parts: string[] = [`${menuHeading(`${label} — ${familyName(family, session)}`)}`];
  if (actions.includes("move")) {
    parts.push(menuItem(tr(session, "Move Up", "انتقال به بالا"), "move-button", { key: "move-up", disabled: index <= 0, dataset: { "tool-command": command.id, "tool-family": family.id, "tool-direction": "-1" } }));
    parts.push(menuItem(tr(session, "Move Down", "انتقال به پایین"), "move-button", { key: "move-down", disabled: index < 0 || index >= family.buttons.length - 1, dataset: { "tool-command": command.id, "tool-family": family.id, "tool-direction": "1" } }));
    parts.push(menuHeading(tr(session, "Move to toolbar", "انتقال به نوار ابزار")));
    for (const target of session.config.families) {
      if (target.id === family.id) continue;
      const commandSupported = target.custom || command.families.includes(target.id);
      parts.push(menuItem(
        `${familyName(target, session)} (${railLabel(session, target.rail)})`,
        "move-to-family",
        {
          key: `move:${target.id}`,
          disabled: !commandSupported,
          dataset: { "tool-command": command.id, "tool-family": family.id, "tool-target": target.id },
        },
      ));
    }
  }
  parts.push('<div class="cp-tool-menu-separator" role="separator"></div>');
  if (actions.includes("hide")) {
    parts.push(menuItem(isCustom ? tr(session, "Delete Button", "حذف دکمه") : tr(session, "Hide Button", "پنهان‌کردن دکمه"), "hide-button", { key: "hide", dataset: { "tool-command": command.id, "tool-family": family.id } }));
  }
  if (actions.includes("rename")) {
    parts.push(`<form class="cp-tool-menu-form" data-tool-menu-form="rename" data-tool-command="${escapeHtml(command.id)}" data-tool-family="${escapeHtml(family.id)}">
      <label class="cp-tool-menu-form-label" for="cp-tool-rename-input">${escapeHtml(tr(session, "Rename button", "تغییر نام دکمه"))}</label>
      <input id="cp-tool-rename-input" name="label" type="text" maxlength="80" value="${escapeHtml(currentLabel || label)}" data-tool-rename-input autocomplete="off" />
      <div class="cp-tool-menu-form-actions">
        <button type="submit" class="cp-tool-menu-primary" data-tool-focus-key="rename-apply">${escapeHtml(tr(session, "Apply", "اعمال"))}</button>
        <button type="button" data-tool-menu-action="reset-rename" data-tool-command="${escapeHtml(command.id)}" data-tool-family="${escapeHtml(family.id)}" data-tool-focus-key="rename-reset">${escapeHtml(tr(session, "Reset", "بازنشانی"))}</button>
      </div>
    </form>`);
  }
  if (actions.includes("style")) {
    parts.push(menuHeading(tr(session, "Button style", "سبک دکمه")));
    for (const style of ["icon", "text", "both"] as const) {
      const labelStyle = style === "icon"
        ? tr(session, "Default Style (Icon)", "سبک پیش‌فرض (نماد)")
        : style === "text"
          ? tr(session, "Text Only", "فقط متن")
          : tr(session, "Image and Text", "نماد و متن");
      parts.push(menuItem(labelStyle, "style-family", { key: `style:${style}`, checked: family.style === style, dataset: { "tool-family": family.id, "tool-style": style } }));
    }
  }
  if (actions.includes("group")) {
    parts.push(menuItem(tr(session, "Begin a Group", "شروع یک گروه"), "toggle-separator", { key: "separator", checked: family.separators.includes(command.id), dataset: { "tool-command": command.id, "tool-family": family.id } }));
  }
  if (actions.includes("reset")) {
    parts.push(menuItem(tr(session, "Reset Toolbar", "بازنشانی نوار ابزار"), "reset-family", { key: "reset", dataset: { "tool-family": family.id } }));
  }
  if (isCustom) {
    parts.push(menuItem(tr(session, "Delete Custom Toolbar", "حذف نوار ابزار سفارشی"), "delete-custom", { key: "delete-custom", dataset: { "tool-family": family.id } }));
  }
  return parts.join("");
}

function menuContent(state: OpenMenu, session: ToolbarRailSession): { title: string; body: string } {
  if (state.kind === "add-remove" && state.familyId) {
    const family = findToolbarFamily(session.config, state.familyId);
    if (!family) return { title: "", body: "" };
    return { title: familyName(family, session), body: addRemoveContent(session, family) };
  }
  if (state.kind === "button" && state.familyId && state.commandId) {
    const family = findToolbarFamily(session.config, state.familyId);
    const command = toolbarCommand(state.commandId);
    if (!family || !command) return { title: "", body: "" };
    return { title: familyName(family, session), body: buttonContent(session, family, command) };
  }
  return { title: railLabel(session, state.rail), body: railContent(session, state.rail) };
}

function focusMenuTarget(): void {
  if (!openMenuState) return;
  const menu = openMenuState.element;
  const key = openMenuState.focusKey;
  const target = key ? menu.querySelector<HTMLElement>(`[data-tool-focus-key="${CSS.escape(key)}"]`) : null;
  const fallback = menu.querySelector<HTMLElement>(".cp-tool-menu-item:not([disabled]), .cp-tool-menu-form input");
  (target ?? fallback)?.focus({ preventScroll: true });
  openMenuState.focusKey = undefined;
}

function placeMenu(menu: HTMLDivElement, state: OpenMenu, session: ToolbarRailSession): void {
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  const rect = menu.getBoundingClientRect();
  const anchor = state.anchor;
  let left: number;
  let top: number;
  if (state.kind === "rail" || state.kind === "family" || state.kind === "button") {
    // Rail menus open toward the workspace, never over the rail itself.
    left = state.rail === "right" ? anchor.left - rect.width - 6 : anchor.right + 6;
  } else {
    left = state.rail === "right" ? anchor.left - rect.width - 6 : anchor.right + 6;
  }
  if (session.direction === "rtl") {
    // Mirror only when the computed position would leave the viewport.
    if (left < 8) left = Math.min(viewportWidth - rect.width - 8, anchor.right + 6);
    if (left + rect.width > viewportWidth - 8) left = Math.max(8, anchor.left - rect.width - 6);
  }
  top = Math.min(Math.max(8, anchor.top), viewportHeight - rect.height - 8);
  left = Math.min(Math.max(8, left), viewportWidth - rect.width - 8);
  menu.style.left = `${Math.round(left)}px`;
  menu.style.top = `${Math.round(top)}px`;
}

function renderMenu(): void {
  if (!openMenuState) return;
  const session = currentSession(openMenuState.container);
  if (!session) {
    closeMenu();
    return;
  }
  const content = menuContent(openMenuState, session);
  const menu = openMenuState.element;
  menu.setAttribute("dir", session.direction);
  menu.innerHTML = `<div class="cp-tool-menu-inner" data-tool-menu-inner>${content.body}</div>`;
  placeMenu(menu, openMenuState, session);
  focusMenuTarget();
}

function openMenu(
  container: HTMLElement,
  kind: MenuKind,
  rail: ToolbarRail,
  anchor: DOMRect,
  options: { familyId?: string; commandId?: string; focusKey?: string } = {},
): void {
  closeMenu();
  const session = currentSession(container);
  if (!session) return;
  const menu = document.createElement("div");
  menu.className = "cp-tool-menu";
  menu.setAttribute("data-tool-menu", kind);
  menu.setAttribute("role", "menu");
  menu.setAttribute("dir", session.direction);
  document.body.appendChild(menu);
  openMenuState = { element: menu, container, kind, rail, anchor, ...options };
  const content = menuContent(openMenuState, session);
  menu.setAttribute("aria-label", content.title || tr(session, "Toolbar menu", "منوی نوار ابزار"));
  menu.innerHTML = `<div class="cp-tool-menu-inner" data-tool-menu-inner>${content.body}</div>`;
  placeMenu(menu, openMenuState, session);
  const anchorButton = kind === "add-remove"
    ? container.querySelector<HTMLElement>(`[data-tool-family="${CSS.escape(options.familyId ?? "")}"] [data-tool-add-remove]`)
    : null;
  anchorButton?.setAttribute("aria-expanded", "true");
  document.querySelectorAll<HTMLElement>("[data-tool-rail-menu]").forEach((button) => button.setAttribute("aria-expanded", "true"));
  bindMenuEvents(menu);
  focusMenuTarget();
  outsideHandler = (event: MouseEvent) => {
    if (!openMenuState) return;
    const node = event.target as Node | null;
    if (node && (menu.contains(node) || (node instanceof Element && node.closest("[data-tool-rail]")))) return;
    closeMenu();
  };
  escapeHandler = (event: KeyboardEvent) => {
    if (event.key === "Escape") {
      event.stopPropagation();
      closeMenu();
    }
  };
  document.addEventListener("mousedown", outsideHandler, true);
  document.addEventListener("keydown", escapeHandler, true);
}

function menuFormValues(menu: HTMLElement): { rename?: string } {
  const input = menu.querySelector<HTMLInputElement>("[data-tool-rename-input]");
  return { rename: input?.value };
}

function bindMenuEvents(menu: HTMLDivElement): void {
  menu.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!openMenuState) return;
    const form = (event.target as HTMLElement).closest<HTMLFormElement>("[data-tool-menu-form]");
    if (!form) return;
    const session = currentSession(openMenuState.container);
    if (!session) return;
    const familyId = form.dataset.toolFamily ?? openMenuState.familyId ?? "";
    const commandId = form.dataset.toolCommand ?? openMenuState.commandId ?? "";
    const value = menuFormValues(menu).rename ?? "";
    applyConfig(openMenuState.container, renameButton(session.config, familyId, commandId, value || null));
    openMenuState.focusKey = "rename-apply";
    renderMenu();
  });
  menu.addEventListener("click", (event) => {
    const target = (event.target as HTMLElement | null)?.closest<HTMLElement>("[data-tool-menu-action]");
    if (!target || !openMenuState) return;
    event.preventDefault();
    event.stopPropagation();
    const action = target.dataset.toolMenuAction ?? "";
    const key = target.getAttribute("data-tool-focus-key") ?? undefined;
    handleMenuAction(action, target.dataset, key);
  });
  menu.addEventListener("keydown", (event) => {
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp" && event.key !== "Home" && event.key !== "End") return;
    const items = [...menu.querySelectorAll<HTMLElement>(".cp-tool-menu-item:not([disabled]), .cp-tool-menu-form input, .cp-tool-menu-form button:not([disabled])")];
    if (!items.length) return;
    const index = items.indexOf(document.activeElement as HTMLElement);
    let next = 0;
    if (event.key === "ArrowDown") next = index < 0 ? 0 : (index + 1) % items.length;
    else if (event.key === "ArrowUp") next = index <= 0 ? items.length - 1 : index - 1;
    else if (event.key === "End") next = items.length - 1;
    items[next]?.focus({ preventScroll: true });
    event.preventDefault();
  });
}

function handleMenuAction(action: string, dataset: DOMStringMap, focusKey?: string): void {
  if (!openMenuState) return;
  const state = openMenuState;
  const session = currentSession(state.container);
  if (!session) return;
  const familyId = dataset.toolFamily ?? state.familyId ?? "";
  const commandId = dataset.toolCommand ?? state.commandId ?? "";
  const family = familyId ? findToolbarFamily(session.config, familyId) : undefined;
  const keepFocus = (key?: string) => { state.focusKey = key ?? focusKey; };

  switch (action) {
    case "toggle-family":
      applyConfig(state.container, setFamilyVisible(session.config, familyId, !family?.visible));
      keepFocus();
      renderMenu();
      return;
    case "toggle-button": {
      if (!family) return;
      const button = family.buttons.find((item) => item.id === commandId);
      applyConfig(state.container, setButtonVisible(session.config, familyId, commandId, !button?.visible));
      keepFocus();
      // When a toolbar family starts empty, adding its first button makes it
      // visible in place without closing the menu.
      renderMenu();
      return;
    }
    case "open-add-remove":
      state.kind = "add-remove";
      state.familyId = familyId;
      state.commandId = undefined;
      keepFocus();
      renderMenu();
      return;
    case "open-customize":
      closeMenu();
      openCustomizeDialog(state.container);
      return;
    case "toggle-lock":
      applyConfig(state.container, setToolbarsLocked(session.config, !session.config.locked));
      keepFocus();
      renderMenu();
      return;
    case "reset-family":
      applyConfig(state.container, resetFamily(session.config, familyId));
      keepFocus();
      renderMenu();
      return;
    case "reset-all":
      applyConfig(state.container, resetAllToolbars(session.config));
      keepFocus();
      renderMenu();
      return;
    case "move-button": {
      if (!family) return;
      const index = family.buttons.findIndex((button) => button.id === commandId);
      const direction = dataset.toolDirection === "-1" ? -1 : 1;
      const target = index + direction;
      if (index < 0 || target < 0 || target >= family.buttons.length) return;
      applyConfig(state.container, moveButton(session.config, commandId, familyId, familyId, target));
      keepFocus(direction < 0 ? "move-up" : "move-down");
      renderMenu();
      return;
    }
    case "move-to-family": {
      const targetId = dataset.toolTarget ?? "";
      const targetFamily = findToolbarFamily(session.config, targetId);
      if (!targetFamily) return;
      applyConfig(state.container, moveButton(session.config, commandId, familyId, targetId, targetFamily.buttons.length));
      keepFocus(`move:${targetId}`);
      // The button now belongs to another toolbar; keep the icon menu open on
      // the destination so repeated moves are possible.
      state.familyId = targetId;
      renderMenu();
      return;
    }
    case "hide-button": {
      if (!family) return;
      if (family.custom) {
        const next = {
          ...session.config,
          families: session.config.families.map((item) => (item.id === familyId
            ? { ...item, buttons: item.buttons.filter((button) => button.id !== commandId), separators: item.separators.filter((id) => id !== commandId) }
            : item)),
        };
        applyConfig(state.container, next);
        closeMenu();
        return;
      }
      applyConfig(state.container, setButtonVisible(session.config, familyId, commandId, false));
      closeMenu();
      return;
    }
    case "style-family":
      applyConfig(state.container, setFamilyStyle(session.config, familyId, (dataset.toolStyle as ToolbarIconStyle) ?? "icon"));
      keepFocus(`style:${dataset.toolStyle}`);
      renderMenu();
      return;
    case "toggle-separator":
      applyConfig(state.container, toggleSeparator(session.config, familyId, commandId));
      keepFocus("separator");
      renderMenu();
      return;
    case "reset-rename":
      applyConfig(state.container, renameButton(session.config, familyId, commandId, null));
      keepFocus("rename-reset");
      renderMenu();
      return;
    case "rename-custom": {
      const name = window.prompt?.(
        session.translate("Rename toolbar", "تغییر نام نوار ابزار"),
        family?.name ?? "",
      );
      if (name?.trim()) applyConfig(state.container, renameCustomFamily(session.config, familyId, name));
      keepFocus(`rename:${familyId}`);
      renderMenu();
      return;
    }
    case "delete-custom":
      applyConfig(state.container, deleteCustomFamily(session.config, familyId));
      closeMenu();
      return;
    case "create-custom":
      state.kind = "rail";
      state.familyId = undefined;
      openCustomizeDialog(state.container, { create: true });
      closeMenu();
      return;
    default:
      return;
  }
}

// ---------------------------------------------------------------------------
// Customize dialog (stays open across configuration changes)
// ---------------------------------------------------------------------------

let customizeDialog: HTMLDialogElement | null = null;
let customizeContainer: HTMLElement | null = null;
let customizeFocusCreate = false;

function closeCustomizeDialog(): void {
  customizeDialog?.close?.();
  customizeDialog?.remove();
  customizeDialog = null;
  customizeContainer = null;
}

function customizeSection(session: ToolbarRailSession, families: ToolbarFamilyState[], rail: ToolbarRail): string {
  const heading = railLabel(session, rail);
  return `<section class="cp-tool-customize-group" data-tool-customize-group="${rail}">
    <h3>${escapeHtml(heading)}</h3>
    ${families.length ? families.map((family, index) => `<div class="cp-tool-customize-row" data-tool-customize-family="${escapeHtml(family.id)}">
      <button type="button" class="cp-tool-customize-check${family.visible ? " is-checked" : ""}" role="menuitemcheckbox" aria-checked="${family.visible}" aria-label="${escapeHtml(tr(session, "Show toolbar", "نمایش نوار ابزار"))}" data-tool-focus-key="visible:${escapeHtml(family.id)}" data-tool-menu-action="toggle-family" data-tool-family="${escapeHtml(family.id)}"><span class="cp-tool-menu-check" aria-hidden="true">${family.visible ? "✓" : ""}</span></button>
      <span class="cp-tool-customize-name">${escapeHtml(familyName(family, session))}${family.custom ? ` <em>${escapeHtml(tr(session, "custom", "سفارشی"))}</em>` : ""}</span>
      <span class="cp-tool-customize-actions">
        <button type="button" data-tool-menu-action="move-family" data-tool-direction="-1" data-tool-family="${escapeHtml(family.id)}" title="${escapeHtml(tr(session, "Move up", "انتقال به بالا"))}" aria-label="${escapeHtml(tr(session, "Move up", "انتقال به بالا"))}"${index === 0 ? " disabled" : ""}>↑</button>
        <button type="button" data-tool-menu-action="move-family" data-tool-direction="1" data-tool-family="${escapeHtml(family.id)}" title="${escapeHtml(tr(session, "Move down", "انتقال به پایین"))}" aria-label="${escapeHtml(tr(session, "Move down", "انتقال به پایین"))}"${index === families.length - 1 ? " disabled" : ""}>↓</button>
        <button type="button" data-tool-menu-action="dock-family" data-tool-rail="left" data-tool-family="${escapeHtml(family.id)}" title="${escapeHtml(tr(session, "Move to left rail", "انتقال به ریل چپ"))}">L</button>
        <button type="button" data-tool-menu-action="dock-family" data-tool-rail="right" data-tool-family="${escapeHtml(family.id)}" title="${escapeHtml(tr(session, "Move to right rail", "انتقال به ریل راست"))}">R</button>
        <button type="button" data-tool-menu-action="dock-family" data-tool-rail="floating" data-tool-family="${escapeHtml(family.id)}" title="${escapeHtml(tr(session, "Dock above workspace", "لنگرانداختن بالای محیط کار"))}">D</button>
        <button type="button" data-tool-menu-action="open-add-remove" data-tool-family="${escapeHtml(family.id)}" title="${escapeHtml(tr(session, "Add or Remove Buttons", "افزودن یا حذف دکمه‌ها"))}">…</button>
        <button type="button" data-tool-menu-action="reset-family" data-tool-family="${escapeHtml(family.id)}" title="${escapeHtml(tr(session, "Reset Toolbar", "بازنشانی نوار ابزار"))}">↺</button>
        ${family.custom ? `<button type="button" data-tool-menu-action="delete-custom" data-tool-family="${escapeHtml(family.id)}" title="${escapeHtml(tr(session, "Delete Custom Toolbar", "حذف نوار ابزار سفارشی"))}">×</button>` : ""}
      </span>
    </div>`).join("") : `<p class="cp-tool-customize-empty">${escapeHtml(tr(session, "No toolbars on this rail", "نوار ابزاری روی این ریل نیست"))}</p>`}
  </section>`;
}

function renderCustomizeDialog(): void {
  if (!customizeDialog || !customizeContainer) return;
  const session = currentSession(customizeContainer);
  if (!session) {
    closeCustomizeDialog();
    return;
  }
  const body = customizeDialog.querySelector<HTMLElement>("[data-tool-customize-body]");
  if (!body) return;
  body.innerHTML = `${customizeSection(session, familiesForRail(session.config, "left"), "left")}
    ${customizeSection(session, familiesForRail(session.config, "right"), "right")}
    ${customizeSection(session, familiesForRail(session.config, "floating"), "floating")}
    <section class="cp-tool-customize-create">
      <h3>${escapeHtml(tr(session, "Create Custom Toolbar", "ایجاد نوار ابزار سفارشی"))}</h3>
      <form data-tool-customize-create>
        <label for="cp-tool-custom-name">${escapeHtml(tr(session, "Toolbar name", "نام نوار ابزار"))}</label>
        <input id="cp-tool-custom-name" name="name" type="text" maxlength="80" placeholder="${escapeHtml(tr(session, "Custom Toolbar", "نوار ابزار سفارشی"))}" autocomplete="off" />
        <button type="submit">${escapeHtml(tr(session, "Create", "ایجاد"))}</button>
      </form>
      <div class="cp-tool-customize-footer">
        <button type="button" data-tool-menu-action="toggle-lock">${escapeHtml(session.config.locked ? tr(session, "Unlock Toolbars", "بازکردن قفل نوارهای ابزار") : tr(session, "Lock Toolbars", "قفل نوارهای ابزار"))}</button>
        <button type="button" data-tool-menu-action="reset-all">${escapeHtml(tr(session, "Reset All Toolbars", "بازنشانی همهٔ نوارهای ابزار"))}</button>
        <button type="button" data-tool-customize-close>${escapeHtml(tr(session, "Close", "بستن"))}</button>
      </div>
    </section>`;
  const create = customizeDialog.querySelector<HTMLInputElement>("#cp-tool-custom-name");
  if (customizeFocusCreate) create?.focus({ preventScroll: true });
  customizeFocusCreate = false;
}

function openCustomizeDialog(container: HTMLElement, options: { create?: boolean } = {}): void {
  closeCustomizeDialog();
  customizeContainer = container;
  customizeFocusCreate = Boolean(options.create);
  const dialog = document.createElement("dialog");
  dialog.className = "cp-tool-customize";
  dialog.setAttribute("data-tool-customize-dialog", "true");
  dialog.innerHTML = `<div class="cp-tool-customize-head">
      <h2>${escapeHtml(tr(currentSession(container)!, "Customize Toolbars", "سفارشی‌سازی نوارهای ابزار"))}</h2>
      <button type="button" class="cp-tool-customize-close" data-tool-customize-close aria-label="${escapeHtml(tr(currentSession(container)!, "Close", "بستن"))}">×</button>
    </div>
    <div class="cp-tool-customize-body" data-tool-customize-body></div>`;
  document.body.appendChild(dialog);
  customizeDialog = dialog;
  dialog.addEventListener("click", (event) => {
    const target = event.target as HTMLElement | null;
    if (!customizeContainer) return;
    if (target?.closest("[data-tool-customize-close]")) {
      closeCustomizeDialog();
      return;
    }
    const action = target?.closest<HTMLElement>("[data-tool-menu-action]");
    if (!action) return;
    const session = currentSession(customizeContainer);
    if (!session) return;
    const dataset = action.dataset;
    const familyId = dataset.toolFamily ?? "";
    switch (dataset.toolMenuAction) {
      case "toggle-family": {
        const family = findToolbarFamily(session.config, familyId);
        applyConfig(customizeContainer, setFamilyVisible(session.config, familyId, !family?.visible));
        break;
      }
      case "move-family": {
        const family = findToolbarFamily(session.config, familyId);
        if (!family) break;
        const peers = familiesForRail(session.config, family.rail);
        const index = peers.findIndex((item) => item.id === familyId);
        const target = index + (dataset.toolDirection === "-1" ? -1 : 1);
        if (index < 0 || target < 0 || target >= peers.length) break;
        applyConfig(customizeContainer, setFamilyRail(session.config, familyId, family.rail, target));
        break;
      }
      case "dock-family": {
        const rail: ToolbarRail = dataset.toolRail === "left" || dataset.toolRail === "right" ? dataset.toolRail : "floating";
        applyConfig(customizeContainer, setFamilyRail(session.config, familyId, rail));
        break;
      }
      case "open-add-remove": {
        const anchor = document.querySelector<HTMLElement>(`[data-tool-customize-family="${CSS.escape(familyId)}"]`)?.getBoundingClientRect();
        if (anchor) openMenu(customizeContainer, "add-remove", "right", anchor, { familyId });
        break;
      }
      case "reset-family":
        applyConfig(customizeContainer, resetFamily(session.config, familyId));
        break;
      case "delete-custom":
        applyConfig(customizeContainer, deleteCustomFamily(session.config, familyId));
        break;
      case "toggle-lock":
        applyConfig(customizeContainer, setToolbarsLocked(session.config, !session.config.locked));
        break;
      case "reset-all":
        applyConfig(customizeContainer, resetAllToolbars(session.config));
        break;
      default:
        break;
    }
  });
  dialog.addEventListener("submit", (event) => {
    const form = (event.target as HTMLElement).closest<HTMLFormElement>("[data-tool-customize-create]");
    if (!form || !customizeContainer) return;
    event.preventDefault();
    const session = currentSession(customizeContainer);
    if (!session) return;
    const input = form.querySelector<HTMLInputElement>("input[name='name']");
    const name = input?.value.trim() || tr(session, "Custom Toolbar", "نوار ابزار سفارشی");
    const created = createCustomFamily(session.config, name);
    const host = customizeContainer;
    applyConfig(host, created.config);
    // A modal dialog sits in the browser top layer; the Add or Remove menu for
    // the new toolbar must live above the workspace, so close the dialog first
    // and then reveal the new docked toolbar's checklist.
    const anchor = document.querySelector<HTMLElement>(`[data-tool-family="${CSS.escape(created.familyId)}"] [data-tool-add-remove]`);
    closeCustomizeDialog();
    if (host && anchor) {
      queueMicrotask(() => {
        openMenu(host, "add-remove", "floating", anchor.getBoundingClientRect(), { familyId: created.familyId });
      });
    }
  });
  dialog.addEventListener("close", () => {
    dialog.remove();
    customizeDialog = null;
    customizeContainer = null;
  });
  renderCustomizeDialog();
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
  dialog.querySelector<HTMLElement>("[data-tool-customize-close]")?.focus({ preventScroll: true });
}

// ---------------------------------------------------------------------------
// Pointer drag and drop
// ---------------------------------------------------------------------------

type DragState = {
  pointerId: number;
  kind: "button" | "family";
  container: HTMLElement;
  commandId?: string;
  familyId: string;
  startX: number;
  startY: number;
  active: boolean;
  ghost: HTMLDivElement | null;
  target: { familyId: string; index: number; rail: ToolbarRail } | null;
};

let dragState: DragState | null = null;
let dropLine: HTMLDivElement | null = null;
let suppressClick = false;

function ensureDropLine(): HTMLDivElement {
  if (dropLine) return dropLine;
  dropLine = document.createElement("div");
  dropLine.className = "cp-tool-drop-line";
  dropLine.setAttribute("data-tool-drop-line", "true");
  dropLine.hidden = true;
  document.body.appendChild(dropLine);
  return dropLine;
}

function owningContainer(element: HTMLElement): HTMLElement | null {
  let node: HTMLElement | null = element;
  while (node) {
    if (sessions.has(node)) return node;
    node = node.parentElement;
  }
  return null;
}

function startDrag(event: PointerEvent, kind: "button" | "family", element: HTMLElement, familyId: string, commandId?: string): void {
  const container = owningContainer(element);
  if (!container) return;
  const session = currentSession(container);
  if (!session || session.config.locked) return;
  dragState = {
    pointerId: event.pointerId,
    kind,
    container,
    familyId,
    commandId,
    startX: event.clientX,
    startY: event.clientY,
    active: false,
    ghost: null,
    target: null,
  };
  element.setPointerCapture?.(event.pointerId);
  const move = (moveEvent: PointerEvent) => onDragMove(moveEvent);
  const up = (upEvent: PointerEvent) => {
    element.removeEventListener("pointermove", move);
    element.removeEventListener("pointerup", up);
    element.removeEventListener("pointercancel", cancel);
    onDragEnd(upEvent);
  };
  const cancel = () => {
    element.removeEventListener("pointermove", move);
    element.removeEventListener("pointerup", up);
    element.removeEventListener("pointercancel", cancel);
    endDragVisuals();
    dragState = null;
  };
  element.addEventListener("pointermove", move);
  element.addEventListener("pointerup", up);
  element.addEventListener("pointercancel", cancel);
}

function onDragMove(event: PointerEvent): void {
  const state = dragState;
  if (!state) return;
  if (!state.active) {
    if (Math.hypot(event.clientX - state.startX, event.clientY - state.startY) < 5) return;
    state.active = true;
    const session = currentSession(state.container);
    const family = session ? findToolbarFamily(session.config, state.familyId) : undefined;
    const ghost = document.createElement("div");
    ghost.className = "cp-tool-drag-ghost";
    const command = state.commandId ? toolbarCommand(state.commandId) : null;
    ghost.innerHTML = `${command ? workspaceIcon(command.icon) : workspaceIcon("bars")}<span>${escapeHtml(command && session ? buttonLabel(family!, command, session) : family && session ? familyName(family, session) : "")}</span>`;
    document.body.appendChild(ghost);
    state.ghost = ghost;
    document.body.classList.add("cp-toolbar-dragging");
  }
  event.preventDefault();
  if (state.ghost) {
    state.ghost.style.left = `${event.clientX + 12}px`;
    state.ghost.style.top = `${event.clientY + 12}px`;
  }
  updateDropTarget(event.clientX, event.clientY);
}

function updateDropTarget(x: number, y: number): void {
  const state = dragState;
  if (!state) return;
  const hit = document.elementFromPoint(x, y) as HTMLElement | null;
  const line = ensureDropLine();
  const targetButton = hit?.closest<HTMLElement>("[data-tool-rail-button]");
  const targetFamily = hit?.closest<HTMLElement>("[data-tool-family]");
  const dock = hit?.closest<HTMLElement>("[data-toolbar-dock]");
  const rail = hit?.closest<HTMLElement>("[data-tool-rail]");
  state.target = null;
  if (state.kind === "button") {
    if (!targetFamily) { line.hidden = true; return; }
    const familyId = targetFamily.dataset.toolFamily ?? "";
    const session = currentSession(state.container);
    const family = session ? findToolbarFamily(session.config, familyId) : undefined;
    if (!family) { line.hidden = true; return; }
    let index = family.buttons.length;
    if (targetButton && targetButton.dataset.toolFamilyId === familyId) {
      const commandId = targetButton.dataset.toolCommandId ?? "";
      const current = family.buttons.findIndex((button) => button.id === commandId);
      if (current >= 0) {
        const rect = targetButton.getBoundingClientRect();
        const after = family.rail === "floating"
          ? x > rect.left + rect.width / 2
          : y > rect.top + rect.height / 2;
        index = current + (after ? 1 : 0);
      }
    }
    state.target = { familyId, index, rail: family.rail };
    const rect = (targetButton ?? targetFamily).getBoundingClientRect();
    if (family.rail === "floating") {
      line.style.left = `${rect.left - 2}px`;
      line.style.top = `${rect.top}px`;
      line.style.width = "2px";
      line.style.height = `${rect.height}px`;
    } else {
      line.style.left = `${rect.left}px`;
      line.style.top = `${y > rect.top + rect.height / 2 ? rect.bottom : rect.top}px`;
      line.style.width = `${rect.width}px`;
      line.style.height = "2px";
    }
    line.hidden = false;
    return;
  }
  // Family drag: dock above the workspace, or a rail, or reorder in the dock.
  if (dock) {
    const session = currentSession(state.container);
    if (!session) return;
    const floating = familiesForRail(session.config, "floating").filter((family) => family.visible);
    let index = floating.length;
    for (const element of dock.querySelectorAll<HTMLElement>("[data-tool-family]")) {
      const rect = element.getBoundingClientRect();
      if (x < rect.left + rect.width / 2) {
        index = Math.max(0, floating.findIndex((family) => family.id === element.dataset.toolFamily));
        break;
      }
    }
    state.target = { familyId: state.familyId, index, rail: "floating" };
    const rect = dock.getBoundingClientRect();
    line.style.left = `${Math.max(rect.left, Math.min(rect.right - 2, x))}px`;
    line.style.top = `${rect.top}px`;
    line.style.width = "2px";
    line.style.height = `${rect.height}px`;
    line.hidden = false;
    return;
  }
  if (rail && targetFamily) {
    const railId: ToolbarRail = rail.dataset.toolRail === "left" ? "left" : "right";
    const session = currentSession(state.container);
    if (!session) return;
    const peers = familiesForRail(session.config, railId).filter((family) => family.visible && family.id !== state.familyId);
    const rect = targetFamily.getBoundingClientRect();
    let index = peers.length;
    for (const [peerIndex, element] of [...rail.querySelectorAll<HTMLElement>("[data-tool-family]")].entries()) {
      if (element.dataset.toolFamily === state.familyId) continue;
      const peerRect = element.getBoundingClientRect();
      if (y < peerRect.top + peerRect.height / 2) {
        index = Math.max(0, Math.min(peerIndex, peers.length));
        break;
      }
    }
    state.target = { familyId: state.familyId, index, rail: railId };
    line.style.left = `${rect.left}px`;
    line.style.top = `${y > rect.top + rect.height / 2 ? rect.bottom : rect.top}px`;
    line.style.width = `${rect.width}px`;
    line.style.height = "2px";
    line.hidden = false;
  } else if (rail) {
    // Empty rail area: dock at the end of that rail.
    const railId: ToolbarRail = rail.dataset.toolRail === "left" ? "left" : "right";
    const session = currentSession(state.container);
    if (!session) return;
    const peers = familiesForRail(session.config, railId).filter((family) => family.visible && family.id !== state.familyId);
    state.target = { familyId: state.familyId, index: peers.length, rail: railId };
    const rect = rail.getBoundingClientRect();
    line.style.left = `${rect.left}px`;
    line.style.top = `${rect.bottom - 2}px`;
    line.style.width = `${rect.width}px`;
    line.style.height = "2px";
    line.hidden = false;
  } else {
    line.hidden = true;
  }
}

function endDragVisuals(): void {
  dragState?.ghost?.remove();
  document.body.classList.remove("cp-toolbar-dragging");
  if (dropLine) dropLine.hidden = true;
  document.querySelectorAll("[data-tool-drop-hover]").forEach((element) => element.removeAttribute("data-tool-drop-hover"));
}

function onDragEnd(_event: PointerEvent): void {
  const state = dragState;
  const target = state?.target;
  if (!state) return;
  if (state.active && target) {
    const session = currentSession(state.container);
    if (session) {
      const next = state.kind === "button" && state.commandId
        ? moveButton(session.config, state.commandId, state.familyId, target.familyId, target.index)
        : setFamilyRail(session.config, state.familyId, target.rail, target.index);
      if (next !== session.config) {
        suppressClick = true;
        window.setTimeout(() => { suppressClick = false; }, 0);
        applyConfig(state.container, next);
      }
    }
  }
  endDragVisuals();
  dragState = null;
}

function moveButtonByKeyboard(container: HTMLElement, familyId: string, commandId: string, delta: number, crossFamily: boolean): void {
  const session = currentSession(container);
  if (!session || session.config.locked) return;
  const family = findToolbarFamily(session.config, familyId);
  if (!family) return;
  if (!crossFamily) {
    const index = family.buttons.findIndex((button) => button.id === commandId);
    const target = index + delta;
    if (index < 0 || target < 0 || target >= family.buttons.length) return;
    applyConfig(container, moveButton(session.config, commandId, familyId, familyId, target));
    return;
  }
  const rails: ToolbarRail[] = ["left", "right", "floating"];
  const ordered = rails.flatMap((rail) => familiesForRail(session.config, rail).filter((item) => item.visible));
  const index = ordered.findIndex((item) => item.id === familyId);
  const targetFamily = ordered[index + delta];
  if (index < 0 || !targetFamily) return;
  if (!targetFamily.custom && !toolbarCommand(commandId)?.families.includes(targetFamily.id)) return;
  applyConfig(container, moveButton(session.config, commandId, familyId, targetFamily.id, targetFamily.buttons.length));
}

// ---------------------------------------------------------------------------
// Event binding
// ---------------------------------------------------------------------------

export function bindToolbarEvents(container: HTMLElement): void {
  if (boundContainers.has(container)) return;
  // The server-side rendering tests use a minimal container shim with only
  // innerHTML; they assert markup, not interaction.
  if (typeof container.addEventListener !== "function") return;
  boundContainers.add(container);

  // Capture phase: a drag must never also run the button's command.
  container.addEventListener("click", (event) => {
    if (!suppressClick) return;
    event.preventDefault();
    event.stopPropagation();
  }, true);

  container.addEventListener("click", (event) => {
    const target = (event.target as HTMLElement | null)?.closest<HTMLElement>("[data-tool-add-remove], [data-tool-rail-menu], [data-tool-family-handle]");
    if (!target) return;
    const session = currentSession(container);
    if (!session) return;
    const family = target.closest<HTMLElement>("[data-tool-family]");
    const rect = target.getBoundingClientRect();
    if (target.hasAttribute("data-tool-add-remove")) {
      event.preventDefault();
      event.stopPropagation();
      openMenu(container, "add-remove", family?.dataset.toolFamilyRail === "left" ? "left" : "right", rect, { familyId: family?.dataset.toolFamily });
      return;
    }
    if (target.hasAttribute("data-tool-rail-menu")) {
      event.preventDefault();
      event.stopPropagation();
      openMenu(container, "rail", target.closest<HTMLElement>("[data-tool-rail]")?.dataset.toolRail === "left" ? "left" : "right", rect);
      return;
    }
    // A click on the family grip is the keyboard/pointer affordance for moving
    // the whole family; pointer drags are started in pointerdown.
    if (target.hasAttribute("data-tool-family-handle") && family) {
      event.preventDefault();
      event.stopPropagation();
      openMenu(container, "family", family.dataset.toolFamilyRail === "left" ? "left" : "right", rect, { familyId: family.dataset.toolFamily });
    }
  });

  container.addEventListener("contextmenu", (event) => {
    const target = event.target as HTMLElement | null;
    if (!target) return;
    const family = target.closest<HTMLElement>("[data-tool-family]");
    const inToolbar = target.closest<HTMLElement>("[data-tool-rail], [data-toolbar-dock]");
    if (!inToolbar) return;
    event.preventDefault();
    event.stopPropagation();
    const button = target.closest<HTMLElement>("[data-tool-rail-button]");
    const rail: ToolbarRail = family?.dataset.toolFamilyRail === "left" || target.closest<HTMLElement>("[data-tool-rail]")?.dataset.toolRail === "left"
      ? "left"
      : family?.dataset.toolFamilyRail === "floating"
        ? "floating"
        : "right";
    if (button && family) {
      openMenu(container, "button", rail, button.getBoundingClientRect(), {
        familyId: family.dataset.toolFamily,
        commandId: button.dataset.toolCommandId,
      });
      return;
    }
    if (family) {
      openMenu(container, "family", rail, family.getBoundingClientRect(), { familyId: family.dataset.toolFamily });
      return;
    }
    openMenu(container, "rail", rail, inToolbar.getBoundingClientRect());
  });

  container.addEventListener("pointerdown", (event) => {
    if (event.button !== 0 || !dragState) {
      const target = event.target as HTMLElement | null;
      if (event.button !== 0 || !target) return;
      const session = currentSession(container);
      if (!session) return;
      const handle = target.closest<HTMLElement>("[data-tool-family-handle]");
      if (handle) {
        const family = handle.closest<HTMLElement>("[data-tool-family]");
        if (!family || session.config.locked) return;
        startDrag(event, "family", handle, family.dataset.toolFamily ?? "");
        return;
      }
      const button = target.closest<HTMLElement>("[data-tool-rail-button]");
      if (button) {
        if (session.config.locked) return;
        const family = button.closest<HTMLElement>("[data-tool-family]");
        if (!family) return;
        startDrag(event, "button", button, family.dataset.toolFamily ?? "", button.dataset.toolCommandId);
      }
    }
  });

  container.addEventListener("keydown", (event) => {
    const button = (event.target as HTMLElement | null)?.closest?.<HTMLElement>("[data-tool-rail-button]");
    if (!button || !event.altKey) return;
    const family = button.closest<HTMLElement>("[data-tool-family]");
    const familyId = family?.dataset.toolFamily ?? button.dataset.toolFamilyId ?? "";
    const commandId = button.dataset.toolCommandId ?? "";
    if (!familyId || !commandId) return;
    if (event.key === "ArrowUp" || event.key === "ArrowDown") {
      event.preventDefault();
      if (event.shiftKey) {
        const session = currentSession(container);
        if (!session) return;
        const current = findToolbarFamily(session.config, familyId);
        if (!current) return;
        const peers = familiesForRail(session.config, current.rail).filter((item) => item.visible);
        const index = peers.findIndex((item) => item.id === familyId);
        const target = index + (event.key === "ArrowUp" ? -1 : 1);
        if (index < 0 || target < 0 || target >= peers.length) return;
        applyConfig(container, setFamilyRail(session.config, familyId, current.rail, target));
        return;
      }
      moveButtonByKeyboard(container, familyId, commandId, event.key === "ArrowUp" ? -1 : 1, false);
      return;
    }
    if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      event.preventDefault();
      moveButtonByKeyboard(container, familyId, commandId, event.key === "ArrowLeft" ? -1 : 1, true);
    }
  });
}

/** Close any open toolbar menu or dialog. Exposed for the shell's Escape path. */
export function closeToolbarSurfaces(): void {
  closeMenu();
  closeCustomizeDialog();
}
