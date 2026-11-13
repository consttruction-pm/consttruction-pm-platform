#!/usr/bin/env node
/**
 * Version 26 relationship acceptance (ACT-012).
 *
 * Proves in the real preview that relationships can be drawn on the Gantt
 * chart from bar edge to bar edge, exactly as the V26 Help documents
 * (finish→start FS, finish→finish FF, start→finish SF, start→start SS), that
 * the drag shows a hint naming the type that will be created, that the new
 * relationship is persisted by the authenticated relationship API and comes
 * back with its arrow after a full reload, that the arrow context menu edits
 * type and lag with optimistic revision and deletes only after confirmation,
 * that drawing is unavailable while relationship lines are hidden, and that
 * the gesture keeps its geometry in en LTR and fa RTL at 1280/1366/1920.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4201 \
 *   CUBI_TESTED_CODE_SHA=<code commit> node e2e/activity-relationships-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4201";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-13";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const suiteName = "activity-relationships-v26";
const outDir = join(artifactsDir, suiteName);
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `${suiteName}-${evidenceDate}`);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const projectId = "preview-rps-01";
const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const scheduleWrites = [];
const relationshipWrites = [];
const scenarios = [];
const screenshots = [];

function log(message) {
  process.stdout.write(`${message}\n`);
}

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

function record(id, name, status, details = {}) {
  scenarios.push({ id, name, status, at: new Date().toISOString(), ...details });
  log(`  ${status.toUpperCase()} ${id}. ${name}`);
}

async function scenario(id, name, body) {
  log(`\n[${id}] ${name}`);
  try {
    const details = (await body()) ?? {};
    record(id, name, "pass", details);
  } catch (error) {
    record(id, name, "fail", { error: String(error && error.stack ? error.stack : error) });
    throw error;
  }
}

async function capture(page, name) {
  const file = `${suiteName}/${name}.png`;
  await page.screenshot(file);
  copyFileSync(join(artifactsDir, file), join(evidenceDir, `${name}.png`));
  screenshots.push(`${name}.png`);
  return file;
}

async function setViewport(page, width, height) {
  await page.cdp.send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
  await sleep(400);
}

async function setLanguage(page, locale) {
  const changed = await page.evaluate(`(() => {
    const select = document.querySelector("[data-workspace-language]");
    if (!select) return false;
    select.value = ${JSON.stringify(locale)};
    if (select.value !== ${JSON.stringify(locale)}) return false;
    select.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  assert(changed, `language selector did not accept ${locale}`);
  await sleep(900);
}

async function clickVisible(page, selector, label) {
  const clicked = await page.evaluate(`(() => {
    const element = [...document.querySelectorAll(${JSON.stringify(selector)})]
      .find((item) => item.getClientRects().length > 0 && !item.disabled);
    if (!element) return false;
    element.click();
    return true;
  })()`);
  assert(clicked, `${label} is missing`);
  await sleep(350);
}

async function waitForLinks(page, expected, label) {
  const deadline = Date.now() + 15000;
  let latest = null;
  while (Date.now() < deadline) {
    latest = await linksState(page);
    if (latest.count === expected) return latest;
    await sleep(150);
  }
  throw new Error(`${label}: ${latest?.count} links, expected ${expected}: ${JSON.stringify(latest?.links)}`);
}

async function linksState(page) {
  return page.evaluate(`(() => ({
    count: document.querySelectorAll("#cp-gantt [data-gantt-link]").length,
    hiddenLayer: !document.querySelector("#cp-gantt .cp-gantt-links"),
    edgeHandles: document.querySelectorAll("#cp-gantt [data-gantt-link-edge]").length,
    primaryBars: document.querySelectorAll("#cp-gantt [data-gantt-bar-primary='true']").length,
    dragActive: document.querySelectorAll("[data-gantt-link-dragging]").length,
    links: [...document.querySelectorAll("#cp-gantt [data-gantt-link]")].map((path) => ({
      id: path.getAttribute("data-gantt-link"),
      type: path.getAttribute("data-link-type"),
      from: path.getAttribute("data-link-from"),
      to: path.getAttribute("data-link-to"),
      critical: path.classList.contains("is-critical"),
    })),
    lagBadges: [...document.querySelectorAll("#cp-gantt [data-gantt-lag-for]")].map((badge) => ({
      relationshipId: badge.getAttribute("data-gantt-lag-for"),
      text: (badge.textContent || "").trim(),
    })),
    dir: document.documentElement.dir || "ltr",
    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  }))()`);
}

async function barRects(page, ids) {
  return page.evaluate(`(() => {
    const result = {};
    for (const id of ${JSON.stringify(ids)}) {
      const row = document.querySelector('#cp-gantt [data-gantt-activity-id="' + id + '"]');
      const bar = row?.querySelector(".cp-gantt-bar[data-gantt-bar-primary='true']");
      if (!bar) { result[id] = null; continue; }
      const rect = bar.getBoundingClientRect();
      result[id] = { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom, width: rect.width, height: rect.height };
    }
    return result;
  })()`);
}

async function dragState(page) {
  return page.evaluate(`(() => {
    const overlay = document.querySelector("#cp-gantt svg.cp-gantt-link-preview-layer");
    const hint = document.querySelector("[data-gantt-link-hint]");
    const body = document.querySelector("#cp-gantt [data-gantt-body]");
    const bodyRect = body?.getBoundingClientRect();
    const path = document.querySelector(".cp-gantt-link-preview");
    const start = (path?.getAttribute("d") ?? "").match(/^M\\s+([\\d.]+)\\s+([\\d.]+)/);
    return {
      active: document.querySelectorAll("[data-gantt-link-dragging]").length > 0,
      previewType: overlay?.getAttribute("data-gantt-link-preview") ?? null,
      path: path?.getAttribute("d") ?? null,
      startXPercent: start ? Number(start[1]) / 10 : null,
      startY: start ? Number(start[2]) : null,
      hintVisible: Boolean(hint && !hint.hidden),
      hintText: (hint?.textContent || "").trim(),
      hintType: hint?.getAttribute("data-gantt-link-type") ?? null,
      targetRow: document.querySelector("#cp-gantt .cp-gantt-row.is-link-target")?.getAttribute("data-gantt-activity-id") ?? null,
      bodyHeight: bodyRect?.height ?? null,
      bodyWidth: bodyRect?.width ?? null,
    };
  })()`);
}

/**
 * Draws one relationship from a source bar edge to a target bar edge with
 * native pointer events, reading the live hint before release.
 */
