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
    <style>
.cubi-compact-home{min-height:100vh;background:#fff;color:#132b4a;font-family:Inter,"Vazirmatn",system-ui,sans-serif}
.cubi-compact-header{height:72px;display:flex;align-items:center;gap:2rem;padding:0 7%;border-bottom:1px solid #e6ebf1;background:#fff}
.cubi-compact-brand{display:flex;align-items:center}.cubi-compact-brand img{width:108px;height:48px;object-fit:contain}
.cubi-compact-header nav{display:flex;gap:2rem;margin:auto}.cubi-compact-header nav a{color:#34445a;text-decoration:none;font-size:12px;font-weight:650}
.cubi-compact-actions{display:flex;align-items:center;gap:.7rem}.cubi-compact-actions button{border:0;background:transparent;color:#1976d2;font-weight:700;cursor:pointer}.cubi-compact-signin,.cubi-compact-start{padding:.62rem .9rem;border-radius:7px;text-decoration:none;font-size:12px;font-weight:750}.cubi-compact-signin{border:1px solid #d9e1ea;color:#253a52}.cubi-compact-start{background:#1976d2;color:#fff}
.cubi-compact-hero{min-height:510px;display:grid;grid-template-columns:45% 55%;align-items:center;padding:3.6rem 7%;gap:2rem;background:linear-gradient(100deg,#071d36,#0f3a65);color:#fff}
.cubi-compact-copy{max-width:590px}.cubi-compact-eyebrow{margin:0 0 .8rem;color:#39a6ff;font-size:12px;font-weight:850;letter-spacing:.13em}.cubi-compact-copy h1{margin:0;font-size:clamp(38px,4.6vw,58px);line-height:1.02;letter-spacing:-.045em}.cubi-compact-copy h1 span{display:block;color:#2c9bf4}.cubi-compact-copy h2{font-size:21px;margin:1rem 0 .8rem}.cubi-compact-copy>p:not(.cubi-compact-eyebrow){max-width:550px;color:#dce8f3;line-height:1.65;font-size:14px}
.cubi-compact-hero-actions{display:flex;gap:.8rem;margin-top:1.3rem}.cubi-compact-primary,.cubi-compact-secondary{display:inline-flex;align-items:center;min-height:45px;padding:0 1.1rem;border-radius:7px;text-decoration:none;font-size:12px;font-weight:800}.cubi-compact-primary{background:#1976d2;color:#fff}.cubi-compact-secondary{border:1px solid rgba(255,255,255,.6);color:#fff}
.cubi-compact-control{width:min(100%,620px);justify-self:end;background:#fff;border-radius:10px;color:#29425d;box-shadow:0 25px 65px rgba(0,0,0,.28);padding:15px}.cubi-control-top{display:flex;justify-content:space-between;font-size:10px;padding-bottom:12px;border-bottom:1px solid #e5ebf2}.cubi-control-top span{color:#2e9b6f;font-weight:850}.cubi-control-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin:12px 0}.cubi-control-grid div{border:1px solid #e6ecf2;border-radius:6px;padding:10px}.cubi-control-grid small{display:block;color:#7b8997;font-size:8px}.cubi-control-grid b{display:block;font-size:19px;margin:5px 0}.cubi-control-grid i{display:block;height:5px;border-radius:5px;background:linear-gradient(90deg,#1976d2 0 75%,#e9eef3 75%)}.cubi-control-grid div:nth-child(2) i{background:linear-gradient(90deg,#2e9b6f 0 88%,#e9eef3 88%)}.cubi-control-grid div:nth-child(3) i{background:linear-gradient(90deg,#f28c28 0 64%,#e9eef3 64%)}.cubi-control-timeline{height:100px;border:1px solid #e6ecf2;border-radius:6px;padding:16px 10px;display:flex;flex-direction:column;justify-content:center;gap:9px;background:#fbfdff}.cubi-control-timeline span{height:6px;border-radius:4px;background:#1976d2}.cubi-control-timeline span:nth-child(2){width:75%;background:#2e9b6f}.cubi-control-timeline span:nth-child(3){width:61%;background:#8b6bd9}.cubi-control-timeline span:nth-child(4){width:84%;background:#e36a51}.cubi-control-timeline span:nth-child(5){width:48%;background:#f28c28}.cubi-control-footer{display:flex;justify-content:space-between;font-size:8px;color:#7a8998;padding:10px 3px 0}
.cubi-compact-capabilities{padding:4rem 7%}.cubi-compact-section-head{text-align:center;max-width:720px;margin:0 auto 2.2rem}.cubi-compact-section-head h2{font-size:28px;margin:.2rem 0;color:#122c4d}.cubi-compact-section-head>p:last-child{font-size:12px;line-height:1.7;color:#68788a}.cubi-compact-grid{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid #dfe7ee;border-left:1px solid #dfe7ee}.cubi-compact-grid article{min-height:185px;padding:22px;border-right:1px solid #dfe7ee;border-bottom:1px solid #dfe7ee}.cubi-compact-grid article>span{color:#1976d2;font-size:11px;font-weight:850}.cubi-compact-grid h3{font-size:14px;margin:25px 0 8px;color:#213b57}.cubi-compact-grid p{font-size:11px;line-height:1.65;color:#6b7b8d;margin:0}
.cubi-compact-cta{padding:2.2rem 7%;display:flex;align-items:center;justify-content:space-between;gap:2rem;background:#eef7ff;border-top:1px solid #dce8f2}.cubi-compact-cta h2{margin:.2rem 0 .4rem;font-size:25px;color:#122c4d}.cubi-compact-cta p:last-child{margin:0;color:#64768a;font-size:12px}.cubi-compact-footer{min-height:100px;padding:1.4rem 7%;display:flex;align-items:center;gap:1.5rem;background:#071a30;color:#9fb2c5;font-size:10px}.cubi-compact-footer span{margin-right:auto}
html:lang(fa) .cubi-compact-home{font-family:"Vazirmatn",Inter,system-ui,sans-serif}.cubi-compact-home[dir="rtl"]{}
@media(max-width:900px){.cubi-compact-header{padding:10px 5%;height:auto;flex-wrap:wrap}.cubi-compact-header nav{order:3;width:100%;justify-content:center;overflow:auto}.cubi-compact-hero{grid-template-columns:1fr;padding:3.5rem 6%;min-height:auto}.cubi-compact-control{justify-self:start}.cubi-compact-grid{grid-template-columns:repeat(2,1fr)}.cubi-compact-capabilities,.cubi-compact-cta{padding-left:6%;padding-right:6%}}
@media(max-width:560px){.cubi-compact-header nav a:nth-child(n+3){display:none}.cubi-compact-signin{display:none}.cubi-compact-copy h1{font-size:38px}.cubi-compact-grid{grid-template-columns:1fr}.cubi-control-grid{grid-template-columns:1fr}.cubi-compact-cta{flex-direction:column;align-items:flex-start}.cubi-compact-footer{flex-wrap:wrap;padding-left:6%;padding-right:6%}.cubi-compact-footer span{margin:0}}
</style>\n    <div class="cubi-compact-home" id="home">
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
