#!/usr/bin/env node
/**
 * Browser E2E for the Version 26 Activities Columns dialog.
 *
 * Proves the real dialog against the Activity Table column contract:
 *   - Available Columns / Selected Options counts come from the registry and
 *     the saved layout, not from a copied DOM list;
 *   - search and subject area filter the available pane; Add all adds only the
 *     listed fields; Add / Remove / Remove all and Move Up/Down edit a draft;
 *   - Edit Column changes title, width and alignment; visibility hides a
 *     column without dropping it from the layout;
 *   - OK persists and reloads, Apply persists without closing, Cancel always
 *     discards the draft and never writes;
 *   - Default reads the server default set into the draft;
 *   - Copy From lists the other saved layout scope and copies its columns;
 *   - a Viewer can inspect but OK/Apply stay disabled and no write is issued;
 *   - a change in one project never alters another project's layout;
 *   - the dialog fits fa/RTL 1280×720 and en/LTR 1920×1080.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4211 node e2e/activity-columns-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4211";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-13";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "activity-columns-v26");
const evidenceDir = join(
  artifactsDir,
  "..",
  "..",
  "..",
  "..",
  "docs",
  "workspace",
  "evidence",
  `activity-columns-v26-${evidenceDate}`,
);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const OTHER_PROJECT = "preview-nse-02";

const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const apiWrites = [];
const scenarios = [];
const screenshots = [];
let trackWrites = false;

function log(message) {
  process.stdout.write(`${message}\n`);
}

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

function record(id, name, status, details = {}) {
  scenarios.push({ ...details, id, name, status, at: new Date().toISOString() });
  log(`  ${status.toUpperCase()} ${id}. ${name}`);
}

async function scenario(id, name, body) {
  log(`\n[${id}] ${name}`);
  try {
    const details = (await body()) ?? {};
    record(id, name, "pass", details);
    return details;
  } catch (error) {
    record(id, name, "fail", { error: String(error && error.stack ? error.stack : error) });
    throw error;
  }
}

async function capture(page, name) {
  const file = `activity-columns-v26/${name}.png`;
  await page.screenshot(file);
  copyFileSync(join(artifactsDir, file), join(evidenceDir, `${name}.png`));
  screenshots.push(`${name}.png`);
  return file;
}

async function openWorkspace(page, roleLabel = "Planner", projectId = PROJECT) {
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "main", "login");
  const hasRoles = await page.evaluate(
    `Boolean(document.querySelector('button[name="role"]'))`,
  );
  if (!hasRoles) {
    await page.evaluate(
      `fetch("/preview/logout", { method: "POST", redirect: "manual" }).then(() => true)`,
      { awaitPromise: true },
    );
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "main", "login after sign out");
    await page.waitForSelector('button[name="role"]', "login role buttons");
  }
  const clicked = await page.evaluate(`(() => {
    const button = [...document.querySelectorAll("form button")].find((item) => (item.textContent || "").trim().startsWith(${JSON.stringify(roleLabel)}));
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `login role ${roleLabel} was not offered`);
  await page.waitForSelector(`[data-project-id="${projectId}"]`, "project selection");
  await page.click(`[data-project-id="${projectId}"]`);
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
  await sleep(1400);
}

async function openColumns(page) {
  await page.evaluate(`(() => {
    const trigger = document.querySelector('[data-desktop-menu="view"]');
    if (!trigger) return false;
    trigger.click();
    return true;
  })()`);
  await sleep(250);
  const clicked = await page.evaluate(`(() => {
    const item = document.querySelector('[data-desktop-item="view.fields"]');
    if (!item || item.disabled) return false;
    item.click();
    return true;
  })()`);
  assert(clicked, "View > Columns… is missing or disabled");
  await page.waitForSelector("[data-p6-columns-dialog][open]", "Columns dialog");
  await sleep(300);
}

async function closeColumns(page, how = "cancel") {
  const selector = how === "ok" ? "[data-columns-ok]" : how === "apply" ? "[data-columns-apply]" : "[data-columns-cancel]";
  await page.evaluate(`(() => { const button = document.querySelector('${selector}'); if (button) button.click(); return true; })()`);
  if (how !== "apply") {
    await page.waitFor(
      `(() => !document.querySelector("[data-p6-columns-dialog][open]"))`,
      "Columns dialog closed",
      5000,
    );
    await sleep(900);
  }
}

async function readLayout(page, projectId = PROJECT, scope = "project") {
  return page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${projectId}/p6/layouts/${scope}/activity");
    let body = null;
    try { body = await response.json(); } catch {}
    return { status: response.status, body };
  })()`, { awaitPromise: true });
}

async function readRegistry(page, projectId = PROJECT) {
  return page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${projectId}/p6/fields/p6-field-registry.v1");
    const body = await response.json();
    return { status: response.status, body };
  })()`, { awaitPromise: true });
}

async function readDefaults(page, projectId = PROJECT) {
  return page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${projectId}/p6/layouts/project/activity/default");
    let body = null;
    try { body = await response.json(); } catch {}
    return { status: response.status, body };
  })()`, { awaitPromise: true });
}

const dialogState = `(() => {
  const dialog = document.querySelector("[data-p6-columns-dialog][open]");
  if (!dialog) return null;
  const value = (selector) => dialog.querySelector(selector)?.textContent?.trim() ?? null;
  return {
    available: [...dialog.querySelectorAll("[data-columns-available-id]")].map((item) => item.dataset.columnsAvailableId),
    selected: [...dialog.querySelectorAll("[data-columns-selected-id]")].map((item) => item.dataset.columnsSelectedId),
    selectedText: [...dialog.querySelectorAll("[data-columns-selected-id]")].map((item) => item.textContent.trim()),
    availableText: [...dialog.querySelectorAll("[data-columns-available-id]")].map((item) => item.textContent.trim()),
    subjects: [...dialog.querySelectorAll("[data-columns-subject] option")].map((item) => item.value),
    readonly: value("[data-columns-readonly]"),
    notice: value("[data-columns-notice]"),
    okDisabled: Boolean(dialog.querySelector("[data-columns-ok]")?.disabled),
    applyDisabled: Boolean(dialog.querySelector("[data-columns-apply]")?.disabled),
    copyDisabled: Boolean(dialog.querySelector('[data-columns-action="copy-from"]')?.disabled),
    removeDisabled: Boolean(dialog.querySelector('[data-columns-action="remove"]')?.disabled),
    removeAllDisabled: Boolean(dialog.querySelector('[data-columns-action="remove-all"]')?.disabled),
    moveUpDisabled: Boolean(dialog.querySelector('[data-columns-action="move-up"]')?.disabled),
    moveDownDisabled: Boolean(dialog.querySelector('[data-columns-action="move-down"]')?.disabled),
    advanced: [
      Boolean(dialog.querySelector(".cp-columns-readonly")),
      Boolean(dialog.querySelector(".cp-columns-footer")),
    ],
    title: dialog.querySelector("#cp-columns-heading")?.textContent?.trim() ?? null,
    direction: document.documentElement.dir || "ltr",
    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  };
})()`;

const gridState = `(() => ({
  headers: [...document.querySelectorAll("#cp-activity-grid thead th[data-column-id]")].map((th) => ({
    id: th.dataset.columnId,
    label: th.querySelector(".cp-p6-column-label")?.textContent?.trim() ?? th.textContent.trim(),
    width: Math.round(th.getBoundingClientRect().width),
    align: getComputedStyle(th).textAlign,
  })),
  rows: document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]").length,
}))()`;

async function clickInDialog(page, selector) {
  return page.evaluate(`(() => {
    const button = document.querySelector("[data-p6-columns-dialog][open] " + ${JSON.stringify(selector)});
    if (!button || button.disabled) return false;
    button.click();
    return true;
  })()`);
}

async function pickAvailable(page, fieldId) {
  const clicked = await page.evaluate(`(() => {
    const item = document.querySelector('[data-p6-columns-dialog][open] [data-columns-available-id="${fieldId}"]');
    if (!item) return false;
    item.click();
    return true;
  })()`);
  assert(clicked, `available column ${fieldId} not found`);
  await sleep(150);
}

async function pickSelected(page, fieldId) {
  const clicked = await page.evaluate(`(() => {
    const item = document.querySelector('[data-p6-columns-dialog][open] [data-columns-selected-id="${fieldId}"]');
    if (!item) return false;
    item.click();
    return true;
  })()`);
  assert(clicked, `selected column ${fieldId} not found`);
  await sleep(150);
}

async function setSearch(page, value) {
  await page.setInput("[data-p6-columns-dialog][open] [data-columns-search]", value);
  await sleep(250);
}

async function main() {
  await waitForHttp(`${baseUrl}/preview/health`, 30000);
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
    consoleErrors.push((params.args ?? []).map((arg) => arg.value ?? arg.description ?? arg.type).join(" "));
  });
  page.cdp.on("Network.responseReceived", (params) => {
    const url = params.response?.url ?? "";
    if (url.includes("/api/") && params.response.status >= 500) {
      apiFailures.push({ status: params.response.status, url });
    }
  });
  page.cdp.on("Network.requestWillBeSent", (params) => {
    if (!trackWrites || params.request.method === "GET" || params.request.method === "OPTIONS") return;
    if (!params.request.url.includes("/api/")) return;
    apiWrites.push({ method: params.request.method, url: params.request.url });
  });

  const report = {
    contract: "cubi-activity-columns-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
    interactionWrites: apiWrites,
  };

  let initialLayout = null;
  let initialGrid = null;
  let otherProjectBefore = null;
  let editTarget = null;
  let hideTarget = null;

  try {
    trackWrites = true;
    await page.cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1440,
      height: 900,
      deviceScaleFactor: 1,
      mobile: false,
    });
    await sleep(400);

    await scenario("01", "The Columns dialog lists the registry and the saved layout, and filters the available pane", async () => {
      await openWorkspace(page, "Planner");
      const registry = await readRegistry(page);
      assert(registry.status === 200, `registry read ${registry.status}`);
      const fields = registry.body.fields ?? [];
      const layout = await readLayout(page);
      assert(layout.status === 200, `project layout read ${layout.status}`);
      const definition = layout.body.layout ?? layout.body;
      initialLayout = definition;
      initialGrid = await page.evaluate(gridState);
      otherProjectBefore = (await readLayout(page, OTHER_PROJECT)).body;
      editTarget = definition.columns[1]?.field_id ?? definition.columns[0]?.field_id;
      hideTarget = definition.columns[2]?.field_id ?? null;
      assert(editTarget, "the saved layout has no column to edit");
      assert(initialGrid.headers.length === definition.columns.filter((column) => column.visible).length,
        `grid headers ${initialGrid.headers.length} vs visible layout columns ${definition.columns.filter((column) => column.visible).length}`);

      await openColumns(page);
      const state = await page.evaluate(dialogState);
      assert(state, "Columns dialog did not open");
      assert(state.selected.length === definition.columns.length,
        `Selected Options ${state.selected.length} vs layout ${definition.columns.length}`);
      assert(state.available.length === fields.length - definition.columns.length,
        `Available Columns ${state.available.length} vs registry ${fields.length} - layout ${definition.columns.length}`);
      assert(state.subjects.length > 1, "subject area options are missing");
      assert(!state.readonly && !state.okDisabled && !state.applyDisabled, "planner should receive writable actions");
      assert(!state.copyDisabled, "Copy From should be available to query the saved layouts");
      await capture(page, "01-dialog-initial");

      // The seeded project layout already holds every registry field, so the
      // available pane starts empty. Removing two columns is exactly how a user
      // makes fields available again, and it gives the search a real population.
      const removable = definition.columns.slice(0, 2).map((column) => column.field_id);
      assert(removable.length === 2, "the saved layout needs at least two columns for this probe");
      for (const fieldId of removable) {
        await pickSelected(page, fieldId);
        assert(await clickInDialog(page, '[data-columns-action="remove"]'), `Remove is disabled for ${fieldId}`);
        await sleep(200);
      }
      const revealed = await page.evaluate(dialogState);
      assert(revealed.selected.length === definition.columns.length - 2,
        `Remove left ${revealed.selected.length} selected columns`);
      assert(removable.every((id) => revealed.available.includes(id)),
        `removed columns did not return to Available: ${revealed.available.join(",")}`);

      const token = removable[0];
      await setSearch(page, token);
      const filtered = await page.evaluate(dialogState);
      assert(filtered.available.length > 0 && filtered.available.length < revealed.available.length,
        `search did not narrow the list: ${revealed.available.length} -> ${filtered.available.length}`);
      assert(filtered.available.every((id) => id === token),
        `search kept unrelated ids: ${filtered.available.join(",")}`);

      await setSearch(page, "");
      const fieldSubject = new Map(fields.map((field) => [field.field_id, field.subject_area]));
      const subject = fieldSubject.get(removable[0]);
      assert(subject, `no subject for ${removable[0]}`);
      await page.setSelect("[data-p6-columns-dialog][open] [data-columns-subject]", subject);
      await sleep(250);
      const bySubject = await page.evaluate(dialogState);
      assert(bySubject.available.length > 0, `subject ${subject} left no available columns`);
      assert(bySubject.available.every((id) => fieldSubject.get(id) === subject),
        `subject filter returned fields outside ${subject}: ${bySubject.available.join(",")}`);
      await page.setSelect("[data-p6-columns-dialog][open] [data-columns-subject]", "");
      await sleep(150);
      await capture(page, "02-dialog-filtered");

      const copyClicked = await clickInDialog(page, '[data-columns-action="copy-from"]').catch(() => false);
      if (copyClicked) {
        await sleep(500);
        const copyState = await page.evaluate(dialogState);
        assert(copyState.notice && /No other saved activity layout/.test(copyState.notice),
          `Copy From empty state is missing: ${copyState.notice}`);
      }
      await closeColumns(page, "cancel");
      return {
        registryFields: fields.length,
        layoutColumns: definition.columns.length,
        available: state.available.length,
        selected: state.selected.length,
        revealed: revealed.available,
        filtered: filtered.available,
        subjects: state.subjects,
        editTarget,
        hideTarget,
      };
    });

    await scenario("02", "Add, Add all, Remove, Remove all and Move edit only the draft; Cancel writes nothing", async () => {
      const before = await readLayout(page);
      const beforeWrites = apiWrites.length;
      const base = before.body.columns.length;
      await openColumns(page);
      const first = await page.evaluate(dialogState);
      const fieldToAdd = first.selected[0];
      assert(fieldToAdd, "no selected column to remove");

      await pickSelected(page, fieldToAdd);
      assert(await clickInDialog(page, '[data-columns-action="remove"]'), "Remove is disabled");
      await sleep(250);
      let state = await page.evaluate(dialogState);
      assert(!state.selected.includes(fieldToAdd), "Remove kept the field selected");
      assert(state.available.includes(fieldToAdd), "Remove did not return the field to Available");

      await pickAvailable(page, fieldToAdd);
      assert(await clickInDialog(page, '[data-columns-action="add"]'), "Add is disabled");
      await sleep(250);
      state = await page.evaluate(dialogState);
      assert(state.selected.includes(fieldToAdd), "Add did not append the field");
      assert(!state.available.includes(fieldToAdd), "Add left the field in the available pane");
      assert(state.selected.length === base, `Add/Remove did not round-trip: ${state.selected.length} vs ${base}`);

      // Make exactly one field available, filter to it, and prove Add all adds
      // only the listed population.
      const probe = state.selected[0];
      await pickSelected(page, probe);
      assert(await clickInDialog(page, '[data-columns-action="remove"]'), "Remove is disabled");
      await sleep(200);
      await setSearch(page, probe);
      const filteredCount = (await page.evaluate(dialogState)).available.length;
      assert(filteredCount === 1, `filter listed ${filteredCount} available fields, expected 1`);
      assert(await clickInDialog(page, '[data-columns-action="add-all"]'), "Add all is disabled");
      await sleep(250);
      state = await page.evaluate(dialogState);
      assert(state.selected.length === base, `Add all added ${state.selected.length - (base - 1)} fields, expected 1`);
      await setSearch(page, "");

      assert(await clickInDialog(page, '[data-columns-action="remove-all"]'), "Remove all is disabled");
      await sleep(250);
      state = await page.evaluate(dialogState);
      assert(state.selected.length === 1, `Remove all left ${state.selected.length} columns`);
      assert(state.removeDisabled && state.removeAllDisabled, "the last column can still be removed");

      assert(await clickInDialog(page, '[data-columns-action="add-all"]'), "Add all is disabled after remove all");
      await sleep(250);
      state = await page.evaluate(dialogState);
      assert(state.selected.length === first.selected.length, `Add all restored ${state.selected.length} of ${first.selected.length}`);
      await pickSelected(page, state.selected[1] ?? state.selected[0]);
      const beforeMove = (await page.evaluate(dialogState)).selected;
      assert(await clickInDialog(page, '[data-columns-action="move-up"]'), "Move up is disabled");
      await sleep(200);
      const movedUp = (await page.evaluate(dialogState)).selected;
      assert(movedUp[0] === beforeMove[1] && movedUp[1] === beforeMove[0], `move up did not swap: ${beforeMove} -> ${movedUp}`);
      assert(await clickInDialog(page, '[data-columns-action="move-down"]'), "Move down is disabled");
      await sleep(200);
      const movedBack = (await page.evaluate(dialogState)).selected;
      assert(movedBack[0] === beforeMove[0], `move down did not restore: ${movedBack}`);

      await capture(page, "03-draft-transfer");
      await closeColumns(page, "cancel");
      const after = await readLayout(page);
      assert(after.body.revision === before.body.revision, `Cancel wrote layout revision ${after.body.revision} vs ${before.body.revision}`);
      assert(JSON.stringify(after.body.columns) === JSON.stringify(before.body.columns), "Cancel changed the stored columns");
      assert(apiWrites.length === beforeWrites, `Cancel issued writes: ${JSON.stringify(apiWrites.slice(beforeWrites))}`);

      await openColumns(page);
      const reopened = await page.evaluate(dialogState);
      assert(reopened.selected.length === base, "reopening after Cancel did not restore the saved column set");
      await closeColumns(page, "cancel");
      return { removedAndAdded: fieldToAdd, filteredCount, reopened: reopened.selected.length };
    });

    await scenario("03", "Edit Column and visibility persist through OK and a full reload", async () => {
      await openColumns(page);
      await pickSelected(page, editTarget);
      assert(await clickInDialog(page, '[data-columns-action="edit"]'), "Edit Column is disabled");
      await page.waitForSelector("[data-p6-edit-column-dialog][open]", "Edit Column dialog");
      await page.setInput('[data-p6-edit-column-dialog] input[name="title"]', "E2E Column");
      await page.setInput('[data-p6-edit-column-dialog] input[name="width"]', "240");
      await page.setSelect('[data-p6-edit-column-dialog] select[name="alignment"]', "center");
      await page.evaluate(`(() => { document.querySelector("[data-p6-edit-column-dialog] form")?.requestSubmit(); return true; })()`);
      await sleep(400);

      if (hideTarget) {
        assert(await clickInDialog(page, `[data-columns-visibility="${hideTarget}"]`), "visibility toggle is missing");
        await sleep(250);
        const hidden = await page.evaluate(dialogState);
        assert(hidden.selectedText.some((text) => /Hidden/.test(text)), "the hidden badge is missing");
      }
      await capture(page, "04-edit-column");
      await closeColumns(page, "ok");

      const stored = await readLayout(page);
      const target = stored.body.columns.find((column) => column.field_id === editTarget);
      assert(target, "edited column disappeared from the layout");
      assert(target.label === "E2E Column", `stored title ${target.label}`);
      assert(target.width === 240, `stored width ${target.width}`);
      assert(target.alignment === "center", `stored alignment ${target.alignment}`);
      if (hideTarget) {
        const hidden = stored.body.columns.find((column) => column.field_id === hideTarget);
        assert(hidden && hidden.visible === false, "the hidden column was not stored with visible=false");
      }
      const grid = await page.evaluate(gridState);
      const header = grid.headers.find((item) => item.id === editTarget);
      assert(header, "edited column is not in the grid header");
      assert(header.label === "E2E Column", `grid label ${header.label}`);
      assert(header.width >= 230, `grid width ${header.width}`);
      assert(header.align === "center", `grid alignment ${header.align}`);
      if (hideTarget) assert(!grid.headers.some((item) => item.id === hideTarget), "hidden column still renders a header");
      await capture(page, "05-grid-after-ok");

      await page.reload();
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "rows after reload");
      await sleep(1500);
      const reloaded = await page.evaluate(gridState);
      const reloadedHeader = reloaded.headers.find((item) => item.id === editTarget);
      assert(reloadedHeader && reloadedHeader.label === "E2E Column", "title did not survive a reload");
      assert(reloadedHeader.width >= 230 && reloadedHeader.align === "center", "width/alignment did not survive a reload");
      if (hideTarget) assert(!reloaded.headers.some((item) => item.id === hideTarget), "hidden column returned after reload");
      return { target: editTarget, hidden: hideTarget, width: reloadedHeader.width };
    });

    await scenario("04", "Cancel discards later edits even after a persisted change", async () => {
      const before = await readLayout(page);
      const beforeWrites = apiWrites.length;
      await openColumns(page);
      await pickSelected(page, editTarget);
      assert(await clickInDialog(page, '[data-columns-action="move-down"]'), "Move down is disabled");
      await sleep(250);
      if (hideTarget) {
        assert(await clickInDialog(page, `[data-columns-visibility="${hideTarget}"]`), "visibility toggle is missing");
        await sleep(250);
      }
      await closeColumns(page, "cancel");
      const after = await readLayout(page);
      assert(after.body.revision === before.body.revision, "Cancel wrote a layout revision");
      assert(JSON.stringify(after.body.columns) === JSON.stringify(before.body.columns), "Cancel changed the stored columns");
      assert(apiWrites.length === beforeWrites, "Cancel issued a write");
      return { revision: after.body.revision };
    });

    await scenario("05", "Apply persists the order without closing the dialog", async () => {
      const before = await readLayout(page);
      await openColumns(page);
      const first = (await page.evaluate(dialogState)).selected[0];
      await pickSelected(page, first);
      assert(await clickInDialog(page, '[data-columns-action="move-down"]'), "Move down is disabled");
      await sleep(250);
      const draft = (await page.evaluate(dialogState)).selected;
      assert(await clickInDialog(page, '[data-columns-apply]'), "Apply is disabled");
      await page.waitForSelector("[data-p6-columns-dialog][open]", "dialog after Apply");
      await sleep(1200);
      const state = await page.evaluate(dialogState);
      assert(state.notice && /applied/i.test(state.notice), `Apply notice is missing: ${state.notice}`);

      const stored = await readLayout(page);
      assert(stored.body.revision > before.body.revision, `Apply did not persist: ${before.body.revision} -> ${stored.body.revision}`);
      assert(stored.body.columns[0]?.field_id === draft[0], `first stored column ${stored.body.columns[0]?.field_id} vs ${draft[0]}`);
      const grid = await page.evaluate(gridState);
      assert(grid.headers[0]?.id === draft[0], `grid did not follow Apply: ${grid.headers[0]?.id}`);

      const afterApply = await readLayout(page);
      await closeColumns(page, "cancel");
      const afterCancel = await readLayout(page);
      assert(afterCancel.body.revision === afterApply.body.revision, "Cancel after Apply rolled back or wrote again");
      await capture(page, "06-applied-grid");
      return { revision: stored.body.revision, first: stored.body.columns[0]?.field_id };
    });

    await scenario("06", "Default stages the server default columns; only OK persists them", async () => {
      const defaults = await readDefaults(page);
      assert(defaults.status === 200, `default layout read ${defaults.status}`);
      const defaultDefinition = defaults.body.layout ?? defaults.body;
      const before = await readLayout(page);
      const beforeWrites = apiWrites.length;

      await openColumns(page);
      assert(await clickInDialog(page, '[data-columns-action="default"]'), "Default is missing");
      await page.waitFor(
        `(() => {
          const notice = document.querySelector("[data-p6-columns-dialog][open] [data-columns-notice]");
          return notice && notice.textContent.trim() === "";
        })()`,
        "defaults loaded",
        15000,
      );
      await sleep(600);
      const staged = await page.evaluate(dialogState);
      assert(staged.selected.length === defaultDefinition.columns.length,
        `Default staged ${staged.selected.length} columns vs ${defaultDefinition.columns.length}`);
      assert(JSON.stringify(staged.selected) === JSON.stringify(defaultDefinition.columns.map((column) => column.field_id)),
        `Default staged a different column order: ${staged.selected}`);
      await closeColumns(page, "cancel");
      const afterCancel = await readLayout(page);
      assert(JSON.stringify(afterCancel.body.columns) === JSON.stringify(before.body.columns), "Cancel after Default changed the stored columns");
      assert(apiWrites.length === beforeWrites, "Default staged a write before OK");

      await openColumns(page);
      assert(await clickInDialog(page, '[data-columns-action="default"]'), "Default is missing");
      await sleep(1200);
      await capture(page, "07-default-staged");
      await closeColumns(page, "ok");
      const restored = await readLayout(page);
      assert(JSON.stringify(restored.body.columns.map((column) => column.field_id)) === JSON.stringify(defaultDefinition.columns.map((column) => column.field_id)),
        "OK did not persist the server default columns");
      return { columns: restored.body.columns.length, revision: restored.body.revision };
    });

    await scenario("07", "Copy From copies the other saved layout's columns into the draft", async () => {
      const seeded = await page.evaluate(`(async () => {
        const layoutResponse = await fetch("/api/projects/${PROJECT}/p6/layouts/project/activity");
        const layout = await layoutResponse.json();
        const ids = layout.columns.slice(0, 4).map((column) => column.field_id).reverse();
        const byId = new Map(layout.columns.map((column) => [column.field_id, column]));
        const columns = ids.map((id, index) => ({ ...byId.get(id), field_id: id, order: index, label: index === 0 ? "Copied First" : byId.get(id)?.label, visible: true }));
        const response = await fetch("/api/projects/${PROJECT}/p6/layouts/user/activity", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ revision: 0, columns, metadata: { layoutName: "Field team view" } }),
        });
        return { status: response.status, body: await response.text(), ids };
      })()`, { awaitPromise: true });
      assert(seeded.status === 200, `user layout seed failed: ${seeded.status} ${seeded.body}`);
      const sourceDefinition = JSON.parse(seeded.body);

      await openColumns(page);
      const state = await page.evaluate(dialogState);
      assert(!state.copyDisabled, "Copy From stayed disabled with a second saved layout");
      assert(await clickInDialog(page, '[data-columns-action="copy-from"]'), "Copy From is disabled");
      await page.waitForSelector("[data-p6-copy-columns-dialog][open]", "Copy From picker");
      const sources = await page.evaluate(`(() => [...document.querySelectorAll("[data-p6-copy-columns-dialog] input[name=\\"source\\"]")].length)()`);
      assert(sources === 1, `Copy From listed ${sources} sources, expected the user layout only`);
      await page.evaluate(`(() => { document.querySelector("[data-p6-copy-columns-dialog] form")?.requestSubmit(); return true; })()`);
      await page.waitFor(`(() => !document.querySelector("[data-p6-copy-columns-dialog][open]"))`, "Copy From picker closed", 5000);
      await sleep(500);
      const copied = await page.evaluate(dialogState);
      assert(copied.notice && /copied/i.test(copied.notice), `Copy done notice is missing: ${copied.notice}`);
      assert(JSON.stringify(copied.selected) === JSON.stringify(sourceDefinition.columns.map((column) => column.field_id)),
        `copied draft ${copied.selected} vs source ${sourceDefinition.columns.map((column) => column.field_id)}`);
      await capture(page, "08-copy-from");
      await closeColumns(page, "ok");
      const stored = await readLayout(page);
      assert(stored.body.scope === "project", `Copy From changed the scope to ${stored.body.scope}`);
      assert(JSON.stringify(stored.body.columns.map((column) => column.field_id)) === JSON.stringify(sourceDefinition.columns.map((column) => column.field_id)),
        "OK did not persist the copied columns in the project scope");
      const userLayout = await readLayout(page, PROJECT, "user");
      assert(userLayout.body.revision === sourceDefinition.revision, "Copy From modified the source user layout");
      return { sourceColumns: sourceDefinition.columns.length, revision: stored.body.revision, scope: stored.body.scope };
    });

    await scenario("08", "A layout change in one project never reaches another project", async () => {
      const otherNow = (await readLayout(page, OTHER_PROJECT)).body;
      assert(JSON.stringify(otherNow.columns) === JSON.stringify(otherProjectBefore.columns),
        "the other project's columns changed after editing this project");
      assert(otherNow.revision === otherProjectBefore.revision, "the other project's layout revision changed");

      await page.evaluate(`(() => { document.querySelector('[data-menu="project"]')?.click(); return true; })()`);
      await page.waitForSelector(`[data-project-open="${OTHER_PROJECT}"]`, `${OTHER_PROJECT} row`);
      await page.click(`[data-project-open="${OTHER_PROJECT}"]`);
      await page.waitFor(
        `document.querySelector(".cp-workspace")?.dataset.project === ${JSON.stringify(OTHER_PROJECT)}`,
        `${OTHER_PROJECT} workspace`,
        20000,
      );
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "rows in the other project");
      await sleep(1200);
      const otherGrid = await page.evaluate(gridState);
      assert(!otherGrid.headers.some((header) => header.label === "Copied First" || header.label === "E2E Column"),
        `the other project inherited this project's column titles: ${JSON.stringify(otherGrid.headers.map((header) => header.label))}`);
      await capture(page, "09-other-project");

      await page.evaluate(`(() => { document.querySelector('[data-menu="project"]')?.click(); return true; })()`);
      await page.waitForSelector(`[data-project-open="${PROJECT}"]`, `${PROJECT} row`);
      await page.click(`[data-project-open="${PROJECT}"]`);
      await page.waitFor(
        `document.querySelector(".cp-workspace")?.dataset.project === ${JSON.stringify(PROJECT)}`,
        `${PROJECT} workspace`,
        20000,
      );
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "rows back in the first project");
      await sleep(1200);
      const back = await page.evaluate(gridState);
      const stored = await readLayout(page);
      assert(JSON.stringify(back.headers.map((header) => header.id)) === JSON.stringify(stored.body.columns.filter((column) => column.visible).map((column) => column.field_id)),
        "returning to the project did not restore its stored columns");
      return { other: otherNow.columns.length, back: back.headers.length };
    });

    await scenario("09", "A Viewer can inspect columns but cannot save, and issues no write", async () => {
      const before = await readLayout(page);
      await openWorkspace(page, "Viewer");
      const beforeWrites = apiWrites.length;
      await openColumns(page);
      const state = await page.evaluate(dialogState);
      assert(state, "Viewer could not open the Columns dialog");
      assert(state.readonly && /cannot save/i.test(state.readonly), `Viewer read-only reason is missing: ${state.readonly}`);
      assert(state.okDisabled && state.applyDisabled, "Viewer received enabled OK/Apply");
      const available = state.available[0];
      if (available) {
        await pickAvailable(page, available);
        assert(await clickInDialog(page, '[data-columns-action="add"]'), "Viewer could not stage a column");
        await sleep(200);
        assert((await page.evaluate(dialogState)).selected.includes(available), "Viewer draft did not change");
      }
      await capture(page, "10-viewer-readonly");
      await closeColumns(page, "cancel");
      const after = await readLayout(page);
      assert(after.body.revision === before.body.revision, "Viewer Cancel wrote a layout revision");
      assert(apiWrites.length === beforeWrites, `Viewer issued writes: ${JSON.stringify(apiWrites.slice(beforeWrites))}`);
      return { readonly: state.readonly, staged: available };
    });

    await scenario("10", "The dialog fits fa/RTL 1280×720 and en/LTR 1920×1080", async () => {
      await openWorkspace(page, "Planner");
      await page.cdp.send("Emulation.setDeviceMetricsOverride", {
        width: 1280,
        height: 720,
        deviceScaleFactor: 1,
        mobile: false,
      });
      await sleep(300);
      const changed = await page.evaluate(`(() => {
        const select = document.querySelector("[data-workspace-language]");
        if (!select) return false;
        select.value = "fa";
        select.dispatchEvent(new Event("change", { bubbles: true }));
        return select.value === "fa";
      })()`);
      assert(changed, "language selector did not accept fa");
      await sleep(1000);
      await openColumns(page);
      const rtl = await page.evaluate(dialogState);
      assert(rtl, "the dialog did not open in fa");
      assert(rtl.direction === "rtl", `document direction is ${rtl.direction}`);
      assert(/ستون/.test(rtl.title ?? ""), `Persian title is ${rtl.title}`);
      assert(rtl.overflow <= 1, `fa dialog overflows by ${rtl.overflow}px`);
      await capture(page, "11-fa-rtl-1280");
      await closeColumns(page, "cancel");

      await page.evaluate(`(() => {
        const select = document.querySelector("[data-workspace-language]");
        if (!select) return false;
        select.value = "en";
        select.dispatchEvent(new Event("change", { bubbles: true }));
        return true;
      })()`);
      await sleep(900);
      await page.cdp.send("Emulation.setDeviceMetricsOverride", {
        width: 1920,
        height: 1080,
        deviceScaleFactor: 1,
        mobile: false,
      });
      await sleep(300);
      await openColumns(page);
      const ltr = await page.evaluate(dialogState);
      assert(ltr && ltr.direction === "ltr", "the dialog did not return to LTR");
      assert(ltr.overflow <= 1, `en 1920 dialog overflows by ${ltr.overflow}px`);
      await capture(page, "12-en-1920");
      await closeColumns(page, "cancel");
      return { rtl: rtl.title, ltr: ltr.title, overflow: { rtl: rtl.overflow, ltr: ltr.overflow } };
    });

    await scenario("11", "The whole run issued no exception, console error or 5xx", async () => {
      assert(exceptions.length === 0, `page exceptions: ${JSON.stringify(exceptions)}`);
      assert(apiFailures.length === 0, `API failures: ${JSON.stringify(apiFailures)}`);
      assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors)}`);
      return { writes: apiWrites, consoleErrors };
    });

    writeFileSync(join(evidenceDir, "activity-columns-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
    log(`\nActivity Columns suite passed: ${scenarios.length} scenarios`);
    log(`Evidence: ${evidenceDir}`);
  } catch (error) {
    const message = String(error && error.stack ? error.stack : error);
    report.failure = message;
    writeFileSync(join(evidenceDir, "activity-columns-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
    throw error;
  } finally {
    await page.cdp.send("Browser.close").catch(() => {});
    chrome.process?.kill?.();
  }
}

main().catch((error) => {
  process.stderr.write(`${error}\n`);
  process.exitCode = 1;
});
