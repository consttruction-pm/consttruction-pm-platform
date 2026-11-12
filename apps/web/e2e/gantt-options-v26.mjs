#!/usr/bin/env node
/**
 * Version 26 Gantt options acceptance.
 *
 * Exercises the real Activities Gantt in the real preview and asserts:
 * - the legend appears above/below the chart with one item per visible bar kind;
 * - sight lines (major horizontal, minor horizontal, minor vertical) appear and
 *   disappear exactly when their options are toggled;
 * - a per-bar filter and the Show flag change the drawn bar kinds;
 * - all five timescales render ticks at their documented content widths;
 * - zoom in/out and Fit change the scale without page overflow;
 * - collapsing and expanding all WBS branches keeps table/Gantt rows aligned.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 \
 *   CUBI_TESTED_CODE_SHA=<code commit> \
 *   node e2e/gantt-options-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "gantt-options-v26");
const durableDir = process.env.CUBI_GANTT_EVIDENCE_DIR || join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", "gantt-options-v26-2026-11-12");
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
  const file = `gantt-options-v26/${name}.png`;
  await page.screenshot(file);
  copyFileSync(join(artifactsDir, file), join(durableDir, `${name}.png`));
  screenshots.push(`${name}.png`);
  return file;
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

async function applyBars(page, mutate) {
  await clickVisible(page, '[data-desktop-command="dialog.bars"]');
  await page.waitForSelector('dialog[data-desktop-dialog="bars"][open]', "bars dialog", 6000);
  await sleep(220);
  await page.evaluate(`(() => {
    const dialog = document.querySelector('dialog[data-desktop-dialog="bars"]');
    const form = dialog.querySelector('[data-dialog-form="bars"]');
    ${mutate}
    form.querySelector('[data-dialog-ok]').click();
    return true;
  })()`);
  await page.waitFor(`!document.querySelector('dialog[data-desktop-dialog="bars"]')?.open`, "bars dialog closed", 6000);
  await sleep(650);
  await page.waitForSelector("#cp-gantt [data-gantt-activity-id]", "gantt rows after bars dialog");
}

async function applyTimescale(page, mutate) {
  await clickVisible(page, '[data-desktop-command="dialog.timescale"]');
  await page.waitForSelector('dialog[data-desktop-dialog="timescale"][open]', "timescale dialog", 6000);
  await sleep(220);
  await page.evaluate(`(() => {
    const dialog = document.querySelector('dialog[data-desktop-dialog="timescale"]');
    const form = dialog.querySelector('[data-dialog-form="timescale"]');
    ${mutate}
    form.querySelector('[data-dialog-ok]').click();
    return true;
  })()`);
  await page.waitFor(`!document.querySelector('dialog[data-desktop-dialog="timescale"]')?.open`, "timescale dialog closed", 6000);
  await sleep(650);
  await page.waitForSelector("#cp-gantt [data-gantt-activity-id]", "gantt rows after timescale dialog");
}

const measurement = `(() => {
  const rect = (element) => {
    if (!element) return null;
    const r = element.getBoundingClientRect();
    return { left: +r.left.toFixed(1), top: +r.top.toFixed(1), right: +r.right.toFixed(1), bottom: +r.bottom.toFixed(1), width: +r.width.toFixed(1), height: +r.height.toFixed(1) };
  };
  const board = document.querySelector("#cp-gantt .cp-gantt-board");
  const chart = document.querySelector("#cp-gantt .cp-gantt-chart");
  const track = document.querySelector("#cp-gantt .cp-gantt-track");
  const legend = document.querySelector("#cp-gantt [data-gantt-legend]");
  const tableRows = [...document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]")];
  const ganttRows = [...document.querySelectorAll("#cp-gantt [data-gantt-activity-id]")];
  const bars = [...document.querySelectorAll("#cp-gantt [data-gantt-bar-kind]")];
  const barsByKind = {};
  for (const bar of bars) {
    const kind = bar.dataset.ganttBarKind || "unknown";
    barsByKind[kind] = (barsByKind[kind] || 0) + 1;
  }
  const pairs = tableRows.slice(0, Math.min(tableRows.length, ganttRows.length)).map((row, index) => ({
    table: +row.getBoundingClientRect().height.toFixed(1),
    gantt: +ganttRows[index].getBoundingClientRect().height.toFixed(1),
  }));
  const contentWidth = board ? Number.parseFloat(getComputedStyle(board).getPropertyValue("--cp-gantt-content-width")) : 0;
  return {
    scale: board?.dataset.ganttScaleMode ?? null,
    viewport: { width: window.innerWidth, height: window.innerHeight },
    documentScrollWidth: document.documentElement.scrollWidth,
    bodyScrollWidth: document.body.scrollWidth,
    rows: { table: tableRows.length, gantt: ganttRows.length },
    rowHeightMismatch: pairs.filter((pair) => Math.abs(pair.table - pair.gantt) > 1).length,
    bands: document.querySelectorAll(".cp-p6-wbs-band").length,
    ganttGroups: document.querySelectorAll("#cp-gantt .cp-gantt-group-row").length,
    ticks: document.querySelectorAll("#cp-gantt [data-gantt-tick]").length,
    periodGroups: document.querySelectorAll("#cp-gantt [data-timescale-group]").length,
    bars: bars.length,
    barsByKind,
    legend: legend ? {
      position: legend.dataset.ganttLegend,
      rect: rect(legend),
      items: legend.querySelectorAll("[data-gantt-legend-kind]").length,
      kinds: [...legend.querySelectorAll("[data-gantt-legend-kind]")].map((item) => item.dataset.ganttLegendKind),
      swatchColors: [...new Set([...legend.querySelectorAll(".cp-gantt-legend-swatch")].map((swatch) => getComputedStyle(swatch).getPropertyValue("--cp-legend-color").trim()))].length,
      chart: rect(chart),
    } : null,
    sight: {
      majorHorizontal: document.querySelectorAll("#cp-gantt .cp-gantt-sight-line.is-horizontal.is-major").length,
      minorHorizontal: document.querySelectorAll("#cp-gantt .cp-gantt-sight-line.is-horizontal.is-minor").length,
      minorVertical: document.querySelectorAll("#cp-gantt .cp-gantt-grid-line.is-minor").length,
    },
    contentWidth,
    chartClientWidth: chart ? chart.clientWidth : 0,
    chartScrollLeft: chart ? chart.scrollLeft : 0,
    trackWidth: track ? +track.getBoundingClientRect().width.toFixed(1) : 0,
  };
})()`;

async function measure(page) {
  return page.evaluate(measurement);
}

function verifyBase(state, label) {
  assert(state.rows.table === state.rows.gantt && state.rows.table > 0, `${label}: table/Gantt row counts differ (${state.rows.table}/${state.rows.gantt})`);
  assert(state.rowHeightMismatch === 0, `${label}: ${state.rowHeightMismatch} table/Gantt row height mismatches`);
  assert(state.bands > 0 && state.ganttGroups > 0, `${label}: WBS bands are missing (${state.bands}/${state.ganttGroups})`);
  assert(state.documentScrollWidth <= state.viewport.width + 1, `${label}: page overflows horizontally (${state.documentScrollWidth} > ${state.viewport.width})`);
  assert(state.bodyScrollWidth <= state.viewport.width + 1, `${label}: body overflows horizontally (${state.bodyScrollWidth} > ${state.viewport.width})`);
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
    contract: "cubi-gantt-options-v26.v1",
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

    for (const locale of ["en", "fa"]) {
      const label = `1366x768-${locale}`;
      log(`\n[${label}]`);
      await setLanguage(page, locale);
      await page.waitForSelector("#cp-gantt [data-gantt-activity-id]", "gantt rows");
      // The preview persists presentation per project, so start every cell from
      // the documented defaults instead of inheriting a previous run.
      await applyBars(page, `
        form.querySelector('[name="gantt.legend.visible"]').checked = false;
        form.querySelector('[name="gantt.legend.position"]').value = 'bottom';
        form.querySelector('[name="gantt.sightLines.beforeSummaries"]').checked = false;
        form.querySelector('[name="gantt.sightLines.rowInterval"]').value = '0';
        form.querySelector('[name="gantt.sightLines.minorVertical"]').checked = false;
        form.querySelector('[name="bar.critical.filter"]').value = 'critical';
        form.querySelector('[name="bar.critical.visible"]').checked = true;
      `);
      await applyTimescale(page, `
        form.querySelector('[name="timescale.interval"]').value = 'quarter-month';
      `);
      await clickVisible(page, '[data-gantt-scale="month"]');
      await sleep(500);
      const baseline = await measure(page);
      verifyBase(baseline, `${label} baseline`);
      assert(baseline.legend === null, `${label}: legend is visible before it is enabled`);
      assert(baseline.sight.majorHorizontal === 0 && baseline.sight.minorHorizontal === 0, `${label}: sight lines are visible before they are enabled`);
      const baselineCriticalBars = baseline.barsByKind.critical ?? 0;
      const baselineTaskBars = baseline.barsByKind.task ?? 0;
      assert(baselineCriticalBars > 0, `${label}: the fixture has no critical bars to test a per-bar filter`);

      // Legend above the chart.
      await applyBars(page, `
        form.querySelector('[name="gantt.legend.visible"]').checked = true;
        form.querySelector('[name="gantt.legend.position"]').value = 'top';
      `);
      const legendTop = await measure(page);
      verifyBase(legendTop, `${label} legend top`);
      assert(legendTop.legend && legendTop.legend.position === "top", `${label}: top legend is missing`);
      assert(legendTop.legend.items >= 5, `${label}: legend has too few items (${legendTop.legend.items})`);
      assert(legendTop.legend.swatchColors >= 4, `${label}: legend swatches do not show distinct colours (${legendTop.legend.swatchColors})`);
      assert(legendTop.legend.rect.bottom <= legendTop.legend.chart.top + 1, `${label}: top legend is not above the chart`);
      await capture(page, `gantt-legend-top-${label}`);

      // Legend below the chart.
      await applyBars(page, `form.querySelector('[name="gantt.legend.position"]').value = 'bottom';`);
      const legendBottom = await measure(page);
      await capture(page, `gantt-legend-bottom-${label}`);
      assert(legendBottom.legend && legendBottom.legend.position === "bottom", `${label}: bottom legend is missing`);
      assert(legendBottom.legend.rect.top >= legendBottom.legend.chart.bottom - 1, `${label}: bottom legend is not below the chart (legend ${legendBottom.legend.rect.top}, chart ${legendBottom.legend.chart.bottom})`);

      // Sight lines.
      await applyBars(page, `
        form.querySelector('[name="gantt.sightLines.beforeSummaries"]').checked = true;
        form.querySelector('[name="gantt.sightLines.rowInterval"]').value = '2';
        form.querySelector('[name="gantt.sightLines.minorVertical"]').checked = true;
      `);
      const sight = await measure(page);
      verifyBase(sight, `${label} sight lines`);
      assert(sight.sight.majorHorizontal === sight.ganttGroups, `${label}: major sight lines ${sight.sight.majorHorizontal} != ${sight.ganttGroups} summary groups`);
      // The chart's row list includes one group row per WBS band plus the
      // activity rows, and the interval starts at the configured row.
      const chartRows = sight.rows.gantt + sight.ganttGroups;
      const expectedMinor = Math.floor((chartRows - 1) / 2);
      assert(sight.sight.minorHorizontal === expectedMinor, `${label}: minor sight lines ${sight.sight.minorHorizontal} != ${expectedMinor}`);
      // The first tick sits at the left edge and is deliberately skipped.
      assert(sight.sight.minorVertical === sight.ticks - 1, `${label}: minor vertical lines ${sight.sight.minorVertical} != ${sight.ticks - 1} plotted ticks`);
      await capture(page, `gantt-sight-lines-${label}`);

      // Per-bar filter and Show flag.
      await applyBars(page, `form.querySelector('[name="bar.critical.filter"]').value = 'milestone';`);
      const filtered = await measure(page);
      verifyBase(filtered, `${label} critical filter milestone`);
      assert((filtered.barsByKind.critical ?? 0) === 0, `${label}: critical bars still drawn under a disjoint filter (${filtered.barsByKind.critical})`);
      // A non-matching specialised style falls back to the generic task bar
      // instead of leaving the row blank, so the total stays stable while the
      // drawn kind changes.
      assert((filtered.barsByKind.task ?? 0) === baselineTaskBars + baselineCriticalBars, `${label}: critical bars did not fall back to task bars (${filtered.barsByKind.task})`);
      assert(filtered.bars === baseline.bars, `${label}: a per-bar filter changed the bar total (${filtered.bars} != ${baseline.bars})`);
      await capture(page, `gantt-bar-filter-${label}`);

      await applyBars(page, `
        form.querySelector('[name="bar.critical.filter"]').value = 'critical';
        form.querySelector('[name="bar.critical.visible"]').checked = false;
      `);
      const hidden = await measure(page);
      verifyBase(hidden, `${label} critical hidden`);
      assert((hidden.barsByKind.critical ?? 0) === 0, `${label}: hidden critical bars are still drawn`);
      assert((hidden.barsByKind.task ?? 0) === baselineTaskBars + baselineCriticalBars, `${label}: hidden critical bars did not fall back to task bars (${hidden.barsByKind.task})`);
      assert(hidden.legend && hidden.legend.items === legendBottom.legend.items - 1, `${label}: legend did not drop the hidden critical style (${hidden.legend?.items})`);
      await applyBars(page, `form.querySelector('[name="bar.critical.visible"]').checked = true;`);
      const restored = await measure(page);
      assert((restored.barsByKind.critical ?? 0) === baselineCriticalBars, `${label}: critical bars did not return (${restored.barsByKind.critical} != ${baselineCriticalBars})`);

      // Five timescales, chosen from the Gantt scale buttons.
      const scales = [
        { scale: "year", width: 520 },
        { scale: "quarter", width: 640 },
        { scale: "month", width: 800 },
        { scale: "week", width: 1100 },
        { scale: "day", width: 1600 },
      ];
      const scaledWidths = Object.fromEntries(scales.map((entry) => [entry.scale, entry.width]));
      const scaleFacts = [];
      for (const entry of scales) {
        await clickVisible(page, `[data-gantt-scale="${entry.scale}"]`);
        await sleep(550);
        await page.waitForSelector("#cp-gantt [data-gantt-activity-id]", "gantt rows after scale");
        const scaled = await measure(page);
        verifyBase(scaled, `${label} scale ${entry.scale}`);
        assert(scaled.scale === entry.scale, `${label}: scale is ${scaled.scale}, expected ${entry.scale}`);
        assert(scaled.contentWidth === entry.width, `${label}: ${entry.scale} content width ${scaled.contentWidth} != ${entry.width}`);
        assert(scaled.ticks > 0, `${label}: ${entry.scale} has no ticks`);
        scaleFacts.push({ scale: entry.scale, contentWidth: scaled.contentWidth, ticks: scaled.ticks, periods: scaled.periodGroups });
        await capture(page, `gantt-scale-${entry.scale}-${label}`);
      }

      // A format-only change must not reset the scale the user picked.
      await applyTimescale(page, `form.querySelector('[name="timescale.fontSize"]').value = '12';`);
      const headerOnly = await measure(page);
      assert(headerOnly.scale === "day", `${label}: a header-only timescale edit reset the scale (${headerOnly.scale})`);
      // Changing the interval picks the matching tick density.
      await applyTimescale(page, `form.querySelector('[name="timescale.interval"]').value = 'year-quarter';`);
      const intervalChanged = await measure(page);
      assert(intervalChanged.scale === "quarter", `${label}: year/quarter interval did not select the quarter scale (${intervalChanged.scale})`);

      // Zoom in/out and Fit.
      await clickVisible(page, '[data-desktop-command="view.zoom-in"]');
      await sleep(500);
      const zoomedIn = await measure(page);
      assert(zoomedIn.scale === "month", `${label}: zoom in from quarter is ${zoomedIn.scale}`);
      await clickVisible(page, '[data-desktop-command="view.zoom-out"]');
      await sleep(500);
      const zoomedOut = await measure(page);
      assert(zoomedOut.scale === "quarter", `${label}: zoom out from month is ${zoomedOut.scale}`);
      await clickVisible(page, '[data-desktop-command="view.fit"]');
      await sleep(500);
      const fitted = await measure(page);
      verifyBase(fitted, `${label} fit`);
      // Fit must choose the finest zoom that actually fits the visible pane:
      // its own declared width may not exceed the pane, and the next finer zoom
      // must not have fitted. When even year is wider than the pane, year is
      // the documented floor.
      const fitOrder = ["day", "week", "month", "quarter", "year"];
      const fitIndex = fitOrder.indexOf(fitted.scale);
      assert(fitIndex >= 0, `${label}: Fit produced an unknown scale (${fitted.scale})`);
      assert(
        fitted.scale === "year" || fitted.contentWidth <= fitted.chartClientWidth + 1,
        `${label}: Fit chose ${fitted.scale} (${fitted.contentWidth}px) wider than the pane (${fitted.chartClientWidth}px)`,
      );
      assert(
        fitIndex === 0 || scaledWidths[fitOrder[fitIndex - 1]] > fitted.chartClientWidth + 1,
        `${label}: Fit chose ${fitted.scale} although the finer ${fitOrder[fitIndex - 1]} would fit`,
      );
      await capture(page, `gantt-zoom-fit-${label}`);

      // Collapse and expand every WBS branch.
      await clickVisible(page, "[data-wbs-collapse-all]");
      await sleep(600);
      const collapsed = await measure(page);
      assert(collapsed.rows.table === collapsed.rows.gantt, `${label}: collapsed row counts differ`);
      assert(collapsed.rows.gantt < baseline.rows.gantt, `${label}: collapse-all did not hide activity rows (${collapsed.rows.gantt})`);
      assert(collapsed.bands > 0, `${label}: collapse-all removed the WBS bands`);
      assert(collapsed.ganttGroups === baseline.ganttGroups, `${label}: collapse-all removed summary groups`);
      assert(collapsed.documentScrollWidth <= collapsed.viewport.width + 1, `${label}: collapsed chart overflows horizontally`);
      await capture(page, `gantt-collapsed-${label}`);
      await clickVisible(page, "[data-wbs-expand-all]");
      await sleep(600);
      const expanded = await measure(page);
      verifyBase(expanded, `${label} expanded`);
      assert(expanded.rows.gantt === baseline.rows.gantt, `${label}: expand-all did not restore rows (${expanded.rows.gantt} != ${baseline.rows.gantt})`);

      // Restore the default presentation and month scale.
      await applyTimescale(page, `
        form.querySelector('[name="timescale.interval"]').value = 'quarter-month';
        form.querySelector('[name="timescale.fontSize"]').value = '11';
      `);
      await applyBars(page, `
        form.querySelector('[name="gantt.legend.visible"]').checked = false;
        form.querySelector('[name="gantt.legend.position"]').value = 'bottom';
        form.querySelector('[name="gantt.sightLines.beforeSummaries"]').checked = false;
        form.querySelector('[name="gantt.sightLines.rowInterval"]').value = '0';
        form.querySelector('[name="gantt.sightLines.minorVertical"]').checked = false;
        form.querySelector('[name="bar.critical.filter"]').value = 'critical';
        form.querySelector('[name="bar.critical.visible"]').checked = true;
      `);
      const final = await measure(page);
      verifyBase(final, `${label} final`);
      assert(final.legend === null, `${label}: legend remained visible after reset`);
      assert(final.sight.majorHorizontal === 0 && final.sight.minorVertical === 0, `${label}: sight lines remained after reset`);
      cells.push({
        viewport: { width: 1366, height: 768 },
        locale,
        baseline,
        legendTop: { position: legendTop.legend.position, items: legendTop.legend.items, kinds: legendTop.legend.kinds },
        legendBottom: { position: legendBottom.legend.position, items: legendBottom.legend.items, chartGap: +(legendBottom.legend.rect.top - legendBottom.legend.chart.bottom).toFixed(1) },
        sight: sight.sight,
        filtered: { bars: filtered.bars, barsByKind: filtered.barsByKind },
        hidden: { bars: hidden.bars, barsByKind: hidden.barsByKind, legendItems: hidden.legend?.items ?? null },
        scales: scaleFacts,
        zoom: { out: zoomedOut.scale, in: zoomedIn.scale, fitted: fitted.scale, fitContentWidth: fitted.contentWidth, fitPaneWidth: fitted.chartClientWidth },
        collapse: { collapsedRows: collapsed.rows.gantt, expandedRows: expanded.rows.gantt },
        final,
      });
    }

    assert(exceptions.length === 0, `runtime exceptions: ${exceptions.join(" | ")}`);
    assert(consoleErrors.length === 0, `console errors: ${consoleErrors.join(" | ")}`);
    assert(apiFailures.length === 0, `HTTP 5xx responses: ${JSON.stringify(apiFailures)}`);
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(outDir, "gantt-options-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(durableDir, "gantt-options-v26.json"), JSON.stringify(report, null, 2));
    log(`\nPASS ${cells.length} Gantt-option cells at ${testedCodeSha}`);
  } catch (error) {
    report.finishedAt = new Date().toISOString();
    report.error = String(error && error.stack ? error.stack : error);
    writeFileSync(join(outDir, "gantt-options-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(durableDir, "gantt-options-v26.json"), JSON.stringify(report, null, 2));
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
