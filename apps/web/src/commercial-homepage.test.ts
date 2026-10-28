import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

const root = process.cwd();
const landing = readFileSync(join(root, "src/landing.ts"), "utf8");
const assistant = readFileSync(join(root, "src/global-assistant-launcher.ts"), "utf8");
const index = readFileSync(join(root, "index.html"), "utf8");
const styles = readFileSync(join(root, "styles.css"), "utf8");
const primaryLogo = readFileSync(join(root, "public/cubi-platform-logo-primary.svg"), "utf8");
const brandAssets = readFileSync(join(root, "src/cubi-brand-assets.ts"), "utf8");

test("CUBI homepage follows the registered full commercial structure", () => {
  for (const pattern of [
    /cubi-reference-home/,
    /cubi-exact-home/,
    /cubi-exact-header/,
    /cubi-exact-hero/,
    /cubi-exact-dashboard/,
    /cubi-exact-features/,
    /cubi-exact-tech/,
    /cubi-exact-cta/,
    /cubi-exact-footer/,
    /cubi-platform-logo-primary\.svg/,
    /cubi-hero-field\.svg/,
  ]) assert.match(landing + styles + brandAssets, pattern);
  // The homepage must resolve the brand mark through the shared asset helper so
  // nested routes and GitHub Pages base paths still reach the public root.
  assert.match(landing, /import \{[^}]*cubiPlatformLogoUrl[^}]*\} from "\.\/cubi-brand-assets\.js"/);
  assert.match(brandAssets, /export function cubiPlatformLogoUrl\(\s*moduleUrl: string = import\.meta\.url/);
  assert.match(brandAssets, /new URL\("\.\.\/\.\.\/\.\.\/cubi-platform-logo-primary\.svg", moduleUrl\)/);
  assert.doesNotMatch(landing + styles + index, /cubi-platform-logo-primary-dark\.svg|logo-dark\.svg/);
});

test("homepage header and footer logos use bounded, aspect-ratio-safe sizing", () => {
  assert.match(styles, /\.cubi-exact-brand\s*\{[^}]*flex:0 0 150px[^}]*width:150px[^}]*min-width:150px/);
  assert.match(styles, /\.cubi-exact-brand img\s*\{[^}]*width:150px[^}]*height:50px[^}]*object-fit:contain/);
  assert.match(styles, /\.cubi-footer-brand img\s*\{[^}]*width:180px[^}]*height:59px[^}]*background:transparent[^}]*padding:0/);
  assert.match(styles, /@media \(max-width:820px\)[\s\S]*?\.cubi-exact-brand img\s*\{[^}]*width:132px[^}]*height:44px/);
  assert.match(styles, /@media \(max-width:520px\)[\s\S]*?\.cubi-exact-brand img\s*\{[^}]*width:120px[^}]*height:40px/);
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
  for (const pattern of [/Oracle/i, /Primavera/i, />\\s*P6\\s*</i]) {
    assert.doesNotMatch(landing, pattern);
    assert.doesNotMatch(index, pattern);
  }
});


test("the landing language follows its route and persists the accepted preference", () => {
  const preferences = readFileSync(join(root, "src/workspace-preferences.ts"), "utf8");
  assert.match(preferences, /LANDING_LOCALE_STORAGE_KEY = "cubi:landing-locale"/);
  // One storage key, one owner: the landing page must consume the shared key
  // instead of declaring a second constant that could silently diverge.
  assert.match(landing, /import \{ LANDING_LOCALE_STORAGE_KEY \} from "\.\/workspace-preferences\.js"/);
  assert.doesNotMatch(landing, /const LANDING_LOCALE_STORAGE_KEY/);
  // A language route, not storage, owns the document language and its metadata.
  assert.match(landing, /function restoreLandingLocale\(\): string \| null/);
  assert.match(landing, /function readSavedLandingLocale\(\): LandingLocale \| null/);
  assert.match(landing, /getLandingLanguageRoutes\(\)\.includes\(saved\)/);
  assert.match(landing, /function persistLandingLocale\(\): void/);
  assert.match(landing, /preferredLanguageRoute = restoreLandingLocale\(\);/);
  assert.match(landing, /persistLandingLocale\(\);/);
  assert.match(landing, /container\.dataset\.localeInitialized !== "true"/);
  // The stored preference is honoured by moving to the document that describes it.
  assert.match(landing, /window\.location\.replace\(preferredLanguageRoute\)/);
  assert.match(landing, /window\.location\.assign\(languageHref\)/);
});

