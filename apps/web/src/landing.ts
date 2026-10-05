// CUBI commercial homepage — aligned to canonical design references in docs/cubi.
// Presentation layer only.

type LandingLocale = "en" | "fa";
type LandingCopy = {
  navHome:string; navFeatures:string; navSolutions:string; navPricing:string; navAi:string; navResources:string;
  language:string; open:string; eyebrow:string; title:string; titleAccent:string; lead:string; tagline:string; cta:string; secondary:string;
  dashboard:string; demo:string; schedule:string; progress:string; cost:string; activities:string; baseline:string; aiInsight:string;
  featuresKicker:string; featuresTitle:string; featuresLead:string; features:Array<[string,string,string]>;
  techKicker:string; techTitle:string; techLead:string; aiTitle:string; aiLead:string; aiItems:string[];
  pricingKicker:string; pricingTitle:string; pricingLead:string; pricingCta:string; footer:string;
};
const translations:Record<LandingLocale,LandingCopy>={
  en:{
    navHome:"Home",navFeatures:"Features",navSolutions:"Solutions",navPricing:"Pricing",navAi:"AI",navResources:"Resources",
    language:"فا",open:"Open Platform",eyebrow:"CUBI PLATFORM",title:"Construction Project Control,",titleAccent:"Reimagined.",
    lead:"Professional project controls, scheduling, cost, progress, resources, documents and AI assistance — designed around the way construction teams actually work.",
    tagline:"Plan. Control. Build Smarter.",cta:"Explore CUBI",secondary:"See capabilities",
    dashboard:"CUBI CONTROL CENTER",demo:"DEMO",schedule:"Schedule Health",progress:"Progress",cost:"Cost Performance",
    activities:"Activities",baseline:"Baseline",aiInsight:"AI Insight",
    featuresKicker:"CORE CAPABILITIES",featuresTitle:"Everything you need for project success.",
    featuresLead:"A single control layer connecting the planning model, field information and commercial performance.",
    features:[
      ["⌁","Project Controls","Schedule, baseline, progress and performance in one operating picture."],
      ["✦","AI Assistant","Context-aware assistance for analysis, guidance and next actions."],
      ["◒","Resources & Cost","Resource demand, cost and EVM signals connected to delivery."],
      ["▤","Documents & Contracts","Contracts, drawings, RFI, submittals, claims and evidence."],
      ["◎","Collaboration","Shared project context for teams, reviews, approvals and traceability."],
      ["◈","Cloud & Scalability","Web-ready architecture built to extend across desktop and mobile."]
    ],
    techKicker:"ENGINEERING FOUNDATION",techTitle:"Powered by the project model, not around it.",
    techLead:"CPM-aligned scheduling semantics, PostgreSQL, AI, data integration and security — with one shared engineering core.",
    aiTitle:"AI assistance that respects the project model.",
    aiLead:"Surface anomalies, explain control signals and suggest the next action without silently changing authoritative project data.",
    aiItems:["Schedule intelligence","Document intelligence","Report & KPI assistance"],
    pricingKicker:"CUBI PLATFORM",pricingTitle:"Ready to build smarter?",pricingLead:"Start with the control layer and grow into the full construction intelligence platform.",pricingCta:"Enter CUBI Platform",
    footer:"Construction & Building Intelligence"
  },
  fa:{
    navHome:"خانه",navFeatures:"قابلیت‌ها",navSolutions:"راهکارها",navPricing:"قیمت‌گذاری",navAi:"هوش مصنوعی",navResources:"منابع",
    language:"EN",open:"ورود به پلتفرم",eyebrow:"پلتفرم CUBI",title:"هوشمندی ساخت و",titleAccent:"کنترل پروژه",
    lead:"کنترل پروژه، زمان‌بندی، هزینه، پیشرفت، منابع، اسناد و دستیار هوشمند در یک لایه حرفه‌ای؛ متناسب با واقعیت اجرای پروژه‌های ساخت.",
    tagline:"برنامه‌ریزی. کنترل. ساخت هوشمندتر.",cta:"مشاهده CUBI",secondary:"مشاهده قابلیت‌ها",
    dashboard:"مرکز کنترل CUBI",demo:"نمونه",schedule:"سلامت زمان‌بندی",progress:"پیشرفت",cost:"عملکرد هزینه",
    activities:"فعالیت‌ها",baseline:"خط مبنا",aiInsight:"بینش هوشمند",
    featuresKicker:"قابلیت‌های اصلی",featuresTitle:"همه آنچه برای موفقیت پروژه نیاز دارید.",
    featuresLead:"یک لایه کنترل واحد که مدل برنامه‌ریزی، اطلاعات کارگاه و عملکرد تجاری را به هم متصل می‌کند.",
    features:[
      ["⌁","کنترل پروژه","زمان‌بندی، خط مبنا، پیشرفت و عملکرد در یک نمای عملیاتی واحد."],
      ["✦","دستیار هوشمند","کمک زمینه‌محور برای تحلیل، راهنمایی و پیشنهاد اقدام بعدی."],
      ["◒","منابع و هزینه","تقاضای منابع، هزینه و سیگنال‌های EVM متصل به اجرا."],
      ["▤","اسناد و قراردادها","قرارداد، نقشه، RFI، Submittal، Claims و شواهد."],
      ["◎","همکاری","زمینه مشترک پروژه برای تیم‌ها، بررسی، تأیید و ردیابی."],
      ["◈","ابر و مقیاس‌پذیری","معماری آماده وب برای توسعه یکپارچه در دسکتاپ و موبایل."]
    ],
    techKicker:"پایه مهندسی",techTitle:"بر پایه مدل پروژه، نه در حاشیه آن.",
    techLead:"معماری زمان‌بندی هم‌راستا با CPM، PostgreSQL، هوش مصنوعی، یکپارچگی داده و امنیت؛ با یک هسته مهندسی مشترک.",
    aiTitle:"دستیار هوشمندی که به مدل پروژه احترام می‌گذارد.",
    aiLead:"ناهنجاری‌ها را آشکار می‌کند، سیگنال‌های کنترل را توضیح می‌دهد و اقدام بعدی را پیشنهاد می‌کند؛ بدون تغییر پنهانی داده‌های معتبر پروژه.",
    aiItems:["هوشمندی زمان‌بندی","هوشمندی اسناد","کمک به گزارش و KPI"],
    pricingKicker:"پلتفرم CUBI",pricingTitle:"آماده ساخت هوشمندتر هستید؟",pricingLead:"با لایه کنترل شروع کنید و به‌تدریج به پلتفرم کامل هوشمندی ساخت برسید.",pricingCta:"ورود به پلتفرم CUBI",
    footer:"هوشمندی ساخت و ساختمان"
  }
};
function setLocale(locale:LandingLocale){document.documentElement.lang=locale;document.documentElement.dir=locale==="fa"?"rtl":"ltr";}
function renderLanding(container:HTMLElement,locale:LandingLocale){
  const t=translations[locale]; setLocale(locale);
  container.innerHTML=`
  <div class="cubi-site cubi-reference-site">
    <header class="cubi-header cubi-reference-header">
      <a class="cubi-reference-brand" href="/" aria-label="CUBI Platform home"><img src="/cubi-logo-lockup.svg" width="184" height="54" alt="CUBI Platform" /></a>
      <nav class="cubi-nav" aria-label="Primary navigation">
        <a href="#product">${t.navHome}</a><a href="#features">${t.navFeatures}</a><a href="#solutions">${t.navSolutions}</a>
        <a href="#pricing">${t.navPricing}</a><a href="#ai">${t.navAi}</a><a href="#resources">${t.navResources}</a>
      </nav>
      <div class="cubi-header-actions"><button class="cubi-lang-switch" type="button" aria-label="${locale==="fa"?"Switch to English":"تغییر به فارسی"}">${t.language}</button><a class="cubi-button cubi-button-small" href="/app">${t.open}</a></div>
    </header>
    <main>
      <section class="cubi-reference-hero" id="product">
        <div class="cubi-reference-hero-copy">
          <div><p class="cubi-eyebrow">${t.eyebrow}</p><h1>${t.title} <em>${t.titleAccent}</em></h1><p class="cubi-lead">${t.lead}</p><p class="cubi-tagline">${t.tagline}</p></div>
          <div class="cubi-hero-actions"><a class="cubi-button" href="/app">${t.cta} <span aria-hidden="true">→</span></a><a class="cubi-text-link" href="#features">${t.secondary}</a></div>
        </div>
        <div class="cubi-reference-dashboard" aria-label="CUBI project-control dashboard preview">
          <div class="cubi-dash-top"><span>${t.dashboard}</span><b>${t.demo}</b></div>
          <div class="cubi-dash-body">
            <div class="cubi-reference-kpis">
              <div class="cubi-metric"><small>${t.schedule}</small><strong>92%</strong><span>${t.demo}</span></div>
              <div class="cubi-metric"><small>${t.progress}</small><strong>78%</strong><span>${t.demo}</span></div>
              <div class="cubi-metric"><small>${t.cost}</small><strong>0.96</strong><span>${t.demo}</span></div>
            </div>
            <div class="cubi-reference-chart" aria-hidden="true">
              <div class="cubi-reference-chart-bars"><i style="height:35%"></i><i style="height:52%"></i><i style="height:46%"></i><i style="height:71%"></i><i style="height:63%"></i><i style="height:86%"></i><i style="height:78%"></i></div>
              <div class="cubi-reference-chart-line"><span></span></div>
            </div>
          </div>
          <div class="cubi-reference-dashboard-footer"><span>${t.activities}</span><span>${t.baseline}</span><span>${t.progress}</span><b>${t.aiInsight}</b></div>
        </div>
      </section>
      <section class="cubi-reference-features cubi-section" id="features">
        <div class="cubi-section-head"><p class="cubi-kicker">${t.featuresKicker}</p><h2>${t.featuresTitle}</h2><p>${t.featuresLead}</p></div>
        <div class="cubi-feature-grid cubi-reference-feature-grid">${t.features.map(([icon,title,body])=>`<article><span class="cubi-icon">${icon}</span><h3>${title}</h3><p>${body}</p></article>`).join("")}</div>
      </section>
      <section class="cubi-reference-tech cubi-section" id="solutions">
        <div class="cubi-section-head"><p class="cubi-kicker">${t.techKicker}</p><h2>${t.techTitle}</h2><p>${t.techLead}</p></div>
        <div class="cubi-tech-pills"><span>CPM Scheduling</span><span>PostgreSQL</span><span>AI</span><span>Data Integration</span><span>Security</span></div>
      </section>
      <section class="cubi-reference-ai cubi-section" id="ai">
        <div class="cubi-reference-ai-mark"><img src="/logo-dark.svg" width="64" height="64" alt="" /></div>
        <div><p class="cubi-kicker">${t.navAi}</p><h2>${t.aiTitle}</h2><p>${t.aiLead}</p><div class="cubi-ai-items">${t.aiItems.map(item=>`<span>${item}</span>`).join("")}</div></div>
      </section>
      <section class="cubi-reference-cta" id="pricing">
        <div><p class="cubi-kicker">${t.pricingKicker}</p><h2>${t.pricingTitle}</h2><p>${t.pricingLead}</p></div><a class="cubi-button" href="/app">${t.pricingCta} <span aria-hidden="true">→</span></a>
      </section>
      <section class="cubi-reference-resources" id="resources" aria-label="${t.navResources}"><span>Project Data</span><span>Control</span><span>Documents</span><span>Field</span><span>Reporting</span></section>
    </main>
    <footer class="cubi-footer cubi-reference-footer"><div class="cubi-brand"><img src="/cubi-logo-lockup-dark.svg" width="184" height="54" alt="CUBI Platform" /></div><p>${t.tagline}</p><span>${t.footer}</span></footer>
  </div>`;
  container.querySelector<HTMLButtonElement>(".cubi-lang-switch")?.addEventListener("click",()=>{
    const next:LandingLocale=locale==="fa"?"en":"fa"; const y=window.scrollY; renderLanding(container,next); window.scrollTo({top:y,behavior:"auto"});
  });
}
export function renderLandingPage(container:HTMLElement):void{renderLanding(container,"en");}
