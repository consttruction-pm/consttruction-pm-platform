#!/usr/bin/env node
/**
 * Browser E2E for WS-008: full-screen and responsive workspace behaviour, plus
 * the shell keyboard contract that makes those controls reachable.
 *
 * The suite runs against the real preview runtime and a headless Chrome whose
 * viewport is emulated at the four acceptance sizes (1280x720, 1366x768,
 * 1920x1080 and a 844x390 landscape phone). It proves:
 *
 *   1. no viewport produces page-level horizontal or vertical overflow, and
 *      every pane stays inside its parent with the table/Gantt/details order
 *      intact;
 *   2. a short viewport keeps the whole workspace reachable through the
 *      `#workspace` scroller instead of clipping the details pane;
 *   3. menus stay inside the viewport and scroll internally when the window is
 *      short, and Escape returns focus to the menu trigger;
 *   4. application keys work from `document.body` (Alt+mnemonic, F1, Ctrl+A)
 *      and never steal a chord from a focused text field;
 *   5. the Full Screen control performs a real `requestFullscreen()` /
 *      `exitFullscreen()` and reflects the state in aria-pressed, the tooltip
 *      and the label, with no layout or data change;
 *   6. the table/Gantt and details splitters respond to pointer drag and
 *      arrow/Home/End keys, clamp at their documented bounds, persist and
 *      survive a reload;
 *   7. Persian RTL keeps the same geometry and stays inside the viewport;
 *   8. nothing in the suite mutates schedule input.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4198 \
 *   CUBI_TESTED_CODE_SHA=<code commit> node e2e/workspace-responsive-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4198";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-13";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "workspace-responsive-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `workspace-responsive-v26-${evidenceDate}`);
rmSync(outDir, { recursive: true, force: true });
rmSync(evidenceDir, { recursive: true, force: true });
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT_ID = "preview-rps-01";
const VIEWPORTS = [
  { id: "1280x720", width: 1280, height: 720 },
  { id: "1366x768", width: 1366, height: 768 },
  { id: "1920x1080", width: 1920, height: 1080 },
  { id: "844x390", width: 844, height: 390 },
];
const MENU_IDS = ["workspace", "edit", "view", "project", "tools", "help"];

const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const scheduleMutations = [];
const scenarios = [];
const screenshots = [];

function log(message) {
  process.stdout.write(`${message}\n`);
}

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

function record(id, name, status, details = {}) {
  scenarios.push({ id, name, status, at: new Date().toISOString(), ...details });
  log(`  ${status.toUpperCase()} ${id}. ${name}`);
}

async function scenario(id, name, body) {
  log(`\n[${id}] ${name}`);
  try {
    const details = (await body()) ?? {};
    record(id, name, "pass", details);
    return details;
  } catch (error) {
    record(id, name, "fail", { error: String(error && error.stack ? error.stack : error) });
    throw error;
  }
}

async function capture(page, name) {
  const file = `workspace-responsive-v26/${name}.png`;
  await page.screenshot(file);
  copyFileSync(join(artifactsDir, file), join(evidenceDir, `${name}.png`));
  screenshots.push(`${name}.png`);
}

async function setViewport(page, width, height) {
  await page.cdp.send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
  await sleep(600);
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
  await sleep(900);
}

/** Trusted key events through CDP, not synthetic DOM events. */
async function press(page, { key, code, vk, modifiers = 0 }) {
  const event = { key, code, windowsVirtualKeyCode: vk, nativeVirtualKeyCode: vk, modifiers };
  await page.cdp.send("Input.dispatchKeyEvent", { type: "keyDown", ...event });
  await page.cdp.send("Input.dispatchKeyEvent", { type: "keyUp", ...event });
  await sleep(180);
}

async function readActivities(page) {
  const context = await page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${PROJECT_ID}/open", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: "{}",
    });
    const body = await response.json();
    return body.context;
  })()`, { awaitPromise: true });
  assert(context, "project open returned no context");
  const result = await page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${PROJECT_ID}/p6/activities", {
      headers: {
        "content-type": "application/json",
        "X-Tenant-Id": ${JSON.stringify(context.tenant_id)},
        "X-Project-Id": ${JSON.stringify(context.project_id)},
        "X-Project-Revision": String(${JSON.stringify(String(context.revision))}),
      },
    });
    const body = await response.json();
    return {
      status: response.status,
      activities: Array.isArray(body.activities) ? body.activities.map((entry) => entry.activity).filter(Boolean) : [],
    };
  })()`, { awaitPromise: true });
  assert(result.status === 200, `activity read returned ${result.status}`);
  return result.activities;
}

