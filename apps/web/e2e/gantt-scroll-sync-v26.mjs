#!/usr/bin/env node
/**
 * Version 26 scroll-sync acceptance for the Activities table and Gantt.
 *
 * The two panes are one vertical surface: scrolling either one must keep every
 * Gantt bar on the table row it belongs to, including at the clamped bottom,
 * while the table header and Gantt timescale stay fixed. Horizontal Gantt
 * scrolling must move the timeline under a sticky axis without moving the
 * table. Runs at 1280×720 and 1366×768 in en/LTR and fa/RTL.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 \
 *   CUBI_TESTED_CODE_SHA=<code commit> \
 *   node e2e/gantt-scroll-sync-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "gantt-scroll-sync-v26");
const durableDir = process.env.CUBI_SCROLL_EVIDENCE_DIR || join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", "gantt-scroll-sync-v26-2026-11-12");
mkdirSync(outDir, { recursive: true });
mkdirSync(durableDir, { recursive: true });

const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const cells = [];
const screenshots = [];

function log(message) {
  process.stdout.write(`${message}\n`);
}

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

async function capture(page, name) {
  const file = `gantt-scroll-sync-v26/${name}.png`;
  await page.screenshot(file);
  copyFileSync(join(artifactsDir, file), join(durableDir, `${name}.png`));
  screenshots.push(`${name}.png`);
}

async function clickVisible(page, selector) {
  const clicked = await page.evaluate(`(() => {
    const element = [...document.querySelectorAll(${JSON.stringify(selector)})].find((item) => item.getClientRects().length > 0);
    if (!element || element.disabled) return false;
    element.click();
    return true;
  })()`);
  assert(clicked, `not clickable: ${selector}`);
}

async function setLanguage(page, locale) {
  const changed = await page.evaluate(`(() => {
    const select = document.querySelector("[data-workspace-language]");
    if (!select) return false;
    if (select.value === ${JSON.stringify(locale)}) return true;
    select.value = ${JSON.stringify(locale)};
    select.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  assert(changed, `language selector did not accept ${locale}`);
  await sleep(900);
}

async function measure(page) {
  return page.evaluate(`(() => {
    const table = document.querySelector("#cp-activity-grid .cp-table-wrap");
    const chart = document.querySelector("#cp-gantt .cp-gantt-chart");
    const axis = document.querySelector("#cp-gantt .cp-gantt-axis");
    const headerCell = document.querySelector("#cp-activity-grid thead th");
    const header = headerCell ? { top: +headerCell.getBoundingClientRect().top.toFixed(1) } : null;
    const rows = (root, selector) => [...root.querySelectorAll(selector)].map((row) => ({
      id: row.dataset.activityId ?? row.dataset.ganttActivityId ?? null,
      top: +row.getBoundingClientRect().top.toFixed(1),
      bottom: +row.getBoundingClientRect().bottom.toFixed(1),
    }));
    return {
      table: table ? { scrollTop: table.scrollTop, scrollLeft: table.scrollLeft, scrollHeight: table.scrollHeight, clientHeight: table.clientHeight, top: +table.getBoundingClientRect().top.toFixed(1), bottom: +table.getBoundingClientRect().bottom.toFixed(1) } : null,
      chart: chart ? { scrollTop: chart.scrollTop, scrollLeft: chart.scrollLeft, scrollHeight: chart.scrollHeight, clientHeight: chart.clientHeight, clientWidth: chart.clientWidth, scrollWidth: chart.scrollWidth, top: +chart.getBoundingClientRect().top.toFixed(1), bottom: +chart.getBoundingClientRect().bottom.toFixed(1) } : null,
      axis: axis ? { top: +axis.getBoundingClientRect().top.toFixed(1) } : null,
      header,
      tableRows: table ? rows(table, "tbody tr[data-activity-id]") : [],
      ganttRows: document.querySelector("#cp-gantt") ? rows(document.querySelector("#cp-gantt"), "[data-gantt-activity-id]") : [],
      viewport: { width: window.innerWidth, height: window.innerHeight },
      documentScrollWidth: document.documentElement.scrollWidth,
    };
  })()`);
}

/** Both panes must show the same activity rows at the same screen height. */
function alignment(state, label) {
  const gantt = new Map(state.ganttRows.map((row) => [row.id, row.top]));
  const pairs = state.tableRows.filter((row) => gantt.has(row.id));
  assert(pairs.length > 0, `${label}: no shared activity rows between table and Gantt`);
  const worst = pairs.reduce((max, row) => Math.max(max, Math.abs(gantt.get(row.id) - row.top)), 0);
  assert(worst <= 1.5, `${label}: table/Gantt rows drift by ${worst.toFixed(1)}px`);
  return { pairs: pairs.length, worstDelta: +worst.toFixed(2) };
}

