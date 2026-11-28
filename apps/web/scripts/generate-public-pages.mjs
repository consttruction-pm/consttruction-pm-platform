// Generates the localized public website from the content modules in apps/web/site.
//
// Two kinds of documents coexist:
//   * hand-written long-form pages (home, platform, solutions, pricing, resources,
//     contact, about, help) in English and Persian. They are never regenerated;
//     this script only refreshes their hreflang alternates and language switcher.
//   * generated pages for every other route and locale, rendered from
//     apps/web/site/locales/<code>.mjs.
//
// Output is written into apps/web/public so the static preview server and the
// Pages assembly step serve exactly the same documents.
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, posix, relative, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import { HANDWRITTEN_ROUTES, NAV_KEYS, ROUTE_PATHS } from "../site/routes.mjs";

const webRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const publicRoot = join(webRoot, "public");

const LOCALE_CODES = ["en", "fa", "de", "fr", "ru", "tr", "ja", "ko", "zh", "ar"];
const OG_LOCALE = {
  en: "en_US", fa: "fa_IR", de: "de_DE", fr: "fr_FR", ru: "ru_RU",
  tr: "tr_TR", ja: "ja_JP", ko: "ko_KR", zh: "zh_CN", ar: "ar_SA",
};
const LANGUAGE_MENU_LABEL = {
  en: "All languages", fa: "همه زبان‌ها", de: "Sprachen", fr: "Langues", ru: "Языки",
  tr: "Diller", ja: "言語", ko: "언어", zh: "语言", ar: "اللغات",
};
const NAV_LABEL = {
  en: "Primary navigation", fa: "ناوبری اصلی", de: "Hauptnavigation", fr: "Navigation principale",
  ru: "Основная навигация", tr: "Ana gezinme", ja: "メインナビゲーション", ko: "주요 탐색",
  zh: "主导航", ar: "التنقل الرئيسي",
};
const CTA_FALLBACK = {
  en: { title: "See CUBI on your own project", text: "Open the workspace and continue from a connected project view.", label: "Open CUBI workspace" },
  fa: { title: "کوبی را روی پروژه خودتان ببینید", text: "فضای کاری را باز کنید و از یک نمای یکپارچه پروژه ادامه دهید.", label: "ورود به فضای کاری کوبی" },
  de: { title: "CUBI in Ihrem eigenen Projekt erleben", text: "Öffnen Sie den Arbeitsbereich und starten Sie aus einer verbundenen Projektansicht.", label: "CUBI-Arbeitsbereich öffnen" },
  fr: { title: "Découvrez CUBI sur votre propre projet", text: "Ouvrez l’espace de travail et partez d’une vue projet connectée.", label: "Ouvrir l’espace CUBI" },
  ru: { title: "Проверьте CUBI на своём проекте", text: "Откройте рабочее пространство и начните со связанного представления проекта.", label: "Открыть рабочее пространство" },
  tr: { title: "CUBI’yi kendi projenizde deneyin", text: "Çalışma alanını açın ve bağlı bir proje görünümünden devam edin.", label: "CUBI çalışma alanını aç" },
  ja: { title: "あなたのプロジェクトで CUBI を確認", text: "ワークスペースを開き、つながったプロジェクトビューから始めましょう。", label: "CUBI ワークスペースを開く" },
  ko: { title: "내 프로젝트에서 CUBI 확인하기", text: "워크스페이스를 열고 연결된 프로젝트 뷰에서 시작하세요.", label: "CUBI 워크스페이스 열기" },
  zh: { title: "在您自己的项目中体验 CUBI", text: "打开工作区，从互联的项目视图开始。", label: "打开 CUBI 工作区" },
  ar: { title: "جرّب CUBI على مشروعك", text: "افتح مساحة العمل وابدأ من عرض مشروع مترابط.", label: "فتح مساحة عمل CUBI" },
};

