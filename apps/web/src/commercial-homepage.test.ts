import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

const root = process.cwd();
const landing = readFileSync(join(root, "src/landing.ts"), "utf8");
const index = readFileSync(join(root, "index.html"), "utf8");
const styles = readFileSync(join(root, "styles.css"), "utf8");

test("CUBI homepage follows the canonical Issue #1101 reference structure", () => {
  assert.match(landing, /title:\s+"Construction Project Control,"/);
  assert.match(landing, /titleAccent:\s+"Reimagined\."/);
  assert.match(landing, /fa:\s+\{/);
  assert.match(landing, /cubi-reference-header/);
  assert.match(landing, /cubi-reference-hero/);
  assert.match(landing, /cubi-reference-dashboard/);
  assert.match(landing, /cubi-reference-feature-grid/);
  assert.match(landing, /cubi-reference-tech/);
  assert.match(landing, /cubi-reference-pricing/);
  assert.match(landing, /cubi-reference-footer/);
  assert.match(landing, /navFeatures/);
  assert.match(landing, /navSolutions/);
  assert.match(landing, /navPricing/);
  assert.match(landing, /navResources/);
  assert.match(landing, /navAbout/);
  assert.match(landing, /cubi-lang-switch/);
  assert.match(landing, /translations/);
  assert.match(landing, /\/logo\.svg/);
  assert.match(landing, /\/logo-dark\.svg/);
  assert.match(styles, /canonical CUBI visual-reference alignment/);
  assert.match(styles, /\.cubi-reference-hero\s*\{[\s\S]*background:#0b3158/);
  assert.match(styles, /\.cubi-reference-feature-grid\s*\{[\s\S]*grid-template-columns:repeat\(5/);
  assert.match(styles, /\.cubi-reference-tech\s*\{[\s\S]*background:#eef6ff/);
  assert.match(styles, /\.cubi-reference-pricing\s*\{[\s\S]*background:#092b50/);
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
  for (const pattern of [/Oracle/i, /Primavera/i, /P6/i]) {
    assert.doesNotMatch(landing, pattern);
    assert.doesNotMatch(index, pattern);
  }
});
