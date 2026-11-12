#!/usr/bin/env node
/**
 * Browser E2E for the Activities layout selector.
 *
 * The control must read the stored project and user layouts from the layout
 * contract, preview a stored layout, cancel back to the saved one, apply,
 * save, save as, and survive a reload and a project switch. Every expected
 * value is read from the same API the page uses; nothing is injected into the
 * document, and no fixture layout is fabricated.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4300 node e2e/layout-selector-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4174";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-10";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "layout-selector-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `layout-selector-v26-${evidenceDate}`);
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
  const file = `layout-selector-v26/${name}.png`;
  await page.screenshot(file);
  copyFileSync(join(artifactsDir, file), join(evidenceDir, `${name}.png`));
  screenshots.push(`${name}.png`);
  return file;
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

async function setViewport(page, width, height) {
  await page.cdp.send("Emulation.setDeviceMetricsOverride", {
    width,
    height,
    deviceScaleFactor: 1,
    mobile: false,
  });
  await sleep(500);
}

async function readLayout(page, projectId, scope) {
  return page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${projectId}/p6/layouts/${scope}/activity");
    let body = null;
    try { body = await response.json(); } catch {}
    return { status: response.status, body };
  })()`, { awaitPromise: true });
}

const gridState = `(() => {
  const selector = document.querySelector("[data-layout-selector]");
  const trigger = selector?.querySelector("[data-layout-trigger]") ?? null;
  const menu = selector?.querySelector("[data-layout-menu]") ?? null;
  const grid = document.querySelector("#cp-activity-grid");
  const gantt = document.querySelector("#cp-gantt");
  const table = grid?.querySelector("table");
  const selectorRect = selector?.getBoundingClientRect() ?? null;
  const tableRect = table?.getBoundingClientRect() ?? null;
  const menuRect = menu && !menu.hidden ? menu.getBoundingClientRect() : null;
  return {
    selectorExists: Boolean(selector),
    triggerVisible: Boolean(trigger && trigger.getClientRects().length && trigger.getBoundingClientRect().width > 0),
    triggerName: trigger?.querySelector("[data-layout-name]")?.textContent?.trim() ?? null,
    triggerScope: trigger?.querySelector("[data-layout-scope]")?.textContent?.trim() ?? null,
    triggerTitle: trigger?.getAttribute("title") ?? null,
    previewState: selector?.querySelector("[data-layout-state]")?.textContent?.trim() ?? null,
    menuOpen: Boolean(menu && !menu.hidden),
    options: [...(selector?.querySelectorAll("[data-layout-option]") ?? [])].map((option) => ({
      scope: option.dataset.layoutOption,
      name: option.querySelector(".cp-layout-option-name")?.textContent?.trim() ?? null,
      meta: option.querySelector(".cp-layout-option-meta")?.textContent?.trim() ?? null,
      checked: option.getAttribute("aria-checked"),
    })),
    actions: [...(selector?.querySelectorAll("[data-layout-action]") ?? [])].map((button) => ({
      action: button.dataset.layoutAction,
      disabled: button.disabled,
      title: button.getAttribute("title"),
    })),
    columns: [...(grid?.querySelectorAll("thead th[data-column-id]") ?? [])].map((th) => th.dataset.columnId),
    columnWidths: [...(grid?.querySelectorAll("thead th[data-column-id]") ?? [])].map((th) => Math.round(th.getBoundingClientRect().width)),
    rowIds: [...(grid?.querySelectorAll("tbody tr[data-activity-id]") ?? [])].map((row) => row.dataset.activityId),
    ganttBars: gantt?.querySelectorAll("[data-gantt-activity-id]").length ?? 0,
    selectorHeight: selectorRect ? Math.round(selectorRect.height) : 0,
    selectorAboveTable: Boolean(selectorRect && tableRect && selectorRect.bottom <= tableRect.top + 2),
    menuWithinViewport: menuRect ? menuRect.right <= window.innerWidth + 1 && menuRect.left >= -1 && menuRect.bottom <= window.innerHeight + 1 : null,
    locale: document.documentElement.lang || null,
    direction: getComputedStyle(document.querySelector(".cp-workspace") ?? document.body).direction,
  };
})()`;

async function openSelector(page) {
  const opened = await page.evaluate(`(() => {
    const selector = document.querySelector("[data-layout-selector]");
    const trigger = selector?.querySelector("[data-layout-trigger]");
    if (!trigger) return false;
    if (selector.querySelector("[data-layout-menu]")?.hidden) trigger.click();
    return true;
  })()`);
  assert(opened, "layout selector trigger is missing");
  await page.waitFor(`(() => {
    const menu = document.querySelector("[data-layout-menu]");
    return Boolean(menu && !menu.hidden);
  })()`, "layout menu open");
  await promiseSleep(400);
}

/** The open menu reloads its catalogue once, so wait for either state. */
async function waitForCatalogue(page) {
  await page.waitFor(`(() => {
    const selector = document.querySelector("[data-layout-selector]");
    if (!selector) return false;
    const options = selector.querySelectorAll("[data-layout-option]").length;
    const text = selector.querySelector(".cp-layout-menu")?.textContent ?? "";
    return options > 0 || text.includes("No stored layout") || text.includes("could not be read") || text.includes("چیدمانی ذخیره");
  })()`, "layout catalogue");
  await promiseSleep(300);
}

