import { cpSync, existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const output = resolve(process.argv[2] || join(root, "../../_site"));
const rawBaseUrl = process.env.SITE_BASE_URL;
if (!rawBaseUrl) throw new Error("SITE_BASE_URL_REQUIRED");
const parsedBaseUrl = new URL(rawBaseUrl);
if (!["https:", "http:"].includes(parsedBaseUrl.protocol)) throw new Error("SITE_BASE_URL_INVALID");
const baseUrl = parsedBaseUrl.href.replace(/\/+$/, "");

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
  .replaceAll("./styles.css", "./styles.css");
homepage = homepage.replace(/<link rel="canonical" href="\.\/"\s*\/>/, '<link rel="canonical" href="' + baseUrl + '/" />');
homepage = homepage.replace(/<meta property="og:url" content="\.\/"\s*\/>/, '<meta property="og:url" content="' + baseUrl + '/" />');
homepage = homepage.replace(/<meta property="og:image" content="\.\/cubi-platform-logo-primary\.svg"\s*\/>/, '<meta property="og:image" content="' + baseUrl + '/cubi-platform-logo-primary.svg" />');
homepage = homepage.replace(/<meta name="twitter:image" content="\.\/cubi-platform-logo-primary\.svg"\s*\/>/, '<meta name="twitter:image" content="' + baseUrl + '/cubi-platform-logo-primary.svg" />');
homepage = homepage.replaceAll('"url": "./"', '"url": "' + baseUrl + '/"');
writeFileSync(join(output, "index.html"), homepage);

let workspace = readFileSync(join(output, "app/index.html"), "utf8")
  .replaceAll("./dist/landing-entry.js", "../dist/web/src/landing-entry.js")
  .replaceAll("./styles.css", "../styles.css")
  .replace(/<title>.*<\/title>/, "<title>CUBI Platform | Workspace</title>")
  .replace(/<meta name="description" content="[^"]*"\s*\/>/, '<meta name="description" content="CUBI Platform workspace." />')
  .replace(/<meta name="robots" content="[^"]*"\s*\/>/, '<meta name="robots" content="noindex,nofollow" />')
  .replace(/\s*<link rel="canonical"[^>]*\/?\s*>/g, "")
  .replace(/\s*<meta property="og:[^"]*"[^>]*\/?\s*>/g, "")
  .replace(/\s*<meta name="twitter:[^"]*"[^>]*\/?\s*>/g, "")
  .replace(/\s*<script type="application\/ld\+json">[\s\S]*?<\/script>/g, "");
writeFileSync(join(output, "app/index.html"), workspace);

// Resolve deployment-specific URL placeholders in all public HTML documents.
for (const file of listHtml(output)) {
  if (file.startsWith(join(output, "app") + "/")) continue;
  const html = readFileSync(file, "utf8").replaceAll("__CUBI_BASE_URL__", baseUrl);
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
  "</urlset>",
  "",
].join("\n"));
writeFileSync(join(output, ".nojekyll"), "");

for (const file of [
  "index.html", "app/index.html", "styles.css", "dist/web/src/landing-entry.js",
  "dist/web/src/landing.js", "cubi-platform-logo-primary.svg", "app/cubi-platform-logo-primary.svg",
  "platform/index.html", "solutions/index.html", "resources/index.html", "contact/index.html",
  "robots.txt", "sitemap.xml", ".nojekyll",
]) assert(existsSync(join(output, file)), "missing " + file);

const expectedTitles = new Map([
  ["platform/index.html", "CUBI Platform | Construction Project Controls"],
  ["solutions/index.html", "CUBI Solutions | Construction Project Delivery"],
  ["resources/index.html", "CUBI Resources | Product Overview and Documentation"],
  ["contact/index.html", "Contact CUBI | Account Access and Product Information"],
]);
for (const [path, title] of expectedTitles) {
  const html = readFileSync(join(output, path), "utf8");
  assert(html.includes("<title>" + title + "</title>"), path + " title mismatch");
  assert(html.includes('<link rel="canonical" href="' + baseUrl + "/" + path.split("/")[0] + '/">'), path + " canonical mismatch");
  assert(html.includes('property="og:url" content="' + baseUrl + "/" + path.split("/")[0] + '/">'), path + " social URL mismatch");
}
const finalHome = readFileSync(join(output, "index.html"), "utf8");
const finalApp = readFileSync(join(output, "app/index.html"), "utf8");
assert(finalHome.includes('<link rel="canonical" href="' + baseUrl + '/" />'), "homepage canonical mismatch");
assert(finalHome.includes('dist/web/src/landing-entry.js'), "homepage script path mismatch");
assert(finalApp.includes('<meta name="robots" content="noindex,nofollow" />'), "workspace must be noindex");
assert(!finalApp.includes('rel="canonical"'), "workspace must not carry marketing canonical");
assert(!finalApp.includes("application/ld+json"), "workspace must not carry marketing structured data");
assert(!readFileSync(join(output, "robots.txt"), "utf8").includes("/app"), "robots must not list workspace");
assert(!readFileSync(join(output, "sitemap.xml"), "utf8").includes("/app"), "sitemap must not list workspace");
assert(!listHtml(output).some((file) => readFileSync(file, "utf8").includes("__CUBI_BASE_URL__")), "unresolved base URL placeholder");
assert(existsSync(join(output, "cubi-platform-logo-primary.svg")), "primary logo missing");
for (const legacy of ["logo.svg", "logo-dark.svg", "cubi-platform-logo-primary-dark.svg"]) {
  assert(!existsSync(join(output, legacy)), "unexpected legacy logo " + legacy);
}
console.log("CUBI Pages artifact validated at " + output + " (" + listHtml(output).length + " HTML files)");