async function drawRelationship(page, { from, fromEdge, to, toEdge }) {
  const rects = await barRects(page, [from, to]);
  assert(rects[from], `source bar ${from} is missing`);
  assert(rects[to], `target bar ${to} is missing`);
  const source = rects[from];
  const target = rects[to];
  const sx = Math.round((fromEdge === "start" ? source.left + 2 : source.right - 2) * 10) / 10;
  const sy = Math.round(((source.top + source.bottom) / 2) * 10) / 10;
  const tx = Math.round((toEdge === "start" ? target.left + 2 : target.right - 2) * 10) / 10;
  const ty = Math.round(((target.top + target.bottom) / 2) * 10) / 10;
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: sx, y: sy, button: "none", buttons: 0 });
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x: sx, y: sy, button: "left", buttons: 1, clickCount: 1 });
  await sleep(60);
  for (let step = 1; step <= 6; step += 1) {
    const x = sx + ((tx - sx) * step) / 6;
    const y = sy + ((ty - sy) * step) / 6;
    await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: Math.round(x * 10) / 10, y: Math.round(y * 10) / 10, button: "left", buttons: 1 });
    await sleep(45);
  }
  await sleep(150);
  const during = await dragState(page);
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: tx, y: ty, button: "left", buttons: 0, clickCount: 1 });
  await sleep(1200);
  return { source: { x: sx, y: sy }, target: { x: tx, y: ty }, during };
}

