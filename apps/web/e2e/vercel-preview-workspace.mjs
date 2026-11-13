#!/usr/bin/env node
/**
 * Real-browser verification of a Vercel preview deployment.
 *
 * Opens the fixture-backed workspace directly at
 * `/app?project=preview-rps-01&view=live`, proves the Riverside Pump Station
 * Upgrade project renders, exercises workspace windows, reloads, and records
 * screenshots. It talks only to the deployed URL; nothing is simulated.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=https://<deployment>.vercel.app node e2e/vercel-preview-workspace.mjs
 */

import { spawn } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { fileURLToPath } from "node:url";

const webRoot = fileURLToPath(new URL("..", import.meta.url));
const baseUrl = (process.env.CUBI_PREVIEW_URL ?? "").replace(/\/+$/, "");
if (!baseUrl) {
  throw new Error("CUBI_PREVIEW_URL is required");
}
const project = process.env.CUBI_PREVIEW_PROJECT ?? "preview-rps-01";
const artifactsDir = process.env.CUBI_E2E_ARTIFACTS ?? join(webRoot, "e2e", "artifacts", "vercel-preview");
mkdirSync(artifactsDir, { recursive: true });

const CHECKS = [];
const ERRORS = [];
const SCREENSHOTS = [];

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

function check(name, detail = {}) {
  CHECKS.push({ name, ok: true, detail, at: new Date().toISOString() });
  process.stdout.write(`ok - ${name}\n`);
}

function findChrome() {
  for (const candidate of [
    process.env.CHROME_PATH,
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
  ].filter(Boolean)) {
    if (existsSync(candidate)) return candidate;
  }
  throw new Error("CHROME_NOT_FOUND");
}

class Cdp {
  constructor(socket) {
    this.socket = socket;
    this.nextId = 1;
    this.pending = new Map();
    this.listeners = new Map();
    socket.addEventListener("message", (event) => {
      const text = typeof event.data === "string" ? event.data : Buffer.from(event.data).toString("utf8");
      let message;
      try {
        message = JSON.parse(text);
      } catch {
        return;
      }
      if (message.id !== undefined) {
        const pending = this.pending.get(message.id);
        if (!pending) return;
        this.pending.delete(message.id);
        if (message.error) pending.reject(new Error(`${pending.method}: ${message.error.message}`));
        else pending.resolve(message.result);
        return;
      }
      for (const listener of this.listeners.get(message.method) ?? []) listener(message.params);
    });
  }

  static async connect(url) {
    const socket = new WebSocket(url);
    await new Promise((open, fail) => {
      socket.addEventListener("open", open, { once: true });
      socket.addEventListener("error", () => fail(new Error("DEVTOOLS_SOCKET_FAILED")), { once: true });
    });
    return new Cdp(socket);
  }

  on(method, listener) {
    const list = this.listeners.get(method) ?? [];
    list.push(listener);
    this.listeners.set(method, list);
  }

  send(method, params = {}, timeoutMs = 30000) {
    const id = this.nextId;
    this.nextId += 1;
    return new Promise((resolveSend, rejectSend) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        rejectSend(new Error(`${method}: timeout`));
      }, timeoutMs);
      this.pending.set(id, {
        method,
        resolve: (value) => {
          clearTimeout(timer);
          resolveSend(value);
        },
        reject: (error) => {
          clearTimeout(timer);
          rejectSend(error);
        },
      });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }
}

async function launchChrome() {
  const userDataDir = mkdtempSync(join(tmpdir(), "cubi-preview-e2e-"));
  const child = spawn(
    findChrome(),
    [
      "--headless=new",
      `--user-data-dir=${userDataDir}`,
      "--remote-debugging-port=0",
      "--no-first-run",
      "--no-default-browser-check",
      "--disable-gpu",
      "--disable-dev-shm-usage",
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--window-size=1280,720",
      "about:blank",
    ],
    { stdio: ["ignore", "ignore", "pipe"] },
  );
  let stderr = "";
  child.stderr.on("data", (chunk) => {
    stderr += chunk.toString();
  });
  const activePortFile = join(userDataDir, "DevToolsActivePort");
  const deadline = Date.now() + 20000;
  while (!existsSync(activePortFile)) {
    if (Date.now() > deadline) throw new Error(`CHROME_DID_NOT_START ${stderr.slice(-500)}`);
    await sleep(50);
  }
  let port = 0;
  while (!port) {
    try {
      const first = readFileSync(activePortFile, "utf8").split("\n")[0].trim();
      if (/^\d+$/.test(first)) port = Number(first);
    } catch {
      // still writing
    }
    if (!port) await sleep(50);
  }
  let target = null;
  for (let attempt = 0; attempt < 60 && !target; attempt += 1) {
    try {
      const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      target = targets.find((item) => item.type === "page");
    } catch {
      // not ready
    }
    if (!target) await sleep(100);
  }
  assert(target?.webSocketDebuggerUrl, "chrome page target");
  return { child, cdp: await Cdp.connect(target.webSocketDebuggerUrl) };
}

