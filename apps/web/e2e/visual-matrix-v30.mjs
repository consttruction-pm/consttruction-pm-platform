#!/usr/bin/env node
/**
 * V30 visual matrix: six themes x three sizes x English LTR / Persian RTL,
 * plus the Edit menu and the new Replace, Spell Check and Gantt attachment
 * dialogs at 1366x768 in every theme and language.
 *
 * Every cell is captured from the real preview; the suite asserts no document
 * overflow, a fitted dialog, the document direction and the presence of the
 * workspace shell.
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4200";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const outDir = join(artifactsDir, "visual-matrix-v30");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", "activity-workspace-v30", "visual");
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const THEMES = ["classic", "modern", "graphite", "arctic", "copper", "midnight"];
const SIZES = [[1280, 720], [1366, 768], [1920, 1080]];
const LOCALES = ["en", "fa"];
const report = {
  contract: "cubi-visual-matrix-v30.v1",
  url: baseUrl,
  testedCodeSha,
  capturedAt: new Date().toISOString(),
  cells: [],
  dialogCells: [],
  screenshots: [],
  exceptions: [],
  apiFailures: [],
};
const assert = (condition, message) => { if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`); };

async function capture(page, name) {
  await page.screenshot(`visual-matrix-v30/${name}.png`);
  copyFileSync(join(outDir, `${name}.png`), join(evidenceDir, `${name}.png`));
  report.screenshots.push(`${name}.png`);
}

function contrast(a, b) {
  const parse = (value) => (value.match(/\d+/g) ?? []).slice(0, 3).map(Number);
  const lum = (value) => {
    const [r, g, bl] = parse(value).map((channel) => {
      const c = channel / 255;
      return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * bl;
  };
  const x = lum(a); const y = lum(b);
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
}

async function setLocale(page, locale) {
  await page.evaluate(`(() => { localStorage.setItem("cubi:workspace-locale", ${JSON.stringify(locale)}); return true; })()`);
  await page.navigate(`${baseUrl}/app?view=live&project=preview-rps-01`, "#cp-activity-grid tbody tr[data-activity-id]", "locale reload");
  await sleep(1300);
}

async function selectTheme(page, theme) {
  const applied = await page.evaluate(`(() => {
    const select = document.querySelector("[data-workspace-theme]");
    if (!select) return false;
    select.value = ${JSON.stringify(theme)};
    select.dispatchEvent(new Event("change", { bubbles: true }));
    return select.value === ${JSON.stringify(theme)};
  })()`);
  assert(applied, `theme ${theme} could not be selected`);
  await sleep(350);
}

async function inspect(page) {
  return page.evaluate(`(() => {
    const style = (selector, properties) => {
      const element = document.querySelector(selector);
      if (!element) return null;
      const computed = getComputedStyle(element);
      return Object.fromEntries(properties.map((property) => [property, computed[property]]));
    };
    return {
      theme: document.querySelector("[data-workspace-theme]")?.value ?? null,
      dir: document.querySelector(".cp-p6")?.getAttribute("dir") ?? document.documentElement.dir ?? null,
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      row: style('#cp-activity-grid tbody tr[data-activity-id] td', ["backgroundColor", "color"]),
      header: style("#cp-activity-grid thead th", ["backgroundColor", "color"]),
      toolbar: Boolean(document.querySelector("[data-tool-family]")),
      details: Boolean(document.querySelector("#cp-details")),
      gantt: Boolean(document.querySelector("#cp-gantt .cp-gantt-bar-task")),
      menu: Boolean(document.querySelector("[data-desktop-menu]")),
      attachmentsButton: Boolean(document.querySelector("#cp-gantt [data-gantt-attachments-open]")),
    };
  })()`);
}

async function openEditMenu(page) {
  const toggled = await page.evaluate(`(() => {
    const trigger = document.querySelector('[data-desktop-menu="edit"]');
    if (!trigger) return false;
    trigger.click();
    return true;
  })()`);
  assert(toggled, "the Edit menu trigger is missing");
  await sleep(250);
}

async function closeMenus(page) {
  await page.evaluate(`(() => {
    const open = document.querySelector('[data-desktop-menu][aria-expanded="true"]');
    if (open) open.click();
    return true;
  })()`);
  await sleep(150);
}

async function dialogFit(page, selector) {
  return page.evaluate(`(() => {
    const dialog = document.querySelector(${JSON.stringify(selector)});
    if (!dialog) return null;
    const rect = dialog.getBoundingClientRect();
    return {
      open: dialog.hasAttribute('open') || dialog.open === true,
      left: Math.round(rect.left),
      top: Math.round(rect.top),
      right: Math.round(rect.right),
      bottom: Math.round(rect.bottom),
      width: Math.round(rect.width),
      height: Math.round(rect.height),
      viewport: [window.innerWidth, window.innerHeight],
    };
  })()`);
}

async function closeDialog(page, selector) {
  await page.evaluate(`(() => {
    const dialog = document.querySelector(${JSON.stringify(selector)});
    if (dialog && typeof dialog.close === 'function') dialog.close();
    else dialog?.removeAttribute('open');
    return true;
  })()`);
  await sleep(200);
}

async function main() {
  await waitForHttp(`${baseUrl}/preview/health`, 20000);
  const chrome = await launchChrome();
  const page = new Page(chrome.cdp);
  await page.initialize();
  page.cdp.on("Runtime.exceptionThrown", (params) => {
    report.exceptions.push(params.exceptionDetails?.exception?.description ?? params.exceptionDetails?.text ?? "unknown exception");
  });
  page.cdp.on("Network.responseReceived", (params) => {
    const url = params.response?.url ?? "";
    if (url.includes("/api/") && params.response.status >= 500) report.apiFailures.push({ url, status: params.response.status });
  });

  await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 768, deviceScaleFactor: 1, mobile: false });
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "form", "login");
  await page.evaluate(`(() => { localStorage.setItem("cubi:workspace-locale", "en"); return true; })()`);
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "form", "login");
  await page.click('button[name="role"][value="admin"]');
  await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
  await page.click('[data-project-id="preview-rps-01"]');
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
  await sleep(1400);

  const signatures = new Set();
  for (const locale of LOCALES) {
    await setLocale(page, locale);
    for (const [width, height] of SIZES) {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
      await sleep(500);
      for (const theme of THEMES) {
        await selectTheme(page, theme);
        const state = await inspect(page);
        const cell = { locale, width, height, theme, ...state };
        report.cells.push(cell);
        assert(state.theme === theme, `${locale}/${width}x${height}/${theme}: theme select shows ${state.theme}`);
        assert(state.overflow <= 1, `${locale}/${width}x${height}/${theme}: horizontal overflow ${state.overflow}px`);
        assert(state.toolbar && state.details && state.menu, `${locale}/${width}x${height}/${theme}: shell surface missing`);
        assert(state.gantt && state.attachmentsButton, `${locale}/${width}x${height}/${theme}: Gantt attachments surface missing`);
        if (locale === "fa") assert(state.dir === "rtl", `${locale}/${width}x${height}/${theme}: direction is ${state.dir}`);
        else assert(state.dir !== "rtl", `${locale}/${width}x${height}/${theme}: direction is ${state.dir}`);
        if ((theme === "graphite" || theme === "midnight") && state.row) {
          const ratio = contrast(state.row.backgroundColor, state.row.color);
          cell.contrast = Number(ratio.toFixed(2));
          assert(ratio >= 4.5, `${locale}/${width}x${height}/${theme}: row contrast ${ratio.toFixed(2)}:1`);
        }
        signatures.add(JSON.stringify([theme, state.row, state.header]));
        await capture(page, `theme-${theme}-${locale}-${width}x${height}`);
      }
    }
  }

  // Dialog coverage at the reference 1366x768 size.
  await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 768, deviceScaleFactor: 1, mobile: false });
  for (const locale of LOCALES) {
    await setLocale(page, locale);
    for (const theme of THEMES) {
      await selectTheme(page, theme);
      await openEditMenu(page);
      await capture(page, `edit-menu-${theme}-${locale}-1366x768`);
      await closeMenus(page);

      const attachmentsClicked = await page.evaluate(`(() => {
        const button = document.querySelector('#cp-gantt [data-gantt-attachments-open]');
        if (!button) return false;
        button.click();
        return true;
      })()`);
      assert(attachmentsClicked, `${locale}/${theme}: attachments button missing`);
      await sleep(300);
      const attachments = await dialogFit(page, "[data-gantt-attachments-dialog]");
      assert(attachments?.open, `${locale}/${theme}: attachments dialog did not open`);
      assert(attachments.left >= 0 && attachments.top >= 0 && attachments.right <= attachments.viewport[0] && attachments.bottom <= attachments.viewport[1], `${locale}/${theme}: attachments dialog is clipped ${JSON.stringify(attachments)}`);
      await capture(page, `attachments-dialog-${theme}-${locale}-1366x768`);
      await closeDialog(page, "[data-gantt-attachments-dialog]");

      const replaceOpened = await page.evaluate(`(() => {
        const button = document.querySelector('[data-desktop-command="dialog.replace"]');
        if (!button) return false;
        button.click();
        return true;
      })()`);
      assert(replaceOpened, `${locale}/${theme}: Replace command missing`);
      await page.waitForSelector("[data-activity-replace-dialog]", "replace dialog");
      const replace = await dialogFit(page, "[data-activity-replace-dialog]");
      assert(replace.left >= 0 && replace.top >= 0 && replace.right <= replace.viewport[0] && replace.bottom <= replace.viewport[1], `${locale}/${theme}: Replace dialog is clipped ${JSON.stringify(replace)}`);
      await capture(page, `replace-dialog-${theme}-${locale}-1366x768`);
      await closeDialog(page, "[data-activity-replace-dialog]");

      const spellOpened = await page.evaluate(`(() => {
        const button = document.querySelector('[data-desktop-command="dialog.spell-check"]');
        if (!button) return false;
        button.click();
        return true;
      })()`);
      assert(spellOpened, `${locale}/${theme}: Spell Check command missing`);
      await page.waitForSelector("[data-activity-spell-dialog]", "spell dialog");
      const spell = await dialogFit(page, "[data-activity-spell-dialog]");
      assert(spell.left >= 0 && spell.top >= 0 && spell.right <= spell.viewport[0] && spell.bottom <= spell.viewport[1], `${locale}/${theme}: Spell dialog is clipped ${JSON.stringify(spell)}`);
      const spellSpellcheck = await page.evaluate(`Boolean(document.querySelector('[data-activity-spell-dialog] input[spellcheck="true"]'))`);
      assert(spellSpellcheck, `${locale}/${theme}: Spell Check inputs do not request browser spellcheck`);
      await capture(page, `spell-dialog-${theme}-${locale}-1366x768`);
      await closeDialog(page, "[data-activity-spell-dialog]");

      report.dialogCells.push({ locale, theme, attachments, replace, spell });
    }
  }

  await setLocale(page, "en");
  await selectTheme(page, "classic");
  assert(signatures.size >= 6, `expected distinct theme signatures, got ${signatures.size}`);
  report.finishedAt = new Date().toISOString();
  report.result = "pass";
}

let failure = null;
try {
  await main();
} catch (error) {
  failure = error;
  report.result = "fail";
  report.failure = error?.stack ?? String(error);
} finally {
  writeFileSync(join(outDir, "visual-matrix-v30.json"), `${JSON.stringify(report, null, 2)}\n`);
  writeFileSync(join(evidenceDir, "visual-matrix-v30.json"), `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({ result: report.result, cells: report.cells.length, dialogs: report.dialogCells.length, screenshots: report.screenshots.length, sha: report.testedCodeSha }, null, 2));
  if (failure) {
    console.error(report.failure);
    process.exitCode = 1;
  }
  process.exit(process.exitCode ?? 0);
}
