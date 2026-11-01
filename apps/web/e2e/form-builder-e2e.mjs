/**
 * CUBI Form Builder end-to-end journey.
 *
 * This harness drives the real browser UI against the real WSGI preview, the
 * real SQLite database and the real Form Builder API. It does not call the API
 * to fabricate the journey: every step below is a user action in the workspace
 * (copy -> customize -> publish -> assign -> fill -> submit -> approve -> print
 * -> reload). Direct fetches are used only to read evidence and to perform the
 * same sign-out endpoint the shell calls.
 *
 * Run from apps/web:  node e2e/form-builder-e2e.mjs
 */
import { spawn, execFileSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createServer } from "node:net";

const webRoot = fileURLToPath(new URL("..", import.meta.url));
const repoRoot = resolve(webRoot, "..", "..");
const artifactsDir = join(webRoot, "e2e", "artifacts");
const PROJECT_ID = "preview-rps-01";
const ORG_TEMPLATE = "contractor-daily-site-report";
const RUN = Date.now().toString(36);
const ORG_NEW_ID = `e2e-org-${RUN}`;
const REPORT_TITLE = `E2E daily report ${RUN}`;

const CHECKS = [];
const SCREENSHOTS = [];
const CONSOLE_ERRORS = [];
const EXCEPTIONS = [];
let activePage = null;

function log(message) {
  process.stdout.write(`${message}\n`);
}

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

function record(name, details = {}) {
  CHECKS.push({ name, ...details });
  log(`  OK ${name}`);
}

function sleep(ms) {
  return new Promise((done) => setTimeout(done, ms));
}

function freePort() {
  return new Promise((resolvePort, rejectPort) => {
    const server = createServer();
    server.on("error", rejectPort);
    server.listen(0, "127.0.0.1", () => {
      const port = server.address().port;
      server.close(() => resolvePort(port));
    });
  });
}

function findChrome() {
  const candidates = [
    process.env.CUBI_CHROME_PATH,
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  ].filter(Boolean);
  const found = candidates.find((candidate) => existsSync(candidate));
  if (!found) throw new Error("CHROME_NOT_FOUND");
  return found;
}

function stopProcessTree(child) {
  if (!child || child.exitCode !== null) return;
  try {
    if (process.platform === "win32") {
      execFileSync("taskkill", ["/pid", String(child.pid), "/T", "/F"], {
        stdio: "ignore",
      });
    } else {
      process.kill(-child.pid, "SIGTERM");
    }
  } catch {
    try {
      child.kill("SIGKILL");
    } catch {
      // already gone
    }
  }
}

async function waitForHttp(url, timeoutMs = 60000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) return response;
    } catch {
      // not ready
    }
    await sleep(150);
  }
  throw new Error(`HTTP_TIMEOUT: ${url}`);
}

