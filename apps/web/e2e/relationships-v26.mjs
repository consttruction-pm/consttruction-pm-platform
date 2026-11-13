#!/usr/bin/env node
/**
 * Browser E2E for REL-001 — persisted relationship lifecycle through the
 * Logic / Relationships panel, with the Activity Details predecessor and
 * successor views and a role-denied write.
 *
 * Drives the real local full-stack preview through headless Chrome. The
 * fixture project is read from the server; the suite creates one relationship,
 * edits it, deletes it, and checks that rejected input is reported instead of
 * failing silently.
 *
 * Usage:
 *   node e2e/relationships-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import {
  Page,
  artifactsDir,
  gitHead,
  launchChrome,
  startManagedRuntime,
} from "./preview-e2e.mjs";

const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-13";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const outDir = join(artifactsDir, "relationships-v26");
const evidenceDir = join(
  artifactsDir,
  "..",
  "..",
  "..",
  "..",
  "docs",
  "workspace",
  "evidence",
  `relationships-v26-${evidenceDate}`,
);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const writes = [];
const scenarios = [];
const screenshots = [];
let baseUrl = "";

function log(message) {
  process.stdout.write(`${message}\n`);
}

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

async function scenario(id, name, body) {
  log(`\n[${id}] ${name}`);
  try {
    const details = (await body()) ?? {};
    scenarios.push({ ...details, id, name, status: "pass", at: new Date().toISOString() });
    log(`  PASS ${id}. ${name}`);
    return details;
  } catch (error) {
    scenarios.push({
      id,
      name,
      status: "fail",
      error: String(error && error.stack ? error.stack : error),
      at: new Date().toISOString(),
    });
    log(`  FAIL ${id}. ${name}`);
    throw error;
  }
}

const logicState = `(() => {
  const drawer = document.querySelector("[data-tools-drawer]");
  const rows = [...document.querySelectorAll("#cp-logic [data-relationship-id]")].map((row) => ({
    id: row.dataset.relationshipId,
    pair: (row.querySelector(".cp-logic-pair")?.textContent ?? "").trim(),
    type: (row.querySelector(".cp-logic-type")?.textContent ?? "").trim(),
    lag: (row.querySelector(".cp-logic-lag")?.textContent ?? "").trim(),
    revision: Number(row.querySelector("[data-relationship-delete]")?.getAttribute("data-relationship-revision") ?? 0),
  }));
  const form = document.querySelector("#cp-logic form[data-relationship-create-form]");
  return {
    open: Boolean(drawer && !drawer.hidden),
    rows,
    activities: form ? [...form.querySelectorAll('select[name="predecessor_id"] option')].map((option) => option.value) : [],
    notice: (document.querySelector("#cp-logic [data-relationship-error]")?.textContent ?? "").trim() || null,
    confirmCalls: window.__confirmCalls ?? 0,
  };
})()`;

async function capture(page, name) {
  const file = `relationships-v26/${name}.png`;
  await page.screenshot(file);
  copyFileSync(join(artifactsDir, file), join(evidenceDir, `${name}.png`));
  screenshots.push(`${name}.png`);
  return file;
}

async function loginAs(page, label) {
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
  await page.waitForSelector(".persona", "persona cards");
  const clicked = await page.evaluate(`(() => {
    const button = [...document.querySelectorAll("form button")].find((item) => (item.textContent || "").trim().startsWith(${JSON.stringify(label)}));
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `${label} login button is missing`);
  await page.waitFor(
    `Boolean(document.querySelector('[data-project-id="${PROJECT}"]')) || Boolean(document.querySelector("#cp-activity-grid tbody tr[data-activity-id]"))`,
    "project picker or activity grid",
  );
  const picker = await page.evaluate(
    `Boolean(document.querySelector('[data-project-id="${PROJECT}"]'))`,
  );
  if (picker) {
    await page.click(`[data-project-id="${PROJECT}"]`);
  }
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
  await sleep(1200);
}

async function openLogic(page) {
  await page.click('[data-desktop-menu="project"]');
  await sleep(220);
  await page.click('[data-desktop-item="project.predecessors"]');
  await page.waitFor("Boolean(document.querySelector('#cp-logic form[data-relationship-create-form]'))", "logic panel");
  await sleep(350);
  const state = await page.evaluate(logicState);
  assert(state.open, "logic drawer did not open");
  assert(state.activities.length >= 2, `fewer than two activities ${state.activities.length}`);
  return state;
}

async function submitCreate(page, predecessor, successor, type = "FS", lag = "0") {
  return page.evaluate(`(() => {
    const form = document.querySelector("#cp-logic form[data-relationship-create-form]");
    if (!form) return false;
    form.querySelector('[name="predecessor_id"]').value = ${JSON.stringify(predecessor)};
    form.querySelector('[name="successor_id"]').value = ${JSON.stringify(successor)};
    form.querySelector('[name="relationship_type"]').value = ${JSON.stringify(type)};
    form.querySelector('[name="lag_value"]').value = ${JSON.stringify(lag)};
    form.querySelector('[name="lag_unit"]').value = "working-day";
    form.requestSubmit();
    return true;
  })()`);
}

async function waitForChange(page, previousCount, predicate = "", label = "relationship list change") {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    await sleep(250);
    const state = await page.evaluate(logicState);
    if (predicate) {
      if (state[predicate]) return state;
    } else if (state.rows.length !== previousCount || state.notice) {
      return state;
    }
  }
  throw new Error(`ASSERTION_FAILED: timed out waiting for ${label}`);
}

function pairOf(rows) {
  return new Set(rows.map((row) => row.pair.replace(/\s+/g, "")));
}

/** Create a pair of activities with no relationship in either direction. */
function pickFreshPair(state) {
  const existing = pairOf(state.rows);
  const activities = state.activities;
  for (let i = 0; i < activities.length; i += 1) {
    for (let j = i + 1; j < activities.length; j += 1) {
      const forward = `${activities[i]}→${activities[j]}`;
      const backward = `${activities[j]}→${activities[i]}`;
      if (!existing.has(forward) && !existing.has(backward)) {
        return { predecessor: activities[i], successor: activities[j] };
      }
    }
  }
  throw new Error("ASSERTION_FAILED: no unrelated activity pair is available");
}

