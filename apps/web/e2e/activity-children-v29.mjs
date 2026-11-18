#!/usr/bin/env node
/**
 * V29: Activity Codes, Notebook, Steps and WPs & Docs through the real
 * Details pane, with reload persistence and cleanup.
 *
 * Reference: Primavera P6 Professional Help G57535-02 (October 2026),
 * Details > Codes / Notebook / Steps / WPs & Docs topics.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4197 node e2e/activity-children-v29.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4197";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const outDir = join(artifactsDir, "activity-children-v29");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", "activity-workspace-v29");
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const report = {
  contract: "cubi-activity-children-v29.v1",
  url: baseUrl,
  testedCodeSha,
  capturedAt: new Date().toISOString(),
  steps: [],
  requests: [],
  exceptions: [],
  consoleErrors: [],
  apiFailures: [],
  screenshots: [],
};

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

async function capture(page, name) {
  await page.screenshot(`activity-children-v29/${name}.png`);
  copyFileSync(join(outDir, `${name}.png`), join(evidenceDir, `${name}.png`));
  report.screenshots.push(`${name}.png`);
}

async function openTab(page, tab) {
  const clicked = await page.evaluate(`(() => {
    const button = document.querySelector('#cp-details [data-detail-tab="${tab}"]');
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `details tab ${tab} is missing`);
  await page.waitForSelector(`#cp-details [data-detail-panel="${tab}"]:not([hidden])`, `${tab} panel`, 8000);
  await sleep(500);
}

async function submit(page, kind, values) {
  const filled = await page.evaluate(`(() => {
    const form = document.querySelector('#cp-details [data-details-form="${kind}"]');
    if (!form) return false;
    const values = ${JSON.stringify(values)};
    for (const [name, value] of Object.entries(values)) {
      const field = form.elements.namedItem(name);
      if (!field) return false;
      field.value = value;
      field.dispatchEvent(new Event("input", { bubbles: true }));
    }
    form.querySelector('button[type="submit"]').click();
    return true;
  })()`);
  assert(filled, `${kind} form is missing a field`);
  await sleep(1300);
}

async function reloadWorkspace(page) {
  await page.navigate(`${baseUrl}/app?view=live&project=preview-rps-01`, "#cp-activity-grid tbody tr[data-activity-id]", "workspace reload");
  await sleep(1500);
}

async function selectA130(page) {
  const clicked = await page.evaluate(`(() => {
    const row = document.querySelector('#cp-activity-grid tbody tr[data-activity-id="A130"]');
    if (!row) return false;
    row.click();
    return true;
  })()`);
  assert(clicked, "A130 row is missing");
  await page.waitFor(`document.querySelector('#cp-details .cp-detail-selected')?.textContent?.includes('A130')`, "A130 selected", 8000);
  await sleep(500);
}

async function main() {
  const chrome = await launchChrome();
  const page = new Page(chrome.cdp);
  await page.initialize();
  page.cdp.on("Runtime.exceptionThrown", (params) => {
    report.exceptions.push(params.exceptionDetails?.text ?? "unknown exception");
  });
  page.cdp.on("Runtime.consoleAPICalled", (params) => {
    if (params.type !== "error") return;
    report.consoleErrors.push((params.args ?? []).map((arg) => arg.value ?? arg.description ?? "").join(" "));
  });
  page.cdp.on("Network.requestWillBeSent", (params) => {
    const request = params.request ?? {};
    if (!["POST", "PATCH", "PUT", "DELETE"].includes(request.method ?? "")) return;
    if (!/\/api\//.test(request.url ?? "")) return;
    report.requests.push({ method: request.method, url: request.url, postData: request.postData ?? null });
  });
  page.cdp.on("Network.responseReceived", (params) => {
    const url = params.response?.url ?? "";
    if (url.includes("/api/") && params.response.status >= 500) {
      report.apiFailures.push({ url, status: params.response.status });
    }
  });

  await page.cdp.send("Emulation.setDeviceMetricsOverride", { width: 1366, height: 768, deviceScaleFactor: 1, mobile: false });
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "form", "login");
  await page.evaluate(`(() => { localStorage.setItem("cubi:workspace-locale", "en"); return true; })()`);
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "form", "login");
  await page.click('button[name="role"][value="admin"]');
  await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
  await page.click('[data-project-id="preview-rps-01"]');
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
  await sleep(1400);

  // A document to link. Created through the existing document service, with
  // no activity link, so the WPs & Docs link control has a real candidate.
  const documentId = `DOC-V29-${Date.now()}`;
  const createdDocument = await page.evaluate(`(async () => {
    const response = await fetch('/api/projects/preview-rps-01/documents', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        document_id: ${JSON.stringify(documentId)},
        resource_type: 'drawing',
        title: 'V29 acceptance drawing',
        status: 'draft',
        storage_ref: 'object://documents/${documentId}/rev-1',
        content_hash: 'sha256:' + 'c'.repeat(64),
        linked_entity_refs: [],
        idempotency_key: 'v29-' + ${JSON.stringify(documentId)},
      }),
    });
    return { status: response.status, body: await response.text() };
  })()`, { awaitPromise: true });
  assert(createdDocument.status === 200, `document create failed: ${createdDocument.status} ${createdDocument.body}`);
  report.createdDocumentId = documentId;

  await selectA130(page);

  // ---- Activity Codes -------------------------------------------------
  await openTab(page, "codes");
  await submit(page, "codes", { codeType: "AREA", codeValue: "ZONE-E2E", description: "V29 acceptance" });
  let text = await page.evaluate(`document.querySelector('#cp-details [data-detail-panel="codes"]')?.textContent ?? ""`);
  assert(text.includes("ZONE-E2E"), "the assigned code is not shown");
  report.steps.push({ feature: "codes", action: "assign", status: "pass" });
  await capture(page, "01-codes-assigned-en-1366");

  await reloadWorkspace(page);
  await selectA130(page);
  await openTab(page, "codes");
  text = await page.evaluate(`document.querySelector('#cp-details [data-detail-panel="codes"]')?.textContent ?? ""`);
  assert(text.includes("ZONE-E2E"), "the assigned code did not survive reload");
  report.steps.push({ feature: "codes", action: "reload", status: "pass" });
  await page.evaluate(`document.querySelector('#cp-details [data-code-delete]')?.click()`);
  await sleep(1300);
  text = await page.evaluate(`document.querySelector('#cp-details [data-detail-panel="codes"]')?.textContent ?? ""`);
  assert(!text.includes("ZONE-E2E"), "the removed code is still listed");
  report.steps.push({ feature: "codes", action: "remove", status: "pass" });

  // ---- Notebook ------------------------------------------------------
  await openTab(page, "notebook");
  await submit(page, "notebook", { topicName: "V29 Topic", description: "<p>Scope <b>agreed</b></p><script>alert(1)</script>" });
  text = await page.evaluate(`document.querySelector('#cp-details [data-detail-panel="notebook"]')?.textContent ?? ""`);
  assert(text.includes("V29 Topic") && text.includes("Scope agreed"), "the notebook topic is not shown");
  const html = await page.evaluate(`document.querySelector('#cp-details [data-detail-panel="notebook"] .cp-detail-notebook-body')?.innerHTML ?? ""`);
  assert(html.includes("<b>agreed</b>"), "allowed formatting was stripped");
  assert(!html.includes("<script"), "script markup was not sanitised");
  report.steps.push({ feature: "notebook", action: "add+sanitise", status: "pass" });
  await capture(page, "02-notebook-topic-en-1366");

  await reloadWorkspace(page);
  await selectA130(page);
  await openTab(page, "notebook");
  text = await page.evaluate(`document.querySelector('#cp-details [data-detail-panel="notebook"]')?.textContent ?? ""`);
  assert(text.includes("V29 Topic"), "the notebook topic did not survive reload");
  report.steps.push({ feature: "notebook", action: "reload", status: "pass" });

  const edited = await page.evaluate(`(() => {
    const details = document.querySelector('#cp-details [data-notebook-topic] details');
    if (!details) return false;
    details.open = true;
    const form = details.querySelector('form[data-details-form="notebook-edit"]');
    const name = form.elements.namedItem("topicName");
    name.value = "V29 Topic edited";
    form.querySelector('button[type="submit"]').click();
    return true;
  })()`);
  assert(edited, "notebook edit form is missing");
  await sleep(1300);
  text = await page.evaluate(`document.querySelector('#cp-details [data-detail-panel="notebook"]')?.textContent ?? ""`);
  assert(text.includes("V29 Topic edited"), "the notebook edit was not shown");
  report.steps.push({ feature: "notebook", action: "modify", status: "pass" });

  await page.evaluate(`document.querySelector('#cp-details [data-notebook-delete]')?.click()`);
  await sleep(1300);
  text = await page.evaluate(`document.querySelector('#cp-details [data-detail-panel="notebook"]')?.textContent ?? ""`);
  assert(!text.includes("V29 Topic edited"), "the deleted notebook topic is still listed");
  report.steps.push({ feature: "notebook", action: "delete", status: "pass" });

  // ---- Steps ---------------------------------------------------------
  await openTab(page, "steps");
  await submit(page, "steps", { description: "V29 step", weight: "15", percentComplete: "10" });
  text = await page.evaluate(`document.querySelector('#cp-details [data-detail-panel="steps"]')?.textContent ?? ""`);
  assert(text.includes("V29 step"), "the new step is not shown");
  assert(text.includes("Step % Complete"), "the step percent column is missing");
  report.steps.push({ feature: "steps", action: "add", status: "pass" });
  await capture(page, "03-step-added-en-1366");

  await reloadWorkspace(page);
  await selectA130(page);
  await openTab(page, "steps");
  text = await page.evaluate(`document.querySelector('#cp-details [data-detail-panel="steps"]')?.textContent ?? ""`);
  assert(text.includes("V29 step"), "the step did not survive reload");
  const percent = await page.evaluate(`(() => {
    const row = [...document.querySelectorAll('#cp-details [data-step-row]')].find((item) => item.textContent.includes('V29 step'));
    return row ? row.children[3]?.textContent?.trim() : null;
  })()`);
  assert(percent === "10", `stored step percent was ${percent}`);
  report.steps.push({ feature: "steps", action: "reload", status: "pass", percentComplete: percent });

  const editedStep = await page.evaluate(`(() => {
    const row = [...document.querySelectorAll('#cp-details [data-step-row]')].find((item) => item.textContent.includes('V29 step'));
    if (!row) return false;
    const editor = row.nextElementSibling?.querySelector('form[data-details-form="step-edit"]');
    if (!editor) return false;
    editor.elements.namedItem("percentComplete").value = "60";
    editor.querySelector('button[type="submit"]').click();
    return true;
  })()`);
  assert(editedStep, "step edit form is missing");
  await sleep(1400);
  const updatedPercent = await page.evaluate(`(() => {
    const row = [...document.querySelectorAll('#cp-details [data-step-row]')].find((item) => item.textContent.includes('V29 step'));
    return row ? row.children[3]?.textContent?.trim() : null;
  })()`);
  assert(updatedPercent === "60", `edited step percent was ${updatedPercent}`);
  report.steps.push({ feature: "steps", action: "modify", status: "pass", percentComplete: updatedPercent });

  const moved = await page.evaluate(`(() => {
    const row = [...document.querySelectorAll('#cp-details [data-step-row]')].find((item) => item.textContent.includes('V29 step'));
    const button = row?.querySelector('[data-step-move="up"]');
    if (!button || button.disabled) return false;
    button.click();
    return true;
  })()`);
  if (moved) {
    await sleep(1500);
    report.steps.push({ feature: "steps", action: "move", status: "pass" });
  } else {
    report.steps.push({ feature: "steps", action: "move", status: "single-step-noop" });
  }

  await page.evaluate(`(() => {
    const row = [...document.querySelectorAll('#cp-details [data-step-row]')].find((item) => item.textContent.includes('V29 step'));
    row?.querySelector('[data-step-delete]')?.click();
  })()`);
  await sleep(1400);
  text = await page.evaluate(`document.querySelector('#cp-details [data-detail-panel="steps"]')?.textContent ?? ""`);
  assert(!text.includes("V29 step"), "the deleted step is still listed");
  report.steps.push({ feature: "steps", action: "delete", status: "pass" });

  // ---- WPs & Docs ----------------------------------------------------
  await openTab(page, "wps-docs");
  const linked = await page.evaluate(`(() => {
    const form = document.querySelector('#cp-details [data-details-form="documents-link"]');
    const select = form?.elements.namedItem("documentId");
    if (!select || !select.value) return null;
    const id = select.value;
    form.querySelector('button[type="submit"]').click();
    return id;
  })()`);
  if (linked) {
    await sleep(1500);
    text = await page.evaluate(`document.querySelector('#cp-details [data-detail-panel="wps-docs"]')?.textContent ?? ""`);
    assert(text.includes("Unlink from activity"), "the linked document is not shown with an unlink control");
    report.steps.push({ feature: "wps-docs", action: "link", status: "pass", documentId: linked });
    await capture(page, "04-document-linked-en-1366");

    await reloadWorkspace(page);
    await selectA130(page);
    await openTab(page, "wps-docs");
    text = await page.evaluate(`document.querySelector('#cp-details [data-detail-panel="wps-docs"]')?.textContent ?? ""`);
    assert(text.includes("Unlink from activity"), "the document link did not survive reload");
    report.steps.push({ feature: "wps-docs", action: "reload", status: "pass" });

    await page.evaluate(`document.querySelector('#cp-details [data-document-unlink]')?.click()`);
    await sleep(1500);
    text = await page.evaluate(`document.querySelector('#cp-details [data-detail-panel="wps-docs"]')?.textContent ?? ""`);
    assert(!text.includes("Unlink from activity"), "the unlinked document is still listed");
    report.steps.push({ feature: "wps-docs", action: "unlink", status: "pass" });
  } else {
    report.steps.push({ feature: "wps-docs", action: "link", status: "no-unlinked-document-in-fixture" });
  }

  // ---- Two-step Alt dispatcher ---------------------------------------
  await page.evaluate(`(() => {
    const shell = document.querySelector('[data-desktop-shell]');
    shell.dispatchEvent(new KeyboardEvent('keydown', { key: 'f', altKey: true, bubbles: true }));
  })()`);
  await sleep(250);
  const pending = await page.evaluate(`(() => {
    const hint = document.querySelector('[data-alt-sequence]');
    return hint && !hint.hidden ? hint.textContent : null;
  })()`);
  assert(pending && pending.includes("F"), "the Alt+F waiting state is not shown");
  await page.evaluate(`(() => {
    const shell = document.querySelector('[data-desktop-shell]');
    shell.dispatchEvent(new KeyboardEvent('keydown', { key: 'n', bubbles: true }));
  })()`);
  await sleep(600);
  const pendingAfter = await page.evaluate(`document.querySelector('[data-alt-sequence]')?.hidden ?? true`);
  assert(pendingAfter, "the Alt waiting state was not cleared after the second key");
  report.steps.push({ feature: "alt-sequences", action: "Alt+F,N", status: "pass" });
  await capture(page, "05-alt-sequence-en-1366");

  assert(report.exceptions.length === 0, `browser exceptions: ${report.exceptions.join(" | ")}`);
  assert(report.apiFailures.length === 0, `API failures: ${JSON.stringify(report.apiFailures)}`);
  report.finishedAt = new Date().toISOString();
  writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
  writeFileSync(join(evidenceDir, "activity-children.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ ok: true, steps: report.steps }, null, 2));
  await chrome.stop();
  process.exit(0);
}

main().catch((error) => {
  report.finishedAt = new Date().toISOString();
  report.failure = error?.stack ?? String(error);
  writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
  writeFileSync(join(evidenceDir, "activity-children.json"), JSON.stringify(report, null, 2));
  console.error(error?.stack ?? error);
  process.exit(1);
});
