import assert from "node:assert/strict";
import test from "node:test";

import type { PreferenceStorage } from "./workspace-preferences.js";
import { WORKSPACE_ICON_NAMES } from "./workspace-icons.js";
import {
  TOOLBAR_COMMANDS,
  TOOLBAR_FAMILIES,
  TOOLBAR_FAMILY_IDS,
  toolbarCommand,
  toolbarCommandDisabledReason,
  toolbarCommandsForFamily,
  type ToolbarContext,
} from "./workspace-toolbar-registry.js";
import {
  LEGACY_WORKSPACE_TOOLBAR_KEY,
  createCustomFamily,
  defaultToolbarConfig,
  deleteCustomFamily,
  findToolbarFamily,
  familiesForRail,
  moveButton,
  normalizeToolbarConfig,
  readToolbarConfig,
  renameCustomFamily,
  resetAllToolbars,
  resetFamily,
  setButtonVisible,
  setFamilyRail,
  setFamilyStyle,
  setFamilyVisible,
  setToolbarsLocked,
  toggleSeparator,
  toolbarConfigStorageKey,
  toolbarWorkspaceKey,
  writeToolbarConfig,
} from "./workspace-toolbar-config.js";
import { renderToolbarRails } from "./workspace-toolbar-view.js";

const RIGHT_FAMILIES = [
  "project-tools", "assign", "edit", "layout", "enterprise", "print", "action",
  "administrator", "bottom-layout", "display", "find", "dictionaries", "publish",
  "standard-reports", "tools", "activity", "critical-check", "schedule",
] as const;

function memoryStorage(seed: Record<string, string> = {}): PreferenceStorage & { values: Map<string, string> } {
  const values = new Map(Object.entries(seed));
  return {
    values,
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => { values.set(key, value); },
    removeItem: (key: string) => { values.delete(key); },
  };
}

function context(overrides: Partial<ToolbarContext> = {}): ToolbarContext {
  return {
    activeWindow: "schedule",
    locale: "en",
    capabilities: {
      hasWbs: true,
      hasSelectedActivity: true,
      hasMultiSelection: true,
      hasActivities: true,
      hasRelationships: true,
      hasLayout: true,
      canUndoLayout: true,
      canRedoLayout: true,
      groupByWbs: true,
      canAdminister: true,
      canOpenFieldChooser: true,
    },
    ...overrides,
  };
}

test("the right rail registers the eighteen Version 26 toolbar families", () => {
  const right = TOOLBAR_FAMILIES.filter((family) => family.rail === "right");
  assert.deepEqual(right.map((family) => family.id), RIGHT_FAMILIES);
  assert.equal(right.length, 18);
  for (const family of right) {
    assert.ok(family.label.en.trim(), `${family.id} needs an English label`);
    assert.ok(family.label.fa.trim(), `${family.id} needs a Persian label`);
    assert.ok(toolbarCommandsForFamily(family.id).length > 0, `${family.id} must own at least one command`);
  }
});

test("one registry defines every command once with a real target and icon", () => {
  const ids = new Set<string>();
  const knownIcons = new Set<string>(WORKSPACE_ICON_NAMES);
  for (const command of TOOLBAR_COMMANDS) {
    assert.ok(!ids.has(command.id), `duplicate command id ${command.id}`);
    ids.add(command.id);
    assert.ok(knownIcons.has(command.icon), `${command.id} uses an unknown icon ${command.icon}`);
    assert.ok(command.families.length > 0, `${command.id} must belong to a family`);
    for (const family of command.families) {
      assert.ok(TOOLBAR_FAMILY_IDS.includes(family), `${command.id} references missing family ${family}`);
    }
    assert.ok(command.target.kind.length > 0);
  }
  assert.equal(toolbarCommand("does.not.exist"), null);
});

test("defaults include every registry family and every command", () => {
  const config = defaultToolbarConfig();
  assert.equal(config.locked, false);
  assert.deepEqual(config.families.map((family) => family.id), [...TOOLBAR_FAMILY_IDS]);
  assert.equal(familiesForRail(config, "left").length, 6);
  assert.equal(familiesForRail(config, "right").length, 18);
  for (const family of config.families) {
    assert.equal(family.visible, true);
    assert.equal(family.style, "icon");
    assert.deepEqual(family.buttons.map((button) => button.id), toolbarCommandsForFamily(family.id).map((command) => command.id));
  }
});

