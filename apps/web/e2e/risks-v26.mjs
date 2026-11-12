#!/usr/bin/env node
/**
 * Browser E2E for the Version 26 project risk register.
 *
 * It drives the real local full-stack preview on project preview-rps-01 with
 * headless Chrome through the DevTools protocol. Every risk is read from and
 * written to the real p6-risk-api.v1 HTTP routes and SQLite preview repository;
 * no page fixture is injected and no API response is mocked. Exposure is always
 * the server-derived probability x impact score, never a UI guess.
 *
 * Scenarios cover the empty register, creation, the scoring matrix, a
 * revision-guarded edit with a stale 409, the closure-note rule and status
 * graph, immutable history, server-side filters, persistence after reload,
 * viewer read-only authorization, the 1280x720 Persian right-to-left layout and
 * deletion with a 404 read.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 node e2e/risks-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "risks-v26");
const evidenceDir = join(
  artifactsDir,
  "..",
  "..",
  "..",
  "..",
  "docs",
  "workspace",
  "evidence",
  `risks-v26-${evidenceDate}`,
);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const stamp = Date.now().toString(36).toUpperCase();
const riskId = `E2E-RK-${stamp}`;

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

const registerState = `(() => {
  const page = document.querySelector("[data-risks-page]");
  const cells = (row) => [...row.querySelectorAll("td")].map((cell) => (cell.textContent || "").trim());
  const risks = [...page?.querySelectorAll("[data-risk-row]") ?? []].map((row) => {
    const values = cells(row);
    const id = row.dataset.riskId;
    return {
      id,
      title: row.querySelector("td span")?.textContent?.trim() ?? null,
      category: values[1],
      probabilityImpact: values[2],
      scoreExposure: values[3],
      response: values[4],
      owner: values[5],
      status: values[6],
      selected: row.classList.contains("is-selected"),
      edit: Boolean(page.querySelector('[data-risk-edit="' + id + '"]')),
      remove: Boolean(page.querySelector('[data-risk-delete="' + id + '"]')),
    };
  });
  const matrix = [...page?.querySelectorAll("[data-risk-matrix-cell]") ?? []].map((cell) => ({
    key: cell.dataset.riskMatrixCell,
    exposure: cell.dataset.exposure,
    count: Number((cell.textContent || "").trim() || "0"),
  }));
  const history = [...page?.querySelectorAll(".cp-risk-history li") ?? []].map((item) => item.textContent.trim());
  const form = page?.querySelector("[data-risk-form]");
  const notice = page?.querySelector("[data-risk-notice]");
  return {
    activeMenu: document.querySelector(".cp-workspace")?.dataset.activeMenu ?? null,
    heading: page?.querySelector(":scope > .cp-register-toolbar strong")?.textContent?.trim() ?? null,
    reading: (page?.textContent ?? "").includes("Reading project risks"),
    empty: [...page?.querySelectorAll(".cp-calendar-empty") ?? []].map((item) => item.textContent.trim()),
    risks,
    matrix,
    history,
    notice: notice ? { kind: notice.dataset.state, text: notice.textContent.trim() } : null,
    newRisk: Boolean(page?.querySelector('[data-risk-action="new"]')),
    form: form ? {
      id: form.querySelector('input[name="risk-id"]')?.value ?? null,
      readonly: Boolean(form.querySelector('input[name="risk-id"]')?.hasAttribute("readonly")),
      title: form.querySelector('input[name="risk-title"]')?.value ?? null,
      category: form.querySelector('select[name="risk-category"]')?.value ?? null,
      status: form.querySelector('select[name="risk-status"]')?.value ?? null,
      probability: form.querySelector('select[name="risk-probability"]')?.value ?? null,
      impact: form.querySelector('select[name="risk-impact"]')?.value ?? null,
      strategy: form.querySelector('select[name="risk-strategy"]')?.value ?? null,
      owner: form.querySelector('input[name="risk-owner"]')?.value ?? null,
      closure: form.querySelector('input[name="risk-closure-note"]')?.value ?? null,
    } : null,
    page: Boolean(page),
  };
})()`;

async function capture(page, name) {
  const file = `risks-v26/${name}.png`;
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
  await sleep(600);
}

async function openRisks(page) {
  await openMenu(page, "risks", "[data-risks-page] .cp-register-toolbar", "risks panel");
  await page.waitFor(
    `(() => {
      const page = document.querySelector("[data-risks-page]");
      return Boolean(page) && !page.textContent.includes("Reading project risks");
    })()`,
    "risk register settled",
  );
  await sleep(400);
}

function riskUrl(suffix = "") {
  return `/api/projects/${PROJECT}/risks${suffix}`;
}

async function api(page, method, path, body) {
  return page.evaluate(`(async () => {
    const response = await fetch(${JSON.stringify(path)}, {
      method: ${JSON.stringify(method)},
      headers: { "Content-Type": "application/json", "Idempotency-Key": "e2e-risk-" + Math.random().toString(36).slice(2) },
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
  await sleep(1400);
  await setLanguage(page, "en");
}

async function fillForm(page, values) {
  if (values.id !== undefined) await page.setInput('[data-risk-form] input[name="risk-id"]', values.id);
  if (values.title !== undefined) await page.setInput('[data-risk-form] input[name="risk-title"]', values.title);
  if (values.category) await page.setSelect('[data-risk-form] select[name="risk-category"]', values.category);
  if (values.status) await page.setSelect('[data-risk-form] select[name="risk-status"]', values.status);
  if (values.probability) await page.setSelect('[data-risk-form] select[name="risk-probability"]', String(values.probability));
  if (values.impact) await page.setSelect('[data-risk-form] select[name="risk-impact"]', String(values.impact));
  if (values.strategy) await page.setSelect('[data-risk-form] select[name="risk-strategy"]', values.strategy);
  if (values.owner !== undefined) await page.setInput('[data-risk-form] input[name="risk-owner"]', values.owner);
  if (values.responseOwner !== undefined) await page.setInput('[data-risk-form] input[name="risk-response-owner"]', values.responseOwner);
  if (values.responseDue !== undefined) await page.setInput('[data-risk-form] input[name="risk-response-due"]', values.responseDue);
  if (values.manager !== undefined) await page.setInput('[data-risk-form] input[name="risk-manager"]', values.manager);
  if (values.identified !== undefined) await page.setInput('[data-risk-form] input[name="risk-identified"]', values.identified);
  if (values.description !== undefined) await page.setInput('[data-risk-form] textarea[name="risk-description"]', values.description);
  if (values.closure !== undefined) await page.setInput('[data-risk-form] input[name="risk-closure-note"]', values.closure);
}

async function selectRisk(page, id) {
  await page.click(`[data-risk-row][data-risk-id="${id}"]`);
  await page.waitFor(
    `(() => {
      const page = document.querySelector("[data-risks-page]");
      if (!page) return false;
      const row = page.querySelector('[data-risk-row][data-risk-id="${id}"]');
      return Boolean(row?.classList.contains("is-selected")) &&
        !page.textContent.includes("Reading risk history");
    })()`,
    `risk ${id} details settled`,
  );
  await sleep(300);
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
    contract: "cubi-risks-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    riskId,
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
  };

  try {
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
    await sleep(400);
    await loginAs(page, "Planner");
    await openRisks(page);

    await scenario("01", "فهرست ریسک خالی است و کنترل ساخت برای Planner نمایش داده می‌شود", async () => {
      const state = await page.evaluate(registerState);
      assert(state.page, "the risks page is missing");
      assert(state.activeMenu === "risks", `active menu is ${state.activeMenu}`);
      assert(state.heading === "Project Risks", `risk heading is ${state.heading}`);
      assert(state.risks.length === 0, `register starts with ${state.risks.length} risks`);
      assert(state.empty.some((text) => /No risks are stored/.test(text)), `empty copy ${JSON.stringify(state.empty)}`);
      assert(state.newRisk, "planner cannot open the risk form");
      assert(state.matrix.length === 25, `risk matrix cells ${state.matrix.length}`);
      const stored = await api(page, "GET", riskUrl());
      assert(stored.status === 200 && stored.body.risks.length === 0, `server risks ${JSON.stringify(stored.body)}`);
      await capture(page, "01-empty-register");
      return { risks: 0, matrixCells: state.matrix.length };
    });

    await scenario("02", "ریسک زمان‌بندی با احتمال ۳ و اثر ۴ امتیاز ۱۲ و مواجههٔ زیاد می‌سازد", async () => {
      await page.click('[data-risk-action="new"]');
      await page.waitForSelector("[data-risk-form]", "risk form");
      await fillForm(page, {
        id: riskId,
        title: "E2E supplier lead time",
        category: "schedule",
        status: "open",
        probability: 3,
        impact: 4,
        strategy: "mitigate",
        owner: "preview-planner",
        responseOwner: "preview-planner",
        responseDue: "2026-12-15",
        manager: "preview-planner",
        identified: "2026-11-05",
        description: "E2E risk created against the real risk register.",
      });
      await page.click('[data-risk-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-risk-notice][data-state="ok"]')?.textContent?.includes("Risk saved.") ?? false`,
        "risk saved notice",
      );
      await page.waitForSelector(`[data-risk-row][data-risk-id="${riskId}"]`, `risk row ${riskId}`);
      await sleep(400);
      const state = await page.evaluate(registerState);
      const row = state.risks.find((item) => item.id === riskId);
      assert(row, `created risk missing: ${JSON.stringify(state.risks)}`);
      assert(row.title === "E2E supplier lead time", `row title ${JSON.stringify(row)}`);
      assert(row.category === "Schedule" && row.probabilityImpact === "3 × 4", `row P×I ${JSON.stringify(row)}`);
      assert(row.scoreExposure === "12 · High", `row score ${JSON.stringify(row)}`);
      assert(row.response === "Mitigate" && row.owner === "preview-planner" && row.status === "Open", `row response ${JSON.stringify(row)}`);
      const stored = await api(page, "GET", riskUrl(`/${encodeURIComponent(riskId)}`));
      assert(stored.status === 200 && stored.body.revision === 1, `stored risk ${JSON.stringify(stored.body)}`);
      assert(stored.body.score === 12 && stored.body.exposure_level === "high", `derived exposure ${JSON.stringify(stored.body)}`);
      await capture(page, "02-created-risk");
      return { row, stored: stored.body };
    });

    await scenario("03", "ماتریس ۵×۵ ریسک را در خانهٔ احتمال ۳ و اثر ۴ می‌شمارد", async () => {
      const state = await page.evaluate(registerState);
      const cell = state.matrix.find((item) => item.key === "3-4");
      assert(cell, `matrix cell 3-4 missing`);
      assert(cell.exposure === "high" && cell.count === 1, `matrix cell ${JSON.stringify(cell)}`);
      assert(state.matrix.find((item) => item.key === "5-5").exposure === "critical", "matrix 5-5 is not critical");
      assert(state.matrix.find((item) => item.key === "1-1").exposure === "low", "matrix 1-1 is not low");
      await capture(page, "03-scoring-matrix");
      return { cell };
    });

    await scenario("04", "ویرایش به احتمال ۴ و اثر ۵ امتیاز ۲۰ بحرانی می‌سازد و نوشتن کهنه ۴۰۹ است", async () => {
      await selectRisk(page, riskId);
      await page.click(`[data-risk-edit="${riskId}"]`);
      await page.waitForSelector("[data-risk-form]", "edit risk form");
      const form = await page.evaluate(registerState);
      assert(form.form?.readonly === true && form.form?.probability === "3", `edit form ${JSON.stringify(form.form)}`);
      await page.setSelect('[data-risk-form] select[name="risk-probability"]', "4");
      await page.setSelect('[data-risk-form] select[name="risk-impact"]', "5");
      await page.setSelect('[data-risk-form] select[name="risk-status"]', "monitoring");
      await page.click('[data-risk-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-risk-notice][data-state="ok"]')?.textContent?.includes("Risk saved.") ?? false`,
        "risk edit saved",
      );
      await sleep(600);
      const state = await page.evaluate(registerState);
      const row = state.risks.find((item) => item.id === riskId);
      assert(row?.scoreExposure === "20 · Critical", `edited row ${JSON.stringify(row)}`);
      assert(row?.status === "Monitoring", `edited status ${JSON.stringify(row)}`);
      assert(state.matrix.find((item) => item.key === "4-5").count === 1, "matrix did not move to 4-5");
      const stored = await api(page, "GET", riskUrl(`/${encodeURIComponent(riskId)}`));
      assert(stored.body.revision === 2 && stored.body.score === 20, `revision after edit ${JSON.stringify(stored.body)}`);
      const stale = await api(page, "PATCH", riskUrl(`/${encodeURIComponent(riskId)}`), {
        risk_id: riskId,
        title: "E2E stale write",
        description: "stale",
        category: "schedule",
        status: "mitigating",
        probability: 2,
        impact: 2,
        response_strategy: "accept",
        owner: "preview-planner",
        date_identified: "2026-11-05",
        expected_revision: 1,
      });
      assert(stale.status === 409 && stale.body.code === "RISK_REVISION_CONFLICT", `stale write ${JSON.stringify(stale)}`);
      await capture(page, "04-edited-and-stale-conflict");
      return { row, staleStatus: stale.status };
    });

    await scenario("05", "بستن ریسک بدون یادداشت رد می‌شود و با یادداشت ثبت می‌شود", async () => {
      await page.click(`[data-risk-edit="${riskId}"]`);
      await page.waitForSelector("[data-risk-form]", "edit risk form for closure");
      await page.setSelect('[data-risk-form] select[name="risk-status"]', "closed");
      await page.click('[data-risk-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-risk-notice][data-state="error"]')?.textContent?.includes("RISK_CLOSURE_NOTE_REQUIRED") ?? false`,
        "closure note required notice",
      );
      await capture(page, "05-closure-note-required");
      await page.setInput('[data-risk-form] input[name="risk-closure-note"]', "Response delivered on time.");
      await page.click('[data-risk-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-risk-notice][data-state="ok"]')?.textContent?.includes("Risk saved.") ?? false`,
        "risk closed",
      );
      await sleep(600);
      const state = await page.evaluate(registerState);
      const row = state.risks.find((item) => item.id === riskId);
      assert(row?.status === "Closed", `closed row ${JSON.stringify(row)}`);
      const stored = await api(page, "GET", riskUrl(`/${encodeURIComponent(riskId)}`));
      assert(stored.body.status === "closed" && stored.body.closure_note === "Response delivered on time.", `stored closure ${JSON.stringify(stored.body)}`);
      await capture(page, "06-closed-with-note");
      return { status: stored.body.status, revision: stored.body.revision };
    });

    await scenario("06", "تاریخچهٔ تغییرناپذیر ساخت، ویرایش و بستن را نشان می‌دهد", async () => {
      await selectRisk(page, riskId);
      const state = await page.evaluate(registerState);
      assert(state.history.length === 3, `history ${JSON.stringify(state.history)}`);
      assert(state.history[0].includes("created"), `history created ${JSON.stringify(state.history)}`);
      assert(state.history[1].includes("status_changed"), `history edit ${JSON.stringify(state.history)}`);
      assert(state.history[1].includes("Plan approved") === false, "unexpected audit reason");
      assert(state.history[2].includes("status_changed"), `history close ${JSON.stringify(state.history)}`);
      const server = await api(page, "GET", riskUrl(`/${encodeURIComponent(riskId)}/history`));
      assert(server.status === 200 && server.body.events.length === 3, `server history ${JSON.stringify(server.body)}`);
      await capture(page, "07-history");
      return { events: server.body.events.length };
    });

    await scenario("07", "صافی‌های دسته، وضعیت، راهبرد، مواجهه و جستجو روی فهرست اعمال می‌شوند", async () => {
      await page.setSelect('select[name="risk-category-filter"]', "schedule");
      await page.waitForSelector(`[data-risk-row][data-risk-id="${riskId}"]`, "filtered risk row");
      await page.setSelect('select[name="risk-status-filter"]', "closed");
      await sleep(300);
      await page.setSelect('select[name="risk-strategy-filter"]', "mitigate");
      await sleep(300);
      await page.setSelect('select[name="risk-exposure-filter"]', "critical");
      await sleep(300);
      await page.setInput('input[name="risk-search-filter"]', "supplier");
      await sleep(500);
      let state = await page.evaluate(registerState);
      assert(state.risks.length === 1 && state.risks[0].id === riskId, `filtered rows ${JSON.stringify(state.risks)}`);
      await page.setSelect('select[name="risk-category-filter"]', "commercial");
      await sleep(500);
      state = await page.evaluate(registerState);
      assert(state.risks.length === 0, `commercial filter rows ${JSON.stringify(state.risks)}`);
      assert(state.empty.some((text) => /No risks are stored/.test(text)), `filtered empty ${JSON.stringify(state.empty)}`);
      await capture(page, "08-filtered-register");
      await page.setSelect('select[name="risk-category-filter"]', "");
      await page.setSelect('select[name="risk-status-filter"]', "");
      await page.setSelect('select[name="risk-strategy-filter"]', "");
      await page.setSelect('select[name="risk-exposure-filter"]', "");
      await page.setInput('input[name="risk-search-filter"]', "");
      await sleep(500);
      return { filtered: 1, empty: 0 };
    });

    await scenario("08", "پس از بارگذاری کامل صفحه، ریسک، امتیاز و نسخه حفظ می‌شوند", async () => {
      await page.navigate(`${baseUrl}/app?project=preview-rps-01&view=visual`, "#cp-activity-grid tbody tr[data-activity-id]", "workspace reload");
      await sleep(1200);
      await openRisks(page);
      const state = await page.evaluate(registerState);
      const row = state.risks.find((item) => item.id === riskId);
      assert(row?.scoreExposure === "20 · Critical" && row?.status === "Closed", `row after reload ${JSON.stringify(row)}`);
      await selectRisk(page, riskId);
      const selected = await page.evaluate(registerState);
      assert(selected.history.length === 3, `history after reload ${JSON.stringify(selected.history)}`);
      await capture(page, "09-persisted-after-reload");
      return { row, history: selected.history.length };
    });

    await scenario("09", "نقش Viewer فقط می‌خواند: بدون کنترل نوشتن و پاسخ مستقیم 403", async () => {
      await loginAs(page, "Viewer");
      await openRisks(page);
      await selectRisk(page, riskId);
      const state = await page.evaluate(registerState);
      assert(state.risks.some((item) => item.id === riskId), `viewer register ${JSON.stringify(state.risks)}`);
      assert(!state.newRisk, "viewer received the new risk button");
      assert(state.risks.every((item) => !item.edit && !item.remove), "viewer received a risk write action");
      const denied = await api(page, "POST", riskUrl(), {
        risk_id: `${riskId}-VIEWER`,
        title: "Viewer must not write",
        description: "",
        category: "schedule",
        status: "open",
        probability: 1,
        impact: 1,
        response_strategy: "accept",
        owner: "preview-viewer",
        date_identified: "2026-11-05",
      });
      assert(denied.status === 403 && denied.body.code === "RISK_PERMISSION_DENIED", `viewer create ${JSON.stringify(denied)}`);
      await capture(page, "10-viewer-denied");
      return { createStatus: denied.status };
    });

    await scenario("10", "فهرست ریسک در 1280×720 فارسی، راست‌به‌چپ و بدون بریدگی رندر می‌شود", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await loginAs(page, "Planner");
      await setLanguage(page, "fa");
      await openRisks(page);
      await selectRisk(page, riskId);
      const layout = await page.evaluate(`(() => {
        const rect = (element) => {
          if (!element) return null;
          const bounds = element.getBoundingClientRect();
          return { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height };
        };
        const page = document.querySelector("[data-risks-page]");
        return {
          innerWidth,
          innerHeight,
          direction: getComputedStyle(document.querySelector(".cp-workspace") || document.body).direction,
          heading: page?.querySelector(":scope > .cp-register-toolbar strong")?.textContent?.trim() ?? null,
          toolbar: rect(page?.querySelector(":scope > .cp-register-toolbar")),
          panel: rect(page),
          table: rect(page?.querySelector(".cp-table-scroll")),
          matrix: rect(page?.querySelector("[data-risk-matrix]")),
          rows: page?.querySelectorAll("[data-risk-row]").length ?? 0,
        };
      })()`);
      assert(layout.direction === "rtl", `workspace direction ${layout.direction}`);
      assert(layout.heading === "ریسک‌های پروژه", `Persian risk heading ${layout.heading}`);
      assert(layout.toolbar && layout.toolbar.width > 0, "the risk toolbar has no layout box at 1280x720");
      assert(layout.table && layout.table.width > 0, "the risk table has no layout box at 1280x720");
      assert(layout.matrix && layout.matrix.width > 0, "the risk matrix has no layout box at 1280x720");
      assert(layout.rows === 1, `rows at 1280x720: ${layout.rows}`);
      assert(layout.toolbar.x >= 0 && layout.toolbar.x + layout.toolbar.width <= layout.innerWidth + 1, `toolbar overflows: ${JSON.stringify(layout.toolbar)}`);
      assert(layout.table.x >= 0 && layout.table.x + layout.table.width <= layout.innerWidth + 1, `table overflows: ${JSON.stringify(layout.table)}`);
      await capture(page, "11-risks-1280x720-fa");
      return layout;
    });

    await scenario("11", "حذف ریسک با نسخهٔ جاری انجام می‌شود و خواندن بعدی ۴۰۴ است", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
      await setLanguage(page, "en");
      await openRisks(page);
      await page.click(`[data-risk-delete="${riskId}"]`);
      await page.waitFor(
        `document.querySelector('[data-risk-notice][data-state="ok"]')?.textContent?.includes("Risk deleted.") ?? false`,
        "risk deleted notice",
      );
      await sleep(600);
      const state = await page.evaluate(registerState);
      assert(state.risks.length === 0, `risks after delete ${JSON.stringify(state.risks)}`);
      const gone = await api(page, "GET", riskUrl(`/${encodeURIComponent(riskId)}`));
      assert(gone.status === 404 && gone.body.code === "RISK_NOT_FOUND", `deleted read ${JSON.stringify(gone)}`);
      await capture(page, "12-deleted-risk");
      return { remaining: state.risks.length, readStatus: gone.status };
    });

    assert(exceptions.length === 0, `uncaught page exceptions: ${JSON.stringify(exceptions.slice(0, 3))}`);
    assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors.slice(0, 3))}`);
    assert(apiFailures.length === 0, `API 5xx responses: ${JSON.stringify(apiFailures.slice(0, 3))}`);
  } finally {
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(outDir, "risks-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(evidenceDir, "risks-v26.json"), JSON.stringify(report, null, 2));
    page.cdp.close();
    chrome.cdp.close();
    await chrome.stop();
  }

  const failed = scenarios.filter((item) => item.status !== "pass");
  log(`\nScenarios: ${scenarios.length - failed.length} passed, ${failed.length} failed`);
  if (failed.length) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  process.stderr.write(`${error && error.stack ? error.stack : error}\n`);
  process.exit(1);
});
