/**
 * Context menus for the record registers (risks, thresholds, expenses, cost
 * accounts, reports).
 *
 * Every command in these menus activates a control that already exists in the
 * window: the row buttons or the detail-pane buttons the user can also click.
 * The menu never invents an action. A command whose control is missing or
 * disabled for the current record is rendered disabled with the reason, so a
 * reader without write rights sees "Edit" greyed out instead of a command that
 * silently does nothing.
 *
 * The menus share the viewport portal in `workspace-context-menu.ts`, which
 * owns positioning, Escape/focus restoration and outside-click dismissal.
 */
import { anchorPoint, openContextMenu, type ContextMenuItem } from "./workspace-context-menu.js";
import type { WorkspaceIconName } from "./workspace-icons.js";

export const REGISTER_MENU_WRITE_REASON = {
  en: "You do not have permission to change this project.",
  fa: "شما اجازهٔ تغییر این پروژه را ندارید.",
} as const;

export const REGISTER_MENU_UNAVAILABLE_REASON = {
  en: "This command is not available for the selected record.",
  fa: "این فرمان برای رکورد انتخاب‌شده در دسترس نیست.",
} as const;

export type RegisterCommandSpec = {
  /** Stable command id; also the id the browser acceptance suite asserts. */
  command: string;
  label: { en: string; fa: string };
  icon?: WorkspaceIconName;
  /**
   * Selector of the real control this command activates. It is looked up
   * inside the row for `scope: "row"` and in the whole register window for
   * `scope: "host"`.
   */
  control: string;
  scope?: "row" | "host";
  /** Hidden behind the write permission, exactly like the control it mirrors. */
  requiresWrite?: boolean;
  separatorBefore?: boolean;
};

export type RegisterRowMenu = {
  kind: string;
  label: { en: string; fa: string };
  rowSelector: string;
  /** Row attribute holding the stable record id. */
  rowIdAttribute: string;
  commands: readonly RegisterCommandSpec[];
};

export type RegisterControlState = {
  present: boolean;
  disabled: boolean;
};

export type RegisterMenuSpec = {
  commands: readonly RegisterCommandSpec[];
  locale: string;
  canWrite: boolean;
};

function localized(locale: string, en: string, fa: string): string {
  return locale.split("-")[0] === "fa" ? fa : en;
}

/**
 * Build the menu items from the state of the real controls. Kept pure so the
 * localized labels and the disabling rules can be unit tested without a DOM.
 */
export function buildRegisterMenuItems(
  spec: RegisterMenuSpec,
  state: (command: string) => RegisterControlState,
): ContextMenuItem[] {
  return spec.commands.map((command) => {
    const control = state(command.command);
    // A permission denial is the more useful explanation, so it wins over
    // "control missing" when the record button is simply not rendered.
    const denied = Boolean(command.requiresWrite) && !spec.canWrite;
    const unavailable = !denied && (!control.present || control.disabled);
    const disabled = denied || unavailable;
    const reason = denied
      ? localized(spec.locale, REGISTER_MENU_WRITE_REASON.en, REGISTER_MENU_WRITE_REASON.fa)
      : unavailable
        ? localized(spec.locale, REGISTER_MENU_UNAVAILABLE_REASON.en, REGISTER_MENU_UNAVAILABLE_REASON.fa)
        : undefined;
    return {
      command: command.command,
      label: localized(spec.locale, command.label.en, command.label.fa),
      icon: command.icon,
      disabled,
      reason,
      separatorBefore: command.separatorBefore,
    };
  });
}

