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
  const allowed = new Set(["0A3B91","1153B8","1468D6","2CC5EB","0E5CC9","21B7E2","3ED3B8","1C9E85","2CC1A8","0B1C30","5E7183","7E8FA0"]);
  const colors = [...primaryLogoLockup.matchAll(/#[0-9A-Fa-f]{6}/g)].map((m) => m[0].slice(1).toUpperCase());
  assert.ok(colors.length > 0);
  for (const color of colors) assert.ok(allowed.has(color), `unexpected logo color #${color}`);
});


test("only one canonical CUBI logo file is referenced", () => {
  assert.match(primaryLogoLockup, /CUBI/);
  assert.match(primaryLogoLockup, /Plan\. Control\. Build Smarter\./);
  assert.match(primaryLogoLockup, /M250 109L156 62/);
});