test("family visibility, button visibility and ordering are independent", () => {
  let config = defaultToolbarConfig();
  config = setFamilyVisible(config, "schedule", false);
  assert.equal(findToolbarFamily(config, "schedule")?.visible, false);

  config = setButtonVisible(config, "layout", "layout.open", false);
  assert.equal(findToolbarFamily(config, "layout")?.buttons.find((button) => button.id === "layout.open")?.visible, false);
  config = setButtonVisible(config, "layout", "layout.open", true);
  assert.equal(findToolbarFamily(config, "layout")?.buttons.find((button) => button.id === "layout.open")?.visible, true);

  config = moveButton(config, "layout.open", "layout", "layout", 0);
  assert.equal(findToolbarFamily(config, "layout")?.buttons[0].id, "layout.open");

  config = setFamilyStyle(config, "layout", "both");
  assert.equal(findToolbarFamily(config, "layout")?.style, "both");
  config = setToolbarsLocked(config, true);
  assert.equal(config.locked, true);
});

test("a command moves between families and between rails without duplication", () => {
  let config = defaultToolbarConfig();
  // layout.open is registered for the Layout family, which also lives on the
  // right rail; a custom toolbar accepts any registered command.
  const created = createCustomFamily(config, "My checks");
  config = created.config;
  assert.equal(findToolbarFamily(config, created.familyId)?.rail, "floating");

  config = moveButton(config, "layout.open", "layout", created.familyId, 0);
  assert.equal(findToolbarFamily(config, "layout")?.buttons.find((button) => button.id === "layout.open")?.visible, false);
  assert.deepEqual(findToolbarFamily(config, created.familyId)?.buttons.map((button) => button.id), ["layout.open"]);
  config = setButtonVisible(config, created.familyId, "print.print", true);
  assert.deepEqual(findToolbarFamily(config, created.familyId)?.buttons.map((button) => button.id), ["layout.open", "print.print"]);
  config = setButtonVisible(config, created.familyId, "print.print", false);
  assert.equal(findToolbarFamily(config, created.familyId)?.buttons.find((button) => button.id === "print.print")?.visible, false);
  assert.equal(config.families.filter((family) => family.buttons.some((button) => button.id === "layout.open" && button.visible)).length, 1);
  // Normalizing a persisted configuration must not resurrect the moved button.
  const normalized = normalizeToolbarConfig(JSON.parse(JSON.stringify(config)));
  assert.equal(findToolbarFamily(normalized, "layout")?.buttons.find((button) => button.id === "layout.open")?.visible, false);

  // A predefined family rejects a command it does not support.
  const untouched = moveButton(config, "layout.open", created.familyId, "print", 0);
  assert.equal(untouched, config);

  config = setFamilyRail(config, "print", "left", 0);
  assert.equal(findToolbarFamily(config, "print")?.rail, "left");
  assert.equal(familiesForRail(config, "left")[0].id, "print");
  assert.equal(familiesForRail(config, "right").some((family) => family.id === "print"), false);
});

test("per-toolbar and global reset restore defaults while keeping custom definitions", () => {
  let config = defaultToolbarConfig();
  config = setFamilyVisible(config, "print", false);
  config = setButtonVisible(config, "print", "print.print", false);
  config = toggleSeparator(config, "print", "print.print");
  config = resetFamily(config, "print");
  assert.equal(findToolbarFamily(config, "print")?.visible, false);
  assert.equal(findToolbarFamily(config, "print")?.buttons.find((button) => button.id === "print.print")?.visible, true);
  assert.deepEqual(findToolbarFamily(config, "print")?.separators, []);

  const created = createCustomFamily(config, "My checks");
  config = moveButton(created.config, "print.print", "print", created.familyId, 0);
  config = resetAllToolbars(config);
  assert.equal(findToolbarFamily(config, "print")?.visible, true);
  assert.equal(findToolbarFamily(config, "schedule")?.rail, "right");
  const custom = findToolbarFamily(config, created.familyId);
  assert.ok(custom, "reset preserves the custom toolbar definition");
  assert.equal(custom?.custom, true);
  assert.deepEqual(custom?.buttons, []);
  assert.equal(config.locked, false);

  config = renameCustomFamily(config, created.familyId, "Renamed");
  assert.equal(findToolbarFamily(config, created.familyId)?.name, "Renamed");
  config = deleteCustomFamily(config, created.familyId);
  assert.equal(findToolbarFamily(config, created.familyId), undefined);
});

