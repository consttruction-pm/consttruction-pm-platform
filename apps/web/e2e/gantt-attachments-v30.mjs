#!/usr/bin/env node
/**
 * V30: Gantt curtain, text and notebook attachments end to end.
 *
 * Reference: Primavera P6 Professional Help G57535-02 (October 2026),
 * "Add a curtain attachment in a Gantt Chart", "Add a text attachment to a
 * Gantt Chart", "Attach notebook items to bars in a Gantt Chart",
 * "Hide all curtain attachments", "Delete a curtain attachment".
 *
 * The evidence proves the record is persisted by the server, drawn inside the
 * real Gantt body from its date range, hides/shows, survives reload, edits with
 * a record revision, rejects a stale revision with 409 and denies writes to a
 * read-only viewer.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4200 node e2e/gantt-attachments-v30.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4200";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const projectId = "preview-rps-01";
const apiBase = `${baseUrl}/api/projects/${projectId}/p6/gantt/attachments`;
const runId = Date.now().toString(36);
const outDir = join(artifactsDir, "gantt-attachments-v30");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", "activity-workspace-v30");
mkdirSync(outDir, { recursive: true });
mkdirSync(join(evidenceDir, "screenshots"), { recursive: true });

const startedAt = new Date().toISOString();
const report = {
  contract: "cubi-gantt-attachments-v30.v1",
  url: baseUrl,
  projectId,
  testedCodeSha,
  runId,
  startedAt,
  steps: [],
  requests: [],
  responses: [],
  exceptions: [],
  consoleErrors: [],
  screenshots: [],
  createdIds: [],
};

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

async function capture(page, name) {
  await page.screenshot(`gantt-attachments-v30/${name}.png`);
  copyFileSync(join(outDir, `${name}.png`), join(evidenceDir, "screenshots", `${name}.png`));
  report.screenshots.push(`screenshots/${name}.png`);
}

async function login(page, role = "admin") {
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "form", "login");
  await page.evaluate(`(() => { localStorage.setItem("cubi:workspace-locale", "en"); return true; })()`);
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "form", "login");
  await page.click(`button[name="role"][value="${role}"]`);
  await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
  await page.click('[data-project-id="preview-rps-01"]');
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
  await sleep(1600);
}

async function api(page, method, suffix = "", body = null) {
  return page.evaluate(`(async () => {
    const init = { method: ${JSON.stringify(method)}, headers: { accept: 'application/json' } };
    ${body === null ? "" : `init.headers['content-type'] = 'application/json'; init.body = ${JSON.stringify(JSON.stringify(body))};`}
    const response = await fetch(${JSON.stringify(apiBase)} + ${JSON.stringify(suffix)}, init);
    return { status: response.status, body: await response.text() };
  })()`, { awaitPromise: true });
}

async function listAttachments(page) {
  const response = await api(page, "GET");
  assert(response.status === 200, `attachment list failed: ${response.status} ${response.body}`);
  const parsed = JSON.parse(response.body);
  return parsed.attachments ?? [];
}

async function openDialog(page) {
  const opened = await page.evaluate(`(() => {
    if (document.querySelector('[data-gantt-attachments-dialog][open]')) return true;
    const button = document.querySelector('#cp-gantt [data-gantt-attachments-open]');
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(opened, "the Gantt attachments button is missing");
  await page.waitForSelector("[data-gantt-attachments-dialog][open]", "attachments dialog", 8000);
  await sleep(200);
}

async function submitAttachment(page, values) {
  const submitted = await page.evaluate(`(() => {
    const form = document.querySelector('[data-gantt-attachment-form]');
    if (!form) return false;
    const values = ${JSON.stringify(values)};
    for (const [name, value] of Object.entries(values)) {
      const field = form.elements.namedItem(name);
      if (!field) return 'MISSING_FIELD:' + name;
      if (field.type === 'checkbox') field.checked = Boolean(value);
      else {
        field.value = value;
        field.dispatchEvent(new Event('input', { bubbles: true }));
        field.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }
    form.querySelector('[data-gantt-attachment-save]').click();
    return true;
  })()`);
  assert(submitted === true, `attachment form submit failed: ${submitted}`);
  await page.waitFor(`document.querySelector('[data-gantt-attachments-dialog][open]') !== null`, "dialog reopened after save", 12000);
  await sleep(900);
}

async function reloadWorkspace(page) {
  await page.navigate(`${baseUrl}/app?view=live&project=${projectId}`, "#cp-activity-grid tbody tr[data-activity-id]", "workspace reload");
  await page.waitForSelector("#cp-gantt [data-gantt-attachments-open]", "gantt attachments button");
  await sleep(1400);
}

function attachmentRow(page, id, action) {
  return page.evaluate(`(() => {
    const row = document.querySelector('[data-gantt-attachment-row="${id}"]');
    if (!row) return false;
    const button = row.querySelector('[${action}="${id}"]');
    if (!button) return false;
    button.click();
    return true;
  })()`);
}

async function main() {
  const chrome = await launchChrome();
  const page = new Page(chrome.cdp);
  await page.initialize();
  page.cdp.on("Runtime.exceptionThrown", (params) => {
    report.exceptions.push(params.exceptionDetails?.text ?? "unknown exception");
  });
  page.cdp.on("Runtime.consoleAPICalled", (params) => {
    if (params.type !== "error") return;
    report.consoleErrors.push((params.args ?? []).map((arg) => arg.value ?? arg.description ?? "").join(" "));
  });
  page.cdp.on("Network.requestWillBeSent", (params) => {
    const request = params.request ?? {};
    if (!/\/(api\/projects\/.+\/p6\/gantt\/attachments)/.test(request.url ?? "")) return;
    report.requests.push({ method: request.method, url: request.url, postData: request.postData ?? null });
  });
  page.cdp.on("Network.responseReceived", (params) => {
    const url = params.response?.url ?? "";
    if (!url.includes("/p6/gantt/attachments")) return;
    report.responses.push({ url, status: params.response.status });
  });

  await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 768, deviceScaleFactor: 1, mobile: false });
  await login(page);

  // Date range taken from the rendered timescale, so the curtain is provably
  // inside the same timeline the bars use.
  const dates = await page.evaluate(`(() => {
    const ticks = [...document.querySelectorAll('#cp-gantt [data-gantt-grid]')]
      .map((node) => node.getAttribute('data-gantt-grid'))
      .filter((value) => /^\\d{4}-\\d{2}-\\d{2}$/.test(value ?? ''));
    return { first: ticks[0] ?? null, last: ticks[ticks.length - 1] ?? null, count: ticks.length };
  })()`);
  assert(dates.first && dates.last && dates.first !== dates.last, `no usable Gantt timescale: ${JSON.stringify(dates)}`);
  report.timeline = dates;

  await openDialog(page);
  assert(await page.evaluate(`document.querySelectorAll('[data-gantt-attachment-row]').length`) === 0, "the fresh database already stores attachments");
  await capture(page, "01-dialog-empty-en-1366");

  // ---- Curtain ---------------------------------------------------------
  const curtainLabel = `V30 curtain ${runId}`;
  await submitAttachment(page, {
    kind: "curtain",
    label: curtainLabel,
    startDate: dates.first,
    endDate: dates.last,
    color: "#b45309",
    activityId: "",
    topicId: "",
    visible: true,
  });
  let records = await listAttachments(page);
  const curtain = records.find((item) => item.label === curtainLabel);
  assert(curtain && curtain.kind === "curtain", "the curtain was not stored by the server");
  report.createdIds.push(curtain.attachment_id);
  assert(curtain.start_date === dates.first && curtain.end_date === dates.last, "the stored range differs from the submitted range");
  report.steps.push({ feature: "curtain", action: "create", status: "pass", id: curtain.attachment_id });

  let drawn = await page.evaluate(`(() => {
    const node = document.querySelector('#cp-gantt [data-gantt-curtain="${curtain.attachment_id}"]');
    if (!node) return null;
    const rect = node.getBoundingClientRect();
    return {
      from: node.getAttribute('data-curtain-from'),
      to: node.getAttribute('data-curtain-to'),
      left: node.style.left,
      width: node.style.width,
      rectWidth: Math.round(rect.width),
      label: node.textContent,
    };
  })()`);
  assert(drawn, "the curtain is not drawn in the Gantt body");
  assert(drawn.from === dates.first && drawn.to === dates.last, "the drawn curtain carries the wrong range");
  assert(drawn.rectWidth > 8, `the curtain has no visual width: ${JSON.stringify(drawn)}`);
  const counts = await page.evaluate(`(() => {
    const board = document.querySelector('#cp-gantt [data-gantt-curtains]');
    return Number(board?.getAttribute('data-gantt-curtains') ?? -1);
  })()`);
  assert(counts >= 1, "the Gantt board does not report its curtain count");
  report.steps.push({ feature: "curtain", action: "draw", status: "pass", drawn, count: counts });
  await capture(page, "02-curtain-drawn-en-1366");

  // ---- Text attachment on A130 ----------------------------------------
  const textLabel = `V30 text ${runId}`;
  await submitAttachment(page, {
    kind: "text",
    label: textLabel,
    startDate: "",
    endDate: "",
    color: "#0f766e",
    activityId: "A130",
    topicId: "",
    visible: true,
  });
  records = await listAttachments(page);
  const textRecord = records.find((item) => item.label === textLabel);
  assert(textRecord && textRecord.kind === "text" && textRecord.activity_id === "A130", "the text attachment was not stored against A130");
  report.createdIds.push(textRecord.attachment_id);
  const textMark = await page.evaluate(`(() => {
    const node = document.querySelector('#cp-gantt [data-gantt-bar-attachment="${textRecord.attachment_id}"]');
    if (!node) return null;
    return {
      kind: node.getAttribute('data-gantt-attachment-kind'),
      activity: node.getAttribute('data-gantt-attachment-activity'),
      text: node.textContent,
      top: node.style.top,
      left: node.style.left,
    };
  })()`);
  assert(textMark && textMark.kind === "text" && textMark.activity === "A130", "the text attachment is not drawn on the A130 bar");
  report.steps.push({ feature: "text", action: "create+draw", status: "pass", id: textRecord.attachment_id, mark: textMark });

  // ---- Notebook attachment on the same bar ----------------------------
  const notebookLabel = `V30 notebook ${runId}`;
  await submitAttachment(page, {
    kind: "notebook",
    label: notebookLabel,
    startDate: "",
    endDate: "",
    color: "#7c3aed",
    activityId: "A130",
    topicId: "V30-TOPIC-1",
    visible: true,
  });
  records = await listAttachments(page);
  const notebook = records.find((item) => item.label === notebookLabel);
  assert(notebook && notebook.kind === "notebook" && notebook.topic_id === "V30-TOPIC-1", "the notebook attachment did not keep its topic link");
  report.createdIds.push(notebook.attachment_id);
  const notebookMark = await page.evaluate(`(() => {
    const node = document.querySelector('#cp-gantt [data-gantt-bar-attachment="${notebook.attachment_id}"]');
    if (!node) return null;
    return { kind: node.getAttribute('data-gantt-attachment-kind'), activity: node.getAttribute('data-gantt-attachment-activity'), text: node.textContent };
  })()`);
  assert(notebookMark && notebookMark.kind === "notebook", "the notebook attachment is not drawn on the bar");
  const notebookCount = await page.evaluate(`Number(document.querySelector('#cp-gantt [data-gantt-notebook-attachments]')?.getAttribute('data-gantt-notebook-attachments') ?? -1)`);
  assert(notebookCount >= 1, "the Gantt board does not report its notebook attachment count");
  report.steps.push({ feature: "notebook", action: "create+draw", status: "pass", id: notebook.attachment_id, mark: notebookMark });
  await capture(page, "03-all-attachments-en-1366");

  // ---- Hide the curtain ------------------------------------------------
  assert(await attachmentRow(page, curtain.attachment_id, "data-gantt-attachment-toggle"), "the curtain toggle is missing");
  await page.waitFor(`document.querySelector('#cp-gantt [data-gantt-curtain="${curtain.attachment_id}"]') === null`, "curtain hidden in the chart");
  records = await listAttachments(page);
  assert(records.find((item) => item.attachment_id === curtain.attachment_id)?.visible === false, "hiding did not persist");
  report.steps.push({ feature: "curtain", action: "hide", status: "pass" });
  await capture(page, "04-curtain-hidden-en-1366");

  // ---- Reload persistence ---------------------------------------------
  await reloadWorkspace(page);
  const afterReload = await page.evaluate(`(() => ({
    curtain: document.querySelector('#cp-gantt [data-gantt-curtain="${curtain.attachment_id}"]') !== null,
    text: document.querySelector('#cp-gantt [data-gantt-bar-attachment="${textRecord.attachment_id}"]') !== null,
    notebook: document.querySelector('#cp-gantt [data-gantt-bar-attachment="${notebook.attachment_id}"]') !== null,
    count: document.querySelector('#cp-gantt [data-gantt-attachments-count]')?.textContent ?? null,
  }))()`);
  assert(afterReload.curtain === false, "the hidden curtain came back after reload");
  assert(afterReload.text === true && afterReload.notebook === true, `bar attachments were lost on reload: ${JSON.stringify(afterReload)}`);
  report.steps.push({ feature: "attachments", action: "reload", status: "pass", state: afterReload });
  await capture(page, "05-reload-en-1366");

  // ---- Show it again ---------------------------------------------------
  await openDialog(page);
  assert(await attachmentRow(page, curtain.attachment_id, "data-gantt-attachment-toggle"), "the curtain show toggle is missing");
  await page.waitFor(`document.querySelector('#cp-gantt [data-gantt-curtain="${curtain.attachment_id}"]') !== null`, "curtain shown again");
  report.steps.push({ feature: "curtain", action: "show", status: "pass" });

  // ---- Edit the text attachment ---------------------------------------
  await openDialog(page);
  assert(await attachmentRow(page, textRecord.attachment_id, "data-gantt-attachment-edit"), "the text edit button is missing");
  const editedLabel = `V30 text edited ${runId}`;
  await submitAttachment(page, { label: editedLabel, visible: true });
  records = await listAttachments(page);
  const edited = records.find((item) => item.attachment_id === textRecord.attachment_id);
  assert(edited?.label === editedLabel, "the edited label was not stored");
  assert(edited.record_revision > textRecord.record_revision, "the edit did not advance the record revision");
  const editedMark = await page.evaluate(`document.querySelector('#cp-gantt [data-gantt-bar-attachment="${textRecord.attachment_id}"]')?.textContent ?? ""`);
  assert(editedMark.includes(editedLabel), "the chart still shows the old label");
  report.steps.push({ feature: "text", action: "edit", status: "pass", revision: edited.record_revision, mark: editedMark });
  await capture(page, "06-edited-en-1366");

  // ---- Stale revision is rejected with 409 -----------------------------
  const stale = await api(page, "PATCH", `/${textRecord.attachment_id}`, {
    kind: "text",
    label: "stale write",
    activity_id: "A130",
    visible: true,
    expected_record_revision: textRecord.record_revision,
  });
  assert(stale.status === 409, `a stale revision expected 409, got ${stale.status} ${stale.body}`);
  assert(stale.body.includes("REVISION_CONFLICT"), `the 409 body is not the stable conflict code: ${stale.body}`);
  report.steps.push({ feature: "revision", action: "stale-write", status: "pass", statusCode: stale.status });

  // ---- Delete every created attachment --------------------------------
  await openDialog(page);
  for (const id of report.createdIds) {
    assert(await attachmentRow(page, id, "data-gantt-attachment-delete"), `the delete control for ${id} is missing`);
    await sleep(1200);
  }
  await page.waitFor(`document.querySelectorAll('[data-gantt-attachment-row]').length === 0`, "attachment rows removed", 12000);
  const remaining = await listAttachments(page);
  assert(!remaining.some((item) => report.createdIds.includes(item.attachment_id)), "a deleted attachment is still stored");
  report.steps.push({ feature: "attachments", action: "delete", status: "pass", remaining: remaining.length });
  await capture(page, "07-deleted-en-1366");

  // ---- Read-only viewer: read allowed, write denied --------------------
  const viewerChrome = await launchChrome();
  const viewer = new Page(viewerChrome.cdp);
  await viewer.initialize();
  try {
    await login(viewer, "viewer");
    const read = await api(viewer, "GET");
    assert(read.status === 200, `viewer read failed: ${read.status} ${read.body}`);
    const denied = await api(viewer, "POST", "", {
      kind: "text",
      label: `viewer attempt ${runId}`,
      activity_id: "A130",
      visible: true,
    });
    assert(denied.status === 403, `viewer write expected 403, got ${denied.status} ${denied.body}`);
    report.steps.push({ feature: "authorization", action: "viewer-read-write", status: "pass", read: read.status, write: denied.status });
    await capture(viewer, "08-viewer-denied-en-1366");
  } finally {
    viewerChrome.stop?.();
  }

  report.finishedAt = new Date().toISOString();
  report.result = "pass";
}

let failure = null;
try {
  await main();
} catch (error) {
  failure = error;
  report.result = "fail";
  report.failure = error?.stack ?? String(error);
} finally {
  writeFileSync(join(outDir, "gantt-attachments-v30.json"), `${JSON.stringify(report, null, 2)}\n`);
  writeFileSync(join(evidenceDir, "gantt-attachments-v30.json"), `${JSON.stringify(report, null, 2)}\n`);
  const passed = (report.steps ?? []).length;
  console.log(JSON.stringify({ result: report.result, steps: passed, screenshots: report.screenshots.length, sha: report.testedCodeSha }, null, 2));
  if (failure) {
    console.error(report.failure);
    process.exitCode = 1;
  }
  // The open CDP websockets keep Node alive after the report is written.
  process.exit(process.exitCode ?? 0);
}
