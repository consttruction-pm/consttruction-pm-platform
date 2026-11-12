#!/usr/bin/env node
/**
 * Browser E2E for the Version 26 project tracking read window.
 *
 * Drives the real local full-stack preview on project preview-rps-01 with
 * headless Chrome. Every value comes from the real
 * `GET /api/projects/{id}/tracking/read` (`tracking-read-model.v1`) route,
 * which reads the published schedule FACT projection, persisted Activity
 * Master rows and persisted assignment facts. No response is mocked.
 *
 * Scenarios cover the summary and activity table, the bar chart, the
 * Gantt/profile buckets, resource analysis honesty, WBS grouping, sort and
 * scale controls, and the 1280x720, 1366x768 and 1920x1080 English and
 * 1280x720 Persian right-to-left layouts.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 node e2e/tracking-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "tracking-v26");
const evidenceDir = join(
  artifactsDir,
  "..",
  "..",
  "..",
  "..",
  "docs",
  "workspace",
  "evidence",
  `tracking-v26-${evidenceDate}`,
);
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
  scenarios.push({ ...details, id, name, status, at: new Date().toISOString() });
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

const pageState = `(() => {
  const host = document.querySelector("[data-tracking-page]");
  const rect = (element) => {
    if (!element) return null;
    const bounds = element.getBoundingClientRect();
    return { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height };
  };
  const cells = (row) => [...row.querySelectorAll("td")].map((cell) => (cell.textContent || "").trim());
  const rows = [...host?.querySelectorAll("[data-tracking-row]") ?? []].map((row) => ({
    id: row.dataset.activityId,
    critical: row.dataset.critical === "true",
    cells: cells(row),
  }));
  return {
    status: host?.dataset.trackingStatus ?? null,
    activeMenu: document.querySelector(".cp-workspace")?.dataset.activeMenu ?? null,
    direction: getComputedStyle(document.querySelector(".cp-workspace") || document.body).direction,
    innerWidth,
    innerHeight,
    pageOverflow: document.documentElement.scrollWidth > innerWidth + 1,
    toolbar: rect(host?.querySelector(".cp-tracking-toolbar")),
    panel: rect(host?.querySelector("[data-tracking-panel]")),
    summary: [...host?.querySelectorAll("[data-tracking-stat]") ?? []].map((item) => ({
      key: item.dataset.trackingStat,
      value: (item.querySelector("strong")?.textContent ?? "").trim(),
    })),
    project: host?.querySelector("[data-tracking-project]")?.textContent?.trim() ?? null,
    revision: host?.querySelector("[data-tracking-revision]")?.textContent?.trim() ?? null,
    run: host?.querySelector("[data-tracking-run]")?.textContent?.trim() ?? null,
    panelView: host?.querySelector("[data-tracking-panel]")?.dataset.trackingPanel ?? null,
    panelHeader: host?.querySelector(".cp-tracking-chart-head span")?.textContent?.trim() ?? null,
    rows,
    selectedView: host?.querySelector("[data-tracking-view][aria-selected='true']")?.dataset.trackingView ?? null,
    bars: [...host?.querySelectorAll("[data-tracking-bar]") ?? []].map((item) => ({
      bucket: item.dataset.trackingBar,
      text: item.textContent.trim(),
    })),
    profile: [...host?.querySelectorAll("[data-tracking-profile]") ?? []].map((item) => ({
      bucket: item.dataset.trackingProfile,
      text: item.textContent.trim(),
    })),
    groups: [...host?.querySelectorAll("[data-tracking-group]") ?? []].map((item) => ({
      group: item.dataset.trackingGroup,
      cells: cells(item),
    })),
    resources: [...host?.querySelectorAll("[data-tracking-resource]") ?? []].map((item) => ({
      id: item.dataset.trackingResource,
      text: item.textContent.trim(),
    })),
    resourceUnavailable: host?.querySelector("[data-tracking-resource-unavailable]")?.dataset.reason ?? null,
    resourceEmpty: Boolean(host?.querySelector("[data-tracking-panel='resource-analysis'] [data-tracking-empty]")),
    empty: Boolean(host?.querySelector("[data-tracking-empty]")),
    error: host?.querySelector("[data-tracking-error]")?.dataset.trackingError ?? null,
    text: host?.textContent ?? "",
  };
})()`;

async function capture(page, name) {
  const file = `tracking-v26/${name}.png`;
  await page.screenshot(file);
  copyFileSync(join(artifactsDir, file), join(evidenceDir, `${name}.png`));
  screenshots.push(`${name}.png`);
  return file;
}

async function loginAs(page) {
  const open = async () => {
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
  };
  await open();
  const hasProjects = await page.evaluate(
    `Boolean(document.querySelector('[data-project-id="preview-rps-01"]'))`,
  );
  if (!hasProjects) {
    const hasPersonas = await page.evaluate('Boolean(document.querySelector(".persona"))');
    if (!hasPersonas) {
      await page.evaluate(
        `fetch("/preview/logout", { method: "POST", redirect: "manual" }).then(() => true)`,
        { awaitPromise: true },
      );
      await open();
    }
    await page.click('button[name="role"][value="admin"]');
    await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
  }
  await page.click('[data-project-id="preview-rps-01"]');
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
  await sleep(1200);
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

async function openTracking(page) {
  const clicked = await page.evaluate(`(() => {
    const buttons = [...document.querySelectorAll('[data-menu="tracking"]')];
    const button = buttons.find((entry) => entry.getClientRects().length > 0) ?? buttons[0];
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, "Tracking menu button is missing");
  await page.waitFor(
    `document.querySelector("[data-tracking-page]")?.dataset.trackingStatus === "loaded"`,
    "tracking read",
    20000,
  );
  await sleep(250);
}

async function select(page, name, value) {
  const changed = await page.evaluate(`(() => {
    const select = document.querySelector('[data-tracking-page] [name="${name}"]');
    if (!select) return false;
    select.value = ${JSON.stringify(value)};
    if (select.value !== ${JSON.stringify(value)}) return false;
    select.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  assert(changed, `tracking select ${name} did not accept ${value}`);
  await page.waitFor(
    `document.querySelector("[data-tracking-page]")?.dataset.trackingStatus === "loaded"`,
    `${name} read`,
    20000,
  );
  await sleep(250);
}

async function view(page, name) {
  await page.click(`[data-tracking-view="${name}"]`);
  await page.waitFor(
    `document.querySelector("[data-tracking-panel]")?.dataset.trackingPanel === ${JSON.stringify(name)}`,
    `${name} panel`,
  );
  await sleep(150);
}

async function viewport(page, width, height) {
  await page.cdp.send("Emulation.setDeviceMetricsOverride", {
    width,
    height,
    deviceScaleFactor: 1,
    mobile: false,
  });
  await sleep(350);
}

async function main() {
  log(`CUBI tracking V26 E2E — ${baseUrl}`);
  await waitForHttp(`${baseUrl}/preview/health`, 30000);
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
    if (url.includes("/api/") && params.response.status >= 500) {
      apiFailures.push({ status: params.response.status, url });
    }
  });

  const report = {
    contract: "cubi-tracking-v26.v1",
    baseUrl,
    testedCodeSha,
    evidenceCommitSha,
    evidenceDate,
    project: "preview-rps-01",
    startedAt: new Date().toISOString(),
    viewport: "1280x720",
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
  };

  try {
    await viewport(page, 1280, 720);
    await loginAs(page);
    await setLanguage(page, "en");
    await openTracking(page);

    await scenario("01", "the Tracking window reads the published schedule and renders the summary and activity table", async () => {
      const state = await page.evaluate(pageState);
      assert(state.activeMenu === "tracking", `active menu ${state.activeMenu}`);
      assert(state.status === "loaded", `tracking status ${state.status}`);
      assert(state.error === null, `tracking error ${state.error}`);
      assert(state.project === "preview-rps-01", `project ${state.project}`);
      assert(state.revision === "7", `project revision ${state.revision}`);
      assert(state.run && state.run.length === 12, `calculation run identity ${state.run}`);
      assert(JSON.stringify(state.summary.map((item) => item.key)) === JSON.stringify([
        "activity-count",
        "not-started",
        "in-progress",
        "completed",
        "critical",
        "project-finish",
        "mean-percent",
        "diagnostics",
      ]), `summary keys ${state.summary.map((item) => item.key).join(",")}`);
      const summary = Object.fromEntries(state.summary.map((item) => [item.key, item.value]));
      assert(summary["activity-count"] === "14", `activity count ${summary["activity-count"]}`);
      assert(summary["not-started"] === "10", `not started ${summary["not-started"]}`);
      assert(summary["in-progress"] === "1", `in progress ${summary["in-progress"]}`);
      assert(summary["completed"] === "3", `completed ${summary["completed"]}`);
      assert(summary["critical"] === "7", `critical ${summary["critical"]}`);
      assert(summary["project-finish"] === "2026-12-03", `project finish ${summary["project-finish"]}`);
      assert(summary["mean-percent"] === "—", `mean percent must stay unset, got ${summary["mean-percent"]}`);
      assert(state.rows.length === 14, `table rows ${state.rows.length}`);
      const first = state.rows[0];
      assert(first.id === "A100", `first row ${first.id}`);
      assert(JSON.stringify(first.cells.slice(0, 9)) === JSON.stringify([
        "A100",
        "Project kickoff",
        "1",
        "Completed",
        "—",
        "2026-09-21",
        "2026-09-21",
        "12",
        "No",
      ]), `first row cells ${JSON.stringify(first.cells)}`);
      const critical = state.rows.find((row) => row.id === "A130");
      assert(critical && critical.critical, "A130 must be flagged critical");
      assert(critical.cells[8] === "Yes" && critical.cells[7] === "0", `critical row ${JSON.stringify(critical.cells)}`);
      assert(state.pageOverflow === false, "the tracking window overflows horizontally");
      assert(state.toolbar && state.toolbar.width > 0, "the tracking toolbar has no layout box");
      assert(state.panel && state.panel.width > 0, "the tracking panel has no layout box");
      assert(!/Oracle|Primavera|P6 Suite/i.test(state.text), "the tracking window leaks external product branding");
      assert(!/not connected yet/i.test(state.text), "the retired placeholder notice is still rendered");
      assert(/Read-only/.test(state.text), "the tracking window must state that it is read-only");
      await capture(page, "01-tracking-1280x720-en");
      return { summary, rows: state.rows.length, revision: state.revision, run: state.run };
    });

    await scenario("02", "the bar chart projects authoritative finish buckets", async () => {
      await view(page, "bar-chart");
      const state = await page.evaluate(pageState);
      assert(state.panelView === "bar-chart", `panel ${state.panelView}`);
      assert(state.selectedView === "bar-chart", `selected view ${state.selectedView}`);
      assert(state.bars.length === 10, `bar buckets ${state.bars.length}`);
      const first = state.bars[0];
      assert(first.bucket === "2026-09-21", `first bucket ${first.bucket}`);
      assert(first.text.startsWith("2026-09-212 · 0 critical"), `first bucket text ${first.text}`);
      assert(state.panelHeader === "week · start asc", `panel header ${state.panelHeader}`);
      await capture(page, "02-tracking-bar-chart");
      return { buckets: state.bars.length, first: first.text };
    });

    await scenario("03", "the Gantt/profile view projects start buckets and summed durations", async () => {
      await view(page, "gantt-profile");
      const state = await page.evaluate(pageState);
      assert(state.panelView === "gantt-profile", `panel ${state.panelView}`);
      assert(state.profile.length === 8, `profile buckets ${state.profile.length}`);
      assert(state.profile[0].bucket === "2026-09-21", `first profile bucket ${state.profile[0].bucket}`);
      assert(state.profile[0].text === "2026-09-213 · duration 0", `first profile text ${state.profile[0].text}`);
      await capture(page, "03-tracking-gantt-profile");
      return { buckets: state.profile.length, first: state.profile[0].text };
    });

    await scenario("04", "resource analysis shows only stored assignments and states an honest empty or unavailable case", async () => {
      await view(page, "resource-analysis");
      const state = await page.evaluate(pageState);
      assert(state.panelView === "resource-analysis", `panel ${state.panelView}`);
      const honest = state.resources.length > 0 || state.resourceEmpty || state.resourceUnavailable !== null;
      assert(honest, "resource analysis rendered neither rows nor an honest empty state");
      if (state.resourceEmpty) assert(/No resource assignments are stored/.test(state.text), "empty resource copy missing");
      if (state.resourceUnavailable !== null) {
        assert(state.resourceUnavailable === "resource_assignment_source_not_configured", `reason ${state.resourceUnavailable}`);
      }
      await capture(page, "04-tracking-resource-analysis");
      return {
        resources: state.resources.length,
        empty: state.resourceEmpty,
        unavailable: state.resourceUnavailable,
      };
    });

    await scenario("05", "WBS grouping, scale and sort change the server projection without inventing values", async () => {
      await view(page, "table");
      await select(page, "tracking-group", "wbs");
      const grouped = await page.evaluate(pageState);
      assert(grouped.groups.length >= 5, `WBS groups ${grouped.groups.length}`);
      const members = grouped.groups.reduce((total, group) => {
        const count = Number(group.cells[1]);
        assert(Number.isInteger(count) && count > 0, `group cells ${JSON.stringify(group.cells)}`);
        return total + count;
      }, 0);
      assert(members === 14, `grouped activities ${members}`);
      assert(grouped.rows.length === 14, `grouped table rows ${grouped.rows.length}`);

      await select(page, "tracking-scale", "month");
      await select(page, "tracking-sort", "total_float");
      await select(page, "tracking-direction", "desc");
      const sorted = await page.evaluate(pageState);
      assert(sorted.panelHeader === "month · total_float desc", `panel header ${sorted.panelHeader}`);
      const floats = sorted.rows.map((row) => Number(row.cells[7]));
      assert(floats.every(Number.isFinite), `float cells ${JSON.stringify(floats)}`);
      assert(
        floats.every((value, index) => index === 0 || floats[index - 1] >= value),
        `floats are not descending: ${JSON.stringify(floats)}`,
      );
      assert(floats[0] === Math.max(...floats), `highest float ${floats[0]}`);
      assert(floats.at(-1) === Math.min(...floats), `lowest float ${floats.at(-1)}`);
      await capture(page, "05-tracking-wbs-groups");
      return { groups: grouped.groups.length, members, firstFloat: floats[0], lastFloat: floats.at(-1) };
    });

    await scenario("06", "the Tracking window renders in Persian right-to-left at 1280x720", async () => {
      await setLanguage(page, "fa");
      // The language change re-renders the workspace; open the window again so
      // its labels and the server projection are read under the new locale.
      await openTracking(page);
      await view(page, "table");
      const state = await page.evaluate(pageState);
      assert(state.direction === "rtl", `workspace direction ${state.direction}`);
      assert(state.status === "loaded", `tracking status ${state.status}`);
      assert(/رهگیری/.test(state.text), "Persian tracking heading is missing");
      assert(/جدول پروژه/.test(state.text), "Persian table label is missing");
      assert(/فقط‌خواندنی/.test(state.text), "Persian read-only note is missing");
      assert(state.pageOverflow === false, "the Persian tracking window overflows horizontally");
      assert(state.toolbar && state.toolbar.x >= 0, "Persian toolbar has no layout box");
      assert(state.panel && state.panel.x >= 0, "Persian panel has no layout box");
      assert(state.rows.length === 14, `Persian table rows ${state.rows.length}`);
      await capture(page, "06-tracking-1280x720-fa");
      return { direction: state.direction, rows: state.rows.length };
    });

    await scenario("07", "the Tracking window fits 1366x768 and 1920x1080 without overflow", async () => {
      await setLanguage(page, "en");
      await openTracking(page);
      await view(page, "table");
      const results = [];
      for (const [width, height] of [[1366, 768], [1920, 1080]]) {
        await viewport(page, width, height);
        const state = await page.evaluate(pageState);
        assert(state.status === "loaded", `${width} status ${state.status}`);
        assert(state.pageOverflow === false, `${width} page overflow`);
        assert(state.toolbar && state.toolbar.width > 0, `${width} toolbar missing`);
        assert(state.toolbar.y + state.toolbar.height <= height + 1, `${width} toolbar below the fold`);
        assert(state.panel && state.panel.width > 0, `${width} panel missing`);
        assert(state.panel.y + state.panel.height <= height + 1, `${width} panel below the fold: ${JSON.stringify(state.panel)}`);
        assert(state.rows.length === 14, `${width} rows ${state.rows.length}`);
        results.push({ width, height, panel: state.panel, toolbar: state.toolbar });
        await capture(page, `07-tracking-${width}x${height}-en`);
      }
      await viewport(page, 1280, 720);
      return { viewports: results };
    });

    assert(exceptions.length === 0, `uncaught page exceptions: ${JSON.stringify(exceptions.slice(0, 3))}`);
    assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors.slice(0, 3))}`);
    assert(apiFailures.length === 0, `API 5xx responses: ${JSON.stringify(apiFailures.slice(0, 3))}`);
  } finally {
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(outDir, "tracking-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(evidenceDir, "tracking-v26.json"), JSON.stringify(report, null, 2));
    page.cdp.close();
    chrome.cdp.close();
    await chrome.stop();
  }

  const failed = scenarios.filter((item) => item.status !== "pass");
  log(`\nScenarios: ${scenarios.length - failed.length} passed, ${failed.length} failed`);
  if (failed.length) process.exitCode = 1;
}

main().catch((error) => {
  process.stderr.write(`${error && error.stack ? error.stack : error}\n`);
  process.exit(1);
});
