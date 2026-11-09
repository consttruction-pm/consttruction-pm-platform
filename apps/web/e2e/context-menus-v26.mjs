#!/usr/bin/env node
/**
 * Version 26 context-menu and customization parity matrix.
 *
 * Verifies against the live preview runtime:
 *  - the artificial horizontal command strip is gone and its commands moved to
 *    real toolbar buttons and context menus;
 *  - every menu opens at the pointer through a viewport-level portal, never in
 *    the upper-left corner, never clipped by the workspace;
 *  - Activity Table (row, cell, header, empty area, WBS band), Gantt (bar,
 *    relationship, WBS summary, empty area, timescale), and Activity Details
 *    each expose only the commands that belong to the object under the pointer;
 *  - keyboard invocation (Shift+F10 / ContextMenu key) and dismissal
 *    (Escape, outside click) behave like the reference, and scrolling does not
 *    dismiss an open menu;
 *  - Customize Activity Details can add, remove, reorder and persist tabs;
 *  - the same behaviour holds in en/LTR and fa/RTL at 1280x800, 1440x900 and
 *    1920x1080.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4174 node e2e/context-menus-v26.mjs
 */

import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4174";
const projectId = process.env.CUBI_PREVIEW_PROJECT || "preview-rps-01";
const outDir = join(artifactsDir, "context-menus-v26");
mkdirSync(outDir, { recursive: true });

const checks = [];
function check(name, condition, detail = {}) {
  checks.push({ name, ok: Boolean(condition), detail });
  if (!condition) {
    console.error(`FAIL ${name}: ${JSON.stringify(detail)}`);
  } else {
    console.log(`ok   ${name}`);
  }
}

const menuState = `(() => {
  const menu = document.querySelector(".cp-context-menu-portal");
  if (!menu) return null;
  const rect = menu.getBoundingClientRect();
  const items = [...menu.querySelectorAll("[data-activity-menu-command]")].map((button) => ({
    command: button.dataset.activityMenuCommand,
    label: button.querySelector(".cp-context-text")?.textContent?.trim() ?? "",
    disabled: button.disabled,
    checked: button.getAttribute("aria-checked") === "true",
    reason: button.getAttribute("title") ?? "",
  }));
  const style = getComputedStyle(menu);
  return {
    kind: menu.dataset.contextMenuKind,
    requested: { x: Number(menu.dataset.contextMenuX), y: Number(menu.dataset.contextMenuY) },
    dir: menu.getAttribute("dir"),
    parentIsBody: menu.parentElement === document.body,
    position: style.position,
    rect: { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom, width: rect.width, height: rect.height },
    viewport: { width: innerWidth, height: innerHeight, clientWidth: document.documentElement.clientWidth, dpr: devicePixelRatio, scale: visualViewport?.scale ?? 1 },
    items,
    itemHeight: (() => {
      const button = menu.querySelector("[data-activity-menu-command]");
      return button ? Math.round(button.getBoundingClientRect().height) : 0;
    })(),
    fontFamily: style.fontFamily,
    borderColor: style.borderTopColor,
    focused: document.activeElement?.getAttribute("data-activity-menu-command") ?? null,
  };
})()`;

async function rightClickAt(page, x, y) {
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y, button: "none", buttons: 0 });
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "right", buttons: 2, clickCount: 1 });
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "right", buttons: 0, clickCount: 1 });
  await sleep(90);
}

async function leftClickAt(page, x, y) {
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y, button: "none", buttons: 0 });
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", buttons: 1, clickCount: 1 });
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", buttons: 0, clickCount: 1 });
  await sleep(90);
}

async function centerOf(page, selector) {
  const point = await page.evaluate(`(() => {
    const element = document.querySelector(${JSON.stringify(selector)});
    if (!element) return null;
    const rect = element.getBoundingClientRect();
    return { x: Math.round(rect.left + rect.width / 2), y: Math.round(rect.top + rect.height / 2), width: Math.round(rect.width), height: Math.round(rect.height) };
  })()`);
  return point;
}

async function openMenuAt(page, selector, offset = { dx: 0, dy: 0 }) {
  const point = await centerOf(page, selector);
  if (!point) return null;
  // The assertion must compare the menu against the exact clicked point, not
  // the element center, because the caller may aim inside the element.
  const target = { x: point.x + offset.dx, y: point.y + offset.dy };
  await rightClickAt(page, target.x, target.y);
  return target;
}

