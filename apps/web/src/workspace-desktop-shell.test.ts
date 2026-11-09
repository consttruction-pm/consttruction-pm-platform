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
import { DEFAULT_PRESENTATION, type WorkspacePresentation } from "./workspace-presentation.js";

const capable: DesktopShellCapabilities = {
  canUndoLayout: true,
  canRedoLayout: true,
  hasWbs: true,
  hasSelectedActivity: true,
  hasMultipleWindows: true,
  canOpenFieldChooser: true,
  hasLayout: true,
  groupByWbs: true,
};

function shellState(patch: Partial<DesktopShellCapabilities> = {}, locale = "en", presentation?: WorkspacePresentation): DesktopShellState {
  return {
    locale,
    activeWindow: "schedule",
    openWindows: ["project", "schedule"],
    capabilities: { ...capable, ...patch },
    presentation,
  };
}

const DEFAULT_PRESENTATION_FOR_TEST: WorkspacePresentation = {
  ...DEFAULT_PRESENTATION,
  table: { ...DEFAULT_PRESENTATION.table, lineNumbers: true },
};

test("desktop chrome owns exactly one persisted window tab strip and dispatches close", () => {
  const listeners = new Map<string, (event: Event) => void>();
  const closed: string[] = [];
  const host = {
    innerHTML: "",
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
    querySelectorAll: () => [],
    querySelector: () => null,
    contains: () => true,
  };
  renderDesktopShell(host as unknown as HTMLElement, shellState(), {
    onWindowOpen: () => {},
    onWindowClose: (window) => closed.push(window),
    onCommand: () => {},
  });
  assert.equal((host.innerHTML.match(/class="cp-window-tabs"/g) ?? []).length, 1);
  assert.match(host.innerHTML, /data-window-tab="project"/);
  assert.match(host.innerHTML, /data-window-tab="schedule"/);
  assert.match(host.innerHTML, /data-window-close="project"/);
  const target = {
    dataset: { windowClose: "project" },
    closest: (selector: string) => selector === "[data-window-close]" ? target : null,
  };
  listeners.get("click")?.({ target, stopPropagation: () => {} } as unknown as Event);
  assert.deepEqual(closed, ["project"]);
});

test("layout commands from the global menu open their owning desktop dialog", () => {
  const listeners = new Map<string, (event: Event) => void>();
  let opened = false;
  let dispatched = "";
  const dialog = { showModal: () => { opened = true; }, setAttribute: () => {} };
  const host = {
    innerHTML: "",
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
    querySelectorAll: () => [],
    querySelector: (selector: string) => selector === '[data-desktop-dialog="timescale"]' ? dialog : null,
    contains: () => true,
  };
  renderDesktopShell(host as unknown as HTMLElement, shellState(), {
    onWindowOpen: () => {},
    onWindowClose: () => {},
    onCommand: (command) => { dispatched = command; },
  });
  const target = {
    dataset: { shellCommand: "Timescale" },
    hasAttribute: () => false,
    closest: (selector: string) => selector === "[data-shell-command]" ? target : null,
  };
  listeners.get("click")?.({ target, stopPropagation: () => {} } as unknown as Event);
  assert.equal(opened, true);
  assert.equal(dispatched, "");
});

test("Ctrl+Numpad plus and minus dispatch the documented expand and collapse commands", () => {
  const listeners = new Map<string, (event: Event) => void>();
  const dispatched: string[] = [];
  const host = {
    innerHTML: "",
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
    querySelectorAll: () => [],
    querySelector: () => null,
    contains: () => true,
  };
  renderDesktopShell(host as unknown as HTMLElement, shellState(), {
    onWindowOpen: () => {},
    onWindowClose: () => {},
    onCommand: (command) => { dispatched.push(command); },
  });
  const press = (code: string) => listeners.get("keydown")?.({
    ctrlKey: true,
    key: code === "NumpadAdd" ? "+" : "-",
    code,
    target: null,
    preventDefault: () => {},
  } as unknown as Event);
  press("NumpadAdd");
  press("NumpadSubtract");
  press("Equal");
  assert.deepEqual(dispatched, ["view.expand-all", "view.collapse-all"]);
});

