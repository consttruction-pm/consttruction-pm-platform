#!/usr/bin/env node
/**
 * Version 26 WBS band format acceptance (ACT-004).
 *
 * Proves in the real preview that the WBS grouping band has its own typeface,
 * size, text ink, height and label selection, independent of the activity
 * table; that the band remains aligned with its Gantt summary row; that the
 * format is published with the saved layout, survives a reload, and can be
 * reset to the shipped defaults without touching any other presentation value.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4199 \
 *   CUBI_TESTED_CODE_SHA=<code commit> node e2e/activity-wbs-band-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4199";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "activity-wbs-band-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `activity-wbs-band-v26-${evidenceDate}`);
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
  const file = `activity-wbs-band-v26/${name}.png`;
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

const dialogSelector = "dialog[data-desktop-dialog=user-preferences]";

async function openPreferences(page) {
  const clicked = await page.evaluate(`(() => {
    const element = [...document.querySelectorAll('[data-desktop-command="dialog.user-preferences"]')]
      .find((item) => item.getClientRects().length > 0 && !item.disabled);
    if (!element) return false;
    element.click();
    return true;
  })()`);
  assert(clicked, "User Preferences command is missing");
  await page.waitForSelector(`${dialogSelector}[open]`, "user preferences dialog", 8000);
  await sleep(250);
}

async function setControl(page, selector, value, kind = "select") {
  const changed = await page.evaluate(`(() => {
    const control = document.querySelector('${dialogSelector} ' + ${JSON.stringify(selector)});
    if (!control) return false;
    ${kind === "check"
      ? "control.checked = " + JSON.stringify(Boolean(value)) + ";"
      : "control.value = " + JSON.stringify(String(value)) + "; if (control.value !== " + JSON.stringify(String(value)) + ") return false;"}
    control.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  assert(changed, `WBS control ${selector} did not accept ${value}`);
  await sleep(120);
}

async function submit(page, selector = "[data-dialog-ok]") {
  const clicked = await page.evaluate(`(() => {
    const button = document.querySelector('${dialogSelector} ' + ${JSON.stringify(selector)});
    if (!button || button.disabled) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `dialog control ${selector} is missing`);
  await page.waitFor(`!document.querySelector('${dialogSelector}')?.open`, "preferences dialog closed", 8000);
  await sleep(900);
}

async function bandState(page) {
  return page.evaluate(`(() => {
    const bands = [...document.querySelectorAll("#cp-activity-grid tbody tr.cp-p6-wbs-band")];
    const gantt = [...document.querySelectorAll("#cp-gantt .cp-gantt-group-row[data-gantt-wbs-id]")];
    const first = bands[0] ?? null;
    const firstCell = first?.querySelector("td.cp-p6-tree-cell") ?? first?.querySelector("td");
    const second = bands[1] ?? null;
    const style = firstCell ? getComputedStyle(firstCell) : null;
    const bandRect = first?.getBoundingClientRect();
    const secondRect = second?.getBoundingClientRect();
    return {
      bands: bands.map((row) => ({
        id: row.dataset.wbsRow ?? "",
        depth: Number(row.dataset.wbsDepth ?? 0),
        level: row.dataset.wbsLevel ?? "",
        fontFamily: style?.fontFamily ?? "",
        fontSize: style ? getComputedStyle(row.querySelector("td.cp-p6-tree-cell") ?? row).fontSize : "",
        colour: style?.color ?? "",
        height: Math.round(row.getBoundingClientRect().height),
        title: row.querySelector(".cp-p6-wbs-title")?.textContent?.trim() ?? "",
        code: row.querySelector(".cp-p6-wbs-code")?.textContent?.trim() ?? "",
        name: row.querySelector(".cp-p6-wbs-name")?.textContent?.trim() ?? "",
        top: Math.round(row.getBoundingClientRect().top),
      })),
      gantt: gantt.map((row) => {
        const rect = row.getBoundingClientRect();
        return { id: row.dataset.ganttWbsId ?? "", depth: Number(row.dataset.ganttDepth ?? 0), top: Math.round(rect.top), height: Math.round(rect.height) };
      }),
      firstFont: style ? style.fontFamily : "",
      firstFontSize: style ? style.fontSize : "",
      firstColour: style ? style.color : "",
      firstHeight: bandRect ? Math.round(bandRect.height) : 0,
      secondTop: secondRect ? Math.round(secondRect.top) : 0,
      firstBottom: bandRect ? Math.round(bandRect.bottom) : 0,
      dir: document.documentElement.dir || "ltr",
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    };
  })()`);
}

function readLayout(page, projectId, scope) {
  return page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${projectId}/p6/layouts/${scope}/activity");
    let body = null;
    try { body = await response.json(); } catch (error) { body = null; }
    return { status: response.status, body };
  })()`, { awaitPromise: true });
}

async function waitForWbsPresence(page, predicate) {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    await sleep(200);
    for (const scope of ["project", "user"]) {
      const saved = await readLayout(page, "preview-rps-01", scope);
      const wbs = saved.body?.metadata?.presentation?.wbs;
      if (saved.status !== 200 || !wbs) continue;
      if (predicate(wbs)) return saved;
    }
  }
  return null;
}

/** Every WBS band keeps its Gantt summary row at the same vertical offset. */
function assertGanttAlignment(state, label) {
  assert(state.gantt.length === state.bands.length, `${label}: Gantt has ${state.gantt.length} rows for ${state.bands.length} bands`);
  const origin = state.gantt[0].top - state.bands[0].top;
  state.bands.forEach((band, index) => {
    const row = state.gantt[index];
    assert(row && row.id === band.id, `${label}: Gantt row ${index} is ${row?.id}, table band ${band.id}`);
    const drift = (row.top - band.top) - origin;
    assert(Math.abs(drift) <= 2, `${label}: band ${band.id} drifts ${drift}px from its Gantt row`);
  });
}

