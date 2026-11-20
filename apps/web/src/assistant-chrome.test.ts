import assert from "node:assert/strict";
import test from "node:test";
import {
  ASSISTANT_CHROME_LOCALES,
  ASSISTANT_CHROME_SOURCES,
  translateAssistantChrome,
} from "./assistant-chrome-translations.js";

test("the assistant chrome is translated in every built-in non-English locale", () => {
  assert.deepEqual([...ASSISTANT_CHROME_LOCALES].sort(), ["ar", "de", "fr", "ja", "ko", "ru", "tr", "zh"]);
  for (const locale of ASSISTANT_CHROME_LOCALES) {
    for (const source of ASSISTANT_CHROME_SOURCES) {
      const text = translateAssistantChrome(locale, source);
      assert.notEqual(text, source, `${locale} must not fall back for "${source}"`);
      assert.ok(text.trim().length > 0, `${locale} must not return an empty string`);
      assert.ok(!text.includes("landing.assistant"), `${locale} must not expose a raw key`);
    }
  }
});

test("English and unrecognized locales keep the source sentence", () => {
  for (const source of ASSISTANT_CHROME_SOURCES) {
    assert.equal(translateAssistantChrome("en", source), source);
    assert.equal(translateAssistantChrome("xx", source), source);
    assert.equal(translateAssistantChrome("", source), source);
  }
});

test("a regional tag resolves through its base language", () => {
  assert.equal(translateAssistantChrome("tr", "Next steps"), "Sonraki adımlar");
  assert.equal(translateAssistantChrome("zh", "Next steps"), "后续步骤");
});
