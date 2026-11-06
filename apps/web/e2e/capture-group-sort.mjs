#!/usr/bin/env node
/**
 * Prove the Group and Sort dialog drives the table order with a real
 * multi-level sort plan: status descending, then activity name ascending.
 * Captures the dialog, the sorted table and the restored WBS order.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4174 node e2e/capture-group-sort.mjs
 */

import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4174";
const outDir = join(artifactsDir, "group-sort-live");
mkdirSync(outDir, { recursive: true });

const tableState = `(() => {
  const header = [...document.querySelectorAll("#cp-activity-grid thead th")].map((cell) => cell.textContent.trim());
  const sequence = [...document.querySelectorAll("#cp-activity-grid tbody tr")].map((row) => {
    if (row.dataset.activityId) {
      return {
        kind: "activity",
        id: row.dataset.activityId,
        cells: [...row.querySelectorAll("td")].map((cell) => cell.textContent.trim()),
      };
    }
    return { kind: "band", label: [...row.querySelectorAll("th, td")].map((cell) => cell.textContent.trim()).join(" ").trim() };
  });
  const gantt = [...document.querySelectorAll("#cp-gantt [data-gantt-activity-id]")].map((row) => row.dataset.ganttActivityId);
  return {
    header,
    sequence,
    ids: sequence.filter((row) => row.kind === "activity").map((row) => row.id),
    ganttIds: gantt,
    counts: { table: sequence.filter((row) => row.kind === "activity").length, gantt: gantt.length },
  };
})()`;

const dialogState = `(() => {
  const dialog = document.querySelector('[data-desktop-dialog="group-sort"]');
  if (!dialog) return null;
  const group = dialog.querySelector('select[name="groupBy"]');
  const rows = [...dialog.querySelectorAll(".cp-sort-row")].map((row) => {
    const field = row.querySelector('select[name^="sort.field."]');
    const direction = row.querySelector('select[name^="sort.direction."]');
    return {
      field: field ? field.value : null,
      direction: direction ? direction.value : null,
      options: field ? [...field.querySelectorAll("option")].map((option) => ({ value: option.value, label: option.textContent.trim() })) : [],
      label: row.querySelector("label > span")?.textContent.trim() ?? null,
    };
  });
  const box = dialog.getBoundingClientRect();
  return {
    open: dialog.hasAttribute("open"),
    group: group ? group.value : null,
    rows,
    rowCount: rows.length,
    rect: { width: Math.round(box.width), height: Math.round(box.height), top: Math.round(box.top) },
    viewport: { width: window.innerWidth, height: window.innerHeight },
    fitsViewport: box.top >= 0 && box.bottom <= window.innerHeight + 1 && box.left >= 0 && box.right <= window.innerWidth + 1,
  };
})()`;

async function openGroupSort(page) {
  await page.evaluate(`(() => {
    const button = [...document.querySelectorAll('[data-desktop-command="dialog.group-sort"]')]
      .find((item) => item.getClientRects().length > 0);
    if (!button) return false;
    button.click();
    return true;
  })()`);
  await page.waitForSelector('[data-desktop-dialog="group-sort"][open]', "group and sort dialog", 4000);
  await sleep(300);
}

async function submit(page) {
  await page.evaluate(`(() => {
    const dialog = document.querySelector('[data-desktop-dialog="group-sort"]');
    dialog?.querySelector("[data-dialog-ok]")?.click();
    return true;
  })()`);
  await page.waitFor(
    `(() => { const dialog = document.querySelector('[data-desktop-dialog="group-sort"]'); return !dialog || !dialog.hasAttribute("open"); })()`,
    "group and sort dialog closed",
    4000,
  );
  await sleep(900);
}

async function setSort(page, index, field, direction) {
  if (field !== null) {
    const ok = await page.evaluate(`(() => {
      const select = document.querySelector('[data-desktop-dialog="group-sort"] select[name="sort.field.${index}"]');
      if (!select) return false;
      select.value = ${JSON.stringify(field)};
      if (select.value !== ${JSON.stringify(field)}) return false;
      select.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    })()`);
    if (!ok) throw new Error(`could not set sort field ${index} to ${field}`);
  }
  const ok = await page.evaluate(`(() => {
    const select = document.querySelector('[data-desktop-dialog="group-sort"] select[name="sort.direction.${index}"]');
    if (!select) return false;
    select.value = ${JSON.stringify(direction)};
    select.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  if (!ok) throw new Error(`could not set sort direction ${index}`);
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
    multiLevel: null,
    restored: null,
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

    report.baseline = await page.evaluate(tableState);

    // 1. The dialog itself: group value and three ordered sort rows.
    await openGroupSort(page);
    report.dialog = await page.evaluate(dialogState);
    await page.screenshot("group-sort-live/group-sort-dialog-1280x720.png");
    report.screenshots.dialog = "group-sort-live/group-sort-dialog-1280x720.png";
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 2, mobile: false });
    await sleep(300);
    await page.screenshot("group-sort-live/group-sort-dialog-zoom.png");
    report.screenshots.dialogZoom = "group-sort-live/group-sort-dialog-zoom.png";
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
    await sleep(250);

    // 2. Multi-level plan: status descending, then activity name ascending.
    const options = report.dialog?.rows?.[0]?.options ?? [];
    const statusOption = options.find((option) => /status/i.test(option.label))
      ?? options.find((option) => /status/i.test(option.value));
    const nameOption = options.find((option) => /name/i.test(option.label))
      ?? options.find((option) => /name/i.test(option.value));
    if (!statusOption || !nameOption) {
      throw new Error(`sort fields not found in ${JSON.stringify(options)}`);
    }
    await setSort(page, 0, statusOption.value, "desc");
    await setSort(page, 1, nameOption.value, "asc");
    await setSort(page, 2, "", "asc");
    await submit(page);
    report.multiLevel = await page.evaluate(tableState);
    report.multiLevel.plan = [
      { field: statusOption.value, label: statusOption.label, direction: "desc" },
      { field: nameOption.value, label: nameOption.label, direction: "asc" },
    ];
    await page.screenshot("group-sort-live/group-sort-multilevel-1280x720.png");
    report.screenshots.multiLevel = "group-sort-live/group-sort-multilevel-1280x720.png";

    // 3. Restore the default WBS order.
    await openGroupSort(page);
    await setSort(page, 0, "wbs", "asc");
    await setSort(page, 1, "", "asc");
    await setSort(page, 2, "", "asc");
    await submit(page);
    report.restored = await page.evaluate(tableState);
    await page.screenshot("group-sort-live/group-sort-restored-1280x720.png");
    report.screenshots.restored = "group-sort-live/group-sort-restored-1280x720.png";
  } finally {
    writeFileSync(join(outDir, "group-sort-capture.json"), `${JSON.stringify(report, null, 2)}\n`);
    await chrome.close();
  }

  console.log(JSON.stringify({
    gitHead: report.gitHead,
    dialog: report.dialog,
    baseline: report.baseline?.ids,
    multiLevel: report.multiLevel?.ids,
    plan: report.multiLevel?.plan,
    restored: report.restored?.ids,
    ganttMulti: report.multiLevel?.ganttIds,
    ganttRestored: report.restored?.ganttIds,
  }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
