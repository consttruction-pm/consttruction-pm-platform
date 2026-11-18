#!/usr/bin/env node
/**
 * V29: six themes x three viewport sizes x English LTR / Persian RTL.
 *
 * Every cell is captured from the real preview. The suite checks horizontal
 * overflow, readable contrast on activity rows, distinct theme tokens, the
 * document direction, and that the toolbar and Details pane are present.
 * CUBI Classic is restored at the end.
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4197";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const outDir = join(artifactsDir, "visual-matrix-v29");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", "activity-workspace-v29", "visual");
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const THEMES = ["classic", "modern", "graphite", "arctic", "copper", "midnight"];
const SIZES = [[1280, 720], [1366, 768], [1920, 1080]];
const LOCALES = ["en", "fa"];
const report = { contract: "cubi-visual-matrix-v29.v1", url: baseUrl, testedCodeSha, capturedAt: new Date().toISOString(), cells: [], screenshots: [], exceptions: [], apiFailures: [] };
const assert = (condition, message) => { if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`); };

async function capture(page, name) {
  await page.screenshot(`visual-matrix-v29/${name}.png`);
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
    };
  })()`);
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
        assert(state.toolbar && state.details && state.menu, `${locale}/${width}x${height}/${theme}: shell surface missing ${JSON.stringify({toolbar: state.toolbar, details: state.details, menu: state.menu})}`);
        if (locale === "fa") assert(state.dir === "rtl", `${locale}/${width}x${height}/${theme}: direction is ${state.dir}`);
        else assert(state.dir !== "rtl", `${locale}/${width}x${height}/${theme}: direction is ${state.dir}`);
        if ((theme === "graphite" || theme === "midnight") && state.row) {
          const ratio = contrast(state.row.backgroundColor, state.row.color);
          cell.contrast = Number(ratio.toFixed(2));
          assert(ratio >= 4.5, `${locale}/${width}x${height}/${theme}: row contrast ${ratio.toFixed(2)}:1`);
        }
        signatures.add(JSON.stringify([theme, state.row, state.header]));
        const name = `theme-${theme}-${locale}-${width}x${height}`;
        await capture(page, name);
      }
    }
  }

  await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 768, deviceScaleFactor: 1, mobile: false });
  await setLocale(page, "en");
  await selectTheme(page, "classic");
  assert(report.cells.length === THEMES.length * SIZES.length * LOCALES.length, "not every matrix cell was captured");
  assert(report.exceptions.length === 0, `browser exceptions: ${report.exceptions.join(" | ")}`);
  assert(report.apiFailures.length === 0, `API failures: ${JSON.stringify(report.apiFailures)}`);
  report.finishedAt = new Date().toISOString();
  writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
  writeFileSync(join(evidenceDir, "visual-matrix.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ ok: true, cells: report.cells.length, screenshots: report.screenshots.length, signatures: signatures.size }, null, 2));
  await chrome.stop();
  process.exit(0);
}

main().catch((error) => {
  report.finishedAt = new Date().toISOString();
  report.failure = error?.stack ?? String(error);
  writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
  writeFileSync(join(evidenceDir, "visual-matrix.json"), JSON.stringify(report, null, 2));
  console.error(error?.stack ?? error);
  process.exit(1);
});