test("full homepage keeps bilingual control and the six capability areas", () => {
  assert.match(landing, /type LandingLocale = string/);
  assert.match(landing, /cubi-language/);
  assert.match(landing, /getAvailableWorkspaceLocales\(\)/);
  assert.match(landing, /translateWorkspaceText/);
  for (const pattern of [
    /Project Controls|کنترل پروژه/,
    /AI Assistant|دستیار هوشمند/,
    /Resources & Cost|منابع و هزینه/,
    /Documents & Contracts|اسناد و قراردادها/,
    /Team Collaboration|همکاری تیمی/,
    /Cloud & Scalability|ابر و توسعه‌پذیری/,
  ]) assert.match(landing, pattern);
});

test("Persian homepage mirrors dashboard and technology layout in RTL mode", () => {
  assert.match(styles, /\[dir="rtl"\] \.cubi-exact-dashboard\s*\{[^}]*margin-right:\s*-1\.5rem/);
  assert.match(styles, /\[dir="rtl"\] \.cubi-tech-node\.n1,[\s\S]*?right:\s*0/);
  assert.match(styles, /\[dir="rtl"\] \.cubi-footer-brand img\s*\{[^}]*object-position:\s*right center/);
});

test("homepage navigation and footer connect to real public routes", () => {
  for (const route of ["./platform/", "./solutions/", "./resources/", "./contact/"]) {
    assert.ok(landing.includes(route), "Expected homepage link to " + route);
  }
  assert.match(landing, /\.\/platform\/#project-controls/);
  assert.match(landing, /\.\/solutions\/#construction-teams/);
  assert.match(landing, /\.\/resources\/#documentation/);
  assert.match(landing, /pricingHref = locale === "fa"/);
  assert.match(landing, /href="\$\{pricingHref\}"/);
});

test("standalone public pages have unique metadata and expected content", () => {
  const pages = [
    ["public/platform/index.html", "CUBI Platform | Construction Project Controls", "scheduling"],
    ["public/solutions/index.html", "CUBI Solutions | Construction Project Delivery", "construction-teams"],
    ["public/resources/index.html", "CUBI Resources | Product Overview and Documentation", "documentation"],
    ["public/contact/index.html", "Contact CUBI | Account Access and Product Information", "Direct contact channel"],
    ["public/pricing/index.html", "CUBI Pro Monthly | Pricing and Checkout", "month-quantity"],
    ["public/fa/pricing/index.html", "اشتراک ماهانه Pro کوبی | قیمت و پرداخت", "month-quantity"],
  ];
  for (const [path, title, marker] of pages) {
    const html = readFileSync(join(root, path), "utf8");
    assert.ok(html.includes("<title>" + title + "</title>"), path + " should have a unique title");
    assert.ok(html.includes('name="description"'), path + " should have a description");
    assert.ok(html.includes('rel="canonical" href="__CUBI_BASE_URL__/'), path + " should have a canonical URL placeholder for deployment");
    assert.ok(html.includes('property="og:url" content="__CUBI_BASE_URL__/'), path + " should have an absolute social URL after deployment");
    assert.ok(html.includes(marker), path + " should have its expected content");
  }
});

test("assistant avatar is connected to every existing Web assistant surface while the product logo stays canonical", () => {
  const chat = readFileSync(join(root, "src/ai-assistant-chat.ts"), "utf8");
  const actions = readFileSync(join(root, "src/ai-action-panel.ts"), "utf8");
  const brandAssets = readFileSync(join(root, "src/cubi-brand-assets.ts"), "utf8");
  const desktopAssets = readFileSync(join(root, "../desktop/src/cubi-brand-assets.ts"), "utf8");
  const mobileAssets = readFileSync(join(root, "../mobile/src/cubi-brand-assets.ts"), "utf8");
  const avatar = readFileSync(join(root, "public/cubi-assistant-avatar.svg"), "utf8");

  assert.match(landing, /assistantAvatar: true/);
  assert.match(landing, /cubiAssistantAvatarUrl\(\)/);
  assert.match(landing, /cubi-feature-icon-assistant/);
  assert.match(chat, /avatar\.src = cubiAssistantAvatarUrl\(\)/);
  assert.match(chat, /messageAvatar\.src = cubiAssistantAvatarUrl\(\)/);
  assert.match(actions, /avatar\.src = cubiAssistantAvatarUrl\(\)/);
  assert.match(brandAssets, /new URL\("\.\.\/\.\.\/\.\.\/cubi-assistant-avatar\.svg", moduleUrl\)/);
  assert.match(desktopAssets, /CUBI_ASSISTANT_AVATAR_ASSET/);
  assert.match(mobileAssets, /CUBI_ASSISTANT_AVATAR_ASSET/);
  assert.match(avatar, /<title id="title">CUBI AI Project Assistant<\/title>/);
  assert.match(index, /<link rel="icon" href="\.\/cubi-platform-logo-primary\.svg" type="image\/svg\+xml"\s*\/>/);
});

test("public homepage exposes the shared accessible floating assistant in Persian and English", () => {
  assert.match(landing, /cubi-reference-home/);
  assert.match(assistant, /launcher\.id = "cubi-assistant-launcher"/);
  assert.match(assistant, /popover\.id = "cubi-assistant-popover"/);
  assert.match(assistant, /setAttribute\("aria-expanded", "false"\)/);
  assert.match(assistant, /setAttribute\("aria-controls", popover\.id\)/);
  assert.match(assistant, /setPopoverOpen\(!isOpen\)/);
  assert.match(assistant, /CUBI AI Assistant/);
  assert.match(assistant, /دستیار هوشمند کوبی/);
  assert.match(assistant, /Open project workspace →/);
  assert.match(assistant, /ورود به فضای کاری پروژه ←/);
  assert.match(assistant, /new URL\("app\/", siteRoot\)/);
  assert.match(styles, /\.cubi-assistant-launcher \{[^}]*position:\s*fixed/);
  assert.match(styles, /\.cubi-assistant-popover\[hidden\] \{[^}]*display:\s*none !important/);
});

test("one assistant entry owns keyboard dismissal, artwork failure and viewport safety", () => {
  // A single mounted instance: no duplicate avatars or independent panels.
  assert.match(assistant, /if \(document\.getElementById\(ROOT_ID\)\) return;/);
  assert.match(assistant, /document\.body\.append\(root\)/);
  // Escape works wherever the focus is, and an outside pointer dismisses the panel.
  assert.match(assistant, /event\.key === "Escape"/);
  assert.match(assistant, /addEventListener\("pointerdown"/);
  assert.match(assistant, /root\.contains\(event\.target as Node \| null\)/);
  // Focus is taken into the dialog and returned to the launcher it came from.
  assert.match(assistant, /closeButton\.focus\(\)/);
  assert.match(assistant, /launcher\.focus\(\)/);
  assert.match(assistant, /setAttribute\("aria-haspopup", "dialog"\)/);
  // Broken artwork must not remove the labelled entry point.
  assert.match(assistant, /addEventListener\("error"/);
  assert.match(assistant, /dataset\.avatarFailed = "true"/);
  assert.match(assistant, /cubi-assistant-avatar-fallback/);
  assert.match(styles, /\.cubi-assistant-avatar-slot\[data-avatar-failed="true"\] img/);
  assert.match(styles, /env\(safe-area-inset-bottom/);
  // Narrow viewports get an icon-only circle so the entry cannot cover controls.
  assert.match(assistant, /COMPACT_MEDIA_QUERY = "\(max-width: 520px\)"/);
  assert.match(assistant, /dataset\.compact/);
  assert.match(styles, /@media \(max-width: 520px\)[\s\S]*\.cubi-assistant-launcher-button/);
  // The document language governs the assistant; a stored preference may not mix
  // two languages inside one page.
  assert.doesNotMatch(assistant, /cubi:landing-locale/);
  assert.match(assistant, /getLanguageRouteLocale/);
});


test("approved primary logo uses the current canonical cube mark, teal center structure and wordmark", () => {
  assert.match(primaryLogo, /CUBI Platform/);
  assert.match(primaryLogo, /Plan\. Control\. Build Smarter\./);
  assert.match(primaryLogo, /<path d="M250 109L156 62/);
  assert.match(primaryLogo, /stop-color="#2CC5EB"/);
  assert.match(primaryLogo, /viewBox="0 0 1000 330"/);
});

test("homepage header, dashboard and footer use the canonical logo asset only", () => {
  assert.equal((landing.match(/\$\{cubiPlatformLogoUrl\(\)\}/g) ?? []).length, 3);
  assert.equal((landing.match(/src="\.\/cubi-platform-logo-primary\.svg"/g) ?? []).length, 0);
  assert.match(landing, /cubi-exact-brand[^>]*>[\s\S]*?cubiPlatformLogoUrl\(\)/);
  assert.match(landing, /cubi-footer-brand[^>]*>[\s\S]*?cubiPlatformLogoUrl\(\)/);
  assert.doesNotMatch(landing, /cubi-footer-social[^>]*>[\s\S]*?<span[^>]*>CUBI<\/span>/);
});
