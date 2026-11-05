#!/usr/bin/env node
/**
 * Verify the delivered presentation work against the already-running preview
 * runtime (the persistent .preview database), not a throwaway fixture.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4174 node e2e/verify-live-preview.mjs
 *
 * The script logs in through the real login form, applies table presentation
 * and Gantt bar styles through the real dialogs, reloads to prove persistence,
 * restores the defaults and signs out. Screenshots land in
 * e2e/artifacts/preview-live/.
 */

import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4174";
const outDir = join(artifactsDir, "preview-live");
mkdirSync(outDir, { recursive: true });

const checks = [];
function check(name, condition, details = {}) {
  checks.push({ name, pass: Boolean(condition), ...details });
  process.stdout.write(`  ${condition ? "ok" : "FAIL"} ${name}\n`);
}

const tableSnapshot = `(() => {
  const table = document.querySelector("#cp-activity-grid table");
  if (!table) return null;
  const style = getComputedStyle(table);
  const rows = [...document.querySelectorAll("#cp-activity-grid tbody tr")];
  return {
    fontFamily: style.fontFamily,
    fontSize: style.fontSize,
    color: style.color,
    background: getComputedStyle(document.querySelector("#cp-activity-grid .cp-table-wrap") || table).backgroundColor,
    rowHeight: rows.length ? Math.round(rows[0].getBoundingClientRect().height) : null,
    lineNumbers: document.querySelectorAll("#cp-activity-grid .cp-p6-line-number").length,
    icons: document.querySelectorAll("#cp-activity-grid .cp-p6-activity-icon").length,
    dates: [...document.querySelectorAll('#cp-activity-grid tbody td[data-column-type="date"]')].map((cell) => cell.textContent.trim()).join("|"),
  };
})()`;

const ganttSnapshot = `(() => {
  const rows = [...document.querySelectorAll("#cp-gantt .cp-gantt-row")];
  const task = document.querySelector("#cp-gantt .cp-gantt-bar-task");
  const rect = (element) => (element ? element.getBoundingClientRect() : null);
  const overflow = rows.flatMap((row) => {
    const bounds = rect(row);
    return [...row.querySelectorAll(".cp-gantt-bar")].filter((bar) => {
      const barBounds = rect(bar);
      return barBounds.top < bounds.top - 1 || barBounds.bottom > bounds.bottom + 1;
    }).map((bar) => ({ activity: row.getAttribute("data-gantt-activity-id"), kind: bar.getAttribute("data-gantt-bar-kind") }));
  });
  const tableRow = document.querySelector("#cp-activity-grid tbody tr");
  const ganttRow = rows[0] || null;
  return {
    rows: rows.length,
    bars: document.querySelectorAll("#cp-gantt .cp-gantt-bar").length,
    task: task ? {
      height: Math.round(rect(task).height),
      background: getComputedStyle(task).backgroundColor,
      pattern: task.getAttribute("data-gantt-bar-pattern"),
    } : null,
    label: task?.querySelector(".cp-gantt-bar-label")?.textContent?.trim() ?? null,
    overflow,
    aligned: Boolean(tableRow && ganttRow) && Math.abs(rect(tableRow).top - rect(ganttRow).top) <= 1,
  };
})()`;

