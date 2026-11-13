import assert from "node:assert/strict";
import test from "node:test";

import {
  REGISTER_MENU_UNAVAILABLE_REASON,
  REGISTER_MENU_WRITE_REASON,
  buildRegisterMenuItems,
  type RegisterCommandSpec,
} from "./workspace-register-context-menu.js";

const COMMANDS: readonly RegisterCommandSpec[] = [
  {
    command: "edit",
    label: { en: "Edit Risk", fa: "ویرایش ریسک" },
    icon: "edit",
    control: "[data-risk-edit]",
    requiresWrite: true,
  },
  {
    command: "run",
    label: { en: "Run Report", fa: "اجرای گزارش" },
    icon: "progress",
    control: '[data-report-action="run"]',
    scope: "host",
  },
  {
    command: "delete",
    label: { en: "Delete Risk", fa: "حذف ریسک" },
    icon: "delete",
    control: "[data-risk-delete]",
    requiresWrite: true,
    separatorBefore: true,
  },
];

const available = () => ({ present: true, disabled: false });

test("register menu items mirror the real controls with localized labels", () => {
  const items = buildRegisterMenuItems({ commands: COMMANDS, locale: "en-US", canWrite: true }, available);
  assert.deepEqual(items.map((item) => item.command), ["edit", "run", "delete"]);
  assert.equal(items[0].label, "Edit Risk");
  assert.equal(items[0].disabled, false);
  assert.equal(items[0].reason, undefined);
  assert.equal(items[0].icon, "edit");
  assert.equal(items[2].separatorBefore, true);
});

test("register menu labels follow the Persian locale", () => {
  const items = buildRegisterMenuItems({ commands: COMMANDS, locale: "fa-IR", canWrite: true }, available);
  assert.equal(items[0].label, "ویرایش ریسک");
  assert.equal(items[2].label, "حذف ریسک");
});

test("a viewer sees write commands disabled with the permission reason", () => {
  // The row buttons are not rendered at all for a viewer, so the control is
  // reported missing; the permission reason is the more useful explanation.
  const items = buildRegisterMenuItems(
    { commands: COMMANDS, locale: "en", canWrite: false },
    (command) => ({ present: command !== "edit" && command !== "delete", disabled: false }),
  );
  const edit = items.find((item) => item.command === "edit");
  const remove = items.find((item) => item.command === "delete");
  const run = items.find((item) => item.command === "run");
  assert.equal(edit?.disabled, true);
  assert.equal(edit?.reason, REGISTER_MENU_WRITE_REASON.en);
  assert.equal(remove?.disabled, true);
  assert.equal(remove?.reason, REGISTER_MENU_WRITE_REASON.en);
  // Running a stored report definition is a read and stays available.
  assert.equal(run?.disabled, false);
});

test("a missing control is disabled with the unavailable reason, not silently dropped", () => {
  const items = buildRegisterMenuItems(
    { commands: COMMANDS, locale: "en", canWrite: true },
    (command) => ({ present: command !== "delete", disabled: false }),
  );
  const remove = items.find((item) => item.command === "delete");
  assert.equal(remove?.disabled, true);
  assert.equal(remove?.reason, REGISTER_MENU_UNAVAILABLE_REASON.en);
});

test("a control disabled for the selected record disables its command", () => {
  // Run Monitoring stays disabled for a threshold that is not active.
  const items = buildRegisterMenuItems(
    { commands: COMMANDS, locale: "fa", canWrite: true },
    (command) => ({ present: true, disabled: command === "run" }),
  );
  const run = items.find((item) => item.command === "run");
  assert.equal(run?.disabled, true);
  assert.equal(run?.reason, REGISTER_MENU_UNAVAILABLE_REASON.fa);
});

test("every command keeps its identity so the menu can dispatch the control it mirrors", () => {
  const items = buildRegisterMenuItems({ commands: COMMANDS, locale: "en", canWrite: false }, available);
  assert.deepEqual(
    items.map((item) => item.command),
    COMMANDS.map((command) => command.command),
  );
  // No command is invented: the menu is exactly the declared set.
  assert.equal(items.length, COMMANDS.length);
});
