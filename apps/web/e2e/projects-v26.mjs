#!/usr/bin/env node
/**
 * Browser E2E for the Version 26 Projects window and Project Details tabs.
 *
 * It drives the real local full-stack preview: the project table must list the
 * session's own projects, the open row must come from the authoritative
 * project record, the Project Details tabs must show that record's fields, and
 * opening another project must re-read its workspace from the server. The
 * expected values are fetched from /api/projects on the same session, so no
 * fixture data is injected into the page.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4174 node e2e/projects-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4174";
const outDir = join(artifactsDir, "projects-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", "projects-v26-2026-11-10");
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

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

const projectState = `(() => {
  const workspace = document.querySelector(".cp-workspace");
  const details = document.querySelector("#cp-details");
  const rows = [...document.querySelectorAll("[data-project-row]")].map((row) => ({
    id: row.dataset.projectRow,
    current: row.getAttribute("aria-current") === "true",
    cells: [...row.querySelectorAll("td")].map((cell) => (cell.textContent || "").trim()),
    openButton: Boolean(row.querySelector("[data-project-open]")),
    currentBadge: Boolean(row.querySelector(".cp-project-current")),
  }));
  const activePanel = details?.querySelector("[data-project-detail-panel]:not([hidden])");
  return {
    activeMenu: workspace?.dataset.activeMenu ?? null,
    projectContext: workspace?.dataset.project ?? null,
    header: (document.querySelector(".cp-project")?.textContent || "").trim(),
    rows,
    pending: Boolean(document.querySelector("[data-project-metadata-pending]")),
    detailsTitle: details?.querySelector("h2")?.textContent?.trim() ?? null,
    detailsSubtitle: details?.querySelector(".cp-activity-details-heading span")?.textContent?.trim() ?? null,
    activeTab: details?.querySelector('[data-project-detail-tab][aria-selected="true"]')?.dataset.projectDetailTab ?? null,
    fields: [...(details?.querySelectorAll(".cp-activity-detail-fields .cp-activity-detail-field") ?? [])].map((field) => ({
      label: field.querySelector("span")?.textContent?.trim() ?? null,
      value: field.querySelector("strong")?.textContent?.trim() ?? null,
    })),
    activePanel: activePanel ? (activePanel.textContent || "").replace(/\\s+/g, " ").trim() : null,
    wbsRows: document.querySelectorAll(".cp-project-wbs-row").length,
    dialog: Boolean(document.querySelector("[data-project-settings-panel]")),
  };
})()`;

const settingsState = `(() => {
  const panel = document.querySelector("[data-project-settings-panel]");
  if (!panel) return null;
  const form = panel.querySelector("[data-project-settings-form]");
  return {
    heading: panel.querySelector("h2")?.textContent?.trim() ?? null,
    revision: panel.querySelector("[data-project-settings-revision]")?.textContent?.trim() ?? null,
    name: form?.querySelector('[name="name"]')?.value ?? null,
    description: form?.querySelector('[name="description"]')?.value ?? null,
    startDate: form?.querySelector('[name="start_date"]')?.value ?? null,
    dateSystem: form?.querySelector('[name="date_system"]')?.value ?? null,
    calendar: form?.querySelector('[name="primary_calendar_id"]')?.value ?? null,
    status: panel.querySelector("[data-project-settings-status]")?.textContent?.trim() ?? null,
  };
})()`;

async function capture(page, name) {
  const file = `projects-v26/${name}.png`;
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

async function openProjectWindow(page) {
  const clicked = await page.evaluate(`(() => {
    const buttons = [...document.querySelectorAll('[data-menu="project"]')];
    const button = buttons.find((entry) => entry.getClientRects().length > 0) ?? buttons[0];
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, "Project menu button is missing");
  await page.waitForSelector(".cp-project-table", "project table");
  await page.waitFor(
    `!document.querySelector("[data-project-metadata-pending]") && document.querySelectorAll("[data-project-row]").length > 0`,
    "authoritative project record",
    15000,
  );
  await sleep(500);
}

async function readProjects(page) {
  return page.evaluate(`(async () => {
    const list = await fetch("/api/projects").then((response) => response.json());
    const one = await fetch("/api/projects/preview-rps-01").then((response) => response.json());
    const second = await fetch("/api/projects/preview-nse-02").then((response) => response.json());
    return { projects: list.projects ?? [], rps: one.project ?? null, nse: second.project ?? null };
  })()`, { awaitPromise: true });
}

function field(state, label) {
  return state.fields.find((entry) => entry.label === label)?.value ?? null;
}

async function clickProject(page, projectId) {
  const clicked = await page.evaluate(`(() => {
    const button = document.querySelector('[data-project-open=${JSON.stringify(projectId)}]');
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `Open button not found for ${projectId}`);
  await page.waitFor(
    `document.querySelector(".cp-workspace")?.dataset.project === ${JSON.stringify(projectId)}`,
    `project ${projectId} to open`,
    20000,
  );
  await page.waitFor(
    `!document.querySelector("[data-project-metadata-pending]") && document.querySelector('.cp-project-table tbody tr[aria-current="true"]')?.dataset.projectRow === ${JSON.stringify(projectId)}`,
    `authoritative record for ${projectId}`,
    15000,
  );
  await sleep(700);
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
    contract: "cubi-projects-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    capturedAt: new Date().toISOString(),
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
    await openProjectWindow(page);
    const api = await readProjects(page);
    assert(api.projects.length === 2, `the session should expose two seeded projects, got ${api.projects.length}`);
    assert(api.rps && api.nse, "the seeded project records are not readable");

    await scenario("01", "پنجرهٔ Projects دقیقاً پروژه‌های مجاز نشست را از سرور نشان می‌دهد", async () => {
      const state = await page.evaluate(projectState);
      assert(state.activeMenu === "project", `active menu is ${state.activeMenu}`);
      assert(state.rows.length === api.projects.length, `table rows ${state.rows.length} vs API ${api.projects.length}`);
      const apiById = new Map(api.projects.map((project) => [project.project_id, project]));
      for (const row of state.rows) {
        const expected = apiById.get(row.id);
        assert(expected, `table row ${row.id} is not in the session list`);
        assert(row.cells[0] === expected.project_id, `row ${row.id} shows project id ${row.cells[0]}`);
        assert(row.cells[1] === expected.name, `row ${row.id} shows name ${row.cells[1]} instead of ${expected.name}`);
        assert(!row.current === row.openButton, `row ${row.id} open/current controls are inconsistent`);
      }
      const current = state.rows.filter((row) => row.current);
      assert(current.length === 1 && current[0].id === "preview-rps-01", `current row is ${current.map((row) => row.id)}`);
      assert(current[0].currentBadge && !current[0].openButton, "the open project must show the Open badge instead of a switch button");
      assert(!state.pending, "the table still says the authoritative record is unread");
      assert(state.wbsRows > 0, "the project structure summary is empty");
      await capture(page, "01-project-table-from-session");
      return { rows: state.rows.map((row) => ({ id: row.id, name: row.cells[1], current: row.current })), wbsRows: state.wbsRows };
    });

    await scenario("02", "نوار عنوان و تب General جزئیات، رکورد مرجع پروژه را نشان می‌دهند", async () => {
      const state = await page.evaluate(projectState);
      assert(state.header === api.rps.name, `title bar shows ${state.header} instead of ${api.rps.name}`);
      assert(state.detailsTitle === "Project Details", `details title is ${state.detailsTitle}`);
      assert(state.detailsSubtitle === `${api.rps.name} — ${api.rps.project_id}`, `details subtitle is ${state.detailsSubtitle}`);
      assert(state.activeTab === "general", `active tab is ${state.activeTab}`);
      assert(field(state, "Project Name") === api.rps.name, `Project Name field ${field(state, "Project Name")}`);
      assert(field(state, "Project ID") === api.rps.project_id, `Project ID field ${field(state, "Project ID")}`);
      assert(field(state, "Start Date") === api.rps.start_date, `Start Date field ${field(state, "Start Date")}`);
      assert(field(state, "Date System") === "Gregorian", `Date System field ${field(state, "Date System")}`);
      assert(field(state, "Primary Calendar") === (api.rps.primary_calendar_id || "—"), `Primary Calendar field ${field(state, "Primary Calendar")}`);
      assert(field(state, "Settings revision") === `R${api.rps.settings_revision ?? 0}`, `Settings revision field ${field(state, "Settings revision")}`);
      assert(!/not been read yet/.test(state.activePanel ?? ""), "the General tab still reports an unread record");
      await capture(page, "02-project-details-general");
      return { header: state.header, fields: state.fields };
    });

    await scenario("03", "تب Dates تاریخ برنامه‌ای را نشان می‌دهد و تب Settings مرزهای واقعی رکورد را اعلام می‌کند", async () => {
      await page.click('[data-project-detail-tab="dates"]');
      await sleep(300);
      let state = await page.evaluate(projectState);
      assert(state.activeTab === "dates", `active tab after Dates click is ${state.activeTab}`);
      assert(field(state, "Planned Start") === api.rps.start_date, `Planned Start field ${field(state, "Planned Start")}`);
      assert(/scheduling core/.test(state.activePanel ?? ""), "the Dates tab does not explain where forecast and finish dates come from");
      await capture(page, "03-project-details-dates");

      await page.click('[data-project-detail-tab="settings"]');
      await sleep(300);
      state = await page.evaluate(projectState);
      assert(state.activeTab === "settings", `active tab after Settings click is ${state.activeTab}`);
      assert(field(state, "Settings revision") === `R${api.rps.settings_revision ?? 0}`, `Settings revision field ${field(state, "Settings revision")}`);
      assert(/not stored on the project record/.test(state.activePanel ?? ""), "the Settings tab invents fiscal, price or numbering controls");
      await capture(page, "04-project-details-settings");
      return { dates: "Planned Start shown", settings: "honest boundary shown" };
    });

    await scenario("04", "ویرایش پروژه همان رکورد مرجع را با نسخهٔ تنظیمات باز می‌کند", async () => {
      await page.evaluate(`(() => {
        const button = document.querySelector('#cp-details [data-project-settings]');
        if (!button) return false;
        button.click();
        return true;
      })()`);
      await page.waitForSelector("[data-project-settings-panel]", "project settings panel");
      await page.waitFor(
        `document.querySelector('[data-project-settings-form] [name="name"]')?.value === ${JSON.stringify(api.rps.name)}`,
        "project settings values",
        15000,
      );
      const state = await page.evaluate(settingsState);
      assert(state, "settings panel state is missing");
      assert(state.name === api.rps.name, `settings name is ${state.name}`);
      assert(state.startDate === api.rps.start_date, `settings start date is ${state.startDate}`);
      assert(state.dateSystem === api.rps.date_system, `settings date system is ${state.dateSystem}`);
      assert(state.revision === `Configuration revision R${api.rps.settings_revision ?? 0}`, `settings revision is ${state.revision}`);
      assert(state.status === "", `settings panel reports ${state.status}`);
      await capture(page, "05-project-settings-dialog");
      await page.click("[data-project-settings-close]");
      await sleep(250);
      const closed = await page.evaluate(`!document.querySelector("[data-project-settings-panel]")`);
      assert(closed, "settings panel did not close");
      return { revision: state.revision, name: state.name };
    });

    await scenario("05", "بازکردن پروژهٔ دوم از جدول، محیط کار همان پروژه را از سرور دوباره می‌خواند", async () => {
      await clickProject(page, "preview-nse-02");
      const state = await page.evaluate(projectState);
      assert(state.projectContext === "preview-nse-02", `workspace context is ${state.projectContext}`);
      assert(state.header === api.nse.name, `title bar shows ${state.header} instead of ${api.nse.name}`);
      const current = state.rows.find((row) => row.current);
      assert(current?.id === "preview-nse-02", `current row is ${current?.id}`);
      assert(field(state, "Project Name") === api.nse.name, `Project Name field ${field(state, "Project Name")}`);
      assert(field(state, "Date System") === "Jalali", `Date System field ${field(state, "Date System")}`);
      assert(field(state, "Settings revision") === `R${api.nse.settings_revision ?? 0}`, `Settings revision field ${field(state, "Settings revision")}`);
      assert(field(state, "Start Date") === api.nse.start_date, `Start Date field ${field(state, "Start Date")}`);
      await capture(page, "06-switched-to-second-project");
      return { context: state.projectContext, header: state.header, current: current?.id };
    });

    await scenario("06", "بازگشت به پروژهٔ اول، رکورد و جدول قبلی را بازمی‌گرداند", async () => {
      await clickProject(page, "preview-rps-01");
      const state = await page.evaluate(projectState);
      assert(state.projectContext === "preview-rps-01", `workspace context is ${state.projectContext}`);
      assert(state.header === api.rps.name, `title bar shows ${state.header} instead of ${api.rps.name}`);
      assert(field(state, "Project Name") === api.rps.name, `Project Name field ${field(state, "Project Name")}`);
      assert(field(state, "Date System") === "Gregorian", `Date System field ${field(state, "Date System")}`);
      const current = state.rows.find((row) => row.current);
      assert(current?.id === "preview-rps-01", `current row is ${current?.id}`);
      assert(exceptions.length === 0, `uncaught page exceptions: ${JSON.stringify(exceptions.slice(0, 3))}`);
      assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors.slice(0, 3))}`);
      assert(apiFailures.length === 0, `API 5xx responses: ${JSON.stringify(apiFailures.slice(0, 3))}`);
      await capture(page, "07-restored-first-project");
      return { context: state.projectContext, header: state.header, exceptions: exceptions.length, consoleErrors: consoleErrors.length };
    });
  } finally {
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(outDir, "projects-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(evidenceDir, "projects-v26.json"), JSON.stringify(report, null, 2));
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