async function main() {
  const health = await waitForHttp(`${baseUrl}/preview/health`, 20000);
  check("preview health", health.status === "ok" || health.status === 200, { status: health.status });

  const chrome = await launchChrome();
  const page = new Page(chrome.cdp);
  try {
    await page.initialize();
    await page.cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1280, height: 720, deviceScaleFactor: 1, mobile: false,
    });

    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "form", "login");
    const planner = await page.evaluate(`(() => {
      const button = [...document.querySelectorAll("form button")].find((item) => (item.textContent || "").trim().startsWith("Planner"));
      if (!button) return false;
      button.click();
      return true;
    })()`);
    check("planner login offered", planner);
    await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
    await page.click('[data-project-id="preview-rps-01"]');
    await page.waitForSelector("#cp-activity-grid tbody tr", "workspace rows");
    await sleep(1200);

    const before = await page.evaluate(tableSnapshot);
    check("live table rendered", Boolean(before && before.fontSize), { before });
    await page.screenshot("preview-live/live-before-1280.png");

    // Apply table presentation through the real User Preferences dialog.
    await page.click('[data-desktop-command="dialog.user-preferences"]');
    const tablePatch = await page.evaluate(`(() => {
      const form = document.querySelector('dialog[data-desktop-dialog="user-preferences"] form');
      if (!form) return { form: false };
      const set = (name, value) => {
        const control = form.querySelector('[name="' + name + '"]');
        if (!control) return false;
        control.value = value;
        return true;
      };
      const check = (name, value) => {
        const control = form.querySelector('[name="' + name + '"]');
        if (!control) return false;
        control.checked = value;
        return true;
      };
      const fixed = form.querySelector('[name="rowHeightMode"][value="fixed"]');
      if (fixed) fixed.checked = true;
      const fields = [
        set("fontFamily", "cairo"),
        set("fontSize", "13"),
        set("textColor", "#102a43"),
        set("backgroundColor", "#eef3f8"),
        Boolean(fixed),
        set("rowHeight", "28"),
        check("showIcons", true),
        check("lineNumbers", true),
      ];
      form.requestSubmit();
      return { form: true, fields };
    })()`);
    await sleep(700);
    const applied = await page.evaluate(tableSnapshot);
    check("table patch submitted", tablePatch.form && tablePatch.fields.every(Boolean), { tablePatch });
    check("table font size applied", applied?.fontSize === "13px", { applied });
    check("table font family applied", /Cairo/i.test(applied?.fontFamily || ""), { fontFamily: applied?.fontFamily });
    check("table text colour applied", applied?.color === "rgb(16, 42, 67)", { color: applied?.color });
    check("table background applied", applied?.background === "rgb(238, 243, 248)", { background: applied?.background });
    check("fixed row height applied", applied?.rowHeight === 28, { rowHeight: applied?.rowHeight });
    check("line numbers applied", applied?.lineNumbers > 0, { lineNumbers: applied?.lineNumbers });
    check("row icons applied", applied?.icons > 0, { icons: applied?.icons });

    await page.reload("#cp-activity-grid tbody tr", "table reload");
    await sleep(600);
    const persisted = await page.evaluate(tableSnapshot);
    check("table presentation persists after reload",
      persisted?.fontSize === "13px" && persisted?.rowHeight === 28 && persisted?.dates === before.dates,
      { persisted });

    // Apply Gantt bar styles through the real Bar Styles dialog.
    const ganttBefore = await page.evaluate(ganttSnapshot);
    await page.click('[data-desktop-command="dialog.bars"]');
    const barsPatch = await page.evaluate(`(() => {
      const form = document.querySelector('dialog[data-desktop-dialog="bars"] form');
      if (!form) return { form: false };
      const set = (name, value) => {
        const control = form.querySelector('[name="' + name + '"]');
        if (!control) return false;
        control.value = value;
        return true;
      };
      const fields = [
        set("bar.task.height", "18"),
        set("bar.task.pattern", "outline"),
        set("bar.task.bodyColor", "#0f4c81"),
        set("bar.task.startColor", "#0f4c81"),
        set("bar.task.finishColor", "#0f4c81"),
        set("bar.task.labelField", "activity-name"),
        set("bar.task.labelPosition", "right"),
        set("bar.summary.height", "10"),
        set("bar.summary.pattern", "hatched"),
        set("bar.summary.bodyColor", "#17324d"),
      ];
      form.requestSubmit();
      return { form: true, fields };
    })()`);
    await sleep(700);
    const ganttCustom = await page.evaluate(ganttSnapshot);
    check("bar styles submitted", barsPatch.form && barsPatch.fields.every(Boolean), { barsPatch });
    check("task bar style applied",
      ganttCustom.task?.pattern === "outline" && ganttCustom.task?.height === 18 && Boolean(ganttCustom.label),
      { task: ganttCustom.task, label: ganttCustom.label });
    check("no bar escapes its activity row", ganttCustom.overflow.length === 0, { overflow: ganttCustom.overflow });
    check("gantt rows stay aligned with the table", ganttCustom.aligned);
    check("bar rows unchanged", ganttCustom.rows === ganttBefore.rows, { before: ganttBefore.rows, after: ganttCustom.rows });

    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
    await sleep(400);
    await page.screenshot("preview-live/live-custom-1280.png");
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
    await sleep(500);
    await page.screenshot("preview-live/live-custom-1440.png");
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false });
    await sleep(500);
    await page.screenshot("preview-live/live-custom-1920.png");

    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
    await sleep(300);
    await page.reload("#cp-gantt .cp-gantt-row", "bars reload");
    await sleep(600);
    const ganttPersisted = await page.evaluate(ganttSnapshot);
    const tableAfterBars = await page.evaluate(tableSnapshot);
    check("bar styles persist after reload",
      ganttPersisted.task?.pattern === "outline" && ganttPersisted.task?.height === 18,
      { task: ganttPersisted.task });
    check("schedule dates unchanged by presentation", tableAfterBars.dates === before.dates);
    check("table presentation stays consistent with saved layout",
      tableAfterBars.fontSize === "13px" && tableAfterBars.rowHeight === 28,
      { table: tableAfterBars });

    // Restore defaults so the delivered preview project keeps its baseline look.
    await page.click('[data-desktop-command="dialog.user-preferences"]');
    await page.click('dialog[data-desktop-dialog="user-preferences"] [data-dialog-default]');
    await sleep(800);
    const restored = await page.evaluate(tableSnapshot);
    const ganttRestored = await page.evaluate(ganttSnapshot);
    check("default restore returns the baseline table",
      restored?.fontSize === before.fontSize && restored?.rowHeight === before.rowHeight && restored?.lineNumbers === before.lineNumbers && restored?.dates === before.dates,
      { restored });
    check("default restore returns the baseline bars", ganttRestored.task?.pattern === "solid");
    await page.screenshot("preview-live/live-restored-1280.png");

    // Logout returns to the public home.
    const signedOut = await page.evaluate(`(() => {
      const button = [...document.querySelectorAll("button")].find((item) => /sign out/i.test(item.textContent || ""));
      if (!button) return false;
      button.click();
      return true;
    })()`);
    await sleep(1500);
    const afterLogout = await page.evaluate(`({
      url: location.href,
      home: Boolean(document.querySelector(".cubi-reference-home")),
      shell: Boolean(document.querySelector(".cp-app-shell")),
    })`);
    check("sign out returns to public home", signedOut && afterLogout.home && !afterLogout.shell, { afterLogout });

    const report = {
      base_url: baseUrl,
      git_head: gitHead(),
      finished_at: new Date().toISOString(),
      checks,
      screenshots: ["live-before-1280.png", "live-custom-1280.png", "live-custom-1440.png", "live-custom-1920.png", "live-restored-1280.png"],
    };
    const file = join(outDir, "live-preview.json");
    writeFileSync(file, JSON.stringify(report, null, 2));
    process.stdout.write(`\nLive preview report: ${file}\n`);
    if (checks.some((entry) => !entry.pass)) process.exitCode = 1;
  } finally {
    page.cdp.close();
    chrome.cdp.close();
    await chrome.stop();
  }
}

main().catch((error) => {
  process.stdout.write(`LIVE PREVIEW FAILED: ${error instanceof Error ? error.stack ?? error.message : String(error)}\n`);
  process.exitCode = 1;
});
