// Issue 1241: reference-aligned CUBI commercial homepage, bilingual and responsive.
type LandingLocale = "en" | "fa";

type LandingCopy = {
  navHome: string; navFeatures: string; navSolutions: string; navPricing: string; navResources: string; navAbout: string;
  signIn: string; getStarted: string; eyebrow: string; title: string; titleAccent: string; lead: string;
  watchDemo: string; heroLabel: string; sampleData: string; success: string; progress: string; cost: string; evm: string; ai: string;
  sectionTitle: string; sectionLead: string; workflow: string[]; workflowMeta: string[];
  features: Array<[string,string,string]>;
  techTitle: string; techLead: string; techItems: string[];
  ctaTitle: string; ctaLead: string; trial: string; contact: string;
  footerDescriptor: string; footerTagline: string;
};

const translations: Record<LandingLocale, LandingCopy> = {
  en: {
    navHome:"Home", navFeatures:"Features", navSolutions:"Solutions", navPricing:"Pricing", navResources:"Resources", navAbout:"About",
    signIn:"Sign In", getStarted:"Get Started", eyebrow:"CUBI PLATFORM",
    title:"Construction & Building", titleAccent:"Intelligence",
    lead:"CUBI Platform brings project controls, AI and engineering precision together to help you plan, monitor and deliver construction projects with confidence.",
    watchDemo:"Watch Demo", heroLabel:"CUBI project controls preview — sample data", sampleData:"Sample Data", success:"Live", progress:"Overall Progress", cost:"Cost Performance", evm:"EVM", ai:"AI Assistant",
    sectionTitle:"Everything You Need for Project Success",
    workflow:["PLAN","CONTROL","ANALYZE","BUILD"], workflowMeta:["Schedule","Cost","Progress","Documents","AI"],
    sectionLead:"From planning to closeout, CUBI gives you the tools, insights and control to manage construction projects smarter, faster and safer.",
    features:[
      ["controls","Project Controls","Plan, schedule and track progress with confidence."],
      ["ai","AI Assistant","Get instant insights, answers and recommendations."],
      ["resources","Resources & Cost","Manage budgets, resources and cost performance."],
      ["documents","Documents & Contracts","Centralize documents, contracts, claims and issues."],
      ["collaboration","Collaboration","Work together across your team and stakeholders."],
      ["cloud","Cloud & Scalability","Secure, reliable and built to grow with your needs."]
    ],
    techTitle:"Powered by Leading Technologies",
    techLead:"CUBI integrates proven engineering foundations and modern intelligence to give project teams reliability, visibility and innovation.",
    techItems:["Primavera P6","PostgreSQL","AI & Analytics"],
    ctaTitle:"Ready to Build Smarter?",
    ctaLead:"Join teams using CUBI to bring schedule, cost, progress, documents and intelligence into one control layer.",
    trial:"Start Free Trial", contact:"Contact Sales",
    footerDescriptor:"Construction & Building Intelligence", footerTagline:"Plan. Control. Build Smarter."
  },
  fa: {
    navHome:"خانه", navFeatures:"قابلیت‌ها", navSolutions:"راهکارها", navPricing:"قیمت‌گذاری", navResources:"منابع", navAbout:"درباره ما",
    signIn:"ورود", getStarted:"شروع کنید", eyebrow:"پلتفرم CUBI",
    title:"هوشمندی ساخت و", titleAccent:"ساختمان",
    lead:"پلتفرم CUBI کنترل پروژه، هوش مصنوعی و دقت مهندسی را یکپارچه می‌کند تا پروژه‌های ساخت را با اطمینان برنامه‌ریزی، پایش و تحویل کنید.",
    watchDemo:"مشاهده دمو", heroLabel:"نمایش کنترل پروژه CUBI — داده نمونه", sampleData:"داده نمونه", success:"زنده", progress:"پیشرفت کل", cost:"عملکرد هزینه", evm:"EVM", ai:"دستیار هوشمند",
    sectionTitle:"همه آنچه برای موفقیت پروژه نیاز دارید",
    workflow:["برنامه‌ریزی","کنترل","تحلیل","ساخت"], workflowMeta:["زمان‌بندی","هزینه","پیشرفت","اسناد","هوش مصنوعی"],
    sectionLead:"از برنامه‌ریزی تا اختتام، CUBI ابزار، بینش و کنترل لازم برای مدیریت هوشمندتر، سریع‌تر و مطمئن‌تر پروژه‌های ساخت را فراهم می‌کند.",
    features:[
      ["controls","کنترل پروژه","برنامه‌ریزی، زمان‌بندی و پایش پیشرفت با اطمینان."],
      ["ai","دستیار هوشمند","دریافت سریع بینش، پاسخ و پیشنهادهای کاربردی."],
      ["resources","منابع و هزینه","مدیریت بودجه، منابع و عملکرد هزینه."],
      ["documents","اسناد و قراردادها","تمرکز اسناد، قراردادها، ادعاها و مسائل پروژه."],
      ["collaboration","همکاری","همکاری یکپارچه تیم پروژه و ذی‌نفعان."],
      ["cloud","ابر و مقیاس‌پذیری","امن، قابل اتکا و آماده رشد متناسب با نیاز پروژه."]
    ],
    techTitle:"با فناوری‌های پیشرو",
    techLead:"CUBI زیرساخت‌های مهندسی آزموده‌شده و هوشمندی مدرن را برای قابلیت اتکا، دیدپذیری و نوآوری یکپارچه می‌کند.",
    techItems:["Primavera P6","PostgreSQL","هوش مصنوعی و تحلیل"],
    ctaTitle:"آماده ساخت هوشمندتر هستید؟",
    ctaLead:"با CUBI زمان‌بندی، هزینه، پیشرفت، اسناد و هوشمندی پروژه را در یک لایه کنترل یکپارچه کنید.",
    trial:"شروع آزمایشی رایگان", contact:"تماس با فروش",
    footerDescriptor:"هوشمندی ساخت و ساختمان", footerTagline:"برنامه‌ریزی. کنترل. ساخت هوشمندتر."
  }
};

