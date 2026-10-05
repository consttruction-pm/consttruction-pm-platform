// CUBI commercial homepage — aligned to canonical Issue #1101 reference handoff.
type LandingLocale = "en" | "fa";

type LandingCopy = {
  navHome: string; navFeatures: string; navSolutions: string; navPricing: string; navResources: string; navAbout: string;
  languageLabel: string; open: string; eyebrow: string; title: string; titleAccent: string; lead: string;
  primaryCta: string; secondaryCta: string; tagline: string; visualLabel: string; demo: string;
  schedule: string; cost: string; progress: string; wbs: string; activities: string; baseline: string; aiInsight: string;
  capabilitiesTitle: string; capabilitiesLead: string; solutionsTitle: string; solutionsLead: string;
  solutionItems: string[]; techTitle: string; techLead: string; pricingTitle: string; pricingLead: string; aboutTitle: string;
  footerDescriptor: string; features: Array<[string, string, string]>;
};

const translations: Record<LandingLocale, LandingCopy> = {
  en: {
    navHome: "Home", navFeatures: "Features", navSolutions: "Solutions", navPricing: "Pricing", navResources: "Resources", navAbout: "About",
    languageLabel: "فا", open: "Open Platform", eyebrow: "CUBI PLATFORM",
    title: "Construction &", titleAccent: "Building Intelligence",
    lead: "Project controls, AI and engineering precision in one professional platform for planning, scheduling, cost, progress, resources and project information.",
    primaryCta: "Explore CUBI", secondaryCta: "View capabilities", tagline: "Plan. Control. Build Smarter.", visualLabel: "CUBI project control dashboard preview", demo: "DEMO",
    schedule: "Schedule Health", cost: "Cost Performance", progress: "Progress", wbs: "WBS", activities: "Activities", baseline: "Baseline", aiInsight: "AI Assistant",
    capabilitiesTitle: "Everything You Need for Project Success",
    capabilitiesLead: "A focused control layer that keeps schedule, cost, resources, documents and intelligence connected.",
    solutionsTitle: "Built around the way construction teams control delivery",
    solutionsLead: "CUBI connects the project model to the information teams use every day, without duplicating engineering calculation logic.",
    solutionItems: ["Planning & Scheduling", "Project Controls", "Progress & EVM", "Resources & Cost", "Documents & Contracts", "AI & Collaboration"],
    techTitle: "Powered by Leading Technologies",
    techLead: "CPM / P6 • PostgreSQL • AI • Data Integration • Security & Reliability",
    pricingTitle: "Ready to Build Smarter?",
    pricingLead: "Start with the CUBI workspace and scale across web, desktop and mobile as your control needs grow.",
    aboutTitle: "Construction & Building Intelligence", footerDescriptor: "Project Controls • AI & Intelligence • Engineering Precision",
    features: [
      ["◈", "Project Controls", "Schedule, baseline, progress and performance signals in one control picture."],
      ["✦", "AI Assistant", "Context-aware guidance and insight that supports decisions without replacing engineering judgment."],
      ["◒", "Resources & Cost", "Resource demand, cost context and EVM signals connected to the project model."],
      ["▤", "Documents & Contracts", "Contracts, drawings, RFIs, submittals, claims and evidence connected to project work."],
      ["◎", "Collaboration", "A shared project view across disciplines, records, decisions and delivery workflows."]
    ]
  },
  fa: {
    navHome: "خانه", navFeatures: "قابلیت‌ها", navSolutions: "راهکارها", navPricing: "قیمت‌گذاری", navResources: "منابع", navAbout: "درباره",
    languageLabel: "EN", open: "ورود به پلتفرم", eyebrow: "پلتفرم CUBI",
    title: "هوشمندی", titleAccent: "ساخت و ساختمان",
    lead: "کنترل پروژه، هوش مصنوعی و دقت مهندسی در یک پلتفرم حرفه‌ای برای برنامه‌ریزی، زمان‌بندی، هزینه، پیشرفت، منابع و اطلاعات پروژه.",
    primaryCta: "ورود به CUBI", secondaryCta: "مشاهده قابلیت‌ها", tagline: "برنامه‌ریزی. کنترل. ساخت هوشمندتر.", visualLabel: "پیش‌نمایش داشبورد کنترل پروژه CUBI", demo: "نمونه",
    schedule: "سلامت زمان‌بندی", cost: "عملکرد هزینه", progress: "پیشرفت", wbs: "ساختار شکست کار", activities: "فعالیت‌ها", baseline: "خط مبنا", aiInsight: "دستیار هوشمند",
    capabilitiesTitle: "همه آنچه برای موفقیت پروژه نیاز دارید",
    capabilitiesLead: "یک لایه کنترل متمرکز که زمان‌بندی، هزینه، منابع، اسناد و هوشمندی را به هم متصل می‌کند.",
    solutionsTitle: "بر اساس شیوه واقعی کنترل پروژه‌های ساخت",
    solutionsLead: "CUBI مدل پروژه را به اطلاعاتی که تیم‌ها هر روز استفاده می‌کنند متصل می‌کند، بدون تکرار منطق محاسبات مهندسی.",
    solutionItems: ["برنامه‌ریزی و زمان‌بندی", "کنترل پروژه", "پیشرفت و EVM", "منابع و هزینه", "اسناد و قراردادها", "هوش مصنوعی و همکاری"],
    techTitle: "مبتنی بر فناوری‌های پیشرو",
    techLead: "CPM / P6 • PostgreSQL • AI • یکپارچه‌سازی داده • امنیت و قابلیت اطمینان",
    pricingTitle: "آماده ساخت هوشمندتر هستید؟",
    pricingLead: "با فضای کاری CUBI شروع کنید و با رشد نیازهای کنترل پروژه، در وب، دسکتاپ و موبایل مقیاس دهید.",
    aboutTitle: "هوشمندی ساخت و ساختمان", footerDescriptor: "کنترل پروژه • هوش مصنوعی و Intelligence • دقت مهندسی",
    features: [
      ["◈", "کنترل پروژه", "زمان‌بندی، خط مبنا، پیشرفت و سیگنال‌های عملکرد در یک نمای واحد."],
      ["✦", "دستیار هوشمند", "راهنمایی و بینش متکی بر context پروژه، بدون جایگزینی قضاوت مهندسی."],
      ["◒", "منابع و هزینه", "تقاضای منابع، زمینه هزینه و سیگنال‌های EVM متصل به مدل پروژه."],
      ["▤", "اسناد و قراردادها", "قرارداد، نقشه، RFI، Submittal، Claim و شواهد متصل به کار پروژه."],
      ["◎", "همکاری", "نمای مشترک پروژه برای رشته‌ها، سوابق، تصمیمات و جریان‌های اجرایی."]
    ]
  }
};

