import assert from "node:assert/strict";
import test from "node:test";
import {
  WINDOW_TITLES,
  getDesktopMenus,
  getDesktopShortcuts,
  getDesktopToolbar,
  getDesktopToolbarGroups,
  matchDesktopShortcut,
  renderDesktopShell,
  shortcutUnavailableReason,
  type DesktopShellCapabilities,
  type DesktopShellState,
} from "./workspace-desktop-shell.js";
import { DEFAULT_PRESENTATION, type WorkspacePresentation } from "./workspace-presentation.js";
import { workspaceIcon } from "./workspace-icons.js";
import { WORKSPACE_TOOLBAR_GROUPS, type WorkspaceToolbarGroup } from "./workspace-toolbars.js";

const capable: DesktopShellCapabilities = {
  canUndoLayout: true,
  canRedoLayout: true,
  hasWbs: true,
  hasSelectedActivity: true,
  hasRelationships: true,
  hasMultipleWindows: true,
  canOpenFieldChooser: true,
  hasLayout: true,
  groupByWbs: true,
  canAdminister: true,
};

function shellState(
  patch: Partial<DesktopShellCapabilities> = {},
  locale = "en",
  presentation?: WorkspacePresentation,
  hiddenToolbarGroups: readonly WorkspaceToolbarGroup[] = [],
): DesktopShellState {
  return {
    locale,
    activeWindow: "schedule",
    openWindows: ["project", "schedule"],
    capabilities: { ...capable, ...patch },
    presentation,
    hiddenToolbarGroups,
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
  const keydown: Array<(event: Event) => void> = [];
  const dispatched: string[] = [];
  const host = {
    innerHTML: "",
    addEventListener: (type: string, listener: (event: Event) => void) => {
      if (type === "keydown") keydown.push(listener);
    },
    querySelectorAll: () => [],
    querySelector: () => null,
    contains: () => true,
  };
  renderDesktopShell(host as unknown as HTMLElement, shellState(), {
    onWindowOpen: () => {},
    onWindowClose: () => {},
    onCommand: (command) => { dispatched.push(command); },
  });
  const press = (code: string) => {
    for (const listener of keydown) {
      listener({
        ctrlKey: true,
        key: code === "NumpadAdd" ? "+" : "-",
        code,
        target: null,
        preventDefault: () => {},
      } as unknown as Event);
    }
  };
  press("NumpadAdd");
  press("NumpadSubtract");
  press("Equal");
  assert.deepEqual(dispatched, ["view.expand-all", "view.collapse-all"]);
});

test("Ctrl+Numpad expand and collapse stay inert without a WBS grouping", () => {
  const keydown: Array<(event: Event) => void> = [];
  const dispatched: string[] = [];
  const host = {
    innerHTML: "",
    addEventListener: (type: string, listener: (event: Event) => void) => {
      if (type === "keydown") keydown.push(listener);
    },
    querySelectorAll: () => [],
    querySelector: () => null,
    contains: () => true,
  };
  renderDesktopShell(host as unknown as HTMLElement, shellState({ hasWbs: false, groupByWbs: false }), {
    onWindowOpen: () => {},
    onWindowClose: () => {},
    onCommand: (command) => { dispatched.push(command); },
  });
  for (const listener of keydown) {
    listener({
      ctrlKey: true,
      key: "+",
      code: "NumpadAdd",
      target: null,
      preventDefault: () => {},
    } as unknown as Event);
  }
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
    ["workspace", "edit", "view", "project", "organization", "tools", "administration", "help"],
  );
  assert.deepEqual(
    menus.map((menu) => menu.accessKey),
    ["w", "e", "v", "p", "o", "t", "a", "h"],
  );
  for (const menu of menus) {
    assert.ok(menu.items.length > 0, `${menu.id} must not be empty`);
  }
  const refused = getDesktopMenus(shellState({ canAdminister: false }));
  assert.ok(!refused.some((menu) => menu.id === "administration"), "non-administrators keep the role-gated menu out");
});

