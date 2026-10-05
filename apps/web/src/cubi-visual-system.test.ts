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

test("CUBI homepage keeps the registered dark-hero/copper-CTA direction", () => {
  assert.match(css, /\.cubi-hero\s*\{[^}]*background:\s*var\(--cp-navy-dark\)/s);
  assert.match(css, /\.cubi-button\s*\{[^}]*background:\s*var\(--cp-copper\)/s);
});

test("CUBI homepage avoids heavy marketing compositing and respects reduced motion", () => {
  assert.match(css, /\.cubi-header\s*\{[^}]*backdrop-filter:\s*none/s);
  assert.match(css, /\.cubi-grid-glow\s*\{[^}]*mask-image:\s*none/s);
  assert.match(css, /@media\s*\(prefers-reduced-motion:\s*reduce\)/);
});

test("CUBI logos contain only registered brand colors", () => {
  const allowed = new Set(["1976D2", "F28C28", "0F2747", "E8EBEF"]);
  const colors = [...(primaryLogo + darkLogo).matchAll(/#[0-9A-Fa-f]{6}/g)].map((m) => m[0].slice(1).toUpperCase());
  assert.ok(colors.length > 0);
  for (const color of colors) assert.ok(allowed.has(color), `unexpected brand color #${color}`);
});
