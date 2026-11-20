#!/usr/bin/env node
// P5 — real-browser responsive audit of the assembled public site.
//
// Serves nothing itself: point it at a static server for `_site`, e.g.
//   SITE_BASE_URL=https://cubi.example node scripts/assemble-pages-site.mjs
//   python3 -m http.server 4179 --directory ../../_site &
//   node e2e/public-site-responsive.mjs http://127.0.0.1:4179
//
// It drives headless Chromium through the DevTools protocol, asserts no
// horizontal overflow at three viewports, requires a rendered h1 on every
// static page, and writes screenshots to e2e/artifacts/responsive/.
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { setTimeout as sleep } from "node:timers/promises";

const webRoot = fileURLToPath(new URL("..", import.meta.url));
const artifacts = join(webRoot, "e2e", "artifacts", "responsive");
mkdirSync(artifacts, { recursive: true });

const base = (process.argv[2] ?? "http://127.0.0.1:4179").replace(/\/+$/, "");
const chrome = process.env.CHROME_PATH ?? "/usr/bin/chromium";
const port = 9333;
const viewports = [
  { name: "mobile", width: 390, height: 844 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "desktop", width: 1440, height: 900 },
];
const pages = [
  { path: "/", static: false },
  { path: "/features/", static: true },
  { path: "/de/features/", static: true },
  { path: "/ar/", static: true },
  { path: "/pricing/", static: true },
  { path: "/fa/pricing/", static: true },
];

const chromium = spawn(
  chrome,
  [
    "--headless=new",
    "--no-sandbox",
    "--disable-gpu",
    "--hide-scrollbars",
    `--remote-debugging-port=${port}`,
    "about:blank",
  ],
  { stdio: "ignore" },
);
chromium.on("error", (error) => {
  console.error("CHROMIUM_START_FAILED", error.message);
  process.exit(1);
});

async function cdpJson(path, init) {
  const response = await fetch(`http://127.0.0.1:${port}${path}`, init);
  if (!response.ok) throw new Error(`CDP ${path} -> ${response.status}`);
  return response.json();
}

async function waitForBrowser() {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      return await cdpJson("/json/version");
    } catch {
      await sleep(100);
    }
  }
  throw new Error("CHROMIUM_CDP_TIMEOUT");
}

function connect(url) {
  return new Promise((resolve, reject) => {
    const socket = new WebSocket(url);
    let nextId = 1;
    const pending = new Map();
    socket.addEventListener("open", () => resolve({ socket, send }));
    socket.addEventListener("error", (event) => reject(event.error ?? new Error("CDP_SOCKET_ERROR")));
    socket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      if (message.id && pending.has(message.id)) {
        const { resolve: done, reject: fail } = pending.get(message.id);
        pending.delete(message.id);
        if (message.error) fail(new Error(message.error.message));
        else done(message.result);
      }
    });
    function send(method, params = {}) {
      const id = nextId++;
      return new Promise((done, fail) => {
        pending.set(id, { resolve: done, reject: fail });
        socket.send(JSON.stringify({ id, method, params }));
      });
    }
  });
}

async function evaluate(cdp, expression) {
  const result = await cdp.send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
  return result.result.value;
}

const failures = [];
let checks = 0;

try {
  await waitForBrowser();
  for (const viewport of viewports) {
    for (const page of pages) {
      const target = await cdpJson(`/json/new?${base + page.path}`, { method: "PUT" });
      const cdp = await connect(target.webSocketDebuggerUrl);
      try {
        await cdp.send("Page.enable");
        await cdp.send("Runtime.enable");
        await cdp.send("Emulation.setDeviceMetricsOverride", {
          width: viewport.width,
          height: viewport.height,
          deviceScaleFactor: 1,
          mobile: viewport.name !== "desktop",
        });
        await cdp.send("Page.navigate", { url: base + page.path });
        await sleep(900);
        const state = await evaluate(
          cdp,
          `JSON.stringify({
            innerWidth: window.innerWidth,
            scrollWidth: document.documentElement.scrollWidth,
            bodyWidth: document.body.scrollWidth,
            h1: document.querySelectorAll("h1").length,
            title: document.title,
            switcher: document.querySelectorAll(".cubi-public-language").length,
            direction: document.documentElement.dir
          })`,
        );
        const info = JSON.parse(state);
        checks += 1;
        const label = `${page.path} ${viewport.name} ${viewport.width}x${viewport.height}`;
        if (info.scrollWidth > info.innerWidth + 1 || info.bodyWidth > info.innerWidth + 1) {
          failures.push(`${label}: horizontal overflow (${info.scrollWidth}/${info.bodyWidth} > ${info.innerWidth})`);
        }
        if (page.static && info.h1 < 1) failures.push(`${label}: no rendered h1`);
        if (page.static && info.switcher < 1) failures.push(`${label}: no language switcher`);
        if (!page.static && !info.title) failures.push(`${label}: empty document title`);
        const shot = await cdp.send("Page.captureScreenshot", { format: "png" });
        const name = `${page.path.replace(/\W+/g, "_").replace(/^_|_$/g, "") || "home"}-${viewport.name}.png`;
        writeFileSync(join(artifacts, name), Buffer.from(shot.data, "base64"));
      } finally {
        cdp.socket.close();
        await cdpJson(`/json/close/${target.id}`).catch(() => {});
      }
    }
  }
} finally {
  chromium.kill("SIGTERM");
}

if (failures.length) {
  console.error(`RESPONSIVE_AUDIT_FAILED ${failures.length}/${checks}`);
  for (const failure of failures) console.error(" - " + failure);
  process.exit(1);
}
console.log(`RESPONSIVE_AUDIT_PASSED ${checks}/${checks}; screenshots in ${artifacts}`);
