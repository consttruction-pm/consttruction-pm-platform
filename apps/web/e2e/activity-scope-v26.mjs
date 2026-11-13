#!/usr/bin/env node
/**
 * Browser E2E for ACT-020: full-project search, count reconciliation,
 * Select All and export scope in the Activities window.
 *
 * Every expected number in this suite is computed from the authoritative
 * Activity Master read (`GET /api/projects/<id>/p6/activities`) or from a
 * published schedule snapshot, never from painted DOM rows. The suite proves:
 *
 *   1. Select All covers the whole allowed project scope, including rows that
 *      grouping or a collapsed WBS branch keeps out of the DOM;
 *   2. quick search and the Filters dialog narrow the scope while a previous
 *      selection stays defined and counted (total vs in-scope selection);
 *   3. the table, the Gantt and the toolbar counters always agree;
 *   4. Export All / Filtered / Selected produce a CSV whose ids exactly match
 *      the chosen read-model scope, show the count before the file, and never
 *      add a row from outside the scope;
 *   5. the 250+ population and a larger seeded project keep the same
 *      invariants, and no UI-only action mutates schedule input.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4198 \
 *   CUBI_TESTED_CODE_SHA=<code commit> node e2e/activity-scope-v26.mjs
 */

import { copyFileSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4198";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-13";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "activity-scope-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `activity-scope-v26-${evidenceDate}`);
const downloadDir = join(artifactsDir, "activity-scope-v26-downloads");
rmSync(outDir, { recursive: true, force: true });
rmSync(evidenceDir, { recursive: true, force: true });
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });
mkdirSync(downloadDir, { recursive: true });

const PROJECT_ID = "preview-rps-01";
const SEED_COUNT = 240;
const SEED_PREFIX = "SX";
const EXTRA_COUNT = 300;
const EXTRA_PREFIX = "SZ";
const STATUS_FILTER_VALUE = "In Progress";

const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const scheduleMutations = [];
const scenarios = [];
const screenshots = [];
const downloads = [];

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
    return details;
  } catch (error) {
    record(id, name, "fail", { error: String(error && error.stack ? error.stack : error) });
    throw error;
  }
}

async function capture(page, name) {
  const file = `activity-scope-v26/${name}.png`;
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

/* ------------------------------------------------------------------ read model */

const openContext = `async () => {
  const response = await fetch("/api/projects/${PROJECT_ID}/open", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: "{}",
  });
  const body = await response.json();
  return { status: response.status, context: body.context };
}`;

async function projectContext(page) {
  const opened = await page.evaluate(`(${openContext})()`, { awaitPromise: true });
  assert(opened.status === 200 && opened.context, `project open failed: ${opened.status}`);
  return opened.context;
}

function contextHeaders(context) {
  return {
    "content-type": "application/json",
    "X-Tenant-Id": context.tenant_id,
    "X-Project-Id": context.project_id,
    "X-Project-Revision": String(context.revision),
  };
}

/** The authoritative activity read model, refreshed with a live project open. */
async function readActivities(page) {
  const context = await projectContext(page);
  const result = await page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${PROJECT_ID}/p6/activities", {
      headers: ${JSON.stringify(contextHeaders(context))},
    });
    const body = await response.json();
    return {
      status: response.status,
      activities: Array.isArray(body.activities)
        ? body.activities.map((entry) => entry.activity).filter(Boolean)
        : [],
    };
  })()`, { awaitPromise: true });
  assert(result.status === 200, `activity read returned ${result.status}`);
  return { context, activities: result.activities };
}

function expectedSearchCount(activities, query) {
  const tokens = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  if (!tokens.length) return activities.length;
  return activities.filter((activity) => {
    const haystack = [
      activity.activity_id,
      activity.name,
      activity.status,
      activity.wbs_id ?? "",
    ].join(" ").toLowerCase();
    return tokens.every((token) => haystack.includes(token));
  }).length;
}

function fingerprint(activities) {
  return JSON.stringify(
    activities
      .map((activity) => [
        activity.activity_id,
        activity.name,
        activity.status,
        activity.wbs_id ?? "",
        activity.duration_value,
        activity.record_revision,
      ])
      .sort((left, right) => String(left[0]).localeCompare(String(right[0]))),
  );
}

/* ------------------------------------------------------------------ seeding */

async function seedActivities(page, context, prefix, count, label, startIndex = 1) {
  const existing = new Set((await readActivities(page)).activities.map((activity) => activity.activity_id));
  const ids = [];
  for (let index = startIndex; index < startIndex + count; index += 1) {
    const id = `${prefix}${String(index).padStart(3, "0")}`;
    if (!existing.has(id)) ids.push({ id, index });
  }
  if (!ids.length) return { created: 0, failures: [] };
  const result = await page.evaluate(`(async () => {
    const headers = ${JSON.stringify(contextHeaders(context))};
    const failures = [];
    const batchSize = 24;
    const jobs = ${JSON.stringify(ids)};
    for (let start = 0; start < jobs.length; start += batchSize) {
      const batch = jobs.slice(start, start + batchSize);
      await Promise.all(batch.map((job) => fetch("/api/projects/${PROJECT_ID}/p6/activities", {
        method: "POST",
        headers,
        body: JSON.stringify({
          contract_version: "p6-activity-master-api.v1",
          activity_id: job.id,
          name: ${JSON.stringify(label)} + " " + job.index,
          duration_value: "2",
          duration_unit: "working-day",
          wbs_id: "WBS-RPS-CIVIL",
          activity_type: "Task Dependent",
          status: "Not Started",
          status_code: "Active",
          percent_complete_type: "DURATION",
          leveling_priority: "Normal",
        }),
      }).then(async (response) => {
        if (!response.ok) failures.push({ id: job.id, status: response.status, body: await response.text() });
      })));
    }
    return { created: jobs.length, failures };
  })()`, { awaitPromise: true });
  assert(result.failures.length === 0, `seed writes failed: ${JSON.stringify(result.failures.slice(0, 3))}`);
  return result;
}

async function reloadWorkspace(page) {
  await page.reload();
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows after reload");
  await sleep(1600);
}

/* ------------------------------------------------------------------ DOM state */

async function countsState(page) {
  const state = await page.evaluate(`(() => {
    const host = document.querySelector("[data-activity-counts]");
    if (!host) return null;
    const number = (name) => Number(host.getAttribute(name) ?? "-1");
    return {
      total: number("data-count-total"),
      filter: number("data-count-filter"),
      search: number("data-count-search"),
      visible: number("data-count-visible"),
      selected: number("data-count-selected"),
      inScope: number("data-count-selected-scope"),
      output: host.querySelector("[data-activity-count]")?.textContent?.trim() ?? "",
      selectAllDisabled: Boolean(document.querySelector("[data-activity-select-all]")?.disabled),
    };
  })()`);
  assert(state, "activity counts host is missing");
  return state;
}

async function gridState(page) {
  return page.evaluate(`(() => {
    const rows = [...document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]")];
    const bars = [...document.querySelectorAll("#cp-gantt [data-gantt-activity-id]")];
    return {
      rows: rows.length,
      rowIds: rows.map((row) => row.getAttribute("data-activity-id")),
      selectedRowIds: rows.filter((row) => row.getAttribute("aria-selected") === "true")
        .map((row) => row.getAttribute("data-activity-id")),
      bars: bars.length,
      pressedBarIds: bars.filter((bar) => bar.getAttribute("aria-pressed") === "true")
        .map((bar) => bar.getAttribute("data-gantt-activity-id")),
      headerLabels: [...document.querySelectorAll("#cp-activity-grid thead th")].map((cell) => (cell.textContent ?? "").trim()),
    };
  })()`);
}

async function clickSelectAll(page) {
  const clicked = await page.evaluate(`(() => {
    const button = document.querySelector("[data-activity-select-all]");
    if (!button || button.disabled) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, "Select All is missing or disabled");
  await sleep(900);
}

