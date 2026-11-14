#!/usr/bin/env node
/**
 * Browser E2E for the V26 Project Details fields implemented by PRJ-002.
 *
 * Covers OBS responsible manager, web-site, leveling priority and project
 * checkout against the real local full-stack preview. Values are read back from
 * the project lifecycle API and the canonical schedule-settings API on the same
 * session, so persistence is proven by the server rather than by the DOM.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4243 \
 *   CUBI_EVIDENCE_DATE=2026-11-14 \
 *   CUBI_TESTED_CODE_SHA=<code commit> \
 *   node e2e/project-details-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4243";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-14";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const outDir = join(artifactsDir, "project-details-v26");
const evidenceDir = join(
  artifactsDir,
  "..",
  "..",
  "..",
  "..",
  "docs",
  "workspace",
  "evidence",
  `project-details-v26-${evidenceDate}`,
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
let knownSchedule = null;

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

async function reveal(page, selector) {
  const visible = await page.evaluate(`(() => {
    const element = document.querySelector(${JSON.stringify(selector)});
    if (!element) return null;
    element.scrollIntoView({ block: "center", inline: "nearest" });
    const rect = element.getBoundingClientRect();
    return { top: rect.top, bottom: rect.bottom, left: rect.left, right: rect.right, width: innerWidth, height: innerHeight };
  })()`);
  assert(visible, `${selector} is missing`);
  assert(
    visible.bottom > 0 && visible.top < visible.height && visible.right > 0 && visible.left < visible.width,
    `${selector} is outside the viewport ${JSON.stringify(visible)}`,
  );
  await sleep(300);
  return visible;
}

async function capture(page, name) {
  const file = `project-details-v26/${name}.png`;
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
  await sleep(500);
}

const panelState = `(() => {
  const panel = document.querySelector("[data-project-settings-panel]");
  if (!panel) return null;
  const levelingInput = panel.querySelector("[data-project-leveling-input]");
  const levelingStatus = panel.querySelector("[data-project-leveling-status]");
  const checkout = panel.querySelector("[data-project-checkout]");
  const rect = panel.getBoundingClientRect();
  return {
    obs: panel.querySelector('[data-project-obs-responsible-manager]')?.value ?? null,
    website: panel.querySelector('[data-project-website]')?.value ?? null,
    name: panel.querySelector('[data-project-settings-form] [name="name"]')?.value ?? null,
    revision: panel.querySelector("[data-project-settings-revision]")?.textContent?.trim() ?? null,
    message: panel.querySelector("[data-project-settings-status]")?.textContent?.trim() ?? null,
    messageState: panel.querySelector("[data-project-settings-status]")?.dataset?.state ?? null,
    checkoutState: checkout?.dataset?.checkoutState ?? null,
    checkoutText: checkout?.querySelector("[data-project-checkout-state]")?.textContent?.trim() ?? null,
    checkoutOwner: checkout?.querySelector("[data-project-checkout-owner]")?.textContent?.trim() ?? null,
    checkoutButton: checkout?.querySelector("[data-project-checkout-toggle]")?.textContent?.trim() ?? null,
    leveling: levelingInput?.value ?? null,
    levelingDisabled: Boolean(levelingInput?.disabled),
    levelingStatus: levelingStatus?.textContent?.trim() ?? null,
    levelingState: levelingStatus?.dataset?.state ?? null,
    levelingVisible: Boolean(levelingInput && levelingInput.getClientRects().length),
    checkoutVisible: Boolean(checkout && checkout.getClientRects().length),
    direction: getComputedStyle(panel).direction,
    rect: { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom },
    viewport: { width: innerWidth, height: innerHeight },
    levelingLabel: panel.querySelector("[data-project-leveling-priority] h3")?.textContent?.trim() ?? null,
    checkoutLabel: checkout?.querySelector("h3")?.textContent?.trim() ?? null,
  };
})()`;

async function readPanel(page) {
  return page.evaluate(panelState);
}

async function readProject(page) {
  return page.evaluate(
    `fetch("/api/projects/${PROJECT}").then((response) => response.json()).then((body) => body.project)`,
    { awaitPromise: true },
  );
}

async function readSchedule(page) {
  return page.evaluate(
    `fetch("/api/projects/${PROJECT}/p6/schedule/settings").then((response) => response.json())`,
    { awaitPromise: true },
  );
}

async function waitLevelingLoaded(page, timeoutMs = 15000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const state = await page.evaluate(`(() => {
      const input = document.querySelector("[data-project-leveling-input]");
      return input && !input.disabled ? input.value : null;
    })()`);
    if (state) return state;
    await sleep(200);
  }
  throw new Error("leveling priority did not load");
}

async function saveMetadata(page) {
  await page.click("[data-project-settings-save]");
  await page.waitFor(
    `(() => {
      const panel = document.querySelector("[data-project-settings-panel]");
      if (!panel) return true;
      const message = panel.querySelector("[data-project-settings-status]");
      return message?.dataset?.state === "success";
    })()`,
    "metadata save confirmation",
    20000,
  );
  await sleep(400);
}

async function directPatch(page, overrides = {}) {
  return page.evaluate(`(async () => {
    const current = await fetch("/api/projects/${PROJECT}").then((response) => response.json()).then((body) => body.project);
    const payload = {
      name: current.name,
      description: current.description ?? "",
      start_date: current.start_date ?? null,
      date_system: current.date_system ?? "gregorian",
      primary_calendar_id: current.primary_calendar_id ?? null,
      business_domain: current.business_domain ?? "",
      obs_responsible_manager: current.obs_responsible_manager ?? "",
      website_url: current.website_url ?? "",
      expected_revision: current.settings_revision ?? 0,
      ...${JSON.stringify(overrides)},
    };
    const response = await fetch("/api/projects/${PROJECT}", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return { status: response.status, body: await response.json().catch(() => null) };
  })()`, { awaitPromise: true });
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
    contract: "cubi-project-details-v26.v1",
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
    await waitLevelingLoaded(page);

    await scenario("01", "Project Details reads the stored OBS, web-site, checkout and leveling values", async () => {
      const api = await readProject(page);
      const schedule = await readSchedule(page);
      const state = await readPanel(page);
      assert(state, "settings panel state is missing");
      assert(state.obs === (api.obs_responsible_manager ?? ""), `OBS ${state.obs} vs API ${api.obs_responsible_manager}`);
      assert(state.website === (api.website_url ?? ""), `website ${state.website} vs API ${api.website_url}`);
      assert(state.checkoutState === (api.checkout_state ?? "checked_in"), `checkout ${state.checkoutState}`);
      assert(state.leveling === String(schedule.project_leveling_priority), `leveling ${state.leveling} vs API ${schedule.project_leveling_priority}`);
      assert(state.levelingVisible, "leveling priority control is not visible");
      assert(state.checkoutVisible, "checkout control is not visible");
      assert(state.rect.left >= 0 && state.rect.top >= 0, `panel outside viewport ${JSON.stringify(state.rect)}`);
      await capture(page, "01-project-details-initial");
      return { obs: state.obs, website: state.website, leveling: state.leveling };
    });

    await scenario("02", "OBS responsible manager and web-site persist through the lifecycle API", async () => {
      await page.setInput('[data-project-settings-form] [name="obs_responsible_manager"]', "Dana Whitfield");
      await page.setInput('[data-project-settings-form] [name="website_url"]', "https://example.com/riverside");
      await saveMetadata(page);
      const api = await readProject(page);
      assert(api.obs_responsible_manager === "Dana Whitfield", `API OBS ${api.obs_responsible_manager}`);
      assert(api.website_url === "https://example.com/riverside", `API website ${api.website_url}`);
      assert(api.settings_revision >= 1, `metadata revision ${api.settings_revision}`);

      await page.navigate(`${baseUrl}/app?view=live`, "form", "workspace reload");
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows after reload");
      await sleep(1200);
      await setLanguage(page, "en");
      await openProjectSettings(page);
      await waitLevelingLoaded(page);
      const state = await readPanel(page);
      assert(state.obs === "Dana Whitfield", `reloaded OBS ${state.obs}`);
      assert(state.website === "https://example.com/riverside", `reloaded website ${state.website}`);
      await capture(page, "02-project-details-persisted");
      return { revision: api.settings_revision };
    });

    await scenario("03", "leveling priority saves through the canonical schedule-settings contract", async () => {
      const before = await readSchedule(page);
      await page.setInput("[data-project-leveling-input]", "42");
      await page.click("[data-project-leveling-save]");
      await page.waitFor(
        `document.querySelector("[data-project-leveling-status]")?.dataset.state === "success"`,
        "leveling save confirmation",
        15000,
      );
      const after = await readSchedule(page);
      knownSchedule = after;
      assert(after.project_leveling_priority === 42, `API leveling ${after.project_leveling_priority}`);
      assert(after.record_revision === before.record_revision + 1, `settings revision ${after.record_revision} from ${before.record_revision}`);
      const state = await readPanel(page);
      assert(state.leveling === "42", `panel leveling ${state.leveling}`);
      assert(/Leveling priority saved/.test(state.levelingStatus), `leveling status ${state.levelingStatus}`);

      await page.navigate(`${baseUrl}/app?view=live`, "form", "workspace reload for leveling");
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows after leveling reload");
      await sleep(1200);
      await setLanguage(page, "en");
      await openProjectSettings(page);
      await waitLevelingLoaded(page);
      const reloaded = await readPanel(page);
      assert(reloaded.leveling === "42", `reloaded leveling ${reloaded.leveling}`);
      await reveal(page, "[data-project-leveling-priority]");
      await capture(page, "03-leveling-priority-persisted");
      return { recordRevision: after.record_revision, priority: after.project_leveling_priority };
    });

    await scenario("04", "project checkout is an exclusive stored lease with check-in", async () => {
      await page.click("[data-project-checkout-toggle]");
      await page.waitFor(
        `document.querySelector("[data-project-checkout]")?.dataset?.checkoutState === "checked_out"`,
        "checkout state",
        15000,
      );
      let api = await readProject(page);
      assert(api.checkout_state === "checked_out", `API checkout ${api.checkout_state}`);
      assert(api.checked_out_by === "preview-admin", `API checkout owner ${api.checked_out_by}`);
      assert(Boolean(api.checked_out_at), "API checkout timestamp is missing");
      let state = await readPanel(page);
      assert(state.checkoutButton === "Check in", `checkout button ${state.checkoutButton}`);
      assert(/preview-admin/.test(state.checkoutOwner), `checkout owner text ${state.checkoutOwner}`);
      await reveal(page, "[data-project-checkout]");
      await capture(page, "04-project-checked-out");

      await page.click("[data-project-checkout-toggle]");
      await page.waitFor(
        `document.querySelector("[data-project-checkout]")?.dataset?.checkoutState === "checked_in"`,
        "check-in state",
        15000,
      );
      api = await readProject(page);
      state = await readPanel(page);
      assert(api.checkout_state === "checked_in", `API check-in ${api.checkout_state}`);
      assert(api.checked_out_by === "", `API owner after check-in ${api.checked_out_by}`);
      assert(state.checkoutButton === "Check out", `checkout button after check-in ${state.checkoutButton}`);
      await reveal(page, "[data-project-checkout]");
      await capture(page, "04-project-checked-in");
      return { owner: "preview-admin", revision: api.settings_revision };
    });

    await scenario("05", "a stale Project Details save is rejected and reloads the latest values", async () => {
      const current = await readProject(page);
      const bumped = await directPatch(page, { website_url: "https://example.com/direct-write" });
      assert(bumped.status === 200, `direct patch status ${bumped.status}`);
      assert(bumped.body.project.settings_revision === current.settings_revision + 1, "direct patch did not bump the revision");

      await page.setInput('[data-project-settings-form] [name="website_url"]', "https://example.com/stale-write");
      await page.click("[data-project-settings-save]");
      await page.waitFor(
        `document.querySelector("[data-project-settings-status]")?.dataset.state === "conflict"`,
        "stale save conflict",
        15000,
      );
      let state = await readPanel(page);
      assert(/changed in another session/.test(state.message), `conflict message ${state.message}`);
      const stored = await readProject(page);
      assert(stored.website_url === "https://example.com/direct-write", `stored website ${stored.website_url}`);

      await page.click("[data-project-settings-reload]");
      await page.waitFor(
        `document.querySelector('[data-project-settings-form] [name="website_url"]')?.value === "https://example.com/direct-write"`,
        "reloaded latest values",
        15000,
      );
      state = await readPanel(page);
      assert(state.website === "https://example.com/direct-write", `reloaded website ${state.website}`);
      assert(state.messageState === "info" || !state.message, `message after reload ${state.messageState}`);
      await capture(page, "05-project-details-conflict");
      return { staleWebsite: "https://example.com/stale-write", stored: stored.website_url };
    });

    await scenario("06", "a viewer reads Project Details but the server rejects every write", async () => {
      cells.push({ viewport: "1366x768", locale: "en", direction: "ltr", role: "viewer" });
      await loginAs(page, "Viewer");
      await openProjectSettings(page);
      await sleep(1200);
      let state = await readPanel(page);
      assert(state.obs === "Dana Whitfield", `viewer OBS ${state.obs}`);
      assert(state.levelingDisabled, "viewer leveling input must be disabled");
      assert(/permission/.test(state.levelingStatus), `viewer leveling reason ${state.levelingStatus}`);

      await page.setInput('[data-project-settings-form] [name="obs_responsible_manager"]', "Viewer attempt");
      await page.click("[data-project-settings-save]");
      await page.waitFor(
        `document.querySelector("[data-project-settings-status]")?.dataset.state === "error"`,
        "viewer metadata rejection",
        15000,
      );
      state = await readPanel(page);
      assert(/permission/.test(state.message), `viewer metadata message ${state.message}`);
      const obsRetry = await readProject(page);
      assert(obsRetry.obs_responsible_manager === "Dana Whitfield", `viewer changed OBS to ${obsRetry.obs_responsible_manager}`);

      const deniedPatch = await directPatch(page, { obs_responsible_manager: "Direct viewer attempt" });
      assert(deniedPatch.status === 403, `direct viewer PATCH ${deniedPatch.status}`);
      const deniedCheckout = await page.evaluate(
        `fetch("/api/projects/${PROJECT}/checkout", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ checked_out: true, expected_revision: 0 }) }).then(async (response) => ({ status: response.status, body: await response.json().catch(() => null) }))`,
        { awaitPromise: true },
      );
      assert(deniedCheckout.status === 403, `direct viewer checkout ${deniedCheckout.status}`);

      assert(knownSchedule, "known schedule settings were not captured");
      const deniedLeveling = await page.evaluate(`(async () => {
        const settings = ${JSON.stringify(knownSchedule)};
        const response = await fetch("/api/projects/${PROJECT}/p6/schedule/settings", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            contract_version: "p6-project-schedule-settings-api.v1",
            expected_record_revision: settings.record_revision,
            mode: settings.mode,
            project_calendar_id: settings.project_calendar.calendar_id,
            project_calendar_version: settings.project_calendar.calendar_version,
            project_calendar_system: settings.project_calendar.system,
            project_start: settings.project_start,
            project_finish: settings.project_finish,
            schedule_options: settings.schedule_options,
            project_leveling_priority: 77,
          }),
        });
        return { status: response.status, body: await response.json().catch(() => null) };
      })()`, { awaitPromise: true });
      assert(deniedLeveling.status === 403, `direct viewer leveling ${deniedLeveling.status}`);
      const settings = await page.evaluate(
        `fetch("/api/projects/${PROJECT}").then((response) => response.json()).then((body) => body.project)`,
        { awaitPromise: true },
      );
      assert(settings.settings_revision === obsRetry.settings_revision, "viewer changed the project revision");
      await capture(page, "06-project-details-viewer");
      return { directPatch: deniedPatch.status, checkout: deniedCheckout.status, leveling: deniedLeveling.status };
    });

    await scenario("07", "the new fields fit the Persian 1280x720 layout in RTL", async () => {
      cells.push({ viewport: "1280x720", locale: "fa", direction: "rtl", role: "project_admin" });
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await sleep(300);
      await loginAs(page, "Project administrator", "fa");
      await openProjectSettings(page);
      await waitLevelingLoaded(page);
      const state = await readPanel(page);
      assert(state.direction === "rtl", `panel direction ${state.direction}`);
      assert(state.obs === "Dana Whitfield", `fa OBS ${state.obs}`);
      assert(state.website === "https://example.com/direct-write", `fa website ${state.website}`);
      assert(state.leveling === "42", `fa leveling ${state.leveling}`);
      assert(state.checkoutLabel === "قفل ویرایش پروژه", `fa checkout label ${state.checkoutLabel}`);
      assert(state.levelingLabel === "اولویت تسطیح", `fa leveling label ${state.levelingLabel}`);
      assert(state.levelingVisible && state.checkoutVisible, "new controls are not visible in the Persian layout");
      assert(state.rect.right <= state.viewport.width && state.rect.bottom <= state.viewport.height, `panel outside viewport ${JSON.stringify(state)}`);
      await reveal(page, "[data-project-leveling-priority]");
      await capture(page, "07-project-details-fa-1280");
      await reveal(page, "[data-project-checkout]");
      await capture(page, "07-project-details-fa-checkout");
      return { locale: "fa", obs: state.obs, leveling: state.leveling };
    });

    assert(exceptions.length === 0, `exceptions: ${exceptions.join(" | ")}`);
    assert(consoleErrors.length === 0, `console errors: ${consoleErrors.join(" | ")}`);
    assert(apiFailures.length === 0, `API failures: ${JSON.stringify(apiFailures)}`);
  } finally {
    writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(evidenceDir, "report.json"), JSON.stringify(report, null, 2));
    chrome.stop();
  }

  log(`\nProject details E2E: ${scenarios.length}/${scenarios.length} scenarios passed`);
  log(`Screenshots: ${screenshots.join(", ")}`);
}

main().catch((error) => {
  process.stderr.write(`${error && error.stack ? error.stack : error}\n`);
  process.exitCode = 1;
});
