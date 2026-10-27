type LandingLocale = string;
type Feature = { icon: string; title: string; body: string; assistantAvatar?: boolean };
type LandingCopy = {
  nav: string[]; eyebrow: string; title: string; accent: string; subtitle: string; body: string;
  primary: string; secondary: string; featuresEyebrow: string; featuresTitle: string; featuresBody: string; features: Feature[];
  techEyebrow: string; techTitle: string; techBody: string; techLink: string; techNodes: string[];
  ctaTitle: string; ctaBody: string; signIn: string; start: string; language: string;
  footerColumns: Array<{ title: string; links: string[] }>; footerNote: string;
  assistantTitle: string; assistantSubtitle: string; assistantDescription: string;
  assistantWorkspaceAction: string; assistantClose: string;
};
const copy: Partial<Record<LandingLocale, LandingCopy>> = {
  en: {
    nav: ["Home", "Platform", "Solutions", "Resources"],
    eyebrow: "CONSTRUCTION & BUILDING INTELLIGENCE",
    title: "Control every detail.", accent: "Build with confidence.",
    subtitle: "Plan. Control. Build Smarter.",
    body: "Bring schedules, cost, progress, resources and project evidence into one clear control room—so your team can make the next decision with confidence.",
    primary: "Explore the Platform →", secondary: "See How It Works",
    featuresEyebrow: "ONE CONNECTED WORKFLOW",
    featuresTitle: "Everything your project needs to stay in control",
    featuresBody: "Connect the work, the numbers and the evidence in one practical workspace built for construction teams.",
    features: [
      { icon: "⌁", title: "Project Controls", body: "Track milestones, progress and performance signals in one project view." },
      { icon: "✧", assistantAvatar: true, title: "AI Assistant", body: "Turn project information into useful summaries, questions and next steps." },
      { icon: "↗", title: "Resources & Cost", body: "Connect resource plans, cost visibility and delivery performance." },
      { icon: "▤", title: "Documents & Contracts", body: "Keep project records and supporting evidence close to the workflow." },
      { icon: "◎", title: "Team Collaboration", body: "Give stakeholders a shared view of project status and actions." },
      { icon: "☁", title: "Cloud & Scalability", body: "Access a consistent project workspace as teams and projects grow." }
    ],
    techEyebrow: "BUILT FOR REAL PROJECTS",
    techTitle: "A connected foundation for better decisions",
    techBody: "CUBI brings project planning, controls, information and intelligent assistance together while keeping the project workflow at the center.",
    techLink: "Explore platform capabilities →",
    techNodes: ["Project controls", "AI assistance", "Connected data", "Secure workflow"],
    ctaTitle: "Bring your project into focus.",
    ctaBody: "Start with one connected view of schedules, costs, progress and decisions.",
    assistantTitle: "CUBI AI Assistant",
    assistantSubtitle: "Project help, one step away",
    assistantDescription: "For project-specific answers or schedule support, open your workspace and select a project. Your assistant is available inside the workspace.",
    assistantWorkspaceAction: "Open project workspace →",
    assistantClose: "Close assistant panel",
    signIn: "Sign In", start: "Get Started", language: "فارسی",
    footerColumns: [
      { title: "Platform", links: ["Project Controls", "Planning & Scheduling", "Resources & Cost"] },
      { title: "Solutions", links: ["Construction Teams", "Project Leadership", "Project Delivery"] },
      { title: "Resources", links: ["Documentation", "Product Overview", "Contact"] }
    ],
    footerNote: "Plan. Control. Build Smarter."
  },
  fa: {
    nav: ["خانه", "پلتفرم", "راهکارها", "منابع"],
    eyebrow: "هوشمندی ساخت و مدیریت پروژه",
    title: "جزئیات را کنترل کنید؛", accent: "با اطمینان بسازید.",
    subtitle: "برنامه‌ریزی. کنترل. ساخت هوشمندتر.",
    body: "زمان‌بندی، هزینه، پیشرفت، منابع و شواهد پروژه را در یک اتاق کنترل روشن کنار هم قرار دهید تا تیم شما با اطمینان تصمیم بعدی را بگیرد.",
    primary: "کاوش پلتفرم ←", secondary: "نحوه کار را ببینید",
    featuresEyebrow: "جریان کاری یکپارچه",
    featuresTitle: "همه آنچه پروژه برای کنترل بهتر نیاز دارد",
    featuresBody: "کارها، اعداد و مستندات پروژه را در یک فضای کاری کاربردی برای تیم‌های ساخت به هم متصل کنید.",
    features: [
      { icon: "⌁", title: "کنترل پروژه", body: "نقاط عطف، پیشرفت و شاخص‌های عملکرد را در یک نمای پروژه دنبال کنید." },
      { icon: "✧", assistantAvatar: true, title: "دستیار هوشمند", body: "اطلاعات پروژه را به خلاصه‌ها، پرسش‌ها و گام‌های بعدی مفید تبدیل کنید." },
      { icon: "↗", title: "منابع و هزینه", body: "برنامه منابع، شفافیت هزینه و عملکرد اجرا را به هم متصل کنید." },
      { icon: "▤", title: "اسناد و قراردادها", body: "سوابق و شواهد پشتیبان پروژه را در کنار جریان کار نگه دارید." },
      { icon: "◎", title: "همکاری تیمی", body: "نمای مشترک و روشنی از وضعیت پروژه و اقدامات در اختیار ذی‌نفعان قرار دهید." },
      { icon: "☁", title: "ابر و توسعه‌پذیری", body: "با رشد تیم‌ها و پروژه‌ها به فضای کاری یکپارچه دسترسی داشته باشید." }
    ],
    techEyebrow: "برای پروژه‌های واقعی",
    techTitle: "زیرساختی یکپارچه برای تصمیم‌های بهتر",
    techBody: "کوبی برنامه‌ریزی، کنترل پروژه، اطلاعات و دستیار هوشمند را کنار هم قرار می‌دهد و جریان کاری پروژه را در مرکز نگه می‌دارد.",
    techLink: "مشاهده قابلیت‌های پلتفرم ←",
    techNodes: ["کنترل پروژه", "دستیار هوشمند", "داده یکپارچه", "جریان کاری امن"],
    ctaTitle: "تصویر روشنی از پروژه بسازید.",
    ctaBody: "با نمایی یکپارچه از زمان‌بندی، هزینه، پیشرفت و تصمیم‌ها شروع کنید.",
    assistantTitle: "دستیار هوشمند کوبی",
    assistantSubtitle: "راهنمای پروژه، همیشه در دسترس",
    assistantDescription: "برای دریافت پاسخ درباره پروژه یا کمک در زمان‌بندی، وارد فضای کاری شوید و یک پروژه انتخاب کنید. دستیار در محیط پروژه در دسترس است.",
    assistantWorkspaceAction: "ورود به فضای کاری پروژه ←",
    assistantClose: "بستن پنل دستیار",
    signIn: "ورود", start: "شروع کنید", language: "EN",
    footerColumns: [
      { title: "پلتفرم", links: ["کنترل پروژه", "برنامه‌ریزی و زمان‌بندی", "منابع و هزینه"] },
      { title: "راهکارها", links: ["تیم‌های ساخت", "مدیریت پروژه", "تحویل پروژه"] },
      { title: "منابع", links: ["مستندات", "معرفی محصول", "تماس"] }
    ],
    footerNote: "برنامه‌ریزی. کنترل. ساخت هوشمندتر."
  }
};
import { getAvailableWorkspaceLocales, getWorkspaceLocaleDirection, getWorkspaceLocaleDisplayName, translateWorkspaceText } from "./workspace-localization.js";
import { cubiAssistantAvatarUrl } from "./cubi-brand-assets.js";

