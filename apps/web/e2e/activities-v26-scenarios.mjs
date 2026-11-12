#!/usr/bin/env node
/**
 * Execute the eighteen mandatory browser scenarios for the Activities window
 * against the real full-stack preview, capture real screenshots, and record
 * the evidence used by docs/qa/ACTIVITIES_V26_COMPLIANCE_MATRIX_2026-11-08.md.
 *
 * Every scenario drives the real workspace, dialogs and read/write routes; no
 * fixture values are injected into the UI. The four relationship types are
 * exercised by creating and then deleting two temporary relations through the
 * real P6 relationship HTTP route, so the preview database is left unchanged.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4174 node e2e/activities-v26-scenarios.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4174";
const outDir = join(artifactsDir, "activities-v26");
const visualDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "screenshots", "visual");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence");
mkdirSync(outDir, { recursive: true });
mkdirSync(visualDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const scenarios = [];
let currentScenario = null;

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
  currentScenario = { id, name };
  log(`\n[${id}] ${name}`);
  try {
    const details = (await body()) ?? {};
    record(id, name, "pass", details);
  } catch (error) {
    record(id, name, "fail", { error: String(error && error.stack ? error.stack : error) });
    throw error;
  } finally {
    currentScenario = null;
  }
}

/** Save a capture into the run artifacts and the durable visual evidence set. */
async function capture(page, name, publishedNumber) {
  const file = `activities-v26/${name}.png`;
  await page.screenshot(file);
  if (publishedNumber) {
    copyFileSync(join(artifactsDir, file), join(visualDir, `${publishedNumber}-${name}.png`));
  }
  return file;
}

const workspaceState = `(() => {
  const details = document.querySelector("#cp-details");
  const table = [...document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]")];
  const gantt = [...document.querySelectorAll("#cp-gantt [data-gantt-activity-id]")];
  const split = document.querySelector("[data-panel-split]");
  const main = document.querySelector(".cp-main");
  const linkTypes = {};
  for (const link of document.querySelectorAll("#cp-gantt [data-gantt-link]")) {
    linkTypes[link.dataset.linkType] = (linkTypes[link.dataset.linkType] || 0) + 1;
  }
  const scrollables = [...document.querySelectorAll("#cp-gantt *")].filter((element) => element.scrollWidth > element.clientWidth + 4);
  const filterHeader = document.querySelector("[data-active-filter]");
  return {
    rowIds: table.map((row) => row.dataset.activityId),
    ganttIds: gantt.map((row) => row.dataset.ganttActivityId),
    sameOrder: table.length === gantt.length && table.every((row, index) => row.dataset.activityId === gantt[index]?.dataset.ganttActivityId),
    bands: document.querySelectorAll(".cp-p6-wbs-band").length,
    selectedRow: document.querySelector('#cp-activity-grid tbody tr[aria-selected="true"]')?.dataset.activityId ?? null,
    selectedGantt: document.querySelector('#cp-gantt [data-gantt-activity-id][aria-pressed="true"]')?.dataset.ganttActivityId ?? null,
    detailsText: document.querySelector("#cp-details .cp-details-id")?.textContent?.trim() ?? null,
    detailsVisible: Boolean(details && details.getClientRects().length > 0),
    splitTable: split?.style.getPropertyValue("--cp-split-table") ?? null,
    splitDetails: main?.style.getPropertyValue("--cp-split-primary") ?? null,
    tabs: [...document.querySelectorAll("[data-detail-tab]")].map((tab) => tab.dataset.detailTab),
    activeTab: document.querySelector("[data-detail-tab].is-active")?.dataset.detailTab ?? null,
    filterLabel: filterHeader?.textContent?.trim() ?? null,
    activeFilterId: filterHeader?.getAttribute("data-active-filter") ?? null,
    scale: document.querySelector("[data-gantt-scale][aria-pressed='true']")?.dataset.ganttScale ?? null,
    lang: document.documentElement.lang,
    dir: getComputedStyle(document.body).direction,
    progressLines: document.querySelectorAll("[data-gantt-progress-line]").length,
    dataDateLines: document.querySelectorAll("[data-gantt-data-date]").length,
    linkTypes,
    barCount: document.querySelectorAll("#cp-gantt [data-gantt-bar-kind]").length,
    header: [...document.querySelectorAll("#cp-activity-grid thead th")].map((th) => th.textContent.trim()),
    scrollables: scrollables.map((element) => ({
      tag: element.tagName,
      className: typeof element.className === "string" ? element.className : "",
      scrollWidth: Math.round(element.scrollWidth),
      clientWidth: Math.round(element.clientWidth),
    })),
  };
})()`;

const tableIds = `(() => [...document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]")].map((row) => row.dataset.activityId))()`;

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

