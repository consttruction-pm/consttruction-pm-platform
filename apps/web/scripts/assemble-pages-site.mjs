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

// GitHub Pages is static and cannot run the authenticated WSGI/API. Its /app
// route therefore serves a dedicated visual-review shell with fixed demo data.

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
mkdirSync(join(output, "app"), { recursive: true });
cpSync(join(root, "index.html"), join(output, "app/index.html"));
cpSync(join(root, "public/cubi-platform-logo-primary.svg"), join(output, "app/cubi-platform-logo-primary.svg"));

// Fix the TypeScript build paths for the root and workspace entry points.
let homepage = readFileSync(join(output, "index.html"), "utf8")
  .replaceAll("./dist/landing-entry.js", "./dist/web/src/landing-entry.js")
  .replaceAll("./dist/global-assistant-launcher.js", "./dist/web/src/global-assistant-launcher.js")
  .replaceAll("./styles.css", "./styles.css");
homepage = homepage.replace(/<link rel="canonical" href="\.\/"\s*\/>/, '<link rel="canonical" href="' + baseUrl + '/" />');
homepage = homepage.replace(/<meta property="og:url" content="\.\/"\s*\/>/, '<meta property="og:url" content="' + baseUrl + '/" />');
homepage = homepage.replace(/<meta property="og:image" content="\.\/cubi-platform-logo-primary\.svg"\s*\/>/, '<meta property="og:image" content="' + baseUrl + '/cubi-platform-logo-primary.svg" />');
homepage = homepage.replace(/<meta name="twitter:image" content="\.\/cubi-platform-logo-primary\.svg"\s*\/>/, '<meta name="twitter:image" content="' + baseUrl + '/cubi-platform-logo-primary.svg" />');
homepage = homepage.replaceAll('"url": "./"', '"url": "' + baseUrl + '/"');
writeFileSync(join(output, "index.html"), homepage);

let workspace = readFileSync(join(output, "app/index.html"), "utf8")
  .replaceAll("./dist/landing-entry.js", "../dist/web/src/landing-entry.js")
  .replaceAll("./dist/global-assistant-launcher.js", "../dist/web/src/global-assistant-launcher.js")
  .replaceAll("./styles.css", "../styles.css")
  .replace(/<title>.*<\/title>/, "<title>CUBI Platform | Workspace</title>")
  .replace(/<meta name="description" content="[^"]*"\s*\/>/, '<meta name="description" content="CUBI Platform workspace." />')
  .replace(/<meta name="robots" content="[^"]*"\s*\/>/, '<meta name="robots" content="noindex,nofollow" />')
  .replace(/\s*<link rel="canonical"[^>]*\/?\s*>/g, "")
  .replace(/\s*<link rel="alternate" hreflang=[^>]*\/?\s*>/g, "")
  .replace(/\s*<meta property="og:[^"]*"[^>]*\/?\s*>/g, "")
  .replace(/\s*<meta name="twitter:[^"]*"[^>]*\/?\s*>/g, "")
  .replace(/\s*<script type="application\/ld\+json">[\s\S]*?<\/script>/g, "");
workspace = workspace.replaceAll(
  "../dist/web/src/landing-entry.js",
  "../dist/web/src/visual-preview-entry.js",
);
writeFileSync(join(output, "app/index.html"), workspace);

// Resolve deployment-specific URL placeholders in all public HTML documents.
// The dist rewrites are prefix-agnostic so documents nested below the site
// root (for example the Persian language routes) load the compiled modules.
for (const file of listHtml(output)) {
  if (file.startsWith(join(output, "app") + "/")) continue;
  const html = readFileSync(file, "utf8")
    .replaceAll("dist/landing-entry.js", "dist/web/src/landing-entry.js")
    .replaceAll("dist/global-assistant-launcher.js", "dist/web/src/global-assistant-launcher.js")
    .replaceAll("dist/pro-checkout.js", "dist/web/src/pro-checkout.js")
    .replaceAll("__CUBI_BASE_URL__", baseUrl);
  writeFileSync(file, html);
}

