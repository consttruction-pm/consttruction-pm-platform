#!/usr/bin/env node
/**
 * Browser E2E for the Version 26 project Import / Export window.
 *
 * It drives the real local full-stack preview on project preview-rps-01 with
 * headless Chrome through the DevTools protocol. Exports read the authoritative
 * activity, resource and risk repositories; imports validate and write the
 * resource master through the real HTTP routes and SQLite preview store. No
 * page fixture is injected and no API response is mocked.
 *
 * Scenarios cover the dataset catalogue and CSV export readback, dataset
 * switching, a valid resource preview with an enabled apply, an idempotent API
 * apply with replay and key-reuse conflict, row/field validation errors with a
 * blocked apply, duplicate/cycle rejection, viewer read-only authorization
 * with a direct 403, and the 1280x720 Persian right-to-left layout.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 node e2e/exchange-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "exchange-v26");
const evidenceDir = join(
  artifactsDir,
  "..",
  "..",
  "..",
  "..",
  "docs",
  "workspace",
  "evidence",
  `exchange-v26-${evidenceDate}`,
);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const stamp = Date.now().toString(36).toUpperCase();
const crewId = `E2E-XCH-CREW-${stamp}`;
const childId = `E2E-XCH-CHILD-${stamp}`;
const duplicateId = `E2E-XCH-DUP-${stamp}`;
const idempotencyKey = `e2e-exchange-${stamp}`;
const CSV_HEADER =
  "resource_id,name,resource_type,parent_resource_id,calendar_id,default_units_per_time,unit_of_measure,email,is_active\n";

const validCsv = `${CSV_HEADER}${crewId},Exchange crew,labor,,,,,e2e.exchange@example.test,true\n${childId},Exchange child,labor,${crewId},,,,false\n`;
const invalidCsv = `${CSV_HEADER}${duplicateId},Bad row,robot,,CAL-DOES-NOT-EXIST,,,not-an-email,maybe\n`;

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
  scenarios.push({ ...details, id, name, status, at: new Date().toISOString() });
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

const pageState = `(() => {
  const page = document.querySelector("[data-exchange-page]");
  const text = (node) => (node?.textContent ?? "").trim();
  return {
    activeMenu: document.querySelector(".cp-workspace")?.dataset.activeMenu ?? null,
    direction: document.querySelector(".cp-workspace")?.getAttribute("dir") ?? null,
    heading: text(page?.querySelector(":scope > .cp-register-toolbar strong")),
    tabs: [...page?.querySelectorAll("[data-exchange-tab]") ?? []].map((tab) => ({
      key: tab.dataset.exchangeTab,
      selected: tab.getAttribute("aria-selected"),
      label: text(tab),
    })),
    activeTab: page?.querySelector("[data-exchange-body]")?.dataset.exchangeActiveTab ?? null,
    exportDataset: page?.querySelector("[data-exchange-dataset]")?.value ?? null,
    exportOptions: [...page?.querySelectorAll("[data-exchange-dataset] option") ?? []].map((option) => option.value),
    exportMeta: text(page?.querySelector("[data-exchange-export-meta]")),
    exportColumns: [...page?.querySelectorAll("[data-exchange-export-table] thead th") ?? []].map((cell) => text(cell)),
    exportRows: page?.querySelectorAll("[data-exchange-export-table] tbody tr").length ?? 0,
    hasDownload: Boolean(page?.querySelector('[data-exchange-action="download"]')),
    content: page?.querySelector("[data-exchange-content]")?.value ?? null,
    contentDisabled: Boolean(page?.querySelector("[data-exchange-content]")?.disabled),
    summary: (() => {
      const node = page?.querySelector("[data-exchange-import-summary]");
      return node
        ? { valid: node.dataset.valid, accepted: node.dataset.accepted, rejected: node.dataset.rejected }
        : null;
    })(),
    summaryText: text(page?.querySelector("[data-exchange-import-summary]")),
    errors: [...page?.querySelectorAll("[data-exchange-error-row]") ?? []].map((row) => ({
      row: row.dataset.row,
      field: row.dataset.field,
      code: row.dataset.code,
    })),
    applyDisabled: Boolean(page?.querySelector('[data-exchange-action="apply"]')?.disabled),
    runs: [...page?.querySelectorAll("[data-exchange-run-row]") ?? []].map((row) => ({
      id: row.dataset.runId,
      text: text(row),
    })),
    notice: page?.querySelector("[data-exchange-notice]")?.dataset.state ?? null,
    noticeText: text(page?.querySelector("[data-exchange-notice]")),
    bodyText: text(page),
  };
})()`;

async function capture(page, name) {
  const file = `exchange-v26/${name}.png`;
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

async function openMenu(page, key, selector, label) {
  const clicked = await page.evaluate(`(() => {
    const buttons = [...document.querySelectorAll('[data-menu="${key}"]')];
    const button = buttons.find((entry) => entry.getClientRects().length > 0) ?? buttons[0];
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `${key} menu button is missing`);
  await page.waitForSelector(selector, label, 20000);
  await sleep(500);
}

async function openExchange(page) {
  await openMenu(page, "exchange", "[data-exchange-page] .cp-register-toolbar", "exchange panel");
  await page.waitFor(
    `(() => {
      const page = document.querySelector("[data-exchange-page]");
      return Boolean(page) && Boolean(page.querySelector("[data-exchange-tab]"));
    })()`,
    "exchange tabs settled",
  );
  await sleep(400);
}

async function openTab(page, tab) {
  await page.click(`[data-exchange-tab="${tab}"]`);
  await page.waitFor(
    `document.querySelector("[data-exchange-page] [data-exchange-body]")?.dataset.exchangeActiveTab === ${JSON.stringify(tab)}`,
    `exchange ${tab} tab`,
  );
  await sleep(300);
}

async function exportDataset(page, dataset) {
  await page.setSelect("[data-exchange-dataset]", dataset);
  await page.click('[data-exchange-action="export"]');
  await page.waitFor(
    `Boolean(document.querySelector("[data-exchange-page] [data-exchange-export-table]"))`,
    `exported ${dataset} table`,
  );
  await sleep(400);
}

async function setContent(page, content) {
  await page.evaluate(`(() => {
    const textarea = document.querySelector("[data-exchange-content]");
    if (!textarea) return false;
    textarea.value = ${JSON.stringify(content)};
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    return true;
  })()`);
  await sleep(200);
}

async function validate(page) {
  await page.click('[data-exchange-action="validate"]');
  await page.waitFor(
    `Boolean(document.querySelector("[data-exchange-page] [data-exchange-import-summary]"))`,
    "import validation summary",
  );
  await sleep(400);
}

function exchangeUrl(suffix = "") {
  return `/api/projects/${PROJECT}/exchange${suffix}`;
}

async function api(page, method, path, body, headers = {}) {
  return page.evaluate(`(async () => {
    const response = await fetch(${JSON.stringify(path)}, {
      method: ${JSON.stringify(method)},
      headers: { "Content-Type": "application/json", ...${JSON.stringify(headers)} },
      ${body === undefined ? "" : `body: JSON.stringify(${JSON.stringify(body)}),`}
    });
    return { status: response.status, body: await response.json() };
  })()`, { awaitPromise: true });
}

async function loginAs(page, label) {
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
  const hasPersonas = await page.evaluate('Boolean(document.querySelector(".persona"))');
  if (!hasPersonas) {
    const logoutStatus = await page.evaluate(`(async () => {
      const response = await fetch("/preview/logout", { method: "POST", redirect: "manual" });
      return response.status;
    })()`, { awaitPromise: true });
    assert([0, 200, 302, 303].includes(logoutStatus), `unexpected logout status ${logoutStatus}`);
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, ".persona", "persona cards after sign out");
  }
  const clicked = await page.evaluate(`(() => {
    const button = [...document.querySelectorAll("form button")].find((item) => (item.textContent || "").trim().startsWith(${JSON.stringify(label)}));
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `${label} login button is missing`);
  await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
  await page.click('[data-project-id="preview-rps-01"]');
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
  await sleep(1200);
  await setLanguage(page, "en");
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
    contract: "cubi-exchange-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    crewId,
    childId,
    idempotencyKey,
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
  };

  try {
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
    await sleep(400);
    await loginAs(page, "Project administrator");
    await openExchange(page);

    await scenario("01", "کاتالوگ مجموعه‌های داده و خروجی منابع از مخزن مرجع خوانده می‌شود", async () => {
      const state = await page.evaluate(pageState);
      assert(state.heading === "Import / Export", `heading ${state.heading}`);
      assert(state.tabs.map((tab) => tab.key).join(",") === "export,import,history", `tabs ${JSON.stringify(state.tabs)}`);
      assert(state.exportOptions.join(",") === "activities,resources,risks", `datasets ${state.exportOptions.join(",")}`);

      await exportDataset(page, "resources");
      const exported = await page.evaluate(pageState);
      assert(exported.exportColumns[0] === "resource_id", `columns ${exported.exportColumns.join(",")}`);
      assert(exported.exportRows > 0, `exported rows ${exported.exportRows}`);
      assert(/\bRows: \d+/.test(exported.exportMeta) || /Rows/.test(exported.exportMeta), `meta ${exported.exportMeta}`);
      assert(exported.hasDownload, "download button missing");
      await capture(page, "01-resource-export");

      const direct = await api(page, "GET", exchangeUrl("/export?dataset=resources"));
      assert(direct.status === 200 && direct.body.contract_version === "p6-exchange-api.v1", `export api ${JSON.stringify(direct).slice(0, 300)}`);
      assert(direct.body.row_count === direct.body.content.split("\n").length - 2, `export row count ${direct.body.row_count}`);
      return { datasets: state.exportOptions, rowCount: direct.body.row_count };
    });

    await scenario("02", "خروجی فعالیت‌ها و ریسک‌ها ستون‌های قراردادی خود را دارند", async () => {
      await exportDataset(page, "activities");
      const activities = await page.evaluate(pageState);
      assert(activities.exportColumns.includes("activity_id"), `activity columns ${activities.exportColumns.join(",")}`);
      assert(activities.exportRows > 0, `activity rows ${activities.exportRows}`);

      await exportDataset(page, "risks");
      const risks = await page.evaluate(pageState);
      assert(risks.exportColumns.includes("score") && risks.exportColumns.includes("exposure"), `risk columns ${risks.exportColumns.join(",")}`);
      await capture(page, "02-activities-and-risks");
      return { activityRows: activities.exportRows, riskColumns: risks.exportColumns.length };
    });

    await scenario("03", "فایل معتبر منابع اعتبارسنجی می‌شود و اعمال برای نقش نویسنده فعال است", async () => {
      await openTab(page, "import");
      await setContent(page, validCsv);
      await validate(page);
      const state = await page.evaluate(pageState);
      assert(state.summary?.valid === "true", `summary ${JSON.stringify(state.summary)}`);
      assert(state.summary?.accepted === "2" && state.summary?.rejected === "0", `counts ${state.summaryText}`);
      assert(state.errors.length === 0, `unexpected errors ${JSON.stringify(state.errors)}`);
      assert(state.applyDisabled === false, "apply must be enabled for a valid file and a write role");
      await capture(page, "03-valid-preview");
      return { accepted: state.summary?.accepted, applyDisabled: state.applyDisabled };
    });

    await scenario("04", "اعمال ایدمپوتنت منابع را می‌نویسد، بازپخش همان اجرا را برمی‌گرداند و تاریخچه ثبت می‌شود", async () => {
      const applied = await api(page, "POST", exchangeUrl("/import"), {
        dataset: "resources",
        content: validCsv,
        idempotency_key: idempotencyKey,
      });
      assert(applied.status === 200 && applied.body.valid === true, `apply ${JSON.stringify(applied).slice(0, 400)}`);
      assert(applied.body.created.join(",") === `${crewId},${childId}`, `created ${JSON.stringify(applied.body.created)}`);
      assert(applied.body.replayed === false, `first apply replayed ${applied.body.replayed}`);

      const replay = await api(page, "POST", exchangeUrl("/import"), {
        dataset: "resources",
        content: validCsv,
        idempotency_key: idempotencyKey,
      });
      assert(replay.status === 200 && replay.body.replayed === true, `replay ${JSON.stringify(replay).slice(0, 300)}`);
      assert(replay.body.run_id === applied.body.run_id, `replay run ${replay.body.run_id} vs ${applied.body.run_id}`);

      const reuse = await api(page, "POST", exchangeUrl("/import"), {
        dataset: "resources",
        content: `${CSV_HEADER}E2E-XCH-OTHER-${stamp},Other,labor,,,,,true\n`,
        idempotency_key: idempotencyKey,
      });
      assert(reuse.status === 409 && reuse.body.code === "EXCHANGE_IDEMPOTENCY_KEY_REUSE", `reuse ${JSON.stringify(reuse).slice(0, 300)}`);

      const exported = await api(page, "GET", exchangeUrl("/export?dataset=resources"));
      assert(exported.body.content.includes(crewId) && exported.body.content.includes(childId), "applied resources are not in the export");

      await page.evaluate('document.querySelector(\'[data-exchange-page] [data-exchange-action="reload"]\').click()');
      await sleep(700);
      await openTab(page, "history");
      const state = await page.evaluate(pageState);
      const appliedRun = state.runs.find((run) => run.id === applied.body.run_id);
      assert(appliedRun, `run ${applied.body.run_id} missing from history: ${JSON.stringify(state.runs.slice(0, 3))}`);
      assert(state.runs.length >= 3, `history runs ${state.runs.length}`);
      await capture(page, "04-applied-and-history");
      return { runId: applied.body.run_id, runs: state.runs.length, reuseStatus: reuse.status };
    });

    await scenario("05", "فایل نامعتبر خطاهای ردیف و فیلد را نشان می‌دهد و اعمال را می‌بندد", async () => {
      await openTab(page, "import");
      await setContent(page, invalidCsv);
      await validate(page);
      const state = await page.evaluate(pageState);
      assert(state.summary?.valid === "false", `summary ${JSON.stringify(state.summary)}`);
      const codes = state.errors.map((error) => `${error.row}:${error.field}:${error.code}`);
      assert(codes.some((code) => code.includes("INVALID_RESOURCE_TYPE")), `type error ${codes.join(",")}`);
      assert(codes.some((code) => code.includes("RESOURCE_CALENDAR_NOT_FOUND")), `calendar error ${codes.join(",")}`);
      assert(codes.some((code) => code.includes("INVALID_RESOURCE_EMAIL")), `email error ${codes.join(",")}`);
      assert(codes.some((code) => code.includes("INVALID_RESOURCE_ACTIVE_FLAG")), `active error ${codes.join(",")}`);
      assert(state.applyDisabled === true, "apply must stay disabled for an invalid file");
      await capture(page, "05-invalid-preview");
      return { errors: state.errors.length };
    });

    await scenario("06", "شناسهٔ موجود و چرخهٔ سلسله‌مراتب پیش از نوشتن رد می‌شوند", async () => {
      const existing = await api(page, "POST", exchangeUrl("/import/preview"), {
        dataset: "resources",
        content: `${CSV_HEADER}${crewId},Duplicate,labor,,,,,true\n`,
      });
      assert(existing.status === 200, `preview ${existing.status}`);
      assert(existing.body.errors.some((error) => error.code === "RESOURCE_ALREADY_EXISTS"), `existing ${JSON.stringify(existing.body.errors)}`);

      const cycle = `${CSV_HEADER}E2E-XCH-A-${stamp},Cycle A,labor,E2E-XCH-B-${stamp},,,,true\nE2E-XCH-B-${stamp},Cycle B,labor,E2E-XCH-A-${stamp},,,,true\n`;
      const looped = await api(page, "POST", exchangeUrl("/import/preview"), {
        dataset: "resources",
        content: cycle,
      });
      assert(looped.status === 200, `cycle preview ${looped.status}`);
      assert(looped.body.errors.filter((error) => error.code === "RESOURCE_HIERARCHY_CYCLE").length === 2, `cycle errors ${JSON.stringify(looped.body.errors)}`);

      const readOnly = await api(page, "POST", exchangeUrl("/import/preview"), {
        dataset: "activities",
        content: "activity_id\nA1\n",
      });
      assert(readOnly.status === 400 && readOnly.body.code === "EXCHANGE_DATASET_READ_ONLY", `read-only ${JSON.stringify(readOnly).slice(0, 200)}`);
      await openTab(page, "export");
      await capture(page, "06-rejected-previews");
      return { existingRejected: true, cycleErrors: looped.body.errors.length };
    });

    await scenario("07", "بازبین خروجی و اعتبارسنجی می‌گیرد اما اعمال مستقیم ۴۰۳ است", async () => {
      await loginAs(page, "Viewer");
      await openExchange(page);
      await exportDataset(page, "resources");
      const state = await page.evaluate(pageState);
      assert(state.exportRows > 0, `viewer export rows ${state.exportRows}`);

      await openTab(page, "import");
      const importState = await page.evaluate(pageState);
      assert(importState.contentDisabled, "viewer content editor must be disabled");
      assert(importState.applyDisabled, "viewer apply must be disabled");

      const denied = await api(page, "POST", exchangeUrl("/import"), {
        dataset: "resources",
        content: `${CSV_HEADER}E2E-XCH-DENIED-${stamp},Denied,labor,,,,,true\n`,
        idempotency_key: `e2e-denied-${stamp}`,
      });
      assert(denied.status === 403 && denied.body.code === "EXCHANGE_PERMISSION_DENIED", `viewer apply ${JSON.stringify(denied).slice(0, 300)}`);
      await capture(page, "07-viewer-read-only");
      return { exportRows: state.exportRows, deniedStatus: denied.status };
    });

    await scenario("08", "چیدمان فارسی راست‌به‌چپ در ۱۲۸۰×۷۲۰ بدون نشان تجاری بیرونی", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await setLanguage(page, "fa");
      await openExchange(page);
      const state = await page.evaluate(pageState);
      assert(state.direction === "rtl", `direction ${state.direction}`);
      assert(state.heading === "ورود / خروجی", `Persian heading ${state.heading}`);
      assert(state.tabs.map((tab) => tab.label).join(",") === "خروجی,ورود,تاریخچهٔ ورود", `Persian tabs ${JSON.stringify(state.tabs.map((tab) => tab.label))}`);
      assert(!/oracle|primavera|\bp6\b/i.test(state.bodyText), "exchange surface leaks third-party branding");
      await capture(page, "08-persian-rtl");
      return { direction: state.direction, heading: state.heading };
    });

    report.status = "pass";
    report.scenarioCount = scenarios.length;
  } catch (error) {
    report.status = "fail";
    report.error = String(error && error.stack ? error.stack : error);
    throw error;
  } finally {
    writeFileSync(join(evidenceDir, "exchange-v26.json"), `${JSON.stringify(report, null, 2)}\n`);
    copyFileSync(join(evidenceDir, "exchange-v26.json"), join(outDir, "exchange-v26.json"));
    log(`\nEvidence: ${evidenceDir}`);
    log(`Scenarios: ${scenarios.filter((item) => item.status === "pass").length}/${scenarios.length} passed`);
    try {
      await chrome.stop();
    } catch {
      // The browser is already gone; the evidence file is what matters.
    }
  }
}

main().catch((error) => {
  process.stderr.write(`\nFAILED: ${error && error.stack ? error.stack : error}\n`);
  process.exitCode = 1;
});
