#!/usr/bin/env node
/**
 * Browser E2E for the Version 26 Issues window.
 *
 * It drives the real local full-stack preview on project preview-rps-01 with
 * headless Chrome through the DevTools protocol. Every value is read from and
 * written to the real `p6-issue-api.v1` HTTP routes and the SQLite preview
 * repositories; no page fixture is injected and no API response is mocked.
 *
 * Scenarios cover the documented behaviour: create, edit with a revision
 * guard, a competing write producing ISSUE_REVISION_CONFLICT without losing
 * the stored record, the resolution-note rule, the status transition graph,
 * comments, history, filters, deletion, viewer authorization, persistence
 * after a full page reload, and the 1280x720 layout.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 node e2e/issues-v26.mjs
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
const outDir = join(artifactsDir, "issues-v26");
const evidenceDir = join(
  artifactsDir,
  "..",
  "..",
  "..",
  "..",
  "docs",
  "workspace",
  "evidence",
  `issues-v26-${evidenceDate}`,
);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const TENANT = "cubi-preview-tenant";
const stamp = Date.now().toString(36).toUpperCase();
const issueA = `E2E-ISS-${stamp}-A`;
const issueB = `E2E-ISS-${stamp}-B`;

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

const issuesState = `(() => {
  const page = document.querySelector("[data-issues-page]");
  const rows = [...document.querySelectorAll("[data-issue-row]")].map((row) => {
    const cells = [...row.querySelectorAll("td")].map((cell) => (cell.textContent || "").trim());
    return {
      id: row.dataset.issueId,
      title: cells[1],
      type: cells[2],
      status: cells[3],
      priority: cells[4],
      owner: cells[5],
      due: cells[6],
      revision: cells[7],
      selected: row.getAttribute("aria-selected") === "true",
    };
  });
  const activeTab = document.querySelector('[data-issue-tab][aria-selected="true"]')?.dataset.issueTab ?? null;
  const form = document.querySelector("[data-issue-form]");
  const detailInputs = [...document.querySelectorAll("[data-issue-details] .cp-expense-fields > label")].map((label) => ({
    label: (label.childNodes[0]?.textContent ?? "").trim(),
    value: label.querySelector("input")?.value ?? label.querySelector("textarea")?.value ?? null,
  }));
  return {
    activeMenu: document.querySelector(".cp-workspace")?.dataset.activeMenu ?? null,
    heading: page?.querySelector(".cp-register-toolbar strong")?.textContent?.trim() ?? null,
    caption: page?.querySelector(".cp-register-details > header span")?.textContent?.trim() ?? null,
    rows,
    empty: page?.querySelector(".cp-calendar-empty")?.textContent?.trim() ?? null,
    activeTab,
    detailInputs,
    history: [...document.querySelectorAll("[data-issue-event]")].map((item) => ({
      type: item.dataset.issueEvent,
      text: (item.textContent || "").trim(),
    })),
    documents: [...document.querySelectorAll("[data-issue-document]")].map((item) => item.dataset.issueDocument),
    commentFormPresent: Boolean(page?.querySelector(".cp-issue-comment")),
    commentFinal: page?.textContent?.includes("Closed issues are final") ?? false,
    form: form ? {
      kind: form.querySelector('input[name="issue-id"][readonly]') ? "edit" : "create",
      idValue: form.querySelector('input[name="issue-id"]')?.value ?? null,
      title: form.querySelector('input[name="issue-title"]')?.value ?? null,
      status: form.querySelector('select[name="issue-status"]')?.value ?? null,
      priority: form.querySelector('select[name="issue-priority"]')?.value ?? null,
      documents: form.querySelector('input[name="issue-documents"]')?.value ?? null,
      resolution: form.querySelector('input[name="issue-resolution"]')?.value ?? null,
    } : null,
    notice: page?.querySelector("[data-issue-notice]")
      ? {
          kind: page.querySelector("[data-issue-notice]").dataset.state,
          text: page.querySelector("[data-issue-notice]").textContent.trim(),
        }
      : null,
    editDisabled: Boolean(page?.querySelector('[data-issue-action="edit"]')?.disabled),
    createDisabled: Boolean(page?.querySelector('[data-issue-action="new"]')?.disabled),
    filterStatus: page?.querySelector("select[name=issue-filter-status]")?.value ?? null,
    filterPriority: page?.querySelector("select[name=issue-filter-priority]")?.value ?? null,
    filterSearch: page?.querySelector("input[name=issue-search]")?.value ?? null,
  };
})()`;

async function capture(page, name) {
  const file = `issues-v26/${name}.png`;
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

async function openIssues(page) {
  await openMenu(page, "issues", "[data-issues-page] .cp-register-toolbar", "issue register");
  await page.waitFor(
    `(() => {
      const page = document.querySelector("[data-issues-page]");
      return Boolean(page) && !page.textContent.includes("Reading project issues");
    })()`,
    "issue register settled",
  );
  await sleep(300);
}

const requestHeaders = `{
  "Content-Type": "application/json",
  "X-Tenant-Id": ${JSON.stringify(TENANT)},
  "X-Project-Id": ${JSON.stringify(PROJECT)},
  "X-Project-Revision": "7"
}`;

function issueUrl(suffix = "") {
  return `/api/projects/${PROJECT}/p6/issues${suffix}`;
}

async function readIssueList(page, query = "") {
  return page.evaluate(`(async () => {
    const response = await fetch(${JSON.stringify(issueUrl())} + ${JSON.stringify(query)});
    return { status: response.status, body: await response.json() };
  })()`, { awaitPromise: true });
}

async function readIssue(page, issueId) {
  return page.evaluate(`(async () => {
    const response = await fetch(${JSON.stringify(issueUrl("/"))} + encodeURIComponent(${JSON.stringify(issueId)}));
    return { status: response.status, body: await response.json() };
  })()`, { awaitPromise: true });
}

async function readHistory(page, issueId) {
  return page.evaluate(`(async () => {
    const response = await fetch(${JSON.stringify(issueUrl("/"))} + encodeURIComponent(${JSON.stringify(issueId)}) + "/history");
    return { status: response.status, body: await response.json() };
  })()`, { awaitPromise: true });
}

async function postIssue(page, payload) {
  return page.evaluate(`(async () => {
    const response = await fetch(${JSON.stringify(issueUrl())}, {
      method: "POST",
      headers: ${requestHeaders},
      body: JSON.stringify(${JSON.stringify(payload)}),
    });
    return { status: response.status, body: await response.json() };
  })()`, { awaitPromise: true });
}

async function putIssue(page, issueId, payload) {
  return page.evaluate(`(async () => {
    const response = await fetch(${JSON.stringify(issueUrl("/"))} + encodeURIComponent(${JSON.stringify(issueId)}), {
      method: "PUT",
      headers: ${requestHeaders},
      body: JSON.stringify(${JSON.stringify(payload)}),
    });
    return { status: response.status, body: await response.json() };
  })()`, { awaitPromise: true });
}

function payloadFromRecord(record) {
  return {
    contract_version: "p6-issue-api.v1",
    issue_id: record.issue_id,
    title: record.title,
    description: record.description,
    issue_type: record.issue_type,
    status: record.status,
    priority: record.priority,
    owner: record.owner,
    responsible_manager: record.responsible_manager,
    date_identified: record.date_identified,
    due_date: record.due_date,
    wbs_id: record.wbs_id,
    activity_id: record.activity_id,
    document_refs: record.document_refs,
    resolution_note: record.resolution_note,
  };
}

function detailValue(state, label) {
  return state.detailInputs.find((entry) => entry.label === label)?.value ?? null;
}

async function loginAs(page, label) {
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
  const hasPersonas = await page.evaluate('Boolean(document.querySelector(".persona"))');
  if (!hasPersonas) {
    // A previous identity is still signed in; the login route then renders the
    // "signed in" page. Sign out through the real route, then reload the login
    // page so the persona cards are the ones this scenario actually selects.
    const logoutStatus = await page.evaluate(`(async () => {
      const response = await fetch("/preview/logout", { method: "POST", redirect: "manual" });
      return response.status;
    })()`, { awaitPromise: true });
    // `redirect: "manual"` surfaces the 303 as an opaque-redirect status 0.
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
    contract: "cubi-issues-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    issueA,
    issueB,
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
    await openIssues(page);

    await scenario("01", "پنجرهٔ Issues فهرست خالی، پالایه‌های واقعی و جزئیات بدون انتخاب نشان می‌دهد", async () => {
      const state = await page.evaluate(issuesState);
      assert(state.activeMenu === "issues", `active menu is ${state.activeMenu}`);
      assert(state.heading === "Project Issues", `window heading is ${state.heading}`);
      assert(state.rows.length === 0, `register starts with ${state.rows.length} rows`);
      assert(/No project issues are stored for this project/.test(state.empty ?? ""), `empty state is ${state.empty}`);
      assert(state.caption === "No selection", `details caption is ${state.caption}`);
      assert(state.filterStatus === "" && state.filterPriority === "", `filter defaults ${state.filterStatus}/${state.filterPriority}`);
      const list = await readIssueList(page);
      assert(list.status === 200, `list status ${list.status}`);
      assert(list.body.issues.length === 0, `server already has ${list.body.issues.length} issues`);
      await capture(page, "01-empty-register");
      return { rows: state.rows.length, empty: state.empty };
    });

    await scenario("02", "ایجاد مسئله از فرم واقعی، ذخیره در سرور و نمایش با نسخهٔ ۱", async () => {
      await page.click('[data-issue-action="new"]');
      await page.waitForSelector("[data-issue-form]", "issue create form");
      let state = await page.evaluate(issuesState);
      assert(state.form?.kind === "create", `form kind ${state.form?.kind}`);
      assert(state.form?.status === "open" && state.form?.priority === "normal", `draft defaults ${JSON.stringify(state.form)}`);

      await page.setInput('[data-issue-form] input[name="issue-id"]', issueA);
      await page.setInput('[data-issue-form] input[name="issue-title"]', "E2E foundation pour hold");
      await page.setSelect('[data-issue-form] select[name="issue-type"]', "quality");
      await page.setSelect('[data-issue-form] select[name="issue-priority"]', "high");
      await page.setInput('[data-issue-form] input[name="issue-owner"]', "Site Engineer");
      await page.setInput('[data-issue-form] input[name="issue-manager"]', "Project Manager");
      await page.setInput('[data-issue-form] input[name="issue-identified"]', "2026-12-01");
      await page.setInput('[data-issue-form] input[name="issue-due"]', "2026-12-15");
      await page.setInput('[data-issue-form] textarea[name="issue-description"]', "Concrete pour held pending cube results.");
      await page.setInput('[data-issue-form] input[name="issue-documents"]', "DOC-CUBE-01, DOC-ITP-04");
      await page.click('[data-issue-form] button[type="submit"]');

      await page.waitFor(
        `document.querySelector('[data-issue-notice][data-state="ok"]')?.textContent?.includes("Issue created") ?? false`,
        "issue created notice",
      );
      await page.waitForSelector(`[data-issue-row][data-issue-id="${issueA}"]`, "created issue row");
      await sleep(400);

      state = await page.evaluate(issuesState);
      const row = state.rows.find((item) => item.id === issueA);
      assert(row, `created row missing: ${JSON.stringify(state.rows)}`);
      assert(row.revision === "1", `created revision ${row.revision}`);
      assert(row.status === "open" && row.priority === "high" && row.type === "quality", `row facts ${JSON.stringify(row)}`);
      assert(row.due === "2026-12-15", `row due ${row.due}`);
      assert(row.selected, "the created issue is not selected");
      assert(state.caption === issueA, `details caption ${state.caption}`);
      assert(detailValue(state, "Record revision") === "1", `general revision ${detailValue(state, "Record revision")}`);

      const stored = await readIssue(page, issueA);
      assert(stored.status === 200, `read status ${stored.status}`);
      assert(stored.body.issue.title === "E2E foundation pour hold", `stored title ${stored.body.issue.title}`);
      assert(stored.body.issue.document_refs.join("|") === "DOC-CUBE-01|DOC-ITP-04", `stored documents ${stored.body.issue.document_refs}`);
      assert(stored.body.issue.record_revision === 1, `stored revision ${stored.body.issue.record_revision}`);

      await page.click('[data-issue-tab="documents"]');
      await page.waitForSelector('[data-issue-document="DOC-CUBE-01"]', "document references tab");
      state = await page.evaluate(issuesState);
      assert(state.documents.join("|") === "DOC-CUBE-01|DOC-ITP-04", `rendered document references ${state.documents}`);
      await page.click('[data-issue-tab="general"]');
      await page.waitForSelector("[data-issue-tab=general][aria-selected=true]", "general tab after documents");

      await capture(page, "02-created");
      return { row, stored: stored.body.issue };
    });

    await scenario("03", "ویرایش با Revision: عنوان و اولویت ذخیره می‌شود و نسخه به ۲ می‌رسد", async () => {
      await page.click('[data-issue-action="edit"]');
      await page.waitForSelector("[data-issue-form] input[name=issue-id][readonly]", "issue edit form");
      let state = await page.evaluate(issuesState);
      assert(state.form?.kind === "edit", `form kind ${state.form?.kind}`);
      assert(state.form?.idValue === issueA, `edit id ${state.form?.idValue}`);
      assert(state.form?.title === "E2E foundation pour hold", `edit title ${state.form?.title}`);

      await page.setInput('[data-issue-form] input[name="issue-title"]', "E2E foundation pour hold (revised)");
      await page.setSelect('[data-issue-form] select[name="issue-priority"]', "critical");
      await page.click('[data-issue-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-issue-notice][data-state="ok"]')?.textContent?.includes("Issue saved") ?? false`,
        "issue saved notice",
      );
      await sleep(500);

      state = await page.evaluate(issuesState);
      const row = state.rows.find((item) => item.id === issueA);
      assert(row?.revision === "2", `edited revision ${row?.revision}`);
      assert(row?.title === "E2E foundation pour hold (revised)" && row?.priority === "critical", `edited row ${JSON.stringify(row)}`);
      assert(detailValue(state, "Record revision") === "2", `general revision ${detailValue(state, "Record revision")}`);

      const stored = await readIssue(page, issueA);
      assert(stored.body.issue.record_revision === 2, `stored revision ${stored.body.issue.record_revision}`);
      const history = await readHistory(page, issueA);
      assert(history.body.events.length === 2, `history events ${history.body.events.length}`);
      assert(history.body.events[0].event.event_type === "created", "first event is not created");
      assert(history.body.events[1].event.event_type === "updated", "second event is not updated");
      await page.click('[data-issue-tab="history"]');
      await page.waitForSelector('[data-issue-event="updated"]', "history updated event");
      state = await page.evaluate(issuesState);
      assert(state.history.length === 2, `rendered history ${state.history.length}`);
      assert(state.history[0].type === "created" && state.history[1].type === "updated", `history order ${JSON.stringify(state.history)}`);
      await capture(page, "03-edited-history");
      return { revision: 2, history: history.body.events.map((entry) => entry.event.event_type) };
    });

    await scenario("04", "نوشتن همزمان بیرونی: ارسال فرم کهنه 409 می‌دهد و رکورد معتبر حفظ می‌شود", async () => {
      await page.click('[data-issue-tab="general"]');
      await page.waitForSelector("[data-issue-tab=general][aria-selected=true]", "general tab");
      await page.click('[data-issue-action="edit"]');
      await page.waitForSelector("[data-issue-form] input[name=issue-id][readonly]", "edit form for conflict");
      await page.setInput('[data-issue-form] input[name="issue-title"]', "E2E stale form title");

      const current = await readIssue(page, issueA);
      const payload = payloadFromRecord(current.body.issue);
      payload.title = "E2E competing edit";
      payload.priority = "normal";
      const competing = await putIssue(page, issueA, { ...payload, expected_revision: current.body.issue.record_revision });
      assert(competing.status === 200, `competing update status ${competing.status}`);
      assert(competing.body.issue.record_revision === 3, `competing revision ${competing.body.issue.record_revision}`);

      await page.click('[data-issue-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-issue-notice][data-state="error"]')?.textContent?.includes("ISSUE_REVISION_CONFLICT") ?? false`,
        "revision conflict notice",
      );
      await sleep(600);

      const state = await page.evaluate(issuesState);
      const row = state.rows.find((item) => item.id === issueA);
      assert(row?.revision === "3", `authoritative revision after conflict ${row?.revision}`);
      assert(row?.title === "E2E competing edit", `authoritative title after conflict ${row?.title}`);
      assert(state.notice?.kind === "error", `notice kind ${state.notice?.kind}`);
      assert(!state.form, `stale edit form is still open`);

      const stored = await readIssue(page, issueA);
      assert(stored.body.issue.title === "E2E competing edit", `stored title was overwritten: ${stored.body.issue.title}`);
      assert(stored.body.issue.record_revision === 3, `stored revision ${stored.body.issue.record_revision}`);
      await capture(page, "04-revision-conflict");
      return { conflictNotice: state.notice.text, authoritative: { title: row.title, revision: row.revision } };
    });

    await scenario("05", "حل مسئله بدون یادداشت حل رد می‌شود و نسخه تغییر نمی‌کند", async () => {
      await page.click('[data-issue-action="edit"]');
      await page.waitForSelector("[data-issue-form] input[name=issue-id][readonly]", "edit form for resolution rule");
      await page.setSelect('[data-issue-form] select[name="issue-status"]', "resolved");
      await page.click('[data-issue-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-issue-notice][data-state="error"]')?.textContent?.includes("ISSUE_RESOLUTION_NOTE_REQUIRED") ?? false`,
        "resolution note rejection",
      );
      await sleep(400);
      const state = await page.evaluate(issuesState);
      assert(state.form?.kind === "edit", "the rejected form should stay open");
      const stored = await readIssue(page, issueA);
      assert(stored.body.issue.status === "open", `status after rejection ${stored.body.issue.status}`);
      assert(stored.body.issue.record_revision === 3, `revision after rejection ${stored.body.issue.record_revision}`);
      return { notice: state.notice?.text };
    });

    await scenario("06", "حل با یادداشت، سپس بازگشایی: گذار وضعیت مجاز در تاریخچه ثبت می‌شود", async () => {
      await page.setInput('[data-issue-form] input[name="issue-resolution"]', "Cube results accepted; pour released.");
      await page.click('[data-issue-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-issue-notice][data-state="ok"]')?.textContent?.includes("Issue saved") ?? false`,
        "resolved save notice",
      );
      await sleep(500);
      let stored = await readIssue(page, issueA);
      assert(stored.body.issue.status === "resolved", `resolved status ${stored.body.issue.status}`);
      assert(stored.body.issue.record_revision === 4, `resolved revision ${stored.body.issue.record_revision}`);

      await page.click('[data-issue-action="edit"]');
      await page.waitForSelector("[data-issue-form] input[name=issue-id][readonly]", "edit form for reopen");
      await page.setSelect('[data-issue-form] select[name="issue-status"]', "open");
      await page.click('[data-issue-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-issue-notice][data-state="ok"]')?.textContent?.includes("Issue saved") ?? false`,
        "reopen save notice",
      );
      await sleep(500);
      stored = await readIssue(page, issueA);
      assert(stored.body.issue.status === "open", `reopened status ${stored.body.issue.status}`);
      assert(stored.body.issue.record_revision === 5, `reopened revision ${stored.body.issue.record_revision}`);

      const history = await readHistory(page, issueA);
      const statusEvents = history.body.events.filter((entry) => entry.event.event_type === "status_changed");
      assert(statusEvents.length === 2, `status changes ${statusEvents.length}`);
      assert(statusEvents[0].event.detail.to_status === "resolved", `first transition ${JSON.stringify(statusEvents[0].event.detail)}`);
      assert(statusEvents[1].event.detail.from_status === "resolved" && statusEvents[1].event.detail.to_status === "open", `reopen transition ${JSON.stringify(statusEvents[1].event.detail)}`);
      await page.click('[data-issue-tab="history"]');
      await page.waitForSelector('[data-issue-event="status_changed"]', "status history");
      const state = await page.evaluate(issuesState);
      assert(state.history.some((item) => item.text.includes("resolved → open")), `history text ${JSON.stringify(state.history)}`);
      await capture(page, "06-status-history");
      return { transitions: statusEvents.map((entry) => entry.event.detail) };
    });

    await scenario("07", "یادداشت جدید پس از بازگشایی ثبت و با متن پیراسته در تاریخچه نمایش داده می‌شود", async () => {
      await page.setInput('[data-issue-details] input[name="issue-comment"]', "  Inspecting foundation pour  ");
      await page.click('[data-issue-action="comment"]');
      await page.waitFor(
        `document.querySelector('[data-issue-notice][data-state="ok"]')?.textContent?.includes("Comment added") ?? false`,
        "comment notice",
      );
      await sleep(500);
      const stored = await readIssue(page, issueA);
      assert(stored.body.issue.record_revision === 6, `comment revision ${stored.body.issue.record_revision}`);
      assert(stored.body.issue.status === "open", `comment changed status ${stored.body.issue.status}`);
      const history = await readHistory(page, issueA);
      const comments = history.body.events.filter((entry) => entry.event.event_type === "commented");
      assert(comments.length === 1, `comment events ${comments.length}`);
      assert(comments[0].event.detail.comment === "Inspecting foundation pour", `stored comment ${JSON.stringify(comments[0].event.detail.comment)}`);
      const state = await page.evaluate(issuesState);
      assert(state.history.some((item) => item.text.includes("Inspecting foundation pour")), "the comment is not rendered in history");
      assert(state.commentFormPresent, "the comment form disappeared before closing");
      await capture(page, "07-comment");
      return { revision: 6, comment: comments[0].event.detail.comment };
    });

    await scenario("08", "بستن مسئله نهایی است: ویرایش غیرفعال و فرم یادداشت برداشته می‌شود", async () => {
      await page.click('[data-issue-tab="general"]');
      await page.waitForSelector("[data-issue-tab=general][aria-selected=true]", "general tab before close");
      await page.click('[data-issue-action="edit"]');
      await page.waitForSelector("[data-issue-form] input[name=issue-id][readonly]", "edit form before close");
      await page.setSelect('[data-issue-form] select[name="issue-status"]', "closed");
      await page.click('[data-issue-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-issue-notice][data-state="ok"]')?.textContent?.includes("Issue saved") ?? false`,
        "close save notice",
      );
      await sleep(500);
      const stored = await readIssue(page, issueA);
      assert(stored.body.issue.status === "closed", `closed status ${stored.body.issue.status}`);
      assert(stored.body.issue.record_revision === 7, `closed revision ${stored.body.issue.record_revision}`);
      let state = await page.evaluate(issuesState);
      assert(state.editDisabled, "edit is still enabled for a closed issue");
      await page.click('[data-issue-tab="history"]');
      await page.waitForSelector("[data-issue-tab=history][aria-selected=true]", "history tab for closed");
      state = await page.evaluate(issuesState);
      assert(!state.commentFormPresent, "the comment form is still offered for a closed issue");
      assert(state.commentFinal, "the closed-issue final note is missing");
      const history = await readHistory(page, issueA);
      assert(history.body.events.at(-1).event.event_type === "status_changed", `last event ${history.body.events.at(-1).event.event_type}`);
      assert(history.body.events.at(-1).event.detail.to_status === "closed", "the close transition was not recorded");
      await capture(page, "08-closed-final");
      return { revision: 7, finalNote: state.commentFinal };
    });

    await scenario("09", "پالایه‌ها و جستجوی سمت سرور فقط رکورد مطابق را برمی‌گردانند", async () => {
      await page.click('[data-issue-action="new"]');
      await page.waitForSelector("[data-issue-form]", "second issue form");
      await page.setInput('[data-issue-form] input[name="issue-id"]', issueB);
      await page.setInput('[data-issue-form] input[name="issue-title"]', "E2E survey benchmark discrepancy");
      await page.setSelect('[data-issue-form] select[name="issue-type"]', "cost");
      await page.setInput('[data-issue-form] input[name="issue-owner"]', "Cost Engineer");
      await page.setInput('[data-issue-form] input[name="issue-identified"]', "2026-12-02");
      await page.click('[data-issue-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-issue-notice][data-state="ok"]')?.textContent?.includes("Issue created") ?? false`,
        "second issue notice",
      );
      await page.waitForSelector(`[data-issue-row][data-issue-id="${issueB}"]`, "second issue row");
      await sleep(400);

      await page.setSelect('select[name="issue-filter-status"]', "closed");
      await page.click('[data-issue-action="apply-filters"]');
      await page.waitFor(
        `document.querySelectorAll("[data-issue-row]").length === 1`,
        "closed filter result",
      );
      let state = await page.evaluate(issuesState);
      assert(state.rows.length === 1 && state.rows[0].id === issueA, `closed filter rows ${JSON.stringify(state.rows)}`);

      await page.setSelect('select[name="issue-filter-status"]', "");
      await page.setInput('input[name="issue-search"]', issueB);
      await page.click('[data-issue-action="apply-filters"]');
      await page.waitFor(
        `document.querySelectorAll("[data-issue-row]").length === 1`,
        "search filter result",
      );
      state = await page.evaluate(issuesState);
      assert(state.rows.length === 1 && state.rows[0].id === issueB, `search rows ${JSON.stringify(state.rows)}`);

      await page.setSelect('select[name="issue-filter-priority"]', "high");
      await page.setInput('input[name="issue-search"]', "");
      await page.click('[data-issue-action="apply-filters"]');
      await page.waitFor(
        `document.querySelector("[data-issues-page] .cp-calendar-empty")?.textContent?.includes("No issue matches the current filters") ?? false`,
        "filtered empty state",
      );
      state = await page.evaluate(issuesState);
      assert(/No issue matches the current filters/.test(state.empty ?? ""), `filtered empty ${state.empty}`);

      const serverFiltered = await readIssueList(page, "?status=closed&search=" + encodeURIComponent(issueA));
      assert(serverFiltered.status === 200, `filtered list status ${serverFiltered.status}`);
      assert(serverFiltered.body.issues.length === 1 && serverFiltered.body.issues[0].issue.issue_id === issueA, `server filter ${JSON.stringify(serverFiltered.body.issues)}`);

      await page.click('[data-issue-action="clear-filters"]');
      await page.waitFor(
        `document.querySelectorAll("[data-issue-row]").length === 2`,
        "clear filters",
      );
      await capture(page, "09-filters");
      return { closedRows: 1, searched: issueB, serverFiltered: 1 };
    });

    await scenario("10", "حذف با Revision: رکورد و ردیف برداشته می‌شود و مسیر GET آن 404 است", async () => {
      await page.evaluate("window.confirm = () => true; true");
      await page.waitForSelector(`[data-issue-row][data-issue-id="${issueA}"]`, "issue A before delete");
      await page.click(`[data-issue-row][data-issue-id="${issueA}"]`);
      await page.waitForSelector("[data-issue-details]", "issue A details");
      await page.click('[data-issue-action="delete"]');
      await page.waitFor(
        `document.querySelector('[data-issue-notice][data-state="ok"]')?.textContent?.includes("Issue deleted") ?? false`,
        "delete notice",
      );
      await sleep(600);
      const state = await page.evaluate(issuesState);
      assert(!state.rows.some((item) => item.id === issueA), `deleted row is still listed: ${JSON.stringify(state.rows)}`);
      assert(state.rows.length === 1 && state.rows[0].id === issueB, `remaining rows ${JSON.stringify(state.rows)}`);
      const gone = await readIssue(page, issueA);
      assert(gone.status === 404, `deleted read status ${gone.status}`);
      assert(gone.body.code === "P6_ISSUE_NOT_FOUND", `deleted read code ${gone.body.code}`);
      // Deleted records are no longer addressable through the detail/history
      // contract; the repository keeps the immutable trail, which the
      // repository test asserts directly.
      const history = await readHistory(page, issueA);
      assert(history.status === 404, `deleted history status ${history.status}`);
      assert(history.body.code === "P6_ISSUE_NOT_FOUND", `deleted history code ${history.body.code}`);
      await capture(page, "10-deleted");
      return { remaining: state.rows.map((item) => item.id), historyStatus: history.status };
    });

    await scenario("11", "پس از بارگذاری کامل صفحه، مسئلهٔ باقی‌مانده و حذف‌شده همان وضعیت سرور را دارند", async () => {
      await page.navigate(`${baseUrl}/app?project=preview-rps-01&view=visual`, "#cp-activity-grid tbody tr[data-activity-id]", "workspace reload");
      await sleep(1200);
      await openIssues(page);
      await sleep(500);
      const state = await page.evaluate(issuesState);
      assert(state.rows.length === 1, `rows after reload ${JSON.stringify(state.rows)}`);
      assert(state.rows[0].id === issueB, `remaining issue after reload ${state.rows[0].id}`);
      assert(state.rows[0].title === "E2E survey benchmark discrepancy", `title after reload ${state.rows[0].title}`);
      assert(state.rows[0].revision === "1", `revision after reload ${state.rows[0].revision}`);
      const list = await readIssueList(page);
      assert(list.body.issues.length === 1 && list.body.issues[0].issue.issue_id === issueB, `server list after reload ${JSON.stringify(list.body.issues)}`);
      const gone = await readIssue(page, issueA);
      assert(gone.status === 404, `deleted issue returned ${gone.status} after reload`);
      await capture(page, "11-persisted-after-reload");
      return { rows: state.rows.length, surviving: issueB };
    });

    await scenario("12", "نقش Viewer فقط می‌خواند: ایجاد مسئله با 403 رد می‌شود و رکورد جدیدی ذخیره نمی‌شود", async () => {
      await loginAs(page, "Viewer");
      await openIssues(page);
      await sleep(400);
      let state = await page.evaluate(issuesState);
      assert(state.rows.length === 1 && state.rows[0].id === issueB, `viewer register ${JSON.stringify(state.rows)}`);

      await page.click('[data-issue-action="new"]');
      await page.waitForSelector("[data-issue-form]", "viewer create form");
      await page.setInput('[data-issue-form] input[name="issue-id"]', `${issueB}-VIEWER`);
      await page.setInput('[data-issue-form] input[name="issue-title"]', "Viewer must not write");
      await page.setInput('[data-issue-form] input[name="issue-owner"]', "Viewer");
      await page.setInput('[data-issue-form] input[name="issue-identified"]', "2026-12-03");
      await page.click('[data-issue-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-issue-notice][data-state="error"]')?.textContent?.includes("authorization denied") ?? false`,
        "viewer denial notice",
      );
      await sleep(400);
      state = await page.evaluate(issuesState);
      assert(state.notice?.kind === "error", `viewer notice ${JSON.stringify(state.notice)}`);
      const list = await readIssueList(page);
      assert(list.body.issues.length === 1, `viewer write leaked ${list.body.issues.length} issues`);
      const denied = await postIssue(page, {
        contract_version: "p6-issue-api.v1",
        issue_id: `${issueB}-DIRECT`,
        title: "Direct viewer write",
        description: "",
        issue_type: "other",
        status: "open",
        priority: "low",
        owner: "Viewer",
        responsible_manager: null,
        date_identified: "2026-12-03",
        due_date: null,
        wbs_id: null,
        activity_id: null,
        document_refs: [],
        resolution_note: null,
      });
      assert(denied.status === 403, `direct viewer write status ${denied.status}`);
      await capture(page, "12-viewer-denied");
      return { notice: state.notice.text, directStatus: denied.status };
    });

    await scenario("13", "پنجرهٔ Issues در 1280×720 بدون بریدگی چیدمان رندر می‌شود", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await sleep(600);
      const layout = await page.evaluate(`(() => {
        const rect = (element) => {
          if (!element) return null;
          const bounds = element.getBoundingClientRect();
          return { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height };
        };
        const page = document.querySelector("[data-issues-page]");
        const bottom = document.querySelector("#cp-details");
        return {
          innerWidth,
          innerHeight,
          toolbar: rect(page?.querySelector(".cp-register-toolbar")),
          filters: rect(page?.querySelector(".cp-issue-filters")),
          register: rect(page?.querySelector(".cp-register-table-wrap")),
          window: rect(page),
          bottomDisplay: bottom ? getComputedStyle(bottom).display : null,
          collapsed: document.querySelector(".cp-main")?.dataset.detailsCollapsed ?? null,
          rowCount: document.querySelectorAll("[data-issue-row]").length,
        };
      })()`);
      assert(layout.toolbar && layout.toolbar.width > 0, "the toolbar has no layout box at 1280x720");
      assert(layout.filters && layout.filters.width > 0, "the filters have no layout box at 1280x720");
      assert(layout.register && layout.register.height > 0, "the register has no layout box at 1280x720");
      assert(layout.window && layout.window.height > 0, "the Issues window has no layout box at 1280x720");
      assert(layout.rowCount === 1, `register rows at 1280x720: ${layout.rowCount}`);
      assert(layout.toolbar.x >= 0 && layout.toolbar.x + layout.toolbar.width <= layout.innerWidth + 1, `toolbar overflows: ${JSON.stringify(layout.toolbar)}`);
      assert(layout.window.x + layout.window.width <= layout.innerWidth + 1, `Issues window overflows: ${JSON.stringify(layout.window)}`);
      // Issues renders its own details pane; the shared bottom surface must not
      // claim space or duplicate the authored facts.
      assert(layout.collapsed === "true", `bottom details still claim space: ${layout.collapsed}`);
      assert(layout.bottomDisplay === "none", `bottom details are still rendered: ${layout.bottomDisplay}`);
      await capture(page, "13-issues-1280x720");
      return layout;
    });

    assert(exceptions.length === 0, `uncaught page exceptions: ${JSON.stringify(exceptions.slice(0, 3))}`);
    assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors.slice(0, 3))}`);
    assert(apiFailures.length === 0, `API 5xx responses: ${JSON.stringify(apiFailures.slice(0, 3))}`);
  } finally {
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(outDir, "issues-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(evidenceDir, "issues-v26.json"), JSON.stringify(report, null, 2));
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
