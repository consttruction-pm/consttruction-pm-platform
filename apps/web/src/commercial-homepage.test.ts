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

test("homepage and public pages share responsive logo proportions and animated navigation", () => {
  assert.match(styles, /\.cubi-exact-brand\s*\{[^}]*flex:0 0 150px[^}]*width:150px[^}]*min-width:150px/);
  assert.ok(styles.includes(".cubi-exact-brand img,.cubi-public-header>a:first-child img{"));
  assert.ok(styles.includes("height:auto;aspect-ratio:1536/664;object-fit:contain"));
  assert.ok(styles.includes(".cubi-footer-brand img{display:block;width:180px;height:auto"));
  assert.ok(styles.includes(".cubi-public-header>a:first-child img{"));
  assert.match(styles, /\.cubi-exact-nav a::after/);
  assert.match(styles, /\.cubi-exact-nav a:hover::after/);
  assert.match(styles, /\.cubi-public-nav a::after/);
  assert.doesNotMatch(styles, /\.cubi-exact-nav a:nth-child\(n\+4\)\{display:none\}/);
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
  // Complete public routes own their URL; homepage-only locales persist without a subpage route.
  assert.match(landing, /function restoreLandingLocale\(\): string \| null/);
  assert.match(landing, /function readSavedLandingLocale\(\): LandingLocale \| null/);
  assert.match(landing, /getLandingHomepageLocales\(\)\.includes\(saved\)/);
  assert.match(landing, /function persistLandingLocale\(\): void/);
  assert.match(landing, /preferredLanguageRoute = restoreLandingLocale\(\);/);
  assert.match(landing, /persistLandingLocale\(\);/);
  assert.match(landing, /container\.dataset\.localeInitialized !== "true"/);
  // Homepage-only locales persist in place; complete subpage locales use their own route.
  assert.match(landing, /window\.location\.replace\(preferredLanguageRoute\)/);
  assert.match(landing, /window\.location\.assign\(targetHome\)/);
});

