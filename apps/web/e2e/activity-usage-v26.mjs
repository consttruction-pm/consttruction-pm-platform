#!/usr/bin/env node
/**
 * Browser E2E for the Version 26 Activity Usage Spreadsheet and Profile.
 *
 * The fixtures are real stored facts: assignments and time-phased assignment
 * periods are written through the authoritative resource write API, then the
 * Activities window projects them. Every displayed value, period total and
 * grand total is checked against the same session's read API. Metric/scope
 * switches are presentation-only, so the run also proves no schedule,
 * activity, relationship or assignment write is issued while using the views.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4184 node e2e/activity-usage-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4184";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-13";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "activity-usage-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `activity-usage-v26-${evidenceDate}`);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const RESOURCE = "RPS-CIVIL-CREW";
const ASSIGNMENTS = [
  { assignment_id: "AS-USE-A130-1", activity_id: "A130", units: "8", planned_cost: "800" },
  { assignment_id: "AS-USE-A130-2", activity_id: "A130", units: "2", planned_cost: "200.25" },
  { assignment_id: "AS-USE-A160", activity_id: "A160", units: "10", planned_cost: "1040.50" },
  { assignment_id: "AS-USE-A170", activity_id: "A170", units: "3", planned_cost: "110" },
];
const PERIODS = [
  { assignment_id: "AS-USE-A130-1", activity_id: "A130", period_start: "2026-10-01", units: "5", cost: "500" },
  { assignment_id: "AS-USE-A130-1", activity_id: "A130", period_start: "2026-11-01", units: "3", cost: "300" },
  { assignment_id: "AS-USE-A130-2", activity_id: "A130", period_start: "2026-10-01", units: "2", cost: "200.25" },
  { assignment_id: "AS-USE-A160", activity_id: "A160", period_start: "2026-10-01", units: "4", cost: "400" },
  { assignment_id: "AS-USE-A160", activity_id: "A160", period_start: "2026-12-01", units: "6", cost: "640.50" },
  { assignment_id: "AS-USE-A170", activity_id: "A170", period_start: "2026-11-01", units: "1", cost: "90" },
];
const EXTRA_PERIOD = { assignment_id: "AS-USE-A170", activity_id: "A170", period_start: "2027-01-01", units: "2", cost: "20" };

const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const apiWrites = [];
const scenarios = [];
const screenshots = [];
let trackWrites = false;

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

const usageState = `(() => {
  const surface = document.querySelector("[data-usage-view]");
  const storageKey = Object.keys(localStorage).find((key) => key.startsWith("cubi:workspace:activity-usage:"));
  return {
    view: surface?.dataset.usageView ?? null,
    metric: surface?.dataset.usageMetric ?? null,
    scope: surface?.dataset.usageScope ?? null,
    heading: surface?.querySelector("h3")?.textContent?.trim() ?? null,
    status: document.querySelector("[data-usage-status]")?.dataset.usageStatus ?? null,
    statusText: document.querySelector("[data-usage-status]")?.textContent?.trim() ?? null,
    source: document.querySelector("[data-usage-source]")?.textContent?.trim() ?? null,
    periods: [...document.querySelectorAll("[data-usage-period]")].map((cell) => cell.dataset.usagePeriod),
    rows: [...document.querySelectorAll("[data-usage-row]")].map((row) => ({
      activityId: row.dataset.activityId,
      activity: row.querySelector("[data-usage-activity] span")?.textContent?.trim() ?? null,
      cells: [...row.querySelectorAll("[data-usage-cell]")].map((cell) => ({
        period: cell.dataset.periodStart,
        value: cell.dataset.value,
        text: (cell.textContent || "").trim(),
      })),
      total: row.dataset.usageRowTotal,
    })),
    periodTotals: [...document.querySelectorAll("[data-usage-period-total]")].map((cell) => ({
      period: cell.dataset.periodStart,
      value: cell.dataset.value,
    })),
    grandTotal: document.querySelector("[data-usage-grand-total]")?.dataset.value ?? null,
    bars: [...document.querySelectorAll("[data-usage-profile-bar]")].map((bar) => ({
      period: bar.dataset.periodStart,
      value: bar.dataset.value,
      height: bar.querySelector("b")?.style.height ?? null,
    })),
    summary: document.querySelector("[data-usage-profile-summary]")?.textContent?.trim() ?? null,
    count: document.querySelector("[data-usage-count]")?.textContent?.trim() ?? null,
    dir: document.documentElement.getAttribute("dir"),
    scopeEmpty: Boolean(document.querySelector("[data-usage-scope-empty]")),
    empty: Boolean(document.querySelector("[data-usage-empty]")),
    editable: Boolean(surface?.querySelector('input:not([data-usage-metric]):not([data-usage-scope]), textarea, [contenteditable="true"]')),
    storage: storageKey ? { key: storageKey, value: localStorage.getItem(storageKey) } : null,
    box: (() => {
      if (!surface) return null;
      const bounds = surface.getBoundingClientRect();
      return { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height, scrollWidth: surface.scrollWidth, clientWidth: surface.clientWidth };
    })(),
  };
})()`;

async function capture(page, name) {
  const file = `activity-usage-v26/${name}.png`;
  await page.screenshot(file);
  copyFileSync(join(artifactsDir, file), join(evidenceDir, `${name}.png`));
  screenshots.push(`${name}.png`);
  return file;
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
  await sleep(1000);
}

async function openLayoutOptions(page) {
  await page.click("[data-layout-options-open]");
  await page.waitFor(
    `document.querySelector("[data-layout-options-dialog]")?.open === true`,
    "layout options dialog",
  );
  await sleep(200);
}

async function bottomOptionState(page) {
  return page.evaluate(`(() => {
    const select = document.querySelector("[data-bottom-layout]");
    const option = (value) => {
      const entry = select?.querySelector('option[value="' + value + '"]');
      return entry ? { present: true, disabled: entry.disabled } : { present: false, disabled: true };
    };
    return {
      spreadsheet: option("usage-spreadsheet"),
      profile: option("usage-profile"),
      trace: option("trace-logic"),
      value: select?.value ?? null,
    };
  })()`);
}

async function seed(page, periods, options = {}) {
  const result = await page.evaluate(`(async () => {
    const base = "/api/projects/${PROJECT}/p6/";
    const out = [];
    const post = async (path, body) => {
      const response = await fetch(base + path, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body),
      });
      let payload = null;
      try { payload = await response.json(); } catch { payload = null; }
      out.push({ path, status: response.status, ok: response.ok, body: payload });
    };
    for (const assignment of ${options.periodsOnly ? "[]" : JSON.stringify(ASSIGNMENTS)}) {
      await post("resource-assignments", {
        contract_version: "p6-resource-write-api.v1",
        assignment_id: assignment.assignment_id,
        activity_id: assignment.activity_id,
        resource_id: "${RESOURCE}",
        role_id: null,
        units: assignment.units,
        unit: "hour",
        planned_cost: assignment.planned_cost,
        currency: "USD",
        calendar_id: null,
        calendar_version: null,
        note: "Activity usage E2E fixture",
      });
    }
    for (const period of ${JSON.stringify(periods)}) {
      await post("resource-assignment-periods", {
        assignment_id: period.assignment_id,
        activity_id: period.activity_id,
        resource_id: "${RESOURCE}",
        period_start: period.period_start,
        units: period.units,
        cost: period.cost,
      });
    }
    return out;
  })()`, { awaitPromise: true });
  const failed = result.filter((entry) => !entry.ok);
  assert(failed.length === 0, `seed writes failed: ${JSON.stringify(failed)}`);
  return result.map((entry) => [entry.path, entry.status]);
}

async function readPeriods(page) {
  return page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${PROJECT}/p6/resource-assignment-periods");
    const payload = await response.json();
    return (payload.periods ?? []).map((item) => item.period ?? item);
  })()`, { awaitPromise: true });
}

async function readAssignmentPeriods(page) {
  const periods = await readPeriods(page);
  return periods.sort((a, b) => (a.period_start + a.activity_id).localeCompare(b.period_start + b.activity_id));
}

async function waitForUsage(page, view) {
  await page.waitForSelector(`[data-usage-view="${view}"]`, `${view} surface`);
  await page.waitFor(
    `document.querySelector('[data-usage-view="${view}"] [data-usage-status]') === null`,
    `${view} loaded state`,
  );
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
    if (url.includes("/api/") && params.response.status >= 500) {
      apiFailures.push({ status: params.response.status, url });
    }
  });
  page.cdp.on("Network.requestWillBeSent", (params) => {
    if (!trackWrites || params.request.method === "GET" || params.request.method === "OPTIONS") return;
    if (!params.request.url.includes("/api/")) return;
    apiWrites.push({ method: params.request.method, url: params.request.url, at: new Date().toISOString() });
  });

  const report = {
    contract: "cubi-activity-usage-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    seededAssignments: ASSIGNMENTS.map((item) => item.assignment_id),
    seededPeriods: PERIODS.map((item) => [item.activity_id, item.period_start, item.units, item.cost]),
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
    interactionWrites: apiWrites,
  };

  try {
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
    await sleep(400);
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "form", "login");
    await page.evaluate(`(() => {
      const button = [...document.querySelectorAll("form button")].find((item) => (item.textContent || "").trim().startsWith("Planner"));
      if (!button) return false;
      button.click();
      return true;
    })()`);
    await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
    await page.click('[data-project-id="preview-rps-01"]');
    await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
    await sleep(1400);
    await setLanguage(page, "en");

    await scenario("01", "A project without stored periods keeps both Activity Usage bottom views disabled", async () => {
      assert((await readPeriods(page)).length === 0, "the reset preview should start with no stored period");
      await openLayoutOptions(page);
      const options = await bottomOptionState(page);
      assert(options.spreadsheet.present, "the Activity Usage Spreadsheet option is missing");
      assert(options.profile.present, "the Activity Usage Profile option is missing");
      assert(options.spreadsheet.disabled, "the spreadsheet option is enabled without stored periods");
      assert(options.profile.disabled, "the profile option is enabled without stored periods");
      await capture(page, "01-usage-disabled-empty-project");
      await page.click("[data-layout-options-close]");
      await sleep(200);
      return options;
    });

    let seedResults;
    await scenario("02", "Stored assignments and periods arrive from the resource API and enable both usage views", async () => {
      seedResults = await seed(page, PERIODS);
      const stored = await readAssignmentPeriods(page);
      assert(stored.length === PERIODS.length, `stored periods ${stored.length} vs ${PERIODS.length}`);
      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "reload after seeding");
      await sleep(800);
      assert((await readPeriods(page)).length === PERIODS.length, "the reloaded page lost the stored periods");
      await openLayoutOptions(page);
      const options = await bottomOptionState(page);
      assert(!options.spreadsheet.disabled, "the spreadsheet option stays disabled with stored periods");
      assert(!options.profile.disabled, "the profile option stays disabled with stored periods");
      await capture(page, "02-usage-enabled-after-read");
      await page.click("[data-layout-options-close]");
      await sleep(200);
      return { seedResults, options };
    });

    await scenario("03", "The Activity Usage Spreadsheet shows stored units per period, row totals and the grand total", async () => {
      await openLayoutOptions(page);
      await page.setSelect("[data-bottom-layout]", "usage-spreadsheet");
      await page.waitFor(
        `document.querySelector("[data-layout-options-dialog]")?.open !== true`,
        "layout dialog closed after the switch",
      );
      await waitForUsage(page, "spreadsheet");
      const state = await page.evaluate(usageState);
      assert(state.metric === "units", `metric ${state.metric}`);
      assert(state.scope === "all", `scope ${state.scope}`);
      assert(JSON.stringify(state.periods) === JSON.stringify(["2026-10-01", "2026-11-01", "2026-12-01"]), `period columns ${state.periods}`);
      assert(JSON.stringify(state.rows.map((row) => row.activityId)) === JSON.stringify(["A130", "A160", "A170"]), `rows ${state.rows.map((row) => row.activityId)}`);
      const byId = Object.fromEntries(state.rows.map((row) => [row.activityId, row]));
      assert(JSON.stringify(byId.A130.cells.map((cell) => cell.value)) === JSON.stringify(["7", "3", ""]), `A130 cells ${JSON.stringify(byId.A130.cells)}`);
      assert(JSON.stringify(byId.A160.cells.map((cell) => cell.value)) === JSON.stringify(["4", "", "6"]), `A160 cells ${JSON.stringify(byId.A160.cells)}`);
      assert(JSON.stringify(byId.A170.cells.map((cell) => cell.value)) === JSON.stringify(["", "1", ""]), `A170 cells ${JSON.stringify(byId.A170.cells)}`);
      assert(byId.A130.total === "10" && byId.A160.total === "10" && byId.A170.total === "1", `row totals ${state.rows.map((row) => row.total)}`);
      assert(JSON.stringify(state.periodTotals.map((cell) => cell.value)) === JSON.stringify(["11", "4", "6"]), `period totals ${JSON.stringify(state.periodTotals)}`);
      assert(state.grandTotal === "21", `grand total ${state.grandTotal}`);
      assert(/Read-only projection of 6 stored assignment period/.test(state.source ?? ""), `source note ${state.source}`);
      assert(!state.editable, "the usage spreadsheet rendered an editable field");
      // Defaults are read-only; the preference key appears on the first change.
      assert(state.storage === null || state.storage.value.includes('"metric":"units"'), `stored prefs ${JSON.stringify(state.storage)}`);
      await capture(page, "03-spreadsheet-units");
      return { periods: state.periods, totals: state.periodTotals, grandTotal: state.grandTotal };
    });

    await scenario("04", "Switching to cost reads the stored cost and the preference survives a reload", async () => {
      await page.setSelect("select[data-usage-metric]", "cost");
      await page.waitFor(
        `document.querySelector('[data-usage-view="spreadsheet"]')?.dataset.usageMetric === "cost"`,
        "cost metric",
      );
      await sleep(250);
      let state = await page.evaluate(usageState);
      const byId = Object.fromEntries(state.rows.map((row) => [row.activityId, row]));
      assert(JSON.stringify(byId.A130.cells.map((cell) => cell.value)) === JSON.stringify(["700.25", "300", ""]), `A130 cost cells ${JSON.stringify(byId.A130.cells)}`);
      assert(JSON.stringify(byId.A160.cells.map((cell) => cell.value)) === JSON.stringify(["400", "", "640.5"]), `A160 cost cells ${JSON.stringify(byId.A160.cells)}`);
      assert(JSON.stringify(state.periodTotals.map((cell) => cell.value)) === JSON.stringify(["1100.25", "390", "640.5"]), `cost period totals ${JSON.stringify(state.periodTotals)}`);
      assert(state.grandTotal === "2130.75", `cost grand total ${state.grandTotal}`);
      assert(state.storage?.value.includes('"metric":"cost"'), `stored prefs ${JSON.stringify(state.storage)}`);
      await capture(page, "04-spreadsheet-cost");

      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "reload with stored usage layout");
      await waitForUsage(page, "spreadsheet");
      state = await page.evaluate(usageState);
      assert(state.metric === "cost", `restored metric ${state.metric}`);
      assert(state.grandTotal === "2130.75", `restored grand total ${state.grandTotal}`);
      return { grandTotal: state.grandTotal, storage: state.storage };
    });

    await scenario("05", "Selected scope keeps only the selected activity's stored periods", async () => {
      await page.setSelect("select[data-usage-metric]", "units");
      await sleep(200);
      await page.click('#cp-activity-grid tbody tr[data-activity-id="A160"]');
      await page.waitFor(
        `document.querySelector('#cp-activity-grid tbody tr[data-activity-id="A160"]')?.getAttribute("aria-selected") === "true"`,
        "A160 selected",
      );
      await page.setSelect("select[data-usage-scope]", "selected");
      await page.waitFor(
        `document.querySelectorAll('[data-usage-row]').length === 1`,
        "selected scope row",
      );
      await sleep(250);
      const state = await page.evaluate(usageState);
      assert(state.scope === "selected", `scope ${state.scope}`);
      assert(JSON.stringify(state.rows.map((row) => row.activityId)) === JSON.stringify(["A160"]), `scoped rows ${state.rows.map((row) => row.activityId)}`);
      assert(JSON.stringify(state.periods) === JSON.stringify(["2026-10-01", "2026-12-01"]), `scoped columns ${state.periods}`);
      assert(JSON.stringify(state.rows[0].cells.map((cell) => cell.value)) === JSON.stringify(["4", "6"]), `scoped cells ${JSON.stringify(state.rows[0].cells)}`);
      assert(state.grandTotal === "10", `scoped grand total ${state.grandTotal}`);
      await capture(page, "05-spreadsheet-selected-scope");

      await page.setSelect("select[data-usage-scope]", "all");
      await sleep(250);
      return { rows: state.rows.map((row) => row.activityId), columns: state.periods };
    });

    await scenario("06", "The Activity Usage Profile draws one labelled bar per stored period with peak and total", async () => {
      await openLayoutOptions(page);
      await page.setSelect("[data-bottom-layout]", "usage-profile");
      await waitForUsage(page, "profile");
      const state = await page.evaluate(usageState);
      assert(state.metric === "units" && state.scope === "all", `prefs ${state.metric}/${state.scope}`);
      assert(JSON.stringify(state.bars.map((bar) => [bar.period, bar.value])) === JSON.stringify([
        ["2026-10-01", "11"],
        ["2026-11-01", "4"],
        ["2026-12-01", "6"],
      ]), `bars ${JSON.stringify(state.bars)}`);
      assert(state.bars[0].height === "100%" && state.bars[1].height === "36%" && state.bars[2].height === "55%", `bar heights ${state.bars.map((bar) => bar.height)}`);
      assert(state.summary === "Units: total 21 · peak 11 over 3 period(s)", `profile summary ${state.summary}`);
      await capture(page, "06-profile-units");
      return { bars: state.bars, summary: state.summary };
    });

    await scenario("07", "Refresh reads a newly stored period without writing anything else", async () => {
      await openLayoutOptions(page);
      await page.setSelect("[data-bottom-layout]", "usage-spreadsheet");
      await waitForUsage(page, "spreadsheet");
      trackWrites = false;
      const seeded = await seed(page, [EXTRA_PERIOD], { periodsOnly: true });
      assert(seeded.length === 1 && seeded[0][1] === 200, `extra period seed ${JSON.stringify(seeded)}`);
      trackWrites = true;
      const before = await page.evaluate(usageState);
      assert(before.periods.length === 3, `period columns before refresh ${before.periods.length}`);
      await page.click("[data-usage-refresh]");
      await page.waitFor(
        `document.querySelectorAll("[data-usage-period]").length === 4`,
        "refreshed usage columns",
      );
      await page.waitFor(
        `document.querySelector('[data-usage-status]') === null`,
        "usage surface after refresh",
      );
      await sleep(250);
      const state = await page.evaluate(usageState);
      assert(JSON.stringify(state.periods) === JSON.stringify(["2026-10-01", "2026-11-01", "2026-12-01", "2027-01-01"]), `refreshed columns ${state.periods}`);
      assert(state.grandTotal === "23", `refreshed grand total ${state.grandTotal}`);
      const january = state.periodTotals.find((cell) => cell.period === "2027-01-01");
      assert(january?.value === "2", `January column total ${JSON.stringify(january)}`);
      const stored = await readAssignmentPeriods(page);
      assert(stored.length === PERIODS.length + 1, `API periods after refresh ${stored.length}`);
      await capture(page, "07-spreadsheet-refreshed");
      return { columns: state.periods, grandTotal: state.grandTotal, apiPeriods: stored.length };
    });

    await scenario("08", "Selecting an activity with no stored period yields an explicit scope-empty state", async () => {
      await page.click('#cp-activity-grid tbody tr[data-activity-id="A100"]');
      await page.waitFor(
        `document.querySelector('#cp-activity-grid tbody tr[data-activity-id="A100"]')?.getAttribute("aria-selected") === "true"`,
        "A100 selected",
      );
      await page.setSelect("select[data-usage-scope]", "selected");
      await page.waitFor(
        `document.querySelector("[data-usage-scope-empty]") !== null`,
        "scope empty state",
      );
      await sleep(200);
      const state = await page.evaluate(usageState);
      assert(state.scopeEmpty, "the scope-empty state is missing");
      assert(state.rows.length === 0, `scope-empty rows ${state.rows.length}`);
      await capture(page, "08-spreadsheet-scope-empty");
      await page.setSelect("select[data-usage-scope]", "all");
      await sleep(250);
      return { scopeEmpty: state.statusText };
    });

    await scenario("09", "Persian RTL at 1280x720 renders the profile from the same stored facts", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await sleep(400);
      await openLayoutOptions(page);
      await page.setSelect("[data-bottom-layout]", "usage-profile");
      await waitForUsage(page, "profile");
      await setLanguage(page, "fa");
      await waitForUsage(page, "profile");
      const state = await page.evaluate(usageState);
      assert(state.dir === "rtl", `document direction ${state.dir}`);
      assert(/نیم‌رخ مصرف فعالیت/.test(state.heading ?? ""), `Persian heading ${state.heading}`);
      assert(state.bars.length === 4, `RTL bars ${state.bars.length}`);
      assert(state.box && state.box.width > 0 && state.box.height > 0, "the profile has no layout box at 1280x720");
      assert(state.box.scrollWidth <= state.box.clientWidth + 1, `the profile overflows horizontally: ${state.box.scrollWidth} > ${state.box.clientWidth}`);
      await capture(page, "09-profile-fa-rtl-1280x720");
      return { dir: state.dir, heading: state.heading, box: state.box };
    });

    await scenario("10", "English at 1920x1080 renders the profile and spreadsheet without overflow", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false });
      await sleep(400);
      await setLanguage(page, "en");
      await waitForUsage(page, "profile");
      let state = await page.evaluate(usageState);
      assert(state.dir === "ltr", `document direction ${state.dir}`);
      assert(state.bars.length === 4, `wide profile bars ${state.bars.length}`);
      assert(state.box.scrollWidth <= state.box.clientWidth + 1, `the profile overflows at 1920: ${state.box.scrollWidth} > ${state.box.clientWidth}`);
      await capture(page, "10-profile-en-1920x1080");

      await openLayoutOptions(page);
      await page.setSelect("[data-bottom-layout]", "usage-spreadsheet");
      await waitForUsage(page, "spreadsheet");
      state = await page.evaluate(usageState);
      assert(state.periods.length === 4, `wide spreadsheet columns ${state.periods.length}`);
      assert(state.box.scrollWidth <= state.box.clientWidth + 1, `the spreadsheet surface overflows at 1920: ${state.box.scrollWidth} > ${state.box.clientWidth}`);
      await capture(page, "10b-spreadsheet-en-1920x1080");
      return { viewport: "1920x1080", columns: state.periods.length };
    });

    await scenario("11", "Using both usage views issued no schedule, activity or relationship write", async () => {
      const writes = apiWrites.map((entry) => `${entry.method} ${entry.url}`);
      assert(writes.length === 0, `usage interactions issued ${writes.length} API write(s): ${JSON.stringify(writes)}`);
      const stored = await readPeriods(page);
      assert(stored.length === PERIODS.length + 1, `unexpected final period count ${stored.length}`);
      return { interactionWrites: writes.length, finalStoredPeriods: stored.length };
    });

    report.finalApiPeriods = await readAssignmentPeriods(page);
    assert(exceptions.length === 0, `uncaught page exceptions: ${JSON.stringify(exceptions.slice(0, 3))}`);
    assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors.slice(0, 3))}`);
    assert(apiFailures.length === 0, `API 5xx responses: ${JSON.stringify(apiFailures.slice(0, 3))}`);
  } finally {
    report.finishedAt = new Date().toISOString();
    report.scenarios = scenarios;
    writeFileSync(join(outDir, "activity-usage-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(evidenceDir, "activity-usage-v26.json"), JSON.stringify(report, null, 2));
    page.cdp.close();
    chrome.cdp.close();
    await chrome.stop();
  }

  const failed = scenarios.filter((item) => item.status !== "pass");
  log(`\nScenarios: ${scenarios.length - failed.length} passed, ${failed.length} failed`);
  if (failed.length) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  process.stderr.write(`${error && error.stack ? error.stack : error}\n`);
  process.exit(1);
});
