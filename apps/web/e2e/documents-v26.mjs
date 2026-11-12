#!/usr/bin/env node
/**
 * Browser E2E for the Version 26 Documents window.
 *
 * It drives the real local full-stack preview on project preview-rps-01 with
 * headless Chrome through the DevTools protocol. Every value is read from and
 * written to the real DocumentAPI v1.0 HTTP routes and the SQLite preview
 * repository; no page fixture is injected and no API response is mocked.
 *
 * Scenarios cover the documented behaviour: the empty register, creating a
 * draft with an explicit content hash, editing metadata under a revision
 * guard, the rule that a metadata write cannot change status, competing writes
 * returning DOCUMENT_REVISION_CONFLICT, the audited status transition graph,
 * role-gated approval, history, filters, persistence after a full page reload,
 * viewer read-only authorization, and the 1280x720 Persian layout.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 node e2e/documents-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
// The commit under test and the commit that stores this report are different
// facts: the bundle is built from the worktree before the evidence commit exists.
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "documents-v26");
const evidenceDir = join(
  artifactsDir,
  "..",
  "..",
  "..",
  "..",
  "docs",
  "workspace",
  "evidence",
  `documents-v26-${evidenceDate}`,
);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const stamp = Date.now().toString(36).toUpperCase();
const documentA = `E2E-DOC-${stamp}-A`;
const documentB = `E2E-DOC-${stamp}-B`;
const hashA = `sha256:${"a".repeat(64)}`;
const hashB = `sha256:${"b".repeat(64)}`;

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
  // Details are spread first so a returned record field named `status` can
  // never overwrite this scenario's own pass/fail status.
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

const documentsState = `(() => {
  const page = document.querySelector("[data-documents-page]");
  const rows = [...document.querySelectorAll("[data-document-row]")].map((row) => {
    const cells = [...row.querySelectorAll("td")].map((cell) => (cell.textContent || "").trim());
    return {
      id: row.dataset.documentId,
      title: cells[1],
      type: cells[2],
      status: cells[3],
      links: cells[4],
      revision: cells[5],
      selected: row.getAttribute("aria-selected") === "true",
    };
  });
  const form = page?.querySelector("[data-document-form]");
  const idInput = form?.querySelector('input[name="document-id"]');
  return {
    activeMenu: document.querySelector(".cp-workspace")?.dataset.activeMenu ?? null,
    heading: page?.querySelector(".cp-register-toolbar strong")?.textContent?.trim() ?? null,
    caption: page?.querySelector(".cp-register-details > header span")?.textContent?.trim() ?? null,
    rows,
    empty: page?.querySelector(".cp-calendar-empty")?.textContent?.trim() ?? null,
    activeTab: page?.querySelector('[data-document-tab][aria-selected="true"]')?.dataset.documentTab ?? null,
    history: [...page?.querySelectorAll("[data-document-event]") ?? []].map((item) => ({
      type: item.dataset.documentEvent,
      text: (item.textContent || "").trim(),
    })),
    detailInputs: [...page?.querySelectorAll(".cp-register-detail-content .cp-expense-fields > label") ?? []].map((label) => ({
      label: (label.childNodes[0]?.textContent ?? "").trim(),
      value: label.querySelector("input")?.value ?? null,
    })),
    transitions: [...page?.querySelectorAll("[data-document-transition]") ?? []].map((button) => ({
      status: button.dataset.documentTransition,
      disabled: Boolean(button.disabled),
      title: button.getAttribute("title") || "",
    })),
    form: form ? {
      kind: idInput?.hasAttribute("readonly") ? "edit" : "create",
      id: idInput?.value ?? null,
      title: form.querySelector('input[name="document-title"]')?.value ?? null,
      type: form.querySelector('select[name="document-type"]')?.value ?? null,
      storage: form.querySelector('input[name="document-storage"]')?.value ?? null,
      hash: form.querySelector('input[name="document-hash"]')?.value ?? null,
      links: form.querySelector('input[name="document-links"]')?.value ?? null,
    } : null,
    notice: page?.querySelector("[data-document-notice]")
      ? {
          kind: page.querySelector("[data-document-notice]").dataset.state,
          text: page.querySelector("[data-document-notice]").textContent.trim(),
        }
      : null,
    newDisabled: Boolean(page?.querySelector('[data-document-action="new"]')?.disabled),
    editDisabled: Boolean(page?.querySelector('[data-document-action="edit"]')?.disabled),
    filterType: page?.querySelector("select[name=document-filter-type]")?.value ?? null,
    filterStatus: page?.querySelector("select[name=document-filter-status]")?.value ?? null,
    filterSearch: page?.querySelector("input[name=document-search]")?.value ?? null,
  };
})()`;

async function capture(page, name) {
  const file = `documents-v26/${name}.png`;
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

async function openDocuments(page) {
  await openMenu(page, "documents", "[data-documents-page] .cp-register-toolbar", "document register");
  await page.waitFor(
    `(() => {
      const page = document.querySelector("[data-documents-page]");
      return Boolean(page) && !page.textContent.includes("Reading project documents");
    })()`,
    "document register settled",
  );
  await sleep(300);
}

function documentUrl(suffix = "") {
  return `/api/projects/${PROJECT}/documents${suffix}`;
}

async function readList(page, query = "") {
  return page.evaluate(`(async () => {
    const response = await fetch(${JSON.stringify(documentUrl())} + ${JSON.stringify(query)});
    return { status: response.status, body: await response.json() };
  })()`, { awaitPromise: true });
}

async function readDocument(page, documentId) {
  return page.evaluate(`(async () => {
    const response = await fetch(${JSON.stringify(documentUrl("/"))} + encodeURIComponent(${JSON.stringify(documentId)}));
    return { status: response.status, body: await response.json() };
  })()`, { awaitPromise: true });
}

async function readHistory(page, documentId) {
  return page.evaluate(`(async () => {
    const response = await fetch(${JSON.stringify(documentUrl("/"))} + encodeURIComponent(${JSON.stringify(documentId)}) + "/history");
    return { status: response.status, body: await response.json() };
  })()`, { awaitPromise: true });
}

async function postDocument(page, payload) {
  return page.evaluate(`(async () => {
    const response = await fetch(${JSON.stringify(documentUrl())}, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Idempotency-Key": "e2e-" + Math.random().toString(36).slice(2) },
      body: JSON.stringify(${JSON.stringify(payload)}),
    });
    return { status: response.status, body: await response.json() };
  })()`, { awaitPromise: true });
}

async function putDocument(page, documentId, payload) {
  return page.evaluate(`(async () => {
    const response = await fetch(${JSON.stringify(documentUrl("/"))} + encodeURIComponent(${JSON.stringify(documentId)}), {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(${JSON.stringify(payload)}),
    });
    return { status: response.status, body: await response.json() };
  })()`, { awaitPromise: true });
}

async function postStatus(page, documentId, payload) {
  return page.evaluate(`(async () => {
    const response = await fetch(${JSON.stringify(documentUrl("/"))} + encodeURIComponent(${JSON.stringify(documentId)}) + "/status", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Idempotency-Key": "e2e-status-" + Math.random().toString(36).slice(2) },
      body: JSON.stringify(${JSON.stringify(payload)}),
    });
    return { status: response.status, body: await response.json() };
  })()`, { awaitPromise: true });
}

function payloadFromRecord(record, overrides = {}) {
  return {
    contract_version: "1.0",
    document_id: record.document_id,
    resource_type: record.resource_type,
    title: record.title,
    status: record.status,
    storage_ref: record.storage_ref,
    content_hash: record.content_hash,
    linked_entity_refs: record.linked_entity_refs,
    expected_revision: record.revision,
    ...overrides,
  };
}

function detailValue(state, label) {
  return state.detailInputs.find((entry) => entry.label === label)?.value ?? null;
}

async function loginAs(page, label) {
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
  const hasPersonas = await page.evaluate('Boolean(document.querySelector(".persona"))');
  if (!hasPersonas) {
    // A previous identity is still signed in; sign out through the real route
    // so the persona cards are the ones this scenario actually selects.
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
    contract: "cubi-documents-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    documentA,
    documentB,
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
    await openDocuments(page);

    await scenario("01", "پنجرهٔ Documents فهرست خالی، پالایه‌ها و جزئیات بدون انتخاب نشان می‌دهد", async () => {
      const state = await page.evaluate(documentsState);
      assert(state.activeMenu === "documents", `active menu is ${state.activeMenu}`);
      assert(state.heading === "Project Documents", `window heading is ${state.heading}`);
      assert(state.rows.length === 0, `register starts with ${state.rows.length} rows`);
      assert(/No project documents are stored for this project/.test(state.empty ?? ""), `empty state is ${state.empty}`);
      assert(state.caption === "No selection", `details caption is ${state.caption}`);
      assert(state.filterType === "" && state.filterStatus === "" && state.filterSearch === "", `filter defaults ${state.filterType}/${state.filterStatus}/${state.filterSearch}`);
      const list = await readList(page);
      assert(list.status === 200, `list status ${list.status}`);
      assert(list.body.contract_version === "1.0", `list contract ${list.body.contract_version}`);
      assert(list.body.documents.length === 0, `server already has ${list.body.documents.length} documents`);
      await capture(page, "01-empty-register");
      return { rows: state.rows.length, empty: state.empty };
    });

    await scenario("02", "ایجاد سند از فرم واقعی به‌صورت پیش‌نویس با نسخهٔ ۱ و هش صریح", async () => {
      await page.click('[data-document-action="new"]');
      await page.waitForSelector("[data-document-form]", "document create form");
      let state = await page.evaluate(documentsState);
      assert(state.form?.kind === "create", `form kind ${state.form?.kind}`);
      assert(state.form?.type === "drawing", `draft type ${state.form?.type}`);
      assert(state.form?.hash === "" && state.form?.storage === "", "the create form prefilled identity fields");

      await page.setInput('[data-document-form] input[name="document-id"]', documentA);
      await page.setInput('[data-document-form] input[name="document-title"]', "E2E foundation layout drawing");
      await page.setSelect('[data-document-form] select[name="document-type"]', "drawing");
      await page.setInput('[data-document-form] input[name="document-storage"]', `s3://cubi-e2e/${documentA}.pdf`);
      await page.setInput('[data-document-form] input[name="document-hash"]', hashA);
      await page.setInput('[data-document-form] input[name="document-links"]', "WBS-1.1, ACT-101");
      await page.click('[data-document-form] button[type="submit"]');

      await page.waitFor(
        `document.querySelector('[data-document-notice][data-state="ok"]')?.textContent?.includes("Document created as a draft") ?? false`,
        "document created notice",
      );
      await page.waitForSelector(`[data-document-row][data-document-id="${documentA}"]`, "created document row");
      await sleep(400);

      state = await page.evaluate(documentsState);
      const row = state.rows.find((item) => item.id === documentA);
      assert(row, `created row missing: ${JSON.stringify(state.rows)}`);
      assert(row.status === "draft" && row.revision === "1" && row.type === "drawing", `row facts ${JSON.stringify(row)}`);
      assert(row.links === "2", `linked reference count ${row.links}`);
      assert(row.selected, "the created document is not selected");
      assert(state.caption === documentA, `details caption ${state.caption}`);
      assert(detailValue(state, "Record revision") === "1", `general revision ${detailValue(state, "Record revision")}`);

      const stored = await readDocument(page, documentA);
      assert(stored.status === 200, `read status ${stored.status}`);
      assert(stored.body.status === "draft", `stored status ${stored.body.status}`);
      assert(stored.body.content_hash === hashA, `stored hash ${stored.body.content_hash}`);
      assert(stored.body.revision === 1, `stored revision ${stored.body.revision}`);

      const transitions = state.transitions.map((item) => item.status);
      assert(transitions.join("|") === "submitted", `declared transitions for a draft: ${transitions.join("|")}`);
      assert(state.transitions[0].disabled === false, "planner cannot submit a draft");

      await capture(page, "02-created");
      return { row, stored: stored.body };
    });

    await scenario("03", "ویرایش فراداده با Revision: عنوان ذخیره می‌شود، نسخه ۲ و تاریخچهٔ created/updated ثبت می‌شود", async () => {
      await page.click('[data-document-action="edit"]');
      await page.waitForSelector("[data-document-form] input[name=document-id][readonly]", "document edit form");
      let state = await page.evaluate(documentsState);
      assert(state.form?.kind === "edit", `form kind ${state.form?.kind}`);
      assert(state.form?.id === documentA, `edit id ${state.form?.id}`);
      assert(state.form?.hash === hashA, `edit hash ${state.form?.hash}`);

      await page.setInput('[data-document-form] input[name="document-title"]', "E2E foundation layout drawing (rev B)");
      await page.click('[data-document-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-document-notice][data-state="ok"]')?.textContent?.includes("Document metadata saved") ?? false`,
        "document saved notice",
      );
      await sleep(500);

      state = await page.evaluate(documentsState);
      const row = state.rows.find((item) => item.id === documentA);
      assert(row?.revision === "2", `edited revision ${row?.revision}`);
      assert(row?.title === "E2E foundation layout drawing (rev B)", `edited title ${row?.title}`);
      assert(detailValue(state, "Record revision") === "2", `general revision ${detailValue(state, "Record revision")}`);

      const history = await readHistory(page, documentA);
      assert(history.status === 200, `history status ${history.status}`);
      assert(history.body.events.length === 2, `history events ${history.body.events.length}`);
      assert(history.body.events[0].event_type === "created", `first event ${history.body.events[0].event_type}`);
      assert(history.body.events[1].event_type === "updated", `second event ${history.body.events[1].event_type}`);

      await page.click('[data-document-tab="history"]');
      await page.waitForSelector('[data-document-event="updated"]', "history updated event");
      state = await page.evaluate(documentsState);
      assert(state.history.length === 2, `rendered history ${state.history.length}`);
      assert(state.history[0].type === "created" && state.history[1].type === "updated", `history order ${JSON.stringify(state.history)}`);
      await capture(page, "03-edited-history");
      return { revision: 2, events: history.body.events.map((entry) => entry.event_type) };
    });

    await scenario("04", "نوشتن فراداده نمی‌تواند وضعیت را تغییر دهد: DOCUMENT_STATUS_REQUIRES_TRANSITION و رکورد پیش‌نویس می‌ماند", async () => {
      const current = await readDocument(page, documentA);
      assert(current.status === 200, `read status ${current.status}`);
      const rejected = await putDocument(page, documentA, payloadFromRecord(current.body, { status: "approved" }));
      assert(rejected.status === 400, `status write accepted with ${rejected.status}`);
      assert(rejected.body.code === "DOCUMENT_STATUS_REQUIRES_TRANSITION", `error code ${rejected.body.code}`);
      const stored = await readDocument(page, documentA);
      assert(stored.body.status === "draft", `stored status after rejected write ${stored.body.status}`);
      assert(stored.body.revision === 2, `stored revision after rejected write ${stored.body.revision}`);
      return { code: rejected.body.code, status: stored.body.status, revision: stored.body.revision };
    });

    await scenario("05", "نوشتن همزمان بیرونی: ارسال فرم کهنه 409 می‌دهد و رکورد معتبر حفظ می‌شود", async () => {
      await page.click('[data-document-tab="general"]');
      await page.waitForSelector("[data-document-tab=general][aria-selected=true]", "general tab");
      await page.click('[data-document-action="edit"]');
      await page.waitForSelector("[data-document-form] input[name=document-id][readonly]", "edit form for conflict");
      await page.setInput('[data-document-form] input[name="document-title"]', "E2E stale form title");

      const current = await readDocument(page, documentA);
      const competing = await putDocument(page, documentA, payloadFromRecord(current.body, { title: "E2E competing metadata edit" }));
      assert(competing.status === 200, `competing update status ${competing.status}`);
      assert(competing.body.revision === 3, `competing revision ${competing.body.revision}`);

      await page.click('[data-document-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-document-notice][data-state="error"]')?.textContent?.includes("DOCUMENT_REVISION_CONFLICT") ?? false`,
        "revision conflict notice",
      );
      await sleep(600);

      const state = await page.evaluate(documentsState);
      const row = state.rows.find((item) => item.id === documentA);
      assert(row?.revision === "3", `authoritative revision after conflict ${row?.revision}`);
      assert(row?.title === "E2E competing metadata edit", `authoritative title after conflict ${row?.title}`);
      assert(!state.form, "stale edit form is still open");
      const stored = await readDocument(page, documentA);
      assert(stored.body.title === "E2E competing metadata edit", `stored title was overwritten: ${stored.body.title}`);
      assert(stored.body.revision === 3, `stored revision ${stored.body.revision}`);
      await capture(page, "05-revision-conflict");
      return { conflict: state.notice?.text, title: row?.title, revision: row?.revision };
    });

    await scenario("06", "گذار وضعیت مجاز با دلیل ثبت می‌شود و تأیید برای Planner غیرفعال است", async () => {
      await page.waitForSelector(`[data-document-row][data-document-id="${documentA}"]`, "document row before transition");
      await page.click(`[data-document-row][data-document-id="${documentA}"]`);
      await page.waitForSelector("[data-document-transition]", "status actions");
      await page.setInput('[data-document-details] input[name="document-transition-reason"]', "Submitted to the consultant");
      await page.click('[data-document-transition="submitted"]');
      await page.waitFor(
        `document.querySelector('[data-document-notice][data-state="ok"]')?.textContent?.includes("Document status is now submitted") ?? false`,
        "submitted notice",
      );
      await sleep(500);

      let state = await page.evaluate(documentsState);
      const row = state.rows.find((item) => item.id === documentA);
      assert(row?.status === "submitted" && row?.revision === "4", `submitted row ${JSON.stringify(row)}`);
      const buttons = new Map(state.transitions.map((item) => [item.status, item]));
      assert(buttons.has("approved") && buttons.has("rejected"), `approval actions missing: ${JSON.stringify(state.transitions)}`);
      assert(buttons.get("approved").disabled, "planner can approve a submitted document");
      assert(/project administrator/.test(buttons.get("approved").title), `approval gate title ${buttons.get("approved").title}`);

      const stored = await readDocument(page, documentA);
      assert(stored.body.status === "submitted", `stored status ${stored.body.status}`);
      const history = await readHistory(page, documentA);
      const changes = history.body.events.filter((entry) => entry.event_type === "status_transition");
      assert(changes.length === 1, `status changes ${changes.length}`);
      assert(changes[0].reason === "Submitted to the consultant", `stored reason ${changes[0].reason}`);
      await capture(page, "06-submitted-planner-gated");
      return { status: stored.body.status, revision: stored.body.revision, approvalDisabled: buttons.get("approved").disabled };
    });

    await scenario("07", "مدیر پروژه سند ارسالی را تأیید می‌کند و تصمیم در تاریخچه ثبت می‌شود", async () => {
      await loginAs(page, "Project administrator");
      await openDocuments(page);
      await sleep(400);
      await page.waitForSelector(`[data-document-row][data-document-id="${documentA}"]`, "document row as administrator");
      await page.click(`[data-document-row][data-document-id="${documentA}"]`);
      await page.waitForSelector('[data-document-transition="approved"]', "approval action");
      let state = await page.evaluate(documentsState);
      const approve = state.transitions.find((item) => item.status === "approved");
      assert(approve && !approve.disabled, `administrator approval is disabled: ${JSON.stringify(state.transitions)}`);
      await page.setInput('[data-document-details] input[name="document-transition-reason"]', "Approved for construction");
      await page.click('[data-document-transition="approved"]');
      await page.waitFor(
        `document.querySelector('[data-document-notice][data-state="ok"]')?.textContent?.includes("Document status is now approved") ?? false`,
        "approved notice",
      );
      await sleep(500);

      const stored = await readDocument(page, documentA);
      assert(stored.body.status === "approved", `stored status ${stored.body.status}`);
      assert(stored.body.revision === 5, `stored revision ${stored.body.revision}`);
      const history = await readHistory(page, documentA);
      const approvals = history.body.events.filter((entry) => entry.event_type === "status_transition");
      assert(approvals.length === 2, `status changes ${approvals.length}`);
      assert(approvals[1].reason === "Approved for construction", `approval reason ${approvals[1].reason}`);
      assert(approvals[1].actor_id === "preview-admin", `approval actor ${approvals[1].actor_id}`);
      await page.click('[data-document-tab="history"]');
      await page.waitForSelector('[data-document-event="status_transition"]', "status history");
      state = await page.evaluate(documentsState);
      assert(state.history.some((item) => item.text.includes("Approved for construction")), "approval reason is not rendered in history");
      await capture(page, "07-approved-admin");
      return { status: stored.body.status, revision: stored.body.revision, actor: approvals[1].actor_id };
    });

    await scenario("08", "گذار نامعتبر در نمودار وضعیت با 400 رد می‌شود و رکورد تغییر نمی‌کند", async () => {
      const current = await readDocument(page, documentA);
      const invalid = await postStatus(page, documentA, { status: "draft", expected_revision: current.body.revision });
      assert(invalid.status === 400, `invalid transition status ${invalid.status}`);
      assert(invalid.body.code === "DOCUMENT_INVALID_STATUS_TRANSITION", `invalid transition code ${invalid.body.code}`);
      const stored = await readDocument(page, documentA);
      assert(stored.body.status === "approved" && stored.body.revision === 5, `stored record after invalid transition ${stored.body.status}/${stored.body.revision}`);
      return { code: invalid.body.code, status: stored.body.status, revision: stored.body.revision };
    });

    await scenario("09", "پالایه‌ها و جستجوی سمت سرور فقط رکورد مطابق را برمی‌گردانند", async () => {
      await page.click('[data-document-action="new"]');
      await page.waitForSelector("[data-document-form]", "second document form");
      await page.setInput('[data-document-form] input[name="document-id"]', documentB);
      await page.setInput('[data-document-form] input[name="document-title"]', "E2E survey evidence pack");
      await page.setSelect('[data-document-form] select[name="document-type"]', "evidence");
      await page.setInput('[data-document-form] input[name="document-storage"]', `s3://cubi-e2e/${documentB}.zip`);
      await page.setInput('[data-document-form] input[name="document-hash"]', hashB);
      await page.click('[data-document-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-document-notice][data-state="ok"]')?.textContent?.includes("Document created as a draft") ?? false`,
        "second document created notice",
      );
      await page.waitForSelector(`[data-document-row][data-document-id="${documentB}"]`, "second document row");
      await sleep(400);

      await page.setSelect('select[name="document-filter-type"]', "evidence");
      await page.click('[data-document-action="apply-filters"]');
      await page.waitFor(`document.querySelectorAll("[data-document-row]").length === 1`, "type filter result");
      let state = await page.evaluate(documentsState);
      assert(state.rows.length === 1 && state.rows[0].id === documentB, `type filter rows ${JSON.stringify(state.rows)}`);

      await page.setSelect('select[name="document-filter-type"]', "");
      await page.setSelect('select[name="document-filter-status"]', "approved");
      await page.click('[data-document-action="apply-filters"]');
      await page.waitFor(`document.querySelectorAll("[data-document-row]").length === 1`, "status filter result");
      state = await page.evaluate(documentsState);
      assert(state.rows.length === 1 && state.rows[0].id === documentA, `status filter rows ${JSON.stringify(state.rows)}`);

      await page.setSelect('select[name="document-filter-status"]', "");
      await page.setInput('input[name="document-search"]', documentB);
      await page.click('[data-document-action="apply-filters"]');
      await page.waitFor(`document.querySelectorAll("[data-document-row]").length === 1`, "search filter result");
      state = await page.evaluate(documentsState);
      assert(state.rows.length === 1 && state.rows[0].id === documentB, `search rows ${JSON.stringify(state.rows)}`);

      await page.setInput('input[name="document-search"]', "no-such-document");
      await page.click('[data-document-action="apply-filters"]');
      await page.waitFor(
        `document.querySelector("[data-documents-page] .cp-calendar-empty")?.textContent?.includes("No document matches the current filters") ?? false`,
        "filtered empty state",
      );
      state = await page.evaluate(documentsState);
      assert(/No document matches the current filters/.test(state.empty ?? ""), `filtered empty ${state.empty}`);

      const serverFiltered = await readList(page, `?status=approved&search=${encodeURIComponent(documentA)}`);
      assert(serverFiltered.status === 200, `filtered list status ${serverFiltered.status}`);
      assert(serverFiltered.body.documents.length === 1 && serverFiltered.body.documents[0].document_id === documentA, `server filter ${JSON.stringify(serverFiltered.body.documents)}`);

      await page.click('[data-document-action="clear-filters"]');
      await page.waitFor(`document.querySelectorAll("[data-document-row]").length === 2`, "clear filters");
      await capture(page, "09-filters");
      return { typeRows: 1, statusRows: 1, searched: documentB, serverFiltered: 1 };
    });

    await scenario("10", "سند تأییدشده جایگزین می‌شود، ویرایش غیرفعال و گذار بیشتری پیشنهاد نمی‌شود", async () => {
      await page.click(`[data-document-row][data-document-id="${documentA}"]`);
      await page.waitForSelector('[data-document-transition="superseded"]', "supersede action");
      await page.setInput('[data-document-details] input[name="document-transition-reason"]', "Replaced by revision C");
      await page.click('[data-document-transition="superseded"]');
      await page.waitFor(
        `document.querySelector('[data-document-notice][data-state="ok"]')?.textContent?.includes("Document status is now superseded") ?? false`,
        "superseded notice",
      );
      await sleep(500);
      const state = await page.evaluate(documentsState);
      const row = state.rows.find((item) => item.id === documentA);
      assert(row?.status === "superseded" && row?.revision === "6", `superseded row ${JSON.stringify(row)}`);
      assert(state.editDisabled, "edit is still enabled for a superseded document");
      assert(state.transitions.length === 0, `superseded still offers transitions: ${JSON.stringify(state.transitions)}`);
      assert(/superseded document is final/.test(state.caption === "No selection" ? "" : await page.text("[data-document-details]")), "the final-state note is missing");
      const stored = await readDocument(page, documentA);
      assert(stored.body.status === "superseded" && stored.body.revision === 6, `stored superseded ${stored.body.status}/${stored.body.revision}`);
      await capture(page, "10-superseded-final");
      return { status: stored.body.status, revision: stored.body.revision, editDisabled: state.editDisabled };
    });

    await scenario("11", "پس از بارگذاری کامل صفحه، رکوردها وضعیت سرور را حفظ می‌کنند", async () => {
      await page.navigate(`${baseUrl}/app?project=preview-rps-01&view=visual`, "#cp-activity-grid tbody tr[data-activity-id]", "workspace reload");
      await sleep(1200);
      await openDocuments(page);
      await sleep(500);
      const state = await page.evaluate(documentsState);
      assert(state.rows.length === 2, `rows after reload ${JSON.stringify(state.rows)}`);
      const approved = state.rows.find((item) => item.id === documentA);
      const draft = state.rows.find((item) => item.id === documentB);
      assert(approved?.status === "superseded" && approved?.revision === "6", `superseded after reload ${JSON.stringify(approved)}`);
      assert(draft?.status === "draft" && draft?.revision === "1", `draft after reload ${JSON.stringify(draft)}`);
      const list = await readList(page);
      assert(list.body.documents.length === 2, `server list after reload ${list.body.documents.length}`);
      const history = await readHistory(page, documentA);
      assert(history.body.events.length === 6, `history after reload ${history.body.events.length}`);
      await capture(page, "11-persisted-after-reload");
      return { rows: state.rows.length, superseded: approved.status, draft: draft.status };
    });

    await scenario("12", "نقش Viewer فقط می‌خواند: دکمهٔ ایجاد غیرفعال و نوشتن مستقیم 403 می‌شود", async () => {
      await loginAs(page, "Viewer");
      await openDocuments(page);
      await sleep(400);
      let state = await page.evaluate(documentsState);
      assert(state.rows.length === 2, `viewer register ${JSON.stringify(state.rows)}`);
      assert(state.newDisabled, "the New Document button is enabled for a viewer");
      await page.click(`[data-document-row][data-document-id="${documentB}"]`);
      await page.waitForSelector("[data-document-details]", "viewer document details");
      state = await page.evaluate(documentsState);
      assert(state.editDisabled, "the edit button is enabled for a viewer");
      assert(state.transitions.length === 1, `viewer transitions ${JSON.stringify(state.transitions)}`);
      assert(state.transitions[0].disabled, "a viewer can submit a draft");
      assert(/planner or administrator/.test(state.transitions[0].title), `viewer transition gate ${state.transitions[0].title}`);

      const denied = await postDocument(page, {
        contract_version: "1.0",
        document_id: `${documentB}-VIEWER`,
        resource_type: "evidence",
        title: "Viewer must not write",
        status: "draft",
        storage_ref: "s3://cubi-e2e/viewer.pdf",
        content_hash: `sha256:${"c".repeat(64)}`,
        linked_entity_refs: [],
      });
      assert(denied.status === 403, `direct viewer create status ${denied.status}`);
      const deniedUpdate = await putDocument(page, documentB, payloadFromRecord((await readDocument(page, documentB)).body, { title: "Viewer edit" }));
      assert(deniedUpdate.status === 403, `direct viewer update status ${deniedUpdate.status}`);
      const list = await readList(page);
      assert(list.body.documents.length === 2, `viewer write leaked ${list.body.documents.length} documents`);
      await capture(page, "12-viewer-denied");
      return { notice: denied.body.code, createStatus: denied.status, updateStatus: deniedUpdate.status };
    });

    await scenario("13", "پنجرهٔ Documents در 1280×720 فارسی، راست‌به‌چپ و بدون بریدگی چیدمان رندر می‌شود", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await setLanguage(page, "fa");
      await sleep(600);
      const layout = await page.evaluate(`(() => {
        const rect = (element) => {
          if (!element) return null;
          const bounds = element.getBoundingClientRect();
          return { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height };
        };
        const page = document.querySelector("[data-documents-page]");
        const bottom = document.querySelector("#cp-details");
        return {
          innerWidth,
          innerHeight,
          direction: getComputedStyle(document.querySelector(".cp-workspace") || document.body).direction,
          toolbar: rect(page?.querySelector(".cp-register-toolbar")),
          filters: rect(page?.querySelector(".cp-issue-filters")),
          register: rect(page?.querySelector(".cp-register-table-wrap")),
          window: rect(page),
          bottomDisplay: bottom ? getComputedStyle(bottom).display : null,
          collapsed: document.querySelector(".cp-main")?.dataset.detailsCollapsed ?? null,
          rowCount: document.querySelectorAll("[data-document-row]").length,
          heading: page?.querySelector(".cp-register-toolbar strong")?.textContent?.trim() ?? null,
        };
      })()`);
      assert(layout.direction === "rtl", `workspace direction ${layout.direction}`);
      assert(layout.heading === "اسناد پروژه", `Persian heading ${layout.heading}`);
      assert(layout.toolbar && layout.toolbar.width > 0, "the toolbar has no layout box at 1280x720");
      assert(layout.filters && layout.filters.width > 0, "the filters have no layout box at 1280x720");
      assert(layout.register && layout.register.height > 0, "the register has no layout box at 1280x720");
      assert(layout.window && layout.window.height > 0, "the Documents window has no layout box at 1280x720");
      assert(layout.rowCount === 2, `register rows at 1280x720: ${layout.rowCount}`);
      assert(layout.toolbar.x >= 0 && layout.toolbar.x + layout.toolbar.width <= layout.innerWidth + 1, `toolbar overflows: ${JSON.stringify(layout.toolbar)}`);
      assert(layout.window.x + layout.window.width <= layout.innerWidth + 1, `Documents window overflows: ${JSON.stringify(layout.window)}`);
      // Documents renders its own details pane; the shared bottom surface must
      // not claim space or duplicate the authored facts.
      assert(layout.collapsed === "true", `bottom details still claim space: ${layout.collapsed}`);
      assert(layout.bottomDisplay === "none", `bottom details are still rendered: ${layout.bottomDisplay}`);
      await capture(page, "13-documents-1280x720-fa");
      return layout;
    });

    assert(exceptions.length === 0, `uncaught page exceptions: ${JSON.stringify(exceptions.slice(0, 3))}`);
    assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors.slice(0, 3))}`);
    assert(apiFailures.length === 0, `API 5xx responses: ${JSON.stringify(apiFailures.slice(0, 3))}`);
  } finally {
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(outDir, "documents-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(evidenceDir, "documents-v26.json"), JSON.stringify(report, null, 2));
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
