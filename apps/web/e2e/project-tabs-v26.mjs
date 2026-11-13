#!/usr/bin/env node
/**
 * PRJ-003 browser acceptance: project open/close/switch and tab lifecycle.
 *
 * Every assertion is made against the real full-stack preview: the tab strip is
 * compared with GET /api/projects on the same session, each switch goes through
 * POST /api/projects/{id}/open, and the project record is re-read by the
 * bootstrap so a revision changed elsewhere is visible after switching.
 *
 * Covered here:
 *  - one tab per opened project, an explicit active tab and no close on the last;
 *  - opening a second project from the register adds an active tab;
 *  - each project tab restores its own desktop window set;
 *  - unsaved edits ask before a switch is allowed and survive a cancelled switch;
 *  - closing an inactive tab keeps the context, closing the active tab switches;
 *  - a reload restores the open tab set and the active project;
 *  - switching re-reads the project record and a stale revision is rejected;
 *  - Persian RTL at 1280x720;
 *  - a Viewer can only switch among the projects the session lists.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4195 node e2e/project-tabs-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4174";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-13";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "project-tabs-v26");
const evidenceDir = join(
  artifactsDir, "..", "..", "..", "..",
  "docs", "workspace", "evidence", `project-tabs-v26-${evidenceDate}`,
);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const FIRST = "preview-rps-01";
const SECOND = "preview-nse-02";
const stamp = Date.now().toString(36).toUpperCase();

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

const tabState = `(() => ({
  count: document.querySelectorAll("[data-project-tab]").length,
  tabs: [...document.querySelectorAll("[data-project-tab]")].map((tab) => ({
    id: tab.dataset.projectTab,
    active: tab.getAttribute("aria-selected") === "true",
    name: tab.querySelector("[data-project-tab-open]")?.textContent?.trim() ?? null,
  })),
  closeButtons: document.querySelectorAll("[data-project-tab-close]").length,
  title: document.querySelector("[data-titlebar-session]")?.textContent?.trim() ?? null,
  windows: [...document.querySelectorAll("[data-window-tab]")].map((tab) => tab.dataset.windowTab),
  dir: document.documentElement.dir,
  lang: document.documentElement.lang,
  overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
}))()`;

async function capture(page, name) {
  const file = `project-tabs-v26/${name}.png`;
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
        headers: { "Content-Type": "application/json", "Idempotency-Key": "e2e-prj3-" + Math.random().toString(36).slice(2) },
        ${body === undefined ? "" : `body: JSON.stringify(${JSON.stringify(body)}),`}
      });
      return { status: response.status, body: await response.json().catch(() => null) };
    })()`,
    { awaitPromise: true },
  );
}

async function readApi(page) {
  return page.evaluate(`(async () => {
    const session = await fetch("/api/session").then((response) => response.json());
    const list = await fetch("/api/projects").then((response) => response.json());
    return { session, projects: list.projects ?? [] };
  })()`, { awaitPromise: true });
}

async function loginAs(page, label) {
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
  const hasPersonas = await page.evaluate('Boolean(document.querySelector(".persona"))');
  if (!hasPersonas) {
    await page.evaluate(`(async () => {
      await fetch("/preview/logout", { method: "POST", redirect: "manual" });
    })()`, { awaitPromise: true });
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, ".persona", "persona cards after sign out");
  }
  const clicked = await page.evaluate(`(() => {
    const button = [...document.querySelectorAll("form button")].find((item) => (item.textContent || "").trim().startsWith(${JSON.stringify(label)}));
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `${label} login button is missing`);
  await page.waitForSelector(`[data-project-id="${FIRST}"]`, "project selection");
  await page.click(`[data-project-id="${FIRST}"]`);
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
  await page.waitForSelector(".cp-project-tabs [data-project-tab]", "project tabs");
  await sleep(900);
}

async function ensureWorkspace(page) {
  const picker = await page.evaluate(`Boolean(document.querySelector('[data-project-id="${FIRST}"]'))`);
  if (picker) await page.click(`[data-project-id="${FIRST}"]`);
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows", 30000);
  await page.waitForSelector(".cp-project-tabs [data-project-tab]", "project tabs", 20000);
  await sleep(600);
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
  await page.evaluate(`(() => { document.querySelector("[data-context-menu-portal]")?.remove(); })()`);
  const clicked = await page.evaluate(`(() => {
    const buttons = [...document.querySelectorAll('[data-menu="project"]')];
    const button = buttons.find((entry) => entry.getClientRects().length > 0) ?? buttons[0];
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, "Project menu button is missing");
  await page.waitForSelector("[data-project-register]", "project register", 20000);
  await page.waitFor(`document.querySelectorAll("[data-project-row]").length > 0`, "project rows", 20000);
  await sleep(500);
}

async function clickSelector(page, selector, label = selector) {
  const clicked = await page.evaluate(`(() => {
    const element = document.querySelector(${JSON.stringify(selector)});
    if (!element || element.hasAttribute("disabled")) return false;
    element.click();
    return true;
  })()`);
  assert(clicked, `missing enabled control: ${label}`);
  await sleep(450);
}

async function waitActive(page, projectId, label) {
  await page.waitFor(
    `document.querySelector('[data-project-tab="${projectId}"]')?.getAttribute("aria-selected") === "true"`,
    label,
    20000,
  );
  await sleep(800);
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
    contract: "cubi-prj-003-project-tabs.v1",
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
    const initial = await readApi(page);
    const first = initial.projects.find((project) => project.project_id === FIRST);
    const second = initial.projects.find((project) => project.project_id === SECOND);
    assert(first && second, "the preview must list both demo projects");

    await scenario("01", "The open project has one tab and no close control", async () => {
      const state = await page.evaluate(tabState);
      check("prj3-single-tab", "one tab exists for the opened project", state.count === 1, state);
      check("prj3-single-active", "that tab is active and named from the session list",
        state.tabs[0]?.id === FIRST && state.tabs[0]?.active === true && state.tabs[0]?.name === first.name,
        state.tabs);
      check("prj3-single-no-close", "the last project tab has no close control", state.closeButtons === 0, state.closeButtons);
      check("prj3-single-title", "the title bar names the same project", state.title === first.name, state);
      await capture(page, "01-single-project-tab");
      return { tab: state.tabs[0], title: state.title };
    });

    await scenario("02", "Opening a second project adds an active tab", async () => {
      await openProjectWindow(page);
      await clickSelector(page, `[data-project-open="${SECOND}"]`, `open ${SECOND}`);
      await waitActive(page, SECOND, "second project tab active");
      const state = await page.evaluate(tabState);
      check("prj3-second-tab", "the strip now holds both projects",
        state.tabs.map((tab) => tab.id).join(",") === `${FIRST},${SECOND}`, state.tabs);
      check("prj3-second-active", "the opened project is the active tab and the title",
        state.tabs.find((tab) => tab.id === SECOND)?.active === true && state.title === second.name, state);
      check("prj3-second-close", "both tabs are closable", state.closeButtons === 2, state.closeButtons);
      check("prj3-second-open-write", "the switch went through the server open endpoint",
        writes.some((entry) => entry.method === "POST" && entry.url === `/api/projects/${SECOND}/open`), writes);
      await capture(page, "02-two-project-tabs");
      return { tabs: state.tabs, title: state.title };
    });

    await scenario("03", "Each project tab restores its own desktop window set", async () => {
      await clickSelector(page, `[data-project-tab-open="${FIRST}"]`, "first project tab");
      await waitActive(page, FIRST, "first project active");
      await clickSelector(page, '[data-window-close="project"]', "close Projects window on the first project");
      await page.waitFor('!document.querySelector(\'[data-window-tab="project"]\')', "Projects window closed", 15000);
      const firstWindows = await page.evaluate('[...document.querySelectorAll("[data-window-tab]")].map((tab) => tab.dataset.windowTab)');
      check("prj3-windows-first-closed", "the first project lost its Projects window",
        !firstWindows.includes("project") && firstWindows.includes("schedule"), firstWindows);

      await clickSelector(page, `[data-project-tab-open="${SECOND}"]`, "second project tab");
      await waitActive(page, SECOND, "second project active");
      const secondWindows = await page.evaluate('[...document.querySelectorAll("[data-window-tab]")].map((tab) => tab.dataset.windowTab)');
      check("prj3-windows-second-default", "a project opened for the first time gets the default window set",
        secondWindows.includes("project") && secondWindows.includes("schedule"), secondWindows);

      await clickSelector(page, `[data-project-tab-open="${FIRST}"]`, "first project tab again");
      await waitActive(page, FIRST, "first project active again");
      const restored = await page.evaluate('[...document.querySelectorAll("[data-window-tab]")].map((tab) => tab.dataset.windowTab)');
      check("prj3-windows-restored", "switching back restores the first project's window set",
        !restored.includes("project") && restored.includes("schedule"), restored);
      await capture(page, "03-per-project-windows");
      return { firstWindows, secondWindows, restored };
    });

    await scenario("04", "Unsaved project work asks before a switch and survives cancel", async () => {
      await openProjectWindow(page);
      await clickSelector(page, `[data-project-row="${FIRST}"]`, "first project row");
      await clickSelector(page, '[data-project-selection] [data-project-settings]', "project settings");
      await page.waitForSelector("[data-project-settings-panel]", "settings panel", 15000);

      await page.evaluate('window.confirm = () => false');
      await clickSelector(page, `[data-project-tab-open="${SECOND}"]`, "second tab while dirty");
      await sleep(900);
      const cancelled = await page.evaluate(tabState);
      check("prj3-dirty-cancel", "a cancelled switch keeps the current project and its editor",
        cancelled.tabs.find((tab) => tab.id === FIRST)?.active === true &&
          (await page.evaluate('Boolean(document.querySelector("[data-project-settings-panel]"))')),
        cancelled.tabs);

      await page.evaluate('window.confirm = () => true');
      await clickSelector(page, `[data-project-tab-open="${SECOND}"]`, "second tab after confirmation");
      await waitActive(page, SECOND, "second project after confirmation");
      const confirmed = await page.evaluate(tabState);
      check("prj3-dirty-confirm", "accepting the prompt switches projects",
        confirmed.tabs.find((tab) => tab.id === SECOND)?.active === true, confirmed.tabs);
      check("prj3-dirty-discarded", "the discarded editor is not left on the new project",
        !(await page.evaluate('Boolean(document.querySelector("[data-project-settings-panel]"))')));
      await page.evaluate('delete window.confirm');
      await capture(page, "04-dirty-switch");
      return { cancelled: cancelled.tabs, confirmed: confirmed.tabs };
    });

    await scenario("05", "Closing an inactive tab keeps context; closing the active tab switches", async () => {
      // Active is the second project. Close the first (inactive) tab.
      const writesBeforeClose = writes.length;
      await clickSelector(page, `[data-project-tab-close="${FIRST}"]`, "close inactive first tab");
      await page.waitFor('document.querySelectorAll("[data-project-tab]").length === 1', "one tab after inactive close", 15000);
      const afterInactive = await page.evaluate(tabState);
      check("prj3-close-inactive", "closing an inactive tab keeps the open project",
        afterInactive.count === 1 && afterInactive.tabs[0]?.id === SECOND &&
          afterInactive.tabs[0]?.active === true && afterInactive.title === second.name, afterInactive);
      check("prj3-close-inactive-no-open", "closing a tab issues no project open transition",
        writes.length === writesBeforeClose, writes.slice(writesBeforeClose));

      // Reopen the first project, then close the active one.
      await openProjectWindow(page);
      await clickSelector(page, `[data-project-open="${FIRST}"]`, "reopen first project");
      await waitActive(page, FIRST, "first project reopened active");
      const writesBeforeActiveClose = writes.length;
      await clickSelector(page, `[data-project-tab-close="${FIRST}"]`, "close active first tab");
      await waitActive(page, SECOND, "neighbour project after active close");
      const afterActive = await page.evaluate(tabState);
      check("prj3-close-active", "closing the active tab opens its neighbour",
        afterActive.count === 1 && afterActive.tabs[0]?.id === SECOND &&
          afterActive.tabs[0]?.active === true && afterActive.title === second.name, afterActive);
      check("prj3-close-active-authorized", "the neighbour was re-authorized through the server",
        writes.slice(writesBeforeActiveClose).some((entry) => entry.method === "POST" && entry.url === `/api/projects/${SECOND}/open`),
        writes.slice(writesBeforeActiveClose));
      await capture(page, "05-close-active-tab");
      return { afterInactive, afterActive };
    });

    await scenario("06", "A reload restores the open tabs and the active project", async () => {
      await openProjectWindow(page);
      await clickSelector(page, `[data-project-open="${FIRST}"]`, "open first project before reload");
      await waitActive(page, FIRST, "first project active before reload");
      await page.reload(".cp-project-tabs [data-project-tab]", "project tabs after reload");
      await sleep(1200);
      const state = await page.evaluate(tabState);
      check("prj3-reload-tabs", "the same two tabs return after a full reload",
        state.tabs.map((tab) => tab.id).join(",") === `${SECOND},${FIRST}`, state.tabs);
      check("prj3-reload-active", "the active project is restored",
        state.tabs.find((tab) => tab.id === FIRST)?.active === true && state.title === first.name, state);
      await capture(page, "06-reload-restores-tabs");
      return { tabs: state.tabs, title: state.title };
    });

    await scenario("07", "Switching re-reads the project record and rejects a stale revision", async () => {
      const before = await api(page, "GET", `/api/projects/${FIRST}`);
      const revision = before.body?.project?.settings_revision ?? 0;
      const renamed = `${first.name} — switched ${stamp}`;
      const saved = await api(page, "PATCH", `/api/projects/${FIRST}`, {
        name: renamed,
        description: first.description ?? "",
        start_date: first.start_date ?? null,
        date_system: first.date_system ?? "gregorian",
        expected_revision: revision,
      });
      check("prj3-revision-saved", "an external save advances the project revision",
        saved.status === 200 && saved.body?.project?.settings_revision === revision + 1,
        { status: saved.status, revision, body: saved.body?.project?.settings_revision });

      await clickSelector(page, `[data-project-tab-open="${SECOND}"]`, "switch away");
      await waitActive(page, SECOND, "second project before returning");
      await clickSelector(page, `[data-project-tab-open="${FIRST}"]`, "switch back");
      await waitActive(page, FIRST, "first project after returning");
      await openProjectWindow(page);
      const refreshed = await page.evaluate(`(() => {
        const row = document.querySelector('[data-project-row="${FIRST}"]');
        const card = document.querySelector("[data-project-selection]");
        const fields = [...(card?.querySelectorAll(".cp-project-selection-fields > div") ?? [])].map((field) => ({
          label: field.querySelector("span")?.textContent?.trim() ?? null,
          value: field.querySelector("strong")?.textContent?.trim() ?? null,
        }));
        return {
          cells: [...(row?.querySelectorAll("td") ?? [])].map((cell) => (cell.textContent || "").trim()),
          revision: fields.find((field) => /Configuration revision|ویرایش تنظیمات/.test(field.label ?? ""))?.value ?? null,
        };
      })()`);
      check("prj3-revision-refreshed", "the register shows the record saved by the other writer",
        refreshed.cells[1] === renamed, refreshed);
      check("prj3-revision-visible", "the selection card shows the advanced configuration revision",
        refreshed.revision === `R${revision + 1}`, refreshed);

      const stale = await api(page, "PATCH", `/api/projects/${FIRST}`, {
        name: "Stale writer",
        description: "",
        start_date: first.start_date ?? null,
        date_system: first.date_system ?? "gregorian",
        expected_revision: revision,
      });
      check("prj3-revision-stale", "a stale revision cannot overwrite the newer record",
        stale.status === 409, { status: stale.status, body: stale.body });
      await capture(page, "07-revision-refresh");
      return { revision, renamed, stale: stale.status };
    });

    await scenario("08", "Persian renders the project tabs right-to-left at 1280x720", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await page.waitFor("document.documentElement.clientWidth === 1280", "1280 viewport");
      await setLanguage(page, "fa");
      const state = await page.evaluate(tabState);
      const aria = await page.evaluate('document.querySelector(".cp-project-tabs")?.getAttribute("aria-label") ?? ""');
      check("prj3-fa-rtl", "the Persian workspace is right-to-left", state.dir === "rtl" && state.lang === "fa", state);
      check("prj3-fa-tabs", "both project tabs remain and one is active",
        state.count === 2 && state.tabs.filter((tab) => tab.active).length === 1, state.tabs);
      check("prj3-fa-label", "the tab strip is labelled in Persian", aria === "پروژه‌های باز", aria);
      check("prj3-fa-overflow", "the strip does not overflow the 1280 viewport", state.overflow <= 1, state.overflow);
      await capture(page, "08-project-tabs-fa-rtl-1280");
      await setLanguage(page, "en");
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
      await page.waitFor("document.documentElement.clientWidth === 1440", "1440 viewport");
      return { dir: state.dir, aria, overflow: state.overflow };
    });

    await scenario("09", "A Viewer can only switch among the session's projects", async () => {
      await loginAs(page, "Viewer");
      const viewer = await readApi(page);
      const authorized = viewer.projects.map((project) => project.project_id);
      const state = await page.evaluate(tabState);
      check("prj3-viewer-tabs", "every open tab belongs to the Viewer's own list",
        state.count >= 1 && state.tabs.every((tab) => authorized.includes(tab.id)),
        { tabs: state.tabs, authorized });
      const denied = await api(page, "POST", "/api/projects/not-a-member-project/open");
      check("prj3-viewer-denied", "opening a project the session does not list is denied",
        denied.status === 403 || denied.status === 404, { status: denied.status, body: denied.body });
      await capture(page, "09-viewer-project-tabs");
      return { tabs: state.tabs, authorized, denied: denied.status };
    });

    const failedChecks = checks.filter((entry) => !entry.ok);
    summary.passed = checks.length - failedChecks.length;
    summary.failed = failedChecks.length;
    summary.status = failedChecks.length ? "failed" : "passed";
    summary.finishedAt = new Date().toISOString();

    const contractFile = join(evidenceDir, "contract.json");
    writeFileSync(contractFile, JSON.stringify(summary, null, 2));
    writeFileSync(join(outDir, "contract.json"), JSON.stringify(summary, null, 2));
    const lines = [
      `# PRJ-003 project tab lifecycle acceptance — ${evidenceDate}`,
      "",
      `Tested code SHA: \`${testedCodeSha}\``,
      `Contract: \`${summary.contract}\``,
      "",
      ...checks.map((entry) => `${entry.ok ? "PASS" : "FAIL"} — ${entry.name}`),
      "",
      `Scenarios: ${scenarios.length}; checks: ${checks.length}; passed: ${summary.passed}; failed: ${summary.failed}`,
      `Exceptions: ${exceptions.length}; console errors: ${consoleErrors.length}; API 5xx: ${apiFailures.length}`,
    ];
    writeFileSync(join(evidenceDir, "CHECKLIST.md"), `${lines.join("\n")}\n`);

    log(`\n${summary.passed} of ${checks.length} project-tab checks passed`);
    if (failedChecks.length) process.exitCode = 1;
  } finally {
    await chrome.close?.();
  }
}

main().catch((error) => {
  process.stderr.write(`${error?.stack ?? error}\n`);
  process.exitCode = 1;
});
