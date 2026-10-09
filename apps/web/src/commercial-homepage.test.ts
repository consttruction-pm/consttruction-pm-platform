import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

const root = process.cwd();
const landing = readFileSync(join(root, "src/landing.ts"), "utf8");
const index = readFileSync(join(root, "index.html"), "utf8");
const styles = readFileSync(join(root, "styles.css"), "utf8");
const logo = readFileSync(join(root, "public/cubi-platform-logo-primary.svg"), "utf8");

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
    /cubi-hero-field\.svg/,
  ]) assert.match(landing + styles, pattern);
  assert.doesNotMatch(landing + styles + index, /cubi-platform-logo-primary-dark\.svg|logo-dark\.svg/);
});

test("canonical CUBI logo keeps an accessible open mark and distinct teal cube faces", () => {
  assert.match(logo, /aria-labelledby="title desc"/);
  assert.match(logo, /CUBI Platform/);
  assert.match(logo, /PLAN\. CONTROL\. BUILD SMARTER\./);
  assert.match(logo, /id="cubeFront"/);
  assert.match(logo, /id="cubeSide"/);
  assert.match(logo, /fill="url\(#cubeFront\)"/);
  assert.match(logo, /fill="url\(#cubeSide\)"/);
  assert.doesNotMatch(logo, /cubi-platform-logo-primary-dark\.svg|logo-dark\.svg/);
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
  for (const pattern of [/Oracle/i, /Primavera/i, />\s*P6\s*</i]) {
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

test("Persian homepage mirrors dashboard and technology layout in RTL mode", () => {
  assert.match(styles, /\[dir="rtl"\] \.cubi-exact-dashboard\s*\{[^}]*margin-right:\s*-1\.5rem/);
  assert.match(styles, /\[dir="rtl"\] \.cubi-tech-node\.n1,[\s\S]*?right:\s*0/);
  assert.match(styles, /\[dir="rtl"\] \.cubi-footer-brand img\s*\{[^}]*object-position:\s*right center/);
});

test("homepage footer links target the relevant page sections", () => {
  assert.match(landing, /targets = \[\["#capabilities", "#technology", "#capabilities"\], \["#capabilities", "#technology", "#resources"\], \["#resources", "#technology", "#resources"\]\]/);
  assert.doesNotMatch(landing, /col\.links\.map\(\(link\) => `<a href="#resources">`/);
});
