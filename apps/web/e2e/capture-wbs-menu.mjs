#!/usr/bin/env node
/**
 * Capture the real WBS hierarchy bands, the collapse behaviour shared by the
 * activity table and the Gantt chart, and the activity context menu from the
 * running preview.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4174 node e2e/capture-wbs-menu.mjs
 */

import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4174";
const outDir = join(artifactsDir, "wbs-live");
mkdirSync(outDir, { recursive: true });

const metricsSnapshot = `(() => {
  const rect = (element) => {
    if (!element) return null;
    const box = element.getBoundingClientRect();
    return { width: Math.round(box.width * 10) / 10, height: Math.round(box.height * 10) / 10, top: Math.round(box.top), left: Math.round(box.left) };
  };
  const bands = [...document.querySelectorAll(".cp-p6-wbs-band")].map((row) => {
    const cell = row.querySelector("td");
    const toggle = row.querySelector("[data-wbs-toggle]");
    const style = getComputedStyle(row);
    return {
      wbsId: row.dataset.wbsRow,
      level: Number(row.dataset.wbsLevel),
      depth: Number(row.dataset.wbsDepth),
      collapsed: row.dataset.wbsCollapsed === "true",
      bandColor: style.getPropertyValue("--cp-wbs-band").trim(),
      cellBackground: cell ? getComputedStyle(cell).backgroundColor : null,
      firstCellShadow: cell ? getComputedStyle(cell).boxShadow : null,
      label: row.getAttribute("aria-label"),
      toggle: toggle ? toggle.textContent.trim() : null,
      toggleSize: rect(toggle),
    };
  });
  const activities = [...document.querySelectorAll('#cp-activity-grid tbody tr[data-activity-id]')].map((row) => ({
    id: row.dataset.activityId,
    depth: Number(row.dataset.wbsDepth),
    indent: row.querySelector(".cp-p6-indent")?.getBoundingClientRect().width ?? 0,
    selected: row.getAttribute("aria-selected") === "true",
  }));
  const ganttGroups = [...document.querySelectorAll("#cp-gantt .cp-gantt-group-row")].map((row) => ({
    wbsId: row.dataset.ganttWbsId,
    depth: Number(row.dataset.ganttDepth),
    background: getComputedStyle(row).backgroundColor,
  }));
  const ganttActivities = [...document.querySelectorAll("#cp-gantt [data-gantt-activity-id]")].map((row) => row.dataset.ganttActivityId);
  const summaryBars = [...document.querySelectorAll("#cp-gantt [data-gantt-summary]")].map((bar) => {
    const style = getComputedStyle(bar);
    return { wbsId: bar.dataset.ganttWbsId, background: style.backgroundColor, border: style.borderColor, width: Math.round(bar.getBoundingClientRect().width) };
  });
  const taskBar = document.querySelector("#cp-gantt .cp-gantt-bar-task");
  const menu = document.querySelector("[data-activity-context-menu]");
  const workspace = document.querySelector(".cp-p6-workspace");
  const menuRect = rect(menu);
  const workspaceRect = rect(workspace);
  const menuLastItem = menu ? [...menu.querySelectorAll("[data-activity-menu-command]")].pop() : null;
  const menuItems = menu
    ? [...menu.querySelectorAll("[data-activity-menu-command]")].map((item) => {
        const style = getComputedStyle(item);
        return {
          command: item.dataset.activityMenuCommand,
          label: item.querySelector(".cp-context-text")?.textContent?.trim() ?? null,
          shortcut: item.querySelector(".cp-context-shortcut")?.textContent?.trim() ?? null,
          disabled: item.disabled,
          reason: item.getAttribute("title") || null,
          height: rect(item)?.height ?? null,
          color: style.color,
          opacity: style.opacity,
        };
      })
    : [];
  return {
    locale: document.documentElement.lang,
    direction: getComputedStyle(document.body).direction,
    bands,
    activities,
    ganttGroups,
    ganttActivities,
    summaryBars,
    taskBar: taskBar ? { background: getComputedStyle(taskBar).backgroundColor, border: getComputedStyle(taskBar).borderColor, width: Math.round(taskBar.getBoundingClientRect().width) } : null,
    menu: menu ? {
      hidden: menu.hidden,
      rect: menuRect,
      workspaceRect,
      fullyVisible: Boolean(menuRect && workspaceRect && menuRect.top >= workspaceRect.top && menuRect.top + menuRect.height <= workspaceRect.top + workspaceRect.height),
      lastItem: menuLastItem ? { command: menuLastItem.dataset.activityMenuCommand, rect: rect(menuLastItem) } : null,
      items: menuItems,
    } : null,
  };
})()`;

