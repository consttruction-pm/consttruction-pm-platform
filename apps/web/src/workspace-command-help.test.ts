import assert from "node:assert/strict";
import test from "node:test";
import {
  COMMAND_HELP_ROWS,
  NO_OFFICIAL_TOPIC,
  commandHelp,
  noTopicReason,
  windowHelp,
} from "./workspace-command-help.js";
import { TOOLBAR_COMMAND_IDS } from "./workspace-toolbar-registry.js";
import { getDesktopShortcuts } from "./workspace-desktop-shell.js";
import { HELP_REGISTRY, WORKSPACE_MENU_HELP } from "./help-registry.js";
import { WORKSPACE_NAVIGATION } from "./workspace-navigation.js";

const ROW_IDS = new Set(HELP_REGISTRY.map((entry) => entry.id));

test("every command either names a real topic row or records why none exists", () => {
  const shortcutCommands = getDesktopShortcuts(["project", "schedule", "wbs"])
    .map((shortcut) => shortcut.command)
    .filter((command): command is NonNullable<typeof command> => Boolean(command));
  const commands = new Set([...TOOLBAR_COMMAND_IDS, ...shortcutCommands]);
  for (const command of commands) {
    assert.ok(
      COMMAND_HELP_ROWS[command] || NO_OFFICIAL_TOPIC[command],
      `${command} must map to a traceability row or be listed as having no topic`,
    );
  }
  for (const command of Object.keys(COMMAND_HELP_ROWS)) {
    assert.ok(!NO_OFFICIAL_TOPIC[command], `${command} cannot be both mapped and unmapped`);
    assert.ok(ROW_IDS.has(COMMAND_HELP_ROWS[command]), `${command} points at unknown row ${COMMAND_HELP_ROWS[command]}`);
  }
});

test("every mapped command resolves to an official topic that the row records", () => {
  for (const command of Object.keys(COMMAND_HELP_ROWS)) {
    const help = commandHelp(command);
    assert.ok(help, `${command} has a row but no topic`);
    assert.equal(help.row, COMMAND_HELP_ROWS[command]);
    assert.ok(help.topic.title.trim(), `${command} topic needs a title`);
    assert.match(help.topic.url, /^https:\/\/docs\.oracle\.com\//, `${command} must cite Oracle's Help`);
    assert.equal(help.topic.source, "P6 Professional V26 HTML Help");
  }
});

test("unmapped commands explain themselves instead of citing a page", () => {
  for (const [command, reason] of Object.entries(NO_OFFICIAL_TOPIC)) {
    assert.equal(commandHelp(command), null);
    assert.ok(reason.trim().length > 10, `${command} needs a real reason`);
    assert.equal(noTopicReason(command), reason);
  }
  assert.equal(commandHelp("not.a.command"), null);
  assert.equal(noTopicReason("not.a.command"), null);
});

test("every navigation window resolves through the menu-surface map", () => {
  for (const item of WORKSPACE_NAVIGATION) {
    const help = windowHelp(item.key);
    if (item.key === "backup") {
      assert.equal(help, null, "backup has no P6 Professional topic");
      continue;
    }
    assert.ok(help, `${item.key} must resolve`);
    assert.equal(WORKSPACE_MENU_HELP[item.key], help.row);
    assert.match(help.topic.url, /^https:\/\/docs\.oracle\.com\//);
  }
});