function escapeSelector(value: string): string {
  if (typeof CSS !== "undefined" && typeof CSS.escape === "function") return CSS.escape(value);
  return value.replace(/["\\]/g, "\\$&");
}

function controlIn(row: HTMLElement, host: HTMLElement, command: RegisterCommandSpec): HTMLElement | null {
  const scope = command.scope === "host" ? host : row;
  return scope.querySelector<HTMLElement>(command.control);
}

function rowIsSelected(row: HTMLElement): boolean {
  return row.getAttribute("aria-selected") === "true" || row.classList.contains("is-selected");
}

export type RegisterMenuBinding = {
  locale: string;
  canWrite: boolean;
  menus: readonly RegisterRowMenu[];
};

/**
 * Bind pointer and keyboard invocation on a register host. The host may render
 * more than one register (Project Expenses renders the expense register and the
 * cost-account register), so each row family carries its own menu.
 */
export function bindRegisterContextMenus(host: HTMLElement, binding: RegisterMenuBinding): void {
  if (host.dataset.registerContextMenu === "bound") return;
  if (!binding.menus.length) return;
  host.dataset.registerContextMenu = "bound";

  const open = (
    menu: RegisterRowMenu,
    row: HTMLElement,
    point: { x: number; y: number },
    focusFirst: boolean,
  ): void => {
    const rowId = row.getAttribute(menu.rowIdAttribute);
    // Selecting the row is what renders the detail-pane commands (reports keep
    // Edit/Delete/Run there). It also matches the desktop reference: the menu
    // acts on the record under the pointer. Selection re-renders the register,
    // so the element is looked up again before its controls are read.
    if (!rowIsSelected(row)) {
      row.click();
    }
    const reselect = rowId
      ? host.querySelector<HTMLElement>(`${menu.rowSelector}[${menu.rowIdAttribute}="${escapeSelector(rowId)}"]`)
      : null;
    const activeRow = reselect && host.contains(reselect) ? reselect : row;
    const items = buildRegisterMenuItems(
      { commands: menu.commands, locale: binding.locale, canWrite: binding.canWrite },
      (command) => {
        const spec = menu.commands.find((entry) => entry.command === command);
        const control = spec ? controlIn(activeRow, host, spec) : null;
        return {
          present: Boolean(control),
          disabled: Boolean(control && (control as HTMLButtonElement).disabled),
        };
      },
    );
    openContextMenu({
      x: point.x,
      y: point.y,
      anchor: activeRow,
      focusFirst,
      kind: menu.kind,
      label: localized(binding.locale, menu.label.en, menu.label.fa),
      direction: binding.locale.split("-")[0] === "fa" ? "rtl" : "ltr",
      items,
      onCommand: (command) => {
        const spec = menu.commands.find((entry) => entry.command === command);
        if (!spec) return;
        // Commands that belong to the register toolbar or the detail pane can
        // be reached after a re-render, so re-resolve the row before dispatch.
        const current = rowId
          ? host.querySelector<HTMLElement>(`${menu.rowSelector}[${menu.rowIdAttribute}="${escapeSelector(rowId)}"]`) ?? activeRow
          : activeRow;
        const control = controlIn(current, host, spec);
        if (!control || (control as HTMLButtonElement).disabled) return;
        control.click();
      },
    });
  };

  const menuFor = (target: HTMLElement): { menu: RegisterRowMenu; row: HTMLElement } | null => {
    for (const menu of binding.menus) {
      const row = target.closest<HTMLElement>(menu.rowSelector);
      if (row && host.contains(row)) return { menu, row };
    }
    return null;
  };

  host.addEventListener("contextmenu", (event) => {
    const target = event.target as HTMLElement | null;
    if (!target || typeof target.closest !== "function") return;
    const match = menuFor(target);
    if (!match) return;
    event.preventDefault();
    // A keyboard-triggered contextmenu event carries no pointer coordinates;
    // anchor the menu to the row instead of the viewport origin.
    const point =
      event.clientX === 0 && event.clientY === 0
        ? anchorPoint(match.row)
        : { x: event.clientX, y: event.clientY };
    open(match.menu, match.row, point, event.clientX === 0 && event.clientY === 0);
  });

  host.addEventListener("keydown", (event) => {
    if (event.key !== "ContextMenu" && !(event.shiftKey && event.key === "F10")) return;
    const target = event.target as HTMLElement | null;
    if (!target || typeof target.closest !== "function") return;
    const match = menuFor(target);
    if (!match) return;
    event.preventDefault();
    open(match.menu, match.row, anchorPoint(match.row), true);
  });
}
