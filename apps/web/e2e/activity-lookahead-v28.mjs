#!/usr/bin/env node
/**
 * V28: the PDF "Create a lookahead filter" recipe, exactly.
 *
 * Reference: Primavera P6 Professional Help G57535-02 (October 2026),
 * "Create a lookahead filter", Chapter 9 Filtering, printed page 10.
 *
 * The reference defines lookahead as a user filter, not a separate dialog:
 *   Start  is within range of  CD  ..  CF+6w
 *   Activity % Complete  is not equal to  100
 *   name: Six-Week Lookahead, then Apply with Replace.
 *
 * This suite proves that the exact recipe is constructible, validated, applied,
 * persisted and reloadable in the real preview, and that it never writes
 * schedule facts.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4198 \
 *   CUBI_TESTED_CODE_SHA=<code commit> node e2e/activity-lookahead-v28.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4198";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const outDir = join(artifactsDir, "activity-lookahead-v28");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", "activity-workspace-v28");
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const dialogSelector = "dialog[data-desktop-dialog=filters]";
const report = {
  contract: "cubi-activity-lookahead-v28.v1",
  url: baseUrl,
  testedCodeSha,
  capturedAt: new Date().toISOString(),
  reference: {
    document: "G57535-02 (October 2026)",
    topic: "Create a lookahead filter",
    chapter: "9 Filtering",
    printedPage: 10,
  },
  screenshots: [],
  requests: [],
  exceptions: [],
  consoleErrors: [],
  apiFailures: [],
};

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

async function capture(page, name) {
  await page.screenshot(`activity-lookahead-v28/${name}.png`);
  copyFileSync(join(outDir, `${name}.png`), join(evidenceDir, `${name}.png`));
  report.screenshots.push(`${name}.png`);
}

async function openFilters(page) {
  const clicked = await page.evaluate(`(() => {
    const element = [...document.querySelectorAll('[data-desktop-command="dialog.filters"]')]
      .find((item) => item.getClientRects().length > 0 && !item.disabled);
    if (!element) return false;
    element.click();
    return true;
  })()`);
  assert(clicked, "the Filters command is missing or disabled");
  await page.waitForSelector(`${dialogSelector}[open]`, "filters dialog", 8000);
  await sleep(300);
}

async function setSelect(page, index, key, value) {
  const changed = await page.evaluate(`(() => {
    const select = document.querySelector('${dialogSelector} select[name="filter.${key}.${index}"]');
    if (!select) return false;
    select.value = ${JSON.stringify(value)};
    if (select.value !== ${JSON.stringify(value)}) return false;
    select.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  assert(changed, `filter ${key}.${index} did not accept ${value}`);
  await sleep(120);
}

async function setText(page, name, value) {
  const changed = await page.evaluate(`(() => {
    const input = document.querySelector('${dialogSelector} input[name="${name}"]');
    if (!input) return false;
    input.value = ${JSON.stringify(value)};
    input.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  assert(changed, `filter input ${name} is missing`);
  await sleep(150);
}

async function clickInDialog(page, selector) {
  const clicked = await page.evaluate(`(() => {
    const element = document.querySelector('${dialogSelector} ' + ${JSON.stringify(selector)});
    if (!element || element.disabled) return false;
    element.click();
    return true;
  })()`);
  assert(clicked, `not clickable in the Filters dialog: ${selector}`);
  await sleep(180);
}

async function preview(page) {
  return page.evaluate(`(() => {
    const element = document.querySelector("${dialogSelector} [data-filter-preview]");
    return {
      text: element?.textContent?.trim() ?? "",
      valid: element?.dataset.filterPreviewValid ?? "",
      matched: Number(element?.dataset.filterPreviewMatched ?? "-1"),
      rows: document.querySelectorAll("${dialogSelector} [data-filter-rows] .cp-filter-row").length,
      fieldLabels: [...document.querySelectorAll('${dialogSelector} select[name^="filter.field."]')].map((select) => select.selectedOptions[0]?.textContent?.trim() ?? ""),
      operatorLabels: [...document.querySelectorAll('${dialogSelector} select[name^="filter.operator."]')].map((select) => select.selectedOptions[0]?.textContent?.trim() ?? ""),
      values: [...document.querySelectorAll('${dialogSelector} input[name^="filter.value."]')].map((input) => input.value),
      highs: [...document.querySelectorAll('${dialogSelector} input[name^="filter.high."]')].map((input) => input.value),
    };
  })()`);
}

async function grid(page) {
  return page.evaluate(`(() => ({
    rows: document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]").length,
    saved: [...document.querySelectorAll("${dialogSelector} tr[data-filter-id]")].map((row) => row.getAttribute("data-filter-name")),
  }))()`);
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
  page.cdp.on("Network.requestWillBeSent", (params) => {
    const request = params.request ?? {};
    if (!["POST", "PATCH", "PUT", "DELETE"].includes(request.method ?? "")) return;
    if (!/\/api\//.test(request.url ?? "")) return;
    report.requests.push({ method: request.method, url: request.url, postData: request.postData ?? null });
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
  await page.click('button[name="role"][value="admin"]');
  await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
  await page.click('[data-project-id="preview-rps-01"]');
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
  await sleep(1400);

  const totalRows = (await grid(page)).rows;
  assert(totalRows >= 14, `expected the fixture rows, got ${totalRows}`);

  await openFilters(page);
  await setSelect(page, 0, "field", "start");
  await setSelect(page, 0, "operator", "within-range");
  await setText(page, "filter.value.0", "CD");
  await setText(page, "filter.high.0", "CF+6w");
  await clickInDialog(page, "[data-filter-row-add]");
  // Add appends after the two starter rows; the PDF's second criterion is the
  // new row, not a rewrite of the starter row.
  await setSelect(page, 2, "field", "progress");
  await setSelect(page, 2, "operator", "not-equals");
  await setText(page, "filter.value.2", "100");
  await setText(page, "filterName", "Six-Week Lookahead");

  const built = await preview(page);
  report.recipe = built;
  assert(built.rows === 3, `expected three rows after Add, got ${built.rows}`);
  assert(built.fieldLabels[0] === "Start", `row 1 field is ${built.fieldLabels[0]}`);
  assert(built.operatorLabels[0] === "is within range of", `row 1 operator is ${built.operatorLabels[0]}`);
  assert(built.values[0] === "CD" && built.highs[0] === "CF+6w", `row 1 values ${built.values[0]}..${built.highs[0]}`);
  assert(built.fieldLabels[2] === "Activity % Complete", `row 3 field is ${built.fieldLabels[2]}`);
  assert(built.operatorLabels[2] === "is not equal to", `row 3 operator is ${built.operatorLabels[2]}`);
  assert(built.values[2] === "100", `row 3 value is ${built.values[2]}`);
  assert(built.valid === "true", `the exact PDF recipe is invalid: ${built.text}`);
  assert(built.matched > 0 && built.matched < totalRows, `lookahead matched ${built.matched}/${totalRows}`);
  report.preview = { matched: built.matched, total: totalRows, text: built.text };
  await capture(page, "01-lookahead-recipe-en-1366");

  // Replace is the reference's first option: remove non-matching rows. It is
  // the default in the dialog; assert it rather than assuming the default.
  const replace = await page.evaluate(`Boolean(document.querySelector('${dialogSelector} [name="filterApplyMode"][value="replace"]')?.checked)`);
  assert(replace, "Replace activities is not the selected apply mode");
  await clickInDialog(page, "[data-dialog-ok]");
  await page.waitFor(`!document.querySelector('${dialogSelector}')?.open`, "filters dialog closed", 8000);
  await sleep(900);

  const applied = await grid(page);
  report.applied = applied;
  assert(applied.rows === built.matched, `grid shows ${applied.rows}, preview said ${built.matched}`);
  await capture(page, "02-lookahead-applied-en-1366");

  await page.navigate(`${baseUrl}/app?view=live&project=preview-rps-01`, "#cp-activity-grid tbody tr[data-activity-id]", "workspace reload");
  await sleep(1500);
  const reloadedGrid = await grid(page);
  await openFilters(page);
  const reloaded = await grid(page);
  report.reloaded = { rows: reloadedGrid.rows, saved: reloaded.saved };
  assert(reloadedGrid.rows === built.matched, `reload shows ${reloadedGrid.rows}, expected ${built.matched}`);
  assert(reloaded.saved.includes("six-week lookahead"), `saved filters: ${reloaded.saved.join(", ")}`);
  await capture(page, "03-lookahead-after-reload-en-1366");
  await clickInDialog(page, "[data-dialog-cancel]");

  // Saving a filter persists it into the project layout, which is the documented
  // behaviour. Filtering must never write activity, progress or schedule facts.
  const scheduleWrites = report.requests.filter((entry) => /\/(p6\/activities|schedule|progress)/.test(entry.url));
  report.layoutWrites = report.requests.filter((entry) => /\/p6\/layouts\//.test(entry.url)).length;
  assert(scheduleWrites.length === 0, `filtering issued schedule writes: ${JSON.stringify(scheduleWrites.slice(0, 3))}`);
  assert(report.exceptions.length === 0, `browser exceptions: ${report.exceptions.join(" | ")}`);
  assert(report.consoleErrors.length === 0, `console errors: ${report.consoleErrors.join(" | ")}`);
  assert(report.apiFailures.length === 0, `API failures: ${JSON.stringify(report.apiFailures)}`);

  report.finishedAt = new Date().toISOString();
  writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
  writeFileSync(join(evidenceDir, "lookahead-filter.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ ok: true, matched: built.matched, total: totalRows, reloaded: reloadedGrid.rows }, null, 2));
  await chrome.stop();
  process.exit(0);
}

main().catch((error) => {
  report.finishedAt = new Date().toISOString();
  report.failure = error?.stack ?? String(error);
  writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
  writeFileSync(join(evidenceDir, "lookahead-filter.json"), JSON.stringify(report, null, 2));
  console.error(error?.stack ?? error);
  process.exit(1);
});
