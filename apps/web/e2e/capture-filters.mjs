#!/usr/bin/env node
/**
 * Capture the Chapter 9 activity filters from the running preview:
 * the Filters dialog, a documented predefined filter, a custom AND filter,
 * a custom OR filter, saved-filter persistence across reload, and clearing.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4174 node e2e/capture-filters.mjs
 */

import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4174";
const outDir = join(artifactsDir, "filters-live");
mkdirSync(outDir, { recursive: true });

const tableState = `(() => {
  const label = document.querySelector("[data-active-filter]");
  const table = [...document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]")].map((row) => row.dataset.activityId);
  const gantt = [...document.querySelectorAll("#cp-gantt [data-gantt-activity-id]")].map((row) => row.dataset.ganttActivityId);
  return {
    label: label ? label.textContent.trim() : null,
    activeFilterId: label ? label.dataset.activeFilter : null,
    tableIds: table,
    ganttIds: gantt,
    tableCount: table.length,
    ganttCount: gantt.length,
    bands: document.querySelectorAll(".cp-p6-wbs-band").length,
  };
})()`;

const dialogState = `(() => {
  const dialog = document.querySelector('[data-desktop-dialog="filters"]');
  if (!dialog) return null;
  const select = dialog.querySelector('select[name="filterActiveId"]');
  const saved = select ? [...select.querySelectorAll("optgroup")].map((group) => ({
    label: group.getAttribute("label"),
    options: [...group.querySelectorAll("option")].map((option) => ({ value: option.value, label: option.textContent.trim() })),
  })) : [];
  const rows = [...dialog.querySelectorAll(".cp-filter-row")].map((row) => ({
    field: row.querySelector('select[name^="filter.field"]')?.value ?? null,
    operator: row.querySelector('select[name^="filter.operator"]')?.value ?? null,
    value: row.querySelector('input[name^="filter.value"]')?.value ?? null,
  }));
  const box = dialog.getBoundingClientRect();
  return {
    open: dialog.hasAttribute("open"),
    activeId: select ? select.value : null,
    groups: saved,
    rowCount: rows.length,
    rows,
    name: dialog.querySelector('input[name="filterName"]')?.value ?? null,
    match: dialog.querySelector('select[name="filterMatch"]')?.value ?? null,
    rect: { width: Math.round(box.width), height: Math.round(box.height), top: Math.round(box.top) },
    viewport: { width: window.innerWidth, height: window.innerHeight },
    fitsViewport: box.top >= 0 && box.bottom <= window.innerHeight + 1 && box.left >= 0 && box.right <= window.innerWidth + 1,
  };
})()`;

async function openFilters(page) {
  await page.evaluate(`(() => {
    const button = [...document.querySelectorAll('[data-desktop-command="dialog.filters"]')]
      .find((item) => item.getClientRects().length > 0);
    if (!button) return false;
    button.click();
    return true;
  })()`);
  await page.waitForSelector('[data-desktop-dialog="filters"][open]', "filters dialog", 4000);
  await sleep(250);
}

async function submitFilters(page) {
  await page.evaluate(`(() => {
    const dialog = document.querySelector('[data-desktop-dialog="filters"]');
    if (!dialog) return false;
    const button = dialog.querySelector("[data-dialog-ok]");
    if (!button) return false;
    button.click();
    return true;
  })()`);
  await page.waitFor(
    `(() => { const dialog = document.querySelector('[data-desktop-dialog="filters"]'); return !dialog || !dialog.hasAttribute("open"); })()`,
    "filters dialog closed",
    4000,
  );
  await sleep(900);
}

