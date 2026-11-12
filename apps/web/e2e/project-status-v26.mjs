#!/usr/bin/env node
/**
 * Browser E2E for the Version 26 project status lifecycle.
 *
 * The Project settings panel must show the status stored on the authoritative
 * project record, change it through project-status-api.v1 under the
 * configuration revision guard, and render the append-only event history that
 * the server recorded. Everything runs against the real local full-stack
 * preview on preview-rps-01; expected values are read from /api/projects on the
 * same session, so no value is mocked or injected into the page.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 \
 *   CUBI_TESTED_CODE_SHA=<code commit> \
 *   node e2e/project-status-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const outDir = join(artifactsDir, "project-status-v26");
const evidenceDir = join(
  artifactsDir,
  "..",
  "..",
  "..",
  "..",
  "docs",
  "workspace",
  "evidence",
  `project-status-v26-${evidenceDate}`,
);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";

const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const scenarios = [];
const screenshots = [];
const cells = [];

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

async function capture(page, name) {
  const file = `project-status-v26/${name}.png`;
  await page.screenshot(file);
  copyFileSync(join(artifactsDir, file), join(evidenceDir, `${name}.png`));
  screenshots.push(`${name}.png`);
  return file;
}

async function setLanguage(page, locale) {
  const changed = await page.evaluate(`(() => {
    const select = document.querySelector("[data-workspace-language]");
    if (!select) return false;
    if (select.value === ${JSON.stringify(locale)}) return true;
    select.value = ${JSON.stringify(locale)};
    select.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  assert(changed, `language selector did not accept ${locale}`);
  await sleep(900);
}

async function loginAs(page, label, locale = "en") {
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
  const hasPersonas = await page.evaluate('Boolean(document.querySelector(".persona"))');
  if (!hasPersonas) {
    const logoutStatus = await page.evaluate(
      `fetch("/preview/logout", { method: "POST", redirect: "manual" }).then((response) => response.status)`,
      { awaitPromise: true },
    );
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
  await sleep(1400);
  await setLanguage(page, locale);
}

async function openProjectSettings(page) {
  const opened = await page.evaluate(`(() => {
    const buttons = [...document.querySelectorAll('[data-menu="project"]')];
    const button = buttons.find((item) => item.getClientRects().length > 0) ?? buttons[0];
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(opened, "Project menu button is missing");
  await page.waitForSelector(".cp-project-table", "project table");
  await sleep(600);
  const clicked = await page.evaluate(`(() => {
    const button = document.querySelector('#cp-details [data-project-settings]');
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, "project settings button is missing");
  await page.waitForSelector("[data-project-settings-panel]", "project settings panel");
  await page.waitFor(
    `document.querySelector('[data-project-settings-form] [name="name"]')?.value.length > 0`,
    "project settings values",
    15000,
  );
  await sleep(400);
}

const settingsState = `(() => {
  const panel = document.querySelector("[data-project-settings-panel]");
  if (!panel) return null;
  return {
    statusValue: panel.querySelector('[data-project-status-select]')?.value ?? null,
    statusMessage: panel.querySelector("[data-project-settings-status]")?.textContent?.trim() ?? null,
    statusState: panel.querySelector("[data-project-settings-status]")?.dataset?.state ?? null,
    revision: panel.querySelector("[data-project-settings-revision]")?.textContent?.trim() ?? null,
    historyRows: [...panel.querySelectorAll("[data-project-status-history-row]")].map((row) => (row.textContent || "").trim()),
    historyEmpty: !panel.querySelector("[data-project-status-history-empty]")?.hidden,
    historyTitle: panel.querySelector("[data-project-status-history] h3")?.textContent?.trim() ?? null,
    panelText: (panel.textContent || "").replace(/\\s+/g, " ").trim(),
  };
})()`;

async function readSettings(page) {
  return page.evaluate(settingsState);
}

async function readApi(page) {
  return page.evaluate(`(async () => {
    const project = await fetch("/api/projects/${PROJECT}").then((response) => response.json());
    const history = await fetch("/api/projects/${PROJECT}/status-history").then((response) => response.json());
    return { project: project.project ?? null, events: history.events ?? [] };
  })()`, { awaitPromise: true });
}

async function saveStatus(page, value) {
  await page.setSelect("[data-project-settings-panel] [data-project-status-select]", value);
  await page.click("[data-project-status-save]");
  await page.waitFor(
    `(() => {
      const panel = document.querySelector("[data-project-settings-panel]");
      const message = panel?.querySelector("[data-project-settings-status]");
      return message && message.dataset.state === "success";
    })()`,
    "status save confirmation",
    15000,
  );
  await page.waitFor(
    `document.querySelectorAll("[data-project-status-history-row]").length >= 1`,
    "recorded status event",
    15000,
  );
  await sleep(400);
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
    contract: "cubi-project-status-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    capturedAt: new Date().toISOString(),
    cells,
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
  };

  try {
    cells.push({ viewport: "1366x768", locale: "en", direction: "ltr", role: "project_admin" });
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 768, deviceScaleFactor: 1, mobile: false });
    await sleep(300);
    await loginAs(page, "Project administrator");
    await openProjectSettings(page);

    await scenario("01", "the settings panel shows the stored status and an empty event history", async () => {
      const api = await readApi(page);
      const state = await readSettings(page);
      assert(state, "settings panel state is missing");
      assert(state.statusValue === (api.project.status ?? "active"), `status select ${state.statusValue} vs API ${api.project.status}`);
      assert(state.statusValue === "active", `expected the seeded project to be active, got ${state.statusValue}`);
      assert(state.historyEmpty, "the history is not marked empty before any change");
      assert(state.historyRows.length === 0, `history rows ${state.historyRows.length}`);
      assert(state.historyTitle === "Status history", `history title ${state.historyTitle}`);
      assert(state.revision === `Configuration revision R${api.project.settings_revision ?? 0}`, `revision ${state.revision}`);
      await capture(page, "01-status-empty-history");
      return { status: state.statusValue, revision: state.revision };
    });

    await scenario("02", "changing the status stores the row and records an event with the actor and revision", async () => {
      await saveStatus(page, "planned");
      const api = await readApi(page);
      const state = await readSettings(page);
      assert(state.statusValue === "planned", `status select ${state.statusValue}`);
      assert(state.statusMessage === "Status saved.", `status message ${state.statusMessage}`);
      assert(state.revision === "Configuration revision R1", `revision ${state.revision}`);
      assert(state.historyRows.length === 1, `history rows ${state.historyRows.length}`);
      assert(/Active → Planned/.test(state.historyRows[0]), `history row ${state.historyRows[0]}`);
      assert(/preview-admin/.test(state.historyRows[0]), `history row actor ${state.historyRows[0]}`);
      assert(/R1/.test(state.historyRows[0]), `history row revision ${state.historyRows[0]}`);
      assert(api.project.status === "planned", `API status ${api.project.status}`);
      assert(api.project.settings_revision === 1, `API settings revision ${api.project.settings_revision}`);
      assert(api.events.length === 1, `API events ${api.events.length}`);
      assert(api.events[0].from_status === "active" && api.events[0].to_status === "planned", "API event transition");
      assert(api.events[0].actor_user_id === "preview-admin", `API actor ${api.events[0].actor_user_id}`);
      await capture(page, "02-status-saved");
      return { status: api.project.status, eventId: api.events[0].event_id };
    });

    await scenario("03", "a full reload re-reads the same status and append-only history", async () => {
      await page.navigate(`${baseUrl}/app?view=live`, "form", "workspace reset");
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows after reload");
      await sleep(1200);
      await setLanguage(page, "en");
      await openProjectSettings(page);
      const state = await readSettings(page);
      assert(state.statusValue === "planned", `status after reload ${state.statusValue}`);
      assert(state.revision === "Configuration revision R1", `revision after reload ${state.revision}`);
      assert(state.historyRows.length === 1, `history after reload ${state.historyRows.length}`);
      await capture(page, "03-status-reload");
      return { status: state.statusValue, history: state.historyRows.length };
    });

    await scenario("04", "the same record redraws at 1920x1080", async () => {
      cells.push({ viewport: "1920x1080", locale: "en", direction: "ltr", role: "project_admin" });
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false });
      await sleep(600);
      const state = await readSettings(page);
      assert(state.statusValue === "planned", `status at 1920 ${state.statusValue}`);
      assert(state.historyRows.length === 1, `history rows at 1920 ${state.historyRows.length}`);
      const fits = await page.evaluate(`(() => {
        const panel = document.querySelector("[data-project-settings-panel]");
        const rect = panel.getBoundingClientRect();
        return { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom, width: innerWidth, height: innerHeight };
      })()`);
      assert(fits.left >= 0 && fits.top >= 0 && fits.right <= fits.width && fits.bottom <= fits.height, `panel outside the viewport ${JSON.stringify(fits)}`);
      await capture(page, "04-status-1920");
      return { viewport: "1920x1080", status: state.statusValue };
    });

    await scenario("05", "a viewer reads the history but the server rejects a status change", async () => {
      cells.push({ viewport: "1366x768", locale: "en", direction: "ltr", role: "viewer" });
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 768, deviceScaleFactor: 1, mobile: false });
      await sleep(300);
      await loginAs(page, "Viewer");
      await openProjectSettings(page);
      let state = await readSettings(page);
      assert(state.historyRows.length === 1, `viewer history rows ${state.historyRows.length}`);
      await page.setSelect("[data-project-settings-panel] [data-project-status-select]", "inactive");
      await page.click("[data-project-status-save]");
      await page.waitFor(
        `(() => {
          const message = document.querySelector("[data-project-settings-panel] [data-project-settings-status]");
          return message && message.dataset.state === "error";
        })()`,
        "viewer write rejection",
        15000,
      );
      state = await readSettings(page);
      assert(/permission/.test(state.statusMessage), `viewer message ${state.statusMessage}`);
      assert(state.statusValue === "planned", `viewer select reverted to ${state.statusValue}`);
      const direct = await page.evaluate(
        `fetch("/api/projects/${PROJECT}/status", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: "inactive", expected_revision: 1 }) }).then(async (response) => ({ status: response.status, body: await response.json().catch(() => null) }))`,
        { awaitPromise: true },
      );
      assert(direct.status === 403, `direct viewer write status ${direct.status}`);
      await capture(page, "05-status-viewer");
      return { viewerEvents: state.historyRows.length, directStatus: direct.status };
    });

    await scenario("06", "the status history fits the Persian 1280x720 layout", async () => {
      cells.push({ viewport: "1280x720", locale: "fa", direction: "rtl", role: "project_admin" });
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await sleep(300);
      await loginAs(page, "Project administrator", "fa");
      await openProjectSettings(page);
      const state = await readSettings(page);
      assert(state.statusValue === "planned", `fa status ${state.statusValue}`);
      assert(state.historyTitle === "تاریخچهٔ وضعیت", `fa history title ${state.historyTitle}`);
      assert(state.historyRows.length === 1, `fa history rows ${state.historyRows.length}`);
      assert(/فعال → برنامه‌ریزی‌شده/.test(state.historyRows[0]), `fa history row ${state.historyRows[0]}`);
      const rtl = await page.evaluate(`(() => {
        const panel = document.querySelector("[data-project-settings-panel]");
        const rect = panel.getBoundingClientRect();
        const list = document.querySelector("[data-project-status-history-list]");
        return {
          direction: getComputedStyle(panel).direction,
          right: rect.right, bottom: rect.bottom, width: innerWidth, height: innerHeight,
          historyVisible: Boolean(list && list.getClientRects().length),
        };
      })()`);
      assert(rtl.direction === "rtl", `panel direction ${rtl.direction}`);
      assert(rtl.right <= rtl.width && rtl.bottom <= rtl.height, `panel outside the viewport ${JSON.stringify(rtl)}`);
      assert(rtl.historyVisible, "status history is not visible in the Persian layout");
      await capture(page, "06-status-fa-1280");
      return { locale: "fa", status: state.statusValue };
    });

    assert(exceptions.length === 0, `exceptions: ${exceptions.join(" | ")}`);
    assert(consoleErrors.length === 0, `console errors: ${consoleErrors.join(" | ")}`);
    assert(apiFailures.length === 0, `API failures: ${JSON.stringify(apiFailures)}`);
  } finally {
    writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(evidenceDir, "report.json"), JSON.stringify(report, null, 2));
    chrome.stop();
  }

  log(`\nProject status E2E: ${scenarios.length}/${scenarios.length} scenarios passed`);
  log(`Screenshots: ${screenshots.join(", ")}`);
}

main().catch((error) => {
  process.stderr.write(`${error && error.stack ? error.stack : error}\n`);
  process.exitCode = 1;
});
