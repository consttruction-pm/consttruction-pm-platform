#!/usr/bin/env node
/**
 * Version 26 Gantt overlay acceptance (ACT-011).
 *
 * Proves in the real preview that the Data Date the server publishes in the
 * project schedule settings reaches the status bar, the Activity Details pane
 * and the Gantt line at the exact same position as its day tick; that the Bars
 * dialog edits draw the line and the progress-point line without writing any
 * schedule data; that the progress points are read against the Data Date the
 * way P6 reads them; that the settings travel with the saved layout and are
 * restored after a full reload; that the baseline editor stays honest when the
 * project has no baseline dates; and that the overlays hold in en LTR and fa
 * RTL at 1280, 1366 and 1920 widths.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4201 \
 *   CUBI_TESTED_CODE_SHA=<code commit> node e2e/activity-gantt-overlays-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4201";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-13";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "activity-gantt-overlays-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `activity-gantt-overlays-v26-${evidenceDate}`);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const projectId = "preview-rps-01";
const dataDate = "2026-10-12";

const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const scheduleWrites = [];
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
  const file = `activity-gantt-overlays-v26/${name}.png`;
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

async function clickVisible(page, selector, label) {
  const clicked = await page.evaluate(`(() => {
    const element = [...document.querySelectorAll(${JSON.stringify(selector)})]
      .find((item) => item.getClientRects().length > 0 && !item.disabled);
    if (!element) return false;
    element.click();
    return true;
  })()`);
  assert(clicked, `${label} is missing`);
  await sleep(350);
}

async function openBars(page) {
  await clickVisible(page, '[data-desktop-command="dialog.bars"]', "Bars command");
  await page.waitFor('Boolean(document.querySelector(\'[data-desktop-dialog="bars"]\')?.open)', "bars dialog");
  await sleep(250);
}

async function readBarsDialog(page) {
  return page.evaluate(`(() => {
    const dialog = document.querySelector('[data-desktop-dialog="bars"]');
    if (!dialog) return null;
    const dataDateFieldset = [...dialog.querySelectorAll("fieldset")].find((item) => (item.querySelector("legend")?.textContent || "").trim().toLowerCase().startsWith("data date"));
    const text = dialog.textContent || "";
    return {
      open: dialog.open,
      dataDateDisabled: dataDateFieldset ? dataDateFieldset.disabled : null,
      dataDateNote: dataDateFieldset?.querySelector(".cp-dialog-note")?.textContent?.trim() ?? "",
      mentionsDataDate: text.includes(${JSON.stringify(dataDate)}),
      baselineNote: /No baseline dates are loaded/.test(text),
      progressField: Boolean(dialog.querySelector('[name="gantt.progressLine.visible"]')),
    };
  })()`);
}

/**
 * Applies the requested Bars-dialog fields and submits with OK. Values are set
 * on the real controls, so the form's FormData path is the one under test.
 */
async function applyBars(page, fields, label) {
  const applied = await page.evaluate(`(() => {
    const dialog = document.querySelector('[data-desktop-dialog="bars"]');
    if (!dialog) return "missing";
    const fields = ${JSON.stringify(fields)};
    for (const [name, value] of Object.entries(fields)) {
      const control = dialog.querySelector('[name="' + name + '"]');
      if (!control) return "missing:" + name;
      if (control.type === "checkbox") control.checked = Boolean(value);
      else control.value = String(value);
    }
    const ok = dialog.querySelector("[data-dialog-ok]");
    if (!ok) return "no-ok";
    ok.click();
    return "ok";
  })()`);
  assert(applied === "ok", `${label}: Bars dialog did not submit (${applied})`);
  await sleep(550);
}

