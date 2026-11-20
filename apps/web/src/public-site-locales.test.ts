import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

/**
 * Contract for the localized public website.
 *
 * Ten locales ship real documents with the correct lang/dir attributes, a
 * canonical URL, an x-default alternate and a language switcher that reaches
 * every locale publishing the same page. English carries the target inventory
 * of 25 indexable routes; every internal link must resolve to a shipped file.
 */
const root = process.cwd();
const publicRoot = join(root, "public");

const LOCALES = [
  { code: "en", prefix: "", lang: "en", dir: "ltr" },
  { code: "fa", prefix: "fa/", lang: "fa", dir: "rtl" },
  { code: "de", prefix: "de/", lang: "de", dir: "ltr" },
  { code: "fr", prefix: "fr/", lang: "fr", dir: "ltr" },
  { code: "ru", prefix: "ru/", lang: "ru", dir: "ltr" },
  { code: "tr", prefix: "tr/", lang: "tr-TR", dir: "ltr" },
  { code: "ja", prefix: "ja/", lang: "ja", dir: "ltr" },
  { code: "ko", prefix: "ko/", lang: "ko", dir: "ltr" },
  { code: "zh", prefix: "zh/", lang: "zh-CN", dir: "ltr" },
  { code: "ar", prefix: "ar/", lang: "ar", dir: "rtl" },
] as const;

const ENGLISH_ROUTES = [
  "", "platform/", "features/", "features/scheduling/", "features/project-controls/",
  "features/resources/", "features/cost/", "features/documents/", "features/risks/",
  "features/reporting/", "features/ai-assistant/", "solutions/", "integrations/",
  "pricing/", "resources/", "documentation/", "help/", "faq/", "about/", "security/",
  "payments/", "contact/", "get-started/", "privacy/", "terms/",
] as const;

const homeFile = (prefix: string) => (prefix === "" ? join(root, "index.html") : join(publicRoot, prefix, "index.html"));
const pageFile = (prefix: string, route: string) =>
  route === "" && prefix === "" ? join(root, "index.html") : join(publicRoot, prefix, route, "index.html");

