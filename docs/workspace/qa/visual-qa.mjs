import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { setTimeout as delay } from "node:timers/promises";

const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PORT = 9333;
const BASE = "http://127.0.0.1:4174";
const OUT = "docs/workspace/screenshots/visual";
const MODE = process.argv[2] ?? "all";

const SHOTS = [
  { name: "01-activities-en-1440", width: 1440, height: 900, locale: "en", setup: "" },
  { name: "02-activities-fa-1440", width: 1440, height: 900, locale: "fa", setup: "" },
  { name: "03-activities-en-1366", width: 1366, height: 768, locale: "en", setup: "" },
  { name: "04-activities-en-1920", width: 1920, height: 1080, locale: "en", setup: "" },
  { name: "05-activities-fa-1920", width: 1920, height: 1080, locale: "fa", setup: "" },
  { name: "06-wbs-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('[data-vd-window="wbs"]').click()` },
  { name: "07-projects-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('[data-vd-window="projects"]').click()` },
  { name: "08-resources-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('[data-vd-window="resources"]').click()` },
  { name: "09-assignments-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('[data-vd-window="assignments"]').click()` },
  { name: "10-calendars-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('[data-vd-window="calendars"]').click()` },
  { name: "11-reports-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('[data-vd-window="reports"]').click()` },
  { name: "12-tracking-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('[data-vd-window="tracking"]').click()` },
  { name: "13-documents-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('[data-vd-window="documents"]').click()` },
  { name: "14-expenses-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('[data-vd-window="expenses"]').click()` },
  { name: "15-thresholds-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('[data-vd-window="thresholds"]').click()` },
  { name: "16-issues-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('[data-vd-window="issues"]').click()` },
  { name: "17-risks-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('[data-vd-window="risks"]').click()` },
  { name: "18-administration-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('[data-vd-window="administration"]').click()` },
  { name: "19-network-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('[data-vd-window="network"]').click()` },
  { name: "20-trace-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('[data-vd-window="trace"]').click()` },
  { name: "21-activity-profile-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('[data-vd-window="activity-profile"]').click()` },
  { name: "22-resource-profile-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('[data-vd-window="resource-profile"]').click()` },
  { name: "23-activity-sheet-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('[data-vd-window="activity-sheet"]').click()` },
  { name: "24-resource-sheet-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('[data-vd-window="resource-sheet"]').click()` },
  { name: "25-menu-view-open-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('[data-vd-menu="view"] .cp-vd-menu-trigger').click()` },
  { name: "26-menu-view-layouts-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('[data-vd-menu="view"] .cp-vd-menu-trigger').click(); const s=[...document.querySelectorAll('[data-vd-submenu]')].find(b=>b.textContent.includes('Layouts')); s.click()` },
  { name: "27-details-predecessors-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('[data-vd-dtab="predecessors"]').click()` },
  { name: "28-details-resources-fa-1440", width: 1440, height: 900, locale: "fa", setup: `document.querySelector('[data-vd-dtab="resources"]').click()` },
  { name: "29-dialog-columns-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('.cp-vd-btn[data-vd-dialog="columns"]').click()` },
  { name: "30-dialog-filters-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('.cp-vd-btn[data-vd-dialog="filters"]').click()` },
  { name: "31-dialog-group-sort-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('.cp-vd-btn[data-vd-dialog="group-sort"]').click()` },
  { name: "32-dialog-timescale-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('.cp-vd-btn[data-vd-dialog="timescale"]').click()` },
  { name: "33-dialog-bars-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('.cp-vd-btn[data-vd-dialog="bars"]').click()` },
  { name: "34-dialog-calendar-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('[data-vd-window="calendars"]').click(); document.querySelector('.cp-vd-btn[data-vd-dialog="calendar"]').click()` },
  { name: "35-dialog-print-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('[data-vd-window="reports"]').click(); document.querySelector('.cp-vd-btn[data-vd-dialog="print"]').click()` },
  { name: "36-dialog-shortcuts-fa-1440", width: 1440, height: 900, locale: "fa", setup: `document.querySelector('.cp-vd-menu-trigger').click(); document.querySelector('[data-vd-menu="help"] .cp-vd-menu-trigger').click(); [...document.querySelectorAll('[data-vd-menu="help"] [data-vd-action]')].find(b=>b.textContent.includes('میانبر')).click()` },
  { name: "37-gantt-day-scale-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('[data-vd-scale="day"]').click()` },
  { name: "38-activities-fa-1366", width: 1366, height: 768, locale: "fa", setup: "" },
  { name: "39-timeline-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('[data-vd-window="timeline"]').click()` },
  { name: "40-timeline-fa-1440", width: 1440, height: 900, locale: "fa", setup: `document.querySelector('[data-vd-window="timeline"]').click()` },
  { name: "41-dialog-timeline-options-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('[data-vd-window="timeline"]').click(); document.querySelector('button[data-vd-dialog="timeline-options"]').click()` },
  { name: "42-details-collapsed-en-1440", width: 1440, height: 900, locale: "en", setup: `document.querySelector('[data-vd-details-toggle]').click()` },
  { name: "43-details-collapsed-fa-1440", width: 1440, height: 900, locale: "fa", setup: `document.querySelector('[data-vd-details-toggle]').click()` },
];

async function endpointUp() {
  try { return (await fetch(`http://127.0.0.1:${PORT}/json/version`)).ok; } catch { return false; }
}

const reuse = await endpointUp();
const profile = `C:/Users/SAAMFF~1/AppData/Local/Temp/qa-chrome-${Date.now()}`;
const chrome = reuse ? null : spawn(CHROME, [
  "--headless=new",
  `--remote-debugging-port=${PORT}`,
  `--user-data-dir=${profile}`,
  "--no-first-run",
  "--disable-gpu",
  "--hide-scrollbars",
  "--window-size=1440,900",
  "about:blank",
], { stdio: "ignore" });

async function waitForEndpoint() {
  for (let i = 0; i < 80; i += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${PORT}/json/version`);
      if (response.ok) return response.json();
    } catch { /* Chrome is still starting. */ }
    await delay(250);
  }
  throw new Error("CHROME_DEVTOOLS_ENDPOINT_TIMEOUT");
}

async function connect(url) {
  const ws = new WebSocket(url);
  await new Promise((resolve, reject) => {
    ws.addEventListener("open", resolve, { once: true });
    ws.addEventListener("error", () => reject(new Error("WS_CONNECT_FAILED")), { once: true });
  });
  let nextId = 0;
  const pending = new Map();
  ws.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const { resolve, reject } = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) reject(new Error(message.error.message));
      else resolve(message.result);
    }
  });
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++nextId;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
  return { ws, send };
}

async function waitFor(send, expression, timeoutMs = 30000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const result = await send("Runtime.evaluate", { expression, returnByValue: true });
    if (result.result?.value) return;
    await delay(200);
  }
  throw new Error("PAGE_READY_TIMEOUT");
}

async function evalValue(send, expression, awaitPromise = false) {
  const result = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise });
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description ?? "EVAL_FAILED");
  return result.result?.value;
}

async function openDemo(send, locale, width, height) {
  await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
  await send("Runtime.evaluate", { expression: `localStorage.setItem('cubi:workspace-locale', ${JSON.stringify(locale)})` });
  await send("Page.navigate", { url: `${BASE}/app?view=visual` });
  await waitFor(send, "Boolean(document.querySelector('.cp-vd'))", 30000);
  await delay(350);
}

async function audit(send) {
  // Every menu command, toolbar button, window tab, detail tab and in-window
  // button is exercised in the page, and the destination it opens is recorded.
  // Elements are re-queried after every redraw: the demo replaces its markup,
  // so a reference captured before a click is stale afterwards.
  return evalValue(send, `(async () => {
    const wait = (ms) => new Promise((r) => setTimeout(r, ms));
    const result = { windows: {}, commands: [], toolbar: [], windowButtons: [], detailTabs: [], missingDialogs: [], errors: [] };
    const dialogsSeen = new Set();
    const q = (selector) => document.querySelector(selector);
    const qa = (selector) => [...document.querySelectorAll(selector)];
    const activeWindow = () => q('.cp-vd-tab.is-active')?.dataset.vdWindow ?? null;

    const closeEverything = async () => {
      const dialog = q('dialog.cp-vd-dialog[open]');
      if (dialog) { dialog.querySelector('[data-vd-close]')?.click(); await wait(12); }
      const openTrigger = q('.cp-vd-menu-trigger[aria-expanded="true"]');
      if (openTrigger) { openTrigger.click(); await wait(10); }
    };
    const goActivities = async () => {
      const tab = q('.cp-vd-tab[data-vd-window="activities"]');
      if (tab && !tab.classList.contains('is-active')) { tab.click(); await wait(15); }
    };
    const reset = async () => { await closeEverything(); await goActivities(); };
    const record = (info) => {
      const dialog = q('dialog.cp-vd-dialog[open]');
      const name = dialog?.dataset.vdDialog ?? null;
      if (name) dialogsSeen.add(name);
      result.commands.push({ ...info, dialog: name, window: activeWindow() });
      return name;
    };

    // 1. Window tabs.
    for (const id of qa('.cp-vd-tab').map((tab) => tab.dataset.vdWindow)) {
      const tab = q('.cp-vd-tab[data-vd-window="' + id + '"]');
      tab.click();
      await wait(18);
      result.windows[id] = activeWindow() === id && Boolean(q('.cp-vd-windowbody'));
    }
    await reset();

    // 2. Activity Details tabs.
    for (const id of qa('[data-vd-dtab]').map((tab) => tab.dataset.vdDtab)) {
      const tab = q('[data-vd-dtab="' + id + '"]');
      if (!tab) { result.errors.push('missing detail tab ' + id); continue; }
      tab.click();
      await wait(18);
      const active = q('[data-vd-dtab].is-active')?.dataset.vdDtab ?? null;
      const panel = q('[data-vd-dpanel]');
      result.detailTabs.push({ id, active: active === id, empty: !panel || panel.textContent.trim().length === 0 });
    }

    // 2b. Collapsible Activity Details: collapse hides the tab strip and the
    // panel, expand restores them, and the toggle stays reachable both ways.
    const detailsToggle = q('[data-vd-details-toggle]');
    if (detailsToggle) {
      detailsToggle.click();
      await wait(16);
      const body = q('#cp-vd-details-body');
      result.details = {
        collapsed: Boolean(q('.cp-vd-details.is-collapsed')),
        bodyHidden: !body || getComputedStyle(body).display === 'none',
        toggleVisible: Boolean(q('[data-vd-details-toggle]')),
        expandedAfter: null,
      };
      q('[data-vd-details-toggle]')?.click();
      await wait(16);
      result.details.expandedAfter = !q('.cp-vd-details.is-collapsed') && Boolean(q('#cp-vd-details-body'));
    } else {
      result.errors.push('missing details toggle');
    }

    // 2c. Administration sidebar sections each switch their own panel.
    q('.cp-vd-tab[data-vd-window="administration"]')?.click();
    await wait(16);
    result.adminSections = [];
    for (const id of qa('[data-vd-admin]').map((button) => button.dataset.vdAdmin)) {
      q('[data-vd-admin="' + id + '"]')?.click();
      await wait(14);
      const body = q('.cp-vd-admin > div');
      result.adminSections.push({
        id,
        active: q('[data-vd-admin].is-active')?.dataset.vdAdmin === id,
        body: Boolean(body && body.textContent.trim().length),
      });
    }
    await reset();

    // 2d. Calendar month navigation keeps the day grid aligned.
    q('.cp-vd-tab[data-vd-window="calendars"]')?.click();
    await wait(16);
    const startMonth = q('.cp-vd-cal-head strong')?.textContent ?? '';
    q('[data-vd-cal-next]')?.click();
    await wait(14);
    const nextMonth = q('.cp-vd-cal-head strong')?.textContent ?? '';
    q('[data-vd-cal-prev]')?.click();
    await wait(14);
    result.calendar = {
      startMonth,
      nextMonth,
      backMonth: q('.cp-vd-cal-head strong')?.textContent ?? '',
      cells: qa('.cp-vd-windowbody .cp-vd-cal-grid span').length,
      dataDate: q('.cp-vd-windowbody .cp-vd-cal-grid .is-today')?.textContent ?? null,
    };
    await reset();

    // 3. Toolbar buttons.
    const groupCount = qa('.cp-vd-tgroup').length;
    for (let b = 0; b < groupCount; b += 1) {
      const count = qa('.cp-vd-tgroup')[b]?.querySelectorAll('.cp-vd-tbtn').length ?? 0;
      for (let i = 0; i < count; i += 1) {
        const button = qa('.cp-vd-tgroup')[b]?.querySelectorAll('.cp-vd-tbtn')[i];
        if (!button) { result.errors.push('missing toolbar button ' + b + '/' + i); continue; }
        const label = button.title;
        button.click();
        await wait(22);
        const dialog = record({ source: 'toolbar', label });
        result.toolbar.push({ bar: b, label, dialog, window: activeWindow() });
        await reset();
      }
    }

    // 4. In-window and layout-bar buttons that open dialogs.
    for (const id of qa('.cp-vd-tab').map((tab) => tab.dataset.vdWindow)) {
      const tab = q('.cp-vd-tab[data-vd-window="' + id + '"]');
      tab.click();
      await wait(18);
      const names = qa('button[data-vd-dialog]').map((button) => button.dataset.vdDialog);
      for (const name of names) {
        const button = qa('button[data-vd-dialog]').find((candidate) => candidate.dataset.vdDialog === name);
        if (!button) { result.errors.push('missing dialog button ' + name + ' in ' + id); continue; }
        button.click();
        await wait(22);
        const opened = q('dialog.cp-vd-dialog[open]')?.dataset.vdDialog ?? null;
        if (opened) dialogsSeen.add(opened);
        result.windowButtons.push({ window: id, requested: name, opened });
        await closeEverything();
      }
    }
    await reset();

    // 5. Menu commands, including nested submenu items.
    const menuIds = qa('.cp-vd-menu').map((menu) => menu.dataset.vdMenu);
    const openMenu = async (menuId) => {
      const trigger = q('[data-vd-menu="' + menuId + '"] .cp-vd-menu-trigger');
      if (!trigger) return false;
      if (trigger.getAttribute('aria-expanded') !== 'true') { trigger.click(); await wait(14); }
      return true;
    };
    const topItems = (menuId) => qa('[data-vd-menu="' + menuId + '"] .cp-vd-popup > .cp-vd-menu-item, [data-vd-menu="' + menuId + '"] .cp-vd-popup > .cp-vd-submenu');
    const runMenuEntry = async (menuId, index, childIndex) => {
      await openMenu(menuId);
      const item = topItems(menuId)[index];
      if (!item) return null;
      if (childIndex === null) {
        const action = JSON.parse(item.dataset.vdAction ?? '{}');
        const label = item.textContent.trim();
        item.click();
        await wait(24);
        return { action, label };
      }
      item.querySelector('[data-vd-submenu]').click();
      await wait(12);
      const child = item.querySelectorAll('.cp-vd-subpopup .cp-vd-menu-item')[childIndex];
      if (!child) return null;
      const action = JSON.parse(child.dataset.vdAction ?? '{}');
      const label = child.textContent.trim();
      child.click();
      await wait(24);
      return { action, label };
    };

    for (const menuId of menuIds) {
      await openMenu(menuId);
      const entries = topItems(menuId).map((item) => ({
        submenu: item.classList.contains('cp-vd-submenu'),
        label: item.textContent.trim(),
        disabled: item.hasAttribute('disabled'),
        childCount: item.classList.contains('cp-vd-submenu') ? item.querySelectorAll('.cp-vd-subpopup .cp-vd-menu-item').length : 1,
      }));
      await closeEverything();
      for (let index = 0; index < entries.length; index += 1) {
        const entry = entries[index];
        if (entry.disabled) { result.commands.push({ menu: menuId, label: entry.label, skipped: 'disabled' }); continue; }
        for (let child = 0; child < entry.childCount; child += 1) {
          const run = await runMenuEntry(menuId, index, entry.submenu ? child : null);
          if (!run) { result.errors.push('missing menu item ' + menuId + '/' + index + '/' + child); continue; }
          record({ source: 'menu', menu: menuId, label: entry.submenu ? entry.label + ' › ' + run.label : run.label, action: run.action });
          await reset();
          if (run.action?.command?.startsWith('toolbar:')) {
            // The toggle just hid a toolbar; click the same entry again so the
            // remaining commands stay visible and reachable.
            await runMenuEntry(menuId, index, entry.submenu ? child : null);
            await closeEverything();
          }
        }
      }
    }

    // 6. Back / forward across windows.
    const go = async (id) => { const t = q('.cp-vd-tab[data-vd-window="' + id + '"]'); if (t && !t.classList.contains('is-active')) { t.click(); await wait(15); } };
    await go('wbs');
    await go('resources');
    q('[data-vd-command="back"]').click();
    await wait(18);
    const afterBack = activeWindow();
    q('[data-vd-command="forward"]').click();
    await wait(18);
    const afterForward = activeWindow();
    result.history = { afterBack, afterForward };
    await reset();

    const dialogs = qa('dialog.cp-vd-dialog').map((dialog) => dialog.dataset.vdDialog);
    result.missingDialogs = dialogs.filter((name) => !dialogsSeen.has(name));
    result.totalDialogs = dialogs.length;
    result.reachedDialogs = dialogsSeen.size;
    result.menuCount = menuIds.length;
    result.windowTabCount = Object.keys(result.windows).length;
    result.toolbarButtonCount = result.toolbar.length;
    result.failedWindows = Object.keys(result.windows).filter((id) => !result.windows[id]);
    result.failedDetailTabs = result.detailTabs.filter((tab) => !tab.active || tab.empty).map((tab) => tab.id);
    result.unopenedWindowButtons = result.windowButtons.filter((item) => item.opened !== item.requested);
    return result;
  })()`, true);
}

try {
  await waitForEndpoint();
  const target = await (await fetch(`http://127.0.0.1:${PORT}/json/new?${encodeURIComponent(`${BASE}/app?view=visual`)}`, { method: "PUT" })).json();
  const { send } = await connect(target.webSocketDebuggerUrl);
  await send("Page.enable");

  // The preview server requires a session before it serves the app shell.
  await send("Page.navigate", { url: `${BASE}/preview/login` });
  await waitFor(send, "document.readyState === 'complete'");
  const login = await send("Runtime.evaluate", {
    expression: `fetch('/preview/login', { method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded' }, body: 'role=planner' }).then(r => r.status)`,
    awaitPromise: true,
    returnByValue: true,
  });
  console.log("login", login.result?.value);

  mkdirSync(OUT, { recursive: true });

  if (MODE === "smoke") {
    await openDemo(send, "en", 1440, 900);
    const png = await send("Page.captureScreenshot", { format: "png" });
    writeFileSync(`${OUT}/00-smoke.png`, Buffer.from(png.data, "base64"));
    console.log("saved 00-smoke.png");
  } else {
    await openDemo(send, "en", 1440, 900);
    const report = await audit(send);
    writeFileSync(`${OUT}/visual-audit.json`, JSON.stringify(report, null, 2));
    console.log("audit", JSON.stringify({
      windows: Object.values(report.windows).filter(Boolean).length + "/" + Object.keys(report.windows).length,
      menus: report.menuCount,
      tabs: report.windowTabCount,
      toolbarButtons: report.toolbarButtonCount,
      commands: report.commands.length,
      reachedDialogs: report.reachedDialogs + "/" + report.totalDialogs,
      missingDialogs: report.missingDialogs,
      errors: report.errors,
    }));

    for (const shot of SHOTS) {
      await openDemo(send, shot.locale, shot.width, shot.height);
      if (shot.setup) {
        await evalValue(send, `(() => { ${shot.setup}; return true; })()`);
        await delay(300);
      }
      const png = await send("Page.captureScreenshot", { format: "png" });
      writeFileSync(`${OUT}/${shot.name}.png`, Buffer.from(png.data, "base64"));
      console.log("saved", shot.name);
    }
  }
} finally {
  chrome?.kill();
}
process.exit(0);
