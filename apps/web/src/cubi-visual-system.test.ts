import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const primaryLogoLockup = readFileSync(new URL("../public/cubi-platform-logo-primary.svg", import.meta.url), "utf8");

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
  const allowed = new Set(["2C9AF4","1474D4","1674D2","0B4EA4","0B66C8","102B4D","263E5A","EAF5FF","DCEEFF","DCE7F2","1689FF", "0752BD", "0D3D91", "19C7D4", "0B4FAE", "1187FF", "12345A", "31577F"]);
  const colors = [...primaryLogoLockup.matchAll(/#[0-9A-Fa-f]{6}/g)].map((m) => m[0].slice(1).toUpperCase());
  assert.ok(colors.length > 0);
  for (const color of colors) assert.ok(allowed.has(color), `unexpected logo color #${color}`);
});


test("only one canonical CUBI logo file is referenced", () => {
  assert.match(primaryLogoLockup, /CUBI/);
  assert.match(primaryLogoLockup, /PLAN\. CONTROL\. BUILD SMARTER\./);
  assert.match(primaryLogoLockup, /M 100 0|M100 0/);
});
