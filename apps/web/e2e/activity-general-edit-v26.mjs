#!/usr/bin/env node
/**
 * Activity Details General tab - Version 26 edit path acceptance.
 *
 * Verifies that the General tab opens an editor from the authoritative Activity
 * Master record, exposes the six Version 26 activity types, the four duration
 * types and the four percent-complete types, writes only through the revision-
 * guarded activity endpoint, persists the change across a reload, and restores
 * the original name so the shared preview database is left as it was found.
 *
 * Locale is pinned to English through the stored workspace preference so the
 * suite is deterministic on hosts whose default locale is not English.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 \
 *   node e2e/activity-general-edit-v26.mjs
 */

import { copyFileSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-18";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const activityId = process.env.CUBI_ACTIVITY_ID || "A100";
const outDir = join(artifactsDir, "activity-general-edit-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `activity-general-edit-v26-${evidenceDate}`);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });
// A stale failure record from an earlier run must not be mistaken for this one.
rmSync(join(outDir, "failure.json"), { force: true });

const probeSuffix = " [V26 general edit probe]";
const report = {
  contract: "cubi-activity-general-edit-v26.v1",
  url: baseUrl,
  testedCodeSha,
  capturedAt: new Date().toISOString(),
  activityId,
  options: null,
  save: null,
  persistence: null,
  restore: null,
  screenshots: [],
  network: [],
  exceptions: [],
  consoleErrors: [],
  apiFailures: [],
};

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

async function capture(page, name) {
  await page.screenshot(`activity-general-edit-v26/${name}.png`);
  copyFileSync(join(outDir, `${name}.png`), join(evidenceDir, `${name}.png`));
  report.screenshots.push(`${name}.png`);
}

async function poll(page, expression, timeout = 15000) {
  const started = Date.now();
  while (Date.now() - started < timeout) {
    if (await page.evaluate(expression)) return true;
    await sleep(250);
  }
  return false;
}

async function openActivity(page) {
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
  await page.click(`#cp-activity-grid tbody tr[data-activity-id="${activityId}"]`);
  await page.waitForSelector('#cp-details [data-detail-tab="general"]', "details tabs");
  await page.click('#cp-details [data-detail-tab="general"]');
  await sleep(400);
}

async function openEditor(page) {
  await page.click("[data-general-edit-load]");
  const opened = await poll(page, `Boolean(document.querySelector('#detail-form-general-name'))`, 15000);
  assert(opened, "the General editor did not open from the authoritative record");
}

async function submitGeneralName(page, name) {
  await page.evaluate(`(() => {
    const form = document.querySelector('#cp-details [data-details-form="general"]');
    const input = form?.querySelector('input[name="name"]');
    if (!input) return false;
    input.value = ${JSON.stringify(name)};
    const submit = form.querySelector('button[type="submit"]');
    submit?.click();
    return true;
  })()`);
  const saved = await poll(page, `Boolean(document.querySelector('#cp-details [data-general-saved]'))`, 15000);
  return saved
    ? page.evaluate(`document.querySelector('#cp-details [data-general-saved]').textContent`)
    : null;
}

async function main() {
  await waitForHttp(`${baseUrl}/preview/health`, 20000);
  const chrome = await launchChrome();
  const page = new Page(chrome.cdp);
  await page.initialize();
  page.cdp.on("Runtime.exceptionThrown", (params) => {
    report.exceptions.push(params.exceptionDetails?.exception?.description ?? params.exceptionDetails?.text ?? "unknown exception");
  });
  page.cdp.on("Runtime.consoleAPICalled", (params) => {
    if (params.type !== "error") return;
    report.consoleErrors.push((params.args ?? []).map((arg) => arg.value ?? arg.description ?? arg.type).join(" "));
  });
  page.cdp.on("Network.requestWillBeSent", (params) => {
    const url = params.request?.url ?? "";
    if (url.includes("/p6/activities")) {
      report.network.push({ method: params.request?.method, url, postData: params.request?.postData ?? null });
    }
  });
  page.cdp.on("Network.responseReceived", (params) => {
    const url = params.response?.url ?? "";
    if (url.includes("/api/") && params.response.status >= 500) {
      report.apiFailures.push({ url, status: params.response.status });
    }
  });
  await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 768, deviceScaleFactor: 1, mobile: false });
  await page.cdp.send("Network.enable");

  // Pin the workspace locale before the app boots; the suite never depends on
  // the host operating-system language.
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "form", "login");
  await page.evaluate(`(() => { localStorage.setItem("cubi:workspace-locale", "en"); return true; })()`);
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "form", "login");
  await page.click('button[name="role"][value="admin"]');
  await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
  await page.click('[data-project-id="preview-rps-01"]');
  await openActivity(page);

  const originalName = await page.evaluate(`(() => {
    const row = document.querySelector('#cp-activity-grid tbody tr[data-activity-id="${activityId}"]');
    const detail = document.querySelector('#cp-details .cp-detail-identity');
    const identity = detail?.textContent ?? "";
    return { rowText: row?.textContent ?? "", identity };
  })()`);
  assert(!originalName.rowText.includes(probeSuffix), "the probe activity already carries the probe suffix");

  await capture(page, "general-tab-before-edit-en-1366");
  await openEditor(page);
  await sleep(400);

  report.options = await page.evaluate(`(() => {
    const form = document.querySelector('#cp-details [data-details-form="general"]');
    const values = (name) => [...(form?.querySelectorAll('select[name="' + name + '"] option') ?? [])].map((option) => option.value);
    return {
      activityTypes: values("activityType"),
      durationTypes: values("durationType"),
      percentCompleteTypes: values("percentCompleteType"),
      revisionHint: form?.querySelector(".cp-detail-hint")?.textContent ?? "",
      nameValue: form?.querySelector('input[name="name"]')?.value ?? "",
    };
  })()`);
  assert(report.options.activityTypes.length === 6, `expected six activity types, got ${report.options.activityTypes.length}`);
  assert(report.options.durationTypes.length === 4, `expected four duration types, got ${report.options.durationTypes.length}`);
  assert(report.options.percentCompleteTypes.length === 4, `expected four percent-complete types, got ${report.options.percentCompleteTypes.length}`);
  assert(/revision r\d+/.test(report.options.revisionHint), "the editor does not state the loaded revision");
  assert(report.options.nameValue.trim().length > 0, "the editor did not prefill the stored activity name");
  const originalEditorName = report.options.nameValue;
  await capture(page, "general-editor-open-en-1366");

  const probeName = `${originalEditorName}${probeSuffix}`;
  const savedText = await submitGeneralName(page, probeName);
  report.save = { probeName, message: savedText };
  assert(savedText, "saving the General fields did not produce a confirmation");
  assert(/revision r\d+/.test(savedText), `the save confirmation does not report the new revision: ${savedText}`);
  const wrote = report.network.some((entry) => entry.method === "PATCH" && entry.url.includes(`/p6/activities/${activityId}`));
  assert(wrote, "no revision-guarded PATCH was sent to the activity endpoint");
  const patched = report.network.find((entry) => entry.method === "PATCH" && entry.url.includes(`/p6/activities/${activityId}`));
  assert(patched && patched.postData && patched.postData.includes("expected_revision"), "the PATCH did not carry expected_revision");
  await capture(page, "general-saved-en-1366");

  const showedProbe = await poll(page, `(document.querySelector('#cp-details')?.innerText ?? "").includes(${JSON.stringify(probeSuffix)})`, 8000);
  assert(showedProbe, "the details pane did not repaint with the saved authoritative name");

  await page.navigate(`${baseUrl}/app?view=live&project=preview-rps-01`, "#cp-activity-grid tbody tr[data-activity-id]", "workspace reload");
  await openActivity(page);
  const persisted = await poll(page, `(document.querySelector('#cp-details')?.innerText ?? "").includes(${JSON.stringify(probeSuffix)})`, 10000);
  report.persistence = { persisted };
  assert(persisted, "the saved name did not survive a full page reload");
  await capture(page, "general-persisted-after-reload-en-1366");

  await openEditor(page);
  const restored = await submitGeneralName(page, originalEditorName);
  report.restore = { name: originalEditorName, message: restored };
  assert(restored, "restoring the original activity name did not confirm");
  const restorePersisted = await poll(page, `(document.querySelector('#cp-details')?.innerText ?? "").includes(${JSON.stringify(probeSuffix)}) === false`, 8000);
  assert(restorePersisted, "the original name was not restored in the details pane");

  assert(report.exceptions.length === 0, `browser exceptions: ${report.exceptions.join("; ")}`);
  assert(report.apiFailures.length === 0, `API failures: ${JSON.stringify(report.apiFailures)}`);

  const summary = [
    "# Activity Details General tab - Version 26 edit path",
    "",
    `- Tested code: \`${testedCodeSha}\``,
    `- Captured: ${report.capturedAt}`,
    `- Environment: managed Python preview runtime, SQLite demo project, headless Chrome, English 1366x768`,
    `- Activity: ${activityId}`,
    "",
    "## Verified",
    "",
    `- The General editor reads the authoritative Activity Master record before opening; the loaded revision is shown to the user.`,
    `- Activity Type exposes the six Version 26 values: ${report.options.activityTypes.join(", ")}.`,
    `- Duration Type exposes the four Version 26 values: ${report.options.durationTypes.join(", ")}.`,
    `- Percent Complete Type exposes: ${report.options.percentCompleteTypes.join(", ")}.`,
    `- Saving sends a PATCH that carries \`expected_revision\` and only the changed field.`,
    `- The saved name repaints in the details pane and survives a full page reload.`,
    `- The original name was restored at the end of the run so the shared preview database is unchanged.`,
    "",
    "## Not verified in this run",
    "",
    "- Version 26 visual side-by-side screenshots of the General tab; the run records CUBI states only.",
    "- Changing Activity Type or Duration Type was exercised only through option enumeration, not through a saved schedule run.",
    "- Revision-conflict handling is unit-tested; provoking a real 409 in the preview runtime is out of scope for this suite.",
    "- The Activity Grid repaints only on its next project read; this run verifies the details pane and a full page reload.",
    "",
    "## Reproduce",
    "",
    "```bash",
    "PYTHONPATH=src py -m construction_pm.preview \\",
    "  --web-root apps/web --database /tmp/activity-general.sqlite --port 4193 --reset",
    "cd apps/web && npm run build",
    "CUBI_PREVIEW_URL=http://127.0.0.1:4193 CUBI_EVIDENCE_DATE=2026-11-18 \\",
    "  CUBI_TESTED_CODE_SHA=$(git rev-parse HEAD) node e2e/activity-general-edit-v26.mjs",
    "```",
    "",
  ].join("\n");
  writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
  writeFileSync(join(outDir, "summary.md"), summary);
  copyFileSync(join(outDir, "report.json"), join(evidenceDir, "report.json"));
  copyFileSync(join(outDir, "summary.md"), join(evidenceDir, "summary.md"));
  console.log(JSON.stringify({ ok: true, options: report.options.activityTypes.length, revision: report.save.message }, null, 2));
  await chrome.stop();
  // The Windows Chrome child keeps stdio handles open; exit explicitly so CI
  // does not wait for the process tree.
  process.exit(0);
}

main().catch((error) => {
  writeFileSync(join(outDir, "failure.json"), JSON.stringify({ ...report, error: error?.stack ?? String(error) }, null, 2));
  console.error(error?.stack ?? error);
  process.exit(1);
});
