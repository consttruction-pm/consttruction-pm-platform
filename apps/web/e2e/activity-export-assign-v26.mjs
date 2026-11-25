#!/usr/bin/env node
/**
 * Browser E2E for the two Activities-window commands that were previously
 * disabled but whose service paths already exist:
 *
 *   - Edit > Export to Excel (authoritative XLSX workbook + response digest)
 *   - Assign Resources (opens the real assignment create form pre-filled)
 *
 * It drives the local full-stack preview (SQLite, real WSGI routes, shared
 * calculation core) with headless Chrome through the DevTools protocol. It does
 * not mock a response, does not build a workbook in the browser, and never
 * touches production.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4199 node e2e/activity-export-assign-v26.mjs
 */

import { createHash } from "node:crypto";
import { mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4199";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-25";
const outDir = join(artifactsDir, "activity-export-assign-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `activity-export-assign-v26-${evidenceDate}`);
const downloadDir = join(outDir, "downloads");
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });
mkdirSync(downloadDir, { recursive: true });

const PROJECT = "preview-rps-01";
const EXPORT_PATH = `/api/projects/${PROJECT}/exchange/export?dataset=activities&format=xlsx`;

const scenarios = [];
const screenshots = [];
const exceptions = [];
const consoleErrors = [];
const apiFailures = [];

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
  const file = `activity-export-assign-v26/${name}.png`;
  await page.screenshot(file);
  writeFileSync(join(evidenceDir, `${name}.png`), readFileSync(join(artifactsDir, file)));
  screenshots.push(`${name}.png`);
  return file;
}

async function selectActivityRow(page, index = 1) {
  const clicked = await page.evaluate(`(() => {
    const rows = [...document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]")];
    const row = rows[${index}] ?? rows[0];
    if (!row) return null;
    row.scrollIntoView({ block: "center" });
    row.click();
    return row.dataset.activityId;
  })()`);
  assert(clicked, `no activity row at index ${index}`);
  await page.waitFor(
    `Boolean(document.querySelector('#cp-activity-grid tbody tr[data-activity-id][aria-selected="true"]'))`,
    "selected activity row",
  );
  await sleep(250);
  return clicked;
}

async function openRowContextMenu(page) {
  const point = await page.evaluate(`(() => {
    const row = document.querySelector('#cp-activity-grid tbody tr[data-activity-id][aria-selected="true"]');
    if (!row) return null;
    row.scrollIntoView({ block: "center" });
    const rect = row.getBoundingClientRect();
    return { x: Math.round(rect.left + Math.min(40, rect.width / 3)), y: Math.round(rect.top + Math.min(6, rect.height / 2)) };
  })()`);
  assert(point, "selected row has no measurable bounds");
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: point.x, y: point.y, button: "none", buttons: 0 });
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x: point.x, y: point.y, button: "right", buttons: 2, clickCount: 1 });
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: point.x, y: point.y, button: "right", buttons: 0, clickCount: 1 });
  await page.waitForSelector('[data-activity-menu-command="edit.export-excel"]', "row context menu");
  await sleep(150);
  return point;
}

function waitForDownloadFile(dir, timeoutMs = 15000) {
  const deadline = Date.now() + timeoutMs;
  return new Promise((resolve, reject) => {
    const poll = () => {
      const entries = (() => {
        try {
          return readdirSync(dir);
        } catch {
          return [];
        }
      })();
      const xlsx = entries.find((name) => name.endsWith(".xlsx") && !name.endsWith(".crdownload"));
      if (xlsx) return resolve(join(dir, xlsx));
      if (Date.now() > deadline) return reject(new Error(`DOWNLOAD_TIMEOUT: no .xlsx in ${dir} (${entries.join(", ")})`));
      setTimeout(poll, 100);
    };
    poll();
  });
}

