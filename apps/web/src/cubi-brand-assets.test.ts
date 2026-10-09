import assert from "node:assert/strict";
import { test } from "node:test";
import { CUBI_BRAND_ASSETS, CUBI_BRAND_ASSET, cubiBrandAsset } from "./cubi-brand-assets.js";

test("all client variants resolve to one canonical approved CUBI logo", () => {
  assert.equal(CUBI_BRAND_ASSET, "apps/web/public/cubi-platform-logo-primary.svg");
  assert.equal(cubiBrandAsset("light"), CUBI_BRAND_ASSET);
  assert.equal(cubiBrandAsset("dark"), CUBI_BRAND_ASSET);
  assert.equal(CUBI_BRAND_ASSETS.light, CUBI_BRAND_ASSETS.dark);
});

test("homepage canonical URL stays relative for GitHub Pages project paths", async () => {
  const { readFileSync } = await import("node:fs");
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(html, /<link rel="canonical" href="\.\/"\s*\/>/);
  assert.doesNotMatch(html, /<link rel="canonical" href="\/"\s*\/>/);
});
