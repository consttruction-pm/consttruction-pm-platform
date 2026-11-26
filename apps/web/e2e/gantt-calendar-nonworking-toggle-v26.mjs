#!/usr/bin/env node
/**
 * Browser E2E for the Bars dialog "Show calendar non-working time" switch.
 *
 * Proves against the real local full-stack preview (real WSGI runtime, real
 * SQLite store, real Shared Core calendar projection) that:
 * - the control lives inside the real Bars dialog (Bar Styles) Gantt options;
 * - it is checked by default for a project whose saved layout has no key;
 * - turning it off removes only the calendar non-working band layer, leaving
 *   activity bars, baseline/progress bars, relationship lines, WBS bands,
 *   table rows and the axis byte-for-byte identical;
 * - the choice is persisted with the saved layout (survives a reload even with
 *   browser-local preferences cleared), and turning it back on restores the
 *   exact same band list;
 * - no schedule snapshot, project revision or calendar day-facts projection
 *   changes, and the page never reloads to apply the switch.
 *
 * No fixture is injected into the page and no API is mocked.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4212 node e2e/gantt-calendar-nonworking-toggle-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4212";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-26";
const outDir = join(artifactsDir, "gantt-calendar-nonworking-toggle-v26");
const evidenceDir = join(
  artifactsDir,
  "..",
  "..",
  "..",
  "..",
  "docs",
  "workspace",
  "evidence",
  `gantt-calendar-nonworking-toggle-v26-${evidenceDate}`,
);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const TENANT = "cubi-preview-tenant";
const CAL_ID = "CUBI-RPS-CAL";
const CAL_VERSION = "1";
const APP_URL = `${baseUrl}/app?project=${PROJECT}&view=live`;
const LAYOUT_PATH = `/api/projects/${PROJECT}/p6/layouts/project/activity`;
const VIEWPORTS = [
  { width: 1280, height: 800 },
  { width: 1440, height: 900 },
  { width: 1920, height: 1080 },
];

let revision = 7;
const scenarios = [];
const screenshots = [];
const exceptions = [];
const consoleErrors = [];
const apiFailures = [];

function log(message) {
  process.stdout.write(`${message}\n`);
}

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

function record(id, name, status, details = {}) {
  scenarios.push({ ...details, id, name, status, at: new Date().toISOString() });
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
  const file = `gantt-calendar-nonworking-toggle-v26/${name}.png`;
  await page.screenshot(file);
  copyFileSync(join(artifactsDir, file), join(evidenceDir, `${name}.png`));
  screenshots.push(`${name}.png`);
  return file;
}

async function api(page, method, path, body) {
  return page.evaluate(
    `(async () => {
      const response = await fetch(${JSON.stringify(path)}, {
        method: ${JSON.stringify(method)},
        headers: {
          "Content-Type": "application/json",
          "X-Tenant-Id": ${JSON.stringify(TENANT)},
          "X-Project-Id": ${JSON.stringify(PROJECT)},
          "X-Project-Revision": String(${revision}),
        },
        ${body === undefined ? "" : `body: JSON.stringify(${JSON.stringify(body)}),`}
      });
      let payload = null;
      try { payload = await response.json(); } catch { payload = null; }
      return { status: response.status, body: payload };
    })()`,
    { awaitPromise: true },
  );
}

async function readLayout(page) {
  const result = await api(page, "GET", LAYOUT_PATH);
  assert(result.status === 200, `layout read status ${result.status}: ${JSON.stringify(result.body)}`);
  return result.body;
}

async function readProject(page) {
  const result = await api(page, "GET", `/api/projects/${PROJECT}`);
  assert(result.status === 200, `project read status ${result.status}`);
  return result.body.project;
}

async function readDayFacts(page) {
  const result = await api(
    page,
    "GET",
    `/api/projects/${PROJECT}/p6/calendars/${encodeURIComponent(CAL_ID)}/${CAL_VERSION}/day-facts`,
  );
  assert(result.status === 200, `day-facts read status ${result.status}`);
  return result.body.overrides;
}

function shownValue(layout) {
  return layout?.metadata?.presentation?.gantt?.showCalendarNonWorkingTime;
}

async function waitForShownValue(page, expected, previousRevision, label) {
  const deadline = Date.now() + 15000;
  let last = null;
  while (Date.now() < deadline) {
    last = await readLayout(page);
    if (shownValue(last) === expected && last.revision > previousRevision) return last;
    await sleep(200);
  }
  throw new Error(
    `LAYOUT_TIMEOUT: ${label}: value ${String(shownValue(last))} revision ${last?.revision} (expected ${expected} > ${previousRevision})`,
  );
}

const factsExpression = `(() => {
  const round = (value) => Math.round(value * 10) / 10;
  // Measure against the content track so page scroll (which the modal can
  // disturb) never changes the geometry signature.
  const track = document.querySelector("#cp-gantt .cp-gantt-track");
  const origin = track ? track.getBoundingClientRect() : { left: 0, top: 0 };
  const bars = [...document.querySelectorAll("#cp-gantt [data-gantt-bar-kind]")].map((bar) => {
    const rect = bar.getBoundingClientRect();
    return {
      kind: bar.dataset.ganttBarKind,
      row: bar.dataset.ganttBarRow ?? null,
      primary: bar.dataset.ganttBarPrimary === "true",
      x: round(rect.left - origin.left),
      y: round(rect.top - origin.top),
      w: round(rect.width),
      h: round(rect.height),
    };
  });
  const links = [...document.querySelectorAll("#cp-gantt [data-gantt-link]")].map((link) => {
    const rect = link.getBoundingClientRect();
    return { id: link.dataset.ganttLink, x: round(rect.left - origin.left), y: round(rect.top - origin.top), w: round(rect.width), h: round(rect.height) };
  });
  const bands = [...document.querySelectorAll("#cp-gantt [data-gantt-nonworking]")].map((band) => ({
    kind: band.dataset.ganttNonworking,
    from: band.dataset.nonworkingFrom,
    to: band.dataset.nonworkingTo,
    days: Number(band.dataset.nonworkingDays),
  }));
  return {
    bands,
    bandCount: bands.length,
    rows: document.querySelectorAll("#cp-gantt [data-gantt-activity-id]").length,
    tableRows: document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]").length,
    wbsBands: document.querySelectorAll("#cp-activity-grid .cp-p6-wbs-band, #cp-activity-grid [data-wbs-band]").length,
    groups: document.querySelectorAll("#cp-gantt .cp-gantt-group-row").length,
    bars,
    links,
    axis: Boolean(document.querySelector("#cp-gantt .cp-gantt-axis")),
    direction: document.documentElement.dir || getComputedStyle(document.documentElement).direction,
    lang: document.documentElement.lang || null,
    viewport: { width: window.innerWidth, height: window.innerHeight },
    scrollWidth: document.documentElement.scrollWidth,
    contentWidth: (() => {
      const board = document.querySelector("#cp-gantt .cp-gantt-board");
      return board ? Number.parseFloat(getComputedStyle(board).getPropertyValue("--cp-gantt-content-width")) : 0;
    })(),
  };
})()`;

async function chartFacts(page) {
  return page.evaluate(factsExpression);
}

function geometry(facts) {
  return {
    rows: facts.rows,
    tableRows: facts.tableRows,
    groups: facts.groups,
    wbsBands: facts.wbsBands,
    axis: facts.axis,
    bars: facts.bars,
    links: facts.links,
  };
}

function diffGeometry(before, after) {
  const problems = [];
  for (const key of ["rows", "tableRows", "groups", "wbsBands", "axis"]) {
    if (before[key] !== after[key]) problems.push(`${key} ${JSON.stringify(before[key])} -> ${JSON.stringify(after[key])}`);
  }
  if (before.bars.length !== after.bars.length) problems.push(`bars ${before.bars.length} -> ${after.bars.length}`);
  else {
    const mismatch = before.bars.findIndex((bar, index) => JSON.stringify(bar) !== JSON.stringify(after.bars[index]));
    if (mismatch !== -1) {
      problems.push(
        `bar ${mismatch} changed: ${JSON.stringify(before.bars[mismatch])} -> ${JSON.stringify(after.bars[mismatch])}`,
      );
    }
  }
  if (before.links.length !== after.links.length) problems.push(`links ${before.links.length} -> ${after.links.length}`);
  else {
    const mismatch = before.links.findIndex((link, index) => JSON.stringify(link) !== JSON.stringify(after.links[index]));
    if (mismatch !== -1) {
      problems.push(
        `link ${mismatch} changed: ${JSON.stringify(before.links[mismatch])} -> ${JSON.stringify(after.links[mismatch])}`,
      );
    }
  }
  return problems;
}

async function setViewport(page, viewport) {
  await page.cdp.send("Emulation.setDeviceMetricsOverride", {
    width: viewport.width,
    height: viewport.height,
    deviceScaleFactor: 1,
    mobile: false,
  });
  await sleep(450);
}

async function setLanguage(page, locale) {
  const changed = await page.evaluate(`(() => {
    const select = document.querySelector("[data-workspace-language]");
    if (!select) return false;
    if (select.value === ${JSON.stringify(locale)}) return true;
    select.value = ${JSON.stringify(locale)};
    if (select.value !== ${JSON.stringify(locale)}) return false;
    select.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  assert(changed, `language selector did not accept ${locale}`);
  await sleep(950);
  await page.waitForSelector("#cp-gantt [data-gantt-activity-id]", "gantt rows after language change");
}

async function openBarsDialog(page) {
  const clicked = await page.evaluate(`(() => {
    const element = [...document.querySelectorAll('[data-desktop-command="dialog.bars"]')].find(
      (item) => item.getClientRects().length > 0,
    );
    if (!element || element.disabled) return false;
    element.click();
    return true;
  })()`);
  assert(clicked, "Bars dialog command is not clickable");
  await page.waitForSelector('dialog[data-desktop-dialog="bars"][open]', "Bars dialog open", 8000);
  await sleep(300);
}

async function focusToggle(page) {
  const box = await page.evaluate(`(() => {
    const dialog = document.querySelector('dialog[data-desktop-dialog="bars"][open]');
    if (!dialog) return null;
    const fieldset = dialog.querySelector("[data-gantt-options]");
    const input = dialog.querySelector('[name="gantt.showCalendarNonWorkingTime"]');
    if (!fieldset || !input) return null;
    // The dialog itself is the scroll container. Align the Gantt options
    // legend to the top so the screenshot frames the control, not a half row
    // from the bar-style list.
    const dialogRect = dialog.getBoundingClientRect();
    const fieldsetRect = fieldset.getBoundingClientRect();
    dialog.scrollTop += fieldsetRect.top - dialogRect.top - 8;
    const rect = input.getBoundingClientRect();
    const label = input.closest("label");
    return {
      checked: input.checked,
      visible: rect.width > 0 && rect.height > 0 && rect.top >= 0 && rect.bottom <= window.innerHeight,
      label: (label?.textContent || "").trim(),
      dialogTitle: (dialog.querySelector("h2")?.textContent || "").trim(),
      perBarNecking: Boolean(dialog.querySelector('[name^="bar."][name$=".necking"]')),
      hasNote: /Calendar non-working time shades/i.test(dialog.textContent || ""),
    };
  })()`);
  assert(box, "calendar non-working switch is not inside the open Bars dialog");
  await sleep(250);
  return box;
}

async function setToggle(page, checked) {
  const applied = await page.evaluate(`(() => {
    const dialog = document.querySelector('dialog[data-desktop-dialog="bars"][open]');
    if (!dialog) return false;
    const form = dialog.querySelector('[data-dialog-form="bars"]');
    const input = form.querySelector('[name="gantt.showCalendarNonWorkingTime"]');
    if (!input) return false;
    input.checked = ${checked ? "true" : "false"};
    return input.checked === ${checked ? "true" : "false"};
  })()`);
  assert(applied, `could not set the switch to ${checked}`);
}

async function cancelDialog(page) {
  const closed = await page.evaluate(`(() => {
    const dialog = document.querySelector('dialog[data-desktop-dialog="bars"][open]');
    if (!dialog) return false;
    const cancel = dialog.querySelector("[data-dialog-cancel]");
    if (!cancel) return false;
    cancel.click();
    return true;
  })()`);
  assert(closed, "Bars dialog cancel is missing");
  await page.waitFor(
    `!document.querySelector('dialog[data-desktop-dialog="bars"]')?.open`,
    "Bars dialog closed by Cancel",
    6000,
  );
  await sleep(250);
}

async function applyDialog(page, mutate, expected, label) {
  const before = await readLayout(page);
  await openBarsDialog(page);
  await page.evaluate(`(() => {
    const dialog = document.querySelector('dialog[data-desktop-dialog="bars"][open]');
    const form = dialog.querySelector('[data-dialog-form="bars"]');
    ${mutate}
    form.querySelector('[data-dialog-ok]').click();
    return true;
  })()`);
  await page.waitFor(
    `!document.querySelector('dialog[data-desktop-dialog="bars"]')?.open`,
    `${label} Bars dialog closed`,
    8000,
  );
  await sleep(500);
  await page.waitForSelector("#cp-gantt [data-gantt-activity-id]", "gantt rows after Bars apply");
  if (expected !== undefined) await waitForShownValue(page, expected, before.revision, label);
  await sleep(350);
  return { beforeRevision: before.revision, beforeValue: shownValue(before) };
}

async function reloadApp(page, locale) {
  await page.navigate(APP_URL, "#cp-activity-grid tbody tr[data-activity-id]", "activities window");
  await page.waitForSelector("#cp-gantt [data-gantt-activity-id]", "gantt rows after reload");
  if (locale) await setLanguage(page, locale);
  await sleep(900);
}

async function main() {
  const health = await waitForHttp(`${baseUrl}/preview/health`, 30000);
  assert(health.status === "ok" || health.status === 200, `preview health ${health.status}`);

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
    contract: "cubi-gantt-calendar-nonworking-toggle-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    capturedAt: new Date().toISOString(),
    project: PROJECT,
    calendar: { id: CAL_ID, version: CAL_VERSION },
    help: {
      product: "Oracle Primavera P6 Professional 26",
      topic: "Change a Gantt Chart bar's settings",
      topicFile: "change_a_gantt_chart_bar_s_settings.htm",
      path: "Customizing Activity Layouts > Gantt Chart",
      url: "https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm",
      perBarSetting: "Calendar nonwork time",
      note:
        "P6 v26 Help documents Calendar nonwork time as a per-bar Bar Settings option that necks the selected bar. The CUBI band-visibility switch is a documented CUBI display-layer extension; the per-bar necking control remains separately available in each bar style.",
    },
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
  };

  try {
    await setViewport(page, VIEWPORTS[0]);
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "form", "login");
    await page.evaluate(`(() => {
      const button = [...document.querySelectorAll("form button")].find((item) => (item.textContent || "").trim().startsWith("Planner"));
      if (!button) return false;
      button.click();
      return true;
    })()`);
    await page.waitForSelector(`[data-project-id="${PROJECT}"]`, "project selection");
    await page.click(`[data-project-id="${PROJECT}"]`);
    await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
    await sleep(1400);
    await page.waitForSelector("#cp-gantt [data-gantt-activity-id]", "gantt rows");

    const meta = await readProject(page);
    revision = meta.revision;
    assert(meta.primary_calendar_id === CAL_ID, `primary calendar ${meta.primary_calendar_id}`);

    const initialLayout = await readLayout(page);
    const initialDayFacts = await readDayFacts(page);
    const initialFacts = await chartFacts(page);

    await scenario("01", "کنترل در دیالوگ Bars قرار دارد و برای چیدمان بدون کلید، پیش‌فرض روشن است", async () => {
      const carried = initialLayout.metadata?.presentation?.gantt?.showCalendarNonWorkingTime;
      // A pristine layout has no key at all; a rerun may already carry the
      // documented default. Anything but "absent or true" is a regression.
      assert(
        carried === undefined || carried === true,
        `saved layout carries an unexpected value: ${JSON.stringify(carried)}`,
      );
      assert(initialFacts.bandCount > 0, "the seeded calendar must paint non-working bands");
      await openBarsDialog(page);
      const box = await focusToggle(page);
      assert(box.dialogTitle.length > 0, "Bars dialog has no title");
      assert(box.checked === true, "the switch is not checked by default");
      assert(/calendar non-working time/i.test(box.label), `unexpected label: ${box.label}`);
      assert(box.perBarNecking === true, "the documented per-bar Calendar nonwork time control is missing");
      assert(box.hasNote === true, "the Bars dialog note does not explain the display-only semantics");
      await capture(page, `dialog-default-on-${VIEWPORTS[0].width}x${VIEWPORTS[0].height}-en`);
      await cancelDialog(page);
      const afterCancel = await chartFacts(page);
      assert(afterCancel.bandCount === initialFacts.bandCount, "Cancel changed the chart");
      const layoutAfterCancel = await readLayout(page);
      assert(layoutAfterCancel.revision === initialLayout.revision, "Cancel wrote the layout");
      return {
        layoutRevision: initialLayout.revision,
        bands: initialFacts.bandCount,
        bandKinds: [...new Set(initialFacts.bands.map((band) => band.kind))],
        label: box.label,
      };
    });

    for (const viewport of VIEWPORTS) {
      await setViewport(page, viewport);
      for (const locale of ["en", "fa"]) {
        const cell = `${viewport.width}x${viewport.height}-${locale}`;
        log(`\n== ${cell} ==`);
        await setLanguage(page, locale);
        const factsOn = await chartFacts(page);
        assert(factsOn.viewport.width === viewport.width, `${cell}: viewport ${factsOn.viewport.width}`);
        assert(factsOn.bandCount > 0, `${cell}: non-working bands were not painted in the on state`);
        assert(factsOn.scrollWidth <= viewport.width + 1, `${cell}: page overflows horizontally`);
        if (locale === "fa") {
          assert(factsOn.direction === "rtl", `${cell}: document direction is ${factsOn.direction}`);
        } else {
          assert(factsOn.direction !== "rtl", `${cell}: document direction is ${factsOn.direction}`);
        }
        await capture(page, `chart-on-${cell}`);

        await openBarsDialog(page);
        const boxOn = await focusToggle(page);
        assert(boxOn.checked === true, `${cell}: switch is not checked in the on state`);
        if (locale === "fa") {
          assert(/زمان غیرکاری تقویم/.test(boxOn.label), `${cell}: Persian label missing: ${boxOn.label}`);
        }
        assert(boxOn.visible, `${cell}: the switch is not visible in the dialog viewport`);
        await capture(page, `dialog-on-${cell}`);
        await cancelDialog(page);

        // Screenshot the control while unchecked, then apply the change.
        await openBarsDialog(page);
        await focusToggle(page);
        await setToggle(page, false);
        const boxOff = await focusToggle(page);
        assert(boxOff.checked === false, `${cell}: the switch did not uncheck`);
        await capture(page, `dialog-off-${cell}`);

        const marker = await page.evaluate(`(() => { window.__qoderToggleMarker = "alive"; return window.__qoderToggleMarker; })()`);
        const beforeProject = await readProject(page);
        const beforeFacts = await readDayFacts(page);
        const beforeLayout = await readLayout(page);
        await page.evaluate(`(() => {
          document.querySelector('dialog[data-desktop-dialog="bars"][open]')
            .querySelector('[data-dialog-form="bars"]')
            .querySelector('[data-dialog-ok]').click();
          return true;
        })()`);
        await page.waitFor(
          `!document.querySelector('dialog[data-desktop-dialog="bars"]')?.open`,
          `${cell}: Bars dialog closed after hiding the layer`,
          8000,
        );
        await sleep(600);
        await page.waitForSelector("#cp-gantt [data-gantt-activity-id]", "gantt rows after hide");
        await waitForShownValue(page, false, beforeLayout.revision, `${cell}: hide`);
        await sleep(350);

        const factsOff = await chartFacts(page);
        const afterProject = await readProject(page);
        const afterFacts = await readDayFacts(page);
        const problems = diffGeometry(geometry(factsOn), geometry(factsOff));
        assert(factsOff.bandCount === 0, `${cell}: ${factsOff.bandCount} non-working bands remain after hiding`);
        assert(problems.length === 0, `${cell}: hiding the layer disturbed the chart: ${problems.join("; ")}`);
        assert(
          afterProject.revision === beforeProject.revision,
          `${cell}: project revision changed ${beforeProject.revision} -> ${afterProject.revision}`,
        );
        assert(
          JSON.stringify(afterFacts) === JSON.stringify(beforeFacts),
          `${cell}: calendar day-facts projection changed`,
        );
        const markerAfter = await page.evaluate("window.__qoderToggleMarker");
        assert(markerAfter === "alive", `${cell}: the page was reloaded to apply the switch`);
        assert(
          factsOff.axis && factsOff.bars.length === factsOn.bars.length && factsOff.links.length === factsOn.links.length,
          `${cell}: bars/lines/axis changed`,
        );
        await capture(page, `chart-off-${cell}`);
        record(`hide-${cell}`, `${cell}: خاموش‌کردن سایه، فقط لایهٔ باند را حذف می‌کند`, "pass", {
          bands: { on: factsOn.bandCount, off: factsOff.bandCount },
          bars: factsOff.bars.length,
          links: factsOff.links.length,
          projectRevision: afterProject.revision,
          dayFacts: afterFacts.length,
        });

        if (locale === "en") {
          // Reopen in a fresh browser state: clear local preferences so the
          // restore must come from the saved project layout, not localStorage.
          await page.evaluate("localStorage.clear()");
          await reloadApp(page, locale);
          const reloaded = await chartFacts(page);
          const reloadLayout = await readLayout(page);
          assert(reloaded.bandCount === 0, `${cell}: the off state did not survive a reload (${reloaded.bandCount})`);
          assert(shownValue(reloadLayout) === false, `${cell}: the saved layout lost the off state`);
          await openBarsDialog(page);
          const boxReload = await focusToggle(page);
          assert(boxReload.checked === false, `${cell}: the switch is not checked off after reload`);
          await capture(page, `dialog-reload-off-${cell}`);
          await cancelDialog(page);
          record(`persist-off-${cell}`, `${cell}: وضعیت خاموش در چیدمان ذخیره‌شده می‌ماند و پس از بازخوانی بازمی‌گردد`, "pass", {
            reloadedBands: reloaded.bandCount,
            layoutRevision: reloadLayout.revision,
          });
        }

        // Restore the documented default and prove the exact band list returns.
        await applyDialog(
          page,
          `form.querySelector('[name="gantt.showCalendarNonWorkingTime"]').checked = true;`,
          true,
          `${cell}: restore`,
        );
        const factsRestored = await chartFacts(page);
        assert(factsRestored.bandCount === factsOn.bandCount, `${cell}: restoring painted ${factsRestored.bandCount} of ${factsOn.bandCount} bands`);
        assert(
          JSON.stringify(factsRestored.bands) === JSON.stringify(factsOn.bands),
          `${cell}: restored band list differs from the original`,
        );
        assert(diffGeometry(geometry(factsOn), geometry(factsRestored)).length === 0, `${cell}: restoring changed the chart`);
        assert(factsRestored.direction === factsOn.direction, `${cell}: direction changed after restore`);
        await capture(page, `chart-on-restored-${cell}`);

        if (locale === "en") {
          await page.evaluate("localStorage.clear()");
          await reloadApp(page, locale);
          const reloadOn = await chartFacts(page);
          const reloadOnLayout = await readLayout(page);
          assert(reloadOn.bandCount === factsOn.bandCount, `${cell}: the on state did not survive a reload (${reloadOn.bandCount})`);
          assert(shownValue(reloadOnLayout) === true, `${cell}: the saved layout lost the on state`);
          await openBarsDialog(page);
          const boxOnReload = await focusToggle(page);
          assert(boxOnReload.checked === true, `${cell}: the switch is not checked on after reload`);
          await capture(page, `dialog-reload-on-${cell}`);
          await cancelDialog(page);
          record(`persist-on-${cell}`, `${cell}: وضعیت روشن نیز پس از بازخوانی بازمی‌گردد`, "pass", {
            reloadedBands: reloadOn.bandCount,
            layoutRevision: reloadOnLayout.revision,
          });
        }
      }
    }

    await scenario("02", "یکپارچگی: بدون استثنا، خطای کنسول، پاسخ 5xx یا تغییر دادهٔ زمان‌بندی", async () => {
      const layout = await readLayout(page);
      const facts = await readDayFacts(page);
      const project = await readProject(page);
      assert(exceptions.length === 0, `runtime exceptions: ${JSON.stringify(exceptions)}`);
      assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors)}`);
      assert(apiFailures.length === 0, `api failures: ${JSON.stringify(apiFailures)}`);
      assert(JSON.stringify(facts) === JSON.stringify(initialDayFacts), "calendar projection drifted across the run");
      assert(project.revision === revision, `project revision drifted ${revision} -> ${project.revision}`);
      assert(shownValue(layout) === true, "the run did not finish in the documented default state");
      return {
        exceptions: exceptions.length,
        consoleErrors: consoleErrors.length,
        apiFailures: apiFailures.length,
        projectRevision: project.revision,
        finalBands: (await chartFacts(page)).bandCount,
        layoutRevision: layout.revision,
      };
    });
  } finally {
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(evidenceDir, "report.json"), JSON.stringify(report, null, 2));
    writeFileSync(
      join(outDir, "summary.md"),
      [
        "# Bars dialog — calendar non-working time visibility (browser evidence)",
        "",
        `- Contract: ${report.contract}`,
        `- Preview: ${baseUrl}`,
        `- Git HEAD: ${report.gitHead}`,
        `- Project: ${PROJECT}`,
        `- Calendar: ${CAL_ID}@${CAL_VERSION}`,
        `- Help: ${report.help.topic} (${report.help.topicFile})`,
        "",
        ...scenarios.map((entry) => `- ${entry.status.toUpperCase()} — ${entry.id}. ${entry.name}`),
        "",
        `Screenshots: ${screenshots.length}`,
        "",
      ].join("\n"),
    );
    writeFileSync(join(evidenceDir, "summary.md"), [
      "# Bars dialog — calendar non-working time visibility (browser evidence)",
      "",
      `- Contract: ${report.contract}`,
      `- Preview: ${baseUrl}`,
      `- Git HEAD: ${report.gitHead}`,
      "",
      ...scenarios.map((entry) => `- ${entry.status.toUpperCase()} — ${entry.id}. ${entry.name}`),
      "",
      `Screenshots: ${screenshots.length}`,
      "",
    ].join("\n"));
    page.cdp.close();
    chrome.cdp.close();
    await chrome.stop();
  }

  log(`\nReport: ${join(outDir, "report.json")}`);
  if (scenarios.some((entry) => entry.status !== "pass")) process.exitCode = 1;
}

main().catch((error) => {
  process.stderr.write(`${error && error.stack ? error.stack : error}\n`);
  process.exitCode = 1;
});
