import assert from "node:assert/strict";
import test from "node:test";
import { createFontFaceCss } from "./language-fonts.ts";

test("creates deterministic font-face CSS for language-pack fonts", () => {
  const css = createFontFaceCss([{
    family: "Vazirmatn",
    uri: "https://example.invalid/fonts/vazirmatn.woff2",
    format: "woff2",
    weight: 400,
    style: "normal",
    unicode_range: "U+0600-06FF,U+200C",
  }]);
  assert.match(css, /@font-face/);
  assert.match(css, /font-family: "Vazirmatn"/);
  assert.match(css, /format("woff2")/);
  assert.match(css, /unicode-range: U\+0600-06FF,U\+200C/);
});