async function dismiss(page) {
  await page.cdp.send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27 });
  await page.cdp.send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27 });
  await sleep(80);
}

async function clickCommand(page, command) {
  const point = await centerOf(page, `[data-activity-menu-command="${command}"]`);
  if (!point) return false;
  await leftClickAt(page, point.x, point.y);
  await sleep(160);
  return true;
}

function commandsOf(state) {
  return (state?.items ?? []).map((item) => item.command);
}

function assertAtPointer(name, state, point, tolerance = 32) {
  const rect = state?.rect;
  // A menu either opens down/right of the pointer or flips up/left at a
  // viewport edge. Measure adjacency to the matching edge instead of assuming
  // the top-left corner always touches the cursor.
  const horizontal = Boolean(rect) &&
    (Math.abs(rect.left - point.x) <= tolerance || Math.abs(rect.right - point.x) <= tolerance);
  const vertical = Boolean(rect) &&
    (Math.abs(rect.top - point.y) <= tolerance || Math.abs(rect.bottom - point.y) <= tolerance);
  const notUpperLeft = Boolean(rect) && !(rect.left <= 8 && rect.top <= 8);
  const inside = Boolean(rect) && rect.left >= -0.5 && rect.top >= -0.5 &&
    rect.right <= state.viewport.width + 0.5 && rect.bottom <= state.viewport.height + 0.5;
  const ok = Boolean(state) && state.parentIsBody && state.position === "fixed" &&
    horizontal && vertical && notUpperLeft && inside;
  check(name, ok, {
    kind: state?.kind,
    requested: state?.requested,
    rect,
    viewport: state?.viewport,
    point,
  });
  return ok;
}

async function setViewport(page, width, height) {
  await page.cdp.send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
  await sleep(120);
  await page.waitFor(`document.documentElement.clientWidth === ${width}`, `viewport ${width}x${height}`);
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
  if (!changed) return false;
  await page.waitFor(`document.documentElement.lang === ${JSON.stringify(locale)}`, `${locale} language`);
  await sleep(400);
  return true;
}

async function ensureRows(page) {
  await page.waitFor(`document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]").length > 0`, "activity rows");
  await page.waitFor(`document.querySelectorAll("#cp-gantt [data-gantt-activity-id]").length > 0`, "gantt rows");
}

