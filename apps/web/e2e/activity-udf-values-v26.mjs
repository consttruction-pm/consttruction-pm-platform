#!/usr/bin/env node
/**
 * Browser E2E for typed Activity Details UDF value editing.
 *
 * The UDFs tab previously listed definition metadata only. This suite creates
 * two project UDF definitions, edits the writable one through the real details
 * form, verifies the stored value through the HTTP contract, reloads the whole
 * page, clears a nullable value, and checks that a viewer receives a read-only
 * table with no form. The Persian and 1920x1080 cells verify labels, RTL and
 * viewport fit.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 node e2e/activity-udf-values-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const projectId = "preview-rps-01";
const registry = "p6-field-registry.v1";
const outDir = join(artifactsDir, "activity-udf-values-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `activity-udf-values-v26-${evidenceDate}`);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const scenarios = [];
const screenshots = [];

const WRITABLE_UDF = "activity.e2e_contract_status";
const READ_ONLY_UDF = "activity.e2e_audit_ref";
const DATETIME_UDF = "activity.e2e_review_at";
const DURATION_UDF = "activity.e2e_cure_time";

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
  const file = `activity-udf-values-v26/${name}.png`;
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

async function loginAs(page, role, locale = "en") {
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
  let hasPersonas = await page.evaluate(`Boolean(document.querySelector('button[name="role"][value="${role}"]'))`);
  if (!hasPersonas) {
    const logoutStatus = await page.evaluate(
      `fetch("/preview/logout", { method: "POST", redirect: "manual" }).then((response) => response.status)`,
      { awaitPromise: true },
    );
    assert([0, 200, 302, 303].includes(logoutStatus), `unexpected logout status ${logoutStatus}`);
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, `button[name="role"][value="${role}"]`, "persona cards after sign out");
    hasPersonas = true;
  }
  const clicked = await page.evaluate(`(() => {
    const button = document.querySelector('button[name="role"][value="${role}"]');
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `${role} login button is missing`);
  await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
  await page.click('[data-project-id="preview-rps-01"]');
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
  await sleep(1400);
  await setLanguage(page, locale);
}

async function createUdf(page, payload) {
  return page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${projectId}/p6/udfs/${registry}", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: ${JSON.stringify(JSON.stringify(payload))},
    });
    let body = null;
    try { body = await response.json(); } catch {}
    return { status: response.status, body };
  })()`, { awaitPromise: true });
}

async function readValues(page, activityId) {
  return page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${projectId}/p6/udf-values/${registry}/activity/${encodeURIComponent(activityId)}");
    let body = null;
    try { body = await response.json(); } catch {}
    return { status: response.status, body };
  })()`, { awaitPromise: true });
}

async function openDetailsUdfTab(page) {
  const selected = await page.evaluate(`(() => {
    const row = document.querySelector("#cp-activity-grid tbody tr[data-activity-id]");
    if (!row) return false;
    row.click();
    return true;
  })()`);
  assert(selected, "no activity row could be selected");
  await sleep(900);
  await page.evaluate(`(() => {
    const toggle = document.querySelector("[data-details-toggle]");
    if (toggle && toggle.dataset.detailsVisible !== "true") toggle.click();
  })()`);
  await page.waitForSelector('#cp-details [data-detail-tab="udfs"]', "UDF details tab", 15000);
  await sleep(500);
  const opened = await page.evaluate(`(() => {
    const tab = document.querySelector('#cp-details [data-detail-tab="udfs"]');
    if (!tab) return false;
    tab.click();
    return true;
  })()`);
  assert(opened, "UDF details tab could not be opened");
  await page.waitForSelector('[data-details-refresh="udfs"]', "UDF reload control", 15000);
  await sleep(700);
}

async function reloadUdfValues(page) {
  const clicked = await page.evaluate(`(() => {
    const button = document.querySelector('[data-details-refresh="udfs"]');
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, "UDF reload control is missing");
  await sleep(1600);
}

const udfState = `(() => {
  const panel = document.querySelector('#cp-details [data-detail-panel="udfs"]');
  const form = panel?.querySelector('[data-details-form="udf-values"]');
  const writable = panel?.querySelector('[data-udf-value-input="${WRITABLE_UDF}"]') ?? null;
  const readOnly = panel?.querySelector('[data-udf-value-input="${READ_ONLY_UDF}"]') ?? null;
  const rect = panel?.getBoundingClientRect() ?? null;
  return {
    panel: Boolean(panel),
    form: Boolean(form),
    writablePresent: Boolean(writable),
    writableTag: writable?.tagName ?? null,
    writableValue: writable?.value ?? null,
    readOnlyInput: Boolean(readOnly),
    rows: panel?.querySelectorAll("[data-udf-value-row]").length ?? 0,
    tableText: panel?.textContent ?? "",
    submitLabel: form?.querySelector('button[type="submit"]')?.textContent?.trim() ?? null,
    message: form?.querySelector("[data-details-form-message]")?.textContent?.trim() ?? null,
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
    contract: "cubi-activity-udf-values-v26.v1",
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

  let activityId = null;

  try {
    await setViewport(page, 1280, 720);
    await loginAs(page, "admin", "en");
    activityId = await page.evaluate(`document.querySelector("#cp-activity-grid tbody tr[data-activity-id]")?.dataset.activityId ?? null`);
    assert(activityId, "no activity id is available");

    const writable = await createUdf(page, {
      udf_id: WRITABLE_UDF,
      subject_area: "activity",
      display_name: "E2E Contract Status",
      data_type: "enum",
      writable: true,
      nullable: true,
      unit: null,
      allowed_values: ["draft", "signed", "closed"],
    });
    assert(writable.status === 200, `writable UDF definition status ${writable.status}`);
    const readOnly = await createUdf(page, {
      udf_id: READ_ONLY_UDF,
      subject_area: "activity",
      display_name: "E2E Audit Reference",
      data_type: "string",
      writable: false,
      nullable: false,
      unit: null,
      allowed_values: [],
    });
    assert(readOnly.status === 200, `read-only UDF definition status ${readOnly.status}`);
    const reviewAt = await createUdf(page, {
      udf_id: DATETIME_UDF,
      subject_area: "activity",
      display_name: "E2E Review At",
      data_type: "datetime",
      writable: true,
      nullable: true,
      unit: null,
      allowed_values: [],
    });
    assert(reviewAt.status === 200, `datetime UDF definition status ${reviewAt.status}`);
    const cureTime = await createUdf(page, {
      udf_id: DURATION_UDF,
      subject_area: "activity",
      display_name: "E2E Cure Time",
      data_type: "duration",
      writable: true,
      nullable: true,
      unit: "day",
      allowed_values: [],
    });
    assert(cureTime.status === 200, `duration UDF definition status ${cureTime.status}`);

    await openDetailsUdfTab(page);
    await reloadUdfValues(page);

    await scenario("01", "an administrator edits a typed UDF and the value survives a full reload", async () => {
      const before = await page.evaluate(udfState);
      assert(before.panel, "UDF panel is missing");
      assert(before.form, "editable UDF form is missing for the administrator");
      assert(before.writablePresent, "writable UDF input is missing");
      assert(before.writableTag === "SELECT", `writable control is ${before.writableTag}`);
      assert(before.readOnlyInput === false, "read-only UDF unexpectedly rendered an input");
      assert(before.rows === 4, `expected four UDF rows, saw ${before.rows}`);
      assert(before.tableText.includes("E2E Audit Reference"), "read-only UDF is not listed");
      await capture(page, "01-udf-form-en-1280x720");

      const changed = await page.evaluate(`(() => {
        const select = document.querySelector('[data-udf-value-input="${WRITABLE_UDF}"]');
        if (!select) return false;
        select.value = "signed";
        select.dispatchEvent(new Event("change", { bubbles: true }));
        return select.value === "signed";
      })()`);
      assert(changed, "writable UDF select did not accept signed");
      const saved = await page.evaluate(`(() => {
        const form = document.querySelector('[data-details-form="udf-values"]');
        const button = form?.querySelector('button[type="submit"]');
        if (!button) return false;
        button.click();
        return true;
      })()`);
      assert(saved, "Save values could not be clicked");
      await page.waitFor(`(() => {
        const text = document.querySelector('[data-details-form="udf-values"] [data-details-form-message]')?.textContent ?? "";
        return text.includes("Saved");
      })()`, "saved UDF message", 20000);

      const stored = await readValues(page, activityId);
      assert(stored.status === 200, `UDF value read status ${stored.status}`);
      const record = (stored.body.values ?? []).find((item) => item.udf_id === WRITABLE_UDF);
      assert(record, "stored UDF value is missing from the API");
      assert(record.value === "signed", `stored UDF value is ${JSON.stringify(record.value)}`);
      await capture(page, "02-udf-saved-en-1280x720");

      await page.reload('#cp-activity-grid tbody tr[data-activity-id]', "workspace reload");
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows after reload");
      await sleep(1000);
      await openDetailsUdfTab(page);
      await reloadUdfValues(page);
      const afterReload = await page.evaluate(udfState);
      assert(afterReload.form, "UDF form is missing after reload");
      assert(afterReload.writableValue === "signed", `reloaded UDF value is ${afterReload.writableValue}`);
      return { activityId, value: record.value };
    });

    await scenario("02", "the Persian details pane shows the localized UDF editor in RTL at 1366x768", async () => {
      await setViewport(page, 1366, 768);
      await setLanguage(page, "fa");
      await sleep(700);
      const state = await page.evaluate(udfState);
      assert(state.panel, "UDF panel is missing in Persian");
      assert(state.form, "UDF form is missing in Persian");
      assert(state.direction === "rtl", `direction is ${state.direction}`);
      assert(state.locale === "fa", `locale is ${state.locale}`);
      assert(state.submitLabel === "ذخیره مقادیر", `submit label is ${state.submitLabel}`);
      assert(state.tableText.includes("فیلد سفارشی"), "localized UDF heading is missing");
      assert(state.withinViewport === true, "UDF panel leaves the 1366x768 viewport");
      assert(state.horizontalOverflow <= 1, `horizontal overflow is ${state.horizontalOverflow}px`);
      await capture(page, "03-udf-form-fa-1366x768");
      return { submitLabel: state.submitLabel, direction: state.direction };
    });

    await scenario("03", "a nullable UDF can be cleared and the cleared value survives a reload at 1920x1080", async () => {
      await setViewport(page, 1920, 1080);
      await setLanguage(page, "en");
      await sleep(700);
      const cleared = await page.evaluate(`(() => {
        const select = document.querySelector('[data-udf-value-input="${WRITABLE_UDF}"]');
        if (!select) return false;
        select.value = "";
        select.dispatchEvent(new Event("change", { bubbles: true }));
        const form = document.querySelector('[data-details-form="udf-values"]');
        form?.querySelector('button[type="submit"]')?.click();
        return select.value === "";
      })()`);
      assert(cleared, "nullable UDF could not be cleared");
      await page.waitFor(`(() => {
        const text = document.querySelector('[data-details-form="udf-values"] [data-details-form-message]')?.textContent ?? "";
        return text.includes("Saved");
      })()`, "saved cleared UDF message", 20000);
      const stored = await readValues(page, activityId);
      const record = (stored.body.values ?? []).find((item) => item.udf_id === WRITABLE_UDF);
      assert(record && record.value === null, `cleared UDF value is ${JSON.stringify(record?.value)}`);
      const state = await page.evaluate(udfState);
      assert(state.withinViewport === true, "UDF panel leaves the 1920x1080 viewport");
      assert(state.horizontalOverflow <= 1, `horizontal overflow is ${state.horizontalOverflow}px at 1920x1080`);
      await capture(page, "04-udf-cleared-en-1920x1080");

      await page.reload('#cp-activity-grid tbody tr[data-activity-id]', "workspace reload after clear");
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows after clear");
      await sleep(1000);
      await openDetailsUdfTab(page);
      await reloadUdfValues(page);
      const afterReload = await page.evaluate(udfState);
      assert(afterReload.writableValue === "", `reloaded cleared UDF value is ${afterReload.writableValue}`);
      return { value: record.value };
    });

    await scenario("04", "datetime and duration UDFs use typed controls and survive a reload", async () => {
      await setViewport(page, 1280, 720);
      await setLanguage(page, "en");
      await sleep(600);
      const typed = await page.evaluate(`(() => {
        const date = document.querySelector('[data-udf-value-input="${DATETIME_UDF}"]');
        const amount = document.querySelector('[data-udf-value-input="${DURATION_UDF}"]');
        const unit = document.querySelector('[data-udf-duration-unit="${DURATION_UDF}"]');
        if (!date || !amount || !unit) return { ok: false, reason: "missing control" };
        date.value = "2026-12-01T09:15";
        date.dispatchEvent(new Event("input", { bubbles: true }));
        amount.value = "10";
        amount.dispatchEvent(new Event("input", { bubbles: true }));
        unit.value = "hour";
        unit.dispatchEvent(new Event("change", { bubbles: true }));
        return {
          ok: true,
          dateType: date.type,
          amountType: amount.type,
          unit: unit.value,
        };
      })()`);
      assert(typed.ok, `typed UDF controls are missing: ${typed.reason ?? "unknown"}`);
      assert(typed.dateType === "datetime-local", `datetime control type is ${typed.dateType}`);
      assert(typed.amountType === "number", `duration control type is ${typed.amountType}`);
      const saved = await page.evaluate(`(() => {
        const form = document.querySelector('[data-details-form="udf-values"]');
        const button = form?.querySelector('button[type="submit"]');
        if (!button) return false;
        button.click();
        return true;
      })()`);
      assert(saved, "Save values could not be clicked for typed UDFs");
      await page.waitFor(`(() => {
        const text = document.querySelector('[data-details-form="udf-values"] [data-details-form-message]')?.textContent ?? "";
        return text.includes("Saved");
      })()`, "saved typed UDF message", 20000);

      const stored = await readValues(page, activityId);
      const dateRecord = (stored.body.values ?? []).find((item) => item.udf_id === DATETIME_UDF);
      const durationRecord = (stored.body.values ?? []).find((item) => item.udf_id === DURATION_UDF);
      const expected = new Date("2026-12-01T09:15").toISOString();
      assert(
        typeof dateRecord?.value === "string" && Date.parse(dateRecord.value) === Date.parse(expected),
        `stored datetime is ${JSON.stringify(dateRecord?.value)}`,
      );
      assert(durationRecord?.value?.value === "10", `stored duration amount is ${JSON.stringify(durationRecord?.value)}`);
      assert(durationRecord?.value?.unit === "hour", `stored duration unit is ${JSON.stringify(durationRecord?.value)}`);
      await capture(page, "06-udf-typed-en-1280x720");

      await page.reload('#cp-activity-grid tbody tr[data-activity-id]', "workspace reload after typed values");
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows after typed save");
      await sleep(1000);
      await openDetailsUdfTab(page);
      await reloadUdfValues(page);
      const afterReload = await page.evaluate(`(() => {
        const date = document.querySelector('[data-udf-value-input="${DATETIME_UDF}"]');
        const amount = document.querySelector('[data-udf-value-input="${DURATION_UDF}"]');
        const unit = document.querySelector('[data-udf-duration-unit="${DURATION_UDF}"]');
        return { date: date?.value ?? null, amount: amount?.value ?? null, unit: unit?.value ?? null };
      })()`);
      assert(afterReload.date === "2026-12-01T09:15", `reloaded datetime input is ${afterReload.date}`);
      assert(afterReload.amount === "10", `reloaded duration amount is ${afterReload.amount}`);
      assert(afterReload.unit === "hour", `reloaded duration unit is ${afterReload.unit}`);
      return { datetime: expected, duration: durationRecord.value };
    });

    await scenario("05", "a viewer sees stored UDF values without an editor and cannot write", async () => {
      await setViewport(page, 1280, 720);
      await loginAs(page, "viewer", "en");
      await openDetailsUdfTab(page);
      await reloadUdfValues(page);
      const state = await page.evaluate(udfState);
      assert(state.panel, "UDF panel is missing for the viewer");
      assert(state.form === false, "viewer received a UDF write form");
      assert(state.readOnlyInput === false, "viewer received an input for the read-only UDF");
      assert(state.tableText.includes("E2E Contract Status"), "viewer cannot see the stored UDF definition");
      const denied = await page.evaluate(`(async () => {
        const response = await fetch("/api/projects/${projectId}/p6/udf-values/${registry}/activity/${encodeURIComponent(activityId)}/${WRITABLE_UDF}", {
          method: "PUT",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ value: "signed" }),
        });
        let body = null;
        try { body = await response.json(); } catch {}
        return { status: response.status, body };
      })()`, { awaitPromise: true });
      assert(denied.status === 403, `viewer write status ${denied.status}`);
      assert(denied.body?.code === "P6_UDF_VALUE_PERMISSION_DENIED", `viewer write code ${denied.body?.code}`);
      await capture(page, "05-udf-viewer-en-1280x720");
      return { httpStatus: denied.status };
    });

    assert(exceptions.length === 0, `uncaught page exceptions: ${JSON.stringify(exceptions.slice(0, 3))}`);
    assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors.slice(0, 3))}`);
    assert(apiFailures.length === 0, `API 5xx responses: ${JSON.stringify(apiFailures.slice(0, 3))}`);
  } finally {
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(outDir, "activity-udf-values-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(evidenceDir, "activity-udf-values-v26.json"), JSON.stringify(report, null, 2));
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
