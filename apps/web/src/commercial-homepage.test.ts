import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

const root = process.cwd();
const landing = readFileSync(join(root, "src/landing.ts"), "utf8");
const index = readFileSync(join(root, "index.html"), "utf8");
const styles = readFileSync(join(root, "styles.css"), "utf8");

test("canonical CUBI reference homepage contract remains presentation-only", () => {
  assert.match(landing, /cubi-logo-lockup\.svg/);
  assert.match(landing, /cubi-logo-lockup-dark\.svg/);
  assert.match(landing, /Construction &/);
  assert.match(landing, /Building Intelligence/);
  assert.match(landing, /Project Controls/);
  assert.match(landing, /AI Assistant/);
  assert.match(landing, /Resources & Cost/);
  assert.match(landing, /Documents & Contracts/);
  assert.match(landing, /Collaboration/);
  assert.match(landing, /Cloud & Scalability/);
  assert.match(landing, /translations/);
  assert.match(styles, /\.cubi-reference-hero/);
  assert.match(styles, /\.cubi-reference-dashboard/);
  assert.match(styles, /\.cubi-reference-feature-grid/);
  assert.match(styles, /\.cubi-reference-tech/);
  assert.match(styles, /\.cubi-reference-cta/);
});

test("registered SEO contract remains intact", () => {
  assert.match(index, /<title>Construction Project Management &amp; Project Controls Software<\/title>/);
  assert.match(index, /rel="canonical"/);
  assert.match(index, /name="robots"/);
  assert.match(index, /property="og:title"/);
  assert.match(index, /name="twitter:title"/);
  assert.match(index, /"@type": \["SoftwareApplication", "WebSite"\]/);
});

test("commercial surface stays provenance-neutral", () => {
  for (const pattern of [/Oracle/i, /Primavera/i, /P6/i]) {
    assert.doesNotMatch(landing, pattern);
    assert.doesNotMatch(index, pattern);
  }
});
