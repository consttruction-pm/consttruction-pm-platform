#!/usr/bin/env node
/**
 * Gantt baseline-window acceptance (Priority 6).
 *
 * Verifies that the stored baseline of the open project is read through the
 * existing authoritative comparison endpoint, projected into the baseline
 * cells, drawn as baseline bars aligned with their activity rows, shown in the
 * status bar and Summary dates, and that the Layout Options toggle persists
 * with the saved layout. No baseline window is ever derived in the browser.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4198 \
 *   node e2e/activity-baseline-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4198";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-14";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const outDir = join(artifactsDir, "activity-baseline-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `activity-baseline-v26-${evidenceDate}`);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT_ID = "preview-rps-01";
const BASELINE_ID = "BL-E2E-P6";
const BASELINE_NAME = "E2E primary baseline";

const report = {
  contract: "cubi-activity-baseline-v26.v1",
  url: baseUrl,
  testedCodeSha,
  gitHead: gitHead(),
  capturedAt: new Date().toISOString(),
  before: null,
  capture: null,
  afterReload: null,
  details: null,
  toggle: null,
  screenshots: [],
  exceptions: [],
  consoleErrors: [],
  apiFailures: [],
};

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

function step(name) {
  if (process.env.CUBI_E2E_TRACE === "1") console.error(`[step] ${name}`);
}

async function captureState(page, name) {
  await page.screenshot(`activity-baseline-v26/${name}.png`);
  copyFileSync(join(outDir, `${name}.png`), join(evidenceDir, `${name}.png`));
  report.screenshots.push(`${name}.png`);
}

async function openProject(page) {
  step("navigate login");
  // The demo session cookie survives navigations. On a repeat visit the login
  // page shows the signed-in variant without role buttons, so only pick a role
  // when the persona cards are actually rendered.
  await page.navigate(`${baseUrl}/preview/login`, null, "login");
  const needsLogin = await page.evaluate(`Boolean(document.querySelector('button[name="role"][value="admin"]'))`);
  if (needsLogin) {
    step("choose admin role");
    await page.click('button[name="role"][value="admin"]');
  } else {
    step("session exists, open workspace");
    await page.navigate(`${baseUrl}/app?view=live`, null, "workspace");
  }
  step("wait project selection");
  await page.waitForSelector(`[data-project-id="${PROJECT_ID}"]`, "project selection");
  step("click project");
  await page.click(`[data-project-id="${PROJECT_ID}"]`);
  step("wait activity rows");
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
  await sleep(1600);
  step("project ready");
}

function geometry(page) {
  return page.evaluate(`(() => {
    const bars = [...document.querySelectorAll('#cp-gantt [data-gantt-bar-kind="baseline"]')].map((bar) => {
      const row = bar.closest('[data-gantt-activity-id]');
      return {
        activityId: row?.dataset.ganttActivityId ?? null,
        left: Number.parseFloat(bar.style.left),
        width: Number.parseFloat(bar.style.width),
        top: Number.parseFloat(bar.style.top),
        height: Number.parseFloat(bar.style.height),
        row: bar.dataset.ganttBarRow,
        shape: bar.dataset.ganttBarShape,
        rowHeight: row ? Number.parseFloat(getComputedStyle(row).height) : null,
      };
    });
    const primary = [...document.querySelectorAll('#cp-gantt [data-gantt-bar-primary="true"]')].map((bar) => ({
      activityId: bar.closest('[data-gantt-activity-id]')?.dataset.ganttActivityId ?? null,
      kind: bar.dataset.ganttBarKind,
    }));
    const status = document.querySelector('[data-chrome-baseline]')?.textContent?.trim()
      ?? document.querySelector('.cp-statusbar')?.textContent ?? "";
    const toggle = document.querySelector('[data-layout-baseline]');
    return {
      bars,
      current: primary,
      status,
      toggle: toggle ? { disabled: toggle.disabled, checked: toggle.checked } : null,
    };
  })()`);
}

async function main() {
  await waitForHttp(`${baseUrl}/preview/health`, 20000);
  const chrome = await launchChrome();
  const page = new Page(chrome.cdp);
  await page.initialize();
  page.cdp.on("Runtime.exceptionThrown", (params) => {
    report.exceptions.push(params.exceptionDetails?.exception?.description ?? params.exceptionDetails?.text ?? "unknown exception");
  });
  page.cdp.on("Runtime.consoleAPICalled", (params) => {
    if (params.type !== "error") return;
    report.consoleErrors.push((params.args ?? []).map((arg) => arg.value ?? arg.description ?? arg.type).join(" "));
  });
  await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 768, deviceScaleFactor: 1, mobile: false });
  page.cdp.on("Network.responseReceived", (params) => {
    const url = params.response?.url ?? "";
    if (url.includes("/api/") && params.response.status >= 500) {
      report.apiFailures.push({ url, status: params.response.status });
    }
  });

  await page.initialize();
  await openProject(page);
  report.before = await geometry(page);
  assert(report.before.status.includes("—"), `a fresh project should show no baseline, got ${report.before.status}`);
  assert(report.before.toggle?.disabled === true, "baseline bars must stay disabled before a baseline window is loaded");
  assert(report.before.bars.length === 0, "no baseline bar may be drawn without a stored baseline");

  // Capture the open schedule into a real PRIMARY baseline through the
  // existing capture endpoint; the dates come from the stored snapshot.
  report.capture = await page.evaluate(`(async () => {
    const list = await (await fetch("/api/projects")).json();
    const project = (list.projects || []).find((item) => item.project_id === ${JSON.stringify(PROJECT_ID)});
    if (!project) return { error: "PROJECT_NOT_LISTED" };
    const response = await fetch("/api/projects/${PROJECT_ID}/p6/baselines/capture", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contract_version: "p6-baseline-capture-api.v1",
        expected_revision: project.revision,
        baseline_id: ${JSON.stringify(BASELINE_ID)},
        name: ${JSON.stringify(BASELINE_NAME)},
        baseline_type: "PRIMARY",
        currency: "USD",
      }),
    });
    return { status: response.status, body: await response.json().catch(() => null) };
  })()`, { awaitPromise: true });
  assert(report.capture?.status === 201 || report.capture?.status === 200, `baseline capture failed: ${JSON.stringify(report.capture)}`);
  const counts = report.capture.body?.counts ?? {};
  assert(Number(counts.activities) > 0, "the captured baseline must store activity windows");
  report.capture = { status: report.capture.status, baselineId: report.capture.body?.baseline?.baseline_id, counts };

  // Read the stored windows through the same read contract the Gantt loader
  // uses, so the rendered bars can be compared with authoritative dates.
  const compared = await page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${PROJECT_ID}/p6/baselines/${BASELINE_ID}/activities");
    const body = await response.json().catch(() => null);
    return {
      status: response.status,
      code: body?.code ?? null,
      contract: body?.contract_version ?? null,
      kind: body?.kind ?? null,
      rows: (body?.activities || [])
        .filter((row) => row?.planned_start && row?.planned_finish)
        .map((row) => ({ activityId: row.activity_id, start: row.planned_start, finish: row.planned_finish })),
    };
  })()`, { awaitPromise: true });
  assert(compared.status === 200, `baseline read failed: ${compared.status} ${compared.code ?? ""}`);
  assert(compared.contract === "p6-baseline-activity-api.v1", `unexpected baseline activity contract: ${compared.contract}`);
  assert(compared.kind === "p6_baseline_activity_list", `unexpected baseline activity kind: ${compared.kind}`);
  assert(compared.rows.length > 0, "the captured baseline must return stored windows");
  report.compare = { status: compared.status, rows: compared.rows.length };

  // Reopen the project so the Gantt loader reads the new baseline on open.
  await openProject(page);
  report.afterReload = await geometry(page);
  assert(report.afterReload.bars.length > 0, "the Gantt did not draw the stored baseline bars");
  assert(report.afterReload.bars.length === compared.rows.length, `expected ${compared.rows.length} baseline bars, got ${report.afterReload.bars.length}`);
  assert(report.afterReload.status.includes(BASELINE_NAME), `status bar does not name the current baseline: ${report.afterReload.status}`);
  assert(report.afterReload.toggle?.disabled === false && report.afterReload.toggle?.checked === true, "baseline bars must be available and visible once stored dates exist");
  const primaryActivities = new Set(report.afterReload.current.map((bar) => bar.activityId));
  for (const bar of report.afterReload.bars) {
    assert(Number.isFinite(bar.left) && bar.width > 0, `baseline bar ${bar.activityId} has no date geometry`);
    assert(bar.row === "3", `baseline bar ${bar.activityId} must use the documented third row, got ${bar.row}`);
    assert(primaryActivities.has(bar.activityId), `baseline bar ${bar.activityId} has no primary bar in its activity row`);
    assert(Number.isFinite(bar.top) && Number.isFinite(bar.height) && bar.height >= 2, `baseline bar ${bar.activityId} has no visible height`);
    assert(bar.top >= 0 && bar.top + bar.height <= (bar.rowHeight ?? 0) + 0.5, `baseline bar ${bar.activityId} is drawn outside its activity row`);
  }
  await captureState(page, "baseline-bars-en-1366");

  // Summary > Display Dates must show the stored baseline window for the row.
  // Select an activity that actually has a stored baseline window instead of
  // the first grid row, which may be a summary row without a baseline fact.
  const subject = report.afterReload.bars[0];
  await page.evaluate(`(() => { document.querySelector('#cp-activity-grid tbody tr[data-activity-id="${subject.activityId}"]')?.click(); return true; })()`);
  await page.waitForSelector('#cp-details [data-detail-tab="summary"]', "summary tab");
  await sleep(500);
  await page.evaluate(`(() => { document.querySelector('#cp-details [data-detail-tab="summary"]')?.click(); return true; })()`);
  await sleep(400);
  await page.evaluate(`(() => { document.querySelector('#cp-details [data-summary-view="dates"]')?.click(); return true; })()`);
  await sleep(300);
  report.details = await page.evaluate(`(() => {
    const panel = document.querySelector('#cp-details [data-summary-panel="dates"]');
    const rows = [...(panel?.querySelectorAll("tbody tr") ?? [])].map((row) => [...row.querySelectorAll("td")].map((cell) => cell.textContent?.trim() ?? ""));
    return { rows, text: panel?.innerText ?? "" };
  })()`);
  const baselineRow = report.details.rows.find((row) => row[0] === "Baseline");
  assert(baselineRow, "the Summary dates panel has no Baseline row");
  const subjectWindow = compared.rows.find((row) => row.activityId === subject.activityId);
  assert(subjectWindow, `no stored window for the selected activity ${subject.activityId}`);
  assert(baselineRow[1] === subjectWindow.start && baselineRow[2] === subjectWindow.finish, `Summary baseline window ${JSON.stringify(baselineRow)} does not match the stored window ${JSON.stringify(subjectWindow)}`);
  await captureState(page, "baseline-summary-en-1366");

  // Layout Options owns the same presentation block: hide, reload, confirm the
  // saved layout keeps the baseline bars hidden, then restore them.
  await page.evaluate(`(() => document.querySelector("[data-layout-options-open]")?.click())()`);
  await page.waitForSelector("[data-layout-options-dialog][open]", "layout options");
  await page.evaluate(`(() => {
    const toggle = document.querySelector("[data-layout-baseline]");
    toggle.checked = false;
    toggle.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  await sleep(1200);
  const hidden = await geometry(page);
  report.toggle = { hiddenBars: hidden.bars.length, toggle: hidden.toggle };
  assert(hidden.bars.length === 0, "unchecking baseline bars left baseline bars on the chart");

  await openProject(page);
  step("project reopened after save");
  const afterToggleReload = await geometry(page);
  step("geometry after toggle reload");
  report.toggle.afterReloadBars = afterToggleReload.bars.length;
  assert(afterToggleReload.bars.length === 0, "the saved layout did not keep baseline bars hidden after reload");

  // The toggle only exists inside the open dialog; reopen it to read the
  // presentation restored from the saved layout and then turn bars back on.
  step("opening layout options");
  await page.evaluate(`(() => document.querySelector("[data-layout-options-open]")?.click())()`);
  step("clicked layout options");
  await page.waitForSelector("[data-layout-options-dialog][open]", "layout options reopen");
  step("layout options open");
  const restoredToggle = await page.evaluate(`(() => {
    const toggle = document.querySelector("[data-layout-baseline]");
    return toggle ? { checked: toggle.checked, disabled: toggle.disabled } : null;
  })()`);
  report.toggle.afterReloadChecked = restoredToggle?.checked;
  assert(restoredToggle?.checked === false, "Layout Options did not restore the saved baseline toggle");
  await page.evaluate(`(() => {
    const toggle = document.querySelector("[data-layout-baseline]");
    toggle.checked = true;
    toggle.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  await page.evaluate(`(() => { document.querySelector("[data-layout-options-close]")?.click(); return true; })()`);
  await sleep(1200);
  const restored = await geometry(page);
  assert(restored.bars.length === report.afterReload.bars.length, "restoring the toggle did not redraw the stored baseline bars");
  await captureState(page, "baseline-restored-en-1366");

  await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false });
  await sleep(600);
  const wide = await page.evaluate(`(() => {
    const section = document.querySelector("#cp-gantt");
    return {
      bars: document.querySelectorAll('#cp-gantt [data-gantt-bar-kind="baseline"]').length,
      overflow: section ? section.scrollWidth - section.clientWidth : null,
    };
  })()`);
  report.wide = wide;
  assert(wide.bars === report.afterReload.bars.length, "baseline bars disappeared at 1920x1080");
  assert(wide.overflow !== null && wide.overflow <= 1, `Gantt overflows at 1920x1080: ${wide.overflow}px`);
  await captureState(page, "baseline-bars-en-1920");

  report.exceptions = report.exceptions.filter(Boolean);
  assert(report.exceptions.length === 0, `browser exceptions: ${report.exceptions.join(" | ")}`);
  assert(report.consoleErrors.length === 0, `console errors: ${report.consoleErrors.join(" | ")}`);
  assert(report.apiFailures.length === 0, `API 5xx: ${JSON.stringify(report.apiFailures)}`);

  report.finishedAt = new Date().toISOString();
  writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
  writeFileSync(join(evidenceDir, "activity-baseline-v26.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  chrome.stop();
}

main().catch(async (error) => {
  report.error = error instanceof Error ? error.message : String(error);
  try {
    writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
  } catch { /* best effort */ }
  console.error(error);
  process.exitCode = 1;
});
