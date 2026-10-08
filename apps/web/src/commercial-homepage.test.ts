import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

const root = process.cwd();
const landing = readFileSync(join(root, "src/landing.ts"), "utf8");
const index = readFileSync(join(root, "index.html"), "utf8");
const styles = readFileSync(join(root, "styles.css"), "utf8");

test("CUBI homepage follows the active compact commercial structure", () => {
  for (const pattern of [
    /cubi-compact-home/,
    /cubi-compact-header/,
    /cubi-compact-hero/,
    /cubi-compact-control/,
    /cubi-compact-capabilities/,
    /cubi-compact-cta/,
    /cubi-compact-footer/,
    /cubi-platform-logo-primary\.svg/,
    /cubi-platform-logo-primary-dark\.svg/,
  ]) assert.match(landing, pattern);
  assert.match(styles, /\.cubi-compact-header/);
  assert.match(styles, /\.cubi-compact-hero/);
  assert.match(styles, /\.cubi-compact-control/);
  assert.match(styles, /\.cubi-compact-grid/);
  assert.match(styles, /\.cubi-compact-cta/);
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


test("compact homepage includes bilingual control and product-control capabilities", () => {
  assert.match(landing, /type LandingLocale = "en" \\| "fa"/);
  assert.match(landing, /cubi-language/);
  for (const pattern of [/Planning &amp; Scheduling|برنامه‌ریزی و زمان‌بندی/, /Project Controls|کنترل پروژه/, /Resources &amp; Documents|منابع و اسناد/, /AI &amp; Insights|هوش مصنوعی و بینش/]) assert.match(landing, pattern);
});
