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
