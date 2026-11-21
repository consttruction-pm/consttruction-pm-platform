import { cpSync, existsSync, mkdirSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const output = resolve(process.argv[2] || join(root, "../../_site"));
const rawBaseUrl = process.env.SITE_BASE_URL;
if (!rawBaseUrl) throw new Error("SITE_BASE_URL_REQUIRED");
const parsedBaseUrl = new URL(rawBaseUrl);
if (!["https:", "http:"].includes(parsedBaseUrl.protocol)) throw new Error("SITE_BASE_URL_INVALID");
const baseUrl = parsedBaseUrl.href.replace(/\/+$/, "");

// GitHub Pages can serve the public site but cannot run the authenticated
// workspace WSGI/API. When a separate read-only demo server is configured,
// the Pages /app route becomes an explicit redirect to that real runtime.
const rawWorkspaceUrl = (process.env.CUBI_WORKSPACE_URL || "").trim();
let workspaceUrl = "";
if (rawWorkspaceUrl) {
  const parsedWorkspaceUrl = new URL(rawWorkspaceUrl);
  if (
    parsedWorkspaceUrl.protocol !== "https:"
    || parsedWorkspaceUrl.username
    || parsedWorkspaceUrl.password
    || parsedWorkspaceUrl.search
    || parsedWorkspaceUrl.hash
    || parsedWorkspaceUrl.pathname.replace(/\/+$/, "") !== "/preview/login"
  ) throw new Error("CUBI_WORKSPACE_URL_INVALID");

  // The public assistant's /app/ entry must preserve the curated visual
  // project through the login form. Without this validated next route, login
  // falls back to the generic API workspace and starts without a project ID.
  parsedWorkspaceUrl.searchParams.set("next", "/app?project=preview-rps-01");
  workspaceUrl = parsedWorkspaceUrl.href.replace(/\/+$/, "");
}

function copyDirectoryContents(source, destination) {
  mkdirSync(destination, { recursive: true });
  for (const name of readdirSync(source)) {
    cpSync(join(source, name), join(destination, name), { recursive: true });
  }
}
function listHtml(directory) {
  const result = [];
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) result.push(...listHtml(path));
    else if (entry.isFile() && entry.name.endsWith(".html")) result.push(path);
  }
  return result;
}
function assert(condition, message) {
  if (!condition) throw new Error("PAGES_ARTIFACT_VALIDATION_FAILED: " + message);
}

// Rebuild from a clean output directory to prevent stale pages from leaking into the artifact.
rmSync(output, { recursive: true, force: true });
mkdirSync(output, { recursive: true });
copyDirectoryContents(join(root, "public"), output);
cpSync(join(root, "dist"), join(output, "dist"), { recursive: true, force: true });
cpSync(join(root, "index.html"), join(output, "index.html"));
cpSync(join(root, "styles.css"), join(output, "styles.css"));
// Workspace documents are served by the session-gated function, but the
// assets they reference (the Workbench stylesheet) must be reachable on the
// same origin. The Enterprise and Workbench bundles are emitted under dist.
cpSync(join(root, "enterprise.html"), join(output, "enterprise.html"));
cpSync(join(root, "ai-workbench.html"), join(output, "ai-workbench.html"));
cpSync(join(root, "ai-workbench.css"), join(output, "ai-workbench.css"));
mkdirSync(join(output, "app"), { recursive: true });
cpSync(join(root, "index.html"), join(output, "app/index.html"));
cpSync(join(root, "public/cubi-platform-logo-primary.svg"), join(output, "app/cubi-platform-logo-primary.svg"));

// Fix the TypeScript build paths for the root and workspace entry points.
let homepage = readFileSync(join(output, "index.html"), "utf8")
  .replaceAll("./dist/landing-entry.bundle.js", "./dist/web/src/landing-entry.bundle.js")
  .replaceAll("./dist/global-assistant-launcher.bundle.js", "./dist/web/src/global-assistant-launcher.bundle.js")
  .replaceAll("./styles.css", "./styles.css");
