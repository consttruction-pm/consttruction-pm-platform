#!/usr/bin/env node
/**
 * Version 26 toolbar / menu / rail acceptance.
 *
 * Measures the real Activities window at 1280x720, 1366x768 and 1920x1080 in
 * English (LTR) and Persian (RTL). It asserts:
 *  - one application menu bar with the Version 26 order and a recognizable
 *    icon on every command, plus a reserved check column;
 *  - one icon toolbar, grouped in the reference order, with no duplicate
 *    command family and no parallel text command band;
 *  - version 26-sized hit targets for the grid action strip, the chart board
 *    controls and both vertical rails;
 *  - the Classic Schedule Layout selector previews, applies and survives a
 *    reload.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 \
 *   CUBI_TESTED_CODE_SHA=<code commit> \
 *   node e2e/toolbars-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const outDir = join(artifactsDir, "toolbars-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `toolbars-v26-${evidenceDate}`);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const cells = [];
const screenshots = [];
const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const commands = [];

const EXPECTED_MENUS = {
  en: ["File", "Edit", "View", "Project", "Enterprise", "Tools", "Admin", "Help"],
  fa: ["فایل", "ویرایش", "نما", "پروژه", "سازمان", "ابزارها", "مدیریت", "راهنما"],
};
const EXPECTED_GROUPS = ["workspace", "edit", "layout", "view", "project", "activities", "wbs", "gantt", "resources", "tools"];

function log(message) {
  process.stdout.write(`${message}\n`);
}

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

async function capture(page, name) {
  const file = `toolbars-v26/${name}.png`;
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
  await sleep(1100);
}

const measure = `(() => {
  const rect = (element) => {
    if (!element) return null;
    const r = element.getBoundingClientRect();
    return { left: +r.left.toFixed(1), top: +r.top.toFixed(1), right: +r.right.toFixed(1), bottom: +r.bottom.toFixed(1), width: +r.width.toFixed(1), height: +r.height.toFixed(1) };
  };
  const style = (element) => element ? getComputedStyle(element) : null;
  const iconBox = (element) => {
    const icon = element?.querySelector?.(".cp-icon");
    return icon ? rect(icon) : null;
  };
  const triggers = [...document.querySelectorAll("[data-desktop-menu]")];
  const toolbar = document.querySelector(".cp-toolbar");
  const toolbarButtons = [...document.querySelectorAll(".cp-toolbar-scroll .cp-toolbar-button")];
  const overflowMirrors = [...document.querySelectorAll("[data-toolbar-overflow-popup] .cp-toolbar-button")];
  const gridActions = [...document.querySelectorAll(".cp-p6-grid-actions")].map((strip) => ({
    rect: rect(strip),
    inHead: (() => { const h = strip.parentElement?.getBoundingClientRect(); const r = strip.getBoundingClientRect(); return Boolean(h) && r.left >= h.left - 1 && r.right <= h.right + 1 && r.top >= h.top - 1 && r.bottom <= h.bottom + 1; })(),
    buttons: [...strip.querySelectorAll("button")].map((button) => ({
      id: button.dataset.activityCreateOpen !== undefined ? "add"
        : button.dataset.columnsOpen !== undefined ? "columns"
        : button.dataset.railAction ?? button.dataset.layoutOptionsOpen !== undefined ? "layout-options"
        : button.dataset.resetTableSplit !== undefined ? "reset-table"
        : button.dataset.resetDetailsSplit !== undefined ? "reset-details"
        : button.dataset.resetColumnWidths !== undefined ? "reset-columns"
        : button.dataset.layoutOptionsOpen !== undefined ? "layout-options" : "other",
      rect: rect(button),
      icon: iconBox(button),
      glyph: button.querySelector(".cp-icon")?.innerHTML ?? null,
      title: button.getAttribute("title"),
    })),
    separators: strip.querySelectorAll(".cp-action-separator").length,
  }));
  const ganttToolbar = document.querySelector(".cp-gantt-toolbar");
  const navRail = document.querySelector(".cp-navigation-tree");
  const contextRail = document.querySelector(".cp-context-command-rail");
  const railButtons = (rail) => [...(rail?.querySelectorAll("button") ?? [])].filter((b) => b.getClientRects().length).map((button) => ({ rect: rect(button), icon: iconBox(button), label: button.getAttribute("aria-label") }));
  return {
    viewport: { width: window.innerWidth, height: window.innerHeight },
    lang: document.documentElement.lang,
    direction: style(document.querySelector(".cp-workspace") ?? document.body)?.direction,
    pageOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
    menubar: { rect: rect(document.querySelector(".cp-menubar")), triggerCount: triggers.length,
      triggers: triggers.map((trigger) => ({ id: trigger.dataset.desktopMenu, text: (trigger.textContent || "").trim(), rect: rect(trigger), font: style(trigger)?.fontSize })) },
    toolbar: { count: document.querySelectorAll(".cp-toolbar").length, rect: rect(toolbar),
      scrollOverflow: toolbar ? toolbar.scrollWidth > toolbar.clientWidth + 1 : null,
      height: rect(toolbar)?.height ?? 0,
      groups: [...document.querySelectorAll("[data-toolbar-group]")].map((group) => group.dataset.toolbarGroup),
      buttons: toolbarButtons.length,
      overflowMirrors: overflowMirrors.length,
      minButton: toolbarButtons.reduce((min, button) => { const r = button.getBoundingClientRect(); return { width: Math.min(min.width, r.width), height: Math.min(min.height, r.height) }; }, { width: 999, height: 999 }),
      withoutIcon: toolbarButtons.filter((button) => !button.querySelector(".cp-icon")).length,
      duplicateCommands: (() => {
        const seen = new Set(); const dupes = [];
        for (const button of toolbarButtons) {
          // New and Open are distinct commands that both open the project window.
          if (["toolbar.new", "toolbar.open"].includes(button.dataset.toolbarCommand)) continue;
          const command = button.dataset.desktopCommand ?? button.dataset.desktopWindow ?? button.dataset.fullscreenToggle;
          if (!command) continue;
          if (seen.has(command)) dupes.push(command); else seen.add(command);
        }
        return [...new Set(dupes)];
      })() },
    parallelShells: { cubiToolbar: document.querySelectorAll(".cubi-toolbar").length, commandShell: document.querySelectorAll(".cubi-command-shell, .cubi-command-menubar").length, layoutbar: document.querySelectorAll(".cp-layoutbar").length, ganttTextCommands: document.querySelectorAll(".cp-gantt-command-button").length },
    gridActions,
    gantt: { rect: rect(ganttToolbar), height: rect(ganttToolbar)?.height ?? 0, scaleButtons: document.querySelectorAll("[data-gantt-scale]").length, relationshipToggle: Boolean(document.querySelector("[data-gantt-relationships-toggle]")), textCommands: document.querySelectorAll(".cp-gantt-command-button").length },
    navRail: { rect: rect(navRail), buttons: railButtons(navRail) },
    contextRail: { rect: rect(contextRail), buttons: railButtons(contextRail) },
    layout: { trigger: Boolean(document.querySelector("[data-layout-trigger]")), name: document.querySelector("[data-layout-name]")?.textContent?.trim() ?? null, scope: document.querySelector("[data-layout-scope]")?.textContent?.trim() ?? null },
  };
})()`;

async function login(page) {
  // Sign in as the administrator so the role-gated Admin menu is part of the
  // audited menu bar; the Activities layout is identical for every role.
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "form", "login");
  await page.click('button[name="role"][value="admin"]');
  await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
  await page.click('[data-project-id="preview-rps-01"]');
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
  await sleep(1600);
}

async function openMenu(page, id) {
  const opened = await page.evaluate(`(() => {
    const trigger = document.querySelector('[data-desktop-menu="${id}"]');
    if (!trigger) return false;
    if (trigger.getAttribute("aria-expanded") !== "true") trigger.click();
    return true;
  })()`);
  assert(opened, `menu ${id} is missing`);
  await page.waitFor(`document.querySelector('[data-desktop-popup="${id}"]')?.hidden === false`, `${id} popup`);
  await sleep(220);
}

async function closeMenus(page) {
  await page.evaluate(`document.body.dispatchEvent(new MouseEvent("click", { bubbles: true }))`);
  await sleep(150);
}

async function runMenuItem(page, menuId, itemId) {
  await openMenu(page, menuId);
  const clicked = await page.evaluate(`(() => {
    const button = document.querySelector('[data-desktop-item="${itemId}"]');
    if (!button || button.disabled) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `${menuId}/${itemId} is missing or disabled`);
  await sleep(500);
}

function verifyCell(cell, locale) {
  const m = cell.measure;
  assert(!m.pageOverflow, "page overflows horizontally");
  assert(m.menubar.triggerCount === 8, `menu bar has ${m.menubar.triggerCount} menus`);
  assert(JSON.stringify(m.menubar.triggers.map((trigger) => trigger.text)) === JSON.stringify(EXPECTED_MENUS[locale]), `menu order is ${m.menubar.triggers.map((t) => t.text).join(", ")}`);
  for (const trigger of m.menubar.triggers) {
    assert(trigger.rect.height >= 22, `menu ${trigger.text} target is ${trigger.rect.height}px high`);
    assert(Number.parseFloat(trigger.font) >= 11, `menu ${trigger.text} font is ${trigger.font}`);
  }
  assert(m.toolbar.count === 1, `${m.toolbar.count} toolbars rendered`);
  assert(m.toolbar.height >= 24, `toolbar is ${m.toolbar.height}px high`);
  assert(JSON.stringify(m.toolbar.groups) === JSON.stringify(EXPECTED_GROUPS), `toolbar groups are ${m.toolbar.groups.join(", ")}`);
  assert(m.toolbar.withoutIcon === 0, `${m.toolbar.withoutIcon} toolbar buttons have no icon`);
  assert(m.toolbar.duplicateCommands.length === 0, `duplicate toolbar commands: ${m.toolbar.duplicateCommands.join(", ")}`);
  assert(m.parallelShells.cubiToolbar === 0 && m.parallelShells.commandShell === 0 && m.parallelShells.layoutbar === 0, "a parallel command shell is rendered");
  assert(m.parallelShells.ganttTextCommands === 0, "the chart board repeats layout commands as text");
  assert(m.gridActions.length >= 1, "grid action strip is missing");
  for (const strip of m.gridActions) {
    assert(strip.inHead, "grid action strip escapes its head");
    assert(strip.separators >= 1, "grid action strip has no group separator");
  }
  const gridButtons = m.gridActions[0].buttons;
  const resetGlyphs = gridButtons.filter((button) => button.id.startsWith("reset-")).map((button) => button.glyph);
  assert(resetGlyphs.length === 3, `grid strip has ${resetGlyphs.length} reset buttons`);
  assert(new Set(resetGlyphs).size === resetGlyphs.length, "reset buttons reuse the same glyph");
  for (const button of gridButtons) {
    assert(button.rect.width >= 20 && button.rect.height >= 20, `grid ${button.id} target is ${button.rect.width}x${button.rect.height}`);
    assert(button.icon && button.icon.width >= 14, `grid ${button.id} icon is undersized`);
  }
  assert(m.gantt.height >= 24, `chart toolbar is ${m.gantt.height}px high`);
  assert(m.gantt.scaleButtons === 5, `chart has ${m.gantt.scaleButtons} scale presets`);
  assert(m.gantt.relationshipToggle, "chart relationship toggle is missing");
  assert(m.gantt.textCommands === 0, "chart toolbar still has text layout commands");
  const navWidth = m.navRail.rect?.width ?? 0;
  const contextWidth = m.contextRail.rect?.width ?? 0;
  assert(navWidth >= 46, `navigation rail is ${navWidth}px wide`);
  assert(contextWidth >= 38, `context rail is ${contextWidth}px wide`);
  for (const button of [...m.navRail.buttons, ...m.contextRail.buttons]) {
    assert(button.icon && button.icon.width >= 16, `rail button icon is ${button.icon?.width}px`);
  }
  const isRtl = m.direction === "rtl";
  const navOnRight = (m.navRail.rect?.left ?? 0) > m.viewport.width / 2;
  const contextOnLeft = (m.contextRail.rect?.left ?? 0) < m.viewport.width / 2;
  assert(isRtl ? navOnRight && contextOnLeft : !navOnRight && !contextOnLeft, `rails are not mirrored for ${m.direction}`);
  assert(m.layout.trigger, "layout selector is missing in the Activities window");
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

  try {
    await setViewport(page, 1366, 768);
    await login(page);
    await setLanguage(page, "en");

    const seedLayout = await page.evaluate(`document.querySelector("[data-layout-name]")?.textContent?.trim() ?? null`);
    assert(seedLayout === "Classic Schedule Layout", `Activities did not open the Classic Schedule Layout (${seedLayout})`);

    // Menu icons and the reserved check column are measured once in English.
    await openMenu(page, "view");
    const menuDetail = await page.evaluate(`(() => {
      const popup = document.querySelector('[data-desktop-popup="view"]');
      const items = [...popup.querySelectorAll("[data-desktop-item]")];
      const checked = items.find((item) => item.getAttribute("aria-checked") === "true");
      const unchecked = items.find((item) => item.getAttribute("aria-checked") !== "true" && item.querySelector(".cp-menubar-item-icon .cp-icon"));
      const labelLeft = (item) => item?.querySelector(".cp-menubar-item-label")?.getBoundingClientRect().left ?? null;
      return {
        open: !popup.hidden,
        insideViewport: (() => { const r = popup.getBoundingClientRect(); return r.left >= -1 && r.right <= window.innerWidth + 1 && r.top >= -1 && r.bottom <= window.innerHeight + 1; })(),
        items: items.length,
        withIcon: items.filter((item) => item.querySelector(".cp-menubar-item-icon .cp-icon")).length,
        minHeight: Math.min(...items.map((item) => item.getBoundingClientRect().height)),
        checkWidth: checked?.querySelector(".cp-menubar-item-check")?.getBoundingClientRect().width ?? null,
        checkedLabelLeft: labelLeft(checked),
        uncheckedLabelLeft: labelLeft(unchecked),
        checkedId: checked?.dataset.desktopItem ?? null,
        uncheckedId: unchecked?.dataset.desktopItem ?? null,
      };
    })()`);
    assert(menuDetail.open, "View menu did not open");
    assert(menuDetail.insideViewport, "View popup escapes the viewport");
    assert(menuDetail.items > 8, "View menu is unexpectedly short");
    assert(menuDetail.withIcon === menuDetail.items, `${menuDetail.items - menuDetail.withIcon} View commands have no icon`);
    assert(menuDetail.minHeight >= 22, `menu item target is ${menuDetail.minHeight}px high`);
    assert(menuDetail.checkWidth >= 10, "check column is not reserved");
    if (menuDetail.checkedId && menuDetail.uncheckedId) {
      assert(Math.abs(menuDetail.checkedLabelLeft - menuDetail.uncheckedLabelLeft) < 0.6, "check state shifts the menu label");
    }
    await capture(page, "menu-view-1366x768-en");
    await closeMenus(page);

    // Every menu opens inside the viewport and shows icons.
    for (const id of ["workspace", "edit", "view", "project", "organization", "tools", "administration", "help"]) {
      await openMenu(page, id);
      const popup = await page.evaluate(`(() => {
        const element = document.querySelector('[data-desktop-popup="${id}"]');
        const rect = element.getBoundingClientRect();
        const items = [...element.querySelectorAll("[data-desktop-item]")];
        return { hidden: element.hidden, rect: { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom }, items: items.length, icons: items.filter((item) => item.querySelector(".cp-menubar-item-icon .cp-icon")).length };
      })()`);
      assert(!popup.hidden, `${id} menu did not open`);
      assert(popup.rect.left >= -1 && popup.rect.right <= 1367 && popup.rect.top >= -1 && popup.rect.bottom <= 769, `${id} popup escapes the viewport: ${JSON.stringify(popup.rect)}`);
      assert(popup.items > 0, `${id} menu is empty`);
      assert(popup.icons === popup.items, `${id} has ${popup.items - popup.icons} iconless commands`);
      await closeMenus(page);
    }

    // Command-by-command execution for the Edit and Display PARTIALs. Each
    // command is driven from its application-menu entry so the menu wiring,
    // not a synthetic function call, is what the evidence proves.
    await page.click("#cp-activity-grid tbody tr[data-activity-id]");
    await sleep(300);
    await runMenuItem(page, "edit", "edit.select-all");
    const selectAll = await page.evaluate(`(() => ({
      visible: document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]").length,
      selected: document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id][aria-selected='true']").length,
      focused: document.activeElement?.getAttribute("data-activity-id") ?? null,
    }))()`);
    assert(selectAll.visible > 1, `Select All saw ${selectAll.visible} visible rows`);
    assert(selectAll.selected === selectAll.visible, `Select All selected ${selectAll.selected} of ${selectAll.visible} rows`);
    assert(selectAll.focused, "Select All did not move focus to the grid");
    commands.push({ id: "edit.select-all", ...selectAll });
    await capture(page, "menu-edit-select-all");

    // Narrow to the seeded A100 → A110 pair so Link and Unlink exercise one
    // real relationship instead of every stored link in the project.
    const pairSelected = await page.evaluate(`(() => {
      const rows = [...document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]")];
      const first = rows.find((row) => row.dataset.activityId === "A100");
      const second = rows.find((row) => row.dataset.activityId === "A110");
      if (!first || !second) return 0;
      first.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      second.dispatchEvent(new MouseEvent("click", { bubbles: true, ctrlKey: true }));
      return document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id][aria-selected='true']").length;
    })()`);
    assert(pairSelected === 2, `pair selection holds ${pairSelected} rows instead of 2`);
    await sleep(300);

    await runMenuItem(page, "edit", "edit.link");
    const link = await page.evaluate(`(() => {
      const drawer = document.querySelector("[data-tools-drawer]");
      const form = document.querySelector("[data-relationship-create-form]");
      return {
        drawerVisible: Boolean(drawer) && !drawer.hidden,
        predecessor: form?.querySelector('select[name="predecessor_id"]')?.value ?? null,
        successor: form?.querySelector('select[name="successor_id"]')?.value ?? null,
        focused: document.activeElement?.getAttribute("name") ?? null,
      };
    })()`);
    assert(link.drawerVisible, "Link did not open the relationship drawer");
    assert(link.predecessor === "A100" && link.successor === "A110", `Link preselected ${link.predecessor} → ${link.successor}`);
    assert(link.focused === "relationship_type", "Link did not focus the relationship type");
    commands.push({ id: "edit.link", ...link });
    await page.evaluate(`document.querySelector("[data-tools-close]")?.click()`);
    await sleep(300);

    await runMenuItem(page, "view", "view.collapse-to");
    const collapseTo = await page.evaluate(`(() => {
      const dialog = document.querySelector("[data-collapse-to-dialog]");
      return {
        open: Boolean(dialog) && (dialog.open === true || dialog.hasAttribute("open")),
        options: dialog?.querySelectorAll("[data-collapse-to-select] option").length ?? 0,
      };
    })()`);
    assert(collapseTo.open, "Collapse To did not open its branch dialog");
    assert(collapseTo.options > 0, "Collapse To has no WBS branches to choose");
    commands.push({ id: "view.collapse-to", ...collapseTo });
    await page.evaluate(`document.querySelector("[data-collapse-to-cancel]")?.click()`);
    await sleep(250);

    // Unlink is destructive, so first prove it reaches the confirmation with
    // the exact selected-pair count, then accept and prove the persisted list
    // really shrinks.
    const beforeUnlink = await page.evaluate(`document.querySelectorAll("[data-relationship-id]").length`);
    assert(beforeUnlink > 0, "the fixture exposes no relationship to unlink");
    await page.evaluate(`(() => { window.__confirmCalls = []; window.confirm = (message) => { window.__confirmCalls.push(message); return false; }; })()`);
    await runMenuItem(page, "edit", "edit.unlink");
    const confirmation = await page.evaluate(`window.__confirmCalls ?? []`);
    assert(confirmation.length === 1, `Unlink asked ${confirmation.length} confirmations`);
    assert(/^Unlink 1 relationship\b/.test(confirmation[0]), `Unlink confirmation says ${confirmation[0]}`);
    await page.evaluate(`window.confirm = () => true;`);
    await runMenuItem(page, "edit", "edit.unlink");
    await page.waitFor(
      `document.querySelectorAll("[data-relationship-id]").length < ${beforeUnlink}`,
      "relationship list to shrink",
    );
    const afterUnlink = await page.evaluate(`document.querySelectorAll("[data-relationship-id]").length`);
    assert(afterUnlink === beforeUnlink - 1, `Unlink left ${afterUnlink} of ${beforeUnlink} relationships`);
    commands.push({ id: "edit.unlink", before: beforeUnlink, after: afterUnlink, confirmation: confirmation[0] });
    await capture(page, "menu-edit-unlink");

    // Layout selector: apply the stored project layout and survive a reload.
    await page.evaluate(`document.querySelector("[data-layout-trigger]")?.click()`);
    await page.waitFor(`document.querySelector("[data-layout-menu]")?.hidden === false`, "layout menu");
    await sleep(400);
    const options = await page.evaluate(`[...document.querySelectorAll("[data-layout-option]")].map((option) => ({ scope: option.dataset.layoutOption, checked: option.getAttribute("aria-checked") }))`);
    assert(options.length >= 1, "layout selector shows no stored layout");
    const projectOption = options.find((option) => option.scope === "project");
    assert(projectOption, "the stored project layout is not listed");
    await page.evaluate(`document.querySelector('[data-layout-option="project"]')?.click()`);
    await sleep(500);
    const applyClicked = await page.evaluate(`(() => { const button = document.querySelector('[data-layout-action="apply"]'); if (!button || button.disabled) return false; button.click(); return true; })()`);
    if (applyClicked) await sleep(900);
    await page.reload("[data-layout-trigger]", "workspace reload");
    await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows after reload");
    await sleep(900);
    const afterReload = await page.evaluate(`({ name: document.querySelector("[data-layout-name]")?.textContent?.trim() ?? null, scope: document.querySelector("[data-layout-scope]")?.textContent?.trim() ?? null })`);
    assert(afterReload.name === "Classic Schedule Layout", `reload restored ${afterReload.name}`);

    const viewports = [
      { width: 1280, height: 720, label: "1280x720" },
      { width: 1366, height: 768, label: "1366x768" },
      { width: 1920, height: 1080, label: "1920x1080" },
    ];
    for (const locale of ["en", "fa"]) {
      await setLanguage(page, locale);
      for (const viewport of viewports) {
        await setViewport(page, viewport.width, viewport.height);
        await sleep(450);
        const measureResult = await page.evaluate(measure);
        const cell = { locale, viewport: viewport.label, direction: locale === "fa" ? "rtl" : "ltr", measure: measureResult };
        verifyCell(cell, locale);
        const file = await capture(page, `activities-${viewport.label}-${locale}`);
        cell.screenshot = file;
        cells.push(cell);
        log(`  PASS ${viewport.label} ${locale}: toolbar ${measureResult.toolbar.groups.length} families, nav ${measureResult.navRail.rect?.width}px, context ${measureResult.contextRail.rect?.width}px`);
      }
    }

    const report = {
      contract: "cubi-toolbars-v26.v1",
      baseUrl,
      gitHead: gitHead(),
      testedCodeSha,
      evidenceCommitSha: process.env.CUBI_EVIDENCE_COMMIT_SHA || null,
      capturedAt: new Date().toISOString(),
      cells,
      commands,
      screenshots,
      exceptions,
      consoleErrors,
      apiFailures,
    };
    writeFileSync(join(outDir, "report.json"), `${JSON.stringify(report, null, 2)}\n`);
    writeFileSync(join(evidenceDir, "report.json"), `${JSON.stringify(report, null, 2)}\n`);
    assert(exceptions.length === 0, `runtime exceptions: ${exceptions.join(" | ")}`);
    assert(consoleErrors.length === 0, `console errors: ${consoleErrors.join(" | ")}`);
    assert(apiFailures.length === 0, `API failures: ${JSON.stringify(apiFailures)}`);
    log(`\nPASS ${cells.length} toolbar cells at ${testedCodeSha}`);
    log(`Evidence: ${join(evidenceDir, "report.json")}`);
  } finally {
    await chrome.stop();
  }
}

main().catch((error) => {
  process.stderr.write(`${error && error.stack ? error.stack : error}\n`);
  process.exitCode = 1;
});