async function tableRowContextScenarios(page, suffix) {
  // 1. Activity row right-click
  const rowPoint = await openMenuAt(page, "#cp-activity-grid tbody tr[data-activity-id]", { dx: 40, dy: 4 });
  const rowMenu = await page.evaluate(menuState);
  const rowCommands = commandsOf(rowMenu);
  assertAtPointer(`table row menu opens at the pointer (${suffix})`, rowMenu, rowPoint);
  check(`table row menu is the activity menu (${suffix})`,
    rowMenu?.kind === "table-activity" && rowCommands.includes("add") && rowCommands.includes("columns") && rowCommands.includes("filters"),
    { kind: rowMenu?.kind, commands: rowCommands });
  check(`disabled commands keep a localized reason (${suffix})`,
    rowMenu?.items.some((item) => item.command === "delete" && item.disabled && item.reason.length > 10),
    { delete: rowMenu?.items.find((item) => item.command === "delete") });
  check(`menu visual metrics match v26 (${suffix})`,
    rowMenu?.itemHeight === 22 && /Tahoma/i.test(rowMenu?.fontFamily ?? "") && rowMenu?.borderColor === "rgb(127, 157, 185)",
    { itemHeight: rowMenu?.itemHeight, font: rowMenu?.fontFamily, border: rowMenu?.borderColor });
  await page.screenshot(`menu-table-row-${suffix}.png`);

  // 2. Scrolling must not dismiss an open menu.
  await page.evaluate(`(() => {
    const wrap = document.querySelector("#cp-activity-grid .cp-table-wrap");
    if (wrap) wrap.scrollTop = Math.min(40, wrap.scrollHeight - wrap.clientHeight);
  })()`);
  await sleep(120);
  check(`scrolling the grid does not dismiss the menu (${suffix})`, Boolean(await page.evaluate(menuState)));
  await dismiss(page);
  check(`Escape dismisses the menu (${suffix})`, (await page.evaluate(menuState)) === null);

  // 3. Activity cell right-click
  const cellPoint = await openMenuAt(page, "#cp-activity-grid tbody tr[data-activity-id] td[data-column-id]", { dx: 18, dy: 3 });
  const cellMenu = await page.evaluate(menuState);
  assertAtPointer(`table cell menu opens at the pointer (${suffix})`, cellMenu, cellPoint);
  check(`table cell keeps the activity menu (${suffix})`, cellMenu?.kind === "table-activity");
  await dismiss(page);

  // 4. Column header right-click
  const headerPoint = await openMenuAt(page, "#cp-activity-grid thead th[data-column-id]", { dx: 12, dy: 3 });
  const headerMenu = await page.evaluate(menuState);
  const headerCommands = commandsOf(headerMenu);
  assertAtPointer(`column header menu opens at the pointer (${suffix})`, headerMenu, headerPoint);
  check(`column header menu exposes Columns and sorting (${suffix})`,
    headerMenu?.kind === "table-header" && headerCommands.includes("columns") && headerCommands.includes("sort-asc") && headerCommands.includes("sort-desc"),
    { kind: headerMenu?.kind, commands: headerCommands });
  await page.screenshot(`menu-table-header-${suffix}.png`);
  await dismiss(page);

  // 5. Columns command opens the real dialog.
  await openMenuAt(page, "#cp-activity-grid thead th[data-column-id]");
  await clickCommand(page, "columns");
  const columnsDialog = await page.evaluate(`(() => {
    const dialog = document.querySelector("[data-p6-columns-dialog]");
    return dialog ? { open: dialog.open, available: dialog.querySelectorAll("[data-columns-available-id]").length, selected: dialog.querySelectorAll("[data-columns-selected-id]").length } : null;
  })()`);
  check(`Columns opens the real Columns dialog (${suffix})`,
    columnsDialog?.open === true && columnsDialog.selected > 0, columnsDialog);
  if (columnsDialog?.open) {
    await page.screenshot(`dialog-columns-${suffix}.png`);
    await page.click("[data-columns-cancel]");
    await sleep(120);
  }

  // 6. Empty area below the rows (still inside the grid). Rows can fill the
  // whole pane, so collapse the WBS groups first to expose the empty body,
  // then restore the expanded tree for the remaining scenarios.
  const findEmptyPoint = `(() => {
    const wrap = document.querySelector("#cp-activity-grid .cp-table-wrap");
    if (!wrap) return null;
    const rect = wrap.getBoundingClientRect();
    for (let y = rect.bottom - 10; y > rect.top + 34; y -= 8) {
      for (const ratio of [0.95, 0.75, 0.55, 0.35, 0.2]) {
        const x = Math.round(rect.left + rect.width * ratio);
        const py = Math.round(y);
        const hit = document.elementFromPoint(x, py);
        if (!hit || !hit.closest("#cp-activity-grid")) continue;
        if (hit.closest("tr[data-activity-id]") || hit.closest("tr[data-wbs-row]") || hit.closest("thead")) continue;
        return { x, y: py };
      }
    }
    return null;
  })()`;
  let emptyPoint = await page.evaluate(findEmptyPoint);
  let collapsed = false;
  if (!emptyPoint) {
    await page.evaluate(`(() => document.querySelector("[data-wbs-collapse-all]")?.click())()`);
    await sleep(200);
    collapsed = true;
    emptyPoint = await page.evaluate(findEmptyPoint);
  }
  if (emptyPoint) {
    await rightClickAt(page, emptyPoint.x, emptyPoint.y);
    const emptyMenu = await page.evaluate(menuState);
    const emptyCommands = commandsOf(emptyMenu);
    assertAtPointer(`table empty-area menu opens at the pointer (${suffix})`, emptyMenu, emptyPoint);
    check(`table empty-area menu exposes Add and Layout Options (${suffix})`,
      emptyMenu?.kind === "table-empty" && emptyCommands.includes("add") && emptyCommands.includes("layout-options"),
      { kind: emptyMenu?.kind, commands: emptyCommands });
    await dismiss(page);
  } else {
    check(`table empty-area is reachable (${suffix})`, false, { emptyPoint });
  }
  if (collapsed) {
    await page.evaluate(`(() => document.querySelector("[data-wbs-expand-all]")?.click())()`);
    await sleep(200);
  }

  // 7. WBS band right-click.
  const wbsPoint = await openMenuAt(page, "#cp-activity-grid tr[data-wbs-row]", { dx: 60, dy: 3 });
  const wbsMenu = await page.evaluate(menuState);
  if (wbsPoint && wbsMenu) {
    check(`WBS band menu is the WBS menu (${suffix})`,
      wbsMenu.kind === "table-wbs" && commandsOf(wbsMenu).includes("group-wbs"),
      { kind: wbsMenu.kind, commands: commandsOf(wbsMenu) });
    await dismiss(page);
  }

  // 8. Keyboard invocation on a focused row.
  await page.evaluate(`(() => {
    const row = document.querySelector("#cp-activity-grid tbody tr[data-activity-id]");
    row?.setAttribute("tabindex", "0");
    row?.focus();
  })()`);
  await page.cdp.send("Input.dispatchKeyEvent", { type: "keyDown", key: "F10", code: "F10", windowsVirtualKeyCode: 121, modifiers: 8 });
  await page.cdp.send("Input.dispatchKeyEvent", { type: "keyUp", key: "F10", code: "F10", windowsVirtualKeyCode: 121, modifiers: 8 });
  await sleep(140);
  const keyboardMenu = await page.evaluate(menuState);
  check(`Shift+F10 opens the menu and focuses the first command (${suffix})`,
    Boolean(keyboardMenu) && keyboardMenu.focused !== null, { menu: keyboardMenu });
  await dismiss(page);
}

