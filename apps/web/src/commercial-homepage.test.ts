import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

const root = process.cwd();
const landing = readFileSync(join(root, "src/landing.ts"), "utf8");
const index = readFileSync(join(root, "index.html"), "utf8");
const styles = readFileSync(join(root, "styles.css"), "utf8");

test("CUBI homepage follows the registered full commercial structure", () => {
  for (const pattern of [
    /cubi-reference-home/,
    /cubi-exact-home/,
    /cubi-exact-header/,
    /cubi-exact-hero/,
    /cubi-exact-dashboard/,
    /cubi-exact-features/,
    /cubi-exact-tech/,
    /cubi-exact-cta/,
    /cubi-exact-footer/,
    /cubi-platform-logo-primary\.svg/,
    /cubi-platform-logo-primary-dark\.svg/,
    /cubi-hero-field\.svg/,
  ]) assert.match(landing + styles, pattern);
});

test("registered SEO contract remains intact", () => {
  assert.match(index, /<title>Construction Project Management &amp; Project Controls Software<\/title>/);
  assert.match(index, /rel="canonical"/);
  assert.match(index, /name="robots"/);
  assert.match(index, /property="og:title"/);
  assert.match(index, /name="twitter:title"/);
  assert.match(index, /"@type": \["SoftwareApplication", "WebSite"\]/);
});

test("commercial surface stays independent of external product provenance", () => {
  for (const pattern of [/Oracle/i, /Primavera/i, />\\s*P6\\s*</i]) {
    assert.doesNotMatch(landing, pattern);
    assert.doesNotMatch(index, pattern);
  }
});


test("full homepage keeps bilingual control and the six capability areas", () => {
  assert.match(landing, /type LandingLocale = "en" \| "fa"/);
  assert.match(landing, /cubi-language/);
  for (const pattern of [
    /Project Controls|کنترل پروژه/,
    /AI Assistant|دستیار هوشمند/,
    /Resources & Cost|منابع و هزینه/,
    /Documents & Contracts|اسناد و قراردادها/,
    /Team Collaboration|همکاری تیمی/,
    /Cloud & Scalability|ابر و توسعه‌پذیری/,
  ]) assert.match(landing, pattern);
});