async function openCommand(page, command) {
  const clicked = await page.evaluate(`(() => {
    const buttons = [...document.querySelectorAll('[data-desktop-command=${JSON.stringify(command)}]')];
    const button = buttons.find((item) => item.getClientRects().length > 0);
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `command button not visible: ${command}`);
  await sleep(500);
}

async function openDialog(page, name) {
  const dialogName = name.replace(/^dialog\./, "");
  // A pending workspace re-render can replace the shell right after the click,
  // so retry against the live DOM before failing.
  let lastError = null;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const clicked = await page.evaluate(`(() => {
      const buttons = [...document.querySelectorAll('[data-desktop-command=${JSON.stringify(name)}]')];
      const button = buttons.find((item) => item.getClientRects().length > 0);
      if (!button) return false;
      button.click();
      return true;
    })()`);
    if (!clicked) {
      await sleep(500);
      continue;
    }
    try {
      await page.waitForSelector(`[data-desktop-dialog="${dialogName}"][open]`, `${name} dialog`, 2500);
      await sleep(250);
      return;
    } catch (error) {
      lastError = error;
      await sleep(600);
    }
  }
  assert(false, `dialog button not visible or dialog did not open: ${name}${lastError ? ` (${lastError.message})` : ""}`);
}

async function submitDialog(page, name) {
  await page.evaluate(`(() => {
    document.querySelector('[data-desktop-dialog="${name}"]')?.querySelector("[data-dialog-ok]")?.click();
    return true;
  })()`);
  await page.waitFor(
    `(() => { const dialog = document.querySelector('[data-desktop-dialog="${name}"]'); return !dialog || !dialog.hasAttribute("open"); })()`,
    `${name} dialog closed`,
    5000,
  );
  await sleep(1000);
}

async function setSelect(page, selector, value) {
  const ok = await page.evaluate(`(() => {
    const select = document.querySelector(${JSON.stringify(selector)});
    if (!select) return false;
    select.value = ${JSON.stringify(value)};
    if (select.value !== ${JSON.stringify(value)}) return false;
    select.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  assert(ok, `could not set ${selector} to ${value}`);
}

async function setInput(page, selector, value) {
  const ok = await page.evaluate(`(() => {
    const input = document.querySelector(${JSON.stringify(selector)});
    if (!input) return false;
    input.value = ${JSON.stringify(value)};
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  assert(ok, `could not fill ${selector}`);
}

async function setCheckbox(page, selector, checked) {
  const ok = await page.evaluate(`(() => {
    const input = document.querySelector(${JSON.stringify(selector)});
    if (!input) return false;
    input.checked = ${checked ? "true" : "false"};
    input.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  assert(ok, `could not toggle ${selector}`);
}

async function dispatchKey(page, key, code, keyCode, modifiers = 0) {
  await page.cdp.send("Input.dispatchKeyEvent", { type: "keyDown", key, code, windowsVirtualKeyCode: keyCode, nativeVirtualKeyCode: keyCode, modifiers });
  await sleep(60);
  await page.cdp.send("Input.dispatchKeyEvent", { type: "keyUp", key, code, windowsVirtualKeyCode: keyCode, nativeVirtualKeyCode: keyCode, modifiers });
  await sleep(500);
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
    contract: "cubi-activities-v26-scenarios.v1",
    baseUrl,
    gitHead: gitHead(),
    capturedAt: new Date().toISOString(),
    scenarios,
    screenshots: [],
    exceptions,
    consoleErrors,
    apiFailures,
  };

  try {
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
    await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
    await sleep(1400);
    await setLanguage(page, "en");
    await page.waitForSelector("#cp-gantt [data-gantt-activity-id]", "gantt rows");

    // Start every run from an unfiltered, WBS-grouped, details-visible layout.
    await openDialog(page, "dialog.filters");
    await setCheckbox(page, '[data-desktop-dialog="filters"] input[name="filterAllActivities"]', true);
    await submitDialog(page, "filters");
    if ((await page.evaluate(`document.querySelectorAll(".cp-p6-wbs-band").length`)) === 0) {
      await openCommand(page, "edit.group-wbs");
      await sleep(800);
    }
    if (!(await page.evaluate(`(() => { const details = document.querySelector("#cp-details"); return Boolean(details && details.getClientRects().length); })()`))) {
      await openCommand(page, "view.toggle-details");
      await sleep(700);
    }

    await scenario("01", "بازکردن پنجره Activities", async () => {
      const state = await page.evaluate(workspaceState);
      assert(state.rowIds.length === 14, `expected 14 RPS activity rows, saw ${state.rowIds.length}`);
      assert(state.ganttIds.length === 14, `expected 14 Gantt rows, saw ${state.ganttIds.length}`);
      assert(state.sameOrder, "table and Gantt rows are not in the same order");
      assert(state.bands > 0, "WBS bands are not rendered");
      assert(state.barCount >= 14, `expected drawn bars, saw ${state.barCount}`);
      const officialTabs = state.tabs.filter((id) => id !== "calendar");
      // CUBI implements the sixteen desktop tabs from the Version 26
      // Activity Details topic. Tasks is EPPM-only; Discussion and Feedback are
      // deferred by docs/workspace/architecture/workspace-window-inventory.md.
      const expectedTabs = [
        "general", "status", "resources", "predecessors", "successors", "relationships",
        "codes", "notebook", "steps", "wps-docs", "expenses", "issues", "risks",
        "summary", "udfs", "update-history",
      ];
      assert(
        officialTabs.length === expectedTabs.length && expectedTabs.every((id) => officialTabs.includes(id)),
        `expected the 16 official detail tabs, saw ${officialTabs.length}: ${officialTabs.join(",")}`,
      );
      assert(!officialTabs.includes("tasks"), "Tasks is EPPM-only and must not be offered");
      assert(!officialTabs.includes("discussion"), "Discussion is deferred for the desktop contract");
      assert(!officialTabs.includes("feedback"), "Feedback is deferred for the desktop contract");
      report.screenshots.push(await capture(page, "01-activities-window-en-1280", 74));
      return { rowIds: state.rowIds, bands: state.bands, tabs: state.tabs, bars: state.barCount };
    });

    await scenario("02", "انتخاب فعالیت و بررسی هماهنگی جدول، Gantt و Details", async () => {
      await page.evaluate(`(() => {
        const row = document.querySelector('#cp-activity-grid tbody tr[data-activity-id="A130"]');
        if (!row) return false;
        row.click();
        return true;
      })()`);
      await sleep(900);
      const state = await page.evaluate(workspaceState);
      assert(state.selectedRow === "A130", `table selection is ${state.selectedRow}`);
      assert(state.selectedGantt === "A130", `Gantt selection is ${state.selectedGantt}`);
      assert(String(state.detailsText).startsWith("A130"), `details heading is ${state.detailsText}`);
      report.screenshots.push(await capture(page, "02-activity-selected-sync-en-1280", 75));
      return { selectedRow: state.selectedRow, selectedGantt: state.selectedGantt, detailsText: state.detailsText };
    });

    await scenario("03", "باز و بسته کردن Activity Details", async () => {
      const before = await page.evaluate(workspaceState);
      assert(before.detailsVisible, "details pane should start open");
      await openCommand(page, "view.toggle-details");
      await sleep(700);
      const closed = await page.evaluate(workspaceState);
      assert(!closed.detailsVisible, "details pane did not close");
      report.screenshots.push(await capture(page, "03-details-closed-en-1280", 76));
      await openCommand(page, "view.toggle-details");
      await sleep(700);
      const reopened = await page.evaluate(workspaceState);
      assert(reopened.detailsVisible, "details pane did not reopen");
      assert(String(reopened.detailsText).startsWith("A130"), "reopened details lost the selection");
      report.screenshots.push(await capture(page, "04-details-open-en-1280", 77));
      return { before: before.detailsVisible, closed: closed.detailsVisible, reopened: reopened.detailsVisible };
    });

    await scenario("04", "تغییر ارتفاع و عرض نواحی", async () => {
      const before = await page.evaluate(workspaceState);
      const tableDrag = await page.drag("[data-panel-splitter]", 120, 0);
      await sleep(500);
      const detailsDrag = await page.drag("[data-details-splitter]", 0, 26);
      await sleep(700);
      const after = await page.evaluate(workspaceState);
      const tablePercent = Number.parseFloat(after.splitTable);
      const detailsPercent = Number.parseFloat(after.splitDetails);
      assert(Number.isFinite(tablePercent) && tablePercent >= 25 && tablePercent <= 75, `table split out of bounds: ${after.splitTable}`);
      assert(Number.isFinite(detailsPercent) && detailsPercent >= 40 && detailsPercent <= 80, `details split out of bounds: ${after.splitDetails}`);
      assert(after.splitTable !== before.splitTable, "table splitter did not move");
      assert(after.splitDetails !== before.splitDetails, "details splitter did not move");
      report.screenshots.push(await capture(page, "05-panes-resized-en-1280", 78));
      return {
        before: { table: before.splitTable, details: before.splitDetails },
        after: { table: after.splitTable, details: after.splitDetails },
        drag: { table: tableDrag.end, details: detailsDrag.end },
      };
    });

    await scenario("05", "Refresh و بررسی پایداری Layout", async () => {
      const before = await page.evaluate(workspaceState);
      await page.reload();
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "rows after reload");
      await sleep(1500);
      const after = await page.evaluate(workspaceState);
      assert(Math.abs(Number.parseFloat(after.splitTable) - Number.parseFloat(before.splitTable)) < 0.6, `table split did not persist: ${before.splitTable} -> ${after.splitTable}`);
      assert(Math.abs(Number.parseFloat(after.splitDetails) - Number.parseFloat(before.splitDetails)) < 0.6, `details split did not persist: ${before.splitDetails} -> ${after.splitDetails}`);
      assert(after.sameOrder, "table and Gantt rows lost their synchronisation after reload");
      // Selection itself is not part of the saved layout; the test only requires
      // that any restored selection is consistent between table and Gantt.
      assert(after.selectedRow === after.selectedGantt, `selection is not synchronised after reload: ${after.selectedRow}/${after.selectedGantt}`);
      report.screenshots.push(await capture(page, "06-layout-after-reload-en-1280", 79));
      return { table: after.splitTable, details: after.splitDetails, selected: after.selectedRow };
    });

    await scenario("06", "تغییر عرض ستون‌ها و جابه‌جایی ستون‌ها", async () => {
      const before = await page.evaluate(workspaceState);
      await openCommand(page, "view.fields");
      await page.waitForSelector("[data-p6-columns-dialog][open]", "columns dialog", 5000);
      await sleep(300);
      report.screenshots.push(await capture(page, "07-columns-dialog-en-1280", 80));
      const second = await page.evaluate(`(() => {
        const items = [...document.querySelectorAll("[data-columns-selected-id]")];
        const item = items[1] ?? null;
        if (!item) return null;
        item.click();
        return { id: item.dataset.columnsSelectedId, title: item.textContent.trim() };
      })()`);
      assert(second?.id, "no second selected column to move");
      const moveUp = await page.evaluate(`(() => {
        const button = document.querySelector('[data-columns-action="move-up"]');
        if (!button || button.disabled) return false;
        button.click();
        return true;
      })()`);
      assert(moveUp, "move-up was disabled");
      await sleep(300);
      const firstId = await page.evaluate(`document.querySelector("[data-columns-selected-id]")?.dataset.columnsSelectedId ?? null`);
      assert(firstId === second.id, `column did not move: first is ${firstId}`);
      const editOpened = await page.evaluate(`(() => {
        const button = document.querySelector('[data-columns-action="edit"]');
        if (!button || button.disabled) return false;
        button.click();
        return true;
      })()`);
      assert(editOpened, "Edit Column was disabled");
      await page.waitForSelector("[data-p6-edit-column-dialog][open]", "edit column dialog", 5000);
      await setInput(page, '[data-p6-edit-column-dialog] input[name="width"]', "210");
      await page.evaluate(`(() => {
        document.querySelector("[data-p6-edit-column-dialog] form")?.requestSubmit();
        return true;
      })()`);
      await sleep(500);
      await page.evaluate(`(() => { document.querySelector("[data-columns-ok]")?.click(); return true; })()`);
      await page.waitFor(`(() => !document.querySelector("[data-p6-columns-dialog][open]"))`, "columns dialog closed", 5000);
      await sleep(1200);
      const after = await page.evaluate(workspaceState);
      assert(after.header[0] === before.header[1], `column order did not change: ${before.header.slice(0, 3)} -> ${after.header.slice(0, 3)}`);
      const width = await page.evaluate(`(() => {
        const th = document.querySelectorAll("#cp-activity-grid thead th")[0];
        return th ? Math.round(th.getBoundingClientRect().width) : null;
      })()`);
      assert(width !== null && width >= 200, `first column width is ${width}`);
      await page.reload();
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "rows after column reload");
      await sleep(1500);
      const persisted = await page.evaluate(workspaceState);
      assert(persisted.header[0] === after.header[0], `column order did not persist: ${persisted.header.slice(0, 3)}`);
      report.screenshots.push(await capture(page, "08-columns-applied-reloaded-en-1280", 81));
      return { moved: second, before: before.header.slice(0, 4), after: after.header.slice(0, 4), width, persisted: persisted.header.slice(0, 4) };
    });

    await scenario("07", "اعمال فیلتر و ترکیب چند فیلتر", async () => {
      // Version 26 combines filters through the Select checkboxes in the filter
      // list; the row name only highlights the current row.
      const applySelection = async (ids, combine) => {
        await openDialog(page, "dialog.filters");
        const selected = await page.evaluate(`(() => {
          const dialog = document.querySelector('[data-desktop-dialog="filters"]');
          const all = dialog.querySelector('input[name="filterAllActivities"]');
          if (all.checked) {
            all.checked = false;
            all.dispatchEvent(new Event("change", { bubbles: true }));
          }
          for (const input of dialog.querySelectorAll('input[name="filterSelected"]')) input.checked = false;
          for (const id of ${JSON.stringify(ids)}) {
            const input = dialog.querySelector('input[name="filterSelected"][value="' + id + '"]');
            if (!input) return { ok: false, missing: id };
            input.checked = true;
          }
          const radio = dialog.querySelector('input[name="filterCombine"][value="${combine}"]');
          radio.checked = true;
          radio.dispatchEvent(new Event("change", { bubbles: true }));
          return { ok: true };
        })()`);
        assert(selected.ok, `predefined filter missing: ${selected.missing}`);
        await submitDialog(page, "filters");
      };
      await applySelection(["builtin:in-progress"], "all");
      const inProgress = await page.evaluate(tableIds);
      await applySelection(["builtin:critical"], "all");
      const critical = await page.evaluate(tableIds);
      await applySelection(["builtin:in-progress", "builtin:critical"], "any");
      const combined = await page.evaluate(tableIds);
      const state = await page.evaluate(workspaceState);
      const expected = [...new Set([...inProgress, ...critical])].sort();
      assert(inProgress.length > 0 && critical.length > 0, `predefined filters returned no rows: ${inProgress} / ${critical}`);
      assert(JSON.stringify([...combined].sort()) === JSON.stringify(expected), `combined filter ${combined} is not the union ${expected}`);
      assert(state.activeFilterId?.includes("builtin:in-progress") && state.activeFilterId?.includes("builtin:critical"), `header does not carry both filter ids: ${state.activeFilterId}`);
      report.screenshots.push(await capture(page, "09-filters-combined-en-1280", 82));
      return { inProgress, critical, combined, label: state.filterLabel, activeFilterId: state.activeFilterId };
    });

    await scenario("08", "ایجاد و ویرایش فیلتر", async () => {
      await openDialog(page, "dialog.filters");
      await setCheckbox(page, '[data-desktop-dialog="filters"] input[name="filterAllActivities"]', false);
      await page.evaluate(`(() => {
        const button = document.querySelector('[data-desktop-dialog="filters"] [data-filter-new]');
        if (!button) return false;
        button.click();
        return true;
      })()`);
      await sleep(300);
      await setInput(page, '[data-desktop-dialog="filters"] input[name="filterName"]', "Civil open");
      await setSelect(page, '[data-desktop-dialog="filters"] select[name="filterMatch"]', "all");
      await setSelect(page, '[data-desktop-dialog="filters"] select[name="filter.field.0"]', "wbs");
      await setSelect(page, '[data-desktop-dialog="filters"] select[name="filter.operator.0"]', "contains");
      await setInput(page, '[data-desktop-dialog="filters"] input[name="filter.value.0"]', "Civil");
      await setSelect(page, '[data-desktop-dialog="filters"] select[name="filter.field.1"]', "activity_status");
      await setSelect(page, '[data-desktop-dialog="filters"] select[name="filter.operator.1"]', "not-equals");
      await setInput(page, '[data-desktop-dialog="filters"] input[name="filter.value.1"]', "Completed");
      report.screenshots.push(await capture(page, "10-filter-editor-en-1280", 83));
      await submitDialog(page, "filters");
      const first = await page.evaluate(tableIds);
      assert(first.length > 0 && first.length < 14, `created filter did not narrow rows: ${first}`);
      await openDialog(page, "dialog.filters");
      const edited = await page.evaluate(`(() => {
        const row = [...document.querySelectorAll('[data-desktop-dialog="filters"] tr[data-filter-id]')]
          .find((item) => item.textContent.includes("Civil open"));
        if (!row) return false;
        row.querySelector("[data-filter-row-select]")?.click();
        return true;
      })()`);
      assert(edited, "saved filter row not found");
      await sleep(300);
      await page.evaluate(`(() => {
        const button = document.querySelector('[data-desktop-dialog="filters"] [data-filter-modify]');
        if (!button) return false;
        button.click();
        return true;
      })()`);
      await sleep(400);
      const loadedName = await page.evaluate(`document.querySelector('[data-desktop-dialog="filters"] input[name="filterName"]')?.value ?? null`);
      assert(loadedName === "Civil open", `Modify did not load the filter: ${loadedName}`);
      await setSelect(page, '[data-desktop-dialog="filters"] select[name="filter.operator.1"]', "equals");
      await setInput(page, '[data-desktop-dialog="filters"] input[name="filter.value.1"]', "Not Started");
      await submitDialog(page, "filters");
      const second = await page.evaluate(tableIds);
      assert(JSON.stringify(second) !== JSON.stringify(first), `editing did not change the result: ${second}`);
      report.screenshots.push(await capture(page, "11-filter-edited-en-1280", 84));
      return { created: first, edited: second, loadedName };
    });

    await scenario("09", "Group و Sort", async () => {
      await openDialog(page, "dialog.group-sort");
      await sleep(200);
      await setSelect(page, '[data-desktop-dialog="group-sort"] select[name="groupBy"]', "wbs");
      const options = await page.evaluate(`(() => {
        const select = document.querySelector('[data-desktop-dialog="group-sort"] select[name="sort.field.0"]');
        return select ? [...select.options].map((option) => ({ value: option.value, label: option.textContent.trim() })) : [];
      })()`);
      const status = options.find((option) => /activity\.name/i.test(option.value)) ?? options.find((option) => option.value === "activity.early_start");
      assert(status, `sortable activity field missing: ${JSON.stringify(options)}`);
      await setSelect(page, '[data-desktop-dialog="group-sort"] select[name="sort.field.0"]', status.value);
      await setSelect(page, '[data-desktop-dialog="group-sort"] select[name="sort.direction.0"]', "desc");
      await page.evaluate(`(() => { document.querySelector('[data-desktop-dialog="group-sort"] [data-dialog-ok]')?.click(); return true; })()`);
      await page.waitFor(`(() => !document.querySelector('[data-desktop-dialog="group-sort"][open]'))`, "group sort closed", 5000);
      await sleep(1200);
      const state = await page.evaluate(workspaceState);
      const sequence = await page.evaluate(`(() => {
        return [...document.querySelectorAll("#cp-activity-grid tbody tr")].map((row) => ({
          kind: row.dataset.activityId ? "activity" : "band",
          id: row.dataset.activityId ?? null,
          label: (row.querySelector(".cp-p6-wbs-band-label, th, td")?.textContent ?? "").trim(),
        }));
      })()`);
      assert(state.bands > 0, "WBS bands disappeared after group/sort");
      assert(sequence.filter((row) => row.kind === "band").length === state.bands, "band sequence does not match rendered bands");
      await page.reload();
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "rows after group reload");
      await sleep(1400);
      const persisted = await page.evaluate(workspaceState);
      assert(persisted.bands === state.bands, `grouping did not persist: ${persisted.bands} vs ${state.bands}`);
      assert(persisted.header.join("|") === state.header.join("|"), "header changed after reload");
      report.screenshots.push(await capture(page, "12-group-sort-multilevel-en-1280", 85));
      return { group: "wbs", statusField: status.value, bands: state.bands, rows: state.rowIds.length };
    });

    await scenario("10", "بازکردن تمام ۱۶ تب Activity Details", async () => {
      // The saved custom filter from scenario 8 would hide rows later scenarios
      // need, so return to All Activities first.
      await openDialog(page, "dialog.filters");
      await setCheckbox(page, '[data-desktop-dialog="filters"] input[name="filterAllActivities"]', true);
      await submitDialog(page, "filters");
      // Screenshots of the details tabs must show a real activity, not a WBS
      // band row whose identity and fields are correctly "Not available".
      const focus = await page.evaluate(`(() => {
        const row = document.querySelector("#cp-activity-grid tbody tr[data-activity-id]");
        if (!row) return null;
        row.click();
        return row.dataset.activityId;
      })()`);
      assert(focus, "no activity row is available for the details tab sweep");
      await page.waitFor(
        `document.querySelector("#cp-details .cp-detail-selected")?.textContent.trim() === ${JSON.stringify(focus)}`,
        "details identity follows the row selected for the tab sweep",
      );
      await sleep(300);
      const tabs = await page.evaluate(`(() => [...document.querySelectorAll("[data-detail-tab]")].map((tab) => tab.dataset.detailTab))()`);
      const official = tabs.filter((id) => id !== "calendar");
      const expectedTabs = [
        "general", "status", "resources", "predecessors", "successors", "relationships",
        "codes", "notebook", "steps", "wps-docs", "expenses", "issues", "risks",
        "summary", "udfs", "update-history",
      ];
      assert(
        official.length === expectedTabs.length && expectedTabs.every((id) => official.includes(id)),
        `expected the 16 official Activity Details tabs, saw ${official.length} of ${tabs.length}: ${official.join(",")}`,
      );
      const rendered = [];
      for (const id of tabs) {
        const opened = await page.evaluate(`(() => {
          const tab = [...document.querySelectorAll("[data-detail-tab]")].find((item) => item.dataset.detailTab === ${JSON.stringify(id)});
          if (!tab) return false;
          tab.click();
          return true;
        })()`);
        assert(opened, `tab ${id} not found`);
        await sleep(260);
        const panel = await page.evaluate(`(() => {
          const panel = document.querySelector('[data-detail-panel="${id}"]');
          const active = document.querySelector("[data-detail-tab].is-active")?.dataset.detailTab ?? null;
          return {
            active,
            present: Boolean(panel),
            hidden: panel?.hidden ?? null,
            text: (panel?.textContent ?? "").replace(/\\s+/g, " ").trim().slice(0, 180),
          };
        })()`);
        assert(panel.present, `panel ${id} missing`);
        assert(panel.hidden === false, `panel ${id} stayed hidden`);
        assert(panel.active === id, `tab ${id} did not become active (${panel.active})`);
        rendered.push({ id, text: panel.text });
        if (id === "general") {
          report.screenshots.push(await capture(page, "13-details-general-en-1280", 86));
        } else if (id === "status") {
          report.screenshots.push(await capture(page, "14-details-status-en-1280", 87));
        } else if (id === "resources") {
          report.screenshots.push(await capture(page, "15-details-resources-en-1280", 88));
        } else if (id === "steps") {
          report.screenshots.push(await capture(page, "16-details-steps-en-1280", 89));
        }
      }
      return { tabs, officialCount: official.length, rendered };
    });

    await scenario("11", "راست‌کلیک در تمام نواحی", async () => {
      const areas = [];
      const openAt = async (selector, label) => {
        const prepared = await page.evaluate(`(() => {
          const target = document.querySelector(${JSON.stringify(selector)});
          if (!target) return false;
          target.scrollIntoView({ block: "center", inline: "nearest" });
          return true;
        })()`);
        assert(prepared, `${label} target missing: ${selector}`);
        // The workspace dismisses an open context menu on scroll, and
        // scrollIntoView fires its scroll event asynchronously; settle first
        // so the right-click below is the last event the menu sees.
        await sleep(500);
        const opened = await page.evaluate(`(() => {
          const target = document.querySelector(${JSON.stringify(selector)});
          if (!target) return false;
          const box = target.getBoundingClientRect();
          if (!box.width || !box.height) return false;
          target.dispatchEvent(new MouseEvent("contextmenu", {
            bubbles: true,
            cancelable: true,
            button: 2,
            clientX: Math.round(box.left + Math.min(180, box.width / 2)),
            clientY: Math.round(box.top + Math.min(30, box.height / 2)),
          }));
          return true;
        })()`);
        await sleep(300);
        const menu = await page.evaluate(`(() => {
          const menu = document.querySelector("[data-activity-context-menu]");
          if (!menu) return null;
          const box = menu.getBoundingClientRect();
          return {
            hidden: menu.hidden,
            width: Math.round(box.width),
            height: Math.round(box.height),
            items: [...menu.querySelectorAll("[data-activity-menu-command]")].map((item) => item.dataset.activityMenuCommand),
            visible: Boolean(menu.getClientRects().length),
          };
        })()`);
        areas.push({ label, opened, menu });
        return menu;
      };
      const tableMenu = await openAt('#cp-activity-grid tbody tr[data-activity-id="A140"]', "activity row");
      assert(tableMenu && !tableMenu.hidden && tableMenu.visible, `table row context menu did not open: ${JSON.stringify(tableMenu)}`);
      assert(tableMenu.items.length > 8, `context menu is too small: ${tableMenu.items.length}`);
      report.screenshots.push(await capture(page, "17-context-menu-table-en-1280", 90));
      await dispatchKey(page, "Escape", "Escape", 27);
      const ganttMenu = await openAt('#cp-gantt [data-gantt-activity-id="A140"]', "gantt row");
      assert(ganttMenu && !ganttMenu.hidden && ganttMenu.visible, "Gantt context menu did not open");
      report.screenshots.push(await capture(page, "18-context-menu-gantt-en-1280", 91));
      await dispatchKey(page, "Escape", "Escape", 27);
      const wbsMenu = await openAt(".cp-p6-wbs-band", "wbs band");
      assert(wbsMenu && !wbsMenu.hidden && wbsMenu.visible, "WBS context menu did not open");
      await dispatchKey(page, "Escape", "Escape", 27);
      const gridMenu = await openAt("#cp-activity-grid", "empty grid area");
      assert(gridMenu && gridMenu.visible, "empty grid area did not open the activity menu");
      await dispatchKey(page, "Escape", "Escape", 27);
      // Right-clicking the details pane opens its own Customize Activity
      // Details menu, never the activity command menu.
      const detailsMenu = await openAt("#cp-details", "details pane");
      const detailsVisible = Boolean(detailsMenu && detailsMenu.visible);
      assert(detailsVisible, "the details pane did not open its customize menu");
      assert(detailsMenu.items.includes("customize-details"),
        `details menu is missing Customize Activity Details: ${JSON.stringify(detailsMenu.items)}`);
      assert(!detailsMenu.items.includes("delete") && !detailsMenu.items.includes("cut"),
        "the details pane exposed activity-only commands");
      await dispatchKey(page, "Escape", "Escape", 27);
      return {
        areas,
        tableItems: tableMenu.items.length,
        gridMenu: gridMenu.visible,
        detailsVisible,
        detailsItems: detailsMenu.items,
      };
    });

    await scenario("12", "آزمون میانبرهای تأییدشده", async () => {
      await page.evaluate(`(() => {
        document.querySelector('#cp-activity-grid tbody tr[data-activity-id="A150"]')?.click();
        return true;
      })()`);
      await sleep(400);
      // Keyboard events only reach the shell handler when the focused element
      // lives inside the host, so focus a visible toolbar button (not an input,
      // which would trip the typing guard).
      const focusShell = async () => {
        const focused = await page.evaluate(`(() => {
          const shell = document.querySelector("[data-desktop-shell]");
          const button = [...(shell?.querySelectorAll("[data-desktop-command]") ?? [])]
            .find((item) => item.getClientRects().length > 0);
          if (!button) return false;
          button.focus();
          return document.activeElement === button;
        })()`);
        assert(focused, "could not focus a control inside the desktop shell");
      };
      await focusShell();
      const focusInside = await page.evaluate(`Boolean(document.activeElement && document.activeElement.closest && document.activeElement.closest("[data-desktop-shell]"))`);
      await dispatchKey(page, "F1", "F1", 112);
      const shortcutsOpen = await page.evaluate(`Boolean(document.querySelector('[data-desktop-dialog="shortcuts"][open]'))`);
      assert(shortcutsOpen, "F1 did not open the shortcuts dialog");
      const shortcutRows = await page.evaluate(`(() => [...document.querySelectorAll('[data-desktop-dialog="shortcuts"] tbody tr')].map((row) => row.textContent.replace(/\\s+/g, " ").trim()))()`);
      report.screenshots.push(await capture(page, "19-shortcuts-dialog-en-1280", 92));
      await dispatchKey(page, "Escape", "Escape", 27);
      await sleep(300);
      await focusShell();
      await dispatchKey(page, "f", "KeyF", 70, 2);
      const focusedFilter = await page.evaluate(`document.activeElement?.matches?.("[data-activity-filter]") ?? false`);
      assert(focusedFilter, "Ctrl+F did not focus the activity find field");
      // Ctrl+F leaves focus inside a text input, so return to the shell before
      // the Ctrl+Numpad shortcuts that are suppressed while typing.
      await focusShell();
      const expandedBands = await page.evaluate(`document.querySelectorAll(".cp-p6-wbs-band").length`);
      const collapsedBefore = await page.evaluate(`document.querySelectorAll('[data-wbs-collapsed="true"]').length`);
      await dispatchKey(page, "-", "NumpadSubtract", 109, 2);
      const collapsedAfter = await page.evaluate(`document.querySelectorAll('[data-wbs-collapsed="true"]').length`);
      assert(collapsedAfter > collapsedBefore, `Ctrl+Numpad- did not collapse WBS nodes: ${collapsedBefore} -> ${collapsedAfter}`);
      await focusShell();
      await dispatchKey(page, "+", "NumpadAdd", 107, 2);
      const expandedAfter = await page.evaluate(`document.querySelectorAll('[data-wbs-collapsed="true"]').length`);
      assert(expandedAfter === 0, `Ctrl+Numpad+ did not expand WBS nodes: ${expandedAfter}`);
      return { focusInside, shortcutsOpen, shortcutRows, focusedFilter, expandedBands, collapsedBefore, collapsedAfter, expandedAfter };
    });

    await scenario("13", "نمایش و مخفی‌سازی Data Date Line و Progress Line", async () => {
      await openDialog(page, "dialog.bars");
      const dataDate = await page.evaluate(`(() => {
        const fieldset = [...document.querySelectorAll('[data-gantt-options] fieldset')].find((item) => item.querySelector('legend')?.textContent.includes("Data Date"));
        return fieldset ? {
          disabled: fieldset.disabled,
          note: [...fieldset.querySelectorAll(".cp-dialog-note")].map((item) => item.textContent.trim()).join(" "),
          checked: fieldset.querySelector('input[name="gantt.dataDateLine.visible"]')?.checked ?? null,
        } : null;
      })()`);
      assert(dataDate, "Data Date fieldset missing");
      assert(dataDate.disabled, "the Data Date fieldset must stay disabled without an authoritative date");
      assert(/no Data Date/i.test(dataDate.note), `Data Date note is not honest: ${dataDate.note}`);
      report.screenshots.push(await capture(page, "20-data-date-disabled-en-1280", 93));
      await setCheckbox(page, '[data-desktop-dialog="bars"] input[name="gantt.progressLine.visible"]', true);
      await setInput(page, '[data-desktop-dialog="bars"] input[name="gantt.progressLine.thickness"]', "3");
      await setInput(page, '[data-desktop-dialog="bars"] input[name="gantt.progressLine.color"]', "#c0392b");
      await submitDialog(page, "bars");
      const shown = await page.evaluate(workspaceState);
      assert(shown.progressLines === 1, `progress line not drawn: ${shown.progressLines}`);
      assert(shown.dataDateLines === 0, `Data Date line drawn without a date: ${shown.dataDateLines}`);
      const points = await page.evaluate(`(() => {
        const line = document.querySelector("[data-gantt-progress-line]");
        if (!line) return null;
        // The count attribute lives on the <path> itself, so the geometry is
        // read from the marked node rather than from a descendant.
        const geometry = line.getAttribute("d") ?? line.getAttribute("points") ?? "";
        const count = (geometry.match(/[ML]\\s*-?\\d/g) ?? []).length;
        const parentStyle = getComputedStyle(line.parentElement ?? line);
        return {
          tag: line.tagName,
          count,
          measured: line.getAttribute("data-gantt-progress-line"),
          stroke: getComputedStyle(line).stroke,
          color: parentStyle.getPropertyValue("--cp-progress-color").trim(),
          width: parentStyle.getPropertyValue("--cp-progress-width").trim(),
        };
      })()`);
      assert(points && points.count >= 2, `progress line has too few points: ${JSON.stringify(points)}`);
      assert(points.color.toLowerCase() === "#c0392b", `progress line colour not applied: ${points.color}`);
      assert(points.width === "3px", `progress line thickness not applied: ${points.width}`);
      report.screenshots.push(await capture(page, "21-progress-line-shown-en-1280", 94));
      await openDialog(page, "dialog.bars");
      await setCheckbox(page, '[data-desktop-dialog="bars"] input[name="gantt.progressLine.visible"]', false);
      await submitDialog(page, "bars");
      const hidden = await page.evaluate(workspaceState);
      assert(hidden.progressLines === 0, `progress line did not hide: ${hidden.progressLines}`);
      return { dataDate, shown: shown.progressLines, hidden: hidden.progressLines, points };
    });

    await scenario("14", "بررسی هر چهار نوع رابطه FS/SS/FF/SF", async () => {
      const before = await page.evaluate(workspaceState);
      assert(before.linkTypes.FS > 0, "no FS links rendered");
      assert((before.linkTypes.SS ?? 0) > 0, "no SS links rendered");
      const created = await page.evaluate(`(async () => {
        const results = [];
        for (const payload of [
          { relationship_id: "REL-E2E-FF-1", predecessor_id: "A140", successor_id: "A170", relationship_type: "FF", lag_value: "0", lag_unit: "working-day" },
          { relationship_id: "REL-E2E-SF-1", predecessor_id: "A100", successor_id: "A210", relationship_type: "SF", lag_value: "0", lag_unit: "working-day" },
        ]) {
          const response = await fetch("/api/projects/preview-rps-01/p6/relationships", {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify(payload),
          });
          results.push({ id: payload.relationship_id, status: response.status, body: await response.text() });
        }
        return results;
      })()`, { awaitPromise: true });
      const allCreated = created.every((item) => item.status === 200);
      assert(allCreated, `temporary FF/SF relationships were rejected: ${JSON.stringify(created)}`);
      let after = null;
      let restored = null;
      const removed = [];
      try {
        await page.reload();
        await page.waitForSelector("#cp-gantt [data-gantt-link]", "links after reload");
        await sleep(1500);
        after = await page.evaluate(workspaceState);
        for (const type of ["FS", "SS", "FF", "SF"]) {
          assert((after.linkTypes[type] ?? 0) > 0, `${type} link not rendered: ${JSON.stringify(after.linkTypes)}`);
        }
        report.screenshots.push(await capture(page, "22-relationships-four-types-en-1280", 95));
      } finally {
        const cleanup = await page.evaluate(`(async () => {
          const results = [];
          const list = await fetch("/api/projects/preview-rps-01/p6/relationships").then((response) => response.json());
          for (const id of ["REL-E2E-FF-1", "REL-E2E-SF-1"]) {
            const entry = (list.relationships ?? []).find((item) => (item.relationship?.relationship_id ?? item.relationship_id) === id);
            if (!entry) { results.push({ id, status: "absent" }); continue; }
            const record = entry.relationship ?? entry;
            const response = await fetch("/api/projects/preview-rps-01/p6/relationships/" + encodeURIComponent(id), {
              method: "DELETE",
              headers: { "content-type": "application/json" },
              body: JSON.stringify({ expected_revision: record.record_revision ?? 1 }),
            });
            results.push({ id, status: response.status, body: await response.text() });
          }
          return results;
        })()`, { awaitPromise: true });
        removed.push(...cleanup);
      }
      await page.reload();
      await page.waitForSelector("#cp-gantt [data-gantt-link]", "links after cleanup");
      await sleep(1500);
      restored = await page.evaluate(workspaceState);
      assert((restored.linkTypes.FF ?? 0) === 0 && (restored.linkTypes.SF ?? 0) === 0, `temporary links not removed: ${JSON.stringify(restored.linkTypes)}`);
      return { before: before.linkTypes, after: after?.linkTypes ?? null, restored: restored.linkTypes, created, removed };
    });

    await scenario("15", "Zoom و Scroll در Gantt", async () => {
      const before = await page.evaluate(workspaceState);
      const axisBefore = await page.evaluate(`(() => ({ ticks: document.querySelectorAll("[data-gantt-tick]").length, width: document.querySelector("#cp-gantt .cp-gantt-body")?.scrollWidth ?? null }))()`);
      await openCommand(page, "view.zoom-in");
      await sleep(800);
      const zoomedIn = await page.evaluate(workspaceState);
      const axisIn = await page.evaluate(`document.querySelectorAll("[data-gantt-tick]").length`);
      await openCommand(page, "view.zoom-out");
      await sleep(800);
      const zoomedOut = await page.evaluate(workspaceState);
      const axisOut = await page.evaluate(`document.querySelectorAll("[data-gantt-tick]").length`);
      assert(zoomedIn.scale !== before.scale, `zoom-in did not change scale: ${before.scale}`);
      assert(zoomedOut.scale === before.scale, `zoom-out did not restore scale: ${zoomedOut.scale}`);
      assert(axisIn !== axisOut || axisIn !== axisBefore.ticks, `axis ticks did not change: ${axisBefore.ticks}/${axisIn}/${axisOut}`);
      const scrolled = await page.evaluate(`(() => {
        const target = [...document.querySelectorAll("#cp-gantt *")].find((element) => element.scrollWidth > element.clientWidth + 8);
        if (!target) return null;
        const before = target.scrollLeft;
        target.scrollLeft = Math.min(240, target.scrollWidth - target.clientWidth);
        target.dispatchEvent(new Event("scroll", { bubbles: true }));
        return { className: typeof target.className === "string" ? target.className : "", before, after: target.scrollLeft, max: target.scrollWidth - target.clientWidth };
      })()`);
      assert(scrolled && scrolled.after > scrolled.before, `Gantt did not scroll: ${JSON.stringify(scrolled)}`);
      await sleep(400);
      report.screenshots.push(await capture(page, "23-gantt-zoom-scroll-en-1280", 96));
      return { before: before.scale, zoomedIn: zoomedIn.scale, zoomedOut: zoomedOut.scale, ticks: [axisBefore.ticks, axisIn, axisOut], scrolled };
    });

    await scenario("16", "تغییر اندازه Splitterها در چند اندازه صفحه", async () => {
      const results = [];
      for (const [width, height] of [[1024, 768], [1280, 720], [1440, 900], [1920, 1080]]) {
        await page.cdp.send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
        await sleep(500);
        const before = await page.evaluate(workspaceState);
        await page.drag("[data-panel-splitter]", -70, 0);
        await sleep(250);
        await page.drag("[data-details-splitter]", 0, -18);
        await sleep(500);
        const after = await page.evaluate(workspaceState);
        const tablePercent = Number.parseFloat(after.splitTable);
        const detailsPercent = Number.parseFloat(after.splitDetails);
        assert(tablePercent >= 25 && tablePercent <= 75, `${width}x${height} table split ${after.splitTable} out of bounds`);
        assert(detailsPercent >= 40 && detailsPercent <= 80, `${width}x${height} details split ${after.splitDetails} out of bounds`);
        const overflow = await page.evaluate(`(() => {
          const table = document.querySelector("#cp-activity-grid")?.getBoundingClientRect();
          const gantt = document.querySelector("#cp-gantt")?.getBoundingClientRect();
          return {
            tableRight: table ? Math.round(table.right) : null,
            ganttRight: gantt ? Math.round(gantt.right) : null,
            viewport: window.innerWidth,
            fits: Boolean(table && gantt && table.right <= window.innerWidth + 1 && gantt.right <= window.innerWidth + 1),
          };
        })()`);
        assert(overflow.fits, `${width}x${height} panes overflow the viewport: ${JSON.stringify(overflow)}`);
        results.push({ width, height, before: { table: before.splitTable, details: before.splitDetails }, after: { table: after.splitTable, details: after.splitDetails }, overflow });
        if (width === 1440 || width === 1920) {
          report.screenshots.push(await capture(page, `24-splitters-${width}x${height}-en`, width === 1440 ? 97 : 98));
        }
      }
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await sleep(400);
      return { results };
    });

    await scenario("17", "بررسی حالت RTL و LTR", async () => {
      await setLanguage(page, "fa");
      const rtl = await page.evaluate(workspaceState);
      assert(rtl.dir === "rtl", `fa workspace direction is ${rtl.dir}`);
      const tableDirection = await page.evaluate(`getComputedStyle(document.querySelector("#cp-activity-grid")).direction`);
      assert(tableDirection === "rtl", `table direction is ${tableDirection}`);
      report.screenshots.push(await capture(page, "25-rtl-fa-1280", 99));
      await setLanguage(page, "en");
      const ltr = await page.evaluate(workspaceState);
      assert(ltr.dir === "ltr", `en workspace direction is ${ltr.dir}`);
      report.screenshots.push(await capture(page, "26-ltr-en-1280", 100));
      return { rtl: { dir: rtl.dir, lang: rtl.lang, table: tableDirection }, ltr: { dir: ltr.dir, lang: ltr.lang } };
    });

    await scenario("18", "بررسی عدم وجود خطای Console و Runtime", async () => {
      // Restore the preview to its default presentation and split.
      await page.evaluate(`(() => {
        document.querySelector("[data-reset-table-split]")?.click();
        document.querySelector("[data-reset-details-split]")?.click();
        return true;
      })()`);
      await sleep(600);
      await openDialog(page, "dialog.filters");
      await setCheckbox(page, '[data-desktop-dialog="filters"] input[name="filterAllActivities"]', true);
      await submitDialog(page, "filters");
      await sleep(600);
      const state = await page.evaluate(workspaceState);
      assert(exceptions.length === 0, `uncaught page exceptions: ${JSON.stringify(exceptions.slice(0, 3))}`);
      assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors.slice(0, 3))}`);
      assert(apiFailures.length === 0, `API 5xx responses: ${JSON.stringify(apiFailures.slice(0, 3))}`);
      report.screenshots.push(await capture(page, "27-final-state-en-1280", 101));
      return { exceptions: exceptions.length, consoleErrors: consoleErrors.length, apiFailures: apiFailures.length, final: { rows: state.rowIds.length, filter: state.filterLabel, dataDateLines: state.dataDateLines } };
    });
  } finally {
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(outDir, "activities-v26-scenarios.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(evidenceDir, "activities-v26-scenarios-2026-11-08.json"), JSON.stringify(report, null, 2));
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