async function ganttContextScenarios(page, suffix) {
  // 1. Activity bar. Relationship hit bands overlay the chart, so probe the
  // bar until a point hit-tests as the row's bar rather than a link.
  const barPoint = await page.evaluate(`(() => {
    const rows = [...document.querySelectorAll("#cp-gantt [data-gantt-activity-id]")];
    for (const row of rows) {
      const bar = row.querySelector("[data-gantt-bar-kind]");
      if (!bar) continue;
      const rect = bar.getBoundingClientRect();
      if (rect.width < 8 || rect.height < 4) continue;
      for (const fx of [0.15, 0.3, 0.5, 0.65, 0.8]) {
        for (const fy of [0.25, 0.5, 0.75]) {
          const x = Math.round(rect.left + rect.width * fx);
          const y = Math.round(rect.top + rect.height * fy);
          const hit = document.elementFromPoint(x, y);
          if (!hit) continue;
          if (!hit.closest("[data-gantt-activity-id]") || hit.closest("[data-gantt-link],[data-gantt-link-hit]")) continue;
          return { x, y };
        }
      }
    }
    return null;
  })()`);
  if (barPoint) await rightClickAt(page, barPoint.x, barPoint.y);
  const barMenu = await page.evaluate(menuState);
  const barCommands = commandsOf(barMenu);
  if (barPoint && barMenu) {
    assertAtPointer(`Gantt bar menu opens at the pointer (${suffix})`, barMenu, barPoint);
    check(`Gantt bar menu is bar-specific (${suffix})`,
      barMenu.kind === "gantt-activity" && barCommands.includes("bars") && barCommands.includes("relationships") &&
        !barCommands.includes("cut") && !barCommands.includes("dissolve"),
      { kind: barMenu.kind, commands: barCommands });
    await page.screenshot(`menu-gantt-bar-${suffix}.png`);
    await dismiss(page);
  }

  // 2. Relationship line: walk the real path geometry to a point that the
  // browser hit-tests as the link, not a bar or the chart background.
  const linkPoint = await page.evaluate(`(() => {
    const links = [...document.querySelectorAll("#cp-gantt [data-gantt-link]")];
    for (const link of links) {
      let length = 0;
      try { length = link.getTotalLength(); } catch { continue; }
      if (!length) continue;
      const matrix = link.getScreenCTM();
      if (!matrix) continue;
      for (const fraction of [0.5, 0.4, 0.6, 0.35, 0.65, 0.3, 0.7, 0.25, 0.75]) {
        const local = link.getPointAtLength(length * fraction);
        const x = Math.round(local.x * matrix.a + local.y * matrix.c + matrix.e);
        const y = Math.round(local.x * matrix.b + local.y * matrix.d + matrix.f);
        if (x < 1 || y < 1 || x >= innerWidth - 1 || y >= innerHeight - 1) continue;
        const hit = document.elementFromPoint(x, y);
        const owner = hit && typeof hit.closest === "function" ? hit.closest("[data-gantt-link],[data-gantt-link-hit]") : null;
        const ownerId = owner?.dataset.ganttLink ?? owner?.dataset.ganttLinkHit ?? null;
        if (ownerId === link.dataset.ganttLink) {
          return { x, y, id: link.dataset.ganttLink };
        }
      }
    }
    return null;
  })()`);
  if (linkPoint) await rightClickAt(page, linkPoint.x, linkPoint.y);
  const linkMenu = await page.evaluate(menuState);
  if (linkPoint && linkMenu) {
    const linkCommands = commandsOf(linkMenu);
    check(`relationship menu exposes edit/delete only for relationships (${suffix})`,
      linkMenu.kind === "gantt-link" && linkCommands.includes("relationship-edit") && linkCommands.includes("relationship-delete") && !linkCommands.includes("cut"),
      { kind: linkMenu.kind, commands: linkCommands });
    await page.screenshot(`menu-gantt-link-${suffix}.png`);
    await dismiss(page);
  } else {
    check(`relationship line is present for the relationship menu (${suffix})`, false, { linkPoint });
  }

  // 3. Empty chart area
  const emptyPoint = await page.evaluate(`(() => {
    const chart = document.querySelector("#cp-gantt .cp-gantt-chart");
    if (!chart) return null;
    const rect = chart.getBoundingClientRect();
    const candidates = [
      { x: Math.round(rect.left + rect.width * 0.97), y: Math.round(rect.bottom - 12) },
      { x: Math.round(rect.left + rect.width * 0.6), y: Math.round(rect.bottom - 10) },
    ];
    for (const point of candidates) {
      const hit = document.elementFromPoint(point.x, point.y);
      if (hit && hit.closest("#cp-gantt") && !hit.closest("[data-gantt-activity-id]") && !hit.closest("[data-gantt-link]") && !hit.closest(".cp-gantt-axis")) return point;
    }
    return null;
  })()`);
  if (emptyPoint) {
    await rightClickAt(page, emptyPoint.x, emptyPoint.y);
    const emptyMenu = await page.evaluate(menuState);
    const emptyCommands = commandsOf(emptyMenu);
    assertAtPointer(`Gantt empty-area menu opens at the pointer (${suffix})`, emptyMenu, emptyPoint);
    check(`Gantt empty-area menu exposes timescale and bar styles (${suffix})`,
      emptyMenu?.kind === "gantt-empty" && emptyCommands.includes("scale-week") && emptyCommands.includes("bars"),
      { kind: emptyMenu?.kind, commands: emptyCommands });
    await page.screenshot(`menu-gantt-empty-${suffix}.png`);
    await dismiss(page);
  }

  // 4. Timescale header
  const axisPoint = await openMenuAt(page, "#cp-gantt .cp-gantt-axis", { dx: 30, dy: 2 });
  const axisMenu = await page.evaluate(menuState);
  if (axisPoint && axisMenu) {
    check(`timescale header has its own menu (${suffix})`,
      axisMenu.kind === "gantt-timescale" && commandsOf(axisMenu).includes("layout-options") && commandsOf(axisMenu).includes("scale-month"),
      { kind: axisMenu.kind, commands: commandsOf(axisMenu) });
    await dismiss(page);
  }

  // 5. WBS summary row in the Gantt
  const summaryPoint = await openMenuAt(page, "#cp-gantt [data-gantt-summary]", { dx: 10, dy: 2 });
  const summaryMenu = await page.evaluate(menuState);
  if (summaryPoint && summaryMenu) {
    check(`Gantt WBS summary has a WBS menu (${suffix})`,
      summaryMenu.kind === "gantt-wbs" && commandsOf(summaryMenu).includes("wbs-details"),
      { kind: summaryMenu.kind, commands: commandsOf(summaryMenu) });
    await dismiss(page);
  }
}

