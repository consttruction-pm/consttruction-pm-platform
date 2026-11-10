#!/usr/bin/env node
/**
 * Browser E2E for the Version 26 Resources and Calendars windows.
 *
 * It drives the real local full-stack preview on project preview-rps-01: the
 * Resource Register must list exactly the resources that the assignment,
 * capacity and rate read contracts expose, its tabs must show the stored
 * effective-dated facts, and the Calendar Register must list the persisted
 * catalogue and read a real workweek snapshot. Expected values are fetched from
 * the same session's API, so no fixture data is injected into the page.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4186 node e2e/resources-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4174";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-10";
const outDir = join(artifactsDir, "resources-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `resources-v26-${evidenceDate}`);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
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

/** Exact decimal sum over the API strings, kept separate from the app code. */
function exactSum(values) {
  const parts = values.filter((value) => typeof value === "string" && value !== "").map((value) => {
    const negative = value.startsWith("-");
    const [whole = "0", fraction = ""] = (negative ? value.slice(1) : value).split(".");
    return { negative, whole, fraction };
  });
  if (!parts.length) return null;
  const scale = Math.max(...parts.map((part) => part.fraction.length));
  let total = 0n;
  for (const part of parts) {
    const scaled = BigInt(part.whole + part.fraction.padEnd(scale, "0"));
    total += part.negative ? -scaled : scaled;
  }
  const negative = total < 0n;
  const digits = (negative ? -total : total).toString().padStart(scale + 1, "0");
  const whole = scale ? digits.slice(0, digits.length - scale) : digits;
  const fraction = scale ? digits.slice(digits.length - scale).replace(/0+$/, "") : "";
  return `${negative ? "-" : ""}${whole}${fraction ? `.${fraction}` : ""}`;
}

const resourcesState = `(() => {
  const page = document.querySelector("[data-resources-page]");
  const rows = [...document.querySelectorAll("[data-resource-row]")].map((row) => ({
    id: row.dataset.resourceId,
    cells: [...row.querySelectorAll("td")].map((cell) => (cell.textContent || "").trim()),
    selected: row.getAttribute("aria-selected") === "true",
  }));
  const activeTab = document.querySelector('[data-resource-tab][aria-selected="true"]')?.dataset.resourceTab ?? null;
  const fields = [...document.querySelectorAll('[data-resource-panel="general"] .cp-calendar-fields label')].map((label) => ({
    label: (label.childNodes[0]?.textContent ?? "").trim(),
    value: label.querySelector("input")?.value ?? null,
  }));
  const table = (panel) => [...document.querySelectorAll('[data-resource-panel="' + panel + '"] tbody tr')].map((row) => [...row.querySelectorAll("td")].map((cell) => (cell.textContent || "").trim()));
  return {
    activeMenu: document.querySelector(".cp-workspace")?.dataset.activeMenu ?? null,
    heading: page?.querySelector(".cp-calendar-window-toolbar strong")?.textContent?.trim() ?? null,
    rows,
    count: page?.querySelector(".cp-calendar-register .cp-calendar-section-head span")?.textContent?.trim() ?? null,
    detailsCaption: page?.querySelector(".cp-calendar-editor .cp-calendar-section-head span")?.textContent?.trim() ?? null,
    activeTab,
    fields,
    hint: page?.querySelector(".cp-calendar-hint")?.textContent?.replace(/\\s+/g, " ").trim() ?? null,
    panels: { assignments: table("assignments"), capacity: table("capacity"), rates: table("rates") },
    empty: page?.querySelector(".cp-calendar-empty")?.textContent?.trim() ?? null,
    refreshDisabled: Boolean(page?.querySelector("[data-resource-action=reload]")?.disabled),
  };
})()`;

const calendarsState = `(() => {
  const page = document.querySelector("[data-calendar-page]");
  const rows = [...document.querySelectorAll("[data-calendar-row]")].map((row) => ({
    id: row.dataset.calendarId,
    version: row.dataset.calendarVersion,
    cells: [...row.querySelectorAll("td")].map((cell) => (cell.textContent || "").trim()),
    selected: row.getAttribute("aria-selected") === "true",
  }));
  const activeTab = document.querySelector('[data-calendar-tab][aria-selected="true"]')?.dataset.calendarTab ?? null;
  const generalFields = [...document.querySelectorAll('[data-calendar-panel="general"] .cp-calendar-fields label')].map((label) => ({
    label: (label.childNodes[0]?.textContent ?? "").trim(),
    value: label.querySelector("input")?.value ?? label.querySelector("select")?.value ?? null,
  }));
  const workweek = [...document.querySelectorAll('[data-calendar-panel="workweek"] tbody tr')].map((row) => [...row.querySelectorAll("th,td")].map((cell) => (cell.textContent || "").trim()));
  return {
    activeMenu: document.querySelector(".cp-workspace")?.dataset.activeMenu ?? null,
    heading: page?.querySelector(".cp-calendar-window-toolbar strong")?.textContent?.trim() ?? null,
    rows,
    count: page?.querySelector(".cp-calendar-register .cp-calendar-section-head span")?.textContent?.trim() ?? null,
    activeTab,
    generalFields,
    workweek,
    empty: page?.querySelector(".cp-calendar-empty")?.textContent?.trim() ?? null,
  };
})()`;

