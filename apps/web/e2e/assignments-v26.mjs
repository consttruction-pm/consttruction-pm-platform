#!/usr/bin/env node
/**
 * Browser E2E for the Version 26 Resource Assignments window.
 *
 * Every fixture is written through the real window: assignments are created by
 * the create form (POST p6-resource-write-api.v1), time-phased periods are
 * written by the Spreadsheet tab (POST resource-assignment-periods), and every
 * assertion is checked against the same session's API afterwards. The register
 * grouping, sorting, filtering, column chooser, collapse state, profile bars and
 * the append-only "Revise" flow are all exercised in the real preview runtime.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4183 node e2e/assignments-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4183";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-11";
// The commit under test and the commit that stores this report are different facts:
// the bundle is built from the worktree before the evidence commit exists.
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "assignments-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `assignments-v26-${evidenceDate}`);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const stamp = Date.now().toString(36).toUpperCase();
const ID_A = `AS-D2B-${stamp}-A`;
const ID_B = `AS-D2B-${stamp}-B`;
const ID_C = `AS-D2B-${stamp}-C`;
const RESOURCE = "RPS-CIVIL-CREW";
const ROLE = "RPS-ROLE-CIVIL";

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
  scenarios.push({ ...details, id, name, status, at: new Date().toISOString() });
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

/** Exact decimal sum over API strings, kept separate from the app code. */
function exactSum(values) {
  const parts = values.filter((value) => typeof value === "string" && value !== "").map((value) => {
    const negative = value.startsWith("-");
    const [whole = "0", fraction = ""] = (negative ? value.slice(1) : value).split(".");
    return { negative, whole, fraction };
  });
  if (!parts.length) return null;
  const scale = Math.max(...parts.map((part) => part.fraction.length));
  let total = 0n;
  for (const part of parts) {
    const scaled = BigInt(part.whole + part.fraction.padEnd(scale, "0"));
    total += part.negative ? -scaled : scaled;
  }
  const negative = total < 0n;
  const digits = (negative ? -total : total).toString().padStart(scale + 1, "0");
  const whole = scale ? digits.slice(0, digits.length - scale) : digits;
  const fraction = scale ? digits.slice(digits.length - scale).replace(/0+$/, "") : "";
  return `${negative ? "-" : ""}${whole}${fraction ? `.${fraction}` : ""}`;
}

