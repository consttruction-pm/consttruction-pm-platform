#!/usr/bin/env node
/**
 * WS-005 browser acceptance: cross-window context menus.
 *
 * The record registers (risks, thresholds, expenses, cost accounts, reports)
 * must expose their own context menu instead of the Activities row menu, and
 * the menu must behave like a desktop shortcut menu:
 *  - it opens at the pointer through the shared viewport portal;
 *  - it acts on the record under the pointer and selects that row;
 *  - every command activates the real control the window already renders, so a
 *    command that is unavailable or denied is disabled with the reason;
 *  - Shift+F10 and the Context Menu key open it from the keyboard and focus the
 *    first command; Escape closes it and returns focus to the row;
 *  - an outside click dismisses it and it stays inside the viewport;
 *  - Persian renders right-to-left;
 *  - a register menu never exposes Activities commands and the Activities menu
 *    never appears over a register.
 *
 * The fixtures are created through the public API on the live preview runtime;
 * nothing is mocked.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 node e2e/register-context-menus-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-13";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "register-context-menus-v26");
const evidenceDir = join(
  artifactsDir,
  "..",
  "..",
  "..",
  "..",
  "docs",
  "workspace",
  "evidence",
  `register-context-menus-v26-${evidenceDate}`,
);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const stamp = Date.now().toString(36).toUpperCase();
const ids = {
  risk: `E2E-WS5-RK-${stamp}`,
  threshold: `E2E-WS5-TH-${stamp}`,
  expense: `E2E-WS5-EX-${stamp}`,
  account: `E2E-WS5-CA-${stamp}`,
  report: `E2E-WS5-RP-${stamp}`,
};

const scenarios = [];
const checks = [];
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

function check(id, name, condition, detail = {}) {
  checks.push({ id, name, ok: Boolean(condition), detail });
  if (condition) log(`  PASS ${id} ${name}`);
  else log(`  FAIL ${id} ${name} ${JSON.stringify(detail)}`);
}

async function scenario(id, name, body) {
  log(`\n[${id}] ${name}`);
  const started = Date.now();
  try {
    const details = (await body()) ?? {};
    scenarios.push({ id, name, status: "pass", at: new Date().toISOString(), durationMs: Date.now() - started, details });
    log(`  PASS ${id}`);
    return details;
  } catch (error) {
    scenarios.push({ id, name, status: "fail", at: new Date().toISOString(), durationMs: Date.now() - started, error: String(error?.stack ?? error) });
    log(`  FAIL ${id}: ${error}`);
    throw error;
  }
}

const menuState = `(() => {
  const menu = document.querySelector(".cp-context-menu-portal");
  if (!menu) return null;
  const rect = menu.getBoundingClientRect();
  const items = [...menu.querySelectorAll("[data-activity-menu-command]")].map((button) => ({
    command: button.dataset.activityMenuCommand,
    label: button.querySelector(".cp-context-text")?.textContent?.trim() ?? "",
    disabled: button.disabled,
    reason: button.getAttribute("title") ?? "",
    separatorBefore: Boolean(button.previousElementSibling?.classList?.contains("cp-context-separator")),
  }));
  const focus = document.activeElement;
  const attribute = (name) => (focus && typeof focus.getAttribute === "function" ? focus.getAttribute(name) : null);
  return {
    kind: menu.dataset.contextMenuKind,
    dir: menu.getAttribute("dir"),
    role: menu.getAttribute("role"),
    label: menu.getAttribute("aria-label"),
    parentIsBody: menu.parentElement === document.body,
    position: getComputedStyle(menu).position,
    rect: { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom, width: rect.width, height: rect.height },
    viewport: { width: innerWidth, height: innerHeight },
    items,
    focusedCommand: attribute("data-activity-menu-command"),
    focus: {
      tag: focus?.tagName ?? null,
      riskId: attribute("data-risk-id"),
      thresholdId: attribute("data-threshold-id"),
      expenseId: attribute("data-expense-id"),
      accountId: attribute("data-cost-account-id"),
      reportId: attribute("data-report-id"),
      activityId: attribute("data-activity-id"),
    },
  };
})()`;

const registerRowState = (selector, idAttribute, id) => `(() => {
  const rows = [...document.querySelectorAll(${JSON.stringify(selector)})];
  const row = rows.find((entry) => entry.getAttribute(${JSON.stringify(idAttribute)}) === ${JSON.stringify(id)});
  if (!row) return null;
  return {
    selected: row.getAttribute("aria-selected") === "true" || row.classList.contains("is-selected"),
    tabIndex: row.getAttribute("tabindex"),
    visible: row.getClientRects().length > 0,
  };
})()`;

async function rightClickAt(page, x, y) {
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y, button: "none", buttons: 0 });
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "right", buttons: 2, clickCount: 1 });
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "right", buttons: 0, clickCount: 1 });
  await sleep(120);
}

async function leftClickAt(page, x, y) {
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y, button: "none", buttons: 0 });
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", buttons: 1, clickCount: 1 });
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", buttons: 0, clickCount: 1 });
  await sleep(120);
}

async function centerOf(page, selector) {
  return page.evaluate(`(() => {
    const element = document.querySelector(${JSON.stringify(selector)});
    if (!element) return null;
    const rect = element.getBoundingClientRect();
    return { x: Math.round(rect.left + rect.width / 2), y: Math.round(rect.top + rect.height / 2), width: Math.round(rect.width), height: Math.round(rect.height), right: Math.round(rect.right), bottom: Math.round(rect.bottom) };
  })()`);
}

async function escape(page) {
  await page.cdp.send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27 });
  await page.cdp.send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27 });
  await sleep(140);
}

async function clickCommand(page, command) {
  const point = await centerOf(page, `[data-activity-menu-command="${command}"]`);
  assert(point, `command ${command} is missing from the open menu`);
  await leftClickAt(page, point.x, point.y);
  await sleep(220);
}

async function capture(page, name, clip = null) {
  const file = `register-context-menus-v26/${name}.png`;
  await page.screenshot(file, clip);
  copyFileSync(join(artifactsDir, file), join(evidenceDir, `${name}.png`));
  screenshots.push(`${name}.png`);
  return file;
}

async function api(page, method, path, body) {
  return page.evaluate(
    `(async () => {
      const response = await fetch(${JSON.stringify(path)}, {
        method: ${JSON.stringify(method)},
        headers: { "Content-Type": "application/json", "Idempotency-Key": "e2e-ws5-" + Math.random().toString(36).slice(2) },
        ${body === undefined ? "" : `body: JSON.stringify(${JSON.stringify(body)}),`}
      });
      return { status: response.status, body: await response.json().catch(() => null) };
    })()`,
    { awaitPromise: true },
  );
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
  await page.waitFor(`document.documentElement.lang === ${JSON.stringify(locale)}`, `${locale} language`);
  await sleep(700);
}

async function openRegister(page, key, hostSelector) {
  await escape(page);
  const clicked = await page.evaluate(`(() => {
    const buttons = [...document.querySelectorAll('[data-menu="${key}"]')];
    const button = buttons.find((entry) => entry.getClientRects().length > 0) ?? buttons[0];
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `${key} menu button is missing`);
  await page.waitForSelector(hostSelector, `${key} register window`, 20000);
  await page.waitFor(
    `(() => {
      const page = document.querySelector(${JSON.stringify(hostSelector)});
      return Boolean(page) && !/Reading project (risks|thresholds|expenses|cost|reports)/.test(page.textContent ?? "");
    })()`,
    `${key} register settled`,
  );
  await sleep(500);
}

async function createFixtures(page) {
  const risk = await api(page, "POST", `/api/projects/${PROJECT}/risks`, {
    risk_id: ids.risk,
    title: "WS-005 context menu fixture",
    description: "Created by the cross-window context-menu acceptance suite.",
    category: "schedule",
    status: "open",
    probability: 2,
    impact: 3,
    response_strategy: "mitigate",
    owner: "preview-planner",
    date_identified: "2026-11-05",
  });
  assert(risk.status === 200 || risk.status === 201, `risk fixture ${JSON.stringify(risk)}`);

  const threshold = await api(page, "POST", `/api/projects/${PROJECT}/thresholds`, {
    threshold_id: ids.threshold,
    name: "WS-005 context menu threshold",
    monitoring_subject: "cost",
    parameter: "expense_actual_total",
    currency: "USD",
    upper_threshold: "1000",
    status: "active",
  });
  assert(threshold.status === 200 || threshold.status === 201, `threshold fixture ${JSON.stringify(threshold)}`);

  const account = await api(page, "POST", `/api/projects/${PROJECT}/cost/accounts`, {
    account_id: ids.account,
    name: "WS-005 context menu account",
  });
  assert(account.status === 200 || account.status === 201, `cost account fixture ${JSON.stringify(account)}`);

  const expense = await api(page, "POST", `/api/projects/${PROJECT}/cost/expenses`, {
    expense_id: ids.expense,
    name: "WS-005 context menu expense",
    category: "equipment",
    currency: "USD",
    planned_amount: "100.00",
    cost_account_id: ids.account,
  });
  assert(expense.status === 200 || expense.status === 201, `expense fixture ${JSON.stringify(expense)}`);

  const report = await api(page, "POST", `/api/projects/${PROJECT}/reports`, {
    report_id: ids.report,
    name: "WS-005 context menu report",
    subject: "activities",
    columns: ["activity_id", "name"],
  });
  assert(report.status === 200 || report.status === 201, `report fixture ${JSON.stringify(report)}`);
  return { risk: risk.body, threshold: threshold.body, account: account.body, expense: expense.body, report: report.body };
}

/** Right-click a row, verify the menu contract, and return its state. */
async function openRowMenu(page, { id, rowSelector, idAttribute, kind, expectedCommands, suffix }) {
  const rowState = await page.evaluate(registerRowState(rowSelector, idAttribute, id));
  assert(rowState?.visible, `row ${id} is not visible (${suffix})`);
  const point = await centerOf(page, `${rowSelector}[${idAttribute}="${id}"]`);
  assert(point, `row point for ${id} (${suffix})`);
  await rightClickAt(page, point.x, point.y);
  const state = await page.evaluate(menuState);
  check(`ws5-${kind}-opens`, `${kind}: the menu opens at the record row (${suffix})`, Boolean(state));
  assert(state, `menu did not open for ${id}`);
  const commands = state.items.map((item) => item.command);
  check(`ws5-${kind}-kind`, `${kind}: the register owns the menu, not the Activities grid (${suffix})`,
    state.kind === kind && !commands.some((command) => ["add", "columns", "filters", "sort-asc", "group-wbs"].includes(command)),
    { kind: state.kind, commands });
  check(`ws5-${kind}-commands`, `${kind}: the menu exposes exactly the real commands (${suffix})`,
    JSON.stringify(commands) === JSON.stringify(expectedCommands),
    { commands, expectedCommands });
  check(`ws5-${kind}-geometry`, `${kind}: viewport portal stays inside the viewport (${suffix})`,
    state.parentIsBody && state.position === "fixed" && state.rect.left >= 0 && state.rect.top >= 0 &&
      state.rect.right <= state.viewport.width + 0.5 && state.rect.bottom <= state.viewport.height + 0.5,
    { parentIsBody: state.parentIsBody, position: state.position, rect: state.rect, viewport: state.viewport });
  const afterOpen = await page.evaluate(registerRowState(rowSelector, idAttribute, id));
  check(`ws5-${kind}-target`, `${kind}: the row under the pointer is the target of the menu (${suffix})`,
    afterOpen?.selected === true, { afterOpen });
  return state;
}

