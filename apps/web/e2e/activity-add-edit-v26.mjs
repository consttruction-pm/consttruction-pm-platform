#!/usr/bin/env node
/**
 * Browser E2E for adding and editing an activity from the Activities window.
 *
 * Proves against the real preview runtime that:
 *   - the Add activity command opens the tools drawer on the create form with a
 *     suggested activity ID and the project's WBS options, and opening it writes
 *     nothing;
 *   - submitting the form creates the activity through the real
 *     p6-activity-master-api POST; the grid row and a fresh read agree on ID,
 *     name, duration and WBS;
 *   - a duplicate activity ID is refused with a visible error, the grid keeps a
 *     single row and the stored record is unchanged;
 *   - the row Edit command loads the stored record into an inline form with the
 *     stored name, duration, unit and WBS;
 *   - saving the form PATCHes with the stored expected revision, the grid shows
 *     the new name and duration and a fresh read confirms them with a bumped
 *     record revision;
 *   - a form opened before a concurrent write is refused with REVISION_CONFLICT
 *     and never overwrites the newer stored value;
 *   - changing the WBS in the edit form moves the activity to the new element;
 *   - the drawer and the inline editor render in fa/RTL at 1280×720 and en/LTR
 *     at 1920×1080 without page overflow;
 *   - the whole run issues no unexpected exception, console error or 5xx.
 *
 * Help topics: add_activities_in_the_activity_table.htm,
 * change_activity_information_in_the_activity_table.htm,
 * define_general_activity_information.htm.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4247 node e2e/activity-add-edit-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4247";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-27";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "activity-add-edit-v26");
const evidenceDir = join(
  artifactsDir,
  "..",
  "..",
  "..",
  "..",
  "docs",
  "workspace",
  "evidence",
  `activity-add-edit-v26-${evidenceDate}`,
);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const stamp = Date.now().toString(36).toUpperCase();
const NEW_ID = `E2E-AE-${stamp}`;
const DUPLICATE_ID = NEW_ID;

const exceptions = [];
const consoleErrors = [];
const designedConsoleErrors = [];
const apiFailures = [];
const apiWrites = [];
const scenarios = [];
const screenshots = [];

const log = (message) => process.stdout.write(`${message}\n`);

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

function record(id, name, status, details = {}) {
  scenarios.push({ ...details, id, name, status, at: new Date().toISOString() });
  log(`  ${status.toUpperCase()} ${id}. ${name}`);
}

async function scenario(id, name, body) {
  log(`[${id}] ${name}`);
  try {
    const details = await body();
    record(id, name, "pass", details ?? {});
  } catch (error) {
    record(id, name, "fail", { error: error instanceof Error ? error.message : String(error) });
    throw error;
  }
}

async function capture(page, name) {
  const file = `activity-add-edit-v26/${name}.png`;
  await page.screenshot(file);
  copyFileSync(join(artifactsDir, file), join(evidenceDir, `${name}.png`));
  screenshots.push(`${name}.png`);
  return file;
}

async function setViewport(page, width, height) {
  await page.cdp.send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
  await sleep(400);
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
  await sleep(1000);
}

function readCounts(page) {
  return page.evaluate(`(() => {
    const counts = document.querySelector("[data-activity-counts]");
    return counts ? {
      total: Number(counts.getAttribute("data-count-total") ?? -1),
      filter: Number(counts.getAttribute("data-count-filter") ?? -1),
      visible: Number(counts.getAttribute("data-count-visible") ?? -1),
    } : null;
  })()`);
}

async function apiActivity(page, activityId) {
  return page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${PROJECT}/p6/activities/" + encodeURIComponent(${JSON.stringify(activityId)}));
    let body = null;
    try { body = await response.json(); } catch (error) { body = null; }
    return { status: response.status, body };
  })()`, { awaitPromise: true });
}

async function waitForApiActivity(page, activityId) {
  const deadline = Date.now() + 20000;
  while (Date.now() < deadline) {
    const result = await apiActivity(page, activityId);
    if (result.status === 200 && result.body?.activity) return result.body.activity;
    await sleep(200);
  }
  throw new Error(`activity ${activityId} never appeared in the read API`);
}

async function gridRow(page, activityId) {
  return page.evaluate(`(() => {
    const row = document.querySelector('#cp-activity-grid tbody tr[data-activity-id=' + JSON.stringify(${JSON.stringify(activityId)}) + ']');
    if (!row) return null;
    return {
      text: row.textContent.replace(/\\s+/g, " ").trim(),
      wbsLevel: row.getAttribute("data-wbs-level"),
      kind: row.getAttribute("data-activity-kind"),
      rows: document.querySelectorAll('#cp-activity-grid tbody tr[data-activity-id]').length,
    };
  })()`);
}

async function waitForGridRow(page, activityId) {
  const deadline = Date.now() + 20000;
  while (Date.now() < deadline) {
    const row = await gridRow(page, activityId);
    if (row) return row;
    await sleep(200);
  }
  throw new Error(`grid row ${activityId} never appeared`);
}

async function scrollIntoView(page, selector) {
  await page.evaluate(`(() => {
    const element = document.querySelector(${JSON.stringify(selector)});
    if (!element) return false;
    element.scrollIntoView({ block: "center", inline: "nearest" });
    return true;
  })()`);
  await sleep(350);
}

async function openCreateDrawer(page) {
  await page.click("#cp-activity-grid [data-activity-create-open]");
  await page.waitFor(
    `(() => {
      const drawer = document.querySelector("[data-tools-drawer]");
      const form = document.querySelector("[data-activity-create-form]");
      if (!drawer || !form) return false;
      return !drawer.hidden && form.getClientRects().length > 0;
    })()`,
    "activity create drawer",
  );
  await sleep(250);
}

function createFormState(page) {
  return page.evaluate(`(() => {
    const form = document.querySelector("[data-activity-create-form]");
    if (!form) return null;
    const suggestion = form.querySelector("input[name='activity_id']")?.value ?? "";
    const wbs = form.querySelector("select[name='wbs_id']");
    const options = wbs ? [...wbs.options].map((option) => ({ value: option.value, label: option.textContent.trim() })) : [];
    const visible = form.getClientRects().length > 0;
    return {
      suggestion,
      suggestionHint: form.querySelector("[data-activity-id-suggestion]")?.textContent?.trim() ?? null,
      wbsOptions: options,
      wbsSelected: wbs?.value ?? null,
      disabled: wbs?.disabled ?? true,
      visible,
      heading: form.querySelector("h3")?.textContent?.trim() ?? null,
      direction: getComputedStyle(form).direction,
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    };
  })()`);
}

async function submitCreate(page) {
  await page.evaluate(`(() => {
    const form = document.querySelector("[data-activity-create-form]");
    if (!form) return false;
    form.requestSubmit();
    return true;
  })()`);
  await sleep(600);
}

async function openEditForm(page, activityId) {
  await page.click(`[data-activity-edit="${activityId}"]`);
  await page.waitFor(
    `Boolean(document.querySelector('[data-activity-update-form="${activityId}"]'))`,
    `inline editor for ${activityId}`,
  );
  await sleep(300);
}

function editFormState(page, activityId) {
  return page.evaluate(`(() => {
    const form = document.querySelector('[data-activity-update-form="${activityId}"]');
    if (!form) return null;
    return {
      name: form.querySelector("input[name='name']")?.value ?? null,
      duration: form.querySelector("input[name='duration_value']")?.value ?? null,
      unit: form.querySelector("select[name='duration_unit']")?.value ?? null,
      wbs: form.querySelector("select[name='wbs_id']")?.value ?? null,
      durationType: form.querySelector("select[name='duration_type']")?.value ?? null,
      heading: form.querySelector("h3")?.textContent?.trim() ?? null,
      wbsOptions: [...(form.querySelector("select[name='wbs_id']")?.options ?? [])].map((option) => option.value),
      direction: getComputedStyle(form).direction,
      overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      error: form.querySelector("[data-activity-error]")?.textContent?.trim() ?? null,
    };
  })()`);
}

async function submitEdit(page, activityId) {
  await page.evaluate(`(() => {
    const form = document.querySelector('[data-activity-update-form="${activityId}"]');
    if (!form) return false;
    form.requestSubmit();
    return true;
  })()`);
  await sleep(600);
}

async function waitForEditFormGone(page, activityId) {
  await page.waitFor(
    `!document.querySelector('[data-activity-update-form="${activityId}"]')`,
    `inline editor for ${activityId} to close`,
  );
}

async function main() {
  const health = await waitForHttp(`${baseUrl}/preview/health`, 30000);
  if (!(health.status === "ok" || health.status === 200)) throw new Error(`preview health ${health.status}`);
  const chrome = await launchChrome();
  const page = new Page(chrome.cdp);
  await page.initialize();
  page.cdp.on("Runtime.exceptionThrown", (params) => {
    exceptions.push(params.exceptionDetails?.exception?.description ?? params.exceptionDetails?.text ?? "exception");
  });
  page.cdp.on("Runtime.consoleAPICalled", (params) => {
    if (params.type !== "error") return;
    const text = (params.args ?? []).map((arg) => arg.value ?? arg.description ?? arg.type).join(" ");
    // A duplicate-ID create is a designed rejection; the UI logs it before it
    // renders the visible error notice, so it is classified, not hidden.
    if (text.startsWith("Activity creation failed")) designedConsoleErrors.push(text);
    else consoleErrors.push(text);
  });
  page.cdp.on("Network.responseReceived", (params) => {
    const url = params.response?.url ?? "";
    if (url.includes("/api/") && params.response.status >= 500) apiFailures.push({ status: params.response.status, url });
  });
  page.cdp.on("Network.requestWillBeSent", (params) => {
    if (params.request.method === "GET" || params.request.method === "OPTIONS") return;
    if (!params.request.url.includes("/api/")) return;
    apiWrites.push({ method: params.request.method, url: params.request.url });
  });

  const report = {
    contract: "cubi-activity-add-edit-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    helpTopics: [
      "https://docs.oracle.com/cd/G48902_01/client_help/en_US/add_activities_in_the_activity_table.htm",
      "https://docs.oracle.com/cd/G48902_01/client_help/en_US/change_activity_information_in_the_activity_table.htm",
      "https://docs.oracle.com/cd/G48902_01/client_help/en_US/define_general_activity_information.htm",
    ],
    activityId: NEW_ID,
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    designedConsoleErrors,
    apiFailures,
    writes: apiWrites,
  };

  function writeReport() {
    report.scenarios = scenarios;
    report.passed = scenarios.filter((entry) => entry.status === "pass").length;
    report.failed = scenarios.filter((entry) => entry.status === "fail").length;
    const json = JSON.stringify(report, null, 2);
    writeFileSync(join(outDir, "activity-add-edit-v26.json"), json);
    writeFileSync(join(evidenceDir, "activity-add-edit-v26.json"), json);
  }

  try {
    await setViewport(page, 1440, 900);
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
    await sleep(700);
    const hasPersonas = await page.evaluate('Boolean(document.querySelector(".persona"))');
    if (!hasPersonas) {
      await page.evaluate('fetch("/preview/logout", { method: "POST", redirect: "manual" }).then((response) => response.status)', { awaitPromise: true });
      await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, ".persona", "persona cards after sign out");
    }
    const plannerClicked = await page.evaluate(`(() => {
      const button = [...document.querySelectorAll("form button")].find((item) => (item.textContent || "").trim().startsWith("Planner"));
      if (!button) return false;
      button.click();
      return true;
    })()`);
    assert(plannerClicked, "Planner login button is missing");
    await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
    await page.click('[data-project-id="preview-rps-01"]');
    await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
    await sleep(1500);

    let initialCounts = null;
    let createdRecord = null;
    let newWbsId = null;
    // Opening a project is itself a recorded workspace action (POST /open); the
    // baseline is taken after the grid is loaded so the scenarios only measure
    // activity writes they cause.
    const baselineWrites = apiWrites.length;
    const activityPostCount = () => apiWrites.filter((entry) => entry.method === "POST" && entry.url.includes("/p6/activities")).length;
    const activityPatchCount = () => apiWrites.filter((entry) => entry.method === "PATCH" && entry.url.includes("/p6/activities")).length;

    await scenario("01", "Add activity opens the create drawer with a suggested ID and the WBS options, and writes nothing", async () => {
      initialCounts = await readCounts(page);
      assert(initialCounts && initialCounts.total > 10, "the project has no activity rows");
      assert(apiWrites.length === baselineWrites, `writes before opening the drawer: ${apiWrites.length} (baseline ${baselineWrites})`);
      await openCreateDrawer(page);
      const state = await createFormState(page);
      assert(state, "the create form is missing");
      assert(state.visible, "the create form is not visible after the Add command");
      assert(/^[A-Z0-9-]+$/.test(state.suggestion), `unexpected suggested ID: ${state.suggestion}`);
      assert(state.wbsOptions.length >= 2, `expected at least two WBS options, got ${state.wbsOptions.length}`);
      assert(!state.disabled, "the WBS select is disabled although WBS nodes exist");
      assert(apiWrites.length === baselineWrites, `opening the drawer wrote ${apiWrites.length - baselineWrites} record(s)`);
      await capture(page, "01-add-drawer-en-1440");
      return { suggestion: state.suggestion, suggestionHint: state.suggestionHint, wbsOptions: state.wbsOptions.length };
    });

    await scenario("02", "Submitting the form creates the activity through the real POST and the grid and read API agree", async () => {
      newWbsId = (await createFormState(page)).wbsSelected;
      await page.setInput("[data-activity-create-form] input[name='activity_id']", NEW_ID);
      await page.setInput("[data-activity-create-form] input[name='name']", `E2E added activity ${stamp}`);
      await page.setInput("[data-activity-create-form] input[name='duration_value']", "5");
      await page.setSelect("[data-activity-create-form] select[name='duration_unit']", "working-day");
      await submitCreate(page);
      const row = await waitForGridRow(page, NEW_ID);
      assert(row.text.includes(NEW_ID), `grid row text lacks the ID: ${row.text}`);
      assert(/E2E added activity/.test(row.text), `grid row text lacks the name: ${row.text}`);
      createdRecord = await waitForApiActivity(page, NEW_ID);
      assert(createdRecord.name === `E2E added activity ${stamp}`, `stored name ${createdRecord.name}`);
      assert(Number(createdRecord.duration_value) === 5, `stored duration ${createdRecord.duration_value}`);
      assert(createdRecord.wbs_id === newWbsId, `stored WBS ${createdRecord.wbs_id} != ${newWbsId}`);
      assert(createdRecord.record_revision === 1, `stored revision ${createdRecord.record_revision}`);
      const counts = await readCounts(page);
      assert(counts.total === initialCounts.total + 1, `total ${counts.total} != ${initialCounts.total + 1}`);
      assert(activityPostCount() === 1, `activity POST count ${activityPostCount()}`);
      await scrollIntoView(page, `#cp-activity-grid tbody tr[data-activity-id="${NEW_ID}"]`);
      await capture(page, "02-created-en-1440");
      return { activityId: NEW_ID, wbsId: newWbsId, revision: createdRecord.record_revision, total: counts.total };
    });

    await scenario("03", "A duplicate activity ID is refused with a visible error and no second row", async () => {
      await openCreateDrawer(page);
      const countsBefore = await readCounts(page);
      await page.setInput("[data-activity-create-form] input[name='activity_id']", DUPLICATE_ID);
      await page.setInput("[data-activity-create-form] input[name='name']", "Duplicate attempt");
      await page.setInput("[data-activity-create-form] input[name='duration_value']", "2");
      await submitCreate(page);
      const notice = await page.waitFor(
        `(() => {
          const node = document.querySelector("#cp-activity-grid [data-activity-error]");
          return node && node.textContent.trim() ? node.textContent.trim() : null;
        })()`,
        "duplicate create error notice",
        10000,
      );
      assert(/REVISION_CONFLICT|CONFLICT|EXISTS/.test(notice), `unexpected error notice: ${notice}`);
      const rows = await page.evaluate(`document.querySelectorAll('#cp-activity-grid tbody tr[data-activity-id="${DUPLICATE_ID}"]').length`);
      assert(rows === 1, `duplicate rows: ${rows}`);
      const countsAfter = await readCounts(page);
      assert(countsAfter.total === countsBefore.total, `total changed ${countsBefore.total} -> ${countsAfter.total}`);
      const stored = await apiActivity(page, DUPLICATE_ID);
      assert(stored.body?.activity?.name === `E2E added activity ${stamp}`, `stored name changed to ${stored.body?.activity?.name}`);
      assert(designedConsoleErrors.length >= 1, "the designed create rejection was not logged");
      await capture(page, "03-duplicate-refused-en-1440");
      return { notice, rows, designedConsoleErrors: designedConsoleErrors.length };
    });

    await scenario("04", "The row Edit command loads the stored record into an inline form", async () => {
      // Close the create drawer so the inline editor is the only open surface.
      await page.evaluate(`document.querySelector("[data-tools-close]")?.click()`);
      await sleep(300);
      await openEditForm(page, NEW_ID);
      const state = await editFormState(page, NEW_ID);
      assert(state, "the inline editor is missing");
      assert(state.name === `E2E added activity ${stamp}`, `prefilled name ${state.name}`);
      assert(Number(state.duration) === 5, `prefilled duration ${state.duration}`);
      assert(state.unit === "working-day", `prefilled unit ${state.unit}`);
      assert(state.wbs === newWbsId, `prefilled WBS ${state.wbs}`);
      assert(state.wbsOptions.length >= 2, "the edit form lost the WBS options");
      await scrollIntoView(page, `[data-activity-update-form="${NEW_ID}"]`);
      await capture(page, "04-edit-form-en-1440");
      return { name: state.name, duration: state.duration, wbs: state.wbs };
    });

    await scenario("05", "Saving the edit form PATCHes with the stored revision and the grid and read API agree", async () => {
      const updatedName = `E2E edited activity ${stamp}`;
      await page.setInput(`[data-activity-update-form="${NEW_ID}"] input[name='name']`, updatedName);
      await page.setInput(`[data-activity-update-form="${NEW_ID}"] input[name='duration_value']`, "7");
      await submitEdit(page, NEW_ID);
      await waitForEditFormGone(page, NEW_ID);
      await page.waitFor(
        `(() => {
          const row = document.querySelector('#cp-activity-grid tbody tr[data-activity-id="${NEW_ID}"]');
          return Boolean(row && row.textContent.includes(${JSON.stringify(updatedName)}));
        })()`,
        "grid row with the edited name",
      );
      const record = await waitForApiActivity(page, NEW_ID);
      assert(record.name === updatedName, `stored name ${record.name}`);
      assert(Number(record.duration_value) === 7, `stored duration ${record.duration_value}`);
      assert(record.record_revision === 2, `stored revision ${record.record_revision}`);
      assert(activityPatchCount() === 1, `activity PATCH count ${activityPatchCount()}`);
      await scrollIntoView(page, `#cp-activity-grid tbody tr[data-activity-id="${NEW_ID}"]`);
      await capture(page, "05-edit-saved-en-1440");
      return { name: record.name, duration: record.duration_value, revision: record.record_revision };
    });

    await scenario("06", "A form opened before a concurrent write is refused and never overwrites the newer value", async () => {
      const current = await waitForApiActivity(page, NEW_ID);
      await openEditForm(page, NEW_ID);
      // Simulate a concurrent edit that lands after the form captured its revision.
      const serverName = `E2E server value ${stamp}`;
      const concurrent = await page.evaluate(`(async () => {
        const response = await fetch("/api/projects/${PROJECT}/p6/activities/" + encodeURIComponent(${JSON.stringify(NEW_ID)}), {
          method: "PATCH",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            contract_version: "p6-activity-master-api.v1",
            expected_revision: ${current.record_revision},
            name: ${JSON.stringify(serverName)},
            duration_value: 7,
            duration_unit: "working-day",
            wbs_id: ${JSON.stringify(current.wbs_id)},
            duration_type: "Fixed Duration & Units",
            cost_account_id: null,
          }),
        });
        let body = null;
        try { body = await response.json(); } catch (error) { body = null; }
        return { status: response.status, body };
      })()`, { awaitPromise: true });
      assert(concurrent.status === 200, `concurrent PATCH ${concurrent.status}`);
      await sleep(300);
      await page.setInput(`[data-activity-update-form="${NEW_ID}"] input[name='name']`, `E2E stale value ${stamp}`);
      await submitEdit(page, NEW_ID);
      const notice = await page.waitFor(
        `(() => {
          const form = document.querySelector('[data-activity-update-form="${NEW_ID}"]');
          const node = form?.querySelector("[data-activity-error]");
          return node && node.textContent.trim() ? node.textContent.trim() : null;
        })()`,
        "stale edit error notice",
        10000,
      );
      assert(/REVISION_CONFLICT|CONFLICT/.test(notice), `unexpected stale notice: ${notice}`);
      const stored = await waitForApiActivity(page, NEW_ID);
      assert(stored.name === serverName, `stored name ${stored.name} != ${serverName}`);
      assert(stored.record_revision === current.record_revision + 1, `stored revision ${stored.record_revision}`);
      await scrollIntoView(page, `[data-activity-update-form="${NEW_ID}"]`);
      await capture(page, "06-stale-refused-en-1440");
      return { notice, storedName: stored.name, revision: stored.record_revision };
    });

    await scenario("07", "Changing the WBS in the edit form moves the activity to the new element", async () => {
      const current = await waitForApiActivity(page, NEW_ID);
      await openEditForm(page, NEW_ID);
      const state = await editFormState(page, NEW_ID);
      const target = state.wbsOptions.find((value) => value !== current.wbs_id);
      assert(target, "no alternative WBS option to move to");
      await page.setSelect(`[data-activity-update-form="${NEW_ID}"] select[name='wbs_id']`, target);
      await submitEdit(page, NEW_ID);
      await waitForEditFormGone(page, NEW_ID);
      const moved = await waitForApiActivity(page, NEW_ID);
      assert(moved.wbs_id === target, `stored WBS ${moved.wbs_id} != ${target}`);
      assert(moved.name === current.name, `name changed during the move: ${moved.name}`);
      const row = await waitForGridRow(page, NEW_ID);
      assert(row.text.includes(NEW_ID), `grid row lost the ID after the move: ${row.text}`);
      await scrollIntoView(page, `#cp-activity-grid tbody tr[data-activity-id="${NEW_ID}"]`);
      await capture(page, "07-wbs-move-en-1440");
      return { from: current.wbs_id, to: moved.wbs_id, revision: moved.record_revision };
    });

    await scenario("08", "Persian RTL at 1280x720 localizes the drawer and the inline editor without overflow", async () => {
      await setViewport(page, 1280, 720);
      await setLanguage(page, "fa");
      await openCreateDrawer(page);
      let form = await createFormState(page);
      assert(form.direction === "rtl", `create form direction ${form.direction}`);
      assert(/افزودن فعالیت/.test(form.heading ?? ""), `Persian create heading ${form.heading}`);
      assert(form.overflow <= 1, `page overflows in fa at 1280: ${form.overflow}`);
      await openEditForm(page, NEW_ID);
      const edit = await editFormState(page, NEW_ID);
      assert(edit.direction === "rtl", `edit form direction ${edit.direction}`);
      assert(/ویرایش فعالیت/.test(edit.heading ?? ""), `Persian edit heading ${edit.heading}`);
      assert(edit.overflow <= 1, `page overflows in fa at 1280: ${edit.overflow}`);
      await scrollIntoView(page, `[data-activity-update-form="${NEW_ID}"]`);
      await capture(page, "08-fa-rtl-1280");
      return { createHeading: form.heading, editHeading: edit.heading };
    });

    await scenario("09", "English at 1920x1080 keeps the drawer and editor usable without overflow", async () => {
      await setViewport(page, 1920, 1080);
      await setLanguage(page, "en");
      await openCreateDrawer(page);
      const form = await createFormState(page);
      assert(form.direction === "ltr", `create form direction ${form.direction}`);
      assert(/Add activity/i.test(form.heading ?? ""), `English create heading ${form.heading}`);
      assert(form.overflow <= 1, `page overflows in en at 1920: ${form.overflow}`);
      await openEditForm(page, NEW_ID);
      const edit = await editFormState(page, NEW_ID);
      assert(edit.direction === "ltr", `edit form direction ${edit.direction}`);
      assert(edit.overflow <= 1, `page overflows in en at 1920: ${edit.overflow}`);
      await scrollIntoView(page, `[data-activity-update-form="${NEW_ID}"]`);
      await capture(page, "09-en-1920");
      return { createHeading: form.heading, editHeading: edit.heading };
    });

    assert(exceptions.length === 0, `runtime exceptions: ${exceptions.join(" | ")}`);
    assert(consoleErrors.length === 0, `unexpected console errors: ${consoleErrors.join(" | ")}`);
    assert(apiFailures.length === 0, `API 5xx: ${JSON.stringify(apiFailures)}`);
  } finally {
    writeReport();
    log(`\nActivity add/edit suite: ${scenarios.filter((entry) => entry.status === "pass").length}/${scenarios.length} passed`);
    log(`Evidence: ${evidenceDir}`);
    try { page.cdp.close(); } catch {}
    try { chrome.child?.kill("SIGKILL"); } catch {}
  }

  const failed = scenarios.filter((entry) => entry.status !== "pass").length;
  log(`\n${scenarios.length - failed}/${scenarios.length} scenarios passed`);
  log(`evidence: docs/workspace/evidence/activity-add-edit-v26-${evidenceDate}/activity-add-edit-v26.json`);
  if (failed > 0) process.exitCode = 1;
}

main().catch((error) => {
  process.stderr.write(`${error instanceof Error ? error.stack ?? error.message : String(error)}\n`);
  process.exitCode = 1;
});