async function clickRow(page, index, modifiers = {}) {
  const clickedId = await page.evaluate(`(() => {
    const rows = [...document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]")];
    const row = rows[${index}];
    if (!row) return null;
    row.dispatchEvent(new MouseEvent("click", {
      bubbles: true,
      cancelable: true,
      view: window,
      shiftKey: ${Boolean(modifiers.shift)},
      ctrlKey: ${Boolean(modifiers.ctrl)},
    }));
    return row.getAttribute("data-activity-id");
  })()`);
  assert(clickedId, `row ${index} is missing`);
  await sleep(800);
  return clickedId;
}

async function setSearch(page, value) {
  const changed = await page.evaluate(`(() => {
    const input = document.querySelector("[data-activity-filter]");
    if (!input) return false;
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
    setter.call(input, ${JSON.stringify(value)});
    input.dispatchEvent(new Event("input", { bubbles: true }));
    return true;
  })()`);
  assert(changed, "activity search input is missing");
  await sleep(800);
}

async function clickTreeAction(page, attribute) {
  const clicked = await page.evaluate(`(() => {
    const button = document.querySelector("[${attribute}]");
    if (!button || button.disabled) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `tree action [${attribute}] is unavailable`);
  await sleep(800);
}

/* ------------------------------------------------------------------ filters dialog */

const dialogSelector = "dialog[data-desktop-dialog=filters]";

async function openFilters(page) {
  const clicked = await page.evaluate(`(() => {
    const element = [...document.querySelectorAll('[data-desktop-command="dialog.filters"]')]
      .find((item) => item.getClientRects().length > 0 && !item.disabled);
    if (!element) return false;
    element.click();
    return true;
  })()`);
  assert(clicked, "Filters toolbar command is missing");
  await page.waitForSelector(`${dialogSelector}[open]`, "filters dialog", 8000);
  await sleep(300);
}

async function setFilterSelect(page, index, key, value) {
  const changed = await page.evaluate(`(() => {
    const select = document.querySelector('${dialogSelector} select[name="filter.${key}.${index}"]');
    if (!select) return false;
    select.value = ${JSON.stringify(value)};
    if (select.value !== ${JSON.stringify(value)}) return false;
    select.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  assert(changed, `filter ${key}.${index} did not accept ${value}`);
  await sleep(200);
}

async function setFilterText(page, name, value) {
  const changed = await page.evaluate(`(() => {
    const input = document.querySelector('${dialogSelector} input[name="${name}"]');
    if (!input) return false;
    input.value = ${JSON.stringify(value)};
    input.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  assert(changed, `filter input ${name} is missing`);
  await sleep(150);
}

async function applyStatusFilter(page, status) {
  await openFilters(page);
  // "All Activities" is an explicit show-everything state. A named draft is
  // applied only once that state is cleared, which is the same transition the
  // dialog's own checkboxes use.
  const allCleared = await page.evaluate(`(() => {
    const all = document.querySelector('${dialogSelector} input[name="filterAllActivities"]');
    if (!all) return false;
    if (all.checked) {
      all.checked = false;
      all.dispatchEvent(new Event("change", { bubbles: true }));
    }
    return true;
  })()`);
  assert(allCleared, "All Activities control is missing");
  await setFilterSelect(page, 0, "field", "activity_status");
  await setFilterSelect(page, 0, "operator", "equals");
  await setFilterSelect(page, 0, "value", status);
  // The Version 26 editor only persists a named draft, so the name is part of
  // the apply contract rather than a cosmetic label.
  await setFilterText(page, "filterName", `${status} Only`);
  const preview = await page.evaluate(`(() => {
    const element = document.querySelector("${dialogSelector} [data-filter-preview]");
    return {
      valid: element?.dataset.filterPreviewValid ?? "",
      matched: Number(element?.dataset.filterPreviewMatched ?? "-1"),
      text: element?.textContent?.trim() ?? "",
    };
  })()`);
  assert(preview.valid === "true", `status filter preview is invalid: ${preview.text}`);
  const replace = await page.evaluate(`(() => {
    const input = document.querySelector('${dialogSelector} input[name="filterApplyMode"][value="replace"]');
    if (!input) return false;
    input.checked = true;
    input.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  assert(replace, "Replace apply mode is missing");
  await submitFilters(page);
  return preview;
}

async function clearFilters(page) {
  await openFilters(page);
  const cleared = await page.evaluate(`(() => {
    const all = document.querySelector('${dialogSelector} input[name="filterAllActivities"]');
    if (!all) return false;
    all.checked = true;
    all.dispatchEvent(new Event("change", { bubbles: true }));
    // An empty builder name keeps the draft out of the form so All Activities
    // remains the applied state instead of re-selecting the saved filter.
    const name = document.querySelector('${dialogSelector} input[name="filterName"]');
    if (name) {
      name.value = "";
      name.dispatchEvent(new Event("change", { bubbles: true }));
    }
    const replace = document.querySelector('${dialogSelector} input[name="filterApplyMode"][value="replace"]');
    if (replace) {
      replace.checked = true;
      replace.dispatchEvent(new Event("change", { bubbles: true }));
    }
    return true;
  })()`);
  assert(cleared, "All Activities control is missing");
  await submitFilters(page);
}

async function submitFilters(page) {
  const clicked = await page.evaluate(`(() => {
    const button = document.querySelector('${dialogSelector} [data-dialog-ok]');
    if (!button || button.disabled) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, "Filters OK is missing");
  await page.waitFor(`!document.querySelector('${dialogSelector}')?.open`, "filters dialog closed", 8000);
  await sleep(1200);
}

/* ------------------------------------------------------------------ export dialog and CSV */

async function openExport(page) {
  const clicked = await page.evaluate(`(() => {
    const button = document.querySelector("[data-activity-export-open]");
    if (!button || button.disabled) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, "Export command is missing or disabled");
  await page.waitFor(`Boolean(document.querySelector("[data-activity-export-dialog]")?.open)`, "export dialog", 6000);
  await sleep(250);
}

async function exportDialogState(page) {
  return page.evaluate(`(() => {
    const dialog = document.querySelector("[data-activity-export-dialog]");
    if (!dialog) return null;
    return {
      active: dialog.dataset.activityExportActive ?? "",
      total: Number(dialog.dataset.exportTotal ?? "-1"),
      filter: Number(dialog.dataset.exportFilter ?? "-1"),
      search: Number(dialog.dataset.exportSearch ?? "-1"),
      selected: Number(dialog.dataset.exportSelected ?? "-1"),
      summary: dialog.querySelector("[data-activity-export-summary]")?.textContent?.trim() ?? "",
      scopes: [...dialog.querySelectorAll("[data-activity-export-scope]")].map((button) => ({
        scope: button.dataset.activityExportScope,
        count: Number(button.querySelector("[data-export-scope-count]")?.textContent ?? "-1"),
        disabled: button.disabled,
        checked: button.getAttribute("aria-checked") === "true",
      })),
      downloadDisabled: Boolean(dialog.querySelector("[data-activity-export-download]")?.disabled),
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    };
  })()`);
}

async function chooseExportScope(page, scope) {
  const selected = await page.evaluate(`(() => {
    const button = document.querySelector('[data-activity-export-scope="${scope}"]');
    if (!button || button.disabled) return false;
    button.click();
    return true;
  })()`);
  assert(selected, `export scope ${scope} is missing or disabled`);
  await sleep(200);
  return exportDialogState(page);
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (quoted) {
      if (char === '"') {
        if (text[index + 1] === '"') {
          cell += '"';
          index += 1;
        } else {
          quoted = false;
        }
      } else {
        cell += char;
      }
      continue;
    }
    if (char === '"') quoted = true;
    else if (char === ",") {
      row.push(cell);
      cell = "";
    } else if (char === "\r" || char === "\n") {
      if (char === "\r" && text[index + 1] === "\n") index += 1;
      row.push(cell);
      rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += char;
    }
  }
  if (cell.length || row.length) {
    row.push(cell);
    rows.push(row);
  }
  return rows;
}

function csvIds(text) {
  const rows = parseCsv(text);
  assert(rows.length >= 1, "CSV has no header");
  const header = rows[0];
  let idIndex = header.findIndex((label) => /activity id/i.test(label));
  if (idIndex < 0) idIndex = 0;
  const data = rows.slice(1).filter((cells) => cells.some((cell) => cell.trim() !== ""));
  return { header, idIndex, ids: data.map((cells) => cells[idIndex]), rows: data };
}

async function waitForDownload(fileName, timeoutMs = 20000) {
  const deadline = Date.now() + timeoutMs;
  const target = join(downloadDir, fileName);
  while (Date.now() < deadline) {
    const entries = readdirSync(downloadDir);
    if (entries.includes(fileName)) {
      const text = readFileSync(target, "utf8");
      return { fileName, text };
    }
    await sleep(150);
  }
  throw new Error(`download ${fileName} did not appear in ${downloadDir}`);
}

async function downloadExport(page, scope, expectedName) {
  const before = await exportDialogState(page);
  const afterScope = await chooseExportScope(page, scope);
  assert(afterScope.active === scope, `active export scope is ${afterScope.active}`);
  const expectedCount = scope === "all" ? afterScope.total : scope === "filtered" ? afterScope.search : afterScope.selected;
  assert(expectedCount > 0, `${scope} scope has no rows: ${JSON.stringify(afterScope)}`);
  assert(/rows will be exported/i.test(afterScope.summary), `scope summary is missing: ${afterScope.summary}`);
  rmSync(join(downloadDir, expectedName), { force: true });
  const clicked = await page.evaluate(`(() => {
    const button = document.querySelector("[data-activity-export-download]");
    if (!button || button.disabled) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, "Download CSV is missing or disabled");
  const file = await waitForDownload(expectedName);
  const parsed = csvIds(file.text);
  downloads.push({ scope, fileName: file.fileName, dataRows: parsed.ids.length, dialogCount: expectedCount });
  assert(parsed.ids.length === expectedCount, `${scope} CSV has ${parsed.ids.length} rows, dialog said ${expectedCount}`);
  return { ...parsed, fileName: file.fileName, before, afterScope, expectedCount };
}

/* ------------------------------------------------------------------ schedule authority */

async function authoritativeCount(page, session) {
  const context = await projectContext(page);
  const result = await page.evaluate(`(async () => {
    const headers = ${JSON.stringify(contextHeaders(context))};
    const publish = await fetch("/api/projects/${PROJECT_ID}/p6/schedule/snapshots", {
      method: "POST",
      headers,
      body: JSON.stringify({ contract_version: "p6-schedule-snapshot-api.v1", timezone: "UTC" }),
    });
    const snapshot = await publish.json();
    if (!publish.ok) return { error: "PUBLISH_" + publish.status, body: snapshot };
    const query = await fetch("/api/v1/schedule/query", {
      method: "POST",
      headers,
      body: JSON.stringify({
        contract_version: "schedule-query.v1",
        query_id: crypto.randomUUID(),
        scope: {
          tenant_id: ${JSON.stringify(context.tenant_id)},
          project_id: ${JSON.stringify(context.project_id)},
          project_revision: ${Number(context.revision)},
        },
        requested_by: ${JSON.stringify(session)},
        query_text: "ACT-020 scope invariant",
        kind: "fact",
        language: "en",
        constraints: { snapshot_id: snapshot.snapshot_id },
      }),
    });
    const body = await query.json();
    if (!query.ok) return { error: "QUERY_" + query.status, body };
    return {
      snapshotId: snapshot.snapshot_id,
      activityCount: body?.data?.activity_count ?? null,
      activityKeys: Object.keys(body?.data?.activities ?? {}).length,
    };
  })()`, { awaitPromise: true });
  assert(!result.error, `authoritative query failed: ${result.error}`);
  return result;
}

/* ------------------------------------------------------------------ main */

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
    if (url.includes("/api/") && params.response.status >= 500) apiFailures.push({ status: params.response.status, url });
  });
  page.cdp.on("Network.requestWillBeSent", (params) => {
    const request = params.request ?? {};
    const url = request.url ?? "";
    const method = request.method ?? "";
    if (!["POST", "PUT", "PATCH", "DELETE"].includes(method)) return;
    if (!trackScheduleWrites) return;
    if (url.includes("/p6/activities") || url.includes("/p6/schedule") || url.includes("/api/v1/schedule")) {
      scheduleMutations.push({ method, url, at: new Date().toISOString() });
    }
  });

  const report = {
    contract: "cubi-activity-scope-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    expected: {},
    scenarios,
    screenshots,
    downloads,
    scheduleMutations,
    exceptions,
    consoleErrors,
    apiFailures,
  };

  function writeReport() {
    report.scenarios = scenarios;
    report.passed = scenarios.filter((entry) => entry.status === "pass").length;
    report.failed = scenarios.filter((entry) => entry.status === "fail").length;
    const json = JSON.stringify(report, null, 2);
    writeFileSync(join(outDir, "activity-scope-v26.json"), json);
    writeFileSync(join(evidenceDir, "activity-scope-v26.json"), json);
  }

  const state = { context: null, session: null, total: 0, seeded: 0, extraSeeded: 0 };
  let trackScheduleWrites = true;

  try {
    await page.cdp.send("Page.setDownloadBehavior", {
      behavior: "allow",
      downloadPath: downloadDir,
    }).catch(async () => {
      await page.cdp.send("Browser.setDownloadBehavior", {
        behavior: "allow",
        downloadPath: downloadDir,
        eventsEnabled: true,
      });
    });

    await setViewport(page, 1366, 768);
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
    const persona = await page.evaluate(`(() => {
      const button = document.querySelector('button[name="role"][value="admin"]');
      if (!button) return false;
      button.click();
      return true;
    })()`);
    assert(persona, "admin persona button is missing");
    await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
    await page.click('[data-project-id="preview-rps-01"]');
    await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
    await sleep(1600);

    state.context = await projectContext(page);
    state.session = await page.evaluate(`(async () => {
      const response = await fetch("/api/session");
      const body = await response.json();
      return body.user_id ?? null;
    })()`, { awaitPromise: true });
    assert(state.session, "session user id is missing");

    const beforeSeed = await readActivities(page);
    const seed = await seedActivities(page, beforeSeed.context, SEED_PREFIX, SEED_COUNT, "Scale seed");
    state.seeded = seed.created;
    await reloadWorkspace(page);
    let read = await readActivities(page);
    state.total = read.activities.length;
    assert(state.total >= 250, `expected a 250+ population, read ${state.total}`);
    assert(state.total === beforeSeed.activities.length + seed.created, `read model ${state.total} != baseline + ${seed.created}`);
    report.expected.afterSeed = { total: state.total, seeded: state.seeded };
    scheduleMutations.length = 0;

    await scenario("01", "Read model, table, Gantt and counters agree before any selection", async () => {
      const counts = await countsState(page);
      const grid = await gridState(page);
      assert(counts.total === state.total, `counter total ${counts.total} != read model ${state.total}`);
      assert(counts.filter === state.total, `no filter is active but filter count is ${counts.filter}`);
      assert(counts.search === state.total, `empty search should keep ${state.total}, got ${counts.search}`);
      assert(counts.selected === 0, `fresh state selected ${counts.selected}`);
      assert(counts.visible === state.total, `visible ${counts.visible} != ${state.total}`);
      assert(grid.rows === state.total, `table rows ${grid.rows} != read model ${state.total}`);
      assert(grid.bars === state.total, `Gantt bars ${grid.bars} != read model ${state.total}`);
      assert(grid.selectedRowIds.length === 0 && grid.pressedBarIds.length === 0, "a fresh grid already has selected rows");
      await capture(page, "01-baseline-counts");
      return { total: state.total, rows: grid.rows, bars: grid.bars };
    });

    await scenario("02", "Select All selects the full 250+ project, not just painted rows", async () => {
      const expected = new Set((await readActivities(page)).activities.map((activity) => activity.activity_id));
      await clickSelectAll(page);
      const counts = await countsState(page);
      const grid = await gridState(page);
      assert(counts.selected === state.total, `selected ${counts.selected} != project ${state.total}`);
      assert(counts.inScope === state.total, `selected-in-scope ${counts.inScope} != ${state.total}`);
      assert(grid.selectedRowIds.length === expected.size, `aria-selected rows ${grid.selectedRowIds.length} != ${expected.size}`);
      assert(grid.pressedBarIds.length === grid.bars, `pressed bars ${grid.pressedBarIds.length} != ${grid.bars}`);
      assert(grid.selectedRowIds.every((id) => expected.has(id)), "a selected row is outside the authoritative project");
      await capture(page, "02-select-all-full-project");
      return { selected: counts.selected, rows: grid.rows, bars: grid.bars, scope: expected.size };
    });

    await scenario("03", "A Shift range selects the inclusive displayed interval and sets one primary row", async () => {
      await clickRow(page, 2);
      let counts = await countsState(page);
      assert(counts.selected === 1, `plain click selected ${counts.selected}`);
      const ids = (await gridState(page)).rowIds;
      const target = await clickRow(page, 6, { shift: true });
      counts = await countsState(page);
      const expected = ids.slice(2, 7);
      assert(counts.selected === expected.length, `range selected ${counts.selected}, expected ${expected.length}`);
      const grid = await gridState(page);
      assert(
        JSON.stringify(grid.selectedRowIds) === JSON.stringify(expected),
        `range selection ${JSON.stringify(grid.selectedRowIds)} != ${JSON.stringify(expected)}`,
      );
      assert(grid.selectedRowIds.includes(target), "the range target is not selected");
      await capture(page, "03-range-selection");
      return { anchor: ids[2], target, selected: counts.selected };
    });

    await scenario("04", "Ctrl subtracts one activity without clearing the rest of the selection", async () => {
      const gridBefore = await gridState(page);
      const removed = gridBefore.selectedRowIds[2];
      const clicked = await clickRow(page, 4, { ctrl: true });
      assert(clicked === removed, `Ctrl-click hit ${clicked}, expected ${removed}`);
      const counts = await countsState(page);
      const grid = await gridState(page);
      assert(counts.selected === gridBefore.selectedRowIds.length - 1, `selected ${counts.selected} after removing one from ${gridBefore.selectedRowIds.length}`);
      assert(!grid.selectedRowIds.includes(removed), `${removed} is still selected`);
      assert(grid.selectedRowIds.length === counts.selected, "DOM and counter selection disagree");
      const readded = await clickRow(page, 4, { ctrl: true });
      assert(readded === removed, "Ctrl-click did not restore the removed row");
      const restored = await countsState(page);
      assert(restored.selected === gridBefore.selectedRowIds.length, `restoring selected ${restored.selected}`);
      await clickRow(page, 2);
      return { removed, afterRemoval: counts.selected, restored: restored.selected };
    });

    await scenario("05", "Search after Select All keeps the selection but narrows the scope count", async () => {
      await clickSelectAll(page);
      const full = await countsState(page);
      assert(full.selected === state.total, `Select All selected ${full.selected}`);
      await setSearch(page, SEED_PREFIX);
      const sxExpected = expectedSearchCount(read.activities, SEED_PREFIX);
      assert(sxExpected === SEED_COUNT, `read model says ${sxExpected} SX activities, expected ${SEED_COUNT}`);
      let counts = await countsState(page);
      let grid = await gridState(page);
      assert(counts.search === sxExpected, `search count ${counts.search} != ${sxExpected}`);
      assert(counts.visible === sxExpected && grid.rows === sxExpected && grid.bars === sxExpected, `table/Gantt/search counts disagree: ${JSON.stringify({ counts, rows: grid.rows, bars: grid.bars, expected: sxExpected })}`);
      assert(counts.selected === state.total, `search change dropped selection to ${counts.selected}`);
      assert(counts.inScope === sxExpected, `in-scope ${counts.inScope} != ${sxExpected}`);
      await clickSelectAll(page);
      counts = await countsState(page);
      assert(counts.selected === sxExpected, `Select All in scope selected ${counts.selected} != ${sxExpected}`);
      assert(counts.inScope === sxExpected, `in-scope after scoped Select All ${counts.inScope}`);
      const selectionBefore = new Set((await gridState(page)).selectedRowIds);
      await setSearch(page, `${SEED_PREFIX}02`);
      const narrowExpected = expectedSearchCount(read.activities, `${SEED_PREFIX}02`);
      counts = await countsState(page);
      grid = await gridState(page);
      assert(narrowExpected > 0 && narrowExpected < sxExpected, `unexpected narrow search count ${narrowExpected}`);
      assert(counts.search === narrowExpected, `narrow search ${counts.search} != ${narrowExpected}`);
      assert(counts.visible === narrowExpected && grid.rows === narrowExpected && grid.bars === narrowExpected, "narrow search table/Gantt disagree");
      assert(counts.selected === sxExpected, `selection after a second search change ${counts.selected} != ${sxExpected}`);
      assert(counts.inScope === narrowExpected, `in-scope ${counts.inScope} != ${narrowExpected}`);
      assert([...selectionBefore].every((id) => id.startsWith(SEED_PREFIX)), "a non-SX id entered the selection");
      await capture(page, "04-search-after-selection");
      return { full: state.total, search: sxExpected, narrow: narrowExpected, selected: counts.selected, inScope: counts.inScope };
    });

    await scenario("06", "A Filters-dialog change after selection keeps it and recomputes the in-scope count", async () => {
      const readNow = await readActivities(page);
      const expected = readNow.activities.filter((activity) => activity.status === STATUS_FILTER_VALUE).length;
      assert(expected > 0 && expected < readNow.activities.length, `status filter count ${expected} is not partial`);
      const selectedBefore = (await countsState(page)).selected;
      await setSearch(page, "");
      const preview = await applyStatusFilter(page, STATUS_FILTER_VALUE);
      let counts = await countsState(page);
      let grid = await gridState(page);
      assert(preview.matched === expected, `dialog preview ${preview.matched} != read model ${expected}`);
      assert(counts.filter === expected, `filter count ${counts.filter} != ${expected}`);
      assert(counts.search === expected, `search count ${counts.search} != ${expected}`);
      assert(counts.visible === expected && grid.rows === expected && grid.bars === expected, "filtered table/Gantt/filter counts disagree");
      assert(counts.selected === selectedBefore, `filter change dropped selection ${selectedBefore} -> ${counts.selected}`);
      const selectedIds = new Set(grid.selectedRowIds);
      assert(counts.selected === selectedBefore, "selection was not preserved across the filter change");
      const expectedInScope = 0; // every selected SX seed is "Not Started"
      assert(counts.inScope === expectedInScope, `in-scope selected ${counts.inScope} != ${expectedInScope}`);
      assert(selectedIds.size === 0, `filtered DOM still paints ${selectedIds.size} selected rows`);
      await clickSelectAll(page);
      counts = await countsState(page);
      grid = await gridState(page);
      assert(counts.selected === expected, `Select All on the filter selected ${counts.selected} != ${expected}`);
      assert(grid.selectedRowIds.length === expected, `filtered selection painted ${grid.selectedRowIds.length}`);
      await capture(page, "05-filter-after-selection");
      await clearFilters(page);
      counts = await countsState(page);
      grid = await gridState(page);
      assert(counts.filter === state.total && counts.search === state.total, `All Activities left filter ${counts.filter}/search ${counts.search}`);
      assert(counts.visible === state.total && grid.rows === state.total, "All Activities did not restore the grid");
      assert(counts.selected === expected, `clearing the filter dropped selection to ${counts.selected}`);
      assert(counts.inScope === expected, `clearing the filter changed in-scope selection to ${counts.inScope}`);
      return { expected, selectedBefore, selectedAfter: counts.selected, inScope: counts.inScope };
    });

    await scenario("07", "Collapse and expand during Select All never narrows the selection", async () => {
      await clickSelectAll(page);
      const full = await countsState(page);
      assert(full.selected === state.total, `Select All selected ${full.selected}`);
      await clickTreeAction(page, "data-wbs-collapse-all");
      let counts = await countsState(page);
      let grid = await gridState(page);
      assert(counts.visible < state.total, `collapse still paints ${counts.visible} rows`);
      assert(grid.rows === counts.visible && grid.bars === counts.visible, `collapsed table ${grid.rows}/Gantt ${grid.bars}/visible ${counts.visible} disagree`);
      assert(counts.selected === state.total, `collapse changed selection to ${counts.selected}`);
      assert(counts.inScope === state.total, `collapse changed in-scope selection to ${counts.inScope}`);
      assert(counts.search === state.total, `collapse changed the search scope to ${counts.search}`);
      const collapsedVisible = counts.visible;
      await capture(page, "06-collapse-during-selection");
      await clickTreeAction(page, "data-wbs-expand-all");
      counts = await countsState(page);
      grid = await gridState(page);
      assert(counts.visible === state.total && grid.rows === state.total, "expand did not restore every row");
      assert(counts.selected === state.total && grid.selectedRowIds.length === state.total, "expanded selection lost rows");
      return { collapsedVisible: collapsedVisible, selected: counts.selected, restored: grid.rows };
    });

    await scenario("08", "Table and Gantt counts match under search and collapse", async () => {
      await setSearch(page, SEED_PREFIX);
      const searchCount = expectedSearchCount(read.activities, SEED_PREFIX);
      let counts = await countsState(page);
      let grid = await gridState(page);
      assert(counts.visible === searchCount && grid.rows === searchCount && grid.bars === searchCount, "search table/Gantt mismatch");
      await clickTreeAction(page, "data-wbs-collapse-all");
      counts = await countsState(page);
      grid = await gridState(page);
      assert(grid.rows === grid.bars, `collapsed table ${grid.rows} != Gantt ${grid.bars}`);
      assert(grid.rows === counts.visible, `collapsed table ${grid.rows} != visible counter ${counts.visible}`);
      assert(counts.search === searchCount, `collapse changed the search scope to ${counts.search}`);
      assert(counts.selected === state.total, "collapse changed the selection");
      await clickTreeAction(page, "data-wbs-expand-all");
      await setSearch(page, "");
      await sleep(400);
      return { searchCount, collapsedVisible: counts.visible };
    });

    await scenario("09", "Export All writes the complete read model with an API-derived id set", async () => {
      const apiActivities = (await readActivities(page)).activities;
      const apiIds = new Set(apiActivities.map((activity) => activity.activity_id));
      await openExport(page);
      const dialog = await exportDialogState(page);
      assert(dialog.total === apiIds.size, `dialog total ${dialog.total} != read model ${apiIds.size}`);
      assert(dialog.scopes.find((scope) => scope.scope === "all")?.count === apiIds.size, "All scope count is wrong");
      const exportResult = await downloadExport(page, "all", `${PROJECT_ID}-activities-all.csv`);
      assert(exportResult.ids.length === apiIds.size, `CSV ${exportResult.ids.length} != ${apiIds.size}`);
      assert(exportResult.ids.every((id) => apiIds.has(id)), "Export All emitted an unknown activity id");
      assert(new Set(exportResult.ids).size === exportResult.ids.length, "Export All emitted duplicate rows");
      await capture(page, "07-export-all");
      return { rows: exportResult.ids.length, fileName: exportResult.fileName ?? `${PROJECT_ID}-activities-all.csv` };
    });

    await scenario("10", "Export scopes include rows that grouping keeps out of the DOM", async () => {
      // Collapse is a browsing preference: with no query active it hides rows
      // from the DOM, but the export scope still counts every project activity.
      await clickTreeAction(page, "data-wbs-collapse-all");
      const collapsed = await countsState(page);
      assert(collapsed.visible < state.total, `collapse still paints ${collapsed.visible} rows`);
      await openExport(page);
      let dialog = await exportDialogState(page);
      assert(dialog.total === state.total, `collapsed dialog total ${dialog.total} != ${state.total}`);
      const allResult = await downloadExport(page, "all", `${PROJECT_ID}-activities-all.csv`);
      assert(allResult.ids.length === state.total, `collapsed Export All wrote ${allResult.ids.length} of ${state.total}`);
      await capture(page, "08-export-all-collapsed");
      await clickTreeAction(page, "data-wbs-expand-all");

      // Filtered export uses the quick-search scope and must contain exactly
      // the matching ids, never the rows painted at some earlier moment.
      const searchCount = expectedSearchCount(read.activities, SEED_PREFIX);
      await setSearch(page, SEED_PREFIX);
      const filteredCounts = await countsState(page);
      assert(filteredCounts.visible === searchCount, `filtered scope paints ${filteredCounts.visible} != ${searchCount}`);
      await openExport(page);
      dialog = await exportDialogState(page);
      assert(dialog.search === searchCount, `filtered dialog ${dialog.search} != ${searchCount}`);
      assert(dialog.scopes.find((scope) => scope.scope === "filtered")?.count === searchCount, "filtered scope count is wrong");
      const exportResult = await downloadExport(page, "filtered", `${PROJECT_ID}-activities-filtered.csv`);
      assert(exportResult.ids.length === searchCount, `filtered CSV ${exportResult.ids.length} != ${searchCount}`);
      assert(exportResult.ids.every((id) => id.startsWith(SEED_PREFIX)), "filtered CSV contains an out-of-scope id");
      await capture(page, "09-export-filtered");
      await setSearch(page, "");
      return { collapsedVisible: collapsed.visible, allRows: allResult.ids.length, filteredRows: exportResult.ids.length };
    });

    await scenario("11", "Export Selected writes exactly the retained selection from the read model", async () => {
      await setSearch(page, SEED_PREFIX);
      await clickSelectAll(page);
      const counts = await countsState(page);
      assert(counts.selected === SEED_COUNT, `selection before export ${counts.selected} != ${SEED_COUNT}`);
      await openExport(page);
      const dialog = await exportDialogState(page);
      assert(dialog.selected === SEED_COUNT, `dialog selected ${dialog.selected} != ${SEED_COUNT}`);
      assert(dialog.scopes.find((scope) => scope.scope === "selected")?.count === SEED_COUNT, "selected scope count is wrong");
      const exportResult = await downloadExport(page, "selected", `${PROJECT_ID}-activities-selected.csv`);
      assert(exportResult.ids.length === SEED_COUNT, `selected CSV ${exportResult.ids.length} != ${SEED_COUNT}`);
      assert(exportResult.ids.every((id) => id.startsWith(SEED_PREFIX)), "selected CSV contains a non-selected id");
      assert(new Set(exportResult.ids).size === SEED_COUNT, "selected CSV emitted duplicate rows");
      const grid = await gridState(page);
      assert(grid.selectedRowIds.length === SEED_COUNT, `painted selection ${grid.selectedRowIds.length} != ${SEED_COUNT}`);
      await capture(page, "09-export-selected");
      await setSearch(page, "");
      return { selected: counts.selected, exported: exportResult.ids.length };
    });

    await scenario("12", "A larger seeded project keeps Select All and Export Selected exact", async () => {
      const extra = await seedActivities(page, (await readActivities(page)).context, EXTRA_PREFIX, EXTRA_COUNT, "Capacity seed", 1);
      state.extraSeeded = extra.created;
      assert(extra.created === EXTRA_COUNT || extra.created === 0, `seeded ${extra.created} extra activities`);
      await reloadWorkspace(page);
      read = await readActivities(page);
      const total = read.activities.length;
      assert(total >= 500, `larger population is only ${total}`);
      const extraIds = read.activities.filter((activity) => activity.activity_id.startsWith(EXTRA_PREFIX)).length;
      assert(extraIds === EXTRA_COUNT, `read model holds ${extraIds} of ${EXTRA_COUNT} extra activities`);
      const counts = await countsState(page);
      const grid = await gridState(page);
      assert(counts.total === total, `counter total ${counts.total} != ${total}`);
      assert(grid.rows === total && grid.bars === total, `larger table ${grid.rows}/Gantt ${grid.bars} != ${total}`);
      assert(grid.rowIds.length === total, "the grid sliced the larger population");
      await clickSelectAll(page);
      const selected = await countsState(page);
      assert(selected.selected === total, `Select All selected ${selected.selected} != ${total}`);
      await openExport(page);
      const dialog = await exportDialogState(page);
      assert(dialog.selected === total && dialog.total === total, `export dialog ${dialog.selected}/${dialog.total} != ${total}`);
      const exportResult = await downloadExport(page, "selected", `${PROJECT_ID}-activities-selected.csv`);
      assert(exportResult.ids.length === total, `large selected CSV ${exportResult.ids.length} != ${total}`);
      assert(new Set(exportResult.ids).size === total, "large selected CSV emitted duplicates");
      await capture(page, "10-large-population");
      state.total = total;
      return { total, seeded: extra.created, exported: exportResult.ids.length };
    });

    await scenario("13", "Selection, search, filter and export never mutate schedule input", async () => {
      scheduleMutations.length = 0;
      const before = await readActivities(page);
      await clickSelectAll(page);
      await setSearch(page, EXTRA_PREFIX);
      await setSearch(page, "");
      await clickTreeAction(page, "data-wbs-collapse-all");
      await clickTreeAction(page, "data-wbs-expand-all");
      await openExport(page);
      await chooseExportScope(page, "all");
      await page.evaluate(`document.querySelector("[data-activity-export-cancel]")?.click()`);
      await sleep(300);
      const after = await readActivities(page);
      assert(fingerprint(before.activities) === fingerprint(after.activities), "UI-only actions changed the activity read model");
      assert(scheduleMutations.length === 0, `UI-only actions wrote schedule/activity endpoints: ${JSON.stringify(scheduleMutations.slice(0, 3))}`);
      // The snapshot publication below is deliberate evidence, not a UI write,
      // so it is excluded from the mutation audit.
      trackScheduleWrites = false;
      const authoritative = await authoritativeCount(page, state.session);
      assert(authoritative.activityCount === after.activities.length, `snapshot ${authoritative.activityCount} != read model ${after.activities.length}`);
      assert(authoritative.activityKeys === after.activities.length, `snapshot keys ${authoritative.activityKeys} != ${after.activities.length}`);
      return { activities: after.activities.length, snapshot: authoritative.activityCount, mutations: scheduleMutations.length };
    });

    await scenario("14", "An empty scope cannot be selected or exported as if it had rows", async () => {
      // Selection is in-memory only, so a reload proves the zero-selection case
      // without inventing a DOM-only reset command.
      await reloadWorkspace(page);
      await setSearch(page, "NO_MATCH_ACTIVITY_ZZZ");
      const counts = await countsState(page);
      assert(counts.search === 0 && counts.visible === 0, `empty search left ${counts.search}/${counts.visible}`);
      const grid = await gridState(page);
      assert(grid.rows === 0 && grid.bars === 0, "empty search still paints rows");
      assert(counts.selectAllDisabled, "Select All stays enabled on an empty scope");
      await openExport(page);
      const dialog = await exportDialogState(page);
      const filtered = dialog.scopes.find((scope) => scope.scope === "filtered");
      assert(filtered && filtered.disabled && filtered.count === 0, "Filtered scope is not disabled at zero rows");
      const selected = dialog.scopes.find((scope) => scope.scope === "selected");
      assert(selected && selected.disabled, "Selected scope is not disabled with no selection");
      await page.evaluate(`document.querySelector("[data-activity-export-cancel]")?.click()`);
      await sleep(250);
      await setSearch(page, "");
      return { search: counts.search, filteredDisabled: true, selectedDisabled: true };
    });

    await scenario("15", "The new controls localize and fit a Persian RTL cell", async () => {
      await setLanguage(page, "fa");
      const state = await page.evaluate(`(() => {
        const host = document.querySelector("[data-activity-counts]");
        return {
          dir: document.documentElement.dir,
          overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
          labels: [...document.querySelectorAll("[data-count-item]")].map((item) => item.textContent.trim()),
          selectAll: document.querySelector("[data-activity-select-all]")?.textContent?.trim() ?? "",
          exportLabel: document.querySelector("[data-activity-export-open]")?.textContent?.trim() ?? "",
          selected: Number(host?.getAttribute("data-count-selected") ?? "-1"),
          total: Number(host?.getAttribute("data-count-total") ?? "-1"),
        };
      })()`);
      assert(state.dir === "rtl", `workspace direction is ${state.dir}`);
      assert(state.overflow <= 1, `RTL workspace overflows by ${state.overflow}px`);
      assert(state.labels.some((label) => /کل/.test(label)), `Persian counts are missing: ${state.labels.join(" | ")}`);
      assert(/انتخاب/.test(state.selectAll) && /خروجی/.test(state.exportLabel), `Persian actions are missing: ${state.selectAll}/${state.exportLabel}`);
      assert(state.total > 0, "counts lost their total in RTL");
      await openExport(page);
      const dialog = await exportDialogState(page);
      assert(dialog.overflow <= 1, `RTL export dialog overflows by ${dialog.overflow}px`);
      await capture(page, "11-rtl-export");
      await page.evaluate(`document.querySelector("[data-activity-export-cancel]")?.click()`);
      await setLanguage(page, "en");
      return { dir: state.dir, overflow: state.overflow, total: state.total };
    });

    assert(exceptions.length === 0, `browser exceptions: ${JSON.stringify(exceptions.slice(0, 3))}`);
    assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors.slice(0, 3))}`);
    assert(apiFailures.length === 0, `API 5xx: ${JSON.stringify(apiFailures.slice(0, 3))}`);
  } catch (error) {
    log(`\nFAILED: ${error && error.stack ? error.stack : error}`);
    report.finishedAt = new Date().toISOString();
    writeReport();
    throw error;
  } finally {
    report.finishedAt = new Date().toISOString();
    writeReport();
  }

  log(`\nScenarios: ${scenarios.filter((entry) => entry.status === "pass").length} passed, ${scenarios.filter((entry) => entry.status === "fail").length} failed`);
  log(`Evidence: ${join(evidenceDir, "activity-scope-v26.json")}`);
  await chrome.close?.();
}

main().catch((error) => {
  process.stderr.write(`\n${error && error.stack ? error.stack : error}\n`);
  process.exit(1);
});