class Page {
  constructor(cdp) {
    this.cdp = cdp;
    this.events = { console: [], exceptions: [], failures: [] };
  }

  async initialize() {
    await this.cdp.send("Page.enable");
    await this.cdp.send("Runtime.enable");
    await this.cdp.send("Network.enable");
    this.cdp.on("Runtime.exceptionThrown", (params) => {
      this.events.exceptions.push(
        params.exceptionDetails?.exception?.description ?? params.exceptionDetails?.text ?? "exception",
      );
    });
    this.cdp.on("Runtime.consoleAPICalled", (params) => {
      if (params.type === "error") {
        this.events.console.push((params.args ?? []).map((arg) => arg.value ?? arg.description ?? "").join(" "));
      }
    });
    this.cdp.on("Network.responseReceived", (params) => {
      const url = params.response?.url ?? "";
      if (url.includes("/api/") && params.response.status >= 500) {
        this.events.failures.push({ status: params.response.status, url });
      }
    });
  }

  async evaluate(expression) {
    const response = await this.cdp.send("Runtime.evaluate", {
      expression,
      awaitPromise: true,
      returnByValue: true,
      userGesture: true,
    });
    if (response.exceptionDetails) {
      throw new Error(
        `EVALUATION_FAILED: ${response.exceptionDetails.exception?.description ?? response.exceptionDetails.text}`,
      );
    }
    return response.result?.value;
  }

  async waitFor(expression, label, timeoutMs = 45000) {
    const deadline = Date.now() + timeoutMs;
    let last;
    while (Date.now() < deadline) {
      try {
        const value = await this.evaluate(expression);
        if (value) return value;
      } catch (error) {
        last = error;
      }
      await sleep(150);
    }
    throw new Error(`WAIT_TIMEOUT: ${label}${last ? ` (${last.message})` : ""}`);
  }

  async goto(url) {
    await this.cdp.send("Page.navigate", { url });
    await this.waitFor(`document.readyState === "complete"`, `load ${url}`);
  }

  async viewport(width, height) {
    await this.cdp.send("Emulation.setDeviceMetricsOverride", {
      width,
      height,
      deviceScaleFactor: 1,
      mobile: false,
    });
  }

  async screenshot(name) {
    const result = await this.cdp.send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
    const path = join(artifactsDir, name);
    writeFileSync(path, Buffer.from(result.data, "base64"));
    SCREENSHOTS.push(path);
    return path;
  }
}