const LANDING_LOCALE_STORAGE_KEY = "cubi:landing-locale";
let locale: LandingLocale = "en";
function restoreLandingLocale(): void {
  try {
    const saved = window.localStorage.getItem(LANDING_LOCALE_STORAGE_KEY);
    if (saved && getAvailableWorkspaceLocales().includes(saved)) locale = saved;
  } catch {
    // Storage may be disabled; the language switch must still work.
  }
}
function persistLandingLocale(): void {
  try {
    window.localStorage.setItem(LANDING_LOCALE_STORAGE_KEY, locale);
  } catch {
    // Keep the selected language for the current render even without storage.
  }
}
function setLandingDocumentLocale(): void {
  document.documentElement.lang = locale;
  document.documentElement.dir = getWorkspaceLocaleDirection(locale);
}
function getLandingCopy(locale: LandingLocale): LandingCopy {
  const baseline = copy[locale] ?? copy.en!;
  const availableLocales = getAvailableWorkspaceLocales();
  const currentLocaleIndex = availableLocales.indexOf(locale);
  const nextLocale = availableLocales[(currentLocaleIndex + 1) % availableLocales.length] ?? "en";
  const translate = (key: string, fallback: string) => translateWorkspaceText(locale, `landing.${key}`, fallback);
  const localized: LandingCopy = {
    ...baseline,
    nav: baseline.nav.map((value, index) => translate(`nav.${index}`, value)),
    eyebrow: translate("eyebrow", baseline.eyebrow),
    title: translate("title", baseline.title),
    accent: translate("accent", baseline.accent),
    subtitle: translate("subtitle", baseline.subtitle),
    body: translate("body", baseline.body),
    primary: translate("primary", baseline.primary),
    secondary: translate("secondary", baseline.secondary),
    featuresEyebrow: translate("featuresEyebrow", baseline.featuresEyebrow),
    featuresTitle: translate("featuresTitle", baseline.featuresTitle),
    featuresBody: translate("featuresBody", baseline.featuresBody),
    features: baseline.features.map((feature, index) => ({
      assistantAvatar: feature.assistantAvatar,
      icon: translate(`features.${index}.icon`, feature.icon),
      title: translate(`features.${index}.title`, feature.title),
      body: translate(`features.${index}.body`, feature.body),
    })),
    techEyebrow: translate("techEyebrow", baseline.techEyebrow),
    techTitle: translate("techTitle", baseline.techTitle),
    techBody: translate("techBody", baseline.techBody),
    techLink: translate("techLink", baseline.techLink),
    techNodes: baseline.techNodes.map((value, index) => translate(`techNodes.${index}`, value)),
    ctaTitle: translate("ctaTitle", baseline.ctaTitle),
    ctaBody: translate("ctaBody", baseline.ctaBody),
    signIn: translate("signIn", baseline.signIn),
    start: translate("start", baseline.start),
    language: translate("language", getWorkspaceLocaleDisplayName(nextLocale)),
    footerColumns: baseline.footerColumns.map((column, columnIndex) => ({
      title: translate(`footerColumns.${columnIndex}.title`, column.title),
      links: column.links.map((value, linkIndex) => translate(`footerColumns.${columnIndex}.links.${linkIndex}`, value)),
    })),
    footerNote: translate("footerNote", baseline.footerNote),
    assistantTitle: translate("assistant.title", baseline.assistantTitle),
    assistantSubtitle: translate("assistant.subtitle", baseline.assistantSubtitle),
    assistantDescription: translate("assistant.description", baseline.assistantDescription),
    assistantWorkspaceAction: translate("assistant.workspaceAction", baseline.assistantWorkspaceAction),
    assistantClose: translate("assistant.close", baseline.assistantClose),
  };
  return escapeLandingCopy(localized);
}