test("Ctrl+Numpad expand and collapse stay inert without a WBS grouping", () => {
  const listeners = new Map<string, (event: Event) => void>();
  const dispatched: string[] = [];
  const host = {
    innerHTML: "",
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
    querySelectorAll: () => [],
    querySelector: () => null,
    contains: () => true,
  };
  renderDesktopShell(host as unknown as HTMLElement, shellState({ hasWbs: false, groupByWbs: false }), {
    onWindowOpen: () => {},
    onWindowClose: () => {},
    onCommand: (command) => { dispatched.push(command); },
  });
  listeners.get("keydown")?.({
    ctrlKey: true,
    key: "+",
    code: "NumpadAdd",
    target: null,
    preventDefault: () => {},
  } as unknown as Event);
  assert.deepEqual(dispatched, []);
});

test("the canonical workspace exposes no alternate visual-demo menu entry", () => {
  const menus = getDesktopMenus(shellState());
  const items = menus.flatMap((menu) => menu.items);
  assert.doesNotMatch(JSON.stringify(items), /visual-demo|Visual workspace demo|نمایش بصری محیط کار/);
  const help = menus.find((menu) => menu.id === "help");
  assert.ok(help?.items.some((item) => item.id === "help.shortcuts"));
  assert.ok(help?.items.some((item) => item.id === "help.about"));
});

test("the menu bar mirrors the eight professional workspace menus in order", () => {
  const menus = getDesktopMenus(shellState());
  assert.deepEqual(
    menus.map((menu) => menu.id),
    ["file", "edit", "view", "project", "enterprise", "tools", "window", "help"],
  );
  for (const menu of menus) {
    assert.ok(menu.items.length > 0, `${menu.id} must not be empty`);
  }
});

test("window shortcuts only advertise the Alt+1…9 keys the keydown handler claims", () => {
  const byId = new Map(getDesktopMenus(shellState()).flatMap((menu) => menu.items.map((item) => [item.id, item])));
  assert.equal(byId.get("window.project")?.shortcut, "Alt+1");
  assert.equal(byId.get("window.schedule")?.shortcut, "Alt+3");
  // WINDOW_ORDER keeps more windows, but only nine single-digit Alt chords
  // exist; later windows must not show a shortcut that would do nothing.
  for (const [id, item] of byId) {
    if (!id.startsWith("window.")) continue;
    if (item.shortcut === undefined) continue;
    assert.match(item.shortcut, /^Alt\+[1-9]$/, `${id} advertises ${item.shortcut}`);
  }
});

test("the consolidated menus keep every scheduling, resource and report command", () => {
  const byId = new Map(getDesktopMenus(shellState()).flatMap((menu) => menu.items.map((item) => [item.id, item])));
  for (const id of [
    "file.open-layout",
    "file.save-layout",
    "file.save-layout-as",
    "view.bars",
    "view.font-row",
    "view.preferences",
    "view.line-numbers",
    "project.schedule",
    "project.schedule-options",
    "project.formula",
    "project.assign-resources",
    "project.predecessors",
    "enterprise.resources",
    "enterprise.calendars",
    "tools.reports",
    "tools.print-preview",
    "tools.generate-report",
  ]) {
    assert.ok(byId.has(id), `${id} must survive the menu consolidation`);
  }
  const save = byId.get("file.save-layout");
  assert.equal(save?.command, "layout.save");
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
  // Distinct windows must be distinguishable in the tab strip; two menus named
  // "Tracking" would make the progress and tracking windows indistinguishable.
  for (const language of ["en", "fa"] as const) {
    const labels = Object.values(WINDOW_TITLES).map((title) => title[language]);
    assert.equal(new Set(labels).size, labels.length, `${language} window titles must be unique`);
  }
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
  assert.ok(toolbar.some((item) => item.id === "toolbar.bars" && item.command === "dialog.bars"));
  assert.ok(toolbar.some((item) => item.id === "toolbar.font-row" && item.command === "dialog.font-row"));
  assert.ok(toolbar.some((item) => item.id === "toolbar.line-numbers" && item.command === "view.line-numbers"));
  assert.ok(toolbar.some((item) => item.id === "toolbar.preferences" && item.command === "dialog.user-preferences"));

  const withNumbers = getDesktopToolbar(shellState({}, "en", DEFAULT_PRESENTATION_FOR_TEST));
  assert.equal(withNumbers.find((item) => item.id === "toolbar.line-numbers")?.active, true);

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