/** A point on the rendered arrow hit band for the given relationship. */
async function linkPoint(page, relationshipId) {
  return page.evaluate(`(() => {
    const path = [...document.querySelectorAll("#cp-gantt [data-gantt-link]")]
      .find((item) => item.getAttribute("data-gantt-link") === ${JSON.stringify(relationshipId)});
    if (!path) return null;
    let length = 0;
    try { length = path.getTotalLength(); } catch { return null; }
    const matrix = path.getScreenCTM();
    if (!length || !matrix) return null;
    for (const fraction of [0.5, 0.35, 0.65, 0.25, 0.75, 0.15, 0.85]) {
      const local = path.getPointAtLength(length * fraction);
      const x = Math.round(local.x * matrix.a + local.y * matrix.c + matrix.e);
      const y = Math.round(local.x * matrix.b + local.y * matrix.d + matrix.f);
      if (x < 1 || y < 1 || x >= innerWidth - 1 || y >= innerHeight - 1) continue;
      const hit = document.elementFromPoint(x, y);
      const owner = hit?.closest?.("[data-gantt-link],[data-gantt-link-hit]");
      const ownerId = owner?.getAttribute("data-gantt-link") ?? owner?.getAttribute("data-gantt-link-hit");
      if (ownerId === ${JSON.stringify(relationshipId)}) return { x, y };
    }
    return null;
  })()`);
}

async function rightClickAt(page, x, y) {
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y, button: "none", buttons: 0 });
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "right", buttons: 2, clickCount: 1 });
  await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "right", buttons: 0, clickCount: 1 });
  await sleep(250);
}

async function openArrowMenu(page, relationshipId) {
  const point = await linkPoint(page, relationshipId);
  assert(point, `no visible arrow hit point for ${relationshipId}`);
  await rightClickAt(page, point.x, point.y);
  const menu = await page.evaluate(`(() => {
    const menu = document.querySelector(".cp-context-menu");
    if (!menu) return null;
    return {
      commands: [...menu.querySelectorAll("[data-activity-menu-command]")].map((item) => item.getAttribute("data-activity-menu-command")),
      labels: [...menu.querySelectorAll("[data-activity-menu-command]")].map((item) => (item.textContent || "").trim()),
    };
  })()`);
  assert(menu, `the relationship menu did not open for ${relationshipId}`);
  return menu;
}

async function clickMenuCommand(page, command) {
  const clicked = await page.evaluate(`(() => {
    const item = document.querySelector('[data-activity-menu-command="${command}"]');
    if (!item || item.disabled) return false;
    item.click();
    return true;
  })()`);
  assert(clicked, `menu command ${command} is missing or disabled`);
  await sleep(500);
}

async function findLinkByEnds(page, from, to) {
  const state = await linksState(page);
  return state.links.find((link) => link.from === from && link.to === to) ?? null;
}

function assertNoScheduleWrites(label) {
  const writes = scheduleWrites.splice(0);
  assert(writes.length === 0, `${label}: relationship gestures wrote schedule/activity data: ${writes.map((item) => `${item.method} ${item.url}`).join(", ")}`);
}

