#!/usr/bin/env node
/**
 * Browser E2E for the Version 26 project document register with binary content.
 *
 * Drives the real local full-stack preview on project preview-rps-01 with
 * headless Chrome. Document metadata is created through the real
 * `/api/projects/{id}/documents` route; file bytes travel through
 * `POST/GET .../documents/{doc}/content` and `.../content/{version}`. The
 * browser computes SHA-256 from the chosen bytes, and the test independently
 * verifies the downloaded file digest. No response is mocked.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4193 node e2e/documents-binary-v26.mjs
 */

import { copyFileSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4193";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-12";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "documents-binary-v26");
const evidenceDir = join(
  artifactsDir,
  "..",
  "..",
  "..",
  "..",
  "docs",
  "workspace",
  "evidence",
  `documents-binary-v26-${evidenceDate}`,
);
const downloadDir = join(outDir, "downloads");
mkdirSync(outDir, { recursive: true });
mkdirSync(downloadDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const scenarios = [];
const screenshots = [];

const runId = Date.now().toString().slice(-7);
const DOC_ID = `DOC-V26-${runId}`;
const LARGE_TEXT_ID = `DOC-V26-BAD-${runId}`;
const V1_PDF = Buffer.from(`%PDF-1.7\nCUBI V26 evidence ${runId}\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n`);
const V2_PDF = Buffer.from(`%PDF-1.7\nCUBI V26 evidence ${runId}\nrevision two\n%%EOF\n`);
const FAKE_PDF = Buffer.from(`<!doctype html><html><body>not a pdf ${runId}</body></html>`);
const HASH1 = `sha256:${createHash("sha256").update(V1_PDF).digest("hex")}`;
const HASH2 = `sha256:${createHash("sha256").update(V2_PDF).digest("hex")}`;

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
  const host = document.querySelector("[data-documents-page]");
  const rect = (element) => {
    if (!element) return null;
    const bounds = element.getBoundingClientRect();
    return { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height };
  };
  const cells = (row) => [...row.querySelectorAll("td")].map((cell) => (cell.textContent || "").trim());
  const rows = [...host?.querySelectorAll("[data-document-row]") ?? []].map((row) => ({
    id: row.dataset.documentId,
    selected: row.getAttribute("aria-selected") === "true",
    cells: cells(row),
  }));
  const versions = [...host?.querySelectorAll("tr[data-document-version]") ?? []].map((row) => ({
    version: Number(row.dataset.documentVersion),
    cells: cells(row),
  }));
  return {
    status: host?.dataset.documentsStatus ?? null,
    selected: host?.dataset.documentsSelected ?? null,
    direction: getComputedStyle(document.querySelector(".cp-workspace") || document.body).direction,
    innerWidth,
    innerHeight,
    pageOverflow: document.documentElement.scrollWidth > innerWidth + 1,
    window: rect(host?.querySelector(".cp-register-window") || host),
    register: rect(host?.querySelector(".cp-register-table-wrap")),
    details: rect(host?.querySelector("[data-document-details]")),
    rows,
    tabs: [...host?.querySelectorAll("[data-document-tab]") ?? []].map((tab) => ({
      id: tab.dataset.documentTab,
      selected: tab.getAttribute("aria-selected") === "true",
    })),
    versions,
    selectedFile: host?.querySelector("[data-document-selected-file]")?.textContent?.trim() ?? null,
    notice: host?.querySelector("[data-document-notice]")?.textContent?.trim() ?? null,
    noticeState: host?.querySelector("[data-document-notice]")?.dataset?.state ?? null,
    uploadDisabled: host?.querySelector('[data-document-action="upload-content"]')?.disabled ?? null,
    fileInputDisabled: host?.querySelector('[name="document-content-file"]')?.disabled ?? null,
    downloadButtons: host?.querySelectorAll('[data-document-action="download-content"]').length ?? 0,
    empty: Boolean(host?.querySelector("[data-document-content-empty]")),
    text: host?.textContent ?? "",
  };
})()`;

async function capture(page, name) {
  const file = `documents-binary-v26/${name}.png`;
  await page.screenshot(file);
  copyFileSync(join(artifactsDir, file), join(evidenceDir, `${name}.png`));
  screenshots.push(`${name}.png`);
  return file;
}

async function loginAs(page, role) {
  const open = async () => {
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
  };
  await open();
  let hasPersonas = await page.evaluate('Boolean(document.querySelector(".persona"))');
  if (!hasPersonas) {
    // A previous identity is still signed in; sign out through the real route
    // so the persona this scenario selects is the one the server binds.
    const logoutStatus = await page.evaluate(
      `(async () => {
        const response = await fetch("/preview/logout", { method: "POST", redirect: "manual" });
        return response.status;
      })()`,
      { awaitPromise: true },
    );
    assert([0, 200, 302, 303].includes(logoutStatus), `unexpected logout status ${logoutStatus}`);
    await open();
    hasPersonas = await page.evaluate('Boolean(document.querySelector(".persona"))');
  }
  assert(hasPersonas, `persona cards missing for ${role}`);
  await page.click(`button[name="role"][value="${role}"]`);
  await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
  await page.click('[data-project-id="preview-rps-01"]');
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
  await sleep(1200);
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

async function openDocuments(page) {
  const clicked = await page.evaluate(`(() => {
    const buttons = [...document.querySelectorAll('[data-menu="documents"]')];
    const button = buttons.find((entry) => entry.getClientRects().length > 0) ?? buttons[0];
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, "Documents menu button is missing");
  await page.waitFor(
    `document.querySelector("[data-documents-page]")?.dataset.documentsStatus === "loaded"`,
    "document register",
    20000,
  );
  await sleep(250);
}

