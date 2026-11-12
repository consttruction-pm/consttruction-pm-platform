import test from "node:test";
import assert from "node:assert/strict";
import {
  getLandingCopyForLocale,
  getLandingLanguageRoutes,
} from "./landing.js";
import { getLandingChromeCopy, normalizeLandingLocaleTag } from "./landing-chrome.js";
import { getWorkspaceLocaleDirection } from "./workspace-localization.js";

const launchLocales = ["en", "fa", "de", "zh-Hans", "zh-Hant", "ar", "fr", "ja", "ko"] as const;
const allHomepageLocales = [...launchLocales, "ru"];

test("homepage marketing copy and all visible dashboard chrome exist for every launch locale", () => {
  const english = getLandingCopyForLocale("en");
  for (const locale of allHomepageLocales) {
    const copy = getLandingCopyForLocale(locale);
    assert.equal(copy.nav.length, 6, `${locale}: all six primary navigation labels must be present`);
    assert.equal(copy.features.length, 6, `${locale}: all six feature cards must be present`);
    assert.equal(copy.techNodes.length, 4, `${locale}: all four technology nodes must be present`);
    assert.equal(copy.footerColumns.length, 3, `${locale}: all footer columns must be present`);
    assert.ok(copy.footerColumns.every((column) => column.links.length === 3), `${locale}: footer links must be complete`);
    assert.ok(copy.industriesTitle && copy.industriesBody, `${locale}: industry section must be translated`);
    assert.ok(copy.assistantTitle && copy.assistantDescription, `${locale}: assistant panel copy must be translated`);
    assert.ok(copy.chrome.pricing && copy.chrome.about && copy.chrome.company, `${locale}: public navigation labels must be present`);
    assert.equal(copy.chrome.dashboardSidebar.length, 5, `${locale}: dashboard sidebar labels must be complete`);
    for (const [key, value] of Object.entries(copy.chrome)) {
      if (Array.isArray(value)) {
        assert.ok(value.every((item) => typeof item === "string" && item.trim()), `${locale}: empty chrome item in ${key}`);
      } else {
        assert.ok(typeof value === "string" && value.trim(), `${locale}: empty chrome value in ${key}`);
      }
    }
    if (locale !== "en") {
      assert.notEqual(copy.title, english.title, `${locale}: headline must not silently fall back to English`);
      assert.notDeepEqual(copy.nav, english.nav, `${locale}: navigation must not silently fall back to English`);
    }
  }
});

test("Chinese script tags normalize deterministically to separate homepage catalogs", () => {
  assert.equal(normalizeLandingLocaleTag("zh"), "zh-Hans");
  assert.equal(normalizeLandingLocaleTag("zh-CN"), "zh-Hans");
  assert.equal(normalizeLandingLocaleTag("zh_SG"), "zh-Hans");
  assert.equal(normalizeLandingLocaleTag("zh-TW"), "zh-Hant");
  assert.equal(normalizeLandingLocaleTag("zh-HK"), "zh-Hant");
  assert.equal(normalizeLandingLocaleTag("zh-MO"), "zh-Hant");
  assert.notEqual(getLandingCopyForLocale("zh-CN").title, getLandingCopyForLocale("zh-TW").title);
  assert.notEqual(getLandingChromeCopy("zh-Hans").dashboardTitle, getLandingChromeCopy("zh-Hant").dashboardTitle);
});

test("homepage direction metadata keeps Persian and Arabic RTL and other launch locales LTR", () => {
  assert.equal(getWorkspaceLocaleDirection("fa"), "rtl");
  assert.equal(getWorkspaceLocaleDirection("ar"), "rtl");
  for (const locale of ["en", "de", "zh-Hans", "zh-Hant", "fr", "ja", "ko"]) {
    assert.equal(getWorkspaceLocaleDirection(locale), "ltr", `${locale} must be LTR`);
  }
});

test("homepage-only translations do not prematurely expose incomplete public-site locales", () => {
  assert.deepEqual(getLandingLanguageRoutes(["en", "fa", ...launchLocales, "ru"]), ["en", "fa"]);
});
