import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";

const sourceCss = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const publicCss = readFileSync(new URL("../public/styles.css", import.meta.url), "utf8");

test("workspace CSS copies are identical for preview and published assets", () => {
  assert.equal(sourceCss, publicCss);
});

test("settings module keeps its center visible and gives it a full-width layout", () => {
  assert.doesNotMatch(
    sourceCss,
    /\.cp-workspace\[data-active-menu="settings"\] \.cp-center\{display:none!important\}/,
  );
  assert.match(
    sourceCss,
    /\.cp-workspace\[data-active-menu="settings"\] \.cp-center\{grid-column:1\/-1;grid-row:auto;align-content:start;gap:12px\}/,
  );
});

test("startup, progress, and preview-only empty states have visible styling", () => {
  assert.match(sourceCss, /\.cp-startup-card\{/);
  assert.match(sourceCss, /\.cp-module-empty-state\{/);
  assert.match(sourceCss, /prefers-reduced-motion:reduce\)\{\.cp-startup-progress span\{animation:none/);
});

test("WBS level colour fills the row band and the solid hierarchy spines", () => {
  const bandRule = /\.cp-p6 #cp-activity-grid tbody tr\.cp-p6-tree-band > td:not\(\.cp-logic-column\):not\(\.cp-actions-column\) \{([^}]*)\}/.exec(sourceCss);
  assert.ok(bandRule, "the WBS row rule must still cover every data cell");
  assert.match(bandRule[1], /background-color: var\(--cp-wbs-level, #0000ff\)/);
  assert.match(bandRule[1], /color: var\(--cp-wbs-ink, #000000\)/);
  // Band typography and height come from the band presentation, not from the
  // activity table font variables.
  assert.match(bandRule[1], /font-family: var\(--cp-wbs-font-family, inherit\)/);
  assert.match(bandRule[1], /font-size: var\(--cp-wbs-font-size, inherit\)/);
  assert.match(bandRule[1], /height: var\(--cp-wbs-row-height, auto\)/);
  assert.match(sourceCss, /\.cp-p6 \.cp-p6-wbs-title::after \{ content: ":"; \}/);
  assert.doesNotMatch(sourceCss, /--cp-wbs-band/);
  const spineRule = /\.cp-p6 \.cp-p6-wbs-spine \{([^}]*)\}/.exec(sourceCss);
  assert.ok(spineRule, "each ancestor level must draw a solid spine");
  assert.match(spineRule[1], /width: 14px/);
  assert.match(spineRule[1], /background: var\(--cp-spine/);
  assert.match(sourceCss, /\.cp-p6 \.cp-p6-wbs-toggle \{[\s\S]*?border: 1px solid #808080/);
  // The reference chart has no frozen label pane; only WBS branch ends rule.
  assert.doesNotMatch(sourceCss, /cp-gantt-tree-rail/);
  assert.doesNotMatch(sourceCss, /cp-gantt-axis-label/);
  assert.doesNotMatch(sourceCss, /--cp-gantt-label-width/);
  assert.match(sourceCss, /\.cp-p6 \.cp-gantt-row\.is-group-end \{ border-bottom: 1px dashed #c0c0c0; \}/);
  assert.match(sourceCss, /\.cp-p6 \.cp-gantt-endpoint\.is-triangle-down \{/);
  assert.doesNotMatch(sourceCss, /tr\.cp-p6-wbs-band > td\.cp-p6-wbs-cell-td/);
  assert.doesNotMatch(sourceCss, /tr\.cp-p6-wbs-band:hover > td\.cp-p6-wbs-cell-td/);
});

test("activity grid headers stay sticky while the rows scroll", () => {
  const headerRule = /\.cp-p6 #cp-activity-grid thead th \{([^}]*)\}/.exec(sourceCss);
  assert.ok(headerRule, "the activity grid header rule must exist");
  assert.match(headerRule[1], /position: sticky/);
  assert.match(headerRule[1], /top: 0/);
  // A later `position: relative` override would scroll every data column
  // header away with the rows while the sync keeps both panes moving.
  assert.doesNotMatch(sourceCss, /thead th\[data-column-id\] \{ position: relative; \}/);
});
