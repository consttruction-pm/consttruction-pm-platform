#!/usr/bin/env node
/**
 * Browser E2E for the persisted activity-layout Undo/Redo history.
 *
 * The suite drives the real Preview runtime and the real layout service:
 * every width change saves a new immutable revision, Undo/Redo write a new
 * revision based on an older snapshot instead of deleting history, and the
 * server revision list is the fallback after a page reload. It also proves
 * that undo restores the Group and Sort plan stored in the layout metadata,
 * including a revision that predates group/sort persistence (canonical
 * default), and that the history bar is readable in fa/RTL.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4224 node e2e/layout-undo-redo-v26.mjs
 *   (use a brand-new --database file; saved layouts survive --reset)
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4224";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-26";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "layout-undo-redo-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `layout-undo-redo-v26-${evidenceDate}`);
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
  const file = `layout-undo-redo-v26/${name}.png`;
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
  await sleep(1000);
}

async function openSettings(page) {
  const already = await page.evaluate(`Boolean(document.querySelector("[data-settings-layout]"))`);
  if (already) return;  const opened = await page.evaluate(`(() => {
    const trigger = document.querySelector('[data-desktop-menu="administration"]');
    if (!trigger) return false;
    trigger.click();
    return true;
  })()`);
  assert(opened, "Administration menu trigger is missing");
  await page.waitFor(`(() => {
    const popup = document.querySelector('[data-desktop-popup="administration"]');
    return Boolean(popup && !popup.hidden);
  })()`, "Administration menu open");
  await sleep(250);
  const clicked = await page.evaluate(`(() => {
    const button = document.querySelector('[data-desktop-window="settings"]');
    if (!button || button.disabled) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, "Settings window command is missing");
  await page.waitForSelector("[data-settings-layout]", "settings layout section", 10000);
  await sleep(700);
}

/** Brings a workspace window tab to the front so its toolbar commands render. */
async function activateWindow(page, key) {
  const clicked = await page.evaluate(`(() => {
    const tab = document.querySelector('[data-window-tab="${key}"]');
    if (!tab) return false;
    tab.click();
    return true;
  })()`);
  assert(clicked, `window tab ${key} is missing`);
  await sleep(900);
}

/** The flattened project layout as the server returns it. */
function readLayout(page) {
  return page.evaluate(`(async () => {
    const response = await fetch("/api/projects/preview-rps-01/p6/layouts/project/activity");
    let body = null;
    try { body = await response.json(); } catch (error) { body = null; }
    return { status: response.status, body };
  })()`, { awaitPromise: true });
}

async function layoutFact(page) {
  const layout = await readLayout(page);
  assert(layout.status === 200 && layout.body, `layout read status ${layout.status}`);
  const width = layout.body.columns?.find((column) => column.field_id === "activity.id")?.width ?? null;
  const groupSort = layout.body.metadata?.groupSort ?? null;
  return { revision: layout.body.revision, width, groupSort };
}

async function waitForRevision(page, previous, label) {
  for (let attempt = 0; attempt < 50; attempt += 1) {
    await sleep(200);
    const fact = await layoutFact(page);
    if (fact.revision > previous) return fact;
  }
  throw new Error(`WAIT_REVISION_TIMEOUT: ${label} (still at R${previous})`);
}

const historyBar = `(() => {
  const section = document.querySelector("[data-settings-layout]");
  const undo = section?.querySelector("[data-p6-layout-undo]") ?? null;
  const redo = section?.querySelector("[data-p6-layout-redo]") ?? null;
  const select = section?.querySelector("[data-p6-layout-revision-select]") ?? null;
  const restore = section?.querySelector("[data-p6-layout-restore]") ?? null;
  const notice = section?.querySelector(".cp-p6-history-notice") ?? null;
  const bar = section?.querySelector(".cp-p6-history-bar") ?? null;
  const rect = bar?.getBoundingClientRect() ?? null;
  return {
    present: Boolean(section),
    undoLabel: undo?.textContent?.trim() ?? null,
    redoLabel: redo?.textContent?.trim() ?? null,
    undoDisabled: undo ? undo.disabled : null,
    redoDisabled: redo ? redo.disabled : null,
    selectDisabled: select ? select.disabled : null,
    restoreDisabled: restore ? restore.disabled : null,
    optionValues: select ? [...select.options].map((option) => option.value).filter(Boolean) : [],
    notice: notice?.textContent?.trim() ?? null,
    heading: section?.querySelector(".cp-p6-field-chooser-heading span")?.textContent?.trim() ?? null,
    barWithinViewport: rect ? rect.left >= -1 && rect.right <= window.innerWidth + 1 : null,
    barOverflow: bar ? bar.scrollWidth - bar.clientWidth : null,
    direction: getComputedStyle(document.querySelector(".cp-workspace") ?? document.body).direction,
    locale: document.documentElement.lang || null,
    horizontalOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  };
})()`;

