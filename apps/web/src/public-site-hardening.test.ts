import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

/**
 * P5 contract — static SEO, security and performance hardening for the public
 * site. The checks run against the shipped source documents, so they fail
 * before assembly if a page loses its metadata or introduces an unsafe pattern.
 */
const webRoot = process.cwd();
const publicRoot = join(webRoot, "public");

const ENGLISH_ROUTES = [
  "platform/", "features/", "features/scheduling/", "features/project-controls/",
  "features/resources/", "features/cost/", "features/documents/", "features/risks/",
  "features/reporting/", "features/ai-assistant/", "solutions/", "integrations/",
  "pricing/", "resources/", "documentation/", "help/", "faq/", "about/", "security/",
  "payments/", "contact/", "get-started/", "privacy/", "terms/",
];

function allHtml(): string[] {
  const files: string[] = [join(webRoot, "index.html")];
  const walk = (dir: string): void => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const path = join(dir, entry.name);
      if (entry.isDirectory()) walk(path);
      else if (entry.name.endsWith(".html")) files.push(path);
    }
  };
  walk(publicRoot);
  return files;
}

function read(file: string): string {
  return readFileSync(file, "utf8");
}

test("every public document declares language, direction and a viewport", () => {
  for (const file of allHtml()) {
    const html = read(file);
    assert.match(html, /<html lang="[^"]+" dir="(?:ltr|rtl)">/, `${file} lang/dir`);
    assert.match(html, /<meta name="viewport"/, `${file} viewport`);
  }
});

test("English marketing pages carry complete, bounded SEO metadata", () => {
  const pages = [join(webRoot, "index.html"), ...ENGLISH_ROUTES.map((route) => join(publicRoot, route, "index.html"))];
  for (const file of pages) {
    const html = read(file);
    const title = html.match(/<title>(.*?)<\/title>/s)?.[1] ?? "";
    const description = html.match(/<meta name="description" content="([^"]*)"/)?.[1] ?? "";
    assert.ok(title.length >= 20 && title.length <= 70, `${file} title length ${title.length}`);
    assert.ok(description.length >= 50 && description.length <= 170, `${file} description length ${description.length}`);
    assert.ok(html.includes('<meta property="og:title"'), `${file} og:title`);
    if (file !== join(webRoot, "index.html")) {
      const escaped = title.replaceAll("&", "&amp;");
      assert.ok(
        html.includes(`<meta property="og:title" content="${title}">`) ||
          html.includes(`<meta property="og:title" content="${escaped}">`),
        `${file} og:title must match the document title`,
      );
    }
    assert.ok(html.includes('<meta property="og:description"'), `${file} og:description`);
    assert.ok(html.includes('<meta property="og:image"'), `${file} og:image`);
    assert.ok(html.includes('<meta name="twitter:card"'), `${file} twitter:card`);
    assert.ok(html.includes('name="robots" content="index'), `${file} must be indexable`);
    assert.ok(html.includes('<link rel="canonical"'), `${file} canonical`);
    if (file !== join(webRoot, "index.html")) {
      assert.equal((html.match(/<h1[ >]/g) ?? []).length, 1, `${file} must have exactly one h1`);
    }
  }
});

test("the homepage structured data is valid JSON for a software application", () => {
  const html = read(join(webRoot, "index.html"));
  const blocks = [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)];
  assert.equal(blocks.length, 1, "one JSON-LD block");
  const data = JSON.parse(blocks[0][1]);
  assert.ok(
    data["@type"].includes("SoftwareApplication") || data["@type"].includes("WebSite"),
    "structured data must describe the product",
  );
  assert.equal(data.name, "CUBI Platform");
});

test("no public document introduces inline handlers, javascript: links or unsafe new tabs", () => {
  for (const file of allHtml()) {
    const html = read(file);
    assert.equal(/\son[a-z]+\s*=\s*["']/i.exec(html), null, `${file} inline event handler`);
    assert.equal(/href="javascript:/i.exec(html), null, `${file} javascript: link`);
    for (const match of html.matchAll(/<a\b[^>]*target="_blank"[^>]*>/gi)) {
      const tag = match[0];
      assert.match(tag, /rel="[^"]*noopener/i, `${file} target=_blank without noopener`);
    }
  }
});

test("public documents stay inside the performance budget", () => {
  for (const file of allHtml()) {
    const size = statSync(file).size;
    assert.ok(size <= 64 * 1024, `${file} is ${size} bytes`);
    const scripts = (read(file).match(/<script\b/g) ?? []).length;
    assert.ok(scripts <= 4, `${file} loads ${scripts} scripts`);
  }
  const css = statSync(join(publicRoot, "styles.css")).size;
  assert.ok(css <= 600 * 1024, `styles.css is ${css} bytes`);
});

test("every indexable page ships WebPage structured data that matches its own head", () => {
  for (const file of allHtml()) {
    const html = read(file);
    if (/name="robots" content="[^"]*noindex/.test(html)) continue; // private shells stay out of the index
    const blocks = [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)];
    assert.ok(blocks.length >= 1, `${file} has no JSON-LD`);
    const data = JSON.parse(blocks[0][1]);
    if (Array.isArray(data["@type"])) continue; // hand-written homepages keep their SoftwareApplication block
    assert.equal(data["@type"], "WebPage", `${file} must describe a WebPage`);
    const title = html.match(/<title>([^<]+)<\/title>/)?.[1];
    const canonical = html.match(/<link rel="canonical" href="([^"]+)"/)?.[1];
    assert.equal(data.name, title, `${file} JSON-LD name must equal its title`);
    assert.equal(data.url, canonical, `${file} JSON-LD url must equal its canonical`);
    assert.equal(data.inLanguage, html.match(/<html lang="([^"]+)"/)?.[1], `${file} JSON-LD language drifted`);
    assert.ok(data.description, `${file} JSON-LD must carry the page description`);
  }
});

test("the assembled sitemap and robots rules cover every indexable English page", () => {
  const assembled = join(webRoot, "..", "..", "_site");
  if (!existsSync(join(assembled, "sitemap.xml"))) {
    // `npm test` runs before assembly in CI; the assembly step owns the
    // sitemap proof. Here we still prove every English document ships.
    for (const route of ENGLISH_ROUTES) {
      assert.ok(existsSync(join(publicRoot, route, "index.html")), `missing English route ${route}`);
    }
    return;
  }
  const sitemap = read(join(assembled, "sitemap.xml"));
  const robots = read(join(assembled, "robots.txt"));
  // Every approved route is published in all ten locales; the sitemap lists the
  // canonical URL of each translation, so the count follows the inventory
  // instead of a constant that has to be edited whenever a locale ships.
  const expectedUrls = (ENGLISH_ROUTES.length + 1) * 10;
  assert.equal((sitemap.match(/<url>/g) ?? []).length, expectedUrls, "sitemap URL count");
  assert.equal(
    (sitemap.match(/hreflang="x-default"/g) ?? []).length,
    expectedUrls,
    "every URL needs x-default",
  );
  for (const route of ["", ...ENGLISH_ROUTES]) {
    assert.match(sitemap, new RegExp(`<loc>[^<]*/${route}</loc>`), `sitemap is missing /${route}`);
  }
  assert.match(robots, /Sitemap: https?:\/\/[^\s]+\/sitemap\.xml/);
  assert.match(robots, /Disallow: \/login/);
  assert.match(robots, /Disallow: \/environments/);
  assert.doesNotMatch(sitemap, /\/app\/|\/login|\/environments/);
});
