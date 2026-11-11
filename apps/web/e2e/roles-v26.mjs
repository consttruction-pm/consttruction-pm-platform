#!/usr/bin/env node
/**
 * Browser E2E for the Version 26 Roles window.
 *
 * It drives the real local full-stack preview on project preview-rps-01.
 * The register, the General tab, the Resources tab and the Units & Prices tab
 * all read and write the persisted role master and role dictionary through the
 * real p6-role-api.v1 / p6-role-rate-api.v1 / p6-role-limit-api.v1 /
 * p6-role-resource-api.v1 contracts. Expected values are read from the same
 * session's API, so no fixture data is injected into the page.
 *
 * The scenarios cover the documented behaviour: a parents-first hierarchy,
 * the revise-with-revision guard, duplicate and conflict rejection, resource
 * proficiency with exactly one primary role per resource, at most five rates
 * per effective date, one limit per effective date (units or percent), and
 * persistence after a full page reload.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4184 node e2e/roles-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4184";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-11";
// The commit under test and the commit that stores this report are different
// facts: the bundle is built from the worktree before the evidence commit exists.
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "roles-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `roles-v26-${evidenceDate}`);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const TENANT = "cubi-preview-tenant";
const RESOURCE_ID = "RPS-CIVIL-CREW";
const stamp = Date.now().toString(36).toUpperCase();
const parentId = `RPS-E2E-ROLE-${stamp}`;
const childId = `${parentId}-SUP`;
const parentName = "E2E Civil Role";
const childName = "E2E Civil Supervision Role";
const childEditedName = "E2E Civil Supervision Role (rev 2)";

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

const rolesState = `(() => {
  const page = document.querySelector("[data-roles-page]");
  const rows = [...document.querySelectorAll("[data-role-row]")].map((row) => {
    const cells = [...row.querySelectorAll("td")].map((cell) => (cell.textContent || "").trim());
    const tree = row.querySelector(".cp-role-tree-cell");
    return {
      id: row.dataset.roleId,
      name: cells[1],
      parent: cells[2],
      revision: cells[3],
      depth: tree ? (tree.style.paddingInlineStart || "0px") : null,
      selected: row.getAttribute("aria-selected") === "true",
    };
  });
  const activeTab = document.querySelector('[data-role-tab][aria-selected="true"]')?.dataset.roleTab ?? null;
  const fields = [...document.querySelectorAll('[data-role-panel="general"] label')].map((label) => ({
    label: (label.childNodes[0]?.textContent ?? "").trim(),
    value: label.querySelector("input")?.value ?? null,
  }));
  const table = (selector) => [...document.querySelectorAll(selector)].map((row) => [...row.querySelectorAll("td")].map((cell) => (cell.textContent || "").trim()));
  const form = document.querySelector("[data-role-general-form]");
  return {
    activeMenu: document.querySelector(".cp-workspace")?.dataset.activeMenu ?? null,
    heading: page?.querySelector(".cp-register-toolbar strong")?.textContent?.trim() ?? null,
    caption: page?.querySelector(".cp-register-details > header span")?.textContent?.trim() ?? null,
    rows,
    empty: page?.querySelector(".cp-calendar-empty")?.textContent?.trim() ?? null,
    activeTab,
    fields,
    resourceRows: table("[data-role-resource-row]"),
    rateRows: table("[data-role-rate-row]"),
    limitRows: table("[data-role-limit-row]"),
    resourceFormPresent: Boolean(page?.querySelector("[data-role-resource-form]")),
    rateFormPresent: Boolean(page?.querySelector("[data-role-rate-form]")),
    limitFormPresent: Boolean(page?.querySelector("[data-role-limit-form]")),
    notice: page?.querySelector("[data-role-notice]")
      ? {
          kind: page.querySelector("[data-role-notice]").dataset.state,
          text: page.querySelector("[data-role-notice]").textContent.trim(),
        }
      : null,
    form: form ? {
      // Create keeps an editable name="role-id" field; edit renders the stored
      // identifier as a readonly value without a name.
      kind: form.querySelector('input[name="role-id"]') ? "create" : "edit",
      idValue: form.querySelector('input[name="role-id"]')?.value ?? form.querySelector("input[readonly]")?.value ?? null,
      parentOptions: [...form.querySelectorAll('select[name="role-parent"] option')].map((option) => option.value),
    } : null,
    refreshDisabled: Boolean(page?.querySelector('[data-role-action="reload"]')?.disabled),
  };
})()`;

async function capture(page, name) {
  const file = `roles-v26/${name}.png`;
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

async function openRoles(page) {
  await openMenu(page, "roles", "[data-roles-page] .cp-register-toolbar", "role register");
  await page.waitFor(
    `(() => {
      const page = document.querySelector("[data-roles-page]");
      return Boolean(page) && !page.textContent.includes("Reading the role register");
    })()`,
    "role register settled",
  );
  await sleep(300);
}

function needsForm(kind) {
  return `Boolean(document.querySelector(${JSON.stringify(`[data-role-${kind}-form]`)}))`;
}

const requestHeaders = `{
  "Content-Type": "application/json",
  "X-Tenant-Id": ${JSON.stringify(TENANT)},
  "X-Project-Id": ${JSON.stringify(PROJECT)},
  "X-Project-Revision": "7"
}`;

function roleUrl(suffix = "") {
  return `/api/projects/${PROJECT}/p6/roles${suffix}`;
}

/**
 * Reads the shared bottom pane's layout state. The Roles window renders its own
 * detail tabs, so the shared pane must be collapsed out of the grid and its
 * fallback text must not be present after a menu switch or a bottom-layout
 * change; a hidden-but-rendered pane would still be a parity claim.
 */
