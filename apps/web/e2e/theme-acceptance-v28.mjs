#!/usr/bin/env node
/**
 * V28: six-theme visual acceptance for the Activities workspace.
 *
 * Captures every CUBI theme at 1366x768 with the real preview, records the
 * computed tokens that distinguish the themes, proves the choice survives a
 * reload, and restores CUBI Classic. It never changes project data.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4199 \
 *   CUBI_TESTED_CODE_SHA=<code commit> node e2e/theme-acceptance-v28.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4199";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const outDir = join(artifactsDir, "theme-acceptance-v28");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", "activity-workspace-v28");
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const THEMES = ["classic", "modern", "graphite", "arctic", "copper", "midnight"];
const report = {
  contract: "cubi-theme-acceptance-v28.v1",
  url: baseUrl,
  testedCodeSha,
  capturedAt: new Date().toISOString(),
  themes: {},
  screenshots: [],
  exceptions: [],
  consoleErrors: [],
  apiFailures: [],
};

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

async function capture(page, name) {
  await page.screenshot(`theme-acceptance-v28/${name}.png`);
  copyFileSync(join(outDir, `${name}.png`), join(evidenceDir, `${name}.png`));
  report.screenshots.push(`${name}.png`);
}

async function selectTheme(page, theme) {
  const applied = await page.evaluate(`(() => {
    const select = document.querySelector("[data-workspace-theme]");
    if (!select) return false;
    select.value = ${JSON.stringify(theme)};
    if (select.value !== ${JSON.stringify(theme)}) return false;
    select.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  assert(applied, `theme ${theme} could not be selected`);
  await sleep(450);
}

async function tokens(page) {
  return page.evaluate(`(() => {
    const css = (selector, properties) => {
      const element = document.querySelector(selector);
      if (!element) return null;
      const style = getComputedStyle(element);
      return Object.fromEntries(properties.map((property) => [property, style[property]]));
    };
    return {
      theme: document.querySelector("[data-workspace-theme]")?.value ?? null,
      documentTheme: document.documentElement.dataset.theme ?? document.body.dataset.theme ?? null,
      titlebar: css(".cp-p6 .cp-titlebar", ["backgroundColor", "color"]),
      menubar: css(".cp-p6 .cp-menubar", ["backgroundColor"]),
      header: css("#cp-activity-grid thead th", ["backgroundColor", "color"]),
      row: css('#cp-activity-grid tbody tr[data-activity-id] td', ["backgroundColor", "color"]),
      taskBar: css("#cp-gantt .cp-gantt-bar-task", ["backgroundColor", "borderColor"]),
      criticalBar: css("#cp-gantt .cp-gantt-bar-critical", ["backgroundColor", "borderColor"]),
      details: css("#cp-details", ["backgroundColor", "color"]),
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
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
  page.cdp.on("Runtime.consoleAPICalled", (params) => {
    if (params.type !== "error") return;
    report.consoleErrors.push((params.args ?? []).map((arg) => arg.value ?? arg.description ?? arg.type).join(" "));
  });
  page.cdp.on("Network.responseReceived", (params) => {
    const url = params.response?.url ?? "";
    if (url.includes("/api/") && params.response.status >= 500) {
      report.apiFailures.push({ url, status: params.response.status });
    }
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

  const seen = new Map();
  for (const theme of THEMES) {
    await selectTheme(page, theme);
    const state = await tokens(page);
    report.themes[theme] = state;
    assert(state.theme === theme, `theme select shows ${state.theme} instead of ${theme}`);
    assert(state.overflow <= 1, `${theme} overflows horizontally by ${state.overflow}px`);
    assert(state.titlebar && state.header && state.taskBar, `${theme} did not expose the expected surfaces`);
    if (theme === "graphite" || theme === "midnight") {
      // Dark skins must not inherit the light layout background: the earlier
      // build rendered near-white text on a white row.
      assert(state.row.backgroundColor !== "rgb(255, 255, 255)", `${theme} kept a white activity row background`);
      const rgb = (value) => (value.match(/\d+/g) ?? []).slice(0, 3).map(Number);
      const luminance = (value) => {
        const [r, g, b] = rgb(value).map((channel) => {
          const c = channel / 255;
          return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
        });
        return 0.2126 * r + 0.7152 * g + 0.0722 * b;
      };
      const a = luminance(state.row.backgroundColor);
      const b = luminance(state.row.color);
      const contrast = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
      state.contrast = Number(contrast.toFixed(2));
      assert(contrast >= 4.5, `${theme} row contrast is ${contrast.toFixed(2)}:1`);
    }
    const signature = JSON.stringify([state.titlebar, state.menubar, state.header, state.row, state.details]);
    if (seen.has(signature)) {
      throw new Error(`ASSERTION_FAILED: ${theme} is visually identical to ${seen.get(signature)}`);
    }
    seen.set(signature, theme);
    await capture(page, `theme-${theme}-en-1366`);
  }

  // The choice is user-level and must survive a full reload.
  await selectTheme(page, "midnight");
  await page.navigate(`${baseUrl}/app?view=live&project=preview-rps-01`, "#cp-activity-grid tbody tr[data-activity-id]", "theme reload");
  await sleep(1200);
  const reloaded = await tokens(page);
  report.reloaded = reloaded;
  assert(reloaded.theme === "midnight", `theme after reload is ${reloaded.theme}`);
  await capture(page, "theme-midnight-after-reload-en-1366");

  await selectTheme(page, "classic");
  const restored = await tokens(page);
  report.restored = restored.theme;
  assert(restored.theme === "classic", "CUBI Classic was not restored");

  assert(report.exceptions.length === 0, `browser exceptions: ${report.exceptions.join(" | ")}`);
  assert(report.consoleErrors.length === 0, `console errors: ${report.consoleErrors.join(" | ")}`);
  assert(report.apiFailures.length === 0, `API failures: ${JSON.stringify(report.apiFailures)}`);

  report.finishedAt = new Date().toISOString();
  writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
  writeFileSync(join(evidenceDir, "theme-acceptance.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ ok: true, themes: THEMES.length, distinct: seen.size, reloaded: reloaded.theme }, null, 2));
  await chrome.stop();
  process.exit(0);
}

main().catch((error) => {
  report.finishedAt = new Date().toISOString();
  report.failure = error?.stack ?? String(error);
  writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
  writeFileSync(join(evidenceDir, "theme-acceptance.json"), JSON.stringify(report, null, 2));
  console.error(error?.stack ?? error);
  process.exit(1);
});
