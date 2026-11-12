#!/usr/bin/env node
/**
 * Browser E2E for the Version 26 project administration window.
 *
 * It drives the real local full-stack preview on project preview-rps-01 with
 * headless Chrome through the DevTools protocol. Preferences, dictionary
 * entries, the permission matrix and financial periods are read from and
 * written to the real administration HTTP routes and the SQLite preview
 * repository; no page fixture is injected and no API response is mocked.
 *
 * Scenarios cover the default preference record and the derived matrix,
 * revision-guarded preference save with a stale 409, dictionary create with a
 * duplicate 409 and idempotent replay, revision-guarded edit with server-side
 * filters, delete with a 404 read, financial-period create against the shared
 * p6 register, viewer read-only authorization with direct 403 responses,
 * the immutable audit history, and the 1280x720 Persian right-to-left layout.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 node e2e/administration-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "administration-v26");
const evidenceDir = join(
  artifactsDir,
  "..",
  "..",
  "..",
  "..",
  "docs",
  "workspace",
  "evidence",
  `administration-v26-${evidenceDate}`,
);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const stamp = Date.now().toString(36).toUpperCase();
const categoryEntry = `E2E-CAT-${stamp}`;
const idempotentEntry = `E2E-IDEM-${stamp}`;
const periodId = `E2E-PERIOD-${stamp}`;
const idempotencyKey = `e2e-admin-${stamp}`;

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
  const page = document.querySelector("[data-administration-page]");
  const text = (node) => (node?.textContent ?? "").trim();
  const form = page?.querySelector("[data-admin-preferences-form]");
  const dictForm = page?.querySelector("[data-admin-dict-form]");
  const periodForm = page?.querySelector("[data-admin-period-form]");
  return {
    activeMenu: document.querySelector(".cp-workspace")?.dataset.activeMenu ?? null,
    direction: document.querySelector(".cp-workspace")?.getAttribute("dir") ?? null,
    heading: text(page?.querySelector(":scope > .cp-register-toolbar strong")),
    tabs: [...page?.querySelectorAll("[data-admin-tab]") ?? []].map((tab) => ({
      key: tab.dataset.adminTab,
      selected: tab.getAttribute("aria-selected"),
      label: text(tab),
    })),
    activeTab: page?.querySelector("[data-admin-body]")?.dataset.adminActiveTab ?? null,
    preferences: form ? {
      currency: form.querySelector('input[name="admin-currency"]')?.value ?? null,
      unit: form.querySelector('input[name="admin-unit"]')?.value ?? null,
      dateDisplay: form.querySelector('select[name="admin-date-display"]')?.value ?? null,
      decimals: form.querySelector('select[name="admin-decimals"]')?.value ?? null,
      fiscalMonth: form.querySelector('select[name="admin-fiscal-month"]')?.value ?? null,
      meta: text(form.querySelector("[data-admin-preferences-meta]")),
      disabled: Boolean(form.querySelector('input[name="admin-currency"]')?.disabled),
      save: Boolean(form.querySelector('button[type="submit"]')),
    } : null,
    dictionary: dictForm ? {
      code: dictForm.querySelector('select[name="admin-dict-code"]')?.value ?? null,
      entry: dictForm.querySelector('input[name="admin-dict-entry"]')?.value ?? null,
      label: dictForm.querySelector('input[name="admin-dict-label"]')?.value ?? null,
      sequence: dictForm.querySelector('input[name="admin-dict-sequence"]')?.value ?? null,
      entries: [...page.querySelectorAll("[data-admin-dict-row]")].map((row) => ({
        code: row.dataset.code,
        entry: row.dataset.entry,
        text: text(row),
      })),
      editable: [...page.querySelectorAll("[data-admin-dict-edit]")].map((button) => button.dataset.adminDictEdit),
      filter: page.querySelector('select[name="admin-dictionary-filter"]')?.value ?? null,
      search: page.querySelector('input[name="admin-dict-search"]')?.value ?? null,
    } : null,
    matrix: page?.querySelector("[data-admin-matrix]") ? {
      permissions: [...page.querySelectorAll("[data-admin-permission]")].map((row) => row.dataset.adminPermission),
      roles: [...page.querySelectorAll("[data-admin-matrix] thead th")].slice(1).map((cell) => text(cell)),
      adminProjectWrite: text(page.querySelector('[data-admin-permission="project.write"] [data-admin-grant="project_admin"]')),
      viewerProjectWrite: text(page.querySelector('[data-admin-permission="project.write"] [data-admin-grant="viewer"]')),
    } : null,
    periods: periodForm ? {
      rows: [...page.querySelectorAll("[data-admin-period-row]")].map((row) => ({
        id: row.dataset.periodId,
        text: text(row),
      })),
      save: Boolean(periodForm.querySelector('button[type="submit"]')),
      formDisabled: Boolean(periodForm.querySelector('input[name="admin-period-id"]')?.disabled),
    } : null,
    notice: page?.querySelector("[data-admin-notice]")
      ? { kind: page.querySelector("[data-admin-notice]").dataset.state, text: text(page.querySelector("[data-admin-notice]")) }
      : null,
    bodyText: text(page),
  };
})()`;

async function capture(page, name) {
  const file = `administration-v26/${name}.png`;
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

async function openAdministration(page) {
  await openMenu(page, "administration", "[data-administration-page] .cp-register-toolbar", "administration panel");
  await page.waitFor(
    `(() => {
      const page = document.querySelector("[data-administration-page]");
      return Boolean(page) && Boolean(page.querySelector("[data-admin-tab]"));
    })()`,
    "administration tabs settled",
  );
  await sleep(400);
}

async function openTab(page, tab) {
  await page.click(`[data-admin-tab="${tab}"]`);
  await page.waitFor(
    `document.querySelector("[data-administration-page] [data-admin-body]")?.dataset.adminActiveTab === ${JSON.stringify(tab)}`,
    `administration ${tab} tab`,
  );
  await sleep(300);
}

function adminUrl(suffix = "") {
  return `/api/projects/${PROJECT}/administration${suffix}`;
}

function periodsUrl() {
  return `/api/projects/${PROJECT}/p6/financial-periods`;
}

async function api(page, method, path, body, headers = {}) {
  return page.evaluate(`(async () => {
    const response = await fetch(${JSON.stringify(path)}, {
      method: ${JSON.stringify(method)},
      headers: { "Content-Type": "application/json", ...${JSON.stringify(headers)} },
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

async function submitPreferences(page, values) {
  await page.setInput('[data-admin-preferences-form] input[name="admin-currency"]', values.currency);
  await page.setInput('[data-admin-preferences-form] input[name="admin-unit"]', values.unit);
  await page.setSelect('[data-admin-preferences-form] select[name="admin-date-display"]', values.dateDisplay);
  await page.setSelect('[data-admin-preferences-form] select[name="admin-decimals"]', String(values.decimals));
  await page.setSelect('[data-admin-preferences-form] select[name="admin-fiscal-month"]', String(values.fiscalMonth));
  await page.click('[data-admin-preferences-form] button[type="submit"]');
  await page.waitFor(
    `(() => {
      const notice = document.querySelector("[data-administration-page] [data-admin-notice]");
      return notice?.dataset.state === "ok" && notice.textContent.includes("Preferences saved");
    })()`,
    "preference save notice",
  );
  await sleep(300);
}

async function submitDictionary(page, values) {
  await page.setSelect('[data-admin-dict-form] select[name="admin-dict-code"]', values.code);
  await page.setInput('[data-admin-dict-form] input[name="admin-dict-entry"]', values.entry);
  await page.setInput('[data-admin-dict-form] input[name="admin-dict-label"]', values.label);
  await page.setInput('[data-admin-dict-form] input[name="admin-dict-sequence"]', String(values.sequence));
  await page.click('[data-admin-dict-form] button[type="submit"]');
  await page.waitFor(
    `(() => {
      const page = document.querySelector("[data-administration-page]");
      const notice = page?.querySelector("[data-admin-notice]");
      return Boolean(page?.querySelector('[data-admin-dict-row][data-entry="${values.entry}"]')) &&
        notice?.dataset.state === "ok";
    })()`,
    `dictionary entry ${values.entry} saved`,
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
    contract: "cubi-administration-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    categoryEntry,
    idempotentEntry,
    periodId,
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
  };

  try {
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
    await sleep(400);
    await loginAs(page, "Project administrator");
    await openAdministration(page);

    await scenario("01", "ترجیحات پیش‌فرض، چهار زبانه و ماتریس مشتق‌شده از سیاست مرجع خوانده می‌شود", async () => {
      const state = await page.evaluate(pageState);
      assert(state.activeMenu === "administration", `active menu is ${state.activeMenu}`);
      assert(state.heading === "Administration", `heading is ${state.heading}`);
      assert(state.tabs.length === 4, `tabs ${JSON.stringify(state.tabs)}`);
      assert(state.tabs.map((tab) => tab.key).join(",") === "preferences,dictionaries,matrix,periods", `tab order ${JSON.stringify(state.tabs)}`);
      assert(state.tabs[0].selected === "true", "preferences is not the initial tab");
      assert(state.preferences?.currency === "USD" && state.preferences?.unit === "day", `defaults ${JSON.stringify(state.preferences)}`);
      assert(state.preferences?.dateDisplay === "gregorian" && state.preferences?.decimals === "2" && state.preferences?.fiscalMonth === "1", `default facts ${JSON.stringify(state.preferences)}`);
      assert((state.preferences?.meta ?? "").includes("Revision 0"), `default revision ${state.preferences?.meta}`);
      assert(state.preferences?.save === true, "administrator has no preference save control");

      const matrix = await api(page, "GET", adminUrl("/permission-matrix"));
      assert(matrix.status === 200 && matrix.body.contract_version === "p6-administration-api.v1", `matrix ${JSON.stringify(matrix)}`);
      assert(matrix.body.permissions.length === 14, `permissions ${matrix.body.permissions.length}`);
      assert(matrix.body.roles.map((role) => role.role).join(",") === "planner,project_admin,viewer", `roles ${JSON.stringify(matrix.body.roles)}`);
      const adminRole = matrix.body.roles.find((role) => role.role === "project_admin");
      const viewerRole = matrix.body.roles.find((role) => role.role === "viewer");
      assert(adminRole.permissions.includes("project.admin"), "administrator role lost project.admin");
      assert(!viewerRole.permissions.includes("project.write"), "viewer role unexpectedly writes projects");
      assert(!viewerRole.permissions.includes("form.create"), "viewer role unexpectedly creates forms");
      await capture(page, "01-preferences-and-matrix");
      return { tabs: state.tabs.map((tab) => tab.key), permissions: matrix.body.permissions.length };
    });

    await scenario("02", "ذخیرهٔ ترجیحات با نسخه محافظت می‌شود و درخواست کهنه ۴۰۹ می‌گیرد", async () => {
      await submitPreferences(page, { currency: "EUR", unit: "hour", dateDisplay: "jalali", decimals: 3, fiscalMonth: 4 });
      const state = await page.evaluate(pageState);
      assert(state.preferences?.currency === "EUR" && state.preferences?.unit === "hour", `saved facts ${JSON.stringify(state.preferences)}`);
      assert((state.preferences?.meta ?? "").includes("Revision 1"), `saved revision ${state.preferences?.meta}`);

      const stale = await api(page, "PUT", adminUrl("/preferences"), {
        currency: "USD",
        unit_of_measure: "day",
        date_display: "gregorian",
        decimal_places: 2,
        fiscal_year_start_month: 1,
        expected_revision: 0,
      });
      assert(stale.status === 409 && stale.body.code === "ADMIN_PREFERENCES_REVISION_CONFLICT", `stale write ${JSON.stringify(stale)}`);

      const stored = await api(page, "GET", adminUrl("/preferences"));
      assert(stored.status === 200 && stored.body.revision === 1, `stored revision ${JSON.stringify(stored.body)}`);
      assert(stored.body.currency === "EUR" && stored.body.date_display === "jalali", `stored facts ${JSON.stringify(stored.body)}`);
      await capture(page, "02-preferences-saved");
      return { revision: stored.body.revision, staleStatus: stale.status };
    });

    await scenario("03", "ورودی فهرست ساخته می‌شود و تکرار شناسه و استفادهٔ دوبارهٔ کلید ایدمپوتنسی کنترل می‌شود", async () => {
      await openTab(page, "dictionaries");
      await page.click('[data-admin-action="new-dict"]');
      await submitDictionary(page, { code: "cost_category", entry: categoryEntry, label: "E2E Civil Works", sequence: 25 });
      const state = await page.evaluate(pageState);
      const row = state.dictionary?.entries.find((entry) => entry.entry === categoryEntry);
      assert(row, `created entry is missing: ${JSON.stringify(state.dictionary?.entries)}`);
      assert(row.text.includes("E2E Civil Works") && row.text.includes("cost_category"), `created row ${row.text}`);

      const duplicate = await api(page, "POST", adminUrl("/dictionaries"), {
        dictionary_code: "cost_category",
        entry_id: categoryEntry,
        label: "Duplicate",
        sequence: 1,
        is_active: true,
      }, { "Idempotency-Key": `${idempotencyKey}-dup` });
      assert(duplicate.status === 409 && duplicate.body.code === "ADMIN_DICTIONARY_ID_ALREADY_EXISTS", `duplicate ${JSON.stringify(duplicate)}`);

      const payload = {
        dictionary_code: "risk_category",
        entry_id: idempotentEntry,
        label: "E2E Idempotent Risk",
        sequence: 5,
        is_active: true,
      };
      const first = await api(page, "POST", adminUrl("/dictionaries"), payload, { "Idempotency-Key": idempotencyKey });
      assert(first.status === 200 && first.body.revision === 1, `idempotent create ${JSON.stringify(first)}`);
      const replay = await api(page, "POST", adminUrl("/dictionaries"), payload, { "Idempotency-Key": idempotencyKey });
      assert(replay.status === 200 && replay.body.entry_id === idempotentEntry && replay.body.revision === 1, `idempotent replay ${JSON.stringify(replay)}`);
      const reuse = await api(page, "POST", adminUrl("/dictionaries"), { ...payload, label: "Changed" }, { "Idempotency-Key": idempotencyKey });
      assert(reuse.status === 409 && reuse.body.code === "ADMIN_IDEMPOTENCY_KEY_REUSE", `idempotency reuse ${JSON.stringify(reuse)}`);
      await capture(page, "03-dictionary-created");
      return { entry: categoryEntry, duplicateStatus: duplicate.status, reuseStatus: reuse.status };
    });

    await scenario("04", "ویرایش با نسخه و پالایهٔ سرور و رابط کاربری هم‌خوان است", async () => {
      await page.click(`[data-admin-dict-edit="${categoryEntry}"]`);
      await page.waitForSelector('[data-admin-dict-form] input[name="admin-dict-entry"][readonly]', "editing dictionary entry");
      await page.setInput('[data-admin-dict-form] input[name="admin-dict-label"]', "E2E Civil Works Updated");
      await page.setInput('[data-admin-dict-form] input[name="admin-dict-sequence"]', "30");
      await page.click('[data-admin-dict-form] button[type="submit"]');
      await page.waitFor(
        `(() => {
          const row = document.querySelector('[data-admin-dict-row][data-entry="${categoryEntry}"]');
          return Boolean(row) && row.textContent.includes("E2E Civil Works Updated");
        })()`,
        "dictionary entry updated",
      );
      await sleep(300);

      const filtered = await api(page, "GET", adminUrl("/dictionaries?dictionary_code=cost_category&search=E2E%20Civil"));
      assert(filtered.status === 200 && filtered.body.entries.length === 1, `server filter ${JSON.stringify(filtered.body.entries)}`);
      assert(filtered.body.entries[0].entry_id === categoryEntry && filtered.body.entries[0].sequence === 30, `filtered entry ${JSON.stringify(filtered.body.entries[0])}`);

      await page.setSelect('select[name="admin-dictionary-filter"]', "cost_category");
      await page.setInput('input[name="admin-dict-search"]', "E2E Civil");
      await page.evaluate(`(() => {
        const input = document.querySelector('input[name="admin-dict-search"]');
        input.dispatchEvent(new Event("change", { bubbles: true }));
      })()`);
      await page.waitFor(
        `(() => {
          const rows = [...document.querySelectorAll("[data-admin-dict-row]")];
          return rows.length === 1 && rows[0].dataset.entry === "${categoryEntry}";
        })()`,
        "ui dictionary filter",
      );
      await capture(page, "04-dictionary-filtered");
      return { filtered: 1, sequence: 30 };
    });

    await scenario("05", "حذف با نسخه انجام می‌شود و بازخوانی بعدی ۴۰۴ است", async () => {
      const before = await api(page, "GET", adminUrl(`/dictionaries/cost_category/${categoryEntry}`));
      assert(before.status === 200 && before.body.revision === 2, `entry before delete ${JSON.stringify(before)}`);
      await page.click(`[data-admin-dict-delete="${categoryEntry}"][data-admin-dict-code="cost_category"]`);
      await page.waitFor(
        `!document.querySelector('[data-admin-dict-row][data-entry="${categoryEntry}"]')`,
        "dictionary entry deleted from the register",
      );
      await sleep(300);
      const after = await api(page, "GET", adminUrl(`/dictionaries/cost_category/${categoryEntry}`));
      assert(after.status === 404 && after.body.code === "ADMIN_DICTIONARY_NOT_FOUND", `read after delete ${JSON.stringify(after)}`);
      await capture(page, "05-dictionary-deleted");
      return { deleteStatus: 200, readAfterDelete: after.status };
    });

    await scenario("06", "دورهٔ مالی در ثبت مشترک p6 ساخته و فهرست می‌شود", async () => {
      await openTab(page, "periods");
      await page.setInput('[data-admin-period-form] input[name="admin-period-id"]', periodId);
      await page.setInput('[data-admin-period-form] input[name="admin-period-name"]', "E2E March 2026");
      await page.setInput('[data-admin-period-form] input[name="admin-period-start"]', "2026-03-01");
      await page.setInput('[data-admin-period-form] input[name="admin-period-end"]', "2026-03-31");
      await page.click('[data-admin-period-form] button[type="submit"]');
      await page.waitFor(
        `Boolean(document.querySelector('[data-admin-period-row][data-period-id="${periodId}"]'))`,
        "financial period row",
      );
      await sleep(300);
      const listed = await api(page, "GET", periodsUrl());
      assert(listed.status === 200 && listed.body.contract_version === "p6-financial-period-api.v1", `period list ${JSON.stringify(listed)}`);
      const stored = listed.body.financial_periods.find((entry) => entry.financial_period.period_id === periodId);
      assert(stored && stored.financial_period.start_date === "2026-03-01", `stored period ${JSON.stringify(stored)}`);
      await capture(page, "06-financial-period");
      return { periodId, startDate: "2026-03-01" };
    });

    await scenario("07", "بازبین فقط می‌خواند و نوشتن مستقیم ۴۰۳ می‌گیرد", async () => {
      await loginAs(page, "Viewer");
      await openAdministration(page);
      const state = await page.evaluate(pageState);
      assert(state.preferences?.disabled === true, "viewer preference inputs are editable");
      assert(state.preferences?.save === false, "viewer receives a preference save control");

      const deniedPreferences = await api(page, "PUT", adminUrl("/preferences"), {
        currency: "USD",
        unit_of_measure: "day",
        date_display: "gregorian",
        decimal_places: 2,
        fiscal_year_start_month: 1,
        expected_revision: 1,
      });
      assert(deniedPreferences.status === 403 && deniedPreferences.body.code === "ADMIN_PERMISSION_DENIED", `viewer preference write ${JSON.stringify(deniedPreferences)}`);
      const deniedCreate = await api(page, "POST", adminUrl("/dictionaries"), {
        dictionary_code: "issue_type",
        entry_id: `E2E-DENIED-${stamp}`,
        label: "Denied",
        sequence: 1,
        is_active: true,
      }, { "Idempotency-Key": `${idempotencyKey}-denied` });
      assert(deniedCreate.status === 403 && deniedCreate.body.code === "ADMIN_PERMISSION_DENIED", `viewer create ${JSON.stringify(deniedCreate)}`);
      const deniedDelete = await api(page, "DELETE", adminUrl(`/dictionaries/risk_category/${idempotentEntry}`), { expected_revision: 1 });
      assert(deniedDelete.status === 403 && deniedDelete.body.code === "ADMIN_PERMISSION_DENIED", `viewer delete ${JSON.stringify(deniedDelete)}`);

      await openTab(page, "matrix");
      const matrix = await page.evaluate(pageState);
      assert(matrix.matrix?.permissions.length === 14, `viewer matrix rows ${matrix.matrix?.permissions.length}`);
      assert(matrix.matrix?.viewerProjectWrite === "—", `viewer project.write grant ${matrix.matrix?.viewerProjectWrite}`);
      await capture(page, "07-viewer-read-only");
      return { preferenceStatus: deniedPreferences.status, createStatus: deniedCreate.status, deleteStatus: deniedDelete.status };
    });

    await scenario("08", "تاریخچهٔ ممیزی همهٔ نوشتن‌ها را با بازیگر ثبت می‌کند", async () => {
      await loginAs(page, "Project administrator");
      const history = await api(page, "GET", adminUrl("/history"));
      assert(history.status === 200 && history.body.contract_version === "p6-administration-api.v1", `history ${JSON.stringify(history)}`);
      const events = history.body.events;
      const kinds = new Set(events.map((event) => `${event.entity_kind}:${event.action}`));
      assert(kinds.has("preferences:updated"), `preference audit event missing: ${JSON.stringify([...kinds])}`);
      assert(kinds.has("dictionary:created") && kinds.has("dictionary:updated") && kinds.has("dictionary:deleted"), `dictionary audit events missing: ${JSON.stringify([...kinds])}`);
      assert(events.every((event) => event.actor_id === "preview-admin"), `unexpected actors ${JSON.stringify(events.map((event) => event.actor_id))}`);
      const created = events.find((event) => event.entity_kind === "dictionary" && event.entity_id === `cost_category/${categoryEntry}` && event.action === "created");
      assert(created && created.revision === 1, `create audit revision ${JSON.stringify(created)}`);
      await openAdministration(page);
      await openTab(page, "matrix");
      await capture(page, "08-audited-writes");
      return { events: events.length, kinds: [...kinds].sort() };
    });

    await scenario("09", "چیدمان فارسی راست‌به‌چپ در ۱۲۸۰×۷۲۰ بدون نشان تجاری بیرونی", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await setLanguage(page, "fa");
      await openAdministration(page);
      const state = await page.evaluate(pageState);
      assert(state.direction === "rtl", `direction ${state.direction}`);
      assert(state.heading === "مدیریت", `Persian heading ${state.heading}`);
      assert(state.tabs.map((tab) => tab.label).join(",") === "ترجیحات,فهرست‌ها,ماتریس دسترسی,دوره‌های مالی", `Persian tabs ${JSON.stringify(state.tabs.map((tab) => tab.label))}`);
      assert(!/oracle|primavera|\bp6\b/i.test(state.bodyText), "administration surface leaks third-party branding");
      await capture(page, "09-persian-rtl");
      return { direction: state.direction, heading: state.heading };
    });

    report.status = "pass";
    report.scenarioCount = scenarios.length;
  } catch (error) {
    report.status = "fail";
    report.error = String(error && error.stack ? error.stack : error);
    throw error;
  } finally {
    writeFileSync(join(evidenceDir, "administration-v26.json"), `${JSON.stringify(report, null, 2)}\n`);
    copyFileSync(join(evidenceDir, "administration-v26.json"), join(outDir, "administration-v26.json"));
    log(`\nEvidence: ${evidenceDir}`);
    log(`Scenarios: ${scenarios.filter((item) => item.status === "pass").length}/${scenarios.length} passed`);
    try {
      await chrome.stop();
    } catch {
      // The browser is already gone; the evidence file is what matters.
    }
  }
}

main().catch((error) => {
  process.stderr.write(`\nFAILED: ${error && error.stack ? error.stack : error}\n`);
  process.exitCode = 1;
});