class Cdp {
  constructor(socket) {
    this.socket = socket;
    this.nextId = 1;
    this.pending = new Map();
    this.listeners = new Map();
    socket.addEventListener("message", (event) => {
      const text = typeof event.data === "string" ? event.data : String(event.data);
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
    await new Promise((resolveOpen, rejectOpen) => {
      socket.addEventListener("open", resolveOpen, { once: true });
      socket.addEventListener("error", () => rejectOpen(new Error("DEVTOOLS_SOCKET_FAILED")), {
        once: true,
      });
    });
    return new Cdp(socket);
  }

  on(method, listener) {
    const listeners = this.listeners.get(method) ?? [];
    listeners.push(listener);
    this.listeners.set(method, listeners);
  }

  send(method, params = {}, timeoutMs = 30000) {
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
    await this.cdp.send("Log.enable");
    this.cdp.on("Runtime.exceptionThrown", (params) => {
      EXCEPTIONS.push(
        params.exceptionDetails?.exception?.description ??
          params.exceptionDetails?.text ??
          "unknown exception",
      );
    });
    this.cdp.on("Runtime.consoleAPICalled", (params) => {
      if (params.type !== "error") return;
      CONSOLE_ERRORS.push(
        (params.args ?? []).map((arg) => arg.value ?? arg.description ?? arg.type).join(" "),
      );
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

  async waitFor(expression, label, timeoutMs = 30000) {
    const deadline = Date.now() + timeoutMs;
    let lastError;
    while (Date.now() < deadline) {
      try {
        // Publish/verification waits use async IIFEs that fetch the real API, so
        // the promise must settle inside the page before the value is read.
        if (await this.evaluate(expression, { awaitPromise: true })) return true;
      } catch (error) {
        lastError = error;
      }
      await sleep(100);
    }
    throw new Error(
      `WAIT_TIMEOUT: ${label}${lastError ? ` (last error: ${lastError.message})` : ""}`,
    );
  }

  waitForSelector(selector, label = selector, timeoutMs = 30000) {
    return this.waitFor(`Boolean(document.querySelector(${JSON.stringify(selector)}))`, label, timeoutMs);
  }

  async navigate(url, selector, label = url) {
    await this.cdp.send("Page.navigate", { url });
    await this.waitFor(`document.readyState === "complete"`, `${label} document`);
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

  async submit(formSelector) {
    const submitted = await this.evaluate(`(() => {
      const form = document.querySelector(${JSON.stringify(formSelector)});
      if (!form) return false;
      if (typeof form.requestSubmit === "function") form.requestSubmit();
      else form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      return true;
    })()`);
    assert(submitted, `form not found: ${formSelector}`);
  }

  async text(selector) {
    return this.evaluate(`(() => {
      const element = document.querySelector(${JSON.stringify(selector)});
      return element ? element.textContent.trim() : null;
    })()`);
  }

  async count(selector) {
    return this.evaluate(`document.querySelectorAll(${JSON.stringify(selector)}).length`);
  }

  async reload(selector, label = "reload") {
    await this.cdp.send("Page.reload", { ignoreCache: true });
    // A reload destroys the previous execution context; give the browser a
    // moment to attach the new document before polling it.
    await sleep(800);
    await this.waitFor(
      `document.readyState === "complete" || document.readyState === "interactive"`,
      `${label} document`,
    );
    if (selector) await this.waitForSelector(selector, label);
  }

  async screenshot(name) {
    const result = await this.cdp.send("Page.captureScreenshot", { format: "png", fromSurface: true });
    const file = join(artifactsDir, name);
    writeFileSync(file, Buffer.from(result.data, "base64"));
    SCREENSHOTS.push(name);
    log(`  captured artifacts/${name}`);
  }
}

async function launchChrome() {
  const chromePath = findChrome();
  const userDataDir = mkdtempSync(join(tmpdir(), "cubi-form-e2e-"));
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
      "--window-size=1440,1000",
      "--hide-scrollbars",
      "about:blank",
    ],
    { stdio: ["ignore", "pipe", "pipe"], detached: process.platform !== "win32" },
  );
  let stderr = "";
  child.stderr.on("data", (chunk) => {
    stderr += chunk.toString();
  });
  const activePortFile = join(userDataDir, "DevToolsActivePort");
  const deadline = Date.now() + 20000;
  while (!existsSync(activePortFile)) {
    if (Date.now() > deadline) throw new Error(`CHROME_DID_NOT_START ${stderr.slice(-800)}`);
    await sleep(50);
  }
  let debugPort = "";
  while (!debugPort) {
    try {
      const first = readFileSync(activePortFile, "utf8").split("\n")[0].trim();
      if (/^\d+$/.test(first)) debugPort = first;
    } catch {
      // Chrome is still writing the file.
    }
    if (debugPort) break;
    if (Date.now() > deadline) throw new Error(`CHROME_DEBUG_PORT_UNREADABLE ${stderr.slice(-800)}`);
    await sleep(50);
  }
  let target = null;
  for (let attempt = 0; attempt < 50 && !target; attempt += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${debugPort}/json/list`);
      target = (await response.json()).find((item) => item.type === "page");
    } catch {
      // not ready
    }
    if (!target) await sleep(100);
  }
  if (!target) {
    const response = await fetch(`http://127.0.0.1:${debugPort}/json/new?about:blank`, { method: "PUT" });
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

async function login(page, baseUrl, role) {
  await page.navigate(`${baseUrl}/preview/login`, 'form[action="/preview/login"]', "login page");
  await page.click(`button[name="role"][value="${role}"]`);
  await page.waitFor(`location.pathname === "/app"`, `${role} redirect`);
  // The shell may restore the previously opened project instead of asking
  // again; both entries are valid for the same session.
  await page.waitFor(
    `Boolean(document.querySelector("[data-project-id]")) ||
     Boolean(document.querySelector('[data-rail-action="forms"]'))`,
    `${role} workspace entry`,
  );
  if (await page.evaluate(`Boolean(document.querySelector("[data-project-id]"))`)) {
    await page.click(`button[data-project-id="${PROJECT_ID}"]`);
  }
  await page.waitForSelector('[data-rail-action="forms"]', "workspace shell");
}

async function logout(page, baseUrl) {
  await page.evaluate('fetch("/preview/logout", { method: "POST" }).then(() => true)', {
    awaitPromise: true,
  });
  await page.navigate(`${baseUrl}/preview/login`, 'form[action="/preview/login"]', "login after logout");
}

async function openForms(page) {
  await page.click('[data-rail-action="forms"]');
  await page.waitForSelector("[data-form-builder] .cp-fb-shell", "form builder shell");
  await page.waitForSelector("[data-fb-tab=\"library\"]", "form builder tabs");
}

async function fetchJson(page, path) {
  return page.evaluate(
    `(async () => {
      const response = await fetch(${JSON.stringify(path)}, { credentials: "same-origin" });
      const body = await response.json().catch(() => null);
      return { status: response.status, body };
    })()`,
    { awaitPromise: true },
  );
}

async function publish(page, reason) {
  await page.click("[data-fb-publish]");
  await page.waitForSelector('form[data-fb-modal="publish"]');
  await page.setInput('form[data-fb-modal="publish"] textarea[name="reason"]', reason);
  await page.submit('form[data-fb-modal="publish"]');
  await page.waitFor(
    `!document.querySelector('form[data-fb-modal="publish"]')`,
    "publish modal closed",
  );
}

async function main() {
  mkdirSync(artifactsDir, { recursive: true });
  const port = await freePort();
  const database = join(tmpdir(), `cubi-form-e2e-${RUN}.sqlite3`);
  const baseUrl = `http://127.0.0.1:${port}`;
  const env = {
    ...process.env,
    PYTHONPATH: join(repoRoot, "src"),
    PYTHONIOENCODING: "utf-8",
    CUBI_PREVIEW_PUBLIC_DEMO: "",
    CUBI_PREVIEW_PRIVATE_ACCESS_TOKEN: "",
  };
  const server = spawn(
    process.platform === "win32" ? "py" : "python3",
    [
      ...(process.platform === "win32" ? ["-3"] : []),
      "-m",
      "construction_pm.preview",
      "--web-root",
      join(webRoot),
      "--database",
      database,
      "--reset",
      "--port",
      String(port),
    ],
    { cwd: repoRoot, env, stdio: ["ignore", "pipe", "pipe"] },
  );
  let serverLog = "";
  server.stdout.on("data", (chunk) => {
    serverLog += chunk.toString();
  });
  server.stderr.on("data", (chunk) => {
    serverLog += chunk.toString();
  });

  let chrome = null;
  try {
    await waitForHttp(`${baseUrl}/preview/health`);
    log(`Preview ready at ${baseUrl} with database ${database}`);
    chrome = await launchChrome();
    const page = new Page(chrome.cdp);
    activePage = page;
    await page.initialize();

    // ---------------------------------------------------------------
    // 1. Project administrator creates and publishes an organization form.
    // ---------------------------------------------------------------
    await login(page, baseUrl, "admin");
    await openForms(page);
    await page.waitFor(
      `document.querySelectorAll('[data-fb-library="organization"]').length >= 10`,
      "seeded organization library",
    );
    const orgCount = await page.count('[data-fb-library="organization"]');
    assert(orgCount >= 10, `seeded organization library expected >= 10, got ${orgCount}`);
    record("organization library lists the seeded standard report templates", { count: orgCount });
    await page.screenshot("fb-01-organization-library.png");

    await page.click('[data-fb-new="organization"]');
    await page.waitForSelector('form[data-fb-modal="new-template"]');
    await page.setInput('form[data-fb-modal="new-template"] input[name="template_id"]', ORG_NEW_ID);
    await page.setInput('form[data-fb-modal="new-template"] input[name="title"]', `E2E Org Form ${RUN}`);
    await page.setInput('form[data-fb-modal="new-template"] input[name="category"]', "daily");
    await page.submit('form[data-fb-modal="new-template"]');
    await page.waitForSelector("[data-fb-add-field=\"text\"]", "new organization designer");
    await page.click('[data-fb-add-field="text"]');
    await page.waitForSelector(".cp-fb-field", "placed field");
    await page.click("[data-fb-save]");
    await page.waitFor(
      `document.querySelector("[data-fb-status]")?.dataset.kind === "ok"`,
      "organization draft saved",
    );
    await publish(page, "Initial organization template");
    await page.waitFor(
      `(async () => {
        const response = await fetch("/api/forms/organization/templates/${ORG_NEW_ID}", { credentials: "same-origin" });
        const body = await response.json();
        return body.published_version === 1;
      })()`,
      "organization template published v1",
    );
    record("a new organization template is created and published through the designer", {
      template_id: ORG_NEW_ID,
      version: 1,
    });
    await page.screenshot("fb-02-organization-published.png");

    // ---------------------------------------------------------------
    // 2. Copy the contractor report into the project and customize it.
    // ---------------------------------------------------------------
    await page.click('[data-fb-tab="library"]');
    await page.waitForSelector(`[data-fb-copy="${ORG_TEMPLATE}"]`);
    await page.click(`[data-fb-copy="${ORG_TEMPLATE}"]`);
    await page.waitForSelector('[data-fb-design-tab="page"]', "copied project designer");
    await page.waitFor(
      `document.querySelector(".cp-fb-outline")?.dataset.fbTemplate === "${ORG_TEMPLATE}"`,
      "copied project template opened",
    );

    const projectsBefore = await fetchJson(page, `/api/projects/${PROJECT_ID}/forms/overview`);
    assert(projectsBefore.status === 200, "project form overview must be readable");
    const projectCopy = projectsBefore.body.libraries.project.templates.find(
      (item) => item.template_id === ORG_TEMPLATE,
    );
    assert(projectCopy, "project copy must exist in the project library");
    assert(!projectCopy.published_version, "the copy must start unpublished");

    await page.click('[data-fb-design-tab="page"]');
    await page.waitForSelector('[data-fb-header="title.en"]');
    await page.setInput('[data-fb-header="title.en"]', "E2E Project Daily Report");
    await page.click("[data-fb-save]");
    await page.waitFor(
      `document.querySelector("[data-fb-status]")?.dataset.kind === "ok"`,
      "project customization saved",
    );
    await publish(page, "Project customization v1");
    await page.waitFor(
      `(async () => {
        const response = await fetch("/api/projects/${PROJECT_ID}/forms/templates/${ORG_TEMPLATE}", { credentials: "same-origin" });
        const body = await response.json();
        return body.published_version === 1;
      })()`,
      "project template published v1",
    );
    record("organization template copied to the project and published as project v1");

    // A second edit must create v2, never mutate v1 in place.
    await page.click('[data-fb-design-tab="page"]');
    await page.waitForSelector('[data-fb-header="title.en"]');
    await page.setInput('[data-fb-header="title.en"]', "E2E Project Daily Report v2");
    await page.click("[data-fb-save]");
    await page.waitFor(
      `document.querySelector("[data-fb-status]")?.dataset.kind === "ok"`,
      "second project edit saved",
    );
    await publish(page, "Project customization v2");
    await page.waitFor(
      `(async () => {
        const response = await fetch("/api/projects/${PROJECT_ID}/forms/templates/${ORG_TEMPLATE}", { credentials: "same-origin" });
        const body = await response.json();
        return body.published_version === 2;
      })()`,
      "project template published v2",
    );
    record("a second project change creates an immutable v2");

    await page.click('[data-fb-design-tab="versions"]');
    await page.waitForSelector("[data-fb-diff]");
    const versionCount = await page.count(".cp-fb-versions li");
    assert(versionCount === 2, `expected two published versions, got ${versionCount}`);
    await page.click("[data-fb-diff]");
    await page.waitForSelector('form[data-fb-modal="diff"]');
    await page.submit('form[data-fb-modal="diff"]');
    await page.waitForSelector(".cp-fb-diff");
    record("version history and version comparison are usable", { versions: versionCount });
    await page.screenshot("fb-03-project-versions.png");

    const orgAfter = await fetchJson(page, `/api/forms/organization/templates/${ORG_TEMPLATE}`);
    assert(orgAfter.status === 200, "organization template must remain readable");
    assert(
      orgAfter.body.payload.header.title.en.toLowerCase().includes("contractor daily"),
      "project edits must never mutate the organization source",
    );
    assert(orgAfter.body.published_version === 1, "organization source must remain at v1");
    record("project publication leaves the organization source immutable");

    // ---------------------------------------------------------------
    // 3. Planner fills, saves and submits a report assigned to them.
    // ---------------------------------------------------------------
    await page.click("[data-fb-close]");
    await logout(page, baseUrl);
    await login(page, baseUrl, "planner");
    await openForms(page);
    await page.click('[data-fb-tab="reports"]');
    await page.waitForSelector("[data-fb-new-report]");
    // A tab switch triggers a library refresh that re-renders the toolbar; a
    // click issued in the same task as a re-render can be lost, so retry until
    // the modal actually exists instead of assuming one attempt is enough.
    let newReportModal = false;
    for (let attempt = 0; attempt < 5 && !newReportModal; attempt += 1) {
      await page.click("[data-fb-new-report]");
      try {
        await page.waitForSelector('form[data-fb-modal="new-report"]', "new report modal", 2000);
        newReportModal = true;
      } catch {
        // The list re-rendered under the click; try again on the fresh DOM.
      }
    }
    assert(newReportModal, "the create report modal must open");
    await page.setSelect('form[data-fb-modal="new-report"] select[name="template_id"]', ORG_TEMPLATE);
    await page.setInput('form[data-fb-modal="new-report"] input[name="title"]', REPORT_TITLE);
    await page.setSelect(
      'form[data-fb-modal="new-report"] select[name="assigned_to"]',
      "preview-planner",
    );
    await page.submit('form[data-fb-modal="new-report"]');
    await page.waitForSelector('[data-fb-field="work_front"]', "report editor");

    await page.setInput('[data-fb-field="report_date"]', "2026-11-01");
    await page.setSelect('[data-fb-field="shift"]', "day");
    await page.setInput('[data-fb-field="work_front"]', "Block B - level 3");
    await page.setInput('[data-fb-field="workforce"]', "12");
    await page.setInput('[data-fb-field="hours_worked"]', "8.5");
    await page.setInput('[data-fb-field="planned_qty"]', "200");
    await page.setInput('[data-fb-field="completed_qty"]', "150");
    await page.setInput('[data-fb-field="planned_work"]', "Concrete pour for block B");
    await page.setInput('[data-fb-field="completed_work"]', "120 m3 placed and vibrated");
    await page.setInput('[data-fb-field="prepared_by"]', "Planner (E2E)");

    await page.click('[data-fb-add-row="work_items"]');
    await page.waitForSelector('[data-fb-cell="work_items|0|item"]');
    await page.setInput('[data-fb-cell="work_items|0|item"]', "Concrete");
    await page.setInput('[data-fb-cell="work_items|0|unit"]', "m3");
    await page.setInput('[data-fb-cell="work_items|0|planned_qty"]', "100");
    await page.setInput('[data-fb-cell="work_items|0|actual_qty"]', "80");
    await page.setInput('[data-fb-cell="work_items|0|remarks"]', "poured in two lifts");

    await page.waitFor(
      `(document.querySelector('[data-fb-calc="man_hours"]')?.textContent || "").includes("102")`,
      "shared formula core calculates man-hours",
    );
    await page.waitFor(
      `(document.querySelector('[data-fb-calc="progress_pct"]')?.textContent || "").includes("75")`,
      "shared formula core calculates progress",
    );
    record("report fields, table row and shared formula results are live in the editor");

    await page.click("[data-fb-save-report]");
    await page.waitFor(
      `document.querySelector("[data-fb-status]")?.dataset.kind === "ok"`,
      "draft saved",
    );
    await page.click('[data-fb-transition="submit"]');
    await page.waitFor(
      `document.querySelector(".cp-fb-report-head")?.dataset.fbReportStatus === "submitted"`,
      "report submitted",
    );
    assert(
      !(await page.evaluate(`Boolean(document.querySelector('[data-fb-transition="approve"]'))`)),
      "the planner must not see an approve action on their own report",
    );
    record("planner saves and submits an assigned report; approval is not offered");
    await page.screenshot("fb-04-report-submitted.png");

    const submitted = await fetchJson(
      page,
      `/api/projects/${PROJECT_ID}/forms/submissions?template_id=${ORG_TEMPLATE}`,
    );
    assert(submitted.status === 200 && submitted.body.submissions.length === 1);
    const submission = submitted.body.submissions[0];
    assert(submission.status === "submitted", `expected submitted, got ${submission.status}`);
    assert(submission.assigned_to === "preview-planner");
    assert(submission.template_version === 2, "submission must pin the latest published version");

    const printFa = await page.evaluate(
      `(async () => {
        const response = await fetch("/api/projects/${PROJECT_ID}/forms/submissions/${submission.submission_id}/print?locale=fa", { credentials: "same-origin" });
        return { status: response.status, text: await response.text() };
      })()`,
      { awaitPromise: true },
    );
    assert(printFa.status === 200 && printFa.text.includes("form-page"));
    assert(printFa.text.includes('dir="rtl"'), "Persian print output must be RTL");
    assert(printFa.text.includes("Concrete"), "print output must contain the real table row");
    record("server print output is RTL-localized and contains persisted table data");

    // ---------------------------------------------------------------
    // 4. Administrator approves, prints, exports and reloads history.
    // ---------------------------------------------------------------
    await page.click("[data-fb-close]");
    await logout(page, baseUrl);
    await login(page, baseUrl, "admin");
    await openForms(page);
    await page.click('[data-fb-tab="reports"]');
    await page.waitForSelector(`[data-fb-open-report="${submission.submission_id}"]`);
    await page.click(`[data-fb-open-report="${submission.submission_id}"]`);
    await page.waitForSelector('[data-fb-transition="approve"]', "approve action");
    await page.click('[data-fb-transition="approve"]');
    await page.waitFor(
      `document.querySelector(".cp-fb-report-head")?.dataset.fbReportStatus === "approved"`,
      "report approved",
    );
    const trail = await page.text(".cp-fb-trail");
    assert(trail.includes("preview-admin"), "approval trail must name the administrator");
    assert(trail.includes("preview-planner"), "approval trail must name the submitter");
    record("administrator approves the submitted report with an audited trail");
    await page.screenshot("fb-05-report-approved.png");

    await page.click("[data-fb-print-html]");
    await page.waitForSelector('[data-fb-tab="print"].is-active');
    await page.waitForSelector("[data-fb-print-frame-src]");
    const printBody = await page.evaluate(
      `document.querySelector("[data-fb-print-frame-src]").getAttribute("srcdoc") || ""`,
    );
    assert(printBody.includes("form-page"));
    assert(printBody.includes("Concrete"));
    record("print preview renders the approved report for PDF output");

    const xlsx = await page.evaluate(
      `(async () => {
        const response = await fetch("/api/projects/${PROJECT_ID}/forms/submissions/${submission.submission_id}/export.xlsx", { credentials: "same-origin" });
        const buffer = new Uint8Array(await response.arrayBuffer());
        return {
          status: response.status,
          contentType: response.headers.get("content-type") || "",
          size: buffer.length,
          signature: String.fromCharCode(buffer[0], buffer[1]),
        };
      })()`,
      { awaitPromise: true },
    );
    assert(xlsx.status === 200, `xlsx status ${xlsx.status}`);
    assert(xlsx.signature === "PK", "xlsx must be a real zip container");
    assert(xlsx.size > 4000, `xlsx too small: ${xlsx.size}`);
    record("Excel export returns a real workbook", { bytes: xlsx.size });

    // A hard reload may land on project selection instead of the workspace, so
    // accept either surface and re-enter the project before opening Forms.
    await page.reload(null, "workspace reload");
    await page.waitFor(
      `Boolean(document.querySelector('[data-rail-action="forms"]')) ||
       Boolean(document.querySelector("[data-project-id]"))`,
      "workspace or project selection after reload",
    );
    if (!(await page.evaluate(`Boolean(document.querySelector('[data-rail-action="forms"]'))`))) {
      await page.click(`button[data-project-id="${PROJECT_ID}"]`);
      await page.waitForSelector('[data-rail-action="forms"]', "workspace shell after reload");
    }
    await openForms(page);
    await page.click('[data-fb-tab="reports"]');
    await page.waitForSelector(`[data-fb-open-report="${submission.submission_id}"]`);
    const persistedStatus = await page.evaluate(
      `document.querySelector('[data-fb-open-report="${submission.submission_id}"] .cp-fb-badge')?.textContent || ""`,
    );
    assert(
      (await page.evaluate(
        `document.querySelector('[data-fb-open-report="${submission.submission_id}"] .cp-fb-badge')?.className || ""`,
      )).includes("is-approved"),
      `reloaded history must show the approved status, got ${persistedStatus}`,
    );
    await page.click(`[data-fb-open-report="${submission.submission_id}"]`);
    await page.waitFor(
      `document.querySelector(".cp-fb-report-head")?.dataset.fbReportStatus === "approved"`,
      "reloaded report detail",
    );
    const head = await page.text(".cp-fb-report-head");
    assert(head.includes("v2"), "reloaded report must remain pinned to its submitted version");
    record("reload and history keep the approved submission pinned to v2");
    await page.screenshot("fb-06-reload-history.png");

    assert(EXCEPTIONS.length === 0, `browser exceptions: ${EXCEPTIONS.join(" | ")}`);
    assert(
      CONSOLE_ERRORS.filter((entry) => !entry.includes("favicon")).length === 0,
      `browser console errors: ${CONSOLE_ERRORS.join(" | ")}`,
    );

    // ---------------------------------------------------------------
    // 5. Inspect the real database after the UI journey.
    // ---------------------------------------------------------------
    const evidence = JSON.parse(
      execFileSync(
        process.platform === "win32" ? "py" : "python3",
        [
          ...(process.platform === "win32" ? ["-3"] : []),
          "-c",
          `
import json, sqlite3, sys
connection = sqlite3.connect(sys.argv[1])
connection.row_factory = sqlite3.Row
def one(sql, params=()):
    row = connection.execute(sql, params).fetchone()
    return dict(row) if row else None
submission = one("SELECT submission_id, template_id, template_version, status, author, assigned_to FROM form_submission ORDER BY rowid DESC LIMIT 1")
approvals = [dict(row) for row in connection.execute("SELECT action, actor, on_behalf_of, reason, template_version FROM form_approval_event ORDER BY sequence")]
versions = [dict(row) for row in connection.execute("SELECT version, schema_hash FROM form_template_version WHERE project_id=? AND template_id=? ORDER BY version", ("${PROJECT_ID}", "${ORG_TEMPLATE}"))]
org = one("SELECT published_version FROM form_template_head WHERE project_id='__organization__' AND template_id=?", ("${ORG_TEMPLATE}",))
print(json.dumps({"submission": submission, "approvals": approvals, "versions": versions, "organization": org}))
`,
          database,
        ],
        { encoding: "utf-8" },
      ),
    );
    assert(evidence.submission.status === "approved");
    assert(evidence.submission.template_version === 2);
    assert(evidence.submission.author === "preview-planner");
    assert(evidence.submission.assigned_to === "preview-planner");
    assert(evidence.approvals.some((event) => event.action === "approve" && event.actor === "preview-admin"));
    assert(evidence.versions.length === 2);
    assert(evidence.versions[0].schema_hash !== evidence.versions[1].schema_hash);
    assert(evidence.organization.published_version === 1);
    record("SQLite confirms the approved submission, v1/v2 history and untouched organization source", evidence);

    writeFileSync(
      join(artifactsDir, "form-builder-e2e-evidence.json"),
      JSON.stringify({ checks: CHECKS, screenshots: SCREENSHOTS, evidence, database }, null, 2),
      "utf-8",
    );
    log(`\nForm Builder E2E passed with ${CHECKS.length} evidence checks.`);
  } catch (error) {
    let pageState = null;
    try {
      pageState = await activePage?.evaluate(`(() => ({
        status: document.querySelector("[data-fb-status]")?.textContent || null,
        statusKind: document.querySelector("[data-fb-status]")?.dataset.kind || null,
        reportStatus: document.querySelector(".cp-fb-report-head")?.dataset.fbReportStatus || null,
        modal: document.querySelector("[data-fb-modal]")?.dataset.fbModal || null,
        newReport: (() => {
          const button = document.querySelector("[data-fb-new-report]");
          return button ? { disabled: button.disabled, text: button.textContent.trim() } : null;
        })(),
        pathname: location.pathname,
      }))()`);
    } catch {
      // The page may be gone; the failure payload still records the error.
    }
    writeFileSync(
      join(artifactsDir, "form-builder-e2e-failure.json"),
      JSON.stringify(
        {
          error: String(error?.stack || error),
          pageState,
          serverLog: serverLog.slice(-8000),
          consoleErrors: CONSOLE_ERRORS,
          exceptions: EXCEPTIONS,
        },
        null,
        2,
      ),
      "utf-8",
    );
    throw error;
  } finally {
    chrome?.cdp.close();
    chrome?.stop();
    server.kill();
    try {
      if (chrome?.userDataDir) rmSync(chrome.userDataDir, { recursive: true, force: true });
    } catch {
      // Windows may still hold the profile briefly.
    }
  }
}

main().catch((error) => {
  console.error(error?.stack || error);
  process.exitCode = 1;
});