async function promiseSleep(ms) {
  await sleep(ms);
}

async function chooseOption(page, scope) {
  const clicked = await page.evaluate(`(() => {
    const option = document.querySelector('[data-layout-option="${scope}"]');
    if (!option) return false;
    option.click();
    return true;
  })()`);
  assert(clicked, `layout option ${scope} is missing`);
  await sleep(900);
}

async function triggerAction(page, action) {
  const clicked = await page.evaluate(`(() => {
    const button = document.querySelector('[data-layout-action="${action}"]');
    if (!button || button.disabled) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `layout action ${action} is missing or disabled`);
  await sleep(900);
}

async function openProjectWindow(page) {
  const clicked = await page.evaluate(`(() => {
    const buttons = [...document.querySelectorAll('[data-menu="project"]')];
    const button = buttons.find((entry) => entry.getClientRects().length > 0) ?? buttons[0];
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, "Project menu button is missing");
  await page.waitForSelector(".cp-project-table", "project table");
  await page.waitFor(`document.querySelectorAll("[data-project-row]").length > 0`, "project rows", 15000);
  await sleep(300);
}

async function openProject(page, projectId) {
  await openProjectWindow(page);
  const clicked = await page.evaluate(`(() => {
    const button = document.querySelector('[data-project-open="${projectId}"]');
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `Open button not found for ${projectId}`);
  await page.waitFor(
    `document.querySelector(".cp-workspace")?.dataset.project === ${JSON.stringify(projectId)}`,
    `project ${projectId} to open`,
    20000,
  );
  await sleep(800);
}

async function openSchedule(page) {
  const clicked = await page.evaluate(`(() => {
    const buttons = [...document.querySelectorAll('[data-menu="schedule"]')];
    const button = buttons.find((entry) => entry.getClientRects().length > 0) ?? buttons[0];
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, "Schedule menu button is missing");
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
  await page.waitForSelector("[data-layout-trigger]", "layout selector");
  await sleep(900);
}

async function hideColumnThroughDialog(page, position) {
  const opened = await page.evaluate(`(() => {
    const button = document.querySelector("[data-columns-open]");
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(opened, "Columns button is missing");
  await page.waitForSelector("[data-p6-columns-dialog][open]", "columns dialog", 6000);
  await sleep(400);
  const hidden = await page.evaluate(`(() => {
    const items = [...document.querySelectorAll("[data-columns-selected-id]")];
    const item = items[${position}] ?? null;
    const button = item?.querySelector("[data-columns-visibility]");
    if (!button) return null;
    const id = button.dataset.columnsVisibility;
    button.click();
    return { id, after: button.dataset.columnsVisible };
  })()`);
  assert(hidden && hidden.id, `no column at position ${position} to hide`);
  await sleep(300);
  const ok = await page.evaluate(`(() => {
    const button = document.querySelector("[data-columns-ok]");
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(ok, "Columns OK button is missing");
  await page.waitFor(`!document.querySelector("[data-p6-columns-dialog][open]")`, "columns dialog closed", 6000);
  await sleep(1400);
  return hidden.id;
}

let pendingPromptText = null;

async function acceptPrompt(page, text) {
  pendingPromptText = text;
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
    contract: "cubi-layout-selector-v26.v1",
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
    page.cdp.on("Page.javascriptDialogOpening", async () => {
      const text = pendingPromptText;
      pendingPromptText = null;
      try {
        await page.cdp.send("Page.handleJavaScriptDialog", text === null ? { accept: true } : { accept: true, promptText: text });
      } catch (error) {
        log(`  prompt handler failed: ${error.message}`);
      }
    });

    await setViewport(page, 1440, 900);
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
    await sleep(1600);
    await setLanguage(page, "en");
    await openSchedule(page);

    const projectLayout = await readLayout(page, "preview-rps-01", "project");
    assert(projectLayout.status === 200, `project layout read status ${projectLayout.status}`);
    const projectDefinition = projectLayout.body.layout ?? projectLayout.body;
    assert(projectDefinition.metadata?.layoutName === "Classic Schedule Layout", `seeded layout name is ${projectDefinition.metadata?.layoutName}`);

    await scenario("01", "انتخاب‌کنندهٔ Layout به‌صورت پیش‌فرض بالای جدول/Gantt و با نام واقعیِ ذخیره‌شده دیده می‌شود", async () => {
      const state = await page.evaluate(gridState);
      assert(state.selectorExists, "layout selector is not rendered");
      assert(state.triggerVisible, "layout trigger is not visible");
      assert(state.selectorAboveTable, "layout selector must sit above the activity table");
      assert(state.triggerName === projectDefinition.metadata.layoutName, `trigger name is ${state.triggerName}`);
      assert(state.triggerScope === `Project layout · r${projectDefinition.revision}`, `trigger scope is ${state.triggerScope}`);
      assert(state.menuOpen === false, "layout menu should start closed");
      assert(state.columns.length > 0, "activity table has no columns");
      await capture(page, "01-default-layout-selector");
      return { name: state.triggerName, scope: state.triggerScope, columns: state.columns.length };
    });

    await scenario("02", "گزینه‌های منو فقط از چیدمان‌های ذخیره‌شدهٔ همان پروژه می‌آیند", async () => {
      const userBefore = await readLayout(page, "preview-rps-01", "user");
      assert(userBefore.status === 404, `user layout should not exist yet, got ${userBefore.status}`);
      await openSelector(page);
      await waitForCatalogue(page);
      const state = await page.evaluate(gridState);
      assert(state.menuOpen, "layout menu did not open");
      assert(state.options.length === 1, `catalogue shows ${state.options.length} options`);
      assert(state.options[0].scope === "project", `catalogue option scope is ${state.options[0].scope}`);
      assert(state.options[0].checked === "true", "the current layout must be checked");
      assert(state.options[0].name === projectDefinition.metadata.layoutName, `option name is ${state.options[0].name}`);
      const saveAs = state.actions.find((entry) => entry.action === "save-as");
      assert(saveAs && !saveAs.disabled, "Save As should be enabled for the planner role");
      await capture(page, "02-layout-catalogue");
      await page.evaluate(`document.querySelector("[data-layout-trigger]")?.click()`);
      await sleep(300);
      return { options: state.options, saveAs: saveAs.title };
    });

    await scenario("03", "Save As یک چیدمان واقعی در scope کاربر می‌نویسد و بلافاصله در منو دیده می‌شود", async () => {
      await openSelector(page);
      await waitForCatalogue(page);
      await acceptPrompt(page, "Field team view");
      const started = Date.now();
      const clicked = await page.evaluate(`(() => {
        const button = document.querySelector('[data-layout-action="save-as"]');
        if (!button || button.disabled) return false;
        button.click();
        return true;
      })()`);
      assert(clicked, "Save As is missing or disabled");
      let userLayout = null;
      while (Date.now() - started < 15000) {
        const read = await readLayout(page, "preview-rps-01", "user");
        if (read.status === 200) {
          userLayout = read.body.layout ?? read.body;
          break;
        }
        await sleep(400);
      }
      assert(userLayout, "Save As did not persist a user layout");
      assert(userLayout.metadata.layoutName === "Field team view", `saved name is ${userLayout.metadata.layoutName}`);
      assert(userLayout.revision === 0, `new user layout revision is ${userLayout.revision}`);
      const state = await page.evaluate(gridState);
      assert(state.triggerName === "Field team view", `trigger name after Save As is ${state.triggerName}`);
      assert(state.triggerScope === "User layout · r0", `trigger scope after Save As is ${state.triggerScope}`);
      await openSelector(page);
      await waitForCatalogue(page);
      const menu = await page.evaluate(gridState);
      assert(menu.options.length === 2, `catalogue shows ${menu.options.length} options after Save As`);
      assert(menu.options.some((entry) => entry.scope === "user" && entry.name === "Field team view"), "saved layout is missing from the menu");
      await capture(page, "03-saved-user-layout");
      await page.evaluate(`document.querySelector("[data-layout-trigger]")?.click()`);
      await sleep(300);
      return { revision: userLayout.revision, name: userLayout.metadata.layoutName, columns: userLayout.columns.filter((column) => column.visible).length };
    });

    const beforeSwitch = await page.evaluate(gridState);
    let hiddenColumnId = null;
    await scenario("04", "بازکردن چیدمان پروژه، جدول را پیش‌نمایش می‌دهد و Cancel آن را دقیقاً بازمی‌گرداند", async () => {
      hiddenColumnId = await hideColumnThroughDialog(page, 2);
      const userLayout = await readLayout(page, "preview-rps-01", "user");
      assert(userLayout.status === 200, "user layout disappeared after the column change");
      const userDefinition = userLayout.body.layout ?? userLayout.body;
      assert(userDefinition.columns.some((column) => column.field_id === hiddenColumnId && column.visible === false), `${hiddenColumnId} was not hidden in the stored user layout`);
      const userGrid = await page.evaluate(gridState);
      assert(!userGrid.columns.includes(hiddenColumnId), `${hiddenColumnId} is still visible in the user layout table`);

      await openSelector(page);
      await waitForCatalogue(page);
      await chooseOption(page, "project");
      const preview = await page.evaluate(gridState);
      assert(preview.columns.includes(hiddenColumnId), "previewing the project layout did not restore the hidden column");
      assert(preview.previewState && preview.previewState.toLowerCase().includes("preview"), `preview badge is ${preview.previewState}`);
      const projectColumns = (projectDefinition.columns ?? []).filter((column) => column.visible).map((column) => column.field_id);
      assert(JSON.stringify(preview.columns) === JSON.stringify(projectColumns), `previewed columns ${preview.columns} do not match the stored project layout ${projectColumns}`);
      await capture(page, "04-layout-preview");
      await openSelector(page);
      await waitForCatalogue(page);
      await triggerAction(page, "cancel");
      const cancelled = await page.evaluate(gridState);
      assert(cancelled.previewState === null, `preview badge survived Cancel: ${cancelled.previewState}`);
      assert(!cancelled.columns.includes(hiddenColumnId), "Cancel did not restore the saved user layout");
      return { hiddenColumnId, userColumns: userGrid.columns.length, projectColumns: preview.columns.length };
    });

    await scenario("05", "Apply و بازخوانی صفحه، چیدمان انتخاب‌شده را برای همان کاربر و پروژه بازمی‌گرداند", async () => {
      await openSelector(page);
      await waitForCatalogue(page);
      await chooseOption(page, "project");
      await openSelector(page);
      await waitForCatalogue(page);
      await triggerAction(page, "apply");
      const applied = await page.evaluate(gridState);
      assert(applied.previewState === null, "preview badge survived Apply");
      assert(applied.triggerName === projectDefinition.metadata.layoutName, `applied name is ${applied.triggerName}`);
      assert(applied.triggerScope === `Project layout · r${projectDefinition.revision}`, `applied scope is ${applied.triggerScope}`);

      await page.reload("[data-layout-trigger]", "workspace reload");
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows after reload");
      await sleep(1400);
      const afterProjectReload = await page.evaluate(gridState);
      assert(afterProjectReload.triggerName === projectDefinition.metadata.layoutName, `reload restored ${afterProjectReload.triggerName}`);

      await openSelector(page);
      await waitForCatalogue(page);
      await chooseOption(page, "user");
      await openSelector(page);
      await waitForCatalogue(page);
      await triggerAction(page, "apply");
      const userApplied = await page.evaluate(gridState);
      assert(userApplied.triggerName === "Field team view", `user apply name is ${userApplied.triggerName}`);
      await page.reload("[data-layout-trigger]", "workspace reload");
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows after second reload");
      await sleep(1400);
      const afterUserReload = await page.evaluate(gridState);
      assert(afterUserReload.triggerName === "Field team view", `reload restored ${afterUserReload.triggerName}`);
      assert(afterUserReload.triggerScope.startsWith("User layout"), `reload scope is ${afterUserReload.triggerScope}`);
      await capture(page, "05-user-layout-after-reload");
      return { project: afterProjectReload.triggerName, user: afterUserReload.triggerName };
    });

    await scenario("06", "Save نسخهٔ ذخیره‌شده را واقعاً افزایش می‌دهد و دادهٔ زمان‌بندی را تغییر نمی‌دهد", async () => {
      const before = await page.evaluate(gridState);
      const beforeLayout = await readLayout(page, "preview-rps-01", "user");
      const beforeDefinition = beforeLayout.body.layout ?? beforeLayout.body;
      await openSelector(page);
      await waitForCatalogue(page);
      await triggerAction(page, "save");
      const started = Date.now();
      let afterDefinition = null;
      while (Date.now() - started < 12000) {
        const read = await readLayout(page, "preview-rps-01", "user");
        if (read.status === 200) {
          const definition = read.body.layout ?? read.body;
          if (definition.revision > beforeDefinition.revision) {
            afterDefinition = definition;
            break;
          }
        }
        await sleep(400);
      }
      assert(afterDefinition, `layout revision did not advance past ${beforeDefinition.revision}`);
      assert(afterDefinition.metadata.layoutName === "Field team view", `save renamed the layout to ${afterDefinition.metadata.layoutName}`);
      const after = await page.evaluate(gridState);
      assert(JSON.stringify(after.rowIds) === JSON.stringify(before.rowIds), "Save changed the activity rows");
      assert(JSON.stringify(after.columnWidths) === JSON.stringify(before.columnWidths), "Save changed the column widths");
      assert(JSON.stringify(after.columns) === JSON.stringify(before.columns), "Save changed the visible columns");
      await capture(page, "06-saved-revision");
      return { beforeRevision: beforeDefinition.revision, afterRevision: afterDefinition.revision, rows: after.rowIds.length };
    });

    await scenario("07", "هر پروژه چیدمان و کاتالوگ خودش را دارد و انتخاب کاربر بین پروژه‌ها نشت نمی‌کند", async () => {
      const projectBefore = await page.evaluate(gridState);
      await openProject(page, "preview-nse-02");
      await openSchedule(page);
      const nseProject = await readLayout(page, "preview-nse-02", "project");
      const nseUser = await readLayout(page, "preview-nse-02", "user");
      assert(nseProject.status === 200, `second project layout status ${nseProject.status}`);
      assert(nseUser.status === 404, `second project should not inherit the first project's user layout, got ${nseUser.status}`);
      const nseDefinition = nseProject.body.layout ?? nseProject.body;
      const nseGrid = await page.evaluate(gridState);
      assert(nseGrid.triggerName === (nseDefinition.metadata?.layoutName ?? "Project layout"), `second project shows ${nseGrid.triggerName}`);
      await openSelector(page);
      await waitForCatalogue(page);
      const nseMenu = await page.evaluate(gridState);
      assert(nseMenu.options.length === 1 && nseMenu.options[0].scope === "project", `second project catalogue is ${JSON.stringify(nseMenu.options)}`);
      await capture(page, "07-second-project");
      await page.evaluate(`document.querySelector("[data-layout-trigger]")?.click()`);
      await sleep(300);

      await openProject(page, "preview-rps-01");
      await openSchedule(page);
      await page.waitFor(
        `document.querySelector("[data-layout-name]")?.textContent?.trim() === "Field team view"`,
        "the first project's stored layout selection",
        15000,
      );
      await sleep(600);
      const backGrid = await page.evaluate(gridState);
      assert(backGrid.triggerName === "Field team view", `returning to the first project shows ${backGrid.triggerName}`);
      await openSelector(page);
      await waitForCatalogue(page);
      const backMenu = await page.evaluate(gridState);
      assert(backMenu.options.length === 2, `returning catalogue is ${JSON.stringify(backMenu.options)}`);
      await page.evaluate(`document.querySelector("[data-layout-trigger]")?.click()`);
      await sleep(300);
      return { projectBefore: projectBefore.triggerName, nse: nseGrid.triggerName, restored: backGrid.triggerName };
    });

    await scenario("08", "رابط راست‌به‌چپ، انتخاب‌کننده را بدون شکستن چیدمان نمایش می‌دهد", async () => {
      await setLanguage(page, "fa");
      const fa = await page.evaluate(gridState);
      assert(fa.direction === "rtl", `workspace direction is ${fa.direction}`);
      assert(fa.triggerVisible, "layout trigger is not visible in RTL");
      await openSelector(page);
      await waitForCatalogue(page);
      const faMenu = await page.evaluate(gridState);
      assert(faMenu.menuOpen && faMenu.menuWithinViewport === true, "RTL layout menu is not usable inside the viewport");
      assert(faMenu.options.length === 2, `RTL catalogue shows ${faMenu.options.length} options`);
      await capture(page, "08-rtl-layout-selector");
      await page.evaluate(`document.querySelector("[data-layout-trigger]")?.click()`);
      await setLanguage(page, "en");
      return { direction: fa.direction, options: faMenu.options.length };
    });

    await scenario("09", "در سه وضوح 1280×720 و 1366×768 و 1920×1080 کنترل دیده می‌شود و منو داخل صفحه می‌ماند", async () => {
      const results = [];
      for (const [width, height] of [[1280, 720], [1366, 768], [1920, 1080]]) {
        await setViewport(page, width, height);
        const state = await page.evaluate(gridState);
        assert(state.triggerVisible, `layout trigger is not visible at ${width}x${height}`);
        assert(state.selectorHeight > 0 && state.selectorHeight < 120, `layout selector height is ${state.selectorHeight} at ${width}x${height}`);
        await openSelector(page);
        await waitForCatalogue(page);
        const menu = await page.evaluate(gridState);
        assert(menu.menuWithinViewport === true, `layout menu leaves the viewport at ${width}x${height}`);
        await capture(page, `09-layout-selector-${width}x${height}`);
        await page.evaluate(`document.querySelector("[data-layout-trigger]")?.click()`);
        await sleep(250);
        results.push({ width, height, selectorHeight: state.selectorHeight, menuWithinViewport: menu.menuWithinViewport });
      }
      await setViewport(page, 1440, 900);
      return results;
    });

    await scenario("10", "Rename، Export و Import یک پروندهٔ چیدمان واقعی می‌سازند و دادهٔ پروژه را تغییر نمی‌دهند", async () => {
      const beforeRows = (await page.evaluate(gridState)).rowIds;

      await openSelector(page);
      await waitForCatalogue(page);
      await acceptPrompt(page, "Field crew layout");
      await triggerAction(page, "rename");
      let renamed = null;
      const renameStarted = Date.now();
      while (Date.now() - renameStarted < 15000) {
        const read = await readLayout(page, "preview-rps-01", "user");
        if (read.status === 200) {
          const definition = read.body.layout ?? read.body;
          if (definition.metadata?.layoutName === "Field crew layout") {
            renamed = definition;
            break;
          }
        }
        await sleep(400);
      }
      assert(renamed, "Rename did not write the new name to the user layout");
      const renamedGrid = await page.evaluate(gridState);
      assert(renamedGrid.triggerName === "Field crew layout", `trigger name after rename is ${renamedGrid.triggerName}`);

      await openSelector(page);
      await waitForCatalogue(page);
      const exported = await page.evaluate(`(async () => {
        const originalCreate = URL.createObjectURL.bind(URL);
        const originalClick = HTMLAnchorElement.prototype.click;
        window.__cubiExportBlob = null;
        window.__cubiDownload = null;
        URL.createObjectURL = (blob) => { window.__cubiExportBlob = blob; return "blob:cubi-layout-export"; };
        HTMLAnchorElement.prototype.click = function () { window.__cubiDownload = this.download; };
        const button = document.querySelector('[data-layout-action="export"]');
        if (!button || button.disabled) return { ok: false, reason: "export disabled" };
        button.click();
        await new Promise((resolve) => setTimeout(resolve, 60));
        const text = window.__cubiExportBlob ? await window.__cubiExportBlob.text() : null;
        HTMLAnchorElement.prototype.click = originalClick;
        URL.createObjectURL = originalCreate;
        return { ok: true, text, download: window.__cubiDownload };
      })()`, { awaitPromise: true });
      assert(exported.ok, `export could not run: ${exported.reason ?? "unknown"}`);
      assert(exported.text, "export produced no file content");
      assert((exported.download ?? "").endsWith(".cubi-layout.json"), `download name is ${exported.download}`);
      const document = JSON.parse(exported.text);
      assert(document.format === "cubi-layout.v1", `export format is ${document.format}`);
      assert(document.name === "Field crew layout", `export name is ${document.name}`);
      assert(document.layout.columns.length === renamed.columns.length, "export dropped columns");
      assert(!("scope" in document.layout) && !("revision" in document.layout), "export pinned a scope or revision");
      assert(!exported.text.includes("preview-rps-01") && !exported.text.includes("cubi-preview-tenant"), "export leaked project or tenant identity");
      await capture(page, "10-layout-export");

      const importedName = "Imported crew layout";
      const importDocument = JSON.parse(exported.text);
      importDocument.name = importedName;
      await openSelector(page);
      await waitForCatalogue(page);
      const imported = await page.evaluate(`(async () => {
        const input = document.querySelector("[data-layout-import]");
        if (!input) return { ok: false, reason: "import input missing" };
        const file = new File([${JSON.stringify(JSON.stringify(importDocument))}], "crew.cubi-layout.json", { type: "application/json" });
        const transfer = new DataTransfer();
        transfer.items.add(file);
        input.files = transfer.files;
        input.dispatchEvent(new Event("change", { bubbles: true }));
        return { ok: true };
      })()`, { awaitPromise: true });
      assert(imported.ok, `import could not run: ${imported.reason ?? "unknown"}`);
      let importedLayout = null;
      const importStarted = Date.now();
      while (Date.now() - importStarted < 15000) {
        const read = await readLayout(page, "preview-rps-01", "user");
        if (read.status === 200) {
          const definition = read.body.layout ?? read.body;
          if (definition.metadata?.layoutName === importedName) {
            importedLayout = definition;
            break;
          }
        }
        await sleep(400);
      }
      assert(importedLayout, "Import did not write the user layout");
      assert(importedLayout.revision > renamed.revision, `import revision ${importedLayout.revision} did not advance past ${renamed.revision}`);
      assert(JSON.stringify(importedLayout.columns) === JSON.stringify(renamed.columns), "Import changed the column presentation");
      const importedGrid = await page.evaluate(gridState);
      assert(importedGrid.triggerName === importedName, `trigger name after import is ${importedGrid.triggerName}`);
      assert(JSON.stringify(importedGrid.rowIds) === JSON.stringify(beforeRows), "layout exchange changed the activity rows");
      await capture(page, "11-layout-import");
      return {
        renamed: renamed.metadata.layoutName,
        download: exported.download,
        imported: importedLayout.metadata.layoutName,
        revision: importedLayout.revision,
        rows: importedGrid.rowIds.length,
      };
    });

    const finalState = await page.evaluate(gridState);
    assert(finalState.columns.length > 0, "the activity table ended without columns");
    assert(exceptions.length === 0, `uncaught page exceptions: ${JSON.stringify(exceptions.slice(0, 3))}`);
    assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors.slice(0, 3))}`);
    assert(apiFailures.length === 0, `API 5xx responses: ${JSON.stringify(apiFailures.slice(0, 3))}`);
  } finally {
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(outDir, "layout-selector-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(evidenceDir, "layout-selector-v26.json"), JSON.stringify(report, null, 2));
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