const locales = new Map();
for (const code of LOCALE_CODES) {
  const modulePath = pathToFileURL(join(webRoot, "site", "locales", `${code}.mjs`)).href;
  const module = await import(modulePath);
  const locale = module.default;
  if (locale.code !== code) throw new Error(`LOCALE_CODE_MISMATCH: ${code}`);
  locales.set(code, locale);
}

const published = new Map();
for (const [code, locale] of locales) {
  const ids = new Set(locale.pages.map((page) => page.id));
  if (code === "en" || code === "fa") for (const id of HANDWRITTEN_ROUTES) ids.add(id);
  published.set(code, ids);
}

/** Absolute site directory for a route inside one locale, e.g. "/de/features". */
function siteDir(code, routePath) {
  const prefix = locales.get(code).prefix;
  return posix.join("/", (prefix + routePath).replace(/\/+$/, ""));
}

function relDir(fromDir, toDir) {
  if (fromDir === toDir) return "./";
  const value = posix.relative(fromDir || "/", toDir || "/");
  return `${value || "."}/`;
}

function relFile(fromDir, target) {
  return posix.relative(fromDir || "/", target);
}

function esc(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function alternateHref(code, routePath) {
  return `__CUBI_BASE_URL__/${locales.get(code).prefix}${routePath}`;
}

function alternateLocales(pageId) {
  return LOCALE_CODES.filter((code) => published.get(code).has(pageId));
}

function renderAlternates(pageId) {
  return alternateLocales(pageId)
    .map((code) => {
      const lang = locales.get(code).htmlLang;
      return `<link rel="alternate" hreflang="${lang}" href="${alternateHref(code, ROUTE_PATHS[pageId])}">`;
    })
    .join("\n");
}

function renderOgAlternates(pageId, selfCode) {
  return alternateLocales(pageId)
    .filter((code) => code !== selfCode)
    .map((code) => `<meta property="og:locale:alternate" content="${OG_LOCALE[code]}">`)
    .join("\n");
}

function navTarget(code, key) {
  const routePath = ROUTE_PATHS[key];
  if (published.get(code).has(key)) return siteDir(code, routePath);
  return siteDir("en", routePath);
}

function renderNav(locale, currentId, fromDir) {
  const links = NAV_KEYS.map((key) => {
    const current = key === currentId ? ' aria-current="page"' : "";
    return `<a href="${relDir(fromDir, navTarget(locale.code, key))}"${current}>${esc(locale.nav[key])}</a>`;
  }).join("");
  return `<nav class="cubi-public-nav" aria-label="${esc(NAV_LABEL[locale.code])}">${links}</nav>`;
}

function renderLanguageSwitch(locale, pageId, fromDir) {
  // The head of the switch is the bilingual twin (fa <-> en) that the existing
  // documents and tests describe; the menu then lists every other published locale.
  const twin = locale.code === "en" ? "fa" : "en";
  const twinLocale = locales.get(twin);
  const twinLink = `<a class="cubi-public-language" hreflang="${twinLocale.htmlLang}" href="${relDir(fromDir, siteDir(twin, ROUTE_PATHS[pageId]))}" lang="${twinLocale.htmlLang}">${esc(twinLocale.label)}</a>`;
  const others = alternateLocales(pageId)
    .filter((code) => code !== locale.code && code !== twin)
    .map((code) => {
      const target = locales.get(code);
      return `<a hreflang="${target.htmlLang}" href="${relDir(fromDir, siteDir(code, ROUTE_PATHS[pageId]))}" lang="${target.htmlLang}">${esc(target.label)}</a>`;
    })
    .join("");
  if (!others) return twinLink;
  const block = `<details class="cubi-public-languages"><summary>${esc(LANGUAGE_MENU_LABEL[locale.code])}</summary><nav aria-label="${esc(LANGUAGE_MENU_LABEL[locale.code])}">${others}</nav></details>`;
  return `${twinLink}${block}`;
}

function renderFooter(locale, fromDir) {
  const groups = locale.footer.groups
    .map((group) => `<div><b>${esc(group.title)}</b>${group.links
      .map(([key, label]) => `<a href="${relDir(fromDir, navTarget(locale.code, key))}">${esc(label)}</a>`)
      .join(" · ")}</div>`)
    .join("");
  return `<footer class="cubi-public-footer"><span>${esc(locale.footer.tagline)}</span><nav aria-label="${esc(NAV_LABEL[locale.code])}">${groups}</nav></footer>`;
}

function renderSections(page) {
  return page.sections
    .map((section) => {
      const cards = (section.cards ?? [])
        .map((card) => `<article class="cubi-public-card"><h3>${esc(card.h3)}</h3><p>${esc(card.p)}</p></article>`)
        .join("");
      const grid = cards ? `<div class="cubi-public-grid">${cards}</div>` : "";
      return `<h2>${esc(section.h2)}</h2><p>${esc(section.p)}</p>${grid}`;
    })
    .join("\n");
}

function renderCta(locale, page, fromDir) {
  const fallback = CTA_FALLBACK[locale.code];
  const cta = page.cta ?? { title: fallback.title, text: fallback.text };
  const label = page.cta?.label ?? locale.cta.label ?? fallback.label;
  const href = page.cta?.href ?? locale.cta.href ?? "/app/";
  const arrow = locale.dir === "rtl" ? "←" : "→";
  return `<div class="cubi-public-cta"><div><strong>${esc(cta.title)}</strong><p>${esc(cta.text)}</p></div><a href="${relDir(fromDir, "/app/") || "/app/"}">${esc(label)} ${arrow}</a></div>`;
}

function renderStructuredData(page, locale, routeUrl) {
  // WebPage + WebSite only: they describe what the document already says in its
  // title, description and canonical URL. No offer, rating or breadcrumb is
  // emitted that the page does not show.
  const data = {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: page.title,
    description: page.description,
    url: `__CUBI_BASE_URL__${routeUrl}`,
    inLanguage: locale.htmlLang,
    isPartOf: {
      "@type": "WebSite",
      name: "CUBI Platform",
      url: "__CUBI_BASE_URL__/",
    },
  };
  return `<script type="application/ld+json">\n${JSON.stringify(data, null, 2).replace(/<\//g, "<\\/")}\n</script>`;
}

function renderPage(locale, page) {
  const routePath = page.path;
  const prefix = locale.prefix;
  const routeUrl = `/${prefix}${routePath}`;
  const fromDir = routePath === "" ? `/${prefix.replace(/\/+$/, "")}` : routeUrl.replace(/\/+$/, "");
  const file = join(publicRoot, prefix, routePath, "index.html");
  const depth = fromDir.split("/").filter(Boolean).length;
  const root = relDir(fromDir || "/", "/");
  const homeHref = locale.code === "en"
    ? `${root}index.html`
    : relDir(fromDir, siteDir(locale.code, ""));

  const html = `<!doctype html>
<html lang="${locale.htmlLang}" dir="${locale.dir}">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(page.title)}</title>
<meta name="description" content="${esc(page.description)}">
<link rel="canonical" href="__CUBI_BASE_URL__${routeUrl}">
${renderAlternates(page.id)}
<link rel="alternate" hreflang="x-default" href="${alternateHref("en", ROUTE_PATHS[page.id])}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="CUBI Platform">
<meta property="og:locale" content="${OG_LOCALE[locale.code]}">
${renderOgAlternates(page.id, locale.code)}
<meta property="og:title" content="${esc(page.title)}">
<meta property="og:description" content="${esc(page.description)}">
<meta property="og:url" content="__CUBI_BASE_URL__${routeUrl}">
<meta property="og:image" content="__CUBI_BASE_URL__/cubi-platform-logo-primary.svg">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="${esc(page.title)}">
<meta name="twitter:description" content="${esc(page.description)}">
<meta name="twitter:image" content="__CUBI_BASE_URL__/cubi-platform-logo-primary.svg">
<meta name="robots" content="index,follow">
<meta name="theme-color" content="#081A2F">
<link rel="stylesheet" href="${relFile(fromDir, "/styles.css")}">
<link rel="icon" href="${relFile(fromDir, "/cubi-platform-logo-primary.svg")}" type="image/svg+xml">
${renderStructuredData(page, locale, routeUrl)}
</head>
<body class="cubi-public-page">
<header class="cubi-public-header"><a href="${homeHref}" aria-label="${esc(locale.nav.home)}"><img src="${relFile(fromDir, "/cubi-platform-logo-primary.svg")}" alt="CUBI Platform" width="132" height="48"></a>${renderNav(locale, page.id, fromDir)}${renderLanguageSwitch(locale, page.id, fromDir)}</header>
<main>
<section class="cubi-public-hero"><p class="eyebrow">${esc(page.eyebrow)}</p><h1>${esc(page.h1)}</h1><p>${esc(page.lead)}</p></section>
<section class="cubi-public-content">${renderSections(page)}
${renderCta(locale, page, fromDir)}</section>
</main>
${renderFooter(locale, fromDir)}
<script type="module" src="${relFile(fromDir, "/dist/global-assistant-launcher.bundle.js")}"></script>
</body></html>
`;
  mkdirSync(dirname(file), { recursive: true });
  writeFileSync(file, html);
  return { file, depth };
}

// ---- hand-written documents: refresh alternates, social alternates and switcher
const HANDWRITTEN_FILES = [
  // id, locale code, file (relative to apps/web), page directory used for links
  ["home", "en", "index.html", "/"],
  ["home", "fa", "public/fa/index.html", "/fa"],
  ["platform", "en", "public/platform/index.html", "/platform"],
  ["platform", "fa", "public/fa/platform/index.html", "/fa/platform"],
  ["solutions", "en", "public/solutions/index.html", "/solutions"],
  ["solutions", "fa", "public/fa/solutions/index.html", "/fa/solutions"],
  ["pricing", "en", "public/pricing/index.html", "/pricing"],
  ["pricing", "fa", "public/fa/pricing/index.html", "/fa/pricing"],
  ["resources", "en", "public/resources/index.html", "/resources"],
  ["resources", "fa", "public/fa/resources/index.html", "/fa/resources"],
  ["contact", "en", "public/contact/index.html", "/contact"],
  ["contact", "fa", "public/fa/contact/index.html", "/fa/contact"],
  ["about", "en", "public/about/index.html", "/about"],
  ["about", "fa", "public/fa/about/index.html", "/fa/about"],
  ["help", "en", "public/help/index.html", "/help"],
  ["help", "fa", "public/fa/help/index.html", "/fa/help"],
];

function refreshHandwritten(pageId, code, relativeFile, fromDir) {
  const file = join(webRoot, relativeFile);
  if (!existsSync(file)) return false;
  let html = readFileSync(file, "utf8");
  const locale = locales.get(code);
  const indentMatch = html.match(/\n([ \t]*)<link rel="canonical"/);
  const indent = indentMatch ? indentMatch[1] : "";

  // Remove every existing alternate link and re-emit the published set.
  html = html.replace(/[ \t]*<link rel="alternate" hreflang="[^"]+"[^>]*>\r?\n?/g, "");
  const alternates = renderAlternates(pageId).replaceAll("\n", `\n${indent}`);
  const alternateBlock = `${alternates}\n${indent}<link rel="alternate" hreflang="x-default" href="${alternateHref("en", ROUTE_PATHS[pageId])}">\n${indent}`;
  html = html.replace(/(<link rel="canonical"[^>]*>\r?\n)/, `$1${indent}${alternateBlock}`);

  // Refresh the social alternates as well.
  html = html.replace(/\s*<meta property="og:locale:alternate" content="[^"]*">/g, "");
  const ogAlternates = renderOgAlternates(pageId, code).replaceAll("\n", `\n${indent}`);
  html = html.replace(/(<meta property="og:locale" content="[^"]*">)/, `$1${ogAlternates ? `\n${indent}${ogAlternates}` : ""}`);

  // Hand-written documents carry the same WebPage structured data as the
  // generated pages, built from their own title, description and canonical URL.
  if (!html.includes("application/ld+json")) {
    const canonical = html.match(/<link rel="canonical" href="([^"]+)"/)?.[1] ?? "";
    const title = html.match(/<title>([^<]+)<\/title>/)?.[1] ?? "";
    const description = html.match(/<meta name="description" content="([^"]*)"/)?.[1] ?? "";
    const lang = html.match(/<html lang="([^"]+)"/)?.[1] ?? locale.htmlLang;
    const data = {
      "@context": "https://schema.org",
      "@type": "WebPage",
      name: title,
      description,
      url: canonical,
      inLanguage: lang,
      isPartOf: { "@type": "WebSite", name: "CUBI Platform", url: "__CUBI_BASE_URL__/" },
    };
    const block = `<script type="application/ld+json">\n${JSON.stringify(data, null, 2).replace(/<\//g, "<\\/")}\n</script>\n${indent}`;
    html = html.replace(/<\/head>/, `${indent}${block}</head>`);
  }

  // The alternate block is re-emitted on every run. Pin the line that follows
  // it to the document indent so repeated generation cannot accumulate spaces.
  html = html.replace(/(hreflang="x-default"[^>]*>)\r?\n[ \t]+/, `$1\n${indent}`);

  // Replace a legacy single twin link with the twin plus the language menu.
  html = html.replace(/<details class="cubi-public-languages">[\s\S]*?<\/details>/g, "");
  const switcher = renderLanguageSwitch(locale, pageId, fromDir);
  if (html.includes('class="cubi-public-language"')) {
    html = html.replace(/<a class="cubi-public-language"[\s\S]*?<\/a>/, switcher);
  }
  writeFileSync(file, html);
  return true;
}

