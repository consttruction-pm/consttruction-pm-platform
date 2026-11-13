#!/usr/bin/env node
/**
 * Browser E2E for the Version 26 Activity formula-column lifecycle.
 *
 * The Shared Calculation Core is the only expression authority. This run proves
 * that the Activities window:
 *   - forwards expressions to the authoritative validator and shows the real
 *     error code with a plain-language explanation;
 *   - persists a valid expression through the formula-column API;
 *   - lists the saved definition with version, data type, result type, unit and
 *     dependencies;
 *   - applies the column to the saved layout, after which every grid value is
 *     the server-evaluated cell from the workspace read (never a browser
 *     calculation);
 *   - restores the column and its values after a full reload;
 *   - rejects a duplicate id with a different definition;
 *   - hides save/apply controls from a Viewer while keeping read-side validation.
 *
 * Usage:
 *   CUBI_PREVIEW_URL=http://127.0.0.1:4184 node e2e/formula-columns-v26.mjs
 */

import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { Page, launchChrome, waitForHttp, artifactsDir, gitHead } from "./preview-e2e.mjs";

const baseUrl = process.env.CUBI_PREVIEW_URL || "http://127.0.0.1:4184";
const evidenceDate = process.env.CUBI_EVIDENCE_DATE || "2026-11-13";
const testedCodeSha = process.env.CUBI_TESTED_CODE_SHA || gitHead();
const evidenceCommitSha = process.env.CUBI_EVIDENCE_COMMIT_SHA || null;
const outDir = join(artifactsDir, "formula-columns-v26");
const evidenceDir = join(
  artifactsDir,
  "..",
  "..",
  "..",
  "..",
  "docs",
  "workspace",
  "evidence",
  `formula-columns-v26-${evidenceDate}`,
);
mkdirSync(outDir, { recursive: true });
mkdirSync(evidenceDir, { recursive: true });

const PROJECT = "preview-rps-01";
const FORMULA_ID = "formula.e2e_progress_fraction";
const FORMULA_TITLE = "Progress Fraction";
const EXPRESSION = "[activity.duration_percent_complete] / 100";
const CONTEXT_FIELD = "activity.actual_finish";
const DIV_ZERO_ID = "formula.e2e_div_zero";

const INVALID_EXPRESSIONS = [
  {
    id: "unknown-field",
    expression: "[activity.not_a_registered_field] + 1",
    expectCode: "FIELD_NOT_FOUND:activity.not_a_registered_field",
  },
  {
    id: "missing-operand",
    expression: "[activity.duration_percent_complete] +",
    expectCode: "EXPECTED_EXPRESSION_AT_",
  },
  {
    id: "type-mismatch",
    expression: "[activity.duration_percent_complete] + [activity.name]",
    expectCode: "NUMERIC_OPERANDS_REQUIRED",
  },
  {
    id: "unsupported-duration",
    expression: "[activity.planned_duration] * 2",
    expectCode: "UNSUPPORTED_P6_FORMULA_FIELD_TYPE:duration",
  },
];

const exceptions = [];
const consoleErrors = [];
const apiFailures = [];
const apiWrites = [];
const scenarios = [];
const screenshots = [];
let trackWrites = false;

