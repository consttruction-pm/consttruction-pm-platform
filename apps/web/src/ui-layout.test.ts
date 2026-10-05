import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

const css = readFileSync(join(process.cwd(), "styles.css"), "utf8");

test("CUBI UI layout system registers typography and sizing tokens", () => {
  for (const token of [
    "--cubi-ui-base", "--cubi-ui-small", "--cubi-ui-label",
    "--cubi-ui-control-height", "--cubi-ui-touch-height",
    "--cubi-ui-header-height", "--cubi-ui-menu-height",
    "--cubi-ui-page-max", "--cubi-ui-table-font-size", "--cubi-ui-table-head-size",
  ]) assert.ok(css.includes(token + ":"), token);
});

test("workspace layout gives full-width treatment to auxiliary control surfaces", () => {
  for (const selector of [
    ".cp-main > .cp-smart-guide", ".cp-main > .cp-control-summary",
    ".cp-main > .cp-site-logs", ".cp-main > .cp-field-ops",
    ".cp-main > .cp-field-assurance", ".cp-main > .cp-change-claim",
    ".cp-main > .cp-procurement",
  ]) assert.ok(css.includes(selector), selector);
  assert.match(css, /grid-column:\s*1\s*\/\s*-1/);
});

test("workspace responsive rules prevent menu wrap and cramped columns", () => {
  assert.match(css, /flex-wrap:\s*nowrap/);
  assert.match(css, /overflow-x:\s*auto/);
  assert.match(css, /@media \(max-width: 1023px\)/);
  assert.match(css, /@media \(max-width: 760px\)/);
});

test("print layout is explicitly sized for A4 landscape project controls output", () => {
  assert.match(css, /@media print/);
  assert.match(css, /size:\s*A4 landscape/);
  assert.match(css, /table[\\s\\S]*?min-width:\s*0/);
  assert.match(css, /cp-gantt-board[\\s\\S]*?overflow:\s*visible/);
});
