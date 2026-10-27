#!/usr/bin/env node
/**
 * Real browser E2E for the CUBI local full-stack preview.
 *
 * It drives headless Chrome through the DevTools protocol against the real
 * WSGI runtime, real SQLite repositories and the Shared Domain/Calculation
 * Core. It does not mock API responses and it never touches production.
 *
 * Usage:
 *   npm run test:e2e:preview              # builds and starts its own runtime
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4174 npm run test:e2e:preview
 *
 * The current Chrome path can be overridden with CHROME_PATH. A CRISP_HTML
 * style fixture is not used: every assertion runs against the served app.
 */

import { spawn, spawnSync, execFileSync } from "node:child_process";
import { createServer } from "node:net";
import { createWriteStream, existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { delimiter, join, resolve } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { fileURLToPath } from "node:url";

const webRoot = fileURLToPath(new URL("..", import.meta.url));
const repoRoot = resolve(webRoot, "..", "..");
const artifactsDir = join(webRoot, "e2e", "artifacts");
mkdirSync(artifactsDir, { recursive: true });

const PROJECT_ID = "preview-rps-01";
const PROJECT_REVISION = 7;
const TENANT_ID = "cubi-preview-tenant";
const SCREENSHOTS = [];
const CHECKS = [];
const EXCEPTIONS = [];
const CONSOLE_ERRORS = [];
const API_FAILURES = [];
const EVIDENCE = {
  contract: "cubi-preview-browser-e2e.v1",
  started_at: new Date().toISOString(),
  base_url: null,
  managed_runtime: false,
  git_head: null,
  checks: CHECKS,
  screenshots: SCREENSHOTS,
  exceptions: EXCEPTIONS,
  console_errors: CONSOLE_ERRORS,
  api_failures: API_FAILURES,
  persistence: {},
  calculation: {},
  permissions: {},
};

function log(message) {
  process.stdout.write(`${message}\n`);
}

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

function record(name, details = {}) {
  CHECKS.push({ name, at: new Date().toISOString(), ...details });
  log(`  ok ${name}`);
}

function relativeArtifact(file) {
  return file.replace(`${artifactsDir}\\`, "").replace(`${artifactsDir}/`, "");
}

function gitHead() {
  try {
    return execFileSync("git", ["rev-parse", "HEAD"], { cwd: repoRoot })
      .toString()
      .trim();
  } catch {
    return null;
  }
}

function findChrome() {
  const candidates = [
    process.env.CHROME_PATH,
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
  ].filter(Boolean);
  for (const candidate of candidates) {
    if (existsSync(candidate)) return candidate;
  }
  throw new Error(
    "CHROME_NOT_FOUND: set CHROME_PATH to a Chrome/Edge executable",
  );
}

async function freePort() {
  return new Promise((resolvePort, reject) => {
    const server = createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const port = server.address().port;
      server.close(() => resolvePort(port));
    });
  });
}

async function fetchJson(url, init) {
  const response = await fetch(url, init);
  let body = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  return { status: response.status, headers: response.headers, body };
}

async function readLayoutFromPage(page) {
  return page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${PROJECT_ID}/p6/layouts/project/activity", {
      headers: {
        "X-Tenant-Id": ${JSON.stringify(TENANT_ID)},
        "X-Project-Id": ${JSON.stringify(PROJECT_ID)},
        "X-Project-Revision": ${JSON.stringify(String(PROJECT_REVISION))},
      },
    });
    const body = await response.json().catch(() => null);
    return { status: response.status, body };
  })()`, { awaitPromise: true });
}

async function readLayoutHistoryFromPage(page) {
  return page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${PROJECT_ID}/p6/layouts/project/activity/revisions", {
      headers: {
        "X-Tenant-Id": ${JSON.stringify(TENANT_ID)},
        "X-Project-Id": ${JSON.stringify(PROJECT_ID)},
        "X-Project-Revision": ${JSON.stringify(String(PROJECT_REVISION))},
      },
    });
    const body = await response.json().catch(() => null);
    return { status: response.status, body };
  })()`, { awaitPromise: true });
}

async function writeLayoutFromPage(page, revision, columns, metadata = {}) {
  return page.evaluate(`(async () => {
    const response = await fetch("/api/projects/${PROJECT_ID}/p6/layouts/project/activity", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Tenant-Id": ${JSON.stringify(TENANT_ID)},
        "X-Project-Id": ${JSON.stringify(PROJECT_ID)},
        "X-Project-Revision": ${JSON.stringify(String(PROJECT_REVISION))},
      },
      body: JSON.stringify({
        revision: ${Number(revision)},
        columns: ${JSON.stringify(columns)},
        metadata: ${JSON.stringify(metadata)},
      }),
    });
    const body = await response.json().catch(() => null);
    return { status: response.status, body };
  })()`, { awaitPromise: true });
}

async function waitForHttp(url, timeoutMs = 60000) {  const deadline = Date.now() + timeoutMs;
  let lastError;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) return await response.json();
      lastError = new Error(`HTTP ${response.status}`);
    } catch (error) {
      lastError = error;
    }
    await sleep(250);
  }
  throw new Error(`PREVIEW_DID_NOT_START: ${lastError?.message ?? "timeout"}`);
}

function pythonCommand() {
  const configured = process.env.CUBI_PYTHON?.trim();
  if (configured) return { executable: configured, prefix: [] };
  if (process.platform === "win32") return { executable: "py", prefix: ["-3"] };
  return { executable: "python3", prefix: [] };
}

async function startManagedRuntime() {
  const runtimeDir = mkdtempSync(join(tmpdir(), "cubi-preview-e2e-"));
  const database = join(runtimeDir, "preview-e2e.sqlite3");
  const port = await freePort();
  const baseUrl = `http://127.0.0.1:${port}`;
  const logFile = join(artifactsDir, "preview-server.log");
  const logStream = createWriteStream(logFile, { flags: "w" });
  const command = pythonCommand();
  const pythonPath = [join(repoRoot, "src"), process.env.PYTHONPATH]
    .filter((value) => value && value.length > 0)
    .join(delimiter);
  const child = spawn(
    command.executable,
    [
      ...command.prefix,
      "-m",
      "construction_pm.preview",
      "--web-root",
      webRoot,
      "--database",
      database,
      "--port",
      String(port),
      "--reset",
    ],
    {
      cwd: repoRoot,
      env: {
        ...process.env,
        PYTHONPATH: pythonPath,
        PYTHONIOENCODING: "utf-8",
      },
      stdio: ["ignore", "pipe", "pipe"],
    },
  );
  child.stdout.pipe(logStream);
  child.stderr.pipe(logStream);
  let exited = null;
  child.on("exit", (code, signal) => {
    exited = { code, signal };
  });
  child.on("error", (error) => {
    exited = { error: String(error) };
  });
  const health = await waitForHttp(`${baseUrl}/preview/health`).catch((error) => {
    if (exited) {
      throw new Error(
        `PREVIEW_RUNTIME_EXITED: ${JSON.stringify(exited)} (see ${logFile})`,
      );
    }
    throw error;
  });
  return {
    baseUrl,
    health,
    logFile,
    runtimeDir,
    stop: () => stopProcessTree(child),
  };
}

function stopProcessTree(child) {
  if (!child || child.killed) return;
  if (process.platform === "win32" && child.pid) {
    spawnSync("taskkill", ["/pid", String(child.pid), "/T", "/F"], {
      stdio: "ignore",
    });
    return;
  }
  child.kill();
}

class Cdp {
  constructor(socket) {
    this.socket = socket;
    this.nextId = 1;
    this.pending = new Map();
    this.listeners = new Map();
    this.closed = false;
    socket.addEventListener("message", (event) => {
      const text =
        typeof event.data === "string"
          ? event.data
          : Buffer.from(event.data).toString("utf8");
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
        if (message.error) {
          pending.reject(new Error(`${pending.method}: ${message.error.message}`));
        } else {
          pending.resolve(message.result);
        }
        return;
      }
      for (const listener of this.listeners.get(message.method) ?? []) {
        listener(message.params);
      }
    });
    socket.addEventListener("close", () => {
      this.closed = true;
      for (const pending of this.pending.values()) {
        pending.reject(new Error(`${pending.method}: DevTools socket closed`));
      }
      this.pending.clear();
    });
  }

  static async connect(url) {
    const socket = new WebSocket(url);
    await new Promise((resolveOpen, rejectOpen) => {
      socket.addEventListener("open", resolveOpen, { once: true });
      socket.addEventListener(
        "error",
        () => rejectOpen(new Error("DEVTOOLS_SOCKET_FAILED")),
        { once: true },
      );
    });
    return new Cdp(socket);
  }

  on(method, listener) {
    const listeners = this.listeners.get(method) ?? [];
    listeners.push(listener);
    this.listeners.set(method, listeners);
  }

  send(method, params = {}, timeoutMs = 30000) {
    if (this.closed) return Promise.reject(new Error("DEVTOOLS_CLOSED"));
    const id = this.nextId;
    this.nextId += 1;
    return new Promise((resolveSend, rejectSend) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        rejectSend(new Error(`${method}: timeout after ${timeoutMs}ms`));
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

  close() {
    try {
      this.socket.close();
    } catch {
      // already closed
    }
  }
}

class Page {
  constructor(cdp) {
    this.cdp = cdp;
  }

  async initialize() {
    await this.cdp.send("Page.enable");
    await this.cdp.send("Runtime.enable");
    await this.cdp.send("Network.enable");
    await this.cdp.send("Log.enable");
    this.cdp.on("Runtime.exceptionThrown", (params) => {
      const text =
        params.exceptionDetails?.exception?.description ??
        params.exceptionDetails?.text ??
        "unknown exception";
      EXCEPTIONS.push({ at: new Date().toISOString(), text });
    });
    this.cdp.on("Runtime.consoleAPICalled", (params) => {
      if (params.type !== "error") return;
      CONSOLE_ERRORS.push({
        at: new Date().toISOString(),
        text: (params.args ?? [])
          .map((arg) => arg.value ?? arg.description ?? arg.type)
          .join(" "),
      });
    });
    this.cdp.on("Network.responseReceived", (params) => {
      const url = params.response?.url ?? "";
      if (url.includes("/api/") && params.response.status >= 500) {
        API_FAILURES.push({
          at: new Date().toISOString(),
          status: params.response.status,
          url,
        });
      }
    });
  }

  async evaluate(expression, options = {}) {
    const response = await this.cdp.send("Runtime.evaluate", {
      expression,
      awaitPromise: options.awaitPromise ?? false,
      returnByValue: true,
      userGesture: true,
    });
    if (response.exceptionDetails) {
      const text =
        response.exceptionDetails.exception?.description ??
        response.exceptionDetails.text ??
        "evaluation failed";
      throw new Error(`PAGE_EVALUATION_FAILED: ${text}\n${expression}`);
    }
    return response.result?.value;
  }

  async waitFor(expression, label, timeoutMs = 20000) {
    const deadline = Date.now() + timeoutMs;
    let lastError;
    while (Date.now() < deadline) {
      try {
        const value = await this.evaluate(expression);
        if (value) return value;
      } catch (error) {
        lastError = error;
      }
      await sleep(100);
    }
    throw new Error(
      `WAIT_TIMEOUT: ${label}${lastError ? ` (last error: ${lastError.message})` : ""}`,
    );
  }

  waitForSelector(selector, label = selector, timeoutMs = 20000) {
    return this.waitFor(
      `Boolean(document.querySelector(${JSON.stringify(selector)}))`,
      label,
      timeoutMs,
    );
  }

  async navigate(url, selector, label = url, expectedUrl = url) {
    await this.cdp.send("Page.navigate", { url });
    await this.waitFor(
      `document.readyState === "complete" && location.href.startsWith(${JSON.stringify(expectedUrl.split("?")[0])})`,
      `${label} document`,
    );
    if (selector) await this.waitForSelector(selector, label);
  }

  async click(selector) {
    const clicked = await this.evaluate(`(() => {
      const element = document.querySelector(${JSON.stringify(selector)});
      if (!element) return false;
      element.click();
      return true;
    })()`);
    assert(clicked, `click target not found: ${selector}`);
  }

  async setInput(selector, value) {
    const changed = await this.evaluate(`(() => {
      const element = document.querySelector(${JSON.stringify(selector)});
      if (!element) return false;
      element.focus();
      element.value = ${JSON.stringify(value)};
      element.dispatchEvent(new Event("input", { bubbles: true }));
      element.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    })()`);
    assert(changed, `input target not found: ${selector}`);
  }

  async setSelect(selector, value) {
    const changed = await this.evaluate(`(() => {
      const element = document.querySelector(${JSON.stringify(selector)});
      if (!element) return false;
      element.value = ${JSON.stringify(value)};
      element.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    })()`);
    assert(changed, `select target not found: ${selector}`);
  }

  async text(selector) {
    return this.evaluate(`(() => {
      const element = document.querySelector(${JSON.stringify(selector)});
      return element ? element.textContent.trim() : null;
    })()`);
  }

  async count(selector) {
    return this.evaluate(
      `document.querySelectorAll(${JSON.stringify(selector)}).length`,
    );
  }

  async reload(selector, label = "reload") {
    await this.cdp.send("Page.reload", { ignoreCache: true });
    await this.waitFor(
      `document.readyState === "complete"`,
      `${label} document`,
    );
    if (selector) await this.waitForSelector(selector, label);
  }

  async screenshot(name) {
    const result = await this.cdp.send("Page.captureScreenshot", {
      format: "png",
      fromSurface: true,
    });
    const file = join(artifactsDir, name);
    writeFileSync(file, Buffer.from(result.data, "base64"));
    SCREENSHOTS.push({ name, file: relativeArtifact(file) });
    log(`  captured ${relativeArtifact(file)}`);
    return file;
  }

  async scrollTo(selector) {
    await this.evaluate(`(() => {
      const element = document.querySelector(${JSON.stringify(selector)});
      if (element) element.scrollIntoView({ block: "start", inline: "nearest" });
      return true;
    })()`);
    await sleep(150);
  }
}

async function launchChrome() {
  const chromePath = findChrome();
  const userDataDir = mkdtempSync(join(tmpdir(), "cubi-preview-chrome-"));
  const child = spawn(
    chromePath,
    [
      "--headless=new",
      `--user-data-dir=${userDataDir}`,
      "--remote-debugging-port=0",
      "--no-first-run",
      "--no-default-browser-check",
      "--disable-background-networking",
      "--disable-component-update",
      "--disable-sync",
      "--disable-extensions",
      "--disable-gpu",
      "--disable-features=Translate,MediaRouter",
      "--window-size=1440,900",
      "--hide-scrollbars",
      "about:blank",
    ],
    { stdio: ["ignore", "pipe", "pipe"] },
  );
  let stderr = "";
  child.stderr.on("data", (chunk) => {
    stderr += chunk.toString();
  });
  let exited = null;
  child.on("exit", (code, signal) => {
    exited = { code, signal };
  });

  const activePortFile = join(userDataDir, "DevToolsActivePort");
  const deadline = Date.now() + 20000;
  while (!existsSync(activePortFile)) {
    if (exited) {
      throw new Error(`CHROME_EXITED: ${JSON.stringify(exited)} ${stderr.slice(-800)}`);
    }
    if (Date.now() > deadline) {
      throw new Error(`CHROME_DID_NOT_START ${stderr.slice(-800)}`);
    }
    await sleep(50);
  }
  const [debugPort] = (await (await import("node:fs/promises")).readFile(activePortFile, "utf8")).split("\n");
  let target = null;
  for (let attempt = 0; attempt < 50 && !target; attempt += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${debugPort}/json/list`);
      const targets = await response.json();
      target = targets.find((item) => item.type === "page");
    } catch {
      // Chrome HTTP endpoint not ready yet
    }
    if (!target) await sleep(100);
  }
  if (!target) {
    const response = await fetch(`http://127.0.0.1:${debugPort}/json/new?about:blank`, {
      method: "PUT",
    });
    target = await response.json();
  }
  assert(target?.webSocketDebuggerUrl, "Chrome page target websocket missing");
  return {
    child,
    userDataDir,
    cdp: await Cdp.connect(target.webSocketDebuggerUrl),
    stop: () => stopProcessTree(child),
  };
}

