#!/usr/bin/env node
/**
 * Browser E2E for the Version 26 Calendars window.
 *
 * Drives the real preview on project preview-rps-01. The register, General tab,
 * Workweek tab and Exceptions tab read and write the persisted calendar master,
 * the immutable snapshot, the work-hour rules and exception facts through the
 * p6-calendar.v1 contracts. Every expected value is read back from the same
 * session's API, so no fixture data is injected into the page.
 *
 * Scenarios cover: seeded register, a real workweek edit that changes CPM,
 * split-shift editing on a working-time calendar, client-side overlap refusal,
 * create-from-base with inherited facts, exception add/remove, persistence
 * after reload, and the 1280x720 layout.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4184 node e2e/calendars-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4184";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "calendars-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `calendars-v26-${evidenceDate}`);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const TENANT = "cubi-preview-tenant";
const BASE_ID = "CUBI-RPS-CAL";
const TIME_ID = "CUBI-RPS-CAL-TIME";
const stamp = Date.now().toString(36).toUpperCase();
const newId = `RPS-E2E-CAL-${stamp}`;
const newName = "E2E Resource Calendar";
const exceptionDate = "2026-12-25";

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
  const rows = [...document.querySelectorAll("[data-calendar-row]")].map((row) => ({
    id: row.dataset.calendarId,
    version: row.dataset.calendarVersion,
    selected: row.getAttribute("aria-selected") === "true",
    cells: [...row.querySelectorAll("td")].map((cell) => (cell.textContent || "").trim()),
  }));
  const workdays = [...document.querySelectorAll("[data-calendar-workday]")].map((row) => ({
    weekday: Number(row.dataset.calendarWorkday),
    working: row.querySelector("[data-workday-working]")?.checked ?? null,
    hours: row.querySelector("[data-workday-hours]")?.value ?? null,
    shifts: row.querySelector("[data-workday-shifts]")?.value ?? null,
  }));
  const notice = page?.querySelector("[data-calendar-notice]");
  return {
    activeMenu: document.querySelector(".cp-workspace")?.dataset.activeMenu ?? null,
    toolbar: page?.querySelector(".cp-calendar-window-toolbar strong")?.textContent?.trim() ?? null,
    rows,
    activeTab: document.querySelector('[data-calendar-tab][aria-selected="true"]')?.dataset.calendarTab ?? null,
    caption: page?.querySelector(".cp-calendar-editor .cp-calendar-section-head span")?.textContent?.trim() ?? null,
    workdays,
    exceptionDates: [...document.querySelectorAll("[data-calendar-exception-delete]")].map((button) => button.dataset.calendarExceptionDelete),
    notice: notice ? { kind: notice.dataset.state, text: notice.textContent.trim() } : null,
    dialog: page?.querySelector(".cp-calendar-dialog")?.textContent?.trim() ?? null,
    newDisabled: Boolean(page?.querySelector('[data-calendar-action="new"]')?.disabled),
    tabs: [...document.querySelectorAll("[data-calendar-tab]")].map((button) => button.dataset.calendarTab),
  };
})()`;

const sharedDetails = `(() => {
  const main = document.querySelector(".cp-main[data-details-split]");
  const details = document.querySelector("#cp-details");
  return {
    collapsed: main?.dataset.detailsCollapsed ?? null,
    bottomDisplay: details ? getComputedStyle(details).display : null,
  };
})()`;

async function capture(page, name) {
  const file = `calendars-v26/${name}.png`;
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

async function readList(page) {
  return api(page, "GET", calendarUrl());
}

async function readCatalogRecord(page, id) {
  const list = await readList(page);
  return list.body.calendars.find((item) => item.calendar_id === id) ?? null;
}

async function readSnapshot(page, id) {
  return api(page, "GET", `${ref(id)}/snapshot`);
}

async function readWorkHours(page, id) {
  return api(page, "GET", `${ref(id)}/work-hours`);
}

async function readExceptions(page, id) {
  return api(page, "GET", `${ref(id)}/exceptions`);
}

async function setWorkday(page, weekday, { working, shifts }) {
  if (working !== undefined) {
    await page.evaluate(`(() => {
      const input = document.querySelector('[data-calendar-workday="${weekday}"] [data-workday-working]');
      if (!input) return false;
      if (input.checked !== ${working}) {
        input.checked = ${working};
        input.dispatchEvent(new Event("change", { bubbles: true }));
      }
      return true;
    })()`);
  }
  if (shifts !== undefined) {
    await page.setInput(`[data-calendar-workday="${weekday}"] [data-workday-shifts]`, shifts);
  }
}

async function saveWorkday(page, weekday) {
  await page.click(`[data-calendar-workday="${weekday}"] [data-workday-save="${weekday}"]`);
  await sleep(700);
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
    contract: "cubi-calendars-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    newCalendarId: newId,
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

    await scenario("01", "پنجرهٔ Calendars فهرست تقویم‌ها را از سرور می‌خواند و پنل Details مشترک را بازنمی‌گذارد", async () => {
      await page.waitFor(`[...document.querySelectorAll("[data-calendar-row]")].some((row) => row.dataset.calendarId === ${JSON.stringify(BASE_ID)})`, "seeded calendar row");
      let state = await page.evaluate(calendarState);
      assert(state.activeMenu === "calendars", `active menu is ${state.activeMenu}`);
      const ids = state.rows.map((row) => row.id);
      assert(ids.includes(BASE_ID), `register is missing ${BASE_ID}: ${ids}`);
      assert(ids.includes(TIME_ID), `register is missing the split-shift calendar: ${ids}`);
      assert(state.newDisabled === false, "New is disabled although calendars exist");
      const list = await readList(page);
      assert(list.status === 200, `catalog status ${list.status}`);
      assert(list.body.calendars.map((item) => item.calendar_id).includes(BASE_ID), "API catalog is missing the base calendar");
      const layout = await page.evaluate(sharedDetails);
      assert(layout.collapsed === "true", `shared details still claim space: ${layout.collapsed}`);
      assert(layout.bottomDisplay === "none", `shared details are still rendered: ${layout.bottomDisplay}`);

      await selectCalendar(page, BASE_ID);
      state = await page.evaluate(calendarState);
      assert(state.caption === `${BASE_ID} / 1`, `selected caption ${state.caption}`);
      assert(state.tabs.join(",") === "general,workweek,exceptions", `tabs ${state.tabs}`);
      const snapshot = await readSnapshot(page, BASE_ID);
      assert(snapshot.status === 200 && snapshot.body.kind === "calendar_snapshot", `snapshot ${snapshot.status}`);
      await capture(page, "01-calendar-register");
      return { ids, caption: state.caption, collapsed: layout.collapsed };
    });

    await scenario("02", "ویرایش روز کاری، ذخیرهٔ قاعدهٔ هفته کاری و تغییر نتیجهٔ زمان‌بندی", async () => {
      await selectTab(page, "workweek");
      let state = await page.evaluate(calendarState);
      const friday = state.workdays.find((day) => day.weekday === 4);
      assert(friday?.working === true, `Friday starts as a working day: ${JSON.stringify(friday)}`);
      await setWorkday(page, 4, { working: false });
      await saveWorkday(page, 4);
      await page.waitFor(`document.querySelector("[data-calendar-notice][data-state='ok']") !== null`, "workday notice");
      const rules = await readWorkHours(page, BASE_ID);
      assert(rules.status === 200, `work hours status ${rules.status}`);
      const stored = rules.body.work_hours.find((rule) => rule.kind === "standard_work_week" && rule.weekday === 4);
      assert(stored, "the Friday rule was not stored");
      assert(stored.is_working_day === false, `Friday rule ${JSON.stringify(stored)}`);
      const record = await readCatalogRecord(page, BASE_ID);
      assert(record.record_revision === 2, `master revision after workweek edit ${record.record_revision}`);
      await capture(page, "02-workweek-edited");
      return { fridayRule: stored, revision: record.record_revision };
    });

    await scenario("03", "ویرایش شیفت‌های تفکیک‌شده روی تقویم زمان‌دار و ذخیرهٔ دقیق بازه‌ها", async () => {
      await selectCalendar(page, TIME_ID);
      await selectTab(page, "workweek");
      let state = await page.evaluate(calendarState);
      assert(state.workdays.length === 7, `workday rows ${state.workdays.length}`);
      const monday = state.workdays.find((day) => day.weekday === 0);
      assert(monday?.shifts === "08:00-12:00, 13:00-17:00", `Monday shifts ${monday?.shifts}`);
      await setWorkday(page, 0, { shifts: "08:00-12:00, 13:00-17:00, 18:00-20:00" });
      await saveWorkday(page, 0);
      await page.waitFor(`document.querySelector("[data-calendar-notice][data-state='ok']") !== null`, "shift notice");
      const rules = await readWorkHours(page, TIME_ID);
      const standard = rules.body.work_hours.find((rule) => rule.kind === "standard_work_week" && rule.weekday === 0);
      const detailed = rules.body.work_hours.find((rule) => rule.kind === "standard_detailed_work_hours" && rule.weekday === 0);
      assert(detailed, "the detailed work-hour rule was not stored");
      assert(JSON.stringify(detailed.intervals) === JSON.stringify([["08:00", "12:00"], ["13:00", "17:00"], ["18:00", "20:00"]]), `intervals ${JSON.stringify(detailed.intervals)}`);
      assert(standard?.total_work_hours === "10", `standard hours ${standard?.total_work_hours}`);
      // Two new declarations (standard and detailed) each bump the master, so
      // the revision moves from 1 to 3.
      const record = await readCatalogRecord(page, TIME_ID);
      assert(record.record_revision === 3, `working-time master revision ${record.record_revision}`);
      await capture(page, "03-split-shifts");
      return { intervals: detailed.intervals, total: standard.total_work_hours, revision: record.record_revision };
    });

    await scenario("04", "بازه‌های هم‌پوشان پیش از ارسال رد می‌شوند و رکورد ذخیره‌شده تغییر نمی‌کند", async () => {
      await setWorkday(page, 0, { shifts: "08:00-12:00, 11:00-13:00" });
      await saveWorkday(page, 0);
      const state = await page.evaluate(calendarState);
      assert(state.notice?.kind === "error", `overlap notice ${JSON.stringify(state.notice)}`);
      assert(/non-overlapping|هم‌پوشانی/.test(state.notice?.text ?? ""), `overlap text ${state.notice?.text}`);
      const rules = await readWorkHours(page, TIME_ID);
      const detailed = rules.body.work_hours.find((rule) => rule.kind === "standard_detailed_work_hours" && rule.weekday === 0);
      assert(detailed?.intervals.length === 3, `stored intervals changed: ${JSON.stringify(detailed?.intervals)}`);
      await capture(page, "04-overlap-rejected");
      return { notice: state.notice.text, storedIntervals: detailed.intervals.length };
    });

    await scenario("05", "ایجاد تقویم جدید از تقویم پایه با تعریف، قواعد هفته کاری و تعطیلات کپی‌شده", async () => {
      await page.click('[data-calendar-action="new"]');
      await page.waitForSelector("[data-calendar-new-base]", "new calendar dialog");
      await page.setSelect("[data-calendar-new-base]", `${BASE_ID}|1`);
      await page.setInput("[data-calendar-new-id]", newId);
      await page.setInput("[data-calendar-new-version]", "1");
      await page.setInput("[data-calendar-new-name]", newName);
      await page.setSelect("[data-calendar-new-type]", "resource");
      await page.click('[data-calendar-action="new-submit"]');
      await page.waitFor(`document.querySelector('[data-calendar-row][data-calendar-id="${newId}"]') !== null`, "created calendar row");
      await sleep(600);
      const record = await readCatalogRecord(page, newId);
      assert(record, "created calendar is missing from the API catalog");
      assert(record.calendar_type === "resource", `created type ${record.calendar_type}`);
      assert(record.base_calendar_id === BASE_ID, `created base ${record.base_calendar_id}`);
      assert(record.record_revision === 1, `created revision ${record.record_revision}`);
      const snapshot = await readSnapshot(page, newId);
      assert(snapshot.status === 200, `created snapshot status ${snapshot.status}`);
      // Working-day snapshots omit a kind field by contract; their weekday set
      // is the authoritative shape. The frozen seeded holiday travels with the
      // copied snapshot instead of living in the exception overlay.
      assert(Array.isArray(snapshot.body.snapshot.working_weekdays), `created snapshot weekdays ${JSON.stringify(snapshot.body.snapshot.working_weekdays)}`);
      const copiedHolidays = snapshot.body.snapshot.holidays ?? [];
      assert(copiedHolidays.includes("2026-10-28"), `created snapshot holidays ${JSON.stringify(copiedHolidays)}`);
      const inheritedHours = await readWorkHours(page, newId);
      const inheritedFriday = inheritedHours.body.work_hours.find((rule) => rule.kind === "standard_work_week" && rule.weekday === 4);
      assert(inheritedFriday?.is_working_day === false, `inherited Friday rule ${JSON.stringify(inheritedFriday)}`);
      const inherited = await readExceptions(page, newId);
      assert(inherited.status === 200 && inherited.body.exceptions.length === 0, `created exceptions ${JSON.stringify(inherited.body.exceptions)}`);
      const state = await page.evaluate(calendarState);
      assert(state.rows.some((row) => row.id === newId), "created calendar is not in the register");
      await capture(page, "05-calendar-created");
      return {
        newId,
        revision: record.record_revision,
        copiedHolidays,
        inheritedWorkHourRules: inheritedHours.body.work_hours.length,
      };
    });

    await scenario("06", "افزودن و حذف استثنا از جدول واقعی و تأیید از سرور", async () => {
      await selectCalendar(page, newId);
      await selectTab(page, "exceptions");
      await page.setInput('[data-calendar-exception-form] [name="date"]', exceptionDate);
      await page.setSelect('[data-calendar-exception-form] [name="mode"]', "nonwork");
      await page.click('[data-calendar-exception-form] button[type="submit"]');
      await page.waitFor(`document.querySelector('[data-calendar-exception-delete="${exceptionDate}"]') !== null`, "stored exception row");
      let listed = await readExceptions(page, newId);
      assert(listed.body.exceptions.length === 1, `exceptions after add ${listed.body.exceptions.length}`);
      await page.click(`[data-calendar-exception-delete="${exceptionDate}"]`);
      await page.waitFor(`document.querySelector('[data-calendar-exception-delete="${exceptionDate}"]') === null`, "removed exception row");
      await sleep(400);
      listed = await readExceptions(page, newId);
      assert(listed.body.exceptions.length === 0, `exceptions after remove ${listed.body.exceptions.length}`);
      const state = await page.evaluate(calendarState);
      assert(state.notice?.kind === "ok", `remove notice ${JSON.stringify(state.notice)}`);
      await capture(page, "06-exception-removed");
      return { remaining: listed.body.exceptions.map((item) => item.date) };
    });

    await scenario("07", "پس از بارگذاری کامل صفحه، تقویم جدید، شیفت‌ها و اثر قاعدهٔ هفته کاری باقی می‌مانند", async () => {
      await page.navigate(`${baseUrl}/app?project=${PROJECT}&view=live`, "body", "workspace");
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows after reload");
      await sleep(1200);
      await openCalendars(page);
      await page.waitFor(`document.querySelector('[data-calendar-row][data-calendar-id="${newId}"]') !== null`, "created calendar after reload");
      const timeRules = await readWorkHours(page, TIME_ID);
      const detailed = timeRules.body.work_hours.find((rule) => rule.kind === "standard_detailed_work_hours" && rule.weekday === 0);
      assert(detailed?.intervals.length === 3, `shift rules after reload ${JSON.stringify(detailed?.intervals)}`);
      const baseRules = await readWorkHours(page, BASE_ID);
      const friday = baseRules.body.work_hours.find((rule) => rule.kind === "standard_work_week" && rule.weekday === 4);
      assert(friday?.is_working_day === false, `Friday rule after reload ${JSON.stringify(friday)}`);
      const facts = await page.evaluate(`(async () => {
        const response = await fetch("/api/v1/workspace/control-room/read", { headers: ${requestHeaders} });
        return response.json();
      })()`, { awaitPromise: true });
      const a140 = facts.workspace.activities.find((activity) => activity.id === "A140");
      assert(a140, "A140 is missing from the workspace read model");
      assert(a140.cells["activity.early_finish"] === "2026-11-05", `A140 finish after workweek edit ${a140.cells["activity.early_finish"]}`);
      await capture(page, "07-persisted-after-reload");
      return { newId, intervals: detailed.intervals.length, fridayWorking: friday.is_working_day, finish: a140.cells["activity.early_finish"] };
    });

    await scenario("08", "پنجرهٔ Calendars در 1280×720 بدون بریدگی چیدمان رندر می‌شود", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await sleep(600);
      await selectCalendar(page, TIME_ID);
      const layout = await page.evaluate(`(() => {
        const page = document.querySelector("[data-calendar-page]");
        const toolbar = page?.querySelector(".cp-calendar-window-toolbar");
        const register = page?.querySelector(".cp-calendar-register");
        const editor = page?.querySelector(".cp-calendar-editor");
        const box = (element) => {
          if (!element) return null;
          const rect = element.getBoundingClientRect();
          return { x: Math.round(rect.x), y: Math.round(rect.y), width: Math.round(rect.width), height: Math.round(rect.height) };
        };
        return {
          innerWidth: window.innerWidth,
          innerHeight: window.innerHeight,
          toolbar: box(toolbar),
          register: box(register),
          editor: box(editor),
          overflow: document.documentElement.scrollWidth > window.innerWidth,
        };
      })()`);
      assert(layout.innerWidth === 1280 && layout.innerHeight === 720, `viewport ${layout.innerWidth}x${layout.innerHeight}`);
      assert(layout.toolbar && layout.toolbar.width > 0, "toolbar is not rendered");
      assert(layout.register && layout.editor, "register or editor is missing");
      assert(layout.overflow === false, "the page has horizontal overflow at 1280");
      const shared = await page.evaluate(sharedDetails);
      assert(shared.collapsed === "true" && shared.bottomDisplay === "none", `shared details at 1280 ${JSON.stringify(shared)}`);
      await capture(page, "08-calendar-1280x720");
      return { ...layout, collapsed: shared.collapsed };
    });

    report.finishedAt = new Date().toISOString();
    writeFileSync(join(evidenceDir, "calendars-v26.json"), `${JSON.stringify(report, null, 2)}\n`, "utf8");
    log(`\nScenarios: ${scenarios.filter((item) => item.status === "pass").length} passed, ${scenarios.filter((item) => item.status === "fail").length} failed`);
  } catch (error) {
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(evidenceDir, "calendars-v26.json"), `${JSON.stringify(report, null, 2)}\n`, "utf8");
    log(`\nFAILED: ${error && error.message ? error.message : error}`);
    process.exitCode = 1;
  } finally {
    try {
      await chrome.close();
    } catch {
      // The harness already has the failure reason; a close error must not mask it.
    }
  }
}

await main();
// The CDP socket and the child process keep the event loop alive even after the
// report is written; exit explicitly so a completed run cannot hang a terminal.
process.exit(process.exitCode ?? 0);