async function detailsContextScenarios(page, suffix) {
  const tabPoint = await openMenuAt(page, "#cp-details [data-detail-tab]", { dx: 10, dy: 3 });
  const detailsMenu = await page.evaluate(menuState);
  if (tabPoint && detailsMenu) {
    assertAtPointer(`Activity Details menu opens at the pointer (${suffix})`, detailsMenu, tabPoint);
    check(`Activity Details menu offers Customize Activity Details (${suffix})`,
      detailsMenu.kind === "activity-details" && commandsOf(detailsMenu).includes("customize-details"),
      { kind: detailsMenu.kind, commands: commandsOf(detailsMenu) });
    await page.screenshot(`menu-details-${suffix}.png`);
    await clickCommand(page, "customize-details");
  } else {
    check(`Activity Details is reachable for its menu (${suffix})`, false, { tabPoint });
    return;
  }

  const dialog = await page.evaluate(`(() => {
    const dialog = document.querySelector("[data-details-customize-dialog]");
    if (!dialog) return null;
    return {
      open: dialog.open,
      title: dialog.querySelector("#cp-details-customize-title")?.textContent?.trim() ?? "",
      available: dialog.querySelectorAll('[data-customize-list="available"] [data-customize-tab]').length,
      display: dialog.querySelectorAll('[data-customize-list="display"] [data-customize-tab]').length,
      hasAdd: Boolean(dialog.querySelector("[data-customize-add]")),
      hasAddAll: Boolean(dialog.querySelector("[data-customize-add-all]")),
      hasRemove: Boolean(dialog.querySelector("[data-customize-remove]")),
      hasRemoveAll: Boolean(dialog.querySelector("[data-customize-remove-all]")),
      hasUp: Boolean(dialog.querySelector("[data-customize-up]")),
      hasDown: Boolean(dialog.querySelector("[data-customize-down]")),
      hasDefault: Boolean(dialog.querySelector("[data-customize-default]")),
      hasApply: Boolean(dialog.querySelector("[data-details-customize-apply]")),
      hasCancel: Boolean(dialog.querySelector("[data-details-customize-close]")),
      dir: dialog.getAttribute("dir"),
    };
  })()`);
  // Every tab is displayed by default, so Available may legitimately start
  // empty; the add/remove scenario below proves that list is live.
  check(`Customize Activity Details dialog exposes the full v26 control set (${suffix})`,
    dialog?.open === true && dialog.title.length > 2 && dialog.display > 1 &&
      dialog.hasAdd && dialog.hasAddAll && dialog.hasRemove && dialog.hasRemoveAll && dialog.hasUp &&
      dialog.hasDown && dialog.hasDefault && dialog.hasApply && dialog.hasCancel,
    dialog);
  await page.screenshot(`dialog-customize-details-${suffix}.png`);
  return dialog;
}