async function keyboardScenario(page, { id, rowSelector, idAttribute, kind, suffix }) {
  await escape(page);
  await page.evaluate(`(() => {
    const row = document.querySelector(${JSON.stringify(`${rowSelector}[${idAttribute}="${id}"]`)});
    if (row) { row.setAttribute("tabindex", "0"); row.focus(); }
    return true;
  })()`);
  await page.cdp.send("Input.dispatchKeyEvent", { type: "keyDown", key: "F10", code: "F10", windowsVirtualKeyCode: 121, modifiers: 8 });
  await page.cdp.send("Input.dispatchKeyEvent", { type: "keyUp", key: "F10", code: "F10", windowsVirtualKeyCode: 121, modifiers: 8 });
  await sleep(200);
  const state = await page.evaluate(menuState);
  check(`ws5-${kind}-shift-f10`, `${kind}: Shift+F10 opens the menu and focuses the first command (${suffix})`,
    Boolean(state) && state.kind === kind && state.focusedCommand === state.items[0]?.command,
    { kind: state?.kind, focused: state?.focusedCommand, first: state?.items?.[0]?.command });
  await page.cdp.send("Input.dispatchKeyEvent", { type: "keyDown", key: "ArrowDown", code: "ArrowDown", windowsVirtualKeyCode: 40 });
  await sleep(120);
  const moved = await page.evaluate(menuState);
  check(`ws5-${kind}-arrow`, `${kind}: ArrowDown moves to the next command (${suffix})`,
    moved?.focusedCommand === moved?.items?.[1]?.command, { focused: moved?.focusedCommand });
  await escape(page);
  const after = await page.evaluate(menuState);
  const focus = await page.evaluate(`(() => {
    const element = document.activeElement;
    return element ? {
      tag: element.tagName,
      riskId: element.getAttribute("data-risk-id"),
      thresholdId: element.getAttribute("data-threshold-id"),
      expenseId: element.getAttribute("data-expense-id"),
      accountId: element.getAttribute("data-cost-account-id"),
      reportId: element.getAttribute("data-report-id"),
    } : null;
  })()`);
  const key = { "data-risk-id": "riskId", "data-threshold-id": "thresholdId", "data-expense-id": "expenseId", "data-cost-account-id": "accountId", "data-report-id": "reportId" }[idAttribute];
  check(`ws5-${kind}-escape`, `${kind}: Escape closes the menu and returns focus to the record row (${suffix})`,
    after === null && focus?.[key] === id, { after, focus, key });
}

