#!/usr/bin/env node
/**
 * Version 26 WBS expand/collapse acceptance (ACT-006 and ACT-007).
 *
 * Proves in the real preview that every WBS band can be collapsed and expanded
 * from its +/− control, a double-click, the toolbar, the context menu and the
 * keyboard; that collapsing a parent hides exactly the descendant activities
 * and bands in the table and the Gantt while both panes keep row-for-row
 * identity and vertical alignment; that nested collapse state survives an
 * ancestor reopening; that the state travels with the saved layout and is
 * restored after the browser-local view state is cleared; and that collapsing
 * writes no schedule data.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4200 \
 *   CUBI_TESTED_CODE_SHA=<code commit> node e2e/activity-wbs-collapse-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4200";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-13";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "activity-wbs-collapse-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `activity-wbs-collapse-v26-${evidenceDate}`);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const projectId = "preview-rps-01";
const storageKey = "cubi:workspace-wbs-collapse";
const root = "WBS-RPS-ROOT";
const civil = "WBS-RPS-CIVIL";

const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const writeRequests = [];
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
  } catch (error) {
    record(id, name, "fail", { error: String(error && error.stack ? error.stack : error) });
    throw error;
  }
}

async function capture(page, name) {
  const file = `activity-wbs-collapse-v26/${name}.png`;
  await page.screenshot(file);
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
  await sleep(900);
}

async function readLayout(page, scope) {
  return page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${projectId}/p6/layouts/" + ${JSON.stringify(scope)} + "/activity");
    let body = null;
    try { body = await response.json(); } catch (error) { body = null; }
    return { status: response.status, body };
  })()`, { awaitPromise: true });
}

async function saveLayout(page) {
  const clicked = await page.evaluate(`(() => {
    const button = [...document.querySelectorAll('[data-desktop-command="layout.save"]')]
      .find((item) => item.getClientRects().length > 0 && !item.disabled);
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, "Save Layout command is missing");
  let latest = null;
  for (let attempt = 0; attempt < 40; attempt += 1) {
    await sleep(200);
    for (const scope of ["project", "user"]) {
      const saved = await readLayout(page, scope);
      if (saved.status !== 200 || !saved.body) continue;
      latest = saved;
      if (Array.isArray(saved.body.metadata?.wbsCollapse)) return saved;
    }
  }
  throw new Error(`layout save did not persist wbsCollapse metadata (status ${latest?.status ?? "none"})`);
}

/** Table bands/rows and Gantt rows in screen order, with view state. */
async function viewState(page) {
  return page.evaluate(`(() => {
    const round = (value) => Math.round(value * 2) / 2;
    const rows = [...document.querySelectorAll("#cp-activity-grid tbody tr")];
    const table = rows.map((row) => {
      const rect = row.getBoundingClientRect();
      if (row.dataset.wbsRow) {
        return {
          kind: "band",
          id: row.dataset.wbsRow,
          depth: Number(row.dataset.wbsDepth),
          collapsed: row.dataset.wbsCollapsed === "true",
          expanded: row.getAttribute("aria-expanded"),
          toggle: row.querySelector("[data-wbs-toggle]")?.textContent?.trim() ?? "",
          toggleTitle: row.querySelector("[data-wbs-toggle]")?.getAttribute("title") ?? "",
          top: round(rect.top),
          height: Math.round(rect.height),
        };
      }
      return {
        kind: "activity",
        id: row.dataset.activityId,
        top: round(rect.top),
        height: Math.round(rect.height),
      };
    });
    const gantt = [...document.querySelectorAll("#cp-gantt .cp-gantt-row")].map((row) => {
      const rect = row.getBoundingClientRect();
      return {
        kind: row.classList.contains("cp-gantt-group-row") ? "band" : "activity",
        id: row.dataset.ganttWbsId ?? row.dataset.ganttActivityId ?? "",
        top: round(rect.top),
        height: Math.round(rect.height),
      };
    });
    let store = {};
    try { store = JSON.parse(localStorage.getItem(${JSON.stringify(storageKey)}) || "{}"); } catch (error) { store = {}; }
    return {
      table,
      gantt,
      bands: table.filter((row) => row.kind === "band"),
      activities: table.filter((row) => row.kind === "activity"),
      ganttBands: gantt.filter((row) => row.kind === "band").length,
      ganttActivities: gantt.filter((row) => row.kind === "activity").length,
      storage: store[${JSON.stringify(projectId)}] ?? [],
      dir: document.documentElement.dir || "ltr",
      lang: document.documentElement.lang || "en",
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    };
  })()`);
}