homepage = homepage.replace(/<link rel="canonical" href="\.\/"\s*\/>/, '<link rel="canonical" href="' + baseUrl + '/" />');
homepage = homepage.replace(/<meta property="og:url" content="\.\/"\s*\/>/, '<meta property="og:url" content="' + baseUrl + '/" />');
homepage = homepage.replace(/<meta property="og:image" content="\.\/cubi-platform-logo-primary\.svg"\s*\/>/, '<meta property="og:image" content="' + baseUrl + '/cubi-platform-logo-primary.svg" />');
homepage = homepage.replace(/<meta name="twitter:image" content="\.\/cubi-platform-logo-primary\.svg"\s*\/>/, '<meta name="twitter:image" content="' + baseUrl + '/cubi-platform-logo-primary.svg" />');
homepage = homepage.replaceAll('"url": "./"', '"url": "' + baseUrl + '/"');
writeFileSync(join(output, "index.html"), homepage);

let workspace = readFileSync(join(output, "app/index.html"), "utf8")
  .replaceAll("./dist/landing-entry.bundle.js", "../dist/web/src/landing-entry.bundle.js")
  .replaceAll("./dist/global-assistant-launcher.bundle.js", "../dist/web/src/global-assistant-launcher.bundle.js")
  .replaceAll("./styles.css", "../styles.css")
  .replace(/<title>.*<\/title>/, "<title>CUBI Platform | Workspace</title>")
  .replace(/<meta name="description" content="[^"]*"\s*\/>/, '<meta name="description" content="CUBI Platform workspace." />')
  .replace(/<meta name="robots" content="[^"]*"\s*\/>/, '<meta name="robots" content="noindex,nofollow" />')
  .replace(/\s*<link rel="canonical"[^>]*\/?\s*>/g, "")
  .replace(/\s*<link rel="alternate" hreflang=[^>]*\/?\s*>/g, "")
  .replace(/\s*<meta property="og:[^"]*"[^>]*\/?\s*>/g, "")
  .replace(/\s*<meta name="twitter:[^"]*"[^>]*\/?\s*>/g, "")
  .replace(/\s*<script type="application\/ld\+json">[\s\S]*?<\/script>/g, "");
if (workspaceUrl) {
  const escapedWorkspaceUrl = workspaceUrl
    .replaceAll("&", "&amp;")
    .replaceAll('"', "&quot;")
    .replaceAll("<", "&lt;");
  writeFileSync(join(output, "app/index.html"), `<!doctype html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<meta http-equiv="refresh" content="0;url=${escapedWorkspaceUrl}">
<title>Opening CUBI Workspace</title>
</head>
<body>
<main>
<h1>Opening CUBI Workspace…</h1>
<p>The workspace runs in a separate read-only demo environment with sample data.</p>
<p lang="fa" dir="rtl">محیط کار در فضای نمایشی جداگانه و با داده‌های آزمایشی باز می‌شود.</p>
<p><a href="${escapedWorkspaceUrl}">Continue to CUBI Workspace</a></p>
</main>
<script>window.location.replace(${JSON.stringify(workspaceUrl)});</script>
</body></html>`);
} else {
  writeFileSync(join(output, "app/index.html"), workspace);
}

// Resolve deployment-specific URL placeholders in all public HTML documents.
// The dist rewrites are prefix-agnostic so documents nested below the site
// root (for example the Persian language routes) load the compiled modules.
for (const file of listHtml(output)) {
  if (file.startsWith(join(output, "app") + "/")) continue;
  const html = readFileSync(file, "utf8")
    .replaceAll("dist/landing-entry.bundle.js", "dist/web/src/landing-entry.bundle.js")
    .replaceAll("dist/global-assistant-launcher.bundle.js", "dist/web/src/global-assistant-launcher.bundle.js")
    .replaceAll("dist/pro-checkout.js", "dist/web/src/pro-checkout.js")
    .replaceAll("__CUBI_BASE_URL__", baseUrl);
  writeFileSync(file, html);
}

writeFileSync(join(output, "robots.txt"), [
  "User-agent: *",
  "Allow: /",
  // Session-gated surfaces are real routes but must never be indexed.
  "Disallow: /environments",
  "Disallow: /login",
  "Sitemap: " + baseUrl + "/sitemap.xml",
  "",
].join("\n"));
writeFileSync(join(output, "sitemap.xml"), [
  '<?xml version="1.0" encoding="UTF-8"?>',
  '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
  "  <url><loc>" + baseUrl + "/</loc></url>",
  "  <url><loc>" + baseUrl + "/platform/</loc></url>",
  "  <url><loc>" + baseUrl + "/solutions/</loc></url>",
  "  <url><loc>" + baseUrl + "/resources/</loc></url>",
  "  <url><loc>" + baseUrl + "/contact/</loc></url>",
  "  <url><loc>" + baseUrl + "/pricing/</loc></url>",
  "</urlset>",
  "",
].join("\n"));
writeFileSync(join(output, ".nojekyll"), "");