let generated = 0;
const generatedIds = new Set();
for (const code of LOCALE_CODES) {
  const locale = locales.get(code);
  for (const page of locale.pages) {
    if ((code === "en" || code === "fa") && HANDWRITTEN_ROUTES.has(page.id)) continue;
    renderPage(locale, page);
    generatedIds.add(`${code}:${page.id}`);
    generated += 1;
  }
}

let refreshed = 0;
for (const [pageId, code, relativeFile, fromDir] of HANDWRITTEN_FILES) {
  if (refreshHandwritten(pageId, code, relativeFile, fromDir)) refreshed += 1;
}

const missing = [];
for (const code of LOCALE_CODES) {
  for (const id of Object.keys(ROUTE_PATHS)) {
    if (!published.get(code).has(id)) continue;
    const locale = locales.get(code);
    const alreadyHandwritten = (code === "en" || code === "fa") && HANDWRITTEN_ROUTES.has(id);
    const routePath = ROUTE_PATHS[id];
    const file = alreadyHandwritten && id === "home" && code === "en"
      ? join(webRoot, "index.html")
      : join(publicRoot, locale.prefix, routePath, "index.html");
    if (!existsSync(file)) missing.push(`${code}:${id} -> ${relative(webRoot, file)}`);
  }
}
if (missing.length) throw new Error(`PUBLIC_PAGE_MISSING:\n${missing.join("\n")}`);

console.log(`Generated ${generated} localized pages and refreshed ${refreshed} hand-written documents.`);
console.log(`Published routes — en: ${[...published.get("en")].length}, fa: ${[...published.get("fa")].length}, others: ${[...published.get("de")].length}.`);
