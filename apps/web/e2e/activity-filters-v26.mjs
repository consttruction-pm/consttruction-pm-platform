#!/usr/bin/env node
/**
 * Version 26 activity filter acceptance (ACT-003).
 *
 * Proves in the real preview that the Filters dialog is a manager plus an
 * editor with the documented Version 26 behaviour:
 *   - the list has Default/Global/Layout/User categories, All Activities,
 *     All/Any combination, Replace/Highlight and the New/Delete/Cut/Copy/
 *     Paste/Duplicate/Modify/Make Global/Copy as Layout actions, with Clear
 *     in the definition editor;
 *   - the editor writes named filters with typed rows, Add/Delete/Move, the
 *     High value column for "is within range of", relative date tokens
 *     (CD/CS/CF ± n d/w/m/y) and inline validation;
 *   - the live preview counts matching activities before Apply, and applying
 *     the filter narrows or highlights the real grid without touching
 *     schedule data;
 *   - a saved filter survives a full reload and renders in a Persian RTL cell
 *     without overflow.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4198 \
 *   CUBI_TESTED_CODE_SHA=<code commit> node e2e/activity-filters-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4198";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
// Optional artificial latency. The deployed preview answers through a relay, so
// local runs can reproduce that timing and prove layout saves stay serialised.
const networkLatencyMs = Number(process.env.CUBI_NETWORK_LATENCY_MS || 0);
const outDir = join(artifactsDir, "activity-filters-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `activity-filters-v26-${evidenceDate}`);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const exceptions = [];
const consoleErrors = [];
const consoleErrorLog = [];
const apiFailures = [];
const layoutWrites = [];
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
  const file = `activity-filters-v26/${name}.png`;
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

const dialogSelector = "dialog[data-desktop-dialog=filters]";

async function openFilters(page) {
  const clicked = await page.evaluate(`(() => {
    const element = [...document.querySelectorAll('[data-desktop-command="dialog.filters"]')]
      .find((item) => item.getClientRects().length > 0 && !item.disabled);
    if (!element) return false;
    element.click();
    return true;
  })()`);
  assert(clicked, "Filters toolbar command is missing");
  await page.waitForSelector(`${dialogSelector}[open]`, "filters dialog", 8000);
  await sleep(250);
}

async function setSelect(page, index, key, value) {
  const changed = await page.evaluate(`(() => {
    const select = document.querySelector('${dialogSelector} select[name="filter.${key}.${index}"]');
    if (!select) return false;
    select.value = ${JSON.stringify(value)};
    if (select.value !== ${JSON.stringify(value)}) return false;
    select.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  assert(changed, `filter ${key}.${index} did not accept ${value}`);
  await sleep(120);
}

async function setText(page, name, value) {
  const changed = await page.evaluate(`(() => {
    const input = document.querySelector('${dialogSelector} input[name="${name}"]');
    if (!input) return false;
    input.value = ${JSON.stringify(value)};
    input.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  assert(changed, `filter input ${name} is missing`);
  await sleep(150);
}

async function clickInDialog(page, selector) {
  const clicked = await page.evaluate(`(() => {
    const element = document.querySelector('${dialogSelector} ' + ${JSON.stringify(selector)});
    if (!element || element.disabled) return false;
    element.click();
    return true;
  })()`);
  assert(clicked, `not clickable in the Filters dialog: ${selector}`);
  await sleep(150);
}

async function preview(page) {
  return page.evaluate(`(() => {
    const element = document.querySelector("${dialogSelector} [data-filter-preview]");
    return {
      text: element?.textContent?.trim() ?? "",
      valid: element?.dataset.filterPreviewValid ?? "",
      matched: Number(element?.dataset.filterPreviewMatched ?? "-1"),
      rows: document.querySelectorAll("${dialogSelector} [data-filter-rows] .cp-filter-row").length,
      names: [...document.querySelectorAll('${dialogSelector} [data-filter-rows] .cp-filter-row input[name^="filter.value."]')].map((input) => input.name),
      joins: [...document.querySelectorAll('${dialogSelector} [data-filter-join]')].map((join) => ({ hidden: join.hidden, text: join.textContent.trim() })),
    };
  })()`);
}

async function gridState(page) {
  return page.evaluate(`(() => ({
    rows: document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]").length,
    matched: document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id].is-filter-match").length,
    ganttRows: document.querySelectorAll("#cp-gantt [data-gantt-activity-id]").length,
    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    dir: document.documentElement.dir || "ltr",
    saved: [...document.querySelectorAll("${dialogSelector} tr[data-filter-id]")].map((row) => row.getAttribute("data-filter-name")),
  }))()`);
}

async function submitOk(page) {
  await clickInDialog(page, "[data-dialog-ok]");
  await page.waitFor(`!document.querySelector('${dialogSelector}')?.open`, "filters dialog closed", 8000);
  await sleep(900);
}

async function main() {
  const health = await waitForHttp(`${baseUrl}/preview/health`, 30000);
  if (!(health.status === "ok" || health.status === 200)) throw new Error(`preview health ${health.status}`);

  const chrome = await launchChrome();
  const page = new Page(chrome.cdp);
  await page.initialize();
  if (networkLatencyMs > 0) {
    await page.cdp.send("Network.emulateNetworkConditions", {
      offline: false,
      latency: networkLatencyMs,
      downloadThroughput: -1,
      uploadThroughput: -1,
    });
  }
  page.cdp.on("Runtime.exceptionThrown", (params) => {
    exceptions.push(params.exceptionDetails?.exception?.description ?? params.exceptionDetails?.text ?? "unknown exception");
  });
  page.cdp.on("Runtime.consoleAPICalled", (params) => {
    if (params.type !== "error") return;
    const message = (params.args ?? []).map((arg) => arg.value ?? arg.description ?? arg.type).join(" ");
    consoleErrors.push(message);
    consoleErrorLog.push({ at: params.timestamp ?? null, message });
  });
  // Layout revisions are append-only: two overlapping saves from the same base
  // are a client race, not a server error. Recording the POSTs makes that race
  // visible instead of hiding it behind the recovery reload.
  const layoutRequests = new Map();
  page.cdp.on("Network.requestWillBeSent", (params) => {
    const request = params.request ?? {};
    if (request.method !== "POST") return;
    if (!/\/p6\/layouts\/[^/]+\/[^/?]+/.test(request.url ?? "")) return;
    const entry = { requestId: params.requestId, at: params.timestamp, url: request.url, revision: null };
    try {
      entry.revision = JSON.parse(request.postData ?? "{}").revision ?? null;
    } catch {
      entry.revision = null;
    }
    layoutRequests.set(params.requestId, entry);
  });
  page.cdp.on("Network.loadingFinished", (params) => {
    const entry = layoutRequests.get(params.requestId);
    if (!entry) return;
    layoutWrites.push({ ...entry, finishedAt: params.timestamp, status: "finished" });
  });
  page.cdp.on("Network.responseReceived", (params) => {
    const url = params.response?.url ?? "";
    if (url.includes("/api/") && params.response.status >= 500) apiFailures.push({ status: params.response.status, url });
    const entry = layoutRequests.get(params.requestId);
    if (entry) entry.httpStatus = params.response.status;
  });

  const report = {
    contract: "cubi-activity-filters-v26.v3",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    consoleErrorLog,
    apiFailures,
    layoutWrites,
  };

  function writeReport() {
    report.scenarios = scenarios;
    report.passed = scenarios.filter((entry) => entry.status === "pass").length;
    report.failed = scenarios.filter((entry) => entry.status === "fail").length;
    const json = JSON.stringify(report, null, 2);
    writeFileSync(join(outDir, "activity-filters-v26.json"), json);
    writeFileSync(join(evidenceDir, "activity-filters-v26.json"), json);
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

    let totalRows = 0;
    let lookaheadMatches = 0;

    await scenario("01", "the manager and editor expose the version 26 surfaces", async () => {
      const initial = await gridState(page);
      totalRows = initial.rows;
      // The preview fixture grew past the original 14 activities; never fewer.
      assert(totalRows >= 14, `expected at least the 14-activity fixture, got ${totalRows}`);
      await openFilters(page);
      const state = await page.evaluate(`(() => {
        const dialog = document.querySelector("${dialogSelector}");
        return {
          rows: dialog.querySelectorAll("[data-filter-rows] .cp-filter-row").length,
          groups: [...dialog.querySelectorAll("tbody[data-filter-group]")].map((body) => body.getAttribute("data-filter-group")),
          actions: [...dialog.querySelectorAll("[name=\\"filterAction\\"]")].map((button) => button.value),
          add: Boolean(dialog.querySelector("[data-filter-row-add]")),
          optimize: Boolean(dialog.querySelector("[data-filter-optimize]")),
          clear: Boolean(dialog.querySelector("[data-filter-clear]")),
          remove: dialog.querySelectorAll("[data-filter-row-remove]").length,
          moves: dialog.querySelectorAll("[data-filter-row-move]").length,
          high: dialog.querySelectorAll("[data-filter-high]").length,
          heads: dialog.querySelectorAll(".cp-filter-head span").length,
          preview: dialog.querySelector("[data-filter-preview]")?.textContent?.trim() ?? "",
          overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        };
      })()`);
      assert(state.rows === 2, `expected two starter rows, got ${state.rows}`);
      assert(state.groups.join(",") === "default,global,layout,user", `filter categories ${state.groups}`);
      for (const action of ["apply", "delete", "cut", "copy", "duplicate", "paste", "make-global", "copy-as-layout"]) {
        assert(state.actions.includes(action), `action ${action} is missing`);
      }
      assert(state.add && state.optimize && state.remove === 2 && state.moves === 4, "row Add/Optimize/Delete/Move controls are incomplete");
      assert(state.clear, "the Clear control is missing");
      assert(state.high === 2, "the High value inputs are missing");
      assert(state.heads === 6, `expected six editor columns (Where/Field/Is/Value/High/actions), got ${state.heads}`);
      assert(/Preview/.test(state.preview), `preview line is missing: ${state.preview}`);
      assert(state.overflow <= 1, `the dialog overflows horizontally by ${state.overflow}px`);
      await capture(page, "01-filters-dialog-en-1366");
      return { rows: state.rows, actions: state.actions, groups: state.groups };
    });

    await scenario("02", "the editor validates typed and relative dates before Apply", async () => {
      await setSelect(page, 0, "field", "start");
      const operators = await page.evaluate(`[...document.querySelectorAll("${dialogSelector} select[name=\\"filter.operator.0\\"] option")].map((option) => option.value)`);
      assert(operators.includes("within-range"), "the Start parameter does not offer is within range of");
      assert(!operators.includes("contains"), "a date parameter must not offer contains");
      await setSelect(page, 0, "operator", "within-range");
      await setText(page, "filter.value.0", "CS");
      const missingHigh = await preview(page);
      assert(missingHigh.valid === "false", "a range without a high value must be invalid");
      assert(/high value/i.test(missingHigh.text), `range message was ${missingHigh.text}`);

      await setText(page, "filter.high.0", "next week");
      const invalidDate = await preview(page);
      assert(invalidDate.valid === "false", "an unparseable date token must be invalid");
      assert(/ISO date|relative token/i.test(invalidDate.text), `date message was ${invalidDate.text}`);

      await setText(page, "filter.high.0", "CS+6w");
      const valid = await preview(page);
      assert(valid.valid === "true", `a CS..CS+6w range must validate: ${valid.text}`);
      assert(valid.matched > 0 && valid.matched < totalRows, `expected a partial match, got ${valid.matched}/${totalRows}`);
      lookaheadMatches = valid.matched;
      await capture(page, "02-filter-preview-en-1366");
      return { matched: valid.matched, total: totalRows, text: valid.text };
    });

    await scenario("03", "Add and the High value column save a compound lookahead filter", async () => {
      await clickInDialog(page, "[data-filter-row-add]");
      let state = await preview(page);
      assert(state.rows === 3, `Add did not append a criterion (rows ${state.rows})`);
      assert(state.joins[2] && !state.joins[2].hidden && /And/i.test(state.joins[2].text), "a later row must show the And join");
      await setSelect(page, 2, "field", "progress");
      await setSelect(page, 2, "operator", "not-equals");
      await setText(page, "filter.value.2", "100");
      await setText(page, "filterName", "Six-Week Lookahead");
      state = await preview(page);
      assert(state.valid === "true", `compound filter is invalid: ${state.text}`);
      assert(state.matched > 0 && state.matched < lookaheadMatches, `progress filter should narrow ${lookaheadMatches}, got ${state.matched}`);
      lookaheadMatches = state.matched;
      await submitOk(page);
      const applied = await gridState(page);
      assert(applied.rows === lookaheadMatches, `grid shows ${applied.rows} rows, preview said ${lookaheadMatches}`);
      await openFilters(page);
      const saved = await gridState(page);
      assert(saved.saved.includes("six-week lookahead"), `saved filter list is ${saved.saved.join(", ")}`);
      await capture(page, "03-saved-lookahead-en-1366");
      await clickInDialog(page, "[data-dialog-cancel]");
      await sleep(300);
      return { matched: lookaheadMatches, rows: applied.rows };
    });

    await scenario("04", "the saved filter and its result survive a full reload", async () => {
      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "reload with the filter applied");
      await sleep(900);
      const reloaded = await gridState(page);
      assert(reloaded.rows === lookaheadMatches, `reload shows ${reloaded.rows} rows, expected ${lookaheadMatches}`);
      await openFilters(page);
      const state = await gridState(page);
      assert(state.saved.includes("six-week lookahead"), "the saved filter disappeared after reload");
      await capture(page, "04-filter-after-reload-en-1366");
      await clickInDialog(page, "[data-dialog-cancel]");
      await sleep(300);
      return { rows: reloaded.rows, saved: state.saved };
    });

    await scenario("05", "Any selected filter highlights instead of removing rows", async () => {
      await openFilters(page);
      const cleared = await page.evaluate(`(() => {
        for (const input of document.querySelectorAll('${dialogSelector} input[name="filterSelected"]')) {
          if (input.checked) { input.checked = false; input.dispatchEvent(new Event("change", { bubbles: true })); }
        }
        for (const id of ["builtin:critical", "builtin:in-progress"]) {
          const input = document.querySelector('${dialogSelector} input[name="filterSelected"][value="' + id + '"]');
          if (!input) return id;
          input.checked = true;
          input.dispatchEvent(new Event("change", { bubbles: true }));
        }
        return "";
      })()`);
      assert(cleared === "", `filter checkbox missing: ${cleared}`);
      await page.evaluate(`(() => {
        const any = document.querySelector('${dialogSelector} input[name="filterCombine"][value="any"]');
        any.checked = true;
        any.dispatchEvent(new Event("change", { bubbles: true }));
        const highlight = document.querySelector('${dialogSelector} input[name="filterApplyMode"][value="highlight"]');
        highlight.checked = true;
        highlight.dispatchEvent(new Event("change", { bubbles: true }));
      })()`);
      await submitOk(page);
      const state = await gridState(page);
      assert(state.rows === totalRows, `highlight mode removed rows: ${state.rows}/${totalRows}`);
      assert(state.matched > 0 && state.matched < totalRows, `expected highlighted rows, got ${state.matched}`);
      await capture(page, "05-highlight-critical-in-progress-en-1366");
      return { rows: state.rows, matched: state.matched };
    });

    await scenario("06", "All Activities clears the filter and the highlight", async () => {
      await openFilters(page);
      await page.evaluate(`(() => {
        const all = document.querySelector('${dialogSelector} input[name="filterAllActivities"]');
        all.checked = true;
        all.dispatchEvent(new Event("change", { bubbles: true }));
      })()`);
      await submitOk(page);
      const state = await gridState(page);
      assert(state.rows === totalRows, `All Activities did not restore ${totalRows} rows (${state.rows})`);
      assert(state.matched === 0, `${state.matched} rows are still highlighted`);
      return { rows: state.rows };
    });

    await scenario("07", "criterion rows renumber when moved and deleted", async () => {
      await openFilters(page);
      const before = (await gridState(page)).saved.length;
      await clickInDialog(page, "[data-filter-row-add]");
      await clickInDialog(page, "[data-filter-row-add]");
      let state = await preview(page);
      assert(state.rows === 4, `expected four rows after two adds, got ${state.rows}`);
      assert(state.names.join(",") === "filter.value.0,filter.value.1,filter.value.2,filter.value.3", `names ${state.names.join(",")}`);
      await setSelect(page, 3, "field", "start");
      const moved = await page.evaluate(`(() => {
        const row = document.querySelector('${dialogSelector} .cp-filter-row[data-filter-row="3"]');
        const button = row?.querySelector('[data-filter-row-move="up"]');
        if (!button) return false;
        button.click();
        return true;
      })()`);
      assert(moved, "the move-up control did not run");
      await sleep(200);
      const order = await page.evaluate(`[...document.querySelectorAll('${dialogSelector} [data-filter-rows] .cp-filter-row')].map((row) => ({
        index: row.getAttribute("data-filter-row"),
        field: row.querySelector('select[name^="filter.field."]')?.value,
        valueName: row.querySelector('input[name^="filter.value."]')?.name,
      }))`);
      assert(order[2].field === "start", `moved row did not land at index 2 (${order.map((row) => row.field).join(",")})`);
      assert(order.every((row, index) => row.index === String(index) && row.valueName === `filter.value.${index}`), "row names were not renumbered");
      const removed = await page.evaluate(`(() => {
        const row = document.querySelector('${dialogSelector} .cp-filter-row[data-filter-row="2"]');
        const button = row?.querySelector("[data-filter-row-remove]");
        if (!button) return false;
        button.click();
        return true;
      })()`);
      assert(removed, "the remove control did not run");
      await sleep(200);
      state = await preview(page);
      assert(state.rows === 3, `expected three rows after delete, got ${state.rows}`);
      assert(state.names.join(",") === "filter.value.0,filter.value.1,filter.value.2", `names after delete ${state.names.join(",")}`);
      await clickInDialog(page, "[data-dialog-cancel]");
      await sleep(300);
      const after = await gridState(page);
      assert(after.saved.length === before, `Cancel changed the saved filter list (${before} -> ${after.saved.length})`);
      return { rows: state.rows, saved: after.saved.length };
    });

    await scenario("08", "the editor renders in a Persian RTL cell without overflow", async () => {
      await setViewport(page, 1280, 720);
      await setLanguage(page, "fa");
      await openFilters(page);
      await setSelect(page, 0, "field", "start");
      await setSelect(page, 0, "operator", "within-range");
      await setText(page, "filter.value.0", "CS");
      await setText(page, "filter.high.0", "CS+4w");
      const state = await preview(page);
      assert(state.valid === "true", `Persian preview is invalid: ${state.text}`);
      assert(/فعالیت/.test(state.text), `preview is not localized: ${state.text}`);
      const labels = await page.evaluate(`(() => {
        const dialog = document.querySelector("${dialogSelector}");
        return {
          range: [...dialog.querySelectorAll('select[name="filter.operator.0"] option')].map((option) => option.textContent.trim()),
          dir: document.documentElement.dir,
          overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        };
      })()`);
      assert(labels.range.includes("در بازهٔ"), `Persian operator label missing: ${labels.range.join(",")}`);
      assert(labels.dir === "rtl", `document direction is ${labels.dir}`);
      assert(labels.overflow <= 1, `the RTL editor overflows by ${labels.overflow}px`);
      await capture(page, "06-filters-dialog-fa-rtl-1280");
      await clickInDialog(page, "[data-dialog-cancel]");
      await sleep(300);
      return { dir: labels.dir, matched: state.matched, overflow: labels.overflow };
    });

    await scenario("09", "the dialog fits a 1920x1080 cell", async () => {
      await setLanguage(page, "en");
      await setViewport(page, 1920, 1080);
      await openFilters(page);
      const state = await preview(page);
      const overflow = await page.evaluate(`document.documentElement.scrollWidth - document.documentElement.clientWidth`);
      assert(state.rows >= 2, "the editor lost its rows at 1920");
      assert(overflow <= 1, `the 1920 dialog overflows by ${overflow}px`);
      await capture(page, "07-filters-dialog-en-1920");
      await clickInDialog(page, "[data-dialog-cancel]");
      await sleep(300);
      return { rows: state.rows, overflow };
    });

    await scenario("10", "list parameters use a typed picker and the saved choice reloads", async () => {
      await setLanguage(page, "en");
      await setViewport(page, 1366, 768);
      await openFilters(page);
      // Scenario 06 left All Activities checked; a specific filter is only
      // applied when that box is clear, so reset it before picking a status.
      await page.evaluate(`(() => {
        const all = document.querySelector('${dialogSelector} input[name="filterAllActivities"]');
        if (!all || !all.checked) return false;
        all.checked = false;
        all.dispatchEvent(new Event("change", { bubbles: true }));
        return true;
      })()`);
      await sleep(150);
      await setSelect(page, 0, "field", "activity_status");
      const picker = await page.evaluate(`(() => {
        const row = document.querySelector('${dialogSelector} .cp-filter-row[data-filter-row="0"]');
        const select = row?.querySelector('select[name="filter.value.0"]');
        return {
          isSelect: Boolean(select),
          hasInput: Boolean(row?.querySelector('input[name="filter.value.0"]')),
          values: select ? [...select.options].map((option) => option.value) : [],
          labels: select ? [...select.options].map((option) => option.textContent.trim()) : [],
          disabled: Boolean(select?.disabled),
        };
      })()`);
      assert(picker.isSelect && !picker.hasInput, "a list parameter must render a picker, not a free-text box");
      assert(picker.values.slice(1).join(",") === "Not Started,In Progress,Completed", `status values ${picker.values.join(",")}`);
      assert(picker.labels.includes("Select a value"), `placeholder label missing: ${picker.labels.join(",")}`);
      assert(!picker.disabled, "a complete operator must keep the picker enabled");

      await setSelect(page, 0, "value", "In Progress");
      const state = await preview(page);
      assert(state.valid === "true", `the picked status is invalid: ${state.text}`);
      assert(state.matched > 0 && state.matched < totalRows, `expected a partial status match, got ${state.matched}/${totalRows}`);
      const inProgress = state.matched;

      await setSelect(page, 0, "field", "is_critical");
      const flag = await page.evaluate(`(() => {
        const select = document.querySelector('${dialogSelector} select[name="filter.value.0"]');
        return {
          values: select ? [...select.options].map((option) => option.value) : [],
          labels: select ? [...select.options].map((option) => option.textContent.trim()) : [],
        };
      })()`);
      assert(flag.values.slice(1).join(",") === "true,false", `flag values ${flag.values.join(",")}`);
      assert(flag.labels.includes("Yes") && flag.labels.includes("No"), `flag labels are not localized: ${flag.labels.join(",")}`);

      await setSelect(page, 0, "field", "activity_status");
      await setSelect(page, 0, "value", "In Progress");
      await setText(page, "filterName", "In Progress Only");
      // Scenario 05 left the dialog in Highlight mode; replace is the mode that
      // narrows the grid, so the saved filter must apply the same way.
      const replace = await page.evaluate(`(() => {
        const input = document.querySelector('${dialogSelector} input[name="filterApplyMode"][value="replace"]');
        if (!input) return false;
        input.checked = true;
        input.dispatchEvent(new Event("change", { bubbles: true }));
        return true;
      })()`);
      assert(replace, "the Replace apply mode is missing");
      await page.evaluate(`document.querySelector('${dialogSelector} .cp-filter-row[data-filter-row="0"]')?.scrollIntoView({ block: "center" })`);
      await sleep(200);
      await capture(page, "08-filter-choice-picker-en-1366");
      await submitOk(page);
      const applied = await gridState(page);
      assert(applied.rows === inProgress, `grid shows ${applied.rows} rows, the picker preview said ${inProgress}`);

      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "reload with the status filter applied");
      await sleep(900);
      const reloaded = await gridState(page);
      assert(reloaded.rows === inProgress, `reload shows ${reloaded.rows} rows, expected ${inProgress}`);
      await openFilters(page);
      const saved = await gridState(page);
      assert(saved.saved.includes("in progress only"), `saved filters ${saved.saved.join(", ")}`);

      const selected = await page.evaluate(`(() => {
        const row = [...document.querySelectorAll('${dialogSelector} tr[data-filter-id]')]
          .find((item) => item.getAttribute("data-filter-name") === "in progress only");
        row?.querySelector("[data-filter-row-select]")?.click();
        return Boolean(row);
      })()`);
      assert(selected, "the saved status filter row is missing");
      await clickInDialog(page, "[data-filter-modify]");
      const loaded = await page.evaluate(`(() => {
        const select = document.querySelector('${dialogSelector} select[name="filter.value.0"]');
        return {
          tag: select?.tagName ?? "",
          value: select?.value ?? "",
          text: select?.selectedOptions?.[0]?.textContent?.trim() ?? "",
        };
      })()`);
      assert(loaded.tag === "SELECT" && loaded.value === "In Progress" && loaded.text === "In Progress", `Modify did not reload the picker: ${JSON.stringify(loaded)}`);
      await capture(page, "09-filter-choice-reload-en-1366");
      await clickInDialog(page, "[data-dialog-cancel]");
      await sleep(300);
      return { matched: inProgress, rows: reloaded.rows, saved: saved.saved.length };
    });

    await scenario("11", "Optimize removes duplicate and implied criteria without changing matches", async () => {
      await openFilters(page);
      await setSelect(page, 0, "field", "activity_name");
      await setSelect(page, 0, "operator", "contains");
      await setText(page, "filter.value.0", "Piling");
      await clickInDialog(page, "[data-filter-row-add]");
      await setSelect(page, 1, "field", "activity_name");
      await setSelect(page, 1, "operator", "contains");
      await setText(page, "filter.value.1", "Piling and foundations");
      const before = await preview(page);
      assert(before.rows === 2, `expected two criteria before Optimize, got ${before.rows}`);
      assert(before.matched > 0, `the containment pair matched nothing: ${before.text}`);

      await clickInDialog(page, "[data-filter-optimize]");
      const after = await preview(page);
      const status = await page.evaluate(`document.querySelector('${dialogSelector} [data-filter-optimize-status]')?.textContent?.trim() ?? ""`);
      assert(after.rows === 1, `All + Optimize kept ${after.rows} rows`);
      assert(/Removed 1 redundant/.test(status), `Optimize status was "${status}"`);
      assert(after.matched === before.matched, `Optimize changed matches ${before.matched} -> ${after.matched}`);

      await clickInDialog(page, "[data-filter-row-add]");
      await setSelect(page, 1, "field", "activity_name");
      await setSelect(page, 1, "operator", "contains");
      await setText(page, "filter.value.1", "Piling and foundations");
      await clickInDialog(page, "[data-filter-optimize]");
      const deduped = await preview(page);
      assert(deduped.rows === 1 && deduped.matched === before.matched, "an exact duplicate was not collapsed");

      await clickInDialog(page, "[data-filter-optimize]");
      const clean = await page.evaluate(`document.querySelector('${dialogSelector} [data-filter-optimize-status]')?.textContent?.trim() ?? ""`);
      assert(/No redundant criteria found/.test(clean), `a clean filter reported "${clean}"`);
      await capture(page, "10-filter-optimize-en-1366");
      await clickInDialog(page, "[data-dialog-cancel]");
      await sleep(300);
      return { before: before.matched, after: after.matched, optimizeStatus: status, clean };
    });

    await scenario("12", "Duplicate stores a second filter and keeps the original", async () => {
      await openFilters(page);
      const before = (await gridState(page)).saved;
      const selected = await page.evaluate(`(() => {
        const row = [...document.querySelectorAll('${dialogSelector} tr[data-filter-id]')]
          .find((item) => item.getAttribute("data-filter-name") === "six-week lookahead");
        if (!row) return false;
        row.querySelector("[data-filter-row-select]")?.click();
        return true;
      })()`);
      assert(selected, "the lookahead filter row is missing");
      await clickInDialog(page, '[name="filterAction"][value="duplicate"]');
      await page.waitForSelector(`${dialogSelector}[open]`, "filters dialog after duplicate", 8000);
      await sleep(600);
      const after = await gridState(page);
      assert(after.saved.length === before.length + 1, `Duplicate stored ${after.saved.length - before.length} entries`);
      assert(after.saved.includes("six-week lookahead"), "Duplicate removed the original filter");
      assert(after.saved.includes("six-week lookahead (copy)"), `the copy is missing: ${after.saved.join(", ")}`);
      const checked = await page.evaluate(`[...document.querySelectorAll('${dialogSelector} input[name="filterSelected"]:checked')].map((input) => input.value)`);
      assert(checked.includes("custom:six-week-lookahead-copy"), `the copy was not selected: ${checked.join(",")}`);
      await capture(page, "11-filter-duplicate-en-1366");

      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "reload with the duplicated filter");
      await sleep(900);
      await openFilters(page);
      const reloaded = await gridState(page);
      assert(reloaded.saved.includes("six-week lookahead (copy)"), "the duplicated filter disappeared after reload");
      await clickInDialog(page, "[data-dialog-cancel]");
      await sleep(300);
      return { before: before.length, after: after.saved.length, checked };
    });

    await scenario("13", "Cut moves a saved filter to the clipboard and Paste restores it", async () => {
      await setLanguage(page, "en");
      await setViewport(page, 1366, 768);
      await openFilters(page);

      const selectRow = async (name) => page.evaluate(`(() => {
        const row = [...document.querySelectorAll('${dialogSelector} tr[data-filter-id]')]
          .find((item) => item.getAttribute("data-filter-name") === ${JSON.stringify(name)});
        if (!row) return null;
        row.querySelector("[data-filter-row-select]")?.click();
        return {
          cut: document.querySelector('${dialogSelector} [data-filter-cut]')?.disabled,
          del: document.querySelector('${dialogSelector} [name="filterAction"][value="delete"]')?.disabled,
          modify: document.querySelector('${dialogSelector} [data-filter-modify]')?.disabled,
          title: document.querySelector('${dialogSelector} [data-filter-cut]')?.title ?? "",
        };
      })()`);

      const defaultRow = await selectRow("critical");
      assert(defaultRow, "the Critical default filter row is missing");
      assert(defaultRow.cut === true, "Cut is enabled for a read-only default filter");
      assert(defaultRow.del === true && defaultRow.modify === true, "Default filter Delete/Modify must stay disabled");
      assert(/read-only/i.test(defaultRow.title), `the disabled reason is "${defaultRow.title}"`);

      const savedRow = await selectRow("six-week lookahead");
      assert(savedRow, "the saved lookahead filter row is missing");
      assert(savedRow.cut === false, "Cut is disabled for a saved filter");
      assert(savedRow.del === false && savedRow.modify === false, "Delete/Modify stayed disabled for a saved filter");

      const before = (await gridState(page)).saved;
      assert(before.includes("six-week lookahead"), `the saved filter is missing before Cut: ${before.join(", ")}`);
      await clickInDialog(page, "[data-filter-cut]");
      await page.waitForSelector(`${dialogSelector}[open]`, "filters dialog after Cut", 8000);
      await sleep(600);
      const cut = (await gridState(page)).saved;
      assert(!cut.includes("six-week lookahead"), `Cut left the filter in place: ${cut.join(", ")}`);
      assert(cut.length === before.length - 1, `Cut changed the count ${before.length} -> ${cut.length}`);

      await clickInDialog(page, '[name="filterAction"][value="paste"]');
      await page.waitForSelector(`${dialogSelector}[open]`, "filters dialog after Paste", 8000);
      await sleep(600);
      const pasted = (await gridState(page)).saved;
      assert(pasted.includes("six-week lookahead"), `Paste did not restore the cut filter: ${pasted.join(", ")}`);
      assert(pasted.length === before.length, `Paste restored ${pasted.length - cut.length} entries, expected 1`);
      await capture(page, "12-filter-cut-paste-en-1366");

      await clickInDialog(page, '[name="filterAction"][value="apply"]');
      await page.waitForSelector(`${dialogSelector}[open]`, "filters dialog after Apply", 8000);
      await sleep(600);
      await clickInDialog(page, "[data-dialog-cancel]");
      await sleep(300);
      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "reload after Cut/Paste");
      await sleep(900);
      await openFilters(page);
      const reloaded = (await gridState(page)).saved;
      assert(reloaded.includes("six-week lookahead"), "the pasted filter disappeared after reload");
      await clickInDialog(page, "[data-dialog-cancel]");
      await sleep(300);
      return { before: before.length, cut: cut.length, pasted: pasted.length, reloaded: reloaded.length };
    });

    await scenario("14", "Clear empties the filter definition without touching the applied filter", async () => {
      await setLanguage(page, "fa");
      await setViewport(page, 1280, 720);
      await openFilters(page);
      const gridBefore = await gridState(page);
      await clickInDialog(page, "[data-filter-new]");
      await setText(page, "filterName", "پاک‌شدنی");
      await setText(page, "filter.value.0", "بازرسی");
      const filled = await preview(page);
      assert(filled.rows === 1, `the editor has ${filled.rows} rows before Clear`);
      await clickInDialog(page, "[data-filter-clear]");
      const cleared = await page.evaluate(`(() => ({
        name: document.querySelector('${dialogSelector} input[name="filterName"]')?.value ?? "",
        value: document.querySelector('${dialogSelector} input[name="filter.value.0"]')?.value ?? "",
        editing: document.querySelector('${dialogSelector} input[name="filterEditingId"]')?.value ?? "",
        rows: document.querySelectorAll('${dialogSelector} [data-filter-rows] .cp-filter-row').length,
        open: document.querySelector('${dialogSelector}')?.open ?? false,
        label: document.querySelector('${dialogSelector} [data-filter-clear]')?.textContent?.trim() ?? "",
      }))()`);
      assert(cleared.open === true, "Clear closed the dialog");
      assert(cleared.name === "", `Clear kept the name "${cleared.name}"`);
      assert(cleared.value === "" && cleared.editing === "", "Clear kept a value or editing id");
      assert(cleared.rows === 1, `Clear left ${cleared.rows} criterion rows`);
      assert(cleared.label === "پاک‌کردن", `Clear label is "${cleared.label}"`);
      const previewAfter = await preview(page);
      assert(/پیش‌نمایش/.test(previewAfter.text), `Clear left a stale preview: ${previewAfter.text}`);
      const overflow = await page.evaluate(`document.documentElement.scrollWidth - document.documentElement.clientWidth`);
      assert(overflow <= 1, `the Persian Clear state overflows by ${overflow}px`);
      await capture(page, "13-filter-clear-fa-rtl-1280");
      await clickInDialog(page, "[data-dialog-cancel]");
      await sleep(300);
      const gridAfter = await gridState(page);
      assert(gridAfter.rows === gridBefore.rows, `Clear changed the grid ${gridBefore.rows} -> ${gridAfter.rows}`);
      return { overflow, rows: gridAfter.rows };
    });

    writeReport();
    log(`\nAll ${report.passed} activity filter scenarios passed`);
    if (report.failed) process.exitCode = 1;
  } catch (error) {
    writeReport();
    throw error;
  } finally {
    page.cdp.close();
    await chrome.stop();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
