#!/usr/bin/env node
/**
 * Version 26 activity grouping and sorting acceptance (ACT-002).
 *
 * Proves in the real preview that the Group and Sort dialog drives the table
 * with an ordered multi-level group and sort plan: WBS bands, value bands for
 * other activity fields, bands nested two levels deep, independent collapse,
 * the Gantt following the same rows, and the saved Activities layout restoring
 * the whole plan after a full reload. Every expected order is computed from the
 * rendered rows; no fixture value is injected into the document.
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

const PROJECT_ID = "preview-rps-01";

/**
 * Reads the same persisted rows the table renders, through the public
 * workspace read API, so every expected band is derived from stored facts
 * instead of a value injected into the document.
 */
async function readWorkspace(page) {
  return page.evaluate(`(async () => {
    const scopeResponse = await fetch("/api/projects/${PROJECT_ID}/p6/formula-columns");
    const scope = await scopeResponse.json();
    const response = await fetch("/api/v2/workspace/control-room/read", {
      headers: {
        "X-Tenant-Id": scope.scope.tenant_id,
        "X-Project-Id": "${PROJECT_ID}",
        "X-Project-Revision": String(scope.scope.project_revision),
      },
    });
    const payload = await response.json();
    const workspace = payload?.workspace ?? {};
    return {
      activities: (workspace.activities ?? []).map((activity) => ({
        id: activity.id,
        wbsId: activity.wbs_id ?? activity.wbsId ?? "",
        code: activity.code ?? "",
        cells: activity.cells ?? {},
        ganttCritical: activity.gantt?.critical ?? null,
      })),
      wbsNodes: (workspace.wbs_nodes ?? []).map((node) => ({
        id: node.wbs_id ?? node.wbsId ?? "",
        parentKind: node.parent_kind ?? node.parentKind ?? "project",
        parentWbsId: node.parent_wbs_id ?? node.parentWbsId ?? null,
        localCode: node.local_code ?? node.localCode ?? "",
        sequenceNumber: Number(node.sequence_number ?? node.sequenceNumber ?? 0),
      })),
    };
  })()`, { awaitPromise: true });
}

function readGroupValue(activity, fieldId) {
  const cells = activity.cells ?? {};
  switch (fieldId) {
    case "wbs": return activity.wbsId || cells["activity.wbs"] || null;
    case "activity_status": return cells["activity.status"] ?? cells["activity.activity_status"] ?? null;
    case "activity_type": return cells["activity.type"] ?? cells["activity.activity_type"] ?? null;
    case "is_critical": return cells["activity.is_critical"] ?? activity.ganttCritical ?? null;
    case "activity_code": return activity.code || null;
    case "total_float": return cells["activity.total_float"] ?? null;
    default: return cells[fieldId] ?? null;
  }
}

function groupKeyOf(value) {
  if (value === null || value === undefined) return "e:";
  if (typeof value === "boolean") return value ? "b:true" : "b:false";
  if (typeof value === "number") return Number.isFinite(value) ? `n:${value}` : "e:";
  const text = String(value).trim();
  return text === "" ? "e:" : `s:${text}`;
}

function groupLabelOf(fieldId, value) {
  if (groupKeyOf(value) === "e:") return "No value";
  if (fieldId === "is_critical") {
    return value === true || String(value).toLowerCase() === "true" ? "Critical" : "Non-critical";
  }
  return String(value);
}

function naturalCompare(left, right) {
  return collator.compare(String(left), String(right));
}

function compareGroupValues(left, right) {
  if (typeof left === "number" && typeof right === "number") return left === right ? 0 : left < right ? -1 : 1;
  if (typeof left === "boolean" && typeof right === "boolean") return left === right ? 0 : left ? -1 : 1;
  return naturalCompare(left, right);
}

function compareGroupBands(left, right, direction) {
  const leftEmpty = groupKeyOf(left) === "e:";
  const rightEmpty = groupKeyOf(right) === "e:";
  if (leftEmpty || rightEmpty) return leftEmpty === rightEmpty ? 0 : leftEmpty ? 1 : -1;
  return (direction === "desc" ? -1 : 1) * compareGroupValues(left, right);
}

/** The exact sibling bands a single field level must render, in order. */
function expectedFieldBands(activities, fieldId, direction) {
  const groups = new Map();
  for (const activity of activities) {
    const value = readGroupValue(activity, fieldId);
    const key = groupKeyOf(value);
    const group = groups.get(key) ?? { value, count: 0 };
    group.count += 1;
    groups.set(key, group);
  }
  return [...groups.entries()]
    .sort(([leftKey, left], [rightKey, right]) =>
      compareGroupBands(left.value, right.value, direction) || naturalCompare(leftKey, rightKey))
    .map(([key, group]) => ({ key, label: groupLabelOf(fieldId, group.value), count: group.count }));
}

function renderedFieldBands(state, fieldId) {
  return state.fieldBands.filter((band) => band.field === fieldId);
}

/** Compares a stored plan by meaning; the API may order object keys freely. */
function groupLevelsEqual(stored, expected) {
  if (!Array.isArray(stored) || stored.length !== expected.length) return false;
  return expected.every((level, index) =>
    stored[index]?.fieldId === level.fieldId && stored[index]?.direction === level.direction);
}

function describeGroupLevels(stored) {
  return Array.isArray(stored)
    ? stored.map((level) => `${level?.fieldId}:${level?.direction}`).join(",")
    : JSON.stringify(stored);
}

