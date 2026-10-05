import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

const root = process.cwd();
const landing = readFileSync(join(root, "src/landing.ts"), "utf8");
const index = readFileSync(join(root, "index.html"), "utf8");

test("commercial homepage exposes the registered navigation and H1", () => {
  for (const id of ["product", "solutions", "features", "pricing", "ai", "resources"]) {
    assert.match(landing, new RegExp('href="#' + id + '"'));
  }
  assert.match(landing, /Construction Project Control, <em>Reimagined\.<\/em>/);
  assert.match(landing, /Plan\. Control\. Build Smarter\./);
});

test("commercial homepage exposes the required SEO contract", () => {
  assert.match(index, /<title>Construction Project Management &amp; Project Controls Software<\/title>/);
  assert.match(index, /rel="canonical"/);
  assert.match(index, /name="robots"/);
  assert.match(index, /property="og:title"/);
  assert.match(index, /name="twitter:title"/);
  assert.match(index, /"@type": \["SoftwareApplication", "WebSite"\]/);
});


test("commercial surfaces do not expose external product provenance", () => {
  for (const pattern of [/Oracle/i, /Primavera/i, /P6/i]) {
    assert.doesNotMatch(landing, pattern);
    assert.doesNotMatch(index, pattern);
  }
});