test("English ships the 25-route indexable inventory", () => {
  assert.equal(ENGLISH_ROUTES.length, 25);
  for (const route of ENGLISH_ROUTES) {
    const file = pageFile("", route);
    assert.ok(existsSync(file), `missing English route /${route}`);
    const html = readFileSync(file, "utf8");
    assert.match(html, /<meta name="robots" content="index/, `/${route} must be indexable`);
    if (route === "") {
      // The English homepage canonical is resolved to the site root during assembly.
      assert.ok(/<link rel="canonical" href="(\.\/|__CUBI_BASE_URL__\/)"/.test(html), "/ canonical");
    } else {
      assert.ok(html.includes(`<link rel="canonical" href="__CUBI_BASE_URL__/${route}"`), `/${route} canonical`);
    }
  }
});

test("ten locales publish a translated homepage with the right language and direction", () => {
  for (const locale of LOCALES) {
    const file = homeFile(locale.prefix);
    assert.ok(existsSync(file), `${locale.code} homepage missing`);
    const html = readFileSync(file, "utf8");
    assert.ok(html.includes(`<html lang="${locale.lang}" dir="${locale.dir}">`), `${locale.code} lang/dir`);
    assert.ok(html.includes('hreflang="x-default"'), `${locale.code} x-default alternate`);
    assert.ok(html.includes("global-assistant-launcher.bundle.js"), `${locale.code} must mount the shared assistant`);
    if (locale.dir === "rtl") assert.match(html, /[\u0600-\u06FF]{4,}/, `${locale.code} must carry real RTL copy`);
    if (locale.code !== "en") assert.ok(html.includes('hreflang="en"'), `${locale.code} must link back to English`);
  }
});

test("each homepage declares an alternate for every published locale including tr-TR", () => {
  for (const locale of LOCALES) {
    const html = readFileSync(homeFile(locale.prefix), "utf8");
    for (const alternate of LOCALES) {
      assert.ok(
        html.includes(`<link rel="alternate" hreflang="${alternate.lang}"`),
        `${locale.code} homepage must declare the ${alternate.code} alternate`,
      );
    }
  }
});

test("localized subpages carry translated copy rather than the English route", () => {
  const english = readFileSync(pageFile("", "features/"), "utf8");
  for (const prefix of ["de/", "tr/", "ja/", "ar/"]) {
    const html = readFileSync(pageFile(prefix, "features/"), "utf8");
    assert.notEqual(
      html.match(/<h1>([^<]+)<\/h1>/)?.[1],
      english.match(/<h1>([^<]+)<\/h1>/)?.[1],
      `${prefix}features must not reuse the English headline`,
    );
    assert.ok(html.includes('<link rel="alternate" hreflang="en"'), `${prefix}features must offer English`);
  }
});

test("every locale publishes all 25 approved routes with its own headline", () => {
  for (const locale of LOCALES) {
    if (locale.code === "en") continue;
    for (const route of ENGLISH_ROUTES) {
      const file = pageFile(locale.prefix, route);
      assert.ok(existsSync(file), `${locale.code} is missing /${route}`);
      const html = readFileSync(file, "utf8");
      const englishHtml = readFileSync(pageFile("", route), "utf8");
      assert.ok(html.includes(`<html lang="${locale.lang}" dir="${locale.dir}">`), `${locale.code} /${route} lang/dir`);
      assert.ok(
        html.includes(`<link rel="canonical" href="__CUBI_BASE_URL__/${locale.prefix}${route}"`),
        `${locale.code} /${route} canonical`,
      );
      const h1 = html.match(/<h1>([^<]+)<\/h1>/)?.[1];
      const englishH1 = englishHtml.match(/<h1>([^<]+)<\/h1>/)?.[1];
      if (route === "") {
        // Homepages render their headline from the landing bundle, so the
        // localized <title> is the stable proof that copy is not reused.
        const title = html.match(/<title>([^<]+)<\/title>/)?.[1];
        const englishTitle = englishHtml.match(/<title>([^<]+)<\/title>/)?.[1];
        assert.ok(title, `${locale.code} homepage must have a title`);
        assert.notEqual(title, englishTitle, `${locale.code} homepage must not reuse the English title`);
        continue;
      }
      assert.ok(h1, `${locale.code} /${route} must have a headline`);
      assert.notEqual(h1, englishH1, `${locale.code} /${route} must not reuse the English headline`);
    }
  }
});

test("Turkish is a first-class locale with the tr-TR language tag", () => {
  const features = readFileSync(pageFile("tr/", "features/"), "utf8");
  assert.ok(features.includes('<html lang="tr-TR" dir="ltr">'));
  assert.ok(features.includes('<link rel="canonical" href="__CUBI_BASE_URL__/tr/features/"'));
  assert.ok(readFileSync(pageFile("", "features/"), "utf8").includes('hreflang="tr-TR"'));
  assert.ok(existsSync(homeFile("tr/")));
});

test("no localized document links to a route that has no shipped document", () => {
  const htmlFiles: string[] = [];
  const walk = (directory: string) => {
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      const path = join(directory, entry.name);
      if (entry.isDirectory()) walk(path);
      else if (entry.name.endsWith(".html")) htmlFiles.push(path);
    }
  };
  walk(publicRoot);
  htmlFiles.push(join(root, "index.html"));
  assert.ok(htmlFiles.length >= 100, `expected the generated locale tree, found ${htmlFiles.length} documents`);

  const resolves = (absolute: string): string => {
    let candidate = absolute;
    if (existsSync(candidate) && statSync(candidate).isDirectory()) candidate = join(candidate, "index.html");
    // The English homepage lives at apps/web/index.html, outside the public tree.
    if (!existsSync(candidate) && candidate === join(publicRoot, "index.html")) return join(root, "index.html");
    return candidate;
  };

  for (const file of htmlFiles) {
    const html = readFileSync(file, "utf8");
    for (const match of html.matchAll(/(?:href|src)="([^"]+)"/g)) {
      const target = match[1];
      if (target.startsWith("__CUBI_BASE_URL__")) continue;
      if (/^(https?:|mailto:|tel:|data:|\/\/)/.test(target)) continue;
      // Build output and the assembled workspace shell are created by the Pages step.
      if (/(^|\/)dist\//.test(target) || /(^|\/)app\/?$/.test(target)) continue;
      const clean = target.split("#")[0].split("?")[0];
      if (!clean) continue;
      // The root homepage is assembled next to the public assets, so resolve its
      // relative references against the public tree.
      const base = file === join(root, "index.html") ? publicRoot : dirname(file);
      const absolute = clean.startsWith("/") ? join(publicRoot, clean) : resolve(base, clean);
      if (!/\.(html|css|svg|js|png|jpg|jpeg|webp|ico)$/.test(clean) && !clean.endsWith("/")) continue;
      assert.ok(
        existsSync(resolves(absolute)),
        `${file.slice(root.length + 1)} links "${target}" which resolves outside the shipped site`,
      );
    }
  }
});
