import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const primaryLogo = readFileSync(new URL("../public/logo.svg", import.meta.url), "utf8");
const darkLogo = readFileSync(new URL("../public/logo-dark.svg", import.meta.url), "utf8");

test("CUBI visual system exposes the registered brand anchors", () => {
  for (const token of [
    "--cubi-deep-navy",
    "--cubi-engineering-blue",
    "--cubi-copper-orange",
    "--cubi-brushed-titanium",
    "--cubi-brushed-metal",
  ]) {
    assert.match(css, new RegExp(token));
  }
});

test("CUBI homepage is aligned to the supplied Issue #1101 website reference", () => {
  assert.match(css, /\.cubi-reference-header\s*\{[\s\S]*background:\s*#fff/);
  assert.match(css, /\.cubi-reference-hero\s*\{[\s\S]*background:#0b3158/);
  assert.match(css, /\.cubi-reference-dashboard\s*\{[\s\S]*background:#f6f9fc/);
  assert.match(css, /\.cubi-reference-feature-grid\s*\{[\s\S]*grid-template-columns:repeat\(5/);
  assert.match(css, /\.cubi-reference-tech\s*\{[\s\S]*background:#eef6ff/);
  assert.match(css, /\.cubi-reference-pricing\s*\{[\s\S]*background:#092b50/);
});

test("CUBI logos use the approved reference palette", () => {
  const allowed = new Set(["1689FF", "0752BD", "0D3D91", "19C7D4", "0B4FAE", "1187FF"]);
  const colors = [...(primaryLogo + darkLogo).matchAll(/#[0-9A-Fa-f]{6}/g)].map((m) => m[0].slice(1).toUpperCase());
  assert.ok(colors.length > 0);
  for (const color of colors) assert.ok(allowed.has(color), `unexpected logo color #${color}`);
});
