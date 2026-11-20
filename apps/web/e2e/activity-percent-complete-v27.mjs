#!/usr/bin/env node
/**
 * V27: Activity Table — Percent Complete Type column.
 *
 * The field already exists in the P6 registry and the Activity Master record;
 * this suite proves it reaches the persisted project layout, the grid header
 * and the cell value without any browser-side derivation.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 node e2e/activity-percent-complete-v27.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const projectId = "preview-rps-01";
const fieldId = "activity.percent_complete_type";
const heading = "Percent Complete Type";
const outDir = join(artifactsDir, "activity-percent-complete-v27");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", "activity-workspace-v27");
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const report = {
  contract: "cubi-activity-percent-complete-v27.v1",
  url: baseUrl,
  testedCodeSha: process.env.CUBI_TESTED_CODE_SHA || gitHead(),
  capturedAt: new Date().toISOString(),
  fieldId,
  screenshots: [],
  exceptions: [],
  consoleErrors: [],
  apiFailures: [],
};

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

async function capture(page, name) {
  await page.screenshot(`activity-percent-complete-v27/${name}.png`);
  copyFileSync(join(outDir, `${name}.png`), join(evidenceDir, `${name}.png`));
  report.screenshots.push(`${name}.png`);
}

async function poll(page, expression, timeout = 10000) {
  const started = Date.now();
  while (Date.now() - started < timeout) {
    if (await page.evaluate(expression)) return true;
    await sleep(250);
  }
  return false;
}

async function openColumns(page) {
  await page.evaluate(`document.querySelector('[data-desktop-menu="view"]')?.click()`);
  await sleep(250);
  const clicked = await page.evaluate(`(() => {
    const item = document.querySelector('[data-desktop-item="view.fields"]');
    if (!item || item.disabled) return false;
    item.click();
    return true;
  })()`);
  assert(clicked, "View > Columns… is missing or disabled");
  await page.waitForSelector("[data-p6-columns-dialog][open]", "Columns dialog");
  await sleep(350);
}

async function toggleVisibility(page, visible) {
  const current = await page.evaluate(`document.querySelector('[data-columns-visibility="${fieldId}"]')?.dataset.columnsVisible ?? null`);
  assert(current !== null, `${fieldId} is not listed in Selected Options`);
  if (current === String(visible)) return false;
  await page.evaluate(`document.querySelector('[data-columns-visibility="${fieldId}"]')?.click()`);
  await sleep(250);
  return true;
}

async function submitColumns(page) {
  await page.evaluate(`document.querySelector('[data-columns-ok]')?.click()`);
  await page.waitFor(`(() => !document.querySelector("[data-p6-columns-dialog][open]"))`, "Columns dialog closed", 8000);
  await sleep(1600);
}

async function gridState(page) {
  return page.evaluate(`(() => {
    const headers = [...document.querySelectorAll("#cp-activity-grid thead th")].map((th) => th.textContent.trim());
    const index = headers.indexOf(${JSON.stringify(heading)});
    const row = document.querySelector("#cp-activity-grid tbody tr[data-activity-id]");
    return {
      headers,
      index,
      cell: index >= 0 ? (row?.children[index]?.textContent?.trim() ?? "") : null,
      rows: document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]").length,
    };
  })()`);
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
  page.cdp.on("Network.responseReceived", (params) => {
    const url = params.response?.url ?? "";
    if (url.includes("/api/") && params.response.status >= 500) {
      report.apiFailures.push({ url, status: params.response.status });
    }
  });

  await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 768, deviceScaleFactor: 1, mobile: false });
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "form", "login");
  await page.evaluate(`(() => { localStorage.setItem("cubi:workspace-locale", "en"); return true; })()`);
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "form", "login");
  await page.evaluate(`(() => { document.querySelector('button[name="role"][value="admin"]').click(); return true; })()`);
  await page.waitForSelector(`[data-project-id="${projectId}"]`, "project selection");
  await page.click(`[data-project-id="${projectId}"]`);
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
  await sleep(1400);

  // The registry is the source of the column identity.
  const registry = await page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${projectId}/p6/fields/p6-field-registry.v1");
    const body = await response.json();
    return (body.fields ?? []).find((field) => field.field_id === ${JSON.stringify(fieldId)}) ?? null;
  })()`, { awaitPromise: true });
  assert(registry, "the P6 field registry does not expose activity.percent_complete_type");
  report.registry = {
    displayName: registry.display_name,
    dataType: registry.data_type,
    subjectArea: registry.subject_area,
  };
  assert(registry.display_name === heading, `registry label is ${registry.display_name}`);

  const before = await gridState(page);
  report.before = before;

  await openColumns(page);
  const toggledOn = await toggleVisibility(page, true);
  assert(toggledOn, "the column was already visible before the test");
  await submitColumns(page);

  const shown = await gridState(page);
  report.shown = shown;
  assert(shown.index >= 0, "the visible column did not reach the grid header");
  assert(/^(DURATION|UNITS|PHYSICAL|SCOPE)$/.test(shown.cell ?? ""), `unexpected stored cell value: ${shown.cell}`);
  assert(shown.rows === before.rows, `row count changed: ${before.rows} -> ${shown.rows}`);
  await capture(page, "percent-complete-column-en-1366");

  // Persistence: a full reload must keep the visible column and its value.
  await page.navigate(`${baseUrl}/app?view=live&project=${projectId}`, "#cp-activity-grid tbody tr[data-activity-id]", "workspace reload");
  await sleep(1500);
  const reloaded = await gridState(page);
  report.reloaded = reloaded;
  assert(reloaded.index >= 0, "the visible column did not survive reload");
  assert(reloaded.cell === shown.cell, `cell changed after reload: ${shown.cell} -> ${reloaded.cell}`);

  // Leave the project layout as it was.
  await openColumns(page);
  const toggledOff = await toggleVisibility(page, false);
  assert(toggledOff, "the column visibility did not toggle back");
  await submitColumns(page);
  const restored = await gridState(page);
  report.restored = restored;
  assert(restored.index < 0, "the column was not hidden again");

  report.finishedAt = new Date().toISOString();
  writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
  writeFileSync(join(evidenceDir, "percent-complete-column.json"), JSON.stringify(report, null, 2));
  assert(report.exceptions.length === 0, `browser exceptions: ${report.exceptions.join(" | ")}`);
  assert(report.consoleErrors.length === 0, `console errors: ${report.consoleErrors.join(" | ")}`);
  assert(report.apiFailures.length === 0, `api failures: ${JSON.stringify(report.apiFailures)}`);
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  await chrome.stop();
  process.exit(0);
}

main().catch((error) => {
  report.finishedAt = new Date().toISOString();
  report.failure = String(error);
  writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
  writeFileSync(join(evidenceDir, "percent-complete-column.json"), JSON.stringify(report, null, 2));
  process.stderr.write(`${error?.stack ?? error}\n`);
  process.exit(1);
});