async function selectDocument(page, documentId) {
  const selected = await page.evaluate(`(() => {
    const row = document.querySelector('[data-document-row][data-document-id=${JSON.stringify(documentId)}]');
    if (!row) return false;
    row.click();
    return true;
  })()`);
  assert(selected, `document row ${documentId} is missing`);
  await page.waitFor(
    `document.querySelector("[data-documents-page]")?.dataset.documentsSelected === ${JSON.stringify(documentId)}`,
    `document ${documentId} selection`,
  );
  await sleep(200);
}

async function openContentTab(page) {
  await page.click('[data-documents-page] [data-document-tab="content"]');
  await page.waitFor(
    `Boolean(document.querySelector("[data-documents-page] [data-document-content]"))`,
    "document content tab",
  );
  await sleep(250);
}

async function chooseFile(page, selector, name, type, bytes) {
  const base64 = Buffer.from(bytes).toString("base64");
  const assigned = await page.evaluate(`(() => {
    const input = document.querySelector(${JSON.stringify(selector)});
    if (!input) return "missing";
    const binary = atob(${JSON.stringify(base64)});
    const data = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) data[index] = binary.charCodeAt(index);
    const file = new File([data], ${JSON.stringify(name)}, { type: ${JSON.stringify(type)} });
    const transfer = new DataTransfer();
    transfer.items.add(file);
    input.files = transfer.files;
    input.dispatchEvent(new Event("change", { bubbles: true }));
    return "ok";
  })()`);
  assert(assigned === "ok", `file input ${selector} was not assigned`);
}

async function waitForNotice(page, fragment) {
  await page.waitFor(
    `(() => {
      const node = document.querySelector("[data-documents-page] [data-document-notice]");
      return Boolean(node && (node.textContent || "").includes(${JSON.stringify(fragment)}));
    })()`,
    `notice containing ${fragment}`,
    20000,
  );
}

async function setInput(page, name, value) {
  const ok = await page.evaluate(`(() => {
    const input = document.querySelector('[data-documents-page] [name=${JSON.stringify(name)}]');
    if (!input) return false;
    input.value = ${JSON.stringify(value)};
    input.dispatchEvent(new Event("input", { bubbles: true }));
    return true;
  })()`);
  assert(ok, `input ${name} is missing`);
}

async function waitForDownload(name, timeoutMs = 15000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const entries = readdirSync(downloadDir).filter((entry) => !entry.endsWith(".crdownload"));
    if (entries.includes(name)) {
      return readFileSync(join(downloadDir, name));
    }
    await sleep(150);
  }
  throw new Error(`download ${name} did not appear in ${downloadDir}`);
}