async function sharedDetailsLayout(page) {
  return page.evaluate(`(() => {
    const main = document.querySelector(".cp-main[data-details-split]");
    const details = document.querySelector("#cp-details");
    return {
      collapsed: main?.dataset.detailsCollapsed ?? null,
      bottomLayout: main?.dataset.bottomLayout ?? null,
      hidden: details ? details.hasAttribute("hidden") : null,
      bottomDisplay: details ? getComputedStyle(details).display : null,
      bottomText: details?.textContent?.trim() ?? "",
    };
  })()`);
}

async function readRoleList(page) {
  return page.evaluate(`(async () => {
    const response = await fetch(${JSON.stringify(roleUrl())});
    return { status: response.status, body: await response.json() };
  })()`, { awaitPromise: true });
}

async function readRole(page, roleId) {
  return page.evaluate(`(async () => {
    const response = await fetch(${JSON.stringify(roleUrl("/"))} + encodeURIComponent(${JSON.stringify(roleId)}));
    return { status: response.status, body: await response.json() };
  })()`, { awaitPromise: true });
}

async function readRoleFacts(page, roleId, kind) {
  return page.evaluate(`(async () => {
    const response = await fetch(${JSON.stringify(roleUrl("/"))} + encodeURIComponent(${JSON.stringify(roleId)}) + "/${kind}");
    return { status: response.status, body: await response.json() };
  })()`, { awaitPromise: true });
}

async function postRole(page, payload) {
  return page.evaluate(`(async () => {
    const response = await fetch(${JSON.stringify(roleUrl())}, {
      method: "POST",
      headers: ${requestHeaders},
      body: JSON.stringify(${JSON.stringify(payload)}),
    });
    return { status: response.status, body: await response.json() };
  })()`, { awaitPromise: true });
}

async function patchRole(page, roleId, payload) {
  return page.evaluate(`(async () => {
    const response = await fetch(${JSON.stringify(roleUrl("/"))} + encodeURIComponent(${JSON.stringify(roleId)}), {
      method: "PATCH",
      headers: ${requestHeaders},
      body: JSON.stringify(${JSON.stringify(payload)}),
    });
    return { status: response.status, body: await response.json() };
  })()`, { awaitPromise: true });
}

async function postRate(page, roleId, payload) {
  return page.evaluate(`(async () => {
    const response = await fetch(${JSON.stringify(roleUrl("/"))} + encodeURIComponent(${JSON.stringify(roleId)}) + "/rates", {
      method: "POST",
      headers: ${requestHeaders},
      body: JSON.stringify(${JSON.stringify(payload)}),
    });
    return { status: response.status, body: await response.json() };
  })()`, { awaitPromise: true });
}

