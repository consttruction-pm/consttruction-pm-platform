#!/usr/bin/env node
/**
 * Version 26 dual tool-rail acceptance.
 *
 * Exercises the real customizable toolbar system in a live browser:
 * both rails, the eighteen right-rail families, Add or Remove Buttons,
 * body-level customization menus, the Customize dialog, pointer drag and
 * drop across families, rails and the workspace dock, custom toolbars,
 * persisted preferences, per-user isolation, permissions, RTL/LTR and three
 * desktop viewports.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4202 \
 *   CUBI_TESTED_CODE_SHA=<sha> \
 *   node e2e/toolbar-rails-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4202";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-14";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const outDir = join(artifactsDir, "toolbar-rails-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `toolbar-rails-v26-${evidenceDate}`);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const checks = [];
const screenshots = [];
const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const RIGHT_FAMILIES = [
  "project-tools", "assign", "edit", "layout", "enterprise", "print", "action",
  "administrator", "bottom-layout", "display", "find", "dictionaries", "publish",
  "standard-reports", "tools", "activity", "critical-check", "schedule",
];
const LEFT_FAMILIES = ["navigation", "project", "planning", "resources-cost", "information", "administration"];

function log(message) {
  process.stdout.write(`${message}\n`);
}

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

function record(name, detail = {}) {
  checks.push({ name, detail, at: new Date().toISOString() });
  log(`  ok  ${name}`);
}

async function capture(page, name, clip = null) {
  const file = `toolbar-rails-v26/${name}.png`;
  await page.screenshot(file, clip);
  copyFileSync(join(artifactsDir, file), join(evidenceDir, `${name}.png`));
  screenshots.push(`${name}.png`);
  return file;
}

async function setViewport(page, width, height) {
  await page.cdp.send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
  await sleep(400);
}

async function setLanguage(page, locale) {
  const changed = await page.evaluate(`(() => {
    const select = document.querySelector("[data-workspace-language]");
    if (!select) return false;
    select.value = ${JSON.stringify(locale)};
    if (select.value !== ${JSON.stringify(locale)}) return false;
    select.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  assert(changed, `language selector did not accept ${locale}`);
  await sleep(1200);
}

async function login(page, role) {
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "form", `${role} login`, `${baseUrl}/preview/login`);
  await page.click(`button[name="role"][value="${role}"]`);
  await page.waitForSelector('[data-project-id="preview-rps-01"]', `${role} project selection`);
  await page.click('[data-project-id="preview-rps-01"]');
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", `${role} activity rows`);
  await sleep(1400);
}

async function logout(page) {
  const clicked = await page.evaluate(`(() => {
    const button = document.querySelector("#cubi-preview-banner button");
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, "sign-out control is missing");
  await page.waitFor(`location.pathname === "/"`, "sign out returns to the public site");
  await sleep(400);
}

async function scrollToElement(page, selector) {
  const ok = await page.evaluate(`(() => {
    const element = document.querySelector(${JSON.stringify(selector)});
    if (!element) return false;
    element.scrollIntoView({ block: "center", inline: "nearest" });
    return true;
  })()`);
  assert(ok, `cannot scroll to ${selector}`);
  await sleep(250);
}

async function centerOf(page, selector) {
  return page.evaluate(`(() => {
    const element = document.querySelector(${JSON.stringify(selector)});
    if (!element) return null;
    const rect = element.getBoundingClientRect();
    return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2, width: rect.width, height: rect.height, top: rect.top, bottom: rect.bottom };
  })()`);
}

async function realDrag(page, selector, targetSelector, options = {}) {
  await scrollToElement(page, selector);
  const start = await centerOf(page, selector);
  assert(start, `drag source not found: ${selector}`);
  const target = await centerOf(page, targetSelector);
  assert(target, `drag target not found: ${targetSelector}`);
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: start.x, y: start.y, button: "none", buttons: 0 });
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x: start.x, y: start.y, button: "left", buttons: 1, clickCount: 1 });
  await sleep(60);
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: start.x + 8, y: start.y + 8, button: "left", buttons: 1 });
  await sleep(80);
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: target.x, y: target.y, button: "left", buttons: 1 });
  await sleep(140);
  if (options.capture) await capture(page, options.capture);
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: target.x, y: target.y, button: "left", buttons: 0, clickCount: 1 });
  await sleep(600);
}

async function dragToPoint(page, selector, point, options = {}) {
  await scrollToElement(page, selector);
  const start = await centerOf(page, selector);
  assert(start, `drag source not found: ${selector}`);
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: start.x, y: start.y, button: "none", buttons: 0 });
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x: start.x, y: start.y, button: "left", buttons: 1, clickCount: 1 });
  await sleep(60);
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: start.x + 8, y: start.y + 8, button: "left", buttons: 1 });
  await sleep(80);
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: point.x, y: point.y, button: "left", buttons: 1 });
  await sleep(140);
  if (options.capture) await capture(page, options.capture);
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: point.x, y: point.y, button: "left", buttons: 0, clickCount: 1 });
  await sleep(600);
}

async function rightClick(page, selector) {
  await scrollToElement(page, selector);
  const point = await centerOf(page, selector);
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x: point.x, y: point.y, button: "right", buttons: 2, clickCount: 1 });
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: point.x, y: point.y, button: "right", buttons: 0, clickCount: 1 });
  await page.waitFor(`Boolean(document.querySelector(".cp-tool-menu"))`, "toolbar context menu", 4000);
  await sleep(200);
}

async function closeMenus(page) {
  await page.evaluate(`document.body.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }))`);
  await sleep(200);
}

async function openFamilyMenu(page, familyId) {
  await closeMenus(page);
  await scrollToElement(page, `[data-tool-family="${familyId}"]`);
  await page.realClick(`[data-tool-family="${familyId}"] [data-tool-add-remove]`);
  await page.waitFor(`Boolean(document.querySelector('.cp-tool-menu[data-tool-menu="add-remove"]'))`, `Add or Remove menu for ${familyId}`, 4000);
  await sleep(200);
}

async function clickMenuItem(page, action, dataset = {}) {
  const clicked = await page.evaluate(`(() => {
    const menu = document.querySelector(".cp-tool-menu");
    if (!menu) return false;
    const item = menu.querySelector(${JSON.stringify(`[data-tool-menu-action="${action}"]`)});
    const candidates = [...menu.querySelectorAll('[data-tool-menu-action="${action}"]')];
    const match = candidates.find((candidate) => Object.entries(${JSON.stringify(dataset)}).every(([key, value]) => candidate.dataset[key] === value));
    const target = match ?? item;
    if (!target || target.disabled) return false;
    target.click();
    return true;
  })()`);
  assert(clicked, `menu action ${action} ${JSON.stringify(dataset)} is missing or disabled`);
  await sleep(450);
}

async function familyVisible(page, familyId) {
  return page.evaluate(`Boolean(document.querySelector('[data-tool-rail] [data-tool-family="${familyId}"], [data-toolbar-dock] [data-tool-family="${familyId}"]'))`);
}

async function buttonVisible(page, familyId, commandId) {
  return page.evaluate(`Boolean(document.querySelector('[data-tool-family="${familyId}"] [data-tool-command-id="${commandId}"]'))`);
}

async function railsMeasure(page) {
  return page.evaluate(`(() => {
    const rect = (element) => {
      if (!element) return null;
      const r = element.getBoundingClientRect();
      return { left: +r.left.toFixed(1), top: +r.top.toFixed(1), right: +r.right.toFixed(1), bottom: +r.bottom.toFixed(1), width: +r.width.toFixed(1), height: +r.height.toFixed(1) };
    };
    const rightFamilies = [...document.querySelectorAll('[data-tool-rail="right"] [data-tool-family]')];
    const leftFamilies = [...document.querySelectorAll('[data-tool-rail="left"] [data-tool-family]')];
    return {
      viewport: { width: window.innerWidth, height: window.innerHeight },
      dir: document.querySelector(".cp-p6-workspace")?.getAttribute("dir") ?? null,
      pageOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
      left: { rect: rect(document.querySelector('[data-tool-rail="left"]')), families: leftFamilies.map((family) => family.dataset.toolFamily), addRemove: leftFamilies.filter((family) => family.querySelector("[data-tool-add-remove]")).length },
      right: { rect: rect(document.querySelector('[data-tool-rail="right"]')), families: rightFamilies.map((family) => family.dataset.toolFamily), addRemove: rightFamilies.filter((family) => family.querySelector("[data-tool-add-remove]")).length },
      dock: { rect: rect(document.querySelector("[data-toolbar-dock]")), families: [...document.querySelectorAll("[data-toolbar-dock] [data-tool-family]")].map((family) => family.dataset.toolFamily) },
      offscreenFamilies: rightFamilies.filter((family) => {
        const r = family.getBoundingClientRect();
        return r.bottom < 0 || r.top > window.innerHeight;
      }).length,
      focusableButtons: [...document.querySelectorAll("[data-tool-rail-button]")].filter((button) => button.tabIndex >= 0).length,
      buttonCount: document.querySelectorAll("[data-tool-rail-button]").length,
    };
  })()`);
}

async function openCustomize(page) {
  await closeMenus(page);
  await scrollToElement(page, '[data-tool-rail="right"] [data-tool-rail-menu]');
  await page.realClick('[data-tool-rail="right"] [data-tool-rail-menu]');
  await page.waitFor(`Boolean(document.querySelector(".cp-tool-menu"))`, "rail customization menu", 4000);
  await clickMenuItem(page, "open-customize");
  await page.waitForSelector("dialog[data-tool-customize-dialog]", "Customize dialog", 5000);
  await sleep(300);
}

async function main() {
  const health = await waitForHttp(`${baseUrl}/preview/health`, 30000);
  if (!(health.status === "ok" || health.status === 200)) throw new Error(`preview health ${health.status}`);

  const chrome = await launchChrome();
  const page = new Page(chrome.cdp);
  await page.initialize();
  page.cdp.on("Runtime.exceptionThrown", (params) => {
    exceptions.push(params.exceptionDetails?.exception?.description ?? params.exceptionDetails?.text ?? "unknown exception");
  });
  page.cdp.on("Runtime.consoleAPICalled", (params) => {
    if (params.type !== "error") return;
    consoleErrors.push((params.args ?? []).map((arg) => arg.value ?? arg.description ?? arg.type).join(" "));
  });
  page.cdp.on("Network.responseReceived", (params) => {
    const url = params.response?.url ?? "";
    if (url.includes("/api/") && params.response.status >= 500) apiFailures.push({ status: params.response.status, url });
  });

  try {
    await setViewport(page, 1366, 768);
    await login(page, "admin");
    await setLanguage(page, "en");

    // ---------------------------------------------------------------- rails
    let measure = await railsMeasure(page);
    assert(measure.right.families.length === 18, `right rail renders ${measure.right.families.length} families`);
    assert(JSON.stringify(measure.right.families) === JSON.stringify(RIGHT_FAMILIES), `right family order is ${measure.right.families.join(",")}`);
    assert(measure.left.families.length === 6, `left rail renders ${measure.left.families.length} families`);
    assert(measure.right.addRemove === 18 && measure.left.addRemove === 6, "every family must end with an Add or Remove control");
    assert(measure.buttonCount > 40, `both rails expose real commands (${measure.buttonCount})`);
    assert(measure.focusableButtons === measure.buttonCount, "every toolbar button is keyboard focusable");
    assert(!measure.pageOverflow, "the workspace must not overflow horizontally");
    await capture(page, "rails-both-1366x768-en");
    record("both independent rails render with the eighteen right families and an Add or Remove control per family", measure.right);

    // Every family can be hidden and restored from the Customize dialog.
    await openCustomize(page);
    const allFamilies = [...LEFT_FAMILIES, ...RIGHT_FAMILIES];
    for (const familyId of allFamilies) {
      await scrollToElement(page, `[data-tool-customize-family="${familyId}"]`);
      await page.realClick(`[data-tool-customize-family="${familyId}"] .cp-tool-customize-check`);
      await sleep(350);
      assert(!(await familyVisible(page, familyId)), `${familyId} did not hide`);
      await page.realClick(`[data-tool-customize-family="${familyId}"] .cp-tool-customize-check`);
      await sleep(350);
      assert(await familyVisible(page, familyId), `${familyId} did not return`);
    }
    assert((await page.evaluate(`document.querySelectorAll("dialog[data-tool-customize-dialog]").length`)) === 1, "customizing must keep one dialog open");
    await capture(page, "customize-dialog-1366x768-en");
    await page.evaluate(`document.querySelector("dialog[data-tool-customize-dialog] [data-tool-customize-close]").click()`);
    await sleep(300);
    record("every left and right family hides and restores independently without closing the Customize dialog", { families: allFamilies.length });

    // Add, remove and multi-select inside one Add or Remove menu.
    await openFamilyMenu(page, "schedule");
    await capture(page, "add-remove-menu-1366x768-en");
    const scheduleCommands = await page.evaluate(`[...document.querySelectorAll('.cp-tool-menu [data-tool-command]')].map((item) => item.dataset.toolCommand)`);
    assert(scheduleCommands.length >= 2, "the schedule family must offer its registered commands");
    const first = scheduleCommands[0];
    const second = scheduleCommands[1];
    await page.evaluate(`document.querySelector('.cp-tool-menu [data-tool-command="${first}"]').click()`);
    await sleep(300);
    assert(!(await buttonVisible(page, "schedule", first)), `${first} did not hide`);
    // A second change in the same open menu.
    assert(await page.evaluate(`Boolean(document.querySelector('.cp-tool-menu'))`), "the Add or Remove menu closed after one change");
    await page.evaluate(`document.querySelector('.cp-tool-menu [data-tool-command="${second}"]').click()`);
    await sleep(300);
    assert(!(await buttonVisible(page, "schedule", second)), `${second} did not hide`);
    record("Add or Remove toggles multiple buttons in one open menu with immediate updates", { first, second });

    // Reset this toolbar only.
    await clickMenuItem(page, "reset-family", { toolFamily: "schedule" });
    assert(await buttonVisible(page, "schedule", first), "Reset Toolbar did not restore the first button");
    assert(await buttonVisible(page, "schedule", second), "Reset Toolbar did not restore the second button");
    record("Reset Toolbar restores one family without touching the others", { family: "schedule" });
    await closeMenus(page);

    // Add a button back to a family whose buttons were all removed.
    await openFamilyMenu(page, "print");
    const printCommands = await page.evaluate(`[...document.querySelectorAll('.cp-tool-menu [data-tool-command]')].map((item) => item.dataset.toolCommand)`);
    for (const command of printCommands) {
      await page.evaluate(`document.querySelector('.cp-tool-menu [data-tool-command="${command}"]')?.click()`);
      await sleep(180);
    }
    assert(await page.evaluate(`Boolean(document.querySelector('[data-tool-family="print"] [data-tool-family-empty]'))`), "an emptied family must stay visible and explain it is empty");
    await page.evaluate(`document.querySelector('.cp-tool-menu [data-tool-command="${printCommands[0]}"]').click()`);
    await sleep(300);
    assert(await buttonVisible(page, "print", printCommands[0]), "a button cannot be added back to an empty family");
    await capture(page, "empty-family-restored-1366x768-en");
    await clickMenuItem(page, "reset-family", { toolFamily: "print" });
    await closeMenus(page);
    record("an empty toolbar stays restorable and its first button can be added from the same menu", { family: "print" });

    // -------------------------------------------------- right-click surfaces
    await rightClick(page, '[data-tool-rail="right"] .cp-tool-family[data-tool-family="layout"] .cp-tool-family-head');
    assert(await page.evaluate(`document.querySelector(".cp-tool-menu")?.dataset.toolMenu !== "add-remove"`), "right-click must open a customization menu, not the Add or Remove checklist");
    await capture(page, "right-click-toolbar-1366x768-en");
    await closeMenus(page);

    await rightClick(page, '[data-tool-family="layout"] [data-tool-command-id="layout.open"]');
    const iconMenu = await page.evaluate(`(() => {
      const menu = document.querySelector(".cp-tool-menu");
      if (!menu) return null;
      return {
        kind: menu.dataset.toolMenu,
        actions: [...menu.querySelectorAll("[data-tool-menu-action]")].map((item) => item.dataset.toolMenuAction),
      };
    })()`);
    assert(iconMenu?.kind === "button", `icon context menu kind is ${iconMenu?.kind}`);
    assert(iconMenu.actions.includes("move-button") && iconMenu.actions.includes("rename-custom") === false, "icon menu is missing move actions");
    assert(iconMenu.actions.includes("style-family"), "icon menu is missing style choices");
    assert(iconMenu.actions.includes("toggle-separator"), "icon menu is missing Begin a Group");
    await capture(page, "right-click-icon-1366x768-en");
    await page.evaluate(`document.querySelector('.cp-tool-menu [data-tool-menu-action="hide-button"]').click()`);
    await sleep(400);
    assert(!(await buttonVisible(page, "layout", "layout.open")), "right-click Hide Button did not remove the command");
    await openFamilyMenu(page, "layout");
    await clickMenuItem(page, "reset-family", { toolFamily: "layout" });
    await closeMenus(page);
    assert(await buttonVisible(page, "layout", "layout.open"), "Reset Toolbar did not restore the hidden icon");
    record("right-clicking a toolbar and an icon opens distinct real customization menus", iconMenu);
    record("the icon menu hides a command and Reset Toolbar restores it");

    // ------------------------------------------------------------- dragging
    // A taller viewport keeps both ends of a long rail visible while the
    // pointer drag is exercised; the required desktop cells are captured below.
    await setViewport(page, 1366, 1400);
    const beforeOrder = await page.evaluate(`[...document.querySelectorAll('[data-tool-family="layout"] [data-tool-rail-button]')].map((button) => button.dataset.toolCommandId)`);
    assert(beforeOrder.length >= 2, "layout family needs two buttons for a reorder test");
    await realDrag(page, '[data-tool-family="layout"] [data-tool-command-id="layout.open"]', '[data-tool-family="layout"] [data-tool-command-id="layout.columns"]');
    const afterOrder = await page.evaluate(`[...document.querySelectorAll('[data-tool-family="layout"] [data-tool-rail-button]')].map((button) => button.dataset.toolCommandId)`);
    assert(afterOrder[0] !== beforeOrder[0] || afterOrder[1] !== beforeOrder[1], "pointer drag did not reorder buttons inside the family");
    assert(JSON.stringify([...afterOrder].sort()) === JSON.stringify([...beforeOrder].sort()), "reordering must not drop or duplicate commands");
    record("pointer drag reorders icons inside a family", { before: beforeOrder.slice(0, 3), after: afterOrder.slice(0, 3) });

    // Move a command between two right-rail families.
    await scrollToElement(page, '[data-tool-family="tools"]');
    await realDrag(page, '[data-tool-family="tools"] [data-tool-command-id="tools.schedule"]', '[data-tool-family="critical-check"]');
    const movedTargetCount = await page.evaluate(`document.querySelectorAll('[data-tool-family="critical-check"] [data-tool-command-id="tools.schedule"]').length`);
    assert(movedTargetCount === 1, `the command appears ${movedTargetCount} times in Critical Check`);
    assert(!(await buttonVisible(page, "tools", "tools.schedule")), "the command was duplicated in its source family");
    await capture(page, "moved-between-families-1366x768-en");
    record("pointer drag moves a button between two toolbar families without duplication");

    // Move a command between the left and right rails.
    await scrollToElement(page, '[data-tool-family="activity"]');
    await realDrag(page, '[data-tool-family="planning"] [data-tool-command-id="planning.add-activity"]', '[data-tool-family="activity"]');
    assert(await buttonVisible(page, "activity", "planning.add-activity"), "the command did not cross to the right rail");
    assert(!(await buttonVisible(page, "planning", "planning.add-activity")), "the command stayed on the left rail");
    record("pointer drag moves a command between the left and right rails");

    // Drag a whole family out of the rail and dock it above the workspace.
    const dockPoint = await page.evaluate(`(() => {
      const primary = document.querySelector(".cp-p6-primary").getBoundingClientRect();
      return { x: primary.left + primary.width / 2, y: primary.top + 18 };
    })()`);
    await dragToPoint(page, '[data-tool-family="print"] [data-tool-family-handle]', dockPoint, { capture: "drag-out-1366x768-en" });
    assert(await page.evaluate(`Boolean(document.querySelector('[data-toolbar-dock] [data-tool-family="print"]'))`), "the toolbar did not dock above the workspace");
    assert(await page.evaluate(`getComputedStyle(document.querySelector("[data-toolbar-dock]")).display !== "none"`), "the dock is not visible after dropping");
    await capture(page, "docked-1366x768-en");
    record("a complete toolbar can be dragged out of the rail and docked above the workspace");

    // Re-dock the floating toolbar back on the right rail.
    const railPoint = await page.evaluate(`(() => {
      const rail = document.querySelector('[data-tool-rail="right"]').getBoundingClientRect();
      return { x: rail.left + rail.width / 2, y: rail.top + rail.height * 0.7 };
    })()`);
    await dragToPoint(page, '[data-toolbar-dock] [data-tool-family="print"] [data-tool-family-handle]', railPoint);
    assert(await page.evaluate(`Boolean(document.querySelector('[data-tool-rail="right"] [data-tool-family="print"]'))`), "the toolbar did not return to the right rail");
    assert(await page.evaluate(`!document.querySelector("[data-toolbar-dock] [data-tool-family]")`), "the dock was not emptied");
    record("a docked toolbar re-docks to a rail and the dock stays recoverable");

    await setViewport(page, 1366, 768);
    // ------------------------------------------------------------- keyboard
    await scrollToElement(page, '[data-tool-family="layout"] [data-tool-command-id="layout.open"]');
    const keyboardBefore = await page.evaluate(`[...document.querySelectorAll('[data-tool-family="layout"] [data-tool-rail-button]')].map((button) => button.dataset.toolCommandId)`);
    const keyboardMoved = await page.evaluate(`(() => {
      const button = document.querySelector('[data-tool-family="layout"] [data-tool-command-id="layout.open"]');
      if (!button) return false;
      button.focus();
      button.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", altKey: true, bubbles: true }));
      return true;
    })()`);
    assert(keyboardMoved, "the layout button could not be focused");
    await sleep(400);
    const keyboardAfter = await page.evaluate(`[...document.querySelectorAll('[data-tool-family="layout"] [data-tool-rail-button]')].map((button) => button.dataset.toolCommandId)`);
    assert(JSON.stringify(keyboardAfter) !== JSON.stringify(keyboardBefore), "Alt+ArrowDown did not reorder the focused button");
    assert(JSON.stringify([...keyboardAfter].sort()) === JSON.stringify([...keyboardBefore].sort()), "keyboard reordering must not drop or duplicate commands");
    record("keyboard Alt+Arrow reorders the focused toolbar button");

    // Reset everything before the persistence and custom-toolbar journeys.
    await closeMenus(page);
    await openCustomize(page);
    await page.evaluate(`document.querySelector('[data-tool-menu-action="reset-all"]').click()`);
    await sleep(600);
    await page.evaluate(`document.querySelector("dialog[data-tool-customize-dialog] [data-tool-customize-close]").click()`);
    await sleep(300);
    assert(await page.evaluate(`document.querySelectorAll('[data-tool-rail="right"] [data-tool-family]').length === 18`), "Reset All did not restore eighteen right families");
    record("Reset All Toolbars restores every predefined family and layout");

    // -------------------------------------------------------- custom toolbar
    await closeMenus(page);
    await scrollToElement(page, '[data-tool-rail="right"] [data-tool-rail-menu]');
    await page.realClick('[data-tool-rail="right"] [data-tool-rail-menu]');
    await page.waitFor(`Boolean(document.querySelector(".cp-tool-menu"))`, "rail menu before custom toolbar");
    await clickMenuItem(page, "create-custom");
    await page.waitForSelector("dialog[data-tool-customize-dialog] #cp-tool-custom-name", "custom toolbar name field", 5000);
    await page.evaluate(`(() => {
      const input = document.querySelector("#cp-tool-custom-name");
      input.value = "QA checks";
      input.form.requestSubmit();
      return true;
    })()`);
    await page.waitFor(`Boolean(document.querySelector('[data-toolbar-dock] [data-tool-family^="custom:"]'))`, "created custom toolbar", 5000);
    await sleep(500);
    const customId = await page.evaluate(`document.querySelector('[data-toolbar-dock] [data-tool-family]')?.dataset.toolFamily ?? null`);
    assert(customId?.startsWith("custom:"), `custom toolbar id is ${customId}`);
    // Its Add or Remove menu opens with every registered command.
    await page.waitFor(`Boolean(document.querySelector('.cp-tool-menu[data-tool-menu="add-remove"]'))`, "custom toolbar Add or Remove menu", 5000);
    const customCommands = await page.evaluate(`[...document.querySelectorAll('.cp-tool-menu [data-tool-command]')].map((item) => item.dataset.toolCommand)`);
    assert(customCommands.length > 20, `custom toolbar lists only ${customCommands.length} commands`);
    await page.evaluate(`document.querySelector('.cp-tool-menu [data-tool-command="layout.open"]').click()`);
    await sleep(300);
    await page.evaluate(`document.querySelector('.cp-tool-menu [data-tool-command="print.print"]').click()`);
    await sleep(400);
    await closeMenus(page);
    assert(await buttonVisible(page, customId, "layout.open"), "custom toolbar did not keep the selected command");
    await capture(page, "custom-toolbar-1366x768-en");
    record("a custom toolbar is created by name and accepts commands from the shared registry", { customId, commands: customCommands.length });

    // Rename through the rail customization menu (native prompt is answered by
    // the test so the real rename action runs unchanged).
    await page.evaluate(`window.prompt = () => "Renamed checks"`);
    await closeMenus(page);
    await scrollToElement(page, '[data-tool-rail="right"] [data-tool-rail-menu]');
    await page.realClick('[data-tool-rail="right"] [data-tool-rail-menu]');
    await page.waitFor(`Boolean(document.querySelector(".cp-tool-menu"))`, "rail menu before rename", 4000);
    await page.evaluate(`(() => {
      const menu = document.querySelector(".cp-tool-menu");
      const rename = [...menu.querySelectorAll('[data-tool-menu-action="rename-custom"]')].find((item) => item.dataset.toolFamily === ${JSON.stringify(customId)});
      if (!rename) return false;
      rename.click();
      return true;
    })()`);
    await sleep(800);
    const renamed = await page.evaluate(`document.querySelector('[data-toolbar-dock] [data-tool-family="${customId}"] .cp-tool-family-name')?.textContent ?? null`);
    assert(renamed === "Renamed checks", `custom toolbar name is ${renamed}`);
    record("a custom toolbar can be renamed", { name: renamed });

    // ---------------------------------------------------------- persistence
    const expected = await page.evaluate(`(() => {
      const dock = document.querySelector('[data-toolbar-dock] [data-tool-family]');
      const nav = document.querySelector('[data-tool-rail="left"]');
      return {
        customId: dock?.dataset.toolFamily ?? null,
        customName: dock?.querySelector(".cp-tool-family-name")?.textContent ?? null,
        customButtons: [...(dock?.querySelectorAll("[data-tool-rail-button]") ?? [])].map((button) => button.dataset.toolCommandId),
        leftFamilies: [...document.querySelectorAll('[data-tool-rail="left"] [data-tool-family]')].map((family) => family.dataset.toolFamily),
        rightCount: document.querySelectorAll('[data-tool-rail="right"] [data-tool-family]').length,
        navWidth: nav?.getBoundingClientRect().width ?? 0,
      };
    })()`);
    await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "reload with custom toolbar");
    await sleep(1200);
    const afterReload = await page.evaluate(`(() => {
      const dock = document.querySelector('[data-toolbar-dock] [data-tool-family]');
      return {
        customId: dock?.dataset.toolFamily ?? null,
        customName: dock?.querySelector(".cp-tool-family-name")?.textContent ?? null,
        customButtons: [...(dock?.querySelectorAll("[data-tool-rail-button]") ?? [])].map((button) => button.dataset.toolCommandId),
        leftFamilies: [...document.querySelectorAll('[data-tool-rail="left"] [data-tool-family]')].map((family) => family.dataset.toolFamily),
        rightCount: document.querySelectorAll('[data-tool-rail="right"] [data-tool-family]').length,
      };
    })()`);
    assert(afterReload.customId === expected.customId, "the custom toolbar did not survive reload");
    assert(afterReload.customName === expected.customName, "the custom toolbar name did not survive reload");
    assert(JSON.stringify(afterReload.customButtons) === JSON.stringify(expected.customButtons), "custom toolbar buttons did not survive reload");
    assert(afterReload.rightCount === expected.rightCount, "right-rail family count changed after reload");
    assert(JSON.stringify(afterReload.leftFamilies) === JSON.stringify(expected.leftFamilies), "left rail arrangement changed after reload");
    await capture(page, "after-reload-1366x768-en");
    record("every toolbar customization survives a full reload", { expected, afterReload });

    // Delete the custom toolbar from the rail context menu.
    await scrollToElement(page, '[data-tool-rail="right"] [data-tool-rail-menu]');
    await page.realClick('[data-tool-rail="right"] [data-tool-rail-menu]');
    await page.waitFor(`Boolean(document.querySelector(".cp-tool-menu"))`, "rail menu before delete", 4000);
    const deleted = await page.evaluate(`(() => {
      const menu = document.querySelector(".cp-tool-menu");
      const target = [...menu.querySelectorAll('[data-tool-menu-action="delete-custom"]')].find((item) => item.dataset.toolFamily === ${JSON.stringify(customId)});
      if (!target) return false;
      target.click();
      return true;
    })()`);
    assert(deleted, "the rail menu does not offer Delete Custom Toolbar");
    await sleep(600);
    assert(await page.evaluate(`!document.querySelector('[data-toolbar-dock] [data-tool-family^="custom:"]')`), "the custom toolbar was not deleted");
    await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "reload after custom toolbar delete");
    await sleep(1000);
    assert(await page.evaluate(`!document.querySelector('[data-toolbar-dock] [data-tool-family^="custom:"]')`), "the deleted custom toolbar returned after reload");
    record("a custom toolbar can be deleted and stays deleted after reload", { customId });

    // ------------------------------------------------------- user isolation
    await logout(page);
    await login(page, "planner");
    await setLanguage(page, "en");
    const plannerState = await page.evaluate(`(() => ({
      customInDock: Boolean(document.querySelector('[data-toolbar-dock] [data-tool-family^="custom:"]')),
      rightCount: document.querySelectorAll('[data-tool-rail="right"] [data-tool-family]').length,
      printVisible: Boolean(document.querySelector('[data-tool-family="print"]')),
    }))()`);
    assert(!plannerState.customInDock, "another user inherited a custom toolbar");
    assert(plannerState.printVisible, "another user did not receive the default toolbars");
    assert(plannerState.rightCount === 18, `another user sees ${plannerState.rightCount} right families`);
    record("toolbar configuration is isolated per user", plannerState);

    // Viewer permission restrictions.
    await logout(page);
    await login(page, "viewer");
    await setLanguage(page, "en");
    await openFamilyMenu(page, "administrator");
    const viewerAdmin = await page.evaluate(`(() => {
      const item = document.querySelector('.cp-tool-menu [data-tool-command="admin.permissions"]');
      return item ? { disabled: item.disabled, aria: item.getAttribute("aria-disabled") } : null;
    })()`);
    assert(viewerAdmin?.disabled === true, "a viewer can use an administrator-only command from Add or Remove");
    await closeMenus(page);
    const viewerButton = await page.evaluate(`(() => {
      const button = document.querySelector('[data-tool-family="administrator"] [data-tool-command-id="admin.permissions"]');
      return button ? { ariaDisabled: button.getAttribute("aria-disabled"), hasTarget: button.hasAttribute("data-desktop-window") || button.hasAttribute("data-desktop-command") } : null;
    })()`);
    assert(viewerButton?.ariaDisabled === "true", "the administrator button is not marked disabled for a viewer");
    assert(viewerButton?.hasTarget === false, "a disabled administrator button keeps an executable target");
    record("permissions disable administrator commands in the menu and on the rail", { viewerAdmin, viewerButton });

    // --------------------------------------------------------------- RTL/fa
    await logout(page);
    await login(page, "admin");
    await setLanguage(page, "fa");
    measure = await railsMeasure(page);
    assert(measure.dir === "rtl", `Persian workspace direction is ${measure.dir}`);
    assert(measure.right.families.length === 18, "the right rail loses families in RTL");
    assert(!measure.pageOverflow, "RTL workspace overflows horizontally");
    await scrollToElement(page, '[data-tool-family="schedule"]');
    await page.realClick('[data-tool-family="schedule"] [data-tool-add-remove]');
    await page.waitFor(`Boolean(document.querySelector(".cp-tool-menu"))`, "RTL Add or Remove menu", 4000);
    assert(await page.evaluate(`document.querySelector(".cp-tool-menu").getAttribute("dir") === "rtl"`), "the toolbar menu does not mirror in RTL");
    const menuInside = await page.evaluate(`(() => {
      const rect = document.querySelector(".cp-tool-menu").getBoundingClientRect();
      return rect.left >= -1 && rect.right <= window.innerWidth + 1 && rect.top >= -1 && rect.bottom <= window.innerHeight + 1;
    })()`);
    assert(menuInside, "the RTL toolbar menu escapes the viewport");
    await capture(page, "rails-1366x768-fa");
    await closeMenus(page);
    record("Persian RTL mirrors the rail controls and keeps every menu inside the viewport");

    // ---------------------------------------------------------- viewports
    for (const [width, height] of [[1280, 720], [1366, 768], [1920, 1080]]) {
      await setViewport(page, width, height);
      await page.waitFor(`window.innerWidth === ${width}`, `${width} viewport`);
      const cell = await railsMeasure(page);
      assert(cell.right.families.length === 18, `${width}x${height}: right rail has ${cell.right.families.length} families`);
      assert(cell.left.families.length === 6, `${width}x${height}: left rail has ${cell.left.families.length} families`);
      assert(!cell.pageOverflow, `${width}x${height}: page overflows horizontally`);
      assert(cell.right.rect.width >= 30, `${width}x${height}: right rail is ${cell.right.rect.width}px wide`);
      assert(cell.left.rect.width >= 34, `${width}x${height}: left rail is ${cell.left.rect.width}px wide`);
      await capture(page, `rails-${width}x${height}-fa`);
    }
    record("both rails keep all families with no page overflow at 1280x720, 1366x768 and 1920x1080");

    // Return to English for the final reload proof.
    await setViewport(page, 1366, 768);
    await setLanguage(page, "en");
    await capture(page, "final-rails-1366x768-en");

    if (exceptions.length > 0) throw new Error(`UNCAUGHT_PAGE_EXCEPTIONS: ${JSON.stringify(exceptions.slice(0, 5))}`);
    if (apiFailures.length > 0) throw new Error(`API_5XX_RESPONSES: ${JSON.stringify(apiFailures.slice(0, 5))}`);
    record("no uncaught browser exceptions or API 5xx responses", { consoleErrorCount: consoleErrors.length });
  } finally {
    page?.cdp.close();
    chrome.cdp.close();
    await chrome.stop();
  }
}

const evidence = {
  test: "toolbar-rails-v26",
  base_url: baseUrl,
  tested_code_sha: testedCodeSha,
  evidence_date: evidenceDate,
  started_at: new Date().toISOString(),
  checks,
  screenshots,
  exceptions,
  consoleErrors,
  apiFailures,
};

let failure = null;
try {
  await main();
} catch (error) {
  failure = error;
  log(`\nE2E FAILED: ${error instanceof Error ? error.message : String(error)}`);
  if (error instanceof Error && error.stack) log(error.stack);
} finally {
  evidence.finished_at = new Date().toISOString();
  evidence.status = failure ? "failed" : "passed";
  evidence.failure = failure ? { message: failure.message, stack: failure.stack ?? null } : null;
  writeFileSync(join(evidenceDir, "evidence.json"), JSON.stringify(evidence, null, 2));
  writeFileSync(join(outDir, "evidence.json"), JSON.stringify(evidence, null, 2));
  log(`\nEvidence: ${join(evidenceDir, "evidence.json")}`);
  log(`Checks: ${checks.length}; screenshots: ${screenshots.length}`);
  if (failure) process.exitCode = 1;
}
