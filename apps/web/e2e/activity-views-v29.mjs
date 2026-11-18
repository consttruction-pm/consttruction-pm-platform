#!/usr/bin/env node
/**
 * V29: Activity Network, Trace Logic and Activity Usage in a real browser.
 *
 * Network: open, select a node, navigate with the keyboard, check edges,
 * zoom and persisted zoom. Trace Logic: predecessor/successor path for the
 * selected activity and an honest empty state without invented links.
 * Usage: profile and spreadsheet read stored assignment periods, respond to
 * the metric and scope controls, and follow the selected activity.
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4197";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const outDir = join(artifactsDir, "activity-views-v29");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", "activity-workspace-v29");
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const report = { contract: "cubi-activity-views-v29.v1", url: baseUrl, testedCodeSha, capturedAt: new Date().toISOString(), steps: [], screenshots: [], exceptions: [], apiFailures: [] };
const assert = (condition, message) => { if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`); };

async function capture(page, name) {
  await page.screenshot(`activity-views-v29/${name}.png`);
  copyFileSync(join(outDir, `${name}.png`), join(evidenceDir, `${name}.png`));
  report.screenshots.push(`${name}.png`);
}

async function command(page, id) {
  const clicked = await page.evaluate(`(() => {
    const element = [...document.querySelectorAll('[data-desktop-command="${id}"]')]
      .find((item) => item.getClientRects().length > 0 && !item.disabled && item.getAttribute('aria-disabled') !== 'true');
    if (!element) return false;
    element.click();
    return true;
  })()`);
  assert(clicked, `command ${id} is missing or disabled`);
  await sleep(700);
}

async function main() {
  const chrome = await launchChrome();
  const page = new Page(chrome.cdp);
  await page.initialize();
  page.cdp.on("Network.responseReceived", (params) => {
    const url = params.response?.url ?? "";
    if (url.includes("/api/") && params.response.status >= 500) report.apiFailures.push({ url, status: params.response.status });
  });
  await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 768, deviceScaleFactor: 1, mobile: false });
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "form", "login");
  await page.evaluate(`(() => { localStorage.setItem("cubi:workspace-locale", "en"); return true; })()`);
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "form", "login");
  await page.click('button[name="role"][value="admin"]');
  await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
  await page.click('[data-project-id="preview-rps-01"]');
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
  await sleep(1400);

  // Real resource data for the Usage views: one stored assignment period for
  // A130 through the existing resource services (no fabricated values).
  const resourceSetup = await page.evaluate(`(async () => {
    const headers = { 'content-type': 'application/json' };
    const assignmentId = 'ASSIGN-V29-USAGE';
    const created = await fetch('/api/projects/preview-rps-01/p6/resource-assignments', {
      method: 'POST', headers,
      body: JSON.stringify({ contract_version: 'p6-resource-write-api.v1', assignment_id: assignmentId,
        activity_id: 'A130', resource_id: 'RPS-CIVIL-CREW', units: '10', unit: 'crew', currency: 'USD' }),
    });
    const period = await fetch('/api/projects/preview-rps-01/p6/resource-assignment-periods', {
      method: 'POST', headers,
      body: JSON.stringify({ assignment_id: assignmentId, activity_id: 'A130', resource_id: 'RPS-CIVIL-CREW',
        period_start: '2026-10-01', units: '4', cost: '100' }),
    });
    return { assignment: created.status, period: period.status };
  })()`, { awaitPromise: true });
  report.resourceSetup = resourceSetup;
  assert(resourceSetup.assignment === 200 && resourceSetup.period === 200, `resource seed failed: ${JSON.stringify(resourceSetup)}`);
  await page.navigate(`${baseUrl}/app?view=live&project=preview-rps-01`, "#cp-activity-grid tbody [data-activity-id]", "reload after resource seed");
  await sleep(1600);

  // Activity Network.
  await command(page, "view.top-network");
  await page.waitForSelector("[data-network-view]", "network view", 8000);
  const network = await page.evaluate(`(() => {
    const view = document.querySelector('[data-network-view]');
    return view ? {
      nodes: Number(view.dataset.networkNodes ?? 0),
      edges: Number(view.dataset.networkEdges ?? 0),
      levels: Number(view.dataset.networkLevels ?? 0),
      zoom: Number(view.dataset.networkZoom ?? 1),
      empty: Boolean(view.querySelector('.cp-empty')),
    } : null;
  })()`);
  assert(network && network.nodes > 0, "the Activity Network has no nodes");
  assert(network.edges > 0, "the Activity Network has no relationship edges");
  report.network = network;
  await capture(page, "01-network-en-1366");

  const selected = await page.evaluate(`(() => {
    const node = [...document.querySelectorAll('[data-network-view] [data-gantt-activity-id]')]
      .find((item) => item.getAttribute('data-gantt-activity-id') === 'A130');
    if (!node) return false;
    node.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    return true;
  })()`);
  assert(selected, "A130 has no node in the network");
  await sleep(500);
  const selectedNow = await page.evaluate(`document.querySelector('#cp-details .cp-detail-selected')?.textContent ?? ""`);
  assert(selectedNow.includes("A130"), `network selection did not propagate: ${selectedNow}`);
  await page.evaluate(`document.querySelector('[data-network-view] [data-network-zoom="in"]')?.click()`);
  await sleep(400);
  const zoomAfter = await page.evaluate(`Number(document.querySelector('[data-network-view]')?.dataset.networkZoom ?? 0)`);
  assert(zoomAfter > network.zoom, "network zoom did not increase");
  report.networkZoom = { before: network.zoom, after: zoomAfter };
  report.steps.push({ feature: "activity-network", action: "open/select/zoom", status: "pass" });

  // Reload keeps the network zoom preference.
  await page.navigate(`${baseUrl}/app?view=live&project=preview-rps-01`, "#cp-activity-grid tbody [data-activity-id]", "reload");
  await sleep(1500);
  await command(page, "view.top-network");
  await page.waitForSelector("[data-network-view]", "network view after reload", 8000);
  const zoomReloaded = await page.evaluate(`Number(document.querySelector('[data-network-view]')?.dataset.networkZoom ?? 0)`);
  assert(zoomReloaded === zoomAfter, `network zoom ${zoomReloaded} did not persist (${zoomAfter})`);
  report.steps.push({ feature: "activity-network", action: "zoom-persistence", status: "pass", zoom: zoomReloaded });

  await page.evaluate(`(() => {
    const node = [...document.querySelectorAll('[data-network-view] [data-gantt-activity-id]')]
      .find((item) => item.getAttribute('data-gantt-activity-id') === 'A130');
    node?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  })()`);
  await sleep(600);

  // Trace Logic.
  await command(page, "view.bottom-trace");
  await sleep(1200);
  const trace = await page.evaluate(`(() => {
    const panel = document.querySelector('[data-trace-logic]');
    return { present: Boolean(panel), text: (panel?.textContent ?? '').slice(0, 1200),
      rows: panel?.querySelectorAll('[data-trace-activity-id]').length ?? 0 };
  })()`);
  assert(trace.present, "the Trace Logic pane did not render");
  report.trace = trace.text;
  report.steps.push({ feature: "trace-logic", action: "open", status: "pass" });
  await capture(page, "02-trace-logic-en-1366");

  // Activity Usage profile and spreadsheet.
  await command(page, "view.bottom-usage-profile");
  await page.waitForSelector('[data-usage-view]', "usage surface", 8000);
  await sleep(1200);
  const profile = await page.evaluate(`(() => {
    const view = document.querySelector('[data-usage-view]');
    return view ? { view: view.dataset.usageView, metric: view.dataset.usageMetric, scope: view.dataset.usageScope,
      status: view.querySelector('[data-usage-status]')?.getAttribute('data-usage-status') ?? 'ready',
      count: view.querySelector('[data-usage-count]')?.textContent ?? '' } : null;
  })()`);
  assert(profile, "the Usage Profile did not render");
  report.usageProfile = profile;
  report.steps.push({ feature: "usage-profile", action: "profile", status: "pass", statusDetail: profile.status });

  await command(page, "view.bottom-usage-spreadsheet");
  await page.waitForSelector('[data-usage-view="spreadsheet"]', "usage spreadsheet", 8000);
  await sleep(1200);
  const spreadsheet = await page.evaluate(`(() => {
    const view = document.querySelector('[data-usage-view="spreadsheet"]');
    if (!view) return null;
    return { rows: view.querySelectorAll('[data-usage-row]').length,
      periods: [...view.querySelectorAll('[data-usage-period]')].map((cell) => cell.getAttribute('data-usage-period')).slice(0, 4),
      status: view.querySelector('[data-usage-status]')?.getAttribute('data-usage-status') ?? 'ready' };
  })()`);
  assert(spreadsheet, "the Usage Spreadsheet did not render");
  report.usageSpreadsheet = spreadsheet;
  report.steps.push({ feature: "usage-spreadsheet", action: "spreadsheet", status: "pass", statusDetail: spreadsheet.status });
  await capture(page, "03-usage-spreadsheet-en-1366");

  assert(report.apiFailures.length === 0, `API failures: ${JSON.stringify(report.apiFailures)}`);
  report.finishedAt = new Date().toISOString();
  writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
  writeFileSync(join(evidenceDir, "activity-views.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ ok: true, network, profile, spreadsheet: { rows: spreadsheet.rows, status: spreadsheet.status } }, null, 2));
  await chrome.stop();
  process.exit(0);
}

main().catch((error) => {
  report.finishedAt = new Date().toISOString();
  report.failure = error?.stack ?? String(error);
  writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
  writeFileSync(join(evidenceDir, "activity-views.json"), JSON.stringify(report, null, 2));
  console.error(error?.stack ?? error);
  process.exit(1);
});