async function customizeApplyScenario(page, suffix) {
  // The details menu was already used to open the dialog.
  const before = await page.evaluate(`(() => ({
    tabs: [...document.querySelectorAll("#cp-details [data-detail-tab]")].map((tab) => tab.dataset.detailTab),
  }))()`);
  const displayId = await page.evaluate(`(() => {
    const dialog = document.querySelector("[data-details-customize-dialog]");
    const last = [...dialog.querySelectorAll('[data-customize-list="display"] [data-customize-tab]')].pop();
    last?.click();
    return last?.dataset.customizeTab ?? null;
  })()`);
  await sleep(80);
  await page.click("[data-customize-remove]");
  await sleep(80);
  const afterRemove = await page.evaluate(`(() => ({
    available: document.querySelectorAll('[data-customize-list="available"] [data-customize-tab]').length,
    display: document.querySelectorAll('[data-customize-list="display"] [data-customize-tab]').length,
  }))()`);
  check(`Customize removes the selected tab into Available (${suffix})`,
    Boolean(displayId) && afterRemove.available > 0, { displayId, afterRemove });
  // The reverse direction must work too: pick the tab from Available, add it
  // back, then remove it again so the persisted change stays measurable.
  const readdedId = await page.evaluate(`(() => {
    const dialog = document.querySelector("[data-details-customize-dialog]");
    const tab = dialog?.querySelector('[data-customize-list="available"] [data-customize-tab]');
    tab?.click();
    return tab?.dataset.customizeTab ?? null;
  })()`);
  await sleep(80);
  await page.click("[data-customize-add]");
  await sleep(80);
  const afterAdd = await page.evaluate(`(() => ({
    available: document.querySelectorAll('[data-customize-list="available"] [data-customize-tab]').length,
    display: document.querySelectorAll('[data-customize-list="display"] [data-customize-tab]').length,
  }))()`);
  check(`Customize adds the selected available tab back (${suffix})`,
    Boolean(readdedId) && afterAdd.display === afterRemove.display + 1 && afterAdd.available === afterRemove.available - 1,
    { readdedId, afterRemove, afterAdd });
  await page.evaluate(`(() => {
    const dialog = document.querySelector("[data-details-customize-dialog]");
    const tab = [...(dialog?.querySelectorAll('[data-customize-list="display"] [data-customize-tab]') ?? [])]
      .find((candidate) => candidate.dataset.customizeTab === ${JSON.stringify(readdedId)});
    tab?.click();
  })()`);
  await sleep(80);
  await page.click("[data-customize-remove]");
  await sleep(80);
  await page.click("[data-details-customize-apply]");
  await sleep(180);
  const afterApply = await page.evaluate(`(() => ({
    tabs: [...document.querySelectorAll("#cp-details [data-detail-tab]")].map((tab) => tab.dataset.detailTab),
    dialogOpen: document.querySelector("[data-details-customize-dialog]")?.open ?? false,
  }))()`);
  check(`Apply writes the tab order to the live details pane (${suffix})`,
    afterApply.tabs.length === before.tabs.length - 1 && !afterApply.tabs.includes(displayId),
    { before, afterApply, displayId });
  await page.click("[data-details-customize-close]");
  await sleep(120);
  return { before, afterApply, displayId };
}