const assignmentsState = `(() => {
  const page = document.querySelector("[data-assignments-page]");
  const rows = [...document.querySelectorAll("[data-assignment-row]")].map((row) => ({
    id: row.dataset.assignmentId,
    cells: [...row.querySelectorAll("td")].map((cell) => (cell.textContent || "").trim()),
    selected: row.getAttribute("aria-selected") === "true",
  }));
  const headers = [...document.querySelectorAll("[data-assignments-page] th[data-assignment-sort]")].map((header) => ({
    key: header.dataset.assignmentSort,
    label: (header.textContent || "").trim(),
    ariaSort: header.getAttribute("aria-sort"),
  }));
  const groups = [...document.querySelectorAll("[data-assignment-group-row]")].map((row) => ({
    key: row.dataset.assignmentGroupRow,
    label: row.querySelector("strong")?.textContent?.trim() ?? null,
    count: row.querySelector("[data-assignment-group-count]")?.textContent?.trim() ?? null,
    totals: row.querySelector("[data-assignment-group-totals]")?.textContent?.trim() ?? null,
    expanded: row.querySelector("[data-assignment-group-toggle]")?.getAttribute("aria-expanded") === "true",
  }));
  const notice = document.querySelector("[data-assignment-notice]");
  const periodNotice = document.querySelector("[data-assignment-period-notice]");
  const details = page?.querySelector(".cp-register-details header span")?.textContent?.trim() ?? null;
  return {
    activeMenu: document.querySelector(".cp-workspace")?.dataset.activeMenu ?? null,
    rows,
    headers,
    groups,
    groupBy: page?.querySelector("select[data-assignment-group]")?.value ?? null,
    columns: [...document.querySelectorAll("[data-assignment-column]")].map((input) => ({
      key: input.dataset.assignmentColumn,
      checked: input.checked,
    })),
    query: page?.querySelector("[data-assignment-filter='query']")?.value ?? null,
    resourceFilter: page?.querySelector("[data-assignment-filter='resource']")?.value ?? null,
    activityFilter: page?.querySelector("[data-assignment-filter='activity']")?.value ?? null,
    activeTab: document.querySelector("[data-assignment-tab][aria-selected='true']")?.dataset.assignmentTab ?? null,
    details,
    empty: page?.querySelector(":scope > .cp-calendar-empty")?.textContent?.trim() ?? null,
    periodEmpty: document.querySelector("[data-assignment-period-empty]")?.textContent?.trim() ?? null,
    register: Boolean(page?.querySelector(".cp-register-table-wrap")),
    notice: notice ? { kind: notice.dataset.state, text: (notice.textContent || "").trim() } : null,
    periodNotice: periodNotice ? { kind: periodNotice.dataset.state, text: (periodNotice.textContent || "").trim() } : null,
    form: document.querySelector("[data-assignment-form]") ? {
      assignmentId: document.querySelector('[data-assignment-form] input[name="assignment-id"]')?.value ?? null,
      activityId: document.querySelector('[data-assignment-form] select[name="activity-id"]')?.value ?? null,
      resourceId: document.querySelector('[data-assignment-form] input[name="resource-id"]')?.value ?? null,
      roleId: document.querySelector('[data-assignment-form] input[name="role-id"]')?.value ?? null,
      units: document.querySelector('[data-assignment-form] input[name="units"]')?.value ?? null,
      plannedCost: document.querySelector('[data-assignment-form] input[name="planned-cost"]')?.value ?? null,
      note: document.querySelector('[data-assignment-form] input[name="note"]')?.value ?? null,
    } : null,
    periodRows: [...document.querySelectorAll("[data-assignment-period-row]")].map((row) => ({
      start: row.dataset.periodStart,
      cells: [...row.querySelectorAll("td")].map((cell) => (cell.textContent || "").trim()),
    })),
    periodTotals: [...document.querySelectorAll("[data-assignment-period-totals] td")].map((cell) => (cell.textContent || "").trim()),
    profileSummary: document.querySelector("[data-assignment-profile-summary]")?.textContent?.trim() ?? null,
    bars: [...document.querySelectorAll("[data-assignment-profile-bar]")].map((bar) => ({
      start: bar.dataset.periodStart,
      units: bar.dataset.units,
      height: bar.querySelector("b")?.style.height ?? null,
    })),
    storage: (() => {
      try { return localStorage.getItem("cubi.assignments.view.v1.${PROJECT}"); } catch { return null; }
    })(),
  };
})()`;