function fingerprint(activities) {
  return JSON.stringify(activities.map((activity) => [activity.activity_id, activity.name, activity.status, activity.duration_value, activity.record_revision]));
}

async function geometry(page) {
  return page.evaluate(`(() => {
    const box = (selector) => {
      const element = document.querySelector(selector);
      if (!element) return null;
      const rect = element.getBoundingClientRect();
      return {
        top: Math.round(rect.top), bottom: Math.round(rect.bottom),
        left: Math.round(rect.left), right: Math.round(rect.right),
        width: Math.round(rect.width), height: Math.round(rect.height),
      };
    };
    const wrap = document.querySelector(".cp-table-wrap");
    const workspace = document.querySelector("#workspace");
    return {
      viewport: [innerWidth, innerHeight],
      direction: document.documentElement.dir || "ltr",
      documentOverflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      documentOverflowY: document.documentElement.scrollHeight - document.documentElement.clientHeight,
      menubar: box(".cp-menubar"),
      toolbar: box(".cp-toolbar"),
      host: box(".cp-desktop-host"),
      main: box(".cp-main"),
      split: box(".cp-p6-split"),
      grid: box("#cp-activity-grid"),
      gantt: box("#cp-gantt"),
      details: box("#cp-details"),
      tableWrap: box(".cp-table-wrap"),
      tableScrollX: wrap ? wrap.scrollWidth - wrap.clientWidth : null,
      tableScrollY: wrap ? wrap.scrollHeight - wrap.clientHeight : null,
      workspaceScroll: workspace ? {
        overflowY: getComputedStyle(workspace).overflowY,
        scrollHeight: workspace.scrollHeight,
        clientHeight: workspace.clientHeight,
        maxScrollTop: workspace.scrollHeight - workspace.clientHeight,
      } : null,
      splitTable: document.querySelector("[data-panel-split]")?.style.getPropertyValue("--cp-split-table") ?? null,
      splitPrimary: document.querySelector(".cp-main")?.style.getPropertyValue("--cp-split-primary") ?? null,
      ganttRows: document.querySelectorAll("[data-gantt-activity-id]").length,
      tableRows: document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]").length,
      lastRowBottom: Math.round(document.querySelector("#cp-activity-grid tbody tr[data-activity-id]:last-of-type")?.getBoundingClientRect().bottom ?? 0),
      toolbarCompact: document.querySelectorAll(".cp-toolbar-button.is-compact").length,
      toolbarTotal: document.querySelectorAll(".cp-toolbar-button").length,
      toolbarUnnamed: [...document.querySelectorAll(".cp-toolbar-button")].filter((button) => !(button.getAttribute("aria-label") ?? "").trim()).length,
    };
  })()`);
}

function assertNoOverflow(metrics, label) {
  assert(metrics.documentOverflowX === 0, `${label}: page overflows horizontally by ${metrics.documentOverflowX}px`);
  assert(metrics.documentOverflowY === 0, `${label}: page overflows vertically by ${metrics.documentOverflowY}px`);
}

function assertPaneOrder(metrics, label) {
  assert(metrics.menubar && metrics.toolbar, `${label}: shell chrome is missing`);
  assert(metrics.toolbar.top >= metrics.menubar.bottom - 1, `${label}: toolbar overlaps the menu bar`);
  assert(metrics.main && metrics.split, `${label}: workspace panes are missing`);
  assert(metrics.grid && metrics.gantt, `${label}: table or Gantt pane is missing`);
  if (metrics.direction === "rtl") {
    assert(metrics.gantt.right <= metrics.grid.left + 1, `${label}: Gantt and table panes overlap in RTL`);
  } else {
    assert(metrics.grid.right <= metrics.gantt.left + 1, `${label}: table and Gantt panes overlap`);
  }
  assert(metrics.grid.bottom <= metrics.details.top + 1, `${label}: details pane overlaps the table pane`);
  assert(metrics.main.right <= metrics.viewport[0] + 1, `${label}: workspace is wider than the viewport`);
}

