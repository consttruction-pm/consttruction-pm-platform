#!/usr/bin/env node
/**
 * Version 26 Trace Logic acceptance (ACT-016).
 *
 * Proves in the real preview that Trace Logic is a lower-layout projection of
 * the persisted relationships: the selected activity's predecessor and
 * successor chains, independent predecessor/successor depths, navigation from
 * a chain row, selection arriving from the Activity Network and the Gantt, the
 * critical red border, and en LTR 1366/1920 plus fa RTL 1280. No schedule or
 * activity write is issued.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4207 \
 *   CUBI_TESTED_CODE_SHA=<code commit> node e2e/activity-trace-logic-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4207";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-13";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const suiteName = "activity-trace-logic-v26";
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
  await sleep(1000);
}

async function selectTableRow(page, activityId) {
  const clicked = await page.evaluate(`(() => {
    const row = document.querySelector('#cp-activity-grid tbody tr[data-activity-id=' + JSON.stringify(${JSON.stringify(activityId)}) + ']');
    if (!row) return false;
    row.scrollIntoView({ block: "center" });
    row.click();
    return true;
  })()`);
  assert(clicked, `table row ${activityId} is missing`);
  await sleep(800);
}

async function showTrace(page) {
  await runMenuCommand(page, "view", "view.bottom-trace");
  await page.waitForSelector("[data-trace-logic]", "Trace Logic");
  await sleep(500);
}

async function setTraceDepth(page, direction, value) {
  const changed = await page.evaluate(`(() => {
    const select = document.querySelector('[data-trace-depth=' + JSON.stringify(${JSON.stringify(direction)}) + ']');
    if (!select) return false;
    select.value = ${JSON.stringify(String(value))};
    if (select.value !== ${JSON.stringify(String(value))}) return false;
    select.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  assert(changed, `trace depth select ${direction} did not accept ${value}`);
  await sleep(700);
}

async function traceState(page) {
  return page.evaluate(`(() => {
    const section = document.querySelector("[data-trace-logic]");
    const groups = [...(section?.querySelectorAll(".cp-trace-group") ?? [])].map((group) => ({
      title: (group.querySelector("h3")?.textContent ?? "").replace(/\\s+/g, " ").trim(),
      empty: (group.querySelector(".cp-trace-empty")?.textContent ?? "").trim(),
      rows: [...group.querySelectorAll(".cp-trace-row")].map((row) => {
        const critical = row.classList.contains("is-critical");
        const style = getComputedStyle(row);
        return {
          id: row.getAttribute("data-trace-activity-id"),
          level: Number(row.querySelector(".cp-trace-level")?.textContent || 0),
          edge: (row.querySelector(".cp-trace-edge")?.textContent ?? "").trim(),
          critical,
          selected: row.classList.contains("is-selected"),
          title: row.getAttribute("title") ?? "",
          borderColor: style.borderInlineStartColor || style.borderLeftColor,
        };
      }),
    }));
    const selects = [...(section?.querySelectorAll("[data-trace-depth]") ?? [])].map((select) => ({
      direction: select.getAttribute("data-trace-depth"),
      value: Number(select.value),
      label: (select.closest("label")?.textContent ?? "").replace(/\\s+/g, " ").trim(),
    }));
    const selectedRow = document.querySelector("#cp-activity-grid tbody tr[aria-selected='true']");
    return {
      present: Boolean(section),
      bottomLayout: document.querySelector(".cp-main[data-details-split]")?.getAttribute("data-bottom-layout") ?? null,
      surface: document.querySelector("#cp-details")?.getAttribute("data-bottom-surface") ?? null,
      labelledBy: document.querySelector("#cp-details")?.getAttribute("aria-labelledby") ?? null,
      heading: (section?.querySelector("h2")?.textContent ?? "").trim(),
      selected: section?.querySelector("[data-trace-selected]")?.getAttribute("data-trace-selected") ?? null,
      selectedRow: selectedRow?.getAttribute("data-activity-id") ?? null,
      predecessorDepth: Number(section?.getAttribute("data-trace-predecessor-depth") || 0),
      successorDepth: Number(section?.getAttribute("data-trace-successor-depth") || 0),
      selects,
      groups,
      notices: [...(section?.querySelectorAll(".cp-register-notice") ?? [])].map((item) => item.textContent.trim()),
      dir: document.documentElement.dir || "ltr",
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      detailsText: (document.querySelector("#cp-details")?.textContent ?? "").replace(/\\s+/g, " ").trim(),
    };
  })()`);
}

function ids(group) {
  return group.rows.map((row) => row.id);
}

function levels(group) {
  return group.rows.map((row) => [row.id, row.level]);
}

async function clickGanttBar(page, activityId) {
  const clicked = await page.evaluate(`(() => {
    const bar = document.querySelector('#cp-gantt [data-gantt-activity-id=' + JSON.stringify(${JSON.stringify(activityId)}) + ']');
    if (!bar) return false;
    bar.scrollIntoView({ block: "center", inline: "center" });
    bar.click();
    return true;
  })()`);
  assert(clicked, `Gantt bar ${activityId} is missing`);
  await sleep(800);
}

async function clickNetworkNode(page, activityId) {
  const point = await page.evaluate(`(() => {
    const node = document.querySelector('[data-network-view] [data-gantt-activity-id=' + JSON.stringify(${JSON.stringify(activityId)}) + ']');
    if (!node) return null;
    node.scrollIntoView({ block: "center", inline: "center" });
    const rect = node.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return null;
    return { x: Math.round(rect.left + rect.width / 2), y: Math.round(rect.top + rect.height / 2) };
  })()`);
  assert(point, `network node ${activityId} is missing`);
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: point.x, y: point.y, button: "none", buttons: 0 });
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x: point.x, y: point.y, button: "left", buttons: 1, clickCount: 1 });
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: point.x, y: point.y, button: "left", buttons: 0, clickCount: 1 });
  await sleep(800);
}

function assertNoScheduleWrites(label) {
  const writes = scheduleWrites.splice(0);
  assert(writes.length === 0, `${label}: Trace Logic wrote schedule/activity data: ${writes.map((item) => `${item.method} ${item.url}`).join(", ")}`);
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
    if (url.includes("/p6/relationships")) { relationshipWrites.push({ method, url }); return; }
    if (url.includes("/p6/schedule/") || url.includes("/activities/")) scheduleWrites.push({ method, url });
  });

  const report = {
    contract: "cubi-activity-trace-logic-v26.v1",
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

    await scenario("01", "Show on Bottom: Trace Logic projects the persisted chain of the selected activity", async () => {
      await selectTableRow(page, "A130");
      await showTrace(page);
      const state = await traceState(page);
      assert(state.present, "Trace Logic did not render");
      assert(state.bottomLayout === "trace-logic" && state.surface === "trace-logic", `layout ${state.bottomLayout}/${state.surface}`);
      assert(state.labelledBy === "cp-trace-heading", `pane labelled by ${state.labelledBy}`);
      assert(state.selected === "A130" && state.selectedRow === "A130", `selected ${state.selected}/${state.selectedRow}`);
      assert(state.groups.length === 2, `groups ${state.groups.length}`);
      assert(ids(state.groups[0]).join(",") === "A120,A110", `predecessors ${JSON.stringify(ids(state.groups[0]))}`);
      assert(JSON.stringify(levels(state.groups[0])) === JSON.stringify([["A120", 1], ["A110", 2]]), `predecessor levels ${JSON.stringify(levels(state.groups[0]))}`);
      assert(ids(state.groups[1]).join(",") === "A140,A150,A145,A155,A160,A170", `successors ${JSON.stringify(ids(state.groups[1]))}`);
      assert(JSON.stringify(levels(state.groups[1])) === JSON.stringify([["A140", 1], ["A150", 1], ["A145", 1], ["A155", 2], ["A160", 2], ["A170", 2]]), `successor levels ${JSON.stringify(levels(state.groups[1]))}`);
      assert(state.groups[0].rows.every((row) => row.edge === "FS"), `predecessor edge labels ${JSON.stringify(state.groups[0].rows.map((row) => row.edge))}`);
      assert(state.groups[1].rows.filter((row) => row.id !== "A170").every((row) => row.edge === "FS"), "a successor lost its FS label");
      assert(state.groups[1].rows.find((row) => row.id === "A170")?.edge === "SS+5d", "the stored SS+5d edge label is missing");
      assert(state.groups[0].rows.find((row) => row.id === "A120")?.selected === false, "the selection leaked onto a chain row");
      assert(state.predecessorDepth === 2 && state.successorDepth === 2, `depths ${state.predecessorDepth}/${state.successorDepth}`);
      assert(state.selects.length === 2 && state.selects.map((select) => select.direction).join(",") === "predecessors,successors", `selects ${JSON.stringify(state.selects)}`);
      assertNoScheduleWrites("opening Trace Logic");
      await capture(page, "01-trace-a130-en-1366");
      return { predecessors: ids(state.groups[0]), successors: ids(state.groups[1]), depths: [state.predecessorDepth, state.successorDepth] };
    });

    await scenario("02", "Bottom Layout Options sets predecessor and successor levels independently and keeps them", async () => {
      await setTraceDepth(page, "predecessors", 1);
      await setTraceDepth(page, "successors", 3);
      let state = await traceState(page);
      assert(state.predecessorDepth === 1 && state.successorDepth === 3, `depths ${state.predecessorDepth}/${state.successorDepth}`);
      assert(ids(state.groups[0]).join(",") === "A120", `depth-1 predecessors ${JSON.stringify(ids(state.groups[0]))}`);
      const successors = ids(state.groups[1]);
      assert(successors.join(",") === "A140,A150,A145,A155,A160,A170,A180", `depth-3 successors ${JSON.stringify(successors)}`);
      const ss = state.groups[1].rows.find((row) => row.id === "A170");
      assert(ss && ss.edge === "SS+5d", `the stored SS lag edge is ${JSON.stringify(ss)}`);

      const stored = await page.evaluate(`(() => ({
        predecessors: localStorage.getItem("cubi:workspace:trace-logic-predecessor-depth"),
        successors: localStorage.getItem("cubi:workspace:trace-logic-successor-depth"),
      }))()`);
      assert(stored.predecessors === "1" && stored.successors === "3", `stored depths ${JSON.stringify(stored)}`);

      await page.reload();
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows after reload");
      await sleep(1400);
      // Trace Logic needs a selected activity, so the reload restores the depth
      // preference and the stored layout, then the first selection reveals it.
      await selectTableRow(page, "A130");
      await page.waitForSelector("[data-trace-logic]", "Trace Logic after reload");
      await sleep(600);
      state = await traceState(page);
      assert(state.predecessorDepth === 1 && state.successorDepth === 3, `reloaded depths ${state.predecessorDepth}/${state.successorDepth}`);
      assert(ids(state.groups[1]).includes("A180"), "the reloaded successor chain lost level 3");
      assert(state.selects.find((select) => select.direction === "predecessors")?.value === 1, "the predecessor select did not restore 1");
      await capture(page, "02-trace-independent-depths-en-1366");
      return { predecessors: state.predecessorDepth, successors: state.successorDepth, successorIds: ids(state.groups[1]) };
    });

    await scenario("03", "following a chain row moves the selection and redraws both chains", async () => {
      const clicked = await page.evaluate(`(() => {
        const button = document.querySelector('[data-trace-goto="A120"]');
        if (!button) return false;
        button.click();
        return true;
      })()`);
      assert(clicked, "the A120 chain row is missing");
      await sleep(900);
      const state = await traceState(page);
      assert(state.selected === "A120" && state.selectedRow === "A120", `goto selected ${state.selected}/${state.selectedRow}`);
      assert(ids(state.groups[0]).join(",") === "A110", `A120 predecessors ${JSON.stringify(ids(state.groups[0]))}`);
      assert(ids(state.groups[1]).includes("A130"), `A120 successors ${JSON.stringify(ids(state.groups[1]))}`);
      assert(state.detailsText.includes("A120"), "the details pane did not follow the chain navigation");
      assertNoScheduleWrites("following a chain row");
      await capture(page, "03-trace-goto-a120-en-1366");
      return { selected: state.selected, predecessors: ids(state.groups[0]) };
    });

    await scenario("04", "selecting in the Activity Network updates Trace Logic", async () => {
      await setTraceDepth(page, "predecessors", 2);
      await setTraceDepth(page, "successors", 2);
      await runMenuCommand(page, "view", "view.top-network");
      await page.waitForSelector("[data-network-view]", "Activity Network");
      await sleep(600);
      await clickNetworkNode(page, "A160");
      const state = await traceState(page);
      assert(state.selected === "A160" && state.selectedRow === "A160", `network selection ${state.selected}/${state.selectedRow}`);
      assert(ids(state.groups[0]).join(",") === "A140,A150,A130", `A160 predecessors ${JSON.stringify(ids(state.groups[0]))}`);
      assert(ids(state.groups[1]).join(",") === "A180,A190", `A160 successors ${JSON.stringify(ids(state.groups[1]))}`);
      assertNoScheduleWrites("network selection");
      await capture(page, "04-trace-from-network-en-1366");
      return { selected: state.selected, predecessors: ids(state.groups[0]), successors: ids(state.groups[1]) };
    });

    await scenario("05", "selecting a Gantt bar updates Trace Logic", async () => {
      await setTraceDepth(page, "predecessors", 1);
      await setTraceDepth(page, "successors", 3);
      await runMenuCommand(page, "view", "view.top-table-gantt");
      await page.waitForSelector("#cp-gantt [data-gantt-activity-id]", "Gantt bars");
      await sleep(600);
      await clickGanttBar(page, "A145");
      const state = await traceState(page);
      assert(state.selected === "A145" && state.selectedRow === "A145", `Gantt selection ${state.selected}/${state.selectedRow}`);
      assert(ids(state.groups[0]).join(",") === "A130", `A145 predecessors ${JSON.stringify(ids(state.groups[0]))}`);
      assert(ids(state.groups[1]).join(",") === "A155,A180,A190", `A145 successors ${JSON.stringify(ids(state.groups[1]))}`);
      assertNoScheduleWrites("Gantt selection");
      await capture(page, "05-trace-from-gantt-en-1366");
      return { selected: state.selected, predecessors: ids(state.groups[0]), successors: ids(state.groups[1]) };
    });

    await scenario("06", "critical activities keep a red border and an accessible label", async () => {
      const criticalBar = await page.evaluate(`(() => {
        const bar = document.querySelector("#cp-gantt .cp-gantt-bar.is-critical");
        return bar?.closest("[data-gantt-activity-id]")?.getAttribute("data-gantt-activity-id") ?? null;
      })()`);
      assert(criticalBar, "the fixture exposes no critical activity to trace");
      await clickGanttBar(page, criticalBar);
      const state = await traceState(page);
      let criticalRows = 0;
      for (const group of state.groups) {
        for (const row of group.rows) {
          if (!row.critical) continue;
          criticalRows += 1;
          assert(row.title.length > 0, `critical row ${row.id} has no accessible label`);
          assert(row.borderColor === "rgb(192, 57, 43)" || row.borderColor === "#c0392b", `critical row ${row.id} border is ${row.borderColor}`);
        }
      }
      assert(criticalRows > 0, "no critical chain row is marked even though a critical activity exists");
      await capture(page, "06-trace-critical-en-1366");
      return { criticalBar, criticalRows };
    });

    await scenario("07", "an activity without predecessors shows an explicit empty predecessor group", async () => {
      await selectTableRow(page, "A100");
      const state = await traceState(page);
      assert(state.selected === "A100", `selected ${state.selected}`);
      assert(state.groups[0].rows.length === 0 && /None within depth/.test(state.groups[0].empty), `predecessor group ${JSON.stringify(state.groups[0])}`);
      assert(ids(state.groups[1]).join(",") === "A110,A120,A130", `A100 successors ${JSON.stringify(ids(state.groups[1]))}`);
      assertNoScheduleWrites("empty predecessor group");
      return { emptyText: state.groups[0].empty };
    });

    await scenario("08", "fa RTL at 1280 localizes Trace Logic and keeps chain navigation working", async () => {
      await setViewport(page, 1280, 720);
      await setLanguage(page, "fa");
      await sleep(700);
      await selectTableRow(page, "A130");
      const state = await traceState(page);
      assert(state.present, "Trace Logic disappeared in RTL");
      assert(state.dir === "rtl", `direction ${state.dir}`);
      assert(state.heading === "ردیابی منطق", `heading ${JSON.stringify(state.heading)}`);
      assert(state.groups[0].title.startsWith("پیش‌نیازها"), `predecessor title ${JSON.stringify(state.groups[0].title)}`);
      assert(state.groups[1].title.startsWith("پس‌نیازها"), `successor title ${JSON.stringify(state.groups[1].title)}`);
      assert(state.selects.every((select) => select.label.length > 0), "a depth control lost its localized label");
      assert(ids(state.groups[0]).join(",") === "A120,A110" || ids(state.groups[0]).join(",") === "A120", `RTL predecessors ${JSON.stringify(ids(state.groups[0]))}`);
      assert(state.overflow <= 1, `RTL layout overflows by ${state.overflow}px`);
      const clicked = await page.evaluate(`(() => {
        const button = document.querySelector('[data-trace-goto="A120"]');
        if (!button) return false;
        button.click();
        return true;
      })()`);
      assert(clicked, "the RTL chain row is missing");
      await sleep(800);
      const after = await traceState(page);
      assert(after.selected === "A120" && after.selectedRow === "A120", `RTL goto selected ${after.selected}/${after.selectedRow}`);
      assertNoScheduleWrites("RTL Trace Logic");
      await capture(page, "07-trace-fa-rtl-1280");
      return { heading: state.heading, dir: state.dir, overflow: state.overflow };
    });

    await scenario("09", "en at 1920 keeps the same chain and no overflow", async () => {
      await setViewport(page, 1920, 1080);
      await setLanguage(page, "en");
      await sleep(700);
      await setTraceDepth(page, "predecessors", 2);
      await setTraceDepth(page, "successors", 2);
      await selectTableRow(page, "A160");
      const state = await traceState(page);
      assert(state.heading === "Trace Logic", `wide heading ${JSON.stringify(state.heading)}`);
      assert(state.dir === "ltr" && state.overflow <= 1, `wide direction/overflow ${state.dir}/${state.overflow}`);
      assert(ids(state.groups[0]).join(",") === "A140,A150,A130", `wide predecessors ${JSON.stringify(ids(state.groups[0]))}`);
      assert(ids(state.groups[1]).join(",") === "A180,A190", `wide successors ${JSON.stringify(ids(state.groups[1]))}`);
      assertNoScheduleWrites("wide Trace Logic");
      await capture(page, "08-trace-en-1920");
      return { predecessors: ids(state.groups[0]), successors: ids(state.groups[1]), overflow: state.overflow };
    });

    assert(relationshipWrites.length === 0, `Trace Logic wrote relationships: ${JSON.stringify(relationshipWrites)}`);
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
