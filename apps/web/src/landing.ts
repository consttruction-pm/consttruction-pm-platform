type LandingLocale = "en" | "fa";

const copy: Record<LandingLocale, {
  nav: string[]; eyebrow: string; title: string; titleAccent: string; sub: string; body: string;
  primary: string; secondary: string; capabilities: string; capabilityBody: string;
  cards: Array<[string,string,string]>; cta: string; ctaBody: string; lang: string;
}> = {
  en: {
    nav: ["Home", "Product", "Solutions", "Resources"],
    eyebrow: "CUBI PLATFORM",
    title: "Construction control,",
    titleAccent: "built for decisions.",
    sub: "Plan. Control. Build Smarter.",
    body: "A construction project-control platform that connects scheduling, progress, cost, resources, documents and AI around one authoritative project workflow.",
    primary: "Open Platform →", secondary: "Explore capabilities ↓",
    capabilities: "One control room for the project",
    capabilityBody: "Keep the most important project signals close to the work—without turning the homepage into a long marketing brochure.",
    cards: [
      ["Planning & Scheduling", "Authoritative project planning, schedules and dependencies.", "01"],
      ["Project Controls", "Progress, cost and EVM signals for practical control.", "02"],
      ["Resources & Documents", "Connect people, resources, records and project evidence.", "03"],
      ["AI & Insights", "Turn project data into faster questions, summaries and decisions.", "04"],
    ],
    cta: "Ready to control the next project?",
    ctaBody: "Open the platform and move from project data to project decisions.",
    lang: "فارسی",
  },
  fa: {
    nav: ["خانه", "محصول", "راهکارها", "منابع"],
    eyebrow: "پلتفرم CUBI",
    title: "کنترل پروژه‌های ساخت،",
    titleAccent: "برای تصمیم‌های بهتر.",
    sub: "برنامه‌ریزی. کنترل. ساخت هوشمندتر.",
    body: "یک پلتفرم کنترل پروژه ساختمانی که زمان‌بندی، پیشرفت، هزینه، منابع، اسناد و هوش مصنوعی را در یک جریان کاری یکپارچه قرار می‌دهد.",
    primary: "ورود به پلتفرم ←", secondary: "مشاهده قابلیت‌ها ↓",
    capabilities: "یک اتاق کنترل برای کل پروژه",
    capabilityBody: "مهم‌ترین سیگنال‌های پروژه را نزدیک به کار نگه دارید؛ بدون تبدیل صفحه اصلی به یک بروشور طولانی.",
    cards: [
      ["برنامه‌ریزی و زمان‌بندی", "برنامه پروژه، زمان‌بندی و روابط وابستگی در یک مرجع واحد.", "۰۱"],
      ["کنترل پروژه", "پیشرفت، هزینه و شاخص‌های EVM برای کنترل عملیاتی.", "۰۲"],
      ["منابع و اسناد", "افراد، منابع، سوابق و شواهد پروژه را به هم متصل کنید.", "۰۳"],
      ["هوش مصنوعی و بینش", "داده پروژه را به پرسش، خلاصه و تصمیم سریع‌تر تبدیل کنید.", "۰۴"],
    ],
    cta: "برای کنترل پروژه بعدی آماده‌اید؟",
    ctaBody: "وارد پلتفرم شوید و از داده پروژه به تصمیم پروژه برسید.",
    lang: "EN",
  },
};

let locale: LandingLocale = "en";

function setLandingDocumentLocale(): void {
  document.documentElement.lang = locale;
  document.documentElement.dir = locale === "fa" ? "rtl" : "ltr";
}

function renderLanding(container: HTMLElement): void {
  const t = copy[locale];
  setLandingDocumentLocale();
  container.innerHTML = `
    <div class="cubi-compact-home" id="home">
      <header class="cubi-compact-header">
        <a class="cubi-compact-brand" href="./" aria-label="CUBI Platform home">
          <img src="./cubi-platform-logo-primary.svg" width="108" height="48" alt="CUBI Platform" />
        </a>
        <nav aria-label="Primary navigation">
          <a href="#home">${t.nav[0]}</a><a href="#capabilities">${t.nav[1]}</a><a href="#capabilities">${t.nav[2]}</a><a href="#resources">${t.nav[3]}</a>
        </nav>
        <div class="cubi-compact-actions">
          <button id="cubi-language" type="button" aria-label="Language selector">${t.lang}</button>
          <a href="./app/" class="cubi-compact-signin">${locale === "fa" ? "ورود" : "Sign In"}</a>
          <a href="./app/" class="cubi-compact-start">${locale === "fa" ? "شروع" : "Get Started"} →</a>
        </div>
      </header>

      <main>
        <section class="cubi-compact-hero" aria-labelledby="cubi-hero-title">
          <div class="cubi-compact-copy">
            <p class="cubi-compact-eyebrow">${t.eyebrow}</p>
            <h1 id="cubi-hero-title">${t.title} <span>${t.titleAccent}</span></h1>
            <h2>${t.sub}</h2>
            <p>${t.body}</p>
            <div class="cubi-compact-hero-actions">
              <a class="cubi-compact-primary" href="./app/">${t.primary}</a>
              <a class="cubi-compact-secondary" href="#capabilities">${t.secondary}</a>
            </div>
          </div>
          <div class="cubi-compact-control" aria-label="Project control dashboard preview">
            <div class="cubi-control-top"><strong>CUBI / Project Control</strong><span>LIVE</span></div>
            <div class="cubi-control-grid">
              <div><small>Schedule</small><b>78%</b><i style="width:78%"></i></div>
              <div><small>Cost Performance</small><b>0.92</b><i style="width:92%"></i></div>
              <div><small>Progress</small><b>84%</b><i style="width:84%"></i></div>
            </div>
            <div class="cubi-control-timeline"><span></span><span></span><span></span><span></span><span></span></div>
            <div class="cubi-control-footer"><span>Planning</span><span>Cost</span><span>Resources</span><span>AI</span></div>
          </div>
        </section>

        <section class="cubi-compact-capabilities" id="capabilities" aria-labelledby="capabilities-title">
          <div class="cubi-compact-section-head"><p class="cubi-compact-eyebrow">CONTROL CENTER</p><h2 id="capabilities-title">${t.capabilities}</h2><p>${t.capabilityBody}</p></div>
          <div class="cubi-compact-grid">
            ${t.cards.map(([title, body, number]) => `<article><span>${number}</span><h3>${title}</h3><p>${body}</p></article>`).join("")}
          </div>
        </section>

        <section class="cubi-compact-cta" id="resources">
          <div><p class="cubi-compact-eyebrow">CUBI PLATFORM</p><h2>${t.cta}</h2><p>${t.ctaBody}</p></div>
          <a class="cubi-compact-primary" href="./app/">${t.primary}</a>
        </section>
      </main>
      <footer class="cubi-compact-footer">
        <img src="./cubi-platform-logo-primary-dark.svg" width="112" height="52" alt="CUBI Platform" />
        <span>Plan. Control. Build Smarter.</span>
        <small>© 2026 CUBI Platform</small>
      </footer>
    </div>`;

  document.getElementById("cubi-language")?.addEventListener("click", () => {
    locale = locale === "en" ? "fa" : "en";
    renderLanding(container);
  });
}

export function renderLandingPage(container: HTMLElement): void {
  renderLanding(container);
}
