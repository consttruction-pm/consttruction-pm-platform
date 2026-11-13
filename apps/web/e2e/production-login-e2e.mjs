#!/usr/bin/env node
/**
 * Real-browser verification of the production login + workspace path.
 *
 * It starts `production-login-server.py`, which serves the exact WSGI callable
 * exported by `api/index.py` over PostgreSQL, then drives headless Chrome
 * through DevTools: anonymous gate, real credential login, authorized project,
 * workspace render, refresh continuity, logout and post-logout rejection.
 *
 * This proves the application locally. It cannot prove the Vercel gateway;
 * that still requires access to the `cubi-web-preview` project.
 *
 * Usage:
 *   CONSTRUCTION_PM_POSTGRES_DSN=postgresql://... node e2e/production-login-e2e.mjs
 */

import { spawn } from "node:child_process";
import { createServer } from "node:net";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { fileURLToPath } from "node:url";

const webRoot = fileURLToPath(new URL("..", import.meta.url));
const repoRoot = resolve(webRoot, "..", "..");
const artifactsDir = join(webRoot, "e2e", "artifacts");
mkdirSync(artifactsDir, { recursive: true });

const EMAIL = process.env.CUBI_E2E_EMAIL ?? "e2e-owner@example.test";
const PASSWORD = process.env.CUBI_E2E_PASSWORD ?? "correct horse battery staple";
const PROJECT = process.env.CUBI_E2E_PROJECT ?? "cubi-e2e-project";
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