async function main() {
  EVIDENCE.git_head = gitHead();
  const buildEntry = join(webRoot, "dist", "web", "src", "landing-entry.js");
  if (!existsSync(buildEntry)) {
    throw new Error(
      `WEB_BUILD_MISSING: ${buildEntry}; run "npm run build" first (npm run test:e2e:preview does this).`,
    );
  }

  let managed = null;
  let baseUrl = process.env.CUBI_PREVIEW_URL?.replace(/\/$/, "") ?? null;
  let health;
  if (baseUrl) {
    health = await waitForHttp(`${baseUrl}/preview/health`, 15000);
  } else {
    log("Starting an isolated preview runtime (temporary SQLite, random port)");
    managed = await startManagedRuntime();
    baseUrl = managed.baseUrl;
    health = managed.health;
    EVIDENCE.managed_runtime = true;
  }
  EVIDENCE.base_url = baseUrl;
  log(`Preview runtime: ${baseUrl}`);

  assert(health.status === "ok", "preview health status");
  assert(health.production === false, "preview must not present itself as production");
  assert(health.demo_data === true, "preview must declare demo data");
  assert(health.project_count >= 2, "two fixture projects expected");
  assert(health.activity_count >= 20, "twenty fixture activities expected");
  record("runtime health identifies local demo composition", {
    project_count: health.project_count,
    activity_count: health.activity_count,
    seed_version: health.seed_version,
  });

  const unauthenticatedApp = await fetch(`${baseUrl}/app`, { redirect: "manual" });
  assert(unauthenticatedApp.status === 302, "unauthenticated /app must redirect");
  assert(
    unauthenticatedApp.headers.get("location") === "/preview/login?next=%2Fapp",
    "unauthenticated /app redirect target",
  );
  const unauthenticatedSession = await fetchJson(`${baseUrl}/api/session`);
  assert(unauthenticatedSession.status === 401, "unauthenticated /api/session must be 401");
  record("unauthenticated workspace and session APIs are guarded", {
    app_status: unauthenticatedApp.status,
    session_status: unauthenticatedSession.status,
  });

  const landing = await fetch(`${baseUrl}/`);
  const landingText = await landing.text();
  assert(landing.status === 200, "landing page must load");
  assert(landingText.includes("CUBI"), "landing page must carry CUBI branding");
  record("landing page served by the same preview runtime", {
    status: landing.status,
    bytes: landingText.length,
  });

  const chrome = await launchChrome();
  let page;
  try {
    page = new Page(chrome.cdp);
    await page.initialize();
    await page.cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1440,
      height: 900,
      deviceScaleFactor: 1,
      mobile: false,
    });

    await page.navigate(`${baseUrl}/`, ".cubi-reference-home", "public homepage for assistant avatar");
    const landingAvatarState = await page.evaluate(`(() => {
      const selectors = {
        dashboard: ".cubi-ai-bubble img",
        capability: ".cubi-feature-icon-assistant img",
        technology: ".cubi-tech-badges .ai img",
      };
      return Object.fromEntries(Object.entries(selectors).map(([name, selector]) => {
        const image = document.querySelector(selector);
        return [name, {
          found: Boolean(image),
          source: image?.getAttribute("src") ?? null,
          loaded: Boolean(image?.complete && image?.naturalWidth > 0),
        }];
      }));
    })()`);
    assert(
      Object.values(landingAvatarState).length === 3 &&
      Object.values(landingAvatarState).every((avatar) =>
        avatar.found && avatar.loaded && avatar.source?.endsWith("/cubi-assistant-avatar.svg")
      ),
      `homepage assistant avatars must all load from the shared asset: ${JSON.stringify(landingAvatarState)}`,
    );
    await page.screenshot("01-homepage-assistant-avatar.png");
    record("homepage assistant avatar is rendered and loaded in dashboard, capability card and technology badge", {
      avatars: landingAvatarState,
    });


    const launcherStateBeforeOpen = await page.evaluate(`(() => {
      const button = document.querySelector("#cubi-assistant-launcher");
      const avatar = button?.querySelector("img");
      const panel = document.querySelector("#cubi-assistant-popover");
      const action = panel?.querySelector("a.cubi-assistant-workspace-link");
      return {
        buttonFound: Boolean(button),
        avatarLoaded: Boolean(avatar?.complete && avatar.naturalWidth > 0),
        panelHidden: Boolean(panel?.hidden),
        expanded: button?.getAttribute("aria-expanded") ?? null,
        actionPath: action ? new URL(action.href).pathname : null,
      };
    })()`);
    assert(
      launcherStateBeforeOpen.buttonFound &&
      launcherStateBeforeOpen.avatarLoaded &&
      launcherStateBeforeOpen.panelHidden &&
      launcherStateBeforeOpen.expanded === "false" &&
      launcherStateBeforeOpen.actionPath?.endsWith("/app/"),
      "homepage assistant launcher initial state is invalid: " + JSON.stringify(launcherStateBeforeOpen),
    );
    await page.click("#cubi-assistant-launcher");
    const launcherStateAfterOpen = await page.evaluate(`(() => {
      const button = document.querySelector("#cubi-assistant-launcher");
      const panel = document.querySelector("#cubi-assistant-popover");
      return {
        visible: Boolean(panel && !panel.hidden),
        expanded: button?.getAttribute("aria-expanded") ?? null,
        title: panel?.querySelector("#cubi-assistant-title")?.textContent?.trim() ?? null,
        description: panel?.querySelector("#cubi-assistant-description")?.textContent?.trim() ?? null,
      };
    })()`);
    assert(
      launcherStateAfterOpen.visible &&
      launcherStateAfterOpen.expanded === "true" &&
      launcherStateAfterOpen.title &&
      launcherStateAfterOpen.description,
      "homepage assistant launcher did not open access panel: " + JSON.stringify(launcherStateAfterOpen),
    );
    await page.click("#cubi-assistant-close");
    const launcherStateAfterClose = await page.evaluate(`(() => {
      const button = document.querySelector("#cubi-assistant-launcher");
      const panel = document.querySelector("#cubi-assistant-popover");
      return { hidden: Boolean(panel?.hidden), expanded: button?.getAttribute("aria-expanded") ?? null };
    })()`);
    assert(
      launcherStateAfterClose.hidden && launcherStateAfterClose.expanded === "false",
      "homepage assistant launcher did not close access panel: " + JSON.stringify(launcherStateAfterClose),
    );
    record("homepage assistant launcher opens and closes its accessible workspace entry panel", {
      before: launcherStateBeforeOpen,
      open: launcherStateAfterOpen,
      closed: launcherStateAfterClose,
    });

    const homepageFixedState = await page.evaluate(`(async () => {
      const root = document.querySelector("#cubi-global-assistant");
      const button = document.querySelector("#cubi-assistant-launcher");
      if (!root || !button) return { found: false };
      document.body.style.minHeight = "180vh";
      window.scrollTo(0, 0);
      const before = root.getBoundingClientRect();
      window.scrollTo(0, document.documentElement.scrollHeight);
      await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const after = root.getBoundingClientRect();
      window.scrollTo(0, 0);
      return {
        found: true,
        mountedOnBody: root.parentElement === document.body,
        position: getComputedStyle(root).position,
        avatarLoaded: Boolean(button.querySelector("img")?.complete && button.querySelector("img")?.naturalWidth > 0),
        staysVisible: after.bottom <= window.innerHeight && after.top >= 0,
        staysPinned: Math.abs(before.bottom - after.bottom) < 1 && Math.abs(before.right - after.right) < 1,
      };
    })()`, { awaitPromise: true });
    assert(
      homepageFixedState.found && homepageFixedState.mountedOnBody &&
      homepageFixedState.position === "fixed" && homepageFixedState.avatarLoaded &&
      homepageFixedState.staysVisible && homepageFixedState.staysPinned,
      "homepage assistant must remain visible while scrolling: " + JSON.stringify(homepageFixedState),
    );
    record("homepage assistant stays visible while scrolling", homepageFixedState);

    const publicAssistantRoutes = [
      { route: "/platform/", shell: ".cubi-public-page", lang: "en", dir: "ltr" },
      { route: "/solutions/", shell: ".cubi-public-page", lang: "en", dir: "ltr" },
      { route: "/resources/", shell: ".cubi-public-page", lang: "en", dir: "ltr" },
      { route: "/contact/", shell: ".cubi-public-page", lang: "en", dir: "ltr" },
      { route: "/fa/", shell: ".cubi-reference-home", lang: "fa", dir: "rtl" },
      { route: "/fa/platform/", shell: ".cubi-public-page", lang: "fa", dir: "rtl" },
      { route: "/fa/solutions/", shell: ".cubi-public-page", lang: "fa", dir: "rtl" },
      { route: "/fa/resources/", shell: ".cubi-public-page", lang: "fa", dir: "rtl" },
      { route: "/fa/contact/", shell: ".cubi-public-page", lang: "fa", dir: "rtl" },
    ];
    for (const publicRoute of publicAssistantRoutes) {
      const route = publicRoute.route;
      // A browser refresh of the direct URL must land on the same page, in the
      // same language, with the same floating assistant entry.
      await page.navigate(`${baseUrl}${route}`, publicRoute.shell, "public page " + route);
      await page.waitFor('Boolean(document.querySelector("#cubi-assistant-launcher"))', "assistant launcher on " + route);
      const routeState = await page.evaluate(`(() => {
        const root = document.querySelector("#cubi-global-assistant");
        const button = document.querySelector("#cubi-assistant-launcher");
        const image = button?.querySelector("img");
        const bounds = button?.getBoundingClientRect();
        return {
          rootFound: Boolean(root),
          mountedOnBody: root?.parentElement === document.body,
          visible: Boolean(bounds && bounds.width > 0 && bounds.height > 0 && bounds.bottom <= window.innerHeight),
          fixed: root ? getComputedStyle(root).position === "fixed" : false,
          avatarLoaded: Boolean(image?.complete && image.naturalWidth > 0),
          documentLang: document.documentElement.lang,
          documentDir: document.documentElement.dir,
          launcherDir: root?.dir ?? null,
          launcherLabel: button?.getAttribute("aria-label") ?? "",
          workspaceHref: document.querySelector("#cubi-assistant-popover a")?.getAttribute("href") ?? "",
        };
      })()`);
      assert(routeState.rootFound && routeState.mountedOnBody && routeState.visible && routeState.fixed && routeState.avatarLoaded,
        "assistant not visible on " + route + ": " + JSON.stringify(routeState));
      assert(
        routeState.documentLang === publicRoute.lang && routeState.documentDir === publicRoute.dir,
        `${route} must render as ${publicRoute.lang}/${publicRoute.dir}: ` + JSON.stringify(routeState),
      );
      assert(
        routeState.launcherDir === publicRoute.dir,
        `${route} assistant entry must follow the document direction: ` + JSON.stringify(routeState),
      );
      assert(
        publicRoute.lang === "en"
          ? routeState.launcherLabel.includes("CUBI AI Assistant")
          : routeState.launcherLabel.includes("دستیار هوشمند کوبی"),
        `${route} assistant entry label is not in ${publicRoute.lang}: ` + JSON.stringify(routeState),
      );
      // The Persian landing is a language route, so its workspace link must climb
      // back to the single application shell instead of /fa/app/.
      assert(
        new URL(routeState.workspaceHref, `${baseUrl}${route}`).pathname.endsWith("/app/"),
        `${route} assistant workspace link must target the real app route: ` + JSON.stringify(routeState),
      );
      record("floating assistant visible on " + route, routeState);
    }

    // The assistant entry must stay a single, self-contained widget that works
    // without any backend call: one root, one panel, zero network requests.
    await page.navigate(`${baseUrl}/platform/`, ".cubi-public-page", "platform page for assistant isolation");
    await page.waitForSelector("#cubi-assistant-launcher", "assistant launcher on platform page");
    const assistantIsolation = await page.evaluate(`(() => {
      const networkEntries = performance.getEntriesByType("resource");
      return {
        roots: document.querySelectorAll("#cubi-global-assistant").length,
        panels: document.querySelectorAll("#cubi-assistant-popover").length,
        launcherButtons: document.querySelectorAll("#cubi-assistant-launcher").length,
        requestInitiators: networkEntries
          .filter((entry) => entry.initiatorType === "fetch" || entry.initiatorType === "xmlhttprequest")
          .map((entry) => entry.name),
      };
    })()`);
    assert(
      assistantIsolation.roots === 1 &&
        assistantIsolation.panels === 1 &&
        assistantIsolation.launcherButtons === 1 &&
        assistantIsolation.requestInitiators.length === 0,
      "assistant entry must be a single instance without network coupling: " +
        JSON.stringify(assistantIsolation),
    );
    record("floating assistant mounts once with one panel and zero API requests", assistantIsolation);

    const assistantEscapeAndOutside = await page.evaluate(`(async () => {
      const launcher = document.querySelector("#cubi-assistant-launcher");
      const panel = document.querySelector("#cubi-assistant-popover");
      const press = (key) => document.body.dispatchEvent(
        new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true }),
      );
      const before = { openByClick: false, closedByEscape: false, closedByOutsideClick: false, focusAfterEscape: null };

      launcher.click();
      before.openByClick = !panel.hidden && launcher.getAttribute("aria-expanded") === "true";
      await new Promise((resolve) => requestAnimationFrame(resolve));
      before.focusAfterOpen = document.activeElement?.id ?? null;
      press("Escape");
      await new Promise((resolve) => requestAnimationFrame(resolve));
      before.closedByEscape = panel.hidden && launcher.getAttribute("aria-expanded") === "false";
      before.focusAfterEscape = document.activeElement?.id ?? null;

      launcher.click();
      await new Promise((resolve) => requestAnimationFrame(resolve));
      document.querySelector("main").dispatchEvent(
        new PointerEvent("pointerdown", { bubbles: true, cancelable: true }),
      );
      await new Promise((resolve) => requestAnimationFrame(resolve));
      before.closedByOutsideClick = panel.hidden && launcher.getAttribute("aria-expanded") === "false";
      before.stillMounted = Boolean(document.querySelector("#cubi-global-assistant"));
      before.pageStillInteractive = document.querySelector(".cubi-public-hero h1") !== null;
      return before;
    })()`, { awaitPromise: true });
    assert(
      assistantEscapeAndOutside.openByClick &&
        assistantEscapeAndOutside.closedByEscape &&
        assistantEscapeAndOutside.focusAfterEscape === "cubi-assistant-launcher" &&
        assistantEscapeAndOutside.closedByOutsideClick &&
        assistantEscapeAndOutside.stillMounted &&
        assistantEscapeAndOutside.pageStillInteractive,
      "assistant panel keyboard and dismissal contract failed: " +
        JSON.stringify(assistantEscapeAndOutside),
    );
    record("assistant panel closes on Escape anywhere and on outside pointer down", assistantEscapeAndOutside);

    const assistantArtworkFailure = await page.evaluate(`(async () => {
      const root = document.querySelector("#cubi-global-assistant");
      const launcher = document.querySelector("#cubi-assistant-launcher");
      const slots = Array.from(root.querySelectorAll(".cubi-assistant-avatar-slot"));
      slots.forEach((slot) => slot.querySelector("img")?.dispatchEvent(new Event("error")));
      await new Promise((resolve) => requestAnimationFrame(resolve));
      const rect = launcher.getBoundingClientRect();
      const badge = root.querySelector(".cubi-assistant-avatar-fallback");
      const before = {
        slotCount: slots.length,
        everySlotFlaggedFailed: slots.every((slot) => slot.dataset.avatarFailed === "true"),
        entryRemovedFromDom: !document.querySelector("#cubi-global-assistant"),
        entryStillVisible: rect.width > 0 && rect.height > 0,
        fallbackBadgeShown: getComputedStyle(badge).display !== "none",
        panelStillOpens: false,
      };
      launcher.click();
      before.panelStillOpens = !document.querySelector("#cubi-assistant-popover").hidden;
      launcher.click();
      return before;
    })()`, { awaitPromise: true });
    assert(
      assistantArtworkFailure.slotCount >= 1 &&
        assistantArtworkFailure.everySlotFlaggedFailed &&
        !assistantArtworkFailure.entryRemovedFromDom &&
        assistantArtworkFailure.entryStillVisible &&
        assistantArtworkFailure.fallbackBadgeShown &&
        assistantArtworkFailure.panelStillOpens,
      "assistant entry must survive a failed avatar artwork load: " +
        JSON.stringify(assistantArtworkFailure),
    );
    record("failed assistant artwork keeps a working labelled entry point", assistantArtworkFailure);

    // The entry point must not depend on any transport: give the document an
    // API layer that always fails and confirm the assistant still mounts.
    const failingTransport = await page.cdp.send("Page.addScriptToEvaluateOnNewDocument", {
      source: `
        window.__cubiAssistantTransportCalls = 0;
        window.fetch = () => {
          window.__cubiAssistantTransportCalls += 1;
          return Promise.reject(new Error("ASSISTANT_SERVICE_UNAVAILABLE"));
        };
        window.XMLHttpRequest = function CubiBlockedXHR() {
          window.__cubiAssistantTransportCalls += 1;
          throw new Error("ASSISTANT_SERVICE_UNAVAILABLE");
        };
      `,
    });
    await page.navigate(
      `${baseUrl}/platform/`,
      "#cubi-assistant-launcher",
      "public page with an unavailable assistant transport",
    );
    const assistantWithoutTransport = await page.evaluate(`(() => {
      const launcher = document.querySelector("#cubi-assistant-launcher");
      const panel = document.querySelector("#cubi-assistant-popover");
      const rect = launcher.getBoundingClientRect();
      launcher.click();
      const opened = !panel.hidden;
      const title = panel.querySelector("#cubi-assistant-title")?.textContent?.trim() ?? null;
      launcher.click();
      return {
        launcherFound: Boolean(launcher),
        singleRoot: document.querySelectorAll("#cubi-global-assistant").length,
        entryVisible: rect.width > 0 && rect.height > 0,
        openedWithoutSession: opened,
        title,
        transportCalls: window.__cubiAssistantTransportCalls,
        pageContentIntact: document.querySelector(".cubi-public-hero h1") !== null,
      };
    })()`);
    await page.cdp.send("Page.removeScriptToEvaluateOnNewDocument", {
      identifier: failingTransport.identifier,
    });
    assert(
      assistantWithoutTransport.launcherFound &&
        assistantWithoutTransport.singleRoot === 1 &&
        assistantWithoutTransport.entryVisible &&
        assistantWithoutTransport.openedWithoutSession &&
        assistantWithoutTransport.title &&
        assistantWithoutTransport.transportCalls === 0 &&
        assistantWithoutTransport.pageContentIntact,
      "assistant entry must stay usable when the workspace backend is unavailable: " +
        JSON.stringify(assistantWithoutTransport),
    );
    record("assistant entry mounts with a failing transport and issues zero transport calls", assistantWithoutTransport);

    // The route is authoritative for the document language, and visiting the
    // Persian routes above persists that preference, so the English landing would
    // legitimately redirect. Geometry evidence has to be language-deterministic:
    // drop the stored preference and prove the document under test is English.
    await page.evaluate(`(() => {
      try { localStorage.removeItem("cubi:landing-locale"); } catch { /* storage is optional */ }
      return true;
    })()`);
    await page.navigate(`${baseUrl}/`, ".cubi-reference-home", "homepage for assistant geometry checks");
    const assistantGeometryProbe = `(() => {
      const root = document.querySelector("#cubi-global-assistant");
      const launcher = document.querySelector("#cubi-assistant-launcher");
      // The button holds two spans: the avatar slot and the visible label. Only
      // the label may be hidden by the compact rules, so select by type, not by
      // ":last-child", which also matches the fallback badge inside the slot.
      const label = launcher.querySelector(":scope > span:last-of-type");
      const rect = launcher.getBoundingClientRect();
      const rootStyle = getComputedStyle(root);
      // "inline end" is a physical edge only once the direction is known: right
      // for LTR, left for RTL. The pin gap must equal the declared inset in both,
      // which is what proves the widget mirrors instead of being hardcoded. A
      // fixed element is positioned against the layout viewport, which excludes a
      // classic scrollbar, so the right edge is clientWidth and not innerWidth.
      const layoutWidth = document.documentElement.clientWidth;
      const inlineEndGap = rootStyle.direction === "rtl"
        ? rect.left
        : layoutWidth - rect.right;
      const coverTargets = [
        ["language", "#cubi-language"],
        ["primary CTA", ".cubi-exact-hero-actions .cubi-exact-primary"],
        ["sign in", ".cubi-exact-signin"],
        ["get started", ".cubi-exact-start"],
        ...Array.from(document.querySelectorAll(".cubi-exact-nav a")).map((_, index) => ["nav link " + index, ".cubi-exact-nav a:nth-of-type(" + (index + 1) + ")"]),
      ].map(([name, selector]) => {
        const element = document.querySelector(selector);
        if (!element) return { name, present: false, overlaps: false };
        const target = element.getBoundingClientRect();
        const overlaps =
          rect.left < target.right && rect.right > target.left &&
          rect.top < target.bottom && rect.bottom > target.top;
        return { name, present: true, overlaps };
      });
      return {
        documentLang: document.documentElement.lang,
        documentDir: document.documentElement.dir,
        compactMode: root.dataset.compact === "true",
        compactMediaMatches: window.matchMedia("(max-width: 520px)").matches,
        viewportWidth: window.innerWidth,
        layoutWidth,
        launcherWidth: Math.round(rect.width),
        insideViewport: rect.left >= -1 && rect.right <= layoutWidth + 1 &&
          rect.top >= -1 && rect.bottom <= window.innerHeight + 1,
        labelHidden: label.getBoundingClientRect().width <= 1,
        labelWidth: Math.round(label.getBoundingClientRect().width),
        rootDirection: rootStyle.direction,
        declaredInlineEndInset: Math.round(parseFloat(rootStyle.insetInlineEnd) || 0),
        inlineEndGap: Math.round(inlineEndGap),
        accessibleName: launcher.getAttribute("aria-label"),
        horizontalOverflow: document.documentElement.scrollWidth - layoutWidth,
        coverTargets,
      };
    })()`;
    for (const viewport of [
      { width: 390, height: 844, mobile: true, compact: true, screenshot: "02a-mobile-assistant-launcher.png", label: "mobile 390px" },
      { width: 820, height: 1180, mobile: true, compact: false, screenshot: "02a2-tablet-assistant-launcher.png", label: "tablet 820px" },
      { width: 1440, height: 900, mobile: false, compact: false, screenshot: "02a3-desktop-assistant-launcher.png", label: "desktop 1440px" },
    ]) {
      await page.cdp.send("Emulation.setDeviceMetricsOverride", {
        width: viewport.width,
        height: viewport.height,
        deviceScaleFactor: viewport.mobile ? 2 : 1,
        mobile: viewport.mobile,
      });
      // The compact flag is driven by a matchMedia listener, so wait until the
      // emulated width, the media query and the widget state agree instead of
      // trusting a fixed delay that can measure a mid-resize layout.
      await page.waitFor(
        `(() => {
          const root = document.querySelector("#cubi-global-assistant");
          if (!root) return false;
          const matches = window.matchMedia("(max-width: 520px)").matches;
          return Math.abs(window.innerWidth - ${viewport.width}) <= 1 &&
            root.dataset.compact === String(${viewport.compact}) &&
            root.dataset.compact === String(matches);
        })()`,
        `${viewport.label} assistant entry settles its compact state`,
        4000,
      );
      const geometry = await page.evaluate(assistantGeometryProbe);
      assert(
        geometry.documentLang === "en" && geometry.documentDir === "ltr",
        `${viewport.label} geometry must be measured on the English landing route: ` +
          JSON.stringify(geometry),
      );
      assert(
        geometry.insideViewport &&
          geometry.horizontalOverflow <= 1 &&
          Boolean(geometry.accessibleName) &&
          geometry.compactMode === viewport.compact &&
          geometry.compactMediaMatches === viewport.compact &&
          geometry.labelHidden === viewport.compact &&
          geometry.launcherWidth <= (viewport.compact ? 64 : 340) &&
          geometry.rootDirection === "ltr" &&
          Math.abs(geometry.inlineEndGap - geometry.declaredInlineEndInset) <= 1 &&
          geometry.coverTargets.every((target) => !target.overlaps),
        `${viewport.label} assistant entry must stay pinned, correctly labelled and clear of page controls: ` +
          JSON.stringify(geometry),
      );
      await page.screenshot(viewport.screenshot);
      record(`${viewport.label} assistant entry is pinned and overlaps no control`, geometry);
    }

    // The panel itself is verified on the narrowest supported viewport. The
    // geometry loop ends on desktop, so re-apply the mobile metrics and wait for
    // them instead of measuring a desktop popover under a mobile label.
    await page.cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 390,
      height: 844,
      deviceScaleFactor: 2,
      mobile: true,
    });
    await page.waitFor(
      `Math.abs(window.innerWidth - 390) <= 1 &&
        document.querySelector("#cubi-global-assistant")?.dataset.compact === "true"`,
      "mobile metrics before the assistant panel check",
      4000,
    );

    const mobileAssistantPanel = await page.evaluate(`(() => {
      const launcher = document.querySelector("#cubi-assistant-launcher");
      launcher.click();
      const panel = document.querySelector("#cubi-assistant-popover");
      const rect = panel.getBoundingClientRect();
      const close = document.querySelector("#cubi-assistant-close");
      const closeRect = close.getBoundingClientRect();
      return {
        opened: !panel.hidden,
        insideViewport: rect.left >= -1 && rect.right <= window.innerWidth + 1 &&
          rect.top >= -1 && rect.bottom <= window.innerHeight + 1,
        panelWidth: Math.round(rect.width),
        closeReachable: closeRect.width >= 24 && closeRect.height >= 24 &&
          closeRect.top >= 0 && closeRect.bottom <= window.innerHeight,
      };
    })()`);
    assert(
      mobileAssistantPanel.opened &&
        mobileAssistantPanel.insideViewport &&
        mobileAssistantPanel.closeReachable,
      "assistant panel must fit a 390px viewport with a reachable close control: " +
        JSON.stringify(mobileAssistantPanel),
    );
    await page.screenshot("02b-mobile-assistant-panel.png");
    record("assistant panel fits the mobile viewport with a reachable close control", mobileAssistantPanel);

    // Persian is a real route with its own document, not a client-only repaint of
    // the English page: load /fa/ directly and verify the mirrored assistant entry.
    await page.cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1440,
      height: 900,
      deviceScaleFactor: 1,
      mobile: false,
    });
    await page.waitFor(
      `Math.abs(window.innerWidth - 1440) <= 1 &&
        document.querySelector("#cubi-global-assistant")?.dataset.compact === "false"`,
      "desktop metrics before the Persian route check",
      4000,
    );
    await page.navigate(`${baseUrl}/fa/`, ".cubi-reference-home", "Persian landing route");
    const rtlAssistant = await page.evaluate(`(() => {
      const root = document.querySelector("#cubi-global-assistant");
      const launcher = document.querySelector("#cubi-assistant-launcher");
      const rect = launcher.getBoundingClientRect();
      const rootStyle = getComputedStyle(root);
      // RTL pinning is proven by geometry, not by a pixel guess: the gap to the
      // physical left edge must equal the declared logical inset, and the entry
      // must sit further from the right edge than from the left one.
      const declaredInlineEndInset = parseFloat(rootStyle.insetInlineEnd) || 0;
      const layoutWidth = document.documentElement.clientWidth;
      const inlineEndGap = rootStyle.direction === "rtl" ? rect.left : layoutWidth - rect.right;
      const panel = document.querySelector("#cubi-assistant-popover");
      launcher.click();
      const panelRect = panel.getBoundingClientRect();
      const persianTitle = panel.querySelector("#cubi-assistant-title")?.textContent?.trim() ?? "";
      const persianAction = panel.querySelector("a.cubi-assistant-workspace-link")?.textContent?.trim() ?? "";
      const workspacePath = new URL(panel.querySelector("a.cubi-assistant-workspace-link").href).pathname;
      launcher.click();
      const result = {
        documentDir: document.documentElement.dir,
        documentLang: document.documentElement.lang,
        launcherDir: root.dir,
        rootDirection: rootStyle.direction,
        declaredInlineEndInset: Math.round(declaredInlineEndInset),
        inlineEndGap: Math.round(inlineEndGap),
        leftGap: Math.round(rect.left),
        rightGap: Math.round(layoutWidth - rect.right),
        pinnedToInlineEnd:
          rootStyle.direction === "rtl" &&
          Math.abs(inlineEndGap - declaredInlineEndInset) <= 1 &&
          rect.left < layoutWidth - rect.right,
        insideViewport: rect.left >= -1 && rect.right <= layoutWidth + 1,
        panelInsideViewport: panelRect.left >= -1 && panelRect.right <= layoutWidth + 1,
        persianTitle,
        persianAction,
        workspacePath,
        panelClosesOnEscape: (() => {
          launcher.click();
          document.body.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));
          const closed = panel.hidden;
          return closed;
        })(),
      };
      return result;
    })()`, { awaitPromise: true });
    assert(
      rtlAssistant.documentDir === "rtl" &&
        rtlAssistant.launcherDir === "rtl" &&
        rtlAssistant.pinnedToInlineEnd &&
        rtlAssistant.insideViewport &&
        rtlAssistant.panelInsideViewport &&
        rtlAssistant.persianTitle.includes("دستیار هوشمند کوبی") &&
        rtlAssistant.persianAction.includes("فضای کاری") &&
        rtlAssistant.workspacePath.endsWith("/app/") &&
        rtlAssistant.panelClosesOnEscape,
      "Persian RTL assistant entry must mirror to the inline end, stay labelled and remain operable: " +
        JSON.stringify(rtlAssistant),
    );
    await page.screenshot("02c-persian-rtl-assistant.png");
    record("Persian RTL assistant entry mirrors, translates and stays operable", rtlAssistant);

    // The header switch must move between the two language routes for a real URL.
    await page.click("#cubi-language");
    await page.waitFor(
      `document.readyState === "complete" && document.documentElement.dir === "ltr" && Boolean(document.querySelector(".cubi-reference-home"))`,
      "English landing after the language switch",
    );
    const switchToEnglish = await page.evaluate(`(() => ({
      pathname: location.pathname,
      lang: document.documentElement.lang,
      dir: document.documentElement.dir,
      assistantLabel: document.querySelector("#cubi-assistant-launcher")?.getAttribute("aria-label") ?? "",
      savedLocale: (() => { try { return localStorage.getItem("cubi:landing-locale"); } catch { return null; } })(),
    }))()`);
    assert(
      switchToEnglish.lang === "en" &&
        switchToEnglish.dir === "ltr" &&
        switchToEnglish.assistantLabel.includes("CUBI AI Assistant") &&
        switchToEnglish.savedLocale === "en",
      "language switch must land on the English route with English assistant copy: " +
        JSON.stringify(switchToEnglish),
    );
    record("header language switch navigates from /fa/ to the English route", switchToEnglish);

    await page.evaluate(`(() => {
      try { localStorage.removeItem("cubi:landing-locale"); } catch { /* storage is optional */ }
      return true;
    })()`);
    await page.cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1440,
      height: 900,
      deviceScaleFactor: 1,
      mobile: false,
    });
    await sleep(200);

    await page.navigate(
      `${baseUrl}/preview/login`,
      'form[action="/preview/login"]',
      "login page",
    );
    const personaCount = await page.count(
      'form[action="/preview/login"] button[name="role"]',
    );
    assert(personaCount === 4, "four demo personas must be offered");
    assert(
      (await page.text(".eyebrow"))?.includes("local full-stack preview"),
      "login page must declare local preview",
    );
    await page.screenshot("01-login.png");
    record("demo login exposes fixture-only personas including a real first-run account", {
      personas: personaCount,
    });

    await page.click('button[name="role"][value="planner"]');
    await page.waitFor(`location.pathname === "/app"`, "planner redirect to /app");
    await page.waitForSelector(".cp-project-selection", "project selection");
    const projectButtons = await page.evaluate(`(() =>
      Array.from(document.querySelectorAll("button[data-project-id]")).map((button) => ({
        id: button.dataset.projectId,
        name: button.textContent.trim(),
      }))
    )()`);
    assert(projectButtons.length === 2, "two projects must be selectable");
    const projectIds = projectButtons.map((item) => item.id).sort();
    assert(
      projectIds.includes("preview-rps-01") && projectIds.includes("preview-nse-02"),
      "both fixture projects must be listed",
    );
    assert(
      (await page.text("#cubi-preview-banner"))?.includes("LOCAL PREVIEW"),
      "preview banner must be visible on the workspace shell",
    );
    await page.screenshot("02-project-selection.png");
    record("planner session lists the two persisted fixture projects", {
      projects: projectButtons,
    });

    // The workspace language is a real preference and the root document must
    // declare it. A CI runner and a developer machine can have different OS
    // locales, so this run picks English explicitly and proves the switch
    // re-renders the same first step instead of dropping the selection.
    const languageBeforeSwitch = await page.evaluate(`(() => ({
      lang: document.documentElement.lang,
      dir: document.documentElement.dir,
      next: document.querySelector("[data-bootstrap-language]")?.dataset.bootstrapLanguage ?? null,
      options: document.querySelectorAll("button[data-project-id]").length,
    }))()`);
    assert(
      languageBeforeSwitch.options === 2,
      "the selection step must still be rendered before the language switch",
    );
    if (languageBeforeSwitch.lang !== "en") {
      await page.click('[data-bootstrap-language="en"]');
      await page.waitFor(
        `document.documentElement.lang === "en" && document.documentElement.dir === "ltr"`,
        "English selection page",
      );
    }
    const languageAfterSwitch = await page.evaluate(`(() => ({
      lang: document.documentElement.lang,
      dir: document.documentElement.dir,
      options: document.querySelectorAll("button[data-project-id]").length,
      stored: (() => { try { return localStorage.getItem("cubi:workspace-locale"); } catch { return null; } })(),
    }))()`);
    assert(
      languageAfterSwitch.lang === "en" &&
        languageAfterSwitch.dir === "ltr" &&
        languageAfterSwitch.options === 2 &&
        languageAfterSwitch.stored === "en",
      "switching language must keep the project-selection step and persist the choice: " +
        JSON.stringify({ before: languageBeforeSwitch, after: languageAfterSwitch }),
    );
    record("workspace language switch keeps the first step and persists the choice", {
      before: languageBeforeSwitch,
      after: languageAfterSwitch,
    });

    // Before a project is open the floating entry must stay honest: it is visible,
    // it does not fabricate a second assistant panel, and it says what the user has
    // to do next instead of appearing to do nothing.
    const assistantNeedsProject = await page.evaluate(`(async () => {
      const frames = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      const launcher = document.querySelector("#cubi-assistant-launcher");
      const panel = document.querySelector("#cubi-assistant-popover");
      const description = panel.querySelector("#cubi-assistant-description");
      const action = panel.querySelector("a.cubi-assistant-workspace-link");
      const state = {
        launcherVisible: launcher.getBoundingClientRect().width > 0,
        chatPanelsBeforeProject: document.querySelectorAll("#cp-ai-assistant-chat").length,
      };
      launcher.click();
      await frames();
      state.openedByClick = !panel.hidden;
      action.click();
      await frames();
      state.guidanceText = description.textContent ?? "";
      state.guidanceFocused = document.activeElement === description;
      state.stillOnePanel = document.querySelectorAll("#cubi-assistant-popover").length === 1;
      document.body.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));
      await frames();
      state.closedOnEscape = panel.hidden;
      return state;
    })()`, { awaitPromise: true });
    assert(
      assistantNeedsProject.launcherVisible &&
        assistantNeedsProject.chatPanelsBeforeProject === 0 &&
        assistantNeedsProject.openedByClick &&
        /open (a|or create a) project/i.test(assistantNeedsProject.guidanceText) &&
        assistantNeedsProject.guidanceFocused &&
        assistantNeedsProject.stillOnePanel &&
        assistantNeedsProject.closedOnEscape,
      "assistant entry must state the missing-project guidance without faking a panel: " +
        JSON.stringify(assistantNeedsProject),
    );
    await page.screenshot("02d-assistant-needs-project.png");
    record("assistant entry guides the user when no project is open", assistantNeedsProject);

    await page.click(`button[data-project-id="${PROJECT_ID}"]`);
    await page.waitForSelector(".cp-workspace", "workspace shell");
    await page.waitFor(
      `document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]").length === 14`,
      "fourteen persisted activity rows",
    );
    await page.waitFor(
      `document.querySelectorAll(".cp-gantt-row").length === 14`,
      "fourteen Gantt rows",
    );
    await page.waitForSelector("#cp-ai-assistant-chat .cp-ai-chat-avatar", "assistant chat avatar");
    await page.waitForSelector("#cp-ai-action-panel .cp-ai-action-avatar", "assistant action panel avatar");
    await page.waitFor(
      `(() => {
        const images = [
          document.querySelector("#cp-ai-assistant-chat .cp-ai-chat-avatar"),
          document.querySelector("#cp-ai-action-panel .cp-ai-action-avatar"),
        ];
        return images.every((image) =>
          image && image.complete && image.naturalWidth > 0 &&
          image.getAttribute("src")?.endsWith("/cubi-assistant-avatar.svg")
        );
      })()`,
      "workspace assistant avatars load from the shared asset",
    );
    const workspaceAvatarState = await page.evaluate(`(() =>
      Array.from(document.querySelectorAll("#cp-ai-assistant-chat .cp-ai-chat-avatar, #cp-ai-action-panel .cp-ai-action-avatar"))
        .map((image) => ({
          src: image.getAttribute("src"),
          loaded: image.complete && image.naturalWidth > 0,
        }))
    )()`);
    assert(
      workspaceAvatarState.length === 2 && workspaceAvatarState.every((avatar) => avatar.loaded),
      `workspace chat and action avatars must both load: ${JSON.stringify(workspaceAvatarState)}`,
    );
    record("authenticated workspace renders loaded chat and action-panel assistant avatars", {
      avatars: workspaceAvatarState,
    });

    // Inside the workspace the floating entry must route to the real assistant
    // panel, stay a single instance and never spawn a second independent panel.
    const workspaceLauncherRouting = await page.evaluate(`(() => {
      const launcher = document.querySelector("#cubi-assistant-launcher");
      const panel = document.querySelector("#cubi-assistant-popover");
      const action = panel.querySelector("a.cubi-assistant-workspace-link");
      const chat = document.querySelector("#cp-ai-assistant-chat");
      // Start from a known closed state so the open/close assertions cannot be
      // satisfied by a panel an earlier step happened to leave open.
      if (!panel.hidden) {
        document.body.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));
      }
      const before = {
        startedClosed: panel.hidden,
        launcherSingle: document.querySelectorAll("#cubi-global-assistant").length,
        panelSingle: document.querySelectorAll("#cubi-assistant-popover").length,
        chatSingle: document.querySelectorAll("#cp-ai-assistant-chat").length,
        actionLabel: action?.textContent?.trim() ?? null,
        chatOpenBefore: chat?.open ?? null,
      };
      launcher.click();
      before.opened = !panel.hidden && launcher.getAttribute("aria-expanded") === "true";
      if (chat) chat.dataset.e2eLauncherTarget = "routing";
      action.click();
      before.chatOpenAfterAction = chat?.open ?? null;
      before.panelClosedAfterAction = panel.hidden;
      before.focusOnChatSummary = document.activeElement === chat?.querySelector("summary");
      return before;
    })()`);
    // The routed panel scrolls itself into view with the platform scroll
    // behaviour, so reachability is waited for instead of trusting a fixed delay.
    // A chat taller than the viewport counts as reachable when its own header is
    // on screen. The stamp proves whether the workspace re-rendered (and therefore
    // replaced) the panel the launcher routed to.
    const chatReachProbe = `(() => {
      const chat = document.querySelector("#cp-ai-assistant-chat");
      if (!chat) return { onScreen: false, found: false };
      const rect = chat.getBoundingClientRect();
      const summaryRect = chat.querySelector("summary")?.getBoundingClientRect();
      return {
        onScreen: rect.height > 0 && rect.top < window.innerHeight && rect.bottom > 0 &&
          Boolean(summaryRect) && summaryRect.top < window.innerHeight && summaryRect.bottom > 0,
        found: true,
        samePanelAfterRouting: chat.dataset.e2eLauncherTarget === "routing",
        panelHeight: Math.round(rect.height),
        panelTop: Math.round(rect.top),
        panelBottom: Math.round(rect.bottom),
        summaryTop: summaryRect ? Math.round(summaryRect.top) : null,
        summaryHeight: summaryRect ? Math.round(summaryRect.height) : null,
        viewportHeight: window.innerHeight,
        scrollY: Math.round(window.scrollY),
      };
    })`;
    let chatReachedTheViewport = true;
    try {
      await page.waitFor(
        `(${chatReachProbe})().onScreen`,
        "assistant chat panel reachable after launcher routing",
        6000,
      );
    } catch {
      chatReachedTheViewport = false;
    }
    const workspaceChatVisibility = await page.evaluate(`(${chatReachProbe})()`);
    assert(
      workspaceLauncherRouting.startedClosed &&
        workspaceLauncherRouting.launcherSingle === 1 &&
        workspaceLauncherRouting.panelSingle === 1 &&
        workspaceLauncherRouting.chatSingle === 1 &&
        workspaceLauncherRouting.opened &&
        /assistant panel|پنل دستیار/.test(workspaceLauncherRouting.actionLabel ?? "") &&
        workspaceLauncherRouting.chatOpenAfterAction === true &&
        workspaceLauncherRouting.panelClosedAfterAction === true &&
        workspaceLauncherRouting.focusOnChatSummary &&
        chatReachedTheViewport &&
        workspaceChatVisibility.found &&
        workspaceChatVisibility.onScreen &&
        workspaceChatVisibility.samePanelAfterRouting,
      "workspace assistant entry must route to the single real chat panel: " +
        JSON.stringify({ ...workspaceLauncherRouting, ...workspaceChatVisibility, chatReachedTheViewport }),
    );
    await page.screenshot("03-workspace-assistant-launcher-routing.png");
    record("workspace assistant entry routes to the single real assistant panel", workspaceLauncherRouting);

    assert(
      (await page.text(".cp-project"))?.includes(PROJECT_ID),
      "workspace identifies the selected project",
    );
    assert(
      (await page.text(".cp-revision"))?.includes(`R${PROJECT_REVISION}`),
      "workspace identifies the persisted project revision",
    );
    const menuCount = await page.count(".cp-menu button[data-menu]");
    assert(menuCount === 9, "nine main menus must render");
    const menuLabels = await page.evaluate(`(() =>
      Array.from(document.querySelectorAll(".cp-menu button[data-menu]")).map((button) => button.textContent.trim())
    )()`);
    assert(
      menuLabels.includes("Schedule") && menuLabels.includes("Resources"),
      "main menu labels must be bilingual-ready English defaults",
    );
    assert(
      (await page.text(".cp-navigation-surface strong")) === "Schedule",
      "schedule is the initial workspace surface",
    );
    assert(
      (await page.text(".cp-navigation-surface [data-surface-status]")) === "Implemented",
      "schedule surface status must be honest",
    );
    const scheduleSubmenus = await page.count(".cp-navigation-surface a.cp-submenu-item");
    assert(scheduleSubmenus === 13, "thirteen schedule submenu anchors expected");
    const headerLabels = await page.evaluate(`(() =>
      Array.from(document.querySelectorAll("#cp-activity-grid thead th")).map((th) => th.textContent.replace("ƒx", "").trim())
    )()`);
    assert(headerLabels.length === 10, "ten visible persisted columns expected");
    assert(
      headerLabels[0] === "Id" && headerLabels[1] === "Name",
      "authoritative Activity Id/Name columns must lead the grid",
    );
    const criticalBars = await page.count(".cp-gantt-bar.is-critical");
    assert(criticalBars >= 1, "Shared Core critical path must reach the Gantt");
    const ganttAria = await page.evaluate(`(() =>
      Array.from(document.querySelectorAll(".cp-gantt-row")).slice(0, 3).map((row) => ({
        id: row.dataset.ganttActivityId,
        label: row.getAttribute("aria-label"),
      }))
    )()`);
    assert(
      ganttAria.every((row) => row.id && row.label === row.id),
      "Gantt rows must expose real activity identities",
    );
    await page.screenshot("03-workspace-desktop.png");
    record("real workspace renders persisted rows, columns and Gantt facts", {
      menu_count: menuCount,
      visible_columns: headerLabels,
      grid_rows: 14,
      gantt_rows: 14,
      critical_bars: criticalBars,
      schedule_submenus: scheduleSubmenus,
    });

    await page.click('#cp-activity-grid tbody tr[data-activity-id="A130"]');
    await page.waitFor(
      `document.querySelector("#cp-details .cp-detail-selected")?.textContent.trim() === "A130"`,
      "A130 selection details",
    );
    assert(
      (await page.evaluate(
        `document.querySelector('#cp-activity-grid tbody tr[data-activity-id="A130"]').getAttribute("aria-selected")`,
      )) === "true",
      "grid row selection must be exposed",
    );
    await page.click('.cp-gantt-row[data-gantt-activity-id="A130"]');
    await page.waitFor(
      `document.querySelector('.cp-gantt-row[data-gantt-activity-id="A130"]').getAttribute("aria-pressed") === "true"`,
      "Gantt row selection",
    );
    assert(
      (await page.text("#cp-details .cp-detail-selected")) === "A130",
      "table and Gantt must share activity selection",
    );
    record("grid and Gantt share real activity selection", { activity: "A130" });

    const isoTooltip = await page.evaluate(
      `document.querySelector('#cp-activity-grid tbody tr[data-activity-id="A130"] td[data-column-id="activity.early_start"]')?.textContent.trim()`,
    );
    assert(
      /^\d{4}-\d{2}-\d{2}$/.test(isoTooltip ?? ""),
      `Gregorian display must show the canonical ISO date, got ${isoTooltip}`,
    );
    await page.click('[data-calendar-mode="jalali"]');
    await page.waitFor(
      `document.querySelector('#cp-activity-grid tbody tr[data-activity-id="A130"] td[data-column-id="activity.early_start"]')?.textContent.trim() === "۱۴۰۵/۰۷/۱۵"`,
      "Jalali display of the stored early start",
    );
    const jalaliText = await page.evaluate(
      `document.querySelector('#cp-activity-grid tbody tr[data-activity-id="A130"] td[data-column-id="activity.early_start"]')?.textContent.trim()`,
    );
    assert(
      jalaliText === "۱۴۰۵/۰۷/۱۵",
      `Jalali display must convert 2026-10-07 without shifting it, got ${jalaliText}`,
    );
    await page.click('[data-calendar-mode="gregorian"]');
    await page.waitFor(
      `document.querySelector('#cp-activity-grid tbody tr[data-activity-id="A130"] td[data-column-id="activity.early_start"]')?.textContent.trim() === ${JSON.stringify(isoTooltip)}`,
      "Gregorian restoration of the stored early start",
    );
    EVIDENCE.calendar_display = {
      stored_iso: isoTooltip,
      jalali: jalaliText,
      restored_iso: isoTooltip,
      source: "persisted workspace cells rendered in Jalali and Gregorian",
    };
    record("Jalali/Gregorian display toggles without changing stored schedule dates", {
      stored_iso: isoTooltip,
      jalali: jalaliText,
    });

    for (const surface of [
      { menu: "project", label: "Project", status: "Partial", submenus: 3 },
      { menu: "resources", label: "Resources", status: "Partial", submenus: 2 },
      { menu: "control", label: "Control", status: "Partial", submenus: 2 },
      { menu: "schedule", label: "Schedule", status: "Implemented", submenus: 13 },
    ]) {
      await page.click(`[data-menu="${surface.menu}"]`);
      await page.waitFor(
        `document.querySelector(".cp-navigation-surface strong")?.textContent.trim() === ${JSON.stringify(surface.label)}`,
        `${surface.label} navigation surface`,
      );
      const status = await page.text(".cp-navigation-surface [data-surface-status]");
      assert(
        status === surface.status,
        `${surface.label} status must be ${surface.status}, got ${status}`,
      );
      const submenus = await page.count(
        ".cp-navigation-surface a.cp-submenu-item, .cp-navigation-surface span.cp-submenu-item",
      );
      assert(
        submenus === surface.submenus,
        `${surface.label} must expose ${surface.submenus} submenus`,
      );
      const current = await page.evaluate(
        `document.querySelector('[data-menu="${surface.menu}"]').getAttribute("aria-current")`,
      );
      assert(current === "page", `${surface.label} menu must be current`);
    }
    record("menus and submenus expose their real implementation status", {
      surfaces: ["Project", "Resources", "Control", "Schedule"],
    });

    await page.click('[data-menu="resources"]');
    await page.waitFor(
      `document.querySelector(".cp-navigation-surface strong")?.textContent.trim() === "Resources"`,
      "resources surface after menu selection",
    );
    await page.scrollTo("#cp-resource-capacity");
    await page.waitForSelector(
      "[data-capacity-write-form]",
      "capacity write form",
    );
    await page.waitFor(
      `document.querySelectorAll("[data-capacity-profile] tbody tr").length === 2`,
      "seeded effective-dated capacity profile",
    );
    const initialCapacityRows = await page.evaluate(`(() =>
      Array.from(document.querySelectorAll("[data-capacity-profile] tbody tr")).map((row) => ({
        from: row.children[0]?.textContent.trim(),
        to: row.children[1]?.textContent.trim(),
        max_units: row.children[2]?.textContent.trim(),
        basis: row.children[3]?.textContent.trim(),
        hours: row.children[4]?.textContent.trim(),
        source: row.children[6]?.textContent.trim(),
        identity: row.children[7]?.textContent.trim(),
      }))
    )()`);
    assert(
      initialCapacityRows.length === 2 &&
        initialCapacityRows[0].max_units === "8" &&
        initialCapacityRows[0].from === "2026-09-21" &&
        initialCapacityRows[1].max_units === "12" &&
        initialCapacityRows[1].to === "Open-ended",
      `seeded capacity profile must be read from the server, got ${JSON.stringify(initialCapacityRows)}`,
    );
    assert(
      initialCapacityRows.every((row) => row.source.startsWith("preview-fixture:")),
      "capacity provenance must come from the server, not the browser",
    );

    await page.setInput("[data-capacity-resolve-resource]", "RPS-CIVIL-CREW");
    await page.setInput("[data-capacity-resolve-period]", "2026-10-16");
    await page.setSelect("[data-capacity-resolve-basis]", "week");
    await page.setInput("[data-capacity-resolve-hours]", "40");
    await page.click("[data-capacity-resolve]");
    await page.waitFor(
      `document.querySelector("[data-capacity-resolve-value]")?.getAttribute("data-capacity-resolve-value") === "60"`,
      "server-resolved weekly capacity before the change",
    );

    await page.setInput("[data-capacity-resource]", "RPS-CIVIL-CREW");
    await page.setInput("[data-capacity-max-units]", "10");
    await page.setSelect("[data-capacity-unit-basis]", "day");
    await page.setInput("[data-capacity-hours]", "8");
    await page.setInput("[data-capacity-from]", "2026-11-01");
    await page.setInput("[data-capacity-to]", "");
    const closeChecked = await page.evaluate(`(() => {
      const element = document.querySelector("[data-capacity-close]");
      if (!element) return false;
      element.checked = true;
      element.dispatchEvent(new Event("change", { bubbles: true }));
      return element.checked;
    })()`);
    assert(closeChecked, "the effective change must request closing the open segment");
    await page.click("[data-capacity-save]");
    await page.waitFor(
      `Boolean(document.querySelector("[data-capacity-write-result] [data-capacity-write-success]"))`,
      "capacity write accepted by the server",
    );
    await page.waitFor(
      `document.querySelectorAll("[data-capacity-profile] tbody tr").length === 3`,
      "three active capacity segments after the effective change",
    );
    const changedCapacityRows = await page.evaluate(`(() =>
      Array.from(document.querySelectorAll("[data-capacity-profile] tbody tr")).map((row) => ({
        from: row.children[0]?.textContent.trim(),
        to: row.children[1]?.textContent.trim(),
        max_units: row.children[2]?.textContent.trim(),
        source: row.children[6]?.textContent.trim(),
      }))
    )()`);
    assert(
      changedCapacityRows.length === 3 &&
        changedCapacityRows[0].max_units === "8" &&
        changedCapacityRows[1].max_units === "12" &&
        changedCapacityRows[1].to === "2026-10-31" &&
        changedCapacityRows[2].max_units === "10" &&
        changedCapacityRows[2].from === "2026-11-01" &&
        changedCapacityRows[2].to === "Open-ended" &&
        changedCapacityRows[2].source === "manual-entry:preview-planner",
      `append-only capacity change must close the prior open segment, got ${JSON.stringify(changedCapacityRows)}`,
    );
    const supersededNotice = await page.text("[data-capacity-superseded]");
    assert(
      (supersededNotice ?? "").includes("closed") &&
        (supersededNotice ?? "").includes("retained"),
      `the panel must report the supersession, got ${supersededNotice}`,
    );

    await page.setInput("[data-capacity-resolve-period]", "2026-11-02");
    await page.setSelect("[data-capacity-resolve-basis]", "week");
    await page.setInput("[data-capacity-resolve-hours]", "40");
    await page.click("[data-capacity-resolve]");
    await page.waitFor(
      `document.querySelector("[data-capacity-resolve-value]")?.getAttribute("data-capacity-resolve-value") === "50"`,
      "server-resolved weekly capacity after the change",
    );
    const resolvedCapacityText = await page.text(
      "[data-capacity-resolve-result]",
    );
    assert(
      (resolvedCapacityText ?? "").includes("50") &&
        (resolvedCapacityText ?? "").includes("Week") &&
        (resolvedCapacityText ?? "").includes("manual-entry:preview-planner"),
      `resolved capacity must come from the stored segment, got ${resolvedCapacityText}`,
    );

    await page.setInput("[data-capacity-resolve-period]", "2026-09-01");
    await page.click("[data-capacity-resolve]");
    await page.waitFor(
      `Boolean(document.querySelector("[data-capacity-resolve-result] .cp-capacity-error"))`,
      "out-of-range capacity resolution error",
    );
    const unresolvedCapacityText = await page.text(
      "[data-capacity-resolve-result]",
    );
    assert(
      (unresolvedCapacityText ?? "").includes("No capacity segment is effective") &&
        (unresolvedCapacityText ?? "").includes("CAPACITY_SEGMENT_NOT_EFFECTIVE"),
      `missing-capacity errors must be explicit, got ${unresolvedCapacityText}`,
    );
    assert(
      !/Oracle|Primavera|\bP6\b|https?:\/\//i.test(
        (await page.text("#cp-resource-capacity")) ?? "",
      ),
      "the capacity surface must not expose third-party branding or URLs",
    );
    await page.screenshot("08-capacity-effective-change.png");
    EVIDENCE.capacity = {
      initial_profile: initialCapacityRows,
      changed_profile: changedCapacityRows,
      resolved_before_change: "60",
      resolved_after_change: "50",
      out_of_range_error: "CAPACITY_SEGMENT_NOT_EFFECTIVE",
      supersession_reported: supersededNotice,
    };
    record(
      "effective-dated capacity is edited, closed append-only and resolved by the server",
      {
        initial_segments: initialCapacityRows.map((row) => row.max_units),
        changed_segments: changedCapacityRows.map((row) => row.max_units),
        resolved_week: "50",
      },
    );

    await page.waitForSelector("[data-schedule-settings-form]", "schedule settings form");
    await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "grid after menu renders");
    const initialHeaders = await page.evaluate(`(() =>
      Array.from(document.querySelectorAll("#cp-activity-grid thead th")).map((th) => th.textContent.replace("ƒx", "").trim())
    )()`);
    assert(initialHeaders.length === 10, "initial visible column count before layout edits");
    const hiddenTarget = await page.evaluate(`(() => {
      const button = document.querySelector('[data-p6-field-visibility]:not([data-p6-field-visible])');
      return button ? button.dataset.p6FieldVisibility : null;
    })()`);
    const addTarget = await page.evaluate(`(() => {
      const button = document.querySelector('[data-p6-field-visibility][data-p6-field-visible="true"]');
      return button ? button.dataset.p6FieldVisibility : null;
    })()`);
    assert(hiddenTarget, "a visible column must be available for hiding");
    assert(addTarget, "a hidden layout field must be available for remove/add");
    const hiddenLabel = await page.evaluate(
      `document.querySelector('[data-p6-field-rename="${hiddenTarget}"]')?.value ?? null`,
    );
    const addedLabel = await page.evaluate(
      `document.querySelector('[data-p6-field-visibility="${addTarget}"][data-p6-field-visible="true"]')?.textContent.trim() ?? null`,
    );
    assert(hiddenLabel, "hidden target must expose its persisted label");
    assert(addedLabel, "add target must expose its persisted label");

    await page.click(`[data-p6-field-visibility="${hiddenTarget}"]:not([data-p6-field-visible])`);
    await page.waitFor(
      `document.querySelectorAll("#cp-activity-grid thead th").length === ${initialHeaders.length - 1}`,
      "hide persisted column",
    );
    await page.click(`[data-p6-field-remove="${addTarget}"]`);
    await page.waitForSelector(
      `[data-p6-field-add="${addTarget}"]`,
      "removed registry field becomes addable",
    );
    await page.click(`[data-p6-field-add="${addTarget}"]`);
    await page.waitFor(
      `document.querySelectorAll("#cp-activity-grid thead th").length === ${initialHeaders.length}`,
      "add persisted column",
    );

    const orderBeforeMove = await page.evaluate(`(() =>
      Array.from(document.querySelectorAll("#cp-activity-grid thead th")).map((th) => th.textContent.replace("ƒx", "").trim())
    )()`);
    await page.click(`[data-p6-field-move="${addTarget}"][data-p6-field-direction="up"]`);
    await page.waitFor(
      `JSON.stringify(Array.from(document.querySelectorAll("#cp-activity-grid thead th")).map((th) => th.textContent.replace("ƒx", "").trim())) !== ${JSON.stringify(JSON.stringify(orderBeforeMove))}`,
      "reorder persisted column",
    );
    const orderAfterMove = await page.evaluate(`(() =>
      Array.from(document.querySelectorAll("#cp-activity-grid thead th")).map((th) => th.textContent.replace("ƒx", "").trim())
    )()`);
    const addedIndex = orderAfterMove.indexOf(addedLabel);
    assert(
      addedIndex >= 0 && addedIndex !== orderBeforeMove.indexOf(addedLabel),
      "reordered column must move in the persisted order",
    );

    const widthBefore = await page.evaluate(`(() => {
      const ths = Array.from(document.querySelectorAll("#cp-activity-grid thead th"));
      const index = ths.findIndex((th) => th.textContent.replace("ƒx", "").trim() === ${JSON.stringify(addedLabel)});
      return index >= 0 ? Number.parseFloat(ths[index].style.width) : null;
    })()`);
    assert(widthBefore > 0, "added column width must be readable");
    await page.click(`[data-p6-field-width="${addTarget}"][data-p6-field-width-delta="increase"]`);
    await page.waitFor(
      `(() => {
        const ths = Array.from(document.querySelectorAll("#cp-activity-grid thead th"));
        const index = ths.findIndex((th) => th.textContent.replace("ƒx", "").trim() === ${JSON.stringify(addedLabel)});
        return index >= 0 && Number.parseFloat(ths[index].style.width) > ${Number(widthBefore)};
      })()`,
      "increase persisted column width",
    );
    const widthAfter = await page.evaluate(`(() => {
      const ths = Array.from(document.querySelectorAll("#cp-activity-grid thead th"));
      const index = ths.findIndex((th) => th.textContent.replace("ƒx", "").trim() === ${JSON.stringify(addedLabel)});
      return index >= 0 ? Number.parseFloat(ths[index].style.width) : null;
    })()`);

    await page.click(`[data-p6-field-pin="${addTarget}"]`);
    await page.waitFor(
      `(() => {
        const ths = Array.from(document.querySelectorAll("#cp-activity-grid thead th"));
        const index = ths.findIndex((th) => th.textContent.replace("ƒx", "").trim() === ${JSON.stringify(addedLabel)});
        return index >= 0 && ths[index].getAttribute("data-column-pinned") === "true";
      })()`,
      "pin persisted column",
    );
    await page.click(`[data-p6-field-freeze="${addTarget}"]`);
    await page.waitFor(
      `(() => {
        const ths = Array.from(document.querySelectorAll("#cp-activity-grid thead th"));
        const index = ths.findIndex((th) => th.textContent.replace("ƒx", "").trim() === ${JSON.stringify(addedLabel)});
        return index >= 0 && ths[index].getAttribute("data-column-frozen") === "true";
      })()`,
      "freeze persisted column",
    );
    await page.scrollTo("#cp-activity-grid");
    await page.screenshot("04-column-operations.png");
    record("column hide/remove/add/reorder/width/pin/freeze are persisted by the layout API", {
      hidden_field: hiddenTarget,
      added_field: addTarget,
      order_after_move: orderAfterMove,
      width_before: widthBefore,
      width_after: widthAfter,
    });

    await page.reload(".cp-workspace", "reload reopens the same project");
    await page.waitFor(
      `document.querySelectorAll("#cp-activity-grid thead th").length === ${initialHeaders.length}`,
      "persisted column count after reload",
    );
    const orderAfterReload = await page.evaluate(`(() =>
      Array.from(document.querySelectorAll("#cp-activity-grid thead th")).map((th) => th.textContent.replace("ƒx", "").trim())
    )()`);
    assert(
      JSON.stringify(orderAfterReload) === JSON.stringify(orderAfterMove),
      "column order must survive a full browser reload",
    );
    const addedHeader = addedLabel;
    assert(
      orderAfterReload.indexOf(addedHeader) === orderAfterMove.indexOf(addedHeader),
      "added column position must survive reload",
    );
    const addedPresentation = await page.evaluate(`(() => {
      const ths = Array.from(document.querySelectorAll("#cp-activity-grid thead th"));
      const th = ths.find((item) => item.textContent.replace("ƒx", "").trim() === ${JSON.stringify(addedHeader)});
      return th ? {
        width: Number.parseFloat(th.style.width),
        pinned: th.getAttribute("data-column-pinned"),
        frozen: th.getAttribute("data-column-frozen"),
      } : null;
    })()`);
    assert(addedPresentation?.pinned === "true", "pinned state must survive reload");
    assert(addedPresentation?.frozen === "true", "frozen state must survive reload");
    assert(addedPresentation.width === widthAfter, "width must survive reload");
    assert(
      !orderAfterReload.includes(hiddenLabel),
      "hidden column must remain hidden after reload",
    );
    EVIDENCE.persistence.layout = {
      hidden_field: hiddenTarget,
      hidden_label: hiddenLabel,
      added_field: addTarget,
      added_label: addedLabel,
      order: orderAfterReload,
      width: addedPresentation.width,
      pinned: addedPresentation.pinned,
      frozen: addedPresentation.frozen,
      reload_verified: true,
    };
    record("layout survives a full reload through the real API and SQLite", {
      order: orderAfterReload,
      width: addedPresentation.width,
      pinned: addedPresentation.pinned,
      frozen: addedPresentation.frozen,
    });

    const layoutBeforeUndo = await readLayoutFromPage(page);
    assert(layoutBeforeUndo.status === 200, "layout must be readable before undo");
    const historyBeforeUndo = await readLayoutHistoryFromPage(page);
    assert(historyBeforeUndo.status === 200, "layout history endpoint must be readable");
    assert(
      historyBeforeUndo.body?.kind === "layout_definition_history",
      "layout history must use the versioned history envelope",
    );
    assert(
      historyBeforeUndo.body?.revisions?.[0]?.revision === layoutBeforeUndo.body.revision,
      "history must start with the current revision",
    );

    await page.click(`[data-p6-field-remove="${addTarget}"]`);
    await page.waitFor(
      `document.querySelectorAll("#cp-activity-grid thead th").length === ${initialHeaders.length - 1}`,
      "remove column before undo",
    );

    await page.click("[data-p6-layout-undo]");
    await page.waitFor(
      `document.querySelectorAll("#cp-activity-grid thead th").length === ${initialHeaders.length}`,
      "undo restores removed column",
    );
    const undoNotice = await page.text(".cp-p6-history-notice");
    assert(
      typeof undoNotice === "string" && /undone|بازگردانی/.test(undoNotice),
      "undo must report its outcome in the active locale",
    );
    const layoutAfterUndo = await readLayoutFromPage(page);
    assert(layoutAfterUndo.status === 200, "layout must be readable after undo");
    assert(
      layoutAfterUndo.body.revision > layoutBeforeUndo.body.revision,
      "undo must append a new revision instead of rewriting history",
    );
    assert(
      layoutAfterUndo.body.columns.some((column) => column.field_id === addTarget),
      "undo must persist the restored column set",
    );

    await page.click("[data-p6-layout-redo]");
    await page.waitFor(
      `document.querySelectorAll("#cp-activity-grid thead th").length === ${initialHeaders.length - 1}`,
      "redo reapplies the removed column",
    );
    const layoutAfterRedo = await readLayoutFromPage(page);
    assert(
      layoutAfterRedo.body.revision > layoutAfterUndo.body.revision,
      "redo must append a newer revision",
    );
    assert(
      !layoutAfterRedo.body.columns.some((column) => column.field_id === addTarget),
      "redo must persist the reapplied column set",
    );
    const historyAfterRedo = await readLayoutHistoryFromPage(page);
    const historyRevisions = (historyAfterRedo.body?.revisions ?? []).map((revision) => revision.revision);
    assert(
      historyRevisions[0] === layoutAfterRedo.body.revision &&
        historyRevisions.every((revision, index) => index === 0 || revision < historyRevisions[index - 1]),
      "layout history must remain append-only and newest-first",
    );
    assert(
      historyRevisions.length >= 3,
      "undo/redo must preserve the prior revisions",
    );
    await page.screenshot("04b-layout-undo-redo.png");
    record("layout undo/redo appends revisions and preserves prior history", {
      revision_before_undo: layoutBeforeUndo.body.revision,
      revision_after_undo: layoutAfterUndo.body.revision,
      revision_after_redo: layoutAfterRedo.body.revision,
      history_revisions: historyRevisions.slice(0, 5),
      restored_field: addTarget,
    });

    const restoreRevision = layoutAfterUndo.body.revision;
    await page.waitFor(
      `(() => {
        const select = document.querySelector("[data-p6-layout-revision-select]");
        return Boolean(select) && Array.from(select.options).some(
          (option) => option.value === ${JSON.stringify(String(restoreRevision))},
        );
      })()`,
      "older layout revision is offered for restore",
    );
    const restoreSelectValues = await page.evaluate(`(() => {
      const select = document.querySelector("[data-p6-layout-revision-select]");
      return select ? Array.from(select.options).map((option) => option.value) : [];
    })()`);
    assert(
      Array.isArray(restoreSelectValues)
        && restoreSelectValues.includes(String(restoreRevision))
        && !restoreSelectValues.includes(String(layoutAfterRedo.body.revision)),
      "restore must offer only older revisions, never the current head",
    );
    await page.evaluate(`(() => {
      const select = document.querySelector("[data-p6-layout-revision-select]");
      if (!select) return false;
      select.value = ${JSON.stringify(String(restoreRevision))};
      return select.value === ${JSON.stringify(String(restoreRevision))};
    })()`);
    await page.click("[data-p6-layout-restore]");
    await page.waitFor(
      `document.querySelectorAll("#cp-activity-grid thead th").length === ${initialHeaders.length}`,
      "restore reapplies the selected older revision",
    );
    const restoreNotice = await page.text(".cp-p6-history-notice");
    assert(
      typeof restoreNotice === "string" && /restored|بازگردانی نسخه/.test(restoreNotice),
      "restore must report its outcome in the active locale",
    );
    const layoutAfterRestore = await readLayoutFromPage(page);
    assert(
      layoutAfterRestore.body.revision > layoutAfterRedo.body.revision,
      "restore must append a new revision instead of rewriting the old one",
    );
    assert(
      layoutAfterRestore.body.columns.some((column) => column.field_id === addTarget),
      "restore must persist the selected revision's column set",
    );
    const historyAfterRestore = await readLayoutHistoryFromPage(page);
    const restoreHistoryRevisions = (historyAfterRestore.body?.revisions ?? []).map((revision) => revision.revision);
    assert(
      restoreHistoryRevisions[0] === layoutAfterRestore.body.revision
        && restoreHistoryRevisions.includes(restoreRevision)
        && restoreHistoryRevisions.length >= 4
        && restoreHistoryRevisions.every((revision, index) => index === 0 || revision < restoreHistoryRevisions[index - 1]),
      "restore must keep the append-only history and preserve the selected revision",
    );
    await page.screenshot("04c-layout-restore.png");
    record("layout restore reapplies a selected older revision as a new revision", {
      restored_from_revision: restoreRevision,
      revision_after_restore: layoutAfterRestore.body.revision,
      history_revisions: restoreHistoryRevisions.slice(0, 6),
      restored_field: addTarget,
    });

    // A competing writer publishes the next revision while this page still
    // holds the previous head. The stale in-page edit must fail closed, the
    // page must reload the authoritative head, and the racing writer's data
    // must survive untouched.
    const conflictBase = await readLayoutFromPage(page);
    assert(conflictBase.status === 200, "layout must be readable before the conflict race");
    const externalColumns = conflictBase.body.columns.map((column) =>
      column.field_id === addTarget ? { ...column, width: 333 } : column);
    const externalWrite = await writeLayoutFromPage(
      page,
      conflictBase.body.revision + 1,
      externalColumns,
      conflictBase.body.metadata ?? {},
    );
    assert(
      externalWrite.status === 200,
      `competing writer must publish the next revision, got ${externalWrite.status}`,
    );

    await page.click(`[data-p6-field-remove="${addTarget}"]`);
    await page.waitFor(
      `(() => {
        const notice = document.querySelector(".cp-p6-history-notice");
        return Boolean(notice) && /Another session changed|نشست دیگری/.test(notice.textContent || "");
      })()`,
      "stale layout edit reports the conflict in the active locale",
    );
    const conflictNotice = await page.text(".cp-p6-history-notice");
    assert(
      typeof conflictNotice === "string"
        && /Another session changed this layout|نشست دیگری این چیدمان/.test(conflictNotice),
      "conflict must surface the localized stale-base message",
    );
    await page.waitFor(
      `(() => {
        const ths = Array.from(document.querySelectorAll("#cp-activity-grid thead th"));
        const target = ths.find((th) => th.dataset.columnId === ${JSON.stringify(addTarget)});
        return ths.length === ${initialHeaders.length}
          && Boolean(target) && Number.parseFloat(target.style.width) === 333;
      })()`,
      "conflict reloads the authoritative head through the layout API",
    );
    const serverHeadAfterConflict = await readLayoutFromPage(page);
    assert(
      serverHeadAfterConflict.body.revision === conflictBase.body.revision + 1,
      "the failed stale write must not append a revision",
    );
    assert(
      serverHeadAfterConflict.body.columns.some(
        (column) => column.field_id === addTarget && column.width === 333,
      ),
      "the competing writer's column presentation must survive",
    );
    const historyAfterConflict = await readLayoutHistoryFromPage(page);
    const conflictHistoryRevisions = (historyAfterConflict.body?.revisions ?? [])
      .map((revision) => revision.revision);
    assert(
      conflictHistoryRevisions.length === restoreHistoryRevisions.length + 1
        && conflictHistoryRevisions[0] === conflictBase.body.revision + 1,
      "a lost race must preserve history and append nothing",
    );
    await page.screenshot("04d-layout-conflict.png");
    record("stale layout write fails closed, reloads the head and keeps the competing revision", {
      stale_base_revision: conflictBase.body.revision,
      authoritative_head: serverHeadAfterConflict.body.revision,
      localized_conflict_shown: true,
      competing_width: 333,
    });

    // A second race advances the head twice, so the next stale edit is a
    // revision gap (REVISION_CONFLICT) rather than a same-revision clash
    // (IMMUTABLE_LAYOUT_REVISION). Both Web recovery branches must reload.
    await page.click(`[data-p6-field-width="${addTarget}"][data-p6-field-width-delta="decrease"]`);
    await page.waitFor(
      `!document.querySelector(".cp-p6-history-notice")`,
      "a successful layout save clears the previous conflict notice",
    );
    const gapBase = await readLayoutFromPage(page);
    assert(
      gapBase.body.revision > conflictBase.body.revision,
      "the successful recovery save must append a revision",
    );
    for (const offset of [1, 2]) {
      const append = await writeLayoutFromPage(
        page,
        gapBase.body.revision + offset,
        gapBase.body.columns,
        gapBase.body.metadata ?? {},
      );
      assert(
        append.status === 200,
        `competing writer must append gap revision ${offset}, got ${append.status}`,
      );
    }

    await page.click(`[data-p6-field-remove="${addTarget}"]`);
    await page.waitFor(
      `(() => {
        const notice = document.querySelector(".cp-p6-history-notice");
        return Boolean(notice) && /Another session changed|نشست دیگری/.test(notice.textContent || "");
      })()`,
      "stale edit behind a revision gap reports the conflict",
    );
    await page.waitFor(
      `(() => {
        const ths = Array.from(document.querySelectorAll("#cp-activity-grid thead th"));
        const target = ths.find((th) => th.dataset.columnId === ${JSON.stringify(addTarget)});
        return ths.length === ${initialHeaders.length}
          && Boolean(target) && Number.parseFloat(target.style.width) === 313;
      })()`,
      "gap conflict reloads the newest authoritative head",
    );
    const headAfterGap = await readLayoutFromPage(page);
    assert(
      headAfterGap.body.revision === gapBase.body.revision + 2,
      "the stale gap write must not append a revision",
    );
    const historyAfterGap = await readLayoutHistoryFromPage(page);
    const gapHistoryRevisions = (historyAfterGap.body?.revisions ?? []).map((revision) => revision.revision);
    assert(
      gapHistoryRevisions.length === conflictHistoryRevisions.length + 3
        && gapHistoryRevisions[0] === headAfterGap.body.revision,
      "the recovery save and both competing revisions must be the only appends",
    );
    await page.screenshot("04e-layout-conflict-gap.png");
    record("stale layout write behind a revision gap reloads the newest head and appends nothing", {
      stale_base_revision: gapBase.body.revision,
      authoritative_head: headAfterGap.body.revision,
      localized_conflict_shown: true,
    });

    await page.click(`[data-p6-field-remove="${addTarget}"]`);
    await page.waitFor(
      `document.querySelectorAll("#cp-activity-grid thead th").length === ${initialHeaders.length - 1}`,
      "remove restored column before durable undo",
    );

    await page.reload(".cp-workspace", "reload reopens the same project before durable undo");
    await page.waitFor(
      `(() => {
        const button = document.querySelector("[data-p6-layout-undo]");
        return Boolean(button) && !button.disabled;
      })()`,
      "undo remains available after reload",
    );
    const layoutBeforeDurableUndo = await readLayoutFromPage(page);
    await page.click("[data-p6-layout-undo]");
    await page.waitFor(
      `document.querySelectorAll("#cp-activity-grid thead th").length === ${initialHeaders.length}`,
      "undo after reload restores removed column",
    );
    const layoutAfterDurableUndo = await readLayoutFromPage(page);
    assert(
      layoutAfterDurableUndo.body.revision > layoutBeforeDurableUndo.body.revision,
      "durable undo must append a revision on the server",
    );
    assert(
      layoutAfterDurableUndo.body.columns.some((column) => column.field_id === addTarget),
      "durable undo must restore the prior column set after reload",
    );
    record("layout undo remains durable across a full reload", {
      revision_before: layoutBeforeDurableUndo.body.revision,
      revision_after: layoutAfterDurableUndo.body.revision,
      restored_field: addTarget,
    });

    await page.click(`[data-p6-field-remove="${addTarget}"]`);
    await page.waitFor(
      `document.querySelectorAll("#cp-activity-grid thead th").length === ${initialHeaders.length - 1}`,
      "remove temporary column",
    );
    await page.click(`[data-p6-field-visibility="${hiddenTarget}"][data-p6-field-visible="true"]`);
    await page.waitFor(
      `document.querySelectorAll("#cp-activity-grid thead th").length === ${initialHeaders.length}`,
      "restore hidden column",
    );
    record("temporary visible column changes restored to the fixture baseline", {
      removed: addTarget,
      restored: hiddenTarget,
      note: "the removed field stays addable in the demo field registry",
    });

    await page.setInput("[data-activity-filter]", "civil");
    await page.waitFor(
      `document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]").length === 5`,
      "filter civil works",
    );
    const civilIds = await page.evaluate(`(() =>
      Array.from(document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]")).map((row) => row.dataset.activityId)
    )()`);
    assert(
      civilIds.join(",") === "A120,A130,A140,A145,A160",
      `civil filter must return the real WBS rows, got ${civilIds.join(",")}`,
    );
    await page.setInput("[data-activity-filter]", "civil completed");
    await page.waitFor(
      `document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]").length === 1`,
      "multi-token filter",
    );
    assert(
      (await page.evaluate(
        `document.querySelector("#cp-activity-grid tbody tr[data-activity-id]").dataset.activityId`,
      )) === "A120",
      "multi-token filter must match WBS and status",
    );
    await page.setInput("[data-activity-filter]", "zzzz-no-match");
    await page.waitFor(
      `document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]").length === 0`,
      "empty filter result",
    );
    assert(
      (await page.text("#cp-activity-grid tbody")).includes("No activities match"),
      "empty filter must have an explicit empty state",
    );
    await page.setInput("[data-activity-filter]", "civil");
    await page.waitFor(
      `document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]").length === 5`,
      "restore civil filter",
    );
    assert(
      (await page.count(".cp-gantt-row")) === 5,
      "Gantt must follow the filtered activity set",
    );
    await page.scrollTo("#cp-activity-grid");
    await page.screenshot("05-filter-sort.png");
    await page.setInput("[data-activity-filter]", "");
    await page.waitFor(
      `document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]").length === 14`,
      "clear activity filter",
    );

    await page.setSelect("[data-activity-sort]", "activity.id");
    await page.waitFor(
      `document.querySelector('#cp-activity-grid tbody tr[data-activity-id]')?.dataset.activityId === "A100"`,
      "sort by activity id",
    );
    await page.click("[data-activity-sort-direction]");
    await page.waitFor(
      `document.querySelector('#cp-activity-grid tbody tr[data-activity-id]')?.dataset.activityId === "A210"`,
      "descending activity id sort",
    );
    await page.setSelect("[data-activity-sort]", "activity.total_float");
    await page.waitFor(
      `document.querySelector("[data-activity-sort]").value === "activity.total_float"`,
      "sort by total float",
    );
    const floatIndex = await page.evaluate(`(() => {
      const labels = Array.from(document.querySelectorAll("#cp-activity-grid thead th")).map((th) => th.textContent.replace("ƒx", "").trim());
      return labels.findIndex((label) => /float/i.test(label));
    })()`);
    assert(floatIndex >= 0, "Total Float column must be visible");
    const ascFloats = await page.evaluate(`(() => {
      const rows = Array.from(document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]"));
      return rows.map((row) => {
        const text = row.children[${floatIndex}]?.textContent.trim() ?? "";
        const value = Number.parseFloat(text);
        return { id: row.dataset.activityId, value: Number.isFinite(value) ? value : null };
      });
    })()`);
    const numericAsc = ascFloats.filter((item) => item.value !== null).map((item) => item.value);
    assert(
      numericAsc.every((value, index) => index === 0 || numericAsc[index - 1] <= value),
      `total float ascending order expected, got ${JSON.stringify(ascFloats)}`,
    );
    assert(
      ascFloats.slice(numericAsc.length).every((item) => item.value === null),
      "missing total float values must sort last",
    );
    await page.click("[data-activity-sort-direction]");
    await page.waitFor(
      `(() => {
        const rows = Array.from(document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]"));
        const values = rows.map((row) => Number.parseFloat(row.children[${floatIndex}]?.textContent.trim() ?? "")).filter(Number.isFinite);
        return values.length < 2 || values[0] >= values[1];
      })()`,
      "descending total float sort",
    );
    const descFloats = await page.evaluate(`(() => {
      const rows = Array.from(document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]"));
      return rows.map((row) => {
        const text = row.children[${floatIndex}]?.textContent.trim() ?? "";
        const value = Number.parseFloat(text);
        return Number.isFinite(value) ? value : null;
      });
    })()`);
    const numericDesc = descFloats.filter((value) => value !== null);
    assert(
      numericDesc.every((value, index) => index === 0 || numericDesc[index - 1] >= value),
      "total float descending order",
    );
    await page.setSelect("[data-activity-sort]", "");
    await page.waitFor(
      `document.querySelector('#cp-activity-grid tbody tr[data-activity-id]')?.dataset.activityId === "A100"`,
      "reset activity sort",
    );
    record("filter and numeric sort operate on persisted activity facts", {
      civil_rows: civilIds,
      multi_token_row: "A120",
      no_match_empty_state: true,
      float_ascending: ascFloats,
      float_descending: descFloats,
    });

    await page.click('[data-menu="schedule"]');
    await page.waitForSelector("[data-schedule-settings-form]", "settings form after menu");
    const settings = await page.evaluate(`(() => {
      const form = document.querySelector("[data-schedule-settings-form]");
      const calendar = form?.querySelector('select[name="calendar_ref"]');
      const selected = calendar?.selectedOptions?.[0];
      return {
        revision: Number(form?.elements.namedItem("record_revision")?.value ?? -1),
        mode: form?.elements.namedItem("mode")?.value ?? null,
        project_start: form?.elements.namedItem("project_start")?.value ?? null,
        calendar_system: form?.elements.namedItem("calendar_system")?.value ?? null,
        priority: form?.elements.namedItem("project_leveling_priority")?.value ?? null,
        selected_calendar: selected?.textContent.trim() ?? null,
        calendar_options: calendar ? Array.from(calendar.options).map((option) => option.textContent.trim()) : [],
      };
    })()`);
    assert(settings.mode === "DATE_BASED", "fixture settings must be date based");
    assert(settings.project_start === "2026-09-21", "fixture project start must load");
    assert(settings.calendar_system === "gregorian", "fixture calendar system must load");
    assert(settings.priority === "10", "fixture leveling priority must load");
    assert(
      settings.calendar_options.some((option) => option.includes("CUBI-RPS-CAL")),
      "project calendar catalogue must include the persisted calendar",
    );
    await page.scrollTo("#cp-schedule-options");
    await page.screenshot("06-settings-calendar.png");

    await page.setSelect('select[name="calendar_system"]', "jalali");
    await page.waitFor(
      `(() => {
        const input = document.querySelector('[data-schedule-settings-form] input[name="project_start"]');
        return input?.type === "text" && input?.value === "1405/06/30";
      })()`,
      "typed Jalali project start control",
    );
    await page.setInput(
      '[data-schedule-settings-form] input[name="project_start"]',
      "1405/13/01",
    );
    await page.click('[data-schedule-settings-form] button[type="submit"]');
    await page.waitFor(
      `document.querySelector("[data-settings-status]")?.textContent.includes("INVALID_PROJECT_START")`,
      "explicit invalid Jalali date error",
    );
    const invalidJalaliSettings = await page.evaluate(
      `(async () => {
        const headers = {
          "X-Tenant-Id": ${JSON.stringify(TENANT_ID)},
          "X-Project-Id": ${JSON.stringify(PROJECT_ID)},
          "X-Project-Revision": ${JSON.stringify(String(PROJECT_REVISION))},
        };
        const response = await fetch("/api/projects/${PROJECT_ID}/p6/schedule/settings", { headers });
        return { status: response.status, body: await response.json() };
      })()`,
      { awaitPromise: true },
    );
    assert(
      invalidJalaliSettings.status === 200 &&
        invalidJalaliSettings.body.project_start === "2026-09-21",
      "an impossible Jalali date must fail closed without changing the stored Gregorian date",
    );
    // The rejected entry must not leave the previous canonical date behind in
    // the control: switching calendars must show the unresolved empty state
    // rather than silently reusing the stored value.
    await page.setSelect('select[name="calendar_system"]', "gregorian");
    await page.waitFor(
      `(() => {
        const input = document.querySelector('[data-schedule-settings-form] input[name="project_start"]');
        return input?.type === "date" && input?.value === "";
      })()`,
      "invalid Jalali entry must not resurrect the previous Gregorian date",
    );
    await page.setSelect('select[name="calendar_system"]', "jalali");
    await page.waitFor(
      `(() => {
        const input = document.querySelector('[data-schedule-settings-form] input[name="project_start"]');
        return input?.type === "text" && input?.value === "";
      })()`,
      "Jalali control stays unresolved after the invalid entry",
    );
    await page.setInput(
      '[data-schedule-settings-form] input[name="project_start"]',
      "۱۴۰۵/۰۶/۳۰",
    );
    await page.click('[data-schedule-settings-form] button[type="submit"]');
    await page.waitFor(
      `document.querySelector("[data-settings-status]")?.textContent.trim() === "Settings saved."`,
      "Jalali settings save status",
    );
    const savedJalaliSettings = await page.evaluate(
      `(async () => {
        const headers = {
          "X-Tenant-Id": ${JSON.stringify(TENANT_ID)},
          "X-Project-Id": ${JSON.stringify(PROJECT_ID)},
          "X-Project-Revision": ${JSON.stringify(String(PROJECT_REVISION))},
        };
        const response = await fetch("/api/projects/${PROJECT_ID}/p6/schedule/settings", { headers });
        return { status: response.status, body: await response.json() };
      })()`,
      { awaitPromise: true },
    );
    assert(
      savedJalaliSettings.body.project_start === "2026-09-21",
      "a typed Jalali date must persist as its canonical Gregorian date",
    );
    assert(
      savedJalaliSettings.body.project_calendar.system === "jalali",
      "the Jalali calendar system must persist with the settings",
    );
    const jalaliSavedRevision = Number(savedJalaliSettings.body.record_revision);
    await page.setSelect('select[name="calendar_system"]', "gregorian");
    await page.waitFor(
      `(() => {
        const input = document.querySelector('[data-schedule-settings-form] input[name="project_start"]');
        return input?.type === "date" && input?.value === "2026-09-21";
      })()`,
      "Gregorian date restored after the Jalali round-trip",
    );
    await page.click('[data-schedule-settings-form] button[type="submit"]');
    await page.waitFor(
      `Number(document.querySelector('[data-schedule-settings-form] input[name="record_revision"]')?.value ?? -1) > ${jalaliSavedRevision}`,
      "restored settings revision",
    );
    const restoredSystem = await page.evaluate(
      `document.querySelector('[data-schedule-settings-form] select[name="calendar_system"]')?.value`,
    );
    assert(restoredSystem === "gregorian", "the Gregorian calendar system must be restorable");
    EVIDENCE.jalali_entry = {
      rendered_from_iso: "2026-09-21 → 1405/06/30",
      invalid_input: "1405/13/01 rejected without persistence",
      persisted_iso: savedJalaliSettings.body.project_start,
      persisted_system: savedJalaliSettings.body.project_calendar.system,
      restored_system: restoredSystem,
      source: "schedule settings form over the authoritative settings API",
    };
    record("typed Jalali date entry converts to the canonical stored date and fails closed", {
      rendered_jalali: "1405/06/30",
      invalid_input_error: "INVALID_PROJECT_START",
      persisted_iso: savedJalaliSettings.body.project_start,
      restored_system: restoredSystem,
    });
    const savedRevision = await page.evaluate(
      `Number(document.querySelector('[data-schedule-settings-form] input[name="record_revision"]')?.value ?? -1)`,
    );
    assert(savedRevision > settings.revision, "settings save must persist a new revision");
    EVIDENCE.persistence.settings = {
      initial_revision: settings.revision,
      saved_revision: savedRevision,
      calendar: settings.selected_calendar,
      project_start: settings.project_start,
      calendar_system: settings.calendar_system,
    };
    record("project settings and calendar persist through the real settings API", {
      initial_revision: settings.revision,
      saved_revision: savedRevision,
      calendar: settings.selected_calendar,
    });

    await page.click("[data-run-schedule]");
    await page.waitFor(
      `document.querySelectorAll("[data-run-results] .cp-schedule-result-table tbody tr").length === 14`,
      "authoritative schedule result rows",
      60000,
    );
    const runStatus = await page.text("[data-run-status]");
    assert(runStatus === "", `schedule run status should be clear, got ${runStatus}`);
    const calculation = await page.evaluate(`(() => {
      const meta = document.querySelector(".cp-schedule-result-meta")?.textContent ?? "";
      const hash = document.querySelector(".cp-schedule-result-meta code")?.textContent.trim() ?? "";
      const rows = Array.from(document.querySelectorAll("[data-run-results] .cp-schedule-result-table tbody tr")).map((row) =>
        Array.from(row.children).map((cell) => cell.textContent.trim())
      );
      const a130 = rows.find((row) => row[0] === "A130");
      const a100 = rows.find((row) => row[0] === "A100");
      return { meta, hash, row_count: rows.length, a130, a100 };
    })()`);
    assert(calculation.hash.length >= 16, "published snapshot hash must be substantial");
    assert(calculation.a130, "A130 must be present in authoritative schedule output");
    assert(
      calculation.a130.every((value) => value.length > 0),
      "A130 authoritative schedule row must be fully populated",
    );
    const gridA130 = await page.evaluate(`(() => {
      const row = document.querySelector('#cp-activity-grid tbody tr[data-activity-id="A130"]');
      return row ? Array.from(row.children).map((cell) => cell.textContent.trim()) : null;
    })()`);
    assert(gridA130, "A130 must remain in the activity grid after calculation");
    await page.scrollTo("#cp-schedule-run");
    await page.screenshot("07-schedule-results.png");
    EVIDENCE.calculation = {
      snapshot_meta: calculation.meta,
      snapshot_hash: calculation.hash,
      row_count: calculation.row_count,
      a130: calculation.a130,
      a100: calculation.a100,
      grid_a130: gridA130,
      source: "POST snapshot + /api/v1/schedule/query (Shared Domain/Calculation Core)",
    };
    record("snapshot publication and Shared Core schedule query return real results", {
      row_count: calculation.row_count,
      hash: calculation.hash,
      a130_start: calculation.a130?.[1],
      a130_finish: calculation.a130?.[2],
    });

    await page.scrollTo("#cp-formula-editor");
    await page.setSelect(
      "#cp-formula-editor [data-formula-field]",
      "activity.total_float",
    );
    await page.setInput(
      "#cp-formula-editor [data-formula-expression]",
      "[activity.duration_percent_complete] / 100",
    );
    await page.click("#cp-formula-editor [data-formula-validate]");
    await page.waitFor(
      `Boolean(document.querySelector("#cp-formula-editor [data-formula-result] .cp-formula-valid"))`,
      "authoritative valid formula result",
    );
    const validFormula = await page.text(
      "#cp-formula-editor [data-formula-result]",
    );
    assert(
      (validFormula ?? "").includes("activity.duration_percent_complete"),
      `valid formula result must list the Shared Core dependency, got ${validFormula}`,
    );
    assert(
      (validFormula ?? "").includes("double"),
      `valid formula result must expose the authoritative result type, got ${validFormula}`,
    );
    await page.screenshot("07b-formula-valid.png");

    await page.setSelect(
      "#cp-formula-editor [data-formula-field]",
      "activity.duration_percent_complete",
    );
    await page.setInput(
      "#cp-formula-editor [data-formula-expression]",
      "[activity.duration_percent_complete] + 1",
    );
    await page.click("#cp-formula-editor [data-formula-validate]");
    await page.waitFor(
      `Boolean(document.querySelector("#cp-formula-editor [data-formula-result] .cp-formula-invalid"))`,
      "authoritative invalid formula result",
    );
    const invalidFormula = await page.text(
      "#cp-formula-editor [data-formula-result]",
    );
    assert(
      (invalidFormula ?? "").includes("FORMULA_SELF_REFERENCE"),
      `invalid formula must report the Shared Core error code, got ${invalidFormula}`,
    );
    assert(
      !(invalidFormula ?? "").includes("Result type"),
      "an invalid formula must not present an invented result type",
    );
    await page.screenshot("07c-formula-invalid.png");

    await page.setSelect(
      "#cp-formula-editor [data-formula-field]",
      "activity.total_float",
    );
    await page.setInput(
      "#cp-formula-editor [data-formula-expression]",
      "[activity.planned_duration] * 2",
    );
    await page.click("#cp-formula-editor [data-formula-validate]");
    await page.waitFor(
      `document.querySelector("#cp-formula-editor [data-formula-result]")?.textContent.includes("UNSUPPORTED_P6_FORMULA_FIELD_TYPE:duration")`,
      "unsupported duration field diagnostic",
    );
    const unsupportedFormula = await page.text(
      "#cp-formula-editor [data-formula-result]",
    );
    assert(
      !(unsupportedFormula ?? "").includes("Result type"),
      "an unsupported field must not present an invented result type",
    );
    EVIDENCE.formula = {
      registry_version: "p6-field-registry.v1",
      valid_expression: "[activity.duration_percent_complete] / 100",
      valid_context_field: "activity.total_float",
      valid_result: validFormula,
      invalid_expression: "[activity.duration_percent_complete] + 1",
      invalid_context_field: "activity.duration_percent_complete",
      invalid_result: invalidFormula,
      unsupported_expression: "[activity.planned_duration] * 2",
      unsupported_error: "UNSUPPORTED_P6_FORMULA_FIELD_TYPE:duration",
      source: "POST /api/projects/{project}/p6/formulas/{registry_version}",
    };
    record("formula editor validates expressions through the Shared Core authority", {
      valid: (validFormula ?? "").includes("Valid expression"),
      error_code: "FORMULA_SELF_REFERENCE",
      invalid_shows_type: (invalidFormula ?? "").includes("Result type"),
      unsupported_code: "UNSUPPORTED_P6_FORMULA_FIELD_TYPE:duration",
      unsupported_shows_type: (unsupportedFormula ?? "").includes("Result type"),
    });

    const interchange = await page.evaluate(
      `(async () => {
        const headers = {
          "X-Tenant-Id": ${JSON.stringify(TENANT_ID)},
          "X-Project-Id": ${JSON.stringify(PROJECT_ID)},
          "X-Project-Revision": ${JSON.stringify(String(PROJECT_REVISION))},
        };
        const exportResponse = await fetch("/api/projects/${PROJECT_ID}/p6/interchange/PRIMAVERA_XML/export", {
          method: "POST",
          headers: { "Content-Type": "application/json", ...headers },
          body: JSON.stringify({
            values: [{ "activity.id": "A130", "activity.name": "Earthworks" }],
            extensions: [{ "p6.primavera.xml.object": "Activity" }],
          }),
        });
        const exported = await exportResponse.json();
        const importResponse = await fetch("/api/projects/${PROJECT_ID}/p6/interchange/PRIMAVERA_XML/import", {
          method: "POST",
          headers: { "Content-Type": "application/xml", ...headers },
          body: exported.document?.data ?? "",
        });
        return {
          export_status: exportResponse.status,
          exported,
          import_status: importResponse.status,
          imported: await importResponse.json(),
        };
      })()`,
      { awaitPromise: true },
    );
    assert(interchange.export_status === 200, "interchange export must succeed");
    assert(
      interchange.exported.format === "PRIMAVERA_XML",
      "export must use the configured provider format",
    );
    assert(
      interchange.exported.document?.encoding === "utf-8",
      "exported document must be UTF-8 text",
    );
    const exportedXml = interchange.exported.document?.data ?? "";
    assert(
      exportedXml.includes("<Id>A130</Id>") &&
        exportedXml.includes("<Name>Earthworks</Name>"),
      "exported XML must carry the mapped activity values",
    );
    assert(interchange.import_status === 200, "interchange import must succeed");
    const importedRow = interchange.imported.rows?.[0];
    assert(importedRow, "import must return the mapped row");
    assert(
      importedRow.values["activity.id"] === "A130" &&
        importedRow.values["activity.name"] === "Earthworks",
      "import must map provider fields back to canonical activity fields",
    );
    assert(
      importedRow.extensions["p6.primavera.xml.object"] === "Activity",
      "provider object identity must be preserved",
    );
    assert(
      Array.isArray(importedRow.warnings) && importedRow.warnings.length === 0,
      "round-trip row must not need loss warnings",
    );
    EVIDENCE.interchange = {
      format: interchange.exported.format,
      export_status: interchange.export_status,
      import_status: interchange.import_status,
      exported_xml: exportedXml,
      imported_row: importedRow,
    };
    record("provider XML interchange round-trip uses persisted mappings and the real codec", {
      format: interchange.exported.format,
      export_status: interchange.export_status,
      import_status: interchange.import_status,
      canonical_values: importedRow.values,
    });

    await page.click('[data-menu="project"]');
    await page.waitFor(
      `document.querySelector("[data-menu='project']")?.getAttribute("aria-current") === "page"`,
      "project surface for interchange",
    );
    await page.scrollTo("#cp-interchange");
    await page.waitForSelector("[data-interchange-export]", "interchange export control");
    const interchangeActivityCount = await page.text(
      "[data-interchange-activity-count]",
    );
    assert(
      interchangeActivityCount === "14 loaded activities",
      `interchange panel must count the loaded activities, got ${interchangeActivityCount}`,
    );
    await page.click("[data-interchange-export]");
    await page.waitFor(
      `Boolean(document.querySelector("[data-interchange-export-result] .cp-interchange-success [data-interchange-download]"))`,
      "server-generated interchange export",
    );
    const interchangeExportStatus = await page.text(
      "[data-interchange-export-status]",
    );
    assert(
      (interchangeExportStatus ?? "").includes("server generated"),
      `export must report the server document, got ${interchangeExportStatus}`,
    );
    const exportedUiXml = await page.evaluate(
      `(async () => {
        const link = document.querySelector("[data-interchange-download]");
        if (!link) return null;
        const response = await fetch(link.href);
        return await response.text();
      })()`,
      { awaitPromise: true },
    );
    assert(exportedUiXml, "the download link must expose the exported document");
    assert(
      (exportedUiXml.match(/<Activity>/g) ?? []).length === 14,
      "the exported document must carry every loaded activity",
    );
    assert(
      exportedUiXml.includes("<Id>A100</Id>") &&
        exportedUiXml.includes("<Name>Project kickoff</Name>"),
      "the exported document must carry canonical activity values",
    );
    assert(
      !(await page.text("#cp-interchange")).includes("Oracle") &&
        !(await page.text("#cp-interchange")).includes("Primavera"),
      "the interchange surface must not expose third-party branding",
    );
    await page.screenshot("07d-interchange-export.png");

    await page.setInput("[data-interchange-input]", exportedUiXml);
    await page.click("[data-interchange-import]");
    await page.waitFor(
      `document.querySelectorAll("[data-interchange-import-result] tbody tr").length === 14`,
      "round-trip mapped import rows",
    );
    const interchangeImportStatus = await page.text(
      "[data-interchange-import-status]",
    );
    assert(
      (interchangeImportStatus ?? "").includes("14 rows mapped"),
      `import must report all mapped rows, got ${interchangeImportStatus}`,
    );
    const firstImportedRow = await page.text(
      "[data-interchange-import-result] tbody tr:first-child",
    );
    assert(
      (firstImportedRow ?? "").includes("A100") &&
        (firstImportedRow ?? "").includes("Project kickoff"),
      `the first mapped row must expose canonical values, got ${firstImportedRow}`,
    );
    await page.screenshot("07e-interchange-import.png");

    await page.setInput("[data-interchange-input]", "<not-a-provider-document>");
    await page.click("[data-interchange-import]");
    await page.waitFor(
      `Boolean(document.querySelector("[data-interchange-import-result] .cp-interchange-error"))`,
      "explicit invalid document error",
    );
    const invalidInterchange = await page.text(
      "[data-interchange-import-result]",
    );
    assert(
      (invalidInterchange ?? "").includes("INVALID_XML"),
      `invalid documents must surface the server code, got ${invalidInterchange}`,
    );
    assert(
      (await page.count("[data-interchange-import-result] tbody tr")) === 0,
      "an invalid document must not display fabricated rows",
    );
    await page.screenshot("07f-interchange-invalid.png");
    EVIDENCE.interchange_ui = {
      activity_count: interchangeActivityCount,
      export_status: interchangeExportStatus,
      download_rows: (exportedUiXml.match(/<Activity>/g) ?? []).length,
      import_status: interchangeImportStatus,
      first_imported_row: firstImportedRow,
      invalid_document: invalidInterchange,
      source: "project import/export panel over the authenticated API",
    };
    record("project panel exports and re-imports every activity through the server codec", {
      activity_count: interchangeActivityCount,
      export_status: interchangeExportStatus,
      import_status: interchangeImportStatus,
      invalid_document_row_count: await page.count(
        "[data-interchange-import-result] tbody tr",
      ),
    });

    await page.click('[data-menu="schedule"]');
    await page.waitFor(
      `document.querySelector("[data-menu='schedule']")?.getAttribute("aria-current") === "page"`,
      "schedule surface after interchange",
    );

    const capacity = await page.evaluate(
      `(async () => {
        const headers = {
          "X-Tenant-Id": ${JSON.stringify(TENANT_ID)},
          "X-Project-Id": ${JSON.stringify(PROJECT_ID)},
          "X-Project-Revision": ${JSON.stringify(String(PROJECT_REVISION))},
        };
        const listResponse = await fetch("/api/projects/${PROJECT_ID}/p6/resource-capacities", {
          headers,
        });
        const listed = await listResponse.json();
        const profileResponse = await fetch(
          "/api/projects/${PROJECT_ID}/p6/resource-capacities/RPS-CIVIL-CREW",
          { headers },
        );
        const profile = await profileResponse.json();
        const missingResponse = await fetch(
          "/api/projects/${PROJECT_ID}/p6/resource-capacities/UNREGISTERED-RESOURCE",
          { headers },
        );
        const missing = await missingResponse.json();
        return {
          list_status: listResponse.status,
          listed,
          profile_status: profileResponse.status,
          profile,
          missing_status: missingResponse.status,
          missing,
        };
      })()`,
      { awaitPromise: true },
    );
    assert(capacity.list_status === 200, "capacity list must be readable");
    assert(
      capacity.listed.contract_version === "p6-resource-capacity-read-api.v1",
      "capacity list must use the typed read contract",
    );
    assert(
      capacity.listed.capacities?.length === 3,
      "RPS-CIVIL-CREW must expose the two fixture ceilings and the appended effective change",
    );
    const [earlyCeiling, lateCeiling, latestCeiling] = capacity.listed.capacities;
    assert(
      earlyCeiling.capacity.max_units === "8" &&
        earlyCeiling.capacity.unit_basis === "day" &&
        earlyCeiling.capacity.hours_per_time_period === "8" &&
        earlyCeiling.capacity.effective_to === "2026-10-14",
      "first ceiling must be an explicit 8/day segment with an end date",
    );
    assert(
      lateCeiling.capacity.max_units === "12" &&
        lateCeiling.capacity.effective_from === "2026-10-15" &&
        lateCeiling.capacity.effective_to === "2026-10-31",
      "the prior open ceiling must be closed the day before the new segment",
    );
    assert(
      latestCeiling.capacity.max_units === "10" &&
        latestCeiling.capacity.effective_from === "2026-11-01" &&
        latestCeiling.capacity.effective_to === null &&
        latestCeiling.capacity.source === "manual-entry:preview-planner",
      "the appended change must be an authenticated 10/day open-ended segment",
    );
    assert(
      new Set(
        capacity.listed.capacities.map((item) => item.capacity.identity),
      ).size === 3 &&
        latestCeiling.capacity.identity.length === 64,
      "each ceiling segment must carry a distinct content identity",
    );
    assert(
      capacity.profile_status === 200 &&
        capacity.profile.status === "REGISTERED" &&
        capacity.profile.segments?.length === 3,
      "capacity profile must resolve the registered effective-dated profile",
    );
    assert(
      capacity.missing_status === 404 &&
        capacity.missing.code === "RESOURCE_CAPACITY_NOT_REGISTERED",
      "an unregistered ceiling must fail closed instead of assuming a value",
    );
    EVIDENCE.resource_capacity = {
      contract_version: capacity.listed.contract_version,
      list_status: capacity.list_status,
      profile_status: capacity.profile_status,
      segments: capacity.profile.segments,
      missing_status: capacity.missing_status,
      missing_code: capacity.missing.code,
      source: "GET /p6/resource-capacities over persisted typed capacity segments",
    };
    record("typed resource Max Units/Time read resolves effective-dated registered ceilings", {
      list_status: capacity.list_status,
      profile_status: capacity.profile_status,
      segment_count: capacity.profile.segments?.length,
      first_max_units: earlyCeiling.capacity.max_units,
      second_max_units: lateCeiling.capacity.max_units,
      latest_max_units: latestCeiling.capacity.max_units,
      unregistered_status: capacity.missing_status,
    });

    await page.click("[data-language-toggle]");
    await page.waitFor(
      `document.querySelector(".cp-workspace")?.getAttribute("dir") === "rtl"`,
      "Persian RTL workspace",
    );
    const faMenu = await page.evaluate(
      `Array.from(document.querySelectorAll(".cp-menu button[data-menu]")).find((button) => button.dataset.menu === "schedule")?.textContent.trim()`,
    );
    assert(faMenu === "زمان‌بندی", "Persian menu label must render");
    const faFilter = await page.evaluate(
      `document.querySelector("[data-activity-filter]")?.getAttribute("placeholder")`,
    );
    assert(faFilter && /[\u0600-\u06FF]/.test(faFilter), "Persian filter placeholder must render");
    await page.waitFor(
      `document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]").length === 14`,
      "Persian workspace keeps activity rows",
    );
    await page.scrollTo("#cp-activity-grid");
    await page.screenshot("08-persian-rtl.png");
    record("Persian/RTL surface renders persisted project data", {
      schedule_label: faMenu,
      filter_placeholder: faFilter,
    });
    await page.click("[data-language-toggle]");
    await page.waitFor(
      `document.querySelector(".cp-workspace")?.getAttribute("dir") === "ltr"`,
      "English LTR workspace",
    );

    await page.cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1024,
      height: 768,
      deviceScaleFactor: 1,
      mobile: false,
    });
    await sleep(300);
    const compact = await page.evaluate(`(() => ({
      innerWidth: window.innerWidth,
      scrollWidth: document.documentElement.scrollWidth,
      menuWidth: document.querySelector(".cp-menu")?.getBoundingClientRect().width ?? 0,
      menuButtons: Array.from(document.querySelectorAll(".cp-menu button[data-menu]")).map((button) => {
        const rect = button.getBoundingClientRect();
        return { label: button.textContent.trim(), left: rect.left, right: rect.right, width: rect.width };
      }),
    }))()`);
    assert(compact.menuWidth > 0, "menu must be visible at 1024px");
    assert(
      compact.menuButtons.every((button) => button.width > 0 && button.left >= -1 && button.right <= compact.innerWidth + 1),
      `menu buttons must stay inside the 1024px viewport: ${JSON.stringify(compact.menuButtons)}`,
    );
    await page.evaluate("window.scrollTo(0, 0)");
    await page.screenshot("09-compact-1024.png");
    record("compact 1024px desktop layout keeps navigation usable", compact);
    await page.cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1440,
      height: 900,
      deviceScaleFactor: 1,
      mobile: false,
    });

    await page.reload(".cp-workspace", "final reload reopens the same project");
    await page.waitFor(
      `document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]").length === 14`,
      "persisted rows after final reload",
    );
    const finalHeaders = await page.evaluate(`(() =>
      Array.from(document.querySelectorAll("#cp-activity-grid thead th")).map((th) => th.textContent.replace("ƒx", "").trim())
    )()`);
    assert(
      finalHeaders.length === initialHeaders.length,
      "baseline column set must be restored after the layout round-trip",
    );
    assert(
      finalHeaders.includes(hiddenLabel) && !finalHeaders.includes(addedLabel),
      "final reload must show the restored baseline columns",
    );
    await page.waitForSelector("[data-schedule-settings-form]", "settings after final reload");
    const finalSettings = await page.evaluate(`(() => {
      const form = document.querySelector("[data-schedule-settings-form]");
      const calendar = form?.querySelector('select[name="calendar_ref"]');
      return {
        revision: Number(form?.elements.namedItem("record_revision")?.value ?? -1),
        calendar: calendar?.selectedOptions?.[0]?.textContent.trim() ?? null,
        project_start: form?.elements.namedItem("project_start")?.value ?? null,
      };
    })()`);
    assert(
      finalSettings.revision >= savedRevision,
      "saved settings revision must survive reload",
    );
    assert(
      finalSettings.calendar?.includes("CUBI-RPS-CAL"),
      "saved calendar must survive reload",
    );
    await page.click('[data-menu="resources"]');
    await page.waitFor(
      `document.querySelector(".cp-navigation-surface strong")?.textContent.trim() === "Resources"`,
      "resources surface after final reload",
    );
    await page.waitFor(
      `document.querySelectorAll("[data-capacity-profile] tbody tr").length === 3`,
      "persisted effective-dated capacity after final reload",
    );
    const finalCapacityRows = await page.evaluate(`(() =>
      Array.from(document.querySelectorAll("[data-capacity-profile] tbody tr")).map((row) => ({
        from: row.children[0]?.textContent.trim(),
        to: row.children[1]?.textContent.trim(),
        max_units: row.children[2]?.textContent.trim(),
        source: row.children[6]?.textContent.trim(),
      }))
    )()`);
    assert(
      finalCapacityRows.length === 3 &&
        finalCapacityRows[2].max_units === "10" &&
        finalCapacityRows[2].from === "2026-11-01" &&
        finalCapacityRows[2].to === "Open-ended" &&
        finalCapacityRows[2].source === "manual-entry:preview-planner",
      `effective-dated capacity must survive a full reload, got ${JSON.stringify(finalCapacityRows)}`,
    );
    await page.setInput("[data-capacity-resolve-period]", "2026-11-02");
    await page.setSelect("[data-capacity-resolve-basis]", "week");
    await page.setInput("[data-capacity-resolve-hours]", "40");
    await page.click("[data-capacity-resolve]");
    await page.waitFor(
      `document.querySelector("[data-capacity-resolve-value]")?.getAttribute("data-capacity-resolve-value") === "50"`,
      "persisted capacity resolution after final reload",
    );
    await page.screenshot("10a-capacity-persisted.png");
    EVIDENCE.persistence.capacity = {
      segments: finalCapacityRows.map((row) => row.max_units),
      resolved_week: "50",
      reload_verified: true,
    };
    record("effective-dated capacity survives a full reload and still resolves on the server", {
      segments: finalCapacityRows.map((row) => row.max_units),
    });
    await page.scrollTo("#cp-activity-grid");
    await page.screenshot("10-reload-persisted.png");
    record("saved settings, calendar and layout survive a full reload", finalSettings);

    await page.click("#cubi-preview-banner button");
    await page.waitForSelector('form[action="/preview/login"]', "logout returns to login");
    await page.navigate(
      `${baseUrl}/app`,
      'form[action="/preview/login"]',
      "guarded /app",
      `${baseUrl}/preview/login`,
    );
    assert(
      (await page.evaluate("location.pathname")) === "/preview/login",
      "unauthenticated /app must land on the preview login",
    );
    record("session logout and /app guard work in the browser", {
      path: await page.evaluate("location.pathname"),
    });

    await page.click('button[name="role"][value="viewer"]');
    await page.waitForSelector(".cp-project-selection", "viewer project selection");
    await page.click(`button[data-project-id="${PROJECT_ID}"]`);
    await page.waitForSelector(".cp-workspace", "viewer workspace");
    await page.waitFor(
      `document.querySelector("#cubi-preview-banner")?.textContent.includes("preview-viewer")`,
      "viewer banner identity",
    );
    await page.waitForSelector("[data-run-schedule]", "viewer run control");
    const sessionViewer = await page.evaluate(
      `fetch("/api/session").then((response) => response.json())`,
      { awaitPromise: true },
    );
    assert(
      Array.isArray(sessionViewer.roles) && sessionViewer.roles.includes("viewer"),
      "viewer session roles must come from the server",
    );

    const layoutGet = await page.evaluate(`(async () => {
      const response = await fetch("/api/projects/${PROJECT_ID}/p6/layouts/project/activity", {
        headers: {
          "X-Tenant-Id": ${JSON.stringify(TENANT_ID)},
          "X-Project-Id": ${JSON.stringify(PROJECT_ID)},
          "X-Project-Revision": ${JSON.stringify(String(PROJECT_REVISION))},
        },
      });
      const body = await response.json().catch(() => null);
      return { status: response.status, body };
    })()`, { awaitPromise: true });
    assert(layoutGet.status === 200, "viewer must be able to read the layout");
    const viewerLayoutPost = await page.evaluate(`(async () => {
      const response = await fetch("/api/projects/${PROJECT_ID}/p6/layouts/project/activity", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Tenant-Id": ${JSON.stringify(TENANT_ID)},
          "X-Project-Id": ${JSON.stringify(PROJECT_ID)},
          "X-Project-Revision": ${JSON.stringify(String(PROJECT_REVISION))},
        },
        body: JSON.stringify({
          revision: ${Number(layoutGet.body.revision) + 1},
          columns: ${JSON.stringify(layoutGet.body.columns)},
          metadata: {},
        }),
      });
      const body = await response.json().catch(() => null);
      return { status: response.status, body };
    })()`, { awaitPromise: true });
    assert(viewerLayoutPost.status === 403, "viewer layout write must be denied with 403");
    const viewerSnapshotPost = await page.evaluate(`(async () => {
      const response = await fetch("/api/projects/${PROJECT_ID}/p6/schedule/snapshots", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Tenant-Id": ${JSON.stringify(TENANT_ID)},
          "X-Project-Id": ${JSON.stringify(PROJECT_ID)},
          "X-Project-Revision": ${JSON.stringify(String(PROJECT_REVISION))},
          "Idempotency-Key": "preview-e2e-viewer-denied",
        },
        body: JSON.stringify({ contract_version: "p6-schedule-snapshot-api.v1", timezone: "UTC" }),
      });
      const body = await response.json().catch(() => null);
      return { status: response.status, body };
    })()`, { awaitPromise: true });
    assert(viewerSnapshotPost.status === 403, "viewer snapshot publication must be denied with 403");

    await page.click('[data-menu="project"]');
    await page.scrollTo("#cp-interchange");
    await page.waitForSelector("[data-interchange-export]", "viewer interchange export");
    await page.click("[data-interchange-export]");
    await page.waitFor(
      `Boolean(document.querySelector("[data-interchange-export-result] .cp-interchange-success [data-interchange-download]"))`,
      "viewer interchange read export",
    );
    const viewerExportStatus = await page.text(
      "[data-interchange-export-status]",
    );
    assert(
      (viewerExportStatus ?? "").includes("server generated"),
      "viewer must be able to generate a read-only export",
    );
    await page.setInput(
      "[data-interchange-input]",
      "<APIBusinessObjects><Activity><Id>V1</Id><Name>Denied</Name></Activity></APIBusinessObjects>",
    );
    await page.click("[data-interchange-import]");
    await page.waitFor(
      `Boolean(document.querySelector("[data-interchange-import-result] .cp-interchange-error"))`,
      "viewer interchange write denial",
    );
    const viewerImportError = await page.text(
      "[data-interchange-import-result]",
    );
    assert(
      (viewerImportError ?? "").includes("authorization denied") &&
        (viewerImportError ?? "").includes("project.write"),
      `viewer import must surface the denied permission, got ${viewerImportError}`,
    );
    assert(
      (await page.count("[data-interchange-import-result] tbody tr")) === 0,
      "a denied import must not display mapped rows",
    );
    await page.screenshot("11a-viewer-interchange.png");

    await page.click('[data-menu="resources"]');
    await page.waitFor(
      `document.querySelector(".cp-navigation-surface strong")?.textContent.trim() === "Resources"`,
      "viewer resources surface",
    );
    await page.waitFor(
      `document.querySelectorAll("[data-capacity-profile] tbody tr").length === 3`,
      "viewer capacity read profile",
    );
    await page.setInput("[data-capacity-resource]", "RPS-CIVIL-CREW");
    await page.setInput("[data-capacity-max-units]", "9");
    await page.setSelect("[data-capacity-unit-basis]", "day");
    await page.setInput("[data-capacity-hours]", "8");
    await page.setInput("[data-capacity-from]", "2026-12-01");
    await page.click("[data-capacity-save]");
    await page.waitFor(
      `Boolean(document.querySelector("[data-capacity-write-result] .cp-capacity-error"))`,
      "viewer capacity write denial",
    );
    const viewerCapacityError = await page.text(
      "[data-capacity-write-result]",
    );
    assert(
      (viewerCapacityError ?? "").includes("denied this operation") &&
        (viewerCapacityError ?? "").includes("project.write"),
      `viewer capacity write must surface the denied permission, got ${viewerCapacityError}`,
    );
    await page.setInput("[data-capacity-resolve-period]", "2026-11-02");
    await page.setSelect("[data-capacity-resolve-basis]", "week");
    await page.setInput("[data-capacity-resolve-hours]", "40");
    await page.click("[data-capacity-resolve]");
    await page.waitFor(
      `document.querySelector("[data-capacity-resolve-value]")?.getAttribute("data-capacity-resolve-value") === "50"`,
      "viewer capacity read resolution",
    );
    await page.screenshot("11b-viewer-capacity.png");

    EVIDENCE.permissions = {
      session_roles: sessionViewer.roles,
      layout_read_status: layoutGet.status,
      layout_write: viewerLayoutPost,
      snapshot_write: viewerSnapshotPost,
      interchange_export: viewerExportStatus,
      interchange_import_denied: viewerImportError,
      capacity_read_resolved: "50",
      capacity_write_denied: viewerCapacityError,
    };
    record("viewer can read capacity but the effective change is explicitly denied", {
      capacity_error: viewerCapacityError,
    });
    record("viewer can read interchange but the import write is explicitly denied", {
      export_status: viewerExportStatus,
      import_error: viewerImportError,
      import_rows: await page.count(
        "[data-interchange-import-result] tbody tr",
      ),
    });
    await page.evaluate(`(() => {
      const button = document.querySelector("[data-run-schedule]");
      if (button) button.setAttribute("data-e2e-stale", "true");
      return true;
    })()`);
    await page.click('[data-menu="schedule"]');
    await page.waitFor(
      `Boolean(document.querySelector("[data-run-schedule]:not([data-e2e-stale])"))`,
      "viewer schedule run panel remounted",
    );
    await page.click("[data-run-schedule]");
    await page.waitFor(
      `(document.querySelector("[data-run-status]")?.textContent ?? "").includes("did not complete") ||
       (document.querySelector("[data-run-status]")?.textContent ?? "").includes("کامل نشد")`,
      "viewer run failure is shown",
      30000,
    );
    const viewerRunStatus = await page.text("[data-run-status]");
    const viewerRunRows = await page.count(
      "[data-run-results] .cp-schedule-result-table tbody tr",
    );
    assert(viewerRunRows === 0, "denied calculation must not display fabricated results");
    await page.scrollTo("#cp-schedule-run");
    await page.screenshot("11-viewer-permission.png");
    record("viewer role is read-only and sees an explicit failed-calculation error", {
      run_status: viewerRunStatus,
      layout_write_status: viewerLayoutPost.status,
      snapshot_write_status: viewerSnapshotPost.status,
      result_rows: viewerRunRows,
    });
    await page.click("#cubi-preview-banner button");
    await page.waitForSelector('form[action="/preview/login"]', "final logout");

    await page.click('button[name="role"][value="admin"]');
    await page.waitForSelector(".cp-project-selection", "admin project selection");
    const createdProjectName = `E2E project ${Date.now()}`;
    await page.evaluate(
      `(() => {
        const input = document.querySelector('.cp-project-create-form input[name="projectName"]');
        const form = document.querySelector('.cp-project-create-form');
        if (!input || !form) throw new Error("PROJECT_CREATE_FORM_MISSING");
        input.value = ${JSON.stringify(createdProjectName)};
        input.dispatchEvent(new Event("input", { bubbles: true }));
        form.requestSubmit();
        return true;
      })()`,
    );
    await page.waitForSelector(".cp-workspace", "created project workspace");
    await page.waitFor(
      `document.querySelector("#cubi-preview-banner")?.textContent.includes("preview-admin")`,
      "admin banner identity",
    );
    const createdProject = await page.evaluate(`(() => ({
      name: document.querySelector(".cp-project")?.textContent.trim() ?? "",
      revision: document.querySelector(".cp-revision")?.textContent.trim() ?? "",
      rows: document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]").length,
      columns: document.querySelectorAll("#cp-activity-grid thead th").length,
      calendar_toggle: document.querySelector("[data-calendar-mode]")?.getAttribute("data-calendar-mode") ?? null,
    }))()`);
    const projectsAfterCreate = await page.evaluate(
      `fetch("/api/projects").then((response) => response.json())`,
      { awaitPromise: true },
    );
    assert(
      Array.isArray(projectsAfterCreate.projects) &&
        projectsAfterCreate.projects.some(
          (project) => project.name === createdProjectName,
        ),
      "the created project name must be returned by the persisted project list",
    );
    assert(
      createdProject.name.length > 0 && createdProject.revision.startsWith("R"),
      "the newly created project must be opened in the workspace",
    );
    assert(createdProject.rows === 0, "a new project must show an explicit empty activity grid");
    assert(createdProject.columns === 10, "a new project must receive the persisted curated layout");
    assert(
      createdProject.calendar_toggle === "jalali",
      "the created empty workspace must still expose the calendar display toggle",
    );
    await page.screenshot("12-admin-project-created.png");
    EVIDENCE.project_creation = {
      name: createdProjectName,
      revision: createdProject.revision,
      rows: createdProject.rows,
      columns: createdProject.columns,
      calendar_toggle: createdProject.calendar_toggle,
      source: "Web create-project form -> POST /api/projects -> preview initializer",
    };
    record("authorized project creation initializes an empty persisted workspace", {
      name: createdProjectName,
      rows: createdProject.rows,
      columns: createdProject.columns,
    });

    // First-run journey on a real account with no project membership. This is
    // not a mocked state: the newcomer session, the empty project list and the
    // created project all go through the same preview API and SQLite store.
    await page.click("#cubi-preview-banner button");
    await page.waitForSelector('form[action="/preview/login"]', "newcomer login");
    await page.click('button[name="role"][value="newcomer"]');
    await page.waitForSelector(".cp-project-selection", "newcomer first-run page");
    // The stored workspace language is English from the earlier explicit
    // choice; select it again only if a different profile locale won.
    if ((await page.evaluate(`document.documentElement.lang`)) !== "en") {
      await page.click('[data-bootstrap-language="en"]');
      await page.waitFor(
        `document.documentElement.lang === "en" && document.documentElement.dir === "ltr"`,
        "English first-run page",
      );
    }
    const firstRun = await page.evaluate(`(() => ({
      heading: document.querySelector(".cp-project-selection h1")?.textContent?.trim() ?? "",
      description: document.querySelector(".cp-project-selection > p")?.textContent?.trim() ?? "",
      projectOptions: document.querySelectorAll(".cp-project-option").length,
      hasCreateForm: Boolean(document.querySelector('.cp-project-create-form input[name="projectName"]')),
      hasErrorPage: Boolean(document.querySelector(".cp-shell-error")),
      rawMessageKey: /error\\.[a-z0-9._-]+/i.test(document.body.textContent ?? ""),
      documentLang: document.documentElement.lang,
      documentDir: document.documentElement.dir,
    }))()`);
    assert(firstRun.projectOptions === 0, "the first-run account must not receive fixture projects");
    assert(firstRun.hasCreateForm, "the first-run page must offer the real create-project form");
    assert(!firstRun.hasErrorPage, "zero projects must not render as a dead-end error page");
    assert(!firstRun.rawMessageKey, "no raw error message key may be shown to the user");
    assert(firstRun.heading === "Create your first project", "the first-run heading must explain the next step");

    await page.click('[data-bootstrap-language="fa"]');
    await page.waitFor(
      `document.documentElement.lang === "fa" && document.documentElement.dir === "rtl" &&
       (document.querySelector(".cp-project-selection h1")?.textContent ?? "").includes("اولین پروژه")`,
      "Persian first-run page",
    );

    await page.evaluate(`(() => {
      const form = document.querySelector(".cp-project-create-form");
      if (!form) throw new Error("FIRST_RUN_FORM_MISSING");
      form.requestSubmit();
      return true;
    })()`);
    await page.waitFor(
      `(() => {
        const error = document.querySelector(".cp-form-error");
        return Boolean(error) && !error.hidden && error.textContent.trim().length > 0;
      })()`,
      "empty project name is rejected inline",
    );
    const emptyNameError = await page.text(".cp-form-error");
    assert(/[\u0600-\u06FF]/.test(emptyNameError), "inline validation must be localized");

    const firstProjectName = `پروژه نخست ${Date.now()}`;
    await page.evaluate(
      `(() => {
        const input = document.querySelector('.cp-project-create-form input[name="projectName"]');
        const form = document.querySelector(".cp-project-create-form");
        if (!input || !form) throw new Error("FIRST_RUN_FORM_MISSING");
        input.value = ${JSON.stringify(firstProjectName)};
        input.dispatchEvent(new Event("input", { bubbles: true }));
        form.requestSubmit();
        return true;
      })()`,
    );
    await page.waitForSelector(".cp-workspace", "first project workspace");
    const firstProject = await page.evaluate(`(() => ({
      url: window.location.href,
      project: document.querySelector(".cp-project")?.textContent?.trim() ?? "",
      lang: document.documentElement.lang,
      dir: document.documentElement.dir,
      menu: document.querySelector('.cp-menu button[aria-current="page"]')?.dataset.menu ?? "",
    }))()`);
    assert(firstProject.lang === "fa" && firstProject.dir === "rtl", "the chosen language must survive project creation");
    assert(firstProject.project.length > 0, "the created project must be opened");
    assert(/[?&]project=/.test(firstProject.url), "the confirmed project must be reflected in the address");

    await page.click('[data-menu="control"]');
    await page.waitFor(
      `document.querySelector('.cp-menu button[data-menu="control"]')?.getAttribute("aria-current") === "page"`,
      "control menu selected",
    );
    const urlBeforeReload = firstProject.url;
    await page.reload(".cp-workspace", "first-run project reload");
    const afterFirstReload = await page.evaluate(`(() => ({
      url: window.location.href,
      lang: document.documentElement.lang,
      dir: document.documentElement.dir,
      project: document.querySelector(".cp-project")?.textContent?.trim() ?? "",
      menu: document.querySelector('.cp-menu button[aria-current="page"]')?.dataset.menu ?? "",
      selectionVisible: Boolean(document.querySelector(".cp-project-selection")),
    }))()`);
    assert(!afterFirstReload.selectionVisible, "refresh must not drop the user back to project selection");
    assert(afterFirstReload.project === firstProject.project, "refresh must reopen the same project");
    assert(afterFirstReload.url === urlBeforeReload, "refresh must keep the project deep link");
    assert(afterFirstReload.lang === "fa" && afterFirstReload.dir === "rtl", "refresh must keep the selected language");
    assert(afterFirstReload.menu === "control", "refresh must keep the active workspace menu");

    const projectsForNewcomer = await page.evaluate(
      `fetch("/api/projects").then((response) => response.json())`,
      { awaitPromise: true },
    );
    assert(
      projectsForNewcomer.projects?.some((project) => project.name === firstProjectName),
      "the first project must be persisted and returned by the real project API",
    );
    await page.screenshot("13-newcomer-first-project.png");
    EVIDENCE.first_run = {
      project_name: firstProjectName,
      project_id: firstProject.project,
      address: afterFirstReload.url,
      language: afterFirstReload.lang,
      menu: afterFirstReload.menu,
      source: "preview-newcomer session -> GET /api/projects (empty) -> POST /api/projects -> GET /api/projects",
    };
    record("a user without projects creates the first real project, and language, project and menu survive reload", {
      project_id: firstProject.project,
      language: afterFirstReload.lang,
      menu: afterFirstReload.menu,
      persisted_projects: projectsForNewcomer.projects?.length ?? 0,
    });

    if (EXCEPTIONS.length > 0) {
      throw new Error(
        `UNCAUGHT_PAGE_EXCEPTIONS: ${JSON.stringify(EXCEPTIONS.slice(0, 5))}`,
      );
    }
    if (API_FAILURES.length > 0) {
      throw new Error(`API_5XX_RESPONSES: ${JSON.stringify(API_FAILURES.slice(0, 5))}`);
    }
    record("no uncaught browser exceptions or API 5xx responses", {
      console_error_count: CONSOLE_ERRORS.length,
    });
  } finally {
    page?.cdp.close();
    chrome.cdp.close();
    chrome.stop();
    if (managed) managed.stop();
  }
}

let failure = null;
try {
  await main();
} catch (error) {
  failure = error;
  EVIDENCE.failure = {
    message: error instanceof Error ? error.message : String(error),
    stack: error instanceof Error ? error.stack : null,
  };
  log(`\nE2E FAILED: ${EVIDENCE.failure.message}`);
} finally {
  EVIDENCE.finished_at = new Date().toISOString();
  EVIDENCE.status = failure ? "failed" : "passed";
  const evidenceFile = join(artifactsDir, "evidence.json");
  writeFileSync(evidenceFile, JSON.stringify(EVIDENCE, null, 2));
  log(`\nEvidence: ${evidenceFile}`);
  log(`Screenshots: ${SCREENSHOTS.length}`);
  if (failure) {
    process.exitCode = 1;
  } else {
    log(`\nCUBI full-stack preview E2E passed (${CHECKS.length} recorded checks).`);
  }
}