async function openMenu(page, id) {
  await page.evaluate(`document.querySelector('[data-desktop-menu="${id}"]')?.click()`);
  await sleep(220);
}

async function menuState(page, id) {
  return page.evaluate(`(() => {
    const popup = document.querySelector('[data-desktop-popup="${id}"]');
    if (!popup) return null;
    const rect = popup.getBoundingClientRect();
    const triggers = [...document.querySelectorAll("[data-desktop-menu]")]
      .filter((trigger) => trigger.getBoundingClientRect().width > 0);
    return {
      hidden: popup.hidden,
      top: Math.round(rect.top), bottom: Math.round(rect.bottom),
      left: Math.round(rect.left), right: Math.round(rect.right),
      scrollHeight: popup.scrollHeight,
      clientHeight: popup.clientHeight,
      active: document.activeElement?.dataset?.desktopItem ?? document.activeElement?.dataset?.desktopMenu ?? document.activeElement?.tagName ?? null,
      triggerClipped: triggers.some((trigger) => trigger.scrollWidth - trigger.clientWidth > 1),
    };
  })()`);
}

async function pointerDrag(page, selector, to) {
  const rect = await page.evaluate(`(() => {
    const element = document.querySelector(${JSON.stringify(selector)});
    if (!element) return null;
    const box = element.getBoundingClientRect();
    return { x: box.left + box.width / 2, y: box.top + box.height / 2 };
  })()`);
  assert(rect, `pointer target ${selector} is missing`);
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x: rect.x, y: rect.y, button: "left", buttons: 1, clickCount: 1 });
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: to.x, y: to.y, button: "left", buttons: 1 });
  await sleep(120);
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: to.x, y: to.y, button: "left", buttons: 0, clickCount: 1 });
  await sleep(250);
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
  page.cdp.on("Network.requestWillBeSent", (params) => {
    const request = params.request ?? {};
    const method = request.method ?? "";
    const url = request.url ?? "";
    if (!["POST", "PUT", "PATCH", "DELETE"].includes(method)) return;
    if (url.includes("/p6/activities") || url.includes("/p6/schedule") || url.includes("/api/v1/schedule")) {
      scheduleMutations.push({ method, url, at: new Date().toISOString() });
    }
  });

  const report = {
    contract: "cubi-workspace-responsive-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    expected: {},
    scenarios,
    screenshots,
    scheduleMutations,
    exceptions,
    consoleErrors,
    apiFailures,
  };

  function writeReport() {
    report.scenarios = scenarios;
    report.passed = scenarios.filter((entry) => entry.status === "pass").length;
    report.failed = scenarios.filter((entry) => entry.status === "fail").length;
    const json = JSON.stringify(report, null, 2);
    writeFileSync(join(outDir, "workspace-responsive-v26.json"), json);
    writeFileSync(join(evidenceDir, "workspace-responsive-v26.json"), json);
  }

  const state = { total: 0, perViewport: {} };

  try {
    await setViewport(page, 1280, 720);
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
    const persona = await page.evaluate(`(() => {
      const button = document.querySelector('button[name="role"][value="admin"]');
      if (!button) return false;
      button.click();
      return true;
    })()`);
    assert(persona, "admin persona button is missing");
    await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
    await page.click('[data-project-id="preview-rps-01"]');
    await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
    await sleep(1800);

    const before = await readActivities(page);
    state.total = before.length;
    const beforeFingerprint = fingerprint(before);
    assert(state.total > 0, "the read model returned no activities");
    report.expected = { total: state.total, viewports: VIEWPORTS.map((entry) => entry.id) };

    await scenario("01", "1280x720 keeps every pane inside the viewport with no page overflow", async () => {
      await setViewport(page, 1280, 720);
      const metrics = await geometry(page);
      assertNoOverflow(metrics, "1280x720");
      assertPaneOrder(metrics, "1280x720");
      assert(metrics.tableRows === state.total, `table paints ${metrics.tableRows} rows, read model has ${state.total}`);
      assert(metrics.ganttRows === state.total, `Gantt paints ${metrics.ganttRows} rows, read model has ${state.total}`);
      assert(metrics.toolbarUnnamed === 0, `${metrics.toolbarUnnamed} toolbar buttons have no accessible name`);
      assert(metrics.tableScrollX > 0 || metrics.tableScrollY > 0, "the table has no internal scroller at 1280x720");
      assert(metrics.workspaceScroll && metrics.workspaceScroll.maxScrollTop === 0, "1280x720 should not need a workspace scroller");
      state.perViewport["1280x720"] = metrics;
      await capture(page, "01-1280x720");
      return { rows: metrics.tableRows, gantt: metrics.gantt.width, grid: metrics.grid.width, scrollX: metrics.tableScrollX, compact: metrics.toolbarCompact };
    });

    await scenario("02", "1366x768 grows the panes without overlap or clipping", async () => {
      await setViewport(page, 1366, 768);
      const metrics = await geometry(page);
      assertNoOverflow(metrics, "1366x768");
      assertPaneOrder(metrics, "1366x768");
      const base = state.perViewport["1280x720"];
      assert(metrics.gantt.width > base.gantt.width, `Gantt did not grow: ${base.gantt.width} -> ${metrics.gantt.width}`);
      assert(metrics.main.height >= base.main.height, `workspace shrank vertically: ${base.main.height} -> ${metrics.main.height}`);
      state.perViewport["1366x768"] = metrics;
      await capture(page, "02-1366x768");
      return { gantt: metrics.gantt.width, main: metrics.main.height };
    });

    await scenario("03", "1920x1080 gives the Gantt the extra width and keeps every row", async () => {
      await setViewport(page, 1920, 1080);
      const metrics = await geometry(page);
      assertNoOverflow(metrics, "1920x1080");
      assertPaneOrder(metrics, "1920x1080");
      const base = state.perViewport["1280x720"];
      assert(metrics.gantt.width - base.gantt.width >= 250, `Gantt width ${metrics.gantt.width} is not materially wider than ${base.gantt.width}`);
      assert(metrics.tableRows === state.total && metrics.ganttRows === state.total, "row parity broke at 1920x1080");
      state.perViewport["1920x1080"] = metrics;
      await capture(page, "03-1920x1080");
      return { gantt: metrics.gantt.width, rows: metrics.tableRows };
    });

    await scenario("04", "844x390 landscape keeps the workspace reachable through its own scroller", async () => {
      await setViewport(page, 844, 390);
      const metrics = await geometry(page);
      assertNoOverflow(metrics, "844x390");
      assert(metrics.menubar && metrics.toolbar, "844x390: shell chrome is missing");
      assert(metrics.tableScrollX > 0, "844x390: the table has no horizontal scroller");
      assert(metrics.workspaceScroll && metrics.workspaceScroll.overflowY === "auto", `844x390: #workspace overflow is ${metrics.workspaceScroll?.overflowY}`);
      assert(metrics.workspaceScroll.maxScrollTop > 0, "844x390: #workspace cannot scroll, so the details pane is unreachable");
      const scrollResult = await page.evaluate(`(() => {
        const workspace = document.querySelector("#workspace");
        workspace.scrollTop = workspace.scrollHeight;
        const details = document.querySelector("#cp-details")?.getBoundingClientRect();
        return { scrollTop: workspace.scrollTop, detailsTop: Math.round(details?.top ?? -1), detailsBottom: Math.round(details?.bottom ?? -1), viewport: innerHeight };
      })()`);
      assert(scrollResult.detailsTop < scrollResult.viewport && scrollResult.detailsBottom > 0, "details pane is not reachable after scrolling");
      await capture(page, "04-landscape-mobile");
      await page.evaluate(`document.querySelector("#workspace").scrollTop = 0`);
      return { scrollTop: scrollResult.scrollTop, detailsTop: scrollResult.detailsTop, tableScrollX: metrics.tableScrollX, compact: metrics.toolbarCompact };
    });

    await scenario("05", "Every menu stays inside the viewport and Escape restores the trigger", async () => {
      await setViewport(page, 844, 390);
      const rows = [];
      for (const id of MENU_IDS) {
        await openMenu(page, id);
        const open = await menuState(page, id);
        assert(open && !open.hidden, `menu ${id} did not open`);
        assert(open.left >= 0 && open.right <= 844 + 1, `menu ${id} is outside the horizontal viewport (${open.left}..${open.right})`);
        assert(open.top >= 0 && open.bottom <= 390 + 1, `menu ${id} is outside the vertical viewport (${open.top}..${open.bottom})`);
        assert(open.triggerClipped === false, `menu ${id}: a menu trigger clips its label`);
        rows.push({ id, bottom: open.bottom, scrollHeight: open.scrollHeight, clientHeight: open.clientHeight });
        if (id === "view") {
          assert(open.scrollHeight > open.clientHeight, "the View menu does not scroll internally on a short viewport");
          await capture(page, "05-menu-landscape");
        }
        await press(page, { key: "Escape", code: "Escape", vk: 27 });
        const closed = await menuState(page, id);
        assert(closed?.hidden === true, `menu ${id} did not close on Escape`);
        assert(closed?.active === id, `focus returned to ${closed?.active}, not the ${id} trigger`);
      }
      return { menus: rows.length, scrolls: rows.filter((row) => row.scrollHeight > row.clientHeight).length };
    });

    await scenario("06", "Application keys work from document.body and never steal a text-field chord", async () => {
      await setViewport(page, 1280, 720);
      await page.evaluate(`document.activeElement?.blur?.(); document.body.focus()`);
      await press(page, { key: "f", code: "KeyF", vk: 70, modifiers: 1 });
      const menu = await menuState(page, "workspace");
      assert(menu && !menu.hidden, "Alt+F did not open the File menu from a body focus");
      assert(menu.active === "file.new", `Alt+F focused ${menu.active}`);
      await press(page, { key: "ArrowDown", code: "ArrowDown", vk: 40 });
      const moved = await menuState(page, "workspace");
      assert(moved.active !== "file.new", "ArrowDown did not move inside the File menu");
      await press(page, { key: "Escape", code: "Escape", vk: 27 });
      assert((await menuState(page, "workspace")).hidden, "Escape did not close the File menu");
      await capture(page, "06-keyboard-body");

      await press(page, { key: "F1", code: "F1", vk: 112 });
      const shortcutDialog = await page.evaluate(`(() => ({ open: [...document.querySelectorAll("dialog")].filter((dialog) => dialog.open).map((dialog) => dialog.dataset.desktopDialog ?? dialog.className) }))()`);
      assert(shortcutDialog.open.includes("shortcuts"), `F1 opened ${JSON.stringify(shortcutDialog.open)}`);
      await press(page, { key: "Escape", code: "Escape", vk: 27 });
      const closedDialog = await page.evaluate(`[...document.querySelectorAll("dialog")].filter((dialog) => dialog.open).length`);
      assert(closedDialog === 0, "Escape did not close the shortcuts dialog");

      // Native Ctrl+A inside the search field must select text, not activities.
      await page.evaluate(`(() => {
        const input = document.querySelector('[data-activity-filter]');
        if (!input) return;
        input.value = "A1";
        input.dispatchEvent(new Event("input", { bubbles: true }));
      })()`);
      await sleep(900);
      await page.evaluate(`document.querySelector('[data-activity-filter]')?.focus()`);
      await sleep(150);
      const selectedBefore = await page.evaluate(`Number(document.querySelector("[data-activity-counts]")?.getAttribute("data-count-selected") ?? -1)`);
      await press(page, { key: "a", code: "KeyA", vk: 65, modifiers: 2 });
      const field = await page.evaluate(`(() => {
        const input = document.querySelector('[data-activity-filter]');
        return {
          selection: input && input.selectionEnd !== null && input.selectionStart !== null ? input.selectionEnd - input.selectionStart : -1,
          length: input?.value?.length ?? 0,
          selected: Number(document.querySelector("[data-activity-counts]")?.getAttribute("data-count-selected") ?? -1),
        };
      })()`);
      assert(field.selection === field.length, `Ctrl+A in the search field selected ${field.selection}/${field.length} characters`);
      assert(field.selected === selectedBefore, `Ctrl+A in the search field changed the activity selection ${selectedBefore} -> ${field.selected}`);
      await page.evaluate(`document.querySelector('[data-activity-filter]')?.blur()`);

      // Clear the query, then the same chord from the page selects the whole project.
      await page.evaluate(`(() => {
        const input = document.querySelector('[data-activity-filter]');
        if (!input) return;
        input.value = "";
        input.dispatchEvent(new Event("input", { bubbles: true }));
      })()`);
      await sleep(900);
      await page.evaluate(`document.activeElement?.blur?.(); document.body.focus()`);
      await press(page, { key: "a", code: "KeyA", vk: 65, modifiers: 2 });
      const counts = await page.evaluate(`(() => {
        const host = document.querySelector("[data-activity-counts]");
        return { total: Number(host?.getAttribute("data-count-total") ?? -1), selected: Number(host?.getAttribute("data-count-selected") ?? -1) };
      })()`);
      assert(counts.total === state.total, `counter total ${counts.total} != read model ${state.total}`);
      assert(counts.selected === counts.total, `Ctrl+A from the page selected ${counts.selected}/${counts.total}`);
      return { menuFocus: menu.active, selected: counts.selected, fieldSelected: field.selection };
    });

    await scenario("07", "Full Screen performs a real transition and keeps layout and data unchanged", async () => {
      await setViewport(page, 1280, 720);
      const beforeFullscreen = await geometry(page);
      await page.evaluate(`document.querySelector('[data-fullscreen-toggle]')?.click()`);
      await sleep(900);
      const entered = await page.evaluate(`(() => {
        const button = document.querySelector('[data-fullscreen-toggle]');
        return {
          active: Boolean(document.fullscreenElement),
          pressed: button?.getAttribute("aria-pressed"),
          title: button?.getAttribute("title"),
          label: button?.querySelector(".cp-toolbar-label")?.textContent?.trim(),
        };
      })()`);
      assert(entered.active, "requestFullscreen did not enter full screen");
      assert(entered.pressed === "true", `aria-pressed is ${entered.pressed} in full screen`);
      assert(/Return/i.test(entered.label ?? "") && /Return/i.test(entered.title ?? ""), `full-screen label/title are ${entered.label}/${entered.title}`);
      await capture(page, "07-fullscreen");
      await press(page, { key: "Escape", code: "Escape", vk: 27 });
      await sleep(700);
      const exited = await page.evaluate(`(() => {
        const button = document.querySelector('[data-fullscreen-toggle]');
        return { active: Boolean(document.fullscreenElement), pressed: button?.getAttribute("aria-pressed"), label: button?.querySelector(".cp-toolbar-label")?.textContent?.trim() };
      })()`);
      if (exited.active) {
        await page.evaluate(`document.querySelector('[data-fullscreen-toggle]')?.click()`);
        await sleep(600);
      }
      const after = await page.evaluate(`(() => {
        const button = document.querySelector('[data-fullscreen-toggle]');
        return {
          active: Boolean(document.fullscreenElement),
          pressed: button?.getAttribute("aria-pressed"),
          rows: document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]").length,
          ganttRows: document.querySelectorAll("[data-gantt-activity-id]").length,
        };
      })()`);
      assert(!after.active, "full screen did not exit");
      assert(after.pressed === "false", `aria-pressed is ${after.pressed} after exit`);
      assert(after.rows === beforeFullscreen.tableRows && after.ganttRows === beforeFullscreen.ganttRows, "full screen changed the rendered rows");
      return { entered: entered.label, rows: after.rows };
    });

    await scenario("08", "The table/Gantt splitter drags, clamps, persists and resets", async () => {
      await setViewport(page, 1280, 720);
      await page.evaluate(`document.querySelector('[data-reset-table-split]')?.click()`);
      await sleep(350);
      const reset = await geometry(page);
      assert(reset.splitTable?.startsWith("50"), `reset split is ${reset.splitTable}`);
      const splitter = await page.evaluate(`(() => {
        const element = document.querySelector("[data-panel-splitter]");
        const box = element?.getBoundingClientRect();
        return element ? { x: box.left + box.width / 2, y: box.top + box.height / 2, value: element.getAttribute("aria-valuenow") } : null;
      })()`);
      assert(splitter, "table splitter is missing");
      await pointerDrag(page, "[data-panel-splitter]", { x: splitter.x - 160, y: splitter.y });
      const dragged = await page.evaluate(`(() => ({
        split: document.querySelector("[data-panel-split]")?.style.getPropertyValue("--cp-split-table"),
        value: document.querySelector("[data-panel-splitter]")?.getAttribute("aria-valuenow"),
        stored: Object.keys(localStorage).filter((key) => key.includes("workspace-split")).map((key) => [key, localStorage.getItem(key)]),
      }))()`);
      const draggedPercent = Number.parseFloat(dragged.split ?? "0");
      assert(draggedPercent < 50 && draggedPercent >= 25, `drag produced ${dragged.split}`);
      assert(Number(dragged.value) === Math.round(draggedPercent), `aria-valuenow ${dragged.value} != ${draggedPercent}`);

      await page.evaluate(`document.querySelector("[data-panel-splitter]")?.focus()`);
      await press(page, { key: "ArrowRight", code: "ArrowRight", vk: 39 });
      const keyed = await page.evaluate(`(() => ({
        split: document.querySelector("[data-panel-split]")?.style.getPropertyValue("--cp-split-table"),
        value: document.querySelector("[data-panel-splitter]")?.getAttribute("aria-valuenow"),
      }))()`);
      assert(Number.parseFloat(keyed.split) === draggedPercent + 2, `ArrowRight produced ${keyed.split}`);

      for (let index = 0; index < 30; index += 1) await press(page, { key: "ArrowLeft", code: "ArrowLeft", vk: 37 });
      const clamped = await page.evaluate(`document.querySelector("[data-panel-split]")?.style.getPropertyValue("--cp-split-table")`);
      assert(Number.parseFloat(clamped) === 25, `left clamp produced ${clamped}`);

      await page.reload();
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
      await sleep(1400);
      const restored = await geometry(page);
      assert(Number.parseFloat(restored.splitTable) === 25, `reload restored ${restored.splitTable}`);
      await capture(page, "08-splitter");
      await page.evaluate(`document.querySelector('[data-reset-table-split]')?.click()`);
      await sleep(300);
      const resetAgain = await geometry(page);
      assert(resetAgain.splitTable?.startsWith("50"), `post-test reset is ${resetAgain.splitTable}`);
      return { dragged: dragged.split, keyed: keyed.split, clamped, restored: restored.splitTable };
    });

    await scenario("09", "The details splitter responds to pointer and keys, and reset restores 70", async () => {
      await setViewport(page, 1366, 768);
      const initial = await page.evaluate(`(() => ({
        primary: document.querySelector(".cp-main")?.style.getPropertyValue("--cp-split-primary"),
        value: document.querySelector("[data-details-splitter]")?.getAttribute("aria-valuenow"),
      }))()`);
      assert(Number.parseFloat(initial.primary) === 70, `details split starts at ${initial.primary}`);
      await page.evaluate(`document.querySelector("[data-details-splitter]")?.focus()`);
      await press(page, { key: "ArrowDown", code: "ArrowDown", vk: 40 });
      const keyed = await page.evaluate(`(() => ({
        primary: document.querySelector(".cp-main")?.style.getPropertyValue("--cp-split-primary"),
        value: document.querySelector("[data-details-splitter]")?.getAttribute("aria-valuenow"),
      }))()`);
      assert(Number.parseFloat(keyed.primary) === 72, `ArrowDown produced ${keyed.primary}`);
      await press(page, { key: "End", code: "End", vk: 35 });
      const max = await page.evaluate(`document.querySelector("[data-details-splitter]")?.getAttribute("aria-valuenow")`);
      assert(Number(max) === 80, `End produced ${max}`);
      const rect = await page.evaluate(`(() => {
        const element = document.querySelector("[data-details-splitter]");
        const box = element.getBoundingClientRect();
        return { x: box.left + box.width / 2, y: box.top + box.height / 2 };
      })()`);
      await pointerDrag(page, "[data-details-splitter]", { x: rect.x, y: rect.y - 90 });
      const dragged = await page.evaluate(`document.querySelector("[data-details-splitter]")?.getAttribute("aria-valuenow")`);
      assert(Number(dragged) < 80 && Number(dragged) >= 40, `drag produced ${dragged}`);
      await page.reload();
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
      await sleep(1400);
      const restored = await page.evaluate(`document.querySelector("[data-details-splitter]")?.getAttribute("aria-valuenow")`);
      assert(restored === dragged, `reload restored ${restored}, expected ${dragged}`);
      await capture(page, "09-details-splitter");
      await page.evaluate(`document.querySelector('[data-reset-details-split]')?.click()`);
      await sleep(300);
      const reset = await page.evaluate(`document.querySelector("[data-details-splitter]")?.getAttribute("aria-valuenow")`);
      assert(Number(reset) === 70, `details reset produced ${reset}`);
      return { initial: initial.primary, keyed: keyed.primary, max, dragged, restored };
    });

    await scenario("10", "Persian RTL keeps the same geometry inside 1280x720", async () => {
      await setViewport(page, 1280, 720);
      await setLanguage(page, "fa");
      const metrics = await geometry(page);
      const direction = await page.evaluate(`document.documentElement.dir`);
      assert(direction === "rtl", `workspace direction is ${direction}`);
      assertNoOverflow(metrics, "fa 1280x720");
      assertPaneOrder(metrics, "fa 1280x720");
      await openMenu(page, "view");
      const menu = await menuState(page, "view");
      assert(menu && menu.left >= 0 && menu.right <= 1281, `RTL View menu leaves the viewport (${menu.left}..${menu.right})`);
      await press(page, { key: "Escape", code: "Escape", vk: 27 });
      const splitBefore = Number.parseFloat(metrics.splitTable);
      await page.evaluate(`document.querySelector("[data-panel-splitter]")?.focus()`);
      await press(page, { key: "ArrowRight", code: "ArrowRight", vk: 39 });
      const splitAfter = Number.parseFloat(await page.evaluate(`document.querySelector("[data-panel-split]")?.style.getPropertyValue("--cp-split-table")`));
      assert(splitAfter < splitBefore, `RTL ArrowRight widened the table: ${splitBefore} -> ${splitAfter}`);
      await capture(page, "10-rtl");
      await page.evaluate(`document.querySelector('[data-reset-table-split]')?.click()`);
      await sleep(250);
      await setLanguage(page, "en");
      return { direction, overflow: metrics.documentOverflowX, menu: [menu.left, menu.right], splitBefore, splitAfter };
    });

    await scenario("11", "The responsive and keyboard work never touches schedule input", async () => {
      const after = await readActivities(page);
      const afterFingerprint = fingerprint(after);
      assert(after.length === state.total, `read model changed ${state.total} -> ${after.length}`);
      assert(afterFingerprint === beforeFingerprint, "activity read model changed during the suite");
      assert(scheduleMutations.length === 0, `schedule writes were observed: ${JSON.stringify(scheduleMutations.slice(0, 3))}`);
      return { activities: after.length, writes: scheduleMutations.length };
    });

    assert(exceptions.length === 0, `browser exceptions: ${JSON.stringify(exceptions.slice(0, 3))}`);
    assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors.slice(0, 3))}`);
    assert(apiFailures.length === 0, `API 5xx: ${JSON.stringify(apiFailures.slice(0, 3))}`);
  } catch (error) {
    log(`\nFAILED: ${error && error.stack ? error.stack : error}`);
    report.finishedAt = new Date().toISOString();
    writeReport();
    throw error;
  } finally {
    report.finishedAt = new Date().toISOString();
    writeReport();
  }

  log(`\nScenarios: ${scenarios.filter((entry) => entry.status === "pass").length} passed, ${scenarios.filter((entry) => entry.status === "fail").length} failed`);
  log(`Evidence: ${join(evidenceDir, "workspace-responsive-v26.json")}`);
}

main().catch((error) => {
  process.stderr.write(`\n${error && error.stack ? error.stack : error}\n`);
  process.exit(1);
});
