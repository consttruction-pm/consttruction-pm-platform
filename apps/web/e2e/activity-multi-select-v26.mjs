#!/usr/bin/env node
/**
 * Browser E2E for Version 26 multi-row selection in the Activities table.
 *
 * The workspace keeps one primary row (the one whose details are shown) plus
 * every Ctrl/Cmd-clicked or Shift-range row, and the Gantt reflects the same
 * selection. Rows are read from the real preview workspace; nothing is mocked.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 \
 *   CUBI_TESTED_CODE_SHA=<code commit> \
 *   CUBI_CHROME_NO_SANDBOX=1 node e2e/activity-multi-select-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const outDir = join(artifactsDir, "activity-multi-select-v26");
const evidenceDir = join(
  artifactsDir,
  "..",
  "..",
  "..",
  "..",
  "docs",
  "workspace",
  "evidence",
  `activity-multi-select-v26-${evidenceDate}`,
);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const CTRL = 2;
const SHIFT = 8;

const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const scenarios = [];
const screenshots = [];
const cells = [];

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
  } catch (error) {
    record(id, name, "fail", { error: String(error && error.stack ? error.stack : error) });
    throw error;
  }
}

async function capture(page, name) {
  const file = `activity-multi-select-v26/${name}.png`;
  await page.screenshot(file);
  copyFileSync(join(artifactsDir, file), join(evidenceDir, `${name}.png`));
  screenshots.push(`${name}.png`);
  return file;
}

async function setLanguage(page, locale) {
  const changed = await page.evaluate(`(() => {
    const select = document.querySelector("[data-workspace-language]");
    if (!select) return false;
    if (select.value === ${JSON.stringify(locale)}) return true;
    select.value = ${JSON.stringify(locale)};
    select.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  assert(changed, `language selector did not accept ${locale}`);
  await sleep(900);
}

async function loginAs(page, label, locale = "en") {
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
  const hasPersonas = await page.evaluate('Boolean(document.querySelector(".persona"))');
  if (!hasPersonas) {
    const logoutStatus = await page.evaluate(
      `fetch("/preview/logout", { method: "POST", redirect: "manual" }).then((response) => response.status)`,
      { awaitPromise: true },
    );
    assert([0, 200, 302, 303].includes(logoutStatus), `unexpected logout status ${logoutStatus}`);
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, ".persona", "persona cards after sign out");
  }
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
  await sleep(1400);
  await setLanguage(page, locale);
}

const selectionState = `(() => {
  const rows = [...document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]")];
  const selected = rows.filter((row) => row.getAttribute("aria-selected") === "true").map((row) => row.dataset.activityId);
  const codes = {};
  for (const row of rows) {
    codes[row.dataset.activityId] = (row.querySelector("td[role='gridcell']")?.textContent ?? "").trim();
  }
  const detailsSelected = document.querySelector("#cp-details .cp-detail-selected")?.textContent?.trim() ?? "";
  return {
    ids: rows.map((row) => row.dataset.activityId),
    selected,
    codes,
    detailsSelected,
    primary: Object.keys(codes).find((id) => codes[id] === detailsSelected) ?? null,
    multiSelectable: document.querySelector("#cp-activity-grid table")?.getAttribute("aria-multiselectable") ?? null,
    ganttSelected: [...document.querySelectorAll("[data-gantt-activity-id][aria-pressed='true']")].map((row) => row.dataset.ganttActivityId),
    direction: getComputedStyle(document.querySelector(".cp-workspace")).direction,
  };
})()`;

async function readSelection(page) {
  return page.evaluate(selectionState);
}

async function clickRow(page, selector, modifiers = 0) {
  const point = await page.evaluate(`(() => {
    const row = document.querySelector(${JSON.stringify(selector)});
    if (!row) return null;
    row.scrollIntoView({ block: "center", inline: "nearest" });
    const rect = row.getBoundingClientRect();
    return { x: rect.left + Math.min(36, Math.max(12, rect.width / 4)), y: rect.top + rect.height / 2 };
  })()`);
  assert(point, `row ${selector} is missing`);
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x: point.x, y: point.y, button: "left", clickCount: 1, modifiers });
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: point.x, y: point.y, button: "left", clickCount: 1, modifiers });
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
    if (url.includes("/api/") && params.response.status >= 500) {
      apiFailures.push({ status: params.response.status, url });
    }
  });

  const report = {
    contract: "cubi-activity-multi-select-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    capturedAt: new Date().toISOString(),
    cells,
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
  };

  try {
    cells.push({ viewport: "1366x768", locale: "en", direction: "ltr", role: "planner" });
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 768, deviceScaleFactor: 1, mobile: false });
    await sleep(300);
    await loginAs(page, "Planner");
    const initial = await readSelection(page);
    assert(initial.ids.length >= 6, `expected at least six activity rows, got ${initial.ids.length}`);
    assert(initial.multiSelectable === "true", `grid aria-multiselectable is ${initial.multiSelectable}`);
    const [first, second, third, fourth, fifth] = initial.ids;

    await scenario("01", "a plain click selects exactly one row", async () => {
      await clickRow(page, `[data-activity-id="${first}"]`);
      const state = await readSelection(page);
      assert(state.selected.length === 1 && state.selected[0] === first, `selected ${JSON.stringify(state.selected)}`);
      assert(state.primary === first, `details primary ${state.primary}`);
      await capture(page, "01-single-select");
      return { selected: state.selected };
    });

    await scenario("02", "Ctrl-click adds a row and focuses its details", async () => {
      await clickRow(page, `[data-activity-id="${third}"]`, CTRL);
      const state = await readSelection(page);
      assert(JSON.stringify(state.selected) === JSON.stringify([first, third]), `selected ${JSON.stringify(state.selected)}`);
      assert(state.primary === third, `details primary ${state.primary}`);
      await capture(page, "02-ctrl-select");
      return { selected: state.selected, primary: state.primary };
    });

    await scenario("03", "Shift-click selects the inclusive range from the fixed anchor", async () => {
      await clickRow(page, `[data-activity-id="${fifth}"]`, SHIFT);
      const state = await readSelection(page);
      assert(JSON.stringify(state.selected) === JSON.stringify([third, fourth, fifth]), `selected ${JSON.stringify(state.selected)}`);
      assert(state.primary === fifth, `details primary ${state.primary}`);
      await capture(page, "03-shift-range");
      return { selected: state.selected, anchor: third };
    });

    await scenario("04", "Ctrl-click removes only the clicked row", async () => {
      await clickRow(page, `[data-activity-id="${fourth}"]`, CTRL);
      let state = await readSelection(page);
      assert(JSON.stringify(state.selected) === JSON.stringify([third, fifth]), `selected ${JSON.stringify(state.selected)}`);
      assert(state.primary === fifth, `details primary ${state.primary}`);
      await clickRow(page, `[data-activity-id="${fifth}"]`, CTRL);
      state = await readSelection(page);
      assert(JSON.stringify(state.selected) === JSON.stringify([third]), `selected after removing primary ${JSON.stringify(state.selected)}`);
      assert(state.primary === third, `details primary after removing the primary ${state.primary}`);
      return { remaining: state.selected };
    });

    await scenario("05", "a plain click collapses back to one row", async () => {
      await clickRow(page, `[data-activity-id="${second}"]`);
      const state = await readSelection(page);
      assert(JSON.stringify(state.selected) === JSON.stringify([second]), `selected ${JSON.stringify(state.selected)}`);
      assert(state.primary === second, `details primary ${state.primary}`);
      return { selected: state.selected };
    });

    await scenario("06", "the Gantt shares the same multi-row selection", async () => {
      await clickRow(page, `[data-gantt-activity-id="${third}"]`, CTRL);
      const state = await readSelection(page);
      assert(JSON.stringify(state.selected) === JSON.stringify([second, third]), `table selected ${JSON.stringify(state.selected)}`);
      assert(JSON.stringify(state.ganttSelected) === JSON.stringify([second, third]), `gantt selected ${JSON.stringify(state.ganttSelected)}`);
      assert(state.primary === third, `details primary ${state.primary}`);
      await capture(page, "04-gantt-selection");
      return { table: state.selected, gantt: state.ganttSelected };
    });

    await scenario("07", "a full reload clears the in-memory selection", async () => {
      await page.navigate(`${baseUrl}/app?view=live`, "form", "workspace reset");
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows after reload");
      await sleep(1200);
      const state = await readSelection(page);
      assert(state.selected.length === 0, `selection after reload ${JSON.stringify(state.selected)}`);
      assert(state.primary === null, `details primary after reload ${state.primary} (${state.detailsSelected})`);
      return { selected: state.selected };
    });

    await scenario("08", "Shift-range selection works in the Persian RTL layout", async () => {
      cells.push({ viewport: "1280x720", locale: "fa", direction: "rtl", role: "planner" });
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await sleep(300);
      await setLanguage(page, "fa");
      const before = await readSelection(page);
      const [faFirst, , faThird] = before.ids;
      await clickRow(page, `[data-activity-id="${faFirst}"]`);
      await clickRow(page, `[data-activity-id="${faThird}"]`, SHIFT);
      const state = await readSelection(page);
      assert(state.direction === "rtl", `workspace direction ${state.direction}`);
      assert(JSON.stringify(state.selected) === JSON.stringify([faFirst, before.ids[1], faThird]), `fa selected ${JSON.stringify(state.selected)}`);
      assert(state.primary === faThird, `fa details primary ${state.primary}`);
      await capture(page, "05-fa-shift-range");
      return { locale: "fa", selected: state.selected };
    });

    assert(exceptions.length === 0, `exceptions: ${exceptions.join(" | ")}`);
    assert(consoleErrors.length === 0, `console errors: ${consoleErrors.join(" | ")}`);
    assert(apiFailures.length === 0, `API failures: ${JSON.stringify(apiFailures)}`);
  } finally {
    writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(evidenceDir, "report.json"), JSON.stringify(report, null, 2));
    chrome.stop();
  }

  log(`\nActivity multi-select E2E: ${scenarios.length}/${scenarios.length} scenarios passed`);
  log(`Screenshots: ${screenshots.join(", ")}`);
}

main().catch((error) => {
  process.stderr.write(`${error && error.stack ? error.stack : error}\n`);
  process.exitCode = 1;
});
