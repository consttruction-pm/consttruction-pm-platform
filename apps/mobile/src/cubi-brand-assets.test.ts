import { test } from "node:test";
import assert from "node:assert/strict";
import { CUBI_BRAND_ASSETS, CUBI_BRAND_ASSET } from "./cubi-brand-assets.js";

test("mobile consumes one canonical CUBI logo for every presentation variant", () => {
  assert.deepEqual(CUBI_BRAND_ASSETS, {
    light: CUBI_BRAND_ASSET,
    dark: CUBI_BRAND_ASSET,
  });
  assert.equal(CUBI_BRAND_ASSET, "apps/web/public/cubi-platform-logo-primary.svg");
});