// The published site is derived from the same content modules that generate the
// documents, so the sitemap, hreflang graph and validation cannot drift apart.
const { ROUTE_PATHS, HANDWRITTEN_ROUTES, REQUIRED_INDEXABLE_ROUTE_COUNT } = await import(
  new URL("../site/routes.mjs", import.meta.url)
);
const LOCALE_CODES = ["en", "fa", "de", "fr", "ru", "tr", "ja", "ko", "zh", "ar"];
const locales = new Map();
for (const code of LOCALE_CODES) {
  const module = await import(new URL(`../site/locales/${code}.mjs`, import.meta.url));
  if (module.default.code !== code) throw new Error("LOCALE_CODE_MISMATCH: " + code);
  locales.set(code, module.default);
}
const published = new Map();
for (const [code, locale] of locales) {
  const ids = new Set(locale.pages.map((page) => page.id));
  if (code === "en" || code === "fa") for (const id of HANDWRITTEN_ROUTES) ids.add(id);
  published.set(code, ids);
}
const documentFor = (code, routePath) => join(output, locales.get(code).prefix + routePath, "index.html");
const routeUrl = (code, id) => baseUrl + "/" + locales.get(code).prefix + ROUTE_PATHS[id];

const sitemapUrls = [];
for (const id of Object.keys(ROUTE_PATHS)) {
  const languages = LOCALE_CODES.filter((code) => published.get(code).has(id));
  if (!languages.length) continue;
  for (const code of languages) {
    sitemapUrls.push(
      "  <url>",
      "    <loc>" + routeUrl(code, id) + "</loc>",
      ...languages.map((alt) => '    <xhtml:link rel="alternate" hreflang="' + locales.get(alt).htmlLang + '" href="' + routeUrl(alt, id) + '"/>'),
      '    <xhtml:link rel="alternate" hreflang="x-default" href="' + routeUrl("en", id) + '"/>',
      "  </url>",
    );
  }
}
writeFileSync(join(output, "sitemap.xml"), [
  '<?xml version="1.0" encoding="UTF-8"?>',
  '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">',
  ...sitemapUrls,
  "</urlset>",
  "",
].join("\n"));

// Target contract: at least 25 indexable English routes, each with translated
// alternates where a locale publishes the same page.
const englishRoutes = [...published.get("en")];
assert(
  englishRoutes.length >= REQUIRED_INDEXABLE_ROUTE_COUNT,
  "expected at least " + REQUIRED_INDEXABLE_ROUTE_COUNT + " indexable English routes, found " + englishRoutes.length,
);
for (const id of englishRoutes) {
  assert(existsSync(documentFor("en", ROUTE_PATHS[id])), "missing English route " + ROUTE_PATHS[id]);
}
for (const code of LOCALE_CODES) {
  const locale = locales.get(code);
  for (const id of published.get(code)) {
    const file = documentFor(code, ROUTE_PATHS[id]);
    assert(existsSync(file), "missing " + code + " route " + ROUTE_PATHS[id]);
    const html = readFileSync(file, "utf8");
    const label = code + ":" + id;
    assert(html.includes('<html lang="' + locale.htmlLang + '" dir="' + locale.dir + '">'), label + " document language or direction");
    assert(html.includes('<link rel="canonical" href="' + routeUrl(code, id) + '"'), label + " canonical");
    for (const alt of LOCALE_CODES.filter((candidate) => published.get(candidate).has(id))) {
      assert(
        html.includes('<link rel="alternate" hreflang="' + locales.get(alt).htmlLang + '" href="' + routeUrl(alt, id) + '"'),
        label + " must declare the " + alt + " alternate",
      );
    }
    assert(html.includes('hreflang="x-default"'), label + " x-default alternate");
    assert(html.includes('name="robots" content="index'), label + " must be indexable");
    assert(/global-assistant-launcher\.bundle\.js/.test(html), label + " must mount the shared assistant");
    if (locale.dir === "rtl") assert(/[\u0600-\u06FF]{4,}/.test(html), label + " must carry real RTL copy");
  }
}

