#!/usr/bin/env node
/**
 * Browser E2E for Version 26 calendar usage and assignment calendar references.
 *
 * Drives the real preview on project preview-rps-01. The Calendars window
 * lists the stored activity, resource and assignment references to one exact
 * calendar version, and the Assignments window persists an explicit calendar
 * reference on a new assignment so the usage list grows.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 node e2e/calendars-usage-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "calendars-usage-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `calendars-usage-v26-${evidenceDate}`);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const TENANT = "cubi-preview-tenant";
const CALENDAR_ID = "CUBI-RPS-CAL";
const CALENDAR_VERSION = "1";
const stamp = Date.now().toString(36).toUpperCase();
const assignmentId = `RPS-E2E-CAL-${stamp}`;

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

function usageUrl() {
  return `/api/projects/${PROJECT}/p6/calendars/${encodeURIComponent(CALENDAR_ID)}/${CALENDAR_VERSION}/uses`;
}

const usageState = `(() => {
  const page = document.querySelector("[data-calendar-page]");
  return {
    activeTab: document.querySelector('[data-calendar-tab][aria-selected="true"]')?.dataset.calendarTab ?? null,
    total: document.querySelector("[data-calendar-usage-total]")?.textContent?.trim() ?? null,
    rows: [...document.querySelectorAll("[data-calendar-usage-row]")].map((row) => ({
      kind: row.dataset.usageKind,
      reference: row.dataset.usageReference,
      text: (row.textContent || "").trim(),
    })),
    summary: document.querySelector("[data-calendar-usage-summary]")?.textContent?.trim() ?? null,
    empty: Boolean(document.querySelector("[data-calendar-usage-empty]")),
    loading: Boolean(document.querySelector("[data-calendar-usage-loading]")),
    error: document.querySelector("[data-calendar-usage-error]")?.textContent?.trim() ?? null,
  };
})()`;

const assignmentState = `(() => {
  const page = document.querySelector("[data-assignments-page]");
  const notice = page?.querySelector("[data-assignment-notice]");
  const form = page?.querySelector("[data-assignment-form]");
  const row = page?.querySelector('[data-assignment-row][data-assignment-id="' + ${JSON.stringify(assignmentId)} + '"]');
  return {
    heading: page?.querySelector(".cp-register-toolbar strong")?.textContent?.trim() ?? null,
    form: form ? {
      calendarOptions: [...form.querySelectorAll('select[name="calendar"] option')].map((option) => ({ value: option.value, label: option.textContent.trim() })),
      calendarValue: form.querySelector('select[name="calendar"]')?.value ?? null,
    } : null,
    row: row ? [...row.querySelectorAll("td")].map((cell) => (cell.textContent || "").trim()) : null,
    notice: notice ? { kind: notice.dataset.state, text: notice.textContent.trim() } : null,
    canCreate: Boolean(page?.querySelector('[data-assignment-action="new"]')),
  };
})()`;

async function capture(page, name) {
  const file = `calendars-usage-v26/${name}.png`;
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

async function loginAs(page, label) {
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
  const hasPersonas = await page.evaluate('Boolean(document.querySelector(".persona"))');
  if (!hasPersonas) {
    const logoutStatus = await page.evaluate(`(async () => {
      const response = await fetch("/preview/logout", { method: "POST", redirect: "manual" });
      return response.status;
    })()`, { awaitPromise: true });
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
  await setLanguage(page, "en");
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

async function readUsage(page) {
  await page.waitFor(
    `(() => {
      const page = document.querySelector("[data-calendar-page]");
      return Boolean(page) && !document.querySelector("[data-calendar-usage-loading]");
    })()`,
    "calendar usage settled",
  );
  return page.evaluate(usageState);
}

async function openCalendarsUsage(page) {
  await openMenu(page, "calendars", "[data-calendar-page] .cp-calendar-window-toolbar", "calendar register");
  await page.waitFor(`document.querySelectorAll("[data-calendar-row]").length > 0`, "calendar rows");
  await page.click(`[data-calendar-row][data-calendar-id="${CALENDAR_ID}"][data-calendar-version="${CALENDAR_VERSION}"]`);
  await page.waitForSelector('[data-calendar-tab="usage"]', "calendar detail tabs");
  await page.click('[data-calendar-tab="usage"]');
  await page.waitFor(`document.querySelector('[data-calendar-tab="usage"][aria-selected="true"]') !== null`, "usage tab");
  await sleep(400);
}

async function openAssignments(page) {
  await openMenu(page, "assignments", "[data-assignments-page] .cp-register-toolbar", "assignment register");
  await page.waitFor(
    `(() => {
      const page = document.querySelector("[data-assignments-page]");
      return Boolean(page) && !page.textContent.includes("Reading resource assignments");
    })()`,
    "assignment register settled",
  );
  await sleep(400);
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
    contract: "cubi-calendars-usage-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    calendarId: CALENDAR_ID,
    assignmentId,
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
  };

  try {
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
    await sleep(400);
    await loginAs(page, "Planner");

    await scenario("01", "فهرست استفاده‌کنندگان تقویم، منبع ذخیره‌شده را نشان می‌دهد", async () => {
      await openCalendarsUsage(page);
      const state = await readUsage(page);
      assert(state.activeTab === "usage", `active tab ${state.activeTab}`);
      assert(state.total === "1", `usage total ${state.total}`);
      assert(!state.empty && !state.loading && !state.error, `usage surface ${JSON.stringify(state)}`);
      assert(state.rows.length === 1, `usage rows ${JSON.stringify(state.rows)}`);
      assert(state.rows[0].kind === "resource_calendar_assignment", `usage kind ${JSON.stringify(state.rows[0])}`);
      assert(state.rows[0].reference === "RPS-CIVIL-CREW", `usage reference ${JSON.stringify(state.rows[0])}`);
      assert(state.summary.includes("Resource master 1"), `usage summary ${state.summary}`);
      await capture(page, "01-usage-resource-master");
      const server = await api(page, "GET", usageUrl());
      assert(server.status === 200 && server.body.total === 1, `server usage ${JSON.stringify(server.body)}`);
      return { total: server.body.total, counts: server.body.counts };
    });

    await scenario("02", "تخصیص منبع با مرجع تقویم ذخیره می‌شود", async () => {
      await openAssignments(page);
      await page.click('[data-assignment-action="new"]');
      await page.waitForSelector("[data-assignment-form]", "assignment form");
      const options = await page.evaluate(assignmentState);
      assert(options.form.calendarOptions.some((item) => item.value === `${CALENDAR_ID}|${CALENDAR_VERSION}`), `calendar options ${JSON.stringify(options.form.calendarOptions)}`);
      await page.setInput('input[name="assignment-id"]', assignmentId);
      await page.setSelect('select[name="activity-id"]', "A100");
      await page.setInput('input[name="resource-id"]', "RPS-CIVIL-CREW");
      await page.setInput('input[name="units"]', "8");
      await page.setSelect('select[name="calendar"]', `${CALENDAR_ID}|${CALENDAR_VERSION}`);
      await page.click('[data-assignment-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-assignment-notice][data-state="ok"]')?.textContent?.includes("Assignment saved.") ?? false`,
        "assignment saved notice",
      );
      await page.waitForSelector(`[data-assignment-row][data-assignment-id="${assignmentId}"]`, `assignment row ${assignmentId}`);
      await page.evaluate(`(() => {
        const checkbox = document.querySelector('[data-assignment-column="calendar"]');
        if (checkbox && !checkbox.checked) checkbox.click();
        return true;
      })()`);
      await sleep(400);
      const state = await page.evaluate(assignmentState);
      assert(state.row, `assignment row missing ${JSON.stringify(state)}`);
      assert(state.row.includes(CALENDAR_ID), `assignment row calendar ${JSON.stringify(state.row)}`);
      await capture(page, "02-assignment-calendar-saved");
      const stored = await api(page, "GET", `/api/projects/${PROJECT}/p6/resource-assignments/${encodeURIComponent(assignmentId)}`);
      assert(stored.status === 200 && stored.body.assignment.calendar_id === CALENDAR_ID, `stored assignment ${JSON.stringify(stored.body)}`);
      assert(stored.body.assignment.calendar_version === CALENDAR_VERSION, `stored version ${JSON.stringify(stored.body)}`);
      return { assignmentId, calendarId: stored.body.assignment.calendar_id };
    });

    await scenario("03", "استفاده‌کنندگان تقویم پس از تخصیص دو مرجع را می‌شمارند", async () => {
      await openCalendarsUsage(page);
      const state = await readUsage(page);
      assert(state.total === "2", `usage total after assignment ${state.total}`);
      assert(state.rows.length === 2, `usage rows after assignment ${JSON.stringify(state.rows)}`);
      const kinds = state.rows.map((row) => row.kind).sort();
      assert(JSON.stringify(kinds) === JSON.stringify(["resource_assignment_calendar", "resource_calendar_assignment"]), `usage kinds ${JSON.stringify(kinds)}`);
      assert(state.rows.some((row) => row.reference === assignmentId), `assignment reference missing ${JSON.stringify(state.rows)}`);
      assert(state.summary.includes("Resource assignment 1") && state.summary.includes("Resource master 1"), `usage summary ${state.summary}`);
      await capture(page, "03-usage-after-assignment");
      return { total: 2, kinds };
    });

    await scenario("04", "تقویم ناشناخته و نسخهٔ ناشناخته ۴۰۴ می‌دهند", async () => {
      const missing = await api(page, "GET", `/api/projects/${PROJECT}/p6/calendars/MISSING-CAL/1/uses`);
      assert(missing.status === 404 && missing.body.code === "P6_CALENDAR_NOT_FOUND", `missing calendar ${JSON.stringify(missing)}`);
      const staleVersion = await api(page, "GET", `/api/projects/${PROJECT}/p6/calendars/${CALENDAR_ID}/9/uses`);
      assert(staleVersion.status === 404, `stale version ${JSON.stringify(staleVersion)}`);
      return { missing: missing.status, staleVersion: staleVersion.status };
    });

    await scenario("05", "نقش Viewer فهرست استفاده را می‌خواند اما تخصیص نمی‌سازد", async () => {
      await loginAs(page, "Viewer");
      await openCalendarsUsage(page);
      const state = await readUsage(page);
      assert(state.total === "2", `viewer usage total ${state.total}`);
      await openAssignments(page);
      const assignments = await page.evaluate(assignmentState);
      assert(!assignments.canCreate, "viewer sees the new-assignment control");
      const denied = await api(page, "POST", `/api/projects/${PROJECT}/p6/resource-assignments`, {
        contract_version: "p6-resource-write-api.v1",
        assignment_id: `RPS-E2E-DENIED-${stamp}`,
        activity_id: "A100",
        resource_id: "RPS-CIVIL-CREW",
        units: "8",
        calendar_id: CALENDAR_ID,
        calendar_version: CALENDAR_VERSION,
      });
      assert(denied.status === 403, `viewer create ${JSON.stringify(denied)}`);
      await capture(page, "04-viewer-denied");
      return { readTotal: state.total, createStatus: denied.status };
    });

    await scenario("06", "زبانهٔ استفاده‌کنندگان در 1280×720 فارسی راست‌به‌چپ بدون بریدگی رندر می‌شود", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await loginAs(page, "Planner");
      await setLanguage(page, "fa");
      await openCalendarsUsage(page);
      const layout = await page.evaluate(`(() => {
        const rect = (element) => {
          if (!element) return null;
          const bounds = element.getBoundingClientRect();
          return { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height };
        };
        const page = document.querySelector("[data-calendar-page]");
        const usage = document.querySelector("[data-calendar-panel='usage']");
        return {
          innerWidth,
          direction: getComputedStyle(document.querySelector(".cp-workspace") || document.body).direction,
          heading: page?.querySelector(".cp-calendar-editor .cp-calendar-section-head strong")?.textContent?.trim() ?? null,
          usage: rect(usage),
          table: rect(usage?.querySelector(".cp-register-table-wrap")),
          total: document.querySelector("[data-calendar-usage-total]")?.textContent?.trim() ?? null,
        };
      })()`);
      assert(layout.direction === "rtl", `workspace direction ${layout.direction}`);
      assert(layout.heading === "جزئیات تقویم", `Persian heading ${layout.heading}`);
      assert(layout.total === "2", `layout total ${layout.total}`);
      assert(layout.usage && layout.usage.width > 0, "usage panel has no layout box");
      assert(layout.table && layout.table.width > 0, "usage table has no layout box");
      assert(layout.usage.x >= 0 && layout.usage.x + layout.usage.width <= layout.innerWidth + 1, `usage overflows: ${JSON.stringify(layout.usage)}`);
      await capture(page, "05-usage-1280x720-fa");
      return layout;
    });

    assert(exceptions.length === 0, `uncaught page exceptions: ${JSON.stringify(exceptions.slice(0, 3))}`);
    assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors.slice(0, 3))}`);
    assert(apiFailures.length === 0, `API 5xx responses: ${JSON.stringify(apiFailures.slice(0, 3))}`);
  } finally {
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(outDir, "calendars-usage-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(evidenceDir, "calendars-usage-v26.json"), JSON.stringify(report, null, 2));
    chrome.stop();
  }

  log(`\nScenarios: ${scenarios.filter((item) => item.status === "pass").length} passed, ${scenarios.filter((item) => item.status === "fail").length} failed`);
}

main().catch((error) => {
  process.stderr.write(`${error?.stack ?? error}\n`);
  process.exitCode = 1;
});