async function toggleBand(page, bandKey) {
  const clicked = await page.evaluate(`(() => {
    const rows = [...document.querySelectorAll("#cp-activity-grid tbody tr")];
    const row = rows.find((item) => item.dataset.bandKey === ${JSON.stringify(bandKey)}
      || item.dataset.fieldGroupRow === ${JSON.stringify(bandKey)});
    const toggle = row?.querySelector("[data-band-toggle], [data-wbs-toggle]");
    if (!toggle) return false;
    toggle.click();
    return true;
  })()`);
  assert(clicked, `band ${bandKey} has no collapse toggle`);
  await sleep(450);
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
      groupRows: dialog.querySelectorAll(".cp-group-row").length,
      groupFields: [...dialog.querySelectorAll('select[name^="group.field."]')].map((select) => ({
        name: select.name,
        value: select.value,
        options: [...select.options].map((option) => option.value),
        labels: [...select.options].map((option) => option.textContent.trim()),
      })),
      groupDirections: [...dialog.querySelectorAll('select[name^="group.direction."]')].map((select) => select.value),
      groupWidths: [...dialog.querySelectorAll('select[name^="group.field."]')].map((select) => Math.round(select.getBoundingClientRect().width)),
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
      if (row.dataset.fieldGroupRow !== undefined) {
        const countText = row.querySelector(".cp-p6-group-count")?.textContent ?? "";
        return {
          kind: "fieldBand",
          bandKey: row.dataset.fieldGroupRow,
          field: row.dataset.groupField,
          valueKey: row.dataset.groupValue,
          level: Number(row.dataset.groupLevel),
          depth: Number(row.dataset.bandDepth),
          collapsed: row.dataset.bandCollapsed === "true",
          label: row.querySelector(".cp-p6-group-label")?.textContent?.trim() ?? "",
          count: Number(countText.replace(/[^0-9]/g, "")),
        };
      }
      if (!row.dataset.activityId) {
        return {
          kind: "wbsBand",
          bandKey: row.dataset.bandKey ?? "",
          wbsId: row.dataset.wbsRow ?? "",
          depth: Number(row.dataset.wbsDepth),
          collapsed: row.dataset.wbsCollapsed === "true",
          label: row.querySelector(".cp-p6-wbs-code")?.textContent?.trim() ?? row.textContent.trim(),
        };
      }
      const cells = {};
      [...row.querySelectorAll("td")].forEach((cell, index) => {
        if (headers[index]) cells[headers[index]] = cell.textContent.trim();
      });
      return { kind: "activity", id: row.dataset.activityId, cells };
    });
    const gantt = [...document.querySelectorAll("#cp-gantt [data-gantt-activity-id]")].map((row) => row.dataset.ganttActivityId);
    const fieldBands = sequence.filter((row) => row.kind === "fieldBand");
    return {
      sequence,
      ids: sequence.filter((row) => row.kind === "activity").map((row) => row.id),
      bands: sequence.filter((row) => row.kind !== "activity").length,
      wbsBands: sequence.filter((row) => row.kind === "wbsBand"),
      fieldBands,
      ganttIds: gantt,
      ganttFieldBands: [...document.querySelectorAll("#cp-gantt [data-gantt-field-group]")].map((row) => ({
        bandKey: row.dataset.ganttFieldGroup,
        field: row.dataset.groupField,
      })),
      toolbarGroup: document.querySelector("[data-activity-group]")?.value ?? null,
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

/** Depth-first WBS order exactly as the renderer walks the persisted tree. */
function wbsDfsOrder(facts) {
  const children = new Map();
  for (const node of facts.wbsNodes) {
    const parentId = node.parentKind === "project" ? null : node.parentWbsId;
    const siblings = children.get(parentId) ?? [];
    siblings.push(node);
    children.set(parentId, siblings);
  }
  for (const siblings of children.values()) {
    siblings.sort((left, right) =>
      left.sequenceNumber - right.sequenceNumber
      || collator.compare(left.localCode, right.localCode)
      || collator.compare(left.id, right.id));
  }
  const ordered = [];
  const visited = new Set();
  const visit = (parentId, depth) => {
    for (const node of children.get(parentId) ?? []) {
      if (visited.has(node.id)) continue;
      visited.add(node.id);
      ordered.push({ id: node.id, depth });
      visit(node.id, depth + 1);
    }
  };
  visit(null, 0);
  for (const node of facts.wbsNodes) {
    if (visited.has(node.id)) continue;
    visited.add(node.id);
    ordered.push({ id: node.id, depth: 0 });
    visit(node.id, 1);
  }
  return ordered;
}

/** Activities whose own WBS node is exactly ``wbsId`` (not a descendant). */
function directMembers(facts, wbsId) {
  return facts.activities.filter((activity) => activity.wbsId === wbsId);
}

/** Activity rows directly inside one band, up to the next shallower band. */
function bandMembers(sequence, band) {
  const index = sequence.findIndex((row) => row.bandKey === band.bandKey);
  assert(index !== -1, `band ${band.bandKey} is missing from the table`);
  const members = [];
  for (let next = index + 1; next < sequence.length; next += 1) {
    const candidate = sequence[next];
    if (candidate.kind !== "activity" && candidate.depth <= band.depth) break;
    if (candidate.kind === "activity") members.push(candidate.id);
  }
  return members;
}

function sortCell(activity, columnId) {
  if (columnId === "activity_id") return activity.id;
  if (columnId === "activity_code") return activity.code;
  if (columnId === "activity_name") return activity.name;
  if (columnId === "wbs") return activity.wbsId;
  return activity.cells?.[columnId] ?? null;
}

/** Applies a multi-level sort plan the way the runtime does, including the id tie-break. */
function expectedByLevels(facts, ids, levels) {
  const byId = new Map(facts.activities.map((activity) => [activity.id, activity]));
  return [...ids]
    .sort((leftId, rightId) => {
      const left = byId.get(leftId);
      const right = byId.get(rightId);
      for (const level of levels) {
        const a = sortCell(left, level.columnId);
        const b = sortCell(right, level.columnId);
        const aMissing = a === null || a === undefined || a === "";
        const bMissing = b === null || b === undefined || b === "";
        if (aMissing || bMissing) {
          if (aMissing && bMissing) continue;
          return aMissing ? 1 : -1;
        }
        const direction = level.direction === "desc" ? -1 : 1;
        const comparison = typeof a === "number" && typeof b === "number"
          ? (a === b ? 0 : a < b ? -1 : 1)
          : collator.compare(String(a), String(b));
        if (comparison !== 0) return direction * comparison;
      }
      return collator.compare(leftId, rightId);
    });
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
    contract: "cubi-activity-group-sort-v26.v2",
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
      assert(baseline.toolbarGroup === "wbs", `default toolbar group is ${baseline.toolbarGroup}`);
      await openGroupSort(page);
      const dialog = await dialogState(page);
      assert(dialog.groupRows === 3, `expected three group rows, got ${dialog.groupRows}`);
      assert(dialog.groupFields.length === 3, `expected three group field selects, got ${dialog.groupFields.length}`);
      assert(dialog.groupFields[0].value === "wbs", `default group field is ${dialog.groupFields[0].value}`);
      assert(
        dialog.groupFields[0].options.join(",") === ",wbs,activity_status,activity_type,is_critical,activity_code,total_float",
        `group fields are ${dialog.groupFields[0].options.join(",")}`,
      );
      assert(dialog.groupFields[0].labels[0] === "No grouping", `first group option is ${dialog.groupFields[0].labels[0]}`);
      assert(dialog.groupDirections.length === 3, `expected three group directions, got ${dialog.groupDirections.length}`);
      assert(dialog.sortRows === 3, `expected three sort rows, got ${dialog.sortRows}`);
      assert(dialog.fields[0].options.includes("activity.early_start"), "Start is not offered as a sort field");
      assert(dialog.fields[0].options.includes("activity.name"), "Activity name is not offered as a sort field");
      assert(dialog.notes.some((note) => /three levels/i.test(note)), `group note is missing: ${dialog.notes.join(" | ")}`);
      assert(dialog.notes.some((note) => /three fields/i.test(note)), `sort note is missing: ${dialog.notes.join(" | ")}`);
      await setSelect(page, "group.field.0", "");
      await setSelect(page, "sort.field.0", "activity.early_start");
      await setSelect(page, "sort.direction.0", "desc");
      await setSelect(page, "sort.field.1", "activity.name");
      await setSelect(page, "sort.direction.1", "asc");
      await submitOk(page);
      const sorted = await tableState(page);
      assert(sorted.bands === 0, `No grouping should remove bands, found ${sorted.bands}`);
      assert(sorted.toolbarGroup === "none", `toolbar group is ${sorted.toolbarGroup}`);
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
      assert(Array.isArray(metadata?.groupLevels) && metadata.groupLevels.length === 0, `stored group levels ${JSON.stringify(metadata?.groupLevels)}`);
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
      await setSelect(page, "group.field.0", "wbs");
      await setSelect(page, "group.direction.0", "asc");
      await setSelect(page, "sort.field.0", "activity.name");
      await setSelect(page, "sort.direction.0", "asc");
      await setSelect(page, "sort.field.1", "");
      await submitOk(page);
      const grouped = await tableState(page);
      assert(grouped.wbsBands.length > 0, "WBS grouping rendered no bands");
      assert(grouped.fieldBands.length === 0, "WBS grouping must not render field bands");
      expectedBands = grouped.wbsBands.length;
      const namesByBand = [];
      let current = null;
      for (const row of grouped.sequence) {
        if (row.kind !== "activity") {
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
      assert(grouped.toolbarGroup === "wbs", `toolbar group is ${grouped.toolbarGroup}`);
      const saved = await saveLayout(page);
      const metadata = saved.body?.metadata?.groupSort;
      assert(
        groupLevelsEqual(metadata?.groupLevels, [{ fieldId: "wbs", direction: "asc" }]),
        `stored group levels ${describeGroupLevels(metadata?.groupLevels)}`,
      );
      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "reload after WBS save");
      await sleep(1200);
      const reloaded = await tableState(page);
      assert(reloaded.wbsBands.length === expectedBands, `reload shows ${reloaded.wbsBands.length} bands, expected ${expectedBands}`);
      assert(reloaded.ids.length === 14, `reload shows ${reloaded.ids.length} activity rows`);
      await capture(page, "03-wbs-group-name-asc-after-reload-en-1366");
      return { bands: grouped.wbsBands.length, rows: grouped.ids.length };
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
      await setSelect(page, "group.field.0", "");
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

    await scenario("06", "Activity Status forms ordered bands that collapse independently and persist", async () => {
      await setViewport(page, 1366, 768);
      await setLanguage(page, "en");
      const facts = await readWorkspace(page);
      assert(facts.activities.length === 14, `workspace read returned ${facts.activities.length} activities`);
      const expected = expectedFieldBands(facts.activities, "activity_status", "asc");
      assert(expected.length >= 2, `the fixture must carry at least two statuses, got ${expected.map((band) => band.label).join(",")}`);
      await openGroupSort(page);
      await setSelect(page, "group.field.0", "activity_status");
      await setSelect(page, "group.direction.0", "asc");
      await setSelect(page, "group.field.1", "");
      await setSelect(page, "sort.field.0", "activity.name");
      await setSelect(page, "sort.direction.0", "asc");
      await setSelect(page, "sort.field.1", "");
      await submitOk(page);
      const grouped = await tableState(page);
      assert(grouped.wbsBands.length === 0, `field grouping rendered ${grouped.wbsBands.length} WBS bands`);
      const bands = renderedFieldBands(grouped, "activity_status");
      assert(bands.length === expected.length, `rendered ${bands.length} status bands, expected ${expected.length}`);
      assert(
        bands.map((band) => band.label).join("|") === expected.map((band) => band.label).join("|"),
        `status band order is ${bands.map((band) => band.label).join("|")} vs ${expected.map((band) => band.label).join("|")}`,
      );
      assert(
        bands.map((band) => band.count).join(",") === expected.map((band) => band.count).join(","),
        `status band counts are ${bands.map((band) => band.count).join(",")} vs ${expected.map((band) => band.count).join(",")}`,
      );
      assert(bands.every((band) => band.depth === 0 && band.level === 0), "status bands are not at the outer level");
      assert(bands.reduce((total, band) => total + band.count, 0) === 14, "status band counts do not cover every activity");
      assert(grouped.ids.length === 14, `grouped table shows ${grouped.ids.length} activities`);
      assert(grouped.toolbarGroup === "activity_status", `toolbar group is ${grouped.toolbarGroup}`);
      assert(grouped.ganttIds.join(",") === grouped.ids.join(","), "Gantt order differs from the status-banded table");
      assert(
        grouped.ganttFieldBands.map((band) => band.bandKey).join("|") === bands.map((band) => band.bandKey).join("|"),
        "Gantt status bands differ from the table bands",
      );
      const namesByBand = [];
      let current = null;
      for (const row of grouped.sequence) {
        if (row.kind === "fieldBand") {
          current = [];
          namesByBand.push(current);
        } else if (row.kind === "activity" && current) {
          current.push(row.cells["activity.name"] ?? "");
        }
      }
      for (const names of namesByBand) {
        const sortedNames = [...names].sort(collator.compare);
        assert(names.join("|") === sortedNames.join("|"), `inside a status band names are not ascending: ${names.join(" | ")}`);
      }
      const target = bands[1];
      await toggleBand(page, target.bandKey);
      const collapsed = await tableState(page);
      assert(collapsed.ids.length === 14 - target.count, `collapsing one band left ${collapsed.ids.length} activities`);
      assert(collapsed.fieldBands.some((band) => band.bandKey === target.bandKey && band.collapsed), "the collapsed band is not marked collapsed");
      assert(collapsed.fieldBands.length === bands.length, "collapsing one band removed another band");
      assert(collapsed.ganttIds.length === collapsed.ids.length, "Gantt did not follow the collapsed table");
      await toggleBand(page, target.bandKey);
      const expanded = await tableState(page);
      assert(expanded.ids.length === 14, `expanding left ${expanded.ids.length} activities`);
      assert(!expanded.fieldBands.find((band) => band.bandKey === target.bandKey)?.collapsed, "the band did not expand");
      const saved = await saveLayout(page);
      const metadata = saved.body?.metadata?.groupSort;
      assert(
        groupLevelsEqual(metadata?.groupLevels, [{ fieldId: "activity_status", direction: "asc" }]),
        `stored group levels ${describeGroupLevels(metadata?.groupLevels)}`,
      );
      assert(metadata?.groupBy === "none", `stored group mode is ${metadata?.groupBy}`);
      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "reload after status-band save");
      await sleep(1300);
      const reloaded = await tableState(page);
      const reloadedBands = renderedFieldBands(reloaded, "activity_status");
      assert(
        reloadedBands.map((band) => `${band.label}:${band.count}`).join("|") === expected.map((band) => `${band.label}:${band.count}`).join("|"),
        `reload restored ${reloadedBands.map((band) => `${band.label}:${band.count}`).join("|")}`,
      );
      assert(reloaded.ids.length === 14, `reload shows ${reloaded.ids.length} activities`);
      assert(reloaded.toolbarGroup === "activity_status", `reload toolbar group is ${reloaded.toolbarGroup}`);
      await capture(page, "06-activity-status-bands-after-reload-en-1366");
      return { bands: bands.length, counts: bands.map((band) => band.count), rows: reloaded.ids.length };
    });

    await scenario("07", "WBS and Activity Status nest two levels with independent collapse", async () => {
      await setLanguage(page, "en");
      const facts = await readWorkspace(page);
      await openGroupSort(page);
      await setSelect(page, "group.field.0", "wbs");
      await setSelect(page, "group.direction.0", "asc");
      await setSelect(page, "group.field.1", "activity_status");
      await setSelect(page, "group.direction.1", "asc");
      await setSelect(page, "group.field.2", "");
      await setSelect(page, "sort.field.0", "activity.name");
      await setSelect(page, "sort.direction.0", "asc");
      await setSelect(page, "sort.field.1", "");
      await submitOk(page);
      const grouped = await tableState(page);
      assert(grouped.wbsBands.length > 0, "the WBS level rendered no bands");
      assert(grouped.fieldBands.length > 0, "the status level rendered no bands");
      assert(
        grouped.fieldBands.every((band) => band.bandKey.includes(">activity_status:") && band.level === 1),
        "a status band is not nested under a WBS band",
      );
      assert(
        grouped.fieldBands.reduce((total, band) => total + band.count, 0) === 14,
        "nested status bands do not cover every activity",
      );
      // Every WBS band owns the status bands of its direct activities only.
      for (let index = 0; index < grouped.sequence.length; index += 1) {
        const row = grouped.sequence[index];
        if (row.kind !== "wbsBand") continue;
        const direct = facts.activities.filter((activity) => activity.wbsId === row.wbsId);
        const expectedDirect = expectedFieldBands(direct, "activity_status", "asc");
        const actual = [];
        for (let next = index + 1; next < grouped.sequence.length; next += 1) {
          const candidate = grouped.sequence[next];
          // The node's direct status bands follow its whole subtree; a sibling
          // or shallower WBS band ends the node's block.
          if (candidate.kind === "wbsBand" && candidate.depth <= row.depth) break;
          if (candidate.kind === "fieldBand" && candidate.depth === row.depth + 1) actual.push(candidate);
        }
        assert(
          actual.map((band) => `${band.label}:${band.count}`).join("|") === expectedDirect.map((band) => `${band.label}:${band.count}`).join("|"),
          `WBS ${row.wbsId} status bands are ${actual.map((band) => `${band.label}:${band.count}`).join("|")} vs ${expectedDirect.map((band) => `${band.label}:${band.count}`).join("|")}`,
        );
      }
      assert(grouped.ids.length === 14, `nested table shows ${grouped.ids.length} activities`);
      assert(grouped.toolbarGroup === "wbs", `toolbar group is ${grouped.toolbarGroup}`);
      assert(grouped.ganttIds.join(",") === grouped.ids.join(","), "Gantt order differs from the nested table");
      assert(
        grouped.ganttFieldBands.map((band) => band.bandKey).join("|") === grouped.fieldBands.map((band) => band.bandKey).join("|"),
        "Gantt status bands differ from the nested table bands",
      );
      // A nested status band collapses without touching its WBS band.
      const deepest = [...grouped.fieldBands].sort((left, right) => right.depth - left.depth)[0];
      const parentKey = deepest.bandKey.split(">").slice(0, -1).join(">");
      await toggleBand(page, deepest.bandKey);
      const nestedCollapsed = await tableState(page);
      assert(nestedCollapsed.ids.length === 14 - deepest.count, `nested collapse left ${nestedCollapsed.ids.length} activities`);
      assert(
        nestedCollapsed.wbsBands.some((band) => band.bandKey === parentKey && !band.collapsed),
        "collapsing a nested status band also collapsed its WBS band",
      );
      assert(
        nestedCollapsed.fieldBands.filter((band) => band.bandKey.startsWith(`${parentKey}>`)).length
          === grouped.fieldBands.filter((band) => band.bandKey.startsWith(`${parentKey}>`)).length,
        "collapsing one nested status band removed a sibling",
      );
      await toggleBand(page, deepest.bandKey);
      // A WBS band hides its whole subtree, then restores it.
      const branch = grouped.wbsBands.find((band) => band.depth === 1 && grouped.fieldBands.some((field) => field.bandKey.startsWith(`${band.bandKey}>`)));
      assert(branch, "no child WBS band owns a status band");
      await toggleBand(page, branch.bandKey);
      const branchCollapsed = await tableState(page);
      assert(branchCollapsed.wbsBands.some((band) => band.bandKey === branch.bandKey && band.collapsed), "the WBS band did not collapse");
      assert(
        !branchCollapsed.fieldBands.some((band) => band.bandKey.startsWith(`${branch.bandKey}>`)),
        "the collapsed WBS band still shows its status bands",
      );
      await toggleBand(page, branch.bandKey);
      const restored = await tableState(page);
      assert(restored.ids.length === 14, `expanding the WBS band left ${restored.ids.length} activities`);
      const saved = await saveLayout(page);
      const metadata = saved.body?.metadata?.groupSort;
      assert(
        groupLevelsEqual(metadata?.groupLevels, [
          { fieldId: "wbs", direction: "asc" },
          { fieldId: "activity_status", direction: "asc" },
        ]),
        `stored group levels ${describeGroupLevels(metadata?.groupLevels)}`,
      );
      assert(metadata?.groupBy === "wbs", `stored group mode is ${metadata?.groupBy}`);
      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "reload after nested save");
      await sleep(1300);
      const reloaded = await tableState(page);
      assert(reloaded.wbsBands.length === grouped.wbsBands.length, `reload shows ${reloaded.wbsBands.length} WBS bands`);
      assert(reloaded.fieldBands.length === grouped.fieldBands.length, `reload shows ${reloaded.fieldBands.length} status bands`);
      assert(reloaded.ids.length === 14, `reload shows ${reloaded.ids.length} activities`);
      assert(reloaded.toolbarGroup === "wbs", `reload toolbar group is ${reloaded.toolbarGroup}`);
      await capture(page, "07-wbs-status-nested-after-reload-en-1366");
      return { wbsBands: grouped.wbsBands.length, statusBands: grouped.fieldBands.length, rows: reloaded.ids.length };
    });

    await scenario("08", "a field-first plan puts WBS bands inside the first field band", async () => {
      const facts = await readWorkspace(page);
      const expected = expectedFieldBands(facts.activities, "is_critical", "asc");
      assert(expected.length >= 2, `criticality produced ${expected.length} bands`);
      await openGroupSort(page);
      await setSelect(page, "group.field.0", "is_critical");
      await setSelect(page, "group.direction.0", "asc");
      await setSelect(page, "group.field.1", "wbs");
      await setSelect(page, "group.direction.1", "asc");
      await setSelect(page, "group.field.2", "");
      await setSelect(page, "sort.field.0", "activity.name");
      await setSelect(page, "sort.direction.0", "asc");
      await setSelect(page, "sort.field.1", "");
      await submitOk(page);
      const grouped = await tableState(page);
      const outer = grouped.fieldBands.filter((band) => band.field === "is_critical" && band.depth === 0);
      assert(outer.length === expected.length, `outer critical bands are ${outer.length}, expected ${expected.length}`);
      assert(
        outer.map((band) => `${band.label}:${band.count}`).join("|") === expected.map((band) => `${band.label}:${band.count}`).join("|"),
        `outer critical bands are ${outer.map((band) => `${band.label}:${band.count}`).join("|")}`,
      );
      assert(outer.every((band) => band.bandKey.startsWith("field:is_critical:")), "the outer bands are not criticality bands");
      assert(grouped.wbsBands.length > 0, "no WBS bands were nested inside the criticality bands");
      assert(grouped.wbsBands.every((band) => band.bandKey.includes(">wbs:")), "a WBS band is not nested under a field band");
      assert(grouped.ids.length === 14, `field-first table shows ${grouped.ids.length} activities`);
      assert(grouped.toolbarGroup === "is_critical", `toolbar group is ${grouped.toolbarGroup}`);
      assert(grouped.ganttIds.join(",") === grouped.ids.join(","), "Gantt order differs from the field-first table");
      const saved = await saveLayout(page);
      const metadata = saved.body?.metadata?.groupSort;
      assert(
        groupLevelsEqual(metadata?.groupLevels, [
          { fieldId: "is_critical", direction: "asc" },
          { fieldId: "wbs", direction: "asc" },
        ]),
        `stored group levels ${describeGroupLevels(metadata?.groupLevels)}`,
      );
      assert(metadata?.groupBy === "none", `stored group mode is ${metadata?.groupBy}`);
      await capture(page, "08-critical-then-wbs-en-1366");
      return { criticalBands: outer.map((band) => band.label), wbsBands: grouped.wbsBands.length, rows: grouped.ids.length };
    });

    await scenario("09", "a nested plan stays readable in a Persian RTL cell at 1280", async () => {
      await setViewport(page, 1280, 720);
      await setLanguage(page, "fa");
      await openGroupSort(page);
      const dialog = await dialogState(page);
      assert(dialog.groupFields[0].labels.includes("بدون گروه‌بندی"), `Persian group options are ${dialog.groupFields[0].labels.join("|")}`);
      assert(dialog.groupFields[0].labels.includes("وضعیت فعالیت"), `Persian group fields are ${dialog.groupFields[0].labels.join("|")}`);
      await setSelect(page, "group.field.0", "wbs");
      await setSelect(page, "group.field.1", "activity_status");
      await setSelect(page, "group.field.2", "");
      await setSelect(page, "sort.field.0", "activity.name");
      await setSelect(page, "sort.direction.0", "asc");
      await setSelect(page, "sort.field.1", "");
      await submitOk(page);
      const state = await tableState(page);
      assert(state.dir === "rtl", `document direction is ${state.dir}`);
      assert(state.ids.length === 14, `the RTL cell shows ${state.ids.length} activities`);
      assert(state.wbsBands.length > 0 && state.fieldBands.length > 0, "the nested plan did not render in the RTL cell");
      assert(state.overflow <= 1, `the RTL nested table overflows by ${state.overflow}px`);
      assert(state.ganttIds.join(",") === state.ids.join(","), "Gantt order differs in the RTL cell");
      await capture(page, "09-wbs-status-fa-rtl-1280");
      return { bands: state.wbsBands.length + state.fieldBands.length, rows: state.ids.length, overflow: state.overflow };
    });

    await scenario("10", "three group levels nest WBS, status and criticality and restore", async () => {
      await setViewport(page, 1440, 900);
      await setLanguage(page, "en");
      const facts = await readWorkspace(page);
      assert(facts.activities.length === 14, `workspace read returned ${facts.activities.length} activities`);
      await openGroupSort(page);
      await setSelect(page, "group.field.0", "wbs");
      await setSelect(page, "group.direction.0", "asc");
      await setSelect(page, "group.field.1", "activity_status");
      await setSelect(page, "group.direction.1", "desc");
      await setSelect(page, "group.field.2", "is_critical");
      await setSelect(page, "group.direction.2", "asc");
      await setSelect(page, "sort.field.0", "activity.name");
      await setSelect(page, "sort.direction.0", "asc");
      await setSelect(page, "sort.field.1", "");
      await setSelect(page, "sort.field.2", "");
      const dialog = await dialogState(page);
      assert(dialog.groupRows === 3 && dialog.sortRows === 3, "the dialog does not expose three group and three sort rows");
      assert(
        dialog.groupFields.map((field) => field.value).join(",") === "wbs,activity_status,is_critical",
        `dialog group fields are ${dialog.groupFields.map((field) => field.value).join(",")}`,
      );
      assert(dialog.groupDirections.join(",") === "asc,desc,asc", `dialog group directions are ${dialog.groupDirections.join(",")}`);
      assert(
        dialog.groupWidths.every((width) => width >= 110),
        `group field selects are clipped to ${dialog.groupWidths.join(",")}px`,
      );
      await capture(page, "10-dialog-three-levels-en-1440");
      await submitOk(page);
      const grouped = await tableState(page);
      const statusBands = grouped.fieldBands.filter((band) => band.level === 1 && band.field === "activity_status");
      const criticalBands = grouped.fieldBands.filter((band) => band.level === 2 && band.field === "is_critical");
      assert(statusBands.length > 0, "the second group level rendered no status bands");
      assert(criticalBands.length > 0, "the third group level rendered no criticality bands");
      assert(
        grouped.fieldBands.every((band) => (band.level === 1 && band.field === "activity_status") || (band.level === 2 && band.field === "is_critical")),
        "a band appears outside the three configured levels",
      );
      const wbsByKey = new Map(grouped.wbsBands.map((band) => [band.bandKey, band.wbsId]));
      const statusPrefix = ">activity_status:";
      for (const band of statusBands) {
        const splitAt = band.bandKey.lastIndexOf(statusPrefix);
        assert(splitAt > 0, `status band key ${band.bandKey} has no WBS parent`);
        const parentKey = band.bandKey.slice(0, splitAt);
        const wbsId = wbsByKey.get(parentKey);
        assert(wbsId, `status band ${band.bandKey} has no rendered WBS parent ${parentKey}`);
        const subset = directMembers(facts, wbsId)
          .filter((activity) => groupKeyOf(readGroupValue(activity, "activity_status")) === band.valueKey);
        assert(subset.length === band.count, `status band ${band.valueKey} shows ${band.count} rows, expected ${subset.length}`);
        const expectedCritical = expectedFieldBands(subset, "is_critical", "asc");
        const actualCritical = criticalBands.filter((child) => child.bandKey.startsWith(`${band.bandKey}>is_critical:`));
        assert(
          actualCritical.map((child) => `${child.label}:${child.count}`).join("|")
            === expectedCritical.map((child) => `${child.label}:${child.count}`).join("|"),
          `criticality bands under ${band.valueKey} are ${actualCritical.map((child) => `${child.label}:${child.count}`).join("|")}`,
        );
        assert(
          actualCritical.reduce((total, child) => total + child.count, 0) === subset.length,
          `criticality bands under ${band.valueKey} do not cover its ${subset.length} activities`,
        );
      }
      assert(
        criticalBands.reduce((total, band) => total + band.count, 0) === 14,
        "the innermost criticality bands do not cover every activity",
      );
      assert(grouped.ids.length === 14, `the three-level table shows ${grouped.ids.length} activities`);
      assert(grouped.toolbarGroup === "wbs", `toolbar group is ${grouped.toolbarGroup}`);
      assert(grouped.ganttIds.join(",") === grouped.ids.join(","), "the Gantt order differs from the three-level table");
      const saved = await saveLayout(page);
      const metadata = saved.body?.metadata?.groupSort;
      assert(
        groupLevelsEqual(metadata?.groupLevels, [
          { fieldId: "wbs", direction: "asc" },
          { fieldId: "activity_status", direction: "desc" },
          { fieldId: "is_critical", direction: "asc" },
        ]),
        `stored group levels ${describeGroupLevels(metadata?.groupLevels)}`,
      );
      assert(metadata?.groupBy === "wbs", `stored group mode is ${metadata?.groupBy}`);
      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "reload after three-level save");
      await sleep(1300);
      const reloaded = await tableState(page);
      assert(
        reloaded.fieldBands.filter((band) => band.level === 1).length === statusBands.length,
        `reload shows ${reloaded.fieldBands.filter((band) => band.level === 1).length} status bands, expected ${statusBands.length}`,
      );
      assert(
        reloaded.fieldBands.filter((band) => band.level === 2).length === criticalBands.length,
        `reload shows ${reloaded.fieldBands.filter((band) => band.level === 2).length} criticality bands, expected ${criticalBands.length}`,
      );
      assert(reloaded.ids.length === 14, `reload shows ${reloaded.ids.length} activities`);
      assert(reloaded.toolbarGroup === "wbs", `reload toolbar group is ${reloaded.toolbarGroup}`);
      await capture(page, "10b-three-level-after-reload-en-1440");
      return {
        statusBands: statusBands.length,
        criticalBands: criticalBands.length,
        rows: reloaded.ids.length,
      };
    });

    await scenario("11", "three sort levels order every band without re-grouping it", async () => {
      await setViewport(page, 1280, 800);
      await setLanguage(page, "en");
      const facts = await readWorkspace(page);
      const levels = [
        { columnId: "activity.total_float", direction: "asc" },
        { columnId: "activity.name", direction: "desc" },
        { columnId: "activity.early_finish", direction: "asc" },
      ];
      await openGroupSort(page);
      await setSelect(page, "group.field.0", "wbs");
      await setSelect(page, "group.direction.0", "asc");
      await setSelect(page, "group.field.1", "activity_status");
      await setSelect(page, "group.direction.1", "asc");
      await setSelect(page, "group.field.2", "");
      await setSelect(page, "sort.field.0", levels[0].columnId);
      await setSelect(page, "sort.direction.0", levels[0].direction);
      await setSelect(page, "sort.field.1", levels[1].columnId);
      await setSelect(page, "sort.direction.1", levels[1].direction);
      await setSelect(page, "sort.field.2", levels[2].columnId);
      await setSelect(page, "sort.direction.2", levels[2].direction);
      await submitOk(page);
      const grouped = await tableState(page);
      const statusBands = grouped.fieldBands.filter((band) => band.level === 1 && band.field === "activity_status");
      assert(statusBands.length > 0, "the status level rendered no bands");
      let checkedBands = 0;
      for (const band of statusBands) {
        const ids = bandMembers(grouped.sequence, band);
        const expected = expectedByLevels(facts, ids, levels);
        assert(
          ids.join(",") === expected.join(","),
          `band ${band.bandKey} order is ${ids.join(",")} vs ${expected.join(",")}`,
        );
        if (ids.length >= 2) checkedBands += 1;
      }
      assert(checkedBands > 0, "no multi-activity band exercised the per-level sort");
      assert(grouped.ids.length === 14, `the sorted table shows ${grouped.ids.length} activities`);
      assert(grouped.ganttIds.join(",") === grouped.ids.join(","), "the Gantt order differs from the per-level sort");
      const saved = await saveLayout(page);
      const metadata = saved.body?.metadata?.groupSort;
      assert(metadata?.sortLevels?.length === 3, `stored sort levels ${JSON.stringify(metadata?.sortLevels)}`);
      assert(
        metadata.sortLevels.map((level) => `${level.columnId}:${level.direction}`).join(",")
          === levels.map((level) => `${level.columnId}:${level.direction}`).join(","),
        `stored sort plan ${JSON.stringify(metadata.sortLevels)}`,
      );
      await capture(page, "11-three-level-sort-en-1280");
      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "reload after three-level sort save");
      await sleep(1300);
      const reloaded = await tableState(page);
      assert(reloaded.ids.join(",") === grouped.ids.join(","), `reload changed the per-level sort: ${reloaded.ids.join(",")}`);
      assert(reloaded.fieldBands.length === grouped.fieldBands.length, "reload changed the band count");
      return { bands: statusBands.length, checkedBands, rows: reloaded.ids.length };
    });

    await scenario("12", "WBS bands follow the persisted hierarchy across a refresh", async () => {
      await setViewport(page, 1920, 1080);
      await setLanguage(page, "en");
      const facts = await readWorkspace(page);
      await openGroupSort(page);
      await setSelect(page, "group.field.0", "wbs");
      await setSelect(page, "group.direction.0", "asc");
      await setSelect(page, "group.field.1", "");
      await setSelect(page, "group.field.2", "");
      await setSelect(page, "sort.field.0", "activity.name");
      await setSelect(page, "sort.direction.0", "asc");
      await setSelect(page, "sort.field.1", "");
      await setSelect(page, "sort.field.2", "");
      await submitOk(page);
      const grouped = await tableState(page);
      const dfs = wbsDfsOrder(facts);
      const parentById = new Map(facts.wbsNodes.map((node) => [
        node.id,
        node.parentKind === "project" ? null : node.parentWbsId,
      ]));
      const withActivities = new Set();
      for (const activity of facts.activities) {
        let nodeId = activity.wbsId;
        const guard = new Set();
        while (nodeId && !guard.has(nodeId)) {
          guard.add(nodeId);
          withActivities.add(nodeId);
          nodeId = parentById.get(nodeId) ?? null;
        }
      }
      const expectedBandIds = dfs.filter((node) => withActivities.has(node.id)).map((node) => node.id);
      assert(grouped.wbsBands.length > 0, "WBS grouping rendered no bands");
      assert(
        grouped.wbsBands.map((band) => band.wbsId).join(",") === expectedBandIds.join(","),
        `WBS order is ${grouped.wbsBands.map((band) => band.wbsId).join(",")} vs hierarchy ${expectedBandIds.join(",")}`,
      );
      assert(
        grouped.wbsBands.map((band) => band.depth).join(",") === dfs.filter((node) => withActivities.has(node.id)).map((node) => node.depth).join(","),
        "WBS band depths do not match the persisted hierarchy",
      );
      assert(grouped.ids.length === 14, `the WBS table shows ${grouped.ids.length} activities`);
      assert(grouped.ganttIds.join(",") === grouped.ids.join(","), "the Gantt order differs from the WBS hierarchy");
      const saved = await saveLayout(page);
      assert(saved.body?.metadata?.groupSort?.groupBy === "wbs", "the WBS plan was not stored");
      await capture(page, "12-wbs-order-en-1920");
      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "reload after WBS order save");
      await sleep(1300);
      const reloaded = await tableState(page);
      assert(
        reloaded.wbsBands.map((band) => band.wbsId).join(",") === expectedBandIds.join(","),
        `refresh changed the WBS order: ${reloaded.wbsBands.map((band) => band.wbsId).join(",")}`,
      );
      assert(reloaded.ids.length === 14, `refresh shows ${reloaded.ids.length} activities`);
      await capture(page, "12b-wbs-order-after-refresh-en-1920");
      return { bands: grouped.wbsBands.length, topLevel: grouped.wbsBands.filter((band) => band.depth === 0).length };
    });

    await scenario("13", "a three-level plan stays readable in a Persian RTL cell at 1440", async () => {
      await setViewport(page, 1440, 900);
      await setLanguage(page, "fa");
      await openGroupSort(page);
      const dialog = await dialogState(page);
      assert(dialog.groupRows === 3 && dialog.sortRows === 3, "the Persian dialog lost a group or sort row");
      assert(dialog.groupFields[1].labels.includes("وضعیت فعالیت"), `Persian status option is missing: ${dialog.groupFields[1].labels.join("|")}`);
      assert(dialog.groupFields[2].labels.includes("بحرانی"), `Persian critical option is missing: ${dialog.groupFields[2].labels.join("|")}`);
      assert(dialog.groupWidths.every((width) => width >= 110), `Persian group selects are clipped to ${dialog.groupWidths.join(",")}px`);
      await setSelect(page, "group.field.0", "wbs");
      await setSelect(page, "group.direction.0", "asc");
      await setSelect(page, "group.field.1", "activity_status");
      await setSelect(page, "group.direction.1", "desc");
      await setSelect(page, "group.field.2", "is_critical");
      await setSelect(page, "group.direction.2", "asc");
      await setSelect(page, "sort.field.0", "activity.name");
      await setSelect(page, "sort.direction.0", "asc");
      await setSelect(page, "sort.field.1", "");
      await setSelect(page, "sort.field.2", "");
      await capture(page, "13-dialog-three-level-fa-1440");
      await submitOk(page);
      const state = await tableState(page);
      assert(state.dir === "rtl", `document direction is ${state.dir}`);
      assert(state.overflow <= 1, `the RTL three-level table overflows by ${state.overflow}px`);
      assert(
        state.fieldBands.some((band) => band.level === 1) && state.fieldBands.some((band) => band.level === 2),
        "the Persian cell lost a nested group level",
      );
      assert(state.ids.length === 14, `the RTL cell shows ${state.ids.length} activities`);
      assert(state.ganttIds.join(",") === state.ids.join(","), "the Gantt order differs in the RTL cell");
      await capture(page, "13-three-level-fa-rtl-1440");
      return { bands: state.fieldBands.length, rows: state.ids.length, overflow: state.overflow };
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