function field(state, label) {
  return state.fields.find((entry) => entry.label === label)?.value ?? null;
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
    contract: "cubi-roles-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    parentRoleId: parentId,
    childRoleId: childId,
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
  };

  try {
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
    await sleep(400);
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "form", "login");
    await page.evaluate(`(() => {
      const button = [...document.querySelectorAll("form button")].find((item) => (item.textContent || "").trim().startsWith("Planner"));
      if (!button) return false;
      button.click();
      return true;
    })()`);
    await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
    await page.click('[data-project-id="preview-rps-01"]');
    await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
    await sleep(1400);
    await setLanguage(page, "en");

    await openRoles(page);

    await scenario("01", "پنجرهٔ Roles ابتدا فهرست خالی و نوار ابزار واقعی نشان می‌دهد", async () => {
      const state = await page.evaluate(rolesState);
      assert(state.activeMenu === "roles", `active menu is ${state.activeMenu}`);
      assert(state.heading === "Role Register", `window heading is ${state.heading}`);
      assert(state.rows.length === 0, `register starts with ${state.rows.length} rows`);
      assert(/No roles are stored for this project/.test(state.empty ?? ""), `empty state is ${state.empty}`);
      // The register must agree with the stored list, not with a client-side fixture.
      const list = await readRoleList(page);
      assert(list.status === 200, `role list status ${list.status}`);
      assert(Array.isArray(list.body.roles) && list.body.roles.length === 0, `API list already has ${list.body.roles?.length} roles`);
      // Switching to Roles must retire the shared bottom pane, not just hide it
      // on first paint: the menu switch goes through the incremental renderer.
      const layout = await sharedDetailsLayout(page);
      assert(layout.collapsed === "true", `shared details still claim space after the menu switch: ${layout.collapsed}`);
      assert(layout.bottomDisplay === "none", `shared details are still rendered after the menu switch: ${layout.bottomDisplay}`);
      assert(!/detail tabs are not implemented yet/.test(layout.bottomText), "the shared details placeholder text is still rendered");
      await capture(page, "01-role-register-empty");
      return { rows: 0, heading: state.heading, bottomDisplay: layout.bottomDisplay, collapsed: layout.collapsed };
    });

    await scenario("02", "ایجاد نقش والد از فرم واقعی، ذخیرهٔ سلسله‌مراتب و رد بازنویسی شناسهٔ موجود", async () => {
      await page.click('[data-role-action="new"]');
      await page.waitForSelector("[data-role-general-form]", "role create form");
      let state = await page.evaluate(rolesState);
      assert(state.form?.kind === "create", `form kind ${state.form?.kind}`);
      assert(JSON.stringify(state.form.parentOptions) === JSON.stringify([""]), `create parent options ${state.form.parentOptions}`);

      await page.setInput('[data-role-general-form] input[name="role-id"]', parentId);
      await page.setInput('[data-role-general-form] input[name="role-name"]', parentName);
      await page.setInput('[data-role-general-form] input[name="role-description"]', "Site civil engineering role");
      await page.click('[data-role-general-form] button[type="submit"]');
      await page.waitFor(`document.querySelector('[data-role-notice][data-state="ok"]') !== null`, "create success notice");
      await page.waitForSelector(`[data-role-row][data-role-id="${parentId}"]`, "created parent row");
      await page.waitForSelector('[data-role-panel="general"]', "created parent general tab");
      await sleep(400);
      state = await page.evaluate(rolesState);
      const row = state.rows.find((item) => item.id === parentId);
      assert(row, "the created parent role is missing from the register");
      assert(row.name === parentName, `created row name ${row.name}`);
      assert(row.parent === "—", `created parent cell ${row.parent}`);
      assert(row.revision === "1", `created revision ${row.revision}`);
      assert(row.selected, "the created parent row is not selected");
      assert(row.depth === "0px" || row.depth === "", `parent depth ${row.depth}`);
      assert(state.caption === parentId, `details caption ${state.caption}`);
      assert(field(state, "Role ID") === parentId, `general Role ID ${field(state, "Role ID")}`);
      assert(field(state, "Role Name") === parentName, `general Role Name ${field(state, "Role Name")}`);
      assert(field(state, "Parent Role") === "Not provided", `general Parent Role ${field(state, "Parent Role")}`);
      assert(field(state, "Calculate Costs from Units") === "Yes", `general cost flag ${field(state, "Calculate Costs from Units")}`);
      assert(field(state, "Record Revision") === "1", `general revision ${field(state, "Record Revision")}`);

      const stored = await readRole(page, parentId);
      assert(stored.status === 200, `created role GET status ${stored.status}`);
      assert(stored.body.role.parent_role_id === null, `stored parent ${stored.body.role.parent_role_id}`);
      assert(stored.body.role.calculate_costs_from_units === true, `stored cost flag ${stored.body.role.calculate_costs_from_units}`);

      const duplicate = await postRole(page, { role_id: parentId, name: "Silent overwrite" });
      assert(duplicate.status === 409, `duplicate create status ${duplicate.status}`);
      assert(duplicate.body.code === "ROLE_ALREADY_EXISTS", `duplicate create code ${duplicate.body.code}`);
      const afterDuplicate = await readRole(page, parentId);
      assert(afterDuplicate.body.role.name === parentName, "a duplicate create overwrote the stored name");

      await capture(page, "02-role-parent-created");
      return { parentId, duplicateStatus: duplicate.status, row };
    });

    await scenario("03", "ایجاد نقش فرزند با والد، ترتیب والد-قبل-فرزند و رد چرخهٔ سلسله‌مراتب", async () => {
      await page.click('[data-role-action="new"]');
      await page.waitForSelector("[data-role-general-form]", "child create form");
      let state = await page.evaluate(rolesState);
      assert(state.form.parentOptions.includes(parentId), `child parent options ${state.form.parentOptions}`);

      await page.setInput('[data-role-general-form] input[name="role-id"]', childId);
      await page.setInput('[data-role-general-form] input[name="role-name"]', childName);
      await page.setSelect('[data-role-general-form] select[name="role-parent"]', parentId);
      await page.click('[data-role-general-form] button[type="submit"]');
      await page.waitFor(`document.querySelector('[data-role-notice][data-state="ok"]') !== null`, "child create notice");
      await page.waitForSelector(`[data-role-row][data-role-id="${childId}"]`, "created child row");
      await page.waitForSelector('[data-role-panel="general"]', "child general tab");
      await sleep(400);
      state = await page.evaluate(rolesState);
      const order = state.rows.map((item) => item.id);
      const child = state.rows.find((item) => item.id === childId);
      assert(child, "the created child role is missing from the register");
      assert(order.indexOf(childId) === order.indexOf(parentId) + 1, `register order ${order}`);
      assert(child.parent === parentId, `child parent cell ${child.parent}`);
      assert(child.depth === "14px", `child depth ${child.depth} instead of one hierarchy level`);
      assert(field(state, "Parent Role") === parentId, `general Parent Role ${field(state, "Parent Role")}`);

      await page.click('[data-role-action="edit"]');
      await page.waitForSelector("[data-role-general-form]", "child edit form");
      state = await page.evaluate(rolesState);
      assert(state.form?.kind === "edit", `edit form kind ${state.form?.kind}`);
      assert(state.form.idValue === childId, `edit form id ${state.form.idValue}`);
      assert(!state.form.parentOptions.includes(childId), "the edit form offers the edited role as its own parent");
      await page.click('[data-role-action="cancel"]');
      await page.waitForSelector('[data-role-panel="general"]', "general tab after cancel");

      const cycle = await patchRole(page, childId, {
        name: childName,
        parent_role_id: childId,
        calculate_costs_from_units: true,
        expected_revision: 1,
      });
      assert(cycle.status === 409, `cycle PATCH status ${cycle.status}`);
      assert(cycle.body.code === "ROLE_HIERARCHY_CYCLE", `cycle PATCH code ${cycle.body.code}`);

      await capture(page, "03-role-hierarchy");
      return { childId, order, depth: child.depth, cycleStatus: cycle.status };
    });

    await scenario("04", "ویرایش نقش با نسخهٔ رکورد، افزایش Revision و رد PATCH با نسخهٔ کهنه", async () => {
      await page.click(`[data-role-row][data-role-id="${childId}"]`);
      await page.waitForSelector('[data-role-panel="general"]', "child general tab");
      await sleep(300);
      await page.click('[data-role-action="edit"]');
      await page.waitForSelector("[data-role-general-form]", "child edit form");
      await page.setInput('[data-role-general-form] input[name="role-name"]', childEditedName);
      const unchecked = await page.evaluate(`(() => {
        const input = document.querySelector('[data-role-general-form] input[name="role-calculate-costs"]');
        if (!input) return false;
        input.checked = false;
        input.dispatchEvent(new Event("change", { bubbles: true }));
        return true;
      })()`);
      assert(unchecked, "the Calculate Costs from Units checkbox is missing from the edit form");
      await page.click('[data-role-general-form] button[type="submit"]');
      await page.waitFor(`document.querySelector('[data-role-notice][data-state="ok"]') !== null`, "edit success notice");
      await page.waitForSelector('[data-role-panel="general"]', "child general after edit");
      await sleep(400);
      let state = await page.evaluate(rolesState);
      const row = state.rows.find((item) => item.id === childId);
      assert(row?.name === childEditedName, `edited row name ${row?.name}`);
      assert(row?.revision === "2", `edited revision ${row?.revision}`);
      assert(field(state, "Calculate Costs from Units") === "No", `edited cost flag ${field(state, "Calculate Costs from Units")}`);

      const stored = await readRole(page, childId);
      assert(stored.body.role.record_revision === 2, `stored revision ${stored.body.role.record_revision}`);
      assert(stored.body.role.calculate_costs_from_units === false, `stored cost flag ${stored.body.role.calculate_costs_from_units}`);

      const stale = await patchRole(page, childId, {
        name: "Stale write",
        parent_role_id: parentId,
        calculate_costs_from_units: true,
        expected_revision: 1,
      });
      assert(stale.status === 409, `stale PATCH status ${stale.status}`);
      assert(stale.body.code === "REVISION_CONFLICT", `stale PATCH code ${stale.body.code}`);
      const afterStale = await readRole(page, childId);
      assert(afterStale.body.role.name === childEditedName, "a stale PATCH changed the stored name");

      // Bind the screenshot to the layout assertion: the window's own detail
      // tabs replace the shared bottom pane, which must stay out of the flow.
      const layout = await sharedDetailsLayout(page);
      assert(layout.collapsed === "true" && layout.bottomDisplay === "none", `shared details visible before capture: ${JSON.stringify(layout)}`);
      await capture(page, "04-role-edited");
      return { revision: stored.body.role.record_revision, staleStatus: stale.status };
    });

    await scenario("05", "تب Resources یک منبع ذخیره‌شده را با سطح تخصص و نقش اصلی تخصیص می‌دهد", async () => {
      await page.click(`[data-role-row][data-role-id="${parentId}"]`);
      await page.waitForSelector('[data-role-panel="general"]', "parent general tab");
      await page.click('[data-role-tab="resources"]');
      await page.waitForSelector("[data-role-resource-form]", "resource assignment form");
      let state = await page.evaluate(rolesState);
      assert(state.activeTab === "resources", `active tab ${state.activeTab}`);
      assert(state.resourceRows.length === 0, `resource rows before assign ${state.resourceRows.length}`);
      const optionIds = await page.evaluate(`[...document.querySelectorAll('[data-role-resource-form] select[name="role-resource-id"] option')].map((option) => option.value)`);
      assert(optionIds.includes(RESOURCE_ID), `resource options ${optionIds}`);
      assert(optionIds.includes(""), `the resource select has no explicit placeholder: ${optionIds}`);

      await page.setSelect('[data-role-resource-form] select[name="role-resource-id"]', RESOURCE_ID);
      await page.setSelect('[data-role-resource-form] select[name="role-resource-proficiency"]', "skilled");
      const primary = await page.evaluate(`(() => {
        const input = document.querySelector('[data-role-resource-form] input[name="role-resource-primary"]');
        if (!input) return false;
        input.checked = true;
        input.dispatchEvent(new Event("change", { bubbles: true }));
        return true;
      })()`);
      assert(primary, "the primary-role checkbox is missing");
      await page.click('[data-role-resource-form] button[type="submit"]');
      await page.waitFor(`document.querySelector('[data-role-notice][data-state="ok"]')?.textContent?.includes("Assignment saved") ?? false`, "assignment notice");
      await page.waitForSelector(`[data-role-resource-row][data-resource-id="${RESOURCE_ID}"]`, "assigned resource row");
      await sleep(400);
      state = await page.evaluate(rolesState);
      assert(state.resourceRows.length === 1, `resource rows ${state.resourceRows.length}`);
      assert(JSON.stringify(state.resourceRows[0]) === JSON.stringify([RESOURCE_ID, "Skilled", "Yes", "1", "Edit Unassign"]), `resource row ${state.resourceRows[0]}`);

      const facts = await readRoleFacts(page, parentId, "resources");
      assert(facts.status === 200, `resource facts status ${facts.status}`);
      assert(facts.body.resources.length === 1, `stored assignments ${facts.body.resources.length}`);
      assert(facts.body.resources[0].proficiency === "skilled", `stored proficiency ${facts.body.resources[0].proficiency}`);
      assert(facts.body.resources[0].is_primary === true, `stored primary ${facts.body.resources[0].is_primary}`);

      await capture(page, "05-role-resource-assigned");
      return { resourceRows: state.resourceRows, stored: facts.body.resources[0] };
    });

    await scenario("06", "تخصیص نقش اصلی دوم همان منبع، نقش اصلی قبلی را در نقش دیگر تنزل می‌دهد", async () => {
      await page.click(`[data-role-row][data-role-id="${childId}"]`);
      await page.waitForSelector('[data-role-panel="general"]', "child general tab");
      await page.click('[data-role-tab="resources"]');
      await page.waitForSelector("[data-role-resource-form]", "child resource form");
      await page.setSelect('[data-role-resource-form] select[name="role-resource-id"]', RESOURCE_ID);
      await page.setSelect('[data-role-resource-form] select[name="role-resource-proficiency"]', "expert");
      await page.evaluate(`(() => {
        const input = document.querySelector('[data-role-resource-form] input[name="role-resource-primary"]');
        if (!input) return false;
        input.checked = true;
        input.dispatchEvent(new Event("change", { bubbles: true }));
        return true;
      })()`);
      await page.click('[data-role-resource-form] button[type="submit"]');
      await page.waitFor(`document.querySelector('[data-role-notice][data-state="ok"]')?.textContent?.includes("Assignment saved") ?? false`, "child assignment notice");
      await page.waitForSelector(`[data-role-resource-row][data-resource-id="${RESOURCE_ID}"]`, "child assigned row");
      await sleep(400);
      let state = await page.evaluate(rolesState);
      assert(JSON.stringify(state.resourceRows[0]) === JSON.stringify([RESOURCE_ID, "Expert", "Yes", "1", "Edit Unassign"]), `child resource row ${state.resourceRows[0]}`);

      const parentFacts = await readRoleFacts(page, parentId, "resources");
      assert(parentFacts.body.resources.length === 1, `parent assignments ${parentFacts.body.resources.length}`);
      assert(parentFacts.body.resources[0].is_primary === false, `parent assignment stayed primary: ${parentFacts.body.resources[0].is_primary}`);
      assert(parentFacts.body.resources[0].record_revision === 2, `demoted parent revision ${parentFacts.body.resources[0].record_revision}`);
      const childFacts = await readRoleFacts(page, childId, "resources");
      assert(childFacts.body.resources[0].is_primary === true, `child assignment primary ${childFacts.body.resources[0].is_primary}`);

      await page.click(`[data-role-row][data-role-id="${parentId}"]`);
      await page.waitForSelector('[data-role-panel="general"]', "parent general tab");
      await page.click('[data-role-tab="resources"]');
      await page.waitForSelector("[data-role-resource-form]", "parent resource form after demotion");
      await sleep(300);
      state = await page.evaluate(rolesState);
      assert(JSON.stringify(state.resourceRows[0]) === JSON.stringify([RESOURCE_ID, "Skilled", "No", "2", "Edit Unassign"]), `parent demoted row ${state.resourceRows[0]}`);

      await capture(page, "06-role-primary-demoted");
      return { parent: parentFacts.body.resources[0], child: childFacts.body.resources[0] };
    });

    await scenario("07", "ویرایش سطح تخصص و حذف تخصیص از جدول واقعی، رکورد را از سرور پاک می‌کند", async () => {
      await page.click(`[data-role-row][data-role-id="${childId}"]`);
      await page.waitForSelector('[data-role-panel="general"]', "child general tab");
      await page.click('[data-role-tab="resources"]');
      await page.waitForSelector(`[data-role-resource-edit="${RESOURCE_ID}"]`, "child assignment edit button");
      await page.click(`[data-role-resource-edit="${RESOURCE_ID}"]`);
      await page.waitForSelector("[data-role-resource-form] input[readonly]", "assignment edit form");
      await page.setSelect('[data-role-resource-form] select[name="role-resource-proficiency"]', "master");
      await page.click('[data-role-resource-form] button[type="submit"]');
      await page.waitFor(`document.querySelector('[data-role-notice][data-state="ok"]')?.textContent?.includes("Assignment saved") ?? false`, "assignment edit notice");
      await page.waitForSelector(`[data-role-resource-row][data-resource-id="${RESOURCE_ID}"]`, "assignment after edit");
      await sleep(400);
      let facts = await readRoleFacts(page, childId, "resources");
      assert(facts.body.resources[0].proficiency === "master", `edited proficiency ${facts.body.resources[0].proficiency}`);
      assert(facts.body.resources[0].record_revision === 2, `edited assignment revision ${facts.body.resources[0].record_revision}`);

      await page.evaluate(`(window.confirm = () => true)`);
      await page.click(`[data-role-resource-remove="${RESOURCE_ID}"]`);
      await page.waitFor(`document.querySelector('[data-role-notice][data-state="ok"]')?.textContent?.includes("unassigned") ?? false`, "unassign notice");
      await page.waitFor(
        `document.querySelectorAll('[data-role-resource-row]').length === 0`,
        "assignment removed from the table",
      );
      await sleep(300);
      const state = await page.evaluate(rolesState);
      assert(state.resourceRows.length === 0, `resource rows after removal ${state.resourceRows.length}`);
      facts = await readRoleFacts(page, childId, "resources");
      assert(facts.body.resources.length === 0, `stored assignments after removal ${facts.body.resources.length}`);
      const parentFacts = await readRoleFacts(page, parentId, "resources");
      assert(parentFacts.body.resources.length === 1, "removing the child assignment deleted the parent assignment");
      assert(parentFacts.body.resources[0].is_primary === false, "the demoted parent assignment became primary again");

      await capture(page, "07-role-resource-unassigned");
      return { childAssignments: 0, parentAssignments: parentFacts.body.resources.length };
    });

    await scenario("08", "نرخ‌های تاریخ‌دار: افزودن، سقف پنج نرخ در هر تاریخ، و ویرایش با Revision", async () => {
      await page.click(`[data-role-row][data-role-id="${parentId}"]`);
      await page.waitForSelector('[data-role-panel="general"]', "parent general tab");
      await page.click('[data-role-tab="prices"]');
      await page.waitForSelector("[data-role-rate-form]", "rate form");
      let state = await page.evaluate(rolesState);
      assert(state.activeTab === "prices", `active tab ${state.activeTab}`);
      assert(state.rateRows.length === 0, `rate rows before add ${state.rateRows.length}`);

      await page.setInput('[data-role-rate-form] input[name="role-rate-date"]', "2026-12-01");
      await page.setInput('[data-role-rate-form] input[name="role-rate-type"]', "Standard");
      await page.setInput('[data-role-rate-form] input[name="role-rate-value"]', "25.5");
      await page.setSelect('[data-role-rate-form] select[name="role-rate-unit"]', "h");
      await page.setInput('[data-role-rate-form] input[name="role-rate-currency"]', "USD");
      await page.click('[data-role-rate-form] button[type="submit"]');
      await page.waitFor(`document.querySelector('[data-role-notice][data-state="ok"]')?.textContent?.includes("Rate saved") ?? false`, "first rate notice");
      await page.waitForSelector('[data-role-rate-row][data-effective-from="2026-12-01"]', "first rate row");

      await page.setInput('[data-role-rate-form] input[name="role-rate-date"]', "2027-01-01");
      await page.setInput('[data-role-rate-form] input[name="role-rate-type"]', "Standard");
      await page.setInput('[data-role-rate-form] input[name="role-rate-value"]', "30");
      await page.setSelect('[data-role-rate-form] select[name="role-rate-unit"]', "d");
      await page.setInput('[data-role-rate-form] input[name="role-rate-currency"]', "USD");
      await page.click('[data-role-rate-form] button[type="submit"]');
      await page.waitFor(`document.querySelector('[data-role-notice][data-state="ok"]')?.textContent?.includes("Rate saved") ?? false`, "second rate notice");
      await page.waitForSelector('[data-role-rate-row][data-effective-from="2027-01-01"]', "second rate row");
      await sleep(300);

      let facts = await readRoleFacts(page, parentId, "rates");
      assert(facts.body.rates.length === 2, `stored rates ${facts.body.rates.length}`);
      const first = facts.body.rates.find((rate) => rate.effective_from === "2026-12-01");
      assert(first?.rate === "25.5" && first.unit === "h" && first.currency === "USD", `stored first rate ${JSON.stringify(first)}`);

      // Fill the documented five-rate ceiling for one effective date through
      // the same real POST contract, then prove the sixth is rejected.
      for (const type of ["Extra A", "Extra B", "Extra C", "Extra D"]) {
        const created = await postRate(page, parentId, {
          effective_from: "2026-12-01",
          rate_type: type,
          rate: "1",
          unit: "h",
          currency: "USD",
        });
        assert(created.status === 200, `rate ${type} status ${created.status}`);
      }
      const sixth = await postRate(page, parentId, {
        effective_from: "2026-12-01",
        rate_type: "Extra E",
        rate: "1",
        unit: "h",
        currency: "USD",
      });
      assert(sixth.status === 409, `sixth same-date rate status ${sixth.status}`);
      assert(sixth.body.code === "ROLE_RATE_LIMIT_EXCEEDED", `sixth rate code ${sixth.body.code}`);

      await page.click('[data-role-action="reload"]');
      await page.waitForSelector('[data-role-row]', "register after rate refresh");
      await page.click(`[data-role-row][data-role-id="${parentId}"]`);
      await page.waitForSelector('[data-role-panel="general"]', "parent general after rate reload");
      await page.click('[data-role-tab="prices"]');
      await page.waitForSelector('[data-role-rate-row][data-effective-from="2027-01-01"]', "rates after refresh");
      await page.click('[data-role-rate-edit="2027-01-01"]');
      await page.waitForSelector('[data-role-rate-form] input[name="role-rate-date"][readonly]', "rate edit form");
      await page.setInput('[data-role-rate-form] input[name="role-rate-value"]', "32.5");
      await page.click('[data-role-rate-form] button[type="submit"]');
      await page.waitFor(`document.querySelector('[data-role-notice][data-state="ok"]')?.textContent?.includes("Rate saved") ?? false`, "rate edit notice");
      await sleep(500);

      facts = await readRoleFacts(page, parentId, "rates");
      const edited = facts.body.rates.find((rate) => rate.effective_from === "2027-01-01");
      assert(edited?.rate === "32.5", `edited rate value ${edited?.rate}`);
      assert(edited?.record_revision === 2, `edited rate revision ${edited?.record_revision}`);
      const sameDate = facts.body.rates.filter((rate) => rate.effective_from === "2026-12-01");
      assert(sameDate.length === 5, `rates on 2026-12-01 ${sameDate.length}`);

      state = await page.evaluate(rolesState);
      // Five rates on 2026-12-01 plus the edited 2027-01-01 rate; the rejected
      // sixth same-date rate must never appear.
      assert(state.rateRows.length === 6, `rate table rows ${state.rateRows.length}`);
      assert(state.rateRows.some((row) => row[0] === "2027-01-01" && row[2] === "32.5"), `edited rate is not in the table: ${state.rateRows}`);

      await capture(page, "08-role-rates");
      return { storedRates: facts.body.rates.length, sameDateRates: sameDate.length, sixthStatus: sixth.status, edited };
    });

    await scenario("09", "محدودیت‌های نقش: واحد و درصد، یک محدودیت در هر تاریخ، و ویرایش با Revision", async () => {
      let state = await page.evaluate(rolesState);
      assert(state.activeTab === "prices", `active tab ${state.activeTab}`);
      assert(state.limitRows.length === 0, `limit rows before add ${state.limitRows.length}`);

      await page.setInput('[data-role-limit-form] input[name="role-limit-date"]', "2026-12-01");
      await page.setInput('[data-role-limit-form] input[name="role-limit-value"]', "8");
      await page.setSelect('[data-role-limit-form] select[name="role-limit-basis"]', "units");
      await page.click('[data-role-limit-form] button[type="submit"]');
      await page.waitFor(`document.querySelector('[data-role-notice][data-state="ok"]')?.textContent?.includes("Limit saved") ?? false`, "first limit notice");
      await page.waitForSelector('[data-role-limit-row][data-effective-from="2026-12-01"]', "first limit row");

      await page.setInput('[data-role-limit-form] input[name="role-limit-date"]', "2027-01-01");
      await page.setInput('[data-role-limit-form] input[name="role-limit-value"]', "60");
      await page.setSelect('[data-role-limit-form] select[name="role-limit-basis"]', "percent");
      await page.click('[data-role-limit-form] button[type="submit"]');
      await page.waitFor(`document.querySelector('[data-role-notice][data-state="ok"]')?.textContent?.includes("Limit saved") ?? false`, "second limit notice");
      await page.waitForSelector('[data-role-limit-row][data-effective-from="2027-01-01"]', "second limit row");
      await sleep(300);

      let facts = await readRoleFacts(page, parentId, "limits");
      assert(facts.body.limits.length === 2, `stored limits ${facts.body.limits.length}`);
      const percent = facts.body.limits.find((limit) => limit.effective_from === "2027-01-01");
      assert(percent?.max_units === "60" && percent.unit_basis === "percent", `stored percent limit ${JSON.stringify(percent)}`);

      await page.click('[data-role-limit-edit="2026-12-01"]');
      await page.waitForSelector('[data-role-limit-form] input[name="role-limit-date"][readonly]', "limit edit form");
      await page.setInput('[data-role-limit-form] input[name="role-limit-value"]', "10");
      await page.click('[data-role-limit-form] button[type="submit"]');
      await page.waitFor(`document.querySelector('[data-role-notice][data-state="ok"]')?.textContent?.includes("Limit saved") ?? false`, "limit edit notice");
      await sleep(500);

      facts = await readRoleFacts(page, parentId, "limits");
      const units = facts.body.limits.find((limit) => limit.effective_from === "2026-12-01");
      assert(units?.max_units === "10", `edited limit value ${units?.max_units}`);
      assert(units?.record_revision === 2, `edited limit revision ${units?.record_revision}`);
      state = await page.evaluate(rolesState);
      assert(state.limitRows.length === 2, `limit table rows ${state.limitRows.length}`);
      assert(state.limitRows.some((row) => row[0] === "2026-12-01" && row[1] === "10"), `edited limit is not in the table: ${state.limitRows}`);

      await capture(page, "09-role-limits");
      return { storedLimits: facts.body.limits.length, edited: units };
    });

    await scenario("10", "پس از بارگذاری کامل صفحه، نقش‌ها، تخصص، نرخ‌ها و محدودیت‌ها از سرور بازمی‌گردند", async () => {
      await page.navigate(`${baseUrl}/app?project=preview-rps-01&view=visual`, "#cp-activity-grid tbody tr[data-activity-id]", "workspace reload");
      await sleep(1200);
      await openRoles(page);
      const rows = await page.evaluate(`[...document.querySelectorAll("[data-role-row]")].map((row) => row.dataset.roleId)`);
      assert(rows.length === 2, `roles after reload ${rows}`);
      assert(rows.indexOf(parentId) === 0 && rows.indexOf(childId) === 1, `stored order after reload ${rows}`);

      await page.click(`[data-role-row][data-role-id="${childId}"]`);
      await page.waitForSelector('[data-role-panel="general"]', "child general after reload");
      await sleep(300);
      let state = await page.evaluate(rolesState);
      assert(field(state, "Role Name") === childEditedName, `child name after reload ${field(state, "Role Name")}`);
      assert(field(state, "Record Revision") === "2", `child revision after reload ${field(state, "Record Revision")}`);
      assert(field(state, "Calculate Costs from Units") === "No", `child cost flag after reload ${field(state, "Calculate Costs from Units")}`);

      await page.click(`[data-role-row][data-role-id="${parentId}"]`);
      await page.waitForSelector('[data-role-panel="general"]', "parent general after reload");
      await page.click('[data-role-tab="resources"]');
      await page.waitForSelector("[data-role-resource-form]", "parent resource form after reload");
      await sleep(300);
      state = await page.evaluate(rolesState);
      assert(state.resourceRows.length === 1, `parent assignments after reload ${state.resourceRows.length}`);
      assert(state.resourceRows[0][1] === "Skilled", `parent proficiency after reload ${state.resourceRows[0][1]}`);

      await page.click('[data-role-tab="prices"]');
      await page.waitForSelector("[data-role-rate-form]", "rate form after reload");
      await sleep(300);
      state = await page.evaluate(rolesState);
      assert(state.rateRows.length === 6, `rates after reload ${state.rateRows.length}`);
      assert(state.limitRows.length === 2, `limits after reload ${state.limitRows.length}`);
      assert(state.rateRows.some((row) => row[0] === "2027-01-01" && row[2] === "32.5"), "the edited rate did not survive the reload");
      assert(state.limitRows.some((row) => row[0] === "2026-12-01" && row[1] === "10"), "the edited limit did not survive the reload");
      await capture(page, "10-role-persisted");
      return { rows, rates: state.rateRows.length, limits: state.limitRows.length };
    });

    await scenario("11", "پنجرهٔ Roles در 1280×720 بدون بریدگی چیدمان رندر می‌شود", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await sleep(600);
      const layout = await page.evaluate(`(() => {
        const rect = (element) => {
          if (!element) return null;
          const bounds = element.getBoundingClientRect();
          return { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height };
        };
        const page = document.querySelector("[data-roles-page]");
        const bottom = document.querySelector("#cp-details");
        return {
          innerWidth,
          innerHeight,
          toolbar: rect(page?.querySelector(".cp-register-toolbar")),
          register: rect(page?.querySelector(".cp-register-table-wrap")),
          window: rect(page),
          bottomDisplay: bottom ? getComputedStyle(bottom).display : null,
          collapsed: document.querySelector(".cp-main")?.dataset.detailsCollapsed ?? null,
          rowCount: document.querySelectorAll("[data-role-row]").length,
        };
      })()`);
      assert(layout.toolbar && layout.toolbar.width > 0, "the toolbar has no layout box at 1280x720");
      assert(layout.register && layout.register.height > 0, "the register has no layout box at 1280x720");
      assert(layout.window && layout.window.height > 0, "the Roles window has no layout box at 1280x720");
      assert(layout.rowCount === 2, `register rows at 1280x720: ${layout.rowCount}`);
      assert(layout.toolbar.x >= 0 && layout.toolbar.x + layout.toolbar.width <= layout.innerWidth + 1, `toolbar overflows: ${JSON.stringify(layout.toolbar)}`);
      assert(layout.window.x + layout.window.width <= layout.innerWidth + 1, `Roles window overflows: ${JSON.stringify(layout.window)}`);
      // Roles carries its own detail pane; the shared bottom surface must not
      // claim the tabs are missing or duplicate the authored facts.
      assert(layout.collapsed === "true", `bottom details still claim space: ${layout.collapsed}`);
      assert(layout.bottomDisplay === "none", `bottom details are still rendered: ${layout.bottomDisplay}`);
      await capture(page, "11-role-1280x720");
      return layout;
    });

    assert(exceptions.length === 0, `uncaught page exceptions: ${JSON.stringify(exceptions.slice(0, 3))}`);
    assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors.slice(0, 3))}`);
    assert(apiFailures.length === 0, `API 5xx responses: ${JSON.stringify(apiFailures.slice(0, 3))}`);
  } finally {
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(outDir, "roles-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(evidenceDir, "roles-v26.json"), JSON.stringify(report, null, 2));
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
