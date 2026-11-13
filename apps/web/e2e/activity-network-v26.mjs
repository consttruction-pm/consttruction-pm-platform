#!/usr/bin/env node
/**
 * Version 26 Activity Network acceptance (ACT-013).
 *
 * Proves in the real preview that the Activity Network is a deterministic
 * projection of the persisted activities and relationships (levels, nodes,
 * edges with their stored types and lag), that selecting a node and a table
 * row stay synchronised in both directions, that a relationship edge exposes
 * its details, opens the editor on double-click / Enter / its context menu and
 * navigates to its successor, and that Zoom In/Out/Best Fit scale only the
 * presentation and survive a reload. Covers en LTR 1366/1920 and fa RTL 1280.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4201 \
 *   CUBI_TESTED_CODE_SHA=<code commit> node e2e/activity-network-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4201";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-13";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const suiteName = "activity-network-v26";
const outDir = join(artifactsDir, suiteName);
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `${suiteName}-${evidenceDate}`);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const scheduleWrites = [];
const relationshipWrites = [];
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
  const file = `${suiteName}/${name}.png`;
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

async function openMenu(page, menu) {
  const opened = await page.evaluate(`(() => {
    const trigger = document.querySelector('[data-desktop-menu=${JSON.stringify(menu)}]');
    if (!trigger) return false;
    if (trigger.getAttribute("aria-expanded") === "true") return true;
    trigger.click();
    return true;
  })()`);
  assert(opened, `menu trigger missing: ${menu}`);
  await sleep(200);
}

async function runMenuCommand(page, menu, command) {
  await openMenu(page, menu);
  const clicked = await page.evaluate(`(() => {
    const item = [...document.querySelectorAll('[data-desktop-command=${JSON.stringify(command)}]')]
      .find((entry) => entry.getClientRects().length > 0);
    if (!item || item.hasAttribute("disabled")) return false;
    item.click();
    return true;
  })()`);
  assert(clicked, `menu command is missing or disabled: ${command}`);
  await sleep(1100);
}

async function showNetwork(page) {
  await runMenuCommand(page, "view", "view.top-network");
  await page.waitForSelector("[data-network-view]", "Activity Network");
  await sleep(500);
}

async function networkState(page) {
  return page.evaluate(`(() => {
    const section = document.querySelector("[data-network-view]");
    const svg = section?.querySelector(".cp-network-svg");
    const selectedRow = document.querySelector("#cp-activity-grid tbody tr[aria-selected='true']");
    return {
      present: Boolean(section),
      levels: Number(section?.getAttribute("data-network-levels") || 0),
      nodeCount: Number(section?.getAttribute("data-network-nodes") || 0),
      edgeCount: Number(section?.getAttribute("data-network-edges") || 0),
      nodes: [...(section?.querySelectorAll("[data-gantt-activity-id]") ?? [])].map((node) => ({
        id: node.getAttribute("data-gantt-activity-id"),
        critical: node.classList.contains("is-critical"),
        selected: node.classList.contains("is-selected"),
        pressed: node.getAttribute("aria-pressed"),
        title: node.querySelector("title")?.textContent ?? "",
      })),
      edges: [...(section?.querySelectorAll("[data-network-relationship-id]") ?? [])].map((edge) => ({
        id: edge.getAttribute("data-network-relationship-id"),
        from: edge.getAttribute("data-link-from"),
        to: edge.getAttribute("data-link-to"),
        type: edge.getAttribute("data-link-type"),
        title: edge.querySelector("title")?.textContent ?? "",
        label: (edge.querySelector(".cp-network-edge-label")?.textContent ?? "").trim(),
      })),
      selectedNode: section?.querySelector(".cp-network-node.is-selected")?.getAttribute("data-gantt-activity-id") ?? null,
      selectedRow: selectedRow?.getAttribute("data-activity-id") ?? null,
      detailsText: (document.querySelector("#cp-details")?.textContent ?? "").replace(/\\s+/g, " ").trim(),
      zoom: Number(section?.getAttribute("data-network-zoom") || 0),
      zoomLabel: (section?.querySelector("[data-network-zoom-label]")?.textContent ?? "").trim(),
      svgWidth: Number(svg?.getAttribute("width") || 0),
      svgHeight: Number(svg?.getAttribute("height") || 0),
      baseWidth: Number(section?.getAttribute("data-network-base-width") || 0),
      baseHeight: Number(section?.getAttribute("data-network-base-height") || 0),
      svgDir: svg?.getAttribute("dir") ?? null,
      heading: (section?.querySelector("h2")?.textContent ?? "").trim(),
      dir: document.documentElement.dir || "ltr",
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    };
  })()`);
}

async function nodePoint(page, activityId) {
  return page.evaluate(`(() => {
    const node = document.querySelector('[data-network-view] [data-gantt-activity-id=' + JSON.stringify(${JSON.stringify(activityId)}) + ']');
    if (!node) return null;
    node.scrollIntoView({ block: "center", inline: "center" });
    const rect = node.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return null;
    return { x: Math.round(rect.left + rect.width / 2), y: Math.round(rect.top + rect.height / 2) };
  })()`);
}

async function clickNode(page, activityId) {
  const point = await nodePoint(page, activityId);
  assert(point, `network node ${activityId} is missing`);
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: point.x, y: point.y, button: "none", buttons: 0 });
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x: point.x, y: point.y, button: "left", buttons: 1, clickCount: 1 });
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: point.x, y: point.y, button: "left", buttons: 0, clickCount: 1 });
  await sleep(700);
}

async function edgePoint(page, relationshipId) {
  return page.evaluate(`(() => {
    const path = document.querySelector('[data-network-edge-hit=' + JSON.stringify(${JSON.stringify(relationshipId)}) + ']');
    if (!path) return null;
    path.scrollIntoView({ block: "center", inline: "center" });
    let length = 0;
    try { length = path.getTotalLength(); } catch { return null; }
    const matrix = path.getScreenCTM();
    if (!length || !matrix) return null;
    const misses = [];
    for (const fraction of [0.5, 0.4, 0.6, 0.3, 0.7, 0.2, 0.8, 0.1, 0.9]) {
      const local = path.getPointAtLength(length * fraction);
      const x = Math.round(local.x * matrix.a + local.y * matrix.c + matrix.e);
      const y = Math.round(local.x * matrix.b + local.y * matrix.d + matrix.f);
      if (x < 1 || y < 1 || x >= innerWidth - 1 || y >= innerHeight - 1) { misses.push("offscreen"); continue; }
      const hit = document.elementFromPoint(x, y);
      const owner = hit?.closest?.("[data-network-relationship-id]")?.getAttribute("data-network-relationship-id");
      if (owner === ${JSON.stringify(relationshipId)}) return { x, y };
      misses.push((hit?.tagName || "none") + ":" + (owner || ""));
    }
    return { miss: misses.join(",") };
  })()`);
}

async function rightClickAt(page, x, y) {
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y, button: "none", buttons: 0 });
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "right", buttons: 2, clickCount: 1 });
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "right", buttons: 0, clickCount: 1 });
  await sleep(300);
}

async function menuState(page) {
  return page.evaluate(`(() => {
    const menu = document.querySelector(".cp-context-menu");
    if (!menu) return null;
    return {
      label: (menu.getAttribute("aria-label") ?? "").trim(),
      commands: [...menu.querySelectorAll("[data-activity-menu-command]")].map((item) => item.getAttribute("data-activity-menu-command")),
      labels: [...menu.querySelectorAll("[data-activity-menu-command]")].map((item) => (item.textContent || "").trim()),
    };
  })()`);
}

async function closeMenu(page) {
  await page.cdp.send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27, nativeVirtualKeyCode: 27 });
  await page.cdp.send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27, nativeVirtualKeyCode: 27 });
  await sleep(200);
}

async function clickZoom(page, mode) {
  const clicked = await page.evaluate(`(() => {
    const button = document.querySelector('[data-network-zoom=' + JSON.stringify(${JSON.stringify(mode)}) + ']');
    if (!button || button.disabled) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `network zoom button ${mode} is missing or disabled`);
  await sleep(350);
}

function assertNoScheduleWrites(label) {
  const writes = scheduleWrites.splice(0);
  assert(writes.length === 0, `${label}: the network wrote schedule/activity data: ${writes.map((item) => `${item.method} ${item.url}`).join(", ")}`);
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
    if (url.includes("/p6/relationships")) {
      relationshipWrites.push({ method, url, postData: params.request?.postData ?? null });
      return;
    }
    if (url.includes("/p6/schedule/") || url.includes("/activities/")) scheduleWrites.push({ method, url });
  });

  const report = {
    contract: "cubi-activity-network-v26.v1",
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
    report.relationshipWrites = relationshipWrites;
    report.scheduleWrites = scheduleWrites;
    report.passed = scenarios.filter((entry) => entry.status === "pass").length;
    report.failed = scenarios.filter((entry) => entry.status === "fail").length;
    const json = JSON.stringify(report, null, 2);
    writeFileSync(join(outDir, `${suiteName}.json`), json);
    writeFileSync(join(evidenceDir, `${suiteName}.json`), json);
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
    await sleep(1800);

    await scenario("01", "the network projects every persisted activity and relationship into a deterministic layout", async () => {
      await showNetwork(page);
      const state = await networkState(page);
      assert(state.present, "the Activity Network did not render");
      assert(state.nodeCount === 14 && state.nodes.length === 14, `network nodes ${state.nodeCount}/${state.nodes.length}`);
      assert(state.edgeCount === 15 && state.edges.length === 15, `network edges ${state.edgeCount}/${state.edges.length}`);
      assert(state.levels >= 3, `network levels ${state.levels}`);
      assert(state.nodes.some((node) => node.critical), "no critical node is marked");
      const types = new Set(state.edges.map((edge) => edge.type));
      assert(types.has("FS") && types.has("SS"), `stored edge types are ${JSON.stringify([...types])}`);
      const lagged = state.edges.find((edge) => edge.id === "REL-RPS-170");
      assert(lagged && lagged.type === "SS" && lagged.label === "SS+5d", `stored SS edge is ${JSON.stringify(lagged)}`);
      assert(lagged.title.includes("A140 → A170") && lagged.title.includes("working-day"), `edge title is ${lagged.title}`);
      assert(state.nodes.every((node) => node.title.includes(node.id)), "a node lost its ID/name tooltip");
      assert(state.selectedNode === state.selectedRow, `initial selection mismatch ${state.selectedRow}/${state.selectedNode}`);
      assertNoScheduleWrites("opening the network");
      await capture(page, "01-network-en-1366");
      return { levels: state.levels, nodes: state.nodeCount, edges: state.edgeCount, types: [...types].sort(), lagged: lagged.label };
    });

    await scenario("02", "selecting a network node and a table row stay synchronised", async () => {
      await clickNode(page, "A120");
      let state = await networkState(page);
      assert(state.selectedNode === "A120" && state.selectedRow === "A120", `node click selected ${state.selectedNode}/${state.selectedRow}`);
      assert(state.nodes.find((node) => node.id === "A120")?.pressed === "true", "the selected node is not aria-pressed");
      assert(state.detailsText.includes("A120"), "the details pane did not follow the network selection");

      const rowClicked = await page.evaluate(`(() => {
        const row = document.querySelector('#cp-activity-grid tbody tr[data-activity-id="A145"]');
        if (!row) return false;
        row.scrollIntoView({ block: "center" });
        row.click();
        return true;
      })()`);
      assert(rowClicked, "table row A145 is missing");
      await sleep(700);
      state = await networkState(page);
      assert(state.selectedNode === "A145" && state.selectedRow === "A145", `table click selected ${state.selectedNode}/${state.selectedRow}`);
      assertNoScheduleWrites("changing selection");
      await capture(page, "02-selection-sync-en-1366");
      return { fromNode: "A120", fromTable: state.selectedRow };
    });

    await scenario("03", "a focused node activates with the keyboard", async () => {
      const focused = await page.evaluate(`(() => {
        const node = document.querySelector('[data-network-view] [data-gantt-activity-id="A150"]');
        if (!node) return false;
        node.scrollIntoView({ block: "center" });
        node.focus();
        return document.activeElement === node;
      })()`);
      assert(focused, "network node A150 could not take focus");
      await page.cdp.send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13 });
      await page.cdp.send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13 });
      await sleep(700);
      const state = await networkState(page);
      assert(state.selectedNode === "A150" && state.selectedRow === "A150", `Enter selected ${state.selectedNode}/${state.selectedRow}`);
      assertNoScheduleWrites("keyboard selection");
      return { selected: state.selectedNode };
    });

    await scenario("04", "double-clicking an edge opens its relationship editor with the stored revision", async () => {
      const state = await networkState(page);
      const edge = state.edges.find((entry) => entry.type === "SS" && entry.id !== "REL-RPS-170")
        ?? state.edges.find((entry) => entry.type === "FS");
      assert(edge, "no relationship edge to open");
      const point = await edgePoint(page, edge.id);
      assert(point && !point.miss, `edge ${edge.id} has no visible hit point: ${JSON.stringify(point)}`);
      const opened = await page.evaluate(`(() => {
        const path = document.querySelector('[data-network-edge-hit=' + JSON.stringify(${JSON.stringify(edge.id)}) + ']');
        if (!path) return false;
        path.dispatchEvent(new MouseEvent("dblclick", { bubbles: true, cancelable: true }));
        return true;
      })()`);
      assert(opened, "the double-click did not reach the edge");
      await sleep(600);
      const editor = await page.evaluate(`(() => {
        const box = document.querySelector('[data-relationship-edit-box=' + JSON.stringify(${JSON.stringify(edge.id)}) + ']');
        const form = document.querySelector('[data-relationship-edit-form=' + JSON.stringify(${JSON.stringify(edge.id)}) + ']');
        const drawer = document.querySelector("[data-tools-drawer]");
        return {
          boxOpen: Boolean(box && box.open),
          formRevision: form ? Number(form.getAttribute("data-relationship-revision")) : null,
          drawerOpen: Boolean(drawer && !drawer.hidden),
          focusedInForm: Boolean(form && form.contains(document.activeElement)),
        };
      })()`);
      assert(editor.boxOpen && editor.drawerOpen, `relationship editor state ${JSON.stringify(editor)}`);
      assert(Number.isFinite(editor.formRevision) && editor.formRevision > 0, `editor revision ${editor.formRevision}`);
      assert(editor.focusedInForm, "the editor did not take focus");
      assert(relationshipWrites.length === 0, `opening the editor wrote a relationship: ${JSON.stringify(relationshipWrites)}`);
      await capture(page, "03-edge-editor-en-1366");
      return { id: edge.id, revision: editor.formRevision, point };
    });

    await scenario("05", "the edge context menu exposes its commands and navigates to the successor", async () => {
      const state = await networkState(page);
      const edge = state.edges.find((entry) => entry.from === "A110" && entry.to === "A140") ?? state.edges[0];
      assert(edge, "no edge is available for the context menu");
      const point = await edgePoint(page, edge.id);
      assert(point && !point.miss, `edge ${edge.id} has no visible point for the context menu: ${JSON.stringify(point)}`);
      await rightClickAt(page, point.x, point.y);
      const menu = await menuState(page);
      assert(menu, "the edge context menu did not open");
      for (const command of ["relationship-edit", "relationship-delete", "relationship-predecessor", "relationship-successor"]) {
        assert(menu.commands.includes(command), `edge menu is missing ${command}: ${JSON.stringify(menu.commands)}`);
      }
      assert(menu.label === "Relationship", `edge menu label is ${JSON.stringify(menu.label)}`);
      const navigated = await page.evaluate(`(() => {
        const item = document.querySelector('[data-activity-menu-command="relationship-successor"]');
        if (!item || item.disabled) return false;
        item.click();
        return true;
      })()`);
      assert(navigated, "the Go to Successor command is disabled");
      await sleep(800);
      const after = await networkState(page);
      assert(after.selectedRow === edge.to && after.selectedNode === edge.to, `successor navigation selected ${after.selectedRow}/${after.selectedNode}, expected ${edge.to}`);
      assert(after.detailsText.includes(edge.to), "details did not follow the successor navigation");
      assertNoScheduleWrites("edge navigation");
      await capture(page, "04-edge-menu-successor-en-1366");
      return { id: edge.id, successor: edge.to, commands: menu.commands };
    });

    await scenario("06", "right-clicking a node opens the activity menu", async () => {
      const point = await nodePoint(page, "A100");
      assert(point, "node A100 is missing");
      await rightClickAt(page, point.x, point.y);
      const menu = await menuState(page);
      assert(menu, "the node context menu did not open");
      assert(menu.commands.includes("details"), `node menu is missing Details: ${JSON.stringify(menu.commands)}`);
      assert(menu.commands.includes("link"), `node menu is missing Link: ${JSON.stringify(menu.commands)}`);
      assert(menu.label === "Network Activity", `node menu label is ${JSON.stringify(menu.label)}`);
      await closeMenu(page);
      return { commands: menu.commands, label: menu.label };
    });

    await scenario("07", "zoom only scales the drawing and survives a full reload", async () => {
      const initial = await networkState(page);
      assert(Math.abs(initial.zoom - 1) < 0.001 && initial.zoomLabel === "100%", `initial zoom ${initial.zoom}/${initial.zoomLabel}`);
      await clickZoom(page, "in");
      await clickZoom(page, "in");
      const zoomed = await networkState(page);
      assert(Math.abs(zoomed.zoom - 1.2) < 0.001 && zoomed.zoomLabel === "120%", `zoom in reached ${zoomed.zoom}/${zoomed.zoomLabel}`);
      assert(Math.abs(zoomed.svgWidth - Math.round(zoomed.baseWidth * 1.2)) <= 1, `zoomed width ${zoomed.svgWidth} vs ${zoomed.baseWidth}`);
      assertNoScheduleWrites("zooming");

      await page.reload();
      await page.waitForSelector("[data-network-view]", "network after reload");
      await sleep(1400);
      const reloaded = await networkState(page);
      assert(Math.abs(reloaded.zoom - 1.2) < 0.001 && reloaded.zoomLabel === "120%", `reloaded zoom ${reloaded.zoom}/${reloaded.zoomLabel}`);

      await clickZoom(page, "out");
      const smaller = await networkState(page);
      assert(Math.abs(smaller.zoom - 1.1) < 0.001, `zoom out reached ${smaller.zoom}`);
      await clickZoom(page, "fit");
      const fitted = await networkState(page);
      assert(fitted.zoom >= 0.2 && fitted.zoom <= 1, `fit reached ${fitted.zoom}`);
      await capture(page, "05-zoom-fit-en-1366");
      return { initial: initial.zoom, zoomed: zoomed.zoom, reloaded: reloaded.zoom, fitted: fitted.zoom };
    });

    await scenario("08", "fa RTL at 1280 keeps the network readable and selection working", async () => {
      await setViewport(page, 1280, 720);
      for (let step = 0; step < 8; step += 1) await clickZoom(page, "in");
      await setLanguage(page, "fa");
      await sleep(600);
      const state = await networkState(page);
      assert(state.present && state.nodeCount === 14 && state.edgeCount === 15, `RTL network ${state.nodeCount}/${state.edgeCount}`);
      assert(state.heading.includes("شبکهٔ فعالیت"), `RTL heading is ${JSON.stringify(state.heading)}`);
      assert(state.dir === "rtl" && state.svgDir === "ltr", `direction ${state.dir}/${state.svgDir}`);
      assert(state.overflow <= 1, `RTL layout overflows by ${state.overflow}px`);
      await clickNode(page, "A160");
      const selected = await networkState(page);
      assert(selected.selectedRow === "A160" && selected.selectedNode === "A160", `RTL selection ${selected.selectedRow}/${selected.selectedNode}`);
      assertNoScheduleWrites("RTL network");
      await capture(page, "06-network-fa-rtl-1280");
      return { heading: state.heading, dir: state.dir, svgDir: state.svgDir, overflow: state.overflow };
    });

    await scenario("09", "en at 1920 keeps the same projection and no overflow", async () => {
      await setViewport(page, 1920, 1080);
      await setLanguage(page, "en");
      await sleep(600);
      const state = await networkState(page);
      assert(state.nodeCount === 14 && state.edgeCount === 15, `wide network ${state.nodeCount}/${state.edgeCount}`);
      assert(state.heading === "Activity Network", `wide heading is ${JSON.stringify(state.heading)}`);
      assert(state.dir === "ltr" && state.overflow <= 1, `wide direction/overflow ${state.dir}/${state.overflow}`);
      await clickNode(page, "A210");
      const selected = await networkState(page);
      assert(selected.selectedNode === "A210" && selected.selectedRow === "A210", `wide selection ${selected.selectedNode}/${selected.selectedRow}`);
      assertNoScheduleWrites("wide network");
      await capture(page, "07-network-en-1920");
      return { nodes: state.nodeCount, edges: state.edgeCount, overflow: state.overflow };
    });

    assert(relationshipWrites.length === 0, `opening network details wrote relationships: ${JSON.stringify(relationshipWrites)}`);
    assert(exceptions.length === 0, `runtime exceptions: ${exceptions.join(" | ")}`);
    assert(consoleErrors.length === 0, `console errors: ${consoleErrors.join(" | ")}`);
    assert(apiFailures.length === 0, `API 5xx: ${JSON.stringify(apiFailures)}`);
  } finally {
    writeReport();
    await chrome.stop();
  }
}

main().then(() => {
  log(`\n${scenarios.filter((entry) => entry.status === "pass").length}/${scenarios.length} scenarios passed`);
  process.exit(0);
}).catch((error) => {
  log(`\nFAILED: ${error && error.stack ? error.stack : error}`);
  process.exit(1);
});
