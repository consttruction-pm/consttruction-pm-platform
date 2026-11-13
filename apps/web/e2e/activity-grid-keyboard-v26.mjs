#!/usr/bin/env node
/**
 * Browser E2E for the Activities grid keyboard contract.
 *
 * The grid is a `role="grid"` table with one roving Tab stop. This suite proves
 * against the real preview runtime that:
 *
 *   1. a click selects and focuses exactly one row and moves the tab stop;
 *   2. ArrowDown/ArrowUp walk the displayed row order (including WBS/field band
 *      rows) and keep the primary row, tab stop, aria-selected and the toolbar
 *      counter in agreement;
 *   3. Shift+Arrow extends the selection from the fixed anchor, Ctrl+Arrow
 *      moves focus without changing the selection, and Home/End/PageUp/PageDown
 *      jump to the computed row;
 *   4. collapsed branches remove their rows from the arrow sequence;
 *   5. Enter on a focused activity selects it and the details pane follows;
 *   6. Persian RTL keeps the vertical order (ArrowDown is still the next row);
 *   7. the keyboard work never mutates schedule input.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4198 \
 *   CUBI_TESTED_CODE_SHA=<code commit> node e2e/activity-grid-keyboard-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4198";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-13";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "activity-grid-keyboard-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `activity-grid-keyboard-v26-${evidenceDate}`);
rmSync(outDir, { recursive: true, force: true });
rmSync(evidenceDir, { recursive: true, force: true });
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT_ID = "preview-rps-01";

const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const scheduleMutations = [];
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
    return details;
  } catch (error) {
    record(id, name, "fail", { error: String(error && error.stack ? error.stack : error) });
    throw error;
  }
}

async function capture(page, name) {
  const file = `activity-grid-keyboard-v26/${name}.png`;
  await page.screenshot(file);
  copyFileSync(join(artifactsDir, file), join(evidenceDir, `${name}.png`));
  screenshots.push(`${name}.png`);
}

async function setViewport(page, width, height) {
  await page.cdp.send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
  await sleep(500);
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

async function press(page, { key, code, vk, modifiers = 0 }) {
  const event = { key, code, windowsVirtualKeyCode: vk, nativeVirtualKeyCode: vk, modifiers };
  await page.cdp.send("Input.dispatchKeyEvent", { type: "keyDown", ...event });
  await page.cdp.send("Input.dispatchKeyEvent", { type: "keyUp", ...event });
  await sleep(260);
}

async function readActivities(page) {
  const context = await page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${PROJECT_ID}/open", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: "{}",
    });
    const body = await response.json();
    return body.context;
  })()`, { awaitPromise: true });
  assert(context, "project open returned no context");
  const result = await page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${PROJECT_ID}/p6/activities", {
      headers: {
        "content-type": "application/json",
        "X-Tenant-Id": ${JSON.stringify(context.tenant_id)},
        "X-Project-Id": ${JSON.stringify(context.project_id)},
        "X-Project-Revision": String(${JSON.stringify(String(context.revision))}),
      },
    });
    const body = await response.json();
    return {
      status: response.status,
      activities: Array.isArray(body.activities) ? body.activities.map((entry) => entry.activity).filter(Boolean) : [],
    };
  })()`, { awaitPromise: true });
  assert(result.status === 200, `activity read returned ${result.status}`);
  return result.activities;
}

function fingerprint(activities) {
  return JSON.stringify(activities.map((activity) => [activity.activity_id, activity.name, activity.status, activity.duration_value, activity.record_revision]));
}

async function gridState(page) {
  return page.evaluate(`(() => {
    const rows = [...document.querySelectorAll("#cp-activity-grid tbody tr[tabindex]")];
    const active = document.activeElement;
    const activeRow = active?.closest?.("tr[tabindex]");
    const counts = document.querySelector("[data-activity-counts]");
    return {
      rows: rows.map((row) => ({
        activityId: row.dataset.activityId ?? null,
        band: Boolean(row.dataset.wbsRow || row.dataset.fieldGroupRow),
        selected: row.getAttribute("aria-selected") === "true",
        tabindex: row.getAttribute("tabindex"),
      })),
      focusIndex: activeRow ? rows.indexOf(activeRow) : -1,
      focusId: activeRow?.dataset.activityId ?? (activeRow ? "band" : active?.tagName ?? null),
      activityTabStops: rows.filter((row) => row.dataset.activityId && row.getAttribute("tabindex") === "0").map((row) => row.dataset.activityId),
      selectedIds: rows.filter((row) => row.getAttribute("aria-selected") === "true").map((row) => row.dataset.activityId),
      counterSelected: Number(counts?.getAttribute("data-count-selected") ?? -1),
      counterTotal: Number(counts?.getAttribute("data-count-total") ?? -1),
      direction: document.documentElement.dir || "ltr",
    };
  })()`);
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
    if (url.includes("/api/") && params.response.status >= 500) apiFailures.push({ status: params.response.status, url });
  });
  page.cdp.on("Network.requestWillBeSent", (params) => {
    const request = params.request ?? {};
    const method = request.method ?? "";
    const url = request.url ?? "";
    if (!["POST", "PUT", "PATCH", "DELETE"].includes(method)) return;
    if (url.includes("/p6/activities") || url.includes("/p6/schedule") || url.includes("/api/v1/schedule")) {
      scheduleMutations.push({ method, url, at: new Date().toISOString() });
    }
  });

  const report = {
    contract: "cubi-activity-grid-keyboard-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    expected: {},
    scenarios,
    screenshots,
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
    writeFileSync(join(outDir, "activity-grid-keyboard-v26.json"), json);
    writeFileSync(join(evidenceDir, "activity-grid-keyboard-v26.json"), json);
  }

  const state = { total: 0 };

  try {
    await setViewport(page, 1280, 720);
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

    const before = await readActivities(page);
    state.total = before.length;
    const beforeFingerprint = fingerprint(before);
    report.expected = { total: state.total };

    const clickRow = async (activityId) => {
      await page.evaluate(`(() => {
        const row = [...document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]")]
          .find((candidate) => candidate.dataset.activityId === ${JSON.stringify(activityId)});
        row?.scrollIntoView({ block: "center" });
        row?.click();
      })()`);
      await sleep(450);
    };
    const anchorId = await page.evaluate(`document.querySelector("#cp-activity-grid tbody tr[data-activity-id]")?.dataset.activityId ?? null`);
    assert(anchorId, "the grid painted no activity row");
    const beforeClick = await gridState(page);
    const secondIndex = beforeClick.rows.findIndex((row, index) => index > 0 && row.activityId);
    const secondId = beforeClick.rows[secondIndex]?.activityId;
    assert(secondId, "the grid has fewer than two activity rows");

    await scenario("01", "A click selects one row, focuses it and moves the single tab stop", async () => {
      await clickRow(anchorId);
      const first = await gridState(page);
      assert(first.focusId === anchorId, `click focused ${first.focusId}`);
      assert(first.selectedIds.length === 1 && first.selectedIds[0] === anchorId, `click selected ${JSON.stringify(first.selectedIds)}`);
      assert(first.activityTabStops.length === 1 && first.activityTabStops[0] === anchorId, `tab stops are ${JSON.stringify(first.activityTabStops)}`);
      assert(first.counterSelected === 1, `counter shows ${first.counterSelected}`);
      await clickRow(secondId);
      const second = await gridState(page);
      assert(second.focusId === secondId, `second click focused ${second.focusId}`);
      assert(second.activityTabStops.length === 1 && second.activityTabStops[0] === secondId, `tab stops are ${JSON.stringify(second.activityTabStops)}`);
      assert(second.selectedIds.length === 1 && second.selectedIds[0] === secondId, `second click selected ${JSON.stringify(second.selectedIds)}`);
      await capture(page, "01-click-focus");
      return { anchor: anchorId, second: secondId, tabStops: second.activityTabStops };
    });

    await scenario("02", "ArrowDown and ArrowUp walk the displayed order and keep selection, focus and tab stop together", async () => {
      await clickRow(anchorId);
      const start = await gridState(page);
      const startIndex = start.rows.findIndex((row) => row.activityId === anchorId);
      await press(page, { key: "ArrowDown", code: "ArrowDown", vk: 40 });
      const down = await gridState(page);
      const expectedDown = start.rows[startIndex + 1];
      assert(down.focusIndex === startIndex + 1, `ArrowDown focused index ${down.focusIndex}, expected ${startIndex + 1}`);
      if (expectedDown.activityId) {
        assert(down.selectedIds.length === 1 && down.selectedIds[0] === expectedDown.activityId, `ArrowDown selected ${JSON.stringify(down.selectedIds)}`);
        assert(down.activityTabStops[0] === expectedDown.activityId, `tab stop is ${JSON.stringify(down.activityTabStops)}`);
      }
      await press(page, { key: "ArrowUp", code: "ArrowUp", vk: 38 });
      const up = await gridState(page);
      assert(up.focusIndex === startIndex, `ArrowUp focused index ${up.focusIndex}`);
      await capture(page, "02-arrow-walk");
      return { startIndex, downIndex: down.focusIndex, upIndex: up.focusIndex, rows: start.rows.length };
    });

    await scenario("03", "Shift+Arrow extends from the anchor while Ctrl+Arrow only moves focus", async () => {
      await clickRow(anchorId);
      await press(page, { key: "ArrowDown", code: "ArrowDown", vk: 40, modifiers: 8 });
      const shifted = await gridState(page);
      assert(shifted.selectedIds.length >= 2, `Shift+ArrowDown selected ${JSON.stringify(shifted.selectedIds)}`);
      assert(shifted.selectedIds.includes(anchorId), "Shift+ArrowDown dropped the anchor");
      assert(shifted.counterSelected === shifted.selectedIds.length, `counter ${shifted.counterSelected} != ${shifted.selectedIds.length}`);
      const selectedBefore = shifted.selectedIds.join(",");
      const focusBefore = shifted.focusIndex;
      await press(page, { key: "ArrowDown", code: "ArrowDown", vk: 40, modifiers: 2 });
      const ctrl = await gridState(page);
      assert(ctrl.focusIndex === focusBefore + 1, `Ctrl+ArrowDown focused ${ctrl.focusIndex}, expected ${focusBefore + 1}`);
      assert(ctrl.selectedIds.join(",") === selectedBefore, `Ctrl+ArrowDown changed the selection to ${JSON.stringify(ctrl.selectedIds)}`);
      await capture(page, "03-shift-range");
      return { shifted: shifted.selectedIds.length, counter: shifted.counterSelected, ctrlFocus: ctrl.focusIndex };
    });

    await scenario("04", "Home, End and PageDown land on the computed row and select only activity targets", async () => {
      await clickRow(anchorId);
      const start = await gridState(page);
      await press(page, { key: "End", code: "End", vk: 35 });
      const end = await gridState(page);
      assert(end.focusIndex === start.rows.length - 1, `End focused ${end.focusIndex} of ${start.rows.length}`);
      await press(page, { key: "Home", code: "Home", vk: 36 });
      const home = await gridState(page);
      assert(home.focusIndex === 0, `Home focused ${home.focusIndex}`);
      await clickRow(anchorId);
      const beforePage = await gridState(page);
      const anchorIndex = beforePage.rows.findIndex((row) => row.activityId === anchorId);
      await press(page, { key: "PageDown", code: "PageDown", vk: 34 });
      const pageDown = await gridState(page);
      assert(pageDown.focusIndex === Math.min(beforePage.rows.length - 1, anchorIndex + 10), `PageDown focused ${pageDown.focusIndex}`);
      const pageRow = beforePage.rows[pageDown.focusIndex];
      if (pageRow.activityId) assert(pageDown.selectedIds.length === 1 && pageDown.selectedIds[0] === pageRow.activityId, `PageDown selected ${JSON.stringify(pageDown.selectedIds)}`);
      await press(page, { key: "PageUp", code: "PageUp", vk: 33 });
      const pageUp = await gridState(page);
      assert(pageUp.focusIndex === anchorIndex, `PageUp focused ${pageUp.focusIndex}, expected ${anchorIndex}`);
      await capture(page, "04-home-end-page");
      return { end: end.focusIndex, home: home.focusIndex, pageDown: pageDown.focusIndex, pageUp: pageUp.focusIndex };
    });

    await scenario("05", "Collapsed branches leave the arrow sequence entirely", async () => {
      const target = await page.evaluate(`(() => {
        const bands = [...document.querySelectorAll("#cp-activity-grid tbody tr[data-wbs-row]")];
        const band = bands.find((candidate, index) => index > 0 && candidate.querySelector("[data-wbs-toggle]"));
        return band ? { id: band.dataset.wbsRow, name: band.getAttribute("aria-label") } : null;
      })()`);
      assert(target, "no child WBS band with a toggle was found");
      await page.evaluate(`document.querySelector("[data-wbs-row='${target.id}'] [data-wbs-toggle]")?.click()`);
      await sleep(600);
      const collapsed = await page.evaluate(`(() => ({
        rows: document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]").length,
        bands: document.querySelectorAll("#cp-activity-grid tbody tr[data-wbs-row]").length,
        expanded: document.querySelector("[data-wbs-row='${target.id}']")?.getAttribute("aria-expanded"),
      }))()`);
      assert(collapsed.expanded === "false", `band aria-expanded is ${collapsed.expanded}`);
      const firstId = await page.evaluate(`document.querySelector("#cp-activity-grid tbody tr[data-activity-id]")?.dataset.activityId ?? null`);
      assert(firstId, "no activity row remained after collapsing the first band");
      await clickRow(firstId);
      const start = await gridState(page);
      await press(page, { key: "ArrowDown", code: "ArrowDown", vk: 40 });
      const next = await gridState(page);
      const expected = start.rows[start.focusIndex + 1];
      assert(next.focusIndex === start.focusIndex + 1, "ArrowDown did not advance after collapse");
      assert(expected && !expected.activityId ? true : next.selectedIds.length === 1, "arrow selection state is inconsistent");
      await page.evaluate(`document.querySelector("[data-wbs-row='${target.id}'] [data-wbs-toggle]")?.click()`);
      await sleep(600);
      await capture(page, "05-collapsed-sequence");
      return { band: target.id, remainingRows: collapsed.rows, remainingBands: collapsed.bands, from: start.focusIndex, to: next.focusIndex };
    });

    await scenario("06", "Enter on the focused row selects it and the details pane follows", async () => {
      await clickRow(anchorId);
      const start = await gridState(page);
      await press(page, { key: "ArrowDown", code: "ArrowDown", vk: 40 });
      const focused = await gridState(page);
      const focusedRow = start.rows[focused.focusIndex];
      if (focusedRow.activityId) {
        await press(page, { key: "Enter", code: "Enter", vk: 13 });
        const entered = await gridState(page);
        assert(entered.selectedIds.length === 1 && entered.selectedIds[0] === focusedRow.activityId, `Enter selected ${JSON.stringify(entered.selectedIds)}`);
        const details = await page.evaluate(`document.querySelector("#cp-details")?.textContent ?? ""`);
        assert(details.includes(focusedRow.activityId), `details pane does not show ${focusedRow.activityId}`);
        return { activity: focusedRow.activityId, details: true };
      }
      return { activity: null, details: false };
    });

    await scenario("07", "Persian RTL keeps the same vertical order", async () => {
      await setLanguage(page, "fa");
      const firstId = await page.evaluate(`document.querySelector("#cp-activity-grid tbody tr[data-activity-id]")?.dataset.activityId ?? null`);
      assert(firstId, "no activity row in RTL");
      await clickRow(firstId);
      const start = await gridState(page);
      assert(start.direction === "rtl", `direction is ${start.direction}`);
      await press(page, { key: "ArrowDown", code: "ArrowDown", vk: 40 });
      const down = await gridState(page);
      assert(down.focusIndex === start.focusIndex + 1, `RTL ArrowDown focused ${down.focusIndex}, expected ${start.focusIndex + 1}`);
      await press(page, { key: "ArrowUp", code: "ArrowUp", vk: 38 });
      const up = await gridState(page);
      assert(up.focusIndex === start.focusIndex, `RTL ArrowUp focused ${up.focusIndex}`);
      await capture(page, "07-rtl-navigation");
      await setLanguage(page, "en");
      return { from: start.focusIndex, down: down.focusIndex, up: up.focusIndex };
    });

    await scenario("08", "Grid navigation never touches schedule input", async () => {
      const after = await readActivities(page);
      assert(after.length === state.total, `read model changed ${state.total} -> ${after.length}`);
      assert(fingerprint(after) === beforeFingerprint, "activity read model changed during the suite");
      assert(scheduleMutations.length === 0, `schedule writes observed: ${JSON.stringify(scheduleMutations.slice(0, 3))}`);
      return { activities: after.length, writes: scheduleMutations.length };
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
  log(`Evidence: ${join(evidenceDir, "activity-grid-keyboard-v26.json")}`);
}

main().catch((error) => {
  process.stderr.write(`\n${error && error.stack ? error.stack : error}\n`);
  process.exit(1);
});
