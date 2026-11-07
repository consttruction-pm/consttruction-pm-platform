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

test("WBS level colour stays in the hierarchy cell and its guide rails", () => {
  const bandRule = /\.cp-p6 #cp-activity-grid tbody tr\.cp-p6-tree-band > td \{([^}]*)\}/.exec(sourceCss);
  assert.ok(bandRule, "the WBS row rule must still cover every cell");
  assert.match(bandRule[1], /background-color: #fff/);
  assert.doesNotMatch(sourceCss, /--cp-wbs-band/);
  const treeCellRule = /tr\.cp-p6-tree-band > td\.cp-p6-tree-cell \{([^}]*)\}/.exec(sourceCss);
  assert.ok(treeCellRule, "the hierarchy cell must carry the level tint");
  assert.match(treeCellRule[1], /color-mix\(in srgb, var\(--cp-wbs-level/);
  assert.match(sourceCss, /\.cp-p6 \.cp-p6-tree-rail::before,[\s\S]*?background: var\(--cp-tree-color/);
  assert.match(sourceCss, /\.cp-p6 \.cp-p6-tree-elbow::before \{ bottom: auto; height: 50%/);
  assert.match(sourceCss, /\.cp-p6 \.cp-p6-tree-elbow\.is-branch::before/);
  assert.doesNotMatch(sourceCss, /tr\.cp-p6-wbs-band > td\.cp-p6-wbs-cell-td/);
  assert.doesNotMatch(sourceCss, /tr\.cp-p6-wbs-band:hover > td\.cp-p6-wbs-cell-td/);
});
