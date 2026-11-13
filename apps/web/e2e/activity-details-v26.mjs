#!/usr/bin/env node
/**
 * Activity Details (Priority Zero) acceptance.
 *
 * Verifies that the live bottom pane exposes the sixteen required Version 26
 * tabs plus the CUBI calendar tab, that every data tab issues its authoritative
 * read and distinguishes loading / empty / error from real rows, and that the
 * Customize Tabs display set survives a reload.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 \
 *   node e2e/activity-details-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-13";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const outDir = join(artifactsDir, "activity-details-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `activity-details-tabs-v26-${evidenceDate}`);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const REQUIRED_TABS = [
  "general", "status", "resources", "predecessors", "successors", "relationships",
  "codes", "notebook", "steps", "wps-docs", "expenses", "issues", "risks",
  "summary", "udfs", "update-history",
];
const DATA_TABS = ["resources", "expenses", "issues", "risks", "steps", "udfs", "update-history"];

const report = {
  contract: "cubi-activity-details-tabs-v26.v1",
  url: baseUrl,
  testedCodeSha,
  gitHead: gitHead(),
  capturedAt: new Date().toISOString(),
  tabs: [],
  data: {},
  writes: {},
  customize: null,
  screenshots: [],
  exceptions: [],
  consoleErrors: [],
  apiFailures: [],
};

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

async function poll(page, expression, timeout = 15000) {
  const started = Date.now();
  while (Date.now() - started < timeout) {
    if (await page.evaluate(expression)) return true;
    await sleep(250);
  }
  return false;
}

async function submitWriteForm(page, tab, values) {
  const outcome = await page.evaluate(`(() => {
    const form = document.querySelector('#cp-details [data-details-form="${tab}"]');
    if (!form) return { error: "form missing" };
    const values = ${JSON.stringify(values)};
    for (const [name, value] of Object.entries(values)) {
      const field = form.querySelector('[name="' + name + '"]');
      if (!field) return { error: "field missing: " + name };
      field.value = value;
      field.dispatchEvent(new Event("input", { bubbles: true }));
      field.dispatchEvent(new Event("change", { bubbles: true }));
    }
    const submit = form.querySelector('button[type="submit"]');
    if (!submit) return { error: "submit missing" };
    submit.click();
    return { submitted: true };
  })()`);
  assert(outcome?.submitted, `${tab} write form could not be submitted: ${JSON.stringify(outcome)}`);
  const settled = await poll(page, `(() => {
    const form = document.querySelector('#cp-details [data-details-form="${tab}"]');
    const slot = form?.querySelector("[data-details-form-message]");
    return Boolean(slot && (slot.dataset.state === "ok" || slot.dataset.state === "error"));
  })()`);
  const state = await page.evaluate(`(() => {
    const form = document.querySelector('#cp-details [data-details-form="${tab}"]');
    const slot = form?.querySelector("[data-details-form-message]");
    return { state: slot?.dataset.state ?? null, text: slot?.textContent ?? "" };
  })()`);
  assert(settled, `${tab} write did not settle: ${JSON.stringify(state)}`);
  assert(state.state === "ok", `${tab} write failed: ${state.text}`);
  return state;
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
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "form", "login");
  await page.click('button[name="role"][value="admin"]');
  await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
  await page.click('[data-project-id="preview-rps-01"]');
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
  await sleep(1600);
  await page.click("#cp-activity-grid tbody tr[data-activity-id]");
  await page.waitForSelector('#cp-details [data-detail-tab="general"]', "details tabs");
  await sleep(1200);

  report.tabs = await page.evaluate(`(() => [...document.querySelectorAll('#cp-details [data-detail-tab]')].map((tab) => tab.dataset.detailTab))()`);
  assert(report.tabs.length === REQUIRED_TABS.length + 1, `expected ${REQUIRED_TABS.length + 1} tabs, got ${report.tabs.length}`);
  assert(JSON.stringify(report.tabs.slice(0, REQUIRED_TABS.length)) === JSON.stringify(REQUIRED_TABS), "required tab order is wrong");
  assert(report.tabs.at(-1) === "calendar", "calendar tab must stay last");

  for (const tab of DATA_TABS) {
    await page.evaluate(`(() => { const b = document.querySelector('#cp-details [data-detail-tab="${tab}"]'); if (b) b.click(); return Boolean(b); })()`);
    await sleep(900);
    const state = await page.evaluate(`(() => {
      const panel = document.querySelector('#cp-details [data-detail-panel="${tab}"]');
      return {
        text: panel?.innerText ?? "",
        rows: panel?.querySelectorAll("tbody tr").length ?? 0,
        loading: Boolean(panel?.querySelector("[data-details-loading]")),
        error: Boolean(panel?.querySelector(".cp-detail-error")),
        refresh: Boolean(panel?.querySelector("[data-details-refresh]")),
      };
    })()`);
    report.data[tab] = state;
    assert(state.refresh, `${tab} must expose a Reload action`);
    assert(!state.loading, `${tab} should have finished loading`);
    assert(!state.error, `${tab} reported a read error: ${state.text.slice(0, 180)}`);
  }

  // Populated Steps evidence: the seeded earthworks activity carries three
  // stored step definitions in sequence order.
  await page.evaluate(`(() => { document.querySelector('#cp-activity-grid tbody tr[data-activity-id="A130"]')?.click(); return true; })()`);
  await sleep(1200);
  await page.evaluate(`(() => { document.querySelector('#cp-details [data-detail-tab="steps"]')?.click(); return true; })()`);
  await sleep(900);
  const stepsPanel = await page.evaluate(`(() => {
    const panel = document.querySelector('#cp-details [data-detail-panel="steps"]');
    return { rows: panel?.querySelectorAll("tbody tr").length ?? 0, text: panel?.innerText ?? "", error: Boolean(panel?.querySelector(".cp-detail-error")) };
  })()`);
  report.steps = stepsPanel;
  assert(!stepsPanel.error, `steps read reported an error: ${stepsPanel.text.slice(0, 180)}`);
  assert(stepsPanel.rows >= 3, `expected seeded steps, got ${stepsPanel.rows} rows`);
  assert(stepsPanel.text.includes("Cut and fill"), "seeded step description is missing");

  // Write path: create one authoritative record from each editable tab, then
  // prove the pane reloads the stored rows rather than trusting local state.
  const today = new Date().toISOString().slice(0, 10);
  const WRITES = [
    {
      tab: "resources",
      values: { resourceId: "RPS-CIVIL-CREW", roleId: "", units: "12", plannedCost: "900", currency: "USD", note: "E2E assignment" },
      expect: "RPS-CIVIL-CREW",
    },
    {
      tab: "expenses",
      values: { name: "E2E concrete", category: "material", currency: "USD", plannedCost: "1500", note: "E2E expense" },
      expect: "E2E concrete",
    },
    {
      tab: "issues",
      values: { title: "E2E schedule risk", description: "Created by the Activity Details acceptance run.", issueType: "schedule", status: "open", priority: "high", owner: "e2e-planner", dateIdentified: today, dueDate: "" },
      expect: "E2E schedule risk",
    },
  ];
  for (const write of WRITES) {
    await page.evaluate(`(() => { document.querySelector('#cp-details [data-detail-tab="${write.tab}"]')?.click(); return true; })()`);
    await sleep(500);
    const settled = await submitWriteForm(page, write.tab, write.values);
    const panel = await page.evaluate(`(() => {
      const panel = document.querySelector('#cp-details [data-detail-panel="${write.tab}"]');
      return { rows: panel?.querySelectorAll("tbody tr").length ?? 0, text: panel?.innerText ?? "" };
    })()`);
    report.writes[write.tab] = { message: settled.text, rows: panel.rows, stored: panel.text.includes(write.expect) };
    assert(panel.rows > 0, `${write.tab} did not show a stored row after saving`);
    assert(panel.text.includes(write.expect), `${write.tab} did not reload the stored record`);
  }

  // Customize Tabs: hide Status, apply, confirm, reload and confirm again.
  await page.evaluate(`(() => document.querySelector("[data-details-customize-open]")?.click())()`);
  await page.waitForSelector("[data-details-customize-dialog][open]", "customize dialog");
  await page.evaluate(`(() => {
    const dialog = document.querySelector("[data-details-customize-dialog]");
    const choose = [...dialog.querySelectorAll("[data-customize-tab]")].find((item) => item.dataset.customizeTab === "status" && item.dataset.customizeSide === "display");
    choose?.click();
    dialog.querySelector("[data-customize-remove]")?.click();
    return true;
  })()`);
  await page.click("[data-details-customize-ok]");
  await sleep(700);
  const afterApply = await page.evaluate(`(() => [...document.querySelectorAll('#cp-details [data-detail-tab]')].map((tab) => tab.dataset.detailTab))()`);
  assert(!afterApply.includes("status"), "status tab was not removed");
  await page.reload('#cp-details [data-detail-tab="general"]', "reload after customize");
  await sleep(1200);
  const afterReload = await page.evaluate(`(() => [...document.querySelectorAll('#cp-details [data-detail-tab]')].map((tab) => tab.dataset.detailTab))()`);
  report.customize = { afterApply, afterReload };
  assert(!afterReload.includes("status"), "customize display set did not survive reload");

  // Restore defaults for the next audit.
  await page.evaluate(`(() => {
    document.querySelector("[data-details-customize-open]")?.click();
    const dialog = document.querySelector("[data-details-customize-dialog]");
    dialog?.querySelector("[data-customize-default]")?.click();
    dialog?.querySelector("[data-details-customize-ok]")?.click();
    return true;
  })()`);

  await page.screenshot("activity-details-v26/details-en-1366.png");
  copyFileSync(join(outDir, "details-en-1366.png"), join(evidenceDir, "details-en-1366.png"));
  report.screenshots.push("details-en-1366.png");
  report.finishedAt = new Date().toISOString();
  writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
  writeFileSync(join(evidenceDir, "activity-details-tabs-v26.json"), JSON.stringify(report, null, 2));
  assert(report.exceptions.length === 0, `browser exceptions: ${report.exceptions.join(" | ")}`);
  assert(report.consoleErrors.length === 0, `console errors: ${report.consoleErrors.join(" | ")}`);
  assert(report.apiFailures.length === 0, `api failures: ${JSON.stringify(report.apiFailures)}`);
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  chrome.stop();
}

main().catch(async (error) => {
  report.finishedAt = new Date().toISOString();
  report.failure = String(error);
  writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
  writeFileSync(join(evidenceDir, "activity-details-tabs-v26.json"), JSON.stringify(report, null, 2));
  process.stderr.write(`${error?.stack ?? error}\n`);
  process.exit(1);
});
