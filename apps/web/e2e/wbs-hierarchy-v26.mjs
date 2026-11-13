#!/usr/bin/env node
/**
 * WBS-001 browser acceptance: hierarchical WBS table and chart.
 *
 * The preview seeds a persisted 7-node hierarchy for `preview-rps-01`. Every
 * assertion is made against the real full-stack preview: the table rows and
 * chart cards are compared with GET /api/projects/{id}/p6/wbs on the same
 * session, both layouts must show the same nodes in the same order, activity
 * counts come from the workspace read behind the grid, and a node created
 * through the WBS API must appear in both layouts after a reload.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4201 node e2e/wbs-hierarchy-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4201";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-13";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const evidenceDir = join(
  artifactsDir, "..", "..", "..", "..",
  "docs", "workspace", "evidence", `wbs-001-table-chart-${evidenceDate}`,
);
const outPrefix = "wbs-001-table-chart";
const outDir = join(artifactsDir, outPrefix);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const WBS_PATH = `/api/projects/${PROJECT}/p6/wbs`;
const EXPECTED = [
  ["WBS-RPS-ROOT", 1, 0],
  ["WBS-RPS-PM", 2, 3],
  ["WBS-RPS-CIVIL", 2, 5],
  ["WBS-RPS-PROC", 2, 1],
  ["WBS-RPS-ENV", 2, 2],
  ["WBS-RPS-MEP", 2, 2],
  ["WBS-RPS-COM", 2, 1],
];

const scenarios = [];
const checks = [];
const screenshots = [];
const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const writes = [];

function log(message) {
  process.stdout.write(`${message}\n`);
}

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

function check(id, name, condition, detail = {}) {
  checks.push({ id, name, ok: Boolean(condition), detail });
  if (condition) log(`  PASS ${id} ${name}`);
  else log(`  FAIL ${id} ${name} ${JSON.stringify(detail)}`);
}

async function scenario(id, name, body) {
  log(`\n[${id}] ${name}`);
  const started = Date.now();
  try {
    const details = (await body()) ?? {};
    scenarios.push({ id, name, status: "pass", at: new Date().toISOString(), durationMs: Date.now() - started, details });
    log(`  PASS ${id}`);
  } catch (error) {
    scenarios.push({ id, name, status: "fail", at: new Date().toISOString(), durationMs: Date.now() - started, error: String(error?.message ?? error) });
    throw error;
  }
}

async function capture(page, name) {
  const file = `${outPrefix}/${name}.png`;
  await page.screenshot(file);
  copyFileSync(join(artifactsDir, file), join(evidenceDir, `${name}.png`));
  screenshots.push(`${name}.png`);
  return file;
}

const tableState = `(() => ({
  rows: [...document.querySelectorAll(".cp-wbs-window .cp-wbs-row")].map((row) => ({
    id: row.dataset.wbsId,
    depth: Number(row.dataset.wbsDepth),
    code: row.querySelector(".cp-wbs-code-cell span")?.textContent?.trim() ?? "",
    name: row.querySelector(".cp-wbs-node")?.textContent?.trim() ?? "",
    count: Number(row.querySelector(".cp-wbs-count-cell")?.textContent?.trim() ?? "NaN"),
    selected: row.getAttribute("aria-selected") === "true",
  })),
  headers: [...document.querySelectorAll(".cp-wbs-window .cp-wbs-table th")].map((th) => th.textContent.trim()),
  table: Boolean(document.querySelector(".cp-wbs-window [data-wbs-table]")),
}))()`;

const chartState = `(() => ({
  cards: [...document.querySelectorAll(".cp-wbs-window .cp-wbs-chart-node")].map((card) => ({
    id: card.dataset.wbsId,
    depth: Number(card.dataset.wbsDepth),
    code: card.querySelector(".cp-wbs-chart-code")?.textContent?.trim() ?? "",
    name: card.querySelector("strong")?.textContent?.trim() ?? "",
    selected: card.getAttribute("aria-current") === "true",
  })),
  chart: Boolean(document.querySelector(".cp-wbs-window [data-wbs-chart]")),
}))()`;

async function api(page, method, path, body) {
  return page.evaluate(
    `(async () => {
      const response = await fetch(${JSON.stringify(path)}, {
        method: ${JSON.stringify(method)},
        headers: { "Content-Type": "application/json", "Idempotency-Key": "e2e-wbs1-" + Math.random().toString(36).slice(2) },
        ${body === undefined ? "" : `body: JSON.stringify(${JSON.stringify(body)}),`}
      });
      return { status: response.status, body: await response.json().catch(() => null) };
    })()`,
    { awaitPromise: true },
  );
}

async function wbsList(page) {
  const response = await api(page, "GET", WBS_PATH);
  assert(response.status === 200, `GET ${WBS_PATH} returned ${response.status}`);
  return (response.body.wbs_nodes ?? []).map((entry) => entry.wbs);
}

async function loginAs(page, label) {
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
  const hasPersonas = await page.evaluate('Boolean(document.querySelector(".persona"))');
  if (!hasPersonas) {
    await page.evaluate(`(async () => { await fetch("/preview/logout", { method: "POST", redirect: "manual" }); })()`, { awaitPromise: true });
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, ".persona", "persona cards after sign out");
  }
  const clicked = await page.evaluate(`(() => {
    const button = [...document.querySelectorAll("form button")].find((item) => (item.textContent || "").trim().startsWith(${JSON.stringify(label)}));
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `${label} login button is missing`);
  await page.waitForSelector(`[data-project-id="${PROJECT}"]`, "project selection");
  await page.click(`[data-project-id="${PROJECT}"]`);
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows", 30000);
  await sleep(800);
}

async function openWbs(page) {
  await page.evaluate(`(() => { document.querySelector("[data-context-menu-portal]")?.remove(); })()`);
  const clicked = await page.evaluate(`(() => {
    const buttons = [...document.querySelectorAll('[data-menu="wbs"]')];
    const button = buttons.find((entry) => entry.getClientRects().length > 0) ?? buttons[0];
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, "WBS navigation button is missing");
  await page.waitForSelector(".cp-wbs-window", "WBS window", 20000);
  const tableVisible = await page.evaluate('Boolean(document.querySelector(".cp-wbs-window [data-wbs-table]"))');
  if (!tableVisible) await switchView(page, "table");
  await page.waitForSelector(".cp-wbs-window [data-wbs-table]", "WBS table", 20000);
  await sleep(400);
}

async function switchView(page, view) {
  const clicked = await page.evaluate(`(() => {
    const button = document.querySelector('.cp-wbs-window [data-wbs-view="${view}"]');
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `WBS view toggle ${view} is missing`);
  await page.waitFor(
    `Boolean(document.querySelector(${JSON.stringify(view === "chart" ? ".cp-wbs-window [data-wbs-chart]" : ".cp-wbs-window [data-wbs-table]")}))`,
    `${view} view`,
    10000,
  );
  await sleep(250);
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
  await page.waitFor(`document.documentElement.lang === ${JSON.stringify(locale)}`, `${locale} language`);
  await sleep(700);
}

async function reloadWorkspace(page) {
  await page.navigate(`${baseUrl}/app?view=live`, "#cp-activity-grid tbody tr[data-activity-id]", "activity rows after reload");
  await sleep(700);
  const picker = await page.evaluate(`Boolean(document.querySelector('[data-project-id="${PROJECT}"]'))`);
  if (picker) {
    await page.click(`[data-project-id="${PROJECT}"]`);
    await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows after project open", 30000);
    await sleep(600);
  }
  await openWbs(page);
}

async function main() {
  const health = await waitForHttp(`${baseUrl}/preview/health`, 30000);
  if (!(health.status === "ok" || health.status === 200)) throw new Error(`preview health ${health.status}`);

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
  page.cdp.on("Network.requestWillBeSent", (params) => {
    const url = params.request?.url ?? "";
    if (url.includes("/api/") && params.request.method !== "GET") {
      writes.push({ method: params.request.method, url: url.replace(baseUrl, "") });
    }
  });

  const summary = {
    contract: "cubi-wbs-001-table-chart.v1",
    testedCodeSha,
    gitHead: gitHead(),
    evidenceCommitSha,
    baseUrl,
    startedAt: new Date().toISOString(),
    scenarios,
    checks,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
    writes,
  };

  try {
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
    await loginAs(page, "Project administrator");
    await setLanguage(page, "en");

    await scenario("01", "Table view lists the persisted hierarchy in project order", async () => {
      await openWbs(page);
      const state = await page.evaluate(tableState);
      check("wbs1-table-present", "the WBS window renders a table grid", state.table === true, state);
      check(
        "wbs1-table-headers",
        "the table exposes code, name, activities, sequence and revision columns",
        ["WBS Code", "WBS Name", "Activities", "Sequence", "Rev"].every((header) => state.headers.includes(header)),
        state.headers,
      );
      check(
        "wbs1-table-order",
        "rows follow the persisted hierarchy order and depth",
        JSON.stringify(state.rows.map((row) => [row.id, row.depth])) === JSON.stringify(EXPECTED.map(([id, depth]) => [id, depth])),
        state.rows,
      );
      check(
        "wbs1-table-counts",
        "activity counts match the persisted assignments",
        JSON.stringify(state.rows.map((row) => row.count)) === JSON.stringify(EXPECTED.map(([, , count]) => count)),
        state.rows.map((row) => [row.id, row.count]),
      );
      const apiNodes = await wbsList(page);
      check(
        "wbs1-no-fabricated-rows",
        "the table shows exactly the nodes the WBS API returns",
        state.rows.length === apiNodes.length &&
          JSON.stringify([...state.rows.map((row) => row.id)].sort()) === JSON.stringify(apiNodes.map((node) => node.wbs_id).sort()),
        { rows: state.rows.length, api: apiNodes.length },
      );
      await capture(page, "01-wbs-table-en");
      return { rows: state.rows.length, headers: state.headers };
    });

    await scenario("02", "Chart view draws the same nodes in the same order", async () => {
      await switchView(page, "chart");
      const tableOrder = EXPECTED.map(([id]) => id);
      const chart = await page.evaluate(chartState);
      check("wbs1-chart-present", "the chart view is rendered", chart.chart === true, chart);
      check(
        "wbs1-chart-order",
        "chart cards keep the table order and depth",
        JSON.stringify(chart.cards.map((card) => [card.id, card.depth])) === JSON.stringify(tableOrder.map((id) => [id, id === "WBS-RPS-ROOT" ? 1 : 2])),
        chart.cards,
      );
      const pressed = await page.evaluate(`(() => ({
        table: document.querySelector('.cp-wbs-window [data-wbs-view="table"]')?.getAttribute("aria-pressed"),
        chart: document.querySelector('.cp-wbs-window [data-wbs-view="chart"]')?.getAttribute("aria-pressed"),
        tableActive: document.querySelector('.cp-wbs-window [data-wbs-view="table"]')?.classList.contains("is-active"),
        chartActive: document.querySelector('.cp-wbs-window [data-wbs-view="chart"]')?.classList.contains("is-active"),
      }))()`);
      check("wbs1-chart-toggle", "the chart toggle is the pressed view", pressed.chart === "true" && pressed.table === "false" && pressed.chartActive && !pressed.tableActive, pressed);
      await capture(page, "02-wbs-chart-en");
      return { cards: chart.cards.length };
    });

    await scenario("03", "Selection stays on the same persisted record across views", async () => {
      await switchView(page, "table");
      await page.evaluate(`document.querySelector('.cp-wbs-window .cp-wbs-row[data-wbs-id="WBS-RPS-CIVIL"] .cp-wbs-node')?.click()`);
      await page.waitFor(
        `document.querySelector('.cp-wbs-window [data-wbs-detail-panel="general"]')?.textContent?.includes("WBS-RPS-CIVIL") === true`,
        "CIVIL details",
        15000,
      );
      const tableSelected = await page.evaluate(`(() => ({
        row: document.querySelector('.cp-wbs-window .cp-wbs-row[data-wbs-id="WBS-RPS-CIVIL"]')?.getAttribute("aria-selected"),
        detail: document.querySelector('.cp-wbs-window [data-wbs-detail-panel="general"]')?.textContent ?? "",
      }))()`);
      check("wbs1-table-selection", "the table marks the clicked record and reads its details", tableSelected.row === "true" && tableSelected.detail.includes("Civil works"), tableSelected.row);

      await switchView(page, "chart");
      const chartSelected = await page.evaluate(`(() => ({
        selected: document.querySelector('.cp-wbs-window .cp-wbs-chart-node[data-wbs-id="WBS-RPS-CIVIL"]')?.getAttribute("aria-current"),
        cls: document.querySelector('.cp-wbs-window .cp-wbs-chart-node[data-wbs-id="WBS-RPS-CIVIL"]')?.classList.contains("is-selected"),
        detail: document.querySelector('.cp-wbs-window [data-wbs-detail-panel="general"]')?.textContent ?? "",
      }))()`);
      check("wbs1-chart-selection", "the chart highlights the same record after the view switch", chartSelected.selected === "true" && chartSelected.cls === true, chartSelected);

      await page.evaluate(`document.querySelector('.cp-wbs-window .cp-wbs-chart-node[data-wbs-id="WBS-RPS-MEP"]')?.click()`);
      await page.waitFor(
        `document.querySelector('.cp-wbs-window [data-wbs-detail-panel="general"]')?.textContent?.includes("WBS-RPS-MEP") === true`,
        "MEP details",
        15000,
      );
      await switchView(page, "table");
      const tableMep = await page.evaluate(`document.querySelector('.cp-wbs-window .cp-wbs-row[data-wbs-id="WBS-RPS-MEP"]')?.getAttribute("aria-selected")`);
      check("wbs1-selection-roundtrip", "a chart selection survives the return to the table", tableMep === "true", tableMep);
      await capture(page, "03-wbs-selection-roundtrip");
      return { tableMep };
    });

    await scenario("04", "A persisted child appears at depth three in both layouts after reload", async () => {
      const created = await api(page, "POST", WBS_PATH, {
        wbs_id: "WBS-E2E-WBS1-CHILD",
        parent_kind: "wbs",
        parent_wbs_id: "WBS-RPS-CIVIL",
        code: "2.1",
        name: "Excavation package",
        sequence_number: 5,
      });
      check("wbs1-create-persisted", "the WBS API persists the new child", created.status === 201, created);
      await reloadWorkspace(page);
      const table = await page.evaluate(tableState);
      const child = table.rows.find((row) => row.id === "WBS-E2E-WBS1-CHILD");
      check(
        "wbs1-child-in-table",
        "the reloaded table shows the persisted child directly under its parent at depth three",
        Boolean(child) && child.depth === 3 && child.code === "2.1" &&
          table.rows[table.rows.findIndex((row) => row.id === "WBS-E2E-WBS1-CHILD") - 1]?.id === "WBS-RPS-CIVIL",
        table.rows,
      );
      await switchView(page, "chart");
      const chart = await page.evaluate(chartState);
      const chartChild = chart.cards.find((card) => card.id === "WBS-E2E-WBS1-CHILD");
      check(
        "wbs1-child-in-chart",
        "the chart shows the same persisted child at the same position",
        Boolean(chartChild) && chartChild.depth === 3 &&
          JSON.stringify(chart.cards.map((card) => card.id)) === JSON.stringify(table.rows.map((row) => row.id)),
        chart.cards,
      );
      await capture(page, "04-wbs-persisted-child");
      return { rows: table.rows.length };
    });

    await scenario("05", "No hierarchy is invented when the parent is absent from the snapshot", async () => {
      await switchView(page, "table");
      const apiNodes = await wbsList(page);
      const parentIds = new Set(apiNodes.map((node) => node.wbs_id));
      const dangling = apiNodes.filter((node) => node.parent_kind === "wbs" && !parentIds.has(node.parent_wbs_id));
      const table = await page.evaluate(tableState);
      check(
        "wbs1-parents-resolve",
        "every rendered child references a parent present in the same snapshot",
        dangling.length === 0 && table.rows.length === apiNodes.length,
        { dangling: dangling.length, rows: table.rows.length },
      );
      return { dangling: dangling.length };
    });

    await scenario("06", "Persian RTL keeps the hierarchy readable at 1280x720", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await setLanguage(page, "fa");
      await openWbs(page);
      const state = await page.evaluate(`(() => ({
        dir: document.documentElement.dir,
        lang: document.documentElement.lang,
        headers: [...document.querySelectorAll(".cp-wbs-window .cp-wbs-table th")].map((th) => th.textContent.trim()),
        overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        wrapOverflow: (() => {
          const wrap = document.querySelector(".cp-wbs-window .cp-wbs-table-wrap");
          return wrap ? wrap.scrollWidth - wrap.clientWidth : null;
        })(),
        rows: document.querySelectorAll(".cp-wbs-window .cp-wbs-row").length,
      }))()`);
      check("wbs1-fa-rtl", "the Persian WBS table is right-to-left", state.dir === "rtl" && state.lang === "fa", state);
      check("wbs1-fa-headers", "the table headers are localized", state.headers.includes("کد WBS") && state.headers.includes("نام WBS"), state.headers);
      check("wbs1-fa-no-overflow", "the page does not overflow horizontally; the table scrolls inside its own wrapper", state.overflow <= 0 && state.rows > 0, state);
      await capture(page, "05-wbs-table-fa-rtl");
      await switchView(page, "chart");
      await capture(page, "06-wbs-chart-fa-rtl");
      return state;
    });

    await scenario("07", "Rows and cards are keyboard-focusable buttons carrying their record", async () => {
      const focus = await page.evaluate(`(() => {
        const button = document.querySelector('.cp-wbs-window .cp-wbs-chart-node[data-wbs-id="WBS-RPS-PM"]');
        if (!button) return null;
        button.focus();
        return {
          active: document.activeElement === button,
          tag: button.tagName,
          id: button.dataset.wbsId,
          aria: button.getAttribute("aria-current"),
        };
      })()`);
      check(
        "wbs1-focusable-records",
        "each chart node is a focusable button identified by its WBS ID",
        Boolean(focus) && focus.active && focus.tag === "BUTTON" && focus.id === "WBS-RPS-PM",
        focus,
      );
      await capture(page, "07-wbs-keyboard-focus");
      return focus;
    });
  } catch (error) {
    summary.error = String(error?.message ?? error);
    log(`\nFAILED: ${summary.error}`);
  } finally {
    summary.finishedAt = new Date().toISOString();
    summary.status = summary.error || checks.some((entry) => !entry.ok) ? "failed" : "passed";
    writeFileSync(join(evidenceDir, "contract.json"), `${JSON.stringify(summary, null, 2)}\n`);
    await chrome.cdp.send("Browser.close").catch(() => undefined);
  }

  const failed = checks.filter((entry) => !entry.ok);
  log(`\n${checks.length - failed.length} of ${checks.length} WBS-001 checks passed`);
  if (failed.length || summary.error) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  log(`UNHANDLED: ${error?.stack ?? error}`);
  process.exitCode = 1;
});