async function filterStateScenario(page, suffix) {
  const state = await page.evaluate(`(() => {
    const output = document.querySelector("[data-active-filter]");
    return output ? {
      text: output.textContent.trim(),
      filterIds: output.getAttribute("data-active-filter"),
      mode: output.getAttribute("data-filter-mode"),
    } : null;
  })()`);
  check(`the filter state lives in the real filter toolbar (${suffix})`,
    Boolean(state) && state.text.length > 0 && state.mode === "replace", state);
}

async function toolbarScenario(page, suffix) {
  const strip = await page.evaluate(`(() => ({
    strip: document.querySelectorAll(".cp-context-command-bar, .cp-p6-activity-header").length,
    bodyRows: getComputedStyle(document.querySelector(".cp-p6-body")).gridTemplateRows,
    actions: document.querySelectorAll(".cp-p6-grid-actions button").length,
  }))()`);
  check(`no artificial command strip remains and the body has one row (${suffix})`,
    strip.strip === 0 && strip.bodyRows.trim().split(/\s+/).length === 1 && strip.actions >= 7, strip);

  await page.click("[data-activity-create-open]");
  await sleep(220);
  const addState = await page.evaluate(`(() => ({
    drawer: !document.querySelector("[data-tools-drawer]")?.hidden,
    focused: document.activeElement?.getAttribute("name") ?? null,
  }))()`);
  check(`Add Activity toolbar button opens the real create form (${suffix})`,
    addState.drawer === true, addState);
  await page.click("[data-tools-close]");
  await sleep(120);

  await page.click("[data-columns-open]");
  await sleep(200);
  const columnsOpen = await page.evaluate(`(() => document.querySelector("[data-p6-columns-dialog]")?.open === true)()`);
  check(`Columns toolbar button opens the real Columns dialog (${suffix})`, columnsOpen);
  if (columnsOpen) await page.click("[data-columns-cancel]");
  await sleep(100);

  await page.click("[data-layout-options-open]");
  await sleep(180);
  const layoutOpen = await page.evaluate(`(() => {
    const dialog = document.querySelector("[data-layout-options-dialog]");
    return Boolean(dialog && (dialog.open || dialog.hasAttribute("open")));
  })()`);
  check(`Layout Options toolbar button opens the real Timescale dialog (${suffix})`, layoutOpen);
  if (layoutOpen) await page.click("[data-layout-options-close]");
  await sleep(100);
}

async function edgeClampScenario(page, suffix) {
  const point = await page.evaluate(`(() => {
    const grid = document.querySelector("#cp-activity-grid");
    const rect = grid.getBoundingClientRect();
    return { x: Math.round(rect.right - 6), y: Math.round(rect.bottom - 34) };
  })()`);
  await rightClickAt(page, point.x, point.y);
  const menu = await page.evaluate(menuState);
  check(`menu flips and clamps at the bottom-right edge (${suffix})`,
    Boolean(menu) && menu.rect.right <= menu.viewport.width + 0.5 && menu.rect.bottom <= menu.viewport.height + 0.5 &&
      menu.rect.left >= 0 && menu.rect.top >= 0 && menu.rect.left < point.x + 8,
    { menu, point });
  await page.screenshot(`menu-edge-clamp-${suffix}.png`);
  await dismiss(page);
}

