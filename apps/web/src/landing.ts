type LandingLocale = "en" | "fa";

type LandingCopy = {
  navProduct: string;
  navControls: string;
  navCapabilities: string;
  languageLabel: string;
  open: string;
  eyebrow: string;
  title: string;
  titleAccent: string;
  lead: string;
  primaryCta: string;
  secondaryCta: string;
  tagline: string;
  visualLabel: string;
  live: string;
  schedule: string;
  cost: string;
  wbs: string;
  activities: string;
  baseline: string;
  progress: string;
  aiInsight: string;
  capabilitiesKicker: string;
  capabilitiesTitle: string;
  capabilitiesLead: string;
  controlsKicker: string;
  controlsTitle: string;
  controlsLead: string;
  controlItems: string[];
  signals: string;
  priority: string;
  footerTagline: string;
  footerDescriptor: string;
  features: Array<[string, string, string]>;
};

const translations: Record<LandingLocale, LandingCopy> = {
  en: {
    navProduct: "Product",
    navControls: "Controls",
    navCapabilities: "Capabilities",
    languageLabel: "فا",
    open: "Open Platform",
    eyebrow: "Construction & Building Intelligence",
    title: "Construction Project Control,",
    titleAccent: "Reimagined.",
    lead: "CUBI brings planning, scheduling, project controls, cost, progress, resources, documents and AI assistance into one professional control layer.",
    primaryCta: "Explore CUBI",
    secondaryCta: "See capabilities",
    tagline: "Plan. Control. Build Smarter.",
    visualLabel: "CUBI project control preview",
    live: "Live",
    schedule: "Schedule Health",
    cost: "Cost Performance",
    wbs: "WBS",
    activities: "Activities",
    baseline: "Baseline",
    progress: "Progress",
    aiInsight: "AI insight",
    capabilitiesKicker: "CORE CAPABILITIES",
    capabilitiesTitle: "The control layer for complex construction delivery.",
    capabilitiesLead: "The essentials are visible quickly, without turning the homepage into a long marketing catalogue.",
    controlsKicker: "PROJECT CONTROLS",
    controlsTitle: "One view of schedule, progress, cost and performance.",
    controlsLead: "CUBI connects the signals that project teams use to understand where delivery stands and where attention is needed.",
    controlItems: [
      "Schedule and baseline visibility",
      "Progress and performance signals",
      "Cost, resources and EVM context",
      "Documents, contracts and issues"
    ],
    signals: "CONTROL SIGNALS",
    priority: "3 priority insights ready for review",
    footerTagline: "Plan. Control. Build Smarter.",
    footerDescriptor: "Construction & Building Intelligence",
    features: [
      ["⌁", "Planning & Scheduling", "CPM logic, WBS, activities, baselines and schedule analysis."],
      ["◈", "Project Controls", "A shared control view for schedule, cost, progress and performance."],
      ["◒", "Cost, Progress & EVM", "Performance context that keeps delivery and commercial signals connected."],
      ["◎", "Resources", "Resource demand and delivery capacity in the same project picture."],
      ["▤", "Documents & Contracts", "Project records, contracts, claims and issues connected to the work."],
      ["✦", "AI Assistant", "Focused project insights that support decisions without replacing engineering judgment."]
    ]
  },
  fa: {
    navProduct: "محصول",
    navControls: "کنترل پروژه",
    navCapabilities: "قابلیت‌ها",
    languageLabel: "EN",
    open: "ورود به پلتفرم",
    eyebrow: "هوشمندی ساخت و ساختمان",
    title: "کنترل پروژه‌های ساخت،",
    titleAccent: "بازطراحی‌شده.",
    lead: "CUBI برنامه‌ریزی، زمان‌بندی، کنترل پروژه، هزینه، پیشرفت، منابع، اسناد و دستیار هوشمند را در یک لایه حرفه‌ای کنترل پروژه یکپارچه می‌کند.",
    primaryCta: "ورود به CUBI",
    secondaryCta: "مشاهده قابلیت‌ها",
    tagline: "برنامه‌ریزی. کنترل. ساخت هوشمندتر.",
    visualLabel: "نمایش کنترل پروژه CUBI",
    live: "زنده",
    schedule: "سلامت زمان‌بندی",
    cost: "عملکرد هزینه",
    wbs: "ساختار شکست کار",
    activities: "فعالیت‌ها",
    baseline: "خط مبنا",
    progress: "پیشرفت",
    aiInsight: "بینش هوشمند",
    capabilitiesKicker: "قابلیت‌های اصلی",
    capabilitiesTitle: "لایه کنترل برای پروژه‌های پیچیده ساخت.",
    capabilitiesLead: "قابلیت‌های ضروری سریع دیده می‌شوند، بدون اینکه صفحه اول به یک صفحه بازاریابی طولانی تبدیل شود.",
    controlsKicker: "کنترل پروژه",
    controlsTitle: "یک نمای واحد از زمان‌بندی، پیشرفت، هزینه و عملکرد.",
    controlsLead: "CUBI سیگنال‌هایی را که تیم پروژه برای درک وضعیت اجرا و نقاط نیازمند توجه استفاده می‌کند، به هم متصل می‌کند.",
    controlItems: [
      "دید یکپارچه زمان‌بندی و خط مبنا",
      "سیگنال‌های پیشرفت و عملکرد",
      "زمینه هزینه، منابع و EVM",
      "اسناد، قراردادها و مسائل پروژه"
    ],
    signals: "سیگنال‌های کنترل",
    priority: "۳ بینش اولویت‌دار آماده بررسی است",
    footerTagline: "برنامه‌ریزی. کنترل. ساخت هوشمندتر.",
    footerDescriptor: "هوشمندی ساخت و ساختمان",
    features: [
      ["⌁", "برنامه‌ریزی و زمان‌بندی", "منطق CPM، ساختار شکست کار، فعالیت‌ها، خط مبنا و تحلیل زمان‌بندی."],
      ["◈", "کنترل پروژه", "نمای واحد برای زمان‌بندی، هزینه، پیشرفت و عملکرد."],
      ["◒", "هزینه، پیشرفت و EVM", "زمینه عملکردی یکپارچه برای سیگنال‌های اجرایی و تجاری."],
      ["◎", "منابع", "تقاضای منابع و ظرفیت اجرا در یک تصویر واحد از پروژه."],
      ["▤", "اسناد و قراردادها", "اسناد، قراردادها، ادعاها و مسائل متصل به فعالیت‌های پروژه."],
      ["✦", "دستیار هوشمند", "بینش‌های متمرکز پروژه برای پشتیبانی از تصمیم‌گیری، بدون جایگزینی قضاوت مهندسی."]
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
    <div class="cubi-site" dir="${locale === "fa" ? "rtl" : "ltr}">
      <header class="cubi-header">
        <a class="cubi-brand" href="/" aria-label="CUBI Platform home">
          <img src="/logo.svg" width="42" height="42" alt="" />
          <span><strong>CUBI</strong><small>Platform</small></span>
        </a>
        <nav class="cubi-nav" aria-label="${t.navProduct}">
          <a href="#product">${t.navProduct}</a>
          <a href="#controls">${t.navControls}</a>
          <a href="#capabilities">${t.navCapabilities}</a>
        </nav>
        <div class="cubi-header-actions">
          <button class="cubi-lang-switch" type="button" aria-label="${locale === "fa" ? "Switch to English" : "تغییر به فارسی"}">${t.languageLabel}</button>
          <a class="cubi-button cubi-button-small" href="/app">${t.open}</a>
        </div>
      </header>

      <main>
        <section class="cubi-hero" id="product">
          <div class="cubi-hero-copy">
            <p class="cubi-eyebrow"><span></span> ${t.eyebrow}</p>
            <h1>${t.title} <em>${t.titleAccent}</em></h1>
            <p class="cubi-lead">${t.lead}</p>
            <div class="cubi-hero-actions">
              <a class="cubi-button" href="/app">${t.primaryCta} <span aria-hidden="true">→</span></a>
              <a class="cubi-text-link" href="#capabilities">${t.secondaryCta}</a>
            </div>
            <p class="cubi-tagline">${t.tagline}</p>
          </div>

          <div class="cubi-hero-visual" aria-label="${t.visualLabel}">
            <div class="cubi-grid-glow"></div>
            <div class="cubi-dashboard">
              <div class="cubi-dash-top"><span class="cubi-dot"></span><span>CUBI CONTROL CENTER</span><b>${t.live}</b></div>
              <div class="cubi-dash-body">
                <div class="cubi-metric"><small>${t.schedule}</small><strong>92%</strong><span>+4.8%</span></div>
                <div class="cubi-metric"><small>${t.cost}</small><strong>0.96</strong><span>On track</span></div>
                <div class="cubi-chart"><div class="cubi-bars"><i style="height:38%"></i><i style="height:55%"></i><i style="height:48%"></i><i style="height:72%"></i><i style="height:64%"></i><i style="height:88%"></i><i style="height:78%"></i></div><div class="cubi-line"><span></span></div></div>
              </div>
              <div class="cubi-timeline"><span>${t.wbs}</span><span>${t.activities}</span><span>${t.baseline}</span><span>${t.progress}</span><b>${t.aiInsight}</b></div>
            </div>
            <div class="cubi-orbit"><img src="/logo.svg" alt="" /></div>
          </div>
        </section>

        <section class="cubi-section cubi-compact-section" id="capabilities">
          <div class="cubi-section-head">
            <p class="cubi-kicker">${t.capabilitiesKicker}</p>
            <h2>${t.capabilitiesTitle}</h2>
            <p>${t.capabilitiesLead}</p>
          </div>
          <div class="cubi-feature-grid">
            ${t.features.map(([icon, title, body]) => `
              <article><span class="cubi-icon">${icon}</span><h3>${title}</h3><p>${body}</p></article>
            `).join("")}
          </div>
        </section>

        <section class="cubi-control-section cubi-compact-section" id="controls">
          <div class="cubi-control-copy">
            <p class="cubi-kicker">${t.controlsKicker}</p>
            <h2>${t.controlsTitle}</h2>
            <p>${t.controlsLead}</p>
            <ul>${t.controlItems.map(item => `<li>${item}</li>`).join("")}</ul>
            <a class="cubi-text-link" href="/app">${t.primaryCta} →</a>
          </div>
          <div class="cubi-control-card">
            <div class="cubi-card-label">${t.signals}</div>
            <div class="cubi-signal"><span>${t.schedule}</span><b>92</b><i></i></div>
            <div class="cubi-signal"><span>${t.progress}</span><b>78</b><i></i></div>
            <div class="cubi-signal"><span>${t.cost}</span><b>96</b><i></i></div>
            <div class="cubi-signal"><span>${t.aiInsight}</span><b>14</b><i></i></div>
            <div class="cubi-mini-note"><span>AI</span> ${t.priority}</div>
          </div>
        </section>
      </main>

      <footer class="cubi-footer">
        <div class="cubi-brand"><img src="/logo-dark.svg" width="40" height="40" alt="" /><span><strong>CUBI</strong><small>Platform</small></span></div>
        <p>${t.footerTagline}</p><span>${t.footerDescriptor}</span>
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
