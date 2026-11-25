#!/usr/bin/env node
/**
 * Browser E2E for persisted calendar exceptions on the Activities Gantt.
 *
 * Before this slice the Gantt shaded only the immutable calendar snapshot's
 * weekends and holidays; persisted `calendar_exception` rows never reached the
 * bands. This scenario proves the whole loop against the local full-stack
 * preview: a real exception is written through the P6 calendar API, the
 * Shared Core projection (`/p6/calendars/{id}/{version}/day-facts`) classifies
 * the date, and the Activities Gantt paints or removes the band accordingly.
 *
 * No fixture is injected into the page and no area is mocked.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4211 node e2e/gantt-calendar-exceptions-v26.mjs
 */

import { mkdirSync, copyFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4211";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-25";
const outDir = join(artifactsDir, "gantt-calendar-exceptions-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `gantt-calendar-exceptions-v26-${evidenceDate}`);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const TENANT = "cubi-preview-tenant";
const CAL_ID = "CUBI-RPS-CAL";
const CAL_VERSION = "1";
const APP_URL = `${baseUrl}/app?project=${PROJECT}&view=live`;
// 2026-11-05 is a Thursday inside the plotted range and not adjacent to the
// seeded 2026-10-28 holiday (adjacent dates merge into one band).
// 2026-10-31 is a Saturday.
const NONWORK_DATE = "2026-11-05";
const WEEKEND_DATE = "2026-10-31";
const SUNDAY = "2026-11-01";

let revision = 7;
const scenarios = [];
const screenshots = [];
const exceptions = [];
const consoleErrors = [];
const apiFailures = [];

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
  const file = `gantt-calendar-exceptions-v26/${name}.png`;
  await page.screenshot(file);
  copyFileSync(join(artifactsDir, file), join(evidenceDir, `${name}.png`));
  screenshots.push(`${name}.png`);
  return file;
}

function calendarRef() {
  return `/api/projects/${PROJECT}/p6/calendars/${encodeURIComponent(CAL_ID)}/${CAL_VERSION}`;
}

async function api(page, method, path, body) {
  return page.evaluate(`(async () => {
    const response = await fetch(${JSON.stringify(path)}, {
      method: ${JSON.stringify(method)},
      headers: {
        "Content-Type": "application/json",
        "X-Tenant-Id": ${JSON.stringify(TENANT)},
        "X-Project-Id": ${JSON.stringify(PROJECT)},
        "X-Project-Revision": String(${revision}),
      },
      ${body === undefined ? "" : `body: JSON.stringify(${JSON.stringify(body)}),`}
    });
    let payload = null;
    try { payload = await response.json(); } catch { payload = null; }
    return { status: response.status, body: payload };
  })()`, { awaitPromise: true });
}

async function readDayFacts(page) {
  const result = await api(page, "GET", `${calendarRef()}/day-facts`);
  assert(result.status === 200, `day-facts status ${result.status}`);
  return result.body.overrides;
}

async function deleteException(page, date) {
  const result = await api(page, "DELETE", `${calendarRef()}/exceptions/${date}`);
  return result.status;
}

async function saveException(page, payload) {
  const result = await api(page, "POST", `${calendarRef()}/exceptions`, payload);
  assert(result.status === 200, `exception save status ${result.status}: ${JSON.stringify(result.body)}`);
  return result.body;
}

async function reloadApp(page) {
  await page.navigate(APP_URL, "#cp-activity-grid tbody tr[data-activity-id]", "activities window");
  await page.waitFor(`Boolean(document.querySelector("[data-gantt-nonworking]"))`, "gantt non-working layer");
  await sleep(500);
}

async function bands(page) {
  return page.evaluate(`(() => [...document.querySelectorAll("[data-gantt-nonworking]")].map((band) => ({
    kind: band.dataset.ganttNonworking,
    from: band.dataset.nonworkingFrom,
    to: band.dataset.nonworkingTo,
    days: Number(band.dataset.nonworkingDays),
  })))()`);
}

function findBand(list, from) {
  return list.find((band) => band.from === from) ?? null;
}

async function main() {
  const health = await waitForHttp(`${baseUrl}/preview/health`, 30000);
  assert(health.status === "ok" || health.status === 200, `preview health ${health.status}`);

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
    contract: "cubi-gantt-calendar-exceptions-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    capturedAt: new Date().toISOString(),
    calendar: { id: CAL_ID, version: CAL_VERSION },
    dates: { nonwork: NONWORK_DATE, weekend: WEEKEND_DATE },
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
  };

  try {
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
    await sleep(300);
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "form", "login");
    await page.evaluate(`(() => {
      const button = [...document.querySelectorAll("form button")].find((item) => (item.textContent || "").trim().startsWith("Planner"));
      if (!button) return false;
      button.click();
      return true;
    })()`);
    await page.waitForSelector(`[data-project-id="${PROJECT}"]`, "project selection");
    await page.click(`[data-project-id="${PROJECT}"]`);
    await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
    await sleep(1200);

    const meta = await api(page, "GET", `/api/projects/${PROJECT}`);
    assert(meta.status === 200, `project metadata status ${meta.status}`);
    revision = meta.body.project.revision;
    assert(meta.body.project.primary_calendar_id === CAL_ID, `primary calendar ${meta.body.project.primary_calendar_id}`);

    await scenario("01", "پیش از استثنا، باند فقط از snapshot می‌آید و روز کاری ۵ نوامبر باند ندارد", async () => {
      await deleteException(page, NONWORK_DATE);
      await deleteException(page, WEEKEND_DATE);
      await reloadApp(page);
      const list = await bands(page);
      assert(!findBand(list, NONWORK_DATE), `working day ${NONWORK_DATE} must not be shaded before the exception`);
      const weekend = findBand(list, WEEKEND_DATE);
      assert(weekend && weekend.kind === "weekend" && weekend.to === SUNDAY, `weekend band before exception ${JSON.stringify(weekend)}`);
      const facts = await readDayFacts(page);
      assert(Array.isArray(facts) && facts.length === 0, `day facts before exception ${JSON.stringify(facts)}`);
      await capture(page, "01-before-exception");
      return { bands: list.length, weekend };
    });

    await scenario("02", "استثنای nonwork واقعی، روز کاری را به باند تعطیل تبدیل می‌کند", async () => {
      const saved = await saveException(page, {
        date: NONWORK_DATE,
        mode: "nonwork",
        system: "gregorian",
        total_work_hours: null,
        intervals: [],
      });
      assert(saved.date === NONWORK_DATE && saved.mode === "nonwork", `saved exception ${JSON.stringify(saved)}`);
      const facts = await readDayFacts(page);
      assert(facts.some((fact) => fact.date === NONWORK_DATE && fact.working === false), `projection ${JSON.stringify(facts)}`);

      await reloadApp(page);
      const list = await bands(page);
      const band = findBand(list, NONWORK_DATE);
      assert(band && band.kind === "holiday" && band.to === NONWORK_DATE && band.days === 1, `exception band ${JSON.stringify(band)}`);
      await capture(page, "02-nonwork-exception-band");
      return { band, facts: facts.length };
    });

    await scenario("03", "استثنای total-work-hours روی شنبه، باند آخر هفته را برمی‌دارد", async () => {
      const saved = await saveException(page, {
        date: WEEKEND_DATE,
        mode: "total-work-hours",
        system: "gregorian",
        total_work_hours: "4",
        intervals: [],
      });
      assert(saved.mode === "total-work-hours", `saved exception ${JSON.stringify(saved)}`);
      const facts = await readDayFacts(page);
      assert(facts.some((fact) => fact.date === WEEKEND_DATE && fact.working === true), `projection ${JSON.stringify(facts)}`);

      await reloadApp(page);
      const list = await bands(page);
      assert(!findBand(list, WEEKEND_DATE), `Saturday ${WEEKEND_DATE} must lose its weekend band`);
      const sunday = findBand(list, SUNDAY);
      assert(sunday && sunday.kind === "weekend" && sunday.to === SUNDAY, `Sunday band ${JSON.stringify(sunday)}`);
      const nonwork = findBand(list, NONWORK_DATE);
      assert(nonwork && nonwork.kind === "holiday", `the earlier exception band must persist ${JSON.stringify(nonwork)}`);
      await capture(page, "03-working-override");
      return { sunday, facts: facts.length };
    });

    await scenario("04", "حذف استثناها باندها را به وضعیت snapshot برمی‌گرداند", async () => {
      const first = await deleteException(page, NONWORK_DATE);
      const second = await deleteException(page, WEEKEND_DATE);
      assert(first === 200 && second === 200, `delete statuses ${first}/${second}`);
      const facts = await readDayFacts(page);
      assert(facts.length === 0, `day facts after cleanup ${JSON.stringify(facts)}`);

      await reloadApp(page);
      const list = await bands(page);
      assert(!findBand(list, NONWORK_DATE), `${NONWORK_DATE} band must disappear`);
      const weekend = findBand(list, WEEKEND_DATE);
      assert(weekend && weekend.kind === "weekend" && weekend.to === SUNDAY, `restored weekend band ${JSON.stringify(weekend)}`);
      await capture(page, "04-after-cleanup");
      return { bands: list.length };
    });

    await scenario("05", "هیچ استثنا، خطای کنسول یا پاسخ 5xx در سناریوها ثبت نشد", async () => {
      assert(exceptions.length === 0, `runtime exceptions: ${JSON.stringify(exceptions)}`);
      assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors)}`);
      assert(apiFailures.length === 0, `api failures: ${JSON.stringify(apiFailures)}`);
      return { exceptions: exceptions.length, consoleErrors: consoleErrors.length, apiFailures: apiFailures.length };
    });
  } finally {
    writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(evidenceDir, "report.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(outDir, "summary.md"), [
      "# Gantt calendar exceptions — browser evidence",
      "",
      `- Contract: ${report.contract}`,
      `- Preview: ${baseUrl}`,
      `- Git HEAD: ${report.gitHead}`,
      `- Calendar: ${CAL_ID}@${CAL_VERSION}`,
      "",
      ...scenarios.map((entry) => `## ${entry.id}. ${entry.name}`),
      ...scenarios.map((entry) => `- ${entry.status.toUpperCase()} — ${entry.name}`),
      "",
    ].join("\n"));
    chrome.stop();
  }

  log(`\nReport: ${join(outDir, "report.json")}`);
  if (scenarios.some((entry) => entry.status !== "pass")) process.exitCode = 1;
}

main().catch((error) => {
  process.stderr.write(`${error && error.stack ? error.stack : error}\n`);
  process.exitCode = 1;
});
