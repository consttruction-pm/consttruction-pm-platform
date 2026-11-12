#!/usr/bin/env node
/**
 * Browser E2E for the Version 26 project report register.
 *
 * It drives the real local full-stack preview on project preview-rps-01 with
 * headless Chrome through the DevTools protocol. Definitions and runs are read
 * from and written to the real p6-report-api.v1 HTTP routes and SQLite preview
 * repository; no page fixture is injected and no API response is mocked. Each
 * run is materialized by the server from the authoritative activity, resource
 * and risk data, then stored verbatim.
 *
 * Scenarios cover the empty register and catalogue, definition creation, the
 * first run with exact rows and columns, immutable stored runs and history,
 * revision-guarded edits with a stale 409, server-side subject/search filters,
 * deletion with a 404 read, viewer read-only authorization with a direct 403,
 * and the 1280x720 Persian right-to-left layout.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 node e2e/reports-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "reports-v26");
const evidenceDir = join(
  artifactsDir,
  "..",
  "..",
  "..",
  "..",
  "docs",
  "workspace",
  "evidence",
  `reports-v26-${evidenceDate}`,
);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const stamp = Date.now().toString(36).toUpperCase();
const activityReportId = `E2E-RPT-ACT-${stamp}`;
const resourceReportId = `E2E-RPT-RES-${stamp}`;

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

const pageState = `(() => {
  const page = document.querySelector("[data-reports-page]");
  const cells = (row) => [...row.querySelectorAll("td")].map((cell) => (cell.textContent || "").trim());
  const rows = [...page?.querySelectorAll("[data-report-row]") ?? []].map((row) => ({
    id: row.dataset.reportId,
    cells: cells(row),
    selected: row.classList.contains("is-selected"),
  }));
  const detail = page?.querySelector("[data-report-detail]");
  const run = page?.querySelector("[data-report-run-preview]");
  const form = page?.querySelector("[data-report-form]");
  const notice = page?.querySelector("[data-report-notice]");
  return {
    activeMenu: document.querySelector(".cp-workspace")?.dataset.activeMenu ?? null,
    heading: page?.querySelector(":scope > .cp-register-toolbar strong")?.textContent?.trim() ?? null,
    reading: (page?.textContent ?? "").includes("Reading report definitions"),
    empty: page?.querySelector("[data-report-empty]")?.textContent?.trim() ?? null,
    rows,
    selected: page?.querySelector("[data-report-detail] > header span")?.textContent?.trim() ?? null,
    columns: [...detail?.querySelectorAll("[data-report-column]") ?? []].map((item) => item.dataset.reportColumn),
    newReport: Boolean(page?.querySelector('[data-report-action="new"]')),
    runAction: Boolean(page?.querySelector('[data-report-action="run"]')),
    edit: [...page?.querySelectorAll("[data-report-edit]") ?? []].map((item) => item.dataset.reportEdit),
    remove: [...page?.querySelectorAll("[data-report-delete]") ?? []].map((item) => item.dataset.reportDelete),
    notice: notice ? { kind: notice.dataset.state, text: notice.textContent.trim() } : null,
    form: form ? {
      id: form.querySelector('input[name="report-id"]')?.value ?? null,
      name: form.querySelector('input[name="report-name"]')?.value ?? null,
      subject: form.querySelector('select[name="report-subject"]')?.value ?? null,
      checked: [...form.querySelectorAll("[data-report-field]")].filter((input) => input.checked).map((input) => input.value),
    } : null,
    run: run ? {
      meta: run.querySelector("[data-report-run-meta]")?.textContent?.trim() ?? null,
      columns: [...run.querySelectorAll("thead th")].map((cell) => cell.textContent.trim()),
      rows: [...run.querySelectorAll("[data-report-run-row]")].map((row) => cells(row)),
    } : null,
    history: [...page?.querySelectorAll("[data-report-run-item]") ?? []].map((item) => ({
      runId: item.dataset.runId,
      text: item.textContent.trim(),
    })),
  };
})()`;

async function capture(page, name) {
  const file = `reports-v26/${name}.png`;
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

async function openReports(page) {
  await openMenu(page, "reports", "[data-reports-page] .cp-register-toolbar", "reports panel");
  await page.waitFor(
    `(() => {
      const page = document.querySelector("[data-reports-page]");
      return Boolean(page) && !page.textContent.includes("Reading report definitions");
    })()`,
    "report register settled",
  );
  await sleep(400);
}

function reportsUrl(suffix = "") {
  return `/api/projects/${PROJECT}/reports${suffix}`;
}

async function api(page, method, path, body) {
  return page.evaluate(`(async () => {
    const response = await fetch(${JSON.stringify(path)}, {
      method: ${JSON.stringify(method)},
      headers: { "Content-Type": "application/json", "Idempotency-Key": "e2e-report-" + Math.random().toString(36).slice(2) },
      ${body === undefined ? "" : `body: JSON.stringify(${JSON.stringify(body)}),`}
    });
    return { status: response.status, body: await response.json() };
  })()`, { awaitPromise: true });
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
  await sleep(1200);
  await setLanguage(page, "en");
}

async function fillReport(page, values) {
  if (values.id !== undefined) await page.setInput('[data-report-form] input[name="report-id"]', values.id);
  if (values.name !== undefined) await page.setInput('[data-report-form] input[name="report-name"]', values.name);
  if (values.description !== undefined) await page.setInput("[data-report-form] textarea[name='report-description']", values.description);
  if (values.subject) {
    await page.setSelect('[data-report-form] select[name="report-subject"]', values.subject);
    await sleep(250);
  }
  if (values.columns) {
    const applied = await page.evaluate(`(() => {
      const wanted = ${JSON.stringify(values.columns)};
      const fields = [...document.querySelectorAll("[data-report-form] [data-report-field]")];
      if (fields.length !== 8 && fields.length !== 7) return { ok: false, fields: fields.length };
      for (const input of fields) {
        const should = wanted.includes(input.value);
        if (input.checked !== should) {
          input.checked = should;
          input.dispatchEvent(new Event("change", { bubbles: true }));
        }
      }
      const checked = [...document.querySelectorAll("[data-report-form] [data-report-field]")].filter((input) => input.checked).map((input) => input.value);
      return { ok: JSON.stringify(checked) === JSON.stringify(wanted), checked };
    })()`);
    assert(applied.ok, `report columns were not applied: ${JSON.stringify(applied)}`);
  }
}

async function selectReport(page, id) {
  await page.click(`[data-report-row][data-report-id="${id}"]`);
  await page.waitFor(
    `(() => {
      const page = document.querySelector("[data-reports-page]");
      if (!page) return false;
      const row = page.querySelector('[data-report-row][data-report-id="${id}"]');
      return Boolean(row?.classList.contains("is-selected")) &&
        !page.textContent.includes("Reading run history");
    })()`,
    `report ${id} details settled`,
  );
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
    contract: "cubi-reports-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    activityReportId,
    resourceReportId,
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
    await openReports(page);

    await scenario("01", "فهرست گزارش خالی است و کاتالوگ سه موضوع و کنترل ساخت دارد", async () => {
      const state = await page.evaluate(pageState);
      assert(state.activeMenu === "reports", `active menu is ${state.activeMenu}`);
      assert(state.heading === "Project Reports", `report heading is ${state.heading}`);
      assert(state.rows.length === 0, `register starts with ${state.rows.length} reports`);
      assert((state.empty ?? "").includes("No report definitions are stored"), `empty copy ${state.empty}`);
      assert(state.newReport, "planner cannot open the report form");
      const catalogue = await api(page, "GET", reportsUrl("/catalogue"));
      assert(catalogue.status === 200 && catalogue.body.contract_version === "p6-report-api.v1", `catalogue ${JSON.stringify(catalogue)}`);
      assert(catalogue.body.subjects.length === 3, `catalogue subjects ${catalogue.body.subjects.length}`);
      assert(catalogue.body.subjects.map((item) => item.subject).join(",") === "activities,resources,risks", `catalogue order ${JSON.stringify(catalogue.body.subjects)}`);
      await capture(page, "01-empty-register");
      return { reports: 0, subjects: catalogue.body.subjects.map((item) => item.subject) };
    });

    await scenario("02", "تعریف گزارش فعالیت با ستون‌های انتخابی ساخته و بازخوانی می‌شود", async () => {
      await page.click('[data-report-action="new"]');
      await page.waitForSelector("[data-report-form]", "report form");
      const draft = await page.evaluate(pageState);
      assert(draft.form?.subject === "activities", `default subject ${draft.form?.subject}`);
      await fillReport(page, {
        id: activityReportId,
        name: "E2E Activity Status",
        description: "E2E report created against the real report register.",
        subject: "activities",
        columns: ["activity_id", "name", "status", "percent_complete"],
      });
      await page.click('[data-report-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-report-notice][data-state="ok"]')?.textContent?.includes("Report saved.") ?? false`,
        "report saved notice",
      );
      await page.waitForSelector(`[data-report-row][data-report-id="${activityReportId}"]`, `report row ${activityReportId}`);
      await sleep(400);
      const state = await page.evaluate(pageState);
      const row = state.rows.find((item) => item.id === activityReportId);
      assert(row, `created report missing: ${JSON.stringify(state.rows)}`);
      assert(row.cells[1] === "Activities", `row subject ${JSON.stringify(row.cells)}`);
      assert(row.cells[2] === "4", `row columns ${JSON.stringify(row.cells)}`);
      assert(row.cells[3] === "1", `row revision ${JSON.stringify(row.cells)}`);
      const stored = await api(page, "GET", reportsUrl(`/${activityReportId}`));
      assert(stored.status === 200 && stored.body.report_id === activityReportId, `stored definition ${JSON.stringify(stored)}`);
      assert(stored.body.record_revision === 1 && stored.body.subject === "activities", `stored revision ${JSON.stringify(stored.body)}`);
      assert(stored.body.columns.join(",") === "activity_id,name,status,percent_complete", `stored columns ${JSON.stringify(stored.body.columns)}`);
      await capture(page, "02-created-definition");
      return { revision: stored.body.record_revision, columns: stored.body.columns };
    });

    await scenario("03", "اجرایگزارش ۱۴ ردیف دادهٔ مرجع را با ستون‌های دقیق ذخیره می‌کند", async () => {
      await selectReport(page, activityReportId);
      const selected = await page.evaluate(pageState);
      assert(selected.columns.join(",") === "activity_id,name,status,percent_complete", `detail columns ${JSON.stringify(selected.columns)}`);
      assert(selected.runAction, "planner cannot run the report");
      await page.click('[data-report-action="run"]');
      await page.waitFor(
        `document.querySelector('[data-report-run-preview]')?.querySelectorAll("[data-report-run-row]")?.length === 14`,
        "fourteen activity rows",
      );
      await sleep(400);
      const state = await page.evaluate(pageState);
      assert(state.notice?.kind === "ok" && state.notice.text.includes("Report run stored."), `run notice ${JSON.stringify(state.notice)}`);
      assert(state.run.columns.join(",") === "activity_id,name,status,percent_complete", `run header ${JSON.stringify(state.run.columns)}`);
      assert(state.run.rows.length === 14, `run rows ${state.run.rows.length}`);
      assert(state.run.rows.every((row) => row.length === 4 && row[0]), `run cell shape ${JSON.stringify(state.run.rows.slice(0, 2))}`);
      assert(state.run.meta.includes(`RUN-${activityReportId}-1`), `run meta ${state.run.meta}`);
      assert(state.run.meta.includes("14 rows"), `run meta row count ${state.run.meta}`);
      assert(state.history.length === 1 && state.history[0].runId.endsWith("-1"), `history ${JSON.stringify(state.history)}`);
      const runs = await api(page, "GET", reportsUrl(`/${activityReportId}/runs`));
      assert(runs.status === 200 && runs.body.runs.length === 1, `server runs ${JSON.stringify(runs.body)}`);
      assert(runs.body.runs[0].row_count === 14, `server run row count ${JSON.stringify(runs.body.runs[0])}`);
      await capture(page, "03-first-run-output");
      return { rows: state.run.rows.length, runId: state.history[0].runId };
    });

    await scenario("04", "اجرای دوم ذخیره می‌شود و خروجی اجرای اول بدون تغییر بازخوانی می‌شود", async () => {
      await page.click('[data-report-action="run"]');
      await page.waitFor(
        `document.querySelectorAll("[data-report-run-history] [data-report-run-item]").length === 2`,
        "second stored run",
      );
      await sleep(400);
      const afterSecond = await page.evaluate(pageState);
      assert(afterSecond.history.length === 2, `history after second run ${JSON.stringify(afterSecond.history)}`);
      assert(afterSecond.history[0].runId.endsWith("-2"), `newest run ${JSON.stringify(afterSecond.history[0])}`);
      const firstRunId = afterSecond.history[1].runId;
      await page.click(`[data-report-run-item][data-run-id="${firstRunId}"]`);
      await page.waitFor(
        `document.querySelector("[data-report-run-meta]")?.textContent?.includes(${JSON.stringify(firstRunId)}) ?? false`,
        "stored first run",
      );
      await sleep(300);
      const stored = await page.evaluate(pageState);
      assert(stored.run.rows.length === 14, `stored run rows ${stored.run.rows.length}`);
      assert(stored.run.columns.join(",") === "activity_id,name,status,percent_complete", `stored run columns ${JSON.stringify(stored.run.columns)}`);
      assert(stored.run.meta.includes("definition revision 1"), `stored run revision ${stored.run.meta}`);
      const readback = await api(page, "GET", reportsUrl(`/${activityReportId}/runs/${firstRunId}`));
      assert(readback.status === 200 && readback.body.run_id === firstRunId, `run readback ${JSON.stringify(readback)}`);
      assert(readback.body.rows.length === 14, `run readback rows ${readback.body.rows.length}`);
      await capture(page, "04-stored-run-readback");
      return { runs: afterSecond.history.length, readback: firstRunId };
    });

    await scenario("05", "ویرایش با نسخهٔ ۲ اعمال می‌شود و نوشتن با نسخهٔ کهنه ۴۰۹ است", async () => {
      await selectReport(page, activityReportId);
      await page.click(`[data-report-edit="${activityReportId}"]`);
      await page.waitForSelector("[data-report-form]", "edit report form");
      await page.setInput('[data-report-form] input[name="report-name"]', "E2E Activity Status v2");
      const applied = await page.evaluate(`(() => {
        const wanted = ["activity_id", "name", "expected_finish", "percent_complete"];
        for (const input of document.querySelectorAll("[data-report-form] [data-report-field]")) {
          const should = wanted.includes(input.value);
          if (input.checked !== should) {
            input.checked = should;
            input.dispatchEvent(new Event("change", { bubbles: true }));
          }
        }
        return [...document.querySelectorAll("[data-report-form] [data-report-field]")].filter((input) => input.checked).map((input) => input.value);
      })()`);
      assert(applied.join(",") === "activity_id,name,expected_finish,percent_complete", `edited columns ${JSON.stringify(applied)}`);
      await page.click('[data-report-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-reports-page]')?.textContent?.includes("E2E Activity Status v2") ?? false`,
        "updated report name",
      );
      await sleep(500);
      const state = await page.evaluate(pageState);
      const row = state.rows.find((item) => item.id === activityReportId);
      assert(row?.cells[3] === "2", `revision after edit ${JSON.stringify(row)}`);
      const stale = await api(page, "PATCH", reportsUrl(`/${activityReportId}`), {
        name: "stale write",
        subject: "activities",
        columns: ["activity_id"],
        expected_revision: 1,
      });
      assert(stale.status === 409 && stale.body.code === "REPORT_REVISION_CONFLICT", `stale update ${JSON.stringify(stale)}`);
      await selectReport(page, activityReportId);
      await page.click('[data-report-action="run"]');
      await page.waitFor(
        `document.querySelector('[data-report-run-preview]')?.querySelectorAll("[data-report-run-row]")?.length === 14`,
        "run after edit",
      );
      await sleep(400);
      const rerun = await page.evaluate(pageState);
      assert(rerun.run.columns.join(",") === "activity_id,name,expected_finish,percent_complete", `rerun columns ${JSON.stringify(rerun.run.columns)}`);
      assert(rerun.run.meta.includes("definition revision 2"), `rerun revision ${rerun.run.meta}`);
      assert(rerun.history.length === 3, `history after rerun ${JSON.stringify(rerun.history)}`);
      await capture(page, "05-revised-run");
      return { revision: 2, staleStatus: stale.status, history: rerun.history.length };
    });

    await scenario("06", "گزارش منابع ساخته می‌شود و فیلتر موضوع و جستجو در سرور اعمال می‌شود", async () => {
      await page.click('[data-report-action="new"]');
      await page.waitForSelector("[data-report-form]", "resource report form");
      await fillReport(page, {
        id: resourceReportId,
        name: "E2E Resource Directory",
        description: "Resource subject coverage.",
        subject: "resources",
        columns: ["resource_id", "name", "resource_type", "is_active"],
      });
      await page.click('[data-report-form] button[type="submit"]');
      await page.waitForSelector(`[data-report-row][data-report-id="${resourceReportId}"]`, "resource report row");
      await sleep(500);
      await page.setSelect('select[name="report-subject-filter"]', "resources");
      await page.waitFor(
        `(() => {
          const rows = [...document.querySelectorAll("[data-report-row]")];
          return rows.length === 1 && rows[0].dataset.reportId === ${JSON.stringify(resourceReportId)};
        })()`,
        "resources subject filter",
      );
      const filtered = await page.evaluate(pageState);
      assert(filtered.rows.length === 1 && filtered.rows[0].id === resourceReportId, `subject filter ${JSON.stringify(filtered.rows)}`);
      const serverFiltered = await api(page, "GET", reportsUrl("?subject=resources"));
      assert(serverFiltered.status === 200 && serverFiltered.body.reports.length === 1, `server subject filter ${JSON.stringify(serverFiltered.body)}`);
      await page.setSelect('select[name="report-subject-filter"]', "");
      await page.waitFor(
        `document.querySelectorAll("[data-report-row]").length === 2`,
        "cleared subject filter",
      );
      await page.setInput('input[name="report-search-filter"]', "Activity Status");
      await page.waitFor(
        `(() => {
          const rows = [...document.querySelectorAll("[data-report-row]")];
          return rows.length === 1 && rows[0].dataset.reportId === ${JSON.stringify(activityReportId)};
        })()`,
        "search filter",
      );
      const searched = await page.evaluate(pageState);
      assert(searched.rows.length === 1 && searched.rows[0].id === activityReportId, `search filter ${JSON.stringify(searched.rows)}`);
      const serverSearch = await api(page, "GET", reportsUrl("?search=Activity%20Status"));
      assert(serverSearch.status === 200 && serverSearch.body.reports.length === 1, `server search ${JSON.stringify(serverSearch.body)}`);
      await page.setInput('input[name="report-search-filter"]', "");
      await page.waitFor(
        `document.querySelectorAll("[data-report-row]").length === 2`,
        "cleared search filter",
      );
      await selectReport(page, resourceReportId);
      await page.click('[data-report-action="run"]');
      await page.waitFor(
        `document.querySelector('[data-report-run-preview]')?.querySelectorAll("[data-report-run-row]")?.length === 1`,
        "resource report run",
      );
      const run = await page.evaluate(pageState);
      assert(run.run.columns.join(",") === "resource_id,name,resource_type,is_active", `resource run header ${JSON.stringify(run.run.columns)}`);
      assert(run.run.rows.length === 1 && run.run.rows[0][0] === "RPS-CIVIL-CREW", `resource run row ${JSON.stringify(run.run.rows)}`);
      assert(run.run.rows[0][3] === "Yes", `resource active cell ${JSON.stringify(run.run.rows[0])}`);
      await capture(page, "06-resource-report");
      return { reports: 2, resourceRows: run.run.rows.length };
    });

    await scenario("07", "حذف گزارش با نسخهٔ جاری انجام می‌شود و خواندن بعدی ۴۰۴ است", async () => {
      await page.click(`[data-report-delete="${resourceReportId}"]`);
      await page.waitFor(
        `document.querySelector('[data-report-notice][data-state="ok"]')?.textContent?.includes("Report deleted.") ?? false`,
        "report deleted notice",
      );
      await sleep(600);
      const state = await page.evaluate(pageState);
      assert(!state.rows.some((item) => item.id === resourceReportId), `deleted report still listed ${JSON.stringify(state.rows)}`);
      const gone = await api(page, "GET", reportsUrl(`/${resourceReportId}`));
      assert(gone.status === 404 && gone.body.code === "REPORT_NOT_FOUND", `deleted read ${JSON.stringify(gone)}`);
      await capture(page, "07-deleted-report");
      return { remaining: state.rows.length, readStatus: gone.status };
    });

    await scenario("08", "نقش Viewer فقط می‌خواند: اجرا مجاز و نوشتن مستقیم ۴۰۳ است", async () => {
      await loginAs(page, "Viewer");
      await openReports(page);
      await selectReport(page, activityReportId);
      const state = await page.evaluate(pageState);
      assert(state.rows.some((item) => item.id === activityReportId), `viewer register ${JSON.stringify(state.rows)}`);
      assert(!state.newReport, "viewer received the new report button");
      assert(state.edit.length === 0 && state.remove.length === 0, `viewer received write actions ${JSON.stringify({ edit: state.edit, remove: state.remove })}`);
      assert(state.runAction, "viewer cannot run a stored report");
      await page.click('[data-report-action="run"]');
      await page.waitFor(
        `document.querySelector('[data-report-run-preview]')?.querySelectorAll("[data-report-run-row]")?.length === 14`,
        "viewer report run",
      );
      const output = await page.evaluate(pageState);
      assert(output.run.rows.length === 14, `viewer output rows ${output.run.rows.length}`);
      const denied = await api(page, "POST", reportsUrl(), {
        report_id: `${activityReportId}-VIEWER`,
        name: "Viewer must not write",
        subject: "activities",
        columns: ["activity_id"],
      });
      assert(denied.status === 403 && denied.body.code === "REPORT_PERMISSION_DENIED", `viewer create ${JSON.stringify(denied)}`);
      await capture(page, "08-viewer-read-only");
      return { createStatus: denied.status, runRows: output.run.rows.length };
    });

    await scenario("09", "پنجرهٔ گزارش در 1280×720 فارسی، راست‌به‌چپ و بدون سرریز رندر می‌شود", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await loginAs(page, "Planner");
      await setLanguage(page, "fa");
      await openReports(page);
      await selectReport(page, activityReportId);
      const layout = await page.evaluate(`(() => {
        const rect = (element) => {
          if (!element) return null;
          const bounds = element.getBoundingClientRect();
          return { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height };
        };
        const page = document.querySelector("[data-reports-page]");
        return {
          innerWidth,
          innerHeight,
          direction: getComputedStyle(document.querySelector(".cp-workspace") || document.body).direction,
          heading: page?.querySelector(":scope > .cp-register-toolbar strong")?.textContent?.trim() ?? null,
          toolbar: rect(page?.querySelector(":scope > .cp-register-toolbar")),
          panel: rect(page),
          register: rect(page?.querySelector(".cp-report-register")),
          detail: rect(page?.querySelector("[data-report-detail]")),
          text: page?.textContent ?? "",
          rows: page?.querySelectorAll("[data-report-row]").length ?? 0,
        };
      })()`);
      assert(layout.direction === "rtl", `workspace direction ${layout.direction}`);
      assert(layout.heading === "گزارش‌های پروژه", `Persian report heading ${layout.heading}`);
      assert(layout.toolbar && layout.toolbar.width > 0, "the report toolbar has no layout box at 1280x720");
      assert(layout.register && layout.register.width > 0, "the report register has no layout box at 1280x720");
      assert(layout.detail && layout.detail.width > 0, "the report detail has no layout box at 1280x720");
      assert(layout.rows === 1, `rows at 1280x720: ${layout.rows}`);
      assert(layout.toolbar.x >= 0 && layout.toolbar.x + layout.toolbar.width <= layout.innerWidth + 1, `toolbar overflows: ${JSON.stringify(layout.toolbar)}`);
      assert(layout.panel.x >= 0 && layout.panel.x + layout.panel.width <= layout.innerWidth + 1, `panel overflows: ${JSON.stringify(layout.panel)}`);
      assert(!/Oracle|Primavera|P6/i.test(layout.text), "the report window leaks external product branding");
      await capture(page, "09-reports-1280x720-fa");
      return { direction: layout.direction, heading: layout.heading, rows: layout.rows };
    });

    assert(exceptions.length === 0, `uncaught page exceptions: ${JSON.stringify(exceptions.slice(0, 3))}`);
    assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors.slice(0, 3))}`);
    assert(apiFailures.length === 0, `API 5xx responses: ${JSON.stringify(apiFailures.slice(0, 3))}`);
  } finally {
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(outDir, "reports-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(evidenceDir, "reports-v26.json"), JSON.stringify(report, null, 2));
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
