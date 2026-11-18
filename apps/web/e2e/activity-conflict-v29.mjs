#!/usr/bin/env node
/**
 * V29: a real two-session optimistic-concurrency conflict (HTTP 409).
 *
 * Two independent browser sessions read A130. Session A saves first. Session B
 * still holds the old record revision, saves, must receive REVISION_CONFLICT,
 * must show that rejection in the General editor, and must read session A's
 * value after reload. Session A's write is never lost.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4197 node e2e/activity-conflict-v29.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4197";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const outDir = join(artifactsDir, "activity-conflict-v29");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", "activity-workspace-v29");
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const report = {
  contract: "cubi-activity-conflict-v29.v1",
  url: baseUrl,
  testedCodeSha,
  capturedAt: new Date().toISOString(),
  responses: [],
  steps: [],
  screenshots: [],
};

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

async function capture(page, name) {
  await page.screenshot(`activity-conflict-v29/${name}.png`);
  copyFileSync(join(outDir, `${name}.png`), join(evidenceDir, `${name}.png`));
  report.screenshots.push(`${name}.png`);
}

async function login(page) {
  await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 768, deviceScaleFactor: 1, mobile: false });
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "form", "login");
  await page.evaluate(`(() => { localStorage.setItem("cubi:workspace-locale", "en"); return true; })()`);
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "form", "login");
  await page.click('button[name="role"][value="admin"]');
  await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
  await page.click('[data-project-id="preview-rps-01"]');
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
  await sleep(1400);
}

async function selectA130(page) {
  const selected = await page.evaluate(`(() => {
    const row = document.querySelector('#cp-activity-grid tbody tr[data-activity-id="A130"]');
    if (!row) return false;
    row.click();
    return true;
  })()`);
  assert(selected, "A130 row is missing");
  await page.waitFor(`document.querySelector('#cp-details .cp-detail-selected')?.textContent?.includes('A130')`, "A130 selected", 8000);
  await sleep(400);
}

async function openGeneralEditor(page) {
  await page.evaluate(`document.querySelector('#cp-details [data-detail-tab="general"]')?.click()`);
  await page.waitForSelector('#cp-details [data-detail-panel="general"]:not([hidden])', "general panel", 8000);
  await sleep(400);
  const loaded = await page.evaluate(`(() => {
    const button = document.querySelector('#cp-details [data-general-edit-load]');
    if (!button || button.disabled) return false;
    button.click();
    return true;
  })()`);
  assert(loaded, "the General editor could not be loaded");
  await page.waitForSelector('#cp-details [data-details-form="general"] input[name="name"]', "general form", 8000);
  await sleep(300);
}

async function readName(page) {
  return page.evaluate(`(() => {
    const input = document.querySelector('#cp-details [data-details-form="general"] input[name="name"]');
    return input ? input.value : null;
  })()`);
}

async function saveName(page, name) {
  return page.evaluate(`(() => {
    const form = document.querySelector('#cp-details [data-details-form="general"]');
    if (!form) return false;
    const input = form.elements.namedItem("name");
    input.value = ${JSON.stringify(name)};
    input.dispatchEvent(new Event("input", { bubbles: true }));
    form.querySelector('button[type="submit"]').click();
    return true;
  })()`);
}

async function formMessage(page) {
  return page.evaluate(`(() => {
    const form = document.querySelector('#cp-details [data-details-form="general"]');
    return form?.querySelector('[data-details-form-message]')?.textContent ?? "";
  })()`);
}

async function main() {
  const chromeA = await launchChrome();
  const chromeB = await launchChrome();
  const pageA = new Page(chromeA.cdp);
  const pageB = new Page(chromeB.cdp);
  await pageA.initialize();
  await pageB.initialize();
  for (const [label, page] of [["A", pageA], ["B", pageB]]) {
    page.cdp.on("Network.responseReceived", (params) => {
      const url = params.response?.url ?? "";
      if (!/\/api\/projects\/preview-rps-01\/p6\/activities\/A130/.test(url)) return;
      report.responses.push({ session: label, url, status: params.response.status });
    });
  }

  await login(pageA);
  await login(pageB);
  await selectA130(pageA);
  await selectA130(pageB);

  // Both sessions load the same record revision.
  await openGeneralEditor(pageA);
  await openGeneralEditor(pageB);
  const original = await readName(pageA);
  const same = (await readName(pageB)) === original;
  assert(original && same, "both sessions must read the same activity name");
  report.originalName = original;

  // Session A saves first.
  const winner = `V29 winner ${Date.now()}`;
  assert(await saveName(pageA, winner), "session A could not submit");
  await sleep(1600);
  const winnerMessage = await formMessage(pageA);
  assert(!/REVISION_CONFLICT|rejected/i.test(winnerMessage), `session A was rejected: ${winnerMessage}`);
  report.steps.push({ session: "A", action: "save", name: winner, message: winnerMessage, status: "pass" });
  await capture(pageA, "01-winner-saved-en-1366");

  // Session B still holds the old revision and must be rejected with 409.
  const loser = `V29 stale ${Date.now()}`;
  assert(await saveName(pageB, loser), "session B could not submit");
  await sleep(1600);
  const loserMessage = await formMessage(pageB);
  assert(/REVISION_CONFLICT|rejected/i.test(loserMessage), `session B was not rejected: ${loserMessage}`);
  report.steps.push({ session: "B", action: "stale-save", name: loser, message: loserMessage, status: "pass" });
  await capture(pageB, "02-conflict-rejected-en-1366");

  // The shell must repaint from the authoritative record: session A's value is
  // intact and session B's stale value was never stored.
  await pageB.navigate(`${baseUrl}/app?view=live&project=preview-rps-01`, "#cp-activity-grid tbody [data-activity-id]", "session B reload");
  await sleep(1600);
  await selectA130(pageB);
  await openGeneralEditor(pageB);
  const reread = await readName(pageB);
  assert(reread === winner, `session B reread ${reread}, expected ${winner}`);
  report.steps.push({ session: "B", action: "read-after-conflict", name: reread, status: "pass" });

  // Restore the fixture name through session A with a fresh revision.
  await pageA.navigate(`${baseUrl}/app?view=live&project=preview-rps-01`, "#cp-activity-grid tbody [data-activity-id]", "session A reload");
  await sleep(1600);
  await selectA130(pageA);
  await openGeneralEditor(pageA);
  assert(await saveName(pageA, original), "restore submit failed");
  await sleep(1600);
  report.restoredName = original;

  assert(report.responses.some((entry) => entry.session === "B" && entry.status === 409), "no 409 response was observed for session B");
  report.finishedAt = new Date().toISOString();
  writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
  writeFileSync(join(evidenceDir, "conflict-409.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ ok: true, steps: report.steps, responses: report.responses }, null, 2));
  await chromeA.stop();
  await chromeB.stop();
  process.exit(0);
}

main().catch(async (error) => {
  report.finishedAt = new Date().toISOString();
  report.failure = error?.stack ?? String(error);
  writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
  writeFileSync(join(evidenceDir, "conflict-409.json"), JSON.stringify(report, null, 2));
  console.error(error?.stack ?? error);
  process.exit(1);
});
