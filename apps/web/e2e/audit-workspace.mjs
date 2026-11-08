#!/usr/bin/env node
/**
 * Desktop journey audit for the deployed workspace build.
 *
 * It drives the same preview runtime and CDP harness as the E2E suite but does
 * not assert feature behaviour: it records what each real window renders, how
 * the shell is laid out at the supported desktop sizes and whether the
 * floating assistant intrudes into page content. The output is a JSON report
 * plus one screenshot per window, so the audit can be reviewed visually rather
 * than trusted from a summary.
 *
 * Usage:
 *   CUBI_AUDIT_URL=http://127.0.0.1:4201 node apps/web/e2e/audit-workspace.mjs
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import {
  Page,
  artifactsDir,
  launchChrome,
  waitForHttp,
} from "./preview-e2e.mjs";

const baseUrl = (process.env.CUBI_AUDIT_URL ?? "http://127.0.0.1:4201").replace(/\/$/, "");
const auditDir = join(artifactsDir, "audit");
mkdirSync(auditDir, { recursive: true });

const MENUS = [
  "project", "eps", "wbs", "schedule", "activities", "progress", "resources",
  "assignments", "calendars", "roles", "cost", "expenses", "documents",
  "reports", "tracking", "control", "thresholds", "risks", "issues", "forms",
  "settings", "tools",
];

const REPORT = {
  contract: "cubi-desktop-journey-audit.v1",
  started_at: new Date().toISOString(),
  base_url: baseUrl,
  windows: [],
  dialogs: [],
  languages: [],
  sizes: [],
  assistant: [],
  journey: {},
  exceptions: [],
};

function log(message) {
  process.stdout.write(`${message}\n`);
}

async function measure(page) {
  return page.evaluate(`(() => {
    const rect = (selector) => {
      const element = document.querySelector(selector);
      if (!element) return null;
      const bounds = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return {
        x: Math.round(bounds.x), y: Math.round(bounds.y),
        width: Math.round(bounds.width), height: Math.round(bounds.height),
        display: style.display, visibility: style.visibility,
        hidden: element.hidden,
      };
    };
    const intersection = (a, b) => {
      if (!a || !b) return 0;
      const width = Math.max(0, Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x));
      const height = Math.max(0, Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y));
      return Math.round(width * height);
    };
    const shell = document.querySelector(".cp-p6-shell");
    const grid = document.querySelector("#cp-activity-grid");
    const gantt = document.querySelector("#cp-gantt");
    const details = document.querySelector(".cp-details");
    const split = document.querySelector("[data-resize-handle=\\"table-gantt\\"]");
    const detailsSplit = document.querySelector("[data-resize-handle=\\"details\\"]");
    return {
      viewport: { width: innerWidth, height: innerHeight },
      direction: getComputedStyle(document.body).direction,
      shell: rect(".cp-p6-shell"),
      body: rect(".cp-p6-body"),
      grid: rect("#cp-activity-grid"),
      gantt: rect("#cp-gantt"),
      details: rect(".cp-details"),
      tableSplitStyle: split?.style.getPropertyValue("--cp-split-table") ?? null,
      tableSplitAria: split?.getAttribute("aria-valuenow") ?? null,
      detailsSplitAria: detailsSplit?.getAttribute("aria-valuenow") ?? null,
      assistantLauncher: rect(".cubi-assistant-launcher"),
      assistantActionPanel: rect("#cp-ai-action-panel"),
      contentIntersection: {
        grid: intersection(rect("#cp-activity-grid"), rect(".cubi-assistant-launcher")),
        gantt: intersection(rect("#cp-gantt"), rect(".cubi-assistant-launcher")),
        details: intersection(rect(".cp-details"), rect(".cubi-assistant-launcher")),
      },
      hasHorizontalOverflow: document.documentElement.scrollWidth > innerWidth + 1,
      hasVerticalOverflow: document.documentElement.scrollHeight > innerHeight + 1,
    };
  })()`);
}

async function windowSummary(page) {
  return page.evaluate(`(() => {
    const stage = document.querySelector("#cp-p6-module-stage:not([hidden])");
    const root = stage || document.querySelector(".cp-p6-workspace") || document.body;
    const headings = [...root.querySelectorAll("h1, h2, h3")]
      .map((element) => element.textContent.trim())
      .filter(Boolean)
      .slice(0, 14);
    const unavailable = (root.textContent.match(/Not available|در دسترس نیست/g) ?? []).length;
    return {
      url: location.href,
      stage: Boolean(stage),
      headings,
      rows: root.querySelectorAll("table tbody tr").length,
      cards: root.querySelectorAll(".cp-register-card, .cp-module-card, .cp-wbs-card, .cp-fb-card").length,
      tables: root.querySelectorAll("table").length,
      forms: root.querySelectorAll("form").length,
      buttons: root.querySelectorAll("button").length,
      unavailable,
      text: root.textContent.replace(/\\s+/g, " ").trim().slice(0, 400),
    };
  })()`);
}

async function main() {
  const health = await waitForHttp(`${baseUrl}/preview/health`, 20000);
  REPORT.health = {
    status: health.status,
    production: health.production,
    demo_data: health.demo_data,
    project_count: health.project_count,
    activity_count: health.activity_count,
  };
  log(`Preview health ok: ${baseUrl}`);

  const chrome = await launchChrome();
  const page = new Page(chrome.cdp);
  try {
    await page.initialize();
    page.cdp.on("Runtime.exceptionThrown", (params) => {
      REPORT.exceptions.push(params.exceptionDetails?.exception?.description ?? params.exceptionDetails?.text ?? "unknown");
    });
    await page.cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1280, height: 720, deviceScaleFactor: 1, mobile: false,
    });

    // Home -> Login -> Workspace.
    await page.navigate(`${baseUrl}/`, ".cubi-reference-home", "home");
    REPORT.journey.home_title = await page.evaluate("document.title");

    await page.navigate(
      `${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`,
      "form",
      "login",
    );
    REPORT.journey.login_personas = await page.evaluate(
      `[...document.querySelectorAll("form button[type=submit]")].map((button) => button.textContent.replace(/\\s+/g, " ").trim().slice(0, 60))`,
    );
    const plannerClicked = await page.evaluate(`(() => {
      const button = [...document.querySelectorAll("form button")].find((item) => (item.textContent || "").trim().startsWith("Planner"));
      if (!button) return false;
      button.click();
      return true;
    })()`);
    await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
    REPORT.journey.project_selection = await page.evaluate(
      `[...document.querySelectorAll("[data-project-id]")].map((button) => ({ id: button.getAttribute("data-project-id"), label: button.textContent.replace(/\\s+/g, " ").trim() }))`,
    );
    await page.click('[data-project-id="preview-rps-01"]');
    await page.waitForSelector("#cp-activity-grid", "workspace grid");
    await sleep(1200);
    REPORT.journey.workspace_url = await page.evaluate("location.href");
    REPORT.journey.workspace_title = await page.evaluate("document.title");

    // Demo route must never render a parallel shell.
    await page.navigate(
      `${baseUrl}/app?project=preview-rps-01&view=visual`,
      "#cp-activity-grid",
      "visual route",
    );
    REPORT.journey.visual_route = await page.evaluate(`({
      url: location.href,
      demoNodes: document.querySelectorAll("[data-visual-demo], .cp-vd-shell").length,
      shell: Boolean(document.querySelector(".cp-app-shell")),
    })`);

    // Window catalogue at 1280x720.
    for (const key of MENUS) {
      const selector = key === "eps" || key === "activities" || key === "forms" || key === "tools"
        ? `[data-rail-action="${key}"]`
        : `[data-menu="${key}"]`;
      const clicked = await page.evaluate(`(() => {
        const target = document.querySelector(${JSON.stringify(`.cp-p6-rail ${selector}`)});
        if (!target) return false;
        target.click();
        return true;
      })()`);
      if (!clicked) {
        REPORT.windows.push({ key, missing: true });
        continue;
      }
      await sleep(700);
      const summary = await windowSummary(page);
      await page.screenshot(`audit/window-${key}-1280.png`);
      REPORT.windows.push({ key, ...summary });
      log(`  window ${key}: ${summary.headings[0] ?? "(no heading)"}`);
      // The Form Builder is an application-level module window; dismiss it
      // before the next rail action so the audit never captures a stale layer.
      await page.evaluate(`document.querySelector("[data-fb-close]")?.click()`);
      await sleep(250);
      // Return to the activities window so the next rail action starts clean.
      if (key !== "activities") {
        await page.evaluate(`document.querySelector('.cp-p6-rail [data-menu="schedule"]')?.click()`);
        await sleep(300);
      }
    }

    // Reset to a clean schedule window before dialogs, locales and sizes.
    await page.navigate(
      `${baseUrl}/app?project=preview-rps-01&view=live`,
      "#cp-activity-grid",
      "clean schedule window",
    );
    await sleep(900);
    await page.click('[data-activity-id="A100"]');
    await sleep(400);
    REPORT.journey.details_populated = await page.evaluate(`(() => {
      const details = document.querySelector(".cp-details");
      return {
        unavailable: (details?.textContent.match(/Not available|در دسترس نیست/g) ?? []).length,
        hasA100: (details?.textContent ?? "").includes("A100"),
        selectedRow: document.querySelector('[data-activity-id="A100"]')?.getAttribute("aria-selected"),
      };
    })()`);
    await page.screenshot("audit/details-selected.png");

    // Activity Network top layout: must be drawn from persisted relationships,
    // selectable, keyboard-renderable and persisted per project.
    await page.evaluate(`document.querySelector("[data-layout-options-open]")?.click()`);
    await sleep(300);
    const networkAvailable = await page.evaluate(`(() => {
      const select = document.querySelector("[data-top-layout]");
      const option = select?.querySelector('option[value="activity-network"]');
      if (!select || !option || option.disabled) return false;
      select.value = "activity-network";
      select.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    })()`);
    await sleep(800);
    const network = await page.evaluate(`(() => {
      const view = document.querySelector("[data-network-view]");
      const scroll = view?.querySelector(".cp-network-scroll");
      const nodes = [...(view?.querySelectorAll("[data-gantt-activity-id]") ?? [])];
      return {
        available: Boolean(view),
        nodes: nodes.length,
        edges: view?.querySelectorAll("[data-relationship-id]").length ?? 0,
        levels: Number(view?.getAttribute("data-network-levels") ?? 0),
        levelsAttribute: view?.getAttribute("data-network-levels") ?? null,
        hasA100: nodes.some((node) => node.getAttribute("data-gantt-activity-id") === "A100"),
        keyboardFocusable: nodes.every((node) => node.getAttribute("tabindex") === "0"),
        scrollWidth: scroll?.scrollWidth ?? 0,
        clientWidth: scroll?.clientWidth ?? 0,
        note: view?.querySelector(".cp-p6-network-note")?.textContent?.trim() ?? null,
      };
    })()`);
    await page.screenshot("audit/window-network-1280.png");
    await page.evaluate(`(() => {
      const node = document.querySelector('[data-network-view] [data-gantt-activity-id="A100"]');
      if (!node) return false;
      // SVG elements do not expose HTMLElement.click(); dispatch the same
      // bubbling click a real pointer produces.
      node.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
      return true;
    })()`);
    await sleep(450);
    const networkSelection = await page.evaluate(`(() => {
      const node = document.querySelector('[data-network-view] [data-gantt-activity-id="A100"]');
      const details = document.querySelector(".cp-details")?.textContent ?? "";
      return { pressed: node?.getAttribute("aria-pressed") ?? null, detailsHasA100: details.includes("A100") };
    })()`);
    await page.reload("[data-network-view]", "activity network persists after reload");
    const networkPersisted = await page.evaluate(`Boolean(document.querySelector("[data-network-view]"))`);
    // Restore the table + Gantt layout for the remaining visual checks.
    await page.evaluate(`document.querySelector("[data-layout-options-open]")?.click()`);
    await sleep(250);
    await page.evaluate(`(() => {
      const select = document.querySelector("[data-top-layout]");
      if (!select) return false;
      select.value = "table-gantt";
      select.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    })()`);
    await page.waitForSelector("#cp-activity-grid", "table layout restored");
    REPORT.journey.activity_network = { available: networkAvailable, ...network, selection: networkSelection, persisted: networkPersisted };
    log(`  network: ${network.nodes} nodes / ${network.edges} edges / levels ${network.levels}, persisted ${networkPersisted}, selection ${networkSelection.pressed}`);
    await page.click('[data-activity-id="A100"]');
    await sleep(300);

    // Dialogs.
    for (const [id, command] of [
      ["group-sort", "dialog.group-sort"],
      ["timescale", "dialog.timescale"],
      ["bars", "dialog.bars"],
      ["font-row", "dialog.font-row"],
      ["user-preferences", "dialog.user-preferences"],
    ]) {
      const opened = await page.evaluate(`(() => {
        const button = document.querySelector('[data-desktop-command="${command}"]');
        if (!button) return false;
        button.click();
        return true;
      })()`);
      await sleep(350);
      const state = await page.evaluate(`(() => {
        const dialog = document.querySelector('[data-desktop-dialog="${id}"]');
        return {
          found: Boolean(dialog),
          open: Boolean(dialog?.open),
          heading: dialog?.querySelector("h2")?.textContent?.trim() ?? null,
          controls: dialog ? dialog.querySelectorAll("input, select, button").length : 0,
        };
      })()`);
      if (state.open) await page.screenshot(`audit/dialog-${id}.png`);
      REPORT.dialogs.push({ id, opened, ...state });
      await page.evaluate(`document.querySelector('[data-desktop-dialog="${id}"] [data-dialog-cancel]')?.click()`);
      await sleep(200);
    }

    // Activity Table presentation: font family/size, text and background
    // colour, row-height mode, activity icons and line numbers must reach the
    // real grid and survive a reload through the saved layout.
    const tableSnapshot = `(() => {
      const table = document.querySelector("#cp-activity-grid table");
      const cell = document.querySelector("#cp-activity-grid tbody td");
      const style = table ? getComputedStyle(table) : null;
      return {
        fontFamily: style?.fontFamily ?? null,
        fontSize: style?.fontSize ?? null,
        color: style?.color ?? null,
        background: style?.backgroundColor ?? null,
        rowHeight: cell ? Math.round(cell.getBoundingClientRect().height) : 0,
        lineNumbers: document.querySelectorAll("#cp-activity-grid .cp-p6-line-number").length,
        icons: document.querySelectorAll("#cp-activity-grid .cp-p6-activity-icon").length,
        dates: [...document.querySelectorAll('#cp-activity-grid tbody td[data-column-type="date"]')].map((cell) => cell.textContent.trim()),
      };
    })()`;
    const tableBefore = await page.evaluate(tableSnapshot);
    await page.screenshot("audit/table-before-1280.png");

    const preferencesPatch = await page.evaluate(`(() => {
      document.querySelector('[data-desktop-command="dialog.user-preferences"]')?.click();
      const form = document.querySelector('dialog[data-desktop-dialog="user-preferences"] form');
      if (!form) return { form: false };
      const set = (name, value) => {
        const control = form.querySelector('[name="' + name + '"]');
        if (!control) return false;
        control.value = value;
        return true;
      };
      const check = (name, checked) => {
        const control = form.querySelector('[name="' + name + '"]');
        if (!control) return false;
        control.checked = checked;
        return true;
      };
      const fixed = form.querySelector('[name="rowHeightMode"][value="fixed"]');
      if (fixed) fixed.checked = true;
      const fields = ["fontFamily", "fontSize", "textColor", "backgroundColor", "rowHeight", "rowHeightMode", "showIcons", "lineNumbers"].map((name) => Boolean(form.querySelector('[name="' + name + '"]')));
      set("fontFamily", "cairo");
      set("fontSize", "13");
      set("textColor", "#102a43");
      set("backgroundColor", "#eef3f8");
      set("rowHeight", "30");
      check("showIcons", true);
      check("lineNumbers", true);
      form.requestSubmit();
      return { form: true, fields };
    })()`);
    await sleep(500);
    const tableCustom = await page.evaluate(tableSnapshot);
    await page.screenshot("audit/table-custom-1280.png");

    // The table and the chart are one vertical surface: scrolling one pane must
    // move the other so bars stay on their activity rows.
    const scrollSync = await page.evaluate(`(async () => {
      const table = document.querySelector("#cp-activity-grid .cp-table-wrap");
      const chart = document.querySelector("#cp-gantt .cp-gantt-chart");
      if (!table || !chart) return null;
      const settle = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const aligned = () => {
        const firstTable = document.querySelector("#cp-activity-grid tbody tr");
        const firstChart = document.querySelector("#cp-gantt .cp-gantt-row");
        if (!firstTable || !firstChart) return null;
        return Math.abs(firstTable.getBoundingClientRect().top - firstChart.getBoundingClientRect().top) <= 1;
      };
      const rowAligned = aligned();
      table.scrollTop = 45;
      await settle();
      const chartFollows = chart.scrollTop;
      chart.scrollTop = 10;
      await settle();
      const tableFollows = table.scrollTop;
      table.scrollTop = 0;
      chart.scrollTop = 0;
      await settle();
      return {
        chartFollows,
        tableFollows,
        tableScrollable: table.scrollHeight > table.clientHeight,
        chartScrollable: chart.scrollHeight > chart.clientHeight,
        rowAligned,
        rowAlignedAfterReset: aligned(),
      };
    })()`, { awaitPromise: true });
    REPORT.journey.gantt_table_sync = scrollSync;
    log(`  table/chart sync: chart ${scrollSync?.chartFollows}, table ${scrollSync?.tableFollows}, aligned ${scrollSync?.rowAligned}`);

    await page.reload("#cp-activity-grid table", "table presentation persists after reload");
    await sleep(500);
    const tablePersisted = await page.evaluate(tableSnapshot);
    REPORT.journey.table_presentation = {
      before: tableBefore,
      patch: preferencesPatch,
      applied: tableCustom,
      persisted: tablePersisted,
      calendarDatesUnchanged: JSON.stringify(tableBefore.dates) === JSON.stringify(tablePersisted.dates),
    };
    log(`  table presentation persisted: ${tablePersisted.fontSize} / ${tablePersisted.fontFamily} / row ${tablePersisted.rowHeight}px / numbers ${tablePersisted.lineNumbers} / icons ${tablePersisted.icons}`);

    // Optimize by content must let long activity names wrap instead of clipping.
    const contentModeApplied = await page.evaluate(`(() => {
      document.querySelector('[data-desktop-command="dialog.user-preferences"]')?.click();
      const form = document.querySelector('dialog[data-desktop-dialog="user-preferences"] form');
      if (!form) return false;
      const radio = form.querySelector('[name="rowHeightMode"][value="content"]');
      if (radio) radio.checked = true;
      const height = form.querySelector('[name="rowHeight"]');
      if (height) height.value = "22";
      form.requestSubmit();
      return true;
    })()`);
    await sleep(500);
    const contentMode = await page.evaluate(`(() => {
      const workspace = document.querySelector("[data-table-row-mode]");
      const cell = document.querySelector('#cp-activity-grid tbody td[data-column-id$=".name"], #cp-activity-grid tbody td[data-column-id="activity_name"]');
      return {
        mode: workspace?.getAttribute("data-table-row-mode") ?? null,
        whiteSpace: cell ? getComputedStyle(cell).whiteSpace : null,
        height: cell ? Math.round(cell.getBoundingClientRect().height) : 0,
      };
    })()`);
    await page.screenshot("audit/table-content-row-mode-1280.png");
    REPORT.journey.table_row_mode = { applied: contentModeApplied, ...contentMode };
    log(`  row mode ${contentMode.mode}: white-space ${contentMode.whiteSpace}, cell ${contentMode.height}px`);

    // Explicit Save Layout, then restore the shipped defaults so the size and
    // locale screenshots keep the documented density.
    const savedLayout = await page.evaluate(`(() => {
      const button = document.querySelector('[data-desktop-command="layout.save"]');
      if (!button) return { available: false };
      const disabled = button.disabled || button.getAttribute("aria-disabled") === "true";
      if (!disabled) button.click();
      return { available: true, disabled, title: button.getAttribute("title") };
    })()`);
    await sleep(900);
    const layoutNotice = await page.evaluate(`(() => {
      const status = document.querySelector(".cp-statusbar")?.textContent ?? "";
      const failed = /failed|خطا|تعارض|conflict/i.test(status);
      return { failed, status: status.replace(/\\s+/g, " ").trim().slice(0, 200) };
    })()`);
    await page.evaluate(`(() => {
      document.querySelector('[data-desktop-command="dialog.user-preferences"]')?.click();
      document.querySelector('dialog[data-desktop-dialog="user-preferences"] [data-dialog-default]')?.click();
    })()`);
    await sleep(500);
    const tableRestored = await page.evaluate(tableSnapshot);
    REPORT.journey.layout_save_restore = {
      save: savedLayout,
      notice: layoutNotice,
      restored: tableRestored,
      restoredMatchesBefore: JSON.stringify(tableBefore) === JSON.stringify(tableRestored),
    };
    log(`  layout save ${savedLayout.available ? (savedLayout.disabled ? "disabled" : "clicked") : "missing"}; restored ${tableRestored.fontSize} / row ${tableRestored.rowHeight}px`);

    // Activity Table row height must actually change the table, not only the form.
    const tableFontRowApplied = await page.evaluate(`(() => {
      const open = document.querySelector('[data-desktop-command="dialog.font-row"]');
      open?.click();
      const form = document.querySelector('dialog[data-desktop-dialog="font-row"] form');
      if (!form) return null;
      const height = form.querySelector('input[name="rowHeight"]');
      const fontSize = form.querySelector('select[name="fontSize"]');
      if (!height || !fontSize) return null;
      height.value = "30";
      fontSize.value = "12";
      form.requestSubmit();
      const cell = document.querySelector("#cp-activity-grid tbody td");
      const table = document.querySelector("#cp-activity-grid table");
      return {
        rowHeight: cell ? Math.round(cell.getBoundingClientRect().height) : 0,
        fontSize: table ? getComputedStyle(table).fontSize : null,
        cssHeight: getComputedStyle(document.documentElement).getPropertyValue("--cp-p6-row-height").trim(),
      };
    })()`);
    await sleep(350);
    const tableFontRowMeasured = await page.evaluate(`(() => {
      const cell = document.querySelector("#cp-activity-grid tbody td");
      const table = document.querySelector("#cp-activity-grid table");
      return {
        rowHeight: cell ? Math.round(cell.getBoundingClientRect().height) : 0,
        fontSize: table ? getComputedStyle(table).fontSize : null,
      };
    })()`);
    // Restore the default row so later screenshots keep the baseline density.
    await page.evaluate(`(() => {
      document.querySelector('[data-desktop-command="dialog.font-row"]')?.click();
      const form = document.querySelector('dialog[data-desktop-dialog="font-row"] form');
      if (!form) return false;
      form.querySelector('input[name="rowHeight"]').value = "22";
      form.querySelector('select[name="fontSize"]').value = "11";
      form.requestSubmit();
      return true;
    })()`);
    await sleep(300);
    REPORT.journey.table_font_row = { patchRead: tableFontRowApplied, applied: tableFontRowMeasured };
    log(`  table font/row applied: ${JSON.stringify(tableFontRowMeasured)}`);

    // Gantt Bar Styles: independent shape, colour, pattern, label and height
    // settings must reach the real bars while schedule dates stay untouched.
    const ganttSnapshot = `(() => {
      const rows = [...document.querySelectorAll("#cp-gantt .cp-gantt-row")];
      const bars = [...document.querySelectorAll("#cp-gantt .cp-gantt-bar")];
      const task = document.querySelector("#cp-gantt .cp-gantt-bar-task");
      const rect = (element) => (element ? element.getBoundingClientRect() : null);
      const overflow = rows.map((row) => {
        const bounds = rect(row);
        return [...row.querySelectorAll(".cp-gantt-bar")].filter((bar) => {
          const barBounds = rect(bar);
          return barBounds.top < bounds.top - 1 || barBounds.bottom > bounds.bottom + 1;
        }).map((bar) => ({
          activity: row.getAttribute("data-gantt-activity-id"),
          kind: bar.getAttribute("data-gantt-bar-kind"),
          rowTop: Math.round(bounds.top),
          rowBottom: Math.round(bounds.bottom),
          barTop: Math.round(rect(bar).top),
          barBottom: Math.round(rect(bar).bottom),
        }));
      }).flat();
      return {
        rowCount: rows.length,
        barCount: bars.length,
        task: task ? {
          height: Math.round(rect(task).height),
          background: getComputedStyle(task).backgroundColor,
          pattern: task.getAttribute("data-gantt-bar-pattern"),
          shape: task.getAttribute("data-gantt-bar-shape"),
        } : null,
        taskLabel: task?.querySelector(".cp-gantt-bar-label")?.textContent?.trim() ?? null,
        overflowRows: overflow.length,
        overflowDetail: overflow,
        tableDates: [...document.querySelectorAll('#cp-activity-grid tbody td[data-column-type="date"]')].map((cell) => cell.textContent.trim()).join("|"),
        rows: rows.map((row) => ({
          activity: row.getAttribute("data-gantt-activity-id"),
          height: Math.round(rect(row).height),
          bars: row.querySelectorAll(".cp-gantt-bar").length,
        })),
      };
    })()`;
    const ganttBefore = await page.evaluate(ganttSnapshot);
    await page.screenshot("audit/gantt-before-1280.png");
    const barsPatch = await page.evaluate(`(() => {
      document.querySelector('[data-desktop-command="dialog.bars"]')?.click();
      const form = document.querySelector('dialog[data-desktop-dialog="bars"] form');
      if (!form) return { form: false };
      const set = (name, value) => {
        const control = form.querySelector('[name="' + name + '"]');
        if (!control) return false;
        control.value = value;
        return true;
      };
      const check = (name, checked) => {
        const control = form.querySelector('[name="' + name + '"]');
        if (!control) return false;
        control.checked = checked;
        return true;
      };
      check("bar.task.visible", true);
      set("bar.task.height", "18");
      set("bar.task.pattern", "striped");
      set("bar.task.bodyColor", "#0f4c81");
      set("bar.task.startColor", "#0f4c81");
      set("bar.task.finishColor", "#0f4c81");
      set("bar.task.labelField", "activity-name");
      set("bar.task.labelPosition", "right");
      check("bar.summary.visible", true);
      set("bar.summary.height", "10");
      set("bar.summary.pattern", "hatched");
      set("bar.summary.bodyColor", "#17324d");
      set("bar.milestone.visible", true);
      set("bar.milestone.bodyShape", "diamond");
      set("bar.milestone.bodyColor", "#c26a2e");
      form.requestSubmit();
      return {
        form: true,
        taskFields: ["visible", "height", "pattern", "bodyColor", "labelField", "labelPosition"].map((field) => Boolean(form.querySelector('[name="bar.task.' + field + '"]'))),
      };
    })()`);
    await sleep(600);
    const ganttCustom = await page.evaluate(ganttSnapshot);
    await page.screenshot("audit/gantt-custom-1280.png");
    await page.reload("#cp-gantt .cp-gantt-row", "bar styles persist after reload");
    await sleep(500);
    const ganttPersisted = await page.evaluate(ganttSnapshot);
    REPORT.journey.gantt_bar_styles = {
      before: ganttBefore,
      patch: barsPatch,
      applied: ganttCustom,
      persisted: ganttPersisted,
      scheduleDatesUnchanged: ganttBefore.tableDates === ganttCustom.tableDates
        && ganttBefore.tableDates === ganttPersisted.tableDates,
      rowsStable: ganttBefore.rowCount === ganttCustom.rowCount
        && ganttBefore.rowCount === ganttPersisted.rowCount,
      noBarOverflow: ganttCustom.overflowRows === 0 && ganttPersisted.overflowRows === 0,
    };
    log(`  bar styles: ${ganttPersisted.task?.height}px ${ganttPersisted.task?.pattern} ${ganttPersisted.task?.background}; rows ${ganttPersisted.rowCount}; overflow ${JSON.stringify(ganttPersisted.overflowDetail)}`);
    // Restore defaults for the remaining locale/size captures.
    await page.evaluate(`(() => {
      document.querySelector('[data-desktop-command="dialog.user-preferences"]')?.click();
      document.querySelector('dialog[data-desktop-dialog="user-preferences"] [data-dialog-default]')?.click();
    })()`);
    await sleep(400);

    // Eight-language matrix at 1280x720.
    REPORT.language_options = await page.evaluate(`(() => {
      const select = document.querySelector("[data-workspace-language]");
      return [...(select?.options ?? [])].map((option) => ({ value: option.value, label: option.textContent.trim() }));
    })()`);
    for (const locale of ["en", "fa", "ar", "de", "zh", "fr", "ja", "ko"]) {
      const changed = await page.evaluate(`(() => {
        const select = document.querySelector("[data-workspace-language]");
        if (!select) return false;
        select.value = ${JSON.stringify(locale)};
        select.dispatchEvent(new Event("change", { bubbles: true }));
        return true;
      })()`);
      await sleep(700);
      const state = await page.evaluate(`({
        lang: document.documentElement.lang,
        dir: getComputedStyle(document.body).direction,
        htmlDir: document.documentElement.dir,
        heading: document.querySelector(".cp-p6-activity-heading strong")?.textContent?.trim() ?? null,
        tab: document.querySelector('[role=tab][aria-selected=true]')?.textContent?.replace(/\\s+/g, " ").trim() ?? null,
        shellWidth: Math.round(document.querySelector(".cp-p6-shell")?.getBoundingClientRect().width ?? 0),
      })`);
      await page.screenshot(`audit/locale-${locale}.png`);
      REPORT.languages.push({ locale, changed, ...state });
      log(`  locale ${locale}: ${state.dir} / ${state.heading}`);
    }

    // Jalali and Gregorian calendars.
    await page.evaluate(`(() => {
      const select = document.querySelector("[data-workspace-language]");
      select.value = "en";
      select.dispatchEvent(new Event("change", { bubbles: true }));
    })()`);
    await sleep(500);
    for (const mode of ["gregorian", "jalali", "gregorian"]) {
      const current = await page.evaluate(`document.querySelector("[data-calendar-mode]")?.getAttribute("data-calendar-mode") ?? null`);
      if (current !== mode) {
        await page.click("[data-calendar-mode]");
        await sleep(500);
      }
      const dates = await page.evaluate(`(() => {
        const cells = [...document.querySelectorAll('#cp-activity-grid tbody td')].map((cell) => cell.textContent.trim());
        const samples = cells.filter((value) => /^\\d{4}-\\d{2}-\\d{2}$/.test(value)
          || /^[\\u06F0-\\u06F9]{4}\\/[\\u06F0-\\u06F9]{1,2}\\/[\\u06F0-\\u06F9]{1,2}$/.test(value)).slice(0, 3);
        const format = samples.some((value) => /^\\d{4}-\\d{2}-\\d{2}$/.test(value))
          ? "gregorian"
          : samples.length ? "jalali" : "unknown";
        const dateCells = [...document.querySelectorAll('#cp-activity-grid tbody td[data-column-type="date"]')].slice(0, 6).map((cell) => ({
          text: cell.textContent.trim(),
          clientWidth: cell.clientWidth,
          scrollWidth: cell.scrollWidth,
          clipped: cell.scrollWidth > cell.clientWidth + 1,
        }));
        return {
          // data-calendar-mode stores the mode the next click would select.
          nextMode: document.querySelector("[data-calendar-mode]")?.getAttribute("data-calendar-mode") ?? null,
          format,
          button: document.querySelector("[data-calendar-mode]")?.textContent?.trim() ?? null,
          samples,
          dateCells,
          clippedCount: dateCells.filter((cell) => cell.clipped).length,
        };
      })()`);
      const slot = REPORT.journey[`calendar_${dates.format}`] ? 2 : 1;
      REPORT.journey[`calendar_${dates.format}_${slot}`] = dates;
      await page.screenshot(`audit/calendar-${dates.format}.png`);
      log(`  calendar ${dates.format}: ${dates.samples.join(", ")}, clipped ${dates.clippedCount}/${dates.dateCells.length}`);
    }

    // Pane geometry at supported desktop sizes.
    for (const size of [
      { width: 1024, height: 768 },
      { width: 1280, height: 720 },
      { width: 1366, height: 768 },
      { width: 1440, height: 900 },
      { width: 1920, height: 1080 },
    ]) {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", {
        width: size.width, height: size.height, deviceScaleFactor: 1, mobile: false,
      });
      await sleep(900);
      const measurement = await measure(page);
      await page.screenshot(`audit/size-${size.width}x${size.height}.png`);
      REPORT.sizes.push({ requested: size, ...measurement });
      log(`  ${size.width}x${size.height}: grid ${measurement.grid?.width}x${measurement.grid?.height}, gantt ${measurement.gantt?.width}, details ${measurement.details?.height}, assistant intersects ${JSON.stringify(measurement.contentIntersection)}`);
    }

    // Assistant must not sit on top of page content at any size.
    for (const width of [1024, 1280, 1366, 1440, 1920]) {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", {
        width,
        height: width === 1920 ? 1080 : width === 1440 ? 900 : width === 1024 ? 768 : 720,
        deviceScaleFactor: 1, mobile: false,
      });
      await sleep(500);
      const measurement = await measure(page);
      REPORT.assistant.push({
        width,
        launcher: measurement.assistantLauncher,
        actionPanel: measurement.assistantActionPanel,
        intersection: measurement.contentIntersection,
      });
    }

    // Logout returns to the public home, not to another shell.
    await page.cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1280, height: 720, deviceScaleFactor: 1, mobile: false,
    });
    await sleep(300);
    const loggedOut = await page.evaluate(`(() => {
      const button = document.querySelector('form button[type="submit"], button');
      const signOut = [...document.querySelectorAll("button")].find((item) => /sign out/i.test(item.textContent || ""));
      if (!signOut) return false;
      signOut.click();
      return true;
    })()`);
    await sleep(1200);
    REPORT.journey.logout = {
      clicked: loggedOut,
      url: await page.evaluate("location.href"),
      title: await page.evaluate("document.title"),
      hasHome: await page.evaluate("Boolean(document.querySelector('.cubi-reference-home'))"),
      hasShell: await page.evaluate("Boolean(document.querySelector('.cp-app-shell'))"),
    };
  } finally {
    page.cdp.close();
    chrome.cdp.close();
    await chrome.stop();
  }

  REPORT.finished_at = new Date().toISOString();
  const file = join(auditDir, "desktop-audit.json");
  writeFileSync(file, JSON.stringify(REPORT, null, 2));
  log(`Audit report: ${file}`);
  log(`Windows: ${REPORT.windows.length}, dialogs: ${REPORT.dialogs.length}, languages: ${REPORT.languages.length}, sizes: ${REPORT.sizes.length}`);
}

main().catch((error) => {
  REPORT.error = error instanceof Error ? error.stack ?? error.message : String(error);
  const file = join(auditDir, "desktop-audit.json");
  writeFileSync(file, JSON.stringify(REPORT, null, 2));
  log(`AUDIT FAILED: ${REPORT.error}`);
  process.exitCode = 1;
});
