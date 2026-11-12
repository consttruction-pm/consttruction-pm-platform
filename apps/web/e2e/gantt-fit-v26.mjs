#!/usr/bin/env node
/**
 * Version 26 "Fit" acceptance for the Activities Gantt.
 *
 * Fit must adapt to the pane it fills instead of jumping to a fixed month
 * scale: it picks the finest documented scale whose timeline fits the visible
 * Gantt scroll container, never finer than the pane allows, while a coarse
 * scale that is still too wide keeps its horizontal scroll. The test proves the
 * rule at two pane widths (1366 and 1920) in both en and fa.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 \
 *   CUBI_TESTED_CODE_SHA=<code commit> \
 *   node e2e/gantt-fit-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "gantt-fit-v26");
const durableDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", "gantt-fit-v26-2026-11-12");
mkdirSync(outDir, { recursive: true });
mkdirSync(durableDir, { recursive: true });

// Mirrors GANTT_CONTENT_WIDTH in src/workspace-gantt.ts. The five-scale test
// asserts these declared widths against the rendered board.
const SCALE_WIDTHS = { day: 1600, week: 1100, month: 800, quarter: 640, year: 520 };
const SCALE_ORDER = ["day", "week", "month", "quarter", "year"];

const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const cells = [];
const screenshots = [];

function log(message) {
  process.stdout.write(`${message}\n`);
}

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

async function capture(page, name) {
  const file = `gantt-fit-v26/${name}.png`;
  await page.screenshot(file);
  copyFileSync(join(artifactsDir, file), join(durableDir, `${name}.png`));
  screenshots.push(`${name}.png`);
}

async function setLanguage(page, locale) {
  const changed = await page.evaluate(`(() => {
    const select = document.querySelector("[data-workspace-language]");
    if (!select) return false;
    if (select.value === ${JSON.stringify(locale)}) return true;
    select.value = ${JSON.stringify(locale)};
    select.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  assert(changed, `language selector did not accept ${locale}`);
  await sleep(900);
}

async function clickVisible(page, selector) {
  const clicked = await page.evaluate(`(() => {
    const element = [...document.querySelectorAll(${JSON.stringify(selector)})].find((item) => item.getClientRects().length > 0);
    if (!element || element.disabled) return false;
    element.click();
    return true;
  })()`);
  assert(clicked, `not clickable: ${selector}`);
}

async function measure(page) {
  return page.evaluate(`(() => {
    const chart = document.querySelector("#cp-gantt .cp-gantt-chart");
    const board = document.querySelector("#cp-gantt .cp-gantt-board");
    const body = document.querySelector("#cp-gantt [data-gantt-body]");
    return {
      scale: board?.dataset.ganttScaleMode ?? null,
      contentWidth: board ? Number.parseFloat(getComputedStyle(board).getPropertyValue("--cp-gantt-content-width")) : 0,
      paneWidth: chart ? chart.clientWidth : 0,
      paneScrollWidth: chart ? chart.scrollWidth : 0,
      paneScrollLeft: chart ? chart.scrollLeft : 0,
      bodyWidth: body ? +body.getBoundingClientRect().width.toFixed(1) : 0,
      rows: document.querySelectorAll("#cp-gantt [data-gantt-activity-id]").length,
      viewportWidth: window.innerWidth,
      documentScrollWidth: document.documentElement.scrollWidth,
    };
  })()`);
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

  const report = {
    contract: "cubi-gantt-fit-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    cells,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
  };

  try {
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 768, deviceScaleFactor: 1, mobile: false });
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
    const hasPersonas = await page.evaluate('Boolean(document.querySelector(".persona"))');
    if (!hasPersonas) {
      await page.evaluate(`fetch("/preview/logout", { method: "POST", redirect: "manual" }).then((response) => response.status)`, { awaitPromise: true });
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
    await sleep(1600);
    await page.waitForSelector("#cp-gantt [data-gantt-activity-id]", "gantt rows");

    const fitFacts = {};
    for (const viewport of [{ width: 1366, height: 768 }, { width: 1920, height: 1080 }]) {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", {
        width: viewport.width,
        height: viewport.height,
        deviceScaleFactor: 1,
        mobile: false,
      });
      await sleep(900);
      for (const locale of ["en", "fa"]) {
        const label = `${viewport.width}x${viewport.height}-${locale}`;
        log(`\n[${label}]`);
        await setLanguage(page, locale);
        await page.waitForSelector("#cp-gantt [data-gantt-activity-id]", "gantt rows");

        // Start from the coarsest scale so Fit has room to choose.
        await clickVisible(page, '[data-gantt-scale="year"]');
        await sleep(550);
        const before = await measure(page);
        assert(before.scale === "year", `${label}: scale did not start at year (${before.scale})`);
        assert(before.paneWidth > 0, `${label}: the Gantt pane has no width`);
        assert(before.rows > 0, `${label}: the Gantt has no activity rows`);

        await clickVisible(page, '[data-desktop-command="view.fit"]');
        await sleep(550);
        const fitted = await measure(page);
        const index = SCALE_ORDER.indexOf(fitted.scale);
        assert(index >= 0, `${label}: Fit produced an unknown scale (${fitted.scale})`);
        assert(fitted.contentWidth === SCALE_WIDTHS[fitted.scale], `${label}: ${fitted.scale} content width ${fitted.contentWidth} != ${SCALE_WIDTHS[fitted.scale]}`);
        assert(fitted.rows === before.rows, `${label}: Fit changed the activity row count (${fitted.rows} != ${before.rows})`);
        assert(fitted.documentScrollWidth <= viewport.width + 1, `${label}: Fit overflowed the page (${fitted.documentScrollWidth} > ${viewport.width})`);

        if (fitted.scale !== "year") {
          assert(fitted.contentWidth <= fitted.paneWidth + 1, `${label}: Fit chose ${fitted.scale} (${fitted.contentWidth}px) wider than the pane (${fitted.paneWidth}px)`);
        }
        // Scroll range may only be explained by the timeline itself. RTL
        // decorations (axis tick transforms, mirrored labels) can add a few
        // pixels, so allow a small slack on top of the wider of pane/content.
        const scrollCeiling = Math.max(fitted.contentWidth, fitted.paneWidth) + 8;
        assert(
          fitted.paneScrollWidth <= scrollCeiling,
          `${label}: chart scroll range ${fitted.paneScrollWidth} exceeds the timeline/pane ${scrollCeiling - 8}px at ${fitted.scale}`,
        );
        assert(
          index === 0 || SCALE_WIDTHS[SCALE_ORDER[index - 1]] > fitted.paneWidth + 1,
          `${label}: Fit chose ${fitted.scale} although the finer ${SCALE_ORDER[index - 1]} (${SCALE_WIDTHS[SCALE_ORDER[index - 1]]}px) would fit the ${fitted.paneWidth}px pane`,
        );
        // A scale that is still wider than the pane must keep its scroll.
        if (fitted.contentWidth > fitted.paneWidth + 1) {
          assert(
            fitted.paneScrollWidth >= fitted.contentWidth - 1,
            `${label}: content ${fitted.contentWidth}px overflows a ${fitted.paneWidth}px pane but the chart cannot scroll to its end (${fitted.paneScrollWidth})`,
          );
        }

        await capture(page, `gantt-fit-${label}`);
        fitFacts[label] = {
          pane: { width: fitted.paneWidth, scrollWidth: fitted.paneScrollWidth },
          scale: fitted.scale,
          contentWidth: fitted.contentWidth,
          fitted: fitted.contentWidth <= fitted.paneWidth + 1,
        };
        cells.push({ viewport, locale, before: { scale: before.scale, pane: before.paneWidth }, fitted: fitFacts[label] });
      }
    }

    // The wider window exposes a wider pane, and Fit never gets coarser on a
    // wider pane.
    for (const locale of ["en", "fa"]) {
      const small = cells.find((cell) => cell.viewport.width === 1366 && cell.locale === locale);
      const large = cells.find((cell) => cell.viewport.width === 1920 && cell.locale === locale);
      assert(large.fitted.pane.width > small.fitted.pane.width, `${locale}: 1920 pane ${large.fitted.pane.width} is not wider than 1366 pane ${small.fitted.pane.width}`);
      assert(
        SCALE_ORDER.indexOf(large.fitted.scale) <= SCALE_ORDER.indexOf(small.fitted.scale),
        `${locale}: Fit got coarser on a wider pane (${large.fitted.scale} vs ${small.fitted.scale})`,
      );
    }

    assert(exceptions.length === 0, `runtime exceptions: ${exceptions.join(" | ")}`);
    assert(consoleErrors.length === 0, `console errors: ${consoleErrors.join(" | ")}`);
    assert(apiFailures.length === 0, `HTTP 5xx responses: ${JSON.stringify(apiFailures)}`);
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(outDir, "gantt-fit-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(durableDir, "gantt-fit-v26.json"), JSON.stringify(report, null, 2));
    log(`\nPASS ${cells.length} Fit cells at ${testedCodeSha}`);
  } catch (error) {
    report.finishedAt = new Date().toISOString();
    report.error = String(error && error.stack ? error.stack : error);
    writeFileSync(join(outDir, "gantt-fit-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(durableDir, "gantt-fit-v26.json"), JSON.stringify(report, null, 2));
    throw error;
  } finally {
    page.cdp.close();
    chrome.cdp.close();
    await chrome.stop();
  }
}

main().catch((error) => {
  process.stderr.write(`${error && error.stack ? error.stack : error}\n`);
  process.exitCode = 1;
});