async function setViewport(page, width, height, scale = 1) {
  await page.cdp.send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: scale, mobile: false });
  await sleep(450);
}

async function openContextMenu(page, selector) {
  return page.evaluate(`(() => {
    const row = document.querySelector(${JSON.stringify(selector)});
    if (!row) return false;
    row.scrollIntoView({ block: "center", inline: "nearest" });
    const box = row.getBoundingClientRect();
    row.dispatchEvent(new MouseEvent("contextmenu", {
      bubbles: true,
      cancelable: true,
      button: 2,
      clientX: Math.round(box.left + Math.min(220, box.width / 2)),
      clientY: Math.round(box.top + box.height / 2),
    }));
    return true;
  })()`);
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
    expanded: null,
    collapsed: null,
    contextMenu: null,
    rtl: null,
  };
  try {
    await page.initialize();
    await setViewport(page, 1280, 720);
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

    // English LTR is the comparison baseline.
    await page.evaluate(`(() => {
      const select = document.querySelector("[data-workspace-language]");
      if (!select) return false;
      select.value = "en";
      select.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    })()`);
    await sleep(900);
    if (!(await page.evaluate(`document.querySelectorAll(".cp-p6-wbs-band").length`))) {
      await page.click('[data-desktop-command="edit.group-wbs"]');
      await page.waitForSelector(".cp-p6-wbs-band", "wbs bands");
      await sleep(700);
    }

    report.expanded = await page.evaluate(metricsSnapshot);

    for (const [width, height] of [[1280, 720], [1440, 900], [1920, 1080]]) {
      await setViewport(page, width, height);
      const name = `wbs-live/expanded-${width}x${height}.png`;
      await page.screenshot(name);
      report.screenshots[`expanded-${width}x${height}`] = name;
    }

    // Collapse one real branch and verify the table rows and Gantt bars of that
    // branch disappear together in the same render.
    await setViewport(page, 1280, 720);
    const branch = await page.evaluate(`(() => {
      const table = [...document.querySelectorAll("#cp-activity-grid tbody tr")];
      const index = table.findIndex((row) => row.dataset.wbsRow && Number(row.dataset.wbsDepth) >= 1 && row.dataset.wbsCollapsed !== "true");
      if (index < 0) return null;
      const row = table[index];
      const depth = Number(row.dataset.wbsDepth);
      const activityIds = [];
      const nestedWbs = [];
      for (let i = index + 1; i < table.length; i += 1) {
        const next = table[i];
        if (next.dataset.wbsRow) {
          if (Number(next.dataset.wbsDepth) <= depth) break;
          nestedWbs.push(next.dataset.wbsRow);
        } else if (next.dataset.activityId) {
          activityIds.push(next.dataset.activityId);
        }
      }
      return { wbsId: row.dataset.wbsRow, depth, activityIds, nestedWbs };
    })()`);
    if (!branch) throw new Error("NO_COLLAPSIBLE_WBS_BRANCH");
    const before = await page.evaluate(metricsSnapshot);
    await page.evaluate(`(() => {
      const toggle = document.querySelector(${JSON.stringify(`[data-wbs-toggle="${branch.wbsId}"]`)});
      if (!toggle) return false;
      toggle.click();
      return true;
    })()`);
    await sleep(700);
    const after = await page.evaluate(metricsSnapshot);
    const remainingTable = new Set(after.activities.map((row) => row.id));
    const remainingGantt = new Set(after.ganttActivities);
    report.collapsed = {
      wbsId: branch.wbsId,
      depth: branch.depth,
      childActivities: branch.activityIds,
      nestedWbs: branch.nestedWbs,
      beforeCounts: { bands: before.bands.length, activities: before.activities.length, ganttRows: before.ganttActivities.length, summaryBars: before.summaryBars.length },
      afterCounts: { bands: after.bands.length, activities: after.activities.length, ganttRows: after.ganttActivities.length, summaryBars: after.summaryBars.length },
      tableChildrenRemoved: branch.activityIds.every((id) => !remainingTable.has(id)),
      ganttChildrenRemoved: branch.activityIds.every((id) => !remainingGantt.has(id)),
      collapsedBand: after.bands.find((row) => row.wbsId === branch.wbsId) ?? null,
      unrelatedActivitiesStillVisible: after.activities.length > 0,
    };
    await page.screenshot("wbs-live/collapsed-1280x720.png");
    report.screenshots.collapsed = "wbs-live/collapsed-1280x720.png";

    // Restore the expanded tree for the context-menu capture.
    await page.click("[data-wbs-expand-all]");
    await sleep(700);

    // Right-click an activity row.
    await openContextMenu(page, "#cp-activity-grid tbody tr[data-activity-id]");
    await page.waitFor(
      `(() => { const menu = document.querySelector("[data-activity-context-menu]"); return Boolean(menu) && !menu.hidden; })()`,
      "activity context menu",
    );
    await sleep(250);
    report.contextMenu = await page.evaluate(metricsSnapshot);
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 2, mobile: false });
    await sleep(450);
    await page.screenshot("wbs-live/context-menu-zoom.png");
    report.screenshots.contextMenuZoom = "wbs-live/context-menu-zoom.png";
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
    await sleep(350);
    await page.screenshot("wbs-live/context-menu-1280x720.png");
    report.screenshots.contextMenu = "wbs-live/context-menu-1280x720.png";

    // Escape closes the menu and the table keeps working.
    await page.evaluate(`(() => {
      const menu = document.querySelector("[data-activity-context-menu]");
      const target = menu?.querySelector("[data-activity-menu-command]") ?? document.querySelector("#cp-activity-grid tbody tr[data-activity-id]");
      target?.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));
      return true;
    })()`);
    await sleep(300);
    report.contextMenu.closedByEscape = await page.evaluate(`(() => {
      const menu = document.querySelector("[data-activity-context-menu]");
      return !menu || menu.hidden;
    })()`);

    // Persian RTL check for the same bands and menu.
    await page.evaluate(`(() => {
      const select = document.querySelector("[data-workspace-language]");
      if (!select) return false;
      select.value = "fa";
      select.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    })()`);
    await sleep(1200);
    await openContextMenu(page, "#cp-activity-grid tbody tr[data-activity-id]");
    await page.waitFor(
      `(() => { const menu = document.querySelector("[data-activity-context-menu]"); return Boolean(menu) && !menu.hidden; })()`,
      "persian activity context menu",
    );
    await sleep(300);
    report.rtl = await page.evaluate(metricsSnapshot);
    await page.screenshot("wbs-live/context-menu-rtl-1280x720.png");
    report.screenshots.contextMenuRtl = "wbs-live/context-menu-rtl-1280x720.png";
  } finally {
    writeFileSync(join(outDir, "wbs-menu-capture.json"), JSON.stringify(report, null, 2));
    page.cdp.close();
    chrome.cdp.close();
    await chrome.stop();
  }
  process.stdout.write(`WBS capture: ${join(outDir, "wbs-menu-capture.json")}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error && error.stack ? error.stack : error}\n`);
  process.exit(1);
});
