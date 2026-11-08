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
const profile = `C:/Users/SAAMFF~1/AppData/Local/Temp/cubi-formula-qa-${Date.now()}`;
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
  await fetch(`${BASE.replace("4174", "9333")}/json/new?${encodeURIComponent("about:blank")}`, {
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

const revealFormulaColumn = () =>
  evaluate(
    `(() => {
      const wrap = document.querySelector('.cp-table-wrap');
      const th = [...document.querySelectorAll('th')].find(h => h.innerText.includes('Double progress'));
      if (!wrap || !th) return false;
      const tr = th.getBoundingClientRect();
      const wr = wrap.getBoundingClientRect();
      wrap.scrollLeft += tr.left - wr.left - (wrap.clientWidth - tr.width) / 2;
      return true;
    })()`,
  );

await revealFormulaColumn();
await delay(350);
const savedCells = await evaluate(
  `JSON.stringify([...document.querySelectorAll('td[data-column-id="formula.double_progress"]')].slice(0, 8).map(c => c.innerText))`,
);
console.log("cells", savedCells);
await shot("62-formula-column-grid-en-1280");

await send("Page.reload");
await waitFor(
  `document.querySelectorAll('tr[data-activity-id]').length > 0`,
  "reload",
);
await delay(600);
await revealFormulaColumn();
await delay(350);
const reloadedHeader = await evaluate(
  `(() => { const th = [...document.querySelectorAll('th')].find(h => h.innerText.includes('Double progress')); return th ? th.innerText : null; })()`,
);
console.log("reloaded header", reloadedHeader);
await shot("63-formula-column-reloaded-en-1280");

await evaluate(
  `(() => { const trigger = [...document.querySelectorAll('[data-desktop-menu]')].find(el => el.dataset.desktopMenu === 'project'); trigger.click(); const item = document.querySelector('[data-desktop-popup="project"] [data-desktop-command="tools.formula"]'); item.click(); return true; })()`,
);
await waitFor(`document.querySelector('#cp-formula-editor [data-formula-column="formula.double_progress"]') != null`, "catalogue");
await delay(300);
await shot("64-formula-editor-catalogue-en-1280");

const catalogueScrolled = await evaluate(
  `(() => {
    const form = document.querySelector('#cp-formula-editor [data-formula-save-form]');
    if (!form) return false;
    form.scrollIntoView({ block: 'center' });
    return true;
  })()`,
);
console.log("catalogue scrolled", catalogueScrolled);
await delay(400);
await shot("67-formula-editor-saved-catalogue-en-1280");

await evaluate(
  `(() => {
    const expression = document.querySelector('#cp-formula-editor [data-formula-expression]');
    expression.scrollIntoView({ block: 'center' });
    return true;
  })()`,
);
await delay(250);

await evaluate(
  `(() => {
    const panel = document.querySelector('#cp-formula-editor');
    const input = panel.querySelector('[data-formula-expression]');
    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
    setter.call(input, '[activity.missing_field] * 2');
    input.dispatchEvent(new Event('input', { bubbles: true }));
    panel.querySelector('[data-formula-validate]').click();
    return true;
  })()`,
);
await waitFor(
  `(() => { const status = document.querySelector('#cp-formula-editor [data-formula-status]'); return status && !status.textContent.includes('Validating'); })()`,
  "invalid-validation",
);
await delay(250);
const invalidState = await evaluate(
  `JSON.stringify({ status: document.querySelector('#cp-formula-editor [data-formula-status]').textContent, result: document.querySelector('#cp-formula-editor [data-formula-result]').innerText })`,
);
console.log("invalid", invalidState);
await shot("65-formula-invalid-en-1280");

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
await revealFormulaColumn();
await delay(400);
await shot("66-formula-column-grid-fa-1280");

await send("Target.closeTarget", { targetId: target.id });
ws.close();
if (chrome) chrome.kill();
process.exit(0);