async function dialogState(page) {
  return page.evaluate(`(() => {
    const dialog = document.querySelector("${dialogSelector}");
    return {
      open: Boolean(dialog?.open),
      title: dialog.querySelector("h2")?.textContent?.trim() ?? "",
      values: {
        fontFamily: dialog.querySelector('select[name="wbs.fontFamily"]')?.value ?? "",
        fontSize: dialog.querySelector('select[name="wbs.fontSize"]')?.value ?? "",
        inkMode: dialog.querySelector('select[name="wbs.inkMode"]')?.value ?? "",
        textColor: dialog.querySelector('input[name="wbs.textColor"]')?.value ?? "",
        rowHeight: dialog.querySelector('input[name="wbs.rowHeight"]')?.value ?? "",
        title: dialog.querySelector('input[name="wbs.label.title"]')?.checked ?? null,
        code: dialog.querySelector('input[name="wbs.label.code"]')?.checked ?? null,
        name: dialog.querySelector('input[name="wbs.label.name"]')?.checked ?? null,
      },
      reset: dialog.querySelector("[data-dialog-reset]")?.textContent?.trim() ?? "",
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
    contract: "cubi-activity-wbs-band-v26.v1",
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

  function writeReport() {
    report.scenarios = scenarios;
    report.passed = scenarios.filter((entry) => entry.status === "pass").length;
    report.failed = scenarios.filter((entry) => entry.status === "fail").length;
    const json = JSON.stringify(report, null, 2);
    writeFileSync(join(outDir, "activity-wbs-band-v26.json"), json);
    writeFileSync(join(evidenceDir, "activity-wbs-band-v26.json"), json);
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

    await scenario("01", "WBS bands render with code, name and the table-independent defaults", async () => {
      const state = await bandState(page);
      assert(state.bands.length === 7, `expected 7 WBS bands, got ${state.bands.length}`);
      assert(state.bands[0].code === "1", `root code is ${state.bands[0].code}`);
      assert(state.bands[0].name === "Riverside Pump Station Upgrade", `root name is ${state.bands[0].name}`);
      assert(state.bands.every((band) => band.title === ""), "the WBS title is shown by default");
      // The band keeps the shipped format: Tahoma 11 px, contrast ink, 22 px.
      assert(/Tahoma/i.test(state.firstFont), `default band font is ${state.firstFont}`);
      assert(state.firstFontSize === "11px", `default band size is ${state.firstFontSize}`);
      assert(state.bands[0].colour === "rgb(255, 255, 0)", `default level-1 ink is ${state.bands[0].colour}`);
      // The rendered band includes the 1 px branch separator below the 22 px row.
      assert(state.firstHeight >= 22 && state.firstHeight <= 23, `default band height is ${state.firstHeight}`);
      // Vertical geometry: the next band starts at or below the previous bottom.
      assert(state.secondTop >= state.firstBottom, `bands overlap: ${state.secondTop} < ${state.firstBottom}`);
      // The Gantt draws one summary row for every visible band at the same
      // depth and keeps the same vertical extent.
      assertGanttAlignment(state, "defaults");
      state.bands.forEach((band, index) => {
        assert(state.gantt[index].depth === band.depth, `Gantt depth ${state.gantt[index].depth} differs from band depth ${band.depth}`);
      });
      await capture(page, "01-wbs-band-defaults-en-1366");
      return { bands: state.bands.length, height: state.firstHeight };
    });

    await scenario("02", "the dialog writes a band font, ink, height and label selection", async () => {
      await openPreferences(page);
      const dialog = await dialogState(page);
      assert(dialog.values.fontFamily === "tahoma", `dialog band font is ${dialog.values.fontFamily}`);
      assert(dialog.values.inkMode === "auto", `dialog ink mode is ${dialog.values.inkMode}`);
      assert(dialog.values.rowHeight === "22", `dialog band height is ${dialog.values.rowHeight}`);
      assert(dialog.values.title === false && dialog.values.code === true && dialog.values.name === true, "label defaults are wrong");
      assert(dialog.reset === "Reset band format", `band reset action is missing: ${dialog.reset}`);
      await setControl(page, 'select[name="wbs.fontFamily"]', "cairo");
      await setControl(page, 'select[name="wbs.fontSize"]', "14");
      await setControl(page, 'select[name="wbs.inkMode"]', "custom");
      await setControl(page, 'input[name="wbs.textColor"]', "#102030");
      await setControl(page, 'input[name="wbs.rowHeight"]', "30");
      await setControl(page, 'input[name="wbs.label.title"]', true, "check");
      await setControl(page, 'input[name="wbs.label.code"]', false, "check");
      await setControl(page, 'input[name="wbs.label.name"]', true, "check");
      await submit(page);
      const after = await bandState(page);
      assert(/Cairo/i.test(after.firstFont), `applied band font is ${after.firstFont}`);
      assert(after.firstFontSize === "14px", `applied band size is ${after.firstFontSize}`);
      assert(after.firstColour === "rgb(16, 32, 48)", `applied band ink is ${after.firstColour}`);
      assert(after.firstHeight >= 30 && after.firstHeight <= 31, `applied band height is ${after.firstHeight}`);
      assert(after.bands[0].title === "WBS", `band title is ${after.bands[0].title}`);
      assert(after.bands.every((band) => band.code === ""), "the band code is still shown");
      assert(after.bands[0].name === "Riverside Pump Station Upgrade", `band name is ${after.bands[0].name}`);
      // The taller band still lines up with its Gantt summary row.
      assertGanttAlignment(after, "applied 30px bands");
      // The activity table keeps its own font, so the two surfaces are independent.
      const tableFont = await page.evaluate(`(() => {
        const cell = document.querySelector("#cp-activity-grid tbody tr[data-activity-id] td");
        const root = getComputedStyle(document.documentElement);
        return { cell: cell ? getComputedStyle(cell).fontFamily : "", size: root.getPropertyValue("--cp-p6-font-size").trim() };
      })()`);
      assert(!/Cairo/i.test(tableFont.cell), `the activity table changed font: ${tableFont.cell}`);
      assert(tableFont.size === "11px", `the activity table changed size: ${tableFont.size}`);
      const saved = await waitForWbsPresence(page, (wbs) => wbs.fontFamily === "cairo" && wbs.fontSize === 14 && wbs.inkMode === "custom");
      assert(saved, "the layout did not publish the new WBS band format");
      assert(saved.body?.metadata?.presentation?.wbs?.labels?.code === false, "the saved labels do not match the dialog");
      await capture(page, "02-wbs-band-cairo-30px-en-1366");
      return { revision: saved.body?.revision, wbs: saved.body?.metadata?.presentation?.wbs };
    });

    await scenario("03", "the saved band format survives a full reload", async () => {
      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "reload after band save");
      await sleep(1200);
      const state = await bandState(page);
      assert(/Cairo/i.test(state.firstFont), `reload band font is ${state.firstFont}`);
      assert(state.firstFontSize === "14px", `reload band size is ${state.firstFontSize}`);
      assert(state.firstColour === "rgb(16, 32, 48)", `reload band ink is ${state.firstColour}`);
      assert(state.firstHeight >= 30 && state.firstHeight <= 31, `reload band height is ${state.firstHeight}`);
      assert(state.bands[0].title === "WBS" && state.bands[0].code === "", "reload lost the band label selection");
      assertGanttAlignment(state, "reload");
      await capture(page, "03-wbs-band-after-reload-en-1366");
      return { height: state.firstHeight, bands: state.bands.length };
    });

    await scenario("04", "Reset band format restores the defaults and keeps the other presentation values", async () => {
      await openPreferences(page);
      await submit(page, "[data-dialog-reset]");
      const reset = await bandState(page);
      assert(/Tahoma/i.test(reset.firstFont), `reset band font is ${reset.firstFont}`);
      assert(reset.firstFontSize === "11px", `reset band size is ${reset.firstFontSize}`);
      assert(reset.bands[0].colour === "rgb(255, 255, 0)", `reset band ink is ${reset.bands[0].colour}`);
      assert(reset.firstHeight >= 22 && reset.firstHeight <= 23, `reset band height is ${reset.firstHeight}`);
      assert(reset.bands[0].title === "" && reset.bands[0].code === "1", "reset did not restore the label defaults");
      const saved = await waitForWbsPresence(page, (wbs) => wbs.fontFamily === "tahoma" && wbs.fontSize === 11 && wbs.inkMode === "auto" && wbs.rowHeight === 22);
      assert(saved, "the reset was not published with the layout");
      assert(saved.body?.metadata?.presentation?.table?.fontFamily === "tahoma", "the reset changed the activity table");
      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "reload after band reset");
      await sleep(1200);
      const reloaded = await bandState(page);
      assert(reloaded.firstHeight >= 22 && reloaded.firstHeight <= 23 && /Tahoma/i.test(reloaded.firstFont), `reset did not survive reload: ${reloaded.firstHeight}/${reloaded.firstFont}`);
      await capture(page, "04-wbs-band-reset-en-1366");
      return { revision: saved.body?.revision, height: reloaded.firstHeight };
    });

    await scenario("05", "the band dialog and hierarchy render in Persian RTL at 1280", async () => {
      await setViewport(page, 1280, 720);
      await setLanguage(page, "fa");
      await openPreferences(page);
      const dialog = await page.evaluate(`(() => {
        const element = document.querySelector("${dialogSelector}");
        return {
          title: element.querySelector("h2")?.textContent?.trim() ?? "",
          reset: element.querySelector("[data-dialog-reset]")?.textContent?.trim() ?? "",
          legend: [...element.querySelectorAll("legend")].map((item) => item.textContent?.trim() ?? "").join(" | "),
          overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        };
      })()`);
      assert(/ترجیحات کاربر/.test(dialog.title), `Persian title is missing: ${dialog.title}`);
      assert(/بازنشانی قالب باند/.test(dialog.reset), `Persian reset label is missing: ${dialog.reset}`);
      assert(/باند WBS/.test(dialog.legend), `Persian band legend is missing: ${dialog.legend}`);
      assert(dialog.overflow <= 1, `the RTL dialog overflows by ${dialog.overflow}px`);
      await capture(page, "05-wbs-band-dialog-fa-rtl-1280");
      await page.evaluate(`(() => {
        const dialog = document.querySelector("${dialogSelector}");
        dialog.querySelector("[data-dialog-cancel]")?.click();
      })()`);
      await sleep(300);
      const state = await bandState(page);
      assert(state.dir === "rtl", "the table lost RTL");
      assert(state.overflow <= 1, `the RTL table overflows by ${state.overflow}px`);
      assert(state.bands.length === 7, `RTL bands are ${state.bands.length}`);
      return dialog;
    });

    await scenario("06", "the band format fits a 1920x1080 cell", async () => {
      await setViewport(page, 1920, 1080);
      await sleep(500);
      const state = await bandState(page);
      assert(state.overflow <= 1, `the 1920 cell overflows by ${state.overflow}px`);
      assert(state.bands.length === 7, `the 1920 cell has ${state.bands.length} bands`);
      assertGanttAlignment(state, "1920");
      await capture(page, "06-wbs-band-en-1920");
      return { bands: state.bands.length, overflow: state.overflow };
    });

    log(`\nAll ${scenarios.length} WBS band scenarios passed`);
  } catch (error) {
    exceptions.push(String(error && error.stack ? error.stack : error));
    process.exitCode = 1;
  } finally {
    writeReport();
    await chrome.stop();
  }
}

await main();
