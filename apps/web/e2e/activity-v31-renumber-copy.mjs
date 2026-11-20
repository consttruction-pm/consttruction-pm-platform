#!/usr/bin/env node
/**
 * V31: Renumber Activity IDs, Copy Activity Options, column Fill Down and
 * bulk curtain visibility through the real local workspace.
 *
 * Reference: Primavera P6 Professional Help G57535-02 (October 2026):
 * "Renumber Activity IDs dialog box", "Copy Activity Options dialog box",
 * "Copy and paste activities in the Activity Table",
 * "Quickly enter the same text in multiple table rows",
 * "Hide all curtain attachments" and "Display all curtain attachments".
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4300 node e2e/activity-v31-renumber-copy.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4300";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const projectId = "preview-rps-01";
const runId = Date.now().toString(36).toUpperCase();
const outDir = join(artifactsDir, "activity-v31-renumber-copy");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", "activity-workspace-v31");
mkdirSync(outDir, { recursive: true });
mkdirSync(join(evidenceDir, "screenshots"), { recursive: true });

const report = {
  contract: "cubi-activity-v31-renumber-copy.v1",
  url: baseUrl,
  projectId,
  testedCodeSha,
  runId,
  startedAt: new Date().toISOString(),
  steps: [],
  dialogs: [],
  requests: [],
  exceptions: [],
  consoleErrors: [],
  screenshots: [],
  createdActivityIds: [],
  createdRelationshipIds: [],
  createdAttachmentIds: [],
};

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

async function capture(page, name) {
  await page.screenshot(`activity-v31-renumber-copy/${name}.png`);
  copyFileSync(join(outDir, `${name}.png`), join(evidenceDir, "screenshots", `${name}.png`));
  report.screenshots.push(`screenshots/${name}.png`);
}

async function api(page, method, path, body = null) {
  return page.evaluate(`(async () => {
    const init = { method: ${JSON.stringify(method)}, headers: { accept: 'application/json', 'idempotency-key': crypto.randomUUID() } };
    ${body === null ? "" : `init.headers['content-type'] = 'application/json'; init.body = ${JSON.stringify(JSON.stringify(body))};`}
    const response = await fetch(${JSON.stringify(`${baseUrl}/api/projects/${projectId}`)} + ${JSON.stringify(path)}, init);
    return { status: response.status, body: await response.text() };
  })()`, { awaitPromise: true });
}

async function activities(page) {
  const response = await api(page, "GET", "/p6/activities");
  assert(response.status === 200, `activity list failed: ${response.status} ${response.body}`);
  return JSON.parse(response.body).activities ?? [];
}

async function relationships(page) {
  const response = await api(page, "GET", "/p6/relationships");
  assert(response.status === 200, `relationship list failed: ${response.status} ${response.body}`);
  return JSON.parse(response.body).relationships ?? [];
}

async function createActivity(page, activityId, name, duration = 2) {
  const rows = await activities(page);
  const template = rows.find((item) => item.activity?.wbs_id) ?? rows[0];
  const wbsId = template?.activity?.wbs_id ?? "WBS-RPS-CIVIL";
  const response = await api(page, "POST", "/p6/activities", {
    contract_version: "p6-activity-master-api.v1",
    activity_id: activityId,
    name,
    duration_value: duration,
    duration_unit: "working-day",
    wbs_id: wbsId,
    activity_type: "Task Dependent",
    status: "Not Started",
    status_code: "Planned",
    percent_complete_type: "DURATION",
    duration_type: "Fixed Duration & Units",
    leveling_priority: "Normal",
  });
  assert(response.status === 201, `activity create failed: ${response.status} ${response.body}`);
  report.createdActivityIds.push(activityId);
  return JSON.parse(response.body).activity;
}

async function createRelationship(page, relationshipId, predecessor, successor, type = "FS") {
  const response = await api(page, "POST", "/p6/relationships", {
    relationship_id: relationshipId,
    predecessor_id: predecessor,
    successor_id: successor,
    relationship_type: type,
    lag_value: 0,
    lag_unit: "working-day",
  });
  assert(response.status === 200, `relationship create failed: ${response.status} ${response.body}`);
  report.createdRelationshipIds.push(relationshipId);
  return JSON.parse(response.body).relationship;
}

async function reloadWorkspace(page) {
  await page.navigate(`${baseUrl}/app?view=live&project=${projectId}`, "#cp-activity-grid tbody tr[data-activity-id]", "workspace reload");
  await sleep(1400);
}

async function selectActivity(page, activityId) {
  const clicked = await page.evaluate(`(() => {
    const row = document.querySelector('#cp-activity-grid tbody tr[data-activity-id="${activityId}"]');
    if (!row) return false;
    row.click();
    return true;
  })()`);
  assert(clicked, `row ${activityId} is missing from the grid`);
  await page.waitFor(`document.querySelector('#cp-details .cp-detail-selected')?.textContent?.includes('${activityId}')`, `${activityId} details`, 8000);
  await sleep(300);
}

async function runCommand(page, command) {
  const clicked = await page.evaluate(`(() => {
    const buttons = [...document.querySelectorAll('[data-desktop-command="${command}"]')];
    const button = buttons.find((node) => !node.hasAttribute('disabled') && node.getAttribute('aria-disabled') !== 'true');
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `command ${command} is unavailable`);
  await sleep(300);
}

async function login(page) {
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "form", "login");
  await page.evaluate(`(() => { localStorage.setItem("cubi:workspace-locale", "en"); localStorage.removeItem("cubi.activity-copy-options.v1"); return true; })()`);
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "form", "login");
  await page.click('button[name="role"][value="admin"]');
  await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
  await page.click('[data-project-id="preview-rps-01"]');
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
  await sleep(1600);
}

async function main() {
  const chrome = await launchChrome();
  const page = new Page(chrome.cdp);
  await page.initialize();
  page.cdp.on("Page.javascriptDialogOpening", (params) => {
    report.dialogs.push({ type: params.type, message: params.message });
    page.cdp.send("Page.handleJavaScriptDialog", { accept: true }).catch(() => {});
  });
  page.cdp.on("Runtime.exceptionThrown", (params) => {
    report.exceptions.push(params.exceptionDetails?.text ?? "unknown exception");
  });
  page.cdp.on("Runtime.consoleAPICalled", (params) => {
    if (params.type !== "error") return;
    report.consoleErrors.push((params.args ?? []).map((arg) => arg.value ?? arg.description ?? "").join(" "));
  });
  page.cdp.on("Network.requestWillBeSent", (params) => {
    const request = params.request ?? {};
    if (!["DELETE", "POST", "PATCH", "PUT"].includes(request.method ?? "")) return;
    if (!/\/p6\/|cost\/expenses/.test(request.url ?? "")) return;
    report.requests.push({ method: request.method, url: request.url, postData: request.postData ?? null });
  });

  await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 768, deviceScaleFactor: 1, mobile: false });
  await login(page);

  const stamp = String(Date.now()).slice(-6);
  const renumberSource = `V31A${stamp}`;
  const renumberOther = `V31B${stamp}`;
  const renumberNew = `V31A${String(Number(stamp) + 10).padStart(stamp.length, "0")}`;

  // ---- Renumber Activity IDs ------------------------------------------
  await createActivity(page, renumberSource, "V31 renumber source", 4);
  await createActivity(page, renumberOther, "V31 renumber successor", 3);
  const renumberLink = `V31RN${runId}`;
  await createRelationship(page, renumberLink, renumberSource, renumberOther, "FS");
  await reloadWorkspace(page);
  await selectActivity(page, renumberSource);
  await runCommand(page, "edit.renumber");
  await page.waitForSelector("[data-activity-renumber-dialog]", "renumber dialog");
  const previewText = await page.evaluate(`(() => {
    const dialog = document.querySelector('[data-activity-renumber-dialog]');
    const increment = dialog.querySelector('[name="increment"]');
    increment.value = "10";
    increment.dispatchEvent(new Event('input', { bubbles: true }));
    increment.dispatchEvent(new Event('change', { bubbles: true }));
    return {
      row: dialog.querySelector('[data-renumber-next="${renumberSource}"]')?.value ?? "",
      status: dialog.querySelector('[data-renumber-status]')?.textContent ?? "",
    };
  })()`);
  assert(previewText.row === renumberNew, `renumber preview expected ${renumberNew}, got ${previewText.row}`);
  await capture(page, "01-renumber-preview-en-1366");
  const applied = await page.evaluate(`(() => {
    const apply = document.querySelector('[data-activity-renumber-dialog] [data-renumber-apply]');
    if (!apply || apply.disabled) return false;
    apply.click();
    return true;
  })()`);
  assert(applied, "Renumber apply was not available");
  await page.waitFor(`document.querySelector('[data-activity-renumber-dialog]') === null`, "renumber dialog closed", 15000);
  await page.waitFor(`document.querySelector('#cp-activity-grid tbody tr[data-activity-id="${renumberNew}"]') !== null`, "renumbered row", 15000);
  const afterRenumber = await activities(page);
  assert(!afterRenumber.some((item) => item.activity?.activity_id === renumberSource), "the old activity ID still exists");
  const renumberStored = afterRenumber.find((item) => item.activity?.activity_id === renumberNew)?.activity;
  assert(renumberStored?.name === "V31 renumber source", "the activity name was not preserved");
  const relStored = (await relationships(page)).find((item) => item.relationship?.relationship_id === renumberLink)?.relationship;
  assert(relStored?.predecessor_id === renumberNew, `the relationship did not follow the new ID: ${JSON.stringify(relStored)}`);
  assert(relStored?.successor_id === renumberOther, "the relationship successor changed");
  report.createdActivityIds = report.createdActivityIds.map((id) => (id === renumberSource ? renumberNew : id));
  report.steps.push({ feature: "renumber", action: "increment+relationship", status: "pass", from: renumberSource, to: renumberNew });
  await capture(page, "02-renumber-complete-en-1366");

  // ---- Copy Activity Options ------------------------------------------
  const copySource = `V31C${stamp}`;
  const copyOther = `V31D${stamp}`;
  await createActivity(page, copySource, "V31 copy source", 5);
  await createActivity(page, copyOther, "V31 copy successor", 2);
  const copyLink = `V31CP${runId}`;
  await createRelationship(page, copyLink, copySource, copyOther, "SS");
  const codeResponse = await api(page, "POST", `/p6/activities/${copySource}/codes`, {
    code_type: "AREA", code_value: "CIVIL", description: "Civil works",
  });
  assert(codeResponse.status === 201, `code fixture failed: ${codeResponse.status} ${codeResponse.body}`);
  const stepResponse = await api(page, "POST", `/p6/activities/${copySource}/steps`, {
    description: "V31 step", weight: 1, percent_complete: 0, sequence: 1,
  });
  assert(stepResponse.status === 201, `step fixture failed: ${stepResponse.status} ${stepResponse.body}`);
  const expenseResponse = await api(page, "POST", "/cost/expenses", {
    expense_id: `V31EXP${runId}`,
    name: "V31 copy expense",
    category: "equipment",
    currency: "USD",
    activity_id: copySource,
    planned_amount: "125.00",
  });
  assert(expenseResponse.status === 200 || expenseResponse.status === 201, `expense fixture failed: ${expenseResponse.status} ${expenseResponse.body}`);

  await reloadWorkspace(page);
  await selectActivity(page, copySource);
  await runCommand(page, "edit.copy");
  await runCommand(page, "edit.paste");
  await page.waitForSelector("[data-activity-copy-dialog]", "copy options dialog");
  const copyChoices = await page.evaluate(`(() => {
    const dialog = document.querySelector('[data-activity-copy-dialog]');
    const steps = dialog.querySelector('[name="steps"]');
    steps.checked = false;
    steps.dispatchEvent(new Event('change', { bubbles: true }));
    const form = dialog.querySelector('[data-activity-copy-form]');
    form.querySelector('[data-copy-apply]').click();
    return {
      steps: steps.checked,
      relationships: dialog.querySelector('[name="relationships"]')?.checked,
      expenses: dialog.querySelector('[name="expenses"]')?.checked,
    };
  })()`);
  assert(copyChoices.steps === false, "the Steps option did not clear");
  await page.waitFor(`document.querySelector('[data-activity-copy-dialog]') === null`, "copy dialog closed", 15000);
  const copiedId = `${copySource}-C1`;
  await page.waitFor(`document.querySelector('#cp-activity-grid tbody tr[data-activity-id="${copiedId}"]') !== null`, "copied row", 15000);
  const copiedCodes = await api(page, "GET", `/p6/activities/${copiedId}/codes`);
  assert(copiedCodes.status === 200 && copiedCodes.body.includes("CIVIL"), `the activity code was not copied: ${copiedCodes.body}`);
  const copiedSteps = await api(page, "GET", `/p6/activities/${copiedId}/steps`);
  assert(copiedSteps.status === 200 && !copiedSteps.body.includes("V31 step"), `Steps were copied although the option was cleared: ${copiedSteps.body}`);
  const copiedExpenses = await api(page, "GET", `/cost/expenses?activity_id=${encodeURIComponent(copiedId)}`);
  assert(copiedExpenses.status === 200 && copiedExpenses.body.includes("V31 copy expense"), `the expense was not copied: ${copiedExpenses.body}`);
  const copiedLinks = await relationships(page);
  const copiedLink = copiedLinks.find((item) => item.relationship?.predecessor_id === copiedId && item.relationship?.successor_id === copyOther)?.relationship;
  assert(copiedLink, "the copied activity lost its relationship to the uncopied activity");
  report.createdActivityIds.push(copiedId);
  report.steps.push({ feature: "copy-options", action: "codes+expenses+relationship, steps cleared", status: "pass", pasted: copiedId });
  await capture(page, "03-copy-options-en-1366");

  // ---- Fill Down the active Duration column ---------------------------
  const fillSource = `V31E${stamp}`;
  const fillTarget = `V31F${stamp}`;
  await createActivity(page, fillSource, "V31 fill source", 9);
  await createActivity(page, fillTarget, "V31 fill target", 2);
  await reloadWorkspace(page);
  const activeColumn = await page.evaluate(`(() => {
    const cell = document.querySelector('#cp-activity-grid tbody tr[data-activity-id="${fillSource}"] td[data-column-id="activity.planned_duration"]');
    if (!cell) return false;
    cell.click();
    return true;
  })()`);
  assert(activeColumn, "the Original Duration cell is missing");
  await selectActivity(page, fillSource);
  const selected = await page.evaluate(`(() => {
    const target = document.querySelector('#cp-activity-grid tbody tr[data-activity-id="${fillTarget}"]');
    if (!target) return 0;
    target.dispatchEvent(new MouseEvent('click', { bubbles: true, ctrlKey: true }));
    return document.querySelectorAll('#cp-activity-grid tbody tr.is-selected[data-activity-id]').length;
  })()`);
  assert(selected >= 2, `Fill Down multi-selection failed: ${selected}`);
  await runCommand(page, "edit.fill-down");
  await page.waitForSelector("[data-activity-fill-dialog]", "fill down dialog");
  const fillPreview = await page.evaluate(`document.querySelector('[data-fill-value]')?.textContent ?? ""`);
  assert(fillPreview === "9", `Fill Down preview expected 9, got ${fillPreview}`);
  await capture(page, "04-fill-down-preview-en-1366");
  await page.evaluate(`document.querySelector('[data-fill-apply]')?.click()`);
  await page.waitFor(`document.querySelector('[data-activity-fill-dialog]') === null`, "fill down dialog closed", 15000);
  const filledRows = await activities(page);
  const targetDuration = filledRows.find((item) => item.activity?.activity_id === fillTarget)?.activity.duration_value;
  assert(String(targetDuration) === "9", `Fill Down did not persist the Duration value: ${targetDuration}`);
  report.steps.push({ feature: "fill-down", action: "planned-duration-column", status: "pass", value: targetDuration });
  await capture(page, "05-fill-down-complete-en-1366");

  // ---- Hide All / Show All curtains -----------------------------------
  const timeline = await page.evaluate(`(() => {
    const ticks = [...document.querySelectorAll('#cp-gantt [data-gantt-grid]')]
      .map((node) => node.getAttribute('data-gantt-grid'))
      .filter((value) => /^\\d{4}-\\d{2}-\\d{2}$/.test(value ?? ''));
    return { first: ticks[0] ?? null, last: ticks[ticks.length - 1] ?? null };
  })()`);
  assert(timeline.first && timeline.last && timeline.first !== timeline.last, "no usable Gantt timescale");
  await page.evaluate(`document.querySelector('#cp-gantt [data-gantt-attachments-open]')?.click()`);
  await page.waitForSelector("[data-gantt-attachments-dialog][open]", "attachments dialog");
  async function createCurtain(label) {
    const submitted = await page.evaluate(`(() => {
      const form = document.querySelector('[data-gantt-attachment-form]');
      const values = { kind: 'curtain', label: ${JSON.stringify(label)}, startDate: ${JSON.stringify(timeline.first)}, endDate: ${JSON.stringify(timeline.last)}, color: '#b45309', activityId: '', topicId: '', visible: true };
      for (const [name, value] of Object.entries(values)) {
        const field = form.elements.namedItem(name);
        if (!field) return 'MISSING:' + name;
        if (field.type === 'checkbox') field.checked = Boolean(value);
        else { field.value = value; field.dispatchEvent(new Event('input', { bubbles: true })); field.dispatchEvent(new Event('change', { bubbles: true })); }
      }
      form.querySelector('[data-gantt-attachment-save]').click();
      return true;
    })()`);
    assert(submitted === true, `curtain submit failed: ${submitted}`);
    await page.waitFor(`document.querySelector('[data-gantt-attachments-dialog][open]') !== null`, "attachments dialog reopened", 12000);
    await sleep(800);
  }
  await createCurtain(`V31 curtain A ${runId}`);
  await createCurtain(`V31 curtain B ${runId}`);
  const listAttachments = async () => {
    const response = await api(page, "GET", "/p6/gantt/attachments");
    assert(response.status === 200, `attachment list failed: ${response.status}`);
    return JSON.parse(response.body).attachments ?? [];
  };
  let curtains = (await listAttachments()).filter((item) => item.kind === "curtain");
  assert(curtains.length >= 2, `curtain fixtures are missing: ${curtains.length}`);
  report.createdAttachmentIds.push(...curtains.map((item) => item.attachment_id));
  await page.evaluate(`document.querySelector('[data-gantt-curtain-hide-all]')?.click()`);
  for (let attempt = 0; attempt < 30; attempt += 1) {
    await sleep(400);
    curtains = (await listAttachments()).filter((item) => item.kind === "curtain");
    if (curtains.length && curtains.every((item) => item.visible === false)) break;
  }
  assert(curtains.every((item) => item.visible === false), `Hide All did not hide every curtain: ${JSON.stringify(curtains.map((item) => item.visible))}`);
  report.steps.push({ feature: "curtain", action: "hide-all", status: "pass", count: curtains.length });
  await capture(page, "06-curtains-hidden-en-1366");
  await page.evaluate(`document.querySelector('[data-gantt-curtain-show-all]')?.click()`);
  for (let attempt = 0; attempt < 30; attempt += 1) {
    await sleep(400);
    curtains = (await listAttachments()).filter((item) => item.kind === "curtain");
    if (curtains.length && curtains.every((item) => item.visible === true)) break;
  }
  assert(curtains.every((item) => item.visible === true), "Show All did not restore every curtain");
  await reloadWorkspace(page);
  curtains = (await listAttachments()).filter((item) => item.kind === "curtain");
  assert(curtains.every((item) => item.visible === true), "curtain visibility did not survive reload");
  report.steps.push({ feature: "curtain", action: "show-all+reload", status: "pass", count: curtains.length });
  await capture(page, "07-curtains-shown-reload-en-1366");

  // ---- Cleanup ---------------------------------------------------------
  for (const attachment of curtains) {
    const current = (await listAttachments()).find((item) => item.attachment_id === attachment.attachment_id);
    if (!current) continue;
    const removed = await api(page, "DELETE", `/p6/gantt/attachments/${current.attachment_id}`, {
      expected_record_revision: current.record_revision,
    });
    assert(removed.status === 200, `attachment cleanup failed: ${removed.status} ${removed.body}`);
  }
  const cleanupActivities = [renumberNew, renumberOther, copySource, copyOther, copiedId, fillSource, fillTarget];
  const deleteChildRecords = async (activityId) => {
    const codes = JSON.parse((await api(page, "GET", `/p6/activities/${activityId}/codes`)).body).codes ?? [];
    for (const code of codes) {
      await api(page, "DELETE", `/p6/activities/${activityId}/codes/${code.assignment_id}`);
    }
    const steps = JSON.parse((await api(page, "GET", `/p6/activities/${activityId}/steps`)).body).steps ?? [];
    for (const step of steps) {
      await api(page, "DELETE", `/p6/activities/${activityId}/steps/${step.step_id}`);
    }
    const expenses = JSON.parse((await api(page, "GET", `/cost/expenses?activity_id=${encodeURIComponent(activityId)}`)).body).expenses ?? [];
    for (const expense of expenses) {
      await api(page, "DELETE", `/cost/expenses/${expense.expense_id}`, { expected_revision: expense.record_revision ?? expense.revision ?? 1 });
    }
  };
  for (const relationship of await relationships(page)) {
    const item = relationship.relationship;
    if (!item) continue;
    if (!cleanupActivities.includes(item.predecessor_id) && !cleanupActivities.includes(item.successor_id)) continue;
    await api(page, "DELETE", `/p6/relationships/${item.relationship_id}`, { expected_revision: item.record_revision });
    report.createdRelationshipIds = report.createdRelationshipIds.filter((id) => id !== item.relationship_id);
  }
  for (const activityId of cleanupActivities) {
    const rows = await activities(page);
    const activity = rows.find((item) => item.activity?.activity_id === activityId)?.activity;
    if (!activity) continue;
    await deleteChildRecords(activityId);
    const removed = await api(page, "DELETE", `/p6/activities/${activityId}`, { expected_revision: activity.record_revision });
    assert(removed.status === 200, `activity cleanup failed for ${activityId}: ${removed.status} ${removed.body}`);
    report.createdActivityIds = report.createdActivityIds.filter((id) => id !== activityId);
  }
  report.steps.push({ feature: "cleanup", action: "fixtures removed", status: "pass" });

  report.finishedAt = new Date().toISOString();
  report.result = "pass";
  await page.cdp.send("Page.close");
}

let failure = null;
try {
  await main();
} catch (error) {
  failure = error;
  report.result = "fail";
  report.failure = error?.stack ?? String(error);
}

writeFileSync(join(outDir, "activity-v31-renumber-copy.json"), JSON.stringify(report, null, 2));
writeFileSync(join(evidenceDir, "activity-v31-renumber-copy.json"), JSON.stringify(report, null, 2));
console.log(JSON.stringify({ result: report.result, steps: report.steps.length, screenshots: report.screenshots.length, sha: testedCodeSha }, null, 2));
if (failure) console.error(failure.stack ?? String(failure));
process.exit(failure ? 1 : 0);
