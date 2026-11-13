#!/usr/bin/env node
/**
 * Browser E2E for the Version 26 single authenticated workspace shell (WS-001).
 *
 * The preview app is a server-rendered shell plus one client workspace. This
 * suite drives the real local full-stack preview and asserts that the login,
 * direct-link, refresh and logout journeys leave exactly one authenticated
 * shell and never expose the workspace without a session.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4198 \
 *   CUBI_TESTED_CODE_SHA=<code commit> \
 *   CUBI_CHROME_NO_SANDBOX=1 node e2e/workspace-shell-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4198";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-13";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "workspace-shell-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `workspace-shell-v26-${evidenceDate}`);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const scenarios = [];
const screenshots = [];

const assert = (condition, message) => {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
};

async function capture(page, name) {
  const file = await page.screenshot(`workspace-shell-v26/${name}.png`);
  copyFileSync(file, join(evidenceDir, `${name}.png`));
  screenshots.push(`${name}.png`);
}

async function scenario(id, name, body) {
  const started = Date.now();
  process.stdout.write(`[${id}] ${name}\n`);
  try {
    const detail = (await body()) ?? {};
    const record = { id, name, status: "pass", durationMs: Date.now() - started, ...detail };
    scenarios.push(record);
    process.stdout.write(`  PASS ${id}. ${name}\n`);
    return record;
  } catch (error) {
    scenarios.push({ id, name, status: "fail", durationMs: Date.now() - started, error: String(error) });
    process.stdout.write(`  FAIL ${id}. ${name}\n`);
    throw error;
  }
}

async function state(page) {
  return page.evaluate(`(() => ({
    href: location.href,
    path: location.pathname,
    search: location.search,
    title: document.title,
    shells: document.querySelectorAll("[data-desktop-shell]").length,
    hosts: document.querySelectorAll("[data-desktop-host]").length,
    projects: document.querySelectorAll("[data-project-id]").length,
    rows: document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]").length,
    loginCards: document.querySelectorAll(".persona").length,
    sessionRole: document.querySelector("[data-session-role]")?.textContent?.trim() ?? null,
  }))()`);
}

async function logout(page) {
  await page.evaluate(
    `fetch("/preview/logout", { method: "POST", redirect: "manual" }).then((response) => response.status)`,
    { awaitPromise: true },
  );
  await sleep(250);
}

async function login(page, role) {
  const clicked = await page.evaluate(`(() => {
    const button = document.querySelector('button[name="role"][value="${role}"]');
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `role button ${role} is missing`);
  await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection after login");
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
    contract: "cubi-workspace-shell-v26.v1",
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

  try {
    await page.navigate(`${baseUrl}/preview/health`, null, "preview origin");

    await scenario("01", "an unauthenticated deep link redirects to login and paints no shell", async () => {
      await logout(page);
      await page.navigate(`${baseUrl}/app?view=wbs`, null, "deep link without session", `${baseUrl}/preview/login`);
      const after = await state(page);
      assert(after.path === "/preview/login", `deep link landed on ${after.path}`);
      assert(after.search.includes("next="), `login URL lost next: ${after.search}`);
      assert(after.search.includes("%2Fapp%3Fview%3Dlive") || after.search.includes("/app?view=live"), `next is ${after.search}`);
      assert(after.shells === 0 && after.hosts === 0, `unauthenticated shell count ${after.shells}/${after.hosts}`);
      assert(after.loginCards >= 3, `login painted ${after.loginCards} persona cards`);
      await capture(page, "01-deep-link-login");
      return { path: after.path, search: after.search, personas: after.loginCards };
    });

    await scenario("02", "the login POST returns to the normalized view and mounts one shell", async () => {
      await login(page, "planner");
      const selected = await state(page);
      assert(selected.path === "/app", `login landed on ${selected.path}`);
      assert(selected.search.includes("view=live"), `login did not normalize the view: ${selected.search}`);
      assert(selected.projects > 0, `login painted no project card: ${selected.projects}`);
      assert(selected.loginCards === 0, `login page is still visible: ${selected.loginCards}`);
      await page.click('[data-project-id="preview-rps-01"]');
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "workspace rows");
      await sleep(400);
      const workspace = await state(page);
      assert(workspace.shells === 1 && workspace.hosts === 1, `workspace shell ${workspace.shells}/${workspace.hosts}`);
      assert(workspace.rows > 0, "workspace painted no activity rows");
      await capture(page, "02-login-one-shell");
      return { path: workspace.path, search: workspace.search, shells: workspace.shells, rows: workspace.rows };
    });

    await scenario("03", "an authenticated direct link reuses the session and mounts one shell", async () => {
      await page.navigate(`${baseUrl}/app?view=live`, "#cp-activity-grid tbody tr[data-activity-id]", "direct link with session", `${baseUrl}/app`);
      await sleep(500);
      const direct = await state(page);
      assert(direct.path === "/app", `direct link landed on ${direct.path}`);
      assert(direct.search.includes("view=live"), `direct link lost view=live: ${direct.search}`);
      assert(direct.shells === 1 && direct.hosts === 1, `direct shell ${direct.shells}/${direct.hosts}`);
      assert(direct.rows > 0, "direct link painted no rows");
      await capture(page, "03-authenticated-direct-link");
      return { path: direct.path, search: direct.search, shells: direct.shells, rows: direct.rows };
    });

    await scenario("04", "a full reload keeps the session, project and single shell", async () => {
      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "workspace reload");
      await sleep(700);
      const reloaded = await state(page);
      assert(reloaded.path === "/app", `reload landed on ${reloaded.path}`);
      assert(reloaded.shells === 1 && reloaded.hosts === 1, `reload shell ${reloaded.shells}/${reloaded.hosts}`);
      assert(reloaded.rows > 0, "reload painted no rows");
      assert(reloaded.loginCards === 0, "reload showed the login page");
      await capture(page, "04-reload-one-shell");
      return { path: reloaded.path, shells: reloaded.shells, rows: reloaded.rows };
    });

    await scenario("05", "a bare /app link normalizes to the live view and keeps one shell", async () => {
      await page.navigate(`${baseUrl}/app`, "#cp-activity-grid tbody tr[data-activity-id]", "bare app link", `${baseUrl}/app`);
      await sleep(500);
      const bare = await state(page);
      assert(bare.path === "/app", `bare link landed on ${bare.path}`);
      assert(bare.search.includes("view=live"), `bare link did not normalize view: ${bare.search}`);
      assert(bare.shells === 1 && bare.hosts === 1, `bare shell ${bare.shells}/${bare.hosts}`);
      await capture(page, "05-bare-app-link");
      return { path: bare.path, search: bare.search, shells: bare.shells };
    });

    await scenario("06", "a viewer session still gets exactly one shell", async () => {
      await logout(page);
      await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, ".persona", "viewer login");
      await login(page, "viewer");
      const viewer = await state(page);
      assert(viewer.path === "/app", `viewer landed on ${viewer.path}`);
      assert(viewer.projects > 0, `viewer painted no project card: ${viewer.projects}`);
      await page.click('[data-project-id="preview-rps-01"]');
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "viewer workspace rows");
      await sleep(400);
      const viewerWorkspace = await state(page);
      assert(viewerWorkspace.shells === 1 && viewerWorkspace.hosts === 1, `viewer workspace shell ${viewerWorkspace.shells}/${viewerWorkspace.hosts}`);
      assert(viewerWorkspace.rows > 0, "viewer workspace painted no rows");
      await capture(page, "06-viewer-one-shell");
      return { path: viewerWorkspace.path, shells: viewerWorkspace.shells, rows: viewerWorkspace.rows };
    });

    await scenario("07", "logout returns to login and a later deep link paints no shell", async () => {
      await logout(page);
      await page.navigate(`${baseUrl}/app?view=live`, null, "deep link after logout", `${baseUrl}/preview/login`);
      const after = await state(page);
      assert(after.path === "/preview/login", `post-logout deep link landed on ${after.path}`);
      assert(after.shells === 0 && after.hosts === 0, `post-logout shell ${after.shells}/${after.hosts}`);
      assert(after.loginCards >= 3, `post-logout login cards ${after.loginCards}`);
      await capture(page, "07-logout-closed-shell");
      return { path: after.path, shells: after.shells, personas: after.loginCards };
    });

    report.passed = scenarios.filter((item) => item.status === "pass").length;
    report.failed = scenarios.filter((item) => item.status === "fail").length;
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(evidenceDir, "workspace-shell-v26.json"), `${JSON.stringify(report, null, 2)}\n`);
    process.stdout.write(`\nScenarios: ${report.passed} passed, ${report.failed} failed\n`);
    process.stdout.write(`Evidence: ${join(evidenceDir, "workspace-shell-v26.json")}\n`);
    if (report.failed > 0) process.exitCode = 1;
  } catch (error) {
    report.passed = scenarios.filter((item) => item.status === "pass").length;
    report.failed = scenarios.filter((item) => item.status === "fail").length;
    report.finishedAt = new Date().toISOString();
    writeFileSync(join(evidenceDir, "workspace-shell-v26.json"), `${JSON.stringify(report, null, 2)}\n`);
    process.stdout.write(`\nFAILED: ${error}\n`);
    process.exitCode = 1;
  } finally {
    try {
      chrome.child.kill("SIGKILL");
    } catch {
      // The browser may already have exited.
    }
  }
}

main().catch((error) => {
  process.stderr.write(`${error?.stack ?? error}\n`);
  process.exitCode = 1;
});
