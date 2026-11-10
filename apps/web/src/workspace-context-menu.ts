/**
 * Viewport-level context menus.
 *
 * A desktop context menu must appear next to the pointer that opened it. The
 * workspace panes are transformed and clipped containers, so a menu rendered
 * inside them inherits those transforms and is cut off at the pane edge. This
 * module renders one menu at a time into `document.body`, positions it in
 * viewport coordinates, flips it at the right and bottom edges, and keeps it
 * inside the viewport. It never scrolls the document: menus open after any
 * navigation has completed, and an asynchronous scroll event must not dismiss
 * a menu that is already visible.
 */
import { workspaceIcon, type WorkspaceIconName } from "./workspace-icons.js";

export type ContextMenuItem = {
  command: string;
  label: string;
  icon?: WorkspaceIconName;
  shortcut?: string;
  disabled?: boolean;
  /** Localized reason shown as the native tooltip for a disabled command. */
  reason?: string;
  checked?: boolean;
  /** Draw a separator above this item. */
  separatorBefore?: boolean;
};

export type ContextMenuRequest = {
  x: number;
  y: number;
  label: string;
  kind: string;
  items: readonly ContextMenuItem[];
  onCommand: (command: string) => void;
  /** Element focus returns to when Escape closes the menu. */
  anchor?: HTMLElement | null;
  direction?: "ltr" | "rtl";
  /**
   * Focus the first command when the menu opens. Pointer invocation leaves the
   * focus where it was, like the desktop reference; keyboard invocation uses
   * the menu as a real focus stop.
   */
  focusFirst?: boolean;
};

type ActiveMenu = {
  element: HTMLElement;
  anchor: HTMLElement | null;
  x: number;
  y: number;
};

const VIEWPORT_MARGIN = 4;
let active: ActiveMenu | null = null;
let documentBound = false;

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]!);
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function viewportSize(): { width: number; height: number } {
  const element = typeof document !== "undefined" ? document.documentElement : null;
  return {
    width: (typeof window !== "undefined" && window.innerWidth) || element?.clientWidth || 1024,
    height: (typeof window !== "undefined" && window.innerHeight) || element?.clientHeight || 768,
  };
}

/** Place the menu at the pointer, flipping at the right/bottom viewport edges. */
function positionMenu(menu: HTMLElement, x: number, y: number): void {
  if (typeof menu.getBoundingClientRect !== "function") return;
  const viewport = viewportSize();
  const margin = VIEWPORT_MARGIN;
  menu.style.maxHeight = `${Math.max(120, viewport.height - margin * 2)}px`;
  // Measure from the viewport origin so a flip uses the real menu box.
  menu.style.left = "0px";
  menu.style.top = "0px";
  const bounds = menu.getBoundingClientRect();
  const width = Math.max(1, bounds.width || 244);
  const height = Math.min(Math.max(1, bounds.height || 200), viewport.height - margin * 2);
  let left = x + 2;
  let top = y + 2;
  if (left + width > viewport.width - margin) left = x - width - 2;
  if (top + height > viewport.height - margin) top = y - height - 2;
  left = clamp(left, margin, Math.max(margin, viewport.width - width - margin));
  top = clamp(top, margin, Math.max(margin, viewport.height - height - margin));
  menu.style.left = `${Math.round(left)}px`;
  menu.style.top = `${Math.round(top)}px`;
}

function focusableItems(menu: HTMLElement): HTMLElement[] {
  return Array.from(menu.querySelectorAll<HTMLElement>("[data-activity-menu-command]:not(:disabled)"));
}

function close(restoreFocus: boolean): void {
  const previous = active;
  active = null;
  if (!previous) return;
  previous.element.remove();
  if (restoreFocus) {
    const anchor = previous.anchor;
    if (anchor && typeof anchor.isConnected === "boolean" && anchor.isConnected && typeof anchor.focus === "function") {
      anchor.focus({ preventScroll: true });
    }
  }
}

export function closeContextMenu(restoreFocus = false): void {
  close(restoreFocus);
}

export function isContextMenuOpen(): boolean {
  return active !== null;
}

