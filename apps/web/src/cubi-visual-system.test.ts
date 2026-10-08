import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const primaryLogo = readFileSync(new URL("../public/logo.svg", import.meta.url), "utf8");
const darkLogo = readFileSync(new URL("../public/logo-dark.svg", import.meta.url), "utf8");
const primaryLogoLockup = readFileSync(new URL("../public/cubi-platform-logo-primary.svg", import.meta.url), "utf8");
const darkLogoLockup = readFileSync(new URL("../public/cubi-platform-logo-primary-dark.svg", import.meta.url), "utf8");

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
  const allowed = new Set(["2C9AF4","1474D4","1674D2","0B4EA4","0B66C8","102B4D","263E5A","EAF5FF","DCEEFF","DCE7F2","1689FF", "0752BD", "0D3D91", "19C7D4", "0B4FAE", "1187FF", "1264D6", "19B7D8", "12B9B1", "62D6A7", "0B3A7A", "071A2F", "0B2342", "31506F", "47708F", "B9D1E8", "8FB7D4", "FFFFFF"]);
  const colors = [...(primaryLogo + darkLogo + primaryLogoLockup + darkLogoLockup).matchAll(/#[0-9A-Fa-f]{6}/g)].map((m) => m[0].slice(1).toUpperCase());
  assert.ok(colors.length > 0);
  for (const color of colors) assert.ok(allowed.has(color), `unexpected logo color #${color}`);
});

test("canonical CUBI logo lockups are available for the public homepage", () => {
  const lockup = readFileSync(new URL("../public/cubi-logo-lockup.svg", import.meta.url), "utf8");
  const darkLockup = readFileSync(new URL("../public/cubi-logo-lockup-dark.svg", import.meta.url), "utf8");
  for (const markup of [lockup, darkLockup]) {
    assert.match(markup, /CUBI/);
    assert.match(markup, /Platform/);
    assert.match(markup, /#1689ff/i);
    assert.match(markup, /#19c7d4/i);
  }
});
