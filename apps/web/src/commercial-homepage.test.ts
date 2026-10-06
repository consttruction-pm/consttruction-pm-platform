import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

const root = process.cwd();
const landing = readFileSync(join(root, "src/landing.ts"), "utf8");
const index = readFileSync(join(root, "index.html"), "utf8");
const styles = readFileSync(join(root, "styles.css"), "utf8");

test("Issue 1241 reference-aligned homepage contract", () => {
  assert.match(landing, /Construction & Building/);
  assert.match(landing, /Everything You Need for Project Success/);
  assert.match(landing, /CUBI Intelligence & Engineering Core/);
  assert.match(landing, /cubi-hero-photo/);
  assert.match(landing, /Sample Data|داده نمونه/);
  assert.match(landing, /<svg viewBox="0 0 24 24"/);
  assert.doesNotMatch(landing, /[▦✦◫▤♧◌]/);
  assert.match(landing, /cubi-lang-switch/);
  assert.match(landing, /cubi-workflow/);
  assert.match(landing, /PLAN/);
  assert.match(landing, /برنامه‌ریزی/);
  assert.match(landing, /translations/);
  assert.match(landing, /\/logo\.svg/);
  assert.match(landing, /\/logo-dark\.svg/);
  assert.doesNotMatch(landing, /Primavera|Oracle|P6/);
  assert.match(styles, /Issue 1241 reference-aligned redesign/);
  assert.match(styles, /rastikerdar\/vazirmatn@v33\.003/);
});

test("registered SEO contract remains intact", () => {
  assert.match(index, /<title>Construction Project Management &amp; Project Controls Software<\/title>/);
  assert.match(index, /rel="canonical"/);
  assert.match(index, /name="robots"/);
  assert.match(index, /property="og:title"/);
  assert.match(index, /name="twitter:title"/);
  assert.match(index, /"@type": \["SoftwareApplication", "WebSite"\]/);
});