function setLandingDocumentLocale(locale: LandingLocale): void {
  document.documentElement.lang = locale;
  document.documentElement.dir = locale === "fa" ? "rtl" : "ltr";
}

function renderLanding(container: HTMLElement, locale: LandingLocale): void {
  const t = translations[locale];
  setLandingDocumentLocale(locale);
  container.innerHTML = `
    <div class="cubi-site cubi-reference-home" dir="${locale === "fa" ? "rtl" : "ltr"}" id="home">
      <header class="cubi-reference-header">
        <a class="cubi-reference-brand" href="/" aria-label="CUBI Platform home">
          <img src="/logo.svg" width="44" height="44" alt="" />
          <span><strong>CUBI</strong><small>Platform</small></span>
        </a>
        <nav class="cubi-reference-nav" aria-label="Primary navigation">
          <a href="#home">${t.navHome}</a><a href="#features">${t.navFeatures}</a><a href="#solutions">${t.navSolutions}</a><a href="#pricing">${t.navPricing}</a><a href="#resources">${t.navResources}</a><a href="#about">${t.navAbout}</a>
        </nav>
        <div class="cubi-reference-actions">
          <button class="cubi-lang-switch" type="button" aria-label="${locale === "fa" ? "Switch to English" : "تغییر به فارسی"}">${t.languageLabel}</button>
          <a class="cubi-reference-cta cubi-reference-cta-small" href="/app">${t.open}</a>
        </div>
      </header>

      <main>
        <section class="cubi-reference-hero">
          <div class="cubi-reference-hero-copy">
            <p class="cubi-reference-eyebrow"><span></span>${t.eyebrow}</p>
            <h1>${t.title} <em>${t.titleAccent}</em></h1>
            <p class="cubi-reference-lead">${t.lead}</p>
            <p class="cubi-reference-tagline">${t.tagline}</p>
            <div class="cubi-reference-actions-row">
              <a class="cubi-reference-cta" href="/app">${t.primaryCta} <span aria-hidden="true">→</span></a>
              <a class="cubi-reference-text-link" href="#features">${t.secondaryCta}</a>
            </div>
          </div>
          <div class="cubi-reference-dashboard-wrap" aria-label="${t.visualLabel}">
            <div class="cubi-reference-dashboard">
              <div class="cubi-ref-dash-head"><strong>CUBI CONTROL CENTER</strong><span>${t.demo}</span></div>
              <div class="cubi-ref-dash-toolbar"><i></i><i></i><i></i><b>Project Controls</b></div>
              <div class="cubi-ref-dash-grid">
                <article><small>${t.schedule}</small><strong>92%</strong><span>+4.8%</span></article>
                <article><small>${t.cost}</small><strong>0.96</strong><span>${t.demo}</span></article>
                <article class="cubi-ref-chart" aria-hidden="true"><div><i style="height:42%"></i><i style="height:64%"></i><i style="height:51%"></i><i style="height:76%"></i><i style="height:68%"></i><i style="height:88%"></i></div><span></span></article>
                <article class="cubi-ref-table"><small>${t.wbs}</small><div><span>${t.activities}</span><b>124</b></div><div><span>${t.baseline}</span><b>v3.1</b></div><div><span>${t.progress}</span><b>78%</b></div></article>
              </div>
              <div class="cubi-ref-ai"><span>AI</span><strong>${t.aiInsight}</strong><small>${t.demo}</small></div>
            </div>
            <div class="cubi-reference-orbit"><img src="/logo-dark.svg" width="78" height="78" alt="" /></div>
          </div>
        </section>

        <section class="cubi-reference-section cubi-reference-features" id="features">
          <div class="cubi-reference-section-head"><p class="cubi-reference-kicker">CORE CAPABILITIES</p><h2>${t.capabilitiesTitle}</h2><p>${t.capabilitiesLead}</p></div>
          <div class="cubi-reference-feature-grid">${t.features.map(([icon,title,body]) => `<article><span class="cubi-reference-icon">${icon}</span><h3>${title}</h3><p>${body}</p></article>`).join("")}</div>
        </section>

        <section class="cubi-reference-solutions" id="solutions">
          <div><p class="cubi-reference-kicker">CONTROL SYSTEM</p><h2>${t.solutionsTitle}</h2><p>${t.solutionsLead}</p></div>
          <div class="cubi-reference-solution-list">${t.solutionItems.map(item => `<span>${item}</span>`).join("")}</div>
        </section>

        <section class="cubi-reference-tech" id="resources">
          <p class="cubi-reference-kicker">TECHNOLOGY</p><h2>${t.techTitle}</h2><p>${t.techLead}</p>
        </section>

        <section class="cubi-reference-pricing" id="pricing">
          <p class="cubi-reference-kicker">CUBI PLATFORM</p><h2>${t.pricingTitle}</h2><p>${t.pricingLead}</p><a class="cubi-reference-cta" href="/app">${t.primaryCta} <span aria-hidden="true">→</span></a>
        </section>
      </main>

      <footer class="cubi-reference-footer" id="about">
        <div class="cubi-reference-brand"><img src="/logo-dark.svg" width="42" height="42" alt="" /><span><strong>CUBI</strong><small>Platform</small></span></div>
        <div><strong>${t.aboutTitle}</strong><span>${t.footerDescriptor}</span></div>
        <p>${t.tagline}</p>
      </footer>
    </div>`;

  const switcher = container.querySelector<HTMLButtonElement>(".cubi-lang-switch");
  switcher?.addEventListener("click", () => {
    const next: LandingLocale = locale === "fa" ? "en" : "fa";
    const scrollY = window.scrollY;
    renderLanding(container, next);
    window.scrollTo({ top: scrollY, behavior: "auto" });
  });
}

export function renderLandingPage(container: HTMLElement): void {
  renderLanding(container, "en");
}
