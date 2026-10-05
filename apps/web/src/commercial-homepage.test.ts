import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

const root = process.cwd();
const landing = readFileSync(join(root, "src/landing.ts"), "utf8");
const index = readFileSync(join(root, "index.html"), "utf8");
const styles = readFileSync(join(root, "styles.css"), "utf8");

test("Issue 1239 compact homepage contract", () => {
  assert.match(landing, /Construction Project Control, <em>Reimagined\.<\/em>/);
  assert.match(landing, /Planning & Scheduling/);
  assert.match(landing, /Project Controls/);
  assert.match(landing, /AI Assistant/);
  assert.match(landing, /cubi-lang-switch/);
  assert.match(landing, /translations/);
  assert.match(landing, /\/logo\.svg/);
  assert.match(landing, /\/logo-dark\.svg/);
  assert.match(styles, /Issue 1239 — compact, user-centered bilingual commercial homepage/);
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
