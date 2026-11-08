import { spawn } from "node:child_process";
import fs from "node:fs";
import { setTimeout as delay } from "node:timers/promises";

const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PORT = 9333;
const BASE = "http://127.0.0.1:4174";
const OUT = "docs/workspace/screenshots/visual";
const WORKSPACE = "/app?view=live&project=preview-rps-01";

async function endpointUp() {
  try {
    return (await fetch(`http://127.0.0.1:${PORT}/json/version`)).ok;
  } catch {
    return false;
  }
}

const reuse = await endpointUp();
const profile = `C:/Users/SAAMFF~1/AppData/Local/Temp/cubi-columns-measure-${Date.now()}`;
const chrome = reuse
  ? null
  : spawn(
      CHROME,
      [
        "--headless=new",
        `--remote-debugging-port=${PORT}`,
        `--user-data-dir=${profile}`,
        "--no-first-run",
        "--disable-gpu",
        "--hide-scrollbars",
        "--lang=en-US",
        "--window-size=1280,720",
        "about:blank",
      ],
      { stdio: "ignore" },
    );

for (let i = 0; i < 80 && !(await endpointUp()); i += 1) await delay(250);
if (!(await endpointUp())) throw new Error("CHROME_CDP_UNAVAILABLE");

const target = await (
  await fetch(`http://127.0.0.1:${PORT}/json/new?${encodeURIComponent("about:blank")}`, {
    method: "PUT",
  })
).json();

const ws = new WebSocket(target.webSocketDebuggerUrl);
let nextId = 0;
const pending = new Map();
ws.addEventListener("message", (event) => {
  const msg = JSON.parse(event.data);
  if (msg.id && pending.has(msg.id)) {
    pending.get(msg.id)(msg);
    pending.delete(msg.id);
  }
});
await new Promise((resolve) => ws.addEventListener("open", resolve, { once: true }));

const send = (method, params = {}) =>
  new Promise((resolve) => {
    const id = ++nextId;
    pending.set(id, resolve);
    ws.send(JSON.stringify({ id, method, params }));
  });

const evaluate = async (expression) => {
  const response = await send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (response.result?.exceptionDetails) {
    throw new Error(JSON.stringify(response.result.exceptionDetails));
  }
  return response.result?.result?.value;
};

const waitFor = async (expression, label) => {
  for (let i = 0; i < 60; i += 1) {
    if (await evaluate(expression)) return;
    await delay(250);
  }
  throw new Error(`TIMEOUT:${label}`);
};

const shot = async (name) => {
  const response = await send("Page.captureScreenshot", { format: "png" });
  fs.writeFileSync(`${OUT}/${name}.png`, Buffer.from(response.result.data, "base64"));
  console.log("saved", name);
};

const measure = () =>
  evaluate(
    `(() => {
      const dialog = document.querySelector('[data-p6-columns-dialog]');
      const pane = dialog.querySelector('.cp-columns-list');
      const rect = dialog.getBoundingClientRect();
      const paneRect = pane.getBoundingClientRect();
      const style = getComputedStyle(dialog);
      return JSON.stringify({
        rect: { x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height) },
        viewport: { w: innerWidth, h: innerHeight },
        direction: style.direction,
        listScroll: { h: Math.round(paneRect.height), scroll: pane.scrollHeight, visible: pane.clientHeight },
        footer: [...dialog.querySelectorAll('.cp-dialog-buttons button')].map(b => b.textContent.trim()),
      });
    })()`,
  );

await send("Page.enable");
await send("Runtime.enable");
await send("Emulation.setDeviceMetricsOverride", {
  width: 1280,
  height: 720,
  deviceScaleFactor: 1,
  mobile: false,
});

const loginUrl = `${BASE}/preview/login?next=${encodeURIComponent(WORKSPACE)}`;
await send("Page.navigate", { url: loginUrl });
await delay(900);
await evaluate(`localStorage.setItem('cubi:workspace-locale', 'en')`);
await evaluate(`document.querySelector('form.persona button[value="planner"]').click()`);
await waitFor(
  `location.pathname === '/app' && document.querySelectorAll('tr[data-activity-id]').length > 0`,
  "workspace",
);
await delay(600);

await evaluate(`document.querySelector('[data-toolbar-command="toolbar.fields"]').click()`);
await waitFor(`document.querySelector('[data-p6-columns-dialog]')?.open === true`, "dialog");
await delay(400);
console.log("en", await measure());

// Apply saves without closing the dialog and reports the applied notice.
await evaluate(
  `document.querySelector('[data-p6-columns-dialog] [data-columns-apply]').click()`,
);
await waitFor(
  `(() => { const n = document.querySelector('[data-p6-columns-dialog] [data-columns-notice]'); return n && n.textContent.trim().length > 0; })()`,
  "apply-notice",
);
await delay(300);
console.log(
  "apply",
  await evaluate(
    `JSON.stringify({ open: document.querySelector('[data-p6-columns-dialog]')?.open, notice: document.querySelector('[data-p6-columns-dialog] [data-columns-notice]').textContent.trim() })`,
  ),
);
await shot("73-columns-applied-en-1280");

await evaluate(`document.querySelector('[data-p6-columns-dialog] [data-columns-cancel]').click()`);
await delay(350);
console.log("closed", await evaluate(`document.querySelector('[data-p6-columns-dialog]') == null`));

// Persian RTL measurement.
await evaluate(
  `(() => {
    const select = document.querySelector('select[data-workspace-language]');
    const setter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set;
    setter.call(select, 'fa');
    select.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
  })()`,
);
await delay(1400);
await evaluate(`document.querySelector('[data-toolbar-command="toolbar.fields"]').click()`);
await waitFor(`document.querySelector('[data-p6-columns-dialog]')?.open === true`, "dialog-fa");
await delay(400);
console.log("fa", await measure());

await send("Target.closeTarget", { targetId: target.id });
ws.close();
if (chrome) chrome.kill();
process.exit(0);
