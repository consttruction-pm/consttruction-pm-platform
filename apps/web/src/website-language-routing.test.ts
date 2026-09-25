import assert from "node:assert/strict";
import test from "node:test";

import {
  buildAlternateLanguagePaths,
  languageFromPath,
  languagePath,
  stripLanguagePrefix,
} from "./website-language-routing.ts";

test("creates localized site paths", () => {
  assert.deepEqual(languagePath("/pricing", "fa"), {
    languageTag: "fa",
    path: "/fa/pricing",
  });
  assert.deepEqual(languagePath("/", "en"), {
    languageTag: "en",
    path: "/en",
  });
});

test("detects a supported language from URL", () => {
  assert.equal(languageFromPath("/fa/pricing", ["fa", "en"]), "fa");
  assert.equal(languageFromPath("/de/pricing", ["fa", "en"]), null);
});

test("strips locale prefix before routing", () => {
  assert.equal(stripLanguagePrefix("/fa/pricing/", ["fa", "en"]), "/pricing");
  assert.equal(stripLanguagePrefix("/pricing", ["fa", "en"]), "/pricing");
});

test("builds alternate SEO language routes", () => {
  assert.deepEqual(buildAlternateLanguagePaths("/pricing", ["fa", "en"]), [
    { languageTag: "fa", path: "/fa/pricing" },
    { languageTag: "en", path: "/en/pricing" },
  ]);
});