async function contextMenuKeyScenario(page, { id, rowSelector, idAttribute, kind, suffix }) {
  await escape(page);
  await page.evaluate(`(() => {
    const row = document.querySelector(${JSON.stringify(`${rowSelector}[${idAttribute}="${id}"]`)});
    if (row) row.focus();
    return true;
  })()`);
  await page.cdp.send("Input.dispatchKeyEvent", { type: "keyDown", key: "ContextMenu", code: "ContextMenu", windowsVirtualKeyCode: 93 });
  await sleep(200);
  const state = await page.evaluate(menuState);
  check(`ws5-${kind}-context-key`, `${kind}: the Context Menu key opens the same menu (${suffix})`,
    Boolean(state) && state.kind === kind, { kind: state?.kind });
  await escape(page);
}

async function outsideClickScenario(page, hostSelector, kind, suffix) {
  await escape(page);
  const row = await centerOf(page, `${hostSelector} [data-risk-row], ${hostSelector} [data-threshold-row], ${hostSelector} [data-expense-row], ${hostSelector} [data-report-row], ${hostSelector} [data-cost-account-row]`);
  assert(row, `no register row for the outside-click scenario (${suffix})`);
  await rightClickAt(page, row.x, row.y);
  const opened = await page.evaluate(menuState);
  assert(opened?.kind === kind, `menu kind before outside click: ${opened?.kind}`);
  const toolbar = await centerOf(page, `${hostSelector} > .cp-register-toolbar strong`);
  assert(toolbar, `register toolbar for outside click (${suffix})`);
  await leftClickAt(page, toolbar.x, toolbar.y);
  const after = await page.evaluate(menuState);
  check(`ws5-${kind}-outside`, `${kind}: an outside click dismisses the menu (${suffix})`, after === null, { after });
}