async function capture(page, name) {
  const file = `resources-v26/${name}.png`;
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
  await sleep(900);
}

async function openMenu(page, key, selector, label) {
  const clicked = await page.evaluate(`(() => {
    const buttons = [...document.querySelectorAll('[data-menu="${key}"]')];
    const button = buttons.find((entry) => entry.getClientRects().length > 0) ?? buttons[0];
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `${key} menu button is missing`);
  await page.waitForSelector(selector, label, 20000);
  await sleep(500);
}

async function readApi(page) {
  return page.evaluate(`(async () => {
    const base = "/api/projects/preview-rps-01/p6/";
    const [assignments, capacities, rates, calendars] = await Promise.all([
      fetch(base + "resource-assignments").then((response) => response.json()),
      fetch(base + "resource-capacities").then((response) => response.json()),
      fetch(base + "resource-rates").then((response) => response.json()),
      fetch(base + "calendars").then((response) => response.json()),
    ]);
    return {
      assignments: assignments.assignments ?? [],
      capacities: capacities.capacities ?? [],
      rates: rates.rates ?? [],
      calendars: calendars.calendars ?? [],
    };
  })()`, { awaitPromise: true });
}

async function readCalendarSnapshot(page, calendarId, calendarVersion) {
  return page.evaluate(`(async () => {
    const response = await fetch("/api/projects/preview-rps-01/p6/calendars/" + encodeURIComponent(${JSON.stringify(calendarId)}) + "/" + encodeURIComponent(${JSON.stringify(calendarVersion)}) + "/snapshot");
    return response.json();
  })()`, { awaitPromise: true });
}

function field(state, label) {
  return state.fields.find((entry) => entry.label === label)?.value ?? null;
}

function calendarField(state, label) {
  return state.generalFields.find((entry) => entry.label === label)?.value ?? null;
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
    contract: "cubi-resources-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    capturedAt: new Date().toISOString(),
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
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

    const api = await readApi(page);
    const crewAssignments = api.assignments.filter((item) => item.assignment?.resource_id === "RPS-CIVIL-CREW").map((item) => item.assignment);
    const crewCapacity = api.capacities.filter((item) => item.capacity?.resource_id === "RPS-CIVIL-CREW").map((item) => item.capacity);
    const crewRates = api.rates.filter((item) => item.resource_id === "RPS-CIVIL-CREW");
    assert(crewCapacity.length === 2, `the RPS crew should have two capacity segments, got ${crewCapacity.length}`);
    assert(crewRates.length === 2, `the RPS crew should have two rate facts, got ${crewRates.length}`);
    const expectedIds = [...new Set([
      ...api.assignments.map((item) => item.assignment?.resource_id),
      ...api.capacities.map((item) => item.capacity?.resource_id),
      ...api.rates.map((item) => item.resource_id),
    ].filter(Boolean))].sort();

    await openMenu(page, "resources", "[data-resources-page] [data-resource-row]", "resource register");

    await scenario("01", "پنجرهٔ Resources دقیقاً منابعی را نشان می‌دهد که قراردادهای تخصیص، ظرفیت و نرخ برمی‌گردانند", async () => {
      const state = await page.evaluate(resourcesState);
      assert(state.activeMenu === "resources", `active menu is ${state.activeMenu}`);
      assert(state.heading === "Resource Register", `window heading is ${state.heading}`);
      assert(state.rows.length === expectedIds.length, `register rows ${state.rows.length} vs API ${expectedIds.length}`);
      assert(JSON.stringify(state.rows.map((row) => row.id).sort()) === JSON.stringify(expectedIds), `register ids ${state.rows.map((row) => row.id)} vs API ${expectedIds}`);
      assert(state.count === String(expectedIds.length), `register counter shows ${state.count}`);
      const crew = state.rows.find((row) => row.id === "RPS-CIVIL-CREW");
      assert(crew, "the RPS crew row is missing");
      assert(crew.cells[1] === String(crewAssignments.length), `assignment count ${crew.cells[1]} vs API ${crewAssignments.length}`);
      assert(crew.cells[5] === "12", `latest max units ${crew.cells[5]} instead of the stored 12`);
      assert(crew.cells[6] === String(crewRates.length), `rate count ${crew.cells[6]} vs API ${crewRates.length}`);
      const expectedUnits = exactSum(crewAssignments.map((item) => item.units));
      assert(crew.cells[2] === (expectedUnits ?? "—"), `budgeted units ${crew.cells[2]} vs API ${expectedUnits}`);
      await capture(page, "01-resource-register");
      return { rows: state.rows.map((row) => row.id), assignments: crewAssignments.length, latestMaxUnits: crew.cells[5] };
    });

    await scenario("02", "تب General حقایق ذخیره‌شده را نشان می‌دهد و مرز رکورد مستر منبع را اعلام می‌کند", async () => {
      await page.click('[data-resource-row][data-resource-id="RPS-CIVIL-CREW"]');
      await page.waitForSelector('[data-resource-panel="general"]', "resource general tab");
      await sleep(300);
      const state = await page.evaluate(resourcesState);
      assert(state.activeTab === "general", `active tab is ${state.activeTab}`);
      assert(field(state, "Resource ID") === "RPS-CIVIL-CREW", `Resource ID field ${field(state, "Resource ID")}`);
      assert(field(state, "Latest Max Units") === "12", `Latest Max Units field ${field(state, "Latest Max Units")}`);
      assert(field(state, "Capacity Effective From") === "2026-10-15", `capacity effective date ${field(state, "Capacity Effective From")}`);
      assert(field(state, "Assignments") === String(crewAssignments.length), `assignments field ${field(state, "Assignments")}`);
      assert(/no resource master record/.test(state.hint ?? ""), "the General tab does not state the resource master-record boundary");
      assert(/\bUSD\b/.test(field(state, "Currencies") ?? "") || crewAssignments.length === 0, `Currencies field ${field(state, "Currencies")}`);
      await capture(page, "02-resource-general");
      return { fields: state.fields, hint: state.hint };
    });

    await scenario("03", "تب Capacity هر دو بازه ظرفیت مؤثر-تاریخ‌دار ذخیره‌شده را نشان می‌دهد", async () => {
      await page.click('[data-resource-tab="capacity"]');
      await page.waitForSelector('[data-resource-panel="capacity"] tbody tr', "capacity rows");
      await sleep(250);
      const state = await page.evaluate(resourcesState);
      assert(state.activeTab === "capacity", `active tab is ${state.activeTab}`);
      assert(state.panels.capacity.length === 2, `capacity rows ${state.panels.capacity.length}`);
      assert(JSON.stringify(state.panels.capacity[0]) === JSON.stringify(["8", "day", "8", "1", "2026-09-21", "2026-10-14"]), `first capacity segment is ${state.panels.capacity[0]}`);
      assert(JSON.stringify(state.panels.capacity[1]) === JSON.stringify(["12", "day", "8", "1.5", "2026-10-15", "Open-ended"]), `second capacity segment is ${state.panels.capacity[1]}`);
      await capture(page, "03-resource-capacity");
      return { segments: state.panels.capacity };
    });

    await scenario("04", "تب Rates هر دو نرخ مؤثر-تاریخ‌دار ذخیره‌شده را نشان می‌دهد", async () => {
      await page.click('[data-resource-tab="rates"]');
      await page.waitForSelector('[data-resource-panel="rates"] tbody tr', "rate rows");
      await sleep(250);
      const state = await page.evaluate(resourcesState);
      assert(state.activeTab === "rates", `active tab is ${state.activeTab}`);
      assert(state.panels.rates.length === 2, `rate rows ${state.panels.rates.length}`);
      assert(JSON.stringify(state.panels.rates[0]) === JSON.stringify(["480", "per_day", "USD", "crew-day", "2026-09-21", "2026-10-14"]), `first rate is ${state.panels.rates[0]}`);
      assert(JSON.stringify(state.panels.rates[1]) === JSON.stringify(["525", "per_day", "USD", "crew-day", "2026-10-15", "Open-ended"]), `second rate is ${state.panels.rates[1]}`);
      await capture(page, "04-resource-rates");
      return { rates: state.panels.rates };
    });

    await scenario("05", "تب Assignments همان تخصیص‌های ذخیره‌شده را نشان می‌دهد و Refresh ثبت را دوباره از سرور می‌خواند", async () => {
      await page.click('[data-resource-tab="assignments"]');
      await sleep(250);
      let state = await page.evaluate(resourcesState);
      assert(state.activeTab === "assignments", `active tab is ${state.activeTab}`);
      if (crewAssignments.length) {
        assert(state.panels.assignments.length === crewAssignments.length, `assignment rows ${state.panels.assignments.length} vs API ${crewAssignments.length}`);
        const apiIds = [...crewAssignments.map((item) => item.assignment_id)].sort();
        const shownIds = [...state.panels.assignments.map((row) => row[0])].sort();
        assert(JSON.stringify(shownIds) === JSON.stringify(apiIds), `assignment ids ${shownIds} vs API ${apiIds}`);
      } else {
        assert(/No assignment is stored/.test(state.empty ?? ""), "the Assignments tab does not state that no assignment is stored");
      }
      await page.click("[data-resource-action=reload]");
      await page.waitForSelector('[data-resources-page] [data-resource-row]', "register after refresh", 20000);
      await sleep(500);
      state = await page.evaluate(resourcesState);
      assert(state.rows.length === expectedIds.length, `register after refresh has ${state.rows.length} rows`);
      assert(!state.refreshDisabled, "the Refresh button stayed disabled after the read finished");
      await capture(page, "05-resource-assignments-refreshed");
      return { assignments: state.panels.assignments.length, rowsAfterRefresh: state.rows.length };
    });

    await openMenu(page, "calendars", "[data-calendar-row]", "calendar register");

    await scenario("06", "پنجرهٔ Calendars فهرست ذخیره‌شده را نشان می‌دهد و هفتهٔ کاری را از نسخهٔ واقعی تقویم می‌خواند", async () => {
      let state = await page.evaluate(calendarsState);
      assert(state.activeMenu === "calendars", `active menu is ${state.activeMenu}`);
      assert(state.heading === "Calendar Register", `window heading is ${state.heading}`);
      const expected = api.calendars.map((item) => `${item.calendar_id}/${item.calendar_version}`).sort();
      const shown = state.rows.map((row) => `${row.id}/${row.version}`).sort();
      assert(JSON.stringify(shown) === JSON.stringify(expected), `calendar rows ${shown} vs API ${expected}`);
      assert(shown.includes("CUBI-RPS-CAL/1"), `the persisted RPS calendar is missing from ${shown}`);
      await capture(page, "06-calendar-register");

      await page.click('[data-calendar-row][data-calendar-id="CUBI-RPS-CAL"]');
      await page.waitForSelector('[data-calendar-panel="general"]', "calendar general tab", 20000);
      await sleep(400);
      state = await page.evaluate(calendarsState);
      assert(state.activeTab === "general", `active calendar tab is ${state.activeTab}`);
      const selected = state.rows.find((row) => row.selected);
      assert(selected?.id === "CUBI-RPS-CAL", `selected calendar row is ${selected?.id}`);
      assert(calendarField(state, "Calendar ID") === "CUBI-RPS-CAL", `Calendar ID field ${calendarField(state, "Calendar ID")}`);
      const snapshot = await readCalendarSnapshot(page, "CUBI-RPS-CAL", "1");
      const snapshotBody = snapshot.snapshot ?? {};
      assert(calendarField(state, "Date System") === String(snapshotBody.system ?? "—"), `Date System field ${calendarField(state, "Date System")} vs snapshot ${snapshotBody.system}`);
      assert(calendarField(state, "Hours per Day") !== "Not provided", "the calendar snapshot factors were not shown");

      await page.click('[data-calendar-tab="workweek"]');
      await page.waitForSelector('[data-calendar-panel="workweek"] tbody tr', "workweek rows");
      await sleep(250);
      state = await page.evaluate(calendarsState);
      assert(state.activeTab === "workweek", `active calendar tab is ${state.activeTab}`);
      assert(state.workweek.length === 7, `workweek has ${state.workweek.length} rows`);
      const byDay = new Map(state.workweek.map((row) => [row[0], row[1]]));
      for (const day of ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]) {
        assert(byDay.get(day) === "Working", `${day} is ${byDay.get(day)} but the stored calendar works that day`);
      }
      for (const day of ["Saturday", "Sunday"]) {
        assert(byDay.get(day) === "Non-working", `${day} is ${byDay.get(day)} but the stored calendar does not work that day`);
      }
      await capture(page, "07-calendar-workweek");
      assert(exceptions.length === 0, `uncaught page exceptions: ${JSON.stringify(exceptions.slice(0, 3))}`);
      assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors.slice(0, 3))}`);
      assert(apiFailures.length === 0, `API 5xx responses: ${JSON.stringify(apiFailures.slice(0, 3))}`);
      return { calendars: shown, workweek: state.workweek, snapshotSystem: snapshotBody.system };
    });
  } finally {
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(outDir, "resources-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(evidenceDir, "resources-v26.json"), JSON.stringify(report, null, 2));
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