async function main() {
  const health = await waitForHttp(`${baseUrl}/preview/health`, 30000);
  assert(health.status === "ok" || health.status === 200, `preview health ${health.status}`);

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
    contract: "cubi-activity-export-assign-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    capturedAt: new Date().toISOString(),
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
  };

  try {
    await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
    await sleep(300);
    try {
      await page.cdp.send("Browser.setDownloadBehavior", { behavior: "allow", downloadPath: downloadDir, eventsEnabled: true });
    } catch {
      await page.cdp.send("Page.setDownloadBehavior", { behavior: "allow", downloadPath: downloadDir });
    }

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
    await sleep(1200);

    const selectedActivity = await selectActivityRow(page, 1);
    log(`selected activity ${selectedActivity}`);

    await scenario("01", "منوی زمینهٔ ردیف، Export to Excel و Assign Resources را فعال (بدون دلیل غیرفعال) نشان می‌دهد", async () => {
      await openRowContextMenu(page);
      const state = await page.evaluate(`(() => {
        const menu = document.querySelector(".cp-context-menu-portal");
        const read = (command) => {
          const button = menu?.querySelector('[data-activity-menu-command="' + command + '"]');
          return button ? {
            present: true,
            disabled: button.disabled,
            reason: button.getAttribute("title"),
            label: (button.textContent || "").trim(),
          } : { present: false };
        };
        return { export: read("edit.export-excel"), assign: read("activity.assign-resources") };
      })()`);
      assert(state.export.present, "Export to Excel is absent from the row menu");
      assert(state.export.disabled === false, `Export to Excel is disabled: ${state.export.reason}`);
      assert(!state.export.reason, `Export to Excel still carries a stale reason: ${state.export.reason}`);
      assert(state.assign.present, "Assign Resources is absent from the row menu");
      assert(state.assign.disabled === false, `Assign Resources is disabled: ${state.assign.reason}`);
      assert(!state.assign.reason, `Assign Resources still carries a stale reason: ${state.assign.reason}`);
      await capture(page, "01-row-menu-enabled");
      return { exportLabel: state.export.label, assignLabel: state.assign.label, selectedActivity };
    });

    await scenario("02", "Export to Excel یک activities.xlsx واقعی با هش تأییدشدهٔ پاسخ دانلود می‌کند", async () => {
      const server = await page.evaluate(`(async () => {
        const response = await fetch(${JSON.stringify(EXPORT_PATH)}, { credentials: "same-origin" });
        if (!response.ok) return { ok: false, status: response.status };
        const bytes = new Uint8Array(await response.arrayBuffer());
        const digest = await crypto.subtle.digest("SHA-256", bytes);
        const hex = [...new Uint8Array(digest)].map((value) => value.toString(16).padStart(2, "0")).join("");
        return {
          ok: true,
          status: response.status,
          header: response.headers.get("x-content-sha256"),
          contentType: response.headers.get("content-type"),
          disposition: response.headers.get("content-disposition"),
          computed: hex,
          byteSize: bytes.byteLength,
        };
      })()`, { awaitPromise: true });
      assert(server.ok, `export fetch failed with ${server.status}`);
      assert(/spreadsheetml\.sheet/.test(server.contentType ?? ""), `content type ${server.contentType}`);
      assert(/activities\.xlsx/.test(server.disposition ?? ""), `disposition ${server.disposition}`);
      assert(server.header === server.computed, `server digest ${server.header} != body ${server.computed}`);

      await page.click('[data-activity-menu-command="edit.export-excel"]');
      await page.waitFor(
        `document.querySelector('[data-activity-export-notice][data-state="ok"]') !== null`,
        "export success notice",
      );
      const notice = await page.evaluate(`(() => {
        const node = document.querySelector("[data-activity-export-notice]");
        return { state: node?.dataset.state ?? null, text: (node?.textContent ?? "").trim() };
      })()`);
      assert(/activities\.xlsx/.test(notice.text), `notice filename: ${notice.text}`);
      assert(/digest verified/.test(notice.text), `notice digest line: ${notice.text}`);

      const file = await waitForDownloadFile(downloadDir);
      const bytes = readFileSync(file);
      const fileDigest = createHash("sha256").update(bytes).digest("hex");
      assert(bytes.length > 4, `downloaded workbook is empty (${bytes.length} bytes)`);
      assert(bytes[0] === 0x50 && bytes[1] === 0x4b && bytes[2] === 0x03 && bytes[3] === 0x04, "downloaded file is not an XLSX/ZIP container");
      assert(fileDigest === server.header, `download digest ${fileDigest} != server ${server.header}`);
      assert(bytes.length === server.byteSize, `download size ${bytes.length} != server ${server.byteSize}`);
      await capture(page, "02-export-notice");
      return { notice: notice.text, download: { name: file.split("/").pop(), byteSize: bytes.length, sha256: fileDigest } };
    });

    await scenario("03", "Assign Resources پنجرهٔ تخصیص را با فرم ایجاد و فعالیت انتخاب‌شده پیش‌پُرشده باز می‌کند و رکورد جعلی نمی‌سازد", async () => {
      const before = await page.evaluate(`(async () => {
        const response = await fetch("/api/projects/${PROJECT}/p6/resource-assignments", { credentials: "same-origin" });
        const body = await response.json();
        return (body.assignments ?? []).length;
      })()`, { awaitPromise: true });

      await openRowContextMenu(page);
      await page.click('[data-activity-menu-command="activity.assign-resources"]');
      await page.waitForSelector("[data-assignment-form] select[name=\"activity-id\"]", "assignment create form");
      await sleep(400);
      const state = await page.evaluate(`(() => {
        const workspace = document.querySelector(".cp-workspace");
        const select = document.querySelector('[data-assignment-form] select[name="activity-id"]');
        return {
          activeMenu: workspace?.dataset.activeMenu ?? null,
          value: select?.value ?? null,
          options: [...(select?.querySelectorAll("option") ?? [])].map((option) => option.value).filter(Boolean),
        };
      })()`);
      assert(state.activeMenu === "assignments", `active window is ${state.activeMenu}`);
      assert(state.options.includes(selectedActivity), `activity ${selectedActivity} missing from the form options`);
      assert(state.value === selectedActivity, `pre-filled activity is ${state.value}`);

      const after = await page.evaluate(`(async () => {
        const response = await fetch("/api/projects/${PROJECT}/p6/resource-assignments", { credentials: "same-origin" });
        const body = await response.json();
        return (body.assignments ?? []).length;
      })()`, { awaitPromise: true });
      assert(after === before, `opening the form wrote an assignment (${before} -> ${after})`);
      await capture(page, "03-assign-prefilled");
      return { activeMenu: state.activeMenu, activityId: state.value, assignmentsBefore: before, assignmentsAfter: after };
    });

    await scenario("04", "بدون خطای JavaScript، پاسخ ۵xx یا نقض کنسول", async () => {
      assert(exceptions.length === 0, `runtime exceptions: ${JSON.stringify(exceptions)}`);
      assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors)}`);
      assert(apiFailures.length === 0, `api failures: ${JSON.stringify(apiFailures)}`);
      return { exceptions: 0, consoleErrors: 0, apiFailures: 0 };
    });
  } finally {
    try {
      chrome.stop();
    } catch {
      /* the managed runtime owns the process group */
    }
    writeFileSync(join(outDir, "activity-export-assign-v26.json"), `${JSON.stringify(report, null, 2)}\n`);
    writeFileSync(join(evidenceDir, "activity-export-assign-v26.json"), `${JSON.stringify(report, null, 2)}\n`);
    log(`\nwrote ${join(outDir, "activity-export-assign-v26.json")}`);
  }
}

main().catch((error) => {
  process.stderr.write(`\nE2E FAILED: ${error && error.stack ? error.stack : error}\n`);
  process.exitCode = 1;
});
