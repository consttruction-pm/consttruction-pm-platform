#!/usr/bin/env node
/**
 * Capture the classic workbench theme from the running preview at the three
 * delivery viewports and record the computed chrome colours so the visual
 * comparison is backed by measured values.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4174 node e2e/capture-theme.mjs
 */

import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4174";
const outDir = join(artifactsDir, "preview-live");
mkdirSync(outDir, { recursive: true });

const themeSnapshot = `(() => {
  const style = (selector) => {
    const element = document.querySelector(selector);
    return element ? getComputedStyle(element) : null;
  };
  const toolbarGroup = (id) => {
    const button = document.querySelector('[data-toolbar-group="' + id + '"] .cp-icon');
    return button ? getComputedStyle(button).color : null;
  };
  const titlebar = style(".cp-p6 .cp-titlebar");
  const menubar = style(".cp-p6 .cp-menubar");
  const toolbar = style(".cp-p6 .cp-toolbar");
  const statusbar = style(".cp-statusbar");
  const header = style("#cp-activity-grid thead th");
  const summary = style('#cp-activity-grid tbody tr[data-activity-kind="summary"] td');
  const selected = style("#cp-activity-grid tbody tr.is-selected td");
  const task = style("#cp-gantt .cp-gantt-bar-task");
  const milestone = style("#cp-gantt .cp-gantt-bar-milestone");
  return {
    titlebar: titlebar ? { background: titlebar.backgroundColor, color: titlebar.color } : null,
    menubar: menubar ? { background: menubar.backgroundColor } : null,
    toolbar: toolbar ? { background: toolbar.backgroundImage } : null,
    statusbar: statusbar ? { background: statusbar.backgroundColor } : null,
    header: header ? { background: header.backgroundImage, color: header.color } : null,
    summary: summary ? { background: summary.backgroundColor, color: summary.color, weight: summary.fontWeight } : null,
    selected: selected ? { background: selected.backgroundColor, color: selected.color } : null,
    toolbarIcons: {
      file: toolbarGroup("file"), edit: toolbarGroup("edit"), layout: toolbarGroup("layout"),
      view: toolbarGroup("view"), project: toolbarGroup("project"),
      activities: toolbarGroup("activities"), tools: toolbarGroup("tools"),
    },
    summaryRows: document.querySelectorAll('#cp-activity-grid tbody tr[data-activity-kind="summary"]').length,
    taskBar: (() => {
      const element = document.querySelector("#cp-gantt .cp-gantt-bar-task");
      return element ? {
        background: getComputedStyle(element).backgroundColor,
        border: getComputedStyle(element).borderColor,
        label: element.querySelector(".cp-gantt-bar-label")?.textContent?.trim() ?? null,
      } : null;
    })(),
    milestoneBar: (() => {
      const element = document.querySelector("#cp-gantt .cp-gantt-bar-milestone");
      return element ? { background: getComputedStyle(element).backgroundColor, border: getComputedStyle(element).borderColor } : null;
    })(),
    rowIcons: document.querySelectorAll("#cp-activity-grid .cp-p6-activity-icon").length,
    showIconsAttr: document.querySelector("#cp-activity-grid")?.closest(".cp-p6-workspace")?.getAttribute("data-show-icons") ?? null,
    iconCells: document.querySelectorAll("#cp-activity-grid .cp-p6-activity-cell").length,
    firstCellHtml: document.querySelector("#cp-activity-grid tbody tr td")?.innerHTML?.slice(0, 260) ?? null,
    columnIds: [...document.querySelectorAll("#cp-activity-grid tbody tr:first-child td[data-column-id]")].map((cell) => cell.getAttribute("data-column-id")),
  };
})()`;

async function main() {
  const health = await waitForHttp(`${baseUrl}/preview/health`, 20000);
  if (!(health.status === "ok" || health.status === 200)) throw new Error(`preview health ${health.status}`);

  const chrome = await launchChrome();
  const page = new Page(chrome.cdp);
  const report = { baseUrl, gitHead: gitHead(), capturedAt: new Date().toISOString(), sizes: {}, theme: null };
  try {
    await page.initialize();
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
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

    // Re-apply the delivered defaults once so the persisted project layout
    // carries the classic table font, icons and bar palette.
    await page.click('[data-desktop-command="dialog.user-preferences"]');
    await page.click("[data-dialog-default]");
    await sleep(800);

    // Capture the LTR English workspace for a like-for-like theme comparison.
    await page.evaluate(`(() => {
      const select = document.querySelector("[data-workspace-language]");
      if (!select) return false;
      select.value = "en";
      select.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    })()`);
    await sleep(900);

    // Select the first task row so the capture shows the classic blue selection.
    await page.evaluate(`(() => {
      const row = document.querySelector('#cp-activity-grid tbody tr:not([data-activity-kind="summary"])');
      if (!row) return false;
      row.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      return true;
    })()`);
    await sleep(400);

    report.theme = await page.evaluate(themeSnapshot);

    for (const [width, height] of [[1280, 720], [1440, 900], [1920, 1080]]) {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
      await sleep(500);
      const name = `preview-live/theme-${width}x${height}.png`;
      await page.screenshot(name);
      report.sizes[`${width}x${height}`] = name;
      process.stdout.write(`captured ${name}\n`);
    }

    // A dense crop for close comparison of table + gantt typography.
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 2, mobile: false });
    await sleep(500);
    await page.screenshot("preview-live/theme-table-zoom.png");
    report.sizes.zoom = "preview-live/theme-table-zoom.png";
    process.stdout.write("captured preview-live/theme-table-zoom.png\n");

    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
    await page.click('[data-desktop-command="dialog.bars"]');
    await sleep(400);
    await page.screenshot("preview-live/theme-dialog-bars.png");
    report.sizes.dialogBars = "preview-live/theme-dialog-bars.png";
    process.stdout.write("captured preview-live/theme-dialog-bars.png\n");
    await page.click("[data-dialog-cancel]");

    await page.click('[data-desktop-command="dialog.font-row"]');
    await sleep(400);
    await page.screenshot("preview-live/theme-dialog-font-row.png");
    report.sizes.dialogFontRow = "preview-live/theme-dialog-font-row.png";
    process.stdout.write("captured preview-live/theme-dialog-font-row.png\n");
    await page.click("[data-dialog-cancel]");
  } finally {
    writeFileSync(join(outDir, "theme-capture.json"), JSON.stringify(report, null, 2));
    page.cdp.close();
    chrome.cdp.close();
    await chrome.stop();
  }
  process.stdout.write(`Theme capture: ${join(outDir, "theme-capture.json")}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error && error.stack ? error.stack : error}\n`);
  process.exit(1);
});
