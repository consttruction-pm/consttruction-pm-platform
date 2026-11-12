#!/usr/bin/env node
/**
 * Browser E2E for the persisted activity field chooser's bulk "Add all" action.
 *
 * The field chooser lives in the Settings window (`data-settings-layout`) and is
 * backed by the same persisted activity-grid layout as the Columns dialog. This
 * suite opens the real Preview runtime, adds every available registry field in
 * one click, checks that the layout revision advanced, reloads the page and
 * confirms the columns came back from the server. The Persian cell verifies the
 * localized label and RTL direction before the only bulk add of the run.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 node e2e/field-chooser-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "field-chooser-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `field-chooser-v26-${evidenceDate}`);
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
  const file = `field-chooser-v26/${name}.png`;
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

async function openSettings(page) {
  const opened = await page.evaluate(`(() => {
    const trigger = document.querySelector('[data-desktop-menu="administration"]');
    if (!trigger) return false;
    trigger.click();
    return true;
  })()`);
  assert(opened, "Admin menu trigger is missing");
  await page.waitFor(`(() => {
    const popup = document.querySelector('[data-desktop-popup="administration"]');
    return Boolean(popup && !popup.hidden);
  })()`, "Admin menu open");
  await sleep(250);
  const clicked = await page.evaluate(`(() => {
    const button = document.querySelector('[data-desktop-window="settings"]');
    if (!button || button.disabled) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, "Settings window command is missing");
  await page.waitForSelector("[data-settings-layout]", "settings layout section", 10000);
  await sleep(600);
}

async function readProjectLayout(page) {
  return page.evaluate(`(async () => {
    const response = await fetch("/api/projects/preview-rps-01/p6/layouts/project/activity");
    let body = null;
    try { body = await response.json(); } catch {}
    return { status: response.status, body };
  })()`, { awaitPromise: true });
}

const chooserState = `(() => {
  const section = document.querySelector("[data-settings-layout]");
  const addAll = section?.querySelector("[data-p6-field-add-all]") ?? null;
  const rect = section?.getBoundingClientRect() ?? null;
  return {
    present: Boolean(section),
    addAllLabel: addAll?.getAttribute("aria-label") ?? null,
    addAllVisible: Boolean(addAll && addAll.getClientRects().length),
    available: section?.querySelectorAll("[data-p6-field-add]").length ?? 0,
    visibleFields: section?.querySelectorAll("input[data-p6-field-rename]").length ?? 0,
    hiddenFields: section?.querySelectorAll(".cp-p6-field-item.is-hidden").length ?? 0,
    heading: section?.querySelector(".cp-p6-field-chooser-heading strong")?.textContent?.trim() ?? null,
    direction: getComputedStyle(document.querySelector(".cp-workspace") ?? document.body).direction,
    locale: document.documentElement.lang || null,
    withinViewport: rect ? rect.left >= -1 && rect.right <= window.innerWidth + 1 : null,
    horizontalOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  };
})()`;

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
    contract: "cubi-field-chooser-v26.v1",
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
    await setViewport(page, 1280, 720);
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
    const persona = await page.evaluate(`(() => {
      const button = document.querySelector('button[name="role"][value="admin"]');
      if (!button) return false;
      button.click();
      return true;
    })()`);
    assert(persona, "admin persona is missing");
    await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
    await page.click('[data-project-id="preview-rps-01"]');
    await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
    await sleep(1400);
    await setLanguage(page, "fa");
    await openSettings(page);

    const initial = await page.evaluate(chooserState);
    const initialLayout = await readProjectLayout(page);
    const initialColumns = (initialLayout.body.layout ?? initialLayout.body).columns.length;
    let afterRemoval = null;

    await scenario("01", "پس از حذف یک فیلد، دکمهٔ افزودن همه با برچسب فارسی و در جهت RTL دیده می‌شود", async () => {
      assert(initial.present, "settings layout section is missing");
      // The seeded layout already contains every registry field, so the bulk
      // action is correctly absent until a field becomes available.
      assert(initial.available === 0, `seeded layout still has ${initial.available} available fields`);
      assert(initial.addAllVisible === false, "Add all must be hidden when no field is available");
      const removed = await page.evaluate(`(() => {
        const input = document.querySelector("input[data-p6-field-rename]");
        const id = input?.dataset.p6FieldRename ?? null;
        const button = id ? document.querySelector('[data-p6-field-remove="' + id + '"]') : null;
        if (!button) return null;
        button.click();
        return id;
      })()`);
      assert(removed, "no visible field could be removed to create an available field");
      await page.waitFor(`Boolean(document.querySelector("[data-p6-field-add-all]"))`, "Add all after removing a field", 15000);
      await sleep(1200);
      afterRemoval = await page.evaluate(chooserState);
      assert(afterRemoval.available > 0, "remove did not make the field available");
      assert(afterRemoval.addAllLabel === "افزودن همه", `Add all label is ${afterRemoval.addAllLabel}`);
      assert(afterRemoval.heading === "فیلدها", `fields heading is ${afterRemoval.heading}`);
      assert(afterRemoval.direction === "rtl", `direction is ${afterRemoval.direction}`);
      assert(afterRemoval.locale === "fa", `locale is ${afterRemoval.locale}`);
      assert(afterRemoval.withinViewport === true, "field chooser leaves the viewport");
      assert(afterRemoval.horizontalOverflow <= 1, `horizontal overflow is ${afterRemoval.horizontalOverflow}px`);
      await capture(page, "01-chooser-before-fa-1280x720");
      return { removed, available: afterRemoval.available, visible: afterRemoval.visibleFields, label: afterRemoval.addAllLabel };
    });

    await scenario("02", "افزودن همه، همهٔ فیلدهای موجود را در یک گذار چیدمان اضافه می‌کند", async () => {
      const clicked = await page.evaluate(`(() => {
        const button = document.querySelector("[data-p6-field-add-all]");
        if (!button || button.disabled) return false;
        button.click();
        return true;
      })()`);
      assert(clicked, "Add all could not be clicked");
      await page.waitFor(`!document.querySelector("[data-p6-field-add-all]")`, "Add all to disappear", 15000);
      await sleep(1200);
      const after = await page.evaluate(chooserState);
      assert(after.available === 0, `${after.available} fields are still available`);
      assert(after.hiddenFields === afterRemoval.hiddenFields, `hidden fields changed from ${afterRemoval.hiddenFields} to ${after.hiddenFields}`);
      assert(after.visibleFields === initial.visibleFields, `visible fields ${after.visibleFields} != ${initial.visibleFields}`);
      const afterLayout = await readProjectLayout(page);
      assert(afterLayout.status === 200, `layout read status ${afterLayout.status}`);
      const afterColumns = (afterLayout.body.layout ?? afterLayout.body).columns.length;
      assert(afterColumns === initialColumns, `stored columns ${afterColumns} != ${initialColumns}`);
      const revisions = (afterLayout.body.layout ?? afterLayout.body).revision;
      await capture(page, "02-chooser-after-fa-1280x720");
      return { added: afterRemoval.available, columns: afterColumns, revision: revisions };
    });

    await scenario("03", "پس از بارگذاری کامل، ستون‌ها از سرور بازمی‌گردند و دکمهٔ افزودن همه دیگر وجود ندارد", async () => {
      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "workspace reload");
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows after reload");
      await sleep(1200);
      await openSettings(page);
      const persisted = await page.evaluate(chooserState);
      assert(persisted.present, "settings layout section is missing after reload");
      assert(persisted.available === 0, `${persisted.available} fields became available again after reload`);
      assert(persisted.addAllVisible === false, "Add all returned after reload");
      assert(persisted.visibleFields === initial.visibleFields, `reloaded visible fields ${persisted.visibleFields}`);
      return { visible: persisted.visibleFields };
    });

    await scenario("04", "در چیدمان انگلیسی و 1920×1080 انتخاب‌گر فیلد بدون سرریز افقی نمایش داده می‌شود", async () => {
      await setViewport(page, 1920, 1080);
      await setLanguage(page, "en");
      await sleep(500);
      const state = await page.evaluate(chooserState);
      assert(state.present, "settings layout section is missing in English");
      assert(state.heading === "Fields", `English heading is ${state.heading}`);
      assert(state.direction === "ltr", `direction is ${state.direction}`);
      assert(state.withinViewport === true, "field chooser leaves the 1920×1080 viewport");
      assert(state.horizontalOverflow <= 1, `horizontal overflow is ${state.horizontalOverflow}px at 1920×1080`);
      await capture(page, "03-chooser-en-1920x1080");
      return { heading: state.heading, visible: state.visibleFields, direction: state.direction };
    });

    assert(exceptions.length === 0, `uncaught page exceptions: ${JSON.stringify(exceptions.slice(0, 3))}`);
    assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors.slice(0, 3))}`);
    assert(apiFailures.length === 0, `API 5xx responses: ${JSON.stringify(apiFailures.slice(0, 3))}`);
  } finally {
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(outDir, "field-chooser-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(evidenceDir, "field-chooser-v26.json"), JSON.stringify(report, null, 2));
    page.cdp.close();
    chrome.cdp.close();
    await chrome.stop();
  }

  const failed = scenarios.filter((item) => item.status !== "pass");
  log(`\nScenarios: ${scenarios.length - failed.length} passed, ${failed.length} failed`);
  if (failed.length) process.exitCode = 1;
}

main().catch((error) => {
  process.stderr.write(`${error && error.stack ? error.stack : error}\n`);
  process.exit(1);
});
