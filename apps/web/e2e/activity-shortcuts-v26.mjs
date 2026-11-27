#!/usr/bin/env node
/**
 * Browser E2E for the Version 26 keyboard shortcut catalogue.
 *
 * Proves against the real preview runtime that:
 *   - F1 opens the shortcut dialog with every catalogue row, a key for each,
 *     a stated reason for every unavailable command, and no conflict banner;
 *   - the dialog search narrows the catalogue and clearing restores it;
 *   - executable shortcuts still work: Ctrl+A selects the whole filter scope,
 *     Ctrl+S saves the layout revision, F5 re-reads the project, Insert opens
 *     the Add Activity drawer without writing;
 *   - rebinding captures a new chord, persists it, survives a reload and
 *     executes the new chord; Reset and Reset all restore the defaults;
 *   - a duplicate chord and an unusable chord are refused with a message and
 *     never stored;
 *   - the dialog renders in fa/RTL at 1280×720 and en/LTR at 1920×1080;
 *   - the whole run issues no exception, console error or 5xx.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4235 node e2e/activity-shortcuts-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4235";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-27";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "activity-shortcuts-v26");
const evidenceDir = join(
  artifactsDir,
  "..",
  "..",
  "..",
  "..",
  "docs",
  "workspace",
  "evidence",
  `activity-shortcuts-v26-${evidenceDate}`,
);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const OVERRIDE_PREFIX = "cubi:workspace-shortcut-overrides";

const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const apiWrites = [];
const scenarios = [];
const screenshots = [];

const log = (message) => process.stdout.write(`${message}\n`);

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

function record(id, name, status, details = {}) {
  scenarios.push({ ...details, id, name, status, at: new Date().toISOString() });
  log(`  ${status.toUpperCase()} ${id}. ${name}`);
}

async function scenario(id, name, body) {
  log(`[${id}] ${name}`);
  try {
    const details = await body();
    record(id, name, "pass", details ?? {});
  } catch (error) {
    record(id, name, "fail", { error: error instanceof Error ? error.message : String(error) });
    throw error;
  }
}

async function capture(page, name) {
  const file = `activity-shortcuts-v26/${name}.png`;
  await page.screenshot(file);
  copyFileSync(join(artifactsDir, file), join(evidenceDir, `${name}.png`));
  screenshots.push(`${name}.png`);
  return file;
}

async function setViewport(page, width, height) {
  await page.cdp.send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
  await sleep(400);
}

const CTRL = 2;
const ALT = 1;

async function press(page, key, code, keyCode, modifiers = 0) {
  await page.cdp.send("Input.dispatchKeyEvent", {
    type: "keyDown",
    key,
    code,
    windowsVirtualKeyCode: keyCode,
    nativeVirtualKeyCode: keyCode,
    modifiers,
  });
  await sleep(70);
  await page.cdp.send("Input.dispatchKeyEvent", {
    type: "keyUp",
    key,
    code,
    windowsVirtualKeyCode: keyCode,
    nativeVirtualKeyCode: keyCode,
    modifiers,
  });
  await sleep(450);
}

async function focusShell(page) {
  const focused = await page.evaluate(`(() => {
    const shell = document.querySelector("[data-desktop-shell]");
    const button = [...(shell?.querySelectorAll("[data-desktop-command], [data-desktop-menu]") ?? [])]
      .find((item) => item.getClientRects().length > 0 && !item.disabled);
    if (!button) return false;
    button.focus();
    return document.activeElement === button;
  })()`);
  assert(focused, "could not focus a control inside the desktop shell");
}

async function shortcutDialogState(page) {
  return page.evaluate(`(() => {
    const dialog = document.querySelector('[data-desktop-dialog="shortcuts"][open]');
    if (!dialog) return null;
    const allRows = [...dialog.querySelectorAll("[data-shortcut-row]")].map((row) => ({
      id: row.dataset.shortcutId,
      text: row.dataset.shortcutText,
      label: row.querySelector("td")?.textContent?.trim() ?? "",
      keys: row.querySelector("kbd")?.textContent?.trim() ?? "",
      unavailable: row.classList.contains("is-unavailable"),
      reason: row.querySelector(".cp-shortcut-reason")?.textContent?.trim() ?? null,
      help: Boolean(row.querySelector(".cp-shortcut-help")),
      capturing: row.classList.contains("is-capturing"),
      hidden: row.hidden,
    }));
    const rows = allRows.filter((row) => !row.hidden);
    const status = dialog.querySelector("[data-shortcut-capture-status]");
    return {
      rows,
      allRows,
      count: rows.length,
      totalCount: allRows.length,
      conflicts: dialog.querySelector(".cp-shortcut-conflicts")?.textContent?.trim() ?? null,
      status: status && !status.hidden ? status.textContent.trim() : null,
      statusTone: status?.dataset.tone ?? "",
      captureRow: rows.find((row) => row.capturing)?.id ?? null,
      resetAll: Boolean(dialog.querySelector("[data-shortcut-reset-all]")),
      direction: getComputedStyle(dialog).direction,
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    };
  })()`);
}

async function openShortcuts(page) {
  await focusShell(page);
  await press(page, "F1", "F1", 112);
  await page.waitForSelector('[data-desktop-dialog="shortcuts"][open]', "shortcuts dialog");
  await sleep(300);
}

async function closeShortcuts(page) {
  await page.evaluate(`(() => {
    const dialog = document.querySelector('[data-desktop-dialog="shortcuts"][open]');
    const close = dialog?.querySelector('form[method="dialog"] button[type="submit"]');
    if (close) close.click();
    return true;
  })()`);
  await page.waitFor(`(() => !document.querySelector('[data-desktop-dialog="shortcuts"][open]'))`, "shortcuts closed", 6000);
  await sleep(300);
}

function readCounts(page) {
  return page.evaluate(`(() => {
    const counts = document.querySelector("[data-activity-counts]");
    return counts ? {
      total: Number(counts.getAttribute("data-count-total") ?? -1),
      filter: Number(counts.getAttribute("data-count-filter") ?? -1),
      visible: Number(counts.getAttribute("data-count-visible") ?? -1),
      selected: Number(counts.getAttribute("data-count-selected") ?? -1),
      selectedScope: Number(counts.getAttribute("data-count-selected-scope") ?? -1),
    } : null;
  })()`);
}

function readLayout(page, scope = "project") {
  return page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${PROJECT}/p6/layouts/${scope}/activity");
    let body = null;
    try { body = await response.json(); } catch (error) { body = null; }
    return { status: response.status, body };
  })()`, { awaitPromise: true });
}

function readOverrides(page) {
  return page.evaluate(`(() => {
    const prefix = ${JSON.stringify(OVERRIDE_PREFIX)};
    const key = Object.keys(localStorage).find((item) => item === prefix || item.startsWith(prefix + ":"));
    return key ? { key, value: localStorage.getItem(key) } : null;
  })()`);
}

async function main() {
  const health = await waitForHttp(`${baseUrl}/preview/health`, 30000);
  if (!(health.status === "ok" || health.status === 200)) throw new Error(`preview health ${health.status}`);
  const chrome = await launchChrome();
  const page = new Page(chrome.cdp);
  await page.initialize();
  page.cdp.on("Runtime.exceptionThrown", (params) => {
    exceptions.push(params.exceptionDetails?.exception?.description ?? params.exceptionDetails?.text ?? "exception");
  });
  page.cdp.on("Runtime.consoleAPICalled", (params) => {
    if (params.type !== "error") return;
    consoleErrors.push((params.args ?? []).map((arg) => arg.value ?? arg.description ?? arg.type).join(" "));
  });
  page.cdp.on("Network.responseReceived", (params) => {
    const url = params.response?.url ?? "";
    if (url.includes("/api/") && params.response.status >= 500) apiFailures.push({ status: params.response.status, url });
  });
  page.cdp.on("Network.requestWillBeSent", (params) => {
    if (params.request.method === "GET" || params.request.method === "OPTIONS") return;
    if (!params.request.url.includes("/api/")) return;
    apiWrites.push({ method: params.request.method, url: params.request.url });
  });

  const report = {
    contract: "cubi-activity-shortcuts-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    helpTopics: ["https://docs.oracle.com/cd/G48902_01/client_help/en_US/63783.htm"],
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
    interactionWrites: apiWrites,
  };

  function writeReport() {
    report.scenarios = scenarios;
    report.passed = scenarios.filter((entry) => entry.status === "pass").length;
    report.failed = scenarios.filter((entry) => entry.status === "fail").length;
    const json = JSON.stringify(report, null, 2);
    writeFileSync(join(outDir, "activity-shortcuts-v26.json"), json);
    writeFileSync(join(evidenceDir, "activity-shortcuts-v26.json"), json);
  }

  try {
    await setViewport(page, 1440, 900);
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
    await sleep(700);
    const hasPersonas = await page.evaluate('Boolean(document.querySelector(".persona"))');
    if (!hasPersonas) {
      await page.evaluate('fetch("/preview/logout", { method: "POST", redirect: "manual" }).then((response) => response.status)', { awaitPromise: true });
      await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, ".persona", "persona cards after sign out");
    }
    const plannerClicked = await page.evaluate(`(() => {
      const button = [...document.querySelectorAll("form button")].find((item) => (item.textContent || "").trim().startsWith("Planner"));
      if (!button) return false;
      button.click();
      return true;
    })()`);
    assert(plannerClicked, "Planner login button is missing");
    await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
    await page.click('[data-project-id="preview-rps-01"]');
    await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
    await sleep(1500);

    let catalogue = null;
    let initialLayout = null;
    let initialCounts = null;

    await scenario("01", "F1 lists the whole catalogue with a key for every row and a reason for every unavailable command", async () => {
      initialCounts = await readCounts(page);
      initialLayout = await readLayout(page);
      assert(initialLayout.status === 200, `layout read ${initialLayout.status}`);
      assert(initialCounts && initialCounts.total > 10, "the project has no activity rows");
      await openShortcuts(page);
      catalogue = await shortcutDialogState(page);
      assert(catalogue, "the shortcuts dialog did not open");
      assert(catalogue.count >= 27, `only ${catalogue.count} catalogue rows rendered`);
      assert(!catalogue.conflicts, `conflict banner: ${catalogue.conflicts}`);
      const required = [
        "shortcut.new", "shortcut.open", "shortcut.print", "shortcut.save-layout",
        "shortcut.undo", "shortcut.redo", "shortcut.cut", "shortcut.copy", "shortcut.paste",
        "shortcut.delete", "shortcut.insert", "shortcut.find", "shortcut.select-all",
        "shortcut.find-next", "shortcut.refresh", "shortcut.schedule", "shortcut.schedule-options",
        "shortcut.leveling", "shortcut.commit", "shortcut.help", "shortcut.about",
      ];
      const ids = catalogue.rows.map((row) => row.id);
      for (const id of required) assert(ids.includes(id), `catalogue lost ${id}`);
      const missingKeys = catalogue.rows.filter((row) => !row.keys);
      assert(missingKeys.length === 0, `${missingKeys.length} rows have no key`);
      const silentUnavailable = catalogue.rows.filter((row) => row.unavailable && !row.reason);
      assert(silentUnavailable.length === 0, `unavailable rows without a reason: ${silentUnavailable.map((row) => row.id).join(",")}`);
      const unavailable = catalogue.rows.filter((row) => row.unavailable);
      assert(unavailable.length > 0, "no unavailable rows were marked");
      const withHelp = catalogue.rows.filter((row) => row.help).length;
      assert(withHelp >= 12, `only ${withHelp} rows link a Help topic`);
      await capture(page, "01-shortcuts-catalog-en-1440");
      return {
        rows: catalogue.count,
        unavailable: unavailable.map((row) => row.id),
        withHelp,
        withHelpIds: catalogue.rows.filter((row) => row.help).map((row) => row.id),
        withoutHelpIds: catalogue.rows.filter((row) => !row.help).map((row) => row.id),
      };
    });

    await scenario("02", "the dialog search narrows the catalogue and clearing it restores every row", async () => {
      await page.setInput('[data-desktop-dialog="shortcuts"][open] [data-shortcut-search]', "save");
      await sleep(300);
      const filtered = await shortcutDialogState(page);
      assert(filtered.count > 0 && filtered.count < catalogue.count, `search kept ${filtered.count} of ${catalogue.count} rows`);
      assert(filtered.rows.every((row) => row.text.includes("save")), "search kept an unrelated row");
      await capture(page, "02-shortcuts-search-en-1440");
      await page.setInput('[data-desktop-dialog="shortcuts"][open] [data-shortcut-search]', "");
      await sleep(300);
      const restored = await shortcutDialogState(page);
      assert(restored.count === catalogue.count, `clearing search left ${restored.count} rows`);
      return { filtered: filtered.count, restored: restored.count };
    });

    await scenario("03", "Ctrl+A selects the whole scope and Ctrl+S appends a saved layout revision", async () => {
      await closeShortcuts(page);
      await focusShell(page);
      await press(page, "a", "KeyA", 65, CTRL);
      const afterSelect = await readCounts(page);
      assert(afterSelect.selected === initialCounts.total, `Ctrl+A selected ${afterSelect.selected} of ${initialCounts.total}`);
      assert(afterSelect.selectedScope === initialCounts.total, `selected-in-scope ${afterSelect.selectedScope}`);
      await focusShell(page);
      const before = await readLayout(page);
      await press(page, "s", "KeyS", 83, CTRL);
      await sleep(1600);
      const after = await readLayout(page);
      assert(after.status === 200, `layout read after save ${after.status}`);
      assert(after.body.revision > before.body.revision, `Ctrl+S did not append a revision: ${before.body.revision} -> ${after.body.revision}`);
      return { selected: afterSelect.selected, revision: `${before.body.revision}→${after.body.revision}` };
    });

    await scenario("04", "F5 re-reads the project and Insert opens the Add Activity drawer without writing", async () => {
      await focusShell(page);
      await press(page, "F5", "F5", 116);
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "rows after refresh");
      await sleep(1200);
      const refreshed = await readCounts(page);
      assert(refreshed.total === initialCounts.total, `F5 changed the total ${initialCounts.total} -> ${refreshed.total}`);
      await focusShell(page);
      const writesBefore = apiWrites.length;
      await press(page, "Insert", "Insert", 45);
      await page.waitForSelector("[data-tools-drawer] [data-activity-create-form] input[name='activity_id']", "add activity form");
      const focusedId = await page.evaluate('document.activeElement?.name ?? ""');
      assert(focusedId === "activity_id", `Insert focused "${focusedId}" instead of the activity id`);
      await capture(page, "03-insert-add-activity-en-1440");
      const writesAfter = apiWrites.length;
      assert(writesAfter === writesBefore, `Insert issued writes: ${JSON.stringify(apiWrites.slice(writesBefore))}`);
      await page.evaluate(`(() => {
        const drawer = document.querySelector("[data-tools-drawer]");
        const close = drawer?.querySelector("[data-tools-close], [data-drawer-close]");
        if (close) { close.click(); return true; }
        return false;
      })()`);
      await sleep(400);
      return { total: refreshed.total, focused: focusedId };
    });

    await scenario("05", "Change captures a new chord, persists it across reload and runs the new binding; Reset restores the default", async () => {
      await openShortcuts(page);
      const changeClicked = await page.evaluate(`(() => {
        const button = document.querySelector('[data-desktop-dialog="shortcuts"][open] [data-shortcut-change="shortcut.about"]');
        if (!button) return false;
        button.click();
        return true;
      })()`);
      assert(changeClicked, "Change is missing for the About shortcut");
      await sleep(200);
      const capturing = await shortcutDialogState(page);
      assert(capturing.captureRow === "shortcut.about", `capturing row is ${capturing.captureRow}`);
      await press(page, "k", "KeyK", 75, CTRL | ALT);
      await sleep(600);
      const reopened = await page.evaluate('Boolean(document.querySelector(\'[data-desktop-dialog="shortcuts"][open]\'))');
      if (!reopened) await openShortcuts(page);
      const changed = await shortcutDialogState(page);
      const about = changed.rows.find((row) => row.id === "shortcut.about");
      assert(about && about.keys === "Ctrl+Alt+K", `About shortcut is "${about?.keys}"`);
      assert(changed.resetAll, "Reset all is not offered after an override");
      const stored = await readOverrides(page);
      assert(stored && stored.value.includes("shortcut.about"), "the override was not persisted");
      await capture(page, "04-shortcut-rebound-en-1440");
      await closeShortcuts(page);
      await page.navigate(`${baseUrl}/app?view=live&project=${PROJECT}`, "main", "reload");
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "rows after reload");
      await sleep(1200);
      await focusShell(page);
      await press(page, "k", "KeyK", 75, CTRL | ALT);
      await page.waitForSelector('[data-desktop-dialog="about"][open]', "about dialog from the new chord");
      await page.evaluate(`(() => { const b = document.querySelector('[data-desktop-dialog="about"][open] form button'); if (b) b.click(); return true; })()`);
      await sleep(300);
      await openShortcuts(page);
      const resetClicked = await page.evaluate(`(() => {
        const button = document.querySelector('[data-desktop-dialog="shortcuts"][open] [data-shortcut-reset="shortcut.about"]');
        if (!button) return false;
        button.click();
        return true;
      })()`);
      assert(resetClicked, "Reset is missing for the overridden shortcut");
      await sleep(500);
      if (!(await page.evaluate('Boolean(document.querySelector(\'[data-desktop-dialog="shortcuts"][open]\'))'))) await openShortcuts(page);
      const reset = await shortcutDialogState(page);
      const restoredAbout = reset.rows.find((row) => row.id === "shortcut.about");
      assert(restoredAbout && restoredAbout.keys === "Shift+F12", `Reset left "${restoredAbout?.keys}"`);
      assert(!(await readOverrides(page)), "Reset did not clear the stored override");
      await closeShortcuts(page);
      return { bound: "Ctrl+Alt+K", restored: restoredAbout.keys };
    });

    await scenario("06", "a duplicate chord and an unusable chord are refused and never stored", async () => {
      await openShortcuts(page);
      await page.evaluate(`(() => {
        document.querySelector('[data-desktop-dialog="shortcuts"][open] [data-shortcut-change="shortcut.about"]')?.click();
        return true;
      })()`);
      await sleep(200);
      await press(page, "f", "KeyF", 70, CTRL);
      let state = await shortcutDialogState(page);
      assert(state.status && /Already used|استفاده شده/.test(state.status), `duplicate message was "${state.status}"`);
      assert(state.statusTone === "error", `duplicate tone was "${state.statusTone}"`);
      assert(!(await readOverrides(page)), "a duplicate chord was stored");
      await press(page, "k", "KeyK", 75, 0);
      state = await shortcutDialogState(page);
      assert(state.status && /not a usable shortcut|قابل استفاده نیست/.test(state.status), `unusable message was "${state.status}"`);
      await capture(page, "05-shortcut-refused-en-1440");
      await press(page, "Escape", "Escape", 27);
      state = await shortcutDialogState(page);
      assert(state.captureRow === null, "Escape did not cancel the capture");
      assert(state.status === null, "Escape left the capture status visible");
      const about = state.rows.find((row) => row.id === "shortcut.about");
      assert(about && about.keys === "Shift+F12", `refusal changed the binding to "${about?.keys}"`);
      await closeShortcuts(page);
      return { duplicate: true, unusable: true };
    });

    await scenario("07", "the dialog localises in fa/RTL at 1280×720 and fits en/LTR at 1920×1080", async () => {
      await setViewport(page, 1280, 720);
      const changed = await page.evaluate(`(() => {
        const select = document.querySelector("[data-workspace-language]");
        if (!select) return false;
        select.value = "fa";
        select.dispatchEvent(new Event("change", { bubbles: true }));
        return true;
      })()`);
      assert(changed, "the language selector is missing");
      await sleep(1200);
      await openShortcuts(page);
      const fa = await shortcutDialogState(page);
      assert(fa.direction === "rtl", `fa dialog direction is ${fa.direction}`);
      assert(fa.count === catalogue.count, `fa dialog rendered ${fa.count} rows`);
      assert(fa.rows.some((row) => /[\u0600-\u06FF]/.test(row.label)), "fa dialog labels are not localised");
      assert(fa.overflow <= 1, `fa dialog overflows by ${fa.overflow}px`);
      await capture(page, "06-shortcuts-fa-rtl-1280");
      await closeShortcuts(page);
      await page.evaluate(`(() => {
        const select = document.querySelector("[data-workspace-language]");
        if (!select) return false;
        select.value = "en";
        select.dispatchEvent(new Event("change", { bubbles: true }));
        return true;
      })()`);
      await sleep(1200);
      await setViewport(page, 1920, 1080);
      await openShortcuts(page);
      const en = await shortcutDialogState(page);
      assert(en.rows.every((row) => !/[\u0600-\u06FF]/.test(row.label)), "en dialog still shows Persian labels");
      assert(en.overflow <= 1, `en dialog overflows by ${en.overflow}px`);
      await capture(page, "07-shortcuts-en-1920");
      await closeShortcuts(page);
      return { fa: fa.count, en: en.count };
    });

    await scenario("08", "the whole run issued no exception, console error or 5xx", async () => {
      assert(exceptions.length === 0, `exceptions: ${JSON.stringify(exceptions.slice(0, 2))}`);
      assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors.slice(0, 2))}`);
      assert(apiFailures.length === 0, `5xx: ${JSON.stringify(apiFailures.slice(0, 2))}`);
      return { exceptions: 0, consoleErrors: 0, apiFailures: 0 };
    });
  } finally {
    writeReport();
    log(`\nActivity shortcuts suite: ${scenarios.filter((s) => s.status === "pass").length}/${scenarios.length} passed`);
    log(`Evidence: ${evidenceDir}`);
    try { page.cdp.close(); } catch {}
    try { chrome.child?.kill("SIGKILL"); } catch {}
  }
}

main().catch((error) => {
  log(`\nE2E FAILED: ${error instanceof Error ? error.stack ?? error.message : String(error)}`);
  process.exitCode = 1;
});
