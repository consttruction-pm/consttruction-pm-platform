#!/usr/bin/env node
/**
 * Version 26 layout-dialog and line-number acceptance (ACT-006).
 *
 * Proves in the real Preview runtime and real Chrome that:
 *   - View > Line Numbers renders a `#` column at the far left over the
 *     activity rows, renumbers after collapsing/expanding grouping bands, is
 *     reachable from the View menu, the grid context menu and the Layout
 *     toolbar, and is published with the saved layout;
 *   - Table Font and Row honours the Version 26 row-height modes: Keep Current
 *     and Optimize by content lock and ignore the height field, Fixed height
 *     for all rows applies it, and Cancel never writes;
 *   - User Preferences shares that table block, toggles line numbers, and its
 *     "Reset band format" action resets the band only instead of committing
 *     unrelated table edits typed in the same form;
 *   - both dialogs localise in fa/RTL at 1280x720 without overflow and fit at
 *     en/LTR 1920x1080.
 *
 * Help authority: P6 Professional v26 HTML Help — "Add line numbers"
 * (51388.htm), "Change Activity Table font, color, and row height"
 * (change_activity_table_font_color_and_row_height.htm) and "Define user
 * preferences" (define_user_preferences.htm).
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4233 node e2e/table-layout-line-numbers-prefs-v26.mjs
 *   (use a brand-new --database file; saved layouts survive --reset)
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4233";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-27";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "table-layout-line-numbers-prefs-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `table-layout-line-numbers-prefs-v26-${evidenceDate}`);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const scenarios = [];
const screenshots = [];
const knownGaps = [
  {
    id: "row-line-limit",
    detail: "Version 26 documents an optional 'Do not exceed X lines per row' limit in Optimize by content. CUBI optimises by content without a line cap; recorded in the compliance matrix as a remaining gap.",
    owner: "backlog",
  },
  {
    id: "group-band-numbering",
    detail: "Line numbers count activity rows; grouping band rows show an empty number cell. Version 26 Help says numbering applies to visible rows and does not state how bands are numbered, so this is recorded as a CUBI presentation choice.",
    owner: "documented",
  },
  {
    id: "preferences-scope",
    detail: "Version 26 User Preferences also carries Time Units, Dates, Currency, Email, Assistance, Application, Password, Resource Analysis, Calculations, Startup Filters and Personal Information. CUBI User Preferences is the layout preference set (table and WBS band) for this web runtime; account-level formats live outside the Activities window.",
    owner: "documented",
  },
];

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
  const file = `table-layout-line-numbers-prefs-v26/${name}.png`;
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

const fontDialog = "dialog[data-desktop-dialog=font-row]";
const prefsDialog = "dialog[data-desktop-dialog=user-preferences]";

async function openCommand(page, command) {
  const clicked = await page.evaluate(`(() => {
    const element = [...document.querySelectorAll('[data-desktop-command=${JSON.stringify(command)}]')]
      .find((item) => item.getClientRects().length > 0 && !item.disabled);
    if (!element) return false;
    element.click();
    return true;
  })()`);
  assert(clicked, `command ${command} is not reachable from the menu or toolbar`);
}

async function openFontRow(page) {
  await openCommand(page, "dialog.font-row");
  await page.waitForSelector(`${fontDialog}[open]`, "table font dialog", 8000);
  await sleep(250);
}

async function openPreferences(page) {
  await openCommand(page, "dialog.user-preferences");
  await page.waitForSelector(`${prefsDialog}[open]`, "user preferences dialog", 8000);
  await sleep(250);
}

async function dialogState(page, selector, names) {
  return page.evaluate(`(() => {
    const dialog = document.querySelector(${JSON.stringify(selector)});
    const out = { open: Boolean(dialog?.open), title: dialog?.querySelector("h2")?.textContent?.trim() ?? "" };
    for (const name of ${JSON.stringify(names)}) {
      const any = dialog?.querySelector('[name="' + name + '"]');
      const control = any && any.type === "radio"
        ? dialog.querySelector('[name="' + name + '"]:checked')
        : any;
      if (!control) { out[name] = null; continue; }
      out[name] = control.type === "checkbox" ? control.checked : control.value;
      out[name + "Disabled"] = Boolean(control.disabled);
    }
    out.overflow = document.documentElement.scrollWidth - document.documentElement.clientWidth;
    return out;
  })()`);
}

async function setControl(page, selector, controlSelector, value, kind = "select") {
  const changed = await page.evaluate(`(() => {
    const dialog = document.querySelector(${JSON.stringify(selector)});
    const control = dialog ? dialog.querySelector(${JSON.stringify(controlSelector)}) : null;
    if (!control) return false;
    ${kind === "check"
      ? "control.checked = " + JSON.stringify(Boolean(value)) + ";"
      : "control.value = " + JSON.stringify(String(value)) + "; if (control.value !== " + JSON.stringify(String(value)) + ") return false;"}
    control.dispatchEvent(new Event("change", { bubbles: true }));
    control.dispatchEvent(new Event("input", { bubbles: true }));
    return true;
  })()`);
  assert(changed, `${controlSelector} inside ${selector} did not accept ${value}`);
  await sleep(150);
}

async function submit(page, selector, buttonSelector = "[data-dialog-ok]") {
  const clicked = await page.evaluate(`(() => {
    const dialog = document.querySelector(${JSON.stringify(selector)});
    const button = dialog ? dialog.querySelector(${JSON.stringify(buttonSelector)}) : null;
    if (!button || button.disabled) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `${buttonSelector} in ${selector} is missing`);
  await page.waitFor(`!document.querySelector(${JSON.stringify(selector)})?.open`, "dialog closed", 8000);
  await sleep(900);
}

async function cancel(page, selector) {
  const clicked = await page.evaluate(`(() => {
    const dialog = document.querySelector(${JSON.stringify(selector)});
    const button = dialog ? dialog.querySelector("[data-dialog-cancel]") : null;
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `Cancel in ${selector} is missing`);
  await page.waitFor(`!document.querySelector(${JSON.stringify(selector)})?.open`, "dialog closed", 8000);
  await sleep(600);
}

async function gridState(page) {
  return page.evaluate(`(() => {
    const head = document.querySelector("#cp-activity-grid thead tr");
    const first = head ? head.firstElementChild : null;
    const rows = [...document.querySelectorAll("#cp-activity-grid tbody tr")];
    const activityRows = rows.filter((row) => row.dataset.activityId);
    const bandRows = rows.filter((row) => row.className.includes("cp-p6-wbs-band"));
    const numbered = activityRows.map((row) => {
      const cell = row.querySelector("td.cp-p6-line-number");
      return cell ? cell.textContent.trim() : null;
    });
    const bandNumbers = bandRows.map((row) => row.querySelector("td.cp-p6-line-number")?.textContent.trim() ?? null);
    const lineHeader = document.querySelector("#cp-activity-grid thead th.cp-p6-line-number");
    const root = getComputedStyle(document.documentElement);
    const firstRow = activityRows[0] ?? null;
    return {
      header: first ? first.textContent.trim() : "",
      headerIsLineNumber: Boolean(first && first.classList.contains("cp-p6-line-number")),
      headerColumnId: first ? first.getAttribute("data-column-id") : null,
      headerResizable: Boolean(lineHeader && lineHeader.querySelector("[data-column-resize]")),
      lineHeaderWidth: lineHeader ? Math.round(lineHeader.getBoundingClientRect().width) : 0,
      numbered,
      bandNumbers,
      activityCount: activityRows.length,
      bandCount: bandRows.length,
      rowMode: document.documentElement.dataset.tableRowMode ?? "",
      rootRow: root.getPropertyValue("--cp-p6-row-height").trim(),
      rootSize: root.getPropertyValue("--cp-p6-font-size").trim(),
      renderedRow: firstRow ? Math.round(firstRow.getBoundingClientRect().height) : 0,
      gridCount: document.querySelectorAll("#cp-activity-grid").length,
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

async function waitForTable(page, predicate) {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    await sleep(200);
    for (const scope of ["project", "user"]) {
      const saved = await readLayout(page, "preview-rps-01", scope);
      if (saved.status !== 200 || !saved.body?.metadata?.presentation?.table) continue;
      if (predicate(saved.body.metadata.presentation.table)) return saved;
    }
  }
  return null;
}

function assertSequential(numbers, expectedCount, label) {
  assert(numbers.length === expectedCount, `${label}: ${numbers.length} numbered rows instead of ${expectedCount}`);
  numbers.forEach((value, index) => {
    assert(value === String(index + 1), `${label}: row ${index + 1} shows "${value}"`);
  });
}

async function toggleLineNumbersFromMenu(page) {
  await openCommand(page, "view.line-numbers");
  await sleep(900);
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
    contract: "cubi-table-layout-line-numbers-prefs-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    helpTopics: [
      "https://docs.oracle.com/cd/G48902_01/client_help/en_US/51388.htm",
      "https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_activity_table_font_color_and_row_height.htm",
      "https://docs.oracle.com/cd/G48902_01/client_help/en_US/define_user_preferences.htm",
    ],
    scenarios,
    screenshots,
    knownGaps,
    exceptions,
    consoleErrors,
    apiFailures,
  };

  function writeReport() {
    report.scenarios = scenarios;
    report.passed = scenarios.filter((entry) => entry.status === "pass").length;
    report.failed = scenarios.filter((entry) => entry.status === "fail").length;
    const json = JSON.stringify(report, null, 2);
    writeFileSync(join(outDir, "table-layout-line-numbers-prefs-v26.json"), json);
    writeFileSync(join(evidenceDir, "table-layout-line-numbers-prefs-v26.json"), json);
  }

  try {
    await setViewport(page, 1440, 900);
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
    await sleep(700);
    const hasPersonas = await page.evaluate('Boolean(document.querySelector(".persona"))');
    if (!hasPersonas) {
      await page.evaluate('fetch("/preview/logout", { method: "POST", redirect: "manual" }).then((response) => response.status)', { awaitPromise: true });
      await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, ".persona", "persona cards after sign out");
    }
    const adminClicked = await page.evaluate(`(() => {
      const button = document.querySelector('button[name="role"][value="admin"]');
      if (!button) return false;
      button.click();
      return true;
    })()`);
    assert(adminClicked, "admin login button is missing");
    await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
    await page.click('[data-project-id="preview-rps-01"]');
    await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
    await sleep(1500);

    await scenario("01", "View > Line Numbers adds a fixed # column that numbers visible activity rows", async () => {
      const initial = await gridState(page);
      assert(initial.headerIsLineNumber === false, "line numbers were on before the toggle");
      assert(initial.activityCount > 10, `only ${initial.activityCount} activity rows rendered`);
      await toggleLineNumbersFromMenu(page);
      const numbered = await gridState(page);
      assert(numbered.headerIsLineNumber, "the first header cell is not the line-number column");
      assert(numbered.header === "#", `line-number heading is "${numbered.header}"`);
      assert(numbered.headerColumnId === null, "the line-number column carries a movable column id");
      assert(numbered.headerResizable === false, "the line-number column can be resized or dragged");
      assert(numbered.lineHeaderWidth >= 30 && numbered.lineHeaderWidth <= 40, `line-number column is ${numbered.lineHeaderWidth}px`);
      assertSequential(numbered.numbered, numbered.activityCount, "initial numbering");
      assert(numbered.bandNumbers.every((value) => value === ""), `group band rows show numbers: ${JSON.stringify(numbered.bandNumbers)}`);
      assert(numbered.gridCount === 1, "the Activities window renders more than one activity grid");
      await capture(page, "01-line-numbers-en-1440");
      return { activityRows: numbered.activityCount, bands: numbered.bandCount, width: numbered.lineHeaderWidth };
    });

    await scenario("02", "collapsing and expanding a grouping band renumbers the visible rows", async () => {
      const before = await gridState(page);
      const collapsed = await page.evaluate(`(() => {
        const toggle = document.querySelector("#cp-activity-grid tbody tr.cp-p6-wbs-band [data-wbs-toggle]");
        if (!toggle) return false;
        toggle.click();
        return true;
      })()`);
      assert(collapsed, "the root WBS band has no collapse toggle");
      await sleep(900);
      const hidden = await gridState(page);
      assert(hidden.activityCount < before.activityCount, `collapse did not hide rows (${hidden.activityCount})`);
      assertSequential(hidden.numbered, hidden.activityCount, "collapsed numbering");
      await capture(page, "02-line-numbers-renumber-en-1440");
      const expanded = await page.evaluate(`(() => {
        const toggle = document.querySelector("#cp-activity-grid tbody tr.cp-p6-wbs-band [data-wbs-toggle]");
        if (!toggle) return false;
        toggle.click();
        return true;
      })()`);
      assert(expanded, "the root WBS band cannot be expanded again");
      await sleep(900);
      const restored = await gridState(page);
      assertSequential(restored.numbered, before.activityCount, "restored numbering");
      return { collapsed: hidden.activityCount, restored: restored.activityCount };
    });

    await scenario("03", "the context menu and toolbar toggle the same saved line-number state", async () => {
      const menuToggle = await page.evaluate(`(() => {
        const row = document.querySelector("#cp-activity-grid tbody tr[data-activity-id]");
        if (!row) return false;
        const cell = row.querySelector("td");
        const bounds = (cell ?? row).getBoundingClientRect();
        row.dispatchEvent(new MouseEvent("contextmenu", {
          bubbles: true,
          cancelable: true,
          clientX: Math.round(bounds.left + 20),
          clientY: Math.round(bounds.top + 8),
          button: 2,
        }));
        return true;
      })()`);
      assert(menuToggle, "the grid row is missing");
      await page.waitForSelector('[data-activity-menu-command="line-numbers"]', "context menu line numbers", 5000);
      const checked = await page.evaluate(`document.querySelector('[data-activity-menu-command="line-numbers"]')?.getAttribute("aria-checked")`);
      assert(checked === "true", `context menu does not show line numbers as checked (${checked})`);
      await page.evaluate(`document.querySelector('[data-activity-menu-command="line-numbers"]').click()`);
      await sleep(900);
      const off = await gridState(page);
      assert(off.headerIsLineNumber === false, "the context menu did not hide line numbers");

      await toggleLineNumbersFromMenu(page);
      const on = await gridState(page);
      assert(on.headerIsLineNumber, "the View menu did not restore line numbers");
      const saved = await waitForTable(page, (table) => table.lineNumbers === true);
      assert(saved, "line numbers were not published with the saved layout");

      await page.evaluate(`localStorage.clear()`);
      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "reload after line-number save");
      await sleep(1400);
      const reloaded = await gridState(page);
      assert(reloaded.headerIsLineNumber, "line numbers did not survive a reload from the saved layout");
      assertSequential(reloaded.numbered, reloaded.activityCount, "reload numbering");
      await capture(page, "03-line-numbers-context-toolbar-reload-en-1440");
      return { revision: saved.body?.revision, rows: reloaded.activityCount };
    });

    await scenario("04", "Table Font and Row applies a height only in Fixed mode and locks the field otherwise", async () => {
      const before = await gridState(page);
      assert(before.rowMode === "fixed", `saved row mode is ${before.rowMode}`);
      const baselineHeight = before.rootRow;
      await openFontRow(page);
      let state = await dialogState(page, fontDialog, ["rowHeightMode", "rowHeight"]);
      assert(state.rowHeightMode === "fixed", `dialog mode is ${state.rowHeightMode}`);
      assert(state.rowHeightDisabled === false, "the height field is locked in Fixed mode");
      await setControl(page, fontDialog, 'input[name="rowHeightMode"][value="keep"]', true, "check");
      state = await dialogState(page, fontDialog, ["rowHeightMode", "rowHeight"]);
      assert(state.rowHeightDisabled === true, "Keep Current leaves the height field editable");
      await capture(page, "04-row-height-keep-locked-en-1440");
      await page.evaluate(`(() => {
        const dialog = document.querySelector("${fontDialog}");
        const input = dialog.querySelector('input[name="rowHeight"]');
        input.removeAttribute("disabled");
        input.value = "40";
        input.dispatchEvent(new Event("input", { bubbles: true }));
      })()`);
      await submit(page, fontDialog);
      const kept = await gridState(page);
      assert(kept.rowMode === "keep", `Keep Current was not saved (${kept.rowMode})`);
      assert(kept.rootRow === baselineHeight, `Keep Current applied ${kept.rootRow} instead of ${baselineHeight}`);

      await openFontRow(page);
      const content = await dialogState(page, fontDialog, ["rowHeightMode", "rowHeight"]);
      assert(content.rowHeightMode === "keep", `reopened mode is ${content.rowHeightMode}`);
      assert(content.rowHeightDisabled === true, "the reopened height field is editable in Keep Current");
      await setControl(page, fontDialog, 'input[name="rowHeightMode"][value="content"]', true, "check");
      await page.evaluate(`(() => {
        const dialog = document.querySelector("${fontDialog}");
        const input = dialog.querySelector('input[name="rowHeight"]');
        input.removeAttribute("disabled");
        input.value = "34";
        input.dispatchEvent(new Event("input", { bubbles: true }));
      })()`);
      await submit(page, fontDialog);
      const sized = await gridState(page);
      assert(sized.rowMode === "content", `content mode was not saved (${sized.rowMode})`);
      assert(sized.rootRow === baselineHeight, `content mode applied ${sized.rootRow} instead of ${baselineHeight}`);

      await openFontRow(page);
      await setControl(page, fontDialog, 'input[name="rowHeightMode"][value="fixed"]', true, "check");
      const unlocked = await dialogState(page, fontDialog, ["rowHeightMode", "rowHeight"]);
      assert(unlocked.rowHeightDisabled === false, "Fixed mode does not unlock the height field");
      await setControl(page, fontDialog, 'input[name="rowHeight"]', "30");
      await submit(page, fontDialog);
      const fixed = await gridState(page);
      assert(fixed.rowMode === "fixed" && fixed.rootRow === "30px", `Fixed height saved ${fixed.rowMode}/${fixed.rootRow}`);
      assert(fixed.renderedRow >= 30 && fixed.renderedRow <= 34, `rendered row height is ${fixed.renderedRow}`);

      await openFontRow(page);
      await setControl(page, fontDialog, 'input[name="rowHeight"]', "40");
      await cancel(page, fontDialog);
      const cancelled = await gridState(page);
      assert(cancelled.rootRow === "30px", `Cancel wrote ${cancelled.rootRow}`);
      await capture(page, "04-row-height-modes-en-1440");
      return { baselineHeight, fixedHeight: fixed.rootRow, renderedRow: fixed.renderedRow };
    });

    await scenario("05", "User Preferences shares the table block, toggles line numbers and resets the band only", async () => {
      await openPreferences(page);
      const state = await dialogState(page, prefsDialog, ["rowHeightMode", "rowHeight", "fontSize", "lineNumbers", "showIcons"]);
      assert(state.lineNumbers === true, "User Preferences does not show the saved line-number state");
      const legends = await page.evaluate(`[...document.querySelectorAll('${prefsDialog} legend')].map((item) => item.textContent.trim())`);
      assert(legends.some((legend) => /WBS band format/.test(legend)), `WBS band fieldset is missing: ${legends.join(" | ")}`);
      assert(legends.some((legend) => /^Display$/.test(legend)), `Display section is missing: ${legends.join(" | ")}`);
      await capture(page, "05-user-preferences-dialog-en-1440");
      await setControl(page, prefsDialog, 'select[name="fontSize"]', "13");
      await setControl(page, prefsDialog, 'input[name="lineNumbers"]', false, "check");
      await submit(page, prefsDialog);
      const applied = await gridState(page);
      assert(applied.rootSize === "13px", `preferences font size is ${applied.rootSize}`);
      assert(applied.headerIsLineNumber === false, "User Preferences did not hide line numbers");

      await openPreferences(page);
      await setControl(page, prefsDialog, 'select[name="fontSize"]', "16");
      await submit(page, prefsDialog, "[data-dialog-reset]");
      const afterReset = await gridState(page);
      assert(afterReset.rootSize === "13px", `Reset band format committed the table font (${afterReset.rootSize})`);
      const resetSaved = await readLayout(page, "preview-rps-01", "project");
      const projectTable = resetSaved.body?.metadata?.presentation?.table;
      assert(projectTable?.fontSize === 13, `saved font size after band reset is ${projectTable?.fontSize}`);

      await openPreferences(page);
      await setControl(page, prefsDialog, 'select[name="fontSize"]', "15");
      await cancel(page, prefsDialog);
      const cancelled = await gridState(page);
      assert(cancelled.rootSize === "13px", `Cancel wrote ${cancelled.rootSize}`);
      await capture(page, "05-line-numbers-off-via-preferences-en-1440");
      return { fontSize: applied.rootSize, legends };
    });

    await scenario("06", "both dialogs localise in fa/RTL 1280x720 and fit en/LTR 1920x1080", async () => {
      await setViewport(page, 1280, 720);
      await setLanguage(page, "fa");
      await openFontRow(page);
      const faFont = await dialogState(page, fontDialog, ["rowHeightMode", "rowHeight"]);
      assert(/قلم/.test(faFont.title), `Persian title is missing: ${faFont.title}`);
      assert(faFont.overflow <= 1, `the RTL font dialog overflows by ${faFont.overflow}px`);
      const faNote = await page.evaluate(`document.querySelector('${fontDialog} [data-row-height-note]')?.textContent ?? ""`);
      assert(/ارتفاع/.test(faNote), "the RTL height note is missing");
      await capture(page, "06-row-height-modes-fa-rtl-1280");
      await cancel(page, fontDialog);
      await openPreferences(page);
      const faPrefs = await page.evaluate(`(() => {
        const dialog = document.querySelector("${prefsDialog}");
        return {
          title: dialog.querySelector("h2")?.textContent?.trim() ?? "",
          lineNumbers: [...dialog.querySelectorAll("label")].find((label) => label.querySelector('input[name="lineNumbers"]'))?.textContent?.trim() ?? "",
          overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
          dir: document.documentElement.dir || "ltr",
        };
      })()`);
      assert(/ترجیحات/.test(faPrefs.title), `Persian preferences title is missing: ${faPrefs.title}`);
      assert(/شمارهٔ ردیف/.test(faPrefs.lineNumbers), `Persian line-number label is missing: ${faPrefs.lineNumbers}`);
      assert(faPrefs.dir === "rtl", `document direction is ${faPrefs.dir}`);
      assert(faPrefs.overflow <= 1, `the RTL preferences dialog overflows by ${faPrefs.overflow}px`);
      await capture(page, "06-user-preferences-fa-rtl-1280");
      await cancel(page, prefsDialog);

      await setLanguage(page, "en");
      await setViewport(page, 1920, 1080);
      await sleep(600);
      const wide = await gridState(page);
      const menuToggle = await page.evaluate(`(() => {
        const item = [...document.querySelectorAll('[data-desktop-command="view.line-numbers"]')].find((element) => element.getClientRects().length > 0);
        return item ? item.getAttribute("aria-checked") ?? item.dataset.checked ?? "unknown" : "missing";
      })()`);
      await toggleLineNumbersFromMenu(page);
      const numbered = await gridState(page);
      assert(numbered.headerIsLineNumber, "line numbers are not visible at 1920x1080");
      await openPreferences(page);
      const widePrefs = await dialogState(page, prefsDialog, ["lineNumbers"]);
      assert(widePrefs.overflow <= 1, `the wide preferences dialog overflows by ${widePrefs.overflow}px`);
      assert(widePrefs.lineNumbers === true, "the wide preferences dialog lost the line-number state");
      await capture(page, "06-user-preferences-en-1920");
      await cancel(page, prefsDialog);
      return { faDirection: faPrefs.dir, wideRows: wide.activityCount, menuState: menuToggle };
    });

    await scenario("07", "the run stays clean: no exception, console error or 5xx", async () => {
      await sleep(800);
      assert(exceptions.length === 0, `runtime exceptions: ${exceptions.join(" | ")}`);
      assert(consoleErrors.length === 0, `console errors: ${consoleErrors.join(" | ")}`);
      assert(apiFailures.length === 0, `API failures: ${JSON.stringify(apiFailures)}`);
      return { exceptions: 0, consoleErrors: 0, apiFailures: 0 };
    });
  } finally {
    writeReport();
  }

  const failed = report.failed ?? 0;
  log(`\n${report.passed}/${scenarios.length} scenarios passed; screenshots: ${screenshots.length}`);
  if (failed) process.exitCode = 1;
}

await main();