/** Every table row keeps its own Gantt row in order and in the same position. */
function assertAligned(state, label) {
  assert(state.gantt.length === state.table.length, `${label}: Gantt has ${state.gantt.length} rows for ${state.table.length} table rows`);
  const origin = state.gantt.length ? state.gantt[0].top - state.table[0].top : 0;
  state.table.forEach((row, index) => {
    const gantt = state.gantt[index];
    assert(gantt && gantt.kind === row.kind, `${label}: Gantt row ${index} is ${gantt?.kind}, table row is ${row.kind}`);
    assert(gantt.id === row.id, `${label}: Gantt row ${index} is ${gantt.id}, table row is ${row.id}`);
    const drift = (gantt.top - row.top) - origin;
    assert(Math.abs(drift) <= 2, `${label}: ${row.id} drifts ${drift}px from its Gantt row`);
    assert(Math.abs(gantt.height - row.height) <= 2, `${label}: ${row.id} height ${row.height} vs Gantt ${gantt.height}`);
  });
}

function bandById(state, id) {
  const band = state.bands.find((row) => row.id === id);
  assert(band, `band ${id} is not rendered`);
  return band;
}

async function clickVisible(page, selector, label) {
  const clicked = await page.evaluate(`(() => {
    const element = [...document.querySelectorAll(${JSON.stringify(selector)})]
      .find((item) => item.getClientRects().length > 0 && !item.disabled);
    if (!element) return false;
    element.click();
    return true;
  })()`);
  assert(clicked, `${label} is missing`);
  await sleep(350);
}

async function toggleBand(page, wbsId) {
  await clickVisible(page, `#cp-activity-grid [data-wbs-toggle="${wbsId}"]`, `band toggle ${wbsId}`);
}

async function ensureCollapsed(page, wbsId) {
  const state = await viewState(page);
  if (bandById(state, wbsId).collapsed) return state;
  await toggleBand(page, wbsId);
  return viewState(page);
}

async function ensureExpanded(page, wbsId) {
  const state = await viewState(page);
  if (!bandById(state, wbsId).collapsed) return state;
  await toggleBand(page, wbsId);
  return viewState(page);
}

