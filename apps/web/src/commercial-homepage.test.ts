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
    /cubi-hero-field\.svg/,
  ]) assert.match(landing + styles, pattern);
  assert.doesNotMatch(landing + styles + index, /cubi-platform-logo-primary-dark\.svg|logo-dark\.svg/);
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


test("landing language preference is restored and persisted safely", () => {
  assert.match(landing, /LANDING_LOCALE_STORAGE_KEY = "cubi:landing-locale"/);
  assert.match(landing, /function restoreLandingLocale\(\): void/);
  assert.match(landing, /saved === "en" \|\| saved === "fa"/);
  assert.match(landing, /function persistLandingLocale\(\): void/);
  assert.match(landing, /restoreLandingLocale\(\);/);
  assert.match(landing, /persistLandingLocale\(\);/);
  assert.match(landing, /container\.dataset\.localeInitialized !== "true"/);
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

test("homepage navigation and footer connect to real public routes", () => {
  for (const route of ["./platform/", "./solutions/", "./resources/", "./contact/"]) {
    assert.ok(landing.includes(route), "Expected homepage link to " + route);
  }
  assert.match(landing, /\.\/platform\/#project-controls/);
  assert.match(landing, /\.\/solutions\/#construction-teams/);
  assert.match(landing, /\.\/resources\/#documentation/);
});

test("standalone public pages have unique metadata and expected content", () => {
  const pages = [
    ["public/platform/index.html", "CUBI Platform | Construction Project Controls", "scheduling"],
    ["public/solutions/index.html", "CUBI Solutions | Construction Project Delivery", "construction-teams"],
    ["public/resources/index.html", "CUBI Resources | Product Overview and Documentation", "documentation"],
    ["public/contact/index.html", "Contact CUBI | Account Access and Product Information", "Direct contact channel"],
  ];
  for (const [path, title, marker] of pages) {
    const html = readFileSync(join(root, path), "utf8");
    assert.ok(html.includes("<title>" + title + "</title>"), path + " should have a unique title");
    assert.ok(html.includes('name="description"'), path + " should have a description");
    assert.ok(html.includes(marker), path + " should have its expected content");
  }
});
