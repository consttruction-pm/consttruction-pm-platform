#!/usr/bin/env node
/**
 * Prove the Gantt Bar Styles dialog drives the rendered bars: change task and
 * summary height, colour, pattern, end shapes and label; verify the DOM,
 * reload for persistence, then restore the defaults.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4174 node e2e/capture-bars.mjs
 */

import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4174";
const outDir = join(artifactsDir, "bars-live");
mkdirSync(outDir, { recursive: true });

const metrics = `(() => {
  const describe = (bar) => bar ? {
    className: bar.className,
    shape: bar.dataset.ganttBarShape ?? null,
    pattern: bar.dataset.ganttBarPattern ?? null,
    height: getComputedStyle(bar).height,
    background: getComputedStyle(bar).backgroundColor,
    backgroundImage: getComputedStyle(bar).backgroundImage,
    label: bar.querySelector(".cp-gantt-bar-label")?.textContent ?? null,
    labelClass: bar.querySelector(".cp-gantt-bar-label")?.className ?? null,
    startMarker: bar.querySelector(".cp-gantt-endpoint.is-start")?.className ?? null,
    finishMarker: bar.querySelector(".cp-gantt-endpoint.is-finish")?.className ?? null,
  } : null;
  return {
    task: describe(document.querySelector('#cp-gantt [data-gantt-bar-kind="task"]')),
    critical: describe(document.querySelector('#cp-gantt [data-gantt-bar-kind="critical"]')),
    summary: describe(document.querySelector("#cp-gantt .cp-gantt-summary-bar")),
    taskCount: document.querySelectorAll('#cp-gantt [data-gantt-bar-kind="task"]').length,
    criticalCount: document.querySelectorAll('#cp-gantt [data-gantt-bar-kind="critical"]').length,
    summaryCount: document.querySelectorAll("#cp-gantt .cp-gantt-summary-bar").length,
  };
})()`;

async function openBars(page) {
  await page.evaluate(`(() => {
    const button = [...document.querySelectorAll('[data-desktop-command="dialog.bars"]')]
      .find((item) => item.getClientRects().length > 0);
    if (!button) return false;
    button.click();
    return true;
  })()`);
  await page.waitForSelector('[data-desktop-dialog="bars"][open]', "bar styles dialog", 4000);
  await sleep(300);
}

async function submitBars(page) {
  await page.evaluate(`(() => {
    const dialog = document.querySelector('[data-desktop-dialog="bars"]');
    dialog?.querySelector("[data-dialog-ok]")?.click();
    return true;
  })()`);
  await page.waitFor(
    `(() => { const dialog = document.querySelector('[data-desktop-dialog="bars"]'); return !dialog || !dialog.hasAttribute("open"); })()`,
    "bar styles dialog closed",
    4000,
  );
  await sleep(1000);
}

