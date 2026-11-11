#!/usr/bin/env node
/**
 * Browser E2E for Version 26 Jalali calendars and the exception revision path.
 *
 * Drives the real preview on project preview-rps-01. A calendar created from
 * the stored base with the Jalali date system keeps canonical ISO dates in
 * storage, accepts a typed Jalali exception date, shows the Jalali equivalent
 * next to the stored ISO date, and edits the stored exception behind its
 * record revision through a real PUT.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4184 node e2e/calendars-jalali-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4184";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "calendars-jalali-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `calendars-jalali-v26-${evidenceDate}`);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const TENANT = "cubi-preview-tenant";
const BASE_ID = "CUBI-RPS-CAL";
const stamp = Date.now().toString(36).toUpperCase();
const newId = `RPS-E2E-JAL-${stamp}`;
const newName = "E2E Jalali Calendar";
const jalaliDate = "1405/10/01";

const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const scenarios = [];
const screenshots = [];
let storedIso = null;

function log(message) {
  process.stdout.write(`${message}\n`);
}

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

async function scenario(id, name, body) {
  log(`\n[${id}] ${name}`);
  try {
    const details = (await body()) ?? {};
    scenarios.push({ id, name, status: "pass", at: new Date().toISOString(), ...details });
    log(`  PASS ${id}. ${name}`);
  } catch (error) {
    scenarios.push({ id, name, status: "fail", at: new Date().toISOString(), error: String(error?.stack ?? error) });
    throw error;
  }
}

const requestHeaders = `{
  "Content-Type": "application/json",
  "X-Tenant-Id": ${JSON.stringify(TENANT)},
  "X-Project-Id": ${JSON.stringify(PROJECT)},
  "X-Project-Revision": "7"
}`;

function calendarUrl(suffix = "") {
  return `/api/projects/${PROJECT}/p6/calendars${suffix}`;
}

function ref(id) {
  return `${calendarUrl("/")}${encodeURIComponent(id)}/1`;
}

const calendarState = `(() => {
  const page = document.querySelector("[data-calendar-page]");
  const notice = page?.querySelector("[data-calendar-notice]");
  return {
    activeMenu: document.querySelector(".cp-workspace")?.dataset.activeMenu ?? null,
    rows: [...document.querySelectorAll("[data-calendar-row]")].map((row) => ({
      id: row.dataset.calendarId,
      version: row.dataset.calendarVersion,
      selected: row.getAttribute("aria-selected") === "true",
    })),
    activeTab: document.querySelector('[data-calendar-tab][aria-selected="true"]')?.dataset.calendarTab ?? null,
    caption: page?.querySelector(".cp-calendar-editor .cp-calendar-section-head span")?.textContent?.trim() ?? null,
    exceptions: [...document.querySelectorAll("[data-calendar-panel='exceptions'] .cp-calendar-holiday-list li")].map((item) => (item.textContent || "").trim()),
    exceptionDates: [...document.querySelectorAll("[data-calendar-exception-delete]")].map((button) => button.dataset.calendarExceptionDelete),
    editing: document.querySelector("[data-calendar-exception-form]")?.dataset.editing ?? null,
    dateInputType: document.querySelector('[data-calendar-exception-form] [name="date"]')?.getAttribute("type") ?? null,
    notice: notice ? { kind: notice.dataset.state, text: notice.textContent.trim() } : null,
    shared: (() => {
      const main = document.querySelector(".cp-main[data-details-split]");
      const details = document.querySelector("#cp-details");
      return {
        collapsed: main?.dataset.detailsCollapsed ?? null,
        bottomDisplay: details ? getComputedStyle(details).display : null,
      };
    })(),
  };
})()`;

async function capture(page, name) {
  const file = `calendars-jalali-v26/${name}.png`;
  await page.screenshot(file);
  copyFileSync(join(artifactsDir, file), join(evidenceDir, `${name}.png`));
  screenshots.push(`${name}.png`);
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

async function openCalendars(page) {
  await openMenu(page, "calendars", "[data-calendar-page] .cp-calendar-window-toolbar", "calendar register");
  await page.waitFor(`document.querySelectorAll("[data-calendar-row]").length > 0`, "calendar rows");
  await sleep(300);
}

async function selectCalendar(page, id) {
  await page.click(`[data-calendar-row][data-calendar-id="${id}"][data-calendar-version="1"]`);
  await page.waitForSelector('[data-calendar-tab="workweek"]', "calendar detail tabs");
  await sleep(500);
}

async function selectTab(page, tab) {
  await page.click(`[data-calendar-tab="${tab}"]`);
  await page.waitFor(`document.querySelector('[data-calendar-tab="${tab}"][aria-selected="true"]') !== null`, `${tab} tab`);
  await sleep(300);
}

async function api(page, method, path, body) {
  return page.evaluate(`(async () => {
    const response = await fetch(${JSON.stringify(path)}, {
      method: ${JSON.stringify(method)},
      headers: ${requestHeaders},
      ${body === undefined ? "" : `body: JSON.stringify(${JSON.stringify(body)}),`}
    });
    return { status: response.status, body: await response.json() };
  })()`, { awaitPromise: true });
}

async function readCatalogRecord(page, id) {
  const list = await api(page, "GET", calendarUrl());
  assert(list.status === 200, `catalog status ${list.status}`);
  return list.body.calendars.find((item) => item.calendar_id === id) ?? null;
}

async function readSnapshot(page, id) {
  return api(page, "GET", `${ref(id)}/snapshot`);
}

async function readExceptions(page, id) {
  return api(page, "GET", `${ref(id)}/exceptions`);
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
    contract: "cubi-calendars-jalali-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    newCalendarId: newId,
    jalaliDate,
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
    await openCalendars(page);

    await scenario("01", "ایجاد تقویم با مبنای تاریخ جلالی از تقویم پایه", async () => {
      await page.click('[data-calendar-action="new"]');
      await page.waitForSelector("[data-calendar-new-base]", "new calendar dialog");
      await page.setSelect("[data-calendar-new-base]", `${BASE_ID}|1`);
      await page.setInput("[data-calendar-new-id]", newId);
      await page.setInput("[data-calendar-new-version]", "1");
      await page.setInput("[data-calendar-new-name]", newName);
      await page.setSelect("[data-calendar-new-type]", "resource");
      await page.setSelect("[data-calendar-new-system]", "jalali");
      await page.click('[data-calendar-action="new-submit"]');
      await page.waitFor(`document.querySelector('[data-calendar-row][data-calendar-id="${newId}"]') !== null`, "created Jalali calendar row");
      await sleep(700);
      const record = await readCatalogRecord(page, newId);
      assert(record, "created calendar is missing from the catalog");
      assert(record.base_calendar_id === BASE_ID, `created base ${record.base_calendar_id}`);
      assert(record.calendar_type === "resource", `created type ${record.calendar_type}`);
      assert(record.record_revision === 1, `created revision ${record.record_revision}`);
      const snapshot = await readSnapshot(page, newId);
      assert(snapshot.status === 200 && snapshot.body.snapshot.system === "jalali", `snapshot system ${snapshot.body.snapshot.system}`);
      assert(Array.isArray(snapshot.body.snapshot.working_weekdays), "created snapshot has no weekdays");
      await capture(page, "01-jalali-calendar-created");
      return { revision: record.record_revision, system: snapshot.body.snapshot.system };
    });

    await scenario("02", "ثبت استثنا با تاریخ جلالی و ذخیرهٔ تاریخ ISO معیار", async () => {
      await selectCalendar(page, newId);
      await selectTab(page, "exceptions");
      const before = await page.evaluate(calendarState);
      assert(before.dateInputType === "text", `date input type is ${before.dateInputType}`);
      await page.setInput('[data-calendar-exception-form] [name="date"]', jalaliDate);
      await page.setSelect('[data-calendar-exception-form] [name="mode"]', "nonwork");
      await page.click('[data-calendar-exception-form] button[type="submit"]');
      await page.waitFor(`document.querySelectorAll("[data-calendar-exception-delete]").length === 1`, "stored Jalali exception");
      await sleep(500);
      const listed = await readExceptions(page, newId);
      assert(listed.status === 200 && listed.body.exceptions.length === 1, `exception count ${listed.body.exceptions.length}`);
      const stored = listed.body.exceptions[0];
      assert(/^\d{4}-\d{2}-\d{2}$/.test(stored.date), `stored date is not ISO: ${stored.date}`);
      assert(stored.system === "jalali", `stored system ${stored.system}`);
      assert(stored.record_revision === 1, `stored revision ${stored.record_revision}`);
      const state = await page.evaluate(calendarState);
      assert(state.exceptions.some((text) => text.includes(jalaliDate)), `Jalali label missing: ${JSON.stringify(state.exceptions)}`);
      storedIso = stored.date;
      await capture(page, "02-jalali-exception-saved");
      return { storedDate: stored.date, label: state.exceptions[0] };
    });

    await scenario("03", "ویرایش استثنا با revision رکورد و تغییر به ساعت کل", async () => {
      await page.click(`[data-calendar-exception-edit="${storedIso}"]`);
      await page.waitFor(`document.querySelector("[data-calendar-exception-form]")?.dataset.editing === "true"`, "exception edit form");
      const editing = await page.evaluate(calendarState);
      assert(editing.editing === "true", "edit state is not active");
      await page.setSelect('[data-calendar-exception-form] [name="mode"]', "total-work-hours");
      const hoursVisible = await page.evaluate(`!document.querySelector('[data-calendar-exception-hours]')?.hidden`);
      assert(hoursVisible, "total-hours field is hidden");
      await page.setInput('[data-calendar-exception-form] [name="hours"]', "6");
      await page.click('[data-calendar-exception-form] button[type="submit"]');
      await page.waitFor(`document.querySelector("[data-calendar-notice][data-state='ok']") !== null`, "revision notice");
      await sleep(500);
      const listed = await readExceptions(page, newId);
      const stored = listed.body.exceptions[0];
      assert(stored.mode === "total-work-hours", `stored mode ${stored.mode}`);
      assert(stored.total_work_hours === "6", `stored hours ${stored.total_work_hours}`);
      assert(stored.record_revision === 2, `stored revision ${stored.record_revision}`);
      const state = await page.evaluate(calendarState);
      assert(state.exceptions.some((text) => text.includes("r2")), `revision label missing: ${JSON.stringify(state.exceptions)}`);
      await capture(page, "03-jalali-exception-revised");
      return { mode: stored.mode, hours: stored.total_work_hours, revision: stored.record_revision };
    });

    await scenario("04", "ویرایش و تاریخ جلالی پس از بارگذاری کامل صفحه باقی می‌مانند", async () => {
      await page.navigate(`${baseUrl}/app?project=${PROJECT}&view=live`, "body", "workspace");
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows after reload");
      await sleep(1200);
      await openCalendars(page);
      await page.waitFor(`document.querySelector('[data-calendar-row][data-calendar-id="${newId}"]') !== null`, "Jalali calendar after reload");
      await selectCalendar(page, newId);
      await selectTab(page, "exceptions");
      const state = await page.evaluate(calendarState);
      assert(state.dateInputType === "text", `date input type after reload ${state.dateInputType}`);
      assert(state.exceptions.some((text) => text.includes(jalaliDate)), `Jalali label after reload: ${JSON.stringify(state.exceptions)}`);
      const listed = await readExceptions(page, newId);
      const stored = listed.body.exceptions[0];
      assert(stored.mode === "total-work-hours" && stored.record_revision === 2, `stored after reload ${JSON.stringify(stored)}`);
      await capture(page, "04-jalali-persisted");
      return { storedDate: stored.date, revision: stored.record_revision };
    });

    await scenario("05", "پنجرهٔ Jalali در 1280×720 بدون بریدگی چیدمان رندر می‌شود", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await sleep(500);
      const layout = await page.evaluate(`(() => ({
        overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        registerWidth: document.querySelector(".cp-calendar-register")?.getBoundingClientRect().width ?? 0,
        editorWidth: document.querySelector(".cp-calendar-editor")?.getBoundingClientRect().width ?? 0,
      }))()`);
      assert(layout.overflow <= 0, `horizontal overflow ${layout.overflow}`);
      assert(layout.registerWidth > 0 && layout.editorWidth > 0, `panes did not render ${JSON.stringify(layout)}`);
      const state = await page.evaluate(calendarState);
      assert(state.shared.collapsed === "true" && state.shared.bottomDisplay === "none", `shared pane ${JSON.stringify(state.shared)}`);
      await capture(page, "05-jalali-1280x720");
      return layout;
    });
  } finally {
    await page.cdp.send("Emulation.clearDeviceMetricsOverride").catch(() => {});
    try {
      chrome.stop();
    } catch {
      // A stop failure must not mask the scenario result.
    }
    report.exceptions = exceptions;
    report.consoleErrors = consoleErrors;
    report.apiFailures = apiFailures;
    writeFileSync(join(evidenceDir, "calendars-jalali-v26.json"), `${JSON.stringify(report, null, 2)}\n`, "utf8");
    const passed = scenarios.filter((item) => item.status === "pass").length;
    const failed = scenarios.filter((item) => item.status === "fail").length;
    log(`\nScenarios: ${passed} passed, ${failed} failed`);
    if (failed) process.exitCode = 1;
  }
  process.exit(process.exitCode ?? 0);
}

main().catch((error) => {
  console.error(`FAILED: ${error?.message ?? error}`);
  process.exit(1);
});
