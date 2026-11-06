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
const profile = `C:/Users/SAAMFF~1/AppData/Local/Temp/cubi-columns-qa-${Date.now()}`;
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

const dialogState = () =>
  evaluate(
    `(() => {
      const dialog = document.querySelector('[data-p6-columns-dialog]');
      if (!dialog) return null;
      return JSON.stringify({
        open: dialog.open,
        available: dialog.querySelectorAll('[data-columns-available-id]').length,
        selected: dialog.querySelectorAll('[data-columns-selected-id]').length,
        selectedTitles: [...dialog.querySelectorAll('[data-columns-selected-id] .cp-columns-option-title')].slice(0, 12).map(el => el.textContent),
        notice: dialog.querySelector('[data-columns-notice]')?.textContent ?? null,
        copyDisabled: dialog.querySelector('[data-columns-action="copy-from"]')?.disabled ?? null,
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

// Open via View > Columns menu to prove the real menu path.
await evaluate(
  `(() => {
    const trigger = document.querySelector('[data-desktop-menu="view"]');
    trigger.click();
    const item = document.querySelector('[data-desktop-popup="view"] [data-desktop-command="view.fields"]');
    if (!item) return false;
    item.click();
    return true;
  })()`,
);
await waitFor(`document.querySelector('[data-p6-columns-dialog]')?.open === true`, "columns-dialog");
await delay(400);
console.log("initial", await dialogState());
await shot("68-columns-dialog-en-1280");

// Select "Activity Name" and open the real Edit Column dialog.
await evaluate(
  `(() => {
    const dialog = document.querySelector('[data-p6-columns-dialog]');
    const row = [...dialog.querySelectorAll('[data-columns-selected-id]')].find(el => el.dataset.columnsSelectedId === 'activity.name');
    row.click();
    dialog.querySelector('[data-columns-action="edit"]').click();
    return true;
  })()`,
);
await waitFor(`document.querySelector('[data-p6-edit-column-dialog]')?.open === true`, "edit-column");
await delay(300);
console.log(
  "edit",
  await evaluate(
    `JSON.stringify({
      title: document.querySelector('[data-p6-edit-column-dialog] input[name="title"]').value,
      defaultTitle: document.querySelector('[data-p6-edit-column-dialog] [data-edit-default-title]').textContent,
      width: document.querySelector('[data-p6-edit-column-dialog] input[name="width"]').value,
      alignment: document.querySelector('[data-p6-edit-column-dialog] select[name="alignment"]').value,
    })`,
  ),
);
await shot("69-edit-column-dialog-en-1280");

await evaluate(`document.querySelector('[data-p6-edit-column-dialog] [data-edit-column-cancel]').click()`);
await delay(250);

// Default must replace the draft with the server-owned canonical columns.
await evaluate(`document.querySelector('[data-p6-columns-dialog] [data-columns-action="default"]').click()`);
await delay(900);
console.log("after-default", await dialogState());
await shot("70-columns-dialog-default-en-1280");

// OK persists the default layout through the real layout endpoint.
await evaluate(
  `(() => {
    const buttons = [...document.querySelectorAll('[data-p6-columns-dialog] .cp-dialog-buttons button')];
    const ok = buttons.find(button => button.classList.contains('cp-dialog-primary'));
    ok.click();
    return true;
  })()`,
);
await waitFor(`document.querySelector('[data-p6-columns-dialog]') == null`, "dialog-closed");
await delay(600);
console.log(
  "grid",
  await evaluate(
    `JSON.stringify([...document.querySelectorAll('#cp-activity-grid thead th')].map(th => th.innerText.trim()))`,
  ),
);
await shot("71-columns-saved-default-grid-en-1280");

// Reload proves the persisted layout revision is what the grid binds to.
await send("Page.reload");
await waitFor(`document.querySelectorAll('tr[data-activity-id]').length > 0`, "reload");
await delay(600);
console.log(
  "reloaded",
  await evaluate(
    `JSON.stringify([...document.querySelectorAll('#cp-activity-grid thead th')].map(th => th.innerText.trim()))`,
  ),
);

// Persian RTL pass through the toolbar Columns button.
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
await waitFor(`document.querySelector('[data-p6-columns-dialog]')?.open === true`, "columns-dialog-fa");
await delay(400);
console.log("fa", await dialogState());
console.log("dir", await evaluate(`getComputedStyle(document.querySelector('[data-p6-columns-dialog]')).direction`));
await shot("72-columns-dialog-fa-1280");

await evaluate(
  `(() => {
    const buttons = [...document.querySelectorAll('[data-p6-columns-dialog] .cp-dialog-buttons button')];
    const cancel = buttons.find(button => button.textContent.trim() === 'انصراف');
    if (cancel) cancel.click();
    return true;
  })()`,
);
await delay(300);

await send("Target.closeTarget", { targetId: target.id });
ws.close();
if (chrome) chrome.kill();
process.exit(0);