test("configuration is persisted per user and per project and never mixes workspaces", () => {
  const storage = memoryStorage();
  const projectA = toolbarWorkspaceKey("project-a");
  const projectB = toolbarWorkspaceKey("project-b");
  assert.notEqual(projectA, projectB);

  let config = defaultToolbarConfig();
  config = setFamilyVisible(config, "enterprise", false);
  writeToolbarConfig("user@example.com", projectA, config, storage);

  const readA = readToolbarConfig("user@example.com", projectA, storage);
  assert.equal(findToolbarFamily(readA, "enterprise")?.visible, false);
  const readB = readToolbarConfig("user@example.com", projectB, storage);
  assert.equal(findToolbarFamily(readB, "enterprise")?.visible, true, "another project keeps the default");

  const otherUser = readToolbarConfig("other@example.com", projectA, storage);
  assert.equal(findToolbarFamily(otherUser, "enterprise")?.visible, true, "another user keeps the default");

  const key = toolbarConfigStorageKey("user@example.com");
  const document = JSON.parse(storage.values.get(key) ?? "{}");
  assert.equal(document.version, 2);
  assert.ok(document.workspaces[projectA]);
  assert.ok(!JSON.stringify(document).includes("activityId"), "toolbar preferences must not store project data");
});

test("the pre-rail hidden-group preference migrates once into the versioned document", () => {
  const storage = memoryStorage({
    [`${LEGACY_WORKSPACE_TOOLBAR_KEY}:migrated%40example.com`]: JSON.stringify(["reports", "tools"]),
  });
  const config = readToolbarConfig("migrated@example.com", toolbarWorkspaceKey("p1"), storage);
  assert.equal(findToolbarFamily(config, "standard-reports")?.visible, false);
  assert.equal(findToolbarFamily(config, "tools")?.visible, false);
  assert.equal(findToolbarFamily(config, "navigation")?.visible, true);
  assert.ok(storage.values.get(toolbarConfigStorageKey("migrated@example.com"))?.includes('"version":2'));

  const second = readToolbarConfig("migrated@example.com", toolbarWorkspaceKey("p1"), storage);
  assert.equal(findToolbarFamily(second, "standard-reports")?.visible, false);
});

test("a malformed preference falls back to complete defaults instead of an empty rail", () => {
  const storage = memoryStorage({
    [toolbarConfigStorageKey("bad@example.com")]: "{not json",
  });
  const config = readToolbarConfig("bad@example.com", "project:x", storage);
  assert.equal(config.families.length, TOOLBAR_FAMILIES.length);
  assert.equal(normalizeToolbarConfig({ families: [{ id: "unknown" }] }).families.length, TOOLBAR_FAMILIES.length);
});

test("disabled commands expose a reason and administrator commands respect the role", () => {
  const permissions = toolbarCommand("admin.permissions");
  assert.ok(permissions);
  assert.ok(toolbarCommandDisabledReason(permissions, context({ capabilities: { ...context().capabilities, canAdminister: false } })));
  assert.equal(toolbarCommandDisabledReason(permissions, context()), null);

  // Commands without a server contract stay disabled for everyone and say so.
  const users = toolbarCommand("enterprise.users");
  assert.ok(users);
  assert.ok(toolbarCommandDisabledReason(users, context()));

  const edit = toolbarCommand("edit.fill-down");
  assert.ok(edit);
  assert.ok(toolbarCommandDisabledReason(edit, context()));

  const addActivity = toolbarCommand("planning.add-activity");
  assert.ok(addActivity);
  const noWbs = context({
    capabilities: { ...context().capabilities, hasWbs: false },
  });
  assert.ok(toolbarCommandDisabledReason(addActivity, noWbs));
});

test("rendering exposes both rails, every family and its Add or Remove control", () => {
  const container = {};
  const session = {
    config: defaultToolbarConfig(),
    context: context(),
    translate: (english: string) => english,
    onChange: () => {},
    direction: "ltr" as const,
  };
  const markup = renderToolbarRails(container as HTMLElement, session);
  assert.equal((markup.left.match(/data-tool-family="/g) ?? []).length, 6);
  assert.equal((markup.right.match(/data-tool-family="/g) ?? []).length, 18);
  assert.match(markup.right, /data-tool-family="critical-check"/);
  assert.match(markup.right, /data-tool-family="schedule"/);
  assert.match(markup.left, /data-tool-add-remove/);
  assert.match(markup.right, /data-tool-add-remove/);
  assert.match(markup.left, /cp-tool-rail-menu/);
  assert.match(markup.right, /cp-tool-rail-menu/);

  // Disabled commands keep their label but carry no target attribute, so a
  // click cannot fire a command that is not available.
  const enterprise = markup.right.slice(
    markup.right.indexOf('data-tool-family="enterprise"'),
    markup.right.indexOf('data-tool-family="print"'),
  );
  assert.match(enterprise, /data-tool-command-id="enterprise.users"/);
  assert.doesNotMatch(enterprise, /data-desktop-command=/);
  assert.match(enterprise, /data-tool-disabled="true"/);
});
