#!/usr/bin/env node
/**
 * Browser E2E for the Version 26 project threshold register.
 *
 * It drives the real local full-stack preview on project preview-rps-01 with
 * headless Chrome through the DevTools protocol. Every threshold definition and
 * monitoring run is read from and written to the real p6-threshold-api.v1 HTTP
 * routes and SQLite preview repository; no page fixture is injected and no API
 * response is mocked. Monitoring reads actual expense rows through the same
 * authoritative cost store the rest of the platform uses.
 *
 * Scenarios cover the empty register, definition creation, normal, warning and
 * issue monitoring levels, one issue per breach transition, immutable runs and
 * history, revision-guarded edit plus a stale 409, register filters, viewer
 * read-only authorization, the 1280x720 Persian right-to-left layout, and
 * deletion with a 404 read.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 node e2e/thresholds-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "thresholds-v26");
const evidenceDir = join(
  artifactsDir,
  "..",
  "..",
  "..",
  "..",
  "docs",
  "workspace",
  "evidence",
  `thresholds-v26-${evidenceDate}`,
);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const stamp = Date.now().toString(36).toUpperCase();
const thresholdId = `E2E-TH-${stamp}`;
const expenseWarningId = `E2E-THEXP-${stamp}-WARN`;
const expenseIssueId = `E2E-THEXP-${stamp}-ISSUE`;

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

const registerState = `(() => {
  const page = document.querySelector("[data-thresholds-page]");
  const cells = (row) => [...row.querySelectorAll("td")].map((cell) => (cell.textContent || "").trim());
  const thresholds = [...page?.querySelectorAll("[data-threshold-row]") ?? []].map((row) => {
    const values = cells(row);
    const id = row.dataset.thresholdId;
    return {
      id,
      name: row.querySelector("td span")?.textContent?.trim() ?? null,
      subject: values[1],
      parameter: values[2],
      bounds: values[3],
      levels: values[4],
      manager: values[5],
      status: values[6],
      selected: row.classList.contains("is-selected"),
      edit: Boolean(page.querySelector('[data-threshold-edit="' + id + '"]')),
      remove: Boolean(page.querySelector('[data-threshold-delete="' + id + '"]')),
    };
  });
  const runs = [...page?.querySelectorAll(".cp-threshold-runs tbody tr") ?? []].map((row) => {
    const values = cells(row);
    return { sequence: Number(values[0]), observed: values[1], level: values[2], issue: values[3], occurred: values[4] };
  });
  const history = [...page?.querySelectorAll(".cp-threshold-history li") ?? []].map((item) => item.textContent.trim());
  const form = page?.querySelector("[data-threshold-form]");
  const notice = page?.querySelector("[data-threshold-notice]");
  return {
    activeMenu: document.querySelector(".cp-workspace")?.dataset.activeMenu ?? null,
    heading: page?.querySelector(":scope > .cp-register-toolbar strong")?.textContent?.trim() ?? null,
    reading: (page?.textContent ?? "").includes("Reading project thresholds"),
    empty: [...page?.querySelectorAll(".cp-calendar-empty") ?? []].map((item) => item.textContent.trim()),
    thresholds,
    runs,
    history,
    notice: notice ? { kind: notice.dataset.state, text: notice.textContent.trim() } : null,
    newThreshold: Boolean(page?.querySelector('[data-threshold-action="new"]')),
    monitor: page?.querySelector("[data-threshold-monitor]")
      ? { id: page.querySelector("[data-threshold-monitor]").dataset.thresholdId, disabled: page.querySelector("[data-threshold-monitor]").disabled }
      : null,
    form: form ? {
      id: form.querySelector('input[name="threshold-id"]')?.value ?? null,
      readonly: Boolean(form.querySelector('input[name="threshold-id"]')?.hasAttribute("readonly")),
      name: form.querySelector('input[name="threshold-name"]')?.value ?? null,
      subject: form.querySelector('select[name="threshold-subject"]')?.value ?? null,
      parameter: form.querySelector('select[name="threshold-parameter"]')?.value ?? null,
      currency: form.querySelector('input[name="threshold-currency"]')?.value ?? null,
      lower: form.querySelector('input[name="threshold-lower"]')?.value ?? null,
      upper: form.querySelector('input[name="threshold-upper"]')?.value ?? null,
      warning: form.querySelector('input[name="threshold-warning"]')?.value ?? null,
      issue: form.querySelector('input[name="threshold-issue"]')?.value ?? null,
    } : null,
    page: Boolean(page),
  };
})()`;

async function capture(page, name) {
  const file = `thresholds-v26/${name}.png`;
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
  await sleep(600);
}

async function openThresholds(page) {
  await openMenu(page, "thresholds", "[data-thresholds-page] .cp-register-toolbar", "thresholds panel");
  await page.waitFor(
    `(() => {
      const page = document.querySelector("[data-thresholds-page]");
      return Boolean(page) && !page.textContent.includes("Reading project thresholds");
    })()`,
    "threshold register settled",
  );
  await sleep(400);
}

function thresholdUrl(suffix = "") {
  return `/api/projects/${PROJECT}/thresholds${suffix}`;
}

function costUrl(suffix) {
  return `/api/projects/${PROJECT}/cost${suffix}`;
}

async function api(page, method, path, body) {
  return page.evaluate(`(async () => {
    const response = await fetch(${JSON.stringify(path)}, {
      method: ${JSON.stringify(method)},
      headers: { "Content-Type": "application/json", "Idempotency-Key": "e2e-threshold-" + Math.random().toString(36).slice(2) },
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
  await sleep(1400);
  await setLanguage(page, "en");
}

async function createThreshold(page, values) {
  await page.click('[data-threshold-action="new"]');
  await page.waitForSelector("[data-threshold-form]", "threshold form");
  await page.setInput('[data-threshold-form] input[name="threshold-id"]', values.id);
  await page.setInput('[data-threshold-form] input[name="threshold-name"]', values.name);
  if (values.parameter) {
    await page.setSelect('[data-threshold-form] select[name="threshold-parameter"]', values.parameter);
    await page.waitForSelector("[data-threshold-form]", "threshold form after parameter change");
  }
  if (values.subject) {
    await page.setSelect('[data-threshold-form] select[name="threshold-subject"]', values.subject);
  }
  if (values.currency !== undefined) {
    await page.setInput('[data-threshold-form] input[name="threshold-currency"]', values.currency);
  }
  await page.setInput('[data-threshold-form] input[name="threshold-upper"]', values.upper);
  await page.setInput('[data-threshold-form] input[name="threshold-warning"]', values.warning);
  await page.setInput('[data-threshold-form] input[name="threshold-issue"]', values.issue);
  await page.setInput('[data-threshold-form] input[name="threshold-manager"]', values.manager);
  await page.click('[data-threshold-form] button[type="submit"]');
  await page.waitFor(
    `document.querySelector('[data-threshold-notice][data-state="ok"]')?.textContent?.includes("Threshold saved.") ?? false`,
    `threshold saved notice for ${values.id}`,
  );
  await page.waitForSelector(
    `[data-threshold-row][data-threshold-id="${values.id}"]`,
    `threshold row ${values.id}`,
  );
  await sleep(400);
}

async function selectThreshold(page, id) {
  await page.click(`[data-threshold-row][data-threshold-id="${id}"]`);
  await page.waitFor(
    `(() => {
      const page = document.querySelector("[data-thresholds-page]");
      if (!page) return false;
      const row = page.querySelector('[data-threshold-row][data-threshold-id="${id}"]');
      return Boolean(row?.classList.contains("is-selected")) &&
        !page.textContent.includes("Reading monitoring runs") &&
        !page.textContent.includes("Reading threshold history");
    })()`,
    `threshold ${id} details settled`,
  );
  await sleep(300);
}

async function runMonitor(page, id) {
  await page.click(`[data-threshold-monitor][data-threshold-id="${id}"]`);
  await page.waitFor(
    `document.querySelector('[data-threshold-notice]')?.textContent?.includes("Monitoring recorded") ?? false`,
    "monitoring notice",
  );
  await sleep(600);
  await page.waitFor(
    `(() => {
      const page = document.querySelector("[data-thresholds-page]");
      return Boolean(page) && !page.textContent.includes("Reading monitoring runs") && !page.textContent.includes("Reading threshold history");
    })()`,
    "monitoring runs settled",
  );
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
    contract: "cubi-thresholds-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    thresholdId,
    expenseWarningId,
    expenseIssueId,
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
    await openThresholds(page);

    await scenario("01", "فهرست آستانهٔ خالی و کنترل ساخت برای Planner نمایش داده می‌شود", async () => {
      const state = await page.evaluate(registerState);
      assert(state.page, "the thresholds page is missing");
      assert(state.activeMenu === "thresholds", `active menu is ${state.activeMenu}`);
      assert(state.heading === "Project Thresholds", `threshold heading is ${state.heading}`);
      assert(state.thresholds.length === 0, `register starts with ${state.thresholds.length} thresholds`);
      assert(state.empty.some((text) => /No thresholds are stored/.test(text)), `empty copy ${JSON.stringify(state.empty)}`);
      assert(state.newThreshold, "planner cannot open the threshold form");
      const stored = await api(page, "GET", thresholdUrl());
      assert(stored.status === 200 && stored.body.thresholds.length === 0, `server thresholds ${JSON.stringify(stored.body)}`);
      await capture(page, "01-empty-register");
      return { thresholds: 0 };
    });

    await scenario("02", "آستانهٔ هزینه با کران بالا، سطوح هشدار و مسئله و نسخهٔ ۱ ساخته می‌شود", async () => {
      await createThreshold(page, {
        id: thresholdId,
        name: "E2E expense ceiling",
        parameter: "expense_actual_total",
        subject: "cost",
        currency: "USD",
        upper: "100",
        warning: "10",
        issue: "50",
        manager: "preview-planner",
      });
      const state = await page.evaluate(registerState);
      const row = state.thresholds.find((item) => item.id === thresholdId);
      assert(row, `created threshold missing: ${JSON.stringify(state.thresholds)}`);
      assert(row.name === "E2E expense ceiling" && row.subject === "Cost" && row.status === "active", `row ${JSON.stringify(row)}`);
      assert(row.bounds === "— / 100" && row.levels === "10 / 50", `bounds/levels ${JSON.stringify(row)}`);
      const stored = await api(page, "GET", thresholdUrl(`/${encodeURIComponent(thresholdId)}`));
      assert(stored.status === 200 && stored.body.revision === 1, `stored threshold ${JSON.stringify(stored.body)}`);
      assert(stored.body.parameter === "expense_actual_total" && stored.body.currency === "USD", `stored parameter ${JSON.stringify(stored.body)}`);
      await capture(page, "02-created-threshold");
      return { row, stored: stored.body };
    });

    await scenario("03", "پایش اول مقدار واقعی صفر را عادی ثبت می‌کند و اجرای شمارهٔ ۱ را می‌سازد", async () => {
      await selectThreshold(page, thresholdId);
      const before = await page.evaluate(registerState);
      assert(before.monitor?.id === thresholdId, `monitor control ${JSON.stringify(before.monitor)}`);
      await runMonitor(page, thresholdId);
      const state = await page.evaluate(registerState);
      assert(state.runs.length === 1, `runs ${JSON.stringify(state.runs)}`);
      assert(state.runs[0].sequence === 1 && state.runs[0].observed === "0 USD", `run ${JSON.stringify(state.runs[0])}`);
      assert(state.runs[0].level === "Normal" && state.runs[0].issue === "—", `run level/issue ${JSON.stringify(state.runs[0])}`);
      assert(state.notice?.kind === "ok", `notice ${JSON.stringify(state.notice)}`);
      const server = await api(page, "GET", thresholdUrl(`/${encodeURIComponent(thresholdId)}/runs`));
      assert(server.status === 200 && server.body.runs.length === 1, `server runs ${JSON.stringify(server.body)}`);
      await capture(page, "03-normal-run");
      return { runs: state.runs };
    });

    await scenario("04", "هزینهٔ ۱۲۰ دلاری با عبور از کران بالا سطح هشدار ایجاد می‌کند", async () => {
      const created = await api(page, "POST", costUrl("/expenses"), {
        expense_id: expenseWarningId,
        name: "E2E threshold expense warning",
        category: "material",
        currency: "USD",
        expense_date: "2026-11-01",
        accrual_date: "2026-11-02",
        planned_amount: "120.00",
        actual_amount: "120.00",
        idempotency_key: `idem-${expenseWarningId}`,
      });
      assert(created.status === 200, `expense create ${JSON.stringify(created)}`);
      await runMonitor(page, thresholdId);
      const state = await page.evaluate(registerState);
      assert(state.runs.length === 2, `runs ${JSON.stringify(state.runs)}`);
      assert(state.runs[0].sequence === 2 && state.runs[0].observed === "120 USD", `warning run ${JSON.stringify(state.runs[0])}`);
      assert(state.runs[0].level === "Warning" && state.runs[0].issue === "—", `warning level ${JSON.stringify(state.runs[0])}`);
      await capture(page, "04-warning-run");
      return { run: state.runs[0] };
    });

    await scenario("05", "هزینهٔ ۲۰۰ دلاری سطح مسئله را عبور می‌دهد و یک مسئلهٔ واقعی با شناسهٔ اجرا می‌سازد", async () => {
      const created = await api(page, "POST", costUrl("/expenses"), {
        expense_id: expenseIssueId,
        name: "E2E threshold expense issue",
        category: "material",
        currency: "USD",
        expense_date: "2026-11-03",
        accrual_date: "2026-11-04",
        planned_amount: "200.00",
        actual_amount: "200.00",
        idempotency_key: `idem-${expenseIssueId}`,
      });
      assert(created.status === 200, `expense create ${JSON.stringify(created)}`);
      await runMonitor(page, thresholdId);
      const state = await page.evaluate(registerState);
      assert(state.runs.length === 3, `runs ${JSON.stringify(state.runs)}`);
      const run = state.runs[0];
      assert(run.sequence === 3 && run.observed === "320 USD" && run.level === "Issue", `issue run ${JSON.stringify(run)}`);
      const issueId = `THR-${thresholdId}-R3`;
      assert(run.issue === issueId, `generated issue ${run.issue}`);
      const issue = await api(page, "GET", `/api/projects/${PROJECT}/p6/issues/${encodeURIComponent(issueId)}`);
      assert(issue.status === 200, `generated issue read ${JSON.stringify(issue)}`);
      assert(issue.body.issue.status === "open" && issue.body.issue.priority === "high", `generated issue ${JSON.stringify(issue.body.issue)}`);
      assert(state.notice?.text.includes(issueId), `breach notice ${JSON.stringify(state.notice)}`);
      await capture(page, "05-issue-run");
      return { run, issue: issue.body.issue };
    });

    await scenario("06", "پایش تکراری در همان سطح مسئله، مسئلهٔ تکراری نمی‌سازد", async () => {
      await runMonitor(page, thresholdId);
      const state = await page.evaluate(registerState);
      assert(state.runs.length === 4, `runs ${JSON.stringify(state.runs)}`);
      assert(state.runs[0].sequence === 4 && state.runs[0].level === "Issue", `repeat run ${JSON.stringify(state.runs[0])}`);
      assert(state.runs[0].issue === "—", `repeat run generated ${state.runs[0].issue}`);
      await capture(page, "06-repeat-issue-run");
      return { run: state.runs[0] };
    });

    await scenario("07", "اجراهای تغییرناپذیر و تاریخچهٔ تعریف در پنل جزئیات خوانده می‌شوند", async () => {
      await selectThreshold(page, thresholdId);
      const state = await page.evaluate(registerState);
      assert(state.runs.length === 4, `displayed runs ${JSON.stringify(state.runs)}`);
      assert(state.runs.map((run) => run.level).join(",") === "Issue,Issue,Warning,Normal", `run order ${JSON.stringify(state.runs)}`);
      assert(state.history.length === 1 && state.history[0].includes("created"), `history ${JSON.stringify(state.history)}`);
      await capture(page, "07-runs-and-history");
      return { runs: state.runs.length, history: state.history };
    });

    await scenario("08", "ویرایش با نسخهٔ جاری ذخیره می‌شود و نوشتن کهنه ۴۰۹ برمی‌گرداند", async () => {
      await page.click(`[data-threshold-edit="${thresholdId}"]`);
      await page.waitForSelector("[data-threshold-form]", "edit threshold form");
      const form = await page.evaluate(registerState);
      assert(form.form?.readonly === true && form.form?.upper === "100", `edit form ${JSON.stringify(form.form)}`);
      await page.setInput('[data-threshold-form] input[name="threshold-upper"]', "2000");
      await page.click('[data-threshold-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-threshold-notice][data-state="ok"]')?.textContent?.includes("Threshold saved.") ?? false`,
        "threshold edit saved",
      );
      await sleep(600);
      let state = await page.evaluate(registerState);
      const row = state.thresholds.find((item) => item.id === thresholdId);
      assert(row?.bounds === "— / 2000", `edited row ${JSON.stringify(row)}`);
      const stored = await api(page, "GET", thresholdUrl(`/${encodeURIComponent(thresholdId)}`));
      assert(stored.body.revision === 2, `revision after edit ${stored.body.revision}`);
      const stale = await api(page, "PATCH", thresholdUrl(`/${encodeURIComponent(thresholdId)}`), {
        threshold_id: thresholdId,
        name: "E2E stale write",
        monitoring_subject: "cost",
        parameter: "expense_actual_total",
        currency: "USD",
        upper_threshold: "3000",
        warning_level: "10",
        issue_level: "50",
        status: "active",
        expected_revision: 1,
      });
      assert(stale.status === 409 && stale.body.code === "THRESHOLD_REVISION_CONFLICT", `stale write ${JSON.stringify(stale)}`);
      await capture(page, "08-edited-and-stale-conflict");
      return { row, staleStatus: stale.status };
    });

    await scenario("09", "صافی‌های موضوع، پارامتر، وضعیت و جستجو روی فهرست اعمال می‌شوند", async () => {
      await page.setSelect('select[name="threshold-subject-filter"]', "cost");
      await page.waitForSelector(`[data-threshold-row][data-threshold-id="${thresholdId}"]`, "filtered threshold row");
      await page.setSelect('select[name="threshold-parameter-filter"]', "expense_actual_total");
      await sleep(300);
      await page.setSelect('select[name="threshold-status-filter"]', "active");
      await sleep(300);
      await page.setInput('input[name="threshold-search-filter"]', "ceiling");
      await sleep(500);
      let state = await page.evaluate(registerState);
      assert(state.thresholds.length === 1 && state.thresholds[0].id === thresholdId, `filtered rows ${JSON.stringify(state.thresholds)}`);
      await page.setSelect('select[name="threshold-subject-filter"]', "quality");
      await sleep(500);
      state = await page.evaluate(registerState);
      assert(state.thresholds.length === 0, `quality filter rows ${JSON.stringify(state.thresholds)}`);
      assert(state.empty.some((text) => /No thresholds are stored/.test(text)), `filtered empty ${JSON.stringify(state.empty)}`);
      await capture(page, "09-filtered-register");
      await page.setSelect('select[name="threshold-subject-filter"]', "");
      await page.setInput('input[name="threshold-search-filter"]', "");
      await sleep(500);
      return { filtered: 1, empty: 0 };
    });

    await scenario("10", "پس از بارگذاری کامل صفحه، تعریف، اجراها و نسخه حفظ می‌شوند", async () => {
      await page.navigate(`${baseUrl}/app?project=preview-rps-01&view=visual`, "#cp-activity-grid tbody tr[data-activity-id]", "workspace reload");
      await sleep(1200);
      await openThresholds(page);
      const state = await page.evaluate(registerState);
      const row = state.thresholds.find((item) => item.id === thresholdId);
      assert(row?.bounds === "— / 2000", `row after reload ${JSON.stringify(row)}`);
      await selectThreshold(page, thresholdId);
      const selected = await page.evaluate(registerState);
      assert(selected.runs.length === 4, `runs after reload ${JSON.stringify(selected.runs)}`);
      assert(selected.history.length === 2, `history after reload ${JSON.stringify(selected.history)}`);
      await capture(page, "10-persisted-after-reload");
      return { row, runs: selected.runs.length, history: selected.history.length };
    });

    await scenario("11", "نقش Viewer فقط می‌خواند: بدون کنترل نوشتن و پاسخ مستقیم 403", async () => {
      await loginAs(page, "Viewer");
      await openThresholds(page);
      await selectThreshold(page, thresholdId);
      const state = await page.evaluate(registerState);
      assert(state.thresholds.some((item) => item.id === thresholdId), `viewer register ${JSON.stringify(state.thresholds)}`);
      assert(!state.newThreshold, "viewer received the new threshold button");
      assert(state.thresholds.every((item) => !item.edit && !item.remove), "viewer received a threshold write action");
      assert(state.monitor === null, "viewer received the monitoring action");
      const denied = await api(page, "POST", thresholdUrl(), {
        threshold_id: `${thresholdId}-VIEWER`,
        name: "Viewer must not write",
        monitoring_subject: "cost",
        parameter: "expense_actual_total",
        currency: "USD",
        upper_threshold: "10",
      });
      assert(denied.status === 403 && denied.body.code === "THRESHOLD_PERMISSION_DENIED", `viewer create ${JSON.stringify(denied)}`);
      const deniedMonitor = await api(page, "POST", thresholdUrl(`/${encodeURIComponent(thresholdId)}/monitor`), {});
      assert(deniedMonitor.status === 403 && deniedMonitor.body.code === "THRESHOLD_PERMISSION_DENIED", `viewer monitor ${JSON.stringify(deniedMonitor)}`);
      await capture(page, "11-viewer-denied");
      return { createStatus: denied.status, monitorStatus: deniedMonitor.status };
    });

    await scenario("12", "فهرست آستانه در 1280×720 فارسی، راست‌به‌چپ و بدون بریدگی رندر می‌شود", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await loginAs(page, "Planner");
      await setLanguage(page, "fa");
      await openThresholds(page);
      await selectThreshold(page, thresholdId);
      const layout = await page.evaluate(`(() => {
        const rect = (element) => {
          if (!element) return null;
          const bounds = element.getBoundingClientRect();
          return { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height };
        };
        const page = document.querySelector("[data-thresholds-page]");
        return {
          innerWidth,
          innerHeight,
          direction: getComputedStyle(document.querySelector(".cp-workspace") || document.body).direction,
          heading: page?.querySelector(":scope > .cp-register-toolbar strong")?.textContent?.trim() ?? null,
          toolbar: rect(page?.querySelector(":scope > .cp-register-toolbar")),
          panel: rect(page),
          table: rect(page?.querySelector(".cp-table-scroll")),
          rows: page?.querySelectorAll("[data-threshold-row]").length ?? 0,
          runs: page?.querySelectorAll(".cp-threshold-runs tbody tr").length ?? 0,
        };
      })()`);
      assert(layout.direction === "rtl", `workspace direction ${layout.direction}`);
      assert(layout.heading === "آستانه‌های پروژه", `Persian threshold heading ${layout.heading}`);
      assert(layout.toolbar && layout.toolbar.width > 0, "the threshold toolbar has no layout box at 1280x720");
      assert(layout.table && layout.table.width > 0, "the threshold table has no layout box at 1280x720");
      assert(layout.rows === 1 && layout.runs === 4, `rows at 1280x720: ${layout.rows}/${layout.runs}`);
      assert(layout.toolbar.x >= 0 && layout.toolbar.x + layout.toolbar.width <= layout.innerWidth + 1, `toolbar overflows: ${JSON.stringify(layout.toolbar)}`);
      assert(layout.table.x >= 0 && layout.table.x + layout.table.width <= layout.innerWidth + 1, `table overflows: ${JSON.stringify(layout.table)}`);
      await capture(page, "12-thresholds-1280x720-fa");
      return layout;
    });

    await scenario("13", "حذف آستانه با نسخهٔ جاری انجام می‌شود و خواندن بعدی ۴۰۴ است", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
      await setLanguage(page, "en");
      await openThresholds(page);
      await page.click(`[data-threshold-delete="${thresholdId}"]`);
      await page.waitFor(
        `document.querySelector('[data-threshold-notice][data-state="ok"]')?.textContent?.includes("Threshold deleted.") ?? false`,
        "threshold deleted notice",
      );
      await sleep(600);
      const state = await page.evaluate(registerState);
      assert(state.thresholds.length === 0, `thresholds after delete ${JSON.stringify(state.thresholds)}`);
      const gone = await api(page, "GET", thresholdUrl(`/${encodeURIComponent(thresholdId)}`));
      assert(gone.status === 404 && gone.body.code === "THRESHOLD_NOT_FOUND", `deleted read ${JSON.stringify(gone)}`);
      await capture(page, "13-deleted-threshold");
      return { remaining: state.thresholds.length, readStatus: gone.status };
    });

    assert(exceptions.length === 0, `uncaught page exceptions: ${JSON.stringify(exceptions.slice(0, 3))}`);
    assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors.slice(0, 3))}`);
    assert(apiFailures.length === 0, `API 5xx responses: ${JSON.stringify(apiFailures.slice(0, 3))}`);
  } finally {
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(outDir, "thresholds-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(evidenceDir, "thresholds-v26.json"), JSON.stringify(report, null, 2));
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
