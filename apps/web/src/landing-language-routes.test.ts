import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";
import {
  DEFAULT_LANDING_LOCALE,
  resolveLandingLanguageHref,
  resolveLandingLocaleFromPath,
} from "./landing.js";

const root = process.cwd();

/**
 * The route model of the shipped Pages artifact. A relative link inside a public
 * document that lands outside this set is a dead route, exactly the class of bug
 * a directory URL such as /contact/ creates when a href is written as ./fa/...
 */
const SHIPPED_ROUTES = new Set([
  "/",
  "/fa/",
  "/platform/",
  "/solutions/",
  "/resources/",
  "/contact/",
  "/pricing/",
  "/fa/pricing/",
  "/fa/platform/",
  "/fa/solutions/",
  "/fa/resources/",
  "/fa/contact/",
  "/app/",
]);

const MARKETING_ROUTES = ["platform", "solutions", "resources", "contact", "pricing"] as const;

function readDoc(relativePath: string): string {
  return readFileSync(join(root, relativePath), "utf8");
}

/** Every internal link of a document, with its URL fragments removed. */
function internalRouteLinks(documentText: string): string[] {
  return [...documentText.matchAll(/href="([^"]+)"/g)]
    .map((match) => match[1].split("#")[0])
    .filter((href) => href.length > 0)
    .filter((href) => !/^(https?:|mailto:|tel:|data:|\/\/)/.test(href))
    .filter((href) => !href.includes("__CUBI_BASE_URL__"));
}

test("the landing language is read from the URL, not from storage alone", () => {
  for (const pathname of ["/", "/index.html", "/platform/", "/app/", "/fa/platform/"]) {
    assert.equal(resolveLandingLocaleFromPath(pathname), null, `${pathname} is not a language route`);
  }
  for (const pathname of ["/fa", "/fa/", "/fa/index.html", "/consttruction-pm-platform/fa/"]) {
    assert.equal(resolveLandingLocaleFromPath(pathname), "fa", `${pathname} carries the Persian landing`);
  }
});

test("switching language produces the twin route and keeps the site base path", () => {
  assert.equal(resolveLandingLanguageHref("fa", "/"), "/fa/");
  assert.equal(resolveLandingLanguageHref("fa", "/index.html"), "/fa/");
  assert.equal(resolveLandingLanguageHref(DEFAULT_LANDING_LOCALE, "/"), "/");
  assert.equal(resolveLandingLanguageHref(DEFAULT_LANDING_LOCALE, "/fa/"), "/");
  assert.equal(resolveLandingLanguageHref(DEFAULT_LANDING_LOCALE, "/fa/index.html"), "/");
  // GitHub Pages project sites are served below /<repository>/ and must stay below it.
  assert.equal(resolveLandingLanguageHref("fa", "/consttruction-pm-platform/"), "/consttruction-pm-platform/fa/");
  assert.equal(resolveLandingLanguageHref("en", "/consttruction-pm-platform/fa/"), "/consttruction-pm-platform/");
  // A base path that merely contains the locale letters is not a language route.
  assert.equal(resolveLandingLanguageHref("fa", "/cubi-fa-tools/"), "/cubi-fa-tools/fa/");
  assert.equal(resolveLandingLanguageHref("en", "/cubi-fa-tools/fa/"), "/cubi-fa-tools/");
});

test("every public route ships an English document and a Persian twin", () => {
  assert.ok(existsSync(join(root, "public/fa/index.html")), "the Persian landing document is missing");
  for (const route of MARKETING_ROUTES) {
    assert.ok(existsSync(join(root, `public/${route}/index.html`)), `missing /${route}/`);
    assert.ok(existsSync(join(root, `public/fa/${route}/index.html`)), `missing /fa/${route}/`);
  }
});