test("the View menu lists the toolbar families as real toggles and the open windows as Alt chords", () => {
  const view = getDesktopMenus(shellState({}, "en", undefined, ["edit"]))
    .find((menu) => menu.id === "view");
  assert.ok(view);
  const toggles = view.items.filter((item) => item.command?.startsWith("view.toolbar-"));
  assert.deepEqual(
    toggles.map((item) => item.command),
    ["view.toolbar-workspace", "view.toolbar-edit", "view.toolbar-layout", "view.toolbar-view", "view.toolbar-project", "view.toolbar-activities", "view.toolbar-wbs", "view.toolbar-gantt", "view.toolbar-resources", "view.toolbar-reports", "view.toolbar-tools"],
  );
  assert.equal(toggles.find((item) => item.command === "view.toolbar-wbs")?.checked, true);
  assert.equal(toggles.find((item) => item.command === "view.toolbar-edit")?.checked, false, "a hidden family stays listed so it can be restored");
  const windows = view.items.filter((item) => item.id.startsWith("window."));
  assert.deepEqual(windows.map((item) => item.shortcut), ["Alt+1", "Alt+2"]);
  assert.match(view.items.map((item) => `${item.label.en} ${item.label.fa}`).join(" "), /CUBI قطبی/);
});

test("window shortcuts only advertise the Alt+1…9 keys the keydown handler claims", () => {
  const byId = new Map(getDesktopMenus(shellState()).flatMap((menu) => menu.items.map((item) => [item.id, item])));
  assert.equal(byId.get("window.project")?.shortcut, "Alt+1");
  assert.equal(byId.get("window.schedule")?.shortcut, "Alt+2");
  // More windows can be open, but only nine single-digit Alt chords
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
        if (item.separator) continue;
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
    "administration",
    "exchange",
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
  assert.ok(toolbar.every((item) => item.command || item.window || item.fullscreen || item.disabledReason));
  // Clipboard and baseline families have no service yet; they say so instead
  // of rendering an enabled button that would do nothing.
  for (const id of ["toolbar.cut", "toolbar.copy", "toolbar.paste", "toolbar.baseline"]) {
    assert.ok(toolbar.find((item) => item.id === id)?.disabledReason, `${id} must explain its missing service`);
  }
  assert.ok(toolbar.filter((item) => !item.disabledReason).length > 8);
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
  assert.equal(menus[0]?.label.fa, "محیط کار");
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

function recordHost(): { host: HTMLElement; keydown: Array<(event: Event) => void>; html: () => string } {
  const keydown: Array<(event: Event) => void> = [];
  const host = {
    innerHTML: "",
    addEventListener: (type: string, listener: (event: Event) => void) => {
      if (type === "keydown") keydown.push(listener);
    },
    querySelectorAll: () => [],
    querySelector: () => null,
    contains: () => true,
  };
  return {
    host: host as unknown as HTMLElement,
    keydown,
    html: () => host.innerHTML,
  };
}

test("every shortcut in the catalog is documented, unique and executable or explicitly unavailable", () => {
  const shortcuts = getDesktopShortcuts(["project", "schedule"]);
  assert.equal(new Set(shortcuts.map((item) => item.id)).size, shortcuts.length);
  assert.equal(new Set(shortcuts.map((item) => item.keys)).size, shortcuts.length, "two commands must not advertise the same keys");
  for (const shortcut of shortcuts) {
    assert.ok(shortcut.label.en.trim() && shortcut.label.fa.trim(), `${shortcut.id} needs both labels`);
    assert.ok(shortcut.keys.trim(), `${shortcut.id} needs a key chord`);
    assert.ok(
      Boolean(shortcut.command) || Boolean(shortcut.window) || Boolean(shortcut.unavailable),
      `${shortcut.id} must run, open, or say why it cannot`,
    );
  }
  assert.deepEqual(
    shortcuts.slice(-2).map((item) => [item.id, item.keys, item.window]),
    [["shortcut.window.project", "Alt+1", "project"], ["shortcut.window.schedule", "Alt+2", "schedule"]],
  );
  assert.deepEqual(getDesktopShortcuts([]).filter((item) => item.id.startsWith("shortcut.window.")), []);
});

test("the shortcut matcher honours every modifier and the availability gate", () => {
  const shortcuts = getDesktopShortcuts(["schedule"]);
  const match = (event: { key: string; ctrlKey?: boolean; shiftKey?: boolean; altKey?: boolean; code?: string }) =>
    matchDesktopShortcut(event, shortcuts)?.id;
  assert.equal(match({ key: "n", ctrlKey: true }), "shortcut.new");
  assert.equal(match({ key: "n" }), undefined, "an unmodified letter is typing, not a command");
  assert.equal(match({ key: "n", ctrlKey: true, shiftKey: true }), undefined);
  assert.equal(match({ key: "F9", shiftKey: true }), "shortcut.schedule-options");
  assert.equal(match({ key: "1", altKey: true }), "shortcut.window.schedule");
  assert.equal(match({ key: "NumpadAdd", code: "NumpadAdd", ctrlKey: true }), "shortcut.expand-all");

  const expand = getDesktopShortcuts().find((item) => item.id === "shortcut.expand-all");
  assert.ok(expand);
  assert.equal(shortcutUnavailableReason(expand, capable), null);
  const reason = shortcutUnavailableReason(expand, { ...capable, groupByWbs: false });
  assert.ok(reason?.en && reason.fa, "an unavailable shortcut must explain itself");
  const cut = getDesktopShortcuts().find((item) => item.id === "shortcut.cut");
  assert.ok(cut && shortcutUnavailableReason(cut, capable)?.en);
});

test("documented but unserviced shortcuts never dispatch a command", () => {
  const recorded = recordHost();
  const dispatched: string[] = [];
  renderDesktopShell(recorded.host, shellState(), {
    onWindowOpen: () => {},
    onWindowClose: () => {},
    onCommand: (command) => { dispatched.push(command); },
  });
  const press = (event: Record<string, unknown>) => {
    for (const listener of recorded.keydown) listener(event as unknown as Event);
  };
  press({ key: "F3", target: null, preventDefault: () => {} });
  press({ key: "F7", target: null, preventDefault: () => {} });
  press({ key: "F10", target: null, preventDefault: () => {} });
  press({ key: "x", ctrlKey: true, target: null, preventDefault: () => {} });
  assert.deepEqual(dispatched, []);
  press({ key: "F5", target: null, preventDefault: () => {} });
  assert.deepEqual(dispatched, ["workspace.refresh"]);
});

test("typing in a field swallows every shell shortcut", () => {
  const recorded = recordHost();
  const dispatched: string[] = [];
  renderDesktopShell(recorded.host, shellState(), {
    onWindowOpen: () => {},
    onWindowClose: () => {},
    onCommand: (command) => { dispatched.push(command); },
  });
  const input = { closest: (selector: string) => (selector.includes("input") ? input : null) };
  for (const listener of recorded.keydown) {
    listener({ key: "F5", ctrlKey: false, target: input, preventDefault: () => {} } as unknown as Event);
  }
  assert.deepEqual(dispatched, []);
});

test("toolbar families follow the closed family list and hidden families leave only the bar", () => {
  const groups = getDesktopToolbarGroups(shellState({}, "en", undefined, ["edit", "reports"]));
  assert.deepEqual(
    groups.map((group) => group.id),
    WORKSPACE_TOOLBAR_GROUPS.filter((id) => id !== "edit" && id !== "reports"),
  );
  for (const group of groups) {
    assert.ok(group.items.length > 0, `${group.id} must not render an empty band`);
    assert.ok(group.items.every((item) => item.group === group.id));
    assert.ok(group.label.en.trim() && group.label.fa.trim());
  }
  const view = getDesktopMenus(shellState({}, "en", undefined, ["edit", "reports"]))
    .find((menu) => menu.id === "view");
  for (const id of ["view.toolbar-edit", "view.toolbar-reports"]) {
    assert.equal(view?.items.find((item) => item.id === id)?.checked, false, "a hidden family stays restorable from View");
  }
});

test("toolbar commands are filtered to the window that can run them", () => {
  const schedule = getDesktopToolbar({ ...shellState(), activeWindow: "schedule" }).map((item) => item.id);
  assert.ok(schedule.includes("toolbar.schedule"));
  assert.ok(schedule.includes("toolbar.columns"));
  assert.equal(schedule.includes("toolbar.reports"), false, "report commands do not belong to the activity window");

  const reports = getDesktopToolbar({ ...shellState(), activeWindow: "reports" }).map((item) => item.id);
  assert.ok(reports.includes("toolbar.reports"));
  assert.equal(reports.includes("toolbar.add-activity"), false);
  assert.equal(reports.includes("toolbar.columns"), false);
});

test("every toolbar icon resolves in the closed registry", () => {
  for (const item of getDesktopToolbar(shellState())) {
    assert.doesNotThrow(() => workspaceIcon(item.icon), `${item.id} uses an unknown icon`);
  }
});

test("dirty windows mark their tab without touching the other tabs", () => {
  const recorded = recordHost();
  renderDesktopShell(recorded.host, { ...shellState(), dirtyWindows: ["project"] }, {
    onWindowOpen: () => {},
    onWindowClose: () => {},
    onCommand: () => {},
  });
  const html = recorded.html();
  assert.match(html, /class="cp-window-tab is-dirty" role="tab" aria-selected="false"[^>]*data-window-dirty="true" data-window-tab="project"/);
  assert.match(html, /cp-window-tab-dirty/);
  assert.doesNotMatch(html, /data-window-dirty="true" data-window-tab="schedule"/);
  assert.match(html, /data-window-close="project"/);
});

test("menu triggers expose their Alt access key and separators render as separators", () => {
  const recorded = recordHost();
  renderDesktopShell(recorded.host, shellState(), {
    onWindowOpen: () => {},
    onWindowClose: () => {},
    onCommand: () => {},
  });
  const html = recorded.html();
  for (const key of ["w", "e", "v", "p", "o", "t", "a", "h"]) {
    assert.match(html, new RegExp(`data-desktop-access="${key}"`));
    assert.match(html, new RegExp(`aria-keyshortcuts="Alt\\+${key.toUpperCase()}"`));
  }
  assert.match(html, /class="cp-menubar-separator" role="separator"/);
});

test("View menu exposes the Activities Show on Top and Show on Bottom layouts", () => {
  const view = getDesktopMenus({
    ...shellState(),
    activityTopLayout: "activity-network",
    activityBottomLayout: "trace-logic",
  }).find((menu) => menu.id === "view");
  assert.ok(view);
  const item = (id: string) => view.items.find((entry) => entry.id === id);
  for (const id of ["view.top-table", "view.top-table-gantt", "view.top-network", "view.bottom-details", "view.bottom-trace", "view.bottom-none"]) {
    assert.ok(item(id), `missing ${id}`);
  }
  assert.equal(item("view.top-network")?.checked, true);
  assert.equal(item("view.top-table-gantt")?.checked, false);
  assert.equal(item("view.bottom-trace")?.checked, true);
  assert.equal(item("view.bottom-details")?.checked, false);
  assert.equal(item("view.top-network")?.disabledReason, undefined);
  assert.equal(item("view.bottom-trace")?.disabledReason, undefined);
});

test("logic layouts explain why they are unavailable instead of pretending to work", () => {
  const view = getDesktopMenus({ ...shellState({ hasRelationships: false }) }).find((menu) => menu.id === "view");
  assert.ok(view);
  assert.match(view.items.find((item) => item.id === "view.top-network")?.disabledReason?.en ?? "", /no persisted relationships/i);
  assert.match(view.items.find((item) => item.id === "view.bottom-trace")?.disabledReason?.en ?? "", /no persisted relationships/i);
  const noSelection = getDesktopMenus({ ...shellState({ hasSelectedActivity: false }) }).find((menu) => menu.id === "view");
  assert.match(noSelection?.items.find((item) => item.id === "view.bottom-trace")?.disabledReason?.en ?? "", /Select an activity/i);
  const otherWindow = getDesktopMenus({ ...shellState(), activeWindow: "project" }).find((menu) => menu.id === "view");
  for (const id of ["view.top-table", "view.top-table-gantt", "view.top-network", "view.bottom-details", "view.bottom-trace", "view.bottom-none"]) {
    assert.match(otherWindow?.items.find((item) => item.id === id)?.disabledReason?.en ?? "", /Activities window/i);
  }
});
