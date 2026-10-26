import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { CUBI_BRAND_ASSETS, CUBI_BRAND_ASSET, CUBI_ASSISTANT_AVATAR_ASSET } from "./cubi-brand-assets.js";

test("desktop consumes one canonical CUBI logo for every presentation variant", () => {
  assert.deepEqual(CUBI_BRAND_ASSETS, {
    light: CUBI_BRAND_ASSET,
    dark: CUBI_BRAND_ASSET,
  });
  assert.equal(CUBI_BRAND_ASSET, "apps/web/public/cubi-platform-logo-primary.svg");
  assert.equal(CUBI_ASSISTANT_AVATAR_ASSET, "apps/web/public/cubi-assistant-avatar.svg");
});

test("desktop can read the canonical shared assistant avatar asset", () => {
  assert.equal(CUBI_ASSISTANT_AVATAR_ASSET, "apps/web/public/cubi-assistant-avatar.svg");
  const svg = readFileSync(new URL("../../web/public/cubi-assistant-avatar.svg", import.meta.url), "utf8");
  assert.match(svg, /<svg[^>]+viewBox="0 0 256 256"/);
  assert.match(svg, /CUBI AI Project Assistant/);
});
