import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

const root = process.cwd();
const landing = readFileSync(join(root, "src/landing.ts"), "utf8");
const index = readFileSync(join(root, "index.html"), "utf8");
const styles = readFileSync(join(root, "styles.css"), "utf8");
const primaryLogo = readFileSync(join(root, "public/cubi-platform-logo-primary.svg"), "utf8");

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
  ]) assert.match(landing + styles, pattern);
  assert.doesNotMatch(landing + styles + index, /cubi-platform-logo-primary-dark\.svg|logo-dark\.svg/);
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


test("landing language preference is restored and persisted safely", () => {
  assert.match(landing, /LANDING_LOCALE_STORAGE_KEY = "cubi:landing-locale"/);
  assert.match(landing, /function restoreLandingLocale\(\): void/);
  assert.match(landing, /getAvailableWorkspaceLocales\(\)\.includes\(saved\)/);
  assert.match(landing, /function persistLandingLocale\(\): void/);
  assert.match(landing, /restoreLandingLocale\(\);/);
  assert.match(landing, /persistLandingLocale\(\);/);
  assert.match(landing, /container\.dataset\.localeInitialized !== "true"/);
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
});

test("standalone public pages have unique metadata and expected content", () => {
  const pages = [
    ["public/platform/index.html", "CUBI Platform | Construction Project Controls", "scheduling"],
    ["public/solutions/index.html", "CUBI Solutions | Construction Project Delivery", "construction-teams"],
    ["public/resources/index.html", "CUBI Resources | Product Overview and Documentation", "documentation"],
    ["public/contact/index.html", "Contact CUBI | Account Access and Product Information", "Direct contact channel"],
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

test("public homepage exposes an accessible, interactive assistant entry point in Persian and English", () => {
  assert.match(landing, /id="cubi-assistant-launcher"/);
  assert.match(landing, /id="cubi-assistant-popover"/);
  assert.match(landing, /aria-expanded="false"/);
  assert.match(landing, /aria-controls="cubi-assistant-popover"/);
  assert.match(landing, /setAssistantPopoverOpen\(assistantLauncher\?\.getAttribute\("aria-expanded"\) !== "true"\)/);
  assert.match(landing, /assistantTitle: "CUBI AI Assistant"/);
  assert.match(landing, /assistantTitle: "دستیار هوشمند کوبی"/);
  assert.match(landing, /assistantWorkspaceAction: "Open project workspace/);
  assert.match(landing, /assistantWorkspaceAction: "ورود به فضای کاری پروژه/);
  assert.match(landing, /href="\.\/app\/">\$\{t\.assistantWorkspaceAction\}/);
  assert.match(styles, /\.cubi-assistant-launcher \{[^}]*position:\s*fixed/);
  assert.match(styles, /\.cubi-assistant-popover\[hidden\] \{[^}]*display:\s*none !important/);
});

test("approved primary logo uses the C-shaped cube mark, teal center cube and canonical wordmark", () => {
  assert.match(primaryLogo, /CUBI Platform/);
  assert.match(primaryLogo, /PLAN\. CONTROL\. BUILD SMARTER\./);
  assert.match(primaryLogo, /<path d="M84 3 158 45/);
  assert.match(primaryLogo, /fill="url\(#cubeTop\)"/);
  assert.match(primaryLogo, /viewBox="0 0 640 180"/);
});

test("homepage header, dashboard and footer use the canonical logo asset only", () => {
  assert.equal((landing.match(/src="\.\/cubi-platform-logo-primary\.svg"/g) ?? []).length, 3);
  assert.match(landing, /cubi-exact-brand[^>]*>[\s\S]*?cubi-platform-logo-primary\.svg/);
  assert.match(landing, /cubi-footer-brand[^>]*>[\s\S]*?cubi-platform-logo-primary\.svg/);
  assert.doesNotMatch(landing, /cubi-footer-social[^>]*>[\s\S]*?<span[^>]*>CUBI<\/span>/);
});