async function setSelect(page, name, value) {
  const ok = await page.evaluate(`(() => {
    const select = document.querySelector('[data-desktop-dialog="bars"] select[name=${JSON.stringify(name)}]');
    if (!select) return false;
    select.value = ${JSON.stringify(value)};
    if (select.value !== ${JSON.stringify(value)}) return false;
    select.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  if (!ok) throw new Error(`could not set ${name}`);
}

async function setInput(page, name, value) {
  const ok = await page.evaluate(`(() => {
    const input = document.querySelector('[data-desktop-dialog="bars"] input[name=${JSON.stringify(name)}]');
    if (!input) return false;
    input.value = ${JSON.stringify(value)};
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  if (!ok) throw new Error(`could not fill ${name}`);
}

async function applyStyle(page, kind, values) {
  for (const [field, value] of Object.entries(values)) {
    const name = `bar.${kind}.${field}`;
    if (field === "bodyShape" || field === "startShape" || field === "finishShape" || field === "pattern" || field === "labelField" || field === "labelPosition" || field === "filter") {
      await setSelect(page, name, value);
    } else if (field === "visible") {
      // Leave visibility untouched.
    } else {
      await setInput(page, name, value);
    }
  }
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
    customized: null,
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
    await sleep(1300);
    await page.evaluate(`(() => {
      const select = document.querySelector("[data-workspace-language]");
      if (!select) return false;
      select.value = "en";
      select.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    })()`);
    await sleep(900);

    // Normalise any style left by an earlier run before measuring the baseline.
    await openBars(page);
    await applyStyle(page, "task", {
      bodyColor: "#eef3f8", borderColor: "#1f3b57", startColor: "#1f3b57", finishColor: "#1f3b57",
      height: "14", pattern: "solid", bodyShape: "bar", startShape: "none", finishShape: "none",
      labelField: "activity-id", labelPosition: "right",
    });
    await applyStyle(page, "summary", {
      bodyColor: "#17324d", borderColor: "#0f2a44", startColor: "#17324d", finishColor: "#17324d",
      height: "10", pattern: "solid", bodyShape: "bar", startShape: "triangle-down", finishShape: "triangle-down",
      labelField: "none", labelPosition: "right",
    });
    await submitBars(page);
    report.baseline = await page.evaluate(metrics);
    await page.screenshot("bars-live/bars-baseline-1280x720.png");
    report.screenshots.baseline = "bars-live/bars-baseline-1280x720.png";

    // Open the real dialog and capture its behaviour list.
    await openBars(page);
    report.dialog = await page.evaluate(`(() => {
      const dialog = document.querySelector('[data-desktop-dialog="bars"]');
      const box = dialog.getBoundingClientRect();
      return {
        open: dialog.hasAttribute("open"),
        sections: [...dialog.querySelectorAll("[data-bar-style]")].map((section) => section.dataset.barStyle),
        taskHeight: dialog.querySelector('input[name="bar.task.height"]')?.value ?? null,
        taskPattern: dialog.querySelector('select[name="bar.task.pattern"]')?.value ?? null,
        taskLabel: dialog.querySelector('select[name="bar.task.labelField"]')?.value ?? null,
        summaryLabel: dialog.querySelector('select[name="bar.summary.labelField"]')?.value ?? null,
        width: Math.round(box.width),
        height: Math.round(box.height),
        fitsViewport: box.top >= 0 && box.bottom <= window.innerHeight + 1,
      };
    })()`);
    await page.screenshot("bars-live/bars-dialog-1280x720.png");
    report.screenshots.dialog = "bars-live/bars-dialog-1280x720.png";
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 2, mobile: false });
    await sleep(350);
    await page.screenshot("bars-live/bars-dialog-zoom.png");
    report.screenshots.dialogZoom = "bars-live/bars-dialog-zoom.png";
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
    await sleep(300);

    // Apply a clearly different, still real style.
    await applyStyle(page, "task", {
      bodyColor: "#c0392b", borderColor: "#7b1f18", startColor: "#000000", finishColor: "#000000",
      height: "18", pattern: "striped", bodyShape: "diamond", startShape: "circle", finishShape: "triangle-up",
      labelField: "activity-name", labelPosition: "inside-center",
    });
    await applyStyle(page, "summary", {
      bodyColor: "#0b5fa5", borderColor: "#063b69", startColor: "#0b5fa5", finishColor: "#0b5fa5",
      height: "16", pattern: "hatched", startShape: "diamond", finishShape: "diamond",
      labelField: "activity-name", labelPosition: "right",
    });
    await submitBars(page);
    report.customized = await page.evaluate(metrics);
    await page.screenshot("bars-live/bars-customized-1280x720.png");
    report.screenshots.customized = "bars-live/bars-customized-1280x720.png";

    // Reload: the saved layout carries the same bar styles.
    await page.reload();
    await page.waitForSelector("#cp-activity-grid tbody tr", "workspace rows after reload");
    await sleep(1500);
    report.afterReload = await page.evaluate(metrics);

    // Restore the defaults so later captures start from the documented palette.
    await openBars(page);
    await applyStyle(page, "task", {
      bodyColor: "#eef3f8", borderColor: "#1f3b57", startColor: "#1f3b57", finishColor: "#1f3b57",
      height: "14", pattern: "solid", bodyShape: "bar", startShape: "none", finishShape: "none",
      labelField: "activity-id", labelPosition: "right",
    });
    await applyStyle(page, "summary", {
      bodyColor: "#17324d", borderColor: "#0f2a44", startColor: "#17324d", finishColor: "#17324d",
      height: "10", pattern: "solid", bodyShape: "bar", startShape: "triangle-down", finishShape: "triangle-down",
      labelField: "none", labelPosition: "right",
    });
    await submitBars(page);
    report.restored = await page.evaluate(metrics);
    await page.screenshot("bars-live/bars-restored-1280x720.png");
    report.screenshots.restored = "bars-live/bars-restored-1280x720.png";
  } finally {
    writeFileSync(join(outDir, "bars-capture.json"), JSON.stringify(report, null, 2));
    page.cdp.close();
    chrome.cdp.close();
    await chrome.stop();
  }
  process.stdout.write(`Bars capture: ${join(outDir, "bars-capture.json")}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error && error.stack ? error.stack : error}\n`);
  process.exit(1);
});