async function readLayout(page, scope) {
  return page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${projectId}/p6/layouts/" + ${JSON.stringify(scope)} + "/activity");
    let body = null;
    try { body = await response.json(); } catch (error) { body = null; }
    return { status: response.status, body };
  })()`, { awaitPromise: true });
}

async function saveLayout(page) {
  await clickVisible(page, '[data-desktop-command="layout.save"]', "Save Layout");
  let latest = null;
  for (let attempt = 0; attempt < 40; attempt += 1) {
    await sleep(200);
    for (const scope of ["project", "user"]) {
      const saved = await readLayout(page, scope);
      if (saved.status !== 200 || !saved.body) continue;
      latest = saved;
      const gantt = saved.body.metadata?.presentation?.gantt;
      if (gantt?.dataDateLine && gantt?.progressLine) return saved;
    }
  }
  throw new Error(`layout save did not persist the Gantt overlays (status ${latest?.status ?? "none"})`);
}

/** Gantt overlays, axis tick, chrome and details read from the live DOM. */
async function overlayState(page) {
  return page.evaluate(`(() => {
    const round = (value) => Math.round(value * 10) / 10;
    const line = document.querySelector("[data-gantt-data-date]");
    const lineStyle = line ? getComputedStyle(line) : null;
    const labelStyle = line ? getComputedStyle(line.querySelector(".cp-gantt-data-date-label")) : null;
    const body = document.querySelector("#cp-gantt [data-gantt-body]");
    const bodyRect = body?.getBoundingClientRect() ?? null;
    const lineRect = line?.getBoundingClientRect() ?? null;
    const tick = document.querySelector('[data-gantt-tick="${dataDate}"]');
    const ticks = [...document.querySelectorAll("#cp-gantt [data-gantt-tick]")].map((item) => ({
      date: item.getAttribute("data-gantt-tick"),
      leftPercent: round(Number.parseFloat(item.style.left)),
    }));
    const svg = document.querySelector(".cp-gantt-progress-line-layer");
    const path = document.querySelector("[data-gantt-progress-line]");
    const pathStyle = path ? getComputedStyle(path) : null;
    const statusCells = [...document.querySelectorAll("[data-statusbar] .cp-statusbar-cell")]
      .map((cell) => (cell.textContent || "").trim());
    const dataDateCell = statusCells.find((text) => /^Data Date:|^تاریخ داده:/.test(text)) ?? "";
    return {
      line: line ? {
        date: line.getAttribute("data-gantt-data-date"),
        leftPercent: round(Number.parseFloat(line.style.left)),
        className: line.className,
        label: (line.textContent || "").trim(),
        colorVariable: lineStyle?.getPropertyValue("--cp-data-date-color").trim(),
        width: lineStyle?.width,
        backgroundColor: lineStyle?.backgroundColor,
        borderLeftStyle: lineStyle?.borderLeftStyle,
        borderRightStyle: lineStyle?.borderRightStyle,
        borderLeftWidth: lineStyle?.borderLeftWidth,
        borderRightWidth: lineStyle?.borderRightWidth,
        height: round(lineRect?.height ?? 0),
        withinBody: Boolean(
          bodyRect && lineRect &&
          lineRect.top >= bodyRect.top - 2 && lineRect.bottom <= bodyRect.bottom + 2 &&
          lineRect.left >= bodyRect.left - 2 && lineRect.right <= bodyRect.right + 2,
        ),
        labelStyle: labelStyle ? {
          fontSize: labelStyle.fontSize,
          backgroundColor: labelStyle.backgroundColor,
          color: labelStyle.color,
        } : null,
      } : null,
      tickLeftPercent: tick ? round(Number.parseFloat(tick.style.left)) : null,
      ticks,
      progress: svg && path ? {
        points: Number(path.getAttribute("data-gantt-progress-line")),
        dataDate: svg.getAttribute("data-gantt-progress-data-date"),
        behind: Number(svg.getAttribute("data-gantt-progress-behind")),
        on: Number(svg.getAttribute("data-gantt-progress-on")),
        ahead: Number(svg.getAttribute("data-gantt-progress-ahead")),
        color: pathStyle?.stroke,
        width: pathStyle?.strokeWidth,
        pathLength: (path.getAttribute("d") || "").length,
      } : null,
      dataDateCell,
      details: document.querySelector("#cp-details")?.innerText ?? "",
      detailsVisible: Boolean(document.querySelector("#cp-details") && !document.querySelector("#cp-details").hidden),
      criticalBars: document.querySelectorAll("#cp-gantt .cp-gantt-bar.is-critical").length,
      baselineBars: document.querySelectorAll('#cp-gantt .cp-gantt-bar[data-gantt-bar-kind="baseline"]').length,
      dayTicks: document.querySelectorAll("#cp-gantt [data-gantt-tick]").length,
      scaleMode: document.querySelector("#cp-gantt [data-gantt-scale-mode]")?.getAttribute("data-gantt-scale-mode") ?? null,
      dir: document.documentElement.dir || "ltr",
      lang: document.documentElement.lang || "en",
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      chartLeft: round(document.querySelector("#cp-gantt")?.getBoundingClientRect().left ?? 0),
      chartRight: round(document.querySelector("#cp-gantt")?.getBoundingClientRect().right ?? 0),
    };
  })()`);
}

function assertNoScheduleWrites(label) {
  const writes = scheduleWrites.splice(0);
  assert(writes.length === 0, `${label}: overlay edits wrote schedule data: ${writes.map((item) => `${item.method} ${item.url}`).join(", ")}`);
}

/**
 * Position the timescale itself assigns to a date, interpolated between the
 * drawn ticks. Day mode thins its tick labels on long projects, so the exact
 * date may not own a tick; the ticks either side still define the same scale.
 */
function expectedLeftPercent(ticks, iso) {
  const ms = Date.parse(`${iso}T00:00:00Z`);
  const points = ticks
    .map((tick) => ({ ms: Date.parse(`${tick.date}T00:00:00Z`), left: tick.leftPercent }))
    .filter((point) => Number.isFinite(point.ms) && Number.isFinite(point.left))
    .sort((a, b) => a.ms - b.ms);
  const exact = points.find((point) => point.ms === ms);
  if (exact) return exact.left;
  const before = [...points].reverse().find((point) => point.ms < ms);
  const after = points.find((point) => point.ms > ms);
  if (!before || !after) return null;
  return before.left + ((ms - before.ms) / (after.ms - before.ms)) * (after.left - before.left);
}

async function waitForDataDate(page) {
  await page.waitFor(
    `(() => {
      const cell = [...document.querySelectorAll("[data-statusbar] .cp-statusbar-cell")]
        .find((item) => /^Data Date:|^تاریخ داده:/.test((item.textContent || "").trim()));
      return Boolean(cell && cell.textContent.includes(${JSON.stringify(dataDate)}));
    })()`,
    "status bar Data Date",
    15000,
  );
}

async function selectDayScale(page) {
  const state = await overlayState(page);
  if (state.scaleMode !== "day") await clickVisible(page, '[data-gantt-scale="day"]', "day timescale");
  await sleep(450);
}

async function revealDetails(page) {
  const state = await overlayState(page);
  if (!state.detailsVisible) await clickVisible(page, '[data-desktop-command="view.toggle-details"]', "Show Activity Details");
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
  page.cdp.on("Network.requestWillBeSent", (params) => {
    const method = params.request?.method ?? "GET";
    const url = params.request?.url ?? "";
    if (method === "GET" || method === "HEAD" || !url.includes("/api/")) return;
    if (!url.includes("/p6/schedule/") && !url.includes("/activities/")) return;
    scheduleWrites.push({ method, url });
  });

  const report = {
    contract: "cubi-activity-gantt-overlays-v26.v1",
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
    writeFileSync(join(outDir, "activity-gantt-overlays-v26.json"), json);
    writeFileSync(join(evidenceDir, "activity-gantt-overlays-v26.json"), json);
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

    await scenario("01", "the server Data Date reaches the chrome, Details and the Gantt line", async () => {
      scheduleWrites.length = 0;
      await waitForDataDate(page);
      await selectDayScale(page);
      await revealDetails(page);
      await page.click('#cp-activity-grid tbody tr[data-activity-id="A100"]');
      await page.waitFor(
        'Boolean(document.querySelector("#cp-details")?.innerText?.includes("2026-10-12"))',
        "Details pane Data date",
        15000,
      );
      const state = await overlayState(page);
      assert(state.line, "the Gantt draws no Data Date line");
      assert(state.line.date === dataDate, `line date is ${state.line.date}`);
      assert(state.line.label === "Data Date", `line label is ${JSON.stringify(state.line.label)}`);
      const expectedLeft = expectedLeftPercent(state.ticks, dataDate);
      assert(expectedLeft !== null, "the timescale has no tick around the Data Date");
      assert(Math.abs(state.line.leftPercent - expectedLeft) <= 0.6, `line at ${state.line.leftPercent}% is not on the timescale position ${Math.round(expectedLeft * 10) / 10}%`);
      assert(state.line.withinBody, "the Data Date line is not contained by the Gantt body");
      assert(state.line.height > 100, `the Data Date line height is ${state.line.height}px`);
      assert(state.line.colorVariable === "#c00000", `default line colour variable is ${state.line.colorVariable}`);
      assert(/Data Date:.*2026-10-12/.test(state.dataDateCell), `status bar shows ${JSON.stringify(state.dataDateCell)}`);
      assert(/data date/i.test(state.details) && state.details.includes(dataDate), `Details pane does not show the authoritative Data Date: ${JSON.stringify(state.details.slice(0, 300))}`);
      assert(state.criticalBars > 0, "no critical bar is drawn");
      assertNoScheduleWrites("reading the Data Date");
      await capture(page, "01-data-date-line-and-tick-en-1366");
      return {
        linePercent: state.line.leftPercent,
        expectedPercent: Math.round(expectedLeft * 10) / 10,
        statusBar: state.dataDateCell,
        lineHeight: state.line.height,
        criticalBars: state.criticalBars,
      };
    });

    await scenario("02", "the Bars dialog is enabled by the real date and draws the progress line", async () => {
      scheduleWrites.length = 0;
      await openBars(page);
      const dialog = await readBarsDialog(page);
      assert(dialog, "the Bars dialog did not open");
      assert(dialog.dataDateDisabled === false, "the Data Date fieldset is still disabled");
      assert(dialog.dataDateNote.includes(dataDate), `the Data Date note does not name the date: ${dialog.dataDateNote}`);
      assert(dialog.progressField, "the progress-line field is missing");
      await applyBars(page, {
        "gantt.progressLine.visible": true,
        "gantt.progressLine.thickness": 2,
        "gantt.progressLine.color": "#ff8800",
      }, "progress line");
      const state = await overlayState(page);
      assert(state.progress, "the progress line was not drawn");
      assert(state.progress.points === 14, `progress line joins ${state.progress.points} points, expected 14`);
      assert(state.progress.dataDate === dataDate, `progress line data date is ${state.progress.dataDate}`);
      const classified = state.progress.behind + state.progress.on + state.progress.ahead;
      assert(classified === state.progress.points, `${classified} classified points for ${state.progress.points} plotted points`);
      assert(state.progress.behind >= 3, `only ${state.progress.behind} progress points are behind the Data Date`);
      assert(state.progress.ahead >= 5, `only ${state.progress.ahead} progress points are ahead of the Data Date`);
      assert(state.progress.on === 0, `unexpected ${state.progress.on} on-schedule points at the fixture dates`);
      assert(state.progress.width === "2px", `progress line width is ${state.progress.width}`);
      assertNoScheduleWrites("enabling the progress line");
      await capture(page, "02-progress-line-en-1366");
      return {
        points: state.progress.points,
        behind: state.progress.behind,
        on: state.progress.on,
        ahead: state.progress.ahead,
        stroke: state.progress.color,
      };
    });

    await scenario("03", "Data Date style, thickness and colour reach the drawn line", async () => {
      scheduleWrites.length = 0;
      await openBars(page);
      await applyBars(page, {
        "gantt.dataDateLine.visible": true,
        "gantt.dataDateLine.style": "dashed",
        "gantt.dataDateLine.thickness": 4,
        "gantt.dataDateLine.color": "#00aa55",
      }, "dashed line");
      let state = await overlayState(page);
      assert(state.line, "the dashed Data Date line disappeared");
      assert(state.line.className.includes("is-dashed"), `line class is ${state.line.className}`);
      assert(state.line.colorVariable === "#00aa55", `line colour is ${state.line.colorVariable}`);
      const dashedWidth = state.line.borderLeftWidth === "1px" || state.line.borderRightWidth === "1px";
      assert(dashedWidth, `dashed line is ${state.line.borderLeftWidth}/${state.line.borderRightWidth}, not 1px`);
      const dashed = { width: state.line.borderLeftWidth, color: state.line.colorVariable, className: state.line.className };

      await openBars(page);
      await applyBars(page, {
        "gantt.dataDateLine.style": "solid",
        "gantt.dataDateLine.thickness": 4,
        "gantt.dataDateLine.color": "#112233",
      }, "solid line");
      state = await overlayState(page);
      assert(state.line, "the solid Data Date line disappeared");
      assert(state.line.className.includes("is-solid"), `line class is ${state.line.className}`);
      assert(state.line.width === "4px", `solid line width is ${state.line.width}`);
      assert(state.line.backgroundColor === "rgb(17, 34, 51)", `solid line colour is ${state.line.backgroundColor}`);
      assertNoScheduleWrites("editing the Data Date line");
      await capture(page, "03-data-date-solid-4px-en-1366");
      return {
        dashed,
        solidWidth: state.line.width,
        solidColor: state.line.backgroundColor,
      };
    });

    await scenario("04", "the overlay settings survive Save Layout and a full reload", async () => {
      scheduleWrites.length = 0;
      await openBars(page);
      await applyBars(page, {
        "gantt.dataDateLine.visible": true,
        "gantt.dataDateLine.style": "solid",
        "gantt.dataDateLine.thickness": 3,
        "gantt.dataDateLine.color": "#112233",
        "gantt.progressLine.visible": true,
        "gantt.progressLine.thickness": 2,
        "gantt.progressLine.color": "#ff8800",
      }, "persistable overlays");
      const saved = await saveLayout(page);
      const gantt = saved.body.metadata?.presentation?.gantt;
      assert(gantt?.dataDateLine?.thickness === 3, `saved data date thickness is ${gantt?.dataDateLine?.thickness}`);
      assert(gantt?.dataDateLine?.color === "#112233", `saved data date colour is ${gantt?.dataDateLine?.color}`);
      assert(gantt?.progressLine?.visible === true, "saved progress line is not visible");

      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "workspace after reload");
      await page.waitForSelector("#cp-gantt [data-gantt-scale]", "Gantt after reload");
      await sleep(1200);
      await waitForDataDate(page);
      const state = await overlayState(page);
      assert(state.line, "the saved Data Date line is not restored after reload");
      assert(state.line.width === "3px", `restored line width is ${state.line.width}`);
      assert(state.line.colorVariable === "#112233", `restored line colour is ${state.line.colorVariable}`);
      assert(state.progress, "the saved progress line is not restored after reload");
      assert(state.progress.dataDate === dataDate, "the restored progress line is not classified against the Data Date");
      assertNoScheduleWrites("restoring saved overlay settings");
      await capture(page, "04-overlays-restored-after-reload-en-1366");
      return {
        layoutRevision: saved.body.revision,
        savedGantt: gantt,
        restoredLineWidth: state.line.width,
        restoredProgressPoints: state.progress.points,
      };
    });

    await scenario("05", "baseline bars stay absent and honest without baseline dates", async () => {
      await openBars(page);
      const dialog = await readBarsDialog(page);
      assert(dialog, "the Bars dialog did not open");
      assert(dialog.baselineNote, "the Bars dialog does not explain the missing baseline dates");
      const state = await overlayState(page);
      assert(state.baselineBars === 0, `${state.baselineBars} baseline bars were invented`);
      await clickVisible(page, '[data-desktop-dialog="bars"] [data-dialog-cancel]', "Cancel");
      assertNoScheduleWrites("reviewing the baseline editor");
      return { baselineNote: dialog.baselineNote, baselineBars: state.baselineBars };
    });

    await scenario("06", "the overlays hold in fa RTL at 1280", async () => {
      await setViewport(page, 1280, 720);
      await setLanguage(page, "fa");
      await selectDayScale(page);
      const state = await overlayState(page);
      assert(state.dir === "rtl", `document direction is ${state.dir}`);
      assert(state.line, "the Data Date line is missing in RTL");
      assert(state.line.label === "تاریخ داده", `line label is ${JSON.stringify(state.line.label)}`);
      assert(state.line.date === dataDate, `RTL line date is ${state.line.date}`);
      const expectedLeft = expectedLeftPercent(state.ticks, dataDate);
      assert(expectedLeft !== null, "the RTL timescale has no tick around the Data Date");
      assert(Math.abs(state.line.leftPercent - expectedLeft) <= 0.6, `RTL line at ${state.line.leftPercent}% is not on the timescale position ${Math.round(expectedLeft * 10) / 10}%`);
      assert(state.line.withinBody, "the RTL Data Date line leaves the Gantt body");
      assert(state.progress?.points === 14, `RTL progress line joins ${state.progress?.points} points`);
      assert(state.overflow <= 0, `RTL page overflows by ${state.overflow}px`);
      await capture(page, "06-data-date-line-fa-rtl-1280");
      return {
        linePercent: state.line.leftPercent,
        expectedPercent: Math.round(expectedLeft * 10) / 10,
        label: state.line.label,
        overflow: state.overflow,
      };
    });

    await scenario("07", "the overlays hold at 1920 with critical bars intact", async () => {
      await setViewport(page, 1920, 1080);
      await setLanguage(page, "en");
      await selectDayScale(page);
      const state = await overlayState(page);
      assert(state.line, "the Data Date line is missing at 1920");
      assert(state.line.withinBody, "the Data Date line leaves the Gantt body at 1920");
      const expectedLeft = expectedLeftPercent(state.ticks, dataDate);
      assert(expectedLeft !== null, "the 1920 timescale has no tick around the Data Date");
      assert(Math.abs(state.line.leftPercent - expectedLeft) <= 0.6, `1920 line at ${state.line.leftPercent}% is not on the timescale position ${Math.round(expectedLeft * 10) / 10}%`);
      assert(state.progress?.points === 14, `1920 progress line joins ${state.progress?.points} points`);
      assert(state.criticalBars > 0, "critical bars disappeared at 1920");
      assert(state.overflow <= 0, `1920 page overflows by ${state.overflow}px`);
      await capture(page, "07-data-date-line-and-progress-en-1920");
      return {
        linePercent: state.line.leftPercent,
        expectedPercent: Math.round(expectedLeft * 10) / 10,
        criticalBars: state.criticalBars,
        overflow: state.overflow,
      };
    });
  } finally {
    writeReport();
    await chrome.stop();
  }

  const failed = scenarios.filter((entry) => entry.status !== "pass");
  log(`\n${scenarios.length - failed.length}/${scenarios.length} scenarios passed`);
  if (failed.length) process.exitCode = 1;
}

main().catch((error) => {
  process.stderr.write(`\nFAILED: ${error && error.stack ? error.stack : error}\n`);
  process.exitCode = 1;
});
