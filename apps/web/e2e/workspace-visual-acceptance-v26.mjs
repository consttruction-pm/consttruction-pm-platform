#!/usr/bin/env node
/**
 * Visual acceptance for the Version 26 Activities workspace.
 *
 * Captures the real Activities window at 1280x720, 1366x768 and 1920x1080 in
 * both English (LTR) and Persian (RTL), and asserts the properties the desktop
 * reference requires: no page-level clipping, a command bar that stays inside
 * its strip, the details pane inside the viewport, table/Gantt row alignment,
 * and bar labels that never escape the plotted timeline content at the right
 * edge. Also switches to Reports and back to prove window switching keeps the
 * shell intact.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 \
 *   CUBI_TESTED_CODE_SHA=<code commit> \
 *   node e2e/workspace-visual-acceptance-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "visual-acceptance-v26");
const durableDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", "visual-acceptance-v26-2026-11-12");
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
  const file = `visual-acceptance-v26/${name}.png`;
  await page.screenshot(file);
  copyFileSync(join(artifactsDir, file), join(durableDir, `${name}.png`));
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
  await sleep(1000);
}

async function openCommand(page, command) {
  const clicked = await page.evaluate(`(() => {
    const buttons = [...document.querySelectorAll('[data-desktop-command=${JSON.stringify(command)}]')];
    const button = buttons.find((item) => item.getClientRects().length > 0);
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `command button not visible: ${command}`);
  await sleep(500);
}

async function openDesktopMenu(page, menuId) {
  const found = await page.evaluate(`(() => {
    const trigger = document.querySelector('[data-desktop-menu=${JSON.stringify(menuId)}]');
    if (!trigger) return false;
    if (trigger.getAttribute("aria-expanded") !== "true") trigger.click();
    return true;
  })()`);
  assert(found, `${menuId} menu trigger is missing`);
  await page.waitFor(
    `document.querySelector('[data-desktop-popup=${JSON.stringify(menuId)}]')?.hidden === false`,
    `${menuId} popup open`,
  );
  await sleep(200);
}

async function clickDesktopItem(page, itemId) {
  const clicked = await page.evaluate(`(() => {
    const item = document.querySelector('[data-desktop-item=${JSON.stringify(itemId)}]');
    if (!item || item.hasAttribute("disabled")) return false;
    item.click();
    return true;
  })()`);
  assert(clicked, `${itemId} is missing or disabled`);
}

const measurement = `(() => {
  const rect = (element) => {
    if (!element) return null;
    const r = element.getBoundingClientRect();
    return { left: +r.left.toFixed(1), top: +r.top.toFixed(1), right: +r.right.toFixed(1), bottom: +r.bottom.toFixed(1), width: +r.width.toFixed(1), height: +r.height.toFixed(1) };
  };
  const workspace = document.querySelector(".cp-workspace");
  const toolbar = document.querySelector(".cp-toolbar");
  const toolbarScroll = document.querySelector(".cp-toolbar-scroll");
  const overflowButton = document.querySelector("[data-toolbar-overflow]");
  const details = document.querySelector("#cp-details");
  const tableRows = [...document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]")];
  const ganttRows = [...document.querySelectorAll("#cp-gantt [data-gantt-activity-id]")];
  const tableBody = document.querySelector("#cp-activity-grid tbody");
  const ganttBody = document.querySelector("#cp-gantt [data-gantt-body]");
  const board = document.querySelector("#cp-gantt .cp-gantt-board");
  const track = document.querySelector("#cp-gantt .cp-gantt-track");
  const contentWidth = board ? Number.parseFloat(getComputedStyle(board).getPropertyValue("--cp-gantt-content-width")) : 0;
  // The track is at least the zoom's content width and stretches to fill a
  // wider pane, so the rendered track width is the real plotting boundary.
  const trackWidth = track ? track.getBoundingClientRect().width : contentWidth;
  const trackLeft = track ? track.getBoundingClientRect().left : 0;
  const labels = [...document.querySelectorAll("#cp-gantt .cp-gantt-bar-label")];
  const clippedLabels = labels.filter((label) => {
    const r = label.getBoundingClientRect();
    return r.right - trackLeft > trackWidth + 1 || r.left - trackLeft < -1;
  }).map((label) => ({ text: label.textContent, position: label.dataset.ganttLabelPosition, left: +(label.getBoundingClientRect().left - trackLeft).toFixed(1), right: +(label.getBoundingClientRect().right - trackLeft).toFixed(1) }));
  const unresolvedEdgeLabels = [...document.querySelectorAll("#cp-gantt .cp-gantt-bar, #cp-gantt .cp-gantt-summary-bar")].filter((bar) => {
    const label = bar.querySelector(".cp-gantt-bar-label");
    if (!label) return false;
    const left = Number.parseFloat(bar.style.left);
    const width = Number.parseFloat(bar.style.width);
    if (!Number.isFinite(left) || !Number.isFinite(width)) return false;
    if (left + width < 78) return false;
    return ["right", "above", "below"].includes(label.dataset.ganttLabelPosition);
  }).map((bar) => ({ kind: bar.dataset.ganttBarKind ?? "summary", label: bar.querySelector(".cp-gantt-bar-label")?.textContent ?? null }));
  const pairs = tableRows.slice(0, Math.min(tableRows.length, ganttRows.length)).map((row, index) => ({
    table: +row.getBoundingClientRect().height.toFixed(1),
    gantt: +ganttRows[index].getBoundingClientRect().height.toFixed(1),
  }));
  const gridActionStrips = [...document.querySelectorAll(".cp-p6-grid-actions")].map((strip) => {
    const r = strip.getBoundingClientRect();
    const head = strip.parentElement?.getBoundingClientRect();
    return {
      rect: rect(strip),
      insideHead: Boolean(head) && r.left >= head.left - 1 && r.right <= head.right + 1,
      buttonsOutside: [...strip.querySelectorAll("button")].filter((button) => {
        const b = button.getBoundingClientRect();
        return b.right > r.right + 1 || b.left < r.left - 1;
      }).length,
    };
  });
  return {
    viewport: { width: window.innerWidth, height: window.innerHeight },
    lang: document.documentElement.lang,
    dir: workspace?.getAttribute("dir") ?? getComputedStyle(document.body).direction,
    activeMenu: workspace?.dataset.activeMenu ?? null,
    documentScrollWidth: document.documentElement.scrollWidth,
    bodyScrollWidth: document.body.scrollWidth,
    toolbar: toolbar ? {
      rect: rect(toolbar),
      scrollWidth: toolbarScroll?.scrollWidth ?? 0,
      clientWidth: toolbarScroll?.clientWidth ?? 0,
      overflowControlVisible: Boolean(overflowButton && overflowButton.getClientRects().length),
    } : null,
    gridActionStrips,
    details: rect(details),
    detailsVisible: Boolean(details && details.getClientRects().length),
    rows: { table: tableRows.length, gantt: ganttRows.length },
    bands: document.querySelectorAll(".cp-p6-wbs-band").length,
    ganttGroups: document.querySelectorAll("#cp-gantt .cp-gantt-group-row").length,
    rowHeightMismatch: pairs.filter((pair) => Math.abs(pair.table - pair.gantt) > 1).length,
    firstRowOffset: tableRows.length && ganttRows.length && tableBody
      ? {
          table: +(tableRows[0].getBoundingClientRect().top - tableBody.getBoundingClientRect().top).toFixed(1),
          gantt: +(ganttRows[0].getBoundingClientRect().top - (ganttBody ? ganttBody.getBoundingClientRect().top : 0)).toFixed(1),
        }
      : null,
    labels: labels.length,
    clippedLabels,
    unresolvedEdgeLabels,
    bars: document.querySelectorAll("#cp-gantt [data-gantt-bar-kind], #cp-gantt [data-gantt-summary]").length,
  };
})()`;

async function measure(page) {
  return page.evaluate(measurement);
}

function verify(state, label) {
  assert(state.activeMenu === "schedule", `${label}: Activities is not the active window (${state.activeMenu})`);
  assert(state.detailsVisible, `${label}: Activity Details pane is not visible`);
  assert(state.rows.table === state.rows.gantt && state.rows.table > 0, `${label}: table/Gantt row counts differ (${state.rows.table}/${state.rows.gantt})`);
  assert(state.bands > 0 && state.ganttGroups > 0, `${label}: WBS bands are missing (${state.bands}/${state.ganttGroups})`);
  assert(state.rowHeightMismatch === 0, `${label}: ${state.rowHeightMismatch} table/Gantt row height mismatches`);
  assert(state.firstRowOffset && Math.abs(state.firstRowOffset.table - state.firstRowOffset.gantt) <= 1, `${label}: first row offsets differ ${JSON.stringify(state.firstRowOffset)}`);
  assert(state.documentScrollWidth <= state.viewport.width + 1, `${label}: page overflows horizontally (${state.documentScrollWidth} > ${state.viewport.width})`);
  assert(state.bodyScrollWidth <= state.viewport.width + 1, `${label}: body overflows horizontally (${state.bodyScrollWidth} > ${state.viewport.width})`);
  assert(state.toolbar && state.toolbar.rect.right <= state.viewport.width + 1 && state.toolbar.rect.bottom <= state.viewport.height + 1, `${label}: toolbar is outside the viewport ${JSON.stringify(state.toolbar)}`);
  if (state.toolbar.scrollWidth > state.toolbar.clientWidth + 1) {
    assert(state.toolbar.overflowControlVisible, `${label}: toolbar overflows without a More control (${state.toolbar.scrollWidth} > ${state.toolbar.clientWidth})`);
  }
  assert(state.gridActionStrips.every((strip) => strip.rect.right <= state.viewport.width + 1 && strip.insideHead && strip.buttonsOutside === 0), `${label}: a grid command strip overflows ${JSON.stringify(state.gridActionStrips)}`);
  const details = state.details;
  assert(details && details.right <= state.viewport.width + 1 && details.bottom <= state.viewport.height + 1, `${label}: details pane is outside the viewport ${JSON.stringify(details)}`);
  assert(details.height > 40 && details.width > 100, `${label}: details pane is collapsed (${details.width}x${details.height})`);
  assert(state.clippedLabels.length === 0, `${label}: clipped bar labels ${JSON.stringify(state.clippedLabels)}`);
  assert(state.unresolvedEdgeLabels.length === 0, `${label}: edge labels not resolved ${JSON.stringify(state.unresolvedEdgeLabels)}`);
}

async function ensureActivitiesLayout(page) {
  const detailsVisible = await page.evaluate(`(() => { const details = document.querySelector("#cp-details"); return Boolean(details && details.getClientRects().length); })()`);
  if (!detailsVisible) {
    await openCommand(page, "view.toggle-details");
    await sleep(800);
  }
  const groups = await page.evaluate(`document.querySelectorAll(".cp-p6-wbs-band").length`);
  if (groups === 0) {
    await openCommand(page, "edit.group-wbs");
    await sleep(900);
  }
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
    contract: "cubi-workspace-visual-acceptance-v26.v1",
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
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
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
    await setLanguage(page, "en");
    await page.waitForSelector("#cp-gantt [data-gantt-activity-id]", "gantt rows");
    await ensureActivitiesLayout(page);

    for (const viewport of [{ width: 1280, height: 720 }, { width: 1366, height: 768 }, { width: 1920, height: 1080 }]) {
      for (const locale of ["en", "fa"]) {
        const label = `${viewport.width}x${viewport.height}-${locale}`;
        log(`\n[${label}]`);
        await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: viewport.width, height: viewport.height, deviceScaleFactor: 1, mobile: false });
        await sleep(500);
        await setLanguage(page, locale);
        await page.waitForSelector("#cp-gantt [data-gantt-activity-id]", "gantt rows");
        await ensureActivitiesLayout(page);
        const initial = await measure(page);
        assert(initial.dir === (locale === "fa" ? "rtl" : "ltr"), `${label}: direction is ${initial.dir}`);
        verify(initial, `${label} initial`);
        await capture(page, `activities-${label}`);

        const dialog = await (async () => {
          await openCommand(page, "view.fields");
          await page.waitForSelector("[data-p6-columns-dialog][open]", "columns dialog", 6000);
          await sleep(300);
          const box = await page.evaluate(`(() => {
            const dialog = document.querySelector("[data-p6-columns-dialog]");
            const r = dialog.getBoundingClientRect();
            return { left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height, viewport: { width: innerWidth, height: innerHeight } };
          })()`);
          assert(box.width > 200 && box.height > 150, `${label}: columns dialog is degenerate ${JSON.stringify(box)}`);
          assert(box.left >= -1 && box.top >= -1 && box.right <= box.viewport.width + 1 && box.bottom <= box.viewport.height + 1, `${label}: columns dialog is clipped ${JSON.stringify(box)}`);
          await capture(page, `columns-dialog-${label}`);
          await page.evaluate(`(() => { document.querySelector("[data-columns-cancel]")?.click(); return true; })()`);
          await page.waitFor(`(() => !document.querySelector("[data-p6-columns-dialog][open]"))`, `${label} columns dialog closed`, 5000);
          await sleep(400);
          return box;
        })();

        const beforeResize = await measure(page);
        await page.drag("[data-details-splitter]", 0, -30);
        await sleep(600);
        const afterResize = await measure(page);
        assert(Math.abs(afterResize.details.height - beforeResize.details.height) >= 10, `${label}: details splitter did not resize (${beforeResize.details.height} -> ${afterResize.details.height})`);
        verify(afterResize, `${label} after details resize`);
        await capture(page, `details-resized-${label}`);

        if (viewport.width === 1366 && locale === "en") {
          await openDesktopMenu(page, "tools");
          await clickDesktopItem(page, "tools.reports");
          await page.waitForSelector("[data-reports-page]", "reports window", 20000);
          await sleep(800);
          const reports = await page.evaluate(`(() => ({
            activeMenu: document.querySelector(".cp-workspace")?.dataset.activeMenu ?? null,
            heading: document.querySelector("[data-reports-page] .cp-register-toolbar strong")?.textContent?.trim() ?? null,
            fits: (() => { const r = document.querySelector("[data-reports-page]")?.getBoundingClientRect(); return Boolean(r && r.right <= innerWidth + 1 && r.bottom <= innerHeight + 1); })(),
          }))()`);
          assert(reports.activeMenu === "reports", `window switch did not activate Reports (${reports.activeMenu})`);
          assert(reports.heading, "Reports window heading is missing");
          assert(reports.fits, "Reports window exceeds the viewport");
          await capture(page, `window-switch-reports-${label}`);
          await page.evaluate(`(() => { document.querySelector('[data-window-open="schedule"]')?.click(); return true; })()`);
          await page.waitFor(`document.querySelector(".cp-workspace")?.dataset.activeMenu === "schedule"`, "Activities window restored", 10000);
          await sleep(900);
          const restored = await measure(page);
          verify(restored, `${label} after window switch`);
          await capture(page, `window-switch-back-${label}`);
          cells.push({ viewport, locale, initial, dialog, afterResize, windowSwitch: { reports, restored } });
        } else {
          cells.push({ viewport, locale, initial, dialog, afterResize });
        }
      }
    }

    // Leave the preview at the default English 1280 layout for later suites.
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
    await setLanguage(page, "en");
    await page.evaluate(`(() => {
      document.querySelector("[data-reset-details-split]")?.click();
      return true;
    })()`);
    await sleep(600);
    await capture(page, "final-state-1280x720-en");

    assert(exceptions.length === 0, `runtime exceptions: ${exceptions.join(" | ")}`);
    assert(apiFailures.length === 0, `HTTP 5xx responses: ${JSON.stringify(apiFailures)}`);
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(outDir, "workspace-visual-acceptance-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(durableDir, "workspace-visual-acceptance-v26.json"), JSON.stringify(report, null, 2));
    log(`\nPASS ${cells.length} visual cells at ${testedCodeSha}`);
  } catch (error) {
    report.finishedAt = new Date().toISOString();
    report.error = String(error && error.stack ? error.stack : error);
    writeFileSync(join(outDir, "workspace-visual-acceptance-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(durableDir, "workspace-visual-acceptance-v26.json"), JSON.stringify(report, null, 2));
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
