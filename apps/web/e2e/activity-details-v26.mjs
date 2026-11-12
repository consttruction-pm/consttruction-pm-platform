#!/usr/bin/env node
/**
 * Activity Details (Priority Zero) acceptance.
 *
 * Verifies that the live bottom pane exposes the sixteen required Version 26
 * tabs plus the CUBI calendar tab, that every data tab issues its authoritative
 * read and distinguishes loading / empty / error from real rows, and that the
 * Customize Tabs display set survives a reload.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 \
 *   node e2e/activity-details-v26.mjs
 */

import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const outDir = join(artifactsDir, "activity-details-v26");
mkdirSync(outDir, { recursive: true });

const REQUIRED_TABS = [
  "general", "status", "resources", "predecessors", "successors", "relationships",
  "codes", "notebook", "steps", "wps-docs", "expenses", "issues", "risks",
  "summary", "udfs", "update-history",
];
const DATA_TABS = ["resources", "expenses", "issues", "risks", "udfs", "update-history"];

const report = { url: baseUrl, tabs: [], data: {}, customize: null, exceptions: [], consoleErrors: [], apiFailures: [] };

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

async function main() {
  await waitForHttp(`${baseUrl}/preview/health`, 20000);
  const chrome = await launchChrome();
  const page = new Page(chrome.cdp);
  await page.initialize();
  page.cdp.on("Runtime.exceptionThrown", (params) => {
    report.exceptions.push(params.exceptionDetails?.exception?.description ?? params.exceptionDetails?.text ?? "unknown exception");
  });
  page.cdp.on("Runtime.consoleAPICalled", (params) => {
    if (params.type !== "error") return;
    report.consoleErrors.push((params.args ?? []).map((arg) => arg.value ?? arg.description ?? arg.type).join(" "));
  });
  await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 768, deviceScaleFactor: 1, mobile: false });
  page.cdp.on("Network.responseReceived", (params) => {
    const url = params.response?.url ?? "";
    if (url.includes("/api/") && params.response.status >= 500) {
      report.apiFailures.push({ url, status: params.response.status });
    }
  });

  await page.initialize();
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "form", "login");
  await page.click('button[name="role"][value="admin"]');
  await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
  await page.click('[data-project-id="preview-rps-01"]');
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
  await sleep(1600);
  await page.click("#cp-activity-grid tbody tr[data-activity-id]");
  await page.waitForSelector('#cp-details [data-detail-tab="general"]', "details tabs");
  await sleep(1200);

  report.tabs = await page.evaluate(`(() => [...document.querySelectorAll('#cp-details [data-detail-tab]')].map((tab) => tab.dataset.detailTab))()`);
  assert(report.tabs.length === REQUIRED_TABS.length + 1, `expected ${REQUIRED_TABS.length + 1} tabs, got ${report.tabs.length}`);
  assert(JSON.stringify(report.tabs.slice(0, REQUIRED_TABS.length)) === JSON.stringify(REQUIRED_TABS), "required tab order is wrong");
  assert(report.tabs.at(-1) === "calendar", "calendar tab must stay last");

  for (const tab of DATA_TABS) {
    await page.evaluate(`(() => { const b = document.querySelector('#cp-details [data-detail-tab="${tab}"]'); if (b) b.click(); return Boolean(b); })()`);
    await sleep(900);
    const state = await page.evaluate(`(() => {
      const panel = document.querySelector('#cp-details [data-detail-panel="${tab}"]');
      return {
        text: panel?.innerText ?? "",
        rows: panel?.querySelectorAll("tbody tr").length ?? 0,
        loading: Boolean(panel?.querySelector("[data-details-loading]")),
        error: Boolean(panel?.querySelector(".cp-detail-error")),
        refresh: Boolean(panel?.querySelector("[data-details-refresh]")),
      };
    })()`);
    report.data[tab] = state;
    assert(state.refresh, `${tab} must expose a Reload action`);
    assert(!state.loading, `${tab} should have finished loading`);
    assert(!state.error, `${tab} reported a read error: ${state.text.slice(0, 180)}`);
  }

  // Customize Tabs: hide Status, apply, confirm, reload and confirm again.
  await page.evaluate(`(() => document.querySelector("[data-details-customize-open]")?.click())()`);
  await page.waitForSelector("[data-details-customize-dialog][open]", "customize dialog");
  await page.evaluate(`(() => {
    const dialog = document.querySelector("[data-details-customize-dialog]");
    const choose = [...dialog.querySelectorAll("[data-customize-tab]")].find((item) => item.dataset.customizeTab === "status" && item.dataset.customizeSide === "display");
    choose?.click();
    dialog.querySelector("[data-customize-remove]")?.click();
    return true;
  })()`);
  await page.click("[data-details-customize-ok]");
  await sleep(700);
  const afterApply = await page.evaluate(`(() => [...document.querySelectorAll('#cp-details [data-detail-tab]')].map((tab) => tab.dataset.detailTab))()`);
  assert(!afterApply.includes("status"), "status tab was not removed");
  await page.reload('#cp-details [data-detail-tab="general"]', "reload after customize");
  await sleep(1200);
  const afterReload = await page.evaluate(`(() => [...document.querySelectorAll('#cp-details [data-detail-tab]')].map((tab) => tab.dataset.detailTab))()`);
  report.customize = { afterApply, afterReload };
  assert(!afterReload.includes("status"), "customize display set did not survive reload");

  // Restore defaults for the next audit.
  await page.evaluate(`(() => {
    document.querySelector("[data-details-customize-open]")?.click();
    const dialog = document.querySelector("[data-details-customize-dialog]");
    dialog?.querySelector("[data-customize-default]")?.click();
    dialog?.querySelector("[data-details-customize-ok]")?.click();
    return true;
  })()`);

  await page.screenshot("activity-details-v26/details-en-1366.png");
  writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
  assert(report.exceptions.length === 0, `browser exceptions: ${report.exceptions.join(" | ")}`);
  assert(report.consoleErrors.length === 0, `console errors: ${report.consoleErrors.join(" | ")}`);
  assert(report.apiFailures.length === 0, `api failures: ${JSON.stringify(report.apiFailures)}`);
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  chrome.stop();
}

main().catch(async (error) => {
  writeFileSync(join(outDir, "report.json"), JSON.stringify({ ...report, failure: String(error) }, null, 2));
  process.stderr.write(`${error?.stack ?? error}\n`);
  process.exit(1);
});
