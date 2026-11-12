#!/usr/bin/env node
/**
 * Browser E2E for the Version 26 project budget register.
 *
 * It drives the real local full-stack preview on project preview-rps-01 with
 * headless Chrome through the DevTools protocol. Every number is read from and
 * written to the real p6-budget-api.v1 HTTP routes and the SQLite preview
 * repository; no page fixture is injected and no API response is mocked.
 *
 * Scenarios cover the empty register, creating a budget line, submitting a
 * pending change, the planner approval gate, administrator approval and
 * rejection, funding creation and revision-guarded funding edit, the derived
 * per-currency summary, persistence after a full page reload, viewer
 * read-only authorization, and the 1280x720 Persian right-to-left layout.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 node e2e/budget-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "budget-v26");
const evidenceDir = join(
  artifactsDir,
  "..",
  "..",
  "..",
  "..",
  "docs",
  "workspace",
  "evidence",
  `budget-v26-${evidenceDate}`,
);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const stamp = Date.now().toString(36).toUpperCase();
const lineId = `E2E-BL-${stamp}`;
const changeId = `E2E-BC-${stamp}`;
const rejectedId = `E2E-BC-${stamp}-R`;
const fundingId = `E2E-FS-${stamp}`;

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

const budgetState = `(() => {
  const page = document.querySelector("[data-cost-page]");
  const root = [...document.querySelectorAll("[data-budget-panel]")].find((element) => element.getClientRects().length > 0)
    ?? document.querySelector("[data-budget-panel]");
  const cells = (row) => [...row.querySelectorAll("td")].map((cell) => (cell.textContent || "").trim());
  const summaries = [...root?.querySelectorAll("[data-budget-summary-currency]") ?? []].map((row) => {
    const values = cells(row);
    return {
      currency: row.dataset.budgetSummaryCurrency,
      original: values[1],
      approved: values[2],
      current: values[3],
      pending: values[4],
      funding: values[5],
      balance: values[6],
    };
  });
  const lines = [...root?.querySelectorAll("[data-budget-line]") ?? []].map((row) => {
    const values = cells(row);
    return {
      id: row.dataset.budgetLine,
      description: values[1],
      currency: values[2],
      original: values[3],
      costAccount: values[4],
      revision: values[5],
      selected: row.classList.contains("is-selected"),
    };
  });
  const changes = [...root?.querySelectorAll("[data-budget-change]") ?? []].map((row) => {
    const values = cells(row);
    return { id: row.dataset.budgetChange, amount: values[1], reason: values[2], status: values[3], revision: values[4] };
  });
  const funding = [...root?.querySelectorAll("[data-budget-funding-id]") ?? []].map((row) => {
    const values = cells(row);
    return { id: row.dataset.budgetFundingId, name: values[1], type: values[2], currency: values[3], amount: values[4], revision: values[6] };
  });
  const history = [...root?.querySelectorAll("[data-budget-history] tbody tr") ?? []].map((row) => {
    const values = cells(row);
    return { revision: values[0], event: values[1], actor: values[2], reason: values[4] };
  });
  return {
    activeMenu: document.querySelector(".cp-workspace")?.dataset.activeMenu ?? null,
    heading: root?.querySelector(":scope > .cp-register-toolbar strong")?.textContent?.trim() ?? null,
    reading: (root?.textContent ?? "").includes("Reading the stored budget"),
    empty: [...root?.querySelectorAll(".cp-register-notice") ?? []].map((item) => item.textContent.trim()),
    summaries,
    lines,
    changes,
    funding,
    history,
    lineForm: root?.querySelector("[data-budget-line-form]")
      ? {
          id: root.querySelector('input[name="budget-line-id"]')?.value ?? null,
          readonly: Boolean(root.querySelector('input[name="budget-line-id"]')?.hasAttribute("readonly")),
          description: root.querySelector('input[name="budget-description"]')?.value ?? null,
          currency: root.querySelector('input[name="budget-currency"]')?.value ?? null,
          original: root.querySelector('input[name="budget-original"]')?.value ?? null,
        }
      : null,
    changeForm: Boolean(root?.querySelector("[data-budget-change-form]")),
    fundingForm: Boolean(root?.querySelector("[data-budget-funding-form]")),
    notice: root?.querySelector("[data-budget-notice]")
      ? { kind: root.querySelector("[data-budget-notice]").dataset.state, text: root.querySelector("[data-budget-notice]").textContent.trim() }
      : null,
    newLine: Boolean(root?.querySelector('[data-budget-action="new-line"]')),
    newFunding: Boolean(root?.querySelector('[data-budget-action="new-funding"]')),
    editLine: Boolean(root?.querySelector('[data-budget-action="edit-line"]')),
    approveButtons: [...root?.querySelectorAll('[data-budget-action="approve"]') ?? []].map((button) => button.dataset.budgetChangeId),
    rejectButtons: [...root?.querySelectorAll('[data-budget-action="reject"]') ?? []].map((button) => button.dataset.budgetChangeId),
    page: Boolean(page),
  };
})()`;

async function capture(page, name) {
  const file = `budget-v26/${name}.png`;
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

async function openBudget(page) {
  await openMenu(page, "cost", "[data-cost-page] [data-budget-panel] .cp-register-toolbar", "budget panel");
  await page.waitFor(
    `(() => {
      const root = [...document.querySelectorAll("[data-budget-panel]")].find((element) => element.getClientRects().length > 0);
      return Boolean(root) && !root.textContent.includes("Reading the stored budget");
    })()`,
    "budget panel settled",
  );
  await sleep(400);
}

function budgetUrl(suffix = "") {
  return `/api/projects/${PROJECT}/budget${suffix}`;
}

async function api(page, method, path, body) {
  return page.evaluate(`(async () => {
    const response = await fetch(${JSON.stringify(path)}, {
      method: ${JSON.stringify(method)},
      headers: { "Content-Type": "application/json", "Idempotency-Key": "e2e-budget-" + Math.random().toString(36).slice(2) },
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
    contract: "cubi-budget-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    lineId,
    changeId,
    rejectedId,
    fundingId,
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
    await openBudget(page);

    await scenario("01", "پنل بودجهٔ خالی، خلاصهٔ ارزی و فرم‌های مجاز برای Planner نمایش داده می‌شود", async () => {
      const state = await page.evaluate(budgetState);
      assert(state.page, "the cost page is missing");
      assert(state.activeMenu === "cost", `active menu is ${state.activeMenu}`);
      assert(state.heading === "Project Budget", `budget heading is ${state.heading}`);
      assert(state.lines.length === 0, `budget starts with ${state.lines.length} lines`);
      assert(state.funding.length === 0, `budget starts with ${state.funding.length} funding rows`);
      assert(state.summaries.length === 0, `budget starts with ${state.summaries.length} summaries`);
      assert(state.empty.some((text) => /No budget or funding is stored/.test(text)), `empty copy ${JSON.stringify(state.empty)}`);
      assert(state.newLine && state.newFunding, "planner cannot open the budget forms");
      const server = await api(page, "GET", budgetUrl("/summary"));
      assert(server.status === 200 && server.body.currencies.length === 0, `server summary ${JSON.stringify(server.body)}`);
      await capture(page, "01-empty-budget");
      return { lines: 0, funding: 0, summaries: 0 };
    });

    await scenario("02", "ایجاد ردیف بودجه از فرم واقعی با نسخهٔ ۱ و مبلغ دو رقم اعشار", async () => {
      await page.click('[data-budget-action="new-line"]');
      await page.waitForSelector("[data-budget-line-form]", "budget line form");
      await page.setInput('[data-budget-line-form] input[name="budget-line-id"]', lineId);
      await page.setInput('[data-budget-line-form] input[name="budget-description"]', "E2E concrete works");
      await page.setInput('[data-budget-line-form] input[name="budget-currency"]', "USD");
      await page.setInput('[data-budget-line-form] input[name="budget-original"]', "1000.00");
      await page.setInput('[data-budget-line-form] input[name="budget-cost-account"]', "CA-1");
      await page.setInput('[data-budget-line-form] input[name="budget-period"]', "2026");
      await page.click('[data-budget-line-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-budget-notice][data-state="ok"]')?.textContent?.includes("The budget line was saved") ?? false`,
        "budget line saved notice",
      );
      await page.waitForSelector(`[data-budget-line="${lineId}"]`, "budget line row");
      await sleep(400);
      const state = await page.evaluate(budgetState);
      const row = state.lines.find((item) => item.id === lineId);
      assert(row, `created line missing: ${JSON.stringify(state.lines)}`);
      assert(row.revision === "R1" && row.original === "1000.00" && row.currency === "USD", `line row ${JSON.stringify(row)}`);
      const summary = state.summaries.find((item) => item.currency === "USD");
      assert(summary?.original === "1000.00" && summary?.current === "1000.00", `summary after create ${JSON.stringify(summary)}`);
      const stored = await api(page, "GET", budgetUrl(`/lines/${encodeURIComponent(lineId)}`));
      assert(stored.status === 200 && stored.body.revision === 1, `stored line ${JSON.stringify(stored.body)}`);
      assert(stored.body.original_amount === "1000.00", `stored amount ${stored.body.original_amount}`);
      await capture(page, "02-created-line");
      return { row, stored: stored.body };
    });

    await scenario("03", "ثبت تغییر از فرم، وضعیت pending و خلاصهٔ بودجهٔ جاری بدون تغییر", async () => {
      await page.click(`[data-budget-action="new-change"][data-budget-line-id="${lineId}"]`);
      await page.waitForSelector("[data-budget-change-form]", "change form");
      await page.setInput('[data-budget-change-form] input[name="budget-change-id"]', changeId);
      await page.setInput('[data-budget-change-form] input[name="budget-change-amount"]', "-100.00");
      await page.setInput('[data-budget-change-form] input[name="budget-change-reason"]', "Reduced scope");
      await page.click('[data-budget-change-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-budget-notice][data-state="ok"]')?.textContent?.includes("submitted as pending") ?? false`,
        "change submitted notice",
      );
      await page.waitForSelector(`[data-budget-change="${changeId}"] [data-budget-change-status="pending"]`, "pending change row");
      await sleep(400);
      let state = await page.evaluate(budgetState);
      const change = state.changes.find((item) => item.id === changeId);
      assert(change?.status === "pending" && change?.amount === "-100.00", `change row ${JSON.stringify(change)}`);
      let summary = state.summaries.find((item) => item.currency === "USD");
      assert(summary?.current === "1000.00" && summary?.pending === "-100.00", `pending summary ${JSON.stringify(summary)}`);
      assert(state.approveButtons.length === 0 && state.rejectButtons.length === 0, "planner received approval buttons");
      const changes = await api(page, "GET", budgetUrl(`/lines/${encodeURIComponent(lineId)}/changes`));
      assert(changes.body.changes.length === 1 && changes.body.changes[0].status === "pending", `stored changes ${JSON.stringify(changes.body)}`);
      await capture(page, "03-pending-change");
      return { change, summary };
    });

    await scenario("04", "تأیید تغییر برای Planner ممنوع است: بدون دکمه و پاسخ مستقیم 403", async () => {
      const denied = await api(page, "POST", budgetUrl(`/changes/${encodeURIComponent(changeId)}/status`), {
        status: "approved",
        expected_revision: 1,
      });
      assert(denied.status === 403, `planner approval status ${denied.status}`);
      assert(denied.body.code === "BUDGET_APPROVAL_REQUIRES_ADMIN", `planner approval code ${denied.body.code}`);
      const state = await page.evaluate(budgetState);
      assert(!state.approveButtons.includes(changeId), "planner sees the approve button after a denied call");
      const summary = state.summaries.find((item) => item.currency === "USD");
      assert(summary?.current === "1000.00", `current budget after denied approval ${summary?.current}`);
      await capture(page, "04-planner-denied");
      return { code: denied.body.code, current: summary?.current };
    });

    await scenario("05", "مدیر پروژه تغییر را تأیید می‌کند و بودجهٔ جاری ۹۰۰٫۰۰ می‌شود", async () => {
      await loginAs(page, "Project administrator");
      await openBudget(page);
      await sleep(500);
      await page.waitForSelector(`[data-budget-line="${lineId}"]`, "line row as administrator");
      await page.click(`[data-budget-action="select-line"][data-budget-line-id="${lineId}"]`);
      await page.waitForSelector(`[data-budget-action="approve"][data-budget-change-id="${changeId}"]`, "approve button");
      let state = await page.evaluate(budgetState);
      assert(state.approveButtons.includes(changeId), `approve button missing: ${JSON.stringify(state.approveButtons)}`);
      await page.click(`[data-budget-action="approve"][data-budget-change-id="${changeId}"]`);
      await page.waitFor(
        `document.querySelector('[data-budget-notice][data-state="ok"]')?.textContent?.includes("now approved") ?? false`,
        "approved notice",
      );
      await page.waitFor(
        `(() => {
          const row = [...document.querySelectorAll("[data-budget-summary-currency]")].find((item) => item.dataset.budgetSummaryCurrency === "USD");
          return row && [...row.querySelectorAll("td")][3]?.textContent.trim() === "900.00";
        })()`,
        "current budget after approval",
      );
      await sleep(400);
      state = await page.evaluate(budgetState);
      const summary = state.summaries.find((item) => item.currency === "USD");
      assert(summary?.approved === "-100.00" && summary?.current === "900.00" && summary?.pending === "0.00", `approved summary ${JSON.stringify(summary)}`);
      const stored = await api(page, "GET", budgetUrl(`/lines/${encodeURIComponent(lineId)}/changes`));
      assert(stored.body.changes[0].status === "approved" && stored.body.changes[0].revision === 2, `stored change ${JSON.stringify(stored.body.changes[0])}`);
      await capture(page, "05-approved-admin");
      return { summary, stored: stored.body.changes[0] };
    });

    await scenario("06", "رد تغییر دوم توسط مدیر، بودجهٔ جاری را تغییر نمی‌دهد و در فهرست می‌ماند", async () => {
      await page.click(`[data-budget-action="new-change"][data-budget-line-id="${lineId}"]`);
      await page.waitForSelector("[data-budget-change-form]", "second change form");
      await page.setInput('[data-budget-change-form] input[name="budget-change-id"]', rejectedId);
      await page.setInput('[data-budget-change-form] input[name="budget-change-amount"]', "250.00");
      await page.setInput('[data-budget-change-form] input[name="budget-change-reason"]', "Rejected extra scope");
      await page.click('[data-budget-change-form] button[type="submit"]');
      await page.waitForSelector(`[data-budget-change="${rejectedId}"] [data-budget-change-status="pending"]`, "second pending change");
      await sleep(400);
      let state = await page.evaluate(budgetState);
      let summary = state.summaries.find((item) => item.currency === "USD");
      assert(summary?.pending === "250.00" && summary?.current === "900.00", `pending second change ${JSON.stringify(summary)}`);
      await page.click(`[data-budget-action="reject"][data-budget-change-id="${rejectedId}"]`);
      await page.waitFor(
        `document.querySelector('[data-budget-notice][data-state="ok"]')?.textContent?.includes("now rejected") ?? false`,
        "rejected notice",
      );
      await sleep(500);
      state = await page.evaluate(budgetState);
      const rejected = state.changes.find((item) => item.id === rejectedId);
      assert(rejected?.status === "rejected", `rejected row ${JSON.stringify(rejected)}`);
      summary = state.summaries.find((item) => item.currency === "USD");
      assert(summary?.pending === "0.00" && summary?.current === "900.00", `summary after rejection ${JSON.stringify(summary)}`);
      await capture(page, "06-rejected-change");
      return { rejected, summary };
    });

    await scenario("07", "ایجاد منبع تأمین مالی و محاسبهٔ ماندهٔ ۵۰۰٫۰۰ توسط سرور", async () => {
      await page.click('[data-budget-action="new-funding"]');
      await page.waitForSelector("[data-budget-funding-form]", "funding form");
      await page.setInput('[data-budget-funding-form] input[name="budget-funding-id"]', fundingId);
      await page.setInput('[data-budget-funding-form] input[name="budget-funding-name"]', "E2E owner equity");
      await page.setSelect('[data-budget-funding-form] select[name="budget-funding-type"]', "internal");
      await page.setInput('[data-budget-funding-form] input[name="budget-funding-currency"]', "USD");
      await page.setInput('[data-budget-funding-form] input[name="budget-funding-amount"]', "400.00");
      await page.setInput('[data-budget-funding-form] input[name="budget-funding-period"]', "2026");
      await page.click('[data-budget-funding-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-budget-notice][data-state="ok"]')?.textContent?.includes("funding source was saved") ?? false`,
        "funding saved notice",
      );
      await page.waitForSelector(`[data-budget-funding-id="${fundingId}"]`, "funding row");
      await sleep(400);
      const state = await page.evaluate(budgetState);
      const row = state.funding.find((item) => item.id === fundingId);
      assert(row?.amount === "400.00" && row?.type === "internal" && row?.revision === "R1", `funding row ${JSON.stringify(row)}`);
      const summary = state.summaries.find((item) => item.currency === "USD");
      assert(summary?.funding === "400.00" && summary?.balance === "500.00", `funding summary ${JSON.stringify(summary)}`);
      await capture(page, "07-funding");
      return { row, summary };
    });

    await scenario("08", "ویرایش تأمین مالی با Revision محافظت می‌شود و نوشتن کهنه 409 می‌گیرد", async () => {
      await page.click(`[data-budget-action="edit-funding"][data-budget-funding-id="${fundingId}"]`);
      await page.waitForSelector("[data-budget-funding-form] input[name=budget-funding-id][readonly]", "funding edit form");
      await page.setInput('[data-budget-funding-form] input[name="budget-funding-amount"]', "450.00");
      await page.click('[data-budget-funding-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-budget-notice][data-state="ok"]')?.textContent?.includes("funding source was saved") ?? false`,
        "funding edit saved notice",
      );
      await sleep(500);
      let state = await page.evaluate(budgetState);
      const row = state.funding.find((item) => item.id === fundingId);
      assert(row?.revision === "R2" && row?.amount === "450.00", `edited funding ${JSON.stringify(row)}`);
      state = await page.evaluate(budgetState);
      const summary = state.summaries.find((item) => item.currency === "USD");
      assert(summary?.funding === "450.00" && summary?.balance === "450.00", `edited funding summary ${JSON.stringify(summary)}`);

      const stale = await api(page, "PATCH", budgetUrl(`/funding/${encodeURIComponent(fundingId)}`), {
        funding_id: fundingId,
        name: "E2E owner equity",
        source_type: "internal",
        currency: "USD",
        amount: "1.00",
        period_id: "2026",
        expected_revision: 1,
      });
      assert(stale.status === 409, `stale funding update status ${stale.status}`);
      assert(stale.body.code === "BUDGET_REVISION_CONFLICT", `stale funding code ${stale.body.code}`);
      const list = await api(page, "GET", budgetUrl("/funding"));
      const stored = list.body.funding_sources.find((item) => item.funding_id === fundingId);
      assert(stored.amount === "450.00" && stored.revision === 2, `stored funding after conflict ${JSON.stringify(stored)}`);
      await capture(page, "08-funding-revision-conflict");
      return { row, conflict: stale.body.code, stored };
    });

    await scenario("09", "ویرایش ردیف بودجه نسخهٔ ۲ می‌سازد و نوشتن هم‌زمان کهنه 409 می‌شود", async () => {
      await page.click(`[data-budget-action="edit-line"][data-budget-line-id="${lineId}"]`);
      await page.waitForSelector("[data-budget-line-form] input[name=budget-line-id][readonly]", "line edit form");
      await page.setInput('[data-budget-line-form] input[name="budget-description"]', "E2E concrete works revised");
      await page.click('[data-budget-line-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-budget-notice][data-state="ok"]')?.textContent?.includes("The budget line was saved") ?? false`,
        "line edit saved notice",
      );
      await sleep(500);
      let state = await page.evaluate(budgetState);
      let row = state.lines.find((item) => item.id === lineId);
      assert(row?.revision === "R2" && row?.description === "E2E concrete works revised", `edited line ${JSON.stringify(row)}`);

      const stale = await api(page, "PATCH", budgetUrl(`/lines/${encodeURIComponent(lineId)}`), {
        budget_line_id: lineId,
        description: "Stale overwrite",
        currency: "USD",
        original_amount: "1000.00",
        cost_account_id: "CA-1",
        period_id: "2026",
        expected_revision: 1,
      });
      assert(stale.status === 409, `stale line update status ${stale.status}`);
      assert(stale.body.code === "BUDGET_REVISION_CONFLICT", `stale line code ${stale.body.code}`);
      const stored = await api(page, "GET", budgetUrl(`/lines/${encodeURIComponent(lineId)}`));
      assert(stored.body.description === "E2E concrete works revised" && stored.body.revision === 2, `stored line after conflict ${JSON.stringify(stored.body)}`);
      await capture(page, "09-line-revision-conflict");
      return { row, conflict: stale.body.code, stored: stored.body };
    });

    await scenario("10", "پس از بارگذاری کامل صفحه، بودجه، تغییرات، تأمین مالی و خلاصه حفظ می‌شوند", async () => {
      await page.navigate(`${baseUrl}/app?project=preview-rps-01&view=visual`, "#cp-activity-grid tbody tr[data-activity-id]", "workspace reload");
      await sleep(1200);
      await openBudget(page);
      await sleep(500);
      const state = await page.evaluate(budgetState);
      const row = state.lines.find((item) => item.id === lineId);
      assert(row?.revision === "R2" && row?.original === "1000.00", `line after reload ${JSON.stringify(row)}`);
      const funding = state.funding.find((item) => item.id === fundingId);
      assert(funding?.revision === "R2" && funding?.amount === "450.00", `funding after reload ${JSON.stringify(funding)}`);
      const summary = state.summaries.find((item) => item.currency === "USD");
      assert(summary?.current === "900.00" && summary?.funding === "450.00" && summary?.balance === "450.00", `summary after reload ${JSON.stringify(summary)}`);
      const changes = await api(page, "GET", budgetUrl(`/lines/${encodeURIComponent(lineId)}/changes`));
      assert(changes.body.changes.length === 2, `changes after reload ${changes.body.changes.length}`);
      const statuses = changes.body.changes.map((item) => item.status).sort();
      assert(statuses.join("|") === "approved|rejected", `change statuses ${statuses.join("|")}`);
      await capture(page, "10-persisted-after-reload");
      return { row, funding, summary };
    });

    await scenario("11", "نقش Viewer فقط می‌خواند: بدون دکمهٔ نوشتن و پاسخ مستقیم 403", async () => {
      await loginAs(page, "Viewer");
      await openBudget(page);
      await sleep(500);
      let state = await page.evaluate(budgetState);
      assert(state.lines.some((item) => item.id === lineId), `viewer register ${JSON.stringify(state.lines)}`);
      assert(!state.newLine && !state.newFunding, "viewer received a budget write button");
      assert(!state.editLine, "viewer received the line edit button");
      const denied = await api(page, "POST", budgetUrl("/lines"), {
        budget_line_id: `${lineId}-VIEWER`,
        description: "Viewer must not write",
        currency: "USD",
        original_amount: "1.00",
      });
      assert(denied.status === 403, `viewer line create status ${denied.status}`);
      assert(denied.body.code === "BUDGET_PERMISSION_DENIED", `viewer line create code ${denied.body.code}`);
      const deniedFunding = await api(page, "POST", budgetUrl("/funding"), {
        funding_id: `${fundingId}-VIEWER`,
        name: "Viewer must not write",
        source_type: "internal",
        currency: "USD",
        amount: "1.00",
      });
      assert(deniedFunding.status === 403, `viewer funding create status ${deniedFunding.status}`);
      state = await page.evaluate(budgetState);
      assert(state.lines.length === 1, `viewer write leaked ${state.lines.length} lines`);
      await capture(page, "11-viewer-denied");
      return { createStatus: denied.status, fundingStatus: deniedFunding.status, lines: state.lines.length };
    });

    await scenario("12", "پنل بودجه در 1280×720 فارسی، راست‌به‌چپ و بدون بریدگی رندر می‌شود", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await setLanguage(page, "fa");
      await sleep(700);
      const layout = await page.evaluate(`(() => {
        const rect = (element) => {
          if (!element) return null;
          const bounds = element.getBoundingClientRect();
          return { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height };
        };
        const root = [...document.querySelectorAll("[data-budget-panel]")].find((element) => element.getClientRects().length > 0)
          ?? document.querySelector("[data-budget-panel]");
        const summary = root?.querySelector("[data-budget-summary]");
        return {
          innerWidth,
          innerHeight,
          direction: getComputedStyle(document.querySelector(".cp-workspace") || document.body).direction,
          heading: root?.querySelector(":scope > .cp-register-toolbar strong")?.textContent?.trim() ?? null,
          toolbar: rect(root?.querySelector(":scope > .cp-register-toolbar")),
          summary: rect(summary),
          panel: rect(root),
          rows: root?.querySelectorAll("[data-budget-line]").length ?? 0,
          fundingRows: root?.querySelectorAll("[data-budget-funding-id]").length ?? 0,
        };
      })()`);
      assert(layout.direction === "rtl", `workspace direction ${layout.direction}`);
      assert(layout.heading === "بودجهٔ پروژه", `Persian budget heading ${layout.heading}`);
      assert(layout.toolbar && layout.toolbar.width > 0, "the budget toolbar has no layout box at 1280x720");
      assert(layout.summary && layout.summary.height > 0, "the budget summary has no layout box at 1280x720");
      assert(layout.panel && layout.panel.height > 0, "the budget panel has no layout box at 1280x720");
      assert(layout.rows === 1 && layout.fundingRows === 1, `budget rows at 1280x720: ${layout.rows}/${layout.fundingRows}`);
      assert(layout.toolbar.x >= 0 && layout.toolbar.x + layout.toolbar.width <= layout.innerWidth + 1, `toolbar overflows: ${JSON.stringify(layout.toolbar)}`);
      assert(layout.summary.x >= 0 && layout.summary.x + layout.summary.width <= layout.innerWidth + 1, `summary overflows: ${JSON.stringify(layout.summary)}`);
      await capture(page, "12-budget-1280x720-fa");
      return layout;
    });

    assert(exceptions.length === 0, `uncaught page exceptions: ${JSON.stringify(exceptions.slice(0, 3))}`);
    assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors.slice(0, 3))}`);
    assert(apiFailures.length === 0, `API 5xx responses: ${JSON.stringify(apiFailures.slice(0, 3))}`);
  } finally {
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(outDir, "budget-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(evidenceDir, "budget-v26.json"), JSON.stringify(report, null, 2));
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