function bindDocumentEvents(): void {
  if (documentBound || typeof document === "undefined") return;
  documentBound = true;
  document.addEventListener("pointerdown", (event) => {
    if (!active) return;
    const target = event.target as Node | null;
    if (target && active.element.contains(target)) return;
    close(false);
  }, true);
  document.addEventListener("keydown", (event) => {
    if (!active) return;
    const menu = active.element;
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      close(true);
      return;
    }
    if (event.key === "Tab") {
      // A shortcut menu is modal to keyboard focus until dismissed.
      close(true);
      return;
    }
    if (event.key === "ArrowDown" || event.key === "ArrowUp" || event.key === "Home" || event.key === "End") {
      const items = focusableItems(menu);
      if (!items.length) return;
      const focused = document.activeElement as HTMLElement | null;
      const index = focused ? items.indexOf(focused) : -1;
      event.preventDefault();
      if (event.key === "Home") {
        items[0].focus({ preventScroll: true });
      } else if (event.key === "End") {
        items[items.length - 1].focus({ preventScroll: true });
      } else {
        const step = event.key === "ArrowDown" ? 1 : -1;
        const next = index < 0 ? (step > 0 ? 0 : items.length - 1) : (index + step + items.length) % items.length;
        items[next].focus({ preventScroll: true });
      }
    }
  }, true);
  window.addEventListener("resize", () => {
    if (active) positionMenu(active.element, active.x, active.y);
  });
}

/**
 * Open a menu at viewport coordinates. Returns the menu element, or null when
 * there is nothing to show.
 */
export function openContextMenu(request: ContextMenuRequest): HTMLElement | null {
  if (typeof document === "undefined" || !document.body) return null;
  if (!request.items.length) return null;
  close(false);
  bindDocumentEvents();
  const menu = document.createElement("div");
  menu.className = "cp-context-menu cp-context-menu-portal";
  menu.dataset.activityContextMenu = "";
  menu.dataset.contextMenuKind = request.kind;
  menu.setAttribute("role", "menu");
  menu.setAttribute("aria-label", request.label);
  menu.setAttribute("dir", request.direction ?? (typeof active?.anchor?.closest === "function" ? active.anchor.closest("[dir]")?.getAttribute("dir") ?? "ltr" : "ltr"));
  menu.tabIndex = -1;
  menu.innerHTML = request.items.map((item) => {
    const separator = item.separatorBefore ? `<div class="cp-context-separator" role="separator"></div>` : "";
    const shortcut = item.shortcut ?? "";
    const reason = item.reason ? ` title="${escapeHtml(item.reason)}"` : "";
    const disabled = item.disabled ? ` disabled aria-disabled="true"` : "";
    const checked = item.checked ? ` aria-checked="true"` : "";
    return `${separator}<button type="button" role="menuitem" data-activity-menu-command="${escapeHtml(item.command)}"${checked}${disabled}${reason}><span class="cp-context-icon">${workspaceIcon(item.checked ? "check" : item.icon ?? "activity")}</span><span class="cp-context-text">${escapeHtml(item.label)}</span><span class="cp-context-shortcut">${escapeHtml(shortcut)}</span></button>`;
  }).join("");
  menu.style.visibility = "hidden";
  document.body.append(menu);
  const x = Number.isFinite(request.x) ? request.x : VIEWPORT_MARGIN;
  const y = Number.isFinite(request.y) ? request.y : VIEWPORT_MARGIN;
  menu.dataset.contextMenuX = String(Math.round(x));
  menu.dataset.contextMenuY = String(Math.round(y));
  active = { element: menu, anchor: request.anchor ?? null, x, y };
  positionMenu(menu, x, y);
  menu.style.visibility = "";
  menu.addEventListener("click", (event) => {
    const target = event.target as HTMLElement | null;
    const button = target && typeof target.closest === "function" ? target.closest<HTMLElement>("[data-activity-menu-command]") : null;
    const command = button?.dataset.activityMenuCommand;
    if (!command || (button as HTMLButtonElement | null)?.disabled) return;
    close(false);
    request.onCommand(command);
  });
  const first = request.focusFirst === false ? null : focusableItems(menu)[0];
  if (first && typeof first.focus === "function") first.focus({ preventScroll: true });
  return menu;
}

/** Keyboard invocation anchors the menu to the focused control, not the cursor. */
export function anchorPoint(anchor: HTMLElement | null | undefined): { x: number; y: number } {
  if (!anchor || typeof anchor.getBoundingClientRect !== "function") return { x: VIEWPORT_MARGIN * 3, y: VIEWPORT_MARGIN * 3 };
  const bounds = anchor.getBoundingClientRect();
  return {
    x: Math.round(bounds.left + Math.min(24, Math.max(0, bounds.width / 3))),
    y: Math.round(bounds.bottom - Math.min(18, Math.max(0, bounds.height / 3))),
  };
}