test("full homepage keeps bilingual control and the six capability areas", () => {
  assert.match(landing, /type LandingLocale = string/);
  assert.match(landing, /cubi-language/);
  assert.match(landing, /<select class="cubi-exact-language" id="cubi-language"/);
  assert.match(landing, /getLandingHomepageLocales\(\)\.map/);
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
  for (const route of ["platform", "solutions", "resources", "contact", "about", "pricing"]) {
    assert.ok(landing.includes("publicPageHref"), "Expected homepage link resolver to " + route);
  }
  assert.match(landing, /"platform\/#project-controls"/);
  assert.match(landing, /"solutions\/#construction-teams"/);
  assert.match(landing, /"resources\/#documentation"/);
  // Pricing links are locale-rooted for every shipped locale, not hard-coded to Persian only.
  assert.match(landing, /const publicLocaleRootHref = locale === "fa"/);
  assert.ok(landing.includes("aboutPageHref"));
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


test("approved primary logo preserves the canonical vector mark or the exact supplied original artwork", () => {
  assert.match(primaryLogo, /CUBI Platform/);
  // The approved original user-provided artwork is intentionally embedded as an
  // image in SVG so it remains visually unchanged. Older vector lockups remain
  // supported, but the test must not require a redraw into SVG paths.
  const preservesOriginalArtwork = /<image\b/.test(primaryLogo) && /href="data:image\/(?:jpeg|png);base64,/.test(primaryLogo);
  const isLegacyVectorLockup =
    /Plan\. Control\. Build Smarter\./.test(primaryLogo) &&
    /<path d="M250 109L156 62/.test(primaryLogo) &&
    /stop-color="#2CC5EB"/.test(primaryLogo) &&
    /viewBox="0 0 1000 330"/.test(primaryLogo);
  assert.ok(preservesOriginalArtwork || isLegacyVectorLockup,
    "logo must preserve either the approved embedded original artwork or the registered vector lockup");
});

test("homepage header, dashboard and footer use the canonical logo asset only", () => {
  assert.equal((landing.match(/\$\{cubiPlatformLogoUrl\(\)\}/g) ?? []).length, 3);
  assert.equal((landing.match(/src="\.\/cubi-platform-logo-primary\.svg"/g) ?? []).length, 0);
  assert.match(landing, /cubi-exact-brand[^>]*>[\s\S]*?cubiPlatformLogoUrl\(\)/);
  assert.match(landing, /cubi-footer-brand[^>]*>[\s\S]*?cubiPlatformLogoUrl\(\)/);
  assert.doesNotMatch(landing, /cubi-footer-social[^>]*>[\s\S]*?<span[^>]*>CUBI<\/span>/);
});

test("homepage messaging covers oil and gas, EPC and the nine requested locales without overstating assistant autonomy", () => {
  for (const locale of ["en", "fa", "de", "fr", "zh", "ja", "ko", "ru", "ar"]) {
    assert.ok(landing.includes("  " + locale + ": {"), "Missing homepage locale copy: " + locale);
  }
  for (const phrase of [
    "oil, gas, petrochemical",
    "pipelines",
    "refineries",
    "EPC",
    "Engineering Intelligence",
    "permission-aware",
    "industriesEyebrow",
    "cubi-exact-industries",
  ]) assert.ok(landing.includes(phrase), "Expected homepage messaging marker: " + phrase);
  assert.ok(landing.includes("request your approval before changing project records"));
  // Do not advertise a locale until its translated homepage AND every public
  // marketing route, metadata and reciprocal language links are shipped.
  assert.ok(landing.includes('Object.freeze(["en", "fa"])'));
});


test("About Us is a first-class bilingual public route with approved founder facts and assistant integration", () => {
  const english = readFileSync(join(root, "public/about/index.html"), "utf8");
  const persian = readFileSync(join(root, "public/fa/about/index.html"), "utf8");
  for (const [html, locale, direction] of [[english, "en", "ltr"], [persian, "fa", "rtl"]]) {
    assert.match(html, new RegExp('<html lang="' + locale + '" dir="' + direction + '">'));
    assert.match(html, /rel="canonical" href="__CUBI_BASE_URL__/);
    assert.match(html, /hreflang="en"/);
    assert.match(html, /hreflang="fa"/);
    assert.match(html, /property="og:locale"/);
    assert.ok(html.includes("global-assistant-launcher.bundle.js"));
    assert.match(html, /Founders and development team|بنیان‌گذاران و تیم توسعه/);
  }
  for (const name of ["Jalal Foroughi Fard", "Javad Foroughi Fard", "Mohammad Foroughi Fard", "Sam Foroughi Fard"]) {
    assert.ok(english.includes(name), "Missing approved founder profile: " + name);
  }
  for (const name of ["جلال فروغی فرد", "جواد فروغی فرد", "محمد فروغی فرد", "سام فروغی فرد"]) {
    assert.ok(persian.includes(name), "Missing approved Persian founder profile: " + name);
  }
  assert.ok(landing.includes('publicPageHref("about")'));
  assert.ok(english.includes('href="../about/" aria-current="page">About Us'));
  assert.ok(persian.includes('href="../about/" aria-current="page">درباره ما'));
});


test("homepage About navigation follows the selected supported language without opening an incomplete locale route tree", () => {
  assert.match(landing, /const aboutLocale = locale === "zh-Hant" \? "zh-Hans" : locale/);
  assert.match(landing, /\["en", "fa", "de", "zh-Hans", "ar", "fr", "ja", "ko"\]\.includes\(aboutLocale\)/);
  assert.match(landing, /const aboutPageHref = \[/);
  assert.equal((landing.match(/href="\$\{aboutPageHref\}"/g) ?? []).length, 2);
  assert.match(landing, /publicRootHref\}about\//);
});

test("homepage security section discloses verified hosting controls and all six approved capability areas", () => {
  for (const marker of [
    'id="security"',
    'aria-labelledby="cubi-security-title"',
    'title: "Secure SSL Connection"',
    'title: "Cloud Firewall Protection"',
    'title: "DDoS Protection"',
    'title: "Automatic Cloud Backup"',
    'title: "Infrastructure Monitoring"',
    'title: "Data Recovery"',
    'status: "ACTIVE — HOST MANAGED"',
    'status: "NOT VERIFIED"',
    "no Render Postgres instance",
    "free web-service filesystems are ephemeral",
    "successful restore drill",
    "getLandingSecurityCopyForLocale",
  ]) assert.ok(landing.includes(marker), "Missing security disclosure requirement: " + marker);
  assert.match(landing, /cubi-security-disclosure/);
  assert.match(landing, /securitySectionCopy\[normalizedLocale\] \?\? \{/);
  assert.match(styles, /\.cubi-security-disclosure/);
  assert.match(styles, /\.cubi-security-status/);
});