writeFileSync(join(output, "robots.txt"), [
  "User-agent: *",
  "Allow: /",
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

// Every marketing route exists in both baseline languages, with hreflang pairs.
const languageRoutes = [
  { en: "/", fa: "/fa/" },
  { en: "/platform/", fa: "/fa/platform/" },
  { en: "/solutions/", fa: "/fa/solutions/" },
  { en: "/resources/", fa: "/fa/resources/" },
  { en: "/contact/", fa: "/fa/contact/" },
  { en: "/pricing/", fa: "/fa/pricing/" },
];
const documentForRoute = (route) => join(output, route === "/" ? "index.html" : route.slice(1) + "index.html");

// Language-aware sitemap: every URL declares both language alternates.
const sitemapUrls = [];
for (const { en, fa } of languageRoutes) {
  sitemapUrls.push(
    "  <url>",
    "    <loc>" + baseUrl + en + "</loc>",
    '    <xhtml:link rel="alternate" hreflang="en" href="' + baseUrl + en + '"/>',
    '    <xhtml:link rel="alternate" hreflang="fa" href="' + baseUrl + fa + '"/>',
    '    <xhtml:link rel="alternate" hreflang="x-default" href="' + baseUrl + en + '"/>',
    "  </url>",
    "  <url>",
    "    <loc>" + baseUrl + fa + "</loc>",
    '    <xhtml:link rel="alternate" hreflang="en" href="' + baseUrl + en + '"/>',
    '    <xhtml:link rel="alternate" hreflang="fa" href="' + baseUrl + fa + '"/>',
    "  </url>",
  );
}
writeFileSync(join(output, "sitemap.xml"), [
  '<?xml version="1.0" encoding="UTF-8"?>',
  '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">',
  ...sitemapUrls,
  "</urlset>",
  "",
].join("\n"));

for (const file of [
  "index.html", "app/index.html", "styles.css", "dist/web/src/landing-entry.js",
  "dist/web/src/landing.js", "dist/web/src/global-assistant-launcher.js", "dist/web/src/pro-checkout.js", "cubi-platform-logo-primary.svg", "cubi-assistant-avatar.svg", "app/cubi-platform-logo-primary.svg",
  "platform/index.html", "solutions/index.html", "resources/index.html", "contact/index.html",
  "fa/index.html", "fa/platform/index.html", "fa/solutions/index.html", "fa/resources/index.html", "fa/contact/index.html",
  "pricing/index.html", "fa/pricing/index.html",
  "robots.txt", "sitemap.xml", ".nojekyll",
]) assert(existsSync(join(output, file)), "missing " + file);
assert(!existsSync(join(output, "app.html")), "the preview-only app.html must not be shipped");

const expectedTitles = new Map([
  ["platform/index.html", "CUBI Platform | Construction Project Controls"],
  ["solutions/index.html", "CUBI Solutions | Construction Project Delivery"],
  ["resources/index.html", "CUBI Resources | Product Overview and Documentation"],
  ["contact/index.html", "Contact CUBI | Account Access and Product Information"],
  ["fa/platform/index.html", "پلتفرم کوبی | کنترل پروژه ساختمانی"],
  ["fa/solutions/index.html", "راهکارهای کوبی | تحویل پروژه ساختمانی"],
  ["fa/resources/index.html", "منابع کوبی | معرفی محصول و راهنما"],
  ["fa/contact/index.html", "تماس با کوبی | دسترسی به حساب و اطلاعات محصول"],
  ["pricing/index.html", "CUBI Pro Monthly | Pricing and Checkout"],
  ["fa/pricing/index.html", "اشتراک ماهانه Pro کوبی | قیمت و پرداخت"],
]);
for (const file of listHtml(output)) {
  assert(
    readFileSync(file, "utf8").includes("global-assistant-launcher.js"),
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
for (const { en, fa } of languageRoutes) {
  const enDocument = readFileSync(documentForRoute(en), "utf8");
  const faDocument = readFileSync(documentForRoute(fa), "utf8");
  assert(enDocument.includes('<link rel="alternate" hreflang="fa" href="' + baseUrl + fa + '"'), en + " must offer " + fa);
  assert(faDocument.includes('<link rel="alternate" hreflang="en" href="' + baseUrl + en + '"'), fa + " must offer " + en);
  assert(faDocument.includes('lang="fa"') && faDocument.includes('dir="rtl"'), fa + " must be a Persian RTL document");
  assert(/[\u0600-\u06FF]/.test(faDocument), fa + " must carry real Persian content");
  assert(faDocument.includes("global-assistant-launcher.js"), fa + " must mount the shared assistant entry");
}
const finalHome = readFileSync(join(output, "index.html"), "utf8");
const finalApp = readFileSync(join(output, "app/index.html"), "utf8");
assert(finalHome.includes('<link rel="canonical" href="' + baseUrl + '/" />'), "homepage canonical mismatch");
assert(finalHome.includes('dist/web/src/landing-entry.js'), "homepage script path mismatch");
assert(finalApp.includes('<meta name="robots" content="noindex,nofollow" />'), "workspace must be noindex");
assert(!finalApp.includes('rel="canonical"'), "workspace must not carry marketing canonical");
assert(!finalApp.includes("application/ld+json"), "workspace must not carry marketing structured data");
assert(finalApp.includes("../dist/web/src/visual-preview-entry.js"), "Pages /app must mount the visual-only workspace entry");
assert(!finalApp.includes("landing-entry.js"), "Pages /app must not mount a second/legacy workspace shell");
assert(!readFileSync(join(output, "robots.txt"), "utf8").includes("/app"), "robots must not list workspace");
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