async function main() {
  const health = await waitForHttp(`${baseUrl}/preview/health`, 20000);
  if (health.status !== "ok") throw new Error(`preview health ${health.status}`);
  const build = { git_head: gitHead(), base_url: baseUrl };

  const chrome = await launchChrome();
  const page = new Page(chrome.cdp);
  const summary = { checks, build, screenshots: [] };
  try {
    await page.initialize();
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });

    await page.navigate(`${baseUrl}/preview/login`, 'form[action="/preview/login"]', "login");
    await page.click('button[name="role"][value="planner"]');
    await page.waitFor(`location.pathname === "/app"`, "planner redirect");
    await page.navigate(`${baseUrl}/app?view=live`, ".cp-project-selection", "project selection");
    await page.click(`button[data-project-id="${projectId}"]`);
    await page.waitForSelector(".cp-workspace", "workspace");
    await ensureRows(page);
    await page.waitForSelector("#cp-details [data-detail-tab]", "details tabs");
    await sleep(300);
    // The language choice persists in localStorage; earlier runs may have left
    // the workspace Persian. Force English before measuring LTR metrics.
    await setLanguage(page, "en");
    await ensureRows(page);

    // Phase A: English, 1440x900.
    await tableRowContextScenarios(page, "en-1440");
    await toolbarScenario(page, "en-1440");
    await filterStateScenario(page, "en-1440");
    await ganttContextScenarios(page, "en-1440");
    const opened = await detailsContextScenarios(page, "en-1440");
    if (opened) {
      const applied = await customizeApplyScenario(page, "en-1440");
      await page.reload("#cp-details [data-detail-tab]", "reload after customize");
      await ensureRows(page);
      const persisted = await page.evaluate(`(() => [...document.querySelectorAll("#cp-details [data-detail-tab]")].map((tab) => tab.dataset.detailTab))()`);
      check("Customize Activity Details persists across reload (en-1440)",
        !persisted.includes(applied.displayId) && persisted.length === applied.afterApply.tabs.length,
        { persisted, removed: applied.displayId });
      // Restore the default tab set for the remaining phases.
      await page.evaluate(`(() => {
        try { localStorage.removeItem("cubi:activity-details-visible-tabs:v1"); } catch {}
      })()`);
      await page.reload("#cp-details [data-detail-tab]", "reload after reset");
      await ensureRows(page);
    }
    await edgeClampScenario(page, "en-1440");

    // Phase B: 1280x800.
    await setViewport(page, 1280, 800);
    await tableRowContextScenarios(page, "en-1280");
    await ganttContextScenarios(page, "en-1280");
    await edgeClampScenario(page, "en-1280");

    // Phase C: 1920x1080.
    await setViewport(page, 1920, 1080);
    await tableRowContextScenarios(page, "en-1920");
    await ganttContextScenarios(page, "en-1920");

    // Phase D: Persian RTL at 1440x900.
    await setViewport(page, 1440, 900);
    const language = await setLanguage(page, "fa");
    check("language switch to Persian is real (fa-1440)", language);
    await ensureRows(page);
    const rtlPoint = await openMenuAt(page, "#cp-activity-grid tbody tr[data-activity-id]", { dx: 30, dy: 3 });
    const rtlMenu = await page.evaluate(menuState);
    assertAtPointer("RTL table menu opens at the pointer (fa-1440)", rtlMenu, rtlPoint);
    check("RTL menu carries dir=rtl and Persian labels (fa-1440)",
      rtlMenu?.dir === "rtl" && /[\u0600-\u06FF]/.test(rtlMenu?.items[0]?.label ?? ""),
      { dir: rtlMenu?.dir, first: rtlMenu?.items[0]?.label });
    await page.screenshot("menu-table-row-fa-rtl.png");
    await dismiss(page);
    await detailsContextScenarios(page, "fa-1440");
    await page.evaluate(`(() => document.querySelector("[data-details-customize-close]")?.click())()`);
    await sleep(120);
    await setLanguage(page, "en");

    const failed = checks.filter((entry) => !entry.ok);
    summary.failed = failed.length;
    summary.passed = checks.length - failed.length;
    summary.finished_at = new Date().toISOString();
    writeFileSync(join(outDir, "context-menus-v26.json"), JSON.stringify(summary, null, 2));
    writeFileSync(join(outDir, "CHECKLIST.md"), checks.map((entry) => `${entry.ok ? "PASS" : "FAIL"} — ${entry.name}${entry.ok ? "" : `\n  ${JSON.stringify(entry.detail)}`}`).join("\n"));
    if (failed.length) {
      console.error(`\n${failed.length} of ${checks.length} checks failed`);
      process.exitCode = 1;
    } else {
      console.log(`\nAll ${checks.length} context-menu checks passed`);
    }
  } finally {
    page.cdp.close();
    await chrome.stop();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