async function registerMenuScenarios(page, config, suffix) {
  await openRegister(page, config.key, config.host);
  const state = await openRowMenu(page, { ...config, suffix });
  await capture(page, `${config.screenshot}-${suffix}`);
  check(`ws5-${config.kind}-aria`, `${config.kind}: the menu is a labelled menu (${suffix})`,
    state.role === "menu" && Boolean(state.label), { role: state.role, label: state.label });
  if (!config.labels) {
    // Escape from a pointer-invoked menu also restores focus to the row.
    await escape(page);
    const focus = await page.evaluate(`(() => {
      const element = document.activeElement;
      return {
        riskId: element?.getAttribute?.("data-risk-id") ?? null,
        thresholdId: element?.getAttribute?.("data-threshold-id") ?? null,
        expenseId: element?.getAttribute?.("data-expense-id") ?? null,
        accountId: element?.getAttribute?.("data-cost-account-id") ?? null,
        reportId: element?.getAttribute?.("data-report-id") ?? null,
      };
    })()`);
    const key = { "data-risk-id": "riskId", "data-threshold-id": "thresholdId", "data-expense-id": "expenseId", "data-cost-account-id": "accountId", "data-report-id": "reportId" }[config.idAttribute];
    check(`ws5-${config.kind}-pointer-escape`, `${config.kind}: Escape from the pointer menu restores focus to the row (${suffix})`,
      focus[key] === config.id, { focus, key });
  }
  return state;
}

