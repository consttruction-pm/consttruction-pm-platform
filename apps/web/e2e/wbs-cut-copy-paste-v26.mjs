#!/usr/bin/env node
/**
 * WBS-003 browser acceptance: WBS Copy, Cut/Paste and Delete guidance.
 *
 * Every assertion runs against the real full-stack preview. The WBS window
 * clipboard copies a subtree through POST /p6/wbs/{id}/copy, a cut pastes by
 * moving the same record through PATCH (so activity assignments stay attached),
 * a paste into a descendant is rejected as a hierarchy cycle, and a delete of a
 * node in use states the V26 precondition instead of the persistence code.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4231 node e2e/wbs-cut-copy-paste-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4231";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-13";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const evidenceDir = join(
  artifactsDir, "..", "..", "..", "..",
  "docs", "workspace", "evidence", `wbs-003-cut-copy-paste-${evidenceDate}`,
);
const outPrefix = "wbs-003-cut-copy-paste";
const outDir = join(artifactsDir, outPrefix);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const WBS_PATH = `/api/projects/${PROJECT}/p6/wbs`;
const ACTIVITY_PATH = `/api/projects/${PROJECT}/p6/activities`;
const CIVIL = "WBS-RPS-CIVIL";
const PM = "WBS-RPS-PM";
const PROC = "WBS-RPS-PROC";
const ENV = "WBS-RPS-ENV";
const SURVEY = "WBS-RPS-CIVIL-SURVEY";

const scenarios = [];
const checks = [];
const screenshots = [];
const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const writes = [];
let copiedRootId = "";

function log(message) {
  process.stdout.write(`${message}\n`);
}

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

function check(id, name, condition, detail = {}) {
  checks.push({ id, name, ok: Boolean(condition), detail });
  if (condition) log(`  PASS ${id} ${name}`);
  else log(`  FAIL ${id} ${name} ${JSON.stringify(detail)}`);
}

async function scenario(id, name, body) {
  log(`\n[${id}] ${name}`);
  const started = Date.now();
  try {
    const details = (await body()) ?? {};
    scenarios.push({ id, name, status: "pass", at: new Date().toISOString(), durationMs: Date.now() - started, details });
    log(`  PASS ${id}`);
  } catch (error) {
    scenarios.push({ id, name, status: "fail", at: new Date().toISOString(), durationMs: Date.now() - started, error: String(error?.message ?? error) });
    throw error;
  }
}

async function capture(page, name) {
  const file = `${outPrefix}/${name}.png`;
  await page.screenshot(file);
  copyFileSync(join(artifactsDir, file), join(evidenceDir, `${name}.png`));
  screenshots.push(`${name}.png`);
  return file;
}

async function api(page, method, path, body) {
  return page.evaluate(
    `(async () => {
      const response = await fetch(${JSON.stringify(path)}, {
        method: ${JSON.stringify(method)},
        headers: { "Content-Type": "application/json", "Idempotency-Key": "e2e-wbs3-" + Math.random().toString(36).slice(2) },
        ${body === undefined ? "" : `body: JSON.stringify(${JSON.stringify(body)}),`}
      });
      return { status: response.status, body: await response.json().catch(() => null) };
    })()`,
    { awaitPromise: true },
  );
}

async function wbsList(page) {
  const response = await api(page, "GET", WBS_PATH);
  assert(response.status === 200, `GET ${WBS_PATH} returned ${response.status}`);
  return response.body.wbs_nodes.map((entry) => entry.wbs);
}

async function nodeState(page, wbsId) {
  const response = await api(page, "GET", `${WBS_PATH}/${wbsId}`);
  assert(response.status === 200, `GET ${WBS_PATH}/${wbsId} returned ${response.status}`);
  return response.body;
}

async function activityAssignments(page) {
  const response = await api(page, "GET", ACTIVITY_PATH);
  assert(response.status === 200, `GET ${ACTIVITY_PATH} returned ${response.status}`);
  const counts = new Map();
  for (const entry of response.body.activities) {
    const wbsId = entry.activity?.wbs_id ?? null;
    counts.set(wbsId, (counts.get(wbsId) ?? 0) + 1);
  }
  return counts;
}

async function waitForNode(page, wbsId, predicate, label) {
  const deadline = Date.now() + 20000;
  let last = null;
  while (Date.now() < deadline) {
    last = await nodeState(page, wbsId);
    if (predicate(last.wbs)) return last;
    await sleep(300);
  }
  throw new Error(`TIMEOUT: ${label} (last=${JSON.stringify(last?.wbs ?? null)})`);
}

async function loginAs(page, label) {
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
  const hasPersonas = await page.evaluate('Boolean(document.querySelector(".persona"))');
  if (!hasPersonas) {
    await page.evaluate(`(async () => { await fetch("/preview/logout", { method: "POST", redirect: "manual" }); })()`, { awaitPromise: true });
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, ".persona", "persona cards after sign out");
  }
  const clicked = await page.evaluate(`(() => {
    const button = [...document.querySelectorAll("form button")].find((item) => (item.textContent || "").trim().startsWith(${JSON.stringify(label)}));
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `${label} login button is missing`);
  await page.waitForSelector(`[data-project-id="${PROJECT}"]`, "project selection");
  await page.click(`[data-project-id="${PROJECT}"]`);
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows", 30000);
  await sleep(800);
}

async function openWbs(page) {
  await page.evaluate(`(() => { document.querySelector("[data-context-menu-portal]")?.remove(); })()`);
  const clicked = await page.evaluate(`(() => {
    const buttons = [...document.querySelectorAll('[data-menu="wbs"]')];
    const button = buttons.find((entry) => entry.getClientRects().length > 0) ?? buttons[0];
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, "WBS navigation button is missing");
  await page.waitForSelector(".cp-wbs-window", "WBS window", 20000);
  await page.waitForSelector(".cp-wbs-window [data-wbs-table]", "WBS table", 20000);
  await sleep(300);
}

async function selectNode(page, wbsId) {
  const clicked = await page.evaluate(`(() => {
    const row = document.querySelector('.cp-wbs-window .cp-wbs-row[data-wbs-id="${wbsId}"] .cp-wbs-node');
    if (!row) return false;
    row.click();
    return true;
  })()`);
  assert(clicked, `WBS row ${wbsId} is missing`);
  await page.waitFor(
    `document.querySelector('.cp-wbs-window [data-wbs-detail-panel="general"]')?.textContent?.includes(${JSON.stringify(wbsId)}) === true`,
    `${wbsId} details`,
    15000,
  );
  await sleep(250);
}

async function clickToolbar(page, attribute) {
  const clicked = await page.evaluate(`(() => {
    const button = document.querySelector('.cp-wbs-window [${attribute}]');
    if (!button || button.disabled) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `WBS toolbar ${attribute} is missing or disabled`);
  await sleep(400);
}

async function clipboardText(page) {
  return page.evaluate(`document.querySelector(".cp-wbs-window [data-wbs-clipboard]")?.textContent?.trim() ?? ""`);
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
  await page.waitFor(`document.documentElement.lang === ${JSON.stringify(locale)}`, `${locale} language`);
  await sleep(700);
}

async function reloadWorkspace(page) {
  await page.navigate(`${baseUrl}/app?view=live`, "#cp-activity-grid tbody tr[data-activity-id]", "activity rows after reload");
  await sleep(700);
  const picker = await page.evaluate(`Boolean(document.querySelector('[data-project-id="${PROJECT}"]'))`);
  if (picker) {
    await page.click(`[data-project-id="${PROJECT}"]`);
    await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows after project open", 30000);
    await sleep(600);
  }
  await openWbs(page);
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
  page.cdp.on("Network.requestWillBeSent", (params) => {
    const url = params.request?.url ?? "";
    if (url.includes("/api/") && params.request.method !== "GET") {
      writes.push({ method: params.request.method, url: url.replace(baseUrl, "") });
    }
  });
  page.cdp.on("Page.javascriptDialogOpening", async () => {
    await page.cdp.send("Page.handleJavaScriptDialog", { accept: true }).catch(() => undefined);
  });

  const summary = {
    contract: "cubi-wbs-003-cut-copy-paste.v1",
    testedCodeSha,
    gitHead: gitHead(),
    evidenceCommitSha,
    baseUrl,
    startedAt: new Date().toISOString(),
    scenarios,
    checks,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
    writes,
  };

  try {
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
    await loginAs(page, "Project administrator");
    await setLanguage(page, "en");

    // Authoritative setup before the copy: the source subtree needs a child and
    // weighted milestones so the copy can prove both are duplicated.
    const childStatus = await api(page, "POST", WBS_PATH, {
      contract_version: "p6-wbs-master-api.v1",
      wbs_id: SURVEY,
      parent_kind: "wbs",
      parent_wbs_id: CIVIL,
      code: "2.1",
      name: "Site survey",
      sequence_number: 0,
    });
    assert(childStatus.status === 201, `child WBS create returned ${childStatus.status}`);
    const techniqueStatus = await api(page, "PATCH", `${WBS_PATH}/${CIVIL}`, {
      expected_revision: 1,
      percent_complete_technique: "milestones",
    });
    assert(techniqueStatus.status === 200, `CIVIL technique update returned ${techniqueStatus.status}`);
    const milestoneStatus = await api(page, "PUT", `${WBS_PATH}/${CIVIL}/milestones`, {
      expected_revision: techniqueStatus.body.wbs.record_revision,
      milestones: [
        { milestone_id: "M-1", name: "Design freeze", weight: 9, completed: true, sequence_number: 0 },
        { milestone_id: "M-2", name: "Site handover", weight: 3, completed: false, sequence_number: 1 },
      ],
    });
    assert(milestoneStatus.status === 200, `CIVIL milestones returned ${milestoneStatus.status}`);
    const civilBefore = await nodeState(page, CIVIL);
    await reloadWorkspace(page);

    await scenario("01", "Copy a WBS subtree beneath another element", async () => {
      await selectNode(page, CIVIL);
      await clickToolbar(page, "data-wbs-copy");
      const clipboard = await clipboardText(page);
      check(
        "wbs3-copy-clipboard",
        "Copy records the selected element in the page-local clipboard",
        clipboard === "Clipboard: copy — Civil works (2)",
        clipboard,
      );
      await capture(page, "01-wbs-copy-clipboard");
      await selectNode(page, PM);
      const writesBefore = writes.length;
      await clickToolbar(page, "data-wbs-paste");
      await sleep(1600);
      const nodes = await wbsList(page);
      const copyRoot = nodes.find((node) => node.parent_wbs_id === PM && node.code === "2");
      check(
        "wbs3-copy-request",
        "Paste sends one POST to the copy endpoint",
        writes.slice(writesBefore).some((entry) => entry.method === "POST" && entry.url.endsWith(`/wbs/${CIVIL}/copy`)),
        writes.slice(writesBefore),
      );
      check(
        "wbs3-copy-root",
        "the copied root is a new record beneath the selected target with the source code",
        Boolean(copyRoot) && copyRoot.wbs_id.startsWith("WBS-COPY-") && copyRoot.record_revision === 1,
        copyRoot ?? null,
      );
      assert(copyRoot, "copied root is missing");
      copiedRootId = copyRoot.wbs_id;
      const copyChild = nodes.find((node) => node.parent_wbs_id === copiedRootId);
      check(
        "wbs3-copy-child",
        "the copied subtree contains the source child",
        copyChild?.code === "2.1" && copyChild?.name === "Site survey",
        copyChild ?? null,
      );
      const copiedMilestones = await api(page, "GET", `${WBS_PATH}/${copiedRootId}/milestones`);
      check(
        "wbs3-copy-milestones",
        "weighted milestones are copied and the copied roll-up is 75%",
        copiedMilestones.status === 200 &&
          copiedMilestones.body.milestones.length === 2 &&
          copiedMilestones.body.percent_complete === 75,
        copiedMilestones.body,
      );
      const source = await nodeState(page, CIVIL);
      check(
        "wbs3-copy-source-unchanged",
        "the source record and its revision are unchanged",
        source.wbs.record_revision === civilBefore.wbs.record_revision &&
          source.wbs.parent_wbs_id === "WBS-RPS-ROOT",
        source.wbs,
      );
      check(
        "wbs3-copy-no-activities",
        "the copied subtree owns no activity assignments",
        !(await activityAssignments(page)).has(copiedRootId),
      );
      await capture(page, "02-wbs-copy-pasted");
      return { copiedRootId, copyChild };
    });

    await scenario("02", "Cut and paste moves the record and keeps its activity assignments", async () => {
      const before = await nodeState(page, PROC);
      const countsBefore = await activityAssignments(page);
      await selectNode(page, PROC);
      await clickToolbar(page, "data-wbs-cut");
      const clipboard = await clipboardText(page);
      check(
        "wbs3-cut-clipboard",
        "Cut records the selected element as a cut entry",
        clipboard === "Clipboard: cut — Procurement (3)",
        clipboard,
      );
      await selectNode(page, ENV);
      const writesBefore = writes.length;
      await clickToolbar(page, "data-wbs-paste");
      const moved = await waitForNode(page, PROC, (wbs) => wbs.parent_wbs_id === ENV, "PROC moved beneath ENV");
      check(
        "wbs3-cut-move",
        "Paste moves the same record to the selected parent and advances its revision",
        moved.wbs.wbs_id === PROC && moved.wbs.record_revision === before.wbs.record_revision + 1,
        { before: before.wbs, after: moved.wbs },
      );
      check(
        "wbs3-cut-request",
        "Cut paste uses PATCH on the existing WBS record",
        writes.slice(writesBefore).some((entry) => entry.method === "PATCH" && entry.url.endsWith(`/wbs/${PROC}`)),
        writes.slice(writesBefore),
      );
      const countsAfter = await activityAssignments(page);
      check(
        "wbs3-cut-activities",
        "the activity assignments stay attached to the moved WBS identity",
        countsBefore.get(PROC) === 1 && countsAfter.get(PROC) === 1,
        { before: countsBefore.get(PROC), after: countsAfter.get(PROC) },
      );
      check(
        "wbs3-cut-clipboard-cleared",
        "pasting a cut clears the page-local clipboard",
        (await clipboardText(page)) === "Clipboard empty",
        await clipboardText(page),
      );
      await capture(page, "03-wbs-cut-pasted");
      return { parentWbsId: moved.wbs.parent_wbs_id };
    });

    await scenario("03", "Pasting a cut into its own descendant is rejected as a hierarchy cycle", async () => {
      assert(copiedRootId, "copied root is missing");
      await selectNode(page, PM);
      await clickToolbar(page, "data-wbs-cut");
      await selectNode(page, copiedRootId);
      await clickToolbar(page, "data-wbs-paste");
      await sleep(1600);
      const pm = await nodeState(page, PM);
      check(
        "wbs3-cycle-rejected",
        "the WBS record is not reparented under its descendant",
        pm.wbs.parent_wbs_id === "WBS-RPS-ROOT",
        pm.wbs,
      );
      const notice = await page.evaluate(
        `document.querySelector('#cp-project-wbs [data-wbs-error]')?.textContent?.trim() ?? ""`,
      );
      check(
        "wbs3-cycle-notice",
        "the window states the hierarchy-cycle rejection",
        notice.includes("WBS_HIERARCHY_CYCLE"),
        notice,
      );
      await capture(page, "04-wbs-cycle-rejected");
      return { notice };
    });

    await scenario("04", "A sibling code collision is rejected without creating a record", async () => {
      const before = await wbsList(page);
      const conflict = await api(page, "POST", `${WBS_PATH}/${CIVIL}/copy`, {
        expected_revision: (await nodeState(page, CIVIL)).wbs.record_revision,
        target_parent_wbs_id: PM,
        code: "2",
      });
      check(
        "wbs3-sibling-conflict",
        "copying onto an existing sibling code is rejected with WBS_SIBLING_CODE_CONFLICT",
        conflict.status === 400 && conflict.body?.code === "WBS_SIBLING_CODE_CONFLICT",
        conflict,
      );
      const after = await wbsList(page);
      check(
        "wbs3-sibling-no-write",
        "the rejected copy leaves the hierarchy unchanged",
        after.length === before.length,
        { before: before.length, after: after.length },
      );
      return { status: conflict.status };
    });

    await scenario("05", "Deleting a WBS element in use states the precondition and keeps the record", async () => {
      await selectNode(page, CIVIL);
      await clickToolbar(page, "data-wbs-delete");
      await sleep(1400);
      const guidance = await page.evaluate(
        `document.querySelector('.cp-wbs-window [data-wbs-delete-guidance]')?.textContent?.trim() ?? ""`,
      );
      check(
        "wbs3-delete-guidance",
        "the delete refusal explains the child/activity precondition instead of the raw code",
        guidance.includes("child elements or activity assignments") && !guidance.includes("WBS_IN_USE"),
        guidance,
      );
      const civil = await nodeState(page, CIVIL);
      check(
        "wbs3-delete-intact",
        "the node in use is still present after the refusal",
        civil.wbs.wbs_id === CIVIL,
        civil.wbs,
      );
      await capture(page, "05-wbs-delete-guidance");
      return { guidance };
    });

    await scenario("06", "Persian RTL shows the WBS clipboard commands without overflow", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await setLanguage(page, "fa");
      await openWbs(page);
      await selectNode(page, CIVIL);
      const state = await page.evaluate(`(() => {
        const labels = [...document.querySelectorAll(".cp-wbs-window [data-wbs-cut], .cp-wbs-window [data-wbs-copy], .cp-wbs-window [data-wbs-paste]")]
          .map((button) => (button.textContent || "").trim());
        return {
          dir: document.documentElement.dir,
          lang: document.documentElement.lang,
          overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
          labels,
        };
      })()`);
      check(
        "wbs3-fa-rtl",
        "the Persian WBS window is right-to-left",
        state.dir === "rtl" && state.lang === "fa",
        { dir: state.dir, lang: state.lang },
      );
      check(
        "wbs3-fa-labels",
        "the Cut, Copy and Paste commands are localized",
        state.labels.join("|").includes("برش") && state.labels.join("|").includes("کپی") && state.labels.join("|").includes("چسباندن"),
        state.labels,
      );
      check("wbs3-fa-no-overflow", "the page does not overflow horizontally", state.overflow <= 0, state.overflow);
      await capture(page, "06-wbs-clipboard-fa-rtl");
      return state;
    });

    await scenario("07", "A reload restores the copied and moved hierarchy and empties the clipboard", async () => {
      await setLanguage(page, "en");
      await reloadWorkspace(page);
      const nodes = await wbsList(page);
      const copyRoot = nodes.find((node) => node.wbs_id === copiedRootId);
      const copyChild = nodes.find((node) => node.parent_wbs_id === copiedRootId);
      const proc = nodes.find((node) => node.wbs_id === PROC);
      check(
        "wbs3-reload-copy",
        "the copied root and child are still persisted beneath their target",
        copyRoot?.parent_wbs_id === PM && copyChild?.code === "2.1",
        { copyRoot: copyRoot ?? null, copyChild: copyChild ?? null },
      );
      check(
        "wbs3-reload-cut",
        "the cut element is still persisted beneath its new parent",
        proc?.parent_wbs_id === ENV,
        proc ?? null,
      );
      check(
        "wbs3-reload-clipboard",
        "the page-local clipboard is empty after a reload",
        (await clipboardText(page)) === "Clipboard empty",
        await clipboardText(page),
      );
      await capture(page, "07-wbs-reloaded");
      return { nodes: nodes.length };
    });
  } catch (error) {
    summary.error = String(error?.message ?? error);
    log(`\nFAILED: ${summary.error}`);
  } finally {
    summary.finishedAt = new Date().toISOString();
    summary.status = summary.error || checks.some((entry) => !entry.ok) ? "failed" : "passed";
    writeFileSync(join(evidenceDir, "contract.json"), `${JSON.stringify(summary, null, 2)}\n`);
    await chrome.cdp.send("Browser.close").catch(() => undefined);
  }

  const failed = checks.filter((entry) => !entry.ok);
  log(`\n${checks.length - failed.length} of ${checks.length} WBS-003 checks passed`);
  if (failed.length || summary.error) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  log(`UNHANDLED: ${error?.stack ?? error}`);
  process.exitCode = 1;
});
