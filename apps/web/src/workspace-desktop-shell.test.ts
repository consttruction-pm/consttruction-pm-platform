import assert from "node:assert/strict";
import test from "node:test";
import {
  WINDOW_TITLES,
  getDesktopMenus,
  getDesktopToolbar,
  renderDesktopShell,
  type DesktopShellCapabilities,
  type DesktopShellState,
} from "./workspace-desktop-shell.js";

const capable: DesktopShellCapabilities = {
  canUndoLayout: true,
  canRedoLayout: true,
  hasWbs: true,
  hasSelectedActivity: true,
  hasMultipleWindows: true,
  canOpenFieldChooser: true,
  groupByWbs: true,
};

function shellState(patch: Partial<DesktopShellCapabilities> = {}, locale = "en"): DesktopShellState {
  return {
    locale,
    activeWindow: "schedule",
    openWindows: ["project", "schedule"],
    capabilities: { ...capable, ...patch },
  };
}

test("the menu bar mirrors the eleven professional workspace menus in order", () => {
  const menus = getDesktopMenus(shellState());
  assert.deepEqual(
    menus.map((menu) => menu.id),
    ["file", "edit", "view", "project", "enterprise", "schedule", "resources", "tools", "reports", "window", "help"],
  );
  for (const menu of menus) {
    assert.ok(menu.items.length > 0, `${menu.id} must not be empty`);
  }
});

test("every menu entry opens a window, runs a command, or states why it is unavailable", () => {
  for (const locale of ["en", "fa"]) {
    for (const menu of getDesktopMenus(shellState({}, locale))) {
      for (const item of menu.items) {
        assert.ok(
          Boolean(item.window) || Boolean(item.command) || Boolean(item.disabledReason),
          `${menu.id}/${item.id} has no effect`,
        );
        assert.ok(
          !item.disabledReason || !item.window,
          `${menu.id}/${item.id} must not advertise a window it cannot open`,
        );
        assert.ok(item.label[locale === "fa" ? "fa" : "en"].trim().length > 0);
      }
    }
  }
});

test("window titles cover every navigation surface and avoid third-party product names", () => {
  const titles = Object.keys(WINDOW_TITLES);
  assert.deepEqual(titles, [
    "project",
    "wbs",
    "schedule",
    "progress",
    "resources",
    "assignments",
    "roles",
    "calendars",
    "cost",
    "expenses",
    "documents",
    "reports",
    "tracking",
    "issues",
    "risks",
    "thresholds",
    "control",
    "settings",
  ]);
  const text = getDesktopMenus(shellState())
    .flatMap((menu) => [menu.label.en, ...menu.items.flatMap((item) => [item.label.en, item.shortcut ?? ""])])
    .join(" ");
  assert.ok(!/oracle|primavera/i.test(text), "user-facing chrome must use CUBI names only");
});

test("disabled commands explain the missing precondition instead of failing silently", () => {
  const menus = getDesktopMenus(shellState({
    canUndoLayout: false,
    canRedoLayout: false,
    hasWbs: false,
    hasSelectedActivity: false,
    hasMultipleWindows: false,
    canOpenFieldChooser: false,
  }));
  const byId = new Map(menus.flatMap((menu) => menu.items.map((item) => [item.id, item])));
  for (const id of [
    "edit.undo",
    "edit.redo",
    "project.add-activity",
    "project.edit-activity",
    "workspace.close",
    "view.fields",
  ]) {
    const item = byId.get(id);
    assert.ok(item?.disabledReason?.en, `${id} must explain why it is disabled`);
  }
  assert.equal(byId.get("edit.group-wbs")?.checked, true, "WBS grouping is the default activity view");
});

test("toolbar commands are real and track layout history and selection", () => {
  const toolbar = getDesktopToolbar(shellState());
  assert.ok(toolbar.length >= 8);
  assert.ok(toolbar.every((item) => item.command || item.window || item.fullscreen));
  assert.ok(toolbar.every((item) => !item.disabledReason));
  const group = toolbar.find((item) => item.id === "toolbar.group-wbs");
  assert.equal(group?.active, true);

  const limited = getDesktopToolbar(shellState({ canUndoLayout: false, hasSelectedActivity: false }));
  assert.ok(limited.find((item) => item.id === "toolbar.undo")?.disabledReason);
  assert.ok(limited.find((item) => item.id === "toolbar.edit-activity")?.disabledReason);
});

test("Persian labels are provided for menus, items and window titles", () => {
  const menus = getDesktopMenus(shellState({}, "fa"));
  assert.equal(menus[0]?.label.fa, "فایل");
  assert.ok(menus.every((menu) => menu.items.every((item) => item.label.fa.trim().length > 0)));
  assert.equal(WINDOW_TITLES.schedule.fa, "فعالیت‌ها");
});

test("the desktop shell renders one tab strip and dispatches close for the selected window", () => {
  const listeners = new Map<string, (event: Event) => void>();
  const host = {
    innerHTML: "",
    querySelectorAll: () => [] as HTMLElement[],
    querySelector: () => null,
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
  };
  const closed: string[] = [];
  renderDesktopShell(host as unknown as HTMLElement, shellState(), {
    onWindowOpen: () => {},
    onWindowClose: (window) => closed.push(window),
    onCommand: () => {},
  });
  assert.match(host.innerHTML, /class="cp-window-tabs"/);
  assert.match(host.innerHTML, /role="tab" aria-selected="true" data-window-tab="schedule"/);
  assert.match(host.innerHTML, /data-window-tab="project"/);
  assert.match(host.innerHTML, /data-window-close="project"/);
  assert.equal((host.innerHTML.match(/class="cp-window-tabs"/g) ?? []).length, 1);
  const target = {
    dataset: { windowClose: "project" },
    closest: (selector: string) => (selector === "[data-window-close]" ? target : null),
  };
  listeners.get("click")?.({ target, stopPropagation: () => {} } as unknown as Event);
  assert.deepEqual(closed, ["project"]);
});
