import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { CUBI_ASSISTANT_AVATAR_ASSET, CUBI_BRAND_ASSETS, CUBI_BRAND_ASSET, cubiAssistantAvatarUrl, cubiBrandAsset } from "./cubi-brand-assets.js";

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

test("assistant avatar URL resolves from compiled Web assets and preserves GitHub Pages project paths", () => {
  assert.equal(CUBI_ASSISTANT_AVATAR_ASSET, "apps/web/public/cubi-assistant-avatar.svg");
  assert.equal(
    cubiAssistantAvatarUrl("https://cubi.example.test/dist/web/src/cubi-brand-assets.js"),
    "https://cubi.example.test/cubi-assistant-avatar.svg",
  );
  assert.equal(
    cubiAssistantAvatarUrl("https://owner.github.io/cubi-project/dist/web/src/cubi-brand-assets.js"),
    "https://owner.github.io/cubi-project/cubi-assistant-avatar.svg",
  );
  const asset = new URL("../public/cubi-assistant-avatar.svg", import.meta.url);
  assert.ok(existsSync(asset), "shared avatar SVG must be present in the Web public directory");
  assert.match(readFileSync(asset, "utf8"), /<title id="title">CUBI AI Project Assistant<\/title>/);
  const svg = readFileSync(asset, "utf8");
  assert.match(svg, /data:image\/jpeg;base64,/);
  assert.match(svg, /<image[^>]+preserveAspectRatio="xMidYMid slice"/);
  assert.match(svg, /class="day"/);
  assert.match(svg, /class="night"/);
  assert.match(svg, /prefers-color-scheme:\s*dark/);
});