function escapeLandingCopy<T>(value: T): T {
  if (typeof value === "string") return escapeHtml(value) as T;
  if (Array.isArray(value)) return value.map((item) => escapeLandingCopy(item)) as T;
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, escapeLandingCopy(item)])) as T;
  }
  return value;
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"\']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"' : "&quot;", "\'": "&#39;" })[character]!);
}

function renderLanding(container: HTMLElement): void {
  const t = getLandingCopy(locale);
  setLandingDocumentLocale();
  container.innerHTML = `
    <div class="cubi-reference-home cubi-exact-home" id="home">
      <header class="cubi-exact-header">
        <a class="cubi-exact-brand" href="./" aria-label="CUBI Platform home"><img src="./cubi-platform-logo-primary.svg" width="180" height="60" alt="CUBI Platform — Plan. Control. Build Smarter." /></a>
        <nav class="cubi-exact-nav" aria-label="Primary navigation">
          <a class="is-active" href="#home">${t.nav[0]}</a><a href="./platform/">${t.nav[1]}</a><a href="./solutions/">${t.nav[2]}</a><a href="./resources/">${t.nav[3]}</a>
        </nav>
        <div class="cubi-exact-actions">
          <button class="cubi-exact-language" id="cubi-language" type="button" aria-label="Change language">${t.language}</button>
          <a href="./app/" class="cubi-exact-signin">${t.signIn}</a><a href="./app/" class="cubi-exact-start">${t.start} →</a>
        </div>
      </header>
      <main>
        <section class="cubi-exact-hero" aria-labelledby="cubi-hero-title">
          <div class="cubi-exact-hero-copy">
            <p class="cubi-exact-eyebrow">${t.eyebrow}</p><h1 id="cubi-hero-title">${t.title}<span>${t.accent}</span></h1><h2>${t.subtitle}</h2><p>${t.body}</p>
            <div class="cubi-exact-hero-actions"><a class="cubi-exact-primary" href="./app/">${t.primary}</a><a class="cubi-exact-demo" href="#technology"><span class="play" aria-hidden="true">▶</span>${t.secondary}</a></div>
          </div>
          <div class="cubi-exact-dashboard" role="img" aria-label="Illustrative CUBI project dashboard showing schedule, progress and performance">
            <aside class="cubi-dash-sidebar"><img src="./cubi-platform-logo-primary.svg" width="110" height="32" alt="CUBI Platform" /><span>Overview</span><span>Schedule</span><span>Cost control</span><span>Resources</span><span>Documents</span></aside>
            <div class="cubi-dash-main"><div class="cubi-dash-title"><strong>Project Control Center</strong><span>PROJECT / 026</span></div>
              <div class="cubi-gantt" aria-hidden="true"><i style="width:76%"></i><i style="width:58%"></i><i style="width:82%"></i><i style="width:49%"></i><i style="width:67%"></i><i style="width:38%"></i></div>
              <div class="cubi-dash-bottom"><div class="cubi-mini-chart"><b>Progress trend</b><div class="cubi-line-chart"></div></div><div class="cubi-ring-card"><b>Schedule</b><div class="cubi-ring"><strong>78%</strong></div><small>On track</small></div><div class="cubi-ai-card"><b>AI insight</b><div class="cubi-ai-bubble" aria-hidden="true"><img src="${cubiAssistantAvatarUrl()}" width="31" height="31" alt="" /></div><small>Review next milestone</small></div></div>
            </div>
            <aside class="cubi-progress-card"><div class="cubi-progress-ring"><strong>84%</strong></div><b>Project progress</b><div><span>Plan</span><span>Actual</span></div></aside>
          </div>
        </section>
        <section class="cubi-exact-features" id="capabilities">
          <div class="cubi-exact-section-head"><p class="cubi-kicker">${t.featuresEyebrow}</p><h2>${t.featuresTitle}</h2><p>${t.featuresBody}</p></div>
          <div class="cubi-exact-feature-grid">${t.features.map((f) => `<article><div class="cubi-feature-icon${f.assistantAvatar ? " cubi-feature-icon-assistant" : ""}" aria-hidden="true">${f.assistantAvatar ? `<img src="${cubiAssistantAvatarUrl()}" width="50" height="50" alt="" />` : f.icon}</div><h3>${f.title}</h3><p>${f.body}</p></article>`).join("")}</div>
        </section>
        <section class="cubi-exact-tech" id="technology" aria-labelledby="cubi-tech-title">
          <div class="cubi-tech-copy"><p class="cubi-kicker">${t.techEyebrow}</p><h2 id="cubi-tech-title">${t.techTitle}</h2><p>${t.techBody}</p>
            <div class="cubi-tech-badges" aria-label="Platform building blocks"><b class="plan">PL</b><span>Planning</span><b class="pg">▦</b><span>Project data</span><b class="ai" aria-hidden="true"><img src="${cubiAssistantAvatarUrl()}" width="29" height="29" alt="" /></b><span>AI</span></div>
            <a class="cubi-exact-outline" href="./app/">${t.techLink}</a>
          </div>
          <div class="cubi-tech-diagram" aria-label="Connected platform capabilities"><div class="cubi-stack" aria-hidden="true"><i></i><i></i><i></i><b>C</b></div>
            <div class="cubi-tech-node n1"><span>${t.techNodes[0]}</span></div><div class="cubi-tech-node n2"><span>${t.techNodes[1]}</span></div><div class="cubi-tech-node n3"><span>${t.techNodes[2]}</span></div><div class="cubi-tech-node n4"><span>${t.techNodes[3]}</span></div>
          </div>
        </section>
        <section class="cubi-exact-cta" id="resources"><div><h2>${t.ctaTitle}</h2><p>${t.ctaBody}</p></div><div class="cubi-cta-actions"><a class="cubi-exact-primary" href="./app/">${t.primary}</a><a class="cubi-exact-demo" href="#capabilities">${t.secondary}</a></div></section>
      </main>
      <footer class="cubi-exact-footer">
        <div class="cubi-footer-brand"><img src="./cubi-platform-logo-primary.svg" width="160" height="45" alt="CUBI Platform — Plan. Control. Build Smarter." /></div>
        ${t.footerColumns.map((col, columnIndex) => { const targets = [["./platform/#project-controls", "./platform/#scheduling", "./platform/#resources-cost"], ["./solutions/#construction-teams", "./solutions/#project-leadership", "./solutions/#project-delivery"], ["./resources/#documentation", "./resources/#overview", "./contact/"]]; return `<div class="cubi-footer-col"><b>${col.title}</b>${col.links.map((link, linkIndex) => `<a href="${targets[columnIndex]?.[linkIndex] ?? "./"}">${link}</a>`).join("")}</div>`; }).join("")}
        <div class="cubi-footer-social"><small>© 2026 CUBI Platform. All rights reserved.</small></div>
      </footer>
      <div class="cubi-assistant-launcher" data-cubi-assistant-entry>
        <section class="cubi-assistant-popover" id="cubi-assistant-popover" role="dialog" aria-modal="false" aria-labelledby="cubi-assistant-title" aria-describedby="cubi-assistant-description" hidden>
          <header class="cubi-assistant-popover-header">
            <img src="${cubiAssistantAvatarUrl()}" width="52" height="52" alt="" aria-hidden="true" />
            <div class="cubi-assistant-popover-heading">
              <strong id="cubi-assistant-title">${t.assistantTitle}</strong>
              <span>${t.assistantSubtitle}</span>
            </div>
            <button class="cubi-assistant-close" id="cubi-assistant-close" type="button" aria-label="${t.assistantClose}">×</button>
          </header>
          <p id="cubi-assistant-description">${t.assistantDescription}</p>
          <a class="cubi-assistant-workspace-link" href="./app/">${t.assistantWorkspaceAction}</a>
        </section>
        <button class="cubi-assistant-launcher-button" id="cubi-assistant-launcher" type="button" aria-controls="cubi-assistant-popover" aria-expanded="false" aria-label="${t.assistantTitle}">
          <img src="${cubiAssistantAvatarUrl()}" width="52" height="52" alt="" aria-hidden="true" />
          <span>${t.assistantTitle}</span>
        </button>
      </div>
    </div>`;
  const assistantLauncher = document.getElementById("cubi-assistant-launcher");
  const assistantPopover = document.getElementById("cubi-assistant-popover");
  const assistantClose = document.getElementById("cubi-assistant-close");
  const setAssistantPopoverOpen = (open: boolean): void => {
    if (!assistantLauncher || !assistantPopover) return;
    assistantPopover.hidden = !open;
    assistantLauncher.setAttribute("aria-expanded", String(open));
    if (open) assistantClose?.focus();
    else assistantLauncher.focus();
  };
  assistantLauncher?.addEventListener("click", () => {
    setAssistantPopoverOpen(assistantLauncher?.getAttribute("aria-expanded") !== "true");
  });
  assistantClose?.addEventListener("click", () => setAssistantPopoverOpen(false));
  assistantPopover?.addEventListener("keydown", (event: KeyboardEvent) => {
    if (event.key === "Escape") setAssistantPopoverOpen(false);
  });
  document.getElementById("cubi-language")?.addEventListener("click", () => {
    const available = getAvailableWorkspaceLocales();
    const index = available.indexOf(locale);
    locale = available[(index + 1) % available.length] ?? "en";
    persistLandingLocale();
    renderLanding(container);
  });
}
export function renderLandingPage(container: HTMLElement): void {
  if (container.dataset.localeInitialized !== "true") {
    restoreLandingLocale();
    container.dataset.localeInitialized = "true";
  }
  renderLanding(container);
}