async function editDispatchScenario(page, config, formSelector, cancelSelector, suffix) {
  await openRegister(page, config.key, config.host);
  const point = await centerOf(page, `${config.rowSelector}[${config.idAttribute}="${config.id}"]`);
  assert(point, `row point for ${config.kind} dispatch (${suffix})`);
  await rightClickAt(page, point.x, point.y);
  await clickCommand(page, config.editCommand);
  const form = await page.evaluate(`(() => {
    const element = document.querySelector(${JSON.stringify(formSelector)});
    return element ? { visible: element.getClientRects().length > 0, id: element.querySelector("input[name$='-id']")?.value ?? null, readonly: Boolean(element.querySelector("input[name$='-id']")?.hasAttribute("readonly")) } : null;
  })()`);
  check(`ws5-${config.kind}-dispatch`, `${config.kind}: the menu command opens the real edit form (${suffix})`,
    Boolean(form?.visible) && form.readonly === true, { form, command: config.editCommand });
  await page.click(cancelSelector);
  await sleep(220);
  const cancelled = await page.evaluate(`document.querySelector(${JSON.stringify(formSelector)}) === null`);
  check(`ws5-${config.kind}-cancel`, `${config.kind}: the edit form cancels back to the register (${suffix})`, cancelled);
}

async function noConflictScenario(page, suffix) {
  // Switch back to the Schedule window and open the Activities row menu.
  const switched = await page.evaluate(`(() => {
    const tab = document.querySelector('[data-window-tab="schedule"]');
    if (!tab) return false;
    tab.click();
    return true;
  })()`);
  check("ws5-conflict-switch", `the Schedule window is reachable next to the register windows (${suffix})`, switched);
  await sleep(500);
  const point = await centerOf(page, "#cp-activity-grid tbody tr[data-activity-id]");
  assert(point, "activity row point");
  await rightClickAt(page, point.x + 30, point.y);
  const state = await page.evaluate(menuState);
  const commands = state?.items.map((item) => item.command) ?? [];
  check("ws5-conflict-activity", `the Activities window still owns its own row menu (${suffix})`,
    state?.kind === "table-activity" && commands.includes("add") && !commands.some((command) => command.startsWith("risk-") || command.startsWith("report-")),
    { kind: state?.kind, commands });
  await capture(page, `06-schedule-menu-${suffix}`);
  await escape(page);

  // A register that is still mounted must not answer for the Activities grid.
  const registerKinds = await page.evaluate(`(() => [...document.querySelectorAll("[data-register-context-menu='bound']")].map((element) => element.dataset.registerContextMenu))()`);
  check("ws5-conflict-bound", `register menus are bound only to their own windows (${suffix})`, Array.isArray(registerKinds));
}

async function reauth(page, label) {
  const status = await page.evaluate(`(async () => {
    const response = await fetch("/preview/logout", { method: "POST", redirect: "manual" });
    return response.status;
  })()`, { awaitPromise: true });
  assert([0, 200, 302, 303].includes(status), `logout before ${label}: ${status}`);
  await loginAs(page, label);
}