class Cdp {
  constructor(socket) {
    this.socket = socket;
    this.nextId = 1;
    this.pending = new Map();
    this.listeners = new Map();
    this.closed = false;
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
    socket.addEventListener("close", () => {
      this.closed = true;
      for (const pending of this.pending.values()) pending.reject(new Error("DEVTOOLS_CLOSED"));
      this.pending.clear();
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
  const userDataDir = mkdtempSync(join(tmpdir(), "cubi-prod-e2e-"));
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

  async waitFor(expression, label, timeoutMs = 30000) {
    const deadline = Date.now() + timeoutMs;
    let last;
    while (Date.now() < deadline) {
      try {
        const value = await this.evaluate(expression);
        if (value) return value;
      } catch (error) {
        last = error;
      }
      await sleep(100);
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
    const result = await this.cdp.send("Page.captureScreenshot", { format: "png" });
    const path = join(artifactsDir, name);
    writeFileSync(path, Buffer.from(result.data, "base64"));
    SCREENSHOTS.push(path);
    return path;
  }
}

async function startServer() {
  const port = await freePort();
  const child = spawn(
    "python3",
    [join(webRoot, "e2e", "production-login-server.py")],
    {
      cwd: repoRoot,
      env: {
        ...process.env,
        CONSTRUCTION_PM_SESSION_SECRET: "cubi-local-e2e-session-secret-0123456789",
        CUBI_E2E_PORT: String(port),
        CUBI_E2E_ORIGIN: `http://127.0.0.1:${port}`,
        CUBI_E2E_PROJECT: PROJECT,
        CUBI_E2E_EMAIL: EMAIL,
        CUBI_E2E_PASSWORD: PASSWORD,
        CUBI_WEB_ROOT: join(repoRoot, "public"),
      },
      stdio: ["ignore", "pipe", "pipe"],
    },
  );
  let output = "";
  child.stderr.on("data", (chunk) => {
    output += chunk.toString();
  });
  await new Promise((resolveReady, rejectReady) => {
    const timer = setTimeout(() => rejectReady(new Error(`SERVER_NOT_READY ${output.slice(-800)}`)), 30000);
    child.stdout.on("data", (chunk) => {
      output += chunk.toString();
      if (output.includes("CUBI_E2E_READY")) {
        clearTimeout(timer);
        resolveReady();
      }
    });
  });
  return { child, baseUrl: `http://127.0.0.1:${port}` };
}

async function waitForHttpOk(url) {
  const deadline = Date.now() + 15000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) return response;
    } catch {
      // retry
    }
    await sleep(100);
  }
  throw new Error(`HTTP_NOT_READY ${url}`);
}

async function main() {
  assert(process.env.CONSTRUCTION_PM_POSTGRES_DSN, "CONSTRUCTION_PM_POSTGRES_DSN is required");
  const server = await startServer();
  let chrome = null;
  try {
    await waitForHttpOk(`${server.baseUrl}/api/health/live`);
    chrome = await launchChrome();
    const page = new Page(chrome.cdp);
    await page.initialize();
    await page.viewport(1280, 720);

    const appUrl = `${server.baseUrl}/app?project=${encodeURIComponent(PROJECT)}&view=live`;
    await page.goto(appUrl);
    await page.waitFor(`location.pathname === "/login"`, "anonymous gate redirect");
    check("anonymous /app is redirected to /login", { url: await page.evaluate("location.href") });
    assert(
      (await page.evaluate("location.pathname")) === "/login",
      "anonymous /app must redirect to /login",
    );

    const nextTarget = await page.evaluate(
      "new URLSearchParams(location.search).get('next')",
    );
    assert(nextTarget.includes(`/app?project=${PROJECT}`), "login keeps the requested project");

    await page.evaluate(`(() => {
      document.querySelector("#cp-login-email").value = ${JSON.stringify(EMAIL)};
      document.querySelector("#cp-login-password").value = "wrong-password-value";
      document.querySelector("#cp-login-form").requestSubmit();
    })()`);
    const errorText = await page.waitFor(
      `document.querySelector("#cp-login-error")?.hidden === false ? document.querySelector("#cp-login-error").textContent : ""`,
      "wrong password error",
    );
    assert(errorText.length > 0, "wrong password shows an error");
    check("invalid credentials are rejected on the login page", { error: errorText });

    await page.evaluate(`(() => {
      document.querySelector("#cp-login-email").value = ${JSON.stringify(EMAIL)};
      document.querySelector("#cp-login-password").value = ${JSON.stringify(PASSWORD)};
      document.querySelector("#cp-login-form").requestSubmit();
    })()`);
    await page.waitFor(`location.pathname === "/app"`, "navigate to /app after login");
    const workspace = await page.waitFor(
      `(() => {
        const node = document.querySelector(".cp-workspace");
        return node ? { project: node.dataset.project, html: document.body.innerText.slice(0, 200) } : null;
      })()`,
      "workspace shell",
    );
    assert(workspace.project === PROJECT, "workspace renders the authorized project");
    check("real login opens the authorized project workspace", {
      url: await page.evaluate("location.href"),
      project: workspace.project,
    });
    await page.screenshot("production-login-workspace-1280x720.png");

    const session = await page.evaluate(
      `fetch("/api/session", { credentials: "same-origin" }).then(async (r) => ({ status: r.status, body: await r.json() }))`,
    );
    assert(session.status === 200, "session endpoint after login");
    assert(session.body.user_id === "e2e-owner", "session reports the real user");
    assert(!("session_id" in session.body), "session id is never echoed");
    const projects = await page.evaluate(
      `fetch("/api/projects", { credentials: "same-origin" }).then((r) => r.json())`,
    );
    assert(
      projects.projects.some((project) => project.project_id === PROJECT),
      "authorized project list contains the project",
    );
    check("session and project list are real and tenant-scoped", {
      user_id: session.body.user_id,
      projects: projects.projects.map((project) => project.project_id),
    });

    await page.cdp.send("Page.reload", { ignoreCache: true });
    await page.waitFor(
      `location.pathname === "/app" && Boolean(document.querySelector(".cp-workspace"))`,
      "workspace after refresh",
    );
    check("refresh keeps the session and the same project", {
      url: await page.evaluate("location.href"),
    });

    await page.viewport(1366, 768);
    await page.screenshot("production-login-workspace-1366x768.png");
    check("workspace renders at 1366x768", {});

    const csrf = await page.evaluate(
      `(() => {
        const entry = document.cookie.split(";").map((part) => part.trim()).find((part) => part.startsWith("cubi_csrf="));
        return entry ? decodeURIComponent(entry.slice("cubi_csrf=".length)) : "";
      })()`,
    );
    assert(csrf, "CSRF cookie is readable for the signed-in session");
    const logout = await page.evaluate(
      `fetch("/api/session", { method: "DELETE", credentials: "same-origin", headers: { "X-CSRF-Token": ${JSON.stringify(csrf)} } }).then((r) => r.status)`,
    );
    assert(logout === 204, "logout revokes the session");
    const afterLogout = await page.evaluate(
      `fetch("/api/session", { credentials: "same-origin" }).then((r) => r.status)`,
    );
    assert(afterLogout === 401, "the revoked session is rejected");
    check("logout revokes the session and the next request is rejected", {
      logout_status: logout,
      session_status: afterLogout,
    });

    await page.viewport(1280, 720);
    await page.goto(`${server.baseUrl}/login?lang=fa`);
    await page.waitFor(`document.querySelector("#cp-login-submit") !== null`, "Persian login page");
    const rtl = await page.evaluate(
      `({ dir: document.documentElement.dir, lang: document.documentElement.lang, submit: document.querySelector("#cp-login-submit").textContent.trim() })`,
    );
    assert(rtl.dir === "rtl", "Persian login is right-to-left");
    assert(rtl.lang === "fa", "Persian locale is applied");
    check("Persian login page is RTL", rtl);
    await page.screenshot("production-login-fa-1280x720.png");

    await page.goto(appUrl);
    await page.waitFor(`location.pathname === "/login"`, "signed-out gate redirect");
    check("signed-out /app is gated again", { url: await page.evaluate("location.href") });
    assert((await page.evaluate("location.pathname")) === "/login", "signed-out /app redirects");

    assert(page.events.failures.length === 0, `no API 5xx responses: ${JSON.stringify(page.events.failures)}`);
    check("no API 5xx during the browser flow", {});

    const evidence = {
      contract: "cubi-production-login-e2e.v1",
      finished_at: new Date().toISOString(),
      base_url: server.baseUrl,
      project: PROJECT,
      checks: CHECKS,
      screenshots: SCREENSHOTS,
      console_errors: page.events.console,
      exceptions: page.events.exceptions,
      api_5xx: page.events.failures,
      vercel_gateway_verified: false,
      note: "Served by the exact api/index.py WSGI callable over PostgreSQL; the Vercel domain itself is not verified from this sandbox.",
    };
    writeFileSync(
      join(artifactsDir, "production-login-e2e.json"),
      `${JSON.stringify(evidence, null, 2)}\n`,
    );
    process.stdout.write(`${CHECKS.length} checks passed\n`);
    if (ERRORS.length) process.stdout.write(`${ERRORS.join("\n")}\n`);
  } finally {
    if (chrome) {
      chrome.cdp.socket?.close?.();
      chrome.child.kill("SIGKILL");
    }
    server.child.kill("SIGTERM");
  }
}

main().catch((error) => {
  process.stderr.write(`${error.stack ?? error.message}\n`);
  process.exitCode = 1;
});
