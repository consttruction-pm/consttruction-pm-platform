#!/usr/bin/env node
/**
 * Version 26 activity grouping and sorting acceptance (ACT-002).
 *
 * Proves in the real preview that the Group and Sort dialog drives the table
 * with an ordered multi-level sort plan, that WBS grouping orders activities
 * inside the hierarchy, that the Gantt follows the same row order, and that the
 * saved Activities layout restores the group mode and sort plan after a full
 * reload. Every expected order is computed from the rendered rows; no fixture
 * value is injected into the document.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4198 \
 *   CUBI_TESTED_CODE_SHA=<code commit> node e2e/activity-group-sort-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4198";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "activity-group-sort-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `activity-group-sort-v26-${evidenceDate}`);
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
  const file = `activity-group-sort-v26/${name}.png`;
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

const dialogSelector = "dialog[data-desktop-dialog=group-sort]";

async function openGroupSort(page) {
  const clicked = await page.evaluate(`(() => {
    const element = [...document.querySelectorAll('[data-desktop-command="dialog.group-sort"]')]
      .find((item) => item.getClientRects().length > 0 && !item.disabled);
    if (!element) return false;
    element.click();
    return true;
  })()`);
  assert(clicked, "Group and Sort command is missing");
  await page.waitForSelector(`${dialogSelector}[open]`, "group and sort dialog", 8000);
  await sleep(250);
}

async function dialogState(page) {
  return page.evaluate(`(() => {
    const dialog = document.querySelector("${dialogSelector}");
    return {
      open: Boolean(dialog?.open),
      groupOptions: [...dialog.querySelectorAll('select[name="groupBy"] option')].map((option) => option.value),
      groups: [...dialog.querySelectorAll("fieldset legend")].map((legend) => legend.textContent.trim()),
      sortRows: dialog.querySelectorAll(".cp-sort-row").length,
      fields: [...dialog.querySelectorAll('select[name^="sort.field."]')].map((select) => ({
        name: select.name,
        value: select.value,
        options: [...select.options].map((option) => option.value).filter(Boolean),
      })),
      directions: [...dialog.querySelectorAll('select[name^="sort.direction."]')].map((select) => select.value),
      notes: [...dialog.querySelectorAll(".cp-dialog-note")].map((note) => note.textContent.trim()),
    };
  })()`);
}

async function setSelect(page, name, value) {
  const changed = await page.evaluate(`(() => {
    const select = document.querySelector('${dialogSelector} select[name="' + ${JSON.stringify(name)} + '"]');
    if (!select) return false;
    select.value = ${JSON.stringify(value)};
    if (select.value !== ${JSON.stringify(value)}) return false;
    select.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  assert(changed, `group/sort control ${name} did not accept ${value}`);
  await sleep(120);
}

async function submitOk(page) {
  const clicked = await page.evaluate(`(() => {
    const button = document.querySelector('${dialogSelector} [data-dialog-ok]');
    if (!button || button.disabled) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, "Group and Sort OK button is missing");
  await page.waitFor(`!document.querySelector('${dialogSelector}')?.open`, "group and sort dialog closed", 8000);
  await sleep(600);
}

async function tableState(page) {
  return page.evaluate(`(() => {
    const grid = document.querySelector("#cp-activity-grid");
    const headers = [...grid.querySelectorAll("thead th[data-column-id]")].map((cell) => cell.dataset.columnId);
    const sequence = [...grid.querySelectorAll("tbody tr")].map((row) => {
      if (!row.dataset.activityId) {
        return { kind: "band", label: row.querySelector(".cp-p6-wbs-code")?.textContent?.trim() ?? row.textContent.trim() };
      }
      const cells = {};
      [...row.querySelectorAll("td")].forEach((cell, index) => {
        if (headers[index]) cells[headers[index]] = cell.textContent.trim();
      });
      return { kind: "activity", id: row.dataset.activityId, cells };
    });
    const gantt = [...document.querySelectorAll("#cp-gantt [data-gantt-activity-id]")].map((row) => row.dataset.ganttActivityId);
    return {
      sequence,
      ids: sequence.filter((row) => row.kind === "activity").map((row) => row.id),
      bands: sequence.filter((row) => row.kind === "band").length,
      ganttIds: gantt,
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      dir: document.documentElement.dir || "ltr",
      locale: document.documentElement.lang || "en",
    };
  })()`);
}

const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });

function compareStartDesc(left, right) {
  const a = left.cells["activity.early_start"] ?? "";
  const b = right.cells["activity.early_start"] ?? "";
  if (!a || a === "—") return b && b !== "—" ? 1 : 0;
  if (!b || b === "—") return -1;
  if (a === b) return 0;
  return a < b ? 1 : -1;
}

/** Expected order for start descending, then name ascending, then id. */
function expectedByStartDesc(rows) {
  return [...rows]
    .sort((left, right) =>
      compareStartDesc(left, right)
      || collator.compare(left.cells["activity.name"] ?? "", right.cells["activity.name"] ?? "")
      || collator.compare(left.id, right.id))
    .map((row) => row.id);
}

