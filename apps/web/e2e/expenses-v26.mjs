#!/usr/bin/env node
/**
 * Browser E2E for the Version 26 project cost register (expenses and cost accounts).
 *
 * It drives the real local full-stack preview on project preview-rps-01 with
 * headless Chrome through the DevTools protocol. Every value is read from and
 * written to the real p6-cost-api.v1 HTTP routes and the SQLite preview
 * repository; no page fixture is injected and no API response is mocked.
 *
 * Scenarios cover the empty register, cost-account creation with parent links,
 * account copy and project default, expense creation and revision-guarded edit,
 * a stale write conflict, account delete guards, expense deletion, persistence
 * after a full page reload, viewer read-only authorization, and the 1280x720
 * Persian right-to-left layout.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 node e2e/expenses-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "expenses-v26");
const evidenceDir = join(
  artifactsDir,
  "..",
  "..",
  "..",
  "..",
  "docs",
  "workspace",
  "evidence",
  `expenses-v26-${evidenceDate}`,
);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const stamp = Date.now().toString(36).toUpperCase();
const parentAccountId = `E2E-CA-${stamp}`;
const childAccountId = `E2E-CA-${stamp}-CONC`;
const expenseId = `E2E-EXP-${stamp}`;
const deletedExpenseId = `E2E-EXP-${stamp}-DEL`;

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
  const page = document.querySelector("[data-expenses-page]");
  const cells = (row) => [...row.querySelectorAll("td")].map((cell) => (cell.textContent || "").trim());
  const expenses = [...page?.querySelectorAll("[data-expense-row]") ?? []].map((row) => {
    const values = cells(row);
    return {
      id: row.dataset.expenseId,
      name: values[1],
      category: values[2],
      activity: values[3],
      account: values[4],
      date: values[5],
      planned: values[6],
      actual: values[7],
      remaining: values[8],
      currency: values[9],
      selected: row.classList.contains("is-selected"),
      edit: Boolean(page.querySelector('[data-expense-edit="' + row.dataset.expenseId + '"]')),
      remove: Boolean(page.querySelector('[data-expense-delete="' + row.dataset.expenseId + '"]')),
    };
  });
  const accounts = [...page?.querySelectorAll("[data-cost-account-row]") ?? []].map((row) => {
    const values = cells(row);
    return {
      id: row.dataset.costAccountId,
      default: Boolean(row.querySelector("[data-cost-account-default-badge]")),
      name: values[1],
      parent: values[2],
      description: values[3],
      revision: Number(values[4]),
      edit: Boolean(page.querySelector('[data-cost-account-edit="' + row.dataset.costAccountId + '"]')),
      copy: Boolean(page.querySelector('[data-cost-account-copy="' + row.dataset.costAccountId + '"]')),
      setDefault: Boolean(page.querySelector('button[data-cost-account-default="' + row.dataset.costAccountId + '"]')),
      remove: Boolean(page.querySelector('[data-cost-account-delete="' + row.dataset.costAccountId + '"]')),
    };
  });
  const form = page?.querySelector("[data-expense-form]");
  const accountForm = page?.querySelector("[data-cost-account-form]");
  return {
    activeMenu: document.querySelector(".cp-workspace")?.dataset.activeMenu ?? null,
    heading: page?.querySelector(":scope > .cp-register-toolbar strong")?.textContent?.trim() ?? null,
    accountsHeading: page?.querySelector("[data-cost-accounts-panel] > .cp-register-toolbar strong")?.textContent?.trim() ?? null,
    reading: (page?.textContent ?? "").includes("Reading project expenses"),
    empty: [...page?.querySelectorAll(".cp-calendar-empty") ?? []].map((item) => item.textContent.trim()),
    expenses,
    accounts,
    notice: page?.querySelector("[data-expense-notice]")
      ? { kind: page.querySelector("[data-expense-notice]").dataset.state, text: page.querySelector("[data-expense-notice]").textContent.trim() }
      : null,
    newExpense: Boolean(page?.querySelector('[data-expense-action="new"]')),
    newAccount: Boolean(page?.querySelector('[data-cost-account-action="new"]')),
    expenseForm: form ? {
      id: form.querySelector('input[name="expense-id"]')?.value ?? null,
      readonly: Boolean(form.querySelector('input[name="expense-id"]')?.hasAttribute("readonly")),
      name: form.querySelector('input[name="expense-name"]')?.value ?? null,
      category: form.querySelector('select[name="expense-category"]')?.value ?? null,
      account: form.querySelector('select[name="cost-account-id"]')?.value ?? null,
      planned: form.querySelector('input[name="planned-cost"]')?.value ?? null,
      actual: form.querySelector('input[name="actual-cost"]')?.value ?? null,
      currency: form.querySelector('input[name="currency"]')?.value ?? null,
    } : null,
    accountForm: accountForm ? {
      id: accountForm.querySelector('input[name="account-id"]')?.value ?? null,
      readonly: Boolean(accountForm.querySelector('input[name="account-id"]')?.hasAttribute("readonly")),
      name: accountForm.querySelector('input[name="account-name"]')?.value ?? null,
      parent: accountForm.querySelector('select[name="parent-account-id"]')?.value ?? null,
      isDefault: Boolean(accountForm.querySelector('input[name="account-default"]')?.checked),
    } : null,
    page: Boolean(page),
  };
})()`;

async function capture(page, name) {
  const file = `expenses-v26/${name}.png`;
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

async function setCheckbox(page, selector, checked) {
  const changed = await page.evaluate(`(() => {
    const element = document.querySelector(${JSON.stringify(selector)});
    if (!element) return false;
    element.checked = ${checked};
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  assert(changed, `checkbox target not found: ${selector}`);
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

async function openExpenses(page) {
  await openMenu(page, "expenses", "[data-expenses-page] .cp-register-toolbar", "expenses panel");
  await page.waitFor(
    `(() => {
      const page = document.querySelector("[data-expenses-page]");
      return Boolean(page) && !page.textContent.includes("Reading project expenses") && !page.textContent.includes("Reading cost accounts");
    })()`,
    "expense register settled",
  );
  await sleep(400);
}

function costUrl(suffix) {
  return `/api/projects/${PROJECT}/cost${suffix}`;
}

async function api(page, method, path, body) {
  return page.evaluate(`(async () => {
    const response = await fetch(${JSON.stringify(path)}, {
      method: ${JSON.stringify(method)},
      headers: { "Content-Type": "application/json", "Idempotency-Key": "e2e-cost-" + Math.random().toString(36).slice(2) },
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

async function createAccount(page, id, name, description, parent, isDefault) {
  await page.click('[data-cost-account-action="new"]');
  await page.waitForSelector("[data-cost-account-form]", "cost account form");
  await page.setInput('[data-cost-account-form] input[name="account-id"]', id);
  await page.setInput('[data-cost-account-form] input[name="account-name"]', name);
  await page.setInput('[data-cost-account-form] input[name="account-description"]', description);
  if (parent) await page.setSelect('[data-cost-account-form] select[name="parent-account-id"]', parent);
  if (isDefault) await setCheckbox(page, '[data-cost-account-form] input[name="account-default"]', true);
  await page.click('[data-cost-account-form] button[type="submit"]');
  await page.waitFor(
    `document.querySelector('[data-expense-notice][data-state="ok"]')?.textContent?.includes("Cost account saved.") ?? false`,
    `cost account saved notice for ${id}`,
  );
  await page.waitForSelector(`[data-cost-account-row][data-cost-account-id="${id}"]`, `cost account row ${id}`);
  await sleep(400);
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
    contract: "cubi-expenses-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    parentAccountId,
    childAccountId,
    expenseId,
    deletedExpenseId,
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
    await openExpenses(page);

    await scenario("01", "فهرست هزینهٔ خالی، حساب‌های خالی و فرم‌های مجاز برای Planner نمایش داده می‌شود", async () => {
      const state = await page.evaluate(registerState);
      assert(state.page, "the expenses page is missing");
      assert(state.activeMenu === "expenses", `active menu is ${state.activeMenu}`);
      assert(state.heading === "Project Expenses", `expense heading is ${state.heading}`);
      assert(state.accountsHeading === "Cost Accounts", `account heading is ${state.accountsHeading}`);
      assert(state.expenses.length === 0, `register starts with ${state.expenses.length} expenses`);
      assert(state.accounts.length === 0, `register starts with ${state.accounts.length} accounts`);
      assert(state.empty.some((text) => /No project expenses are stored/.test(text)), `expense empty copy ${JSON.stringify(state.empty)}`);
      assert(state.empty.some((text) => /No cost accounts are stored/.test(text)), `account empty copy ${JSON.stringify(state.empty)}`);
      assert(state.newExpense && state.newAccount, "planner cannot open the register forms");
      const expenses = await api(page, "GET", costUrl("/expenses"));
      const accounts = await api(page, "GET", costUrl("/accounts"));
      assert(expenses.status === 200 && expenses.body.expenses.length === 0, `server expenses ${JSON.stringify(expenses.body)}`);
      assert(accounts.status === 200 && accounts.body.cost_accounts.length === 0, `server accounts ${JSON.stringify(accounts.body)}`);
      await capture(page, "01-empty-register");
      return { expenses: 0, accounts: 0 };
    });

    await scenario("02", "ایجاد حساب هزینهٔ والد به‌عنوان پیش‌فرض پروژه با نسخهٔ ۱", async () => {
      await createAccount(page, parentAccountId, "E2E civil works", "Parent cost account", null, true);
      const state = await page.evaluate(registerState);
      const row = state.accounts.find((item) => item.id === parentAccountId);
      assert(row, `created account missing: ${JSON.stringify(state.accounts)}`);
      assert(row.revision === 1 && row.default === true && row.parent === "—", `account row ${JSON.stringify(row)}`);
      const stored = await api(page, "GET", costUrl(`/accounts/${encodeURIComponent(parentAccountId)}`));
      assert(stored.status === 200 && stored.body.revision === 1 && stored.body.is_default === true, `stored account ${JSON.stringify(stored.body)}`);
      await capture(page, "02-parent-account");
      return { row, stored: stored.body };
    });

    await scenario("03", "حساب فرزند با ارجاع والد ساخته می‌شود و والد در ستون حساب والد نمایش داده می‌شود", async () => {
      await createAccount(page, childAccountId, "E2E concrete", "Child account", parentAccountId, false);
      const state = await page.evaluate(registerState);
      const row = state.accounts.find((item) => item.id === childAccountId);
      assert(row, `child account missing: ${JSON.stringify(state.accounts)}`);
      assert(row.parent === parentAccountId && row.default === false, `child row ${JSON.stringify(row)}`);
      const stored = await api(page, "GET", costUrl(`/accounts/${encodeURIComponent(childAccountId)}`));
      assert(stored.body.parent_account_id === parentAccountId, `stored child ${JSON.stringify(stored.body)}`);
      await capture(page, "03-child-account");
      return { row, stored: stored.body };
    });

    await scenario("04", "کپی حساب هزینه یک حساب مستقل بدون پیش‌فرض می‌سازد", async () => {
      await page.click(`[data-cost-account-copy="${childAccountId}"]`);
      await page.waitFor(
        `document.querySelector('[data-expense-notice][data-state="ok"]')?.textContent?.includes("Cost account copied.") ?? false`,
        "cost account copied notice",
      );
      await sleep(500);
      const state = await page.evaluate(registerState);
      assert(state.accounts.length === 3, `accounts after copy: ${JSON.stringify(state.accounts)}`);
      const server = await api(page, "GET", costUrl("/accounts"));
      const copies = server.body.cost_accounts.filter((item) => item.account_id.startsWith(`${childAccountId}-COPY-`));
      assert(copies.length === 1, `stored copies ${JSON.stringify(server.body.cost_accounts)}`);
      assert(copies[0].is_default === false && copies[0].parent_account_id === parentAccountId, `copied account ${JSON.stringify(copies[0])}`);
      assert(copies[0].name === "E2E concrete copy", `copied name ${copies[0].name}`);
      await capture(page, "04-copied-account");
      return { accounts: state.accounts.length, copy: copies[0] };
    });

    await scenario("05", "تعیین پیش‌فرض به حساب فرزند، پیش‌فرض والد را پاک می‌کند و نسخهٔ والد را افزایش می‌دهد", async () => {
      await page.click(`button[data-cost-account-default="${childAccountId}"]`);
      await page.waitFor(
        `document.querySelector('[data-expense-notice][data-state="ok"]')?.textContent?.includes("Default cost account updated.") ?? false`,
        "default account notice",
      );
      await sleep(500);
      const state = await page.evaluate(registerState);
      const child = state.accounts.find((item) => item.id === childAccountId);
      const parent = state.accounts.find((item) => item.id === parentAccountId);
      assert(child?.default === true, `child default ${JSON.stringify(child)}`);
      assert(parent?.default === false && parent?.revision === 2, `parent after default ${JSON.stringify(parent)}`);
      const stored = await api(page, "GET", costUrl(`/accounts/${encodeURIComponent(childAccountId)}`));
      assert(stored.body.is_default === true && stored.body.revision === 2, `stored child default ${JSON.stringify(stored.body)}`);
      await capture(page, "05-default-account");
      return { child, parent };
    });

    await scenario("06", "ایجاد هزینه از فرم با حساب هزینه، تاریخ تعهد و مبالغ دو رقم اعشار", async () => {
      await page.click('[data-expense-action="new"]');
      await page.waitForSelector("[data-expense-form]", "expense form");
      await page.setInput('[data-expense-form] input[name="expense-id"]', expenseId);
      await page.setInput('[data-expense-form] input[name="expense-name"]', "E2E concrete pump");
      await page.setInput('[data-expense-form] select[name="expense-category"]', "equipment");
      await page.setSelect('[data-expense-form] select[name="cost-account-id"]', childAccountId);
      await page.setInput('[data-expense-form] input[name="expense-date"]', "2026-10-05");
      await page.setInput('[data-expense-form] input[name="accrual-date"]', "2026-10-01");
      await page.setInput('[data-expense-form] input[name="planned-cost"]', "1250.50");
      await page.setInput('[data-expense-form] input[name="actual-cost"]', "500.00");
      await page.setInput('[data-expense-form] input[name="remaining-cost"]', "750.50");
      await page.click('[data-expense-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-expense-notice][data-state="ok"]')?.textContent?.includes("Expense saved.") ?? false`,
        "expense saved notice",
      );
      await page.waitForSelector(`[data-expense-row][data-expense-id="${expenseId}"]`, "expense row");
      await sleep(400);
      const state = await page.evaluate(registerState);
      const row = state.expenses.find((item) => item.id === expenseId);
      assert(row, `created expense missing: ${JSON.stringify(state.expenses)}`);
      assert(row.category === "equipment" && row.account === `${childAccountId} E2E concrete`, `expense row ${JSON.stringify(row)}`);
      assert(row.planned === "1250.50" && row.actual === "500.00" && row.remaining === "750.50" && row.currency === "USD", `expense amounts ${JSON.stringify(row)}`);
      const stored = await api(page, "GET", costUrl(`/expenses/${encodeURIComponent(expenseId)}`));
      assert(stored.status === 200 && stored.body.revision === 1, `stored expense ${JSON.stringify(stored.body)}`);
      assert(stored.body.cost_account_id === childAccountId && stored.body.accrual_date === "2026-10-01", `stored expense refs ${JSON.stringify(stored.body)}`);
      await capture(page, "06-created-expense");
      return { row, stored: stored.body };
    });

    await scenario("07", "ویرایش هزینه نسخهٔ ۲ می‌سازد و نوشتن کهنه 409 می‌گیرد", async () => {
      await page.click(`[data-expense-edit="${expenseId}"]`);
      await page.waitForSelector("[data-expense-form] input[name=expense-id][readonly]", "expense edit form");
      await page.setInput('[data-expense-form] input[name="expense-name"]', "E2E concrete pump revised");
      await page.setInput('[data-expense-form] input[name="actual-cost"]', "600.00");
      await page.click('[data-expense-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-expense-notice][data-state="ok"]')?.textContent?.includes("Expense saved.") ?? false`,
        "expense edit notice",
      );
      await sleep(500);
      let state = await page.evaluate(registerState);
      let row = state.expenses.find((item) => item.id === expenseId);
      assert(row?.actual === "600.00", `edited expense row ${JSON.stringify(row)}`);
      const stored = await api(page, "GET", costUrl(`/expenses/${encodeURIComponent(expenseId)}`));
      assert(stored.body.revision === 2 && stored.body.name === "E2E concrete pump revised", `stored edited expense ${JSON.stringify(stored.body)}`);

      const stale = await api(page, "PATCH", costUrl(`/expenses/${encodeURIComponent(expenseId)}`), {
        expense_id: expenseId,
        name: "Stale overwrite",
        category: "equipment",
        currency: "USD",
        planned_amount: "1.00",
        expected_revision: 1,
      });
      assert(stale.status === 409, `stale expense update status ${stale.status}`);
      assert(stale.body.code === "COST_REVISION_CONFLICT", `stale expense code ${stale.body.code}`);
      state = await page.evaluate(registerState);
      row = state.expenses.find((item) => item.id === expenseId);
      assert(row?.name === "E2E concrete pump revised" && row?.actual === "600.00", `row after conflict ${JSON.stringify(row)}`);
      await capture(page, "07-expense-revision-conflict");
      return { row, conflict: stale.body.code, stored: stored.body };
    });

    await scenario("08", "حذف حساب در حال استفاده و حساب دارای فرزند با 409 مسدود می‌شود", async () => {
      await page.click(`[data-cost-account-delete="${childAccountId}"]`);
      await page.waitFor(
        `document.querySelector('[data-expense-notice][data-state="error"]')?.textContent?.includes("COST_ACCOUNT_IN_USE") ?? false`,
        "account in-use notice",
      );
      await sleep(400);
      let state = await page.evaluate(registerState);
      assert(state.accounts.some((item) => item.id === childAccountId), "in-use account disappeared from the register");

      await page.click(`[data-cost-account-delete="${parentAccountId}"]`);
      await page.waitFor(
        `document.querySelector('[data-expense-notice][data-state="error"]')?.textContent?.includes("COST_ACCOUNT_HAS_CHILDREN") ?? false`,
        "account has-children notice",
      );
      await sleep(400);
      state = await page.evaluate(registerState);
      assert(state.accounts.some((item) => item.id === parentAccountId), "parent account disappeared from the register");
      const denied = await api(page, "DELETE", costUrl(`/accounts/${encodeURIComponent(childAccountId)}`), { expected_revision: 2 });
      assert(denied.status === 409 && denied.body.code === "COST_ACCOUNT_IN_USE", `direct in-use delete ${JSON.stringify(denied)}`);
      await capture(page, "08-account-delete-guards");
      return { inUse: denied.body.code };
    });

    await scenario("09", "حذف هزینه با نسخهٔ جاری انجام می‌شود و ردیف از فهرست و سرور حذف می‌شود", async () => {
      await page.click('[data-expense-action="new"]');
      await page.waitForSelector("[data-expense-form]", "second expense form");
      await page.setInput('[data-expense-form] input[name="expense-id"]', deletedExpenseId);
      await page.setInput('[data-expense-form] input[name="expense-name"]', "E2E temporary expense");
      await page.setInput('[data-expense-form] input[name="planned-cost"]', "10.00");
      await page.click('[data-expense-form] button[type="submit"]');
      await page.waitForSelector(`[data-expense-row][data-expense-id="${deletedExpenseId}"]`, "temporary expense row");
      await sleep(400);

      await page.click(`[data-expense-delete="${deletedExpenseId}"]`);
      await page.waitFor(
        `document.querySelector('[data-expense-notice][data-state="ok"]')?.textContent?.includes("Expense deleted.") ?? false`,
        "expense deleted notice",
      );
      await sleep(500);
      const state = await page.evaluate(registerState);
      assert(!state.expenses.some((item) => item.id === deletedExpenseId), `deleted expense still listed: ${JSON.stringify(state.expenses)}`);
      assert(state.expenses.some((item) => item.id === expenseId), "the remaining expense disappeared");
      const gone = await api(page, "GET", costUrl(`/expenses/${encodeURIComponent(deletedExpenseId)}`));
      assert(gone.status === 404, `deleted expense read status ${gone.status}`);
      await capture(page, "09-deleted-expense");
      return { remaining: state.expenses.length, readStatus: gone.status };
    });

    await scenario("10", "پس از بارگذاری کامل صفحه، هزینه‌ها، حساب‌ها و پیش‌فرض حفظ می‌شوند", async () => {
      await page.navigate(`${baseUrl}/app?project=preview-rps-01&view=visual`, "#cp-activity-grid tbody tr[data-activity-id]", "workspace reload");
      await sleep(1200);
      await openExpenses(page);
      await sleep(500);
      const state = await page.evaluate(registerState);
      const row = state.expenses.find((item) => item.id === expenseId);
      assert(row?.name === "E2E concrete pump revised" && row?.actual === "600.00", `expense after reload ${JSON.stringify(row)}`);
      assert(state.accounts.length === 3, `accounts after reload ${JSON.stringify(state.accounts)}`);
      const child = state.accounts.find((item) => item.id === childAccountId);
      assert(child?.default === true && child?.revision === 2, `default after reload ${JSON.stringify(child)}`);
      await capture(page, "10-persisted-after-reload");
      return { row, accounts: state.accounts.length };
    });

    await scenario("11", "نقش Viewer فقط می‌خواند: بدون دکمهٔ نوشتن و پاسخ مستقیم 403", async () => {
      await loginAs(page, "Viewer");
      await openExpenses(page);
      await sleep(500);
      let state = await page.evaluate(registerState);
      assert(state.expenses.some((item) => item.id === expenseId), `viewer register ${JSON.stringify(state.expenses)}`);
      assert(!state.newExpense && !state.newAccount, "viewer received a register write button");
      assert(state.expenses.every((item) => !item.edit && !item.remove), "viewer received an expense write action");
      assert(state.accounts.every((item) => !item.edit && !item.copy && !item.setDefault && !item.remove), "viewer received a cost account write action");
      const denied = await api(page, "POST", costUrl("/expenses"), {
        expense_id: `${expenseId}-VIEWER`,
        name: "Viewer must not write",
        category: "other",
        currency: "USD",
        planned_amount: "1.00",
      });
      assert(denied.status === 403, `viewer expense create status ${denied.status}`);
      assert(denied.body.code === "COST_PERMISSION_DENIED", `viewer expense create code ${denied.body.code}`);
      const deniedAccount = await api(page, "POST", costUrl("/accounts"), {
        account_id: `${parentAccountId}-VIEWER`,
        name: "Viewer must not write",
      });
      assert(deniedAccount.status === 403, `viewer account create status ${deniedAccount.status}`);
      assert(deniedAccount.body.code === "COST_PERMISSION_DENIED", `viewer account create code ${deniedAccount.body.code}`);
      state = await page.evaluate(registerState);
      assert(state.expenses.length === 1 && state.accounts.length === 3, `viewer write leaked ${state.expenses.length}/${state.accounts.length}`);
      await capture(page, "11-viewer-denied");
      return { expenseStatus: denied.status, accountStatus: deniedAccount.status };
    });

    await scenario("12", "فهرست هزینه در 1280×720 فارسی، راست‌به‌چپ و بدون بریدگی رندر می‌شود", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await setLanguage(page, "fa");
      await sleep(700);
      const layout = await page.evaluate(`(() => {
        const rect = (element) => {
          if (!element) return null;
          const bounds = element.getBoundingClientRect();
          return { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height };
        };
        const page = document.querySelector("[data-expenses-page]");
        const accountPanel = page?.querySelector("[data-cost-accounts-panel]");
        return {
          innerWidth,
          innerHeight,
          direction: getComputedStyle(document.querySelector(".cp-workspace") || document.body).direction,
          heading: page?.querySelector(":scope > .cp-register-toolbar strong")?.textContent?.trim() ?? null,
          toolbar: rect(page?.querySelector(":scope > .cp-register-toolbar")),
          panel: rect(page),
          accountPanel: rect(accountPanel),
          table: rect(page?.querySelector(".cp-register-table-wrap")),
          rows: page?.querySelectorAll("[data-expense-row]").length ?? 0,
          accountRows: page?.querySelectorAll("[data-cost-account-row]").length ?? 0,
        };
      })()`);
      assert(layout.direction === "rtl", `workspace direction ${layout.direction}`);
      assert(layout.heading === "هزینه‌های پروژه", `Persian expense heading ${layout.heading}`);
      assert(layout.toolbar && layout.toolbar.width > 0, "the expense toolbar has no layout box at 1280x720");
      assert(layout.accountPanel && layout.accountPanel.height > 0, "the cost account panel has no layout box at 1280x720");
      assert(layout.table && layout.table.width > 0, "the expense table has no layout box at 1280x720");
      assert(layout.rows === 1 && layout.accountRows === 3, `rows at 1280x720: ${layout.rows}/${layout.accountRows}`);
      assert(layout.toolbar.x >= 0 && layout.toolbar.x + layout.toolbar.width <= layout.innerWidth + 1, `toolbar overflows: ${JSON.stringify(layout.toolbar)}`);
      assert(layout.table.x >= 0 && layout.table.x + layout.table.width <= layout.innerWidth + 1, `table overflows: ${JSON.stringify(layout.table)}`);
      await capture(page, "12-expenses-1280x720-fa");
      return layout;
    });

    assert(exceptions.length === 0, `uncaught page exceptions: ${JSON.stringify(exceptions.slice(0, 3))}`);
    assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors.slice(0, 3))}`);
    assert(apiFailures.length === 0, `API 5xx responses: ${JSON.stringify(apiFailures.slice(0, 3))}`);
  } finally {
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(outDir, "expenses-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(evidenceDir, "expenses-v26.json"), JSON.stringify(report, null, 2));
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