test("English and Persian documents declare locale, metadata, twin and the shared assistant", () => {
  const documents = [
    ...MARKETING_ROUTES.map((route) => ({
      file: `public/${route}/index.html`,
      route: `/${route}/`,
      lang: "en",
      dir: "ltr",
      twin: `/fa/${route}/`,
      twinLang: "fa",
    })),
    ...MARKETING_ROUTES.map((route) => ({
      file: `public/fa/${route}/index.html`,
      route: `/fa/${route}/`,
      lang: "fa",
      dir: "rtl",
      twin: `/${route}/`,
      twinLang: "en",
    })),
  ];
  for (const document of documents) {
    const html = readDoc(document.file);
    const isPersian = document.lang === "fa";
    assert.match(html, new RegExp(`<html lang="${document.lang}" dir="${document.dir}">`), `${document.file} root element`);
    assert.ok(
      html.includes(`<link rel="canonical" href="__CUBI_BASE_URL__${document.route}"`),
      `${document.file} canonical must point at ${document.route}`,
    );
    assert.ok(
      html.includes(`<link rel="alternate" hreflang="${document.lang}" href="__CUBI_BASE_URL__${document.route}"`),
      `${document.file} must declare its own hreflang`,
    );
    assert.ok(
      html.includes(`<link rel="alternate" hreflang="${document.twinLang}" href="__CUBI_BASE_URL__${document.twin}"`),
      `${document.file} must declare the ${document.twin} twin`,
    );
    assert.ok(html.includes('<link rel="alternate" hreflang="x-default"'), `${document.file} x-default`);
    assert.match(html, /<meta property="og:locale" content="[A-Za-z_]+"/, `${document.file} og:locale`);
    assert.match(html, /<meta property="og:locale:alternate" content="[A-Za-z_]+"/, `${document.file} og:locale:alternate`);
    assert.match(html, /global-assistant-launcher\.bundle\.js/, `${document.file} must mount the shared assistant`);
    if (isPersian) {
      assert.match(html, /[\u0600-\u06FF]{4,}/, `${document.file} must carry Persian copy, not English markup only`);
      assert.doesNotMatch(html, /<h1>[^<]*[A-Za-z]{5,}/, `${document.file} must not fall back to an English headline`);
    } else {
      assert.match(html, /<h1>[^<]*[A-Za-z]{5,}/, `${document.file} English headline`);
    }
  }
});

test("the header language switch reaches the twin from the document directory URL", () => {
  const cases = [
    ...MARKETING_ROUTES.map((route) => ({
      file: `public/${route}/index.html`,
      from: `https://cubi.test/${route}/`,
      expect: `/fa/${route}/`,
      hreflang: "fa",
    })),
    ...MARKETING_ROUTES.map((route) => ({
      file: `public/fa/${route}/index.html`,
      from: `https://cubi.test/fa/${route}/`,
      expect: `/${route}/`,
      hreflang: "en",
    })),
  ];
  for (const item of cases) {
    const html = readDoc(item.file);
    const href = html.match(/<a class="cubi-public-language"[^>]*?href="([^"]+)"/)?.[1];
    assert.ok(href, `${item.file} has no language switch link`);
    assert.ok(html.includes(`<a class="cubi-public-language" hreflang="${item.hreflang}"`), `${item.file} hreflang label`);
    assert.equal(
      new URL(href, item.from).pathname,
      item.expect,
      `${item.file} language link "${href}" resolved from ${item.from}`,
    );
  }
});

test("no public document links to a route that is not shipped", () => {
  const documents = [
    { file: "index.html", from: "https://cubi.test/" },
    { file: "public/fa/index.html", from: "https://cubi.test/fa/" },
    ...MARKETING_ROUTES.map((route) => ({ file: `public/${route}/index.html`, from: `https://cubi.test/${route}/` })),
    ...MARKETING_ROUTES.map((route) => ({ file: `public/fa/${route}/index.html`, from: `https://cubi.test/fa/${route}/` })),
  ];
  for (const document of documents) {
    const html = readDoc(document.file);
    for (const href of internalRouteLinks(html)) {
      const resolved = new URL(href, document.from).pathname;
      if (!resolved.endsWith("/")) continue;
      assert.ok(
        SHIPPED_ROUTES.has(resolved),
        `${document.file} links "${href}" which resolves to the unshipped route ${resolved}`,
      );
    }
  }
});

test("the Persian landing document boots the same JavaScript entries as the English one", () => {
  const faHome = readDoc("public/fa/index.html");
  const enHome = readDoc("index.html");
  for (const script of ["landing-entry.bundle.js", "global-assistant-launcher.bundle.js"]) {
    assert.match(faHome, new RegExp(`src="[^"]*${script}"`), `Persian home must load ${script}`);
    assert.match(enHome, new RegExp(`src="[^"]*${script}"`), `English home must load ${script}`);
  }
  assert.match(faHome, /<html lang="fa" dir="rtl">/);
  assert.match(faHome, /<link rel="canonical" href="__CUBI_BASE_URL__\/fa\/" \/>/);
});
