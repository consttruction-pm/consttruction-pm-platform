#!/usr/bin/env node
/**
 * Browser E2E for Version 26 progress-update history and out-of-sequence review.
 *
 * The Progress window must show the values the shared activity service actually
 * stored, the immutable events recorded for every progress-bearing change, the
 * percent-complete trend read from those events, and the out-of-sequence review
 * captured against the stored predecessor logic. Everything is driven through
 * the real local full-stack preview on project preview-rps-01 and the real
 * p6-activity-master-api.v1 / p6-activity-progress-history-api.v1 routes; no
 * value is mocked or injected into the page.
 *
 * Scenarios cover the empty history, two progress updates from the UI, the
 * persisted percent trend, the FS out-of-sequence finding for A140 against its
 * stored predecessor A130, an API cross-check, a viewer read-only session, a
 * 1920x1080 redraw and the 1280x720 Persian right-to-left layout.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 \
 *   CUBI_TESTED_CODE_SHA=<code commit> \
 *   node e2e/progress-history-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "progress-history-v26");
const evidenceDir = join(
  artifactsDir,
  "..",
  "..",
  "..",
  "..",
  "docs",
  "workspace",
  "evidence",
  `progress-history-v26-${evidenceDate}`,
);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const ACTIVITY = "A140";
const PREDECESSOR = "A130";

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
  const file = `progress-history-v26/${name}.png`;
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

async function openProgress(page) {
  const clicked = await page.evaluate(`(() => {
    const buttons = [...document.querySelectorAll('[data-menu="progress"]')];
    const button = buttons.find((item) => item.getClientRects().length > 0) ?? buttons[0];
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, "Progress menu button is missing");
  await page.waitForSelector("[data-progress-page] .cp-register-toolbar", "progress window");
  await page.waitFor(
    `(() => {
      const page = document.querySelector("[data-progress-page]");
      if (!page) return false;
      const text = page.textContent || "";
      return !text.includes("Reading activity progress");
    })()`,
    "progress register settled",
  );
  await sleep(300);
}

const progressState = `(() => {
  const page = document.querySelector("[data-progress-page]");
  const rows = [...(page?.querySelectorAll("[data-progress-row]") ?? [])];
  const historyRows = [...(page?.querySelectorAll("[data-progress-history-row]") ?? [])];
  const history = page?.querySelector("[data-progress-history]");
  return {
    mounted: Boolean(page),
    rowIds: rows.map((row) => row.dataset.activityId),
    selected: page?.querySelector("[data-progress-row].is-selected")?.dataset.activityId ?? null,
    form: Boolean(page?.querySelector("[data-progress-form]")),
    historyCount: historyRows.length,
    historyEventIds: historyRows.map((row) => row.dataset.eventId),
    historyText: history?.textContent ?? "",
    trendText: page?.querySelector("[data-progress-trend] span")?.textContent ?? null,
    trendPoints: page?.querySelector("[data-progress-trend] polyline")?.getAttribute("points") ?? null,
    sequenceFlags: [...(page?.querySelectorAll('[data-progress-sequence="out"]') ?? [])]
      .map((node) => node.getAttribute("title")),
    review: page?.querySelector("[data-progress-sequence-review]")?.textContent?.trim() ?? null,
    notice: page?.querySelector("[data-progress-notice]")?.textContent?.trim() ?? null,
  };
})()`;

async function readProgress(page) {
  return page.evaluate(progressState);
}

async function selectActivity(page, activityId = ACTIVITY) {
  const clicked = await page.evaluate(`(() => {
    const row = document.querySelector('[data-progress-row][data-activity-id="${activityId}"]');
    if (!row) return false;
    row.click();
    return true;
  })()`);
  assert(clicked, `activity row ${activityId} is missing`);
  await page.waitForSelector("[data-progress-form]", "progress editor");
  await page.waitFor(
    `(() => {
      const history = document.querySelector("[data-progress-history]");
      return Boolean(history && !history.textContent.includes("Reading progress history"));
    })()`,
    "progress history settled",
  );
  await sleep(250);
}

async function api(page, method, path, body) {
  return page.evaluate(
    `(async () => {
      const session = await (await fetch("/api/session")).json();
      const projects = await (await fetch("/api/projects")).json();
      const project = (projects.projects || []).find((item) => item.project_id === ${JSON.stringify(PROJECT)});
      const response = await fetch(${JSON.stringify(path)}, {
        method: ${JSON.stringify(method)},
        headers: {
          "Content-Type": "application/json",
          "X-Tenant-Id": session.tenant_id,
          "X-Project-Id": ${JSON.stringify(PROJECT)},
          "X-Project-Revision": String(project ? project.revision : ""),
        },
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
  await setLanguage(page, "en");
}

async function submitProgress(page, { percent, actualStart, remaining }, expectedEvents) {
  await page.setSelect('[data-progress-form] [name="status"]', "In Progress");
  await page.setInput('[data-progress-form] [name="percent-complete"]', percent);
  await page.setInput('[data-progress-form] [name="actual-start"]', actualStart);
  await page.setInput('[data-progress-form] [name="remaining-duration"]', remaining);
  await page.click('[data-progress-form] button[type="submit"]');
  // The workspace re-renders after a stored update, so the transient notice is
  // not a stable signal. The appended history event is the stored result.
  await page.waitFor(
    `document.querySelectorAll("[data-progress-history-row]").length === ${expectedEvents}`,
    `history event ${expectedEvents}`,
  );
  const failed = await page.evaluate(
    `document.querySelector('[data-progress-notice][data-state="error"]')?.textContent ?? null`,
  );
  assert(!failed, `progress save failed: ${failed}`);
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
    if (url.includes("/api/") && params.response.status >= 500) apiFailures.push({ status: params.response.status, url });
  });

  const report = {
    contract: "cubi-progress-history-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    project: PROJECT,
    activityId: ACTIVITY,
    predecessorId: PREDECESSOR,
    cells,
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
  };

  try {
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 768, deviceScaleFactor: 1, mobile: false });
    await loginAs(page, "Planner");
    await openProgress(page);

    await scenario("01", "the Progress register and an empty update history are read from the activity service", async () => {
      const state = await readProgress(page);
      assert(state.mounted, "progress page missing");
      assert(state.rowIds.includes(ACTIVITY), `activity ${ACTIVITY} is not in the register`);
      assert(state.historyCount === 0, "history rendered before an activity was selected");
      await selectActivity(page);
      const selected = await readProgress(page);
      assert(selected.selected === ACTIVITY, "the selected row is not marked");
      assert(selected.form, "the progress editor is missing");
      assert(selected.historyCount === 0, `history is not empty: ${JSON.stringify(selected.historyEventIds)}`);
      assert(selected.historyText.includes("No progress updates are recorded"), "empty history is not stated");
      assert(selected.trendText === null, "a trend is shown without percent events");
      await capture(page, "01-progress-empty-history");
      return { rows: selected.rowIds.length, events: selected.historyCount };
    });

    await scenario("02", "a UI progress update is stored and recorded as an out-of-sequence event", async () => {
      await submitProgress(page, { percent: "20", actualStart: "2026-10-07", remaining: "6" }, 1);
      const state = await readProgress(page);
      assert(state.historyEventIds[0] === `${ACTIVITY}@2`, `event id ${state.historyEventIds[0]}`);
      assert(state.trendText.includes("r2: 20%"), `trend text ${state.trendText}`);
      assert(state.trendPoints && state.trendPoints.length > 0, "trend polyline has no points");
      assert(state.sequenceFlags.length === 1, "out-of-sequence flag is missing");
      assert(state.sequenceFlags[0].includes("FS_PREDECESSOR_NOT_FINISHED"), `finding ${state.sequenceFlags[0]}`);
      assert(state.sequenceFlags[0].includes(PREDECESSOR), `finding predecessor ${state.sequenceFlags[0]}`);
      assert((state.review ?? "").toLowerCase().includes("out of sequence"), `review ${state.review}`);
      assert(state.historyText.includes("Percent Complete") || state.historyText.includes("% Complete"), "change fields are not rendered");
      await capture(page, "02-progress-first-update");
      return { event: state.historyEventIds[0], findings: state.sequenceFlags };
    });

    await scenario("03", "a second update appends an event and extends the persisted percent trend", async () => {
      await submitProgress(page, { percent: "55", actualStart: "2026-10-07", remaining: "4" }, 2);
      const state = await readProgress(page);
      assert(state.historyEventIds.join(",") === `${ACTIVITY}@2,${ACTIVITY}@3`, `events ${state.historyEventIds}`);
      assert(state.trendText.includes("r2: 20%") && state.trendText.includes("r3: 55%"), `trend ${state.trendText}`);
      await capture(page, "03-progress-two-events");
      return { events: state.historyEventIds, trend: state.trendText };
    });

    await scenario("04", "the history API reports the same actor, changes and findings", async () => {
      const stored = await api(page, "GET", `/api/projects/${PROJECT}/p6/activities/${ACTIVITY}/progress-history`);
      assert(stored.status === 200, `history status ${stored.status}: ${JSON.stringify(stored.body)}`);
      assert(stored.body.contract_version === "p6-activity-progress-history-api.v1", "contract version");
      assert(stored.body.kind === "p6_activity_progress_history", "kind");
      assert(stored.body.events.length === 2, `events ${stored.body.events.length}`);
      const latest = stored.body.events[1];
      assert(latest.actor_user_id === "preview-planner", `actor ${latest.actor_user_id}`);
      assert(latest.to_record_revision === 3, `revision ${latest.to_record_revision}`);
      const percent = latest.changes.find((change) => change.field === "percent_complete");
      assert(percent && percent.after === "55.0", `percent change ${JSON.stringify(percent)}`);
      assert(latest.out_of_sequence.is_out_of_sequence === true, "review is not flagged");
      assert(
        latest.out_of_sequence.findings.some((finding) => finding.code === "FS_PREDECESSOR_NOT_FINISHED" && finding.predecessor_id === PREDECESSOR),
        `findings ${JSON.stringify(latest.out_of_sequence.findings)}`,
      );
      assert(stored.body.out_of_sequence_review.evaluated_event_id === `${ACTIVITY}@3`, "review event");
      assert(stored.body.percent_complete_trend.length === 2, "trend length");
      return { events: stored.body.events.length, actor: latest.actor_user_id };
    });

    await scenario("05", "the stored history survives a reload and redraws at 1920x1080", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false });
      await page.navigate(`${baseUrl}/app?view=progress`, "[data-progress-page] .cp-register-toolbar", "progress after reload");
      await openProgress(page);
      await selectActivity(page);
      const state = await readProgress(page);
      assert(state.historyCount === 2, `history after reload ${state.historyCount}`);
      assert(state.trendText.includes("r3: 55%"), `trend after reload ${state.trendText}`);
      await capture(page, "05-progress-1920");
      cells.push({ viewport: "1920x1080", locale: "en", result: "history and trend redrawn" });
      return { events: state.historyCount };
    });

    await scenario("06", "a viewer can read the history but the server rejects a progress write", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 768, deviceScaleFactor: 1, mobile: false });
      await loginAs(page, "Viewer");
      await openProgress(page);
      await selectActivity(page);
      const state = await readProgress(page);
      assert(state.historyCount === 2, `viewer history ${state.historyCount}`);
      assert(state.sequenceFlags.length === 2, `viewer review flags ${state.sequenceFlags.length}`);
      const denied = await api(page, "PATCH", `/api/projects/${PROJECT}/p6/activities/${ACTIVITY}`, {
        contract_version: "p6-activity-master-api.v1",
        expected_revision: 3,
        percent_complete: 90,
      });
      assert(denied.status === 403, `viewer write status ${denied.status}`);
      assert(String(denied.body?.code ?? "") === "AUTHORIZATION_PERMISSION_DENIED", `viewer code ${JSON.stringify(denied.body)}`);
      await capture(page, "06-progress-viewer-1366");
      cells.push({ viewport: "1366x768", locale: "en", result: "viewer read-only history; PATCH 403" });
      return { events: state.historyCount, writeStatus: denied.status };
    });

    await scenario("07", "the history and out-of-sequence review fit the Persian 1280x720 layout", async () => {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await loginAs(page, "Planner");
      await setLanguage(page, "fa");
      await openProgress(page);
      await selectActivity(page);
      const state = await readProgress(page);
      assert(state.historyCount === 2, `fa history ${state.historyCount}`);
      assert(state.sequenceFlags.length === 2, `fa review flags ${state.sequenceFlags.length}`);
      assert(state.review?.includes("خارج از توالی"), `fa review ${state.review}`);
      const rtl = await page.evaluate(`document.documentElement.dir === "rtl" || document.body.dir === "rtl"`);
      assert(rtl, "the workspace is not right-to-left");
      const fits = await page.evaluate(`(() => {
        const section = document.querySelector("[data-progress-history]");
        if (!section) return false;
        const rect = section.getBoundingClientRect();
        return rect.width <= window.innerWidth + 1 && rect.height > 0;
      })()`);
      assert(fits, "the history section does not fit the 1280x720 pane");
      await capture(page, "07-progress-fa-1280");
      cells.push({ viewport: "1280x720", locale: "fa", result: "RTL history and review visible" });
      return { events: state.historyCount, rtl };
    });

    report.cells.push({ viewport: "1366x768", locale: "en", result: "register, history, trend and review" });
  } finally {
    writeFileSync(join(evidenceDir, "report.json"), `${JSON.stringify(report, null, 2)}\n`);
    writeFileSync(join(outDir, "report.json"), `${JSON.stringify(report, null, 2)}\n`);
    await chrome.stop?.();
  }

  log(`\nProgress history E2E: ${scenarios.filter((item) => item.status === "pass").length}/${scenarios.length} scenarios passed`);
  log(`Screenshots: ${screenshots.join(", ")}`);
  if (exceptions.length || apiFailures.length) {
    throw new Error(`runtime exceptions=${exceptions.length} apiFailures=${apiFailures.length}`);
  }
}

main().catch((error) => {
  process.stderr.write(`\nPROGRESS HISTORY E2E FAILED\n${error && error.stack ? error.stack : error}\n`);
  process.exit(1);
});