function readLayout(page, projectId, scope) {
  return page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${projectId}/p6/layouts/${scope}/activity");
    let body = null;
    try { body = await response.json(); } catch (error) { body = null; }
    return { status: response.status, body };
  })()`, { awaitPromise: true });
}

async function saveLayout(page) {
  const clicked = await page.evaluate(`(() => {
    const button = [...document.querySelectorAll('[data-desktop-command="layout.save"]')]
      .find((item) => item.getClientRects().length > 0 && !item.disabled);
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, "Save Layout command is missing");
  let latest = null;
  for (let attempt = 0; attempt < 40; attempt += 1) {
    await sleep(200);
    for (const scope of ["project", "user"]) {
      const saved = await readLayout(page, "preview-rps-01", scope);
      if (saved.status !== 200 || !saved.body) continue;
      latest = saved;
      if (saved.body.metadata?.groupSort) return saved;
    }
  }
  throw new Error(`layout save did not persist group/sort metadata (status ${latest?.status ?? "none"})`);
}

async function main() {
  const health = await waitForHttp(`${baseUrl}/preview/health`, 30000);
  if (!(health.status === "ok" || health.status === 200)) throw new Error(`preview health ${health.status}`);
  const chrome = await launchChrome();
  const page = new Page(chrome.cdp);
  await page.initialize();
  page.cdp.on("Runtime.exceptionThrown", (params) => {
    exceptions.push(params.exceptionDetails?.exception?.description ?? params.exceptionDetails?.text ?? "exception");
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
    contract: "cubi-activity-group-sort-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testCodeSha: testedCodeSha,
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
    writeFileSync(join(outDir, "activity-group-sort-v26.json"), json);
    writeFileSync(join(evidenceDir, "activity-group-sort-v26.json"), json);
  }

  try {
    await setViewport(page, 1366, 768);
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
    const hasPersonas = await page.evaluate('Boolean(document.querySelector(".persona"))');
    if (!hasPersonas) {
      await page.evaluate('fetch("/preview/logout", { method: "POST", redirect: "manual" }).then((response) => response.status)', { awaitPromise: true });
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

    let expectedOrder = [];
    let expectedBands = 0;

    await scenario("01", "the dialog applies an ordered sort plan and the Gantt follows it", async () => {
      const baseline = await tableState(page);
      assert(baseline.ids.length === 14, `expected the 14-activity fixture, got ${baseline.ids.length}`);
      assert(baseline.bands > 0, "the default layout must start grouped by WBS");
      await openGroupSort(page);
      const dialog = await dialogState(page);
      assert(dialog.groupOptions.join(",") === "wbs,none", `group modes are ${dialog.groupOptions.join(",")}`);
      assert(dialog.sortRows === 3, `expected three sort rows, got ${dialog.sortRows}`);
      assert(dialog.fields[0].options.includes("activity.early_start"), "Start is not offered as a sort field");
      assert(dialog.fields[0].options.includes("activity.name"), "Activity name is not offered as a sort field");
      assert(dialog.notes.some((note) => /three/i.test(note)), `sort note is missing: ${dialog.notes.join(" | ")}`);
      await setSelect(page, "groupBy", "none");
      await setSelect(page, "sort.field.0", "activity.early_start");
      await setSelect(page, "sort.direction.0", "desc");
      await setSelect(page, "sort.field.1", "activity.name");
      await setSelect(page, "sort.direction.1", "asc");
      await submitOk(page);
      const sorted = await tableState(page);
      assert(sorted.bands === 0, `No grouping should remove WBS bands, found ${sorted.bands}`);
      const rows = sorted.sequence.filter((row) => row.kind === "activity");
      expectedOrder = expectedByStartDesc(rows);
      assert(
        sorted.ids.join(",") === expectedOrder.join(","),
        `table order differs from Start desc, name asc: ${sorted.ids.join(",")} vs ${expectedOrder.join(",")}`,
      );
      assert(
        sorted.ganttIds.join(",") === sorted.ids.join(","),
        `Gantt order differs from the table: ${sorted.ganttIds.join(",")} vs ${sorted.ids.join(",")}`,
      );
      await capture(page, "01-group-sort-start-desc-name-asc-en-1366");
      return { rows: sorted.ids.length, bands: sorted.bands, order: sorted.ids.join(",") };
    });

    await scenario("02", "the saved layout stores the plan and a reload restores it", async () => {
      const saved = await saveLayout(page);
      const metadata = saved.body?.metadata?.groupSort;
      assert(metadata?.groupBy === "none", `stored group mode is ${metadata?.groupBy}`);
      assert(metadata?.sortLevels?.length === 2, `stored sort levels ${JSON.stringify(metadata?.sortLevels)}`);
      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "reload after layout save");
      await sleep(1200);
      const reloaded = await tableState(page);
      assert(reloaded.bands === 0, `reload restored WBS bands (${reloaded.bands})`);
      assert(reloaded.ids.join(",") === expectedOrder.join(","), `reload order changed: ${reloaded.ids.join(",")}`);
      await capture(page, "02-sorted-layout-after-reload-en-1366");
      return { revision: saved.body?.revision, sortLevels: metadata.sortLevels, rows: reloaded.ids.length };
    });

    await scenario("03", "WBS grouping orders activities inside each band and persists", async () => {
      await openGroupSort(page);
      await setSelect(page, "groupBy", "wbs");
      await setSelect(page, "sort.field.0", "activity.name");
      await setSelect(page, "sort.direction.0", "asc");
      await setSelect(page, "sort.field.1", "");
      await submitOk(page);
      const grouped = await tableState(page);
      assert(grouped.bands > 0, "WBS grouping rendered no bands");
      expectedBands = grouped.bands;
      const namesByBand = [];
      let current = null;
      for (const row of grouped.sequence) {
        if (row.kind === "band") {
          current = [];
          namesByBand.push(current);
        } else if (current) {
          current.push(row.cells["activity.name"] ?? "");
        }
      }
      for (const names of namesByBand) {
        const sortedNames = [...names].sort(collator.compare);
        assert(names.join("|") === sortedNames.join("|"), `band order is not name asc: ${names.join(" | ")}`);
      }
      assert(
        grouped.ganttIds.join(",") === grouped.ids.join(","),
        "Gantt order differs from the grouped table",
      );
      await saveLayout(page);
      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "reload after WBS save");
      await sleep(1200);
      const reloaded = await tableState(page);
      assert(reloaded.bands === expectedBands, `reload shows ${reloaded.bands} bands, expected ${expectedBands}`);
      assert(reloaded.ids.length === 14, `reload shows ${reloaded.ids.length} activity rows`);
      await capture(page, "03-wbs-group-name-asc-after-reload-en-1366");
      return { bands: grouped.bands, rows: grouped.ids.length };
    });

    await scenario("04", "the dialog and a sort plan render in a Persian RTL cell", async () => {
      await setViewport(page, 1280, 720);
      await setLanguage(page, "fa");
      await openGroupSort(page);
      const dialog = await page.evaluate(`(() => {
        const element = document.querySelector("${dialogSelector}");
        return {
          title: element.querySelector(".cp-dialog-title, header, h2")?.textContent?.trim() ?? "",
          rows: element.querySelectorAll(".cp-sort-row").length,
          overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        };
      })()`);
      assert(/گروه|ترتیب/.test(dialog.title), `Persian dialog title is missing: ${dialog.title}`);
      assert(dialog.overflow <= 1, `the RTL dialog overflows by ${dialog.overflow}px`);
      await setSelect(page, "groupBy", "none");
      await setSelect(page, "sort.field.0", "activity.early_start");
      await setSelect(page, "sort.direction.0", "asc");
      await setSelect(page, "sort.field.1", "");
      const shot = await page.evaluate(`(() => {
        const dialog = document.querySelector("${dialogSelector}");
        const body = dialog.getBoundingClientRect();
        return { dir: document.documentElement.dir, width: Math.round(body.width), height: Math.round(body.height) };
      })()`);
      assert(shot.dir === "rtl", `document direction is ${shot.dir}`);
      await capture(page, "04-group-sort-fa-rtl-1280");
      await submitOk(page);
      const ascending = await tableState(page);
      assert(ascending.dir === "rtl", "the sorted table lost RTL");
      assert(ascending.bands === 0, "No grouping was not applied in the RTL cell");
      const rows = ascending.sequence.filter((row) => row.kind === "activity");
      const expected = [...rows]
        .sort((left, right) => {
          const a = left.cells["activity.early_start"] ?? "";
          const b = right.cells["activity.early_start"] ?? "";
          if (!a || a === "—") return b && b !== "—" ? 1 : 0;
          if (!b || b === "—") return -1;
          return a === b ? 0 : a < b ? -1 : 1;
        })
        .map((row) => row.id);
      assert(ascending.ids.join(",") === expected.join(","), `RTL Start asc order differs: ${ascending.ids.join(",")}`);
      assert(ascending.overflow <= 1, `the RTL table overflows by ${ascending.overflow}px`);
      return { dialog, rows: ascending.ids.length };
    });

    await scenario("05", "the grouped layout fits a 1920x1080 cell", async () => {
      await setViewport(page, 1920, 1080);
      await sleep(500);
      const state = await tableState(page);
      assert(state.overflow <= 1, `the 1920 cell overflows by ${state.overflow}px`);
      assert(state.ids.length === 14, `the 1920 cell shows ${state.ids.length} rows`);
      await capture(page, "05-group-sort-en-1920");
      return { rows: state.ids.length, overflow: state.overflow };
    });

    log(`\nAll ${scenarios.length} group and sort scenarios passed`);
  } catch (error) {
    exceptions.push(String(error && error.stack ? error.stack : error));
    process.exitCode = 1;
  } finally {
    writeReport();
    await chrome.stop();
  }
}

await main();
