#!/usr/bin/env node
/**
 * Browser E2E for WS-004 — window tabs, close, reorder, dirty state and
 * lifecycle (Version 26 "Using Main Windows").
 *
 * Drives the real local full-stack preview through headless Chrome. No API
 * response is mocked and no page fixture is injected: every tab is opened
 * through the real toolbar/menu bar and the workspace state is read from the
 * rendered shell.
 *
 * Scenarios: duplicate-open suppression, tab switching, closing a non-active
 * and the active tab, the last-window guard, keyboard and pointer reordering
 * with persistence across reload, the active-tab dirty marker, the
 * discard-confirmation path, restored tab set/order/active window after a full
 * reload, and a Persian 1280×720 layout check.
 *
 * Usage:
 *   node e2e/workspace-window-tabs-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import {
  Page,
  artifactsDir,
  gitHead,
  launchChrome,
  startManagedRuntime,
} from "./preview-e2e.mjs";

const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-13";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const outDir = join(artifactsDir, "workspace-window-tabs-v26");
const evidenceDir = join(
  artifactsDir,
  "..",
  "..",
  "..",
  "..",
  "docs",
  "workspace",
  "evidence",
  `workspace-window-tabs-v26-${evidenceDate}`,
);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const scenarios = [];
const screenshots = [];
const writes = [];
let baseUrl = "";

function log(message) {
  process.stdout.write(`${message}\n`);
}

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

function record(id, name, status, details = {}) {
  scenarios.push({ ...details, id, name, status, at: new Date().toISOString() });
  log(`  ${status.toUpperCase()} ${id}. ${name}`);
}

async function scenario(id, name, body) {
  log(`\n[${id}] ${name}`);
  try {
    const details = (await body()) ?? {};
    record(id, name, "pass", details);
    return details;
  } catch (error) {
    record(id, name, "fail", {
      error: String(error && error.stack ? error.stack : error),
    });
    throw error;
  }
}

const tabState = `(() => {
  const workspace = document.querySelector(".cp-workspace");
  const tabs = [...document.querySelectorAll("[data-window-tab]")];
  return {
    activeMenu: workspace?.dataset.activeMenu ?? null,
    direction: workspace?.getAttribute("dir") ?? document.documentElement.getAttribute("dir"),
    order: tabs.map((tab) => tab.dataset.windowTab),
    tabs: tabs.map((tab) => ({
      key: tab.dataset.windowTab,
      selected: tab.getAttribute("aria-selected") === "true",
      dirty: tab.dataset.windowDirty === "true",
      closable: Boolean(tab.querySelector("[data-window-close]")),
      label: (tab.querySelector("[data-window-open]")?.textContent ?? "").trim(),
    })),
    closeButtons: document.querySelectorAll("[data-window-close]").length,
    tablist: (() => {
      const tablist = document.querySelector(".cp-window-tabs");
      if (!tablist) return null;
      return {
        scrollWidth: tablist.scrollWidth,
        clientWidth: tablist.clientWidth,
        overflow: tablist.scrollWidth - tablist.clientWidth,
      };
    })(),
    settingsPanel: Boolean(document.querySelector("[data-project-settings-panel]")),
    confirmCalls: window.__confirmCalls ?? 0,
  };
})()`;

async function capture(page, name) {
  const file = `workspace-window-tabs-v26/${name}.png`;
  await page.screenshot(file);
  copyFileSync(join(artifactsDir, file), join(evidenceDir, `${name}.png`));
  screenshots.push(`${name}.png`);
  return file;
}

async function loginAs(page, label) {
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
  await page.waitForSelector(".persona", "persona cards");
  const clicked = await page.evaluate(`(() => {
    const button = [...document.querySelectorAll("form button")].find((item) => (item.textContent || "").trim().startsWith(${JSON.stringify(label)}));
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `${label} login button is missing`);
  await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
  await page.click('[data-project-id="preview-rps-01"]');
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
  await sleep(1200);
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
  assert(changed, `language selector does not accept ${locale}`);
  await sleep(700);
}

async function openWindowFromToolbar(page, selector, key) {
  await page.click(selector);
  await page.waitFor(
    `document.querySelector(".cp-workspace")?.dataset.activeMenu === ${JSON.stringify(key)}`,
    `${key} window active`,
  );
  await sleep(350);
}

async function main() {
  const runtime = await startManagedRuntime();
  baseUrl = runtime.baseUrl;
  const chrome = await launchChrome();
  const page = new Page(chrome.cdp);
  await page.initialize();
  page.cdp.on("Runtime.exceptionThrown", (params) => {
    exceptions.push(
      params.exceptionDetails?.exception?.description ??
        params.exceptionDetails?.text ??
        "unknown exception",
    );
  });
  page.cdp.on("Runtime.consoleAPICalled", (params) => {
    if (params.type !== "error") return;
    consoleErrors.push(
      (params.args ?? [])
        .map((arg) => arg.value ?? arg.description ?? arg.type)
        .join(" "),
    );
  });
  page.cdp.on("Network.responseReceived", (params) => {
    const url = params.response?.url ?? "";
    if (url.includes("/api/") && params.response.status >= 500) {
      apiFailures.push({ status: params.response.status, url });
    }
  });
  // Window management is presentation only: record every non-read request so
  // the last scenario can prove no schedule or project write was issued.
  page.cdp.on("Network.requestWillBeSent", (params) => {
    const url = params.request?.url ?? "";
    const method = params.request?.method ?? "GET";
    if (!url.includes("/api/")) return;
    if (method === "GET" || method === "HEAD" || method === "OPTIONS") return;
    writes.push({ method, url });
  });

  const report = {
    contract: "cubi-window-tabs-v26.v1",
    baseUrl,
    project: PROJECT,
    gitHead: gitHead(),
    testedCodeSha,
    capturedAt: new Date().toISOString(),
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
  };

  try {
    await page.cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1440,
      height: 900,
      deviceScaleFactor: 1,
      mobile: false,
    });
    await sleep(400);
    await loginAs(page, "Project administrator");
    await setLanguage(page, "en");

    await scenario("01", "the default tab set has one active tab and no duplicates", async () => {
      const state = await page.evaluate(tabState);
      assert(state.order.length >= 2, `default tabs ${JSON.stringify(state.order)}`);
      assert(
        new Set(state.order).size === state.order.length,
        `duplicate tabs ${JSON.stringify(state.order)}`,
      );
      assert(
        state.tabs.filter((tab) => tab.selected).length === 1,
        `selected tabs ${JSON.stringify(state.tabs)}`,
      );
      assert(state.tabs.every((tab) => tab.closable), "every tab in a multi-window set is closable");
      await capture(page, "01-default-tabs");
      return { order: state.order, activeMenu: state.activeMenu };
    });

    await scenario("02", "re-opening the active window does not duplicate its tab", async () => {
      const before = await page.evaluate(tabState);
      await openWindowFromToolbar(page, '[data-toolbar-command="toolbar.activities-window"]', "schedule");
      await openWindowFromToolbar(page, '[data-toolbar-command="toolbar.new"]', "project");
      await page.click('[data-toolbar-command="toolbar.new"]');
      await sleep(300);
      const after = await page.evaluate(tabState);
      assert(
        after.order.length === before.order.length,
        `tab count changed ${before.order.length} -> ${after.order.length}: ${JSON.stringify(after.order)}`,
      );
      assert(
        new Set(after.order).size === after.order.length,
        `duplicate tabs after re-open ${JSON.stringify(after.order)}`,
      );
      assert(after.activeMenu === "project", `active window ${after.activeMenu}`);
      await capture(page, "02-no-duplicate");
      return { order: after.order };
    });

    await scenario("03", "clicking a tab switches the active window without reordering", async () => {
      const before = await page.evaluate(tabState);
      await page.click(`[data-window-open="${before.order[0]}"]`);
      await sleep(400);
      const after = await page.evaluate(tabState);
      assert(after.activeMenu === before.order[0], `active window ${after.activeMenu}`);
      assert(
        after.tabs.filter((tab) => tab.selected).length === 1 &&
          after.tabs.find((tab) => tab.selected)?.key === before.order[0],
        `selection ${JSON.stringify(after.tabs)}`,
      );
      assert(
        JSON.stringify(after.order) === JSON.stringify(before.order),
        `order changed on switch ${JSON.stringify(after.order)}`,
      );
      await capture(page, "03-switch");
      return { activeMenu: after.activeMenu, order: after.order };
    });

    await scenario("04", "opening a third window appends a tab and closing a non-active tab keeps the active one", async () => {
      await page.click('[data-desktop-menu="tools"]');
      await sleep(300);
      await page.click('[data-desktop-item="tools.reports"]');
      await page.waitForSelector("[data-reports-page]", "reports window");
      await sleep(900);
      const opened = await page.evaluate(tabState);
      assert(opened.order.length === 3, `tabs after reports ${JSON.stringify(opened.order)}`);
      assert(opened.activeMenu === "reports", `active window ${opened.activeMenu}`);

      const victim = opened.order.find((key) => key !== "reports");
      await page.click(`[data-window-close="${victim}"]`);
      await sleep(500);
      const closed = await page.evaluate(tabState);
      assert(!closed.order.includes(victim), `${victim} still open ${JSON.stringify(closed.order)}`);
      assert(closed.activeMenu === "reports", `active window after close ${closed.activeMenu}`);
      await capture(page, "04-close-inactive");
      return { opened: opened.order, closed: closed.order };
    });

    await scenario("05", "keyboard reorder moves a tab and survives a full reload", async () => {
      const before = await page.evaluate(tabState);
      const first = before.order[0];
      const moved = await page.evaluate(`(() => {
        const tab = document.querySelector('[data-window-tab="${first}"]');
        if (!tab) return false;
        tab.focus();
        tab.dispatchEvent(new KeyboardEvent("keydown", {
          key: "ArrowRight", ctrlKey: true, shiftKey: true, bubbles: true, cancelable: true,
        }));
        return true;
      })()`);
      assert(moved, "tab focus failed");
      await sleep(600);
      const after = await page.evaluate(tabState);
      assert(
        after.order[1] === first,
        `keyboard reorder ${JSON.stringify(before.order)} -> ${JSON.stringify(after.order)}`,
      );
      await page.reload("[data-window-tab]");
      await sleep(1500);
      const reloaded = await page.evaluate(tabState);
      assert(
        JSON.stringify(reloaded.order) === JSON.stringify(after.order),
        `order not persisted ${JSON.stringify(after.order)} -> ${JSON.stringify(reloaded.order)}`,
      );
      await capture(page, "05-keyboard-reorder");
      return { before: before.order, after: after.order, reloaded: reloaded.order };
    });

    await scenario("06", "pointer drag reorder moves the first tab onto the second", async () => {
      const before = await page.evaluate(tabState);
      const [from, to] = before.order;
      const dragged = await page.evaluate(`(() => {
        const source = document.querySelector('[data-window-tab="${from}"]');
        const target = document.querySelector('[data-window-tab="${to}"]');
        if (!source || !target) return false;
        const transfer = new DataTransfer();
        source.dispatchEvent(new DragEvent("dragstart", { bubbles: true, dataTransfer: transfer }));
        target.dispatchEvent(new DragEvent("dragover", { bubbles: true, cancelable: true, dataTransfer: transfer }));
        target.dispatchEvent(new DragEvent("drop", { bubbles: true, cancelable: true, dataTransfer: transfer }));
        source.dispatchEvent(new DragEvent("dragend", { bubbles: true, dataTransfer: transfer }));
        return true;
      })()`);
      assert(dragged, "drag dispatch failed");
      await sleep(600);
      const after = await page.evaluate(tabState);
      assert(
        after.order[0] === to && after.order[1] === from,
        `drag reorder ${JSON.stringify(before.order)} -> ${JSON.stringify(after.order)}`,
      );
      await capture(page, "06-pointer-reorder");
      return { before: before.order, after: after.order };
    });

    await scenario("07", "unsaved edits mark only the active tab and closing it asks before discarding", async () => {
      const active = (await page.evaluate(tabState)).activeMenu;
      await page.click('[data-toolbar-command="toolbar.properties"]');
      await page.waitForSelector("[data-project-settings-panel]", "project settings panel");
      await sleep(400);
      const dirty = await page.evaluate(tabState);
      assert(dirty.settingsPanel, "settings panel did not open");
      assert(
        dirty.tabs.filter((tab) => tab.dirty).length === 1 &&
          dirty.tabs.find((tab) => tab.selected)?.dirty === true,
        `dirty markers ${JSON.stringify(dirty.tabs)}`,
      );

      await page.evaluate(`(() => {
        window.__confirmCalls = 0;
        window.__nativeConfirm = window.confirm;
        window.confirm = (message) => {
          window.__confirmCalls = (window.__confirmCalls ?? 0) + 1;
          window.__confirmPrompt = message;
          return false;
        };
        return true;
      })()`);
      await page.click(`[data-window-close="${active}"]`);
      await sleep(400);
      const kept = await page.evaluate(tabState);
      assert(kept.order.includes(active), `tab closed despite cancel ${JSON.stringify(kept.order)}`);
      assert(kept.confirmCalls === 1, `confirm calls ${kept.confirmCalls}`);
      await capture(page, "07-dirty-confirm-cancel");

      await page.evaluate("window.confirm = () => true");
      await page.click(`[data-window-close="${active}"]`);
      await sleep(500);
      const discarded = await page.evaluate(tabState);
      assert(!discarded.order.includes(active), `dirty tab not closed ${JSON.stringify(discarded.order)}`);
      assert(!discarded.settingsPanel, "discarded window kept its settings panel");
      assert(
        discarded.tabs.every((tab) => !tab.dirty),
        `dirty marker survived ${JSON.stringify(discarded.tabs)}`,
      );
      await capture(page, "07-dirty-confirm-accept");
      return { active, kept: kept.order, discarded: discarded.order };
    });

    await scenario("08", "the last open window has no close control", async () => {
      for (;;) {
        const state = await page.evaluate(tabState);
        if (state.order.length === 1) break;
        await page.click(`[data-window-close="${state.order.find((key) => key !== state.activeMenu) ?? state.order[0]}"]`);
        await sleep(400);
      }
      const single = await page.evaluate(tabState);
      assert(single.order.length === 1, `tabs ${JSON.stringify(single.order)}`);
      assert(single.closeButtons === 0, `close controls ${single.closeButtons}`);
      assert(single.tabs[0].closable === false, "the last tab advertises a close control");
      await capture(page, "08-last-window");
      return { order: single.order };
    });

    await scenario("09", "tab set, order and active window are restored after a full reload", async () => {
      await openWindowFromToolbar(page, '[data-toolbar-command="toolbar.activities-window"]', "schedule");
      await page.click('[data-desktop-menu="organization"]');
      await sleep(250);
      await page.click('[data-desktop-item="enterprise.resources"]');
      await page.waitFor(
        'document.querySelector(".cp-workspace")?.dataset.activeMenu === "resources"',
        "resources window active",
      );
      await sleep(700);
      await page.click('[data-desktop-menu="organization"]');
      await sleep(250);
      await page.click('[data-desktop-item="enterprise.calendars"]');
      await page.waitFor(
        'document.querySelector(".cp-workspace")?.dataset.activeMenu === "calendars"',
        "calendars window active",
      );
      await sleep(700);
      const before = await page.evaluate(tabState);
      assert(before.order.length >= 3, `tabs before reload ${JSON.stringify(before.order)}`);
      await page.reload("[data-window-tab]");
      await sleep(1800);
      const after = await page.evaluate(tabState);
      assert(
        JSON.stringify(after.order) === JSON.stringify(before.order),
        `order not restored ${JSON.stringify(before.order)} -> ${JSON.stringify(after.order)}`,
      );
      assert(
        after.activeMenu === before.activeMenu,
        `active window not restored ${before.activeMenu} -> ${after.activeMenu}`,
      );
      await capture(page, "09-reload-restored");
      return { before: before.order, after: after.order, active: after.activeMenu };
    });

    await scenario("10", "Persian right-to-left tabs fit 1280x720 without overflow", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", {
        width: 1280,
        height: 720,
        deviceScaleFactor: 1,
        mobile: false,
      });
      await setLanguage(page, "fa");
      await sleep(800);
      const state = await page.evaluate(tabState);
      assert(state.order.length >= 3, `tabs ${JSON.stringify(state.order)}`);
      assert(state.direction === "rtl", `direction ${state.direction}`);
      assert(state.tablist, "tab list missing");
      assert(
        state.tablist.overflow <= 1,
        `tab strip overflows by ${state.tablist.overflow}px at 1280x720`,
      );
      assert(
        state.tabs.every((tab) => tab.label.length > 0),
        "a Persian tab label is empty",
      );
      await capture(page, "10-persian-rtl-1280");
      return { order: state.order, labels: state.tabs.map((tab) => tab.label) };
    });

    await scenario("11", "no schedule write is issued while tabs are managed", async () => {
      // Activating a window re-opens the project session (``POST …/open``);
      // that is the workspace handshake, not a schedule mutation. Any other
      // write would mean a tab action changed persisted planning data.
      const sessionOpens = writes.filter((item) => /\/api\/projects\/[^/]+\/open$/.test(item.url));
      const mutations = writes.filter((item) => !sessionOpens.includes(item));
      assert(
        mutations.length === 0,
        `unexpected write requests ${JSON.stringify(mutations.map((item) => `${item.method} ${item.url}`))}`,
      );
      return { writes: writes.length, sessionOpens: sessionOpens.length };
    });

    return report;
  } finally {
    report.finishedAt = new Date().toISOString();
    report.status = scenarios.some((item) => item.status === "fail") ? "failed" : "passed";
    report.writes = writes;
    const reportFile = join(evidenceDir, "workspace-window-tabs-v26.json");
    writeFileSync(reportFile, JSON.stringify(report, null, 2));
    log(`\nEvidence: ${reportFile}`);
    log(`Screenshots: ${screenshots.length}`);
    log(
      `Exceptions: ${exceptions.length}, console errors: ${consoleErrors.length}, 5xx: ${apiFailures.length}`,
    );
    page.cdp.close();
    await chrome.stop();
    await runtime.stop();
  }
}

main()
  .then((report) => {
    if (report && report.status !== "passed") process.exitCode = 1;
  })
  .catch((error) => {
    process.stderr.write(`\nE2E FAILED: ${error?.stack ?? error}\n`);
    process.exitCode = 1;
  });