function log(message) {
  process.stdout.write(`${message}\n`);
}

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION_FAILED: ${message}`);
}

function record(id, name, status, details = {}) {
  scenarios.push({ ...details, id, name, status, at: new Date().toISOString() });
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

const panelState = `(() => {
  const panel = document.querySelector("#cp-formula-editor [data-formula-editor]");
  if (!panel) return null;
  return {
    hasForm: Boolean(panel.querySelector("[data-formula-form]")),
    hasSaveForm: Boolean(panel.querySelector("[data-formula-save-form]")),
    readonlyText: panel.querySelector("[data-formula-readonly]")?.textContent?.trim() ?? null,
    status: panel.querySelector("[data-formula-status]")?.textContent?.trim() ?? null,
    resultText: panel.querySelector("[data-formula-result]")?.textContent?.trim() ?? null,
    resultCode: panel.querySelector("[data-formula-result] code")?.textContent?.trim() ?? null,
    resultMessage: panel.querySelector("[data-formula-error-message]")?.textContent?.trim() ?? null,
    fieldValue: panel.querySelector("[data-formula-field]")?.value ?? null,
    columns: [...panel.querySelectorAll("[data-formula-columns] [data-formula-column]")].map((item) => ({
      id: item.getAttribute("data-formula-column"),
      version: item.querySelector("[data-formula-version]")?.textContent?.trim() ?? null,
      dataType: item.querySelector("[data-formula-data-type]")?.textContent?.trim() ?? null,
      resultType: item.querySelector("[data-formula-result-type]")?.textContent?.trim() ?? null,
      unit: item.querySelector("[data-formula-unit]")?.textContent?.trim() ?? null,
      dependencies: item.querySelector("[data-formula-dependencies]")?.textContent?.trim() ?? null,
      apply: item.querySelector("[data-formula-apply]")?.getAttribute("data-formula-apply") ?? null,
      inLayout: Boolean(item.querySelector("[data-formula-in-layout]")),
    })),
  };
})()`;

async function capture(page, name, selector = "#cp-formula-editor") {
  if (selector === "#cp-formula-editor") {
    await page.evaluate(`(() => {
      const panel = document.querySelector("#cp-formula-editor");
      if (panel && panel.getClientRects().length > 0) return true;
      const menu = document.querySelector('[data-desktop-menu="project"]');
      if (!menu) return false;
      menu.click();
      const item = document.querySelector('[data-desktop-item="project.formula"]');
      if (!item) return false;
      item.click();
      return true;
    })()`);
    await sleep(500);
  } else {
    await page.evaluate(`(() => {
      const drawer = document.querySelector("[data-tools-drawer]");
      if (drawer) drawer.hidden = true;
      const formulaHeader = [...document.querySelectorAll('#cp-activity-grid th[data-column-id^="formula."]')].pop();
      formulaHeader?.scrollIntoView({ inline: "end", block: "nearest" });
      return true;
    })()`);
    await sleep(300);
  }
  const rect = await page.evaluate(
    `(() => {
      const element = document.querySelector(${JSON.stringify(selector)});
      if (!element) return null;
      element.scrollIntoView({ block: "center", inline: "nearest" });
      const bounds = element.getBoundingClientRect();
      return { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height };
    })()`,
  );
  await sleep(300);
  const file = `formula-columns-v26/${name}.png`;
  const clip =
    rect && rect.width > 0 && rect.height > 0
      ? {
          x: Math.max(0, Math.floor(rect.x)),
          y: Math.max(0, Math.floor(rect.y)),
          width: Math.min(Math.ceil(rect.width), 1400),
          height: Math.min(Math.ceil(rect.height), 820),
        }
      : null;
  await page.screenshot(file, clip);
  copyFileSync(join(artifactsDir, file), join(evidenceDir, `${name}.png`));
  screenshots.push(`${name}.png`);
  return file;
}

async function openWorkspace(page, roleLabel = "Planner") {
  await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "main", "login");
  const hasRoles = await page.evaluate(
    `Boolean(document.querySelector('button[name="role"]'))`,
  );
  if (!hasRoles) {
    // A persona is already signed in for this tab; sign out before switching.
    await page.evaluate(
      `fetch("/preview/logout", { method: "POST" }).then(() => true)`,
      { awaitPromise: true },
    );
    await page.navigate(`${baseUrl}/preview/login?next=%2Fapp%3Fview%3Dlive`, "main", "login after sign out");
    await page.waitForSelector('button[name="role"]', "login role buttons");
  }
  const clicked = await page.evaluate(`(() => {
    const button = [...document.querySelectorAll("form button")].find((item) => (item.textContent || "").trim().startsWith(${JSON.stringify(roleLabel)}));
    if (!button) return false;
    button.click();
    return true;
  })()`);
  assert(clicked, `login role ${roleLabel} was not offered`);
  await page.waitForSelector('[data-project-id="preview-rps-01"]', "project selection");
  await page.click('[data-project-id="preview-rps-01"]');
  await page.waitForSelector("#cp-activity-grid tbody tr[data-activity-id]", "activity rows");
  await sleep(1400);
}

async function fillExpression(page, expression) {
  await page.setSelect("#cp-formula-editor [data-formula-field]", CONTEXT_FIELD);
  await page.setInput("#cp-formula-editor [data-formula-expression]", expression);
  await sleep(150);
}

async function validate(page) {
  await page.click("#cp-formula-editor [data-formula-validate]");
  await page.waitFor(
    `(() => {
      const panel = document.querySelector("#cp-formula-editor [data-formula-editor]");
      const status = panel?.querySelector("[data-formula-status]")?.textContent?.trim() ?? "";
      return status && !status.includes("Validating");
    })()`,
    "formula validation settled",
  );
  await sleep(200);
  return page.evaluate(panelState);
}

async function readSavedColumns(page) {
  return page.evaluate(
    `(async () => {
      const response = await fetch("/api/projects/${PROJECT}/p6/formula-columns");
      const payload = await response.json();
      return { status: response.status, payload };
    })()`,
    { awaitPromise: true },
  );
}

async function readWorkspace(page) {
  return page.evaluate(
    `(async () => {
      const scopeResponse = await fetch("/api/projects/${PROJECT}/p6/formula-columns");
      const scope = await scopeResponse.json();
      const response = await fetch("/api/v2/workspace/control-room/read", {
        headers: {
          "X-Tenant-Id": scope.scope.tenant_id,
          "X-Project-Id": "${PROJECT}",
          "X-Project-Revision": String(scope.scope.project_revision),
        },
      });
      const payload = await response.json();
      return { status: response.status, payload };
    })()`,
    { awaitPromise: true },
  );
}

function formulaCells(workspacePayload, formulaId) {
  const activities = workspacePayload?.workspace?.activities ?? [];
  return activities.map((activity) => ({
    activityId: activity.id,
    value: activity.cells?.[formulaId] ?? null,
  }));
}

async function gridFormulaState(page, formulaId) {
  return page.evaluate(`(() => {
    const header = document.querySelector('#cp-activity-grid th[data-column-id="${formulaId}"]');
    const rows = [...document.querySelectorAll("#cp-activity-grid tbody tr[data-activity-id]")];
    return {
      header: header ? { label: header.textContent?.trim() ?? "", marked: Boolean(header.querySelector('[aria-label*="ƒx"], span[aria-label]')) } : null,
      headerCount: document.querySelectorAll('#cp-activity-grid th[data-column-id="${formulaId}"]').length,
      rows: rows.map((row) => ({
        activityId: row.getAttribute("data-activity-id"),
        text: (row.querySelector('td[data-column-id="${formulaId}"]')?.textContent ?? "").trim(),
      })),
    };
  })()`);
}

async function applySavedColumn(page, formulaId) {
  await page.click(`#cp-formula-editor [data-formula-apply="${formulaId}"]`);
  await page.waitFor(
    `Boolean(document.querySelector('#cp-activity-grid th[data-column-id="${formulaId}"]'))`,
    "applied formula column header",
  );
  await sleep(1200);
}

