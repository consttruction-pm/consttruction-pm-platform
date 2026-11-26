#!/usr/bin/env node
/**
 * Activity Details — tab and behaviour acceptance on the real runtime.
 *
 * Proves the pane that the compliance matrix and Help traceability describe:
 * seventeen tabs in the canonical order with a single materialized panel, the
 * pane following the selected activity, previous/next navigation, tab-switch
 * and reload persistence, the full Customize Tabs dialog (move, remove, Add
 * All/Remove All guard, Default, Apply, Cancel), the per-window visibility
 * preference (hiding Details in Activities must not hide it in another window),
 * and en/LTR plus fa/RTL layout at the review sizes.
 *
 * The Arrow-key tab navigation is recorded as a known gap: it is not present on
 * this baseline and is implemented in the open V30 branch (#2048), so this
 * suite does not rebuild or claim it.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4228 node e2e/activity-details-behavior-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4228";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-26";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const outDir = join(artifactsDir, "activity-details-behavior-v26");
const evidenceDir = join(artifactsDir, "..", "..", "..", "..", "docs", "workspace", "evidence", `activity-details-behavior-v26-${evidenceDate}`);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const EXPECTED_TABS = [
  "general", "status", "resources", "predecessors", "successors", "relationships",
  "codes", "notebook", "steps", "wps-docs", "expenses", "issues", "risks",
  "summary", "udfs", "update-history", "calendar",
];

const scenarios = [];
const screenshots = [];
const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const knownGaps = [];

function log(message) {
  process.stdout.write(`${message}\n`);
}

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

async function scenario(id, name, body) {
  log(`\n[${id}] ${name}`);
  try {
    const details = (await body()) ?? {};
    scenarios.push({ id, name, status: "pass", at: new Date().toISOString(), ...details });
    log(`  PASS ${id}`);
  } catch (error) {
    scenarios.push({ id, name, status: "fail", at: new Date().toISOString(), error: String(error?.stack ?? error) });
    throw error;
  }
}

async function capture(page, name) {
  const file = `activity-details-behavior-v26/${name}.png`;
  await page.screenshot(file);
  copyFileSync(join(artifactsDir, file), join(evidenceDir, `${name}.png`));
  screenshots.push(`${name}.png`);
}

async function setViewport(page, width, height) {
  await page.cdp.send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
  await sleep(400);
}

async function setLanguage(page, locale) {
  await page.evaluate(`(() => {
    const select = document.querySelector("[data-workspace-language]");
    if (!select) return false;
    select.value = ${JSON.stringify(locale)};
    if (select.value !== ${JSON.stringify(locale)}) return false;
    select.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  await sleep(1500);
}

async function selectActivity(page, id) {
  const clicked = await page.evaluate(`(() => {
    const row = [...document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]")].find((row) => row.dataset.activityId === ${JSON.stringify(id)});
    if (!row) return false;
    row.click();
    return true;
  })()`);
  assert(clicked, `activity ${id} is not in the grid`);
  await sleep(1600);
}

async function activateWindow(page, key) {
  const clicked = await page.evaluate(`(() => {
    const tab = document.querySelector('[data-window-tab="${key}"]');
    if (!tab) return false;
    tab.click();
    return true;
  })()`);
  assert(clicked, `window tab ${key} is missing`);
  await sleep(1700);
}

function paneStateExpression(extra = "") {
  return `(() => {
    const pane = document.querySelector("#cp-details");
    const tabs = [...document.querySelectorAll("#cp-details [data-detail-tab]")];
    const panels = [...document.querySelectorAll("#cp-details [data-detail-panel]")];
    const toggle = [...document.querySelectorAll(".cp-details-toggle")].find((button) => button.getClientRects().length);
    const active = tabs.find((tab) => tab.getAttribute("aria-selected") === "true");
    return {
      paneVisible: !!pane && pane.getClientRects().length > 0 && !pane.hidden,
      tabs: tabs.map((tab) => tab.dataset.detailTab),
      labels: tabs.map((tab) => tab.textContent.trim()),
      active: active?.dataset.detailTab ?? null,
      materialized: panels.filter((panel) => !panel.hidden && panel.innerHTML.trim().length > 0).map((panel) => panel.dataset.detailPanel),
      roving: tabs.filter((tab) => tab.tabIndex === 0).map((tab) => tab.dataset.detailTab),
      tabIndexes: tabs.map((tab) => tab.tabIndex),
      toggle: toggle ? { pressed: toggle.getAttribute("aria-pressed"), title: toggle.getAttribute("title"), label: toggle.getAttribute("aria-label") } : null,
      selected: document.querySelector("#cp-details .cp-detail-selected")?.textContent?.trim() ?? null,
      storage: Object.fromEntries(Object.keys(localStorage).filter((key) => key.includes("details-visible")).map((key) => [key, localStorage.getItem(key)])),
      window: document.querySelector('[data-window-tab][aria-selected="true"]')?.dataset.windowTab ?? null,
      ${extra}
    };
  })()`;
}

async function panelText(page, tab) {
  return page.evaluate(`(() => {
    const panel = document.querySelector('#cp-details [data-detail-panel="${tab}"]');
    return (panel?.innerText || "").replace(/\\s+/g, " ").trim();
  })()`);
}

async function main() {
  const health = await waitForHttp(`${baseUrl}/preview/health`, 30000);
  if (!(health.status === "ok" || health.status === 200)) throw new Error(`preview health ${health.status}`);

  const chrome = await launchChrome();
  const page = new Page(chrome.cdp);
  await page.initialize();
  page.cdp.on("Runtime.exceptionThrown", (params) => {
    exceptions.push(params.exceptionDetails?.exception?.description ?? params.exceptionDetails?.text ?? "unknown exception");
  });
  page.cdp.on("Runtime.consoleAPICalled", (params) => {
    if (params.type !== "error") return;
    consoleErrors.push((params.args ?? []).map((arg) => arg.value ?? arg.description ?? arg.type).join(" "));
  });
  page.cdp.on("Network.responseReceived", (params) => {
    const url = params.response?.url ?? "";
    if (url.includes("/api/") && params.response.status >= 500) {
      apiFailures.push({ status: params.response.status, url });
    }
  });

  const report = {
    contract: "cubi-activity-details-behavior-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    capturedAt: new Date().toISOString(),
    scenarios,
    screenshots,
    knownGaps,
    exceptions,
    consoleErrors,
    apiFailures,
  };

  try {
    await setViewport(page, 1440, 900);
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, null, "login");
    const persona = await page.evaluate(`(() => {
      const button = document.querySelector('button[name="role"][value="admin"]');
      if (!button) return false;
      button.click();
      return true;
    })()`);
    assert(persona, "admin persona is missing");
    await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
    await page.click('[data-project-id="preview-rps-01"]');
    await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
    await sleep(1700);

    await scenario("01", "the pane exposes seventeen tabs in the canonical order with one materialized panel", async () => {
      const state = await page.evaluate(paneStateExpression());
      assert(state.tabs.length === EXPECTED_TABS.length, `expected 17 tabs, got ${state.tabs.length}`);
      assert(JSON.stringify(state.tabs) === JSON.stringify(EXPECTED_TABS), `tab order is ${JSON.stringify(state.tabs)}`);
      assert(state.active === "general", `default active tab is ${state.active}`);
      assert(state.materialized.length === 1 && state.materialized[0] === "general", `materialized panels: ${JSON.stringify(state.materialized)}`);
      assert(state.roving.length === 1 && state.roving[0] === "general", `roving tabindex is ${JSON.stringify(state.roving)}`);
      await capture(page, "01-tabs-en-1440");
      return { tabs: state.tabs.length, active: state.active, materialized: state.materialized };
    });

    await scenario("02", "the pane follows the selected activity and shows its authoritative values", async () => {
      await selectActivity(page, "A100");
      const first = await page.evaluate(paneStateExpression());
      assert(first.selected === "A100", `selected identity is ${first.selected}`);
      const general = await panelText(page, "general");
      assert(general.includes("Task Dependent"), `General is missing the stored activity type: ${general.slice(0, 120)}`);
      assert(general.includes("Project management"), "General is missing the WBS element");
      assert(!general.includes("ACTIVITY TYPE Not available"), "a stored activity type was reported as not available");
      const status = await page.evaluate(`(() => {
        document.querySelector('#cp-details [data-detail-tab="status"]').click();
        const panel = document.querySelector('#cp-details [data-detail-panel="status"]');
        return (panel?.innerText || "").replace(/\\s+/g, " ").trim();
      })()`);
      assert(/PERCENT COMPLETE\s+100/.test(status), `Status did not show the stored percent complete: ${status.slice(0, 160)}`);
      assert(/ACTUAL START\s+\d{4}-\d{2}-\d{2}/.test(status), "Status did not show the stored actual start");
      await capture(page, "02-selection-a100-en-1440");

      await selectActivity(page, "A110");
      const second = await page.evaluate(paneStateExpression());
      assert(second.selected === "A110", `selected identity after the second click is ${second.selected}`);
      await page.evaluate(`document.querySelector('#cp-details [data-detail-tab="general"]').click()`);
      await sleep(400);
      const general2 = await panelText(page, "general");
      assert(!general2.includes("Project kickoff"), "the previous activity's name leaked into the new selection");
      assert(general2.length > 60, "the General tab was blank for the second activity");
      return { first: first.selected, second: second.selected };
    });

    await scenario("03", "previous and next navigation moves the selection and keeps the pane content in sync", async () => {
      await selectActivity(page, "A100");
      const before = await page.evaluate(`(() => {
        const next = document.querySelector("#cp-details [data-details-next]");
        return { target: next?.dataset.detailsNext, disabled: next?.disabled };
      })()`);
      assert(before.target === "A110" && before.disabled === false, `next control state is ${JSON.stringify(before)}`);
      await page.evaluate(`document.querySelector("#cp-details [data-details-next]").click()`);
      await sleep(1500);
      const afterNext = await page.evaluate(`document.querySelector("#cp-details .cp-detail-selected")?.textContent?.trim()`);
      assert(afterNext === "A110", `next moved to ${afterNext}`);
      await page.evaluate(`document.querySelector("#cp-details [data-details-prev]").click()`);
      await sleep(1500);
      const afterPrev = await page.evaluate(`document.querySelector("#cp-details .cp-detail-selected")?.textContent?.trim()`);
      assert(afterPrev === "A100", `previous moved to ${afterPrev}`);
      await capture(page, "03-navigation-en-1440");
      return { next: before.target, afterNext, afterPrev };
    });

    await scenario("04", "every data tab settles into rows or an explicit notice, never an empty claim", async () => {
      await selectActivity(page, "A130");
      const results = [];
      for (const tab of ["resources", "expenses", "issues", "risks", "steps", "udfs", "update-history"]) {
        await page.evaluate(`document.querySelector('#cp-details [data-detail-tab="${tab}"]').click()`);
        let text = "";
        for (let attempt = 0; attempt < 24; attempt += 1) {
          await sleep(300);
          text = await panelText(page, tab);
          if (text.length > 20 && !/have not been read yet/i.test(text)) break;
        }
        assert(text.length > 20, `${tab} rendered nothing`);
        assert(!/read error|failed to read|HTTP 5\d\d/i.test(text), `${tab} reported a read failure: ${text.slice(0, 160)}`);
        assert(!/have not been read yet/i.test(text), `${tab} never started its authoritative read`);
        results.push({ tab, length: text.length, first: text.slice(0, 90) });
      }
      await capture(page, "04-data-tabs-en-1440");
      return { tabs: results.map((item) => item.tab) };
    });

    await scenario("05", "switching tabs keeps the grid scroll position and the active tab survives a reload", async () => {
      await page.evaluate(`(() => {
        const grid = document.querySelector("#cp-activity-grid");
        let scroller = grid?.parentElement ?? null;
        while (scroller && scroller.scrollHeight <= scroller.clientHeight && scroller !== document.body) scroller = scroller.parentElement;
        if (scroller) scroller.scrollTop = 0;
        return !!scroller;
      })()`);
      const scrollBefore = await page.evaluate(`(() => {
        const grid = document.querySelector("#cp-activity-grid");
        let scroller = grid?.parentElement ?? null;
        while (scroller && scroller.scrollHeight <= scroller.clientHeight && scroller !== document.body) scroller = scroller.parentElement;
        return scroller ? scroller.scrollTop : 0;
      })()`);
      await page.evaluate(`document.querySelector('#cp-details [data-detail-tab="summary"]').click()`);
      await sleep(500);
      const scrollAfter = await page.evaluate(`(() => {
        const grid = document.querySelector("#cp-activity-grid");
        let scroller = grid?.parentElement ?? null;
        while (scroller && scroller.scrollHeight <= scroller.clientHeight && scroller !== document.body) scroller = scroller.parentElement;
        return scroller ? scroller.scrollTop : 0;
      })()`);
      assert(scrollBefore === scrollAfter, `grid scroll moved from ${scrollBefore} to ${scrollAfter} on a tab switch`);
      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "reload");
      await sleep(1800);
      const state = await page.evaluate(paneStateExpression());
      assert(state.active === "summary", `active tab after reload is ${state.active}`);
      assert(state.materialized.length === 1, "more than one panel materialized after reload");
      await capture(page, "05-active-tab-reload-en-1440");
      return { active: state.active };
    });

    await scenario("06", "Customize Tabs moves, removes, guards the last tab, applies and cancels", async () => {
      await page.evaluate(`document.querySelector("#cp-details [data-details-customize-open]").click()`);
      await sleep(400);
      const opened = await page.evaluate(`(() => {
        const dialog = document.querySelector("#cp-details [data-details-customize-dialog]");
        const list = (side) => [...dialog.querySelectorAll('[data-customize-list="' + side + '"] [data-customize-tab]')].map((item) => item.dataset.customizeTab);
        return {
          open: dialog.open,
          display: list("display"),
          available: list("available"),
          removeAllDisabled: dialog.querySelector("[data-customize-remove-all]").disabled,
          addDisabled: dialog.querySelector("[data-customize-add]").disabled,
          upDisabled: dialog.querySelector("[data-customize-up]").disabled,
        };
      })()`);
      assert(opened.open, "Customize dialog did not open");
      assert(JSON.stringify(opened.display) === JSON.stringify(EXPECTED_TABS), "the display list is not the current tab order");
      assert(opened.available.length === 0, "the available list is not empty for a full display set");
      assert(opened.addDisabled && opened.upDisabled, "a control is enabled without a selection");

      const moved = await page.evaluate(`(() => {
        const dialog = document.querySelector("#cp-details [data-details-customize-dialog]");
        dialog.querySelector('[data-customize-list="display"] [data-customize-tab="general"]').click();
        const before = [...dialog.querySelectorAll('[data-customize-list="display"] [data-customize-tab]')].map((item) => item.dataset.customizeTab);
        dialog.querySelector("[data-customize-down]").click();
        const after = [...dialog.querySelectorAll('[data-customize-list="display"] [data-customize-tab]')].map((item) => item.dataset.customizeTab);
        return { before: before.slice(0, 3), after: after.slice(0, 3) };
      })()`);
      assert(moved.after[0] === "status" && moved.after[1] === "general", `Move Down produced ${JSON.stringify(moved.after)}`);

      await page.evaluate(`document.querySelector("#cp-details [data-details-customize-dialog] [data-details-customize-close]").click()`);
      await sleep(300);
      const cancelled = await page.evaluate(paneStateExpression());
      assert(cancelled.tabs[0] === "general", "Cancel kept the unapplied order");
      assert(cancelled.tabs.length === 17, "Cancel changed the tab set");

      await page.evaluate(`document.querySelector("#cp-details [data-details-customize-open]").click()`);
      await sleep(300);
      const removed = await page.evaluate(`(() => {
        const dialog = document.querySelector("#cp-details [data-details-customize-dialog]");
        dialog.querySelector('[data-customize-list="display"] [data-customize-tab="status"]').click();
        dialog.querySelector("[data-customize-remove]").click();
        dialog.querySelector("[data-details-customize-apply]").click();
        return {
          strip: [...document.querySelectorAll("#cp-details [data-detail-tab]")].map((tab) => tab.dataset.detailTab),
          open: document.querySelector("#cp-details [data-details-customize-dialog]").open,
          available: [...document.querySelectorAll('#cp-details [data-customize-list="available"] [data-customize-tab]')].map((tab) => tab.dataset.customizeTab),
          storage: localStorage.getItem("cubi:activity-details-visible-tabs:v2"),
        };
      })()`);
      assert(removed.open, "Apply closed the dialog");
      assert(!removed.strip.includes("status"), "the removed tab is still in the strip");
      assert(removed.available.includes("status"), "the removed tab is not offered as available");
      assert(removed.storage && removed.storage.includes("general"), "the display set was not persisted");

      const guarded = await page.evaluate(`(() => {
        const dialog = document.querySelector("#cp-details [data-details-customize-dialog]");
        dialog.querySelector("[data-customize-remove-all]").click();
        const after = [...dialog.querySelectorAll('[data-customize-list="display"] [data-customize-tab]')].length;
        return { after, removeAllDisabled: dialog.querySelector("[data-customize-remove-all]").disabled };
      })()`);
      assert(guarded.after === 1 && guarded.removeAllDisabled, "Remove All did not stop at one tab");

      const restored = await page.evaluate(`(() => {
        const dialog = document.querySelector("#cp-details [data-details-customize-dialog]");
        dialog.querySelector("[data-customize-default]").click();
        const display = [...dialog.querySelectorAll('[data-customize-list="display"] [data-customize-tab]')].map((item) => item.dataset.customizeTab);
        dialog.querySelector("[data-details-customize-ok]").click();
        return {
          display,
          open: document.querySelector("#cp-details [data-details-customize-dialog]").open,
          strip: [...document.querySelectorAll("#cp-details [data-detail-tab]")].map((tab) => tab.dataset.detailTab),
        };
      })()`);
      assert(JSON.stringify(restored.display) === JSON.stringify(EXPECTED_TABS), "Default did not restore the canonical order");
      assert(restored.open === false, "OK did not close the dialog");
      assert(JSON.stringify(restored.strip) === JSON.stringify(EXPECTED_TABS), "the strip is not restored after OK");

      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "reload");
      await sleep(1700);
      const afterReload = await page.evaluate(paneStateExpression());
      assert(JSON.stringify(afterReload.tabs) === JSON.stringify(EXPECTED_TABS), "the applied order did not survive the reload");
      await capture(page, "06-customize-en-1440");
      return { moved: moved.after, removed: removed.strip.length, restored: restored.strip.length };
    });

    await scenario("07", "Details visibility is scoped per window and never leaks into another window", async () => {
      await page.evaluate(`(() => {
        for (const key of Object.keys(localStorage)) {
          if (key.includes("details-visible")) localStorage.removeItem(key);
        }
      })()`);
      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "reload");
      await sleep(1700);
      const initial = await page.evaluate(paneStateExpression());
      assert(initial.paneVisible && initial.toggle?.pressed === "true", "Details is not visible by default");
      assert(Object.keys(initial.storage).length === 0, "a default window wrote a preference");

      await page.evaluate(`[...document.querySelectorAll(".cp-details-toggle")].find((button) => button.getClientRects().length).click()`);
      await sleep(700);
      const hidden = await page.evaluate(paneStateExpression());
      assert(!hidden.paneVisible && hidden.toggle?.pressed === "false", "Details did not hide in Activities");
      assert(hidden.storage["cubi:workspace:details-visible:preview-admin:cubi-preview-tenant:preview-rps-01:schedule"] === "false", "the Activities preference was not stored per window");

      await activateWindow(page, "project");
      const project = await page.evaluate(paneStateExpression());
      assert(project.paneVisible, "hiding Details in Activities also hid the Project window pane");
      assert(project.toggle?.pressed === "true", "the Project window toggle inherited the Activities value");
      await capture(page, "07-visibility-project-visible-en-1440");

      await activateWindow(page, "schedule");
      const back = await page.evaluate(paneStateExpression());
      assert(!back.paneVisible, "returning to Activities lost its hidden preference");
      await capture(page, "07-visibility-activities-hidden-en-1440");

      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "reload");
      await sleep(1700);
      const reloaded = await page.evaluate(paneStateExpression());
      assert(!reloaded.paneVisible, "the hidden preference did not survive a reload");

      await page.evaluate(`[...document.querySelectorAll(".cp-details-toggle")].find((button) => button.getClientRects().length).click()`);
      await sleep(700);
      const shown = await page.evaluate(paneStateExpression());
      assert(shown.paneVisible && shown.toggle?.pressed === "true", "Details did not come back");
      return { hidden: !hidden.paneVisible, projectVisible: project.paneVisible, reloadedHidden: !reloaded.paneVisible };
    });

    await scenario("08", "the tab strip is roving-focus accessible and arrow keys are recorded as a known gap", async () => {
      const focused = await page.evaluate(`(() => {
        const active = document.querySelector('#cp-details [data-detail-tab][aria-selected="true"]');
        active?.focus();
        return document.activeElement?.dataset?.detailTab ?? null;
      })()`);
      assert(focused === "summary", `focus did not land on the active tab: ${focused}`);
      await page.cdp.send("Input.dispatchKeyEvent", { type: "keyDown", key: "ArrowRight", code: "ArrowRight", windowsVirtualKeyCode: 39, nativeVirtualKeyCode: 39 });
      await page.cdp.send("Input.dispatchKeyEvent", { type: "keyUp", key: "ArrowRight", code: "ArrowRight", windowsVirtualKeyCode: 39, nativeVirtualKeyCode: 39 });
      await sleep(400);
      const afterArrow = await page.evaluate(`(() => ({
        focused: document.activeElement?.dataset?.detailTab ?? null,
        active: document.querySelector('#cp-details [data-detail-tab][aria-selected="true"]')?.dataset.detailTab,
      }))()`);
      if (afterArrow.active === "summary") {
        knownGaps.push({
          id: "details-tab-arrow-keys",
          detail: "ArrowLeft/ArrowRight/Home/End do not move between Activity Details tabs on this baseline; the open V30 branch (#2048) implements the WAI-ARIA roving navigation.",
          owner: "#2048",
        });
      }
      assert(afterArrow.focused === focused, "the arrow key moved DOM focus in an unhandled way");
      await capture(page, "08-keyboard-en-1440");
      return { focused, afterArrow };
    });

    await scenario("09", "fa/RTL at 1280x720 localizes the tabs and Customize dialog without overflow", async () => {
      await setViewport(page, 1280, 720);
      await setLanguage(page, "fa");
      const state = await page.evaluate(paneStateExpression());
      assert(state.active === "summary", `active tab changed on locale switch: ${state.active}`);
      assert(state.labels.includes("عمومی"), `Persian labels missing: ${JSON.stringify(state.labels.slice(0, 4))}`);
      const fa = await page.evaluate(`(() => {
        const pane = document.querySelector("#cp-details");
        const strip = document.querySelector('#cp-details [role="tablist"]');
        return {
          dir: document.documentElement.dir,
          locale: document.documentElement.lang,
          labels: [...document.querySelectorAll("#cp-details [data-detail-tab]")].slice(0, 5).map((tab) => tab.textContent.trim()),
          customize: document.querySelector("#cp-details [data-details-customize-open]")?.textContent?.trim(),
          paneOverflow: pane ? pane.scrollWidth > pane.clientWidth + 1 : null,
          stripOverflow: strip ? strip.scrollWidth > strip.clientWidth + 1 : null,
          docOverflow: document.scrollingElement.scrollWidth > document.scrollingElement.clientWidth,
        };
      })()`);
      assert(fa.dir === "rtl" && fa.locale === "fa", `document direction/locale is ${fa.dir}/${fa.locale}`);
      assert(fa.labels[0] === "عمومی", `first Persian label is ${fa.labels[0]}`);
      assert(fa.customize && fa.customize !== "Customize Tabs", "the Customize control is not localized");
      assert(!fa.paneOverflow && !fa.stripOverflow, `the details pane overflows horizontally: ${JSON.stringify(fa)}`);
      assert(!fa.docOverflow, "the document overflows horizontally in fa/RTL");
      await page.evaluate(`document.querySelector("#cp-details [data-details-customize-open]").click()`);
      await sleep(400);
      const dialog = await page.evaluate(`(() => {
        const node = document.querySelector("#cp-details [data-details-customize-dialog]");
        return {
          dir: node?.getAttribute("dir"),
          open: node?.open,
          overflow: node ? node.scrollWidth > node.clientWidth + 1 : null,
          title: node?.querySelector("h3")?.textContent?.trim(),
        };
      })()`);
      assert(dialog.open && dialog.dir === "rtl", `Customize dialog direction is ${dialog.dir}`);
      assert(dialog.title && dialog.title !== "Customize Activity Details", "the dialog title is not localized");
      assert(!dialog.overflow, "the Customize dialog overflows horizontally");
      await capture(page, "09-details-fa-rtl-1280");
      await page.evaluate(`document.querySelector("#cp-details [data-details-customize-dialog] [data-details-customize-close]").click()`);
      return { dir: fa.dir, labels: fa.labels.slice(0, 3) };
    });

    await scenario("10", "en/LTR at 1920x1080 keeps one tab row and a readable Details pane", async () => {
      await setViewport(page, 1920, 1080);
      await setLanguage(page, "en");
      const state = await page.evaluate(paneStateExpression(`strip: (() => { const strip = document.querySelector('#cp-details [role="tablist"]'); return strip ? { height: Math.round(strip.getBoundingClientRect().height), sw: strip.scrollWidth, cw: strip.clientWidth, rows: Math.round(strip.getBoundingClientRect().height / (parseFloat(getComputedStyle(strip.querySelector('[data-detail-tab]')).height) || 1)) } : null; })()`));
      assert(state.paneVisible, "Details is hidden at 1920");
      assert(state.strip && state.strip.sw <= state.strip.cw + 1, `the tab strip overflows at 1920: ${JSON.stringify(state.strip)}`);
      const pane = await page.evaluate(`(() => {
        const node = document.querySelector("#cp-details");
        return { width: node.getBoundingClientRect().width, height: node.getBoundingClientRect().height, visible: node.getClientRects().length > 0 };
      })()`);
      assert(pane.width > 1500, `the pane is only ${pane.width} px wide at 1920`);
      await capture(page, "10-details-en-1920");
      return { strip: state.strip, pane };
    });

    assert(report.exceptions.length === 0, `browser exceptions: ${report.exceptions.join(" | ")}`);
    assert(report.consoleErrors.length === 0, `console errors: ${report.consoleErrors.join(" | ")}`);
    assert(report.apiFailures.length === 0, `api failures: ${JSON.stringify(report.apiFailures)}`);
    report.finishedAt = new Date().toISOString();
    report.summary = { passed: scenarios.length, failed: 0, screenshots: screenshots.length };
    writeFileSync(join(evidenceDir, "activity-details-behavior-v26.json"), JSON.stringify(report, null, 2));
    log(`\nALL ${scenarios.length} SCENARIOS PASS · ${screenshots.length} screenshots · known gaps: ${knownGaps.length}`);
  } finally {
    if (scenarios.some((item) => item.status === "fail")) {
      report.finishedAt = new Date().toISOString();
      writeFileSync(join(evidenceDir, "activity-details-behavior-v26.json"), JSON.stringify(report, null, 2));
    }
    await chrome.close?.();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
