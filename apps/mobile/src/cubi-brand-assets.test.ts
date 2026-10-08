import { test } from "node:test";
import assert from "node:assert/strict";
import { CUBI_BRAND_ASSETS } from "./cubi-brand-assets.js";

test("mobile consumes the canonical CUBI asset family", () => {
  assert.deepEqual(CUBI_BRAND_ASSETS, {
    light: "apps/web/public/cubi-platform-logo-primary.svg",
    dark: "apps/web/public/cubi-platform-logo-primary-dark.svg",
  });
});
