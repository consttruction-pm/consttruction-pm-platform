import { test } from "node:test";
import assert from "node:assert/strict";
import { CUBI_BRAND_ASSETS, cubiBrandAsset } from "./cubi-brand-assets.js";

test("web consumes the canonical CUBI asset family", () => {
  assert.equal(cubiBrandAsset("light"), "apps/web/public/cubi-platform-logo-primary.svg");
  assert.equal(cubiBrandAsset("dark"), "apps/web/public/cubi-platform-logo-primary-dark.svg");
  assert.notEqual(CUBI_BRAND_ASSETS.light, CUBI_BRAND_ASSETS.dark);
});