for (const file of [
  "index.html", "app/index.html", "styles.css", "dist/web/src/landing-entry.bundle.js",
  "dist/web/src/landing.js", "dist/web/src/global-assistant-launcher.bundle.js", "dist/web/src/pro-checkout.js", "cubi-platform-logo-primary.svg", "cubi-assistant-avatar.svg", "app/cubi-platform-logo-primary.svg",
  "platform/index.html", "solutions/index.html", "resources/index.html", "contact/index.html", "about/index.html",
  "fa/index.html", "fa/platform/index.html", "fa/solutions/index.html", "fa/resources/index.html", "fa/contact/index.html", "fa/about/index.html",
  "pricing/index.html", "fa/pricing/index.html",
  "environments/index.html", "capabilities.json",
  "robots.txt", "sitemap.xml", ".nojekyll",
]) assert(existsSync(join(output, file)), "missing " + file);
assert(!existsSync(join(output, "app.html")), "the preview-only app.html must not be shipped");

// The public capability contract is generated from evidence-backed rows. It is
// served as static JSON and must never leak the internal vendor baseline.
const capabilityCatalog = JSON.parse(readFileSync(join(output, "capabilities.json"), "utf8"));
assert(
  capabilityCatalog.contract_version === "cubi-public-capabilities.v1",
  "capability catalog contract version",
);
assert(capabilityCatalog.capabilities.length >= 10, "capability catalog must list every public capability");
assert(
  Number.isInteger(capabilityCatalog.offer?.unit_price_minor) && capabilityCatalog.offer.unit_price_minor > 0,
  "capability catalog must carry the authoritative Pro price",
);
assert(
  capabilityCatalog.offer?.currency === "USD",
  "capability catalog currency must match the checkout constant",
);
for (const capability of capabilityCatalog.capabilities) {
  assert(
    existsSync(join(output, capability.route.replace(/^\/+/, ""), "index.html")),
    "capability route not published: " + capability.route,
  );
  assert(!/oracle|primavera|eppm|\bp6\b/i.test(JSON.stringify(capability)), "capability leaks vendor branding: " + capability.id);
}
assert(
  !/oracle|primavera|eppm|\bp6\b/i.test(JSON.stringify(capabilityCatalog.offer)),
  "capability offer leaks vendor branding",
);

