#!/usr/bin/env node
/**
 * WBS-002 browser acceptance: WBS status, percent-complete technique and
 * weighted WBS milestones.
 *
 * Everything is asserted against the real full-stack preview. The status and
 * technique are saved from the WBS window settings form, the milestone editor
 * saves a weighted list through PUT /p6/wbs/{id}/milestones, and the roll-up
 * is compared with the persisted percent_complete the workspace read returns.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4231 node e2e/wbs-status-milestones-v26.mjs
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
  "docs", "workspace", "evidence", `wbs-002-status-milestones-${evidenceDate}`,
);
const outPrefix = "wbs-002-status-milestones";
const outDir = join(artifactsDir, outPrefix);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const WBS_ID = "WBS-RPS-CIVIL";
const WBS_PATH = `/api/projects/${PROJECT}/p6/wbs`;

const scenarios = [];
const checks = [];
const screenshots = [];
const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const writes = [];

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
        headers: { "Content-Type": "application/json", "Idempotency-Key": "e2e-wbs2-" + Math.random().toString(36).slice(2) },
        ${body === undefined ? "" : `body: JSON.stringify(${JSON.stringify(body)}),`}
      });
      return { status: response.status, body: await response.json().catch(() => null) };
    })()`,
    { awaitPromise: true },
  );
}

async function nodeState(page, wbsId) {
  const response = await api(page, "GET", `${WBS_PATH}/${wbsId}`);
  assert(response.status === 200, `GET ${WBS_PATH}/${wbsId} returned ${response.status}`);
  return response.body;
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
  const tableVisible = await page.evaluate('Boolean(document.querySelector(".cp-wbs-window [data-wbs-table]"))');
  if (!tableVisible) await switchView(page, "table");
  await page.waitForSelector(".cp-wbs-window [data-wbs-table]", "WBS table", 20000);
  await sleep(300);
}

async function switchView(page, view) {
  const clicked = await page.evaluate(`(() => {
    const button = document.querySelector('.cp-wbs-window [data-wbs-view="${view}"]');
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `WBS view toggle ${view} is missing`);
  await page.waitFor(
    `Boolean(document.querySelector(${JSON.stringify(view === "chart" ? ".cp-wbs-window [data-wbs-chart]" : ".cp-wbs-window [data-wbs-table]")}))`,
    `${view} view`,
    10000,
  );
  await sleep(250);
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
  await sleep(300);
}

async function openTab(page, tab) {
  const clicked = await page.evaluate(`(() => {
    const button = document.querySelector('.cp-wbs-window [data-wbs-detail-tab="${tab}"]');
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `WBS detail tab ${tab} is missing`);
  await page.waitFor(
    `document.querySelector('.cp-wbs-window [data-wbs-detail-panel="${tab}"]')?.hidden === false`,
    `${tab} panel`,
    10000,
  );
  await sleep(250);
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

const generalPanelText = `document.querySelector('.cp-wbs-window [data-wbs-detail-panel="general"]')?.textContent ?? ""`;
const milestonesPanel = `.cp-wbs-window [data-wbs-detail-panel="milestones"]`;

async function saveStatus(page, status, technique) {
  const submitted = await page.evaluate(`(() => {
    const form = document.querySelector('.cp-wbs-window [data-wbs-status-form="${WBS_ID}"]');
    if (!form) return false;
    form.querySelector('[name="status"]').value = ${JSON.stringify(status)};
    form.querySelector('[name="percent_complete_technique"]').value = ${JSON.stringify(technique)};
    form.requestSubmit();
    return true;
  })()`);
  assert(submitted, "WBS status form is missing");
  await sleep(1500);
}

async function milestoneState(page) {
  return page.evaluate(`(() => ({
    rows: [...document.querySelectorAll('${milestonesPanel} [data-wbs-milestone-row]')].map((row) => ({
      id: row.querySelector('[name="milestone_id"]')?.value ?? "",
      name: row.querySelector('[name="milestone_name"]')?.value ?? "",
      weight: Number(row.querySelector('[name="milestone_weight"]')?.value ?? "NaN"),
      completed: Boolean(row.querySelector('[name="milestone_completed"]')?.checked),
    })),
    rollup: document.querySelector('${milestonesPanel} [data-wbs-milestone-rollup]')?.textContent?.trim() ?? "",
    total: document.querySelector('${milestonesPanel} [data-wbs-milestone-total]')?.textContent?.trim() ?? "",
    revision: Number(document.querySelector('${milestonesPanel} [data-wbs-milestones-form]')?.dataset.wbsRevision ?? "0"),
    panelText: document.querySelector('${milestonesPanel}')?.textContent ?? "",
  }))()`);
}

async function addMilestones(page, items) {
  for (let index = 0; index < items.length; index += 1) {
    const added = await page.evaluate(`(() => {
      const button = document.querySelector('${milestonesPanel} [data-wbs-milestone-add]');
      if (!button) return false;
      button.click();
      return true;
    })()`);
    assert(added, "add-milestone button is missing");
  }
  const filled = await page.evaluate(`(() => {
    const rows = [...document.querySelectorAll('${milestonesPanel} [data-wbs-milestone-row]')];
    const items = ${JSON.stringify(items)};
    items.forEach((item, index) => {
      const row = rows[index];
      if (!row) return;
      const set = (name, value) => {
        const input = row.querySelector('[name="' + name + '"]');
        if (!input) return;
        if (input.type === "checkbox") {
          input.checked = Boolean(value);
          input.dispatchEvent(new Event("input", { bubbles: true }));
          return;
        }
        input.value = String(value);
        input.dispatchEvent(new Event("input", { bubbles: true }));
      };
      set("milestone_id", item.id);
      set("milestone_name", item.name);
      set("milestone_weight", item.weight);
      set("milestone_completed", item.completed);
    });
    return rows.length;
  })()`);
  assert(filled === items.length, `expected ${items.length} milestone rows, found ${filled}`);
  await sleep(200);
}

async function submitMilestones(page) {
  const submitted = await page.evaluate(`(() => {
    const form = document.querySelector('${milestonesPanel} [data-wbs-milestones-form]');
    if (!form) return false;
    form.requestSubmit();
    return true;
  })()`);
  assert(submitted, "milestone form is missing");
  await sleep(1800);
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
  await selectNode(page, WBS_ID);
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

  const summary = {
    contract: "cubi-wbs-002-status-milestones.v1",
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

    await scenario("01", "WBS details read the persisted status and technique", async () => {
      await openWbs(page);
      await selectNode(page, WBS_ID);
      const before = await nodeState(page, WBS_ID);
      const text = await page.evaluate(generalPanelText);
      check(
        "wbs2-general-status",
        "the General tab shows the persisted status and technique instead of placeholders",
        text.includes("Status") && text.includes(before.wbs.status === "active" ? "Active" : "Planned") &&
          text.includes(before.wbs.percent_complete_technique === "milestones" ? "WBS Milestones" : "Activities"),
        { status: before.wbs.status, technique: before.wbs.percent_complete_technique },
      );
      check(
        "wbs2-settings-form",
        "the General tab exposes the status and technique editor",
        await page.evaluate(`Boolean(document.querySelector('.cp-wbs-window [data-wbs-status-form="${WBS_ID}"]'))`),
      );
      await capture(page, "01-wbs-general-status");
      return before.wbs;
    });

    await scenario("02", "Saving status Active and technique WBS Milestones persists both fields", async () => {
      const before = await nodeState(page, WBS_ID);
      await saveStatus(page, "active", "milestones");
      const after = await nodeState(page, WBS_ID);
      check(
        "wbs2-status-saved",
        "PATCH persists status=active and technique=milestones with an advanced revision",
        after.wbs.status === "active" &&
          after.wbs.percent_complete_technique === "milestones" &&
          after.wbs.record_revision === before.wbs.record_revision + 1,
        { before: before.wbs.record_revision, after: after.wbs.record_revision, status: after.wbs.status },
      );
      const text = await page.evaluate(generalPanelText);
      check(
        "wbs2-general-reflects-save",
        "the General tab reflects the saved status and technique",
        text.includes("Active") && text.includes("WBS Milestones"),
        text.slice(0, 240),
      );
      await capture(page, "02-wbs-status-saved");
      return { revision: after.wbs.record_revision };
    });

    await scenario("03", "The milestone editor rolls up weighted completion before saving", async () => {
      await openTab(page, "milestones");
      const empty = await milestoneState(page);
      check(
        "wbs2-milestones-empty",
        "a node without milestones shows an empty authoritative list, not fabricated rows",
        empty.rows.length === 0 && empty.rollup === "0.00%",
        empty,
      );
      await addMilestones(page, [
        { id: "M-1", name: "Mobilize", weight: 9, completed: true },
        { id: "M-2", name: "Foundations", weight: 1, completed: false },
        { id: "M-3", name: "Steel", weight: 1, completed: false },
        { id: "M-4", name: "Handover", weight: 1, completed: false },
      ]);
      const preview = await milestoneState(page);
      check(
        "wbs2-live-rollup",
        "the editor previews 9 of 12 weight complete as 75.00%",
        preview.rollup === "75.00%" && preview.total === "12",
        preview,
      );
      await capture(page, "03-wbs-milestone-editor");
      return preview;
    });

    await scenario("04", "Saved milestones persist and the roll-up matches the workspace read", async () => {
      await submitMilestones(page);
      const persisted = await api(page, "GET", `${WBS_PATH}/${WBS_ID}/milestones`);
      check(
        "wbs2-milestones-persisted",
        "PUT persists four weighted milestones and returns 75%",
        persisted.status === 200 &&
          persisted.body.milestones.length === 4 &&
          persisted.body.percent_complete === 75 &&
          persisted.body.percent_complete_technique === "milestones",
        persisted.body,
      );
      const node = await nodeState(page, WBS_ID);
      check(
        "wbs2-node-rollup",
        "the WBS record exposes the same weighted percent complete",
        node.wbs.percent_complete === 75,
        node.wbs,
      );
      const view = await milestoneState(page);
      check(
        "wbs2-ui-rollup",
        "the reloaded milestone tab shows the persisted weights and 75.00%",
        view.rows.length === 4 && view.rollup === "75.00%" && view.rows[0]?.completed === true,
        view,
      );
      await capture(page, "04-wbs-milestones-saved");
      return persisted.body;
    });

    await scenario("05", "Completing a second milestone advances the revision and the weighted roll-up", async () => {
      const before = await milestoneState(page);
      const toggled = await page.evaluate(`(() => {
        const row = document.querySelectorAll('${milestonesPanel} [data-wbs-milestone-row]')[3];
        const box = row?.querySelector('[name="milestone_completed"]');
        if (!box) return false;
        box.checked = true;
        box.dispatchEvent(new Event("input", { bubbles: true }));
        return true;
      })()`);
      check("wbs2-toggle-m4", "the fourth milestone completion can be toggled", toggled === true);
      const preview = await milestoneState(page);
      check(
        "wbs2-live-rollup-after-toggle",
        "the editor previews 10 of 12 weight complete as 83.33%",
        preview.rollup === "83.33%",
        preview.rollup,
      );
      await submitMilestones(page);
      const node = await nodeState(page, WBS_ID);
      check(
        "wbs2-second-save",
        "saving advances the WBS revision and persists 83.33%",
        node.wbs.record_revision === before.revision + 1 && node.wbs.percent_complete === 83.33,
        { revisionBefore: before.revision, revisionAfter: node.wbs.record_revision, percent: node.wbs.percent_complete },
      );
      await capture(page, "05-wbs-milestones-83");
      return node.wbs;
    });

    await scenario("06", "A stale revision cannot overwrite the saved milestone list", async () => {
      const current = await nodeState(page, WBS_ID);
      const stale = await api(page, "PUT", `${WBS_PATH}/${WBS_ID}/milestones`, {
        expected_revision: current.wbs.record_revision - 1,
        milestones: [{ milestone_id: "M-1", name: "Overwrite", weight: 1, completed: true, sequence_number: 0 }],
      });
      check(
        "wbs2-revision-conflict",
        "a PUT with an old expected revision returns 409 REVISION_CONFLICT",
        stale.status === 409 && stale.body?.code === "REVISION_CONFLICT",
        stale,
      );
      const after = await api(page, "GET", `${WBS_PATH}/${WBS_ID}/milestones`);
      check(
        "wbs2-conflict-no-write",
        "the rejected write leaves the persisted milestones untouched",
        after.body.milestones.length === 4 && after.body.milestones[0].name === "Mobilize",
        after.body.milestones,
      );
      return { status: stale.status };
    });

    await scenario("07", "Duplicate IDs and zero weights are rejected in the editor without a request", async () => {
      const writesBefore = writes.length;
      const duplicate = await page.evaluate(`(() => {
        const form = document.querySelector('${milestonesPanel} [data-wbs-milestones-form]');
        if (!form) return null;
        const second = form.querySelectorAll('[data-wbs-milestone-row]')[1];
        const id = second?.querySelector('[name="milestone_id"]');
        if (!id) return null;
        id.value = "M-1";
        id.dispatchEvent(new Event("input", { bubbles: true }));
        form.requestSubmit();
        return { id: id.value, valid: form.checkValidity() };
      })()`);
      await sleep(700);
      const duplicateError = await page.evaluate(`document.querySelector('${milestonesPanel} [data-wbs-milestone-error]')?.textContent?.trim() ?? ""`);
      check(
        "wbs2-duplicate-guard",
        "a duplicate milestone ID is explained in the editor and no milestone write is sent",
        duplicate?.id === "M-1" && duplicate?.valid === true && duplicateError.length > 0 &&
          writes.length === writesBefore,
        { error: duplicateError, writesAdded: writes.length - writesBefore },
      );

      const zero = await page.evaluate(`(() => {
        const form = document.querySelector('${milestonesPanel} [data-wbs-milestones-form]');
        if (!form) return null;
        const rows = form.querySelectorAll('[data-wbs-milestone-row]');
        const id = rows[1]?.querySelector('[name="milestone_id"]');
        const weight = rows[0]?.querySelector('[name="milestone_weight"]');
        if (!id || !weight) return null;
        id.value = "M-2";
        id.dispatchEvent(new Event("input", { bubbles: true }));
        weight.value = "0";
        weight.dispatchEvent(new Event("input", { bubbles: true }));
        form.requestSubmit();
        return { weight: weight.value, valid: form.checkValidity() };
      })()`);
      await sleep(700);
      check(
        "wbs2-weight-guard",
        "a zero weight is blocked by the field constraints and no milestone write is sent",
        zero?.weight === "0" && zero?.valid === false && writes.length === writesBefore,
        { zero, writesAdded: writes.length - writesBefore },
      );
      await capture(page, "06-wbs-milestone-validation");
      return { duplicateError, zero };
    });

    await scenario("08", "Persian RTL shows the milestone editor and status without page overflow", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await setLanguage(page, "fa");
      await openWbs(page);
      await selectNode(page, WBS_ID);
      const general = await page.evaluate(generalPanelText);
      await openTab(page, "milestones");
      const state = await page.evaluate(`(() => ({
        dir: document.documentElement.dir,
        lang: document.documentElement.lang,
        overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        rows: document.querySelectorAll('${milestonesPanel} [data-wbs-milestone-row]').length,
        rollup: document.querySelector('${milestonesPanel} [data-wbs-milestone-rollup]')?.textContent?.trim() ?? "",
        general: ${JSON.stringify(general)},
      }))()`);
      check(
        "wbs2-fa-rtl",
        "the Persian WBS status and milestones are right-to-left",
        state.dir === "rtl" && state.lang === "fa",
        { dir: state.dir, lang: state.lang },
      );
      check(
        "wbs2-fa-localized",
        "the Persian details show the localized status labels",
        state.general.includes("وضعیت") && state.general.includes("روش درصد تکمیل"),
        state.general.slice(0, 240),
      );
      check(
        "wbs2-fa-rows",
        "the persisted milestones and roll-up are visible in Persian",
        state.rows === 4 && state.rollup === "83.33%",
        { rows: state.rows, rollup: state.rollup },
      );
      check("wbs2-fa-no-overflow", "the page does not overflow horizontally", state.overflow <= 0, state.overflow);
      await capture(page, "07-wbs-milestones-fa-rtl");
      return state;
    });

    await scenario("09", "A reload restores the persisted status, technique and milestones", async () => {
      await setLanguage(page, "en");
      await reloadWorkspace(page);
      const general = await page.evaluate(generalPanelText);
      check(
        "wbs2-reload-general",
        "the reloaded General tab still shows Active and WBS Milestones",
        general.includes("Active") && general.includes("WBS Milestones"),
        general.slice(0, 240),
      );
      await openTab(page, "milestones");
      const state = await milestoneState(page);
      check(
        "wbs2-reload-milestones",
        "the reloaded milestone editor lists all four persisted milestones at 83.33%",
        state.rows.length === 4 && state.rollup === "83.33%" &&
          state.rows.filter((row) => row.completed).length === 2,
        state,
      );
      await capture(page, "08-wbs-reloaded");
      return state;
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
  log(`\n${checks.length - failed.length} of ${checks.length} WBS-002 checks passed`);
  if (failed.length || summary.error) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  log(`UNHANDLED: ${error?.stack ?? error}`);
  process.exitCode = 1;
});