async function doubleClickBand(page, wbsId) {
  const fired = await page.evaluate(`(() => {
    const row = document.querySelector(${JSON.stringify(`#cp-activity-grid tr[data-wbs-row="${wbsId}"]`)});
    if (!row) return false;
    row.dispatchEvent(new MouseEvent("dblclick", { bubbles: true, cancelable: true }));
    return true;
  })()`);
  assert(fired, `band row ${wbsId} is not rendered`);
  await sleep(350);
}

async function centerOf(page, selector) {
  return page.evaluate(`(() => {
    const element = document.querySelector(${JSON.stringify(selector)});
    if (!element) return null;
    const rect = element.getBoundingClientRect();
    return { x: Math.round(rect.left + rect.width / 2), y: Math.round(rect.top + rect.height / 2) };
  })()`);
}

async function rightClickAt(page, point) {
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: point.x, y: point.y, button: "none", buttons: 0 });
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x: point.x, y: point.y, button: "right", buttons: 2, clickCount: 1 });
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: point.x, y: point.y, button: "right", buttons: 0, clickCount: 1 });
  await sleep(200);
}

async function clickAt(page, point) {
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: point.x, y: point.y, button: "none", buttons: 0 });
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x: point.x, y: point.y, button: "left", buttons: 1, clickCount: 1 });
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: point.x, y: point.y, button: "left", buttons: 0, clickCount: 1 });
  await sleep(300);
}

async function pressKey(page, key, code, keyCode) {
  const text = key === "Enter" ? "\r" : key === " " ? " " : undefined;
  await page.cdp.send("Input.dispatchKeyEvent", {
    type: "keyDown", key, code, windowsVirtualKeyCode: keyCode, nativeVirtualKeyCode: keyCode,
    ...(text ? { text, unmodifiedText: text } : {}),
  });
  await page.cdp.send("Input.dispatchKeyEvent", {
    type: "keyUp", key, code, windowsVirtualKeyCode: keyCode, nativeVirtualKeyCode: keyCode,
  });
  await sleep(350);
}

async function focusSelector(page, selector) {
  const focused = await page.evaluate(`(() => {
    const element = document.querySelector(${JSON.stringify(selector)});
    if (!element) return false;
    element.focus();
    return document.activeElement === element;
  })()`);
  assert(focused, `could not focus ${selector}`);
  await sleep(120);
}

function assertNoScheduleWrites(label) {
  const writes = writeRequests.splice(0);
  assert(writes.length === 0, `${label}: collapse issued ${writes.length} schedule write(s): ${writes.map((item) => `${item.method} ${item.url}`).join(", ")}`);
}

async function main() {
  const health = await waitForHttp(`${baseUrl}/preview/health`, 30000);
  if (!(health.status === "ok" || health.status === 200)) throw new Error(`preview health ${health.status}`);
  const chrome = await launchChrome();
  const page = new Page(chrome.cdp);
  await page.initialize();
  page.cdp.on("Runtime.exceptionThrown", (params) => {
    exceptions.push(params.exceptionDetails?.exception?.description ?? params.exceptionDetails?.text ?? "exception");
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
    const method = params.request?.method ?? "GET";
    const url = params.request?.url ?? "";
    if (method === "GET" || method === "HEAD" || !url.includes("/api/")) return;
    writeRequests.push({ method, url });
  });

  const report = {
    contract: "cubi-activity-wbs-collapse-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
  };

  function writeReport() {
    report.scenarios = scenarios;
    report.passed = scenarios.filter((entry) => entry.status === "pass").length;
    report.failed = scenarios.filter((entry) => entry.status === "fail").length;
    const json = JSON.stringify(report, null, 2);
    writeFileSync(join(outDir, "activity-wbs-collapse-v26.json"), json);
    writeFileSync(join(evidenceDir, "activity-wbs-collapse-v26.json"), json);
  }

  try {
    await setViewport(page, 1366, 768);
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
    const hasPersonas = await page.evaluate('Boolean(document.querySelector(".persona"))');
    if (!hasPersonas) {
      await page.evaluate('fetch("/preview/logout", { method: "POST", redirect: "manual" }).then((response) => response.status)', { awaitPromise: true });
      await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, ".persona", "persona cards after sign out");
    }
    const plannerClicked = await page.evaluate(`(() => {
      const button = [...document.querySelectorAll("form button")].find((item) => (item.textContent || "").trim().startsWith("Planner"));
      if (!button) return false;
      button.click();
      return true;
    })()`);
    assert(plannerClicked, "Planner login button is missing");
    await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
    await page.click('[data-project-id="preview-rps-01"]');
    await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
    await sleep(1500);

    await scenario("01", "one band toggle hides exactly its activities in both panes", async () => {
      writeRequests.length = 0;
      const baseline = await viewState(page);
      assert(baseline.bands.length === 7, `expected 7 WBS bands, got ${baseline.bands.length}`);
      assert(baseline.activities.length === 14, `expected 14 activities, got ${baseline.activities.length}`);
      assert(baseline.ganttBands === 7 && baseline.ganttActivities === 14, `Gantt has ${baseline.ganttBands} bands and ${baseline.ganttActivities} activities`);
      assertAligned(baseline, "expanded baseline");
      const before = bandById(baseline, civil);
      assert(before.collapsed === false && before.expanded === "true" && before.toggle === "−", `CIVIL starts ${JSON.stringify(before)}`);

      await toggleBand(page, civil);
      const collapsed = await viewState(page);
      const band = bandById(collapsed, civil);
      assert(band.collapsed === true && band.expanded === "false" && band.toggle === "+", `CIVIL did not collapse: ${JSON.stringify(band)}`);
      assert(band.toggleTitle.toLowerCase().includes("expand"), `toggle title after collapse is ${band.toggleTitle}`);
      assert(collapsed.activities.length === 9, `expected 9 visible activities after collapsing CIVIL, got ${collapsed.activities.length}`);
      assert(collapsed.ganttActivities === 9, `Gantt still shows ${collapsed.ganttActivities} activities`);
      assert(collapsed.bands.length === 7 && collapsed.ganttBands === 7, "the band structure must stay complete");
      assert(collapsed.storage.includes(civil), `local view state does not hold ${civil}: ${JSON.stringify(collapsed.storage)}`);
      assertAligned(collapsed, "collapsed branch");
      assertNoScheduleWrites("collapsing CIVIL");
      await capture(page, "01-one-band-collapsed-en-1366");
      return { bands: collapsed.bands.length, visibleActivities: collapsed.activities.length, storage: collapsed.storage };
    });

    await scenario("02", "the root band collapses the whole tree and reopens it", async () => {
      writeRequests.length = 0;
      await ensureExpanded(page, civil);
      await toggleBand(page, root);
      const collapsed = await viewState(page);
      assert(collapsed.bands.length === 1 && collapsed.bands[0].id === root, `root collapse left ${collapsed.bands.map((row) => row.id).join(",")}`);
      assert(collapsed.activities.length === 0, `root collapse left ${collapsed.activities.length} activity rows`);
      assert(collapsed.gantt.length === 1 && collapsed.gantt[0].id === root, `Gantt root collapse left ${collapsed.gantt.length} rows`);
      assertAligned(collapsed, "root collapsed");
      assertNoScheduleWrites("collapsing the root");

      await toggleBand(page, root);
      const expanded = await viewState(page);
      assert(expanded.bands.length === 7 && expanded.activities.length === 14, `root expand restored ${expanded.bands.length} bands and ${expanded.activities.length} activities`);
      assertAligned(expanded, "root expanded");
      assertNoScheduleWrites("expanding the root");
      await capture(page, "02-root-collapsed-en-1366");
      return { rootBands: collapsed.bands.length, restored: expanded.activities.length };
    });

    await scenario("03", "a nested child stays collapsed when its ancestor reopens", async () => {
      await toggleBand(page, civil);
      await doubleClickBand(page, root);
      const nested = await viewState(page);
      assert(nested.activities.length === 0 && nested.bands.length === 1, `double-click root left ${nested.bands.length} bands and ${nested.activities.length} activities`);
      await doubleClickBand(page, root);
      const reopened = await viewState(page);
      assert(reopened.bands.length === 7, `reopening the root restored ${reopened.bands.length} bands`);
      assert(reopened.activities.length === 9, `CIVIL forgot its collapsed state: ${reopened.activities.length} activities`);
      assert(bandById(reopened, civil).collapsed === true, "CIVIL is no longer marked collapsed");
      assertAligned(reopened, "nested collapse");
      await capture(page, "03-nested-collapse-after-ancestor-expand-en-1366");
      return { bands: reopened.bands.length, activities: reopened.activities.length };
    });

    await scenario("04", "the toolbar and the band context menu drive the same state", async () => {
      await clickVisible(page, "[data-wbs-collapse-all]", "Collapse All");
      const allCollapsed = await viewState(page);
      assert(allCollapsed.bands.length === 7, `Collapse All left ${allCollapsed.bands.length} bands`);
      assert(allCollapsed.activities.length === 0, `Collapse All left ${allCollapsed.activities.length} activities`);
      assert(allCollapsed.bands.filter((row) => row.depth === 1).every((row) => row.collapsed), "Collapse All did not collapse every child band");
      assertAligned(allCollapsed, "collapse all");

      await clickVisible(page, "[data-wbs-expand-all]", "Expand All");
      const allExpanded = await viewState(page);
      assert(allExpanded.bands.length === 7 && allExpanded.activities.length === 14, `Expand All restored ${allExpanded.activities.length} activities`);

      const point = await centerOf(page, `#cp-activity-grid tr[data-wbs-row="${root}"]`);
      assert(point, "root band row is missing");
      await rightClickAt(page, point);
      const menu = await page.evaluate(`(() => {
        const menus = [...document.querySelectorAll("[data-activity-context-menu]")];
        const menu = menus[menus.length - 1];
        if (!menu) return null;
        return {
          kind: menu.dataset.contextMenuKind,
          items: [...menu.querySelectorAll("[data-activity-menu-command]")].map((item) => {
            const rect = item.getBoundingClientRect();
            return {
              command: item.dataset.activityMenuCommand,
              disabled: Boolean(item.disabled),
              label: (item.textContent || "").trim(),
              x: Math.round(rect.left + rect.width / 2),
              y: Math.round(rect.top + rect.height / 2),
            };
          }),
        };
      })()`);
      assert(menu, "band context menu did not open");
      assert(menu.kind === "table-wbs", `context menu kind is ${menu.kind}`);
      const collapseEntry = menu.items.find((item) => item.command === "collapse-wbs");
      assert(collapseEntry && !collapseEntry.disabled, `band context menu lacks Collapse This Branch: ${JSON.stringify(menu)}`);
      await clickAt(page, { x: collapseEntry.x, y: collapseEntry.y });
      const viaMenu = await viewState(page);
      assert(viaMenu.bands.length === 1 && viaMenu.activities.length === 0, `context-menu collapse left ${viaMenu.bands.length} bands and ${viaMenu.activities.length} activities`);
      await capture(page, "04-context-menu-root-collapsed-en-1366");
      await clickVisible(page, "[data-wbs-expand-all]", "Expand All after context menu");
      const restored = await viewState(page);
      assert(restored.activities.length === 14, `Expand All after the menu restored ${restored.activities.length} activities`);
      return { bands: allExpanded.bands.length, menuLabel: collapseEntry.label, afterMenu: viaMenu.activities.length };
    });

    await scenario("05", "the saved layout restores collapsed branches after local state is cleared", async () => {
      await toggleBand(page, civil);
      const beforeSave = await viewState(page);
      assert(beforeSave.activities.length === 9, `CIVIL collapse before save shows ${beforeSave.activities.length} activities`);
      const saved = await saveLayout(page);
      const stored = saved.body.metadata.wbsCollapse;
      assert(Array.isArray(stored) && stored.includes(civil), `saved layout collapse is ${JSON.stringify(stored)}`);
      assert(saved.body.metadata.groupSort?.groupBy === "wbs", `the save also lost the group mode: ${JSON.stringify(saved.body.metadata.groupSort)}`);

      await page.evaluate(`localStorage.setItem(${JSON.stringify(storageKey)}, "{}")`);
      await page.reload(`#cp-activity-grid tr[data-wbs-row="${civil}"]`, "reload with empty local collapse state");
      await sleep(1400);
      const restored = await viewState(page);
      assert(bandById(restored, civil).collapsed === true, "the layout did not restore the collapsed branch");
      assert(restored.activities.length === 9, `reload restored ${restored.activities.length} activities, expected 9`);
      assert(restored.storage.includes(civil), `reload did not repopulate the local view state: ${JSON.stringify(restored.storage)}`);
      assertAligned(restored, "layout-restored collapse");
      await capture(page, "05-layout-restored-collapse-en-1366");
      return { revision: saved.body.revision, stored, activities: restored.activities.length };
    });

    await scenario("06", "a layout saved with every branch open restores the full tree", async () => {
      await clickVisible(page, "[data-wbs-expand-all]", "Expand All before the second save");
      const saved = await saveLayout(page);
      assert(Array.isArray(saved.body.metadata.wbsCollapse) && saved.body.metadata.wbsCollapse.length === 0, `saved layout collapse is ${JSON.stringify(saved.body.metadata.wbsCollapse)}`);
      await page.evaluate(`localStorage.setItem(${JSON.stringify(storageKey)}, "{}")`);
      await page.reload(`#cp-activity-grid tbody tr[data-activity-id]`, "reload with an expanded layout");
      await sleep(1400);
      const restored = await viewState(page);
      assert(restored.bands.length === 7 && restored.activities.length === 14, `expanded layout restored ${restored.bands.length} bands and ${restored.activities.length} activities`);
      assertAligned(restored, "layout restored expanded");
      await capture(page, "06-layout-restored-expanded-en-1366");
      return { revision: saved.body.revision, activities: restored.activities.length };
    });

    await scenario("07", "the keyboard toggles a focused band exactly once", async () => {
      writeRequests.length = 0;
      await focusSelector(page, `#cp-activity-grid tr[data-wbs-row="${civil}"]`);
      await pressKey(page, "Enter", "Enter", 13);
      let state = await viewState(page);
      assert(bandById(state, civil).collapsed === true, "Enter on the focused band row did not collapse it");
      assert(state.activities.length === 9, `Enter collapsed ${state.activities.length} activities`);
      assertNoScheduleWrites("keyboard collapse");

      await focusSelector(page, `#cp-activity-grid tr[data-wbs-row="${civil}"]`);
      await pressKey(page, " ", "Space", 32);
      state = await viewState(page);
      assert(bandById(state, civil).collapsed === false, "Space on the focused band row did not expand it");
      assert(state.activities.length === 14, `Space expanded ${state.activities.length} activities`);

      await focusSelector(page, `#cp-activity-grid [data-wbs-toggle="${civil}"]`);
      await pressKey(page, "Enter", "Enter", 13);
      state = await viewState(page);
      assert(bandById(state, civil).collapsed === true, "Enter on the toggle button did not collapse the band");
      assertNoScheduleWrites("toggle-button keyboard collapse");
      await capture(page, "07-keyboard-collapse-en-1366");
      return { toggle: bandById(state, civil).toggle, activities: state.activities.length };
    });

    await scenario("08", "Persian RTL at 1280 keeps the collapsed tree and its controls aligned", async () => {
      await ensureCollapsed(page, civil);
      await setLanguage(page, "fa");
      await setViewport(page, 1280, 720);
      await sleep(500);
      const state = await viewState(page);
      assert(state.dir === "rtl", `document direction is ${state.dir}`);
      assert(state.bands.length === 7 && state.activities.length === 9, `fa state shows ${state.bands.length} bands and ${state.activities.length} activities`);
      const band = bandById(state, civil);
      assert(band.collapsed === true, "the collapsed branch was lost on the locale switch");
      assert(band.toggleTitle.includes("بازکردن"), `fa toggle title is ${band.toggleTitle}`);
      assert(state.overflow <= 0, `fa layout overflows by ${state.overflow}px`);
      assertAligned(state, "fa collapsed");
      await capture(page, "08-collapsed-fa-rtl-1280");
      return { dir: state.dir, overflow: state.overflow, activities: state.activities.length };
    });

    await scenario("09", "the collapsed tree stays in step at 1920x1080", async () => {
      await setLanguage(page, "en");
      await setViewport(page, 1920, 1080);
      await sleep(500);
      const state = await viewState(page);
      assert(state.bands.length === 7 && state.activities.length === 9, `1920 state shows ${state.bands.length} bands and ${state.activities.length} activities`);
      assertAligned(state, "1920 collapsed");
      assert(state.overflow <= 0, `1920 layout overflows by ${state.overflow}px`);
      await capture(page, "09-collapsed-en-1920");
      return { overflow: state.overflow, activities: state.activities.length };
    });

    log(`\nAll ${scenarios.length} WBS collapse scenarios passed`);
  } finally {
    writeReport();
    await chrome.stop();
  }
}

main().catch((error) => {
  process.stderr.write(`${error && error.stack ? error.stack : error}\n`);
  process.exit(1);
});