async function main() {
  const health = await waitForHttp(`${baseUrl}/preview/health`, 30000);
  if (!(health.status === "ok" || health.status === 200)) throw new Error(`preview health ${health.status}`);
  const chrome = await launchChrome();
  const page = new Page(chrome.cdp);
  await page.initialize();
  page.cdp.on("Runtime.exceptionThrown", (params) => {
    exceptions.push(params.exceptionDetails?.exception?.description ?? params.exceptionDetails?.text ?? "exception");
  });
  page.cdp.on("Runtime.consoleAPICalled", (params) => {
    if (params.type !== "error") return;
    consoleErrors.push((params.args ?? []).map((arg) => arg.value ?? arg.description ?? arg.type).join(" "));
  });
  page.cdp.on("Network.responseReceived", (params) => {
    const url = params.response?.url ?? "";
    if (url.includes("/api/") && params.response.status >= 500) apiFailures.push({ status: params.response.status, url });
  });
  page.cdp.on("Network.requestWillBeSent", (params) => {
    const method = params.request?.method ?? "GET";
    const url = params.request?.url ?? "";
    if (method === "GET" || method === "HEAD" || !url.includes("/api/")) return;
    if (url.includes("/p6/relationships")) {
      relationshipWrites.push({ method, url, postData: params.request?.postData ?? null });
      return;
    }
    if (url.includes("/p6/schedule/") || url.includes("/activities/")) scheduleWrites.push({ method, url });
  });

  const report = {
    contract: "cubi-activity-relationships-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
  };

  function writeReport() {
    report.scenarios = scenarios;
    report.relationshipWrites = relationshipWrites;
    report.scheduleWrites = scheduleWrites;
    report.passed = scenarios.filter((entry) => entry.status === "pass").length;
    report.failed = scenarios.filter((entry) => entry.status === "fail").length;
    const json = JSON.stringify(report, null, 2);
    writeFileSync(join(outDir, `${suiteName}.json`), json);
    writeFileSync(join(evidenceDir, `${suiteName}.json`), json);
  }

  try {
    await setViewport(page, 1366, 768);
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
    const hasPersonas = await page.evaluate('Boolean(document.querySelector(".persona"))');
    if (!hasPersonas) {
      await page.evaluate('fetch("/preview/logout", { method: "POST", redirect: "manual" }).then((response) => response.status)', { awaitPromise: true });
      await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, ".persona", "persona cards after sign out");
    }
    const plannerClicked = await page.evaluate(`(() => {
      const button = [...document.querySelectorAll("form button")].find((item) => (item.textContent || "").trim().startsWith("Planner"));
      if (!button) return false;
      button.click();
      return true;
    })()`);
    assert(plannerClicked, "Planner login button is missing");
    await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
    await page.click('[data-project-id="preview-rps-01"]');
    await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
    await sleep(1800);

    await scenario("01", "the persisted network draws every arrow with its stored type and exposes drag handles", async () => {
      const initial = await waitForLinks(page, 15, "initial relationship arrows");
      const types = new Set(initial.links.map((link) => link.type));
      assert([...types].every((type) => ["FS", "SS", "FF", "SF"].includes(type)), `unexpected type in ${JSON.stringify([...types])}`);
      assert(types.has("FS") && types.has("SS"), `stored fixture types are ${JSON.stringify([...types])}`);
      assert(initial.edgeHandles === initial.primaryBars * 2, `${initial.edgeHandles} edge handles for ${initial.primaryBars} primary bars`);
      assert(!initial.hiddenLayer, "the relationship layer is hidden at rest");
      assert(initial.lagBadges.length === 1 && initial.lagBadges[0].text === "+5d", `existing lag badge is ${JSON.stringify(initial.lagBadges)}`);
      assertNoScheduleWrites("loading the network");
      await capture(page, "01-persisted-arrows-en-1366");
      return { links: initial.count, types: [...types].sort(), edgeHandles: initial.edgeHandles, primaryBars: initial.primaryBars, lagBadges: initial.lagBadges };
    });

    await scenario("02", "drawing finish→start creates an FS relationship with a live type hint", async () => {
      const postsBefore = relationshipWrites.filter((write) => write.method === "POST").length;
      // Escape must abandon a drag without persisting anything.
      const abortRects = await barRects(page, ["A110", "A130"]);
      const ax = Math.round(abortRects.A110.right - 2);
      const ay = Math.round((abortRects.A110.top + abortRects.A110.bottom) / 2);
      await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: ax, y: ay, button: "none", buttons: 0 });
      await page.cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x: ax, y: ay, button: "left", buttons: 1, clickCount: 1 });
      await sleep(60);
      await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: ax + 40, y: ay + 20, button: "left", buttons: 1 });
      await sleep(80);
      await page.cdp.send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27, nativeVirtualKeyCode: 27 });
      await page.cdp.send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27, nativeVirtualKeyCode: 27 });
      await sleep(120);
      const aborted = await dragState(page);
      await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: ax + 40, y: ay + 20, button: "left", buttons: 0, clickCount: 1 });
      await sleep(400);
      assert(!aborted.active && aborted.previewType === null && aborted.hintType === null, `Escape left the drag active: ${JSON.stringify(aborted)}`);
      assert(relationshipWrites.filter((write) => write.method === "POST").length === postsBefore, "Escape still persisted a relationship");
      const drawn = await drawRelationship(page, { from: "A100", fromEdge: "finish", to: "A120", toEdge: "start" });
      assert(drawn.during.active, "the drag did not start on the bar edge");
      assert(drawn.during.previewType === "FS", `preview type is ${drawn.during.previewType}`);
      assert(drawn.during.hintVisible && drawn.during.hintType === "FS", `hint is ${JSON.stringify(drawn.during)}`);
      assert(/^FS — Finish to Start$/.test(drawn.during.hintText), `hint text is ${JSON.stringify(drawn.during.hintText)}`);
      assert(drawn.during.targetRow === "A120", `highlighted target is ${drawn.during.targetRow}`);
      assert(drawn.during.startY !== null, "the preview has no source position");
      const after = await waitForLinks(page, 16, "FS creation");
      const created = after.links.find((link) => link.from === "A100" && link.to === "A120");
      assert(created && created.type === "FS", `created link is ${JSON.stringify(created)}`);
      const posts = relationshipWrites.filter((write) => write.method === "POST");
      const post = posts[postsBefore] ?? null;
      assert(posts.length === postsBefore + 1 && post, `relationship POSTs ${JSON.stringify(posts)}`);
      const payload = JSON.parse(post.postData || "{}");
      assert(payload.predecessor_id === "A100" && payload.successor_id === "A120", `POST payload ${post.postData}`);
      assert(payload.relationship_type === "FS" && payload.lag_value === "0" && payload.lag_unit === "working-day", `POST payload ${post.postData}`);
      assertNoScheduleWrites("drawing FS");
      await capture(page, "02-drag-hint-fs-en-1366");
      return { during: drawn.during, id: created.id, post: payload };
    });

    await scenario("03", "drawing finish→finish creates an FF relationship", async () => {
      const drawn = await drawRelationship(page, { from: "A110", fromEdge: "finish", to: "A140", toEdge: "finish" });
      assert(drawn.during.previewType === "FF" && drawn.during.hintType === "FF", `FF hint state ${JSON.stringify(drawn.during)}`);
      const after = await waitForLinks(page, 17, "FF creation");
      const created = after.links.find((link) => link.from === "A110" && link.to === "A140");
      assert(created && created.type === "FF", `created link is ${JSON.stringify(created)}`);
      assertNoScheduleWrites("drawing FF");
      return { id: created.id, during: { hint: drawn.during.hintText, target: drawn.during.targetRow } };
    });

    await scenario("04", "drawing start→start creates an SS relationship", async () => {
      const drawn = await drawRelationship(page, { from: "A120", fromEdge: "start", to: "A145", toEdge: "start" });
      assert(drawn.during.previewType === "SS" && drawn.during.hintType === "SS", `SS hint state ${JSON.stringify(drawn.during)}`);
      const after = await waitForLinks(page, 18, "SS creation");
      const created = after.links.find((link) => link.from === "A120" && link.to === "A145");
      assert(created && created.type === "SS", `created link is ${JSON.stringify(created)}`);
      assertNoScheduleWrites("drawing SS");
      return { id: created.id, during: { hint: drawn.during.hintText, target: drawn.during.targetRow } };
    });

    await scenario("05", "drawing start→finish creates an SF relationship", async () => {
      const drawn = await drawRelationship(page, { from: "A140", fromEdge: "start", to: "A150", toEdge: "finish" });
      assert(drawn.during.previewType === "SF" && drawn.during.hintType === "SF", `SF hint state ${JSON.stringify(drawn.during)}`);
      const after = await waitForLinks(page, 19, "SF creation");
      const created = after.links.find((link) => link.from === "A140" && link.to === "A150");
      assert(created && created.type === "SF", `created link is ${JSON.stringify(created)}`);
      assertNoScheduleWrites("drawing SF");
      await capture(page, "03-drawn-four-types-en-1366");
      return { id: created.id, during: { hint: drawn.during.hintText, target: drawn.during.targetRow } };
    });

    await scenario("06", "every drawn relationship survives a full reload with its type and endpoint", async () => {
      await page.reload();
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows after reload");
      await sleep(1500);
      const state = await waitForLinks(page, 19, "relationships after reload");
      const expected = [
        ["A100", "A120", "FS"],
        ["A110", "A140", "FF"],
        ["A120", "A145", "SS"],
        ["A140", "A150", "SF"],
      ];
      for (const [from, to, type] of expected) {
        const link = state.links.find((entry) => entry.from === from && entry.to === to);
        assert(link && link.type === type, `${from}→${to} after reload is ${JSON.stringify(link)}`);
      }
      assertNoScheduleWrites("reloading the drawn network");
      await capture(page, "04-persisted-after-reload-en-1366");
      return { links: state.count, expected };
    });

    await scenario("07", "the arrow context menu edits type and lag through optimistic revision", async () => {
      const created = await findLinkByEnds(page, "A100", "A120");
      assert(created, "the FS relationship is missing before editing");
      const patchesBefore = relationshipWrites.filter((write) => write.method === "PATCH").length;
      const menu = await openArrowMenu(page, created.id);
      assert(menu.commands.includes("relationship-edit") && menu.commands.includes("relationship-delete"), `arrow menu commands ${JSON.stringify(menu.commands)}`);
      assert(menu.commands.includes("relationship-predecessor") && menu.commands.includes("relationship-successor"), `arrow menu is missing navigation ${JSON.stringify(menu.commands)}`);
      await clickMenuCommand(page, "relationship-edit");
      const opened = await page.waitFor(
        `Boolean(document.querySelector('[data-relationship-edit-form="${created.id}"]'))`,
        "relationship editor from the arrow menu",
        10000,
      );
      assert(opened, "the relationship editor did not open");
      const saved = await page.evaluate(`(() => {
        const form = document.querySelector('[data-relationship-edit-form="${created.id}"]');
        if (!form) return "missing";
        form.querySelector('[name="relationship_type"]').value = "SS";
        form.querySelector('[name="lag_value"]').value = "2";
        form.querySelector('[name="lag_unit"]').value = "working-day";
        const revision = Number(form.getAttribute("data-relationship-revision"));
        form.requestSubmit();
        return revision;
      })()`);
      assert(typeof saved === "number" && saved > 0, `editor revision ${saved}`);
      let updated = null;
      for (let attempt = 0; attempt < 80; attempt += 1) {
        await sleep(200);
        updated = await linksState(page);
        const link = updated.links.find((entry) => entry.id === created.id);
        const badge = updated.lagBadges.find((entry) => entry.relationshipId === created.id);
        if (link?.type === "SS" && badge?.text === "+2d") break;
      }
      const edited = updated.links.find((entry) => entry.id === created.id);
      const badge = updated.lagBadges.find((entry) => entry.relationshipId === created.id);
      assert(edited?.type === "SS", `edited arrow type is ${JSON.stringify(edited)}`);
      assert(badge?.text === "+2d", `edited lag badge is ${JSON.stringify(badge)}`);
      const patches = relationshipWrites.filter((write) => write.method === "PATCH");
      const patch = patches[patchesBefore] ?? null;
      assert(patches.length === patchesBefore + 1 && patch, `relationship PATCHes ${JSON.stringify(patches)}`);
      const payload = JSON.parse(patch.postData || "{}");
      assert(payload.expected_revision === saved, `PATCH expected_revision ${payload.expected_revision}, editor revision ${saved}`);
      assert(payload.relationship_type === "SS" && payload.lag_value === "2", `PATCH payload ${patch.postData}`);
      assertNoScheduleWrites("editing the relationship");
      await page.reload();
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows after edit reload");
      await sleep(1500);
      const reloaded = await waitForLinks(page, 19, "edited relationship after reload");
      const persisted = reloaded.links.find((entry) => entry.id === created.id);
      const persistedBadge = reloaded.lagBadges.find((entry) => entry.relationshipId === created.id);
      assert(persisted?.type === "SS" && persistedBadge?.text === "+2d", `reloaded relationship is ${JSON.stringify(persisted)} / ${JSON.stringify(persistedBadge)}`);
      await capture(page, "05-edited-type-and-lag-en-1366");
      return { id: created.id, expectedRevision: saved, patch: payload, type: persisted.type, lag: persistedBadge.text };
    });

    await scenario("08", "the arrow context menu deletes only after confirmation and the removal persists", async () => {
      const doomed = await findLinkByEnds(page, "A140", "A150");
      assert(doomed, "the SF relationship is missing before delete");
      const deletesBefore = relationshipWrites.filter((write) => write.method === "DELETE").length;
      await page.evaluate("window.confirm = () => false");
      const menu = await openArrowMenu(page, doomed.id);
      assert(menu.commands.includes("relationship-delete"), `arrow menu commands ${JSON.stringify(menu.commands)}`);
      await clickMenuCommand(page, "relationship-delete");
      await sleep(600);
      const unchanged = await linksState(page);
      assert(unchanged.count === 19, `cancelled delete changed the network to ${unchanged.count}`);
      assert(relationshipWrites.filter((write) => write.method === "DELETE").length === deletesBefore, "a cancelled delete still sent DELETE");
      await page.evaluate("window.confirm = () => true");
      await openArrowMenu(page, doomed.id);
      await clickMenuCommand(page, "relationship-delete");
      const after = await waitForLinks(page, 18, "delete of the SF relationship");
      assert(!after.links.some((entry) => entry.id === doomed.id), "the deleted relationship still draws");
      assert(relationshipWrites.filter((write) => write.method === "DELETE").length === deletesBefore + 1, "no relationship DELETE was observed");
      assertNoScheduleWrites("deleting the relationship");
      await page.reload();
      await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows after delete reload");
      await sleep(1500);
      const reloaded = await waitForLinks(page, 18, "deleted relationship after reload");
      assert(!reloaded.links.some((entry) => entry.id === doomed.id), "the deleted relationship returned after reload");
      await capture(page, "06-deleted-arrow-en-1366");
      return { id: doomed.id, remaining: reloaded.count };
    });

    await scenario("09", "relationship lines hidden also disable drawing and the gestures persist nothing", async () => {
      const writesBeforeHidden = relationshipWrites.length;
      await clickVisible(page, "[data-gantt-relationships-toggle]", "relationship lines toggle");
      const hidden = await page.waitFor(
        'document.querySelector("#cp-gantt .cp-gantt-links") === null && document.querySelectorAll("#cp-gantt [data-gantt-link-edge]").length === 0',
        "relationship lines hidden",
        10000,
      );
      assert(hidden, "hiding relationship lines left the layer or handles in place");
      const rects = await barRects(page, ["A150", "A190"]);
      assert(rects.A150 && rects.A190, "bars are missing with relationships hidden");
      const sx = Math.round(rects.A150.right - 2);
      const sy = Math.round((rects.A150.top + rects.A150.bottom) / 2);
      const tx = Math.round(rects.A190.left + 2);
      const ty = Math.round((rects.A190.top + rects.A190.bottom) / 2);
      await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: sx, y: sy, button: "none", buttons: 0 });
      await page.cdp.send("Input.dispatchMouseEvent", { type: "mousePressed", x: sx, y: sy, button: "left", buttons: 1, clickCount: 1 });
      await sleep(80);
      for (let step = 1; step <= 4; step += 1) {
        await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseMoved", x: Math.round(sx + ((tx - sx) * step) / 4), y: Math.round(sy + ((ty - sy) * step) / 4), button: "left", buttons: 1 });
        await sleep(45);
      }
      const during = await dragState(page);
      await page.cdp.send("Input.dispatchMouseEvent", { type: "mouseReleased", x: tx, y: ty, button: "left", buttons: 0, clickCount: 1 });
      await sleep(700);
      assert(!during.active, "a relationship drag started while lines were hidden");
      assert(during.previewType === null && during.hintType === null, `hidden-layer drag produced ${JSON.stringify(during)}`);
      assert(relationshipWrites.length === writesBeforeHidden, `hidden-layer drag wrote relationships: ${JSON.stringify(relationshipWrites.slice(writesBeforeHidden))}`);
      const state = await linksState(page);
      assert(state.count === 0 && state.hiddenLayer, `hidden state is ${JSON.stringify({ count: state.count, hidden: state.hiddenLayer })}`);
      await clickVisible(page, "[data-gantt-relationships-toggle]", "relationship lines toggle back");
      await page.waitFor('Boolean(document.querySelector("#cp-gantt .cp-gantt-links"))', "relationship lines restored", 10000);
      const restored = await waitForLinks(page, 18, "relationships restored after toggling back");
      assertNoScheduleWrites("hidden relationship lines");
      return { hiddenCount: state.count, restored: restored.count, writes: relationshipWrites.length };
    });

    await scenario("10", "fa RTL at 1280 draws from the correct physical edges", async () => {
      await setViewport(page, 1280, 720);
      await setLanguage(page, "fa");
      const rtlPostsBefore = relationshipWrites.filter((write) => write.method === "POST").length;
      const drawn = await drawRelationship(page, { from: "A150", fromEdge: "finish", to: "A190", toEdge: "start" });
      assert(drawn.during.active, "the RTL drag did not start");
      assert(drawn.during.previewType === "FS", `RTL preview type is ${drawn.during.previewType}`);
      assert(drawn.during.hintType === "FS", `RTL hint type is ${drawn.during.hintType}`);
      assert(drawn.during.hintText.includes("پایان به شروع"), `RTL hint text is ${JSON.stringify(drawn.during.hintText)}`);
      const after = await waitForLinks(page, 19, "RTL relationship creation");
      const created = after.links.find((link) => link.from === "A150" && link.to === "A190");
      assert(created && created.type === "FS", `RTL created link is ${JSON.stringify(created)}`);
      assert(after.dir === "rtl", `document direction is ${after.dir}`);
      assert(after.overflow <= 1, `RTL layout overflows by ${after.overflow}px`);
      assertNoScheduleWrites("drawing in RTL");
      await capture(page, "07-drag-fa-rtl-1280");
      assert(relationshipWrites.filter((write) => write.method === "POST").length === rtlPostsBefore + 1, "RTL creation did not send exactly one POST");
      return { id: created.id, hint: drawn.during.hintText, dir: after.dir, overflow: after.overflow };
    });

    await scenario("11", "en at 1920 keeps the same edge semantics and layout", async () => {
      await setViewport(page, 1920, 1080);
      await setLanguage(page, "en");
      const drawn = await drawRelationship(page, { from: "A190", fromEdge: "start", to: "A210", toEdge: "start" });
      assert(drawn.during.previewType === "SS", `wide preview type is ${drawn.during.previewType}`);
      assert(drawn.during.hintText === "SS — Start to Start", `wide hint text is ${JSON.stringify(drawn.during.hintText)}`);
      const after = await waitForLinks(page, 20, "wide relationship creation");
      const created = after.links.find((link) => link.from === "A190" && link.to === "A210");
      assert(created && created.type === "SS", `wide created link is ${JSON.stringify(created)}`);
      assert(after.dir === "ltr", `document direction is ${after.dir}`);
      assert(after.overflow <= 1, `wide layout overflows by ${after.overflow}px`);
      assertNoScheduleWrites("drawing at 1920");
      await capture(page, "08-drawn-en-1920");
      return { id: created.id, links: after.count, overflow: after.overflow };
    });

    assert(exceptions.length === 0, `runtime exceptions: ${exceptions.join(" | ")}`);
    assert(consoleErrors.length === 0, `console errors: ${consoleErrors.join(" | ")}`);
    assert(apiFailures.length === 0, `API 5xx: ${JSON.stringify(apiFailures)}`);
  } finally {
    writeReport();
    await chrome.stop();
  }
}

main().then(() => {
  log(`\n${scenarios.filter((entry) => entry.status === "pass").length}/${scenarios.length} scenarios passed`);
  process.exit(0);
}).catch((error) => {
  log(`\nFAILED: ${error && error.stack ? error.stack : error}`);
  process.exit(1);
});
