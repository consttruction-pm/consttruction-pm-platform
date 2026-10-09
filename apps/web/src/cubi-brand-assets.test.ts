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

test("web, desktop and mobile brand contracts all use the canonical asset path", () => {
  const desktop = readFileSync(new URL("../../desktop/src/cubi-brand-assets.ts", import.meta.url), "utf8");
  const mobile = readFileSync(new URL("../../mobile/src/cubi-brand-assets.ts", import.meta.url), "utf8");
  for (const client of [desktop, mobile]) {
    assert.ok(client.includes("apps/web/public/cubi-platform-logo-primary.svg"));
    assert.ok(!client.includes("logo-dark.svg"));
    assert.ok(!client.includes("cubi-platform-logo-primary-dark.svg"));
  }
});

test("homepage favicon and social previews point to the canonical logo", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.ok(html.includes('rel="icon" href="./cubi-platform-logo-primary.svg"'));
  assert.ok(html.includes('property="og:image" content="./cubi-platform-logo-primary.svg"'));
  assert.ok(html.includes('name="twitter:image" content="./cubi-platform-logo-primary.svg"'));
});

test("canonical SVG preserves the approved C-shaped cube lockup and tagline", () => {
  const svg = readFileSync(new URL("../public/cubi-platform-logo-primary.svg", import.meta.url), "utf8");
  assert.ok(svg.includes('viewBox="0 0 640 180"'));
  assert.ok(svg.includes("CUBI's connected C-shaped isometric mark surrounding a teal cube"));
  assert.ok(svg.includes("PLAN. CONTROL. BUILD SMARTER."));
  assert.ok(svg.includes("#00BFEA") || svg.includes("#078BFF"));
  assert.ok(svg.includes("#19D5D0") || svg.includes("#0AA6A7"));
  assert.ok(svg.includes('fill="url(#cubeFront)"'));
  assert.ok(svg.includes('fill="url(#cubeSide)"'));
  assert.ok(!svg.includes("M48 58 82 38 121 60 89 79"));
  assert.ok(!svg.includes("cubi-platform-logo-primary-dark.svg"));
  assert.ok(!svg.includes("logo-dark.svg"));
});