async function main() {
  const runtime = await startManagedRuntime();
  baseUrl = runtime.baseUrl;
  const chrome = await launchChrome();
  const page = new Page(chrome.cdp);
  await page.initialize();
  page.cdp.on("Runtime.exceptionThrown", (params) => {
    exceptions.push(
      params.exceptionDetails?.exception?.description ??
        params.exceptionDetails?.text ??
        "unknown exception",
    );
  });
  page.cdp.on("Runtime.consoleAPICalled", (params) => {
    if (params.type !== "error") return;
    consoleErrors.push(
      (params.args ?? []).map((arg) => arg.value ?? arg.description ?? arg.type).join(" "),
    );
  });
  page.cdp.on("Network.responseReceived", (params) => {
    const url = params.response?.url ?? "";
    if (url.includes("/api/") && params.response.status >= 500) {
      apiFailures.push({ status: params.response.status, url });
    }
  });
  page.cdp.on("Network.requestWillBeSent", (params) => {
    const url = params.request?.url ?? "";
    const method = params.request?.method ?? "GET";
    if (!url.includes("/api/")) return;
    if (method === "GET" || method === "HEAD" || method === "OPTIONS") return;
    writes.push({ method, url });
  });

  const report = {
    contract: "cubi-relationships-v26.v1",
    baseUrl,
    project: PROJECT,
    gitHead: gitHead(),
    testedCodeSha,
    capturedAt: new Date().toISOString(),
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
    writes,
  };

  // The created relationship id is shared across scenarios so cleanup and the
  // persistence checks refer to exactly one row.
  let created = null;

  try {
    await page.cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1440,
      height: 900,
      deviceScaleFactor: 1,
      mobile: false,
    });
    await sleep(400);
    await loginAs(page, "Project administrator");
    let state = await openLogic(page);
    const initialCount = state.rows.length;

    await scenario("01", "the Logic panel lists every persisted relationship with pair, type and lag", async () => {
      assert(initialCount > 0, "fixture has no persisted relationships");
      assert(
        state.rows.every((row) => row.pair.includes("→") && ["FS", "SS", "FF", "SF"].includes(row.type)),
        `relationship rows ${JSON.stringify(state.rows.slice(0, 3))}`,
      );
      assert(
        state.rows.every((row) => row.revision >= 1),
        "a relationship row has no record revision",
      );
      await capture(page, "01-persisted-logic");
      return { count: initialCount, sample: state.rows.slice(0, 3) };
    });

    await scenario("02", "submitting one activity twice is reported instead of silently ignored", async () => {
      const activity = state.activities[0];
      await submitCreate(page, activity, activity, "FS", "0");
      const after = await waitForChange(page, initialCount, "notice", "self-link notice");
      assert(after.rows.length === initialCount, `row count changed ${after.rows.length}`);
      assert(after.notice, "no visible notice for a self relationship");
      await capture(page, "02-self-link-notice");
      return { notice: after.notice };
    });

    await scenario("03", "a new relationship is created with its type and lag", async () => {
      state = await page.evaluate(logicState);
      const pair = pickFreshPair(state);
      const before = state.rows.length;
      await submitCreate(page, pair.predecessor, pair.successor, "SS", "2");
      const after = await waitForChange(page, before, "", "created relationship");
      assert(after.rows.length === before + 1, `rows ${before} -> ${after.rows.length}: ${after.notice ?? ""}`);
      const expected = `${pair.predecessor} → ${pair.successor}`;
      const row = after.rows.find((item) => item.pair === expected);
      assert(row, `created pair ${expected} missing from ${JSON.stringify(after.rows.map((item) => item.pair))}`);
      assert(row.type === "SS", `type ${row.type}`);
      assert(row.lag.startsWith("2"), `lag ${row.lag}`);
      assert(row.id.startsWith("REL-"), `id ${row.id}`);
      created = { ...row, predecessor: pair.predecessor, successor: pair.successor };
      await capture(page, "03-created-ss");
      return { relationship: created };
    });

    await scenario("04", "the created relationship survives a full reload", async () => {
      await page.reload("[data-window-tab]");
      await sleep(1800);
      const after = await openLogic(page);
      const row = after.rows.find((item) => item.id === created.id);
      assert(row, `relationship ${created.id} disappeared`);
      assert(row.pair === created.pair, `pair ${row.pair}`);
      assert(row.type === "SS", `type after reload ${row.type}`);
      await capture(page, "04-reload-persisted");
      return { id: row.id, type: row.type };
    });

    await scenario("05", "editing type and lag in the Logic panel persists", async () => {
      const panel = await page.evaluate(`(() => {
        const box = document.querySelector('[data-relationship-edit-box="${created.id}"]');
        if (!box) return false;
        box.open = true;
        const form = box.querySelector("form[data-relationship-edit-form]");
        form.querySelector('[name="relationship_type"]').value = "FF";
        form.querySelector('[name="lag_value"]').value = "3";
        form.querySelector('[name="lag_unit"]').value = "working-day";
        form.requestSubmit();
        return true;
      })()`);
      assert(panel, "edit form did not open");
      let after = null;
      for (let attempt = 0; attempt < 40; attempt += 1) {
        await sleep(250);
        after = await page.evaluate(logicState);
        const row = after.rows.find((item) => item.id === created.id);
        if (row && row.type === "FF") break;
      }
      const row = after?.rows.find((item) => item.id === created.id);
      assert(row, "edited relationship disappeared");
      assert(row.type === "FF", `type after edit ${row.type}`);
      assert(row.lag.startsWith("3"), `lag after edit ${row.lag}`);
      assert(row.revision > created.revision, `revision did not advance ${created.revision} -> ${row.revision}`);
      await capture(page, "05-edited-ff");
      return { id: row.id, type: row.type, lag: row.lag, revision: row.revision };
    });

    await scenario("06", "Activity Details shows the pair under Predecessors and Successors", async () => {
      await page.click(`tr[data-activity-id="${created.successor}"]`);
      await sleep(500);
      await page.click('[data-detail-tab="relationships"]');
      await sleep(400);
      const successorView = await page.evaluate('document.querySelector("#cp-details")?.textContent ?? ""');
      assert(successorView.includes(created.predecessor), "predecessor id missing from the successor's details");
      assert(successorView.includes("FF"), "relationship type missing from the predecessor table");

      await page.click(`tr[data-activity-id="${created.predecessor}"]`);
      await sleep(500);
      const predecessorView = await page.evaluate('document.querySelector("#cp-details")?.textContent ?? ""');
      assert(predecessorView.includes(created.successor), "successor id missing from the predecessor's details");
      await capture(page, "06-details-predecessors-successors");
      return { successorView: true, predecessorView: true };
    });

    await scenario("07", "deleting a relationship asks first and only then removes it", async () => {
      await openLogic(page);
      await page.evaluate(`(() => {
        window.__confirmCalls = 0;
        window.confirm = () => { window.__confirmCalls += 1; return false; };
        return true;
      })()`);
      await page.click(`[data-relationship-delete="${created.id}"]`);
      await sleep(500);
      let state = await page.evaluate(logicState);
      assert(state.confirmCalls === 1, `confirm calls ${state.confirmCalls}`);
      assert(state.rows.some((item) => item.id === created.id), "relationship deleted despite cancel");
      await capture(page, "07-delete-cancel");

      await page.evaluate("window.confirm = () => { window.__confirmCalls += 1; return true; }");
      await page.click(`[data-relationship-delete="${created.id}"]`);
      const before = state.rows.length;
      state = await waitForChange(page, before, "", "deleted relationship");
      assert(!state.rows.some((item) => item.id === created.id), "relationship still listed after delete");
      await capture(page, "07-delete-accept");
      return { confirmCalls: state.confirmCalls, remaining: state.rows.length };
    });

    await scenario("08", "a duplicate relationship is rejected with a visible notice", async () => {
      const state = await page.evaluate(logicState);
      const existing = state.rows[0];
      const [predecessor, successor] = existing.pair.split("→").map((part) => part.trim());
      const before = state.rows.length;
      await submitCreate(page, predecessor, successor, existing.type, "0");
      const after = await waitForChange(page, before, "notice", "duplicate notice");
      assert(after.rows.length === before, `duplicate created a row ${before} -> ${after.rows.length}`);
      assert(after.notice, "no visible notice for a duplicate relationship");
      await capture(page, "08-duplicate-notice");
      return { notice: after.notice };
    });

    await scenario("09", "the deleted relationship stays gone after a reload", async () => {
      await page.reload("[data-window-tab]");
      await sleep(1800);
      const state = await openLogic(page);
      assert(
        !state.rows.some((item) => item.id === created.id),
        `deleted relationship ${created.id} came back`,
      );
      assert(
        state.rows.length === initialCount,
        `row count ${state.rows.length} did not return to ${initialCount}`,
      );
      await capture(page, "09-deleted-after-reload");
      return { remaining: state.rows.length };
    });

    await scenario("10", "a viewer sees the persisted logic but the server rejects a create", async () => {
      await page.evaluate('fetch("/preview/logout", { method: "POST", redirect: "manual" }).then(() => true)');
      await sleep(800);
      await loginAs(page, "Viewer");
      const state = await openLogic(page);
      const before = state.rows.length;
      const pair = pickFreshPair(state);
      await submitCreate(page, pair.predecessor, pair.successor, "FS", "0");
      let after = null;
      for (let attempt = 0; attempt < 40; attempt += 1) {
        await sleep(250);
        after = await page.evaluate(logicState);
        if (after.notice || after.rows.length !== before) break;
      }
      assert(after, "no response to the viewer create");
      assert(after.rows.length === before, `viewer created a row ${before} -> ${after.rows.length}`);
      assert(after.notice, "viewer denial has no visible notice");
      await capture(page, "10-viewer-denied");
      return { notice: after.notice };
    });

    await scenario("11", "only the two intentionally rejected writes logged an error", async () => {
      const unexpected = consoleErrors.filter((message) => !message.startsWith("Relationship mutation failed"));
      assert(unexpected.length === 0, `unexpected console errors ${JSON.stringify(unexpected)}`);
      assert(consoleErrors.length === 2, `console errors ${JSON.stringify(consoleErrors)}`);
      assert(apiFailures.length === 0, `5xx responses ${JSON.stringify(apiFailures)}`);
      return { rejectedWrites: consoleErrors.length };
    });

    return report;
  } finally {
    report.finishedAt = new Date().toISOString();
    report.status = scenarios.some((item) => item.status === "fail") ? "failed" : "passed";
    report.writes = writes;
    const reportFile = join(evidenceDir, "relationships-v26.json");
    writeFileSync(reportFile, JSON.stringify(report, null, 2));
    log(`\nEvidence: ${reportFile}`);
    log(`Screenshots: ${screenshots.length}`);
    log(`Exceptions: ${exceptions.length}, console errors: ${consoleErrors.length}, 5xx: ${apiFailures.length}`);
    page.cdp.close();
    await chrome.stop();
    await runtime.stop();
  }
}

main().then(
  () => process.exit(0),
  (error) => {
    process.stderr.write(`\nE2E FAILED: ${error && error.stack ? error.stack : error}\n`);
    process.exit(1);
  },
);