const featureIcons: Record<string, string> = {
  controls: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z"/></svg>',
  ai: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 2 1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8L12 2Zm7 14 .8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8L19 16Z"/></svg>',
  resources: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 19V10h4v9H4Zm6 0V5h4v14h-4Zm6 0v-7h4v7h-4Z"/></svg>',
  documents: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h9l3 3v15H6V3Zm8 1.5V8h3.5L14 4.5ZM9 12h6M9 15h6M9 18h4"/></svg>',
  collaboration: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm8 1a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM2.5 21a6.5 6.5 0 0 1 13 0h-13Zm10.5 0a6 6 0 0 1 8.5-5.48A6.5 6.5 0 0 1 21.5 21H13Z"/></svg>',
  cloud: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 19a5 5 0 1 1 1.3-9.83A6 6 0 0 1 20 11a4 4 0 0 1 0 8H7Z"/></svg>'
};

function setLandingDocumentLocale(locale: LandingLocale): void {
  document.documentElement.lang = locale;
  document.documentElement.dir = locale === "fa" ? "rtl" : "ltr";
}

function renderLanding(container: HTMLElement, locale: LandingLocale): void {
  const t = translations[locale];
  setLandingDocumentLocale(locale);
  container.innerHTML = `
    <div class="cubi-site" dir="${locale === "fa" ? "rtl" : "ltr"}">
      <header class="cubi-header">
        <a class="cubi-brand" href="/" aria-label="CUBI Platform home">
          <img src="./logo.svg" width="46" height="46" alt="CUBI Platform" />
          <span><strong>CUBI</strong><small>Platform</small></span>
        </a>
        <nav class="cubi-nav" aria-label="Primary navigation">
          <a class="is-active" href="#home">${t.navHome}</a><a href="#features">${t.navFeatures}</a><a href="#solutions">${t.navSolutions}</a><a href="#pricing">${t.navPricing}</a><a href="#resources">${t.navResources}</a><a href="#about">${t.navAbout}</a>
        </nav>
        <div class="cubi-header-actions">
          <button class="cubi-lang-switch" type="button" aria-label="Change language"><span class="cubi-globe" aria-hidden="true">◉</span>EN <span aria-hidden="true">⌄</span></button>
          <a class="cubi-sign-in" href="./app/">${t.signIn}</a>
          <a class="cubi-button cubi-button-small" href="./app/">${t.getStarted} <span>→</span></a>
        </div>
      </header>

      <main>
        <section class="cubi-hero" id="home">
          <div class="cubi-hero-photo" aria-hidden="true"></div>
          <div class="cubi-hero-overlay" aria-hidden="true"></div>
          <div class="cubi-hero-copy">
            <p class="cubi-eyebrow">${t.eyebrow}</p>
            <h1>${t.title}<br><em>${t.titleAccent}</em></h1>
            <p class="cubi-hero-tagline">Plan. Control. Build Smarter.</p>
            <p class="cubi-lead">${t.lead}</p>
            <div class="cubi-hero-actions">
              <a class="cubi-button" href="./app/">${t.getStarted} <span>→</span></a>
              <a class="cubi-demo-link" href="#features"><span class="cubi-play">▶</span>${t.watchDemo}</a>
            </div>
          </div>
          <div class="cubi-hero-product" aria-label="${t.heroLabel}">
            <div class="cubi-product-window">
              <div class="cubi-product-sidebar"><strong>CUBI</strong><span>Dashboard</span><span>Projects</span><span>Schedule</span><span>Cost</span><span>Documents</span><span>Reports</span><span>Settings</span></div>
              <div class="cubi-product-main">
                <div class="cubi-product-heading"><b>Project Schedule</b><span class="cubi-demo-badge">${t.sampleData}</span><span>${t.success}</span></div>
                <div class="cubi-gantt-mini"><i></i><i></i><i></i><i></i><i></i></div>
                <div class="cubi-product-kpis">
                  <div><small>${t.progress}</small><strong>78%</strong><span class="cubi-ring"></span></div>
                  <div><small>${t.cost}</small><strong>0.92</strong><span>On track</span></div>
                  <div><small>${t.evm}</small><strong>0.96</strong><span>Healthy</span></div>
                  <div><small>${t.ai}</small><b class="cubi-product-ai-mark">AI</b><span>Ask anything about your project</span></div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section class="cubi-features-section" id="features">
          <div class="cubi-section-head"><h2>${t.sectionTitle}</h2><p>${t.sectionLead}</p></div>
          <div class="cubi-feature-grid">
            ${t.features.map(([icon,title,body]) => `<article><span class="cubi-feature-icon">${featureIcons[icon] ?? ""}</span><h3>${title}</h3><p>${body}</p></article>`).join("")}
          </div>
        </section>

        <section class="cubi-tech-section" id="solutions">
          <div class="cubi-tech-copy"><span id="resources" aria-hidden="true"></span>
            <p class="cubi-kicker">CUBI ENGINEERING STACK</p><h2>${t.techTitle}</h2><p>${t.techLead}</p>
            <div class="cubi-tech-list">${t.techItems.map(item => `<span>${item}</span>`).join("")}</div>
            <a class="cubi-outline-button" href="./app/">${t.navFeatures} <span>→</span></a>
          </div>
          <div class="cubi-tech-visual" aria-hidden="true"><div class="cubi-stack"><b>◆</b><i></i><i></i><i></i></div><span>Project Controls</span><span>AI &amp; Analytics</span><span>Data &amp; Integration</span><span>Security &amp; Reliability</span></div>
        </section>

        <section class="cubi-cta" id="pricing">
          <div><p class="cubi-kicker">CUBI PLATFORM</p><h2>${t.ctaTitle}</h2><p>${t.ctaLead}</p></div>
          <div class="cubi-cta-actions"><a class="cubi-button" href="./app/">${t.trial} <span>→</span></a><a class="cubi-cta-contact" href="./app/">${t.contact}</a></div>
        </section>
      </main>

      <footer class="cubi-footer" id="about">
        <div class="cubi-footer-brand">
          <div class="cubi-brand"><img src="./logo-dark.svg" width="46" height="46" alt="CUBI Platform" /><span><strong>CUBI</strong><small>Platform</small></span></div>
          <p>${t.footerTagline}</p>
        </div>
        <div class="cubi-footer-links">
          <div><strong>Product</strong><a href="#features">${t.navFeatures}</a><a href="#pricing">${t.navPricing}</a><a href="#solutions">Integrations</a></div>
          <div><strong>Resources</strong><a href="#resources">${t.navResources}</a><a href="#about">Documentation</a><a href="#about">Support</a></div>
          <div><strong>Company</strong><a href="#about">${t.navAbout}</a><a href="#about">Careers</a><a href="#about">Contact</a></div>
        </div>
        <div class="cubi-footer-end">
          <div class="cubi-socials" aria-label="Social links"><a href="#about" aria-label="LinkedIn">in</a><a href="#about" aria-label="X">𝕏</a><a href="#about" aria-label="YouTube">▶</a><a href="#about" aria-label="GitHub">◉</a></div>
          <small>© 2026 CUBI Platform. All rights reserved.</small>
        </div>
      </footer>
    </div>`;

  container.querySelector<HTMLButtonElement>(".cubi-lang-switch")?.addEventListener("click", () => {
    const next: LandingLocale = locale === "fa" ? "en" : "fa";
    const y = window.scrollY;
    renderLanding(container, next);
    window.scrollTo({ top:y, behavior:"auto" });
  });
}

export function renderLandingPage(container: HTMLElement): void {
  renderLanding(container, "en");
}
