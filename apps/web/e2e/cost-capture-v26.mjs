#!/usr/bin/env node
/**
 * Browser E2E for Version 26 baseline capture on the Cost Overview window.
 *
 * The page must show only what the server computed: the operator selects a
 * baseline identity, the server captures the latest published schedule
 * snapshot as immutable baseline activities, and the shared earned-value read
 * model measures that stored baseline. The test drives the real local
 * full-stack preview on project preview-rps-01 through headless Chrome; every
 * baseline, expense and earned-value value is read from the real
 * p6-baseline-capture-api.v1, p6-cost-api.v1 and p6-earned-value-read-model.v1
 * HTTP routes backed by the SQLite preview store. Nothing is mocked or
 * injected into the page.
 *
 * Scenarios cover the empty baseline register, capturing the calculated
 * schedule from the UI, idempotent replay, a stale-revision conflict, measuring
 * earned value from the captured baseline, viewer read-only authorization, and
 * the 1280x720 Persian right-to-left layout.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 \
 *   CUBI_TESTED_CODE_SHA=<code commit> \
 *   node e2e/cost-capture-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "cost-capture-v26");
const evidenceDir = join(
  artifactsDir,
  "..",
  "..",
  "..",
  "..",
  "docs",
  "workspace",
  "evidence",
  `cost-capture-v26-${evidenceDate}`,
);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const stamp = Date.now().toString(36).toUpperCase();
const baselineId = `E2E-BL-${stamp}`;
const expenseId = `E2E-EXP-CAP-${stamp}`;
const EXPENSE_ACTIVITY = "A130";
const DATA_DATE = "2026-10-12";

const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const scenarios = [];
const screenshots = [];
const cells = [];

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

async function capture(page, name) {
  const file = `cost-capture-v26/${name}.png`;
  await page.screenshot(file);
  copyFileSync(join(artifactsDir, file), join(evidenceDir, `${name}.png`));
  screenshots.push(`${name}.png`);
  return file;
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

async function openCost(page) {
  const clicked = await page.evaluate(`(() => {
    const buttons = [...document.querySelectorAll('[data-menu="cost"]')];
    const button = buttons.find((item) => item.getClientRects().length > 0) ?? buttons[0];
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, "Cost menu button is missing");
  await page.waitForSelector("[data-cost-page] .cp-register-toolbar", "cost overview window");
  await page.waitFor(
    `(() => {
      const page = document.querySelector("[data-cost-page]");
      if (!page) return false;
      const text = page.textContent || "";
      return !text.includes("Reading stored expenses") && !text.includes("Reading baselines");
    })()`,
    "cost overview settled",
  );
  await sleep(500);
}

const costState = `(() => {
  const page = document.querySelector("[data-cost-page]");
  const select = page?.querySelector('select[name="evm-baseline"]');
  const result = page?.querySelector("[data-cost-evm-result]");
  const notice = page?.querySelector("[data-cost-notice]");
  return {
    heading: page?.querySelector(":scope > .cp-register-toolbar strong")?.textContent?.trim() ?? null,
    baselines: select ? [...select.options].map((option) => option.value) : [],
    selectedBaseline: select?.value ?? null,
    baselineOptionsText: select ? [...select.options].map((option) => option.textContent.trim()) : [],
    noBaselineText: page?.textContent.includes("No baseline is stored.") ?? false,
    captureNew: Boolean(page?.querySelector('[data-cost-capture-action="new"]')),
    captureForm: Boolean(page?.querySelector("[data-cost-capture-form]")),
    captureFields: page?.querySelector("[data-cost-capture-form]")
      ? {
          id: page.querySelector('[data-cost-capture-form] input[name="capture-baseline-id"]')?.value ?? null,
          name: page.querySelector('[data-cost-capture-form] input[name="capture-name"]')?.value ?? null,
          type: page.querySelector('[data-cost-capture-form] select[name="capture-type"]')?.value ?? null,
          currency: page.querySelector('[data-cost-capture-form] input[name="capture-currency"]')?.value ?? null,
        }
      : null,
    measureEnabled: !(page?.querySelector('[data-cost-evm-form] button[type="submit"]')?.disabled ?? true),
    evmForm: page?.querySelector("[data-cost-evm-form]")
      ? {
          dataDate: page.querySelector('[data-cost-evm-form] input[name="evm-data-date"]')?.value ?? null,
          currency: page.querySelector('[data-cost-evm-form] input[name="evm-currency"]')?.value ?? null,
          method: page.querySelector('[data-cost-evm-form] select[name="evm-etc-method"]')?.value ?? null,
        }
      : null,
    notice: notice ? { kind: notice.dataset.state, text: notice.textContent.trim() } : null,
    result: result
      ? Object.fromEntries([...result.querySelectorAll("label")].map((label) => [
          label.firstChild?.textContent?.trim() ?? "",
          label.querySelector("input")?.value ?? null,
        ]))
      : null,
    page: Boolean(page),
  };
})()`;

async function readCost(page) {
  return page.evaluate(costState);
}

async function api(page, method, path, body, extraHeaders = {}) {
  return page.evaluate(
    `(async () => {
      const session = await (await fetch("/api/session")).json();
      const projects = await (await fetch("/api/projects")).json();
      const project = (projects.projects || []).find((item) => item.project_id === ${JSON.stringify(PROJECT)});
      const headers = {
        "Content-Type": "application/json",
        "X-Tenant-Id": session.tenant_id,
        "X-Project-Id": ${JSON.stringify(PROJECT)},
        "X-Project-Revision": String(project ? project.revision : ""),
        ...${JSON.stringify(extraHeaders)},
      };
      const response = await fetch(${JSON.stringify(path)}, {
        method: ${JSON.stringify(method)},
        headers,
        ${body === undefined ? "" : `body: JSON.stringify(${JSON.stringify(body)}),`}
      });
      return { status: response.status, body: await response.json().catch(() => null) };
    })()`,
    { awaitPromise: true },
  );
}

function baselineUrl(suffix = "") {
  return `/api/projects/${PROJECT}/p6/baselines${suffix}`;
}

async function loginAs(page, label) {
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
  const hasPersonas = await page.evaluate('Boolean(document.querySelector(".persona"))');
  if (!hasPersonas) {
    const logoutStatus = await page.evaluate(
      `fetch("/preview/logout", { method: "POST", redirect: "manual" }).then((response) => response.status)`,
      { awaitPromise: true },
    );
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
  await sleep(1400);
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
    if (url.includes("/api/") && params.response.status >= 500) apiFailures.push({ status: params.response.status, url });
  });

  const report = {
    contract: "cubi-cost-capture-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    project: PROJECT,
    baselineId,
    expenseId,
    dataDate: DATA_DATE,
    cells,
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
  };

  try {
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 768, deviceScaleFactor: 1, mobile: false });
    await loginAs(page, "Planner");
    await openCost(page);

    await scenario("01", "Cost Overview without baselines shows the capture entry point and no fabricated values", async () => {
      const state = await readCost(page);
      assert(state.page, "cost overview page missing");
      assert(state.noBaselineText, "the empty baseline register is not stated");
      assert(state.baselines.length === 0, `baselines unexpectedly present: ${JSON.stringify(state.baselines)}`);
      assert(state.captureNew && !state.captureForm, "capture does not start in browse mode");
      assert(!state.measureEnabled, "earned value can be measured without a baseline");
      assert(state.result === null, "an earned-value result is shown without a measurement");
      await capture(page, "01-cost-empty");
      return { baselines: state.baselines.length, captureNew: state.captureNew };
    });

    let expense = null;
    await scenario("02", "a stored expense rolls into the captured baseline budget", async () => {
      const created = await api(page, "POST", `/api/projects/${PROJECT}/p6/expenses`, {
        expense_id: expenseId,
        name: "E2E captured baseline expense",
        category: "equipment",
        currency: "USD",
        activity_id: EXPENSE_ACTIVITY,
        planned_cost: "1000.00",
      });
      assert(created.status === 200, `expense create status ${created.status}: ${JSON.stringify(created.body)}`);
      expense = created.body;
      const row = expense.expense ?? expense.p6_expense ?? expense;
      assert(row.expense_id === expenseId, `stored expense ${JSON.stringify(expense)}`);
      const readBack = await api(page, "GET", `/api/projects/${PROJECT}/p6/expenses/${encodeURIComponent(expenseId)}`);
      assert(readBack.status === 200, `expense read-back status ${readBack.status}`);
      const stored = readBack.body?.expense ?? readBack.body?.p6_expense ?? readBack.body;
      assert(stored.planned_cost === "1000.00" && stored.currency === "USD", `stored expense ${JSON.stringify(stored)}`);
      return { expenseId, activity: stored.activity_id, planned: stored.planned_cost };
    });

    await scenario("03", "capturing from the UI stores the calculated schedule as an immutable baseline", async () => {
      await page.click('[data-cost-capture-action="new"]');
      await page.waitForSelector("[data-cost-capture-form]", "capture form");
      await page.setInput('[data-cost-capture-form] input[name="capture-baseline-id"]', baselineId);
      await page.setInput('[data-cost-capture-form] input[name="capture-name"]', "E2E captured schedule");
      await page.setSelect('[data-cost-capture-form] select[name="capture-type"]', "USER_SELECTED");
      await page.setInput('[data-cost-capture-form] input[name="capture-currency"]', "USD");
      await page.setInput('[data-cost-capture-form] input[name="capture-notes"]', "Captured by the Cost Overview browser acceptance.");
      await capture(page, "03-capture-form");
      await page.click('[data-cost-capture-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-cost-notice][data-state="ok"]')?.textContent?.includes("Baseline captured from the calculated schedule.") ?? false`,
        "capture success notice",
      );
      await page.waitFor(
        `Boolean(document.querySelector('[data-cost-page] select[name="evm-baseline"] option[value="${baselineId}"]'))`,
        "captured baseline listed",
      );
      await sleep(500);
      const state = await readCost(page);
      assert(!state.captureForm, "the capture form did not close after success");
      assert(state.baselines.includes(baselineId), `captured baseline not listed: ${JSON.stringify(state.baselines)}`);
      assert(state.selectedBaseline === baselineId, `captured baseline not selected (${state.selectedBaseline})`);
      const stored = await api(page, "GET", baselineUrl());
      const rows = (stored.body?.baselines ?? []).map((row) => row.baseline ?? row);
      assert(rows.filter((row) => row.baseline_id === baselineId).length === 1, `stored baselines ${JSON.stringify(rows)}`);
      const metadata = rows.find((row) => row.baseline_id === baselineId);
      assert(metadata.baseline_type === "USER_SELECTED" && metadata.source_revision === 7, `baseline metadata ${JSON.stringify(metadata)}`);
      await capture(page, "03-captured-baseline-selected");
      return { metadata, listed: state.baselines };
    });

    await scenario("04", "replaying the same capture is idempotent and never duplicates rows", async () => {
      const replay = await api(page, "POST", baselineUrl("/capture"), {
        contract_version: "p6-baseline-capture-api.v1",
        expected_revision: 7,
        baseline_id: baselineId,
        name: "E2E captured schedule",
        baseline_type: "USER_SELECTED",
        notes: "Captured by the Cost Overview browser acceptance.",
        currency: "USD",
      });
      assert(replay.status === 200, `replay status ${replay.status}: ${JSON.stringify(replay.body)}`);
      assert(replay.body?.replayed === true, `replay flag ${JSON.stringify(replay.body?.replayed)}`);
      assert(replay.body?.baseline?.baseline_id === baselineId, `replay baseline ${JSON.stringify(replay.body?.baseline)}`);
      assert(replay.body?.counts?.activities > 0, `replay activity count ${JSON.stringify(replay.body?.counts)}`);
      assert(replay.body?.snapshot?.snapshot_id, "replay lost the snapshot identity");
      return {
        replayed: replay.body.replayed,
        counts: replay.body.counts,
        snapshot: replay.body.snapshot.snapshot_id,
        excluded: replay.body.excluded_activity_ids,
      };
    });

    await scenario("05", "a stale revision is rejected with a conflict and the page stays unchanged", async () => {
      const stale = await api(page, "POST", baselineUrl("/capture"), {
        contract_version: "p6-baseline-capture-api.v1",
        expected_revision: 6,
        baseline_id: `E2E-BL-STALE-${stamp}`,
        name: "Stale capture",
        baseline_type: "USER_SELECTED",
        currency: "USD",
      });
      assert(stale.status === 409, `stale status ${stale.status}: ${JSON.stringify(stale.body)}`);
      assert(stale.body?.code === "BASELINE_CAPTURE_STALE_REVISION", `stale code ${stale.body?.code}`);
      const state = await readCost(page);
      assert(state.selectedBaseline === baselineId, "a rejected write changed the selected baseline");
      return { status: stale.status, code: stale.body.code };
    });

    await scenario("06", "the captured baseline is measurable through the shared earned-value read model", async () => {
      await page.setSelect('[data-cost-evm-form] select[name="evm-baseline"]', baselineId);
      await page.setInput('[data-cost-evm-form] input[name="evm-data-date"]', DATA_DATE);
      await page.setInput('[data-cost-evm-form] input[name="evm-currency"]', "USD");
      await page.setSelect('[data-cost-evm-form] select[name="evm-etc-method"]', "PF_ONE");
      await capture(page, "06-evm-form");
      await page.click('[data-cost-evm-form] button[type="submit"]');
      await page.waitForSelector("[data-cost-evm-result]", "earned-value result");
      await sleep(400);
      const state = await readCost(page);
      const result = state.result ?? {};
      assert(state.notice === null || state.notice.kind !== "error", `measurement notice ${JSON.stringify(state.notice)}`);
      assert(result["Baseline"] === baselineId, `result baseline ${JSON.stringify(result["Baseline"])}`);
      assert(result["Data Date"] === DATA_DATE, `result data date ${JSON.stringify(result["Data Date"])}`);
      assert(result["Currency"] === "USD", `result currency ${JSON.stringify(result["Currency"])}`);
      assert(result["Budget at Completion"] === "1000.00", `result BAC ${JSON.stringify(result["Budget at Completion"])}`);
      assert(result["Planned Value"] && result["Planned Value"] !== "Not available", `planned value ${JSON.stringify(result["Planned Value"])}`);
      assert(result["Earned Value"] && result["Earned Value"] !== "Not available", `earned value ${JSON.stringify(result["Earned Value"])}`);
      const direct = await api(page, "POST", `/api/projects/${PROJECT}/p6/earned-value`, {
        contract_version: "p6-earned-value-read-model.v1",
        baseline_id: baselineId,
        data_date: DATA_DATE,
        currency: "USD",
        etc_method: "PF_ONE",
      });
      assert(direct.status === 200, `earned-value status ${direct.status}`);
      assert(direct.body?.earned_value?.budget_at_completion === "1000.00", `read model BAC ${JSON.stringify(direct.body?.earned_value?.budget_at_completion)}`);
      assert(result["Budget at Completion"] === direct.body.earned_value.budget_at_completion, "the page disagrees with the read model");
      await capture(page, "06-evm-result");
      const viewportWidth = await page.evaluate("window.innerWidth");
      cells.push({
        viewport: { width: 1366, height: 768 },
        locale: "en",
        baseline: baselineId,
        budgetAtCompletion: result["Budget at Completion"],
        plannedValue: result["Planned Value"],
        documentScrollWidth: await page.evaluate("document.documentElement.scrollWidth"),
        viewportWidth,
      });
      return {
        budgetAtCompletion: result["Budget at Completion"],
        plannedValue: result["Planned Value"],
        earnedValue: result["Earned Value"],
      };
    });

    await scenario("07", "the captured baseline survives a full page reload", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false });
      await sleep(700);
      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "workspace reload");
      await sleep(1500);
      await openCost(page);
      await page.waitFor(
        `Boolean(document.querySelector('[data-cost-page] select[name="evm-baseline"] option[value="${baselineId}"]'))`,
        "captured baseline after reload",
      );
      const state = await readCost(page);
      assert(state.baselines.includes(baselineId), `baseline missing after reload: ${JSON.stringify(state.baselines)}`);
      assert(state.captureNew && !state.captureForm, "capture entry point missing after reload");
      await capture(page, "07-after-reload-1920");
      return { baselines: state.baselines };
    });

    await scenario("08", "a viewer sees the stored baseline read-only and cannot capture", async () => {
      await loginAs(page, "Viewer");
      await openCost(page);
      const state = await readCost(page);
      assert(state.baselines.includes(baselineId), "the stored baseline is not readable by a viewer");
      assert(!state.captureNew && !state.captureForm, "a viewer is offered the capture form");
      const denied = await api(page, "POST", baselineUrl("/capture"), {
        contract_version: "p6-baseline-capture-api.v1",
        expected_revision: 7,
        baseline_id: `E2E-BL-VIEWER-${stamp}`,
        name: "Viewer capture",
        baseline_type: "USER_SELECTED",
        currency: "USD",
      });
      assert(denied.status === 403, `viewer capture status ${denied.status}: ${JSON.stringify(denied.body)}`);
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await sleep(700);
      await setLanguage(page, "fa");
      const settled = await readCost(page);
      assert(settled.heading, "cost heading missing in Persian layout");
      assert(!settled.captureNew, "capture button visible in Persian viewer layout");
      await capture(page, "08-fa-rtl-1280x720-viewer");
      const direction = await page.evaluate('document.documentElement.getAttribute("dir")');
      assert(direction === "rtl", `document direction ${direction}`);
      cells.push({
        viewport: { width: 1280, height: 720 },
        locale: "fa",
        role: "viewer",
        direction,
        documentScrollWidth: await page.evaluate("document.documentElement.scrollWidth"),
        viewportWidth: await page.evaluate("window.innerWidth"),
      });
      return { status: denied.status, baselines: settled.baselines.length, direction };
    });

    assert(exceptions.length === 0, `runtime exceptions: ${exceptions.join(" | ")}`);
    assert(consoleErrors.length === 0, `console errors: ${consoleErrors.join(" | ")}`);
    assert(apiFailures.length === 0, `HTTP 5xx responses: ${JSON.stringify(apiFailures)}`);
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(outDir, "cost-capture-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(evidenceDir, "cost-capture-v26.json"), JSON.stringify(report, null, 2));
    log(`\nPASS ${scenarios.length} scenarios, ${screenshots.length} screenshots at ${testedCodeSha}`);
  } catch (error) {
    report.finishedAt = new Date().toISOString();
    report.error = String(error && error.stack ? error.stack : error);
    writeFileSync(join(outDir, "cost-capture-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(evidenceDir, "cost-capture-v26.json"), JSON.stringify(report, null, 2));
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
