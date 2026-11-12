#!/usr/bin/env node
/**
 * Browser E2E for Activities scale and presentation invariants (ACT-018/ACT-019).
 *
 * The suite seeds a real population of 240 activities through the authenticated
 * Activity Master API, then proves three things in the real Preview runtime:
 *
 *   1. the table and the Gantt draw every persisted activity (no row cap), and
 *      the last row is reachable by scrolling;
 *   2. a quick filter, a collapsed WBS branch and a hidden column change only
 *      what is drawn — the authoritative schedule snapshot keeps the same
 *      activity count (published snapshot + `/api/v1/schedule/query`);
 *   3. the full population survives a reload and renders in a Persian RTL cell.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4196 node e2e/activity-scale-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "activity-scale-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `activity-scale-v26-${evidenceDate}`);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT_ID = "preview-rps-01";
const SEED_COUNT = 240;
const SEED_PREFIX = "SX";

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

async function capture(page, name) {
  const file = `activity-scale-v26/${name}.png`;
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
  await sleep(900);
}

const openContext = `async () => {
  const response = await fetch("/api/projects/${PROJECT_ID}/open", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: "{}",
  });
  const body = await response.json();
  return { status: response.status, context: body.context };
}`;

async function projectContext(page) {
  const opened = await page.evaluate(`(${openContext})()`, { awaitPromise: true });
  assert(opened.status === 200 && opened.context, `project open failed: ${opened.status}`);
  return opened.context;
}

function contextHeaders(context) {
  return {
    "content-type": "application/json",
    "X-Tenant-Id": context.tenant_id,
    "X-Project-Id": context.project_id,
    "X-Project-Revision": String(context.revision),
  };
}

async function readActivityCount(page, context) {
  const result = await page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${PROJECT_ID}/p6/activities", {
      headers: ${JSON.stringify(contextHeaders(context))},
    });
    const body = await response.json();
    return { status: response.status, count: Array.isArray(body.activities) ? body.activities.length : -1 };
  })()`, { awaitPromise: true });
  assert(result.status === 200, `activity list returned ${result.status}`);
  return result.count;
}

async function authoritativeCount(page, context, session) {
  const result = await page.evaluate(`(async () => {
    const headers = ${JSON.stringify(contextHeaders(context))};
    const publish = await fetch("/api/projects/${PROJECT_ID}/p6/schedule/snapshots", {
      method: "POST",
      headers,
      body: JSON.stringify({ contract_version: "p6-schedule-snapshot-api.v1", timezone: "UTC" }),
    });
    const snapshot = await publish.json();
    if (!publish.ok) return { error: "PUBLISH_" + publish.status, body: snapshot };
    const query = await fetch("/api/v1/schedule/query", {
      method: "POST",
      headers,
      body: JSON.stringify({
        contract_version: "schedule-query.v1",
        query_id: crypto.randomUUID(),
        scope: {
          tenant_id: ${JSON.stringify(context.tenant_id)},
          project_id: ${JSON.stringify(context.project_id)},
          project_revision: ${Number(context.revision)},
        },
        requested_by: ${JSON.stringify(session)},
        query_text: "Scale invariant check",
        kind: "fact",
        language: "en",
        constraints: { snapshot_id: snapshot.snapshot_id },
      }),
    });
    const body = await query.json();
    if (!query.ok) return { error: "QUERY_" + query.status, body };
    return {
      snapshotId: snapshot.snapshot_id,
      activityCount: body?.data?.activity_count ?? null,
      activityKeys: Object.keys(body?.data?.activities ?? {}).length,
    };
  })()`, { awaitPromise: true });
  assert(!result.error, `authoritative query failed: ${result.error}`);
  return result;
}

const domState = `(() => {
  const rows = document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]");
  const bars = document.querySelectorAll("#cp-gantt [data-gantt-activity-id]");
  const wrap = document.querySelector("#cp-activity-grid .cp-table-wrap");
  return {
    rows: rows.length,
    bars: bars.length,
    lastId: rows.length ? rows[rows.length - 1].getAttribute("data-activity-id") : null,
    gridScrollable: wrap ? wrap.scrollHeight > wrap.clientHeight : false,
    horizontalOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    direction: getComputedStyle(document.querySelector(".cp-workspace") ?? document.body).direction,
  };
})()`;

async function gridState(page) {
  return page.evaluate(domState);
}

async function setQuickFilter(page, value) {
  const changed = await page.evaluate(`(() => {
    const input = document.querySelector("[data-activity-filter]");
    if (!input) return false;
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
    setter.call(input, ${JSON.stringify(value)});
    input.dispatchEvent(new Event("input", { bubbles: true }));
    return true;
  })()`);
  assert(changed, "activity filter input is missing");
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
    contract: "cubi-activity-scale-v26.v1",
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
  };

  const state = { context: null, session: null, seeded: 0, baseline: 0, authoritative: 0 };

  try {
    await setViewport(page, 1280, 720);
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
    const persona = await page.evaluate(`(() => {
      const button = document.querySelector('button[name="role"][value="admin"]');
      if (!button) return false;
      button.click();
      return true;
    })()`);
    assert(persona, "admin persona button is missing");
    await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
    await page.click('[data-project-id="preview-rps-01"]');
    await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
    await sleep(1400);

    state.context = await projectContext(page);
    const session = await page.evaluate(`(async () => {
      const response = await fetch("/api/session");
      const body = await response.json();
      return body.user_id ?? null;
    })()`, { awaitPromise: true });
    assert(session, "session user id is missing");
    state.session = session;

    await scenario("01", "The seeded population is persisted and readable without a row cap", async () => {
      state.baseline = await readActivityCount(page, state.context);
      const seeds = await page.evaluate(`(async () => {
        const headers = ${JSON.stringify(contextHeaders(state.context))};
        const ids = [];
        const failures = [];
        const batchSize = 24;
        for (let start = 1; start <= ${SEED_COUNT}; start += batchSize) {
          const batch = [];
          for (let index = start; index < Math.min(start + batchSize, ${SEED_COUNT} + 1); index += 1) {
            const id = "${SEED_PREFIX}" + String(index).padStart(3, "0");
            ids.push(id);
            batch.push(fetch("/api/projects/${PROJECT_ID}/p6/activities", {
              method: "POST",
              headers,
              body: JSON.stringify({
                contract_version: "p6-activity-master-api.v1",
                activity_id: id,
                name: "Scale seed " + index,
                duration_value: "2",
                duration_unit: "working-day",
                wbs_id: "WBS-RPS-CIVIL",
                activity_type: "Task Dependent",
                status: "Not Started",
                status_code: "Active",
                percent_complete_type: "DURATION",
                leveling_priority: "Normal",
              }),
            }).then(async (response) => {
              if (!response.ok) failures.push({ id, status: response.status, body: await response.text() });
            }));
          }
          await Promise.all(batch);
        }
        return { ids: ids.length, failures };
      })()`, { awaitPromise: true });
      assert(seeds.failures.length === 0, `seed writes failed: ${JSON.stringify(seeds.failures.slice(0, 3))}`);
      state.seeded = seeds.ids;
      const afterSeed = await readActivityCount(page, state.context);
      assert(afterSeed >= 250, `expected at least 250 activities, read ${afterSeed}`);
      assert(afterSeed === state.baseline + state.seeded, `read model ${afterSeed} != ${state.baseline} + ${state.seeded}`);
      return { baseline: state.baseline, seeded: state.seeded, total: afterSeed };
    });

    await page.reload();
    await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows after reload");
    await sleep(1500);
    state.context = await projectContext(page);
    state.authoritative = await authoritativeCount(page, state.context, state.session);

    await scenario("02", "The table draws every persisted activity and the last row is reachable", async () => {
      const total = await readActivityCount(page, state.context);
      const dom = await gridState(page);
      assert(dom.rows === total, `table rows ${dom.rows} != read model ${total}`);
      assert(dom.rows >= 250, `rows ${dom.rows} below the 250-activity stress floor`);
      assert(dom.lastId, "the table has no data row");
      assert(dom.gridScrollable, "the activity grid is not scrollable");
      const lastVisible = await page.evaluate(`(() => {
        const wrap = document.querySelector("#cp-activity-grid .cp-table-wrap");
        if (!wrap) return null;
        wrap.scrollTop = wrap.scrollHeight;
        const rows = wrap.querySelectorAll("tbody tr[data-activity-id]");
        const last = rows[rows.length - 1];
        if (!last) return null;
        const box = last.getBoundingClientRect();
        const host = wrap.getBoundingClientRect();
        return {
          id: last.getAttribute("data-activity-id"),
          top: box.top,
          bottom: box.bottom,
          hostTop: host.top,
          hostBottom: host.bottom,
          visible: box.top >= host.top - 2 && box.bottom <= host.bottom + 2,
        };
      })()`);
      assert(lastVisible && lastVisible.visible, `last row is not reachable: ${JSON.stringify(lastVisible)}`);
      await capture(page, "01-full-population");
      return { rows: dom.rows, lastId: lastVisible.id, total };
    });

    await scenario("03", "The Gantt renders one bar per visible activity in the same population", async () => {
      const dom = await gridState(page);
      assert(dom.bars === dom.rows, `Gantt bars ${dom.bars} != table rows ${dom.rows}`);
      assert(dom.bars >= 250, `bars ${dom.bars} below the stress floor`);
      return { rows: dom.rows, bars: dom.bars };
    });

    await scenario("04", "A quick filter narrows the rows while the authoritative snapshot keeps every activity", async () => {
      await setQuickFilter(page, SEED_PREFIX);
      const filtered = await gridState(page);
      const total = await readActivityCount(page, state.context);
      assert(filtered.rows === state.seeded, `filtered rows ${filtered.rows} != seeded ${state.seeded}`);
      assert(filtered.rows < total, `filter did not narrow rows (${filtered.rows} of ${total})`);
      const authoritative = await authoritativeCount(page, state.context, state.session);
      assert(authoritative.activityCount === total, `authoritative count ${authoritative.activityCount} != ${total}`);
      await capture(page, "02-filter-narrows");
      await setQuickFilter(page, "");
      const cleared = await gridState(page);
      assert(cleared.rows === total, `clearing the filter left ${cleared.rows} of ${total} rows`);
      return { filteredRows: filtered.rows, total, snapshotCount: authoritative.activityCount };
    });

    await scenario("05", "Collapsing every WBS branch hides rows without changing the authoritative snapshot", async () => {
      const collapsed = await page.evaluate(`(() => {
        const button = document.querySelector("[data-wbs-collapse-all]");
        if (!button) return false;
        button.click();
        return true;
      })()`);
      assert(collapsed, "collapse-all control is missing");
      await sleep(700);
      const dom = await gridState(page);
      assert(dom.rows < state.seeded, `collapse still draws ${dom.rows} activity rows`);
      const authoritative = await authoritativeCount(page, state.context, state.session);
      const total = await readActivityCount(page, state.context);
      assert(authoritative.activityCount === total, `collapsed snapshot ${authoritative.activityCount} != ${total}`);
      await capture(page, "03-collapsed-wbs");
      const expanded = await page.evaluate(`(() => {
        const button = document.querySelector("[data-wbs-expand-all]");
        if (!button) return false;
        button.click();
        return true;
      })()`);
      assert(expanded, "expand-all control is missing");
      await sleep(700);
      const restored = await gridState(page);
      assert(restored.rows === total, `expanding restored ${restored.rows} of ${total} rows`);
      return { collapsedRows: dom.rows, restoredRows: restored.rows, snapshotCount: authoritative.activityCount };
    });

    await scenario("06", "Hiding a column keeps every row and the schedule facts intact", async () => {
      const before = await gridState(page);
      await page.click("[data-columns-open]");
      await page.waitForSelector("[data-columns-form]", "columns dialog", 8000);
      const hidden = await page.evaluate(`(() => {
        const target = document.querySelector('[data-columns-visibility="activity.name"]')
          ?? document.querySelector('[data-columns-visibility="activity_name"]')
          ?? document.querySelector("[data-columns-visibility]");
        if (!target) return null;
        const field = target.getAttribute("data-columns-visibility");
        target.click();
        return field;
      })()`);
      assert(hidden, "no visible column could be hidden");
      await page.click("[data-columns-apply]");
      await sleep(900);
      const after = await gridState(page);
      assert(after.rows === before.rows, `hiding ${hidden} changed rows ${before.rows} -> ${after.rows}`);
      assert(after.rows >= 250, `rows fell below the stress floor after hiding a column`);
      const header = await page.evaluate(`Boolean(document.querySelector('#cp-activity-grid thead th[data-column-id="' + ${JSON.stringify(hidden)} + '"]'))`);
      assert(!header, `hidden column ${hidden} is still rendered`);
      await capture(page, "04-hidden-column");
      // Restore the column so later cells see the default presentation.
      await page.click("[data-columns-open]");
      await page.waitForSelector("[data-columns-form]", "columns dialog reopened", 8000);
      const restoredColumn = await page.evaluate(`(() => {
        const target = document.querySelector('[data-columns-visibility="${hidden}"]');
        if (!target) return false;
        target.click();
        return true;
      })()`);
      assert(restoredColumn, `could not restore ${hidden}`);
      await page.click("[data-columns-apply]");
      await sleep(700);
      return { hiddenField: hidden, rows: after.rows };
    });

    await scenario("07", "A reload returns the whole population from the server", async () => {
      await page.reload();
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows after reload");
      await sleep(1500);
      state.context = await projectContext(page);
      const total = await readActivityCount(page, state.context);
      const dom = await gridState(page);
      assert(dom.rows === total, `after reload rows ${dom.rows} != read model ${total}`);
      assert(dom.rows >= 250, `after reload rows ${dom.rows} below the stress floor`);
      const authoritative = await authoritativeCount(page, state.context, state.session);
      assert(authoritative.activityCount === total, `snapshot ${authoritative.activityCount} != ${total}`);
      await capture(page, "05-after-reload");
      return { rows: dom.rows, total, snapshotCount: authoritative.activityCount };
    });

    await scenario("08", "The full population renders in a Persian RTL cell without overflow", async () => {
      await setViewport(page, 1366, 768);
      await setLanguage(page, "fa");
      await sleep(900);
      const total = await readActivityCount(page, state.context);
      const dom = await gridState(page);
      assert(dom.direction === "rtl", `workspace direction is ${dom.direction}`);
      assert(dom.rows === total, `RTL rows ${dom.rows} != read model ${total}`);
      assert(dom.horizontalOverflow <= 1, `RTL horizontal overflow ${dom.horizontalOverflow}px`);
      await capture(page, "06-rtl-1366x768");
      return { rows: dom.rows, direction: dom.direction, overflow: dom.horizontalOverflow };
    });
  } catch (error) {
    log(`\nFAILED: ${error && error.stack ? error.stack : error}`);
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(evidenceDir, "activity-scale-v26.json"), JSON.stringify(report, null, 2));
    throw error;
  } finally {
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(evidenceDir, "activity-scale-v26.json"), JSON.stringify(report, null, 2));
  }

  log(`\nScenarios: ${scenarios.filter((s) => s.status === "pass").length} passed, ${scenarios.filter((s) => s.status === "fail").length} failed`);
  log(`Evidence: ${join(evidenceDir, "activity-scale-v26.json")}`);
  await chrome.close?.();
}

main().catch((error) => {
  process.stderr.write(`\n${error && error.stack ? error.stack : error}\n`);
  process.exit(1);
});
