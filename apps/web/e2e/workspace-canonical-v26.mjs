#!/usr/bin/env node
/**
 * Browser E2E for the Version 26 canonical workspace integration (Stage G).
 *
 * The Reports, Administration, Import / Export and Backup / Recovery surfaces
 * already ship as real windows, but until Stage G the desktop menu bar still
 * advertised three of them as unavailable and had no entry at all for import /
 * export or backup. This script drives the real local full-stack preview through
 * headless Chrome and reaches every one of those windows exclusively through the
 * canonical menu bar (Tools and Administration), never through a direct URL or a
 * rail shortcut. No page fixture is injected and no API response is mocked.
 *
 * Scenarios cover the Tools entries, the Administration rewiring, independent
 * window tabs that keep each surface mounted, viewer capability gating, and the
 * 1280x720 Persian right-to-left menu bar.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 node e2e/workspace-canonical-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "workspace-canonical-v26");
const evidenceDir = join(
  artifactsDir,
  "..",
  "..",
  "..",
  "..",
  "docs",
  "workspace",
  "evidence",
  `workspace-canonical-v26-${evidenceDate}`,
);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
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
  const text = (node) => (node?.textContent ?? "").trim();
  const workspace = document.querySelector(".cp-workspace");
  const popup = (id) => document.querySelector('[data-desktop-popup="' + id + '"]');
  const items = (id) => [...(popup(id)?.querySelectorAll("[data-desktop-item]") ?? [])].map((item) => ({
    id: item.dataset.desktopItem,
    label: text(item.querySelector(".cp-menubar-item-label")),
    window: item.dataset.desktopWindow ?? null,
    command: item.dataset.desktopCommand ?? null,
    disabled: item.hasAttribute("disabled"),
    reason: text(item.querySelector(".cp-menubar-item-reason")) || null,
  }));
  const pageOf = (selector) => {
    const page = document.querySelector(selector);
    if (!page) return null;
    return {
      heading: text(page.querySelector(":scope > .cp-register-toolbar strong")),
      tabs: [...page.querySelectorAll("[data-reports-tab], [data-administration-tab], [data-exchange-tab], [data-backup-tab]")].map((tab) => text(tab)),
      text: text(page).slice(0, 400),
    };
  };
  return {
    direction: workspace?.getAttribute("dir") ?? null,
    activeMenu: workspace?.dataset.activeMenu ?? null,
    menus: [...document.querySelectorAll("[data-desktop-menu]")].map((trigger) => ({
      id: trigger.dataset.desktopMenu,
      label: text(trigger),
      expanded: trigger.getAttribute("aria-expanded") === "true",
    })),
    tools: items("tools"),
    administration: items("administration"),
    tabs: [...document.querySelectorAll("[data-window-tab]")].map((tab) => ({
      key: tab.dataset.windowTab,
      selected: tab.getAttribute("aria-selected") === "true",
      label: text(tab.querySelector("[data-window-open]")),
      dirty: tab.dataset.windowDirty === "true",
    })),
    pages: {
      reports: pageOf("[data-reports-page]"),
      administration: pageOf("[data-administration-page]"),
      exchange: pageOf("[data-exchange-page]"),
      backup: pageOf("[data-backup-page]"),
    },
    backupCreateDisabled: Boolean(document.querySelector('[data-backup-page] [data-backup-action="create"]')?.disabled),
    workspaceText: text(workspace).slice(0, 2000),
  };
})()`;

async function capture(page, name) {
  const file = `workspace-canonical-v26/${name}.png`;
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

/** Opens a canonical menu bar popup by menu id and leaves it visible. */
async function openDesktopMenu(page, menuId) {
  const state = await page.evaluate(`(() => {
    const trigger = document.querySelector('[data-desktop-menu=' + ${JSON.stringify(JSON.stringify(menuId))} + ']');
    if (!trigger) return { found: false, expanded: false };
    const expanded = trigger.getAttribute("aria-expanded") === "true";
    if (!expanded) trigger.click();
    return { found: true, expanded: trigger.getAttribute("aria-expanded") === "true" };
  })()`);
  assert(state.found, `${menuId} menu trigger is missing from the canonical menu bar`);
  await page.waitFor(
    `document.querySelector('[data-desktop-popup=${JSON.stringify(menuId)}]')?.hidden === false`,
    `${menuId} popup open`,
  );
  await sleep(200);
}