async function main() {
  const chrome = await launchChrome();
  let failure = null;
  try {
    const page = new Page(chrome.cdp);
    await page.initialize();
    await page.viewport(1280, 720);

    const appUrl = `${baseUrl}/app?project=${encodeURIComponent(project)}&view=live`;
    await page.goto(appUrl);

    const workspace = await page.waitFor(
      `(() => {
        const node = document.querySelector(".cp-workspace[data-project]");
        return node ? { project: node.dataset.project, menu: node.dataset.activeMenu, url: location.href } : null;
      })()`,
      "workspace renders without a sign-in step",
    );
    assert(workspace.project === project, `workspace project is ${project}`);
    check("the preview URL opens the workspace directly", { url: workspace.url, menu: workspace.menu });

    const session = await page.evaluate(
      `fetch("/api/session", { credentials: "same-origin" }).then(async (r) => ({ status: r.status, body: await r.json() }))`,
    );
    assert(session.status === 200, "session is available");
    assert(session.body.user_id.startsWith("preview-"), "a demo identity is active");
    assert(!("session_id" in session.body), "the session id is never echoed");
    check("a preview-only demo session backs the workspace", {
      user_id: session.body.user_id,
      roles: session.body.roles,
    });

    const projects = await page.evaluate(
      `fetch("/api/projects", { credentials: "same-origin" }).then((r) => r.json())`,
    );
    const ids = projects.projects.map((item) => item.project_id);
    assert(ids.includes("preview-rps-01"), "the fixture project is listed");
    const riverside = projects.projects.find((item) => item.project_id === "preview-rps-01");
    assert(riverside.name === "Riverside Pump Station Upgrade", "fixture project name");
    check("the authorized project list carries the Riverside fixture", { projects: ids });

    const activities = await page.waitFor(
      `document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]").length`,
      "activity grid rows",
    );
    assert(activities > 0, "the activity grid has rows");
    const wbsNodes = await page.evaluate(
      `document.querySelectorAll("[data-wbs-row], [data-wbs-id]").length`,
    );
    check("the persisted schedule renders in the workspace", {
      activity_rows: activities,
      wbs_markers: wbsNodes,
    });

    const projectName = await page.evaluate(
      `document.body.innerText.includes("Riverside Pump Station Upgrade")`,
    );
    assert(projectName, "the project name shows in the workspace");
    check("the workspace displays the Riverside project name", {});
    await page.screenshot("vercel-preview-workspace-1280x720.png");

    // Each window must show loaded data, not just an active tab: wait for the
    // register rows (or tracking layout) the deployed API feeds.
    const windowContent = {
      resources: {
        loaded: `document.querySelectorAll("[data-resources-page] table tbody tr").length`,
        failure: `document.querySelector("[data-resources-page] [role=\\"alert\\"]")?.innerText ?? ""`,
      },
      progress: {
        loaded: `document.querySelectorAll("[data-progress-page] [data-progress-row]").length`,
        failure: `document.querySelector("[data-progress-page] [role=\\"alert\\"]")?.innerText ?? ""`,
      },
      tracking: {
        loaded: `document.querySelectorAll("[data-tracking-page] .cp-tracking-layout").length`,
        failure: `document.querySelector("[data-tracking-error]")?.dataset.trackingError ?? ""`,
      },
    };
    const menuTargets = await page.evaluate(
      `Array.from(document.querySelectorAll("[data-menu]")).map((node) => node.dataset.menu)`,
    );
    for (const menu of ["resources", "progress", "tracking"]) {
      if (!menuTargets.includes(menu)) {
        ERRORS.push(`menu ${menu} is not rendered`);
        continue;
      }
      await page.evaluate(
        `document.querySelector('[data-menu="${menu}"]').click()`,
      );
      const active = await page.waitFor(
        `document.querySelector('.cp-workspace[data-project]')?.dataset.activeMenu`,
        `menu ${menu}`,
        15000,
      );
      assert(active === menu, `menu ${menu} becomes active`);
      const content = windowContent[menu];
      let rows = 0;
      try {
        rows = await page.waitFor(content.loaded, `${menu} data loads`, 30000);
      } catch (error) {
        const failure = await page.evaluate(content.failure);
        throw new Error(`${menu} window never loaded its data${failure ? ` (${failure})` : ""}: ${error.message}`);
      }
      assert(rows > 0, `${menu} window has data rows`);
      await page.screenshot(`vercel-preview-${menu}-window.png`);
      check(`workspace window ${menu} opens with data`, { active, rows });
    }

    await page.evaluate(`document.querySelector('[data-menu="schedule"]')?.click()`);
    await page.waitFor(
      `document.querySelector('.cp-workspace[data-project]')?.dataset.activeMenu === "schedule"`,
      "return to the schedule window",
      15000,
    );

    await page.cdp.send("Page.reload", { ignoreCache: true });
    const afterReload = await page.waitFor(
      `(() => {
        const node = document.querySelector(".cp-workspace[data-project]");
        return node ? { project: node.dataset.project, rows: document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]").length } : null;
      })()`,
      "workspace after refresh",
    );
    assert(afterReload.project === project && afterReload.rows > 0, "refresh keeps the project and rows");
    check("refresh keeps the fixture workspace", afterReload);

    await page.viewport(1366, 768);
    await page.screenshot("vercel-preview-workspace-1366x768.png");
    check("workspace renders at 1366x768", {});

    const rtl = await page.evaluate(
      `(() => {
        const select = document.querySelector(".cp-workspace-language");
        if (!select) return null;
        select.value = "fa";
        select.dispatchEvent(new Event("change", { bubbles: true }));
        return true;
      })()`,
    );
    if (rtl) {
      const direction = await page.waitFor(
        `document.querySelector('.cp-workspace[data-project]')?.getAttribute("dir")`,
        "Persian direction",
        15000,
      );
      assert(direction === "rtl", "Persian switches the workspace to RTL");
      await page.screenshot("vercel-preview-workspace-fa-rtl.png");
      check("Persian locale renders right-to-left", { direction });
    }

    assert(page.events.exceptions.length === 0, `browser exceptions: ${page.events.exceptions.join(" | ")}`);
    assert(page.events.failures.length === 0, `API 5xx responses: ${JSON.stringify(page.events.failures)}`);
    assert(ERRORS.length === 0, `workspace defects: ${ERRORS.join(" | ")}`);
    check("no browser exceptions and no API 5xx", {
      console_errors: page.events.console.length,
    });
    if (page.events.console.length) {
      ERRORS.push(...page.events.console);
    }
  } catch (error) {
    failure = error;
    ERRORS.push(error.message);
  } finally {
    chrome.child.kill("SIGTERM");
  }

  const report = {
    contract: "cubi-vercel-preview-workspace.v1",
    base_url: baseUrl,
    project,
    checks: CHECKS,
    screenshots: SCREENSHOTS,
    errors: ERRORS,
    console: [],
    finished_at: new Date().toISOString(),
  };
  writeFileSync(join(artifactsDir, "vercel-preview-workspace.json"), `${JSON.stringify(report, null, 2)}\n`);
  process.stdout.write(`\n${CHECKS.length} checks passed, ${ERRORS.length} errors\n`);
  if (failure) {
    process.stderr.write(`\nFAILED: ${failure.stack ?? failure.message}\n`);
    process.exit(1);
  }
}

main().catch((error) => {
  process.stderr.write(`${error.stack ?? error.message}\n`);
  process.exit(1);
});