const expectedTitles = new Map([
  ["platform/index.html", "CUBI Platform | Construction Project Controls"],
  ["solutions/index.html", "CUBI Solutions | Construction Project Delivery"],
  ["resources/index.html", "CUBI Resources | Product Overview and Documentation"],
  ["contact/index.html", "Contact CUBI | Account Access and Product Information"],
  ["about/index.html", "About CUBI | Founders and Development Team"],
  ["fa/platform/index.html", "پلتفرم کوبی | کنترل پروژه ساختمانی"],
  ["fa/solutions/index.html", "راهکارهای کوبی | تحویل پروژه ساختمانی"],
  ["fa/resources/index.html", "منابع کوبی | معرفی محصول و راهنما"],
  ["fa/contact/index.html", "تماس با کوبی | دسترسی به حساب و اطلاعات محصول"],
  ["fa/about/index.html", "درباره کوبی | بنیان‌گذاران و تیم توسعه"],
  ["pricing/index.html", "CUBI Pro Monthly | Pricing and Checkout"],
  ["fa/pricing/index.html", "اشتراک ماهانه Pro کوبی | قیمت و پرداخت"],
]);
for (const file of listHtml(output)) {
  // When a separate API-backed demo is configured, /app/ is only a redirect
  // document; it is intentionally not the workspace shell and should not mount
  // the assistant while the browser navigates away.
  if (workspaceUrl && file === join(output, "app/index.html")) continue;
  assert(
    readFileSync(file, "utf8").includes("global-assistant-launcher.bundle.js"),
    "global floating assistant launcher missing from " + file,
  );
}
for (const [path, title] of expectedTitles) {
  const html = readFileSync(join(output, path), "utf8");
  const route = "/" + path.split("/").slice(0, -1).join("/");
  assert(html.includes("<title>" + title + "</title>"), path + " title mismatch");
  assert(html.includes('<link rel="canonical" href="' + baseUrl + route + '/">'), path + " canonical mismatch");
  assert(html.includes('property="og:url" content="' + baseUrl + route + '/">'), path + " social URL mismatch");
}
const finalHome = readFileSync(join(output, "index.html"), "utf8");
const finalApp = readFileSync(join(output, "app/index.html"), "utf8");
assert(finalHome.includes('<link rel="canonical" href="' + baseUrl + '/" />'), "homepage canonical mismatch");
assert(finalHome.includes('dist/web/src/landing-entry.bundle.js'), "homepage script path mismatch");
if (workspaceUrl) {
  assert(finalApp.includes("window.location.replace("), "configured workspace route must redirect to the API-backed demo");
  assert(finalApp.includes(workspaceUrl), "workspace redirect target mismatch");
  assert(
    new URL(workspaceUrl).searchParams.get("next") === "/app?project=preview-rps-01",
    "assistant workspace redirect must preserve the visual preview project through login",
  );
  assert(finalApp.includes('noindex,nofollow'), "workspace redirect must not be indexed");
} else {
  assert(finalApp.includes('<meta name="robots" content="noindex,nofollow" />'), "workspace must be noindex");
  assert(!finalApp.includes('rel="canonical"'), "workspace must not carry marketing canonical");
  assert(!finalApp.includes("application/ld+json"), "workspace must not carry marketing structured data");
}
assert(!readFileSync(join(output, "robots.txt"), "utf8").includes("/app"), "robots must not list workspace");
assert(!readFileSync(join(output, "sitemap.xml"), "utf8").includes("/environments"), "sitemap must not list the environment selector");
assert(readFileSync(join(output, "robots.txt"), "utf8").includes("Disallow: /environments"), "environment selector must be disallowed");
assert(readFileSync(join(output, "environments/index.html"), "utf8").includes('name="robots" content="noindex'), "environment selector must be noindex");
assert(!readFileSync(join(output, "sitemap.xml"), "utf8").includes("/app"), "sitemap must not list workspace");
assert(!listHtml(output).some((file) => readFileSync(file, "utf8").includes("__CUBI_BASE_URL__")), "unresolved base URL placeholder");
assert(existsSync(join(output, "cubi-platform-logo-primary.svg")), "primary logo missing");
assert(existsSync(join(output, "cubi-assistant-avatar.svg")), "assistant avatar missing");
for (const legacy of ["logo.svg", "logo-dark.svg", "cubi-platform-logo-primary-dark.svg"]) {
  assert(!existsSync(join(output, legacy)), "unexpected legacy logo " + legacy);
}

// Link integrity: every internal href/src in a shipped document must resolve to
// a real artifact file, so no empty link or dead route can reach production.
function toArtifactPath(rawTarget) {
  const withoutFragment = rawTarget.split("#")[0].split("?")[0];
  if (/^[a-z][a-z0-9+.-]*:/i.test(withoutFragment)) {
    if (!withoutFragment.startsWith(baseUrl + "/")) return null;
    return withoutFragment.slice(baseUrl.length);
  }
  return withoutFragment;
}

function resolveArtifactTarget(file, rawTarget) {
  const route = toArtifactPath(rawTarget);
  if (route === null) return null;
  const decoded = decodeURIComponent(route).replace(/^\/+/, "");
  const absolute = route.startsWith("/") || /^[a-z][a-z0-9+.-]*:/i.test(rawTarget.split("#")[0])
    ? join(output, decoded)
    : resolve(dirname(file), decoded.split("#")[0].split("?")[0]);
  if (existsSync(absolute) && statSync(absolute).isDirectory()) return join(absolute, "index.html");
  return absolute;
}

const internalLinks = [];
for (const file of listHtml(output)) {
  const html = readFileSync(file, "utf8");
  for (const match of html.matchAll(/(?:href|src)="([^"]+)"/g)) {
    const target = match[1];
    if (target.startsWith("mailto:") || target.startsWith("tel:") || target.startsWith("data:")) continue;
    internalLinks.push({ file, target });
  }
}
for (const { file, target } of internalLinks) {
  const resolved = resolveArtifactTarget(file, target);
  if (resolved === null) continue;
  const relativeTarget = relative(output, resolved).split(sep).join("/");
  const documentName = relative(output, file).split(sep).join("/");
  assert(
    !relativeTarget.startsWith("..") && existsSync(resolved),
    "broken link in " + documentName + ": " + target + " does not resolve to a shipped file",
  );
}
console.log("CUBI Pages artifact validated at " + output + " (" + listHtml(output).length + " HTML files)");