async function main() {
  log(`CUBI documents V26 E2E — ${baseUrl}`);
  await waitForHttp(`${baseUrl}/preview/health`, 30000);
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
    contract: "cubi-documents-v26.v1",
    baseUrl,
    testedCodeSha,
    evidenceCommitSha,
    evidenceDate,
    project: "preview-rps-01",
    documentId: DOC_ID,
    startedAt: new Date().toISOString(),
    viewport: "1280x720",
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
  };

  try {
    await page.cdp.send("Page.setDownloadBehavior", {
      behavior: "allow",
      downloadPath: downloadDir,
    }).catch(async () => {
      await page.cdp.send("Browser.setDownloadBehavior", {
        behavior: "allow",
        downloadPath: downloadDir,
        eventsEnabled: true,
      });
    });
    rmSync(downloadDir, { recursive: true, force: true });
    mkdirSync(downloadDir, { recursive: true });

    await page.cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1280,
      height: 720,
      deviceScaleFactor: 1,
      mobile: false,
    });
    await loginAs(page, "admin");
    await setLanguage(page, "en");
    await openDocuments(page);

    await scenario("01", "a new document is created and its chosen file is uploaded as version 1", async () => {
      await page.click('[data-documents-page] [data-document-action="new"]');
      await page.waitForSelector('[data-documents-page] [name="document-id"]', "create form");
      await setInput(page, "document-id", DOC_ID);
      await setInput(page, "document-title", `V26 evidence ${runId}`);
      await setInput(page, "document-storage", `object://e2e/${DOC_ID}`);
      await chooseFile(page, '[data-documents-page] [name="document-create-file"]', "evidence.pdf", "application/pdf", V1_PDF);
      await page.waitFor(
        `document.querySelector('[data-documents-page] [data-document-chosen-file]')?.textContent?.includes(${JSON.stringify(HASH1)}) === true`,
        "locally computed SHA-256",
        20000,
      );
      const hashValue = await page.evaluate(
        `document.querySelector('[data-documents-page] [name="document-hash"]')?.value ?? ""`,
      );
      assert(hashValue === HASH1, `create hash ${hashValue}`);
      await page.evaluate(
        `document.querySelector('[data-documents-page] [data-document-form]').requestSubmit()`,
      );
      await page.waitFor(
        `Boolean(document.querySelector('[data-document-row][data-document-id=${JSON.stringify(DOC_ID)}]'))`,
        "created document row",
        20000,
      );
      await page.waitFor(
        `Boolean(document.querySelector('tr[data-document-version="1"]'))`,
        "uploaded version 1",
        20000,
      );
      const state = await page.evaluate(pageState);
      assert(state.selected === DOC_ID, `selected ${state.selected}`);
      assert(state.tabs.find((tab) => tab.id === "content")?.selected === true, "content tab is not active");
      assert(state.versions.length === 1, `versions ${state.versions.length}`);
      assert(state.versions[0].cells[1] === "evidence.pdf", `version file ${state.versions[0].cells[1]}`);
      assert(state.versions[0].cells[4].startsWith("sha256:"), `version hash ${state.versions[0].cells[4]}`);
      assert(state.noticeState === "ok" && state.notice.includes("Stored version 1"), `notice ${state.notice}`);
      await capture(page, "01-document-created-version-1");
      return { documentId: DOC_ID, versions: state.versions.length, hash: HASH1 };
    });

    await scenario("02", "version 1 downloads with a matching SHA-256 and the original bytes", async () => {
      const filename = `evidence-${runId}.pdf`;
      // The server names the download from the stored original filename.
      await page.click('[data-document-version="1"] [data-document-action="download-content"]');
      const downloaded = await waitForDownload("evidence.pdf");
      assert(downloaded.equals(V1_PDF), `downloaded bytes differ (${downloaded.length} vs ${V1_PDF.length})`);
      const digest = `sha256:${createHash("sha256").update(downloaded).digest("hex")}`;
      assert(digest === HASH1, `downloaded digest ${digest}`);
      await page.waitFor(
        `(() => {
          const node = document.querySelector("[data-documents-page] [data-document-notice]");
          return Boolean(node && (node.textContent || "").includes("SHA-256 verified"));
        })()`,
        "verified download notice",
      );
      await capture(page, "02-verified-download");
      return { filename, bytes: downloaded.length, digest };
    });

    await scenario("03", "a second upload becomes version 2 while version 1 stays byte-identical", async () => {
      await chooseFile(page, '[data-documents-page] [name="document-content-file"]', "evidence.pdf", "application/pdf", V2_PDF);
      await page.waitFor(
        `Boolean(document.querySelector('[data-documents-page] [data-document-selected-file]'))`,
        "selected file summary",
      );
      await page.click('[data-documents-page] [data-document-action="upload-content"]');
      await page.waitFor(
        `Boolean(document.querySelector('tr[data-document-version="2"]'))`,
        "uploaded version 2",
        20000,
      );
      const state = await page.evaluate(pageState);
      assert(state.versions.length === 2, `versions ${state.versions.length}`);
      const revisionCells = state.rows.find((row) => row.id === DOC_ID)?.cells ?? [];
      assert(revisionCells.at(-1) === "3", `document revision ${revisionCells.at(-1)} after two uploads`);

      rmSync(join(downloadDir, "evidence.pdf"), { force: true });
      await page.click('[data-document-version="1"] [data-document-action="download-content"]');
      const first = await waitForDownload("evidence.pdf");
      assert(first.equals(V1_PDF), "version 1 bytes changed after version 2 upload");
      rmSync(join(downloadDir, "evidence.pdf"), { force: true });
      await page.click('[data-document-version="2"] [data-document-action="download-content"]');
      const second = await waitForDownload("evidence.pdf");
      const digest = `sha256:${createHash("sha256").update(second).digest("hex")}`;
      assert(digest === HASH2, `version 2 digest ${digest}`);
      assert(!second.equals(first), "version 2 returned version 1 bytes");
      await capture(page, "03-two-immutable-versions");
      return { versions: state.versions.length, version1: HASH1, version2: HASH2 };
    });

    await scenario("04", "the server rejects a declared PDF whose bytes are not a PDF", async () => {
      await page.click('[data-documents-page] [data-document-action="new"]');
      await page.waitForSelector('[data-documents-page] [name="document-id"]', "create form");
      await setInput(page, "document-id", LARGE_TEXT_ID);
      await setInput(page, "document-title", "Rejected payload");
      await setInput(page, "document-storage", `object://e2e/${LARGE_TEXT_ID}`);
      await chooseFile(page, '[data-documents-page] [name="document-create-file"]', "fake.pdf", "application/pdf", FAKE_PDF);
      await page.waitFor(
        `Boolean(document.querySelector('[data-documents-page] [data-document-chosen-file]'))`,
        "selected fake pdf",
      );
      // Clear the automatically computed hash so the metadata create uses a
      // real digest but the record is submitted; the file upload then fails
      // server-side because the bytes are HTML, not PDF.
      await page.evaluate(
        `document.querySelector('[data-documents-page] [data-document-form]').requestSubmit()`,
      );
      await page.waitFor(
        `Boolean(document.querySelector('[data-document-row][data-document-id=${JSON.stringify(LARGE_TEXT_ID)}]'))`,
        "created rejection document",
        20000,
      );
      await waitForNotice(page, "DOCUMENT_CONTENT_TYPE_MISMATCH");
      const state = await page.evaluate(pageState);
      assert(state.noticeState === "error", `notice state ${state.noticeState}`);
      assert(state.notice.includes("rejected the file type"), `notice copy ${state.notice}`);
      assert(state.empty === true || state.versions.length === 0, "rejected bytes must not become a version");
      await capture(page, "04-server-rejects-mismatched-bytes");
      return { code: "DOCUMENT_CONTENT_TYPE_MISMATCH", versions: state.versions.length };
    });

    await scenario("05", "the register and versions survive a full page reload", async () => {
      await page.navigate(`${baseUrl}/app?view=live`, null, "workspace reload");
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
      await sleep(1000);
      await openDocuments(page);
      await selectDocument(page, DOC_ID);
      await openContentTab(page);
      await page.waitFor(
        `document.querySelectorAll("tr[data-document-version]").length === 2`,
        "persisted versions",
        20000,
      );
      const state = await page.evaluate(pageState);
      assert(state.versions.length === 2, `persisted versions ${state.versions.length}`);
      assert(state.versions.find((version) => version.version === 1), "version 1 missing after reload");
      await capture(page, "05-persisted-after-reload");
      return { versions: state.versions.length };
    });

    await scenario("06", "a Viewer can download but cannot upload file bytes", async () => {
      await loginAs(page, "viewer");
      await setLanguage(page, "en");
      await openDocuments(page);
      await selectDocument(page, DOC_ID);
      await openContentTab(page);
      await page.waitFor(
        `document.querySelectorAll("tr[data-document-version]").length === 2`,
        "viewer versions",
      );
      const state = await page.evaluate(pageState);
      assert(state.direction === "ltr", `direction ${state.direction}`);
      assert(state.fileInputDisabled === true, "viewer file input must be disabled");
      assert(state.uploadDisabled === true, "viewer upload button must be disabled");
      assert(state.downloadButtons === 2, `viewer download buttons ${state.downloadButtons}`);
      assert(/Viewers may download stored versions/.test(state.text), "viewer permission hint missing");
      await capture(page, "06-viewer-read-only-bytes");
      return { downloads: state.downloadButtons, uploadDisabled: true };
    });

    await scenario("07", "the Content tab renders in Persian right-to-left at 1280x720", async () => {
      await loginAs(page, "admin");
      await setLanguage(page, "fa");
      await openDocuments(page);
      await selectDocument(page, DOC_ID);
      await openContentTab(page);
      await page.waitFor(
        `document.querySelectorAll("tr[data-document-version]").length === 2`,
        "Persian versions",
      );
      const state = await page.evaluate(pageState);
      assert(state.direction === "rtl", `direction ${state.direction}`);
      assert(/محتوا/.test(state.text), "Persian Content tab label is missing");
      assert(/بارگذاری به‌عنوان نسخهٔ جدید/.test(state.text), "Persian upload label is missing");
      assert(/بایت‌ها پشت یک مرجع/.test(state.text), "Persian storage note is missing");
      assert(state.pageOverflow === false, "Persian documents window overflows horizontally");
      assert(state.window && state.window.x >= 0, "Persian window has no layout box");
      await capture(page, "07-documents-1280x720-fa");
      return { direction: state.direction, versions: state.versions.length };
    });

    await scenario("08", "the document window fits 1366x768 and 1920x1080 without overflow", async () => {
      await setLanguage(page, "en");
      await openDocuments(page);
      await selectDocument(page, DOC_ID);
      await openContentTab(page);
      const results = [];
      for (const [width, height] of [[1366, 768], [1920, 1080]]) {
        await page.cdp.send("Emulation.setDeviceMetricsOverride", {
          width,
          height,
          deviceScaleFactor: 1,
          mobile: false,
        });
        await sleep(350);
        const state = await page.evaluate(pageState);
        assert(state.status === "loaded", `${width} status ${state.status}`);
        assert(state.pageOverflow === false, `${width} page overflow`);
        assert(state.window && state.window.width > 0, `${width} window missing`);
        assert(state.window.y + state.window.height <= height + 1, `${width} window below the fold: ${JSON.stringify(state.window)}`);
        assert(state.details && state.details.width > 0, `${width} details pane missing`);
        assert(state.versions.length === 2, `${width} versions ${state.versions.length}`);
        results.push({ width, height, window: state.window, details: state.details });
        await capture(page, `08-documents-${width}x${height}-en`);
      }
      await page.cdp.send("Emulation.setDeviceMetricsOverride", {
        width: 1280,
        height: 720,
        deviceScaleFactor: 1,
        mobile: false,
      });
      return { viewports: results };
    });

    assert(exceptions.length === 0, `uncaught page exceptions: ${JSON.stringify(exceptions.slice(0, 3))}`);
    assert(consoleErrors.length === 0, `console errors: ${JSON.stringify(consoleErrors.slice(0, 3))}`);
  } finally {
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(outDir, "documents-binary-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(evidenceDir, "documents-binary-v26.json"), JSON.stringify(report, null, 2));
    page.cdp.close();
    chrome.cdp.close();
    await chrome.stop();
  }

  const failed = scenarios.filter((item) => item.status !== "pass");
  log(`\nScenarios: ${scenarios.length - failed.length} passed, ${failed.length} failed`);
  if (failed.length) process.exitCode = 1;
}

main().catch((error) => {
  process.stderr.write(`${error && error.stack ? error.stack : error}\n`);
  process.exit(1);
});