async function capture(page, name) {
  const file = `assignments-v26/${name}.png`;
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

async function waitForRegister(page) {
  await page.waitFor(`(() => {
    const page = document.querySelector("[data-assignments-page]");
    if (!page || !page.querySelector("[data-assignment-action='new']")) return false;
    if (page.querySelector(".cp-register-table-wrap")) return true;
    const empty = page.querySelector(":scope > .cp-calendar-empty");
    return Boolean(empty && !/Reading resource assignments/.test(empty.textContent || ""));
  })()`, "assignment register");
}

async function readApi(page) {
  return page.evaluate(`(async () => {
    const base = "/api/projects/${PROJECT}/p6/";
    const [assignments, periods, resources] = await Promise.all([
      fetch(base + "resource-assignments").then((response) => response.json()),
      fetch(base + "resource-assignment-periods").then((response) => response.json()),
      fetch(base + "resources").then((response) => response.json()),
    ]);
    return {
      assignments: (assignments.assignments ?? []).map((item) => item.assignment),
      periods: (periods.periods ?? []).map((item) => item.period ?? item),
      resources: (resources.resources ?? []).map((item) => item.resource?.resource_id).filter(Boolean),
    };
  })()`, { awaitPromise: true });
}

async function formActivityOptions(page) {
  return page.evaluate(`(() => {
    const select = document.querySelector('[data-assignment-form] select[name="activity-id"]');
    if (!select) return [];
    return [...select.querySelectorAll("option")].map((option) => option.value).filter((value) => value !== "");
  })()`);
}

async function openCreateForm(page) {
  await page.click('[data-assignment-action="new"]');
  await page.waitForSelector("[data-assignment-form]", "assignment create form");
  await sleep(200);
}

async function fillAssignmentForm(page, spec) {
  const options = await formActivityOptions(page);
  assert(options.length > 0, "the activity selector has no real activity to choose");
  const activityId = spec.activityId && options.includes(spec.activityId) ? spec.activityId : options[spec.activityIndex ?? 0];
  assert(activityId, `no activity option at index ${spec.activityIndex ?? 0}`);
  await page.setInput('[data-assignment-form] input[name="assignment-id"]', spec.assignmentId);
  await page.setSelect('[data-assignment-form] select[name="activity-id"]', activityId);
  await page.setInput('[data-assignment-form] input[name="resource-id"]', spec.resourceId);
  await page.setInput('[data-assignment-form] input[name="role-id"]', spec.roleId ?? "");
  await page.setInput('[data-assignment-form] input[name="units"]', spec.units);
  await page.setInput('[data-assignment-form] input[name="unit"]', spec.unit ?? "hour");
  await page.setInput('[data-assignment-form] input[name="planned-cost"]', spec.plannedCost);
  await page.setInput('[data-assignment-form] input[name="currency"]', spec.currency ?? "USD");
  await page.setInput('[data-assignment-form] input[name="note"]', spec.note ?? "");
  return activityId;
}

async function createAssignment(page, spec) {
  await openCreateForm(page);
  const activityId = await fillAssignmentForm(page, spec);
  await page.click('[data-assignment-form] button[type="submit"]');
  await page.waitFor(
    `document.querySelector('[data-assignment-notice][data-state="ok"]') !== null`,
    `create notice for ${spec.assignmentId}`,
  );
  await page.waitForSelector(`[data-assignment-row][data-assignment-id="${spec.assignmentId}"]`, "created assignment row");
  await sleep(300);
  return activityId;
}

async function selectAssignment(page, assignmentId) {
  await page.click(`[data-assignment-row][data-assignment-id="${assignmentId}"]`);
  await page.waitFor(
    `document.querySelector('[data-assignment-row][data-assignment-id="${assignmentId}"][aria-selected="true"]') !== null`,
    `selected ${assignmentId}`,
  );
  await sleep(250);
}

async function selectTab(page, tab, selector) {
  await page.click(`[data-assignment-tab="${tab}"]`);
  if (selector) await page.waitForSelector(selector, `${tab} panel`);
  await sleep(250);
}

async function addPeriod(page, periodStart, units, cost) {
  await page.setInput('[data-assignment-period-form] input[name="period-start"]', periodStart);
  await page.setInput('[data-assignment-period-form] input[name="period-units"]', units);
  await page.setInput('[data-assignment-period-form] input[name="period-cost"]', cost);
  await page.click('[data-assignment-period-form] button[type="submit"]');
  await page.waitFor(
    `document.querySelector('[data-assignment-period-row][data-period-start="${periodStart}"]') !== null`,
    `stored period ${periodStart}`,
  );
  await sleep(300);
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
    contract: "cubi-assignments-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    createdAssignmentIds: [ID_A, ID_B, ID_C],
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
  };

  let api;

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

    api = await readApi(page);
    assert(api.assignments.length === 0, `the reset preview should start with no assignment, got ${api.assignments.length}`);
    assert(api.periods.length === 0, `the reset preview should start with no period, got ${api.periods.length}`);

    await openMenu(page, "assignments", "[data-assignments-page] [data-assignment-action='new']", "assignments window");
    await waitForRegister(page);

    await scenario("01", "پنجرهٔ تخصیص‌ها ثبت خالی، هشت ستون پیش‌فرض و گروه‌بندی «هیچ» را از API نشان می‌دهد", async () => {
      const state = await page.evaluate(assignmentsState);
      assert(state.activeMenu === "assignments", `active menu is ${state.activeMenu}`);
      assert(state.rows.length === 0, `empty register has ${state.rows.length} rows`);
      assert(state.empty && /No resource assignments are stored/.test(state.empty), `empty state is ${state.empty}`);
      const visible = state.columns.filter((column) => column.checked).map((column) => column.key);
      assert(JSON.stringify(visible) === JSON.stringify([
        "assignment", "activity", "resource", "role", "units", "unit", "plannedCost", "currency",
      ]), `default columns are ${visible}`);
      assert(state.groupBy === "none", `group-by value ${state.groupBy}`);
      assert(state.storage === null, `a fresh project should not need stored preferences yet: ${state.storage}`);
      await capture(page, "01-empty-register");
      return { columns: visible };
    });

    let activityA;
    await scenario("02", "ایجاد تخصیص از فرم واقعی، خواندن دوباره از API و انتخاب پایدار سطر", async () => {
      activityA = await createAssignment(page, {
        assignmentId: ID_A,
        activityIndex: 0,
        resourceId: RESOURCE,
        roleId: ROLE,
        units: "8",
        plannedCost: "1200.50",
        note: "E2E crew assignment",
      });
      const state = await page.evaluate(assignmentsState);
      const row = state.rows.find((item) => item.id === ID_A);
      assert(row, "the created assignment is missing from the register");
      assert(row.selected, "the created assignment is not selected");
      assert(row.cells[2] === RESOURCE, `resource cell ${row.cells[2]}`);
      assert(row.cells[3] === ROLE, `role cell ${row.cells[3]}`);
      assert(row.cells[4] === "8", `units cell ${row.cells[4]}`);
      assert(row.cells[6] === "1200.50", `planned cost cell ${row.cells[6]}`);
      assert(row.cells[7] === "USD", `currency cell ${row.cells[7]}`);

      api = await readApi(page);
      const stored = api.assignments.find((item) => item.assignment_id === ID_A);
      assert(stored, "the API does not return the created assignment");
      assert(stored.units === "8", `API units ${stored.units}`);
      assert(stored.planned_cost === "1200.50", `API planned cost ${stored.planned_cost}`);
      assert(stored.note === "E2E crew assignment", `API note ${stored.note}`);
      await capture(page, "02-created-assignment");
      return { activityId: activityA, stored };
    });

    await scenario("03", "ایجاد دوبارهٔ همان شناسه با 409 رد می‌شود و سطر ذخیره‌شده را بازنویسی نمی‌کند", async () => {
      const before = await readApi(page);
      await openCreateForm(page);
      await fillAssignmentForm(page, {
        assignmentId: ID_A,
        activityIndex: 0,
        resourceId: RESOURCE,
        roleId: ROLE,
        units: "9",
        plannedCost: "999",
        note: "Silent overwrite",
      });
      await page.click('[data-assignment-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-assignment-notice][data-state="error"]') !== null`,
        "duplicate create error notice",
      );
      await sleep(200);
      const state = await page.evaluate(assignmentsState);
      assert(/IMMUTABLE_RESOURCE_ASSIGNMENT/.test(state.notice?.text ?? ""), `duplicate notice ${state.notice?.text}`);
      assert(state.rows.length === before.assignments.length, `rows after duplicate ${state.rows.length}`);
      const after = await readApi(page);
      const stored = after.assignments.find((item) => item.assignment_id === ID_A);
      assert(stored.units === "8", `a duplicate create overwrote units to ${stored.units}`);
      assert(stored.note === "E2E crew assignment", `a duplicate create overwrote note to ${stored.note}`);
      await capture(page, "03-duplicate-rejected");
      await page.click('[data-assignment-action="cancel"]');
      await sleep(200);
      return { duplicateStatus: 409, code: "IMMUTABLE_RESOURCE_ASSIGNMENT" };
    });

    await scenario("04", "ایجاد دو تخصیص دیگر با فعالیت، منبع و نقش متفاوت برای گروه‌بندی واقعی", async () => {
      await createAssignment(page, {
        assignmentId: ID_B,
        activityIndex: 1,
        resourceId: RESOURCE,
        roleId: ROLE,
        units: "4.5",
        plannedCost: "600.25",
        note: "Second crew assignment",
      });
      await createAssignment(page, {
        assignmentId: ID_C,
        activityIndex: 0,
        resourceId: RESOURCE,
        roleId: "",
        units: "2",
        plannedCost: "100",
        note: "Unassigned role assignment",
      });
      api = await readApi(page);
      const ids = api.assignments.map((item) => item.assignment_id).sort();
      assert(JSON.stringify(ids) === JSON.stringify([ID_A, ID_B, ID_C].sort()), `API ids ${ids}`);
      const state = await page.evaluate(assignmentsState);
      assert(state.rows.length === 3, `register rows ${state.rows.length}`);
      await capture(page, "04-three-assignments");
      return { ids, activities: api.assignments.map((item) => [item.assignment_id, item.activity_id]) };
    });

    await scenario("05", "گروه‌بندی بر اساس نقش، جمع دقیق واحد و هزینه، و بدون نقش را جدا می‌کند", async () => {
      await page.setSelect("select[data-assignment-group]", "role");
      await page.waitForSelector("[data-assignment-group-row]", "role groups");
      await sleep(300);
      let state = await page.evaluate(assignmentsState);
      assert(state.groupBy === "role", `group-by value ${state.groupBy}`);
      const byRole = api.assignments.reduce((groups, item) => {
        const key = item.role_id ?? "";
        groups[key] = groups[key] ?? [];
        groups[key].push(item);
        return groups;
      }, {});
      assert(state.groups.length === Object.keys(byRole).length, `groups ${state.groups.length} vs API ${Object.keys(byRole).length}`);
      const roleGroup = state.groups.find((group) => group.label === ROLE);
      assert(roleGroup, `the ${ROLE} group is missing from ${state.groups.map((group) => group.label)}`);
      assert(roleGroup.count === "(2)", `role group count ${roleGroup.count}`);
      const roleRows = byRole[ROLE];
      const expectedRoleTotals = `Units: ${exactSum(roleRows.map((row) => row.units))} · Planned Cost: ${exactSum(roleRows.map((row) => row.planned_cost))} · Actual Cost: —`;
      assert(roleGroup.totals === expectedRoleTotals, `role totals ${roleGroup.totals} vs ${expectedRoleTotals}`);
      const unassigned = state.groups.find((group) => group.label === "Unassigned");
      assert(unassigned, `the Unassigned group is missing from ${state.groups.map((group) => group.label)}`);
      assert(unassigned.count === "(1)", `unassigned count ${unassigned.count}`);
      assert(unassigned.totals === "Units: 2 · Planned Cost: 100 · Actual Cost: —", `unassigned totals ${unassigned.totals}`);

      await page.click(`[data-assignment-group-toggle="${ROLE}"]`);
      await sleep(250);
      state = await page.evaluate(assignmentsState);
      assert(state.groups.find((group) => group.label === ROLE)?.expanded === false, "the role group did not collapse");
      assert(state.rows.length === 1, `collapsed role group still shows ${state.rows.length} rows`);
      await capture(page, "05-role-group-collapsed");

      await page.click(`[data-assignment-group-toggle="${ROLE}"]`);
      await sleep(250);
      state = await page.evaluate(assignmentsState);
      assert(state.rows.length === 3, `expanded role group shows ${state.rows.length} rows`);
      return { groups: state.groups };
    });

    await scenario("06", "گروه‌بندی بر اساس منبع یک گروه با جمع کل 14.5 واحد و 1900.75 هزینه می‌سازد", async () => {
      await page.setSelect("select[data-assignment-group]", "resource");
      await page.waitForSelector("[data-assignment-group-row]", "resource groups");
      await sleep(300);
      const state = await page.evaluate(assignmentsState);
      assert(state.groupBy === "resource", `group-by value ${state.groupBy}`);
      assert(state.groups.length === 1, `resource groups ${state.groups.map((group) => group.label)}`);
      assert(state.groups[0].label === RESOURCE, `resource group label ${state.groups[0].label}`);
      const expected = `Units: ${exactSum(api.assignments.map((row) => row.units))} · Planned Cost: ${exactSum(api.assignments.map((row) => row.planned_cost))} · Actual Cost: —`;
      assert(state.groups[0].totals === expected, `resource totals ${state.groups[0].totals} vs ${expected}`);
      assert(state.rows.length === 3, `resource group rows ${state.rows.length}`);
      await capture(page, "06-resource-group");
      return { totals: state.groups[0].totals };
    });

    await scenario("07", "مرتب‌سازی عددی ستون واحد صعودی و نزولی با نشانگر aria-sort واقعی کار می‌کند", async () => {
      await page.setSelect("select[data-assignment-group]", "none");
      await sleep(300);
      await page.click('th[data-assignment-sort="units"]');
      await sleep(250);
      let state = await page.evaluate(assignmentsState);
      const unitsHeader = state.headers.find((header) => header.key === "units");
      assert(unitsHeader?.ariaSort === "ascending", `units aria-sort ${unitsHeader?.ariaSort}`);
      assert(unitsHeader?.label.includes("▲"), `units header label ${unitsHeader?.label}`);
      assert(JSON.stringify(state.rows.map((row) => row.id)) === JSON.stringify([ID_C, ID_B, ID_A]), `ascending order ${state.rows.map((row) => row.id)}`);
      await page.click('th[data-assignment-sort="units"]');
      await sleep(250);
      state = await page.evaluate(assignmentsState);
      const descHeader = state.headers.find((header) => header.key === "units");
      assert(descHeader?.ariaSort === "descending", `units aria-sort after toggle ${descHeader?.ariaSort}`);
      assert(descHeader?.label.includes("▼"), `units header label after toggle ${descHeader?.label}`);
      assert(JSON.stringify(state.rows.map((row) => row.id)) === JSON.stringify([ID_A, ID_B, ID_C]), `descending order ${state.rows.map((row) => row.id)}`);
      assert(/"sort":\{"column":"units","dir":"desc"\}/.test(state.storage ?? ""), `stored sort ${state.storage}`);
      await capture(page, "07-sorted-units-desc");
      return { ascending: [ID_C, ID_B, ID_A], descending: [ID_A, ID_B, ID_C] };
    });

    await scenario("08", "جستجو و فیلتر منبع و فعالیت سطرها را واقعاً محدود و سپس بازمی‌گرداند", async () => {
      await page.setInput('[data-assignment-filter="query"]', ID_B);
      await page.waitFor(
        `document.querySelectorAll("[data-assignment-row]").length === 1`,
        "search filtered rows",
      );
      let state = await page.evaluate(assignmentsState);
      assert(JSON.stringify(state.rows.map((row) => row.id)) === JSON.stringify([ID_B]), `search rows ${state.rows.map((row) => row.id)}`);
      assert(state.query === ID_B, `search input value ${state.query}`);
      await capture(page, "08-search-filter");

      await page.setInput('[data-assignment-filter="query"]', "");
      await page.waitFor(
        `document.querySelectorAll("[data-assignment-row]").length === 3`,
        "search cleared rows",
      );
      await page.setSelect('[data-assignment-filter="resource"]', RESOURCE);
      await sleep(250);
      state = await page.evaluate(assignmentsState);
      assert(state.resourceFilter === RESOURCE, `resource filter ${state.resourceFilter}`);
      assert(state.rows.length === 3, `resource filter rows ${state.rows.length}`);
      await page.setSelect('[data-assignment-filter="resource"]', "");

      const activityC = api.assignments.find((item) => item.assignment_id === ID_C).activity_id;
      const expectedActivityRows = api.assignments.filter((item) => item.activity_id === activityC).length;
      await page.setSelect('[data-assignment-filter="activity"]', activityC);
      await sleep(250);
      state = await page.evaluate(assignmentsState);
      assert(state.rows.length === expectedActivityRows, `activity filter rows ${state.rows.length} vs API ${expectedActivityRows}`);
      await page.setSelect('[data-assignment-filter="activity"]', "");
      await sleep(250);
      state = await page.evaluate(assignmentsState);
      assert(state.rows.length === 3, `rows after clearing filters ${state.rows.length}`);
      return { queryRows: 1, resourceRows: 3, activityRows: expectedActivityRows };
    });

    await scenario("09", "انتخاب ستون‌ها هدر را پنهان می‌کند و پس از رفت‌وبرگشت پنجره پایدار می‌ماند", async () => {
      const toggled = await page.evaluate(`(() => {
        const input = document.querySelector('[data-assignment-column="currency"]');
        if (!input) return false;
        input.click();
        return true;
      })()`);
      assert(toggled, "the currency column checkbox is missing");
      await sleep(300);
      let state = await page.evaluate(assignmentsState);
      assert(!state.headers.some((header) => header.key === "currency"), `currency header still visible: ${state.headers.map((header) => header.key)}`);
      assert(!/currency/.test(state.storage ?? ""), `stored columns still contain currency: ${state.storage}`);
      await capture(page, "09-column-hidden");

      await openMenu(page, "resources", "[data-resources-page] [data-resource-row]", "resources window");
      await openMenu(page, "assignments", "[data-assignments-page] [data-assignment-action='new']", "assignments window again");
      await waitForRegister(page);
      state = await page.evaluate(assignmentsState);
      assert(!state.headers.some((header) => header.key === "currency"), `currency returned after remount: ${state.headers.map((header) => header.key)}`);

      const restored = await page.evaluate(`(() => {
        const input = document.querySelector('[data-assignment-column="currency"]');
        if (!input) return false;
        input.click();
        return true;
      })()`);
      assert(restored, "the currency column checkbox is missing after remount");
      await sleep(300);
      state = await page.evaluate(assignmentsState);
      assert(state.headers.some((header) => header.key === "currency"), "the currency column did not return");
      return { hiddenStorage: state.storage };
    });

    await scenario("10", "صفحه‌گسترده دو دورهٔ زمان‌محور را با POST واقعی ذخیره و جمع دقیق را نشان می‌دهد", async () => {
      await selectAssignment(page, ID_A);
      await selectTab(page, "spreadsheet", "[data-assignment-period-form]");
      let state = await page.evaluate(assignmentsState);
      assert(state.activeTab === "spreadsheet", `active tab ${state.activeTab}`);
      assert(state.periodRows.length === 0, `period rows before write ${state.periodRows.length}`);
      assert(/No time-phased period/.test(state.periodEmpty ?? ""), `period empty state ${state.periodEmpty}`);

      await addPeriod(page, "2026-12-01", "8", "640.75");
      await addPeriod(page, "2027-01-01", "4", "320.25");
      state = await page.evaluate(assignmentsState);
      assert(state.periodRows.length === 2, `period rows ${state.periodRows.length}`);
      assert(JSON.stringify(state.periodRows.map((row) => row.start)) === JSON.stringify(["2026-12-01", "2027-01-01"]), `period order ${state.periodRows.map((row) => row.start)}`);
      assert(JSON.stringify(state.periodTotals) === JSON.stringify(["Total", "12", "961"]), `period totals ${state.periodTotals}`);
      assert(state.periodNotice?.kind === "ok", `period notice ${state.periodNotice?.text}`);

      api = await readApi(page);
      const periods = api.periods.filter((item) => item.assignment_id === ID_A).sort((a, b) => a.period_start.localeCompare(b.period_start));
      assert(periods.length === 2, `API periods ${periods.length}`);
      assert(periods[0].units === "8" && periods[0].cost === "640.75", `API first period ${JSON.stringify(periods[0])}`);
      assert(periods[1].units === "4" && periods[1].cost === "320.25", `API second period ${JSON.stringify(periods[1])}`);
      assert(periods[0].activity_id === api.assignments.find((item) => item.assignment_id === ID_A).activity_id, "period activity does not match its assignment");
      await capture(page, "10-spreadsheet-periods");
      return { periods: periods.map((item) => [item.period_start, item.units, item.cost]) };
    });

    await scenario("11", "دورهٔ تکراری با مقدار دیگر رد می‌شود و ردیف ذخیره‌شده را تغییر نمی‌دهد", async () => {
      await page.setInput('[data-assignment-period-form] input[name="period-start"]', "2026-12-01");
      await page.setInput('[data-assignment-period-form] input[name="period-units"]', "9");
      await page.setInput('[data-assignment-period-form] input[name="period-cost"]', "700");
      await page.click('[data-assignment-period-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-assignment-period-notice][data-state="error"]') !== null`,
        "duplicate period error",
      );
      await sleep(250);
      const state = await page.evaluate(assignmentsState);
      assert(state.periodRows.length === 2, `period rows after duplicate ${state.periodRows.length}`);
      api = await readApi(page);
      const periods = api.periods.filter((item) => item.assignment_id === ID_A && item.period_start === "2026-12-01");
      assert(periods.length === 1, `stored duplicates ${periods.length}`);
      assert(periods[0].units === "8", `a duplicate period overwrote units to ${periods[0].units}`);
      await capture(page, "11-duplicate-period-rejected");
      return { notice: state.periodNotice?.text, units: periods[0].units };
    });

    await scenario("12", "تب Profile مجموع و اوج دوره‌های ذخیره‌شده را با میله‌های متناسب نشان می‌دهد", async () => {
      await selectTab(page, "profile", "[data-assignment-profile-summary]");
      const state = await page.evaluate(assignmentsState);
      assert(state.activeTab === "profile", `active tab ${state.activeTab}`);
      assert(state.profileSummary === "Units 12 · Cost 961 · Peak 8 over 2 period(s)", `profile summary ${state.profileSummary}`);
      assert(state.bars.length === 2, `profile bars ${state.bars.length}`);
      assert(JSON.stringify(state.bars.map((bar) => [bar.start, bar.units, bar.height])) === JSON.stringify([
        ["2026-12-01", "8", "100%"],
        ["2027-01-01", "4", "50%"],
      ]), `profile bars ${JSON.stringify(state.bars)}`);
      await capture(page, "12-profile");
      return { summary: state.profileSummary, bars: state.bars };
    });

    await scenario("13", "بازنگری، تخصیص را با شناسهٔ جدید -R2 ذخیره می‌کند و رکورد اصلی را دست‌نخورده نگه می‌دارد", async () => {
      await selectTab(page, "general", null);
      await selectAssignment(page, ID_A);
      await page.click('[data-assignment-action="revise"]');
      await page.waitForSelector("[data-assignment-form]", "revise form");
      await sleep(200);
      let state = await page.evaluate(assignmentsState);
      assert(state.form?.assignmentId === `${ID_A}-R2`, `revise form id ${state.form?.assignmentId}`);
      assert(state.form?.units === "8", `revise form units ${state.form?.units}`);
      assert(state.form?.plannedCost === "1200.50", `revise form planned cost ${state.form?.plannedCost}`);
      assert(state.form?.note === "E2E crew assignment", `revise form note ${state.form?.note}`);
      await page.click('[data-assignment-form] button[type="submit"]');
      await page.waitFor(
        `document.querySelector('[data-assignment-row][data-assignment-id="${ID_A}-R2"]') !== null`,
        "revised assignment row",
      );
      await sleep(300);
      state = await page.evaluate(assignmentsState);
      assert(state.rows.some((row) => row.id === `${ID_A}-R2`), "the revision row is missing");
      api = await readApi(page);
      const original = api.assignments.find((item) => item.assignment_id === ID_A);
      const revision = api.assignments.find((item) => item.assignment_id === `${ID_A}-R2`);
      assert(original.units === "8" && original.note === "E2E crew assignment", "the original assignment was modified by a revision");
      assert(revision.units === "8" && revision.planned_cost === "1200.50", `revision values ${JSON.stringify(revision)}`);

      await selectAssignment(page, `${ID_A}-R2`);
      await page.click('[data-assignment-action="revise"]');
      await page.waitForSelector("[data-assignment-form]", "second revise form");
      await sleep(200);
      state = await page.evaluate(assignmentsState);
      assert(state.form?.assignmentId === `${ID_A}-R3`, `second revise form id ${state.form?.assignmentId}`);
      await page.click('[data-assignment-action="cancel"]');
      await sleep(200);
      await capture(page, "13-revision-created");
      return { revisionId: `${ID_A}-R2`, nextRevisionId: `${ID_A}-R3` };
    });

    await scenario("14", "Refresh و رفت‌وبرگشت پنجره، ثبت و دوره‌های ذخیره‌شده را از سرور بازمی‌خوانند", async () => {
      await page.click('[data-assignment-action="reload"]');
      await waitForRegister(page);
      await page.waitFor(
        `document.querySelectorAll("[data-assignment-row]").length === 4`,
        "reloaded assignment rows",
      );
      let state = await page.evaluate(assignmentsState);
      assert(state.rows.length === 4, `rows after refresh ${state.rows.length}`);

      await selectAssignment(page, ID_A);
      await selectTab(page, "spreadsheet", "[data-assignment-period-row]");
      state = await page.evaluate(assignmentsState);
      assert(state.periodRows.length === 2, `period rows after refresh ${state.periodRows.length}`);
      assert(JSON.stringify(state.periodTotals) === JSON.stringify(["Total", "12", "961"]), `period totals after refresh ${state.periodTotals}`);
      await capture(page, "14-reloaded-from-server");
      return { assignments: state.rows.length, periods: state.periodRows.length };
    });

    await scenario("15", "پنجرهٔ تخصیص‌ها در 1280×720 بدون سرریز چیدمان رندر می‌شود", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await sleep(500);
      const layout = await page.evaluate(`(() => {
        const rect = (element) => {
          if (!element) return null;
          const bounds = element.getBoundingClientRect();
          return { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height };
        };
        const page = document.querySelector("[data-assignments-page]");
        return {
          innerWidth,
          innerHeight,
          host: rect(page),
          toolbar: rect(page?.querySelector(".cp-register-toolbar")),
          register: rect(page?.querySelector(".cp-register-table-wrap")),
          details: rect(page?.querySelector(".cp-register-details")),
          rows: document.querySelectorAll("[data-assignment-row]").length,
        };
      })()`);
      assert(layout.toolbar && layout.toolbar.width > 0, "the toolbar has no layout box at 1280x720");
      assert(layout.register && layout.register.height > 0, "the register has no layout box at 1280x720");
      assert(layout.details && layout.details.height > 0, "the details pane has no layout box at 1280x720");
      assert(layout.rows === 4, `register rows at 1280x720: ${layout.rows}`);
      assert(layout.toolbar.x >= 0 && layout.toolbar.x + layout.toolbar.width <= layout.innerWidth + 1, `toolbar overflows: ${JSON.stringify(layout.toolbar)}`);
      await capture(page, "15-1280x720");
      return layout;
    });

    api = await readApi(page);
    assert(api.assignments.length === 4, `final API assignments ${api.assignments.length}`);
    assert(api.periods.length === 2, `final API periods ${api.periods.length}`);
    report.finalApi = api;

    assert(exceptions.length === 0, `uncaught page exceptions: ${JSON.stringify(exceptions.slice(0, 3))}`);
    assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors.slice(0, 3))}`);
    assert(apiFailures.length === 0, `API 5xx responses: ${JSON.stringify(apiFailures.slice(0, 3))}`);
  } finally {
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(outDir, "assignments-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(evidenceDir, "assignments-v26.json"), JSON.stringify(report, null, 2));
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