async function setSelect(page, selector, value) {
  const ok = await page.evaluate(`(() => {
    const select = document.querySelector(${JSON.stringify(selector)});
    if (!select) return false;
    select.value = ${JSON.stringify(value)};
    if (select.value !== ${JSON.stringify(value)}) return false;
    select.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  if (!ok) throw new Error(`could not set ${selector} to ${value}`);
}

async function setInput(page, selector, value) {
  const ok = await page.evaluate(`(() => {
    const input = document.querySelector(${JSON.stringify(selector)});
    if (!input) return false;
    input.value = ${JSON.stringify(value)};
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  if (!ok) throw new Error(`could not fill ${selector}`);
}

async function fillCriterion(page, index, field, operator, value) {
  await setSelect(page, `[data-desktop-dialog="filters"] select[name="filter.field.${index}"]`, field);
  await setSelect(page, `[data-desktop-dialog="filters"] select[name="filter.operator.${index}"]`, operator);
  await setInput(page, `[data-desktop-dialog="filters"] input[name="filter.value.${index}"]`, value);
}

async function main() {
  const health = await waitForHttp(`${baseUrl}/preview/health`, 20000);
  if (!(health.status === "ok" || health.status === 200)) throw new Error(`preview health ${health.status}`);

  const chrome = await launchChrome();
  const page = new Page(chrome.cdp);
  const report = {
    baseUrl,
    gitHead: gitHead(),
    capturedAt: new Date().toISOString(),
    screenshots: {},
    baseline: null,
    dialog: null,
    predefined: null,
    customAnd: null,
    customOr: null,
    savedDialog: null,
    afterReload: null,
    cleared: null,
  };
  try {
    await page.initialize();
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
    await sleep(400);
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "form", "login");
    await page.evaluate(`(() => {
      const button = [...document.querySelectorAll("form button")].find((item) => (item.textContent || "").trim().startsWith("Planner"));
      if (!button) return false;
      button.click();
      return true;
    })()`);
    await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
    await page.click('[data-project-id="preview-rps-01"]');
    await page.waitForSelector("#cp-activity-grid tbody tr", "workspace rows");
    await sleep(1200);
    await page.evaluate(`(() => {
      const select = document.querySelector("[data-workspace-language]");
      if (!select) return false;
      select.value = "en";
      select.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    })()`);
    await sleep(900);

    // Start from All activities even if a previous capture saved a filter.
    await openFilters(page);
    await setSelect(page, '[data-desktop-dialog="filters"] select[name="filterActiveId"]', "");
    await submitFilters(page);
    report.baseline = await page.evaluate(tableState);

    // 1. The Filters dialog itself: predefined filters, four criteria rows.
    await openFilters(page);
    report.dialog = await page.evaluate(dialogState);
    await page.screenshot("filters-live/filters-dialog-1280x720.png");
    report.screenshots.dialog = "filters-live/filters-dialog-1280x720.png";
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 2, mobile: false });
    await sleep(350);
    await page.screenshot("filters-live/filters-dialog-zoom.png");
    report.screenshots.dialogZoom = "filters-live/filters-dialog-zoom.png";
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
    await sleep(300);

    // 2. Documented predefined filter: In Progress.
    await setSelect(page, '[data-desktop-dialog="filters"] select[name="filterActiveId"]', "builtin:in-progress");
    await submitFilters(page);
    report.predefined = await page.evaluate(tableState);
    await page.screenshot("filters-live/filters-in-progress-1280x720.png");
    report.screenshots.predefined = "filters-live/filters-in-progress-1280x720.png";

    // 3. Custom AND filter: Civil works that are not Completed.
    await openFilters(page);
    await setInput(page, '[data-desktop-dialog="filters"] input[name="filterName"]', "Civil open");
    await setSelect(page, '[data-desktop-dialog="filters"] select[name="filterMatch"]', "all");
    await fillCriterion(page, 0, "wbs", "contains", "Civil");
    await fillCriterion(page, 1, "activity_status", "not-equals", "Completed");
    await submitFilters(page);
    report.customAnd = await page.evaluate(tableState);
    await page.screenshot("filters-live/filters-custom-and-1280x720.png");
    report.screenshots.customAnd = "filters-live/filters-custom-and-1280x720.png";

    // 4. Custom OR filter: Civil works or Procurement.
    await openFilters(page);
    await setInput(page, '[data-desktop-dialog="filters"] input[name="filterName"]', "Civil or procurement");
    await setSelect(page, '[data-desktop-dialog="filters"] select[name="filterMatch"]', "any");
    await fillCriterion(page, 0, "wbs", "contains", "Civil");
    await fillCriterion(page, 1, "wbs", "contains", "Procurement");
    await submitFilters(page);
    report.customOr = await page.evaluate(tableState);
    await page.screenshot("filters-live/filters-custom-or-1280x720.png");
    report.screenshots.customOr = "filters-live/filters-custom-or-1280x720.png";

    // 5. Reopen: both saved filters are listed, active one selected.
    await openFilters(page);
    report.savedDialog = await page.evaluate(dialogState);
    await page.screenshot("filters-live/filters-saved-list-1280x720.png");
    report.screenshots.savedDialog = "filters-live/filters-saved-list-1280x720.png";
    await page.evaluate(`(() => {
      const dialog = document.querySelector('[data-desktop-dialog="filters"]');
      dialog?.querySelector("[data-dialog-cancel]")?.click();
      return true;
    })()`);
    await sleep(400);

    // 6. Reload: the saved layout metadata still applies the filter.
    await page.reload();
    await page.waitForSelector("#cp-activity-grid tbody tr", "workspace rows after reload");
    await sleep(1400);
    report.afterReload = await page.evaluate(tableState);

    // 7. Clear back to All activities.
    await openFilters(page);
    await setSelect(page, '[data-desktop-dialog="filters"] select[name="filterActiveId"]', "");
    await submitFilters(page);
    report.cleared = await page.evaluate(tableState);
    await page.screenshot("filters-live/filters-cleared-1280x720.png");
    report.screenshots.cleared = "filters-live/filters-cleared-1280x720.png";
  } finally {
    writeFileSync(join(outDir, "filters-capture.json"), JSON.stringify(report, null, 2));
    page.cdp.close();
    chrome.cdp.close();
    await chrome.stop();
  }
  process.stdout.write(`Filters capture: ${join(outDir, "filters-capture.json")}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error && error.stack ? error.stack : error}\n`);
  process.exit(1);
});