async function main() {
  const health = await waitForHttp(`${baseUrl}/preview/health`, 30000);
  if (!(health.status === "ok" || health.status === 200)) throw new Error(`preview health ${health.status}`);

  const chrome = await launchChrome();
  const page = new Page(chrome.cdp);
  await page.initialize();
  page.cdp.on("Runtime.exceptionThrown", (params) => {
    exceptions.push(
      params.exceptionDetails?.exception?.description ??
        params.exceptionDetails?.text ??
        "unknown exception",
    );
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
  page.cdp.on("Network.requestWillBeSent", (params) => {
    if (!trackWrites || params.request.method === "GET" || params.request.method === "OPTIONS") return;
    if (!params.request.url.includes("/api/")) return;
    apiWrites.push({ method: params.request.method, url: params.request.url });
  });

  const report = {
    contract: "cubi-formula-columns-v26.v1",
    baseUrl,
    gitHead: gitHead(),
    testedCodeSha,
    evidenceCommitSha,
    capturedAt: new Date().toISOString(),
    formula: { id: FORMULA_ID, title: FORMULA_TITLE, expression: EXPRESSION, contextField: CONTEXT_FIELD },
    invalidExpressions: INVALID_EXPRESSIONS,
    scenarios,
    screenshots,
    exceptions,
    consoleErrors,
    apiFailures,
    interactionWrites: apiWrites,
  };

  try {
    await page.cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1440,
      height: 900,
      deviceScaleFactor: 1,
      mobile: false,
    });
    await sleep(400);
    await openWorkspace(page, "Planner");
    await page.waitForSelector("#cp-formula-editor [data-formula-form]", "formula editor form");

    await scenario("01", "A planner sees the authoritative validation form and the save lifecycle", async () => {
      const state = await page.evaluate(panelState);
      assert(state, "the formula editor panel is missing");
      assert(state.hasForm, "the validation form is missing");
      assert(state.hasSaveForm, "the save form is missing for a planner");
      assert(!state.readonlyText, "a writable session must not show the read-only notice");
      assert(/^activity\./.test(state.fieldValue ?? ""), `context field default ${state.fieldValue}`);
      assert(state.columns.length === 0, `a fresh project should have no saved columns, saw ${state.columns.length}`);
      await capture(page, "01-planner-editor");
      return state;
    });

    const validationResults = [];
    await scenario("02", "Invalid expressions show the authoritative code and a plain-language reason", async () => {
      for (const item of INVALID_EXPRESSIONS) {
        await fillExpression(page, item.expression);
        const state = await validate(page);
        assert(state.resultCode, `${item.id}: no error code was shown`);
        assert(
          state.resultMessage && state.resultMessage.length > 10,
          `${item.id}: no plain-language explanation was shown`,
        );
        assert(
          !state.resultText.includes("Result type"),
          `${item.id}: an invalid expression must not report a result type`,
        );
        if (item.expectCode) {
          const matches = item.expectCode.endsWith("_")
            ? state.resultCode.startsWith(item.expectCode)
            : state.resultCode === item.expectCode;
          assert(
            matches,
            `${item.id}: expected ${item.expectCode}, received ${state.resultCode}`,
          );
        }
        validationResults.push({
          id: item.id,
          expression: item.expression,
          code: state.resultCode,
          message: state.resultMessage,
          statusText: state.status,
        });
      }
      const columns = await readSavedColumns(page);
      assert(
        columns.payload.formula_columns.length === 0,
        "an invalid expression must never persist a column",
      );
      await capture(page, "02-invalid-expression");
      return validationResults;
    });

    let validState;
    await scenario("03", "A valid expression returns authoritative dependencies and result type", async () => {
      await fillExpression(page, EXPRESSION);
      validState = await validate(page);
      assert(validState.resultText.includes("Valid expression"), `unexpected result: ${validState.resultText}`);
      assert(
        validState.resultText.includes("activity.duration_percent_complete"),
        `the authoritative dependency list is missing: ${JSON.stringify(validState.resultText)}`,
      );
      assert(validState.resultText.includes("double"), "the authoritative result type is missing");
      await capture(page, "03-valid-expression");
      return validState;
    });

    let createdRecord;
    await scenario("04", "Saving persists the definition and the catalogue shows its full identity", async () => {
      trackWrites = true;
      await page.setInput("#cp-formula-editor [data-formula-title]", FORMULA_TITLE);
      await page.setInput("#cp-formula-editor [data-formula-id]", FORMULA_ID);
      await page.click("#cp-formula-editor [data-formula-save]");
      await page.waitFor(
        `Boolean(document.querySelector('#cp-formula-editor [data-formula-columns] [data-formula-column="${FORMULA_ID}"]'))`,
        "saved formula column",
      );
      await sleep(1200);
      const state = await page.evaluate(panelState);
      const saved = state.columns.find((item) => item.id === FORMULA_ID);
      assert(saved, "the saved column is missing from the catalogue");
      assert(/Definition version \d+/.test(saved.version ?? ""), `version text ${saved.version}`);
      assert((saved.dataType ?? "").includes("double"), `data type ${saved.dataType}`);
      assert((saved.resultType ?? "").includes("number"), `result type ${saved.resultType}`);
      assert((saved.dependencies ?? "").includes("activity.duration_percent_complete"), `dependencies ${saved.dependencies}`);
      assert(saved.apply === FORMULA_ID, "an unapplied saved column must offer the apply action");
      assert(!saved.inLayout, "a freshly saved column must not claim to be in the layout");

      const api = await readSavedColumns(page);
      assert(api.payload.formula_columns.length === 1, "the API must expose exactly one column");
      createdRecord = api.payload.formula_columns[0];
      assert(createdRecord.formula.formula_id === FORMULA_ID, "the API id differs from the UI");
      assert(createdRecord.formula.expression === EXPRESSION, "the API expression differs from the UI");
      trackWrites = false;
      await capture(page, "04-saved-column");
      return { saved, record: createdRecord };
    });

    let layoutState;
    await scenario("05", "Applying the column adds it to the layout and every cell is the server value", async () => {
      trackWrites = true;
      await applySavedColumn(page, FORMULA_ID);
      const grid = await gridFormulaState(page, FORMULA_ID);
      assert(grid.header, "the formula column header is missing from the grid");
      assert(grid.headerCount === 1, `duplicate formula headers: ${grid.headerCount}`);
      assert(grid.header.marked, "the grid header is not marked as a computed column");
      assert(grid.header.label.includes(FORMULA_TITLE), `header label ${grid.header.label}`);

      const read = await readWorkspace(page);
      assert(read.status === 200, `workspace read ${read.status}`);
      const serverCells = formulaCells(read.payload, FORMULA_ID);
      assert(serverCells.length === grid.rows.length, `rows ${grid.rows.length} vs server ${serverCells.length}`);
      let nonEmpty = 0;
      for (const row of grid.rows) {
        const server = serverCells.find((cell) => cell.activityId === row.activityId);
        assert(server, `server cell missing for ${row.activityId}`);
        const expected = server.value === null ? "" : String(server.value).trim();
        const actual = server.value === null && row.text === "—" ? "" : row.text;
        assert(
          actual === expected,
          `${row.activityId}: grid "${row.text}" is not the server value "${expected}"`,
        );
        assert(!/NaN|undefined|\[object/.test(row.text), `${row.activityId}: invalid cell text "${row.text}"`);
        if (row.text) nonEmpty += 1;
      }
      assert(nonEmpty > 0, "every formula cell is empty; the server did not evaluate the column");

      const panel = await page.evaluate(panelState);
      const saved = panel.columns.find((item) => item.id === FORMULA_ID);
      assert(saved?.inLayout, "the catalogue must mark the applied column as in layout");
      assert(!saved.apply, "an applied column must not offer apply again");
      trackWrites = false;
      layoutState = { gridHeader: grid.header, rows: grid.rows.length, nonEmpty, serverCells };
      await capture(page, "05-applied-grid", "#cp-activity-grid");
      return layoutState;
    });

    await scenario("06", "A full reload restores the saved column, layout and server values", async () => {
      await page.reload("#cp-activity-grid tbody tr[data-activity-id]", "reload after apply");
      await sleep(1500);
      const grid = await gridFormulaState(page, FORMULA_ID);
      assert(grid.header, "the formula column disappeared after reload");
      assert(grid.headerCount === 1, "the formula column duplicated after reload");
      const read = await readWorkspace(page);
      const serverCells = formulaCells(read.payload, FORMULA_ID);
      for (const row of grid.rows) {
        const server = serverCells.find((cell) => cell.activityId === row.activityId);
        const expected = server?.value === null || server?.value === undefined ? "" : String(server.value).trim();
        const actual = (server?.value === null || server?.value === undefined) && row.text === "—" ? "" : row.text;
        assert(actual === expected, `${row.activityId}: reloaded cell "${row.text}" vs "${expected}"`);
      }
      await page.waitForSelector("#cp-formula-editor [data-formula-columns]", "catalogue after reload");
      await page.waitFor(
        `Boolean(document.querySelector('#cp-formula-editor [data-formula-columns] [data-formula-column="${FORMULA_ID}"] [data-formula-in-layout]'))`,
        "in-layout marker after reload",
      );
      await capture(page, "06-reload-restored", "#cp-activity-grid");
      return { rows: grid.rows.length, header: grid.header };
    });

    await scenario("07", "A duplicate id with a different definition is rejected with a meaningful error", async () => {
      await fillExpression(page, "[activity.duration_percent_complete] / 50");
      await page.setInput("#cp-formula-editor [data-formula-title]", "Duplicate attempt");
      await page.setInput("#cp-formula-editor [data-formula-id]", FORMULA_ID);
      await page.click("#cp-formula-editor [data-formula-save]");
      await page.waitFor(
        `(() => {
          const panel = document.querySelector("#cp-formula-editor [data-formula-editor]");
          const status = panel?.querySelector("[data-formula-status]")?.textContent?.trim() ?? "";
          return status && !status.includes("Saving");
        })()`,
        "duplicate save settled",
      );
      await sleep(600);
      const state = await page.evaluate(panelState);
      assert(state.resultCode === "FORMULA_COLUMN_ALREADY_EXISTS", `error code ${state.resultCode}`);
      assert(
        state.resultMessage && /already uses this ID/.test(state.resultMessage),
        `error message ${state.resultMessage}`,
      );
      const api = await readSavedColumns(page);
      assert(api.payload.formula_columns.length === 1, "the duplicate must not create a second column");
      assert(
        api.payload.formula_columns[0].formula.expression === EXPRESSION,
        "the duplicate attempt overwrote the stored definition",
      );
      await capture(page, "07-duplicate-rejected");
      return { code: state.resultCode, message: state.resultMessage };
    });

    let divZero;
    await scenario("08", "A zero divisor validates but yields empty server cells, never a fabricated number", async () => {
      // The Shared Core treats division by zero as an evaluation-time condition,
      // not a compile-time error. The browser must not invent an error or a
      // substitute value; the authoritative contract leaves the cell empty.
      await fillExpression(page, "[activity.duration_percent_complete] / 0");
      const validation = await validate(page);
      assert(
        validation.resultText.includes("Valid expression"),
        `the authoritative validator should accept the expression, saw ${validation.resultText}`,
      );
      await page.setInput("#cp-formula-editor [data-formula-title]", "Div Zero");
      await page.setInput("#cp-formula-editor [data-formula-id]", DIV_ZERO_ID);
      await page.click("#cp-formula-editor [data-formula-save]");
      await page.waitFor(
        `Boolean(document.querySelector('#cp-formula-editor [data-formula-columns] [data-formula-column="${DIV_ZERO_ID}"]'))`,
        "div-zero column saved",
      );
      await sleep(600);
      await applySavedColumn(page, DIV_ZERO_ID);
      const grid = await gridFormulaState(page, DIV_ZERO_ID);
      const read = await readWorkspace(page);
      const serverCells = formulaCells(read.payload, DIV_ZERO_ID);
      assert(serverCells.length === grid.rows.length, "div-zero rows disagree with the server");
      for (const row of grid.rows) {
        const server = serverCells.find((cell) => cell.activityId === row.activityId);
        const expected = server?.value === null || server?.value === undefined ? "" : String(server.value).trim();
        const actual = (server?.value === null || server?.value === undefined) && row.text === "—" ? "" : row.text;
        assert(actual === expected, `${row.activityId}: div-zero "${row.text}" vs server "${expected}"`);
        assert(!/NaN|Infinity|undefined/.test(row.text), `${row.activityId}: fabricated cell "${row.text}"`);
      }
      divZero = {
        validation: validation.resultText,
        rows: grid.rows.length,
        emptyCells: serverCells.filter((cell) => cell.value === null).length,
        serverValues: serverCells,
      };
      await capture(page, "08-division-by-zero-empty-cells", "#cp-activity-grid");
      return divZero;
    });

    await scenario("09", "A Viewer can validate but never save or apply a formula column", async () => {
      await openWorkspace(page, "Viewer");
      await page.waitForSelector("#cp-formula-editor [data-formula-editor]", "viewer formula panel");
      await page.waitFor(
        `Boolean(document.querySelector("#cp-formula-editor [data-formula-readonly]"))`,
        "viewer read-only notice",
      );
      const state = await page.evaluate(panelState);
      assert(state.hasForm, "a Viewer should still be able to validate an expression");
      assert(!state.hasSaveForm, "a Viewer must not receive the save form");
      assert(/planner or project administrator/.test(state.readonlyText ?? ""), "the read-only reason is missing");
      assert(state.columns.length === 2, "a Viewer should still read the saved catalogue");
      assert(state.columns.every((column) => !column.apply), "a Viewer must not receive the apply action");
      await fillExpression(page, EXPRESSION);
      const validated = await validate(page);
      assert(
        validated.resultText.includes("Valid expression"),
        `Viewer validation failed: ${validated.resultText}`,
      );
      await capture(page, "09-viewer-readonly");
      return { readonlyText: state.readonlyText, validation: validated.resultText };
    });

    await scenario("10", "No browser evaluation endpoint is contacted during the lifecycle", async () => {
      const evaluateCalls = apiWrites.filter((entry) => /evaluate|compute|calculate/i.test(entry.url));
      assert(evaluateCalls.length === 0, `unexpected evaluation requests: ${JSON.stringify(evaluateCalls)}`);
      assert(exceptions.length === 0, `page exceptions: ${JSON.stringify(exceptions)}`);
      assert(apiFailures.length === 0, `API failures: ${JSON.stringify(apiFailures)}`);
      return { writes: apiWrites };
    });

    await capture(page, "10-final");
    writeFileSync(join(evidenceDir, "formula-columns-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
    log(`\nFormula-column suite passed: ${scenarios.length} scenarios`);
    log(`Evidence: ${evidenceDir}`);
  } catch (error) {
    const message = String(error && error.stack ? error.stack : error);
    report.failure = message;
    writeFileSync(join(evidenceDir, "formula-columns-v26.json"), JSON.stringify(report, null, 2));
    writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
    throw error;
  } finally {
    await page.cdp.send("Browser.close").catch(() => {});
    chrome.process?.kill?.();
  }
}

main().catch((error) => {
  process.stderr.write(`${error}\n`);
  process.exitCode = 1;
});
