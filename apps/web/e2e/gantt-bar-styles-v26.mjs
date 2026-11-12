#!/usr/bin/env node
/**
 * Version 26 Gantt bar style acceptance (ACT-009).
 *
 * Proves in the real preview that the Bar Styles dialog drives the rendered
 * bars for the selected bar type:
 *   - shape, fill pattern, height, row and label are written to the layout,
 *     reflected by the real bar element and survive a full reload;
 *   - the bar's date-derived horizontal geometry (inline left/width) and the
 *     primary bar population are unchanged, so a style edit never moves
 *     schedule data. Moving the task bar off the default progress row turns
 *     the progress fill into an independent layer; those layers must reuse the
 *     unchanged task span.
 *   - the same values render in a Persian RTL cell without horizontal overflow;
 *   - restoring the defaults through the dialog returns the documented style.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4197 \
 *   CUBI_TESTED_CODE_SHA=<code commit> node e2e/gantt-bar-styles-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4197";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "gantt-bar-styles-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `gantt-bar-styles-v26-${evidenceDate}`);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const scenarios = [];
const screenshots = [];

function log(message) {
  process.stdout.write(`${message}\n`);
}

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

function record(id, name, status, details = {}) {
  scenarios.push({ id, name, status, at: new Date().toISOString(), ...details });
  log(`  ${status.toUpperCase()} ${id}. ${name}`);
}

async function scenario(id, name, body) {
  log(`\n[${id}] ${name}`);
  try {
    const details = (await body()) ?? {};
    record(id, name, "pass", details);
  } catch (error) {
    record(id, name, "fail", { error: String(error && error.stack ? error.stack : error) });
    throw error;
  }
}

async function capture(page, name) {
  const file = `gantt-bar-styles-v26/${name}.png`;
  await page.screenshot(file);
  copyFileSync(join(artifactsDir, file), join(evidenceDir, `${name}.png`));
  screenshots.push(`${name}.png`);
  return file;
}

async function setViewport(page, width, height) {
  await page.cdp.send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
  await sleep(400);
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

async function clickVisible(page, selector) {
  const clicked = await page.evaluate(`(() => {
    const element = [...document.querySelectorAll(${JSON.stringify(selector)})].find((item) => item.getClientRects().length > 0);
    if (!element || element.disabled) return false;
    element.click();
    return true;
  })()`);
  assert(clicked, `not clickable: ${selector}`);
}

async function applyBarSettings(page, values) {
  await clickVisible(page, '[data-desktop-command="dialog.bars"]');
  await page.waitForSelector('dialog[data-desktop-dialog="bars"][open]', "bars dialog", 8000);
  await sleep(250);
  const applied = await page.evaluate(`(() => {
    const dialog = document.querySelector('dialog[data-desktop-dialog="bars"]');
    const form = dialog.querySelector('[data-dialog-form="bars"]');
    const values = ${JSON.stringify(values)};
    const set = (name, value) => {
      const field = form.querySelector('[name="bar.' + name + '"]');
      if (!field) return false;
      if (field.type === "checkbox") field.checked = value === true || value === "true";
      else field.value = String(value);
      return true;
    };
    for (const [name, value] of Object.entries(values)) {
      if (!set(name, value)) return { ok: false, name };
    }
    form.querySelector('[data-dialog-ok]').click();
    return { ok: true };
  })()`);
  assert(applied.ok, `bar style field missing: ${applied.name}`);
  await page.waitFor(`!document.querySelector('dialog[data-desktop-dialog="bars"]')?.open`, "bars dialog closed", 8000);
  await sleep(700);
  await page.waitForSelector("#cp-gantt [data-gantt-activity-id]", "gantt rows after bars dialog");
}

const barState = `(() => {
  const bars = [...document.querySelectorAll("#cp-gantt [data-gantt-bar-kind]")];
  const byId = {};
  let taskBars = 0;
  const byKind = {};
  for (const bar of bars) {
    const row = bar.closest("[data-gantt-activity-id]");
    const id = row?.getAttribute("data-gantt-activity-id") ?? "";
    const kind = bar.getAttribute("data-gantt-bar-kind") ?? "";
    byKind[kind] = (byKind[kind] || 0) + 1;
    if (kind === "task") taskBars += 1;
    if (!id) continue;
    // One activity can draw several layers (primary bar plus an independent
    // progress/actual/baseline layer), so key by activity and kind.
    byId[id + "::" + kind] = {
      kind,
      shape: bar.getAttribute("data-gantt-bar-shape"),
      pattern: bar.getAttribute("data-gantt-bar-pattern"),
      row: bar.getAttribute("data-gantt-bar-row"),
      left: bar.style.left,
      width: bar.style.width,
      top: bar.style.top,
      height: Math.round(bar.getBoundingClientRect().height * 10) / 10,
      className: bar.className,
      bodyColor: (bar.style.getPropertyValue("--cp-bar-body") || "").trim(),
      borderColor: (bar.style.getPropertyValue("--cp-bar-border") || "").trim(),
      startMarker: bar.querySelector(".cp-gantt-endpoint.is-start")?.className ?? "",
      finishMarker: bar.querySelector(".cp-gantt-endpoint.is-finish")?.className ?? "",
      label: bar.querySelector(".cp-gantt-bar-label")?.textContent?.trim() ?? "",
      labelPosition: bar.querySelector(".cp-gantt-bar-label")?.getAttribute("data-gantt-label-position") ?? "",
    };
  }
  return {
    bars: bars.length,
    byKind,
    taskBars,
    byId,
    rows: document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]").length,
    ganttRows: document.querySelectorAll("#cp-gantt [data-gantt-activity-id]").length,
    dir: document.documentElement.dir || document.documentElement.getAttribute("dir") || "ltr",
    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  };
})()`;

function taskBarsOf(state) {
  return Object.values(state.byId).filter((bar) => bar.kind === "task");
}

function assertStyle(state, expected, label) {
  const tasks = taskBarsOf(state);
  assert(tasks.length > 0, `${label}: no task bars were drawn`);
  for (const bar of tasks) {
    assert(bar.shape === expected.shape, `${label}: task bar shape ${bar.shape} != ${expected.shape}`);
    assert(bar.pattern === expected.pattern, `${label}: task bar pattern ${bar.pattern} != ${expected.pattern}`);
    assert(bar.row === String(expected.row), `${label}: task bar row ${bar.row} != ${expected.row}`);
    assert(/is-pattern-/.test(bar.className), `${label}: task bar has no pattern class (${bar.className})`);
    assert(Math.abs(bar.height - expected.height) <= 1, `${label}: task bar height ${bar.height} != ${expected.height}`);
    if (expected.labelPosition) {
      assert(bar.labelPosition === expected.labelPosition, `${label}: label position ${bar.labelPosition} != ${expected.labelPosition}`);
    }
  }
}

async function main() {
  const health = await waitForHttp(`${baseUrl}/preview/health`, 30000);  if (!(health.status === "ok" || health.status === 200)) throw new Error(`preview health ${health.status}`);

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
    contract: "cubi-gantt-bar-styles-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
  };

  function writeReport() {
    report.scenarios = scenarios;
    report.passed = scenarios.filter((entry) => entry.status === "pass").length;
    report.failed = scenarios.filter((entry) => entry.status === "fail").length;
    const json = JSON.stringify(report, null, 2);
    writeFileSync(join(outDir, "gantt-bar-styles-v26.json"), json);
    writeFileSync(join(evidenceDir, "gantt-bar-styles-v26.json"), json);
  }

  try {
    await setViewport(page, 1366, 768);
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
    await sleep(1500);
    await page.waitForSelector("#cp-gantt [data-gantt-activity-id]", "gantt rows");

    let baseline = null;
    let styledState = null;

    await scenario("01", "documented default task bar renders", async () => {
      await applyBarSettings(page, {
        "task.bodyShape": "bar",
        "task.pattern": "solid",
        "task.height": 9,
        "task.row": 1,
        "task.startShape": "none",
        "task.finishShape": "none",
        "task.bodyColor": "#0000ff",
        "task.borderColor": "#000000",
        "task.labelField": "finish-id-name",
        "task.labelPosition": "right",
        // Actual and baseline layers stack in other rows; hiding them keeps the
        // task layer's requested height from being packed down this scenario.
        "actual.visible": false,
        "baseline.visible": false,
      });
      baseline = await page.evaluate(barState);
      assertStyle(baseline, { shape: "bar", pattern: "solid", row: 1, height: 9 }, "default");
      assert(baseline.bars > 0 && baseline.taskBars > 0, "the fixture drew no task bars");
      await capture(page, "01-default-task-bar-en-1366");
      return { bars: baseline.bars, taskBars: baseline.taskBars, rows: baseline.rows, ganttRows: baseline.ganttRows };
    });

    await scenario("02", "Bar Styles writes shape, pattern, height, row and label to every task bar", async () => {
      // Snapshot immediately before the edit: asynchronous schedule facts can
      // still add bars while the chart warms up, and the invariant under test
      // is the difference this style edit makes.
      await sleep(1200);
      baseline = await page.evaluate(barState);
      await applyBarSettings(page, {
        "task.bodyShape": "diamond",
        "task.pattern": "hatched",
        "task.height": 12,
        "task.row": 2,
        "task.startShape": "triangle-up",
        "task.finishShape": "circle",
        "task.bodyColor": "#123456",
        "task.borderColor": "#654321",
        "task.labelField": "duration",
        "task.labelPosition": "above",
      });
      const styled = await page.evaluate(barState);
      styledState = styled;
      assertStyle(styled, { shape: "diamond", pattern: "hatched", row: 2, height: 12, labelPosition: "above" }, "styled");
      for (const bar of taskBarsOf(styled)) {
        assert(/is-body-diamond/.test(bar.className), `task bar is missing the diamond body class (${bar.className})`);
        assert(/is-start/.test(bar.startMarker) && /is-triangle-up/.test(bar.startMarker), `start marker ${bar.startMarker} is not a triangle-up`);
        assert(/is-finish/.test(bar.finishMarker) && /is-circle/.test(bar.finishMarker), `finish marker ${bar.finishMarker} is not a circle`);
        assert(bar.bodyColor.toLowerCase() === "#123456", `body colour ${bar.bodyColor} != #123456`);
        assert(bar.borderColor.toLowerCase() === "#654321", `border colour ${bar.borderColor} != #654321`);
        assert(bar.label.length > 0, "the duration label is empty after the style change");
      }
      await capture(page, "02-styled-task-bar-en-1366");
      return { taskBars: styled.taskBars, barsBefore: baseline.bars, barsAfter: styled.bars, kindsBefore: baseline.byKind, kindsAfter: styled.byKind, sample: taskBarsOf(styled)[0] };
    });

    await scenario("03", "a style edit does not move date-derived geometry or change the primary bar population", async () => {
      const styled = styledState;
      assert(styled, "the styled measurement is missing");
      assert(styled.rows === baseline.rows && styled.ganttRows === baseline.ganttRows, "table/Gantt row population changed");
      // Moving the task bar off row 1 (the default progress row) turns the
      // progress fill into an independent layer, so compare every other layer
      // one-to-one and require progress layers to reuse the unchanged task span.
      const kindOf = (key) => key.slice(key.indexOf("::") + 2);
      const primaryBefore = Object.entries(baseline.byId).filter(([key]) => kindOf(key) !== "progress");
      const primaryAfter = Object.entries(styled.byId).filter(([key]) => kindOf(key) !== "progress");
      assert(primaryAfter.length === primaryBefore.length, `primary bar count changed ${primaryBefore.length} → ${primaryAfter.length}`);
      for (const [key, before] of primaryBefore) {
        const after = styled.byId[key];
        assert(after, `bar ${key} disappeared after the style edit`);
        assert(after.left === before.left && after.width === before.width, `bar ${key} moved from ${before.left}/${before.width} to ${after.left}/${after.width}`);
      }
      const progressLayers = Object.entries(styled.byId).filter(([key]) => kindOf(key) === "progress");
      for (const [key, progress] of progressLayers) {
        const task = styled.byId[key.replace(/::progress$/, "::task")];
        assert(task, `progress layer ${key} has no task bar`);
        assert(progress.left === task.left, `progress layer ${key} left ${progress.left} != task ${task.left}`);
      }
      return {
        primaryBars: primaryAfter.length,
        compared: primaryBefore.length,
        progressLayers: progressLayers.length,
        kindsBefore: baseline.byKind,
        kindsAfter: styled.byKind,
      };
    });

    await scenario("04", "the bar style survives a full reload", async () => {
      await page.reload("#cp-gantt [data-gantt-activity-id]", "reload after bar style");
      await sleep(900);
      const reloaded = await page.evaluate(barState);
      assertStyle(reloaded, { shape: "diamond", pattern: "hatched", row: 2, height: 12, labelPosition: "above" }, "reloaded");
      assert(reloaded.bars === styledState.bars, "the reloaded chart lost bars");
      await capture(page, "03-styled-task-bar-after-reload-en-1366");
      return { bars: reloaded.bars };
    });

    await scenario("05", "the same style renders in a Persian RTL cell without overflow", async () => {
      await setViewport(page, 1366, 768);
      await setLanguage(page, "fa");
      await page.waitForSelector("#cp-gantt [data-gantt-activity-id]", "gantt rows after language switch");
      const rtl = await page.evaluate(barState);
      assertStyle(rtl, { shape: "diamond", pattern: "hatched", row: 2, height: 12, labelPosition: "above" }, "rtl");
      assert(rtl.dir === "rtl", `document direction is ${rtl.dir}, not rtl`);
      assert(rtl.overflow <= 1, `the RTL chart overflows horizontally by ${rtl.overflow}px`);
      await capture(page, "04-styled-task-bar-fa-rtl-1366");
      return { dir: rtl.dir, overflow: rtl.overflow, bars: rtl.bars };
    });

    await scenario("06", "the style renders at 1280x720 without overflow", async () => {
      await setLanguage(page, "en");
      await setViewport(page, 1280, 720);
      await page.waitForSelector("#cp-gantt [data-gantt-activity-id]", "gantt rows at 1280");
      const small = await page.evaluate(barState);
      assertStyle(small, { shape: "diamond", pattern: "hatched", row: 2, height: 12, labelPosition: "above" }, "1280");
      assert(small.overflow <= 1, `the 1280 chart overflows horizontally by ${small.overflow}px`);
      await capture(page, "05-styled-task-bar-en-1280");
      return { viewport: "1280x720", overflow: small.overflow, bars: small.bars };
    });

    await scenario("07", "the style renders at 1920x1080 without overflow", async () => {
      await setViewport(page, 1920, 1080);
      await page.waitForSelector("#cp-gantt [data-gantt-activity-id]", "gantt rows at 1920");
      const large = await page.evaluate(barState);
      assertStyle(large, { shape: "diamond", pattern: "hatched", row: 2, height: 12, labelPosition: "above" }, "1920");
      assert(large.overflow <= 1, `the 1920 chart overflows horizontally by ${large.overflow}px`);
      await capture(page, "06-styled-task-bar-en-1920");
      return { viewport: "1920x1080", overflow: large.overflow, bars: large.bars };
    });

    await scenario("08", "the milestone type writes its own shape, pattern, height and label", async () => {
      await applyBarSettings(page, {
        "milestone.bodyShape": "diamond",
        "milestone.pattern": "hatched",
        "milestone.height": 14,
        "milestone.labelField": "duration",
        "milestone.labelPosition": "below",
      });
      const state = await page.evaluate(barState);
      const milestones = Object.entries(state.byId).filter(([, bar]) => bar.kind === "milestone");
      assert(milestones.length > 0, "the fixture drew no milestone bar");
      for (const [key, bar] of milestones) {
        assert(bar.shape === "diamond", `${key}: milestone shape ${bar.shape} != diamond`);
        assert(bar.pattern === "hatched", `${key}: milestone pattern ${bar.pattern} != hatched`);
        assert(/is-body-diamond/.test(bar.className), `${key}: milestone is missing the diamond class (${bar.className})`);
        assert(Math.abs(bar.height - 14) <= 1, `${key}: milestone height ${bar.height} != 14`);
        assert(bar.labelPosition === "below", `${key}: milestone label position ${bar.labelPosition} != below`);
        assert(bar.label.length > 0, `${key}: milestone duration label is empty`);
      }
      const tasks = taskBarsOf(state);
      assert(tasks.every((bar) => bar.shape === "diamond"), "editing the milestone type changed the task bars");
      await capture(page, "07-styled-milestone-en-1920");
      return { milestones: milestones.length, sample: milestones[0][1] };
    });

    await scenario("09", "restoring the defaults returns the documented task and milestone bars", async () => {
      await setLanguage(page, "en");
      await applyBarSettings(page, {
        "task.bodyShape": "bar",
        "task.pattern": "solid",
        "task.height": 9,
        "task.row": 1,
        "task.startShape": "none",
        "task.finishShape": "none",
        "task.bodyColor": "#0000ff",
        "task.borderColor": "#000000",
        "task.labelField": "finish-id-name",
        "task.labelPosition": "right",
        "milestone.bodyShape": "triangle-down",
        "milestone.pattern": "solid",
        "milestone.height": 9,
        "milestone.labelField": "finish-id-name",
        "milestone.labelPosition": "right",
      });
      const restored = await page.evaluate(barState);
      assertStyle(restored, { shape: "bar", pattern: "solid", row: 1, height: 9 }, "restored");
      assert(restored.bars === baseline.bars, "restoring the style changed the bar count");
      return { bars: restored.bars };
    });

    writeReport();
    log(`\nAll ${report.passed} Gantt bar style scenarios passed`);
    if (report.failed) process.exitCode = 1;
  } catch (error) {
    writeReport();
    throw error;
  } finally {
    page.cdp.close();
    await chrome.stop();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
