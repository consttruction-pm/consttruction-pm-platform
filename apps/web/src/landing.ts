type LandingLocale = "en";

function setLandingDocumentLocale(): void {
  document.documentElement.lang = "en";
  document.documentElement.dir = "ltr";
}

function renderLanding(container: HTMLElement): void {
  setLandingDocumentLocale();
  container.innerHTML = \`
    <div class="cubi-reference-home" id="home">
      <header class="cubi-exact-header">
        <a class="cubi-exact-brand" href="./" aria-label="CUBI Platform home">
          <img src="./homepage/jalal151/logo-header.svg" width="108" height="48" alt="CUBI Platform" />
        </a>
        <nav class="cubi-exact-nav" aria-label="Primary navigation">
          <a class="is-active" href="#home">Home</a><a href="#features">Features</a><a href="#solutions">Solutions</a><a href="#pricing">Pricing</a><a href="#resources">Resources</a><a href="#about">About</a>
        </nav>
        <div class="cubi-exact-actions">
          <button class="cubi-exact-language" type="button" aria-label="Language selector"><span>◉</span> EN <b>⌄</b></button>
          <a class="cubi-exact-signin" href="./app/">Sign In</a>
          <a class="cubi-exact-start" href="./app/">Get Started</a>
        </div>
      </header>
      <main>
        <section class="cubi-exact-hero" aria-labelledby="cubi-hero-title">
          <div class="cubi-exact-hero-copy">
            <p class="cubi-exact-eyebrow">CUBI PLATFORM</p>
            <h1 id="cubi-hero-title">Construction &amp; Building <span>Intelligence</span></h1>
            <h2>Plan. Control. Build Smarter.</h2>
            <p>CUBI Platform brings together project controls, AI and engineering precision to help you plan, monitor and deliver construction projects with confidence.</p>
            <div class="cubi-exact-hero-actions">
              <a class="cubi-exact-primary" href="./app/">Get Started <span>→</span></a>
              <a class="cubi-exact-demo" href="#features"><span class="play">▶</span> Watch Demo</a>
            </div>
          </div>
          <div class="cubi-exact-dashboard" aria-label="CUBI project controls dashboard preview">
            <img src="./homepage/jalal151/hero-dashboard.svg" alt="CUBI project controls dashboard preview" style="width:100%;height:100%;object-fit:contain;" />
          </div>
        </section>
        <section class="cubi-exact-features" id="features">
          <div class="cubi-exact-section-head"><h2>Everything You Need for Project Success</h2><p>From planning to closeout, CUBI gives you the tools, insights and control to<br/>manage your construction projects smarter, faster and safer.</p></div>
          <div class="cubi-exact-feature-grid">
            <article><img class="cubi-feature-icon" src="./homepage/jalal151/feature-01-project-controls.svg" alt="" aria-hidden="true" style="object-fit:contain;" /><h3>Project Controls</h3><p>Plan, schedule and<br/>track progress with<br/>confidence.</p></article>
            <article><div class="cubi-feature-icon">✦</div><h3>AI Assistant</h3><p>Get instant insights,<br/>answers and<br/>recommendations.</p></article>
            <article><img class="cubi-feature-icon" src="./homepage/jalal151/feature-02-ai-assistant.svg" alt="" aria-hidden="true" style="object-fit:contain;" /><h3>Resources &amp; Cost</h3><p>Manage budgets,<br/>resources and<br/>cost performance.</p></article>
            <article><div class="cubi-feature-icon">▱</div><h3>Documents &amp; Contracts</h3><p>Centralize documents,<br/>contracts, claims<br/>and issues.</p></article>
            <article><img class="cubi-feature-icon" src="./homepage/jalal151/feature-03-resources-cost.svg" alt="" aria-hidden="true" style="object-fit:contain;" /><h3>Collaboration</h3><p>Work together<br/>across your team<br/>and stakeholders.</p></article>
            <article><div class="cubi-feature-icon">☁</div><h3>Cloud &amp; Scalability</h3><p>Secure, reliable and<br/>built to grow with<br/>your needs.</p></article>
          </div>
        </section>
        <section class="cubi-exact-tech" id="resources">
          <div class="cubi-tech-copy">
            <h2>Powered by Leading<br/>Technologies</h2>
            <p>CUBI integrates industry standards and proven tools<br/>to give you the best of both worlds — reliability and<br/>innovation.</p>
            <div class="cubi-tech-badges"><b class="p6">P6</b><span>Primavera P6</span><b class="pg">♟</b><span>PostgreSQL</span><b class="ai">✧</b><span>AI</span></div>
            <a class="cubi-exact-outline" href="#solutions">Learn More <span>→</span></a>
          </div>
          <div class="cubi-tech-diagram" aria-label="CUBI technology architecture">
            <img src="./homepage/jalal151/tech-stack-illustration.svg" alt="CUBI technology architecture" style="width:100%;height:100%;object-fit:contain;" />
          </div>
        </section>
        <section class="cubi-exact-cta" id="pricing" style="background-image:linear-gradient(100deg,rgba(10,42,75,.94),rgba(6,33,67,.94)),url('./homepage/jalal151/cta-background.svg');background-size:cover;background-position:center;">
          <div><h2>Ready to Build Smarter?</h2><p>Join teams around the world who are transforming construction<br/>with CUBI Platform.</p></div>
          <div class="cubi-cta-actions"><a class="cubi-exact-primary" href="./app/">Start Free Trial <span>→</span></a><a class="cubi-exact-demo" href="#about">Contact Sales</a></div>
        </section>
      </main>
      <footer class="cubi-exact-footer" id="about">
        <div class="cubi-footer-brand"><img src="./homepage/jalal151/logo-footer.svg" width="112" height="52" alt="CUBI Platform"/><small>Plan. Control. Build Smarter.</small></div>
        <div class="cubi-footer-col"><b>Product</b><a href="#features">Features</a><a href="#pricing">Pricing</a><a href="#resources">Integrations</a></div>
        <div class="cubi-footer-col"><b>Resources</b><a href="#resources">Documentation</a><a href="#resources">Blog</a><a href="#about">Support</a></div>
        <div class="cubi-footer-col"><b>Company</b><a href="#about">About Us</a><a href="#about">Careers</a><a href="#about">Contact</a></div>
        <div class="cubi-footer-social"><span>in</span><span>𝕏</span><span>▶</span><span>◉</span><small>© 2026 CUBI Platform. All rights reserved.</small></div>
      </footer>
    </div>\`;
}

export function renderLandingPage(container: HTMLElement): void {
  renderLanding(container);
}
