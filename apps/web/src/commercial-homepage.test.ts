import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

const root = process.cwd();
const landing = readFileSync(join(root, "src/landing.ts"), "utf8");
const index = readFileSync(join(root, "index.html"), "utf8");
const styles = readFileSync(join(root, "styles.css"), "utf8");

test("Issue 1239 compact homepage contract", () => {
  assert.match(landing, /title:\s+"Construction Project Control,"/);
  assert.match(landing, /titleAccent:\s+"Reimagined\."/);
  assert.match(landing, /fa:\s+\{/);
  assert.match(landing, /Planning & Scheduling/);
  assert.match(landing, /Project Controls/);
  assert.match(landing, /AI Assistant/);
  assert.match(landing, /cubi-lang-switch/);
  assert.match(landing, /translations/);
  assert.match(landing, /\/logo\.svg/);
  assert.match(landing, /\/logo-dark\.svg/);
  assert.match(landing, /<div class="cubi-orbit"><img src="\/logo-dark\.svg"/);
  assert.match(landing, /demo: "Demo"/);
  assert.match(landing, /demo: "نمونه"/);
  assert.match(styles, /Issue 1239 — compact, user-centered bilingual commercial homepage/);
  assert.match(styles, /\.cubi-hero\s*\{[^}]*background:\s*var\(--cp-navy-dark\)/s);
  assert.match(styles, /\.cubi-button\s*\{[^}]*background:\s*var\(--cp-copper\)/s);
  assert.match(styles, /\.cubi-header\s*\{[^}]*backdrop-filter:\s*none/s);
  assert.match(styles, /@media\s*\(prefers-reduced-motion:\s*reduce\)/);
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
