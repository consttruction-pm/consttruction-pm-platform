import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { CUBI_BRAND_ASSETS, CUBI_BRAND_ASSET, cubiBrandAsset } from "./cubi-brand-assets.js";

test("all client variants resolve to one canonical approved CUBI logo", () => {
  assert.equal(CUBI_BRAND_ASSET, "apps/web/public/cubi-platform-logo-primary.svg");
  assert.equal(cubiBrandAsset("light"), CUBI_BRAND_ASSET);
  assert.equal(cubiBrandAsset("dark"), CUBI_BRAND_ASSET);
  assert.equal(CUBI_BRAND_ASSETS.light, CUBI_BRAND_ASSETS.dark);
});

test("canonical SVG preserves the approved C-shaped cube lockup and tagline", () => {
  const svg = readFileSync("public/cubi-platform-logo-primary.svg", "utf8");
  assert.match(svg, /viewBox="0 0 640 180"/);
  assert.match(svg, /CUBI's connected C-shaped isometric mark surrounding a teal cube/);
  assert.match(svg, /PLAN\. CONTROL\. BUILD SMARTER\./);
  assert.match(svg, /#00BFEA|#078BFF/);
  assert.match(svg, /#19D5D0|#0AA6A7/);
  assert.doesNotMatch(svg, /cubi-platform-logo-primary-dark\.svg|logo-dark\.svg/);
});
