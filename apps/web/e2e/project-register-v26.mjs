#!/usr/bin/env node
/**
 * PRJ-001 browser acceptance: the Projects register.
 *
 * Runs against the real full-stack preview. Every assertion reads the project
 * rows from /api/projects on the same session, so the register may only show
 * persisted records: no fixture is injected into the page and no hierarchy is
 * inferred from a project name.
 *
 * Covered here:
 *  - the session list, tenant scope and Business Domain classification;
 *  - the Business Domain tree (the CUBI replacement for the P6 EPS level),
 *    expansion/collapse and two-way selection with the table;
 *  - search, domain filter and sort without inventing rows;
 *  - a selection that previews a project without opening it;
 *  - a revision-guarded Business Domain update, stale conflict and invalid
 *    classification over the public API;
 *  - Persian RTL at 1280x720 and a Viewer session.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4195 node e2e/project-register-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4174";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-13";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "project-register-v26");
const evidenceDir = join(
  artifactsDir,
  "..",
  "..",
  "..",
  "..",
  "docs",
  "workspace",
  "evidence",
  `project-register-v26-${evidenceDate}`,
);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const stamp = Date.now().toString(36).toUpperCase();
const fixtureId = `E2E-PRJ-${stamp}`;

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
    return details;
  } catch (error) {
    scenarios.push({ id, name, status: "fail", at: new Date().toISOString(), durationMs: Date.now() - started, error: String(error?.stack ?? error) });
    log(`  FAIL ${id}: ${error}`);
    throw error;
  }
}

const registerState = `(() => {
  const register = document.querySelector("[data-project-register]");
  const selection = document.querySelector("[data-project-selection]");
  return {
    present: Boolean(register),
    loading: register?.getAttribute("aria-busy") === "true",
    count: document.querySelector("[data-project-register-count]")?.textContent?.trim() ?? null,
    rows: [...document.querySelectorAll("[data-project-row]")].map((row) => ({
      id: row.dataset.projectRow,
      current: row.getAttribute("aria-current") === "true",
      selected: row.getAttribute("aria-selected") === "true",
      domain: row.dataset.projectDomain ?? "",
      cells: [...row.querySelectorAll("td")].map((cell) => (cell.textContent || "").trim()),
      openButton: Boolean(row.querySelector("[data-project-open]")),
    })),
    tree: [...document.querySelectorAll("[data-project-domain-group]")].map((group) => ({
      key: group.dataset.projectDomainGroup,
      expanded: group.querySelector("[data-project-domain-toggle]")?.getAttribute("aria-expanded") === "true",
      label: group.querySelector(".cp-project-domain-name")?.textContent?.trim() ?? null,
      count: group.querySelector(".cp-project-domain-count")?.textContent?.trim() ?? null,
      projects: [...group.querySelectorAll("[data-project-select]")].map((button) => ({
        id: button.dataset.projectSelect,
        pressed: button.getAttribute("aria-pressed") === "true",
        label: button.querySelector("strong")?.textContent?.trim() ?? null,
      })),
    })),
    selection: selection ? {
      header: selection.querySelector("header span")?.textContent?.trim() ?? null,
      fields: [...selection.querySelectorAll(".cp-project-selection-fields > div")].map((field) => ({
        label: field.querySelector("span")?.textContent?.trim() ?? null,
        value: field.querySelector("strong")?.textContent?.trim() ?? null,
      })),
      openTarget: selection.querySelector("[data-project-open]")?.dataset.projectOpen ?? null,
      hasSettings: Boolean(selection.querySelector("[data-project-settings]")),
    } : null,
    noMatches: Boolean(document.querySelector("[data-project-no-matches]")),
    detailsSubtitle: document.querySelector("#cp-details .cp-activity-details-heading span")?.textContent?.trim() ?? null,
    lang: document.documentElement.lang,
    dir: document.documentElement.dir,
    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  };
})()`;

async function capture(page, name) {
  const file = `project-register-v26/${name}.png`;
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
        headers: { "Content-Type": "application/json", "Idempotency-Key": "e2e-prj1-" + Math.random().toString(36).slice(2) },
        ${body === undefined ? "" : `body: JSON.stringify(${JSON.stringify(body)}),`}
      });
      return { status: response.status, body: await response.json().catch(() => null) };
    })()`,
    { awaitPromise: true },
  );
}

async function loginAs(page, label) {
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
  const hasPersonas = await page.evaluate('Boolean(document.querySelector(".persona"))');
  if (!hasPersonas) {
    const logoutStatus = await page.evaluate(`(async () => {
      const response = await fetch("/preview/logout", { method: "POST", redirect: "manual" });
      return response.status;
    })()`, { awaitPromise: true });
    assert([0, 200, 302, 303].includes(logoutStatus), `unexpected logout status ${logoutStatus}`);
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, ".persona", "persona cards after sign out");
  }
  const clicked = await page.evaluate(`(() => {
    const button = [...document.querySelectorAll("form button")].find((item) => (item.textContent || "").trim().startsWith(${JSON.stringify(label)}));
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `${label} login button is missing`);
  await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
  await page.click('[data-project-id="preview-rps-01"]');
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
  await sleep(1200);
}

async function ensureWorkspace(page) {
  const picker = await page.evaluate('Boolean(document.querySelector("[data-project-id=\\"preview-rps-01\\"]"))');
  if (picker) {
    await page.click('[data-project-id="preview-rps-01"]');
  }
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows", 30000);
  await sleep(900);
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

async function openProjectWindow(page) {
  await page.evaluate(`(() => { const menu = document.querySelector("[data-context-menu-portal]"); menu?.remove(); })()`);
  const clicked = await page.evaluate(`(() => {
    const buttons = [...document.querySelectorAll('[data-menu="project"]')];
    const button = buttons.find((entry) => entry.getClientRects().length > 0) ?? buttons[0];
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, "Project menu button is missing");
  await page.waitForSelector("[data-project-register]", "project register", 20000);
  await page.waitFor(
    `Boolean(document.querySelector("[data-project-register-count]")) && document.querySelectorAll("[data-project-row]").length > 0`,
    "project register rows",
    20000,
  );
  await sleep(500);
}

async function readApi(page) {
  return page.evaluate(`(async () => {
    const session = await fetch("/api/session").then((response) => response.json());
    const list = await fetch("/api/projects").then((response) => response.json());
    return { session, projects: list.projects ?? [] };
  })()`, { awaitPromise: true });
}

async function setSearch(page, value) {
  await page.evaluate(`(() => {
    const input = document.querySelector("[data-project-search]");
    if (!input) return false;
    input.value = ${JSON.stringify(value)};
    input.dispatchEvent(new Event("input", { bubbles: true }));
    return true;
  })()`);
  await sleep(350);
}

async function clickSelector(page, selector) {
  const clicked = await page.evaluate(`(() => {
    const element = document.querySelector(${JSON.stringify(selector)});
    if (!element) return false;
    element.click();
    return true;
  })()`);
  assert(clicked, `selector not found: ${selector}`);
  await sleep(350);
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
    contract: "cubi-prj-001-project-register.v1",
    testedCodeSha,
    gitHead: gitHead(),
    evidenceCommitSha,
    baseUrl,
    fixtureId,
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
    await openProjectWindow(page);
    const initial = await readApi(page);

    await scenario("01", "The register shows exactly the session-authorized projects with their persisted Business Domain", async () => {
      const state = await page.evaluate(registerState);
      check("prj1-present", "the Projects window renders the register", state.present);
      check("prj1-count", "the register reports every project in the session list",
        state.count === `${initial.projects.length} of ${initial.projects.length} projects`,
        { count: state.count, api: initial.projects.length });
      const apiIds = initial.projects.map((project) => project.project_id).sort();
      const rowIds = state.rows.map((row) => row.id).sort();
      check("prj1-exact-rows", "table rows are exactly the API projects", JSON.stringify(rowIds) === JSON.stringify(apiIds), { rowIds, apiIds });
      check("prj1-tenant", "every listed project belongs to the session tenant",
        initial.projects.every((project) => project.tenant_id === initial.session.tenant_id),
        { tenant: initial.session.tenant_id, tenants: [...new Set(initial.projects.map((project) => project.tenant_id))] });
      const apiById = new Map(initial.projects.map((project) => [project.project_id, project]));
      check("prj1-domain-cells", "each row shows its stored Business Domain",
        state.rows.every((row) => row.cells[2] === (apiById.get(row.id)?.business_domain === "oil_gas" ? "Oil & Gas" : (apiById.get(row.id)?.business_domain ? apiById.get(row.id).business_domain[0].toUpperCase() + apiById.get(row.id).business_domain.slice(1) : "Not classified"))),
        { rows: state.rows.map((row) => ({ id: row.id, domain: row.domain, cell: row.cells[2] })) });
      const expectedGroups = [...new Set(initial.projects.map((project) => project.business_domain || "__unclassified__"))].sort();
      check("prj1-tree-groups", "the tree groups the persisted domains",
        JSON.stringify(state.tree.map((group) => group.key).sort()) === JSON.stringify(expectedGroups),
        { groups: state.tree.map((group) => group.key), expectedGroups });
      check("prj1-tree-projects", "the tree contains every project once",
        JSON.stringify(state.tree.flatMap((group) => group.projects.map((project) => project.id)).sort()) === JSON.stringify(apiIds));
      const current = state.rows.filter((row) => row.current);
      check("prj1-current", "the open project is the only aria-current row",
        current.length === 1 && current[0].id === PROJECT && !current[0].openButton && otherRowsHaveOpen(state.rows, PROJECT));
      check("prj1-selection-default", "the open project is selected before any click",
        state.selection?.fields.find((field) => field.label === "Project ID")?.value === PROJECT && state.selection?.header === "Currently open",
        { selection: state.selection });
      await capture(page, "01-register-domain-tree");
      return { count: state.count, groups: state.tree.map((group) => ({ key: group.key, count: group.count })) };
    });

    await scenario("02", "Search narrows the tree and the table to matching persisted rows", async () => {
      await setSearch(page, "nse-02");
      let state = await page.evaluate(registerState);
      check("prj1-search-rows", "only the matching project row remains",
        state.rows.length === 1 && state.rows[0].id === "preview-nse-02", { rows: state.rows.map((row) => row.id) });
      check("prj1-search-count", "the count reports the filtered result", state.count === `1 of ${initial.projects.length} projects`, { count: state.count });
      check("prj1-search-tree", "the tree shows only the matching domain group",
        state.tree.length === 1 && state.tree[0].projects.length === 1 && state.tree[0].projects[0].id === "preview-nse-02",
        { tree: state.tree });
      await capture(page, "02-search-narrows-register");

      await setSearch(page, "no-such-project");
      state = await page.evaluate(registerState);
      check("prj1-search-empty", "an unmatched search shows a no-match state, not fabricated rows",
        state.noMatches && state.rows.length === 0 && state.tree.length === 0 && state.count === `0 of ${initial.projects.length} projects`,
        { count: state.count, rows: state.rows.length });
      await capture(page, "03-search-no-matches");

      await clickSelector(page, "[data-project-filter-reset]");
      state = await page.evaluate(registerState);
      check("prj1-search-reset", "Clear filters restores every authorized row",
        state.rows.length === initial.projects.length && state.count === `${initial.projects.length} of ${initial.projects.length} projects` && !state.noMatches);
      return { filtered: "1 of 2" };
    });

    await scenario("03", "Business Domain filter and sort reorder only the visible view", async () => {
      await page.evaluate(`(() => {
        const select = document.querySelector("[data-project-domain-filter]");
        select.value = "infrastructure";
        select.dispatchEvent(new Event("change", { bubbles: true }));
      })()`);
      await sleep(350);
      let state = await page.evaluate(registerState);
      check("prj1-domain-filter", "the domain filter keeps only that domain",
        state.rows.length === 1 && state.rows[0].id === PROJECT && state.rows[0].domain === "infrastructure",
        { rows: state.rows.map((row) => ({ id: row.id, domain: row.domain })) });

      await clickSelector(page, "[data-project-filter-reset]");
      await page.evaluate(`(() => {
        const select = document.querySelector("[data-project-sort]");
        select.value = "start_date";
        select.dispatchEvent(new Event("change", { bubbles: true }));
      })()`);
      await sleep(350);
      state = await page.evaluate(registerState);
      const apiById = new Map(initial.projects.map((project) => [project.project_id, project]));
      const expected = [...initial.projects]
        .sort((a, b) => String(a.start_date ?? "").localeCompare(String(b.start_date ?? "")))
        .map((project) => project.project_id);
      check("prj1-sort-start", "Start date sorts the persisted rows ascending",
        JSON.stringify(state.rows.map((row) => row.id)) === JSON.stringify(expected),
        { rows: state.rows.map((row) => row.id), expected, api: expected.map((id) => apiById.get(id)?.start_date) });
      await capture(page, "04-domain-filter-and-sort");
      await page.evaluate(`(() => {
        const select = document.querySelector("[data-project-sort]");
        select.value = "name";
        select.dispatchEvent(new Event("change", { bubbles: true }));
      })()`);
      await sleep(300);
      return { expected };
    });

    await scenario("04", "Selecting a project previews its record without opening it", async () => {
      await clickSelector(page, '[data-project-select="preview-nse-02"]');
      const state = await page.evaluate(registerState);
      const field = (label) => state.selection?.fields.find((entry) => entry.label === label)?.value ?? null;
      check("prj1-select-nse", "the tree selection marks the chosen project, not the open one",
        state.rows.find((row) => row.id === "preview-nse-02")?.selected === true &&
          state.rows.find((row) => row.id === PROJECT)?.current === true &&
          state.tree.flatMap((group) => group.projects).find((project) => project.id === "preview-nse-02")?.pressed === true,
        { rows: state.rows.map((row) => ({ id: row.id, selected: row.selected, current: row.current })) });
      check("prj1-selection-record", "the selection card shows the persisted record",
        field("Project ID") === "preview-nse-02" &&
          field("Business Domain") === "Industrial" &&
          field("Organization") === initial.session.tenant_id &&
          /R\d+/.test(field("Data revision") ?? "") &&
          state.selection?.header === "Not open" &&
          state.selection?.openTarget === "preview-nse-02",
        { selection: state.selection });
      check("prj1-no-open", "selection does not change the open project", state.detailsSubtitle?.includes(PROJECT) === true || state.detailsSubtitle?.includes("Riverside") === true, { detailsSubtitle: state.detailsSubtitle });
      await capture(page, "05-selection-preview");

      await clickSelector(page, '[data-project-selection] [data-project-open="preview-nse-02"]');
      await page.waitFor(`document.querySelector(".cp-workspace")?.dataset.project === "preview-nse-02"`, "project switch", 25000);
      await page.waitFor(`Boolean(document.querySelector("[data-project-selection]"))`, "register after switch", 20000);
      await sleep(700);
      const opened = await page.evaluate(registerState);
      check("prj1-open-from-selection", "Open project switches the workspace and marks the row current",
        opened.rows.find((row) => row.id === "preview-nse-02")?.current === true &&
          opened.selection?.header === "Currently open" && opened.selection?.hasSettings === true,
        { current: opened.rows.filter((row) => row.current).map((row) => row.id), selection: opened.selection });
      await capture(page, "06-selection-opened");
      await clickSelector(page, '[data-project-select="preview-rps-01"]');
      await clickSelector(page, '[data-project-selection] [data-project-open="preview-rps-01"]');
      await page.waitFor(`document.querySelector(".cp-workspace")?.dataset.project === "preview-rps-01"`, "back to first project", 25000);
      await sleep(700);
      return { opened: "preview-nse-02" };
    });

    await scenario("05", "The tree collapses and keyboard selection works on the register", async () => {
      await page.evaluate(`document.querySelector('[data-project-row="preview-rps-01"]')?.focus()`);
      await page.cdp.send("Input.dispatchKeyEvent", { type: "rawKeyDown", windowsVirtualKeyCode: 13, key: "Enter", code: "Enter" });
      await page.cdp.send("Input.dispatchKeyEvent", { type: "keyUp", windowsVirtualKeyCode: 13, key: "Enter", code: "Enter" });
      await sleep(400);
      let state = await page.evaluate(registerState);
      check("prj1-keyboard-select", "Enter on a focused row selects that project",
        state.rows.find((row) => row.id === PROJECT)?.selected === true,
        { rows: state.rows.map((row) => ({ id: row.id, selected: row.selected })) });
      await clickSelector(page, '[data-project-domain-toggle="infrastructure"]');
      state = await page.evaluate(registerState);
      const collapsed = state.tree.find((group) => group.key === "infrastructure");
      check("prj1-collapse", "the domain group collapses without losing its rows",
        collapsed?.expanded === false && collapsed.projects.length === 0 && state.rows.length === initial.projects.length,
        { group: collapsed });
      await capture(page, "07-collapsed-domain");
      await clickSelector(page, '[data-project-domain-toggle="infrastructure"]');
      state = await page.evaluate(registerState);
      check("prj1-expand", "the group expands again",
        state.tree.find((group) => group.key === "infrastructure")?.expanded === true &&
          (state.tree.find((group) => group.key === "infrastructure")?.projects.length ?? 0) > 0);
      return { keyboard: "Enter", collapsed: true };
    });

    await scenario("06", "Business Domain edits are persisted, revision-guarded and validated", async () => {
      const created = await api(page, "POST", "/api/projects", {
        project_id: fixtureId,
        name: `E2E Domain Project ${stamp}`,
        description: "Created by the PRJ-001 browser acceptance suite.",
        start_date: "2026-11-20",
        date_system: "gregorian",
        business_domain: "construction",
      });
      check("prj1-create", "a project created through the API starts in its chosen domain",
        created.status === 201, { status: created.status, body: created.body });
      const listed = await readApi(page);
      const stored = listed.projects.find((project) => project.project_id === fixtureId);
      check("prj1-create-persisted", "the new record is in the authorized list with its domain",
        stored?.business_domain === "construction", { stored });

      await page.reload(".cp-workspace", "reload with the new project");
      await ensureWorkspace(page);
      await openProjectWindow(page);
      let state = await page.evaluate(registerState);
      check("prj1-create-tree", "the reloaded tree contains the new Construction group",
        state.tree.some((group) => group.key === "construction" && group.projects.some((project) => project.id === fixtureId)) &&
          state.rows.some((row) => row.id === fixtureId && row.cells[2] === "Construction"),
        { groups: state.tree.map((group) => ({ key: group.key, projects: group.projects.map((project) => project.id) })) });

      const updated = await api(page, "PATCH", `/api/projects/${fixtureId}`, {
        name: `E2E Domain Project ${stamp}`,
        description: "Created by the PRJ-001 browser acceptance suite.",
        start_date: "2026-11-20",
        date_system: "gregorian",
        business_domain: "energy",
        expected_revision: 0,
      });
      check("prj1-update", "a revision-guarded PATCH moves the project to Energy",
        updated.status === 200 && updated.body?.project?.business_domain === "energy" && updated.body?.project?.settings_revision === 1,
        { status: updated.status, project: updated.body?.project });

      const stale = await api(page, "PATCH", `/api/projects/${fixtureId}`, {
        name: `Stale ${stamp}`,
        business_domain: "other",
        expected_revision: 0,
      });
      check("prj1-stale", "a stale configuration revision is rejected without overwriting",
        stale.status === 409 && stale.body?.code === "PROJECT_REVISION_CONFLICT", { status: stale.status, body: stale.body });

      const invalid = await api(page, "PATCH", `/api/projects/${fixtureId}`, {
        name: `E2E Domain Project ${stamp}`,
        business_domain: "north-region",
        expected_revision: 1,
      });
      check("prj1-invalid-domain", "an unknown classification is rejected",
        invalid.status === 400 && invalid.body?.code === "PROJECT_BUSINESS_DOMAIN_INVALID", { status: invalid.status, body: invalid.body });

      const reread = await api(page, "GET", `/api/projects/${fixtureId}`);
      check("prj1-update-persisted", "the stored record still holds the last accepted domain",
        reread.body?.project?.business_domain === "energy" && reread.body?.project?.settings_revision === 1,
        { project: reread.body?.project });

      await page.reload(".cp-workspace", "reload after the domain update");
      if (!(await page.evaluate('Boolean(document.querySelector("[data-project-register]"))'))) {
        await openProjectWindow(page);
      }
      state = await page.evaluate(registerState);
      check("prj1-update-tree", "the Energy group now contains the project and Construction is gone",
        state.tree.some((group) => group.key === "energy" && group.projects.some((project) => project.id === fixtureId)) &&
          !state.tree.some((group) => group.key === "construction"),
        { groups: state.tree.map((group) => group.key) });
      await capture(page, "08-persisted-domain-update");
      return { fixtureId, domain: "energy", settingsRevision: 1 };
    });

    await scenario("07", "Persian renders the register right-to-left at 1280x720", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await page.waitFor("document.documentElement.clientWidth === 1280", "1280 viewport");
      await setLanguage(page, "fa");
      if (!(await page.evaluate('Boolean(document.querySelector("[data-project-register]"))'))) {
        await openProjectWindow(page);
      }
      const state = await page.evaluate(registerState);
      check("prj1-rtl", "the Persian workspace is right-to-left", state.dir === "rtl" && state.lang === "fa", { dir: state.dir, lang: state.lang });
      const labels = [state.tree[0]?.label, ...state.rows.map((row) => row.cells[2])].join(" ");
      check("prj1-fa-labels", "the tree and rows use Persian domain labels",
        /زیرساخت|صنعتی|انرژی|ساخت‌وساز|نفت و گاز|سایر|طبقه‌بندی‌نشده/.test(labels) && !/Infrastructure|Industrial|Energy|Construction/.test(labels),
        { labels });
      check("prj1-fa-controls", "search, filter and selection surfaces are present in Persian",
        (await page.evaluate('Boolean(document.querySelector("[data-project-search]"))')) &&
          (await page.evaluate('Boolean(document.querySelector("[data-project-domain-filter]"))')) &&
          (await page.evaluate('Boolean(document.querySelector("[data-project-selection]"))')));
      check("prj1-fa-overflow", "the register does not overflow the 1280 viewport", state.overflow <= 1, { overflow: state.overflow });
      await capture(page, "09-register-fa-rtl-1280");
      await setLanguage(page, "en");
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
      await page.waitFor("document.documentElement.clientWidth === 1440", "1440 viewport");
      return { dir: state.dir, overflow: state.overflow };
    });

    await scenario("08", "A Viewer sees the authorized register but cannot change a Business Domain", async () => {
      await loginAs(page, "Viewer");
      await openProjectWindow(page);
      const viewer = await readApi(page);
      const state = await page.evaluate(registerState);
      check("prj1-viewer-list", "the Viewer sees exactly the session-authorized records",
        JSON.stringify(state.rows.map((row) => row.id).sort()) === JSON.stringify(viewer.projects.map((project) => project.project_id).sort()),
        { rows: state.rows.map((row) => row.id), api: viewer.projects.map((project) => project.project_id) });
      check("prj1-viewer-tree", "the Viewer gets the same Business Domain hierarchy", state.tree.length > 0 && state.tree.every((group) => group.projects.length > 0));
      const denied = await api(page, "PATCH", `/api/projects/${fixtureId}`, {
        name: "Viewer edit",
        business_domain: "other",
        expected_revision: 1,
      });
      check("prj1-viewer-denied", "a Viewer PATCH is denied by the server",
        denied.status === 403 && String(denied.body?.code ?? "").includes("AUTHORIZATION"), { status: denied.status, body: denied.body });
      await capture(page, "10-viewer-register");
      return { status: denied.status };
    });

    const failedChecks = checks.filter((entry) => !entry.ok);
    summary.passed = checks.length - failedChecks.length;
    summary.failed = failedChecks.length;
    summary.finishedAt = new Date().toISOString();
    summary.status = failedChecks.length === 0 ? "passed" : "failed";
    writeFileSync(join(outDir, "project-register-v26.json"), JSON.stringify(summary, null, 2));
    writeFileSync(join(evidenceDir, "contract.json"), JSON.stringify(summary, null, 2));
    writeFileSync(
      join(evidenceDir, "CHECKLIST.md"),
      [
        `# PRJ-001 project register acceptance — ${evidenceDate}`,
        "",
        `Tested code SHA: \`${testedCodeSha}\``,
        `Contract: \`${summary.contract}\``,
        "",
        ...checks.map((entry) => `${entry.ok ? "PASS" : "FAIL"} — ${entry.name}${entry.ok ? "" : `\n  ${JSON.stringify(entry.detail)}`}`),
      ].join("\n"),
    );
    if (failedChecks.length) {
      console.error(`\n${failedChecks.length} of ${checks.length} checks failed`);
      process.exitCode = 1;
    } else {
      console.log(`\nAll ${checks.length} project-register checks passed`);
    }
  } catch (error) {
    summary.status = "error";
    summary.error = String(error?.stack ?? error);
    writeFileSync(join(outDir, "project-register-v26.json"), JSON.stringify(summary, null, 2));
    writeFileSync(join(evidenceDir, "contract.json"), JSON.stringify(summary, null, 2));
    throw error;
  } finally {
    page.cdp.close();
    await chrome.stop();
  }
}

function otherRowsHaveOpen(rows, currentId) {
  return rows.filter((row) => row.id !== currentId).every((row) => row.openButton);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
