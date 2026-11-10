#!/usr/bin/env node
/**
 * Browser checks for the CUBI workspace master implementation order.
 *
 * It drives the real preview runtime (no mocked APIs) and proves:
 *  - hiding Details releases its whole grid allocation at 1280x800, 1440x900
 *    and 1920x1080, with the table/Gantt reaching the bottom of the workspace;
 *  - showing it again restores the previous height;
 *  - the bottom-bar Details toggle and the View menu command share one state;
 *  - Details visibility and the selected theme survive a full reload;
 *  - CUBI Classic and CUBI Modern 3D expose the same commands and render real
 *    rows and bars;
 *  - Russian, French, Japanese, Korean and Arabic translate the command surface,
 *    with Arabic in RTL.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4174 node e2e/workspace-master-order.mjs
 */

import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import {
  Page,
  launchChrome,
  waitForHttp,
  artifactsDir,
  gitHead,
} from "./preview-e2e.mjs";

const baseUrl = (process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4174").replace(/\/$/, "");
const outDir = join(artifactsDir, "master-order");
mkdirSync(outDir, { recursive: true });

const checks = [];
const measurements = {};

function record(name, details = {}) {
  checks.push({ name, at: new Date().toISOString(), ...details });
  process.stdout.write(`  ok ${name}\n`);
}

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

const layoutSnapshot = `(() => {
  const box = (selector) => {
    const element = document.querySelector(selector);
    if (!element) return null;
    const rect = element.getBoundingClientRect();
    return {
      x: Math.round(rect.x), y: Math.round(rect.y),
      width: Math.round(rect.width), height: Math.round(rect.height),
      bottom: Math.round(rect.bottom),
    };
  };
  const main = document.querySelector(".cp-main");
  const details = document.querySelector("#cp-details");
  const splitter = document.querySelector("[data-details-splitter]");
  const toggle = document.querySelector("[data-details-toggle]");
  return {
    viewport: { width: innerWidth, height: innerHeight },
    main: box(".cp-main"),
    primary: box(".cp-p6-primary"),
    grid: box("#cp-activity-grid"),
    gantt: box("#cp-gantt"),
    details: box("#cp-details"),
    splitter: box("[data-details-splitter]"),
    toggle: box("[data-details-toggle]"),
    calendar: box("[data-calendar-mode]"),
    detailsDisplay: details ? getComputedStyle(details).display : null,
    splitterDisplay: splitter ? getComputedStyle(splitter).display : null,
    collapsed: main ? main.getAttribute("data-details-collapsed") : null,
    rows: main ? getComputedStyle(main).gridTemplateRows : null,
    pressed: toggle ? toggle.getAttribute("aria-pressed") : null,
    rowCount: document.querySelectorAll("#cp-activity-grid tbody tr").length,
    barCount: document.querySelectorAll("#cp-gantt .cp-gantt-bar").length,
    theme: document.documentElement.getAttribute("data-cubi-theme"),
  };
})()`;

const chromeSnapshot = `(() => {
  const style = (selector) => {
    const element = document.querySelector(selector);
    return element ? getComputedStyle(element) : null;
  };
  const pick = (computed, keys) => {
    if (!computed) return null;
    const out = {};
    for (const key of keys) out[key] = computed[key];
    return out;
  };
  return {
    theme: document.documentElement.getAttribute("data-cubi-theme"),
    body: pick(style("body"), ["backgroundImage", "backgroundColor", "color", "fontFamily"]),
    desktop: pick(style(".cp-desktop"), ["backgroundImage", "backgroundColor", "borderRadius", "boxShadow"]),
    titlebar: pick(style(".cp-p6 .cp-titlebar"), ["backgroundImage", "backgroundColor", "borderBottom", "color"]),
    toolbar: pick(style(".cp-p6 .cp-toolbar"), ["backgroundImage", "backgroundColor"]),
    gridHeader: pick(style("#cp-activity-grid thead th"), ["backgroundImage", "backgroundColor", "color"]),
    details: pick(style("#cp-details"), ["backgroundColor", "borderRadius", "boxShadow"]),
    statusbar: pick(style(".cp-app-status"), ["backgroundImage", "backgroundColor", "color"]),
    toggleRadius: style("[data-details-toggle]")?.borderRadius ?? null,
  };
})()`;

const menuViewSnapshot = `(() => {
  const popup = document.querySelector('[data-desktop-popup="view"]');
  return {
    hasPopup: Boolean(popup),
    visible: popup ? !popup.hidden : false,
    items: popup ? Array.from(popup.querySelectorAll("[data-desktop-item]")).map((item) => ({
      id: item.dataset.desktopItem,
      label: item.textContent.trim(),
      checked: item.getAttribute("aria-checked"),
    })) : [],
  };
})()`;

async function loginAndOpenWorkspace(page) {
  await page.navigate(
    `${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`,
    "form",
    "login",
  );
  const signedIn = await page.evaluate(`(() => {
    const link = document.querySelector('a[href*="/app"]');
    if (link) { link.click(); return "link"; }
    const button = [...document.querySelectorAll("form button")].find((item) =>
      (item.textContent || "").trim().startsWith("Planner"));
    if (!button) return null;
    button.click();
    return "persona";
  })()`);
  assert(signedIn, "preview login must offer a planner session");
  await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
  await page.click('[data-project-id="preview-rps-01"]');
  await page.waitForSelector("#cp-activity-grid tbody tr", "workspace rows");
  await sleep(1200);
}

async function setLanguage(page, locale) {
  await page.setSelect("[data-workspace-language]", locale);
  await page.waitFor(
    `document.documentElement.lang === "${locale}" && document.documentElement.dir === "${locale === "fa" || locale === "ar" ? "rtl" : "ltr"}"`,
    `${locale} workspace locale`,
  );
  await page.waitForSelector("#cp-activity-grid tbody tr", `${locale} rows`);
  await sleep(600);
}

async function setTheme(page, theme) {
  await page.setSelect("[data-workspace-theme]", theme);
  await page.waitFor(
    `document.documentElement.getAttribute("data-cubi-theme") === "${theme}"`,
    `${theme} theme applied`,
  );
  await sleep(350);
}

async function ensureDetailsVisible(page) {
  const pressed = await page.evaluate(
    `document.querySelector("[data-details-toggle]")?.getAttribute("aria-pressed")`,
  );
  if (pressed !== "true") {
    await page.click("[data-details-toggle]");
    await page.waitFor(
      `document.querySelector("[data-details-toggle]")?.getAttribute("aria-pressed") === "true"`,
      "details visible",
    );
    await sleep(350);
  }
}

async function toggleDetails(page) {
  const before = await page.evaluate(
    `document.querySelector("[data-details-toggle]")?.getAttribute("aria-pressed")`,
  );
  await page.click("[data-details-toggle]");
  await page.waitFor(
    `document.querySelector("[data-details-toggle]")?.getAttribute("aria-pressed") === "${before === "true" ? "false" : "true"}"`,
    `details toggled from ${before}`,
  );
  await sleep(400);
  return before;
}

async function main() {
  const health = await waitForHttp(`${baseUrl}/preview/health`, 20000);
  assert(health.status === "ok" || health.status === 200, `preview health ${health.status}`);

  const chrome = await launchChrome();
  const page = new Page(chrome.cdp);
  const report = {
    contract: "cubi-workspace-master-order.v1",
    baseUrl,
    gitHead: gitHead(),
    startedAt: new Date().toISOString(),
    checks,
    measurements,
  };
  try {
    await page.initialize();
    await page.cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1440,
      height: 900,
      deviceScaleFactor: 1,
      mobile: false,
    });
    await loginAndOpenWorkspace(page);
    await setLanguage(page, "en");
    await setTheme(page, "classic");
    await ensureDetailsVisible(page);

    // ---------------------------------------------------------------------
    // Phase 1 + 2 — Details allocation, toggle placement and View command.
    // ---------------------------------------------------------------------
    const viewports = [
      [1280, 800],
      [1440, 900],
      [1920, 1080],
    ];
    for (const [width, height] of viewports) {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", {
        width,
        height,
        deviceScaleFactor: 1,
        mobile: false,
      });
      await sleep(500);

      const shown = await page.evaluate(layoutSnapshot);
      assert(shown.pressed === "true", `${width}x${height} details must start visible`);
      assert(shown.details && shown.details.height > 90, `${width}x${height} details height ${shown.details?.height}`);
      assert(shown.collapsed === "false", `${width}x${height} main must not be collapsed while Details is visible`);
      assert(shown.rowCount > 0, `${width}x${height} activity rows must render`);
      assert(shown.barCount > 0, `${width}x${height} Gantt bars must render`);
      // The Details toggle sits in the lowest bar, to the right of the calendar switch.
      assert(shown.toggle && shown.calendar, `${width}x${height} toggle and calendar must both exist`);
      assert(
        Math.abs(shown.toggle.y - shown.calendar.y) <= 2,
        `${width}x${height} Details toggle must share the calendar row (${shown.toggle.y} vs ${shown.calendar.y})`,
      );
      assert(
        shown.toggle.x > shown.calendar.x,
        `${width}x${height} Details toggle must sit beside the calendar selector`,
      );
      // The fixed local-preview banner must not cover the lowest workspace bar.
      assert(
        shown.toggle.y >= shown.main.bottom && shown.toggle.bottom < height - 40,
        `${width}x${height} Details toggle is hidden under the preview banner (${shown.toggle.y}..${shown.toggle.bottom})`,
      );
      await page.screenshot(`master-order/classic-details-shown-${width}x${height}.png`);

      const before = await toggleDetails(page);
      assert(before === "true", `${width}x${height} toggle started visible`);
      const hidden = await page.evaluate(layoutSnapshot);
      assert(hidden.pressed === "false", `${width}x${height} toggle must report hidden`);
      assert(hidden.collapsed === "true", `${width}x${height} main must be collapsed`);
      assert(hidden.detailsDisplay === "none", `${width}x${height} Details must leave the flow`);
      assert(hidden.splitterDisplay === "none", `${width}x${height} the 6px splitter row must leave the flow`);
      assert(
        hidden.details === null || hidden.details.height === 0,
        `${width}x${height} Details must have zero height`,
      );
      const gap = hidden.main.bottom - hidden.primary.bottom;
      assert(gap <= 1, `${width}x${height} primary pane leaves a ${gap}px empty strip`);
      assert(
        hidden.primary.bottom - hidden.primary.y > shown.primary.bottom - shown.primary.y,
        `${width}x${height} hiding Details must grow the table/Gantt area`,
      );
      assert(
        hidden.rows.split(" ").filter((track) => track.trim()).length === 1,
        `${width}x${height} collapsed grid must have one row, got ${hidden.rows}`,
      );
      await page.screenshot(`master-order/classic-details-hidden-${width}x${height}.png`);

      await toggleDetails(page);
      const restored = await page.evaluate(layoutSnapshot);
      assert(restored.pressed === "true", `${width}x${height} Details must show again`);
      assert(
        Math.abs(restored.details.height - shown.details.height) <= 2,
        `${width}x${height} previous Details height must be restored (${restored.details.height} vs ${shown.details.height})`,
      );
      assert(
        restored.splitterDisplay !== "none",
        `${width}x${height} splitter must return with the Details pane`,
      );

      measurements[`${width}x${height}`] = { shown, hidden, restored };
      record(`Details collapse releases the full workspace at ${width}x${height}`, {
        detailsHeight: shown.details.height,
        gapAfterHide: gap,
        primaryGrewBy: (hidden.primary.bottom - hidden.primary.y) - (shown.primary.bottom - shown.primary.y),
      });
    }

    // The View menu exposes the same command with an accurate Show/Hide label.
    await page.cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1440,
      height: 900,
      deviceScaleFactor: 1,
      mobile: false,
    });
    await page.click('[data-desktop-menu="view"]');
    await page.waitFor(
      `!document.querySelector('[data-desktop-popup="view"]')?.hidden`,
      "View menu open",
    );
    const viewMenu = await page.evaluate(menuViewSnapshot);
    assert(viewMenu.visible, "View menu must open");
    const detailsItem = viewMenu.items.find((item) => item.id === "view.toggle-details");
    assert(detailsItem, "View menu must contain the Details command");
    assert(detailsItem.label === "Hide Details", `View command must read Hide Details, got ${detailsItem.label}`);
    assert(detailsItem.checked === "true", "View command must be checked while Details is visible");
    assert(
      ["classic", "modern", "graphite", "arctic", "copper", "midnight"].every((theme) =>
        viewMenu.items.some((item) => item.id === "view.theme-" + theme)),
      "View menu must offer all six CUBI workspace themes",
    );
    const classicMenuIds = viewMenu.items.map((item) => item.id).join(",");
    await page.screenshot("master-order/classic-view-menu.png");

    // Run the menu command itself; it must hide Details exactly like the button.
    await page.click('[data-desktop-item="view.toggle-details"]');
    await page.waitFor(
      `document.querySelector("[data-details-toggle]")?.getAttribute("aria-pressed") === "false"`,
      "View command hides Details",
    );
    await sleep(350);
    record("View > Hide Details and the bottom-bar toggle share one state");

    // Persistence: hidden Details survives a full reload, then show it again.
    await page.reload("#cp-activity-grid tbody tr", "reload with hidden details");
    await sleep(900);
    const afterReloadHidden = await page.evaluate(layoutSnapshot);
    assert(afterReloadHidden.pressed === "false", "hidden Details must survive reload");
    assert(afterReloadHidden.collapsed === "true", "reload must restore the collapsed grid");
    assert(
      afterReloadHidden.main.bottom - afterReloadHidden.primary.bottom <= 1,
      "reloaded collapsed layout must have no empty strip",
    );
    record("Details visibility persists per user, project and window across reload");

    await page.click("[data-details-toggle]");
    await page.waitFor(
      `document.querySelector("[data-details-toggle]")?.getAttribute("aria-pressed") === "true"`,
      "details shown after reload",
    );
    await sleep(400);
    const afterReloadShown = await page.evaluate(layoutSnapshot);
    assert(afterReloadShown.details.height > 90, "previous Details height must return after reload");

    // ---------------------------------------------------------------------
    // Phases 3 + 4 — two skins, one command surface, persistent selection.
    // ---------------------------------------------------------------------
    const classicChrome = await page.evaluate(chromeSnapshot);
    assert(classicChrome.theme === "classic", "workspace must start in CUBI Classic");

    await setTheme(page, "modern");
    const modernChrome = await page.evaluate(chromeSnapshot);
    assert(modernChrome.theme === "modern", "CUBI Modern 3D must apply");
    assert(
      modernChrome.titlebar.backgroundImage !== classicChrome.titlebar.backgroundImage ||
        modernChrome.desktop.backgroundColor !== classicChrome.desktop.backgroundColor,
      "modern skin must change the chrome tokens",
    );
    assert(modernChrome.body.fontFamily !== classicChrome.body.fontFamily, "modern skin must switch to the Inter/Vazirmatn stack");
    const modernRows = await page.evaluate(
      `({
        rows: document.querySelectorAll("#cp-activity-grid tbody tr").length,
        bars: document.querySelectorAll("#cp-gantt .cp-gantt-bar").length,
        detailsTabs: document.querySelectorAll("#cp-details [role=tab]").length,
        languageOptions: document.querySelectorAll(".cp-app-status [data-workspace-language] option").length,
        themeOptions: document.querySelectorAll("[data-workspace-theme] option").length,
        themeValue: document.querySelector("[data-workspace-theme]")?.value ?? null,
      })`,
    );
    assert(modernRows.rows > 0 && modernRows.bars > 0, "modern skin must keep real rows and bars");
    assert(modernRows.detailsTabs >= 10, "modern skin must keep the details tabs");
    assert(modernRows.languageOptions === 9, `language selector must offer nine locales, got ${modernRows.languageOptions}`);
    assert(modernRows.themeValue === "modern", "theme selector must reflect the modern skin");
    assert(modernRows.themeOptions === 6, "theme selector must expose all six CUBI skins");

    const classicFingerprint = JSON.stringify({
      titlebar: classicChrome.titlebar,
      gridHeader: classicChrome.gridHeader,
      details: classicChrome.details,
      body: classicChrome.body,
    });
    for (const theme of ["graphite", "arctic", "copper", "midnight"]) {
      await setTheme(page, theme);
      const snapshot = await page.evaluate(chromeSnapshot);
      assert(snapshot.theme === theme, theme + " theme must apply to the document");
      assert(
        JSON.stringify({
          titlebar: snapshot.titlebar,
          gridHeader: snapshot.gridHeader,
          details: snapshot.details,
          body: snapshot.body,
        }) !== classicFingerprint,
        theme + " must have a distinct visual token fingerprint",
      );
      const liveData = await page.evaluate("({" +
        "rows: document.querySelectorAll('#cp-activity-grid tbody tr').length," +
        "bars: document.querySelectorAll('#cp-gantt .cp-gantt-bar').length," +
        "detailsTabs: document.querySelectorAll('#cp-details [role=tab]').length," +
        "themeValue: document.querySelector('[data-workspace-theme]')?.value ?? null," +
        "colorScheme: document.documentElement.getAttribute('data-cubi-color-scheme')" +
      "})");
      assert(liveData.rows > 0 && liveData.bars > 0, theme + " must preserve activity rows and Gantt bars");
      assert(liveData.detailsTabs >= 10, theme + " must preserve the Details tab surface");
      assert(liveData.themeValue === theme, theme + " selector must reflect the active palette");
      assert(
        liveData.colorScheme === (theme === "graphite" || theme === "midnight" ? "dark" : "light"),
        theme + " must declare the matching native color scheme",
      );
      await page.screenshot("master-order/theme-" + theme + "-1440x900.png");
      record("CUBI " + theme + " palette applies without changing workspace content", {
        rows: liveData.rows,
        bars: liveData.bars,
        detailsTabs: liveData.detailsTabs,
      });
    }
    // Persist a dark skin through a full reload, then return to Modern.
    await setTheme(page, "midnight");
    await page.reload("#cp-activity-grid tbody tr", "reload with Midnight theme");
    await sleep(700);
    assert(
      await page.evaluate("document.documentElement.getAttribute('data-cubi-theme')") === "midnight",
      "selected Midnight theme must persist across reload",
    );
    await setTheme(page, "modern");

    await page.click('[data-desktop-menu="view"]');
    await page.waitFor(
      `!document.querySelector('[data-desktop-popup="view"]')?.hidden`,
      "View menu open in modern",
    );
    const modernViewMenu = await page.evaluate(menuViewSnapshot);
    assert(
      modernViewMenu.items.map((item) => item.id).join(",") === classicMenuIds,
      "both skins must expose the identical View command registry",
    );
    record("CUBI Classic and CUBI Modern 3D share one command registry", {
      viewItems: modernViewMenu.items.length,
    });
    await page.click('[data-desktop-menu="view"]');

    for (const [width, height] of viewports) {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", {
        width,
        height,
        deviceScaleFactor: 1,
        mobile: false,
      });
      await sleep(450);
      await page.screenshot(`master-order/modern-${width}x${height}.png`);
    }
    measurements.modernChrome = modernChrome;

    // Theme persistence across reload.
    await page.reload("#cp-activity-grid tbody tr", "reload in modern skin");
    await sleep(1000);
    const modernAfterReload = await page.evaluate(`({
      theme: document.documentElement.getAttribute("data-cubi-theme"),
      select: document.querySelector("[data-workspace-theme]")?.value ?? null,
      rows: document.querySelectorAll("#cp-activity-grid tbody tr").length,
    })`);
    assert(modernAfterReload.theme === "modern", "modern theme must survive reload");
    assert(modernAfterReload.select === "modern", "theme selector must show modern after reload");
    assert(modernAfterReload.rows > 0, "reloaded modern workspace must render rows");
    record("theme selection persists per user across reload");

    await setTheme(page, "classic");
    const backToClassic = await page.evaluate(chromeSnapshot);
    assert(backToClassic.theme === "classic", "classic skin must reapply");
    assert(
      backToClassic.titlebar.backgroundImage === classicChrome.titlebar.backgroundImage,
      "returning to Classic must restore the original chrome tokens",
    );
    record("switching back to CUBI Classic restores the original tokens");

    // ---------------------------------------------------------------------
    // Phase 6 — nine launch languages, with real translations and RTL Arabic.
    // ---------------------------------------------------------------------
    const localeChecks = [
      { locale: "ru", fileMenu: "Рабочая область", theme: "Тема рабочей области" },
      { locale: "fr", fileMenu: "Espace de travail", theme: "Thème de l'espace de travail" },
      { locale: "ja", fileMenu: "ワークスペース", theme: "ワークスペースのテーマ" },
      { locale: "ko", fileMenu: "작업 공간", theme: "작업 영역 테마" },
      { locale: "ar", fileMenu: "مساحة العمل", theme: "سمة بيئة العمل" },
    ];
    for (const { locale, fileMenu, theme } of localeChecks) {
      await setLanguage(page, locale);
      const surface = await page.evaluate(`(() => {
        const file = document.querySelector('[data-desktop-menu="workspace"]');
        const details = document.querySelector("[data-details-toggle]");
        const themeSelect = document.querySelector("[data-workspace-theme]");
        const languageSelect = document.querySelector("[data-workspace-language]");
        const header = document.querySelector('#cp-activity-grid thead th[data-column-id="activity_name"] .cp-p6-column-label') ??
          document.querySelector("#cp-activity-grid thead th .cp-p6-column-label");
        return {
          lang: document.documentElement.lang,
          dir: document.documentElement.dir,
          file: file ? file.textContent.trim() : null,
          view: document.querySelector('[data-desktop-menu="view"]')?.textContent.trim() ?? null,
          details: details ? details.getAttribute("aria-label") : null,
          theme: themeSelect ? themeSelect.getAttribute("aria-label") : null,
          themeValue: themeSelect?.value ?? null,
          language: languageSelect?.value ?? null,
          header: header ? header.textContent.trim() : null,
          toggleLabel: document.querySelector('[data-desktop-menu="view"]')?.textContent.trim() ?? null,
        };
      })()`);
      assert(surface.lang === locale, `${locale} document lang ${surface.lang}`);
      assert(surface.file === fileMenu, `${locale} Workspace menu must read ${fileMenu}, got ${surface.file}`);
      assert(surface.theme === theme, `${locale} theme aria must read ${theme}, got ${surface.theme}`);
      assert(surface.language === locale, `${locale} selector value ${surface.language}`);
      assert(surface.details && surface.details !== "Hide Details", `${locale} Details tooltip must be translated`);
      assert(surface.header && surface.header !== "Activity Name", `${locale} column header must be translated`);
      assert(surface.dir === (locale === "ar" ? "rtl" : "ltr"), `${locale} direction ${surface.dir}`);
      assert(surface.themeValue === "classic", `${locale} theme selection must stay classic`);
      if (locale === "ru" || locale === "ar") {
        await page.cdp.send("Emulation.setDeviceMetricsOverride", {
          width: 1440,
          height: 900,
          deviceScaleFactor: 1,
          mobile: false,
        });
        await sleep(400);
        await page.screenshot(`master-order/locale-${locale}-1440x900.png`);
      }
      record(`${locale} translates the command surface`, {
        fileMenu: surface.file,
        detailsTooltip: surface.details,
        columnHeader: surface.header,
        direction: surface.dir,
      });
    }

    // Return the preview to the delivered default: English + Classic, Details shown.
    await setLanguage(page, "en");
    await ensureDetailsVisible(page);
    await page.cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1440,
      height: 900,
      deviceScaleFactor: 1,
      mobile: false,
    });
    await sleep(400);
    await page.screenshot("master-order/final-english-classic-1440x900.png");
    record("workspace returns to English + CUBI Classic with Details visible");
  } finally {
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
    page.cdp.close();
    chrome.cdp.close();
    await chrome.stop();
  }

  process.stdout.write(`\nMaster-order E2E passed (${checks.length} recorded checks).\n`);
  process.stdout.write(`Report: ${join(outDir, "report.json")}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error && error.stack ? error.stack : error}\n`);
  process.exit(1);
});
