import fs from 'node:fs';

const [windowId = 'network', locale = 'en', width = '1440', height = '900', out = '.qa-tmp/view-shot.png'] = process.argv.slice(2);
const base = 'http://127.0.0.1:9333';
const target = await (await fetch(`${base}/json/new?${encodeURIComponent('http://127.0.0.1:4174/app?view=visual')}`, { method: 'PUT' })).json();
const ws = new WebSocket(target.webSocketDebuggerUrl);
let id = 0;
const pending = new Map();
ws.addEventListener('message', (event) => {
  const msg = JSON.parse(event.data);
  if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
});
await new Promise((resolve) => ws.addEventListener('open', resolve, { once: true }));
const send = (method, params = {}) => new Promise((resolve) => { const n = ++id; pending.set(n, resolve); ws.send(JSON.stringify({ id: n, method, params })); });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
await send('Page.enable');
await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', { width: Number(width), height: Number(height), deviceScaleFactor: 2, mobile: false });
await send('Page.navigate', { url: 'http://127.0.0.1:4174/app?view=visual' });
await sleep(1300);
await send('Runtime.evaluate', { expression: `localStorage.setItem('cubi:workspace-locale','${locale}');` });
await send('Page.navigate', { url: 'http://127.0.0.1:4174/app?view=visual' });
await sleep(1600);
const result = await send('Runtime.evaluate', { expression: `(() => { const tab=[...document.querySelectorAll('[data-vd-window]')].find(b=>b.dataset.vdWindow==='${windowId}'); if(!tab) return 'no-tab'; tab.click(); return 'ok'; })()`, returnByValue: true });
console.log('window', result.result?.result?.value);
await sleep(500);
const shot = await send('Page.captureScreenshot', { format: 'png' });
fs.writeFileSync(out, Buffer.from(shot.result.data, 'base64'));
console.log('saved', out);
await send('Target.closeTarget', { targetId: target.id });
ws.close();
process.exit(0);
