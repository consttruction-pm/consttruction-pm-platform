#!/usr/bin/env node
/**
 * Browser E2E for the Version 26 Backup / Recovery window.
 *
 * It drives the real local full-stack preview on project preview-rps-01 with
 * headless Chrome through the DevTools protocol. Snapshots are captured from the
 * authoritative WBS, activity, relationship, resource and layout repositories;
 * restores write back through the same versioned repositories. No page fixture
 * is injected and no API response is mocked.
 *
 * Scenarios cover a project snapshot with checksummed manifest, a layouts-only
 * snapshot, idempotent capture replay and key-reuse conflict, overwrite restore
 * that rewinds an edited activity, non-destructive merge skip counts, restore
 * history, viewer/planner authorization gates with direct 403s, and the
 * 1280x720 Persian right-to-left layout.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 node e2e/backup-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "backup-v26");
const evidenceDir = join(
  artifactsDir,
  "..",
  "..",
  "..",
  "..",
  "docs",
  "workspace",
  "evidence",
  `backup-v26-${evidenceDate}`,
);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const TENANT = "cubi-preview-tenant";
const stamp = Date.now().toString(36).toUpperCase();
const idempotencyKey = `e2e-backup-${stamp}`;
const restoreKey = `e2e-restore-${stamp}`;
const mergeKey = `e2e-merge-${stamp}`;

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

const pageState = `(() => {
  const page = document.querySelector("[data-backup-page]");
  const text = (node) => (node?.textContent ?? "").trim();
  return {
    activeMenu: document.querySelector(".cp-workspace")?.dataset.activeMenu ?? null,
    direction: document.querySelector(".cp-workspace")?.getAttribute("dir") ?? null,
    heading: text(page?.querySelector(":scope > .cp-register-toolbar strong")),
    tabs: [...page?.querySelectorAll("[data-backup-tab]") ?? []].map((tab) => ({
      key: tab.dataset.backupTab,
      selected: tab.getAttribute("aria-selected"),
      label: text(tab),
    })),
    activeTab: page?.querySelector("[data-backup-body]")?.dataset.backupActiveTab ?? null,
    kind: page?.querySelector("[data-backup-kind]")?.value ?? null,
    label: page?.querySelector("[data-backup-label]")?.value ?? null,
    createDisabled: Boolean(page?.querySelector('[data-backup-action="create"]')?.disabled),
    rows: [...page?.querySelectorAll("[data-backup-snapshot-row]") ?? []].map((row) => ({
      id: row.dataset.snapshotId,
      kind: row.dataset.kind,
      sha: row.dataset.sha,
      text: text(row),
    })),
    snapshotOptions: [...page?.querySelectorAll("[data-backup-snapshot] option") ?? []].map((option) => option.value),
    selectedSnapshot: page?.querySelector("[data-backup-snapshot]")?.value ?? null,
    mode: page?.querySelector("[data-backup-mode]")?.value ?? null,
    restoreDisabled: Boolean(page?.querySelector('[data-backup-action="restore"]')?.disabled),
    manifest: (() => {
      const node = page?.querySelector("[data-backup-manifest]");
      return node ? text(node) : null;
    })(),
    hasDownload: Boolean(page?.querySelector('[data-backup-action="download"]')),
    restoreSummary: (() => {
      const node = page?.querySelector("[data-backup-restore-summary]");
      return node
        ? { created: node.dataset.created, updated: node.dataset.updated, skipped: node.dataset.skipped }
        : null;
    })(),
    restoreSummaryText: text(page?.querySelector("[data-backup-restore-summary]")),
    runs: [...page?.querySelectorAll("[data-backup-run-row]") ?? []].map((row) => ({
      id: row.dataset.runId,
      text: text(row),
    })),
    notice: page?.querySelector("[data-backup-notice]")?.dataset.state ?? null,
    noticeText: text(page?.querySelector("[data-backup-notice]")),
    bodyText: text(page),
  };
})()`;

async function capture(page, name) {
  const file = `backup-v26/${name}.png`;
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

async function openBackup(page) {
  await openMenu(page, "backup", "[data-backup-page] .cp-register-toolbar", "backup panel");
  await page.waitFor(
    `(() => {
      const page = document.querySelector("[data-backup-page]");
      return Boolean(page) && Boolean(page.querySelector("[data-backup-tab]"));
    })()`,
    "backup tabs settled",
  );
  await sleep(400);
}

async function openTab(page, tab) {
  await page.click(`[data-backup-tab="${tab}"]`);
  await page.waitFor(
    `document.querySelector("[data-backup-page] [data-backup-body]")?.dataset.backupActiveTab === ${JSON.stringify(tab)}`,
    `backup ${tab} tab`,
  );
  await sleep(300);
}

async function reload(page) {
  await page.evaluate('document.querySelector(\'[data-backup-page] [data-backup-action="reload"]\').click()');
  await sleep(700);
}

async function setKind(page, kind) {
  await page.evaluate(`(() => {
    const select = document.querySelector("[data-backup-kind]");
    if (!select) return false;
    select.value = ${JSON.stringify(kind)};
    select.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  await sleep(200);
}

async function setLabel(page, label) {
  await page.evaluate(`(() => {
    const input = document.querySelector("[data-backup-label]");
    if (!input) return false;
    input.value = ${JSON.stringify(label)};
    input.dispatchEvent(new Event("input", { bubbles: true }));
    return true;
  })()`);
  await sleep(200);
}

async function createFromUi(page) {
  await page.click('[data-backup-action="create"]');
  await page.waitFor(
    `Boolean(document.querySelector("[data-backup-page] [data-backup-notice]"))`,
    "backup creation notice",
  );
  const notice = await page.evaluate(`(() => {
    const node = document.querySelector("[data-backup-page] [data-backup-notice]");
    return { state: node?.dataset.state ?? null, text: (node?.textContent ?? "").trim() };
  })()`);
  assert(notice.state === "ok", `backup creation failed: ${JSON.stringify(notice)}`);
  await sleep(700);
}

function backupUrl(suffix = "") {
  return `/api/projects/${PROJECT}/backup${suffix}`;
}

async function api(page, method, path, body, headers = {}) {
  return page.evaluate(`(async () => {
    const response = await fetch(${JSON.stringify(path)}, {
      method: ${JSON.stringify(method)},
      headers: { "Content-Type": "application/json", ...${JSON.stringify(headers)} },
      ${body === undefined ? "" : `body: JSON.stringify(${JSON.stringify(body)}),`}
    });
    return { status: response.status, body: await response.json() };
  })()`, { awaitPromise: true });
}

const projectHeaders = {
  "X-Tenant-Id": TENANT,
  "X-Project-Id": PROJECT,
  "X-Project-Revision": "7",
};

async function firstActivity(page) {
  const activity = await page.evaluate(`(async () => {
    const response = await fetch("/api/projects/" + encodeURIComponent(${JSON.stringify(PROJECT)}) + "/p6/activities", {
      headers: ${JSON.stringify(projectHeaders)},
    });
    const body = await response.json().catch(() => null);
    const items = body?.activities ?? body?.items ?? [];
    const first = items[0] ?? null;
    return { status: response.status, activity: first?.activity ?? first };
  })()`, { awaitPromise: true });
  assert(activity.status === 200 && activity.activity, `activities ${JSON.stringify(activity).slice(0, 300)}`);
  return activity.activity;
}

async function readActivity(page, activityId) {
  return page.evaluate(`(async () => {
    const response = await fetch("/api/projects/" + encodeURIComponent(${JSON.stringify(PROJECT)}) + "/p6/activities/" + encodeURIComponent(${JSON.stringify(activityId)}), {
      headers: ${JSON.stringify(projectHeaders)},
    });
    const body = await response.json().catch(() => null);
    return { status: response.status, activity: body?.activity ?? null };
  })()`, { awaitPromise: true });
}

async function renameActivity(page, activityId, name, expectedRevision, wbsId) {
  return page.evaluate(`(async () => {
    const response = await fetch("/api/projects/" + encodeURIComponent(${JSON.stringify(PROJECT)}) + "/p6/activities/" + encodeURIComponent(${JSON.stringify(activityId)}), {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...${JSON.stringify(projectHeaders)} },
      body: JSON.stringify({
        contract_version: "p6-activity-master-api.v1",
        expected_revision: ${Number(expectedRevision)},
        name: ${JSON.stringify(name)},
        wbs_id: ${JSON.stringify(wbsId)},
      }),
    });
    const body = await response.json().catch(() => null);
    return { status: response.status, body };
  })()`, { awaitPromise: true });
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
  await setLanguage(page, "en");
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
    contract: "cubi-backup-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    idempotencyKey,
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
  };

  try {
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
    await sleep(400);
    await loginAs(page, "Project administrator");
    await openBackup(page);

    let projectSnapshot = null;

    await scenario("01", "عکس‌برداری پروژه با فهرست محتوا و اثر انگشت SHA-256 ثبت می‌شود", async () => {
      const state = await page.evaluate(pageState);
      assert(state.heading === "Backup / Recovery", `heading ${state.heading}`);
      assert(state.tabs.map((tab) => tab.key).join(",") === "snapshots,restore,history", `tabs ${JSON.stringify(state.tabs)}`);
      assert(state.activeTab === "snapshots", `active tab ${state.activeTab}`);

      await setKind(page, "project");
      await setLabel(page, `E2E project baseline ${stamp}`);
      await createFromUi(page);
      const created = await page.evaluate(pageState);
      const row = created.rows.find((item) => item.kind === "project" && item.text.includes(`E2E project baseline ${stamp}`));
      assert(row, `created snapshot row missing: ${JSON.stringify(created.rows)}`);
      assert(/^BKP-\d+$/.test(row.id), `snapshot id ${row.id}`);
      assert(/^[0-9a-f]{64}$/.test(row.sha), `snapshot sha ${row.sha}`);
      projectSnapshot = row.id;

      await page.evaluate(`document.querySelector('[data-backup-action="manifest"][data-snapshot-id="${row.id}"]').click()`);
      await page.waitFor(`Boolean(document.querySelector("[data-backup-page] [data-backup-manifest]"))`, "manifest panel");
      await sleep(400);
      const withManifest = await page.evaluate(pageState);
      assert(withManifest.manifest.includes("wbs:") && withManifest.manifest.includes("activities:"), `manifest ${withManifest.manifest}`);
      assert(withManifest.hasDownload, "manifest download button missing");

      const list = await api(page, "GET", backupUrl(""));
      assert(list.status === 200 && list.body.contract_version === "p6-backup-api.v1", `list ${JSON.stringify(list).slice(0, 300)}`);
      const stored = list.body.snapshots.find((item) => item.snapshot_id === row.id);
      assert(stored && stored.content_sha256 === row.sha, `stored snapshot ${JSON.stringify(stored).slice(0, 300)}`);
      assert(Object.keys(stored.section_counts).sort().join(",") === "activities,relationships,resources,wbs", `sections ${JSON.stringify(stored.section_counts)}`);

      const content = await api(page, "GET", backupUrl(`/${row.id}/content`));
      assert(content.status === 200 && content.body.contract_version === "p6-backup-api.v1", `content ${content.status}`);
      assert(Object.keys(content.body.sections).sort().join(",") === "activities,relationships,resources,wbs", `content sections ${JSON.stringify(Object.keys(content.body.sections))}`);
      await capture(page, "01-project-snapshot");
      return { snapshotId: row.id, sha: row.sha, sections: Object.keys(content.body.sections) };
    });

    await scenario("02", "عکس‌برداری چیدمان‌ها فقط بخش layouts را نگه می‌دارد", async () => {
      await setKind(page, "layouts");
      await setLabel(page, `E2E layouts ${stamp}`);
      await createFromUi(page);
      const state = await page.evaluate(pageState);
      const row = state.rows.find((item) => item.kind === "layouts" && item.text.includes(`E2E layouts ${stamp}`));
      assert(row, `layouts snapshot row missing: ${JSON.stringify(state.rows.map((item) => item.text))}`);

      const content = await api(page, "GET", backupUrl(`/${row.id}/content`));
      assert(content.status === 200, `layouts content ${content.status}`);
      assert(Object.keys(content.body.sections).join(",") === "layouts", `layouts sections ${JSON.stringify(Object.keys(content.body.sections))}`);
      await capture(page, "02-layout-snapshot");
      return { snapshotId: row.id, sections: Object.keys(content.body.sections) };
    });

    await scenario("03", "ثبت ایدمپوتنت همان عکس را برمی‌گرداند و استفادهٔ دوبارهٔ کلید ۴۰۹ است", async () => {
      const first = await api(page, "POST", backupUrl(""), {
        kind: "project",
        label: `E2E replay ${stamp}`,
        idempotency_key: idempotencyKey,
      });
      assert(first.status === 201 && first.body.replayed === false, `first capture ${JSON.stringify(first).slice(0, 300)}`);

      const replay = await api(page, "POST", backupUrl(""), {
        kind: "project",
        label: `E2E replay ${stamp}`,
        idempotency_key: idempotencyKey,
      });
      assert(replay.status === 201 && replay.body.replayed === true, `replay ${JSON.stringify(replay).slice(0, 300)}`);
      assert(replay.body.snapshot_id === first.body.snapshot_id, `replay snapshot ${replay.body.snapshot_id} vs ${first.body.snapshot_id}`);

      const reuse = await api(page, "POST", backupUrl(""), {
        kind: "project",
        label: `E2E other ${stamp}`,
        idempotency_key: idempotencyKey,
      });
      assert(reuse.status === 409 && reuse.body.code === "BACKUP_IDEMPOTENCY_KEY_REUSE", `reuse ${JSON.stringify(reuse).slice(0, 300)}`);

      const badMode = await api(page, "POST", backupUrl(`/${first.body.snapshot_id}/restore`), {
        mode: "delete",
        idempotency_key: restoreKey,
      });
      assert(badMode.status === 400 && badMode.body.code === "INVALID_RESTORE_MODE", `bad mode ${JSON.stringify(badMode).slice(0, 300)}`);

      const missing = await api(page, "GET", backupUrl("/BKP-999999/content"));
      assert(missing.status === 404 && missing.body.code === "BACKUP_SNAPSHOT_NOT_FOUND", `missing ${JSON.stringify(missing).slice(0, 300)}`);

      await reload(page);
      const state = await page.evaluate(pageState);
      assert(state.rows.some((item) => item.id === first.body.snapshot_id), "replayed snapshot is missing from the list");
      return { snapshotId: first.body.snapshot_id, reuseStatus: reuse.status, missingStatus: missing.status };
    });

    let restoredActivity = null;

    await scenario("04", "بازیابی overwrite فعالیت ویرایش‌شده را به محتوای عکس برمی‌گرداند و اجرا ثبت می‌شود", async () => {
      const activity = await firstActivity(page);
      const activityId = activity.activity_id;
      const originalName = activity.name;
      const wbsId = activity.wbs_id;
      const loaded = await readActivity(page, activityId);
      assert(loaded.status === 200 && loaded.activity, `activity read ${JSON.stringify(loaded).slice(0, 300)}`);

      assert(projectSnapshot, "project snapshot id missing from scenario 01");

      const driftName = `${originalName} (E2E drift ${stamp})`;
      const patched = await renameActivity(page, activityId, driftName, loaded.activity.record_revision, wbsId);
      assert(patched.status === 200, `activity rename ${JSON.stringify(patched).slice(0, 300)}`);
      const drifted = await readActivity(page, activityId);
      assert(drifted.activity?.name === driftName, `activity did not drift: ${JSON.stringify(drifted.activity)}`);

      await reload(page);
      await openTab(page, "restore");
      const before = await page.evaluate(pageState);
      assert(before.snapshotOptions.includes(projectSnapshot), `restore options ${JSON.stringify(before.snapshotOptions)}`);
      await page.evaluate(`(() => {
        const select = document.querySelector("[data-backup-snapshot]");
        select.value = ${JSON.stringify(projectSnapshot)};
        select.dispatchEvent(new Event("change", { bubbles: true }));
        const mode = document.querySelector("[data-backup-mode]");
        mode.value = "overwrite";
        mode.dispatchEvent(new Event("change", { bubbles: true }));
      })()`);
      await sleep(300);
      const armed = await page.evaluate(pageState);
      assert(armed.mode === "overwrite", `restore mode ${armed.mode}`);
      assert(armed.restoreDisabled === false, "restore must be enabled for an administrator");
      await capture(page, "03-restore-armed");

      await page.click('[data-backup-action="restore"]');
      await page.waitFor(
        `Boolean(document.querySelector("[data-backup-page] [data-backup-restore-summary]"))`,
        "restore summary",
      );
      await sleep(700);
      const restored = await page.evaluate(pageState);
      assert(restored.notice === "ok", `restore notice ${restored.noticeText}`);
      assert(Number(restored.restoreSummary?.updated) >= 1, `restore summary ${JSON.stringify(restored.restoreSummary)}`);
      assert(/^RSR-\d+/.test(restored.restoreSummaryText), `restore run ${restored.restoreSummaryText}`);

      const rewound = await readActivity(page, activityId);
      assert(rewound.activity?.name === originalName, `activity was not rewound: ${JSON.stringify(rewound.activity?.name)}`);
      assert(rewound.activity.record_revision > drifted.activity.record_revision, "rewound revision did not advance");
      restoredActivity = activityId;

      const runs = await api(page, "GET", backupUrl("/restores"));
      assert(runs.status === 200 && runs.body.runs.length >= 1, `restore runs ${JSON.stringify(runs).slice(0, 300)}`);
      assert(runs.body.runs.some((run) => run.snapshot_id === projectSnapshot && run.mode === "overwrite"), "overwrite run is missing");

      await openTab(page, "history");
      const history = await page.evaluate(pageState);
      assert(history.runs.length >= 1, `history rows ${history.runs.length}`);
      assert(history.runs.some((run) => /^RSR-\d+/.test(run.id)), `history ids ${JSON.stringify(history.runs.map((run) => run.id))}`);
      await capture(page, "04-restored-and-history");
      return {
        activityId,
        updated: restored.restoreSummary?.updated,
        originalName,
        run: restored.restoreSummaryText,
      };
    });

    await scenario("05", "بازیابی merge چیزی را حذف نمی‌کند و رکوردهای یکسان را رد می‌کند", async () => {
      const merged = await api(page, "POST", backupUrl(`/${projectSnapshot}/restore`), {
        mode: "merge",
        idempotency_key: mergeKey,
      });
      assert(merged.status === 200 && merged.body.replayed === false, `merge ${JSON.stringify(merged).slice(0, 300)}`);
      const counts = Object.values(merged.body.sections).reduce(
        (total, item) => ({ created: total.created + item.created, updated: total.updated + item.updated, skipped: total.skipped + item.skipped }),
        { created: 0, updated: 0, skipped: 0 },
      );
      assert(counts.created === 0, `merge created ${counts.created}`);
      assert(counts.updated === 0, `merge updated ${counts.updated}`);
      assert(counts.skipped > 0, `merge skipped ${counts.skipped}`);

      const replay = await api(page, "POST", backupUrl(`/${projectSnapshot}/restore`), {
        mode: "merge",
        idempotency_key: mergeKey,
      });
      assert(replay.status === 200 && replay.body.replayed === true, `merge replay ${JSON.stringify(replay).slice(0, 300)}`);
      assert(replay.body.run_id === merged.body.run_id, `merge replay run ${replay.body.run_id} vs ${merged.body.run_id}`);

      const activity = await readActivity(page, restoredActivity);
      assert(activity.status === 200, `post-merge activity read ${activity.status}`);
      await openTab(page, "restore");
      await capture(page, "05-merge-skip");
      return { counts, runId: merged.body.run_id };
    });

    await scenario("06", "بازبین و برنامه‌ریز عکس‌ها را می‌خوانند اما بازیابی فقط برای مدیر پروژه است", async () => {
      await loginAs(page, "Viewer");
      await openBackup(page);
      const viewer = await page.evaluate(pageState);
      assert(viewer.createDisabled === true, "viewer create must be disabled");
      await openTab(page, "restore");
      const viewerRestore = await page.evaluate(pageState);
      assert(viewerRestore.restoreDisabled === true, "viewer restore must be disabled");

      const deniedCapture = await api(page, "POST", backupUrl(""), {
        kind: "project",
        label: `E2E denied ${stamp}`,
        idempotency_key: `e2e-denied-${stamp}`,
      });
      assert(deniedCapture.status === 403 && deniedCapture.body.code === "BACKUP_PERMISSION_DENIED", `viewer capture ${JSON.stringify(deniedCapture).slice(0, 300)}`);
      const deniedRestore = await api(page, "POST", backupUrl(`/${projectSnapshot}/restore`), {
        mode: "merge",
        idempotency_key: `e2e-denied-restore-${stamp}`,
      });
      assert(deniedRestore.status === 403 && deniedRestore.body.code === "BACKUP_PERMISSION_DENIED", `viewer restore ${JSON.stringify(deniedRestore).slice(0, 300)}`);
      await capture(page, "06-viewer-read-only");

      await loginAs(page, "Planner");
      await openBackup(page);
      const planner = await page.evaluate(pageState);
      assert(planner.createDisabled === false, "planner capture must be enabled");
      await openTab(page, "restore");
      const plannerRestore = await page.evaluate(pageState);
      assert(plannerRestore.restoreDisabled === true, "planner restore must be disabled");

      const plannerCapture = await api(page, "POST", backupUrl(""), {
        kind: "project",
        label: `E2E planner ${stamp}`,
        idempotency_key: `e2e-planner-${stamp}`,
      });
      assert(plannerCapture.status === 201, `planner capture ${JSON.stringify(plannerCapture).slice(0, 300)}`);
      const plannerDeniedRestore = await api(page, "POST", backupUrl(`/${plannerCapture.body.snapshot_id}/restore`), {
        mode: "merge",
        idempotency_key: `e2e-planner-restore-${stamp}`,
      });
      assert(plannerDeniedRestore.status === 403, `planner restore ${JSON.stringify(plannerDeniedRestore).slice(0, 300)}`);
      await capture(page, "07-planner-write-only");
      return {
        viewerCapture: deniedCapture.status,
        viewerRestore: deniedRestore.status,
        plannerCapture: plannerCapture.status,
        plannerRestore: plannerDeniedRestore.status,
      };
    });

    await scenario("07", "چیدمان فارسی راست‌به‌چپ در ۱۲۸۰×۷۲۰ بدون نشان تجاری بیرونی", async () => {
      await loginAs(page, "Project administrator");
      await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
      await setLanguage(page, "fa");
      await openBackup(page);
      const state = await page.evaluate(pageState);
      assert(state.direction === "rtl", `direction ${state.direction}`);
      assert(state.heading === "پشتیبان‌گیری / بازیابی", `Persian heading ${state.heading}`);
      assert(state.tabs.map((tab) => tab.label).join(",") === "نسخه‌های پشتیبان,بازیابی,تاریخچهٔ بازیابی", `Persian tabs ${JSON.stringify(state.tabs.map((tab) => tab.label))}`);
      assert(!/oracle|primavera|\bp6\b/i.test(state.bodyText), "backup surface leaks third-party branding");
      await capture(page, "08-persian-rtl");
      return { direction: state.direction, heading: state.heading };
    });

    report.status = "pass";
    report.scenarioCount = scenarios.length;
  } catch (error) {
    report.status = "fail";
    report.error = String(error && error.stack ? error.stack : error);
    throw error;
  } finally {
    writeFileSync(join(evidenceDir, "backup-v26.json"), `${JSON.stringify(report, null, 2)}\n`);
    copyFileSync(join(evidenceDir, "backup-v26.json"), join(outDir, "backup-v26.json"));
    log(`\nEvidence: ${evidenceDir}`);
    log(`Scenarios: ${scenarios.filter((item) => item.status === "pass").length}/${scenarios.length} passed`);
    try {
      await chrome.stop();
    } catch {
      // The browser is already gone; the evidence file is what matters.
    }
  }
}

main().catch((error) => {
  process.stderr.write(`\nFAILED: ${error && error.stack ? error.stack : error}\n`);
  process.exitCode = 1;
});
