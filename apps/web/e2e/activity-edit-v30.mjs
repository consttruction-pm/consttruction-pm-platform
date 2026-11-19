#!/usr/bin/env node
/**
 * V30: Delete Activity and Dissolve Activity through the real workspace.
 *
 * Reference: Primavera P6 Professional Help G57535-02,
 * "Delete an activity" and "Dissolve an activity": delete removes the activity
 * (and never leaves dependencies silently orphaned here); dissolve removes the
 * activity and joins each predecessor to each successor, combining the
 * predecessor's first half with the successor's second half.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4200 node e2e/activity-edit-v30.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, artifactsDir, gitHead, launchChrome } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4200";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const projectId = "preview-rps-01";
const runId = Date.now().toString(36).toUpperCase();
const outDir = join(artifactsDir, "activity-edit-v30");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", "activity-workspace-v30");
mkdirSync(outDir, { recursive: true });
mkdirSync(join(evidenceDir, "screenshots"), { recursive: true });

const report = {
  contract: "cubi-activity-edit-v30.v1",
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
};

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

async function capture(page, name) {
  await page.screenshot(`activity-edit-v30/${name}.png`);
  copyFileSync(join(outDir, `${name}.png`), join(evidenceDir, "screenshots", `${name}.png`));
  report.screenshots.push(`screenshots/${name}.png`);
}

async function api(page, method, path, body = null) {
  return page.evaluate(`(async () => {
    const init = { method: ${JSON.stringify(method)}, headers: { accept: 'application/json' } };
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

async function createActivity(page, activityId) {
  const rows = await activities(page);
  const template = rows.find((item) => item.activity?.wbs_id) ?? rows[0];
  // The Activity Master GET does not embed the WBS link; the preview project's
  // civil band is the canonical target used by the fixture.
  const wbsId = template?.activity?.wbs_id ?? "WBS-RPS-CIVIL";
  const response = await api(page, "POST", "/p6/activities", {
    contract_version: "p6-activity-master-api.v1",
    activity_id: activityId,
    name: `V30 edit ${activityId}`,
    duration_value: 2,
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

async function createRelationship(page, relationshipId, predecessor, successor, type) {
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
  await sleep(400);
}

async function runCommand(page, command) {
  const clicked = await page.evaluate(`(() => {
    const buttons = [...document.querySelectorAll('[data-desktop-command="${command}"]')];
    const button = buttons.find((node) => !node.hasAttribute('disabled') && node.getAttribute('aria-disabled') !== 'true');
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `enabled command ${command} is missing`);
  await sleep(1800);
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
    if (!["DELETE", "POST"].includes(request.method ?? "")) return;
    if (!/\/p6\/(activities|relationships)/.test(request.url ?? "")) return;
    report.requests.push({ method: request.method, url: request.url, postData: request.postData ?? null });
  });

  await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 768, deviceScaleFactor: 1, mobile: false });
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "form", "login");
  await page.evaluate(`(() => { localStorage.setItem("cubi:workspace-locale", "en"); return true; })()`);
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "form", "login");
  await page.click('button[name="role"][value="admin"]');
  await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
  await page.click('[data-project-id="preview-rps-01"]');
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
  await sleep(1600);

  // ---- Delete a newly created leaf activity ---------------------------
  const leafId = `V30DEL${runId}`;
  await createActivity(page, leafId);
  await reloadWorkspace(page);
  await selectActivity(page, leafId);
  await capture(page, "01-delete-selected-en-1366");
  await runCommand(page, "edit.delete");
  await page.waitFor(`document.querySelector('#cp-activity-grid tbody tr[data-activity-id="${leafId}"]') === null`, "deleted row removed", 12000);
  const afterDelete = await activities(page);
  assert(!afterDelete.some((item) => item.activity?.activity_id === leafId), "the deleted activity is still stored");
  assert(report.dialogs.some((dialog) => dialog.type === "confirm"), "Delete did not ask for confirmation");
  report.createdActivityIds = report.createdActivityIds.filter((id) => id !== leafId);
  report.steps.push({ feature: "delete", action: "leaf-activity", status: "pass" });
  await capture(page, "02-delete-complete-en-1366");

  // ---- Delete refuses an activity that still owns logic ---------------
  await selectActivity(page, "A130");
  await runCommand(page, "edit.delete");
  await page.waitFor(`document.querySelector('#cp-activity-grid tbody tr[data-activity-id="A130"]') !== null`, "linked activity kept", 8000);
  assert((await activities(page)).some((item) => item.activity?.activity_id === "A130"), "a linked activity was removed");
  assert(report.dialogs.some((dialog) => dialog.type === "alert" && /ACTIVITY_HAS_RELATIONSHIPS/.test(dialog.message)), "the refusal did not name the relationship guard");
  report.steps.push({ feature: "delete", action: "linked-activity-refused", status: "pass" });

  // ---- Stale revision is rejected -------------------------------------
  const staleId = `V30STALE${runId}`;
  await createActivity(page, staleId);
  const staleRows = await activities(page);
  const staleActivity = staleRows.find((item) => item.activity?.activity_id === staleId).activity;
  const bumped = await api(page, "PATCH", `/p6/activities/${staleId}`, {
    contract_version: "p6-activity-master-api.v1",
    name: "V30 stale revision bump",
    duration_value: 2,
    duration_unit: "working-day",
    wbs_id: staleActivity.wbs_id,
    expected_revision: staleActivity.record_revision,
  });
  assert(bumped.status === 200, `revision bump failed: ${bumped.status} ${bumped.body}`);
  const stale = await api(page, "DELETE", `/p6/activities/${staleId}`, { expected_revision: staleActivity.record_revision });
  assert(stale.status === 409 && stale.body.includes("REVISION_CONFLICT"), `stale delete expected 409, got ${stale.status} ${stale.body}`);
  const current = JSON.parse(bumped.body).activity;
  const cleanupStale = await api(page, "DELETE", `/p6/activities/${staleId}`, { expected_revision: current.record_revision });
  assert(cleanupStale.status === 200, `current revision delete failed: ${cleanupStale.status} ${cleanupStale.body}`);
  report.createdActivityIds = report.createdActivityIds.filter((id) => id !== staleId);
  report.steps.push({ feature: "delete", action: "stale-revision", status: "pass", statusCode: stale.status });

  // ---- Dissolve joins predecessor and successor -----------------------
  const predId = `V30PRE${runId}`;
  const midId = `V30MID${runId}`;
  const succId = `V30SUC${runId}`;
  await createActivity(page, predId);
  await createActivity(page, midId);
  await createActivity(page, succId);
  const relOne = `V30R1${runId}`;
  const relTwo = `V30R2${runId}`;
  await createRelationship(page, relOne, predId, midId, "SF");
  await createRelationship(page, relTwo, midId, succId, "FF");
  await reloadWorkspace(page);
  await selectActivity(page, midId);
  const dissolveEnabled = await page.evaluate(`(() => {
    const button = document.querySelector('[data-desktop-command="edit.dissolve"]');
    return Boolean(button) && !button.hasAttribute('disabled') && button.getAttribute('aria-disabled') !== 'true';
  })()`);
  assert(dissolveEnabled, "Dissolve is not enabled for an activity with a predecessor and successor");
  await capture(page, "03-dissolve-ready-en-1366");
  await runCommand(page, "edit.dissolve");
  await page.waitFor(`document.querySelector('#cp-activity-grid tbody tr[data-activity-id="${midId}"]') === null`, "dissolved row removed", 12000);
  const afterDissolve = await activities(page);
  assert(!afterDissolve.some((item) => item.activity?.activity_id === midId), "the dissolved activity is still stored");
  const stored = (await relationships(page)).map((item) => item.relationship);
  const joined = stored.find((item) => item.predecessor_id === predId && item.successor_id === succId);
  assert(joined, `the joined relationship is missing: ${JSON.stringify(stored)}`);
  assert(joined.relationship_type === "SF", `joined type expected SF, got ${joined.relationship_type}`);
  assert(!stored.some((item) => item.relationship_id === relOne || item.relationship_id === relTwo), "the dissolved activity's relationships were left behind");
  report.createdRelationshipIds = report.createdRelationshipIds.filter((id) => id !== relOne && id !== relTwo).concat(joined.relationship_id);
  report.createdActivityIds = report.createdActivityIds.filter((id) => id !== midId);
  report.steps.push({ feature: "dissolve", action: "join-predecessor-successor", status: "pass", type: joined.relationship_type });
  await capture(page, "04-dissolve-complete-en-1366");

  // ---- Copy, Paste and Cut through the authoritative clipboard ----------
  const clipSource = `V30CLIP${runId}`;
  await createActivity(page, clipSource);
  await reloadWorkspace(page);
  await selectActivity(page, clipSource);
  const pasteBefore = await page.evaluate(`(() => {
    const button = document.querySelector('[data-desktop-command="edit.paste"]');
    return Boolean(button) && !button.hasAttribute('disabled') && button.getAttribute('aria-disabled') !== 'true';
  })()`);
  assert(pasteBefore === false, "Paste must be disabled before anything is copied");
  await runCommand(page, "edit.copy");
  const pasteAfter = await page.evaluate(`(() => {
    const button = document.querySelector('[data-desktop-command="edit.paste"]');
    return Boolean(button) && !button.hasAttribute('disabled') && button.getAttribute('aria-disabled') !== 'true';
  })()`);
  assert(pasteAfter, "Copy did not enable Paste");
  await runCommand(page, "edit.paste");
  const copiedId = `${clipSource}-C1`;
  await page.waitFor(`document.querySelector('#cp-activity-grid tbody tr[data-activity-id="${copiedId}"]') !== null`, "pasted row", 12000);
  const copiedStored = (await activities(page)).find((item) => item.activity?.activity_id === copiedId)?.activity;
  assert(copiedStored, "the pasted activity is not stored by the server");
  assert(copiedStored.status === "Not Started", `the pasted activity must start planned, got ${copiedStored.status}`);
  report.createdActivityIds.push(copiedId);
  report.steps.push({ feature: "clipboard", action: "copy-paste", status: "pass", pasted: copiedId });
  await capture(page, "05-paste-en-1366");

  await selectActivity(page, copiedId);
  await runCommand(page, "edit.cut");
  await runCommand(page, "edit.paste");
  const movedId = `${copiedId}-C1`;
  await page.waitFor(`document.querySelector('#cp-activity-grid tbody tr[data-activity-id="${movedId}"]') !== null`, "cut/paste row", 12000);
  const afterCut = await activities(page);
  assert(!afterCut.some((item) => item.activity?.activity_id === copiedId), "Cut left the source activity behind after Paste");
  assert(afterCut.some((item) => item.activity?.activity_id === movedId), "Cut/Paste did not create the moved activity");
  report.createdActivityIds = report.createdActivityIds.filter((id) => id !== copiedId);
  report.createdActivityIds.push(movedId);
  report.steps.push({ feature: "clipboard", action: "cut-paste", status: "pass", moved: movedId });
  await capture(page, "06-cut-paste-en-1366");

  // ---- Replace in activity names --------------------------------------
  const replaceSource = `V30REP${runId}`;
  const replaceRecord = await createActivity(page, replaceSource);
  await reloadWorkspace(page);
  const token = `Token${runId}`;
  const renamed = await api(page, "PATCH", `/p6/activities/${replaceSource}`, {
    contract_version: "p6-activity-master-api.v1",
    name: `Replace ${token} name`,
    expected_revision: replaceRecord.record_revision,
  });
  assert(renamed.status === 200, `replace fixture rename failed: ${renamed.status} ${renamed.body}`);
  await reloadWorkspace(page);
  const opened = await page.evaluate(`(() => {
    const button = document.querySelector('[data-desktop-command="dialog.replace"]');
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(opened, "the Replace command is missing from the Edit menu");
  await page.waitForSelector("[data-activity-replace-dialog]", "replace dialog");
  const filled = await page.evaluate(`(() => {
    const dialog = document.querySelector('[data-activity-replace-dialog]');
    const form = dialog.querySelector('[data-activity-replace-form]');
    const find = form.querySelector('[name="find"]');
    const replacement = form.querySelector('[name="replace"]');
    find.value = ${JSON.stringify(token)};
    replacement.value = "Swapped";
    find.dispatchEvent(new Event('input', { bubbles: true }));
    replacement.dispatchEvent(new Event('input', { bubbles: true }));
    const preview = dialog.querySelector('[data-activity-replace-status]')?.textContent ?? "";
    form.querySelector('[data-activity-replace-apply]').click();
    return preview;
  })()`);
  assert(filled.includes("1"), `Replace preview did not count the matching row: ${filled}`);
  await page.waitFor(`document.querySelector('[data-activity-replace-dialog]') === null`, "replace dialog closed", 12000);
  const replaced = (await activities(page)).find((item) => item.activity?.activity_id === replaceSource)?.activity;
  assert(replaced?.name === "Replace Swapped name", `Replace did not persist: ${JSON.stringify(replaced)}`);
  const gridHasOld = await page.evaluate(`document.querySelector('#cp-activity-grid')?.textContent?.includes(${JSON.stringify(token)}) ?? false`);
  assert(!gridHasOld, "the grid still shows the replaced token");
  report.createdActivityIds.push(replaceSource);
  report.steps.push({ feature: "replace", action: "activity-name", status: "pass", preview: filled });

  // ---- Fill Down across two selected rows -----------------------------
  const fillSource = `V30FILL${runId}`;
  const fillTarget = `V30FILD${runId}`;
  await createActivity(page, fillSource);
  await createActivity(page, fillTarget);
  await reloadWorkspace(page);
  const multiSelected = await page.evaluate(`(() => {
    const first = document.querySelector('#cp-activity-grid tbody tr[data-activity-id="${fillSource}"]');
    const second = document.querySelector('#cp-activity-grid tbody tr[data-activity-id="${fillTarget}"]');
    if (!first || !second) return 0;
    first.click();
    second.dispatchEvent(new MouseEvent('click', { bubbles: true, ctrlKey: true }));
    return document.querySelectorAll('#cp-activity-grid tbody tr.is-selected[data-activity-id]').length;
  })()`);
  assert(multiSelected >= 2, `multi-selection did not happen: ${multiSelected}`);
  await runCommand(page, "edit.fill-down");
  await sleep(1500);
  const filledRows = await activities(page);
  const firstName = filledRows.find((item) => item.activity?.activity_id === fillSource)?.activity.name;
  const targetName = filledRows.find((item) => item.activity?.activity_id === fillTarget)?.activity.name;
  assert(firstName && targetName === firstName, `Fill Down did not copy the source name: ${firstName} / ${targetName}`);
  report.createdActivityIds.push(fillSource, fillTarget);
  report.steps.push({ feature: "fill-down", action: "two-selected-rows", status: "pass", name: firstName });

  // ---- Spell Check dialog saves a corrected name ----------------------
  const spellSource = `V30SPL${runId}`;
  const spellRecord = await createActivity(page, spellSource);
  const misspelled = `Mispellled wrod ${runId}`;
  const spellPatch = await api(page, "PATCH", `/p6/activities/${spellSource}`, {
    contract_version: "p6-activity-master-api.v1",
    name: misspelled,
    expected_revision: spellRecord.record_revision,
  });
  assert(spellPatch.status === 200, `spell fixture rename failed: ${spellPatch.status} ${spellPatch.body}`);
  await reloadWorkspace(page);
  const spellOpened = await page.evaluate(`(() => {
    const button = document.querySelector('[data-desktop-command="dialog.spell-check"]');
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(spellOpened, "the Spell Check command is missing from the Edit menu");
  await page.waitForSelector("[data-activity-spell-dialog]", "spell dialog");
  const corrected = `Misspelled word ${runId}`;
  const savedSpell = await page.evaluate(`(() => {
    const dialog = document.querySelector('[data-activity-spell-dialog]');
    const field = dialog.querySelector('[data-spell-id="${spellSource}"]');
    if (!field) return false;
    const spellcheck = field.getAttribute('spellcheck');
    field.value = ${JSON.stringify(corrected)};
    field.dispatchEvent(new Event('input', { bubbles: true }));
    dialog.querySelector('[data-spell-save]').click();
    return spellcheck;
  })()`);
  assert(savedSpell === "true", "the Spell Check field does not expose browser spellcheck");
  await page.waitFor(`document.querySelector('[data-activity-spell-dialog]') === null`, "spell dialog closed", 12000);
  const spellRows = await activities(page);
  const spellName = spellRows.find((item) => item.activity?.activity_id === spellSource)?.activity.name;
  assert(spellName === corrected, `Spell Check did not save the corrected name: ${spellName}`);
  report.createdActivityIds.push(spellSource);
  report.steps.push({ feature: "spell-check", action: "save-correction", status: "pass", name: corrected });

  // ---- Cleanup through the same contracts -----------------------------
  await api(page, "DELETE", `/p6/relationships/${joined.relationship_id}`, { expected_revision: joined.record_revision });
  for (const activityId of [predId, succId, clipSource, movedId, replaceSource, fillSource, fillTarget, spellSource]) {
    const rows = await activities(page);
    const activity = rows.find((item) => item.activity?.activity_id === activityId)?.activity;
    if (!activity) continue;
    const removed = await api(page, "DELETE", `/p6/activities/${activityId}`, { expected_revision: activity.record_revision });
    assert(removed.status === 200, `cleanup delete failed: ${removed.status} ${removed.body}`);
    report.createdActivityIds = report.createdActivityIds.filter((id) => id !== activityId);
  }
  report.steps.push({ feature: "cleanup", action: "delete-fixtures", status: "pass" });

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
  writeFileSync(join(outDir, "activity-edit-v30.json"), `${JSON.stringify(report, null, 2)}\n`);
  writeFileSync(join(evidenceDir, "activity-edit-v30.json"), `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({ result: report.result, steps: report.steps.length, screenshots: report.screenshots.length, sha: report.testedCodeSha }, null, 2));
  if (failure) {
    console.error(report.failure);
    process.exitCode = 1;
  }
  process.exit(process.exitCode ?? 0);
}
