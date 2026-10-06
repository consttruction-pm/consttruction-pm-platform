import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const primaryLogo = readFileSync(new URL("../public/logo.svg", import.meta.url), "utf8");
const darkLogo = readFileSync(new URL("../public/logo-dark.svg", import.meta.url), "utf8");

test("CUBI visual system exposes the approved blue/cyan brand anchors", () => {
  for (const token of ["--cubi-deep-navy","--cubi-engineering-blue","--cubi-copper-orange","--cubi-brushed-titanium"]) {
    assert.match(css, new RegExp(token));
  }
});

test("homepage follows the approved white-nav, photographic hero and blue-CTA direction", () => {
  assert.match(css, /\.cubi-header[^\{]*\{[^}]*background:#fff/s);
  assert.match(css, /\.cubi-hero-photo[^\{]*\{[^}]*url\("\/cubi-hero-field\.svg"\)/s);
  assert.match(css, /\.cubi-button[^\{]*\{[^}]*#087cf2/s);
});

test("CUBI logos use only the approved blue/cyan palette", () => {
  const colors = [...(primaryLogo + darkLogo).matchAll(/#[0-9A-Fa-f]{6}/g)].map((m) => m[0].slice(1).toUpperCase());
  assert.ok(colors.length > 0);
  for (const color of colors) assert.ok(["078FF5","13D0E3","0756B8","1689E8","071C31","0C67C7","13B8C4"].includes(color), `unexpected brand color #${color}`);
});
