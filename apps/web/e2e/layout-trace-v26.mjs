#!/usr/bin/env node
/**
 * Browser E2E for the Version 26 "Show on Top" / "Show on Bottom" layouts and
 * the Trace Logic bottom view. It drives the real local full-stack preview:
 * the activity table, Gantt, network, details, trace chain, menus and the
 * persisted per-project layout preferences are all exercised as served.
 *
 * The trace chain assertions use the persisted relationships of the seeded
 * Riverside Pump Station project (A130 has A120 as predecessor and A140, A145,
 * A150 as successors), so no fixture data is injected into the page.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4174 node e2e/layout-trace-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4174";
const outDir = join(artifactsDir, "layout-trace-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", "layout-trace-v26-2026-11-10");
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

const layoutState = `(() => {
  const split = document.querySelector(".cp-p6-split");
  const main = document.querySelector(".cp-main[data-details-split]");
  const details = document.querySelector("#cp-details");
  const trace = document.querySelector("[data-trace-logic]");
  const network = document.querySelector("[data-network-view]");
  const groups = [...document.querySelectorAll(".cp-trace-group")];
  return {
    topLayout: split?.dataset.topLayout ?? null,
    bottomLayout: main?.dataset.bottomLayout ?? null,
    bottomSurface: details?.dataset.bottomSurface ?? null,
    detailsHidden: details ? details.hasAttribute("hidden") : null,
    detailsVisible: Boolean(details && details.getClientRects().length),
    detailsLabelledBy: details?.getAttribute("aria-labelledby") ?? null,
    collapsed: main?.dataset.detailsCollapsed ?? null,
    gantt: Boolean(document.querySelector("#cp-gantt")),
    ganttRows: document.querySelectorAll("#cp-gantt [data-gantt-activity-id]").length,
    ganttLinks: document.querySelectorAll("#cp-gantt [data-gantt-link]").length,
    tableRows: document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]").length,
    splitter: Boolean(document.querySelector("[data-panel-splitter]")),
    selectedRow: document.querySelector('#cp-activity-grid tbody tr[aria-selected="true"]')?.dataset.activityId ?? null,
    network: network ? {
      nodes: Number(network.dataset.networkNodes),
      edges: Number(network.dataset.networkEdges),
      visible: Boolean(network.getClientRects().length),
    } : null,
    trace: trace ? {
      depth: Number(trace.dataset.traceDepthValue),
      depthSelect: document.querySelector("[data-trace-depth]")?.value ?? null,
      selected: document.querySelector("[data-trace-selected]")?.dataset.traceSelected ?? null,
      predecessors: groups[0] ? groups[0].querySelectorAll("[data-trace-activity-id]").length : 0,
      successors: groups[1] ? groups[1].querySelectorAll("[data-trace-activity-id]").length : 0,
      rows: [...document.querySelectorAll("[data-trace-activity-id]")].map((row) => ({
        id: row.dataset.traceActivityId,
        level: row.querySelector(".cp-trace-level")?.textContent?.trim() ?? null,
        edge: row.querySelector(".cp-trace-edge")?.textContent?.trim() ?? null,
      })),
      visible: Boolean(trace.getClientRects().length),
    } : null,
  };
})()`;

const viewMenuItems = `(() => [...document.querySelectorAll('[data-desktop-popup="view"] [data-desktop-command]')]
  .map((item) => ({
    command: item.dataset.desktopCommand,
    text: (item.textContent || "").trim(),
    disabled: item.hasAttribute("disabled"),
    checked: item.getAttribute("aria-checked") === "true",
    reason: item.getAttribute("title"),
  })))()`;

async function capture(page, name) {
  const file = `layout-trace-v26/${name}.png`;
  await page.screenshot(file);
  copyFileSync(join(artifactsDir, file), join(evidenceDir, `${name}.png`));
  screenshots.push(`${name}.png`);
  return file;
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

async function openMenu(page, menu) {
  const opened = await page.evaluate(`(() => {
    const trigger = document.querySelector('[data-desktop-menu=${JSON.stringify(menu)}]');
    if (!trigger) return false;
    if (trigger.getAttribute("aria-expanded") === "true") return true;
    trigger.click();
    return true;
  })()`);
  assert(opened, `menu trigger missing: ${menu}`);
  await sleep(200);
}

async function runMenuCommand(page, menu, command) {
  await openMenu(page, menu);
  const item = await page.evaluate(`(() => {
    const node = [...document.querySelectorAll('[data-desktop-command=${JSON.stringify(command)}]')]
      .find((entry) => entry.getClientRects().length > 0);
    if (!node) return null;
    return { disabled: node.hasAttribute("disabled"), reason: node.getAttribute("title") };
  })()`);
  assert(item, `menu command is not visible: ${command}`);
  assert(!item.disabled, `menu command is disabled: ${command} (${item.reason ?? "no reason"})`);
  await page.evaluate(`(() => {
    const item = [...document.querySelectorAll('[data-desktop-command=${JSON.stringify(command)}]')]
      .find((node) => node.getClientRects().length > 0);
    if (!item) return false;
    item.click();
    return true;
  })()`);
  await sleep(1100);
}

async function selectActivity(page, id) {
  const clicked = await page.evaluate(`(() => {
    const row = document.querySelector('#cp-activity-grid tbody tr[data-activity-id=${JSON.stringify(id)}]');
    if (!row) return false;
    row.click();
    return true;
  })()`);
  assert(clicked, `activity row not found: ${id}`);
  await sleep(800);
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

  const report = {
    contract: "cubi-layout-trace-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    capturedAt: new Date().toISOString(),
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
  };

  try {
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
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
    await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
    await sleep(1400);
    await setLanguage(page, "en");
    await page.waitForSelector("#cp-gantt [data-gantt-activity-id]", "gantt rows");

    await scenario("01", "باز شدن Activities با چیدمان پیش‌فرض جدول + گانت و جزئیات", async () => {
      const state = await page.evaluate(layoutState);
      assert(state.topLayout === "table-gantt", `default top layout is ${state.topLayout}`);
      assert(state.gantt && state.ganttRows === state.tableRows, "Gantt is not synchronised with the table");
      assert(state.ganttLinks > 0, "the seeded project has no drawn relationships");
      assert(state.bottomLayout === "details" && state.bottomSurface === "details", "default bottom surface is not Details");
      assert(state.detailsVisible && state.detailsLabelledBy === "cp-details-heading", "Details pane is not the labelled default surface");
      await capture(page, "01-default-table-gantt-details");
      return {
        topLayout: state.topLayout,
        bottomLayout: state.bottomLayout,
        rows: state.tableRows,
        links: state.ganttLinks,
      };
    });

    await scenario("02", "منوی View شش فرمان Show on Top و Show on Bottom را با وضعیت واقعی نشان می‌دهد", async () => {
      await openMenu(page, "view");
      const items = await page.evaluate(viewMenuItems);
      await capture(page, "02-view-menu-layout-and-trace");
      await openMenu(page, "view");
      const expected = [
        "view.top-table",
        "view.top-table-gantt",
        "view.top-network",
        "view.bottom-details",
        "view.bottom-trace",
        "view.bottom-none",
      ];
      for (const command of expected) {
        assert(items.some((item) => item.command === command), `View menu is missing ${command}`);
      }
      const checkedTop = items.find((item) => item.command === "view.top-table-gantt");
      const checkedBottom = items.find((item) => item.command === "view.bottom-details");
      assert(checkedTop?.checked === true, "Show on Top: Table + Gantt is not checked");
      assert(checkedBottom?.checked === true, "Show on Bottom: Details is not checked");
      assert(items.find((item) => item.command === "view.top-network")?.disabled === false, "Activity Network should be available with loaded relationships");
      return { items };
    });

    await scenario("03", "Show on Top: Activity Table فقط جدول را نشان می‌دهد", async () => {
      await runMenuCommand(page, "view", "view.top-table");
      const state = await page.evaluate(layoutState);
      assert(state.topLayout === "table-only", `top layout is ${state.topLayout}`);
      assert(!state.gantt, "Gantt is still rendered in table-only mode");
      assert(!state.splitter, "table splitter is still rendered in table-only mode");
      assert(state.tableRows === 14, `activity table lost rows: ${state.tableRows}`);
      assert(state.bottomLayout === "details" && state.detailsVisible, "Details pane did not survive the top layout switch");
      await capture(page, "03-top-table-only");
      return { topLayout: state.topLayout, rows: state.tableRows, gantt: state.gantt };
    });

    await scenario("04", "Show on Top: Activity Network شبکه واقعی فعالیت‌ها را از روابط ذخیره‌شده رسم می‌کند", async () => {
      await runMenuCommand(page, "view", "view.top-network");
      await page.waitForSelector("[data-network-view]", "activity network", 5000);
      const state = await page.evaluate(layoutState);
      assert(state.topLayout === "activity-network", `top layout is ${state.topLayout}`);
      assert(state.network && state.network.visible, "activity network is not visible");
      assert(state.network.nodes === 14, `network nodes are ${state.network.nodes}`);
      assert(state.network.edges === 15, `network edges are ${state.network.edges}`);
      assert(!state.gantt, "Gantt is still rendered in network mode");
      await capture(page, "04-top-activity-network");
      return { topLayout: state.topLayout, nodes: state.network.nodes, edges: state.network.edges };
    });

    await scenario("05", "بازگشت به جدول + گانت و انتخاب فعالیت متصل A130", async () => {
      await runMenuCommand(page, "view", "view.top-table-gantt");
      let state = await page.evaluate(layoutState);
      assert(state.topLayout === "table-gantt" && state.gantt, "table + Gantt did not come back");
      await selectActivity(page, "A130");
      state = await page.evaluate(layoutState);
      assert(state.selectedRow === "A130", `selected row is ${state.selectedRow}`);
      await capture(page, "05-activity-a130-selected");
      return { topLayout: state.topLayout, selectedRow: state.selectedRow };
    });

    await scenario("06", "Show on Bottom: Trace Logic زنجیرهٔ واقعی پیش‌نیاز و پس‌نیاز A130 را نشان می‌دهد", async () => {
      await runMenuCommand(page, "view", "view.bottom-trace");
      await page.waitForSelector("[data-trace-logic]", "trace logic", 5000);
      const state = await page.evaluate(layoutState);
      assert(state.bottomLayout === "trace-logic" && state.bottomSurface === "trace-logic", `bottom surface is ${state.bottomSurface}`);
      assert(state.detailsVisible && state.detailsLabelledBy === "cp-trace-heading", "Trace Logic is not the labelled bottom surface");
      assert(state.trace?.visible, "trace logic is not visible");
      assert(state.trace.selected === "A130", `trace selected ${state.trace?.selected}`);
      assert(state.trace.depth === 2 && state.trace.depthSelect === "2", "default trace depth is not 2");
      assert(state.trace.predecessors === 2, `expected 2 predecessor rows, saw ${state.trace.predecessors}`);
      assert(state.trace.successors === 6, `expected 6 successor rows, saw ${state.trace.successors}`);
      const ids = state.trace.rows.map((row) => row.id);
      for (const id of ["A120", "A110", "A140", "A145", "A150", "A155", "A160", "A170"]) {
        assert(ids.includes(id), `trace chain is missing ${id}`);
      }
      assert(state.trace.rows.every((row) => row.edge && row.edge.length > 1), "a trace row has no persisted link label");
      assert(state.trace.rows.some((row) => row.edge.startsWith("SS+5")), "the SS+5d relationship is not shown");
      await capture(page, "06-bottom-trace-logic-a130");
      return {
        selected: state.trace.selected,
        depth: state.trace.depth,
        predecessors: state.trace.predecessors,
        successors: state.trace.successors,
        rows: state.trace.rows,
      };
    });

    await scenario("07", "تغییر عمق ردیابی، زنجیره را به سطح ۱ محدود می‌کند", async () => {
      const changed = await page.evaluate(`(() => {
        const select = document.querySelector("[data-trace-depth]");
        if (!select) return false;
        select.value = "1";
        if (select.value !== "1") return false;
        select.dispatchEvent(new Event("change", { bubbles: true }));
        return true;
      })()`);
      assert(changed, "trace depth selector did not accept 1");
      await sleep(900);
      const state = await page.evaluate(layoutState);
      assert(state.trace.depth === 1, `trace depth is ${state.trace?.depth}`);
      assert(state.trace.predecessors === 1 && state.trace.successors === 3, `depth 1 rows are ${state.trace.predecessors}/${state.trace.successors}`);
      const stored = await page.evaluate(`(() => localStorage.getItem("cubi:workspace:trace-logic-depth"))()`);
      assert(stored === "1", `stored trace depth is ${stored}`);
      await capture(page, "07-trace-depth-1");
      return { depth: state.trace.depth, predecessors: state.trace.predecessors, successors: state.trace.successors, stored };
    });

    await scenario("08", "پرش از ردیف ردیابی، فعالیت مقصد را در جدول انتخاب می‌کند", async () => {
      const clicked = await page.evaluate(`(() => {
        const button = document.querySelector('[data-trace-goto="A120"]');
        if (!button) return false;
        button.click();
        return true;
      })()`);
      assert(clicked, "trace navigation button for A120 is missing");
      await sleep(900);
      const state = await page.evaluate(layoutState);
      assert(state.selectedRow === "A120", `selected row is ${state.selectedRow}`);
      assert(state.trace.selected === "A120", `trace selected ${state.trace?.selected}`);
      assert(state.bottomSurface === "trace-logic", "trace navigation dropped the Trace Logic bottom surface");
      await capture(page, "08-trace-goto-a120");
      return { selectedRow: state.selectedRow, bottomSurface: state.bottomSurface };
    });

    await scenario("09", "Show on Bottom: None ناحیهٔ پایین را می‌بندد و انتخاب را حفظ می‌کند", async () => {
      await runMenuCommand(page, "view", "view.bottom-none");
      const state = await page.evaluate(layoutState);
      assert(state.bottomLayout === "none", `bottom layout is ${state.bottomLayout}`);
      assert(state.detailsHidden === true && state.detailsVisible === false, "bottom pane is still visible");
      assert(state.collapsed === "true", `details allocation is ${state.collapsed}`);
      assert(state.selectedRow === "A120", "hiding the bottom pane lost the activity selection");
      await capture(page, "09-bottom-none");
      return { bottomLayout: state.bottomLayout, collapsed: state.collapsed, selectedRow: state.selectedRow };
    });

    await scenario("10", "چیدمان انتخابی پس از Refresh پایدار می‌ماند", async () => {
      await runMenuCommand(page, "view", "view.top-table");
      let before = await page.evaluate(layoutState);
      assert(before.topLayout === "table-only" && before.bottomLayout === "none", `pre-reload layout is ${before.topLayout}/${before.bottomLayout}`);
      const storage = await page.evaluate(`(() => {
        const rows = {};
        for (let index = 0; index < localStorage.length; index += 1) {
          const key = localStorage.key(index);
          if (key && key.startsWith("cubi:workspace:")) rows[key] = localStorage.getItem(key);
        }
        return rows;
      })()`);
      await page.reload();
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "rows after reload");
      await sleep(1600);
      const after = await page.evaluate(layoutState);
      assert(after.topLayout === "table-only", `top layout after reload is ${after.topLayout}`);
      assert(!after.gantt && !after.splitter, "Gantt or splitter came back after reload");
      assert(after.bottomLayout === "none" && after.detailsHidden === true, "bottom pane reopened after reload");
      assert(after.tableRows === 14, `rows after reload ${after.tableRows}`);
      await capture(page, "10-layout-persisted-after-reload");
      return { before: { top: before.topLayout, bottom: before.bottomLayout }, after: { top: after.topLayout, bottom: after.bottomLayout, collapsed: after.collapsed }, storage };
    });

    await scenario("11", "بازگرداندن چیدمان پیش‌فرض و بررسی نهایی", async () => {
      await runMenuCommand(page, "view", "view.top-table-gantt");
      await runMenuCommand(page, "view", "view.bottom-details");
      const state = await page.evaluate(layoutState);
      assert(state.topLayout === "table-gantt" && state.gantt, "table + Gantt was not restored");
      assert(state.bottomLayout === "details" && state.detailsVisible, "Details was not restored");
      assert(exceptions.length === 0, `uncaught page exceptions: ${JSON.stringify(exceptions.slice(0, 3))}`);
      assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors.slice(0, 3))}`);
      assert(apiFailures.length === 0, `API 5xx responses: ${JSON.stringify(apiFailures.slice(0, 3))}`);
      await capture(page, "11-restored-default-layout");
      return { top: state.topLayout, bottom: state.bottomLayout, exceptions: exceptions.length, consoleErrors: consoleErrors.length, apiFailures: apiFailures.length };
    });
  } finally {
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(outDir, "layout-trace-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(evidenceDir, "layout-trace-v26.json"), JSON.stringify(report, null, 2));
    page.cdp.close();
    chrome.cdp.close();
    await chrome.stop();
  }

  const failed = scenarios.filter((item) => item.status !== "pass");
  log(`\nScenarios: ${scenarios.length - failed.length} passed, ${failed.length} failed`);
  if (failed.length) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  process.stderr.write(`${error && error.stack ? error.stack : error}\n`);
  process.exit(1);
});