async function barState(page) {
  return page.evaluate(historyBar);
}

async function clickHistory(page, which) {
  const attribute = which === "undo" ? "data-p6-layout-undo" : "data-p6-layout-redo";
  const clicked = await page.evaluate(`(() => {
    const button = document.querySelector("[data-settings-layout] [${attribute}]");
    if (!button || button.disabled) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `history ${which} button is missing or disabled`);
  await sleep(1600);
}

async function resizeIdColumn(page) {
  const clicked = await page.evaluate(`(() => {
    const button = document.querySelector('[data-p6-field-width="activity.id"][data-p6-field-width-delta="increase"]');
    if (!button || button.disabled) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, "activity.id widen button is missing");
}

const gridState = `(() => {
  const grid = document.querySelector("#cp-activity-grid");
  const header = grid?.querySelector('thead th[data-column-id="activity.id"]');
  return {
    idWidth: header ? Number.parseFloat(header.style.width || "0") : null,
    wbsRows: grid ? grid.querySelectorAll("tbody tr[data-wbs-row]").length : 0,
    fieldBands: grid ? [...grid.querySelectorAll("tbody tr[data-field-group-row]")]
      .map((row) => ({ field: row.dataset.groupField, key: row.dataset.fieldGroupRow, level: row.dataset.groupLevel })) : [],
    activityRows: grid ? grid.querySelectorAll("tbody tr[data-activity-id]").length : 0,
  };
})()`;

async function gridFact(page) {
  return page.evaluate(gridState);
}

const dialogSelector = "dialog[data-desktop-dialog=group-sort]";

async function setStatusGrouping(page) {
  const opened = await page.evaluate(`(() => {
    const element = [...document.querySelectorAll('[data-desktop-command="dialog.group-sort"]')]
      .find((item) => item.getClientRects().length > 0 && !item.disabled);
    if (!element) return false;
    element.click();
    return true;
  })()`);
  assert(opened, "Group and Sort command is missing");
  await page.waitForSelector(`${dialogSelector}[open]`, "group and sort dialog", 8000);
  await sleep(250);
  const changed = await page.evaluate(`(() => {
    const dialog = document.querySelector("${dialogSelector}");
    const select = dialog.querySelector('select[name="group.field.0"]');
    if (!select) return false;
    select.value = "activity_status";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    return select.value === "activity_status";
  })()`);
  assert(changed, "group field 0 did not accept activity_status");
  await sleep(200);
  const submitted = await page.evaluate(`(() => {
    const button = document.querySelector("${dialogSelector} [data-dialog-ok]");
    if (!button || button.disabled) return false;
    button.click();
    return true;
  })()`);
  assert(submitted, "Group and Sort OK button is missing");
  await page.waitFor(`!document.querySelector("${dialogSelector}")?.open`, "group and sort dialog closed", 8000);
  await sleep(700);
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
}

async function sendKey(page, key, code, virtualKeyCode) {
  await page.cdp.send("Input.dispatchKeyEvent", { type: "keyDown", modifiers: 2, key, code, windowsVirtualKeyCode: virtualKeyCode, nativeVirtualKeyCode: virtualKeyCode });
  await page.cdp.send("Input.dispatchKeyEvent", { type: "keyUp", modifiers: 2, key, code, windowsVirtualKeyCode: virtualKeyCode, nativeVirtualKeyCode: virtualKeyCode });
  await sleep(1600);
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
    contract: "cubi-layout-undo-redo-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
  };

  try {
    await setViewport(page, 1440, 900);
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
    const persona = await page.evaluate(`(() => {
      const button = document.querySelector('button[name="role"][value="admin"]');
      if (!button) return false;
      button.click();
      return true;
    })()`);
    assert(persona, "admin persona is missing");
    await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
    await page.click('[data-project-id="preview-rps-01"]');
    await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
    await sleep(1600);
    await openSettings(page);

    let baseline = await layoutFact(page);
    let grid = await gridFact(page);
    const baseWidth = baseline.width;
    const baseRevision = baseline.revision;

    await scenario("01", "a fresh layout exposes an honest empty undo history", async () => {
      const bar = await barState(page);
      assert(bar.present, "layout history bar is missing");
      assert(bar.undoDisabled === false, "undo should be available to query saved revisions");
      assert(bar.redoDisabled === true, "redo must start disabled");
      assert(bar.undoLabel?.startsWith("↶"), `undo label is ${bar.undoLabel}`);
      assert(bar.redoLabel?.startsWith("↷"), `redo label is ${bar.redoLabel}`);
      assert(bar.heading?.includes(`R${baseRevision}`), `heading does not show R${baseRevision}: ${bar.heading}`);
      await clickHistory(page, "undo");
      const after = await barState(page);
      const fact = await layoutFact(page);
      assert(fact.revision === baseRevision, `empty undo changed revision to ${fact.revision}`);
      assert(after.notice === "No earlier layout revision is available.", `empty undo notice is ${after.notice}`);
      await capture(page, "01-empty-history-en-1440");
      return { revision: fact.revision, width: fact.width, notice: after.notice };
    });

    let afterChange = null;

    await scenario("02", "a column resize saves one revision and undo restores the grid width", async () => {
      await resizeIdColumn(page);
      afterChange = await waitForRevision(page, baseRevision, "width resize");
      assert(afterChange.width === baseWidth + 20, `stored width ${afterChange.width} != ${baseWidth + 20}`);
      const resizedGrid = await gridFact(page);
      assert(resizedGrid.idWidth === baseWidth + 20, `rendered header width ${resizedGrid.idWidth}`);
      const bar = await barState(page);
      assert(bar.redoDisabled === true, "redo must stay disabled before an undo");
      assert(bar.optionValues.includes(String(baseRevision)), `history list lacks R${baseRevision}: ${bar.optionValues}`);
      await capture(page, "02-resized-before-undo-en-1440");

      await clickHistory(page, "undo");
      const undone = await waitForRevision(page, afterChange.revision, "undo resize");
      assert(undone.width === baseWidth, `undo left width ${undone.width}`);
      const undoneGrid = await gridFact(page);
      assert(undoneGrid.idWidth === baseWidth, `undo left rendered width ${undoneGrid.idWidth}`);
      const undoneBar = await barState(page);
      assert(undoneBar.notice === "Last layout change undone.", `undo notice is ${undoneBar.notice}`);
      assert(undoneBar.redoDisabled === false, "redo must be enabled after undo");
      await capture(page, "03-undone-en-1440");
      return { before: afterChange.width, after: undone.width, revision: undone.revision };
    });

    await scenario("03", "redo reapplies the change and a fresh edit clears the redo stack", async () => {
      await clickHistory(page, "redo");
      const redone = await waitForRevision(page, afterChange.revision + 1, "redo resize");
      assert(redone.width === baseWidth + 20, `redo width ${redone.width}`);
      const redoneBar = await barState(page);
      assert(redoneBar.notice === "Layout change reapplied.", `redo notice is ${redoneBar.notice}`);
      assert(redoneBar.redoDisabled === true, "redo must be empty after it was consumed");

      await resizeIdColumn(page);
      const edited = await waitForRevision(page, redone.revision, "new edit after undo");
      assert(edited.width === baseWidth + 40, `new edit width ${edited.width}`);
      const editedBar = await barState(page);
      assert(editedBar.redoDisabled === true, "a fresh edit must clear the redo stack");
      const editedGrid = await gridFact(page);
      assert(editedGrid.idWidth === baseWidth + 40, `rendered width after new edit ${editedGrid.idWidth}`);
      await capture(page, "04-redo-and-new-edit-en-1440");
      return { width: edited.width, revision: edited.revision };
    });

    await scenario("04", "Ctrl+Z and Ctrl+Y run the same layout history", async () => {
      const before = await layoutFact(page);
      await sendKey(page, "z", "KeyZ", 90);
      const undone = await waitForRevision(page, before.revision, "Ctrl+Z");
      assert(undone.width === baseWidth + 20, `Ctrl+Z width ${undone.width}`);
      let bar = await barState(page);
      assert(bar.notice === "Last layout change undone.", `Ctrl+Z notice is ${bar.notice}`);
      await sendKey(page, "y", "KeyY", 89);
      const redone = await waitForRevision(page, undone.revision, "Ctrl+Y");
      assert(redone.width === baseWidth + 40, `Ctrl+Y width ${redone.width}`);
      bar = await barState(page);
      assert(bar.notice === "Layout change reapplied.", `Ctrl+Y notice is ${bar.notice}`);
      assert(bar.redoDisabled === true, "redone state must leave redo empty");
      await capture(page, "05-keyboard-history-en-1440");
      return { afterUndo: undone.width, afterRedo: redone.width, revision: redone.revision };
    });

    await scenario("05", "undo after a reload uses the persisted revision history", async () => {
      const beforeReload = await layoutFact(page);
      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "workspace reload");
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows after reload");
      await sleep(1500);
      await openSettings(page);
      const reloadedBar = await barState(page);
      assert(reloadedBar.redoDisabled === true, "redo stack must not survive a page reload");
      assert(reloadedBar.undoDisabled === false, "undo must remain available after reload");
      assert(reloadedBar.notice === null, `reload kept a stale notice: ${reloadedBar.notice}`);
      await clickHistory(page, "undo");
      const undone = await waitForRevision(page, beforeReload.revision, "undo after reload");
      assert(undone.width === baseWidth + 20, `reload undo width ${undone.width}`);
      const bar = await barState(page);
      assert(bar.notice === "Last layout change undone.", `reload undo notice is ${bar.notice}`);
      assert(bar.redoDisabled === false, "undo after reload must open a redo entry");
      await capture(page, "06-reload-undo-en-1440");
      return { revision: undone.revision, width: undone.width };
    });

    await scenario("06", "restore a specific earlier revision from the history list", async () => {
      const before = await layoutFact(page);
      const bar = await barState(page);
      assert(bar.optionValues.length >= 2, `history list is too short: ${bar.optionValues}`);
      const oldest = Math.min(...bar.optionValues.map((value) => Number(value)));
      const selected = await page.evaluate(`(() => {
        const select = document.querySelector("[data-settings-layout] [data-p6-layout-revision-select]");
        const option = [...select.options].find((item) => item.value === ${JSON.stringify(String(oldest))});
        if (!option) return false;
        select.value = option.value;
        select.dispatchEvent(new Event("change", { bubbles: true }));
        return true;
      })()`);
      assert(selected, `revision R${oldest} is not offered`);
      const clicked = await page.evaluate(`(() => {
        const button = document.querySelector("[data-settings-layout] [data-p6-layout-restore]");
        if (!button || button.disabled) return false;
        button.click();
        return true;
      })()`);
      assert(clicked, "restore button is missing");
      const restored = await waitForRevision(page, before.revision, "restore revision");
      assert(restored.revision === before.revision + 1, `restore must append one revision, got R${restored.revision}`);
      assert(restored.width === baseWidth, `restored width ${restored.width} != R${oldest} width ${baseWidth}`);
      const after = await barState(page);
      assert(after.notice === "Layout revision restored.", `restore notice is ${after.notice}`);
      assert(after.redoDisabled === true, "restore must clear the redo stack");
      assert(after.optionValues.includes(String(before.revision)), "the replaced revision must stay recoverable");
      const gridAfter = await gridFact(page);
      assert(gridAfter.idWidth === baseWidth, `restored rendered width ${gridAfter.idWidth}`);
      await capture(page, "07-restore-oldest-en-1440");
      return { from: before.revision, restored: oldest, revision: restored.revision, width: restored.width };
    });

    await scenario("07", "undo restores the Group and Sort plan saved in the layout", async () => {
      const beforeGroup = await gridFact(page);
      assert(beforeGroup.fieldBands.length === 0, "baseline unexpectedly shows field bands");
      assert(beforeGroup.wbsRows > 0, "baseline WBS bands are missing");
      await activateWindow(page, "schedule");
      await setStatusGrouping(page);
      await saveLayout(page);
      let saved = null;
      for (let attempt = 0; attempt < 40; attempt += 1) {
        await sleep(200);
        const fact = await layoutFact(page);
        if (fact.groupSort) {
          saved = fact;
          break;
        }
      }
      assert(saved, "layout save did not persist a group/sort plan");
      assert(saved.groupSort.groupLevels?.[0]?.fieldId === "activity_status", `saved plan is ${JSON.stringify(saved.groupSort)}`);
      const grouped = await gridFact(page);
      assert(grouped.fieldBands.length === 3, `expected three status bands, got ${grouped.fieldBands.length}`);
      assert(grouped.fieldBands.every((band) => band.field === "activity_status"), "bands are not status bands");
      await capture(page, "08-group-plan-saved-en-1440");

      await openSettings(page);
      await clickHistory(page, "undo");
      const undone = await waitForRevision(page, saved.revision, "undo group plan");
      assert(!undone.groupSort, `undo kept a group/sort plan: ${JSON.stringify(undone.groupSort)}`);
      const ungrouped = await gridFact(page);
      assert(ungrouped.fieldBands.length === 0, `undo left ${ungrouped.fieldBands.length} field bands`);
      assert(ungrouped.wbsRows === beforeGroup.wbsRows, `undo changed WBS bands from ${beforeGroup.wbsRows} to ${ungrouped.wbsRows}`);
      assert(ungrouped.activityRows === grouped.activityRows, "undo changed the activity count");
      const bar = await barState(page);
      assert(bar.notice === "Last layout change undone.", `group undo notice is ${bar.notice}`);
      await capture(page, "09-group-plan-undone-en-1440");

      await clickHistory(page, "redo");
      const redone = await waitForRevision(page, undone.revision, "redo group plan");
      assert(redone.groupSort?.groupLevels?.[0]?.fieldId === "activity_status", "redo lost the status plan");
      const regrouped = await gridFact(page);
      assert(regrouped.fieldBands.length === 3, `redo left ${regrouped.fieldBands.length} status bands`);
      await capture(page, "10-group-plan-redone-en-1440");
      return {
        beforeWbs: beforeGroup.wbsRows,
        savedRevision: saved.revision,
        undoneRevision: undone.revision,
        redoneRevision: redone.revision,
      };
    });

    await scenario("08", "the history bar and notices are readable in a fa/RTL cell at 1280", async () => {
      await setViewport(page, 1280, 720);
      await setLanguage(page, "fa");
      await sleep(600);
      await openSettings(page);
      await clickHistory(page, "undo");
      const bar = await barState(page);
      assert(bar.direction === "rtl", `direction is ${bar.direction}`);
      assert(bar.locale === "fa", `locale is ${bar.locale}`);
      assert(bar.undoLabel === "↶ بازگردانی", `undo label is ${bar.undoLabel}`);
      assert(bar.redoLabel === "↷ تکرار", `redo label is ${bar.redoLabel}`);
      assert(bar.notice === "آخرین تغییر چیدمان بازگردانی شد.", `Persian notice is ${bar.notice}`);
      assert(bar.barWithinViewport === true, "history bar leaves the 1280 viewport");
      assert(bar.barOverflow === 0, `history bar overflows by ${bar.barOverflow}px`);
      assert(bar.horizontalOverflow <= 1, `page overflow is ${bar.horizontalOverflow}px`);
      await capture(page, "11-history-fa-rtl-1280");
      return { notice: bar.notice, direction: bar.direction, labels: [bar.undoLabel, bar.redoLabel] };
    });

    await scenario("09", "the history bar fits an en/LTR 1920×1080 cell", async () => {
      await setViewport(page, 1920, 1080);
      await setLanguage(page, "en");
      await sleep(600);
      await openSettings(page);
      const bar = await barState(page);
      assert(bar.direction === "ltr", `direction is ${bar.direction}`);
      assert(bar.undoLabel === "↶ Undo", `undo label is ${bar.undoLabel}`);
      assert(bar.barWithinViewport === true, "history bar leaves the 1920×1080 viewport");
      assert(bar.barOverflow === 0, `history bar overflows by ${bar.barOverflow}px`);
      assert(bar.horizontalOverflow <= 1, `page overflow is ${bar.horizontalOverflow}px`);
      await capture(page, "12-history-en-1920");
      return { revision: bar.heading, options: bar.optionValues.length };
    });

    assert(exceptions.length === 0, `uncaught page exceptions: ${JSON.stringify(exceptions.slice(0, 3))}`);
    assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors.slice(0, 3))}`);
    assert(apiFailures.length === 0, `API 5xx responses: ${JSON.stringify(apiFailures.slice(0, 3))}`);
  } finally {
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(outDir, "layout-undo-redo-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(evidenceDir, "layout-undo-redo-v26.json"), JSON.stringify(report, null, 2));
    page.cdp.close();
    chrome.cdp.close();
    await chrome.stop();
  }

  const failed = scenarios.filter((item) => item.status !== "pass");
  log(`\nScenarios: ${scenarios.length - failed.length} passed, ${failed.length} failed`);
  if (failed.length) process.exitCode = 1;
}

main().catch((error) => {
  log(`\nERROR: ${error && error.stack ? error.stack : error}`);
  process.exitCode = 1;
});
