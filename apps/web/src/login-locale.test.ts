import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const html = readFileSync(new URL("../login.html", import.meta.url), "utf8");

function objectLiteral(name: string): string {
  const start = html.indexOf(`const ${name} = {`);
  assert.ok(start >= 0, `${name} must be declared`);
  const depthFrom = html.indexOf("{", start);
  let depth = 0;
  for (let index = depthFrom; index < html.length; index += 1) {
    const char = html[index];
    if (char === "{") depth += 1;
    else if (char === "}") {
      depth -= 1;
      if (depth === 0) return html.slice(depthFrom, index + 1);
    }
  }
  throw new Error(`${name} is not closed`);
}

// The login page is a standalone module (no bundler), so the copy tables are
// read straight from the shipped HTML and evaluated as literals.
const COPY = new Function(`return (${objectLiteral("COPY")});`)() as Record<
  string,
  Record<string, string>
>;
const DIRECTION = new Function(`return (${objectLiteral("DIRECTION")});`)() as Record<string, string>;
const HTML_LANG = new Function(`return (${objectLiteral("HTML_LANG")});`)() as Record<string, string>;

const LOCALES = ["en", "fa", "de", "zh", "ar", "fr", "ja", "ko", "ru", "tr"];
const KEYS = [
  "product",
  "title",
  "lead",
  "username",
  "password",
  "submit",
  "signup",
  "usernameTaken",
  "forgot",
  "forgotHelp",
  "working",
  "footer",
  "failed",
  "throttled",
  "invalid",
  "network",
];

test("the login page ships all ten approved locales", () => {
  assert.deepEqual(Object.keys(COPY).sort(), [...LOCALES].sort());
  assert.deepEqual(Object.keys(HTML_LANG).sort(), [...LOCALES].sort());
});

test("every login locale translates every visible sentence", () => {
  for (const locale of LOCALES) {
    const copy = COPY[locale];
    for (const key of KEYS) {
      assert.equal(typeof copy[key], "string", `${locale}.${key}`);
      assert.ok(copy[key].trim().length > 0, `${locale}.${key} must not be empty`);
    }
    assert.equal(Object.keys(copy).length, KEYS.length, `${locale} must not carry stray keys`);
  }
  for (const locale of ["fa", "de", "zh", "ar", "fr", "ja", "ko", "ru", "tr"]) {
    for (const key of ["product", "title", "lead", "password", "submit", "failed"]) {
      assert.notEqual(COPY[locale][key], COPY.en[key], `${locale}.${key} must not reuse English`);
    }
  }
});

test("the login page declares RTL for Persian and Arabic and correct BCP 47 tags", () => {
  assert.equal(DIRECTION.fa, "rtl");
  assert.equal(DIRECTION.ar, "rtl");
  for (const locale of ["en", "de", "zh", "fr", "ja", "ko", "ru", "tr"]) {
    assert.equal(DIRECTION[locale], undefined, `${locale} must stay left-to-right`);
  }
  assert.equal(HTML_LANG.zh, "zh-CN");
  assert.equal(HTML_LANG.tr, "tr-TR");
  assert.equal(HTML_LANG.fa, "fa");
});

test("the language selector offers exactly the supported locales", () => {
  const values = [...html.matchAll(/<option value="([a-z]+)">/g)].map((match) => match[1]);
  assert.deepEqual(values, LOCALES);
  assert.ok(html.includes('id="cp-login-locale"'));
  assert.ok(!html.includes("cp-login-locale\").textContent"));
  assert.ok(html.includes('STORAGE_KEY = "cubi.login.locale"'));
});
