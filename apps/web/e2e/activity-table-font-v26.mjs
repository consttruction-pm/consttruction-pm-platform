#!/usr/bin/env node
/**
 * Version 26 Table Font and Row acceptance (ACT-005).
 *
 * Proves in the real preview that font family, size, text/background colours,
 * row-height mode and fixed height reach the rendered grid, are published with
 * the saved layout, survive a full reload, and can be reset to the shipped
 * defaults through the dialog's own Reset action.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4198 \
 *   CUBI_TESTED_CODE_SHA=<code commit> node e2e/activity-table-font-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4198";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "activity-table-font-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `activity-table-font-v26-${evidenceDate}`);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

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
  scenarios.push({ id, name, status, at: new Date().toISOString(), ...details });
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
  const file = `activity-table-font-v26/${name}.png`;
  await page.screenshot(file);
  copyFileSync(join(artifactsDir, file), join(evidenceDir, `${name}.png`));
  screenshots.push(`${name}.png`);
  return file;
}

async function setViewport(page, width, height) {
  await page.cdp.send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
  await sleep(400);
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

const dialogSelector = "dialog[data-desktop-dialog=font-row]";

async function openFontRow(page) {
  const clicked = await page.evaluate(`(() => {
    const element = [...document.querySelectorAll('[data-desktop-command="dialog.font-row"]')]
      .find((item) => item.getClientRects().length > 0 && !item.disabled);
    if (!element) return false;
    element.click();
    return true;
  })()`);
  assert(clicked, "Table Font and Row command is missing");
  await page.waitForSelector(`${dialogSelector}[open]`, "table font dialog", 8000);
  await sleep(250);
}

async function setControl(page, selector, value, kind = "select") {
  const changed = await page.evaluate(`(() => {
    const control = document.querySelector('${dialogSelector} ' + ${JSON.stringify(selector)});
    if (!control) return false;
    ${kind === "check"
      ? "control.checked = " + JSON.stringify(Boolean(value)) + ";"
      : "control.value = " + JSON.stringify(String(value)) + "; if (control.value !== " + JSON.stringify(String(value)) + ") return false;"}
    control.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  assert(changed, `font control ${selector} did not accept ${value}`);
  await sleep(120);
}

async function submit(page, selector = "[data-dialog-ok]") {
  const clicked = await page.evaluate(`(() => {
    const button = document.querySelector('${dialogSelector} ' + ${JSON.stringify(selector)});
    if (!button || button.disabled) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `font dialog control ${selector} is missing`);
  await page.waitFor(`!document.querySelector('${dialogSelector}')?.open`, "font dialog closed", 8000);
  await sleep(900);
}

async function tableStyle(page) {
  return page.evaluate(`(() => {
    const root = getComputedStyle(document.documentElement);
    const cell = document.querySelector("#cp-activity-grid tbody tr[data-activity-id] td");
    const row = document.querySelector("#cp-activity-grid tbody tr[data-activity-id]");
    const band = document.querySelector("#cp-activity-grid tbody tr.cp-p6-wbs-band");
    const cellStyle = cell ? getComputedStyle(cell) : null;
    return {
      rootFont: root.getPropertyValue("--cp-p6-font-family").trim(),
      rootSize: root.getPropertyValue("--cp-p6-font-size").trim(),
      rootRow: root.getPropertyValue("--cp-p6-row-height").trim(),
      rootText: root.getPropertyValue("--cp-p6-text-color").trim(),
      rootBackground: root.getPropertyValue("--cp-p6-bg-color").trim(),
      rowMode: document.documentElement.dataset.tableRowMode ?? "",
      showIcons: document.documentElement.dataset.showIcons ?? "",
      cellFontSize: cellStyle?.fontSize ?? "",
      cellFontFamily: cellStyle?.fontFamily ?? "",
      cellColor: cellStyle?.color ?? "",
      rowHeight: row ? Math.round(row.getBoundingClientRect().height) : 0,
      bandCount: document.querySelectorAll("#cp-activity-grid tbody tr.cp-p6-wbs-band").length,
      bandFontSize: band ? getComputedStyle(band).fontSize : "",
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      dir: document.documentElement.dir || "ltr",
    };
  })()`);
}

function readLayout(page, projectId, scope) {
  return page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${projectId}/p6/layouts/${scope}/activity");
    let body = null;
    try { body = await response.json(); } catch (error) { body = null; }
    return { status: response.status, body };
  })()`, { awaitPromise: true });
}

async function waitForPresentation(page, predicate) {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    await sleep(200);
    for (const scope of ["project", "user"]) {
      const saved = await readLayout(page, "preview-rps-01", scope);
      if (saved.status !== 200 || !saved.body?.metadata?.presentation?.table) continue;
      if (predicate(saved.body.metadata.presentation.table)) return saved;
    }
  }
  return null;
}

async function dialogState(page) {
  return page.evaluate(`(() => {
    const dialog = document.querySelector("${dialogSelector}");
    return {
      open: Boolean(dialog?.open),
      title: dialog.querySelector("h2")?.textContent?.trim() ?? "",
      values: {
        fontFamily: dialog.querySelector('select[name="fontFamily"]')?.value ?? "",
        fontSize: dialog.querySelector('select[name="fontSize"]')?.value ?? "",
        textColor: dialog.querySelector('input[name="textColor"]')?.value ?? "",
        backgroundColor: dialog.querySelector('input[name="backgroundColor"]')?.value ?? "",
        rowHeightMode: dialog.querySelector('input[name="rowHeightMode"]:checked')?.value ?? "",
        rowHeight: dialog.querySelector('input[name="rowHeight"]')?.value ?? "",
        showIcons: dialog.querySelector('input[name="showIcons"]')?.checked ?? null,
      },
      reset: dialog.querySelector("[data-dialog-reset]")?.textContent?.trim() ?? "",
    };
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

  const report = {
    contract: "cubi-activity-table-font-v26.v1",
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

  function writeReport() {
    report.scenarios = scenarios;
    report.passed = scenarios.filter((entry) => entry.status === "pass").length;
    report.failed = scenarios.filter((entry) => entry.status === "fail").length;
    const json = JSON.stringify(report, null, 2);
    writeFileSync(join(outDir, "activity-table-font-v26.json"), json);
    writeFileSync(join(evidenceDir, "activity-table-font-v26.json"), json);
  }

  try {
    await setViewport(page, 1366, 768);
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
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

    await scenario("01", "the dialog writes font, colours and a fixed row height to the table", async () => {
      const before = await tableStyle(page);
      assert(before.rootSize === "11px", `default font size is ${before.rootSize}`);
      assert(before.rootRow === "18px", `default row height is ${before.rootRow}`);
      await openFontRow(page);
      const dialog = await dialogState(page);
      assert(dialog.values.fontFamily === "tahoma", `default family is ${dialog.values.fontFamily}`);
      assert(dialog.values.rowHeightMode === "fixed", `default row mode is ${dialog.values.rowHeightMode}`);
      assert(dialog.reset === "Reset to defaults", `reset action is missing: ${dialog.reset}`);
      await setControl(page, 'select[name="fontFamily"]', "cairo");
      await setControl(page, 'select[name="fontSize"]', "14");
      await setControl(page, 'input[name="textColor"]', "#102030");
      await setControl(page, 'input[name="backgroundColor"]', "#fdf6e3");
      await setControl(page, 'input[name="rowHeightMode"][value="fixed"]', true, "check");
      await setControl(page, 'input[name="rowHeight"]', "26");
      await setControl(page, 'input[name="showIcons"]', false, "check");
      await submit(page);
      const after = await tableStyle(page);
      assert(after.rootSize === "14px", `applied font size is ${after.rootSize}`);
      assert(/Cairo/i.test(after.rootFont), `applied font family is ${after.rootFont}`);
      assert(after.rootText === "#102030", `applied text colour is ${after.rootText}`);
      assert(after.rootBackground === "#fdf6e3", `applied background is ${after.rootBackground}`);
      assert(after.rowMode === "fixed", `applied row mode is ${after.rowMode}`);
      assert(after.showIcons === "false", `icons flag is ${after.showIcons}`);
      assert(after.rootRow === "26px", `applied row height is ${after.rootRow}`);
      assert(after.cellFontSize === "14px", `cell font size is ${after.cellFontSize}`);
      assert(after.cellColor === "rgb(16, 32, 48)", `cell colour is ${after.cellColor}`);
      assert(after.rowHeight >= 26 && after.rowHeight <= 30, `rendered row height is ${after.rowHeight}`);
      const saved = await waitForPresentation(page, (table) => table.fontFamily === "cairo" && table.fontSize === 14);
      assert(saved, "the layout did not publish the new table presentation");
      await capture(page, "01-table-font-cairo-26px-en-1366");
      return { revision: saved.body?.revision, table: saved.body?.metadata?.presentation?.table };
    });

    await scenario("02", "the saved table presentation survives a full reload", async () => {
      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "reload after font save");
      await sleep(1200);
      const state = await tableStyle(page);
      assert(state.rootSize === "14px", `reload font size is ${state.rootSize}`);
      assert(/Cairo/i.test(state.rootFont), `reload font family is ${state.rootFont}`);
      assert(state.rootText === "#102030", `reload text colour is ${state.rootText}`);
      assert(state.rootBackground === "#fdf6e3", `reload background is ${state.rootBackground}`);
      assert(state.rootRow === "26px", `reload row height is ${state.rootRow}`);
      assert(state.rowHeight >= 26 && state.rowHeight <= 30, `reload rendered row height is ${state.rowHeight}`);
      await capture(page, "02-table-font-after-reload-en-1366");
      return { rowHeight: state.rowHeight, fontSize: state.rootSize };
    });

    await scenario("03", "Reset to defaults restores the shipped table and persists", async () => {
      await openFontRow(page);
      await submit(page, "[data-dialog-reset]");
      const reset = await tableStyle(page);
      assert(reset.rootSize === "11px", `reset font size is ${reset.rootSize}`);
      assert(reset.rootFont.includes("Tahoma"), `reset font family is ${reset.rootFont}`);
      assert(reset.rootText === "#000000", `reset text colour is ${reset.rootText}`);
      assert(reset.rootBackground === "#ffffff", `reset background is ${reset.rootBackground}`);
      assert(reset.rootRow === "18px", `reset row height is ${reset.rootRow}`);
      assert(reset.rowMode === "fixed", `reset row mode is ${reset.rowMode}`);
      assert(reset.showIcons === "true", `reset icons flag is ${reset.showIcons}`);
      const saved = await waitForPresentation(page, (table) => table.fontFamily === "tahoma" && table.fontSize === 11 && table.rowHeight === 18);
      assert(saved, "the reset was not published with the layout");
      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "reload after reset");
      await sleep(1200);
      const reloaded = await tableStyle(page);
      assert(reloaded.rootSize === "11px" && reloaded.rootRow === "18px", `reset did not survive reload: ${reloaded.rootSize}/${reloaded.rootRow}`);
      await capture(page, "03-table-font-reset-en-1366");
      return { revision: saved.body?.revision, rowHeight: reloaded.rowHeight };
    });

    await scenario("04", "the dialog and defaults render in a Persian RTL cell", async () => {
      await setViewport(page, 1280, 720);
      await setLanguage(page, "fa");
      await openFontRow(page);
      const dialog = await page.evaluate(`(() => {
        const element = document.querySelector("${dialogSelector}");
        return {
          title: element.querySelector("h2")?.textContent?.trim() ?? "",
          reset: element.querySelector("[data-dialog-reset]")?.textContent?.trim() ?? "",
          overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        };
      })()`);
      assert(/قلم/.test(dialog.title), `Persian title is missing: ${dialog.title}`);
      assert(/بازنشانی/.test(dialog.reset), `Persian reset label is missing: ${dialog.reset}`);
      assert(dialog.overflow <= 1, `the RTL dialog overflows by ${dialog.overflow}px`);
      await capture(page, "04-table-font-fa-rtl-1280");
      await page.evaluate(`(() => {
        const dialog = document.querySelector("${dialogSelector}");
        dialog.querySelector("[data-dialog-cancel]")?.click();
      })()`);
      await sleep(300);
      const state = await tableStyle(page);
      assert(state.dir === "rtl", "the table lost RTL");
      assert(state.overflow <= 1, `the RTL table overflows by ${state.overflow}px`);
      return dialog;
    });

    await scenario("05", "the table presentation fits a 1920x1080 cell", async () => {
      await setViewport(page, 1920, 1080);
      await sleep(500);
      const state = await tableStyle(page);
      assert(state.overflow <= 1, `the 1920 cell overflows by ${state.overflow}px`);
      assert(state.rootSize === "11px", `the 1920 cell font size is ${state.rootSize}`);
      await capture(page, "05-table-font-en-1920");
      return { rows: state.bandCount, overflow: state.overflow };
    });

    log(`\nAll ${scenarios.length} table font scenarios passed`);
  } catch (error) {
    exceptions.push(String(error && error.stack ? error.stack : error));
    process.exitCode = 1;
  } finally {
    writeReport();
    await chrome.stop();
  }
}

await main();
