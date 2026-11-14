#!/usr/bin/env node
/**
 * Browser E2E for the Version 26 Resources and Calendars windows.
 *
 * It drives the real local full-stack preview on project preview-rps-01. The
 * Resource Register must list every resource master stored for the project plus
 * every resource referenced only by assignment, capacity or rate facts. The
 * General tab must expose the stored master fields, the fact tabs must show the
 * stored effective-dated facts, and the Calendar Register must list the
 * persisted catalogue and read a real workweek snapshot. Creating and editing a
 * resource runs through the real POST/PATCH contracts with record revisions.
 * Expected values are fetched from the same session's API, so no fixture data is
 * injected into the page.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4183 node e2e/resources-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4174";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
// The commit under test and the commit that stores this report are different facts:
// the bundle is built from the worktree before the evidence commit exists.
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "resources-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `resources-v26-${evidenceDate}`);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const createdId = `RPS-CIVIL-CREW-E2E-${Date.now().toString(36).toUpperCase()}`;

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
  const rows = [...document.querySelectorAll("[data-resource-row]")].map((row) => {
    const cells = [...row.querySelectorAll("td")].map((cell) => (cell.textContent || "").trim());
    const tree = row.querySelector(".cp-resource-tree-cell");
    const toggle = row.querySelector("[data-resource-toggle]");
    return {
      id: row.dataset.resourceId,
      name: row.querySelector(".cp-resource-tree-label strong")?.textContent?.trim() ?? null,
      idText: row.querySelector(".cp-resource-tree-label span")?.textContent?.trim() ?? null,
      type: cells[1],
      assignments: cells[2],
      budgetedUnits: cells[3],
      plannedCost: cells[4],
      actualCost: cells[5],
      latestMaxUnits: cells[6],
      rates: cells[7],
      depth: tree ? (tree.style.paddingInlineStart || "0px") : null,
      selected: row.getAttribute("aria-selected") === "true",
      hasToggle: Boolean(toggle),
      expanded: toggle ? toggle.getAttribute("aria-expanded") === "true" : null,
    };
  });
  const activeTab = document.querySelector('[data-resource-tab][aria-selected="true"]')?.dataset.resourceTab ?? null;
  const fields = [...document.querySelectorAll('[data-resource-panel="general"] .cp-calendar-fields label')].map((label) => ({
    label: (label.childNodes[0]?.textContent ?? "").trim(),
    value: label.querySelector("input")?.value ?? null,
  }));
  const table = (panel) => [...document.querySelectorAll('[data-resource-panel="' + panel + '"] tbody tr')].map((row) => [...row.querySelectorAll("td")].map((cell) => (cell.textContent || "").trim()));
  const usageRows = [...document.querySelectorAll("[data-resource-usage-row]")].map((row) => ({
    period: row.dataset.periodStart,
    status: row.dataset.status,
    cells: [...row.querySelectorAll("td")].map((cell) => (cell.textContent || "").trim()),
  }));
  const form = document.querySelector("[data-resource-create-form], [data-resource-edit-form]");
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
    usageRows,
    usageTabLabel: page?.querySelector('[data-resource-tab="usage"]')?.textContent?.trim() ?? null,
    direction: page ? getComputedStyle(page).direction : null,
    usageSummary: page?.querySelector("[data-resource-usage-summary]")?.textContent?.replace(/\\s+/g, " ").trim() ?? null,
    usageHint: page?.querySelector("[data-resource-usage-hint]")?.textContent?.replace(/\\s+/g, " ").trim() ?? null,
    empty: page?.querySelector(".cp-calendar-empty")?.textContent?.trim() ?? null,
    filter: page?.querySelector("[data-resource-filter]")?.value ?? null,
    refreshDisabled: Boolean(page?.querySelector("[data-resource-action=reload]")?.disabled),
    notice: page?.querySelector("[data-resource-notice]")
      ? {
          kind: page.querySelector("[data-resource-notice]").dataset.state,
          text: page.querySelector("[data-resource-notice]").textContent.trim(),
        }
      : null,
    form: form ? {
      kind: form.matches("[data-resource-edit-form]") ? "edit" : "create",
      idReadonly: form.querySelector('input[readonly]')?.value ?? null,
      parentOptions: [...form.querySelectorAll('select[name="resource-parent"] option')].map((option) => option.value),
      calendarControl: form.querySelector('[name="resource-calendar"]')?.tagName?.toLowerCase() ?? null,
      calendarValue: form.querySelector('[name="resource-calendar"]')?.value ?? null,
      calendarOptions: [...form.querySelectorAll('select[name="resource-calendar"] option')].map((option) => option.value),
    } : null,
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
  const workweek = [...document.querySelectorAll('[data-calendar-panel="workweek"] tbody tr')].map((row) => {
    const cells = [...row.querySelectorAll("th,td")];
    const working = row.querySelector("input[data-workday-working]");
    return [
      (cells[0]?.textContent || "").trim(),
      working ? (working.checked ? "Working" : "Non-working") : (cells[1]?.textContent || "").trim(),
      row.querySelector("input[data-workday-hours]")?.value ?? (cells[2]?.textContent || "").trim(),
    ];
  });
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
    const base = "/api/projects/${PROJECT}/p6/";
    const [assignments, capacities, rates, calendars, resources] = await Promise.all([
      fetch(base + "resource-assignments").then((response) => response.json()),
      fetch(base + "resource-capacities").then((response) => response.json()),
      fetch(base + "resource-rates").then((response) => response.json()),
      fetch(base + "calendars").then((response) => response.json()),
      fetch(base + "resources").then((response) => response.json()),
    ]);
    return {
      assignments: assignments.assignments ?? [],
      capacities: capacities.capacities ?? [],
      rates: rates.rates ?? [],
      calendars: calendars.calendars ?? [],
      resources: resources.resources ?? [],
    };
  })()`, { awaitPromise: true });
}

async function readResource(page, resourceId) {
  return page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${PROJECT}/p6/resources/" + encodeURIComponent(${JSON.stringify(resourceId)}));
    return { status: response.status, body: await response.json() };
  })()`, { awaitPromise: true });
}

async function postResource(page, payload) {
  return page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${PROJECT}/p6/resources", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Tenant-Id": "cubi-preview-tenant",
        "X-Project-Id": ${JSON.stringify(PROJECT)},
        "X-Project-Revision": "7",
      },
      body: JSON.stringify(${JSON.stringify(payload)}),
    });
    return { status: response.status, body: await response.json() };
  })()`, { awaitPromise: true });
}

async function patchResource(page, resourceId, payload) {
  return page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${PROJECT}/p6/resources/" + encodeURIComponent(${JSON.stringify(resourceId)}), {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "X-Tenant-Id": "cubi-preview-tenant",
        "X-Project-Id": ${JSON.stringify(PROJECT)},
        "X-Project-Revision": "7",
      },
      body: JSON.stringify(${JSON.stringify(payload)}),
    });
    return { status: response.status, body: await response.json() };
  })()`, { awaitPromise: true });
}

async function postResourceFact(page, suffix, payload) {
  return page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${PROJECT}/p6/" + ${JSON.stringify(suffix)}, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Tenant-Id": "cubi-preview-tenant",
        "X-Project-Id": ${JSON.stringify(PROJECT)},
        "X-Project-Revision": "7",
      },
      body: JSON.stringify(${JSON.stringify(payload)}),
    });
    const text = await response.text();
    return { status: response.status, body: text ? JSON.parse(text) : null };
  })()`, { awaitPromise: true });
}

async function readCalendarSnapshot(page, calendarId, calendarVersion) {
  return page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${PROJECT}/p6/calendars/" + encodeURIComponent(${JSON.stringify(calendarId)}) + "/" + encodeURIComponent(${JSON.stringify(calendarVersion)}) + "/snapshot");
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
    contract: "cubi-resources-v26.v2",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    createdResourceId: createdId,
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
    const crewMaster = api.resources.map((item) => item.resource).find((item) => item?.resource_id === "RPS-CIVIL-CREW");
    assert(crewMaster, "the API did not expose the seeded RPS crew master");
    const crewCalendar = api.calendars.find((item) => item.calendar_id === crewMaster.calendar_id);
    assert(crewCalendar, `the API did not expose the calendar ${crewMaster.calendar_id} assigned to the crew`);
    assert(crewCapacity.length === 2, `the RPS crew should have two capacity segments, got ${crewCapacity.length}`);
    assert(crewRates.length === 2, `the RPS crew should have two rate facts, got ${crewRates.length}`);
    const expectedIds = [...new Set([
      ...api.resources.map((item) => item.resource?.resource_id),
      ...api.assignments.map((item) => item.assignment?.resource_id),
      ...api.capacities.map((item) => item.capacity?.resource_id),
      ...api.rates.map((item) => item.resource_id),
    ].filter(Boolean))].sort();

    await openMenu(page, "resources", "[data-resources-page] [data-resource-row]", "resource register");

    await scenario("01", "پنجرهٔ Resources منابع ذخیره‌شده و ارجاع‌داده‌شده را با نام مستر، نوع و شمارندهٔ درست نشان می‌دهد", async () => {
      const state = await page.evaluate(resourcesState);
      assert(state.activeMenu === "resources", `active menu is ${state.activeMenu}`);
      assert(state.heading === "Resource Register", `window heading is ${state.heading}`);
      assert(state.rows.length === expectedIds.length, `register rows ${state.rows.length} vs API ${expectedIds.length}`);
      assert(JSON.stringify(state.rows.map((row) => row.id).sort()) === JSON.stringify(expectedIds), `register ids ${state.rows.map((row) => row.id)} vs API ${expectedIds}`);
      assert(state.count === String(expectedIds.length), `register counter shows ${state.count}`);
      const crew = state.rows.find((row) => row.id === "RPS-CIVIL-CREW");
      assert(crew, "the RPS crew row is missing");
      assert(crew.name === crewMaster.name, `crew name ${crew.name} vs API ${crewMaster.name}`);
      assert(crew.idText === "RPS-CIVIL-CREW", `crew id text ${crew.idText}`);
      assert(crew.type === "Labor", `crew type ${crew.type}`);
      assert(crew.assignments === String(crewAssignments.length), `assignment count ${crew.assignments} vs API ${crewAssignments.length}`);
      assert(crew.latestMaxUnits === "12", `latest max units ${crew.latestMaxUnits} instead of the stored 12`);
      assert(crew.rates === String(crewRates.length), `rate count ${crew.rates} vs API ${crewRates.length}`);
      const expectedUnits = exactSum(crewAssignments.map((item) => item.units));
      assert(crew.budgetedUnits === (expectedUnits ?? "—"), `budgeted units ${crew.budgetedUnits} vs API ${expectedUnits}`);
      assert(crew.depth === "0px" || crew.depth === "", `crew tree depth ${crew.depth}`);
      assert(crew.hasToggle === false, "a top-level resource without children must not render a collapse toggle");
      await capture(page, "01-resource-register");
      return { rows: state.rows.map((row) => row.id), masterName: crew.name, latestMaxUnits: crew.latestMaxUnits };
    });

    await scenario("02", "تب General فیلدهای مستر ذخیره‌شده و تجمیع حقایق را از هم جدا نشان می‌دهد", async () => {
      await page.click('[data-resource-row][data-resource-id="RPS-CIVIL-CREW"]');
      await page.waitForSelector('[data-resource-panel="general"]', "resource general tab");
      await sleep(300);
      const state = await page.evaluate(resourcesState);
      assert(state.activeTab === "general", `active tab is ${state.activeTab}`);
      assert(field(state, "Resource ID") === "RPS-CIVIL-CREW", `Resource ID field ${field(state, "Resource ID")}`);
      assert(field(state, "Resource Name") === crewMaster.name, `Resource Name field ${field(state, "Resource Name")}`);
      assert(field(state, "Resource Type") === "Labor", `Resource Type field ${field(state, "Resource Type")}`);
      assert(field(state, "Parent Resource") === "Not provided", `Parent Resource field ${field(state, "Parent Resource")}`);
      assert(
        (field(state, "Calendar") ?? "").includes(crewMaster.calendar_id),
        `Calendar field ${field(state, "Calendar")} does not name the stored calendar ${crewMaster.calendar_id}`,
      );
      assert(
        (field(state, "Calendar") ?? "").includes(crewCalendar.name),
        `Calendar field ${field(state, "Calendar")} does not show the stored calendar name ${crewCalendar.name}`,
      );
      assert(field(state, "Unit of Measure") === crewMaster.unit_of_measure, `Unit of Measure field ${field(state, "Unit of Measure")}`);
      assert(field(state, "Record Revision") === String(crewMaster.record_revision), `Record Revision field ${field(state, "Record Revision")}`);
      assert(field(state, "Active") === "Yes", `Active field ${field(state, "Active")}`);
      assert(field(state, "Latest Max Units") === "12", `Latest Max Units field ${field(state, "Latest Max Units")}`);
      assert(field(state, "Capacity Effective From") === "2026-10-15", `capacity effective date ${field(state, "Capacity Effective From")}`);
      assert(field(state, "Assignments") === String(crewAssignments.length), `assignments field ${field(state, "Assignments")}`);
      assert(!/no resource master record is stored/i.test(state.hint ?? ""), "the General tab still reports a missing master");
      assert(/not a data-date resolution/.test(state.hint ?? ""), `the General tab hint does not state the latest-max-units boundary: ${state.hint}`);
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

    await scenario("05b", "تب Usage تقاضای ذخیره‌شده را با ظرفیت حل‌شدهٔ سرویس برای هر تاریخ مقایسه می‌کند", async () => {
      const seed = [
        ["resource-assignments", {
          contract_version: "p6-resource-write-api.v1",
          assignment_id: "RES-USAGE-E2E-1",
          activity_id: "A100",
          resource_id: "RPS-CIVIL-CREW",
          units: "12",
          unit: "crew-day",
          currency: "USD",
          units_per_time: "12",
          units_per_time_period: "day",
          hours_per_units_time_period: "8",
        }],
        ["resource-assignment-periods", {
          assignment_id: "RES-USAGE-E2E-1",
          activity_id: "A100",
          resource_id: "RPS-CIVIL-CREW",
          period_start: "2026-09-30",
          units: "12",
          cost: "960",
        }],
        ["resource-assignments", {
          contract_version: "p6-resource-write-api.v1",
          assignment_id: "RES-USAGE-E2E-2",
          activity_id: "A110",
          resource_id: "RPS-CIVIL-CREW",
          units: "4",
          unit: "crew-day",
          currency: "USD",
          units_per_time: "4",
          units_per_time_period: "day",
          hours_per_units_time_period: "8",
        }],
        ["resource-assignment-periods", {
          assignment_id: "RES-USAGE-E2E-2",
          activity_id: "A110",
          resource_id: "RPS-CIVIL-CREW",
          period_start: "2026-09-30",
          units: "4",
          cost: "320",
        }],
        ["resource-assignment-periods", {
          assignment_id: "RES-USAGE-E2E-2",
          activity_id: "A110",
          resource_id: "RPS-CIVIL-CREW",
          period_start: "2026-10-16",
          units: "4",
          cost: "320",
        }],
      ];
      for (const [suffix, payload] of seed) {
        const result = await postResourceFact(page, suffix, payload);
        assert(result.status === 200, `seed ${suffix} ${payload.assignment_id} returned ${result.status}: ${JSON.stringify(result.body)}`);
      }
      const resolved = await page.evaluate(`(async () => {
        const response = await fetch("/api/projects/${PROJECT}/p6/resource-capacities/RPS-CIVIL-CREW/resolve", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Tenant-Id": "cubi-preview-tenant", "X-Project-Id": ${JSON.stringify(PROJECT)}, "X-Project-Revision": "7" },
          body: JSON.stringify({ contract_version: "p6-resource-capacity-read-api.v1", period: "2026-09-30", basis: "day", hours_per_time_period: "8" }),
        });
        return { status: response.status, body: await response.json() };
      })()`, { awaitPromise: true });
      assert(resolved.status === 200, `capacity resolve ${resolved.status}`);
      assert(resolved.body.kind === "resource_capacity_value", `capacity kind ${resolved.body.kind}`);
      assert(resolved.body.capacity === "8", `resolved capacity ${resolved.body.capacity}`);

      await page.click("[data-resource-action=reload]");
      await page.waitForSelector('[data-resources-page] [data-resource-row]', "register after usage seed", 20000);
      await sleep(600);
      await page.click('[data-resource-row][data-resource-id="RPS-CIVIL-CREW"]');
      await sleep(200);
      await page.click('[data-resource-tab="usage"]');
      await page.waitForSelector("[data-resource-usage-row]", "usage rows", 20000);
      await sleep(400);
      const state = await page.evaluate(resourcesState);
      assert(state.activeTab === "usage", `active tab is ${state.activeTab}`);
      assert(state.usageRows.length === 2, `usage rows ${state.usageRows.length}`);
      assert(JSON.stringify(state.usageRows[0].cells) === JSON.stringify(["2026-09-30", "16", "1280", "2", "16", "day", "8", "8", "Overallocated"]), `first usage row ${JSON.stringify(state.usageRows[0].cells)}`);
      assert(state.usageRows[0].status === "overallocated", `first usage status ${state.usageRows[0].status}`);
      assert(JSON.stringify(state.usageRows[1].cells) === JSON.stringify(["2026-10-16", "4", "320", "1", "4", "day", "12", "—", "Within capacity"]), `second usage row ${JSON.stringify(state.usageRows[1].cells)}`);
      assert(state.usageRows[1].status === "within", `second usage status ${state.usageRows[1].status}`);
      assert(state.usageSummary === "2 stored period(s) · 2 compared · 1 overallocated.", `usage summary ${state.usageSummary}`);
      assert(/no scheduler or leveling pass runs here/.test(state.usageHint ?? ""), `usage hint ${state.usageHint}`);
      await capture(page, "05b-resource-usage");
      return { rows: state.usageRows.map((row) => [row.period, row.status]), summary: state.usageSummary };
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
      return { calendars: shown, workweek: state.workweek, snapshotSystem: snapshotBody.system };
    });

    const createdName = "E2E Night Shift Crew";
    const editedName = "E2E Night Shift Crew (rev 2)";
    await openMenu(page, "resources", "[data-resources-page] [data-resource-row]", "resource register");

    await scenario("07", "ایجاد منبع فرزند از فرم واقعی، ذخیره در مستر و رد بازنویسی شناسهٔ موجود", async () => {
      await page.click('[data-resource-action="new"]');
      await page.waitForSelector("[data-resource-create-form]", "resource create form");
      let state = await page.evaluate(resourcesState);
      assert(state.form?.kind === "create", `form kind ${state.form?.kind}`);
      assert(state.form.parentOptions.includes("RPS-CIVIL-CREW"), `parent options ${state.form.parentOptions}`);

      await page.setInput('[data-resource-create-form] input[name="resource-id"]', createdId);
      await page.setInput('[data-resource-create-form] input[name="resource-name"]', createdName);
      await page.setSelect('[data-resource-create-form] select[name="resource-type"]', "labor");
      await page.setSelect('[data-resource-create-form] select[name="resource-parent"]', "RPS-CIVIL-CREW");
      const createState = await page.evaluate(resourcesState);
      assert(createState.form?.calendarControl === "select", `calendar control ${createState.form?.calendarControl} instead of a stored-calendar selector`);
      assert(
        createState.form?.calendarOptions?.includes(crewMaster.calendar_id),
        `calendar options ${createState.form?.calendarOptions} do not include ${crewMaster.calendar_id}`,
      );
      await page.setSelect('[data-resource-create-form] select[name="resource-calendar"]', crewMaster.calendar_id);
      await page.setInput('[data-resource-create-form] input[name="resource-units"]', "6");
      await page.setInput('[data-resource-create-form] input[name="resource-uom"]', "crew");
      await page.setInput('[data-resource-create-form] input[name="resource-email"]', "night@example.com");
      await page.click('[data-resource-create-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-resource-notice][data-state="ok"]')?.textContent?.includes(${JSON.stringify(createdId)}) ?? false`,
        "create success notice",
      );
      await page.waitForSelector(`[data-resource-row][data-resource-id="${createdId}"]`, "created register row");
      await sleep(300);
      state = await page.evaluate(resourcesState);
      const row = state.rows.find((item) => item.id === createdId);
      assert(row, "the created resource is missing from the register");
      assert(row.name === createdName, `created row name ${row.name}`);
      assert(row.type === "Labor", `created row type ${row.type}`);
      assert(row.depth === "14px", `created row depth ${row.depth} instead of one hierarchy level`);
      assert(state.selectedId === createdId || state.detailsCaption === createdName, `details caption ${state.detailsCaption}`);
      assert(field(state, "Resource Name") === createdName, `general Resource Name ${field(state, "Resource Name")}`);
      assert(field(state, "Parent Resource") === "RPS-CIVIL-CREW", `general Parent Resource ${field(state, "Parent Resource")}`);
      assert(field(state, "Record Revision") === "1", `general Record Revision ${field(state, "Record Revision")}`);
      assert(field(state, "Default Units per Time") === "6", `general Default Units per Time ${field(state, "Default Units per Time")}`);
      const order = state.rows.map((item) => item.id);
      assert(order.indexOf(createdId) === order.indexOf("RPS-CIVIL-CREW") + 1, `child order ${order}`);

      const stored = await readResource(page, createdId);
      assert(stored.status === 200, `created resource GET status ${stored.status}`);
      assert(stored.body.resource.parent_resource_id === "RPS-CIVIL-CREW", `stored parent ${stored.body.resource.parent_resource_id}`);
      assert(stored.body.resource.record_revision === 1, `stored revision ${stored.body.resource.record_revision}`);
      assert(stored.body.resource.email === "night@example.com", `stored email ${stored.body.resource.email}`);
      assert(
        stored.body.resource.calendar_id === crewMaster.calendar_id,
        `stored calendar ${stored.body.resource.calendar_id} instead of the selected ${crewMaster.calendar_id}`,
      );

      // The selected calendar is a stored reference, so the edit form and the
      // General tab must both read it back from the persisted master.
      await page.click('[data-resource-action="edit"]');
      await page.waitForSelector("[data-resource-edit-form]", "resource edit form after reload");
      const editState = await page.evaluate(resourcesState);
      assert(editState.form?.calendarControl === "select", `edit calendar control ${editState.form?.calendarControl}`);
      assert(
        editState.form?.calendarValue === crewMaster.calendar_id,
        `edit calendar value ${editState.form?.calendarValue} instead of ${crewMaster.calendar_id}`,
      );
      await page.click('[data-resource-action="cancel"]');
      await page.waitForSelector("[data-resource-panel=\"general\"]", "general tab after cancel");

      const duplicate = await postResource(page, {
        resource_id: createdId,
        name: "Silent overwrite",
        resource_type: "labor",
      });
      assert(duplicate.status === 409, `duplicate create status ${duplicate.status}`);
      assert(duplicate.body.code === "RESOURCE_ALREADY_EXISTS", `duplicate create code ${duplicate.body.code}`);
      const afterDuplicate = await readResource(page, createdId);
      assert(afterDuplicate.body.resource.name === createdName, "a duplicate create overwrote the stored name");

      await capture(page, "08-resource-created");
      return { createdId, row, duplicateStatus: duplicate.status };
    });

    await scenario("08", "ویرایش منبع با نسخهٔ رکورد، افزایش Revision و رد PATCH با نسخهٔ کهنه", async () => {
      await page.click('[data-resource-action="edit"]');
      await page.waitForSelector("[data-resource-edit-form]", "resource edit form");
      let state = await page.evaluate(resourcesState);
      assert(state.form?.kind === "edit", `form kind ${state.form?.kind}`);
      assert(state.form.idReadonly === createdId, `edit form id ${state.form.idReadonly}`);
      assert(!state.form.parentOptions.includes(createdId), "the edit form offers the edited resource as its own parent");

      await page.setInput('[data-resource-edit-form] input[name="resource-name"]', editedName);
      await page.setInput('[data-resource-edit-form] input[name="resource-units"]', "7");
      const unchecked = await page.evaluate(`(() => {
        const input = document.querySelector('[data-resource-edit-form] input[name="resource-active"]');
        if (!input) return false;
        input.checked = false;
        input.dispatchEvent(new Event("change", { bubbles: true }));
        return true;
      })()`);
      assert(unchecked, "the active checkbox is missing from the edit form");
      await page.click('[data-resource-edit-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-resource-notice][data-state="ok"]')?.textContent?.includes(${JSON.stringify(createdId)}) ?? false`,
        "edit success notice",
      );
      await page.waitForSelector(`[data-resource-row][data-resource-id="${createdId}"]`, "edited register row");
      await page.waitForSelector('[data-resource-panel="general"]', "edited general tab");
      await sleep(400);
      state = await page.evaluate(resourcesState);
      const row = state.rows.find((item) => item.id === createdId);
      assert(row?.name === editedName, `edited row name ${row?.name}`);
      assert(field(state, "Record Revision") === "2", `Record Revision ${field(state, "Record Revision")}`);
      assert(field(state, "Active") === "No", `Active ${field(state, "Active")}`);
      assert(field(state, "Default Units per Time") === "7", `Default Units per Time ${field(state, "Default Units per Time")}`);

      const stored = await readResource(page, createdId);
      assert(stored.body.resource.record_revision === 2, `stored revision ${stored.body.resource.record_revision}`);
      assert(stored.body.resource.is_active === false, `stored active ${stored.body.resource.is_active}`);

      const stale = await patchResource(page, createdId, {
        name: "Stale write",
        resource_type: "labor",
        expected_revision: 1,
      });
      assert(stale.status === 409, `stale PATCH status ${stale.status}`);
      assert(stale.body.code === "REVISION_CONFLICT", `stale PATCH code ${stale.body.code}`);
      const afterStale = await readResource(page, createdId);
      assert(afterStale.body.resource.name === editedName, "a stale PATCH changed the stored name");

      await capture(page, "09-resource-edited");
      return { revision: stored.body.resource.record_revision, staleStatus: stale.status };
    });

    await scenario("09", "فیلتر نوع منبع سطرها را واقعاً محدود می‌کند و با «همه» بازمی‌گردد", async () => {
      await page.setSelect("[data-resource-filter]", "material");
      await sleep(300);
      let state = await page.evaluate(resourcesState);
      assert(state.filter === "material", `filter value ${state.filter}`);
      assert(state.rows.length === 0, `material filter still shows ${state.rows.length} rows`);
      assert(/No resource matches/.test(state.empty ?? ""), "the empty filter state is missing");

      await page.setSelect("[data-resource-filter]", "labor");
      await sleep(300);
      state = await page.evaluate(resourcesState);
      assert(state.filter === "labor", `filter value ${state.filter}`);
      assert(state.rows.length === 2, `labor filter shows ${state.rows.length} rows`);
      assert(state.rows.every((row) => row.type === "Labor"), `labor filter rows ${state.rows.map((row) => row.type)}`);
      await capture(page, "10-resource-filter");

      await page.setSelect("[data-resource-filter]", "all");
      await sleep(300);
      state = await page.evaluate(resourcesState);
      assert(state.filter === "all", `filter value ${state.filter}`);
      assert(state.rows.length === expectedIds.length + 1, `all filter shows ${state.rows.length} rows`);
      return { materialRows: 0, laborRows: 2, allRows: state.rows.length };
    });

    await scenario("10", "جمع و باز کردن شاخهٔ درخت منبع، فرزند را واقعاً پنهان و آشکار می‌کند", async () => {
      await page.click('[data-resource-toggle="RPS-CIVIL-CREW"]');
      await sleep(300);
      let state = await page.evaluate(resourcesState);
      const parent = state.rows.find((row) => row.id === "RPS-CIVIL-CREW");
      assert(parent?.hasToggle === true, "the parent resource does not expose a collapse toggle");
      assert(parent.expanded === false, `parent expanded after collapse ${parent.expanded}`);
      assert(!state.rows.some((row) => row.id === createdId), "the child row stayed visible after collapse");
      await capture(page, "11-resource-collapsed");

      await page.click('[data-resource-toggle="RPS-CIVIL-CREW"]');
      await sleep(300);
      state = await page.evaluate(resourcesState);
      assert(state.rows.some((row) => row.id === createdId), "the child row did not return after expand");
      return { collapsedRows: 1, expandedRows: state.rows.length };
    });

    await scenario("11", "پنجرهٔ Resources در 1280×720 بدون بریدگی چیدمان رندر می‌شود", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await sleep(500);
      const layout = await page.evaluate(`(() => {
        const rect = (element) => {
          if (!element) return null;
          const bounds = element.getBoundingClientRect();
          return { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height };
        };
        return {
          innerWidth,
          innerHeight,
          toolbar: rect(document.querySelector("[data-resources-page] .cp-calendar-window-toolbar")),
          register: rect(document.querySelector("[data-resources-page] .cp-calendar-register")),
          rowCount: document.querySelectorAll("[data-resource-row]").length,
        };
      })()`);
      assert(layout.toolbar && layout.toolbar.width > 0, "the toolbar has no layout box at 1280x720");
      assert(layout.register && layout.register.height > 0, "the register has no layout box at 1280x720");
      assert(layout.rowCount === 2, `register rows at 1280x720: ${layout.rowCount}`);
      assert(layout.toolbar.x >= 0 && layout.toolbar.x + layout.toolbar.width <= layout.innerWidth + 1, `toolbar overflows: ${JSON.stringify(layout.toolbar)}`);
      await capture(page, "12-resource-1280x720");
      return layout;
    });

    await scenario("12", "تب Usage در فارسی RTL همان حقایق ذخیره‌شده را نشان می‌دهد و از کادر 1280×720 بیرون نمی‌زند", async () => {
      await setLanguage(page, "fa");
      await openMenu(page, "resources", "[data-resources-page] [data-resource-row]", "resource register in Persian");
      await page.click('[data-resource-row][data-resource-id="RPS-CIVIL-CREW"]');
      await sleep(200);
      await page.click('[data-resource-tab="usage"]');
      await page.waitForSelector("[data-resource-usage-row]", "Persian usage rows", 20000);
      await sleep(400);
      const state = await page.evaluate(resourcesState);
      assert(state.direction === "rtl", `resources page direction ${state.direction}`);
      assert(state.usageTabLabel === "استفاده", `Persian usage tab label ${state.usageTabLabel}`);
      assert(state.usageRows.length === 2, `Persian usage rows ${state.usageRows.length}`);
      assert(state.usageRows[0].status === "overallocated", `Persian first usage status ${state.usageRows[0].status}`);
      assert(state.usageRows[1].status === "within", `Persian second usage status ${state.usageRows[1].status}`);
      assert(/2 دورهٔ ذخیره‌شده · 2 مقایسه‌شده · 1 اضافه‌تخصیص\./.test(state.usageSummary ?? ""), `Persian usage summary ${state.usageSummary}`);
      assert(/هیچ اجرای زمان‌بندی یا تراز منابعی در اینجا انجام نمی‌شود/.test(state.usageHint ?? ""), `Persian usage hint ${state.usageHint}`);
      const bounds = await page.evaluate(`(() => {
        const panel = document.querySelector('[data-resource-panel="usage"]');
        if (!panel) return null;
        const rect = panel.getBoundingClientRect();
        return { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom, width: innerWidth, height: innerHeight };
      })()`);
      assert(bounds, "the usage panel has no layout box in Persian");
      assert(bounds.left >= -1 && bounds.right <= bounds.width + 1, `usage panel overflows horizontally: ${JSON.stringify(bounds)}`);
      assert(bounds.bottom <= bounds.height + 1, `usage panel overflows vertically: ${JSON.stringify(bounds)}`);
      await capture(page, "13-resource-usage-fa");
      return { direction: state.direction, summary: state.usageSummary };
    });

    assert(exceptions.length === 0, `uncaught page exceptions: ${JSON.stringify(exceptions.slice(0, 3))}`);
    assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors.slice(0, 3))}`);
    assert(apiFailures.length === 0, `API 5xx responses: ${JSON.stringify(apiFailures.slice(0, 3))}`);
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