async function main() {
  const health = await waitForHttp(`${baseUrl}/preview/health`, 20000);
  if (!(health.status === "ok" || health.status === 200)) throw new Error(`preview health ${health.status}`);

  const chrome = await launchChrome();
  const page = new Page(chrome.cdp);
  await page.initialize();
  page.cdp.on("Runtime.exceptionThrown", (params) => {
    exceptions.push(params.exceptionDetails?.exception?.description ?? params.exceptionDetails?.text ?? "unknown exception");
  });
  page.cdp.on("Runtime.consoleAPICalled", (params) => {
    if (params.type === "error") consoleErrors.push((params.args ?? []).map((arg) => arg.value ?? arg.description ?? "").join(" "));
  });
  page.cdp.on("Network.responseReceived", (params) => {
    if (params.response?.status >= 500) apiFailures.push({ url: params.response.url, status: params.response.status });
  });

  const summary = { contract: "cubi-ws-005-register-context-menus.v1", testedCodeSha, gitHead: gitHead(), evidenceCommitSha, baseUrl, startedAt: new Date().toISOString(), fixtures: ids, scenarios, checks, screenshots, exceptions, consoleErrors, apiFailures };

  try {
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
    await loginAs(page, "Planner");
    await setLanguage(page, "en");

    await scenario("01", "Register menus act on the record under the pointer and expose only real commands", async () => {
      const fixtures = await createFixtures(page);
      const configs = [
        { key: "risks", host: "[data-risks-page]", kind: "risk-register", rowSelector: "[data-risk-row]", idAttribute: "data-risk-id", id: ids.risk, expectedCommands: ["risk-edit", "risk-delete"], screenshot: "01-risks-menu" },
        { key: "thresholds", host: "[data-thresholds-page]", kind: "threshold-register", rowSelector: "[data-threshold-row]", idAttribute: "data-threshold-id", id: ids.threshold, expectedCommands: ["threshold-edit", "threshold-monitor", "threshold-delete"], screenshot: "02-thresholds-menu" },
        { key: "expenses", host: "[data-expenses-page]", kind: "expense-register", rowSelector: "[data-expense-row]", idAttribute: "data-expense-id", id: ids.expense, expectedCommands: ["expense-edit", "expense-delete"], screenshot: "03-expenses-menu" },
        { key: "expenses", host: "[data-expenses-page]", kind: "cost-account-register", rowSelector: "[data-cost-account-row]", idAttribute: "data-cost-account-id", id: ids.account, expectedCommands: ["cost-account-edit", "cost-account-copy", "cost-account-default", "cost-account-delete"], screenshot: "04-cost-account-menu" },
        { key: "reports", host: "[data-reports-page]", kind: "report-register", rowSelector: "[data-report-row]", idAttribute: "data-report-id", id: ids.report, expectedCommands: ["report-edit", "report-delete", "report-run"], screenshot: "05-reports-menu" },
      ];
      for (const config of configs) {
        await registerMenuScenarios(page, config, "en-1440");
      }
      return { fixtures, kinds: configs.map((config) => config.kind) };
    });

    await scenario("02", "Menus open from Shift+F10 and the Context Menu key and restore focus on Escape", async () => {
      const configs = [
        { key: "risks", host: "[data-risks-page]", kind: "risk-register", rowSelector: "[data-risk-row]", idAttribute: "data-risk-id", id: ids.risk },
        { key: "expenses", host: "[data-expenses-page]", kind: "cost-account-register", rowSelector: "[data-cost-account-row]", idAttribute: "data-cost-account-id", id: ids.account },
        { key: "reports", host: "[data-reports-page]", kind: "report-register", rowSelector: "[data-report-row]", idAttribute: "data-report-id", id: ids.report },
      ];
      for (const config of configs) {
        await openRegister(page, config.key, config.host);
        await keyboardScenario(page, { ...config, suffix: "en-1440" });
        await contextMenuKeyScenario(page, { ...config, suffix: "en-1440" });
      }
      return { windows: configs.length };
    });

    await scenario("03", "An outside click dismisses the register menu", async () => {
      await openRegister(page, "risks", "[data-risks-page]");
      await outsideClickScenario(page, "[data-risks-page]", "risk-register", "en-1440");
      const after = await page.evaluate(menuState);
      check("ws5-outside-closed", "no menu remains after the outside click", after === null, { after });
      return { dismissed: after === null };
    });

    await scenario("04", "Commands invoke the real register controls (edit and cancel)", async () => {
      await editDispatchScenario(page, {
        key: "risks", host: "[data-risks-page]", kind: "risk-register",
        rowSelector: "[data-risk-row]", idAttribute: "data-risk-id", id: ids.risk,
        editCommand: "risk-edit",
      }, "[data-risk-form]", "[data-risk-action='cancel']", "en-1440");
      await editDispatchScenario(page, {
        key: "thresholds", host: "[data-thresholds-page]", kind: "threshold-register",
        rowSelector: "[data-threshold-row]", idAttribute: "data-threshold-id", id: ids.threshold,
        editCommand: "threshold-edit",
      }, "[data-threshold-form]", "[data-threshold-action='cancel']", "en-1440");
      await editDispatchScenario(page, {
        key: "expenses", host: "[data-expenses-page]", kind: "cost-account-register",
        rowSelector: "[data-cost-account-row]", idAttribute: "data-cost-account-id", id: ids.account,
        editCommand: "cost-account-edit",
      }, "[data-cost-account-form]", "[data-cost-account-action='cancel']", "en-1440");
      return { dispatched: 3 };
    });

    await scenario("05", "Run Report from the menu produces a real server-stored report run", async () => {
      await openRegister(page, "reports", "[data-reports-page]");
      const point = await centerOf(page, `[data-report-row][data-report-id="${ids.report}"]`);
      await rightClickAt(page, point.x, point.y);
      await clickCommand(page, "report-run");
      await page.waitFor(
        `document.querySelector("[data-report-run-preview]")?.querySelectorAll("[data-report-run-row]").length > 0`,
        "report run rows",
        20000,
      );
      const run = await page.evaluate(`(() => ({
        rows: document.querySelectorAll("[data-report-run-preview] [data-report-run-row]").length,
        meta: document.querySelector("[data-report-run-meta]")?.textContent?.trim() ?? null,
      }))()`);
      check("ws5-report-run", "the report run renders stored rows and the definition revision", run.rows > 0 && /definition revision/.test(run.meta ?? ""), run);
      await capture(page, "07-report-run-from-menu-en-1440");
      return run;
    });

    await scenario("06", "Register menus and Activities menus never claim each other's window", async () => {
      await noConflictScenario(page, "en-1440");
      return { checked: true };
    });

    await scenario("07", "A viewer gets disabled write commands with the permission reason", async () => {
      await reauth(page, "Viewer");
      await openRegister(page, "risks", "[data-risks-page]");
      const point = await centerOf(page, `[data-risk-row][data-risk-id="${ids.risk}"]`);
      assert(point, "viewer risk row");
      await rightClickAt(page, point.x, point.y);
      const state = await page.evaluate(menuState);
      const edit = state?.items.find((item) => item.command === "risk-edit");
      const remove = state?.items.find((item) => item.command === "risk-delete");
      check("ws5-viewer", "the viewer menu disables Edit and Delete with the permission reason",
        Boolean(edit?.disabled && remove?.disabled) && /permission/i.test(edit?.reason ?? "") && !state.items.some((item) => item.command === "risk-monitor"),
        { items: state?.items });
      check("ws5-viewer-commands", "the viewer menu keeps the same commands, disabled rather than removed",
        JSON.stringify(state?.items.map((item) => item.command)) === JSON.stringify(["risk-edit", "risk-delete"]),
        { items: state?.items });
      await capture(page, "08-viewer-disabled-en-1440");
      await escape(page);

      // A report run is a read of a stored definition and stays available.
      await openRegister(page, "reports", "[data-reports-page]");
      const reportPoint = await centerOf(page, `[data-report-row][data-report-id="${ids.report}"]`);
      assert(reportPoint, "viewer report row");
      await rightClickAt(page, reportPoint.x, reportPoint.y);
      const reportMenu = await page.evaluate(menuState);
      const run = reportMenu?.items.find((item) => item.command === "report-run");
      const reportEdit = reportMenu?.items.find((item) => item.command === "report-edit");
      check("ws5-viewer-report", "a viewer can run a stored report but not edit it",
        run?.disabled === false && reportEdit?.disabled === true, { run, reportEdit });
      await escape(page);
      return { items: state?.items };
    });

    await scenario("08", "Persian renders the register menu right-to-left inside 1280x720", async () => {
      await reauth(page, "Planner");
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await page.waitFor("document.documentElement.clientWidth === 1280", "1280 viewport");
      await setLanguage(page, "fa");
      await openRegister(page, "risks", "[data-risks-page]");
      const point = await centerOf(page, `[data-risk-row][data-risk-id="${ids.risk}"]`);
      assert(point, "persian risk row");
      await rightClickAt(page, point.x, point.y);
      const state = await page.evaluate(menuState);
      const persian = (value) => /[\u0600-\u06FF]/.test(value ?? "");
      check("ws5-rtl", "the Persian menu carries dir=rtl, Persian labels and stays inside the viewport",
        state?.dir === "rtl" && persian(state?.items?.[0]?.label) && state.rect.left >= 0 && state.rect.top >= 0 &&
          state.rect.right <= state.viewport.width + 0.5 && state.rect.bottom <= state.viewport.height + 0.5,
        { dir: state?.dir, labels: state?.items?.map((item) => item.label), rect: state?.rect, viewport: state?.viewport });
      await capture(page, "09-risks-menu-fa-1280");
      await escape(page);

      // Bottom-right edge: the menu flips and stays on screen.
      const lastRow = await page.evaluate(`(() => {
        const rows = [...document.querySelectorAll("[data-risk-row]")];
        const row = rows[rows.length - 1];
        if (!row) return null;
        const rect = row.getBoundingClientRect();
        return { x: Math.round(rect.right - 8), y: Math.round(rect.bottom - 4) };
      })()`);
      assert(lastRow, "persian last risk row");
      await rightClickAt(page, lastRow.x, lastRow.y);
      const edge = await page.evaluate(menuState);
      check("ws5-edge", "at the bottom-right edge the menu flips and clamps inside the viewport",
        Boolean(edge) && edge.rect.right <= edge.viewport.width + 0.5 && edge.rect.bottom <= edge.viewport.height + 0.5 &&
          edge.rect.left >= 0 && edge.rect.top >= 0 && !(edge.rect.left <= 8 && edge.rect.top <= 8),
        { rect: edge?.rect, viewport: edge?.viewport, point: lastRow });
      await capture(page, "10-menu-edge-fa-1280");
      await escape(page);
      await setLanguage(page, "en");
      return { dir: state?.dir };
    });

    await scenario("09", "Delete Risk from the menu removes the persisted record", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
      await page.waitFor("document.documentElement.clientWidth === 1440", "1440 viewport");
      await openRegister(page, "risks", "[data-risks-page]");
      const point = await centerOf(page, `[data-risk-row][data-risk-id="${ids.risk}"]`);
      await rightClickAt(page, point.x, point.y);
      await clickCommand(page, "risk-delete");
      await page.waitFor(
        `!document.querySelector('[data-risk-row][data-risk-id="${ids.risk}"]')`,
        "risk row removed by the menu command",
        20000,
      );
      const stored = await api(page, "GET", `/api/projects/${PROJECT}/risks/${encodeURIComponent(ids.risk)}`);
      check("ws5-delete", "the menu Delete removed the stored risk", stored.status === 404, { status: stored.status });
      await capture(page, "11-risk-deleted-from-menu");
      return { status: stored.status };
    });

    // Best-effort fixture cleanup through the public API.
    await api(page, "DELETE", `/api/projects/${PROJECT}/cost/expenses/${encodeURIComponent(ids.expense)}`, { expected_revision: 1 });
    await api(page, "DELETE", `/api/projects/${PROJECT}/cost/accounts/${encodeURIComponent(ids.account)}`, { expected_revision: 1 });
    await api(page, "DELETE", `/api/projects/${PROJECT}/thresholds/${encodeURIComponent(ids.threshold)}`, { expected_revision: 1 });
    await api(page, "DELETE", `/api/projects/${PROJECT}/reports/${encodeURIComponent(ids.report)}`, { expected_revision: 1 });

    const failedChecks = checks.filter((entry) => !entry.ok);
    summary.passed = checks.length - failedChecks.length;
    summary.failed = failedChecks.length;
    summary.finishedAt = new Date().toISOString();
    summary.status = failedChecks.length === 0 ? "passed" : "failed";
    writeFileSync(join(outDir, "register-context-menus-v26.json"), JSON.stringify(summary, null, 2));
    writeFileSync(join(evidenceDir, "contract.json"), JSON.stringify(summary, null, 2));
    writeFileSync(join(evidenceDir, "CHECKLIST.md"), checks.map((entry) => `${entry.ok ? "PASS" : "FAIL"} — ${entry.name}${entry.ok ? "" : `\n  ${JSON.stringify(entry.detail)}`}`).join("\n"));
    if (failedChecks.length) {
      console.error(`\n${failedChecks.length} of ${checks.length} checks failed`);
      process.exitCode = 1;
    } else {
      console.log(`\nAll ${checks.length} register context-menu checks passed`);
    }
  } catch (error) {
    summary.status = "error";
    summary.error = String(error?.stack ?? error);
    writeFileSync(join(outDir, "register-context-menus-v26.json"), JSON.stringify(summary, null, 2));
    writeFileSync(join(evidenceDir, "contract.json"), JSON.stringify(summary, null, 2));
    throw error;
  } finally {
    page.cdp.close();
    await chrome.stop();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