async function scroll(page, pane, axis, value) {
  const set = await page.evaluate(`(() => {
    const element = document.querySelector(${JSON.stringify(pane === "table" ? "#cp-activity-grid .cp-table-wrap" : "#cp-gantt .cp-gantt-chart")});
    if (!element) return false;
    if (${JSON.stringify(axis)} === "top") {
      element.scrollTop = ${Number(value)};
    } else {
      // Chrome uses negative scrollLeft values for right-to-left surfaces.
      const rtl = getComputedStyle(element).direction === "rtl";
      element.scrollLeft = rtl ? -Math.abs(${Number(value)}) : Math.abs(${Number(value)});
    }
    return true;
  })()`);
  assert(set, `missing scroll surface for ${pane}`);
  await sleep(260);
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
    if (url.includes("/api/") && params.response.status >= 500) apiFailures.push({ status: params.response.status, url });
  });

  const report = {
    contract: "cubi-gantt-scroll-sync-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    cells,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
  };

  try {
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 768, deviceScaleFactor: 1, mobile: false });
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
    const hasPersonas = await page.evaluate('Boolean(document.querySelector(".persona"))');
    if (!hasPersonas) {
      await page.evaluate(`fetch("/preview/logout", { method: "POST", redirect: "manual" }).then((response) => response.status)`, { awaitPromise: true });
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
    await sleep(1600);
    await page.waitForSelector("#cp-gantt [data-gantt-activity-id]", "gantt rows");

    for (const viewport of [{ width: 1280, height: 720 }, { width: 1366, height: 768 }]) {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", {
        width: viewport.width,
        height: viewport.height,
        deviceScaleFactor: 1,
        mobile: false,
      });
      await sleep(900);
      for (const locale of ["en", "fa"]) {
        const label = `${viewport.width}x${viewport.height}-${locale}`;
        log(`\n[${label}]`);
        await setLanguage(page, locale);
        await page.waitForSelector("#cp-gantt [data-gantt-activity-id]", "gantt rows");

        const rest = await measure(page);
        assert(rest.table && rest.chart, `${label}: table or Gantt scroll surface is missing`);
        assert(rest.documentScrollWidth <= viewport.width + 1, `${label}: page overflows horizontally`);
        assert(rest.tableRows.length === rest.ganttRows.length, `${label}: row counts differ (${rest.tableRows.length}/${rest.ganttRows.length})`);
        const tableCapacity = rest.table.scrollHeight - rest.table.clientHeight;
        assert(tableCapacity > 0, `${label}: the table cannot scroll (${rest.table.scrollHeight}/${rest.table.clientHeight}), the sync cannot be exercised`);
        const restAlign = alignment(rest, `${label} rest`);

        // Scroll the table halfway; the chart must follow to the same row.
        const midpoint = Math.round(tableCapacity / 2);
        await scroll(page, "table", "top", midpoint);
        const afterTable = await measure(page);
        assert(Math.abs(afterTable.table.scrollTop - midpoint) <= 1, `${label}: the table did not scroll (${afterTable.table.scrollTop} != ${midpoint})`);
        assert(afterTable.chart.scrollTop > 0, `${label}: scrolling the table did not move the Gantt`);
        // The table header and the Gantt axis stay put while the rows move.
        assert(Math.abs(afterTable.header.top - rest.header.top) <= 1, `${label}: the table header moved while scrolling`);
        assert(Math.abs(afterTable.axis.top - rest.axis.top) <= 1, `${label}: the Gantt axis moved while scrolling`);
        const tableSync = alignment(afterTable, `${label} table→chart`);
        await capture(page, `gantt-scroll-table-${label}`);

        // Scrolling the chart back to the top must bring the table back too.
        await scroll(page, "chart", "top", 0);
        const afterChart = await measure(page);
        assert(afterChart.chart.scrollTop <= 2, `${label}: the chart did not return to the top (${afterChart.chart.scrollTop})`);
        assert(afterChart.table.scrollTop <= 2, `${label}: the table did not follow the chart to the top (${afterChart.table.scrollTop})`);
        const chartSync = alignment(afterChart, `${label} chart→table`);

        // Both extremes clamp together: the last table row and last bar must
        // still share one screen height at the bottom of both panes.
        await scroll(page, "table", "top", rest.table.scrollHeight);
        const bottom = await measure(page);
        const bottomAlign = alignment(bottom, `${label} bottom`);
        // Alignment wins over an absolute clamp: content heights can differ by
        // a couple of pixels, so the semantic check is that the last activity
        // row is fully visible in both panes at the bottom.
        const lastTable = bottom.tableRows.reduce((max, row) => (row.bottom > max.bottom ? row : max), bottom.tableRows[0]);
        const lastGantt = bottom.ganttRows.reduce((max, row) => (row.bottom > max.bottom ? row : max), bottom.ganttRows[0]);
        assert(bottom.table.scrollTop >= tableCapacity - 4, `${label}: table did not reach its bottom (${bottom.table.scrollTop}/${tableCapacity})`);
        assert(lastTable.bottom <= bottom.table.bottom + 1.5, `${label}: the last table row is clipped (${lastTable.bottom} > ${bottom.table.bottom})`);
        assert(lastGantt.bottom <= bottom.chart.bottom + 1.5, `${label}: the last Gantt row is clipped (${lastGantt.bottom} > ${bottom.chart.bottom})`);
        assert(bottom.chart.scrollTop > 0, `${label}: chart stayed at the top while the table was at the bottom`);
        assert(bottom.chart.scrollTop >= Math.max(0, bottom.chart.scrollHeight - bottom.chart.clientHeight) - 2, `${label}: the chart did not reach its clamped bottom (${bottom.chart.scrollTop})`);
        await capture(page, `gantt-scroll-bottom-${label}`);

        // Horizontal Gantt scrolling moves the timeline, not the table, and the
        // axis stays pinned above the scrolled rows.
        await clickVisible(page, '[data-gantt-scale="day"]');
        await sleep(550);
        const beforeHorizontal = await measure(page);
        assert(beforeHorizontal.chart.scrollWidth > beforeHorizontal.chart.clientWidth, `${label}: the day scale has no horizontal range (${beforeHorizontal.chart.scrollWidth}/${beforeHorizontal.chart.clientWidth})`);
        await scroll(page, "chart", "left", beforeHorizontal.chart.scrollWidth);
        const afterHorizontal = await measure(page);
        assert(Math.abs(afterHorizontal.chart.scrollLeft) > 0, `${label}: horizontal scrolling did not move the timeline`);
        assert(afterHorizontal.table.scrollLeft === beforeHorizontal.table.scrollLeft, `${label}: horizontal Gantt scrolling moved the table`);
        assert(afterHorizontal.axis && afterHorizontal.chart && Math.abs(afterHorizontal.axis.top - afterHorizontal.chart.top) <= 2, `${label}: the axis is not pinned to the top of the scrolled chart`);
        await capture(page, `gantt-scroll-horizontal-${label}`);

        cells.push({
          viewport,
          locale,
          rest: { table: rest.table, chart: rest.chart, alignment: restAlign },
          tableToChart: { scrollTop: afterTable.chart.scrollTop, alignment: tableSync },
          chartToTable: { scrollTop: afterChart.table.scrollTop, alignment: chartSync },
          bottom: { table: bottom.table.scrollTop, chart: bottom.chart.scrollTop, alignment: bottomAlign },
          horizontal: { scrollLeft: afterHorizontal.chart.scrollLeft, width: afterHorizontal.chart.scrollWidth, clientWidth: afterHorizontal.chart.clientWidth },
        });
      }
    }

    assert(exceptions.length === 0, `runtime exceptions: ${exceptions.join(" | ")}`);
    assert(consoleErrors.length === 0, `console errors: ${consoleErrors.join(" | ")}`);
    assert(apiFailures.length === 0, `HTTP 5xx responses: ${JSON.stringify(apiFailures)}`);
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(outDir, "gantt-scroll-sync-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(durableDir, "gantt-scroll-sync-v26.json"), JSON.stringify(report, null, 2));
    log(`\nPASS ${cells.length} scroll-sync cells at ${testedCodeSha}`);
  } catch (error) {
    report.finishedAt = new Date().toISOString();
    report.error = String(error && error.stack ? error.stack : error);
    writeFileSync(join(outDir, "gantt-scroll-sync-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(durableDir, "gantt-scroll-sync-v26.json"), JSON.stringify(report, null, 2));
    throw error;
  } finally {
    page.cdp.close();
    chrome.cdp.close();
    await chrome.stop();
  }
}

main().catch((error) => {
  process.stderr.write(`${error && error.stack ? error.stack : error}\n`);
  process.exitCode = 1;
});
