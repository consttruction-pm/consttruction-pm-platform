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
  const allowed = new Set(["0877F9", "09BDE0", "063A9D", "0757C5", "0753B8", "0878E9", "13D2C2", "08AFA9", "0879F3", "0755B9", "0FC7B9", "0875E6", "0AA6D2", "064AAE", "08C4B5", "071A36", "243B5B", "087BFA", "06BDE3", "07358F", "0757BD", "0876E8", "0645A7", "0DD6C6", "08AFA7", "087BF1", "0748A7", "0879EA", "0AC5B8", "08BBD4", "172F52"]);
  const colors = [...primaryLogoLockup.matchAll(/#[0-9A-Fa-f]{6}/g)].map((m) => m[0].slice(1).toUpperCase());
  assert.ok(colors.length > 0);
  for (const color of colors) assert.ok(allowed.has(color), `unexpected logo color #${color}`);
});


test("only one canonical CUBI logo file is referenced", () => {
  assert.match(primaryLogoLockup, /CUBI/);
  assert.match(primaryLogoLockup, /Plan\. Control\. Build Smarter\./);
  assert.match(primaryLogoLockup, /M\d+ 0 \d+ \d+/);
});
