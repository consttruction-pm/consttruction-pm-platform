type LandingLocale = "en" | "fa";
type Feature = { icon: string; title: string; body: string };
type LandingCopy = {
  nav: string[]; eyebrow: string; title: string; accent: string; subtitle: string; body: string;
  primary: string; secondary: string; featuresTitle: string; featuresBody: string; features: Feature[];
  techTitle: string; techBody: string; techLink: string; techNodes: string[];
  ctaTitle: string; ctaBody: string; signIn: string; start: string; language: string;
  footerColumns: Array<{ title: string; links: string[] }>; footerNote: string;
};
const copy: Record<LandingLocale, LandingCopy> = {
  en: {
    nav: ["Home", "Platform", "Solutions", "Resources"],
    eyebrow: "CONSTRUCTION & BUILDING INTELLIGENCE",
    title: "Control every detail.", accent: "Build with confidence.",
    subtitle: "Plan. Control. Build Smarter.",
    body: "Bring schedules, cost, progress, resources and project evidence into one clear control room—so your team can make the next decision with confidence.",
    primary: "Explore the Platform →", secondary: "See How It Works",
    featuresTitle: "Everything your project needs to stay in control",
    featuresBody: "Connect the work, the numbers and the evidence in one practical workspace built for construction teams.",
    features: [
      { icon: "⌁", title: "Project Controls", body: "Track milestones, progress and performance signals in one project view." },
      { icon: "✧", title: "AI Assistant", body: "Turn project information into useful summaries, questions and next steps." },
      { icon: "↗", title: "Resources & Cost", body: "Connect resource plans, cost visibility and delivery performance." },
      { icon: "▤", title: "Documents & Contracts", body: "Keep project records and supporting evidence close to the workflow." },
      { icon: "◎", title: "Team Collaboration", body: "Give stakeholders a shared view of project status and actions." },
      { icon: "☁", title: "Cloud & Scalability", body: "Access a consistent project workspace as teams and projects grow." }
    ],
    techTitle: "A connected foundation for better decisions",
    techBody: "CUBI brings project planning, controls, information and intelligent assistance together while keeping the project workflow at the center.",
    techLink: "Explore platform capabilities →",
    techNodes: ["Project controls", "AI assistance", "Connected data", "Secure workflow"],
    ctaTitle: "Bring your project into focus.",
    ctaBody: "Start with one connected view of schedules, costs, progress and decisions.",
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
    featuresTitle: "همه آنچه پروژه برای کنترل بهتر نیاز دارد",
    featuresBody: "کارها، اعداد و مستندات پروژه را در یک فضای کاری کاربردی برای تیم‌های ساخت به هم متصل کنید.",
    features: [
      { icon: "⌁", title: "کنترل پروژه", body: "نقاط عطف، پیشرفت و شاخص‌های عملکرد را در یک نمای پروژه دنبال کنید." },
      { icon: "✧", title: "دستیار هوشمند", body: "اطلاعات پروژه را به خلاصه‌ها، پرسش‌ها و گام‌های بعدی مفید تبدیل کنید." },
      { icon: "↗", title: "منابع و هزینه", body: "برنامه منابع، شفافیت هزینه و عملکرد اجرا را به هم متصل کنید." },
      { icon: "▤", title: "اسناد و قراردادها", body: "سوابق و شواهد پشتیبان پروژه را در کنار جریان کار نگه دارید." },
      { icon: "◎", title: "همکاری تیمی", body: "نمای مشترک و روشنی از وضعیت پروژه و اقدامات در اختیار ذی‌نفعان قرار دهید." },
      { icon: "☁", title: "ابر و توسعه‌پذیری", body: "با رشد تیم‌ها و پروژه‌ها به فضای کاری یکپارچه دسترسی داشته باشید." }
    ],
    techTitle: "زیرساختی یکپارچه برای تصمیم‌های بهتر",
    techBody: "کوبی برنامه‌ریزی، کنترل پروژه، اطلاعات و دستیار هوشمند را کنار هم قرار می‌دهد و جریان کاری پروژه را در مرکز نگه می‌دارد.",
    techLink: "مشاهده قابلیت‌های پلتفرم ←",
    techNodes: ["کنترل پروژه", "دستیار هوشمند", "داده یکپارچه", "جریان کاری امن"],
    ctaTitle: "تصویر روشنی از پروژه بسازید.",
    ctaBody: "با نمایی یکپارچه از زمان‌بندی، هزینه، پیشرفت و تصمیم‌ها شروع کنید.",
    signIn: "ورود", start: "شروع کنید", language: "EN",
    footerColumns: [
      { title: "پلتفرم", links: ["کنترل پروژه", "برنامه‌ریزی و زمان‌بندی", "منابع و هزینه"] },
      { title: "راهکارها", links: ["تیم‌های ساخت", "مدیریت پروژه", "تحویل پروژه"] },
      { title: "منابع", links: ["مستندات", "معرفی محصول", "تماس"] }
    ],
    footerNote: "برنامه‌ریزی. کنترل. ساخت هوشمندتر."
  }
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
    <div class="cubi-reference-home cubi-exact-home" id="home">
      <header class="cubi-exact-header">
        <a class="cubi-exact-brand" href="./" aria-label="CUBI Platform home"><img src="./cubi-platform-logo-primary.svg" width="108" height="48" alt="CUBI Platform" /></a>
        <nav class="cubi-exact-nav" aria-label="Primary navigation">
          <a class="is-active" href="#home">${t.nav[0]}</a><a href="#capabilities">${t.nav[1]}</a><a href="#technology">${t.nav[2]}</a><a href="#resources">${t.nav[3]}</a>
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
            <aside class="cubi-dash-sidebar"><img src="./cubi-platform-logo-primary-dark.svg" width="26" height="26" alt="" /><strong>CUBI</strong><span>Overview</span><span>Schedule</span><span>Cost control</span><span>Resources</span><span>Documents</span></aside>
            <div class="cubi-dash-main"><div class="cubi-dash-title"><strong>Project Control Center</strong><span>PROJECT / 026</span></div>
              <div class="cubi-gantt" aria-hidden="true"><i style="width:76%"></i><i style="width:58%"></i><i style="width:82%"></i><i style="width:49%"></i><i style="width:67%"></i><i style="width:38%"></i></div>
              <div class="cubi-dash-bottom"><div class="cubi-mini-chart"><b>Progress trend</b><div class="cubi-line-chart"></div></div><div class="cubi-ring-card"><b>Schedule</b><div class="cubi-ring"><strong>78%</strong></div><small>On track</small></div><div class="cubi-ai-card"><b>AI insight</b><div class="cubi-ai-bubble" aria-hidden="true">✧</div><small>Review next milestone</small></div></div>
            </div>
            <aside class="cubi-progress-card"><div class="cubi-progress-ring"><strong>84%</strong></div><b>Project progress</b><div><span>Plan</span><span>Actual</span></div></aside>
          </div>
        </section>
        <section class="cubi-exact-features" id="capabilities">
          <div class="cubi-exact-section-head"><p class="cubi-kicker">ONE CONNECTED WORKFLOW</p><h2>${t.featuresTitle}</h2><p>${t.featuresBody}</p></div>
          <div class="cubi-exact-feature-grid">${t.features.map((f) => `<article><div class="cubi-feature-icon" aria-hidden="true">${f.icon}</div><h3>${f.title}</h3><p>${f.body}</p></article>`).join("")}</div>
        </section>
        <section class="cubi-exact-tech" id="technology" aria-labelledby="cubi-tech-title">
          <div class="cubi-tech-copy"><p class="cubi-kicker">BUILT FOR REAL PROJECTS</p><h2 id="cubi-tech-title">${t.techTitle}</h2><p>${t.techBody}</p>
            <div class="cubi-tech-badges" aria-label="Platform building blocks"><b class="plan">PL</b><span>Planning</span><b class="pg">▦</b><span>Project data</span><b class="ai">✧</b><span>AI</span></div>
            <a class="cubi-exact-outline" href="./app/">${t.techLink}</a>
          </div>
          <div class="cubi-tech-diagram" aria-label="Connected platform capabilities"><div class="cubi-stack" aria-hidden="true"><i></i><i></i><i></i><b>C</b></div>
            <div class="cubi-tech-node n1"><span>${t.techNodes[0]}</span></div><div class="cubi-tech-node n2"><span>${t.techNodes[1]}</span></div><div class="cubi-tech-node n3"><span>${t.techNodes[2]}</span></div><div class="cubi-tech-node n4"><span>${t.techNodes[3]}</span></div>
          </div>
        </section>
        <section class="cubi-exact-cta" id="resources"><div><h2>${t.ctaTitle}</h2><p>${t.ctaBody}</p></div><div class="cubi-cta-actions"><a class="cubi-exact-primary" href="./app/">${t.primary}</a><a class="cubi-exact-demo" href="#capabilities">${t.secondary}</a></div></section>
      </main>
      <footer class="cubi-exact-footer">
        <div class="cubi-footer-brand"><img src="./cubi-platform-logo-primary-dark.svg" width="112" height="52" alt="CUBI Platform" /><small>${t.footerNote}</small></div>
        ${t.footerColumns.map((col) => `<div class="cubi-footer-col"><b>${col.title}</b>${col.links.map((link) => `<a href="#resources">${link}</a>`).join("")}</div>`).join("")}
        <div class="cubi-footer-social"><span aria-label="CUBI Platform">CUBI</span><small>© 2026 CUBI Platform. All rights reserved.</small></div>
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
