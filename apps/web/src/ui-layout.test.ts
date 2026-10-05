import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";
import assert from "node:assert/strict";

const css = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), "../styles.css"),
  "utf8",
);

test("CUBI UI layout system registers typography and sizing tokens", () => {
  for (const token of [
    "--cubi-ui-base",
    "--cubi-ui-small",
    "--cubi-ui-label",
    "--cubi-ui-control-height",
    "--cubi-ui-touch-height",
    "--cubi-ui-header-height",
    "--cubi-ui-menu-height",
    "--cubi-ui-page-max",
    "--cubi-ui-table-font-size",
    "--cubi-ui-table-head-size",
  ]) {
    assert.ok(css.includes(token + ":"), token);
  }
});

test("workspace layout gives full-width treatment to auxiliary control surfaces", () => {
  for (const selector of [
    ".cp-main > .cp-smart-guide",
    ".cp-main > .cp-control-summary",
    ".cp-main > .cp-site-logs",
    ".cp-main > .cp-field-ops",
    ".cp-main > .cp-field-assurance",
    ".cp-main > .cp-change-claim",
    ".cp-main > .cp-procurement",
  ]) {
    assert.ok(css.includes(selector), selector);
  }
  assert.ok(css.includes("grid-column: 1 / -1"));
});

test("workspace responsive rules prevent menu wrap and cramped columns", () => {
  assert.ok(css.includes("flex-wrap: nowrap"));
  assert.ok(css.includes("overflow-x: auto"));
  assert.ok(css.includes("@media (max-width: 1023px)"));
  assert.ok(css.includes("@media (max-width: 760px)"));
});

test("print layout is explicitly sized for A4 landscape project controls output", () => {
  const printIndex = css.indexOf("@media print");
  assert.ok(printIndex >= 0);
  const printCss = css.slice(printIndex);
  assert.ok(printCss.includes("size: A4 landscape"));
  assert.ok(printCss.includes("table {"));
  assert.ok(printCss.includes("min-width: 0"));
  assert.ok(printCss.includes(".cp-gantt-board"));
  assert.ok(printCss.includes("overflow: visible"));
});