/** Clicks a menu item in an already-open popup. */
async function clickDesktopItem(page, itemId) {
  const clicked = await page.evaluate(`(() => {
    const item = document.querySelector('[data-desktop-item=${JSON.stringify(itemId)}]');
    if (!item) return { found: false };
    const disabled = item.hasAttribute("disabled");
    item.click();
    return { found: true, disabled };
  })()`);
  assert(clicked.found, `${itemId} is missing from the canonical menu bar`);
  assert(clicked.disabled === false, `${itemId} must be enabled`);
}

async function openViaMenu(page, menuId, itemId, selector, label) {
  await openDesktopMenu(page, menuId);
  await clickDesktopItem(page, itemId);
  await page.waitForSelector(selector, label, 20000);
  await page.waitFor(
    `(() => {
      const page = document.querySelector(${JSON.stringify(selector)});
      return Boolean(page?.querySelector(".cp-register-toolbar strong"));
    })()`,
    `${label} settled`,
  );
  await sleep(500);
}

async function openWindowTab(page, key) {
  await page.click(`[data-window-open="${key}"]`);
  await page.waitFor(
    `document.querySelector(".cp-workspace")?.dataset.activeMenu === ${JSON.stringify(key)}`,
    `${key} window active`,
  );
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
    contract: "cubi-workspace-canonical-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
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

    await scenario("01", "منوی Tools گزارش‌ها، ورود/خروجی و پشتیبان‌گیری را بدون دلیل غیرفعالی باز می‌کند", async () => {
      await openDesktopMenu(page, "tools");
      const state = await page.evaluate(pageState);
      const byId = new Map(state.tools.map((item) => [item.id, item]));
      const expected = {
        "tools.reports": ["reports", "Reports"],
        "tools.import-export": ["exchange", "Project CSV Import / Export…"],
        "tools.backup": ["backup", "Project Backup / Recovery…"],
      };
      for (const [id, [windowKey, label]] of Object.entries(expected)) {
        const item = byId.get(id);
        assert(item, `${id} is missing from the Tools menu`);
        assert(item.window === windowKey, `${id} opens ${item.window} instead of ${windowKey}`);
        assert(item.disabled === false && item.reason === null, `${id} must not claim to be unavailable`);
        assert(item.label === label, `${id} label ${item.label}`);
      }
      assert(state.menus.some((menu) => menu.id === "tools" && menu.expanded), "Tools popup is not expanded");
      await capture(page, "01-tools-menu");

      await clickDesktopItem(page, "tools.reports");
      await page.waitForSelector("[data-reports-page]", "reports window");
      await page.waitForSelector("[data-reports-page] .cp-register-toolbar strong", "reports heading");
      await sleep(700);
      const opened = await page.evaluate(pageState);
      assert(opened.activeMenu === "reports", `active window ${opened.activeMenu}`);
      assert(opened.pages.reports?.heading === "Project Reports", `reports heading ${opened.pages.reports?.heading}`);
      assert(opened.tabs.some((tab) => tab.key === "reports" && tab.selected && tab.label === "Reports"), `tabs ${JSON.stringify(opened.tabs)}`);
      await capture(page, "02-reports-window");
      return { tools: state.tools.length, heading: opened.pages.reports?.heading };
    });

    await scenario("02", "Tools / Project CSV Import / Export پنجرهٔ واقعی تبادل را باز می‌کند", async () => {
      await openViaMenu(page, "tools", "tools.import-export", "[data-exchange-page]", "exchange window");
      const state = await page.evaluate(pageState);
      assert(state.activeMenu === "exchange", `active window ${state.activeMenu}`);
      assert(state.pages.exchange?.heading === "Import / Export", `exchange heading ${state.pages.exchange?.heading}`);
      assert(state.pages.exchange.tabs.length >= 2, `exchange dataset tabs ${JSON.stringify(state.pages.exchange.tabs)}`);
      assert(state.tabs.some((tab) => tab.key === "exchange" && tab.selected), `tabs ${JSON.stringify(state.tabs)}`);
      await capture(page, "03-exchange-window");
      return { heading: state.pages.exchange.heading, tabs: state.pages.exchange.tabs };
    });

    await scenario("03", "Tools / Project Backup / Recovery پنجرهٔ پشتیبان‌گیری را باز می‌کند", async () => {
      await openViaMenu(page, "tools", "tools.backup", "[data-backup-page]", "backup window");
      const state = await page.evaluate(pageState);
      assert(state.activeMenu === "backup", `active window ${state.activeMenu}`);
      assert(state.pages.backup?.heading === "Backup / Recovery", `backup heading ${state.pages.backup?.heading}`);
      assert(state.pages.backup.tabs.length === 3, `backup tabs ${JSON.stringify(state.pages.backup.tabs)}`);
      assert(state.tabs.some((tab) => tab.key === "backup" && tab.selected), `tabs ${JSON.stringify(state.tabs)}`);
      await capture(page, "04-backup-window");
      return { heading: state.pages.backup.heading, tabs: state.pages.backup.tabs };
    });

    await scenario("04", "منوی Administration ماتریس دسترسی، دسته‌ها، دوره‌ها و بازیابی را به پنجره‌های واقعی می‌رساند", async () => {
      await openDesktopMenu(page, "administration");
      const menu = await page.evaluate(pageState);
      const byId = new Map(menu.administration.map((item) => [item.id, item]));
      assert(byId.size > 0, "Administration menu is empty for a project administrator");
      const expected = {
        "admin.permissions": "administration",
        "admin.categories": "administration",
        "admin.periods": "administration",
        "admin.recovery": "backup",
      };
      for (const [id, windowKey] of Object.entries(expected)) {
        const item = byId.get(id);
        assert(item, `${id} is missing from the Administration menu`);
        assert(item.window === windowKey, `${id} opens ${item.window} instead of ${windowKey}`);
        assert(item.disabled === false && item.reason === null, `${id} must not claim to be unavailable`);
      }
      // Entries with no shipped surface still explain themselves rather than
      // rendering an enabled item that would do nothing.
      for (const id of ["admin.users", "admin.security", "admin.currencies", "admin.audit"]) {
        const item = byId.get(id);
        assert(item, `${id} is missing`);
        assert(item.disabled === true && item.reason, `${id} must state why it is unavailable`);
      }
      await capture(page, "05-administration-menu");

      await clickDesktopItem(page, "admin.permissions");
      await page.waitForSelector("[data-administration-page] .cp-register-toolbar strong", "administration window");
      await sleep(700);
      const permissions = await page.evaluate(pageState);
      assert(permissions.activeMenu === "administration", `active window ${permissions.activeMenu}`);
      assert(permissions.pages.administration?.heading === "Administration", `admin heading ${permissions.pages.administration?.heading}`);
      assert(permissions.tabs.some((tab) => tab.key === "administration" && tab.selected), `tabs ${JSON.stringify(permissions.tabs)}`);
      await capture(page, "06-administration-window");

      await openDesktopMenu(page, "administration");
      await clickDesktopItem(page, "admin.categories");
      await page.waitForSelector("[data-administration-page] .cp-register-toolbar strong", "administration window again");
      await sleep(400);
      const categories = await page.evaluate(pageState);
      assert(categories.activeMenu === "administration" && categories.pages.administration, "categories must land on the administration window");
      assert(categories.tabs.filter((tab) => tab.key === "administration").length === 1, "administration must not be duplicated in the tab strip");

      await openDesktopMenu(page, "administration");
      await clickDesktopItem(page, "admin.periods");
      await page.waitForSelector("[data-administration-page] .cp-register-toolbar strong", "administration window once more");
      await sleep(400);

      await openViaMenu(page, "administration", "admin.recovery", "[data-backup-page]", "backup window from administration");
      const recovery = await page.evaluate(pageState);
      assert(recovery.activeMenu === "backup", `active window ${recovery.activeMenu}`);
      assert(recovery.pages.backup?.heading === "Backup / Recovery", `recovery heading ${recovery.pages.backup?.heading}`);
      assert(recovery.tabs.some((tab) => tab.key === "backup" && tab.selected), `tabs ${JSON.stringify(recovery.tabs)}`);
      await capture(page, "07-administration-recovery");
      return { administrationTabs: recovery.tabs.length, active: recovery.activeMenu };
    });

    await scenario("05", "تمام چهار پنجره هم‌زمان در نوار زبانه‌ها می‌مانند و با زبانه جابه‌جا می‌شوند", async () => {
      const state = await page.evaluate(pageState);
      const keys = state.tabs.map((tab) => tab.key);
      for (const key of ["reports", "exchange", "backup", "administration"]) {
        assert(keys.includes(key), `${key} is missing from the tab strip: ${JSON.stringify(keys)}`);
      }
      assert(keys.filter((key) => key === "backup").length === 1, `backup opened twice: ${JSON.stringify(keys)}`);

      await openWindowTab(page, "reports");
      let current = await page.evaluate(pageState);
      assert(current.pages.reports?.heading === "Project Reports", "reports surface was lost when switching windows");
      await openWindowTab(page, "exchange");
      current = await page.evaluate(pageState);
      assert(current.pages.exchange?.heading === "Import / Export", "exchange surface was lost when switching windows");
      await openWindowTab(page, "administration");
      current = await page.evaluate(pageState);
      assert(current.pages.administration?.heading === "Administration", "administration surface was lost when switching windows");
      await openWindowTab(page, "backup");
      current = await page.evaluate(pageState);
      assert(current.pages.backup?.heading === "Backup / Recovery", "backup surface was lost when switching windows");
      await capture(page, "08-four-windows");
      return { tabs: current.tabs.map((tab) => tab.key) };
    });

    await scenario("06", "بازبین منوی مدیریت را نمی‌بیند اما پنجره‌های پروژه را فقط خواندنی باز می‌کند", async () => {
      await loginAs(page, "Viewer");
      const shell = await page.evaluate(pageState);
      assert(!shell.menus.some((menu) => menu.id === "administration"), `viewer sees administration: ${JSON.stringify(shell.menus)}`);

      await openViaMenu(page, "tools", "tools.backup", "[data-backup-page]", "viewer backup window");
      const backup = await page.evaluate(pageState);
      assert(backup.activeMenu === "backup", `viewer active window ${backup.activeMenu}`);
      assert(backup.backupCreateDisabled === true, "viewer backup capture must be disabled");

      await openViaMenu(page, "tools", "tools.reports", "[data-reports-page]", "viewer reports window");
      const reports = await page.evaluate(pageState);
      assert(reports.activeMenu === "reports" && reports.pages.reports?.heading === "Project Reports", "viewer reports window did not open");
      await capture(page, "09-viewer-canonical");
      return { menus: shell.menus.map((menu) => menu.id), backupCreateDisabled: backup.backupCreateDisabled };
    });

    await scenario("07", "چیدمان فارسی راست‌به‌چپ در ۱۲۸۰×۷۲۰ از منوی کانونیک بدون نشان تجاری بیرونی", async () => {
      await loginAs(page, "Project administrator");
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await setLanguage(page, "fa");
      await openDesktopMenu(page, "tools");
      const tools = await page.evaluate(pageState);
      assert(tools.direction === "rtl", `direction ${tools.direction}`);
      const backupItem = tools.tools.find((item) => item.id === "tools.backup");
      assert(backupItem?.label === "پشتیبان‌گیری / بازیابی پروژه…", `Persian backup label ${backupItem?.label}`);
      await capture(page, "10-persian-tools");

      await clickDesktopItem(page, "tools.import-export");
      await page.waitForSelector("[data-exchange-page] .cp-register-toolbar strong", "Persian exchange window");
      await sleep(700);
      const exchange = await page.evaluate(pageState);
      assert(exchange.pages.exchange?.heading === "ورود / خروجی", `Persian exchange heading ${exchange.pages.exchange?.heading}`);

      await openDesktopMenu(page, "administration");
      const adminState = await page.evaluate(pageState);
      const permissions = adminState.administration.find((item) => item.id === "admin.permissions");
      assert(permissions?.label === "ماتریس دسترسی…", `Persian permission label ${permissions?.label}`);
      await clickDesktopItem(page, "admin.recovery");
      await page.waitForSelector("[data-backup-page] .cp-register-toolbar strong", "Persian backup window");
      await sleep(700);
      const backup = await page.evaluate(pageState);
      assert(backup.direction === "rtl", `direction after restore ${backup.direction}`);
      assert(backup.pages.backup?.heading === "پشتیبان‌گیری / بازیابی", `Persian backup heading ${backup.pages.backup?.heading}`);
      assert(!/oracle|primavera|\bp6\b/i.test(backup.workspaceText), "canonical menu bar leaks third-party branding");
      await capture(page, "11-persian-workspace");
      return { direction: backup.direction, heading: backup.pages.backup?.heading };
    });

    assert(exceptions.length === 0, `browser exceptions: ${JSON.stringify(exceptions.slice(0, 3))}`);
    assert(apiFailures.length === 0, `API 5xx responses: ${JSON.stringify(apiFailures.slice(0, 3))}`);

    report.status = "pass";
    report.scenarioCount = scenarios.length;
  } catch (error) {
    report.status = "fail";
    report.error = String(error && error.stack ? error.stack : error);
    throw error;
  } finally {
    writeFileSync(join(evidenceDir, "workspace-canonical-v26.json"), `${JSON.stringify(report, null, 2)}\n`);
    copyFileSync(join(evidenceDir, "workspace-canonical-v26.json"), join(outDir, "workspace-canonical-v26.json"));
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
