export function renderLandingPage(container: HTMLElement): void {
  container.innerHTML = `
    <div class="cubi-site">
      <header class="cubi-header">
        <a class="cubi-brand" href="/" aria-label="CUBI Platform home">
          <img src="/logo.svg" width="42" height="42" alt="" />
          <span><strong>CUBI</strong><small>Platform</small></span>
        </a>
        <nav class="cubi-nav" aria-label="Primary navigation">
          <a href="#product">Product</a><a href="#solutions">Solutions</a><a href="#features">Features</a><a href="#pricing">Pricing</a><a href="#ai">AI</a><a href="#resources">Resources</a>
        </nav>
        <div class="cubi-header-actions"><a class="cubi-link" href="#faq">FAQ</a><a class="cubi-button cubi-button-small" href="/app">Open Platform</a></div>
      </header>

      <main>
        <section class="cubi-hero">
          <div class="cubi-hero-copy">
            <p class="cubi-eyebrow"><span></span> Construction & Building Intelligence</p>
            <h1>Construction Project Control, <em>Reimagined.</em></h1>
            <p class="cubi-lead">CUBI Platform brings construction planning, scheduling, project controls, cost, progress, documents and AI assistance into one professional platform.</p>
            <div class="cubi-hero-actions"><a class="cubi-button" href="/app">Explore CUBI Platform <span>→</span></a><a class="cubi-text-link" href="#features">See features</a></div>
            <p class="cubi-tagline">Plan. Control. Build Smarter.</p>
          </div>
          <div class="cubi-hero-visual" aria-label="CUBI project controls preview">
            <div class="cubi-grid-glow"></div>
            <div class="cubi-dashboard">
              <div class="cubi-dash-top"><span class="cubi-dot"></span><span>PROJECT CONTROL CENTER</span><b>Live</b></div>
              <div class="cubi-dash-body">
                <div class="cubi-metric"><small>Schedule Health</small><strong>92%</strong><span>+4.8%</span></div>
                <div class="cubi-metric"><small>Cost Performance</small><strong>0.96</strong><span>On track</span></div>
                <div class="cubi-chart"><div class="cubi-bars"><i style="height:38%"></i><i style="height:55%"></i><i style="height:48%"></i><i style="height:72%"></i><i style="height:64%"></i><i style="height:88%"></i><i style="height:78%"></i></div><div class="cubi-line"><span></span></div></div>
              </div>
              <div class="cubi-timeline"><span>WBS</span><span>Activities</span><span>Baseline</span><span>Progress</span><b>AI insight</b></div>
            </div>
            <div class="cubi-orbit"><img src="/logo.svg" alt="" /></div>
          </div>
        </section>

        <section class="cubi-proof" aria-label="Platform scope">
          <span>Built for the disciplines that control project outcomes</span><b>CPM / P6 Logic</b><b>Project Controls</b><b>Cost & EVM</b><b>Resources</b><b>Progress</b>
        </section>

        <section class="cubi-section" id="product">
          <div class="cubi-section-head"><p class="cubi-kicker">ONE CONTROL LAYER</p><h2>Everything teams need to keep projects moving.</h2><p>One coherent workspace for the planning, control and intelligence workflows behind complex construction delivery.</p></div>
          <div class="cubi-feature-grid">
            <article><span class="cubi-icon">⌁</span><h3>Planning & Scheduling</h3><p>CPM logic, WBS, activities, baselines and schedule analysis built for serious project planning.</p></article>
            <article><span class="cubi-icon">◈</span><h3>Project Controls</h3><p>Connect schedule, cost, progress and performance signals into one control view.</p></article>
            <article><span class="cubi-icon">✦</span><h3>AI Assistant</h3><p>Turn project data into focused insights and next actions without replacing engineering judgment.</p></article>
            <article><span class="cubi-icon">◒</span><h3>Resources & EVM</h3><p>Track resource demand, cost performance, earned value and delivery trends together.</p></article>
            <article><span class="cubi-icon">▤</span><h3>Documents & Contracts</h3><p>Keep project records, contracts, claims and issues connected to the work they affect.</p></article>
            <article><span class="cubi-icon">◎</span><h3>Collaboration & Cloud</h3><p>Work across teams with multilingual, responsive and audit-aware project workflows.</p></article>
          </div>
        </section>

        <section class="cubi-control-section" id="solutions">
          <div class="cubi-control-copy"><p class="cubi-kicker">PROJECT CONTROLS</p><h2>See the project as a system, not a collection of spreadsheets.</h2><p>Bring schedule logic, progress, cost and performance into a shared operating picture. CUBI is designed around the realities of construction control.</p><ul><li>Schedule and baseline visibility</li><li>Progress and performance signals</li><li>Cost, resources and EVM context</li><li>Documents, contracts, claims and issues</li></ul><a class="cubi-text-link" href="/app">Open the control workspace →</a></div>
          <div class="cubi-control-card"><div class="cubi-card-label">CONTROL SIGNALS</div><div class="cubi-signal"><span>Schedule</span><b>92</b><i></i></div><div class="cubi-signal"><span>Progress</span><b>78</b><i></i></div><div class="cubi-signal"><span>Cost</span><b>96</b><i></i></div><div class="cubi-signal"><span>Risk</span><b>14</b><i></i></div><div class="cubi-mini-note"><span>AI</span> 3 priority insights ready for review</div></div>
        </section>

        <section class="cubi-ai" id="ai"><div class="cubi-ai-mark"><img src="/logo-dark.svg" alt="" /></div><div><p class="cubi-kicker">INTELLIGENCE LAYER</p><h2>AI assistance that respects the project model.</h2><p>Use project context to surface anomalies, summarize control signals and focus attention on decisions that need a human owner.</p></div><a class="cubi-button" href="/app">Explore the platform</a></section>

        <section class="cubi-section cubi-resources" id="resources"><div class="cubi-section-head"><p class="cubi-kicker">CONNECTED DELIVERY</p><h2>From baseline to field progress.</h2><p>Designed to keep core project information connected across the lifecycle.</p></div><div class="cubi-flow"><span>Plan</span><i>→</i><span>Schedule</span><i>→</i><span>Control</span><i>→</i><span>Measure</span><i>→</i><span>Improve</span></div></section>

        <section class="cubi-cta" id="pricing"><p class="cubi-kicker">CUBI PLATFORM</p><h2>Plan with clarity. Control with confidence.</h2><p>Built for teams that need a professional project control layer without compromising the engineering core.</p><a class="cubi-button" href="/app">Enter CUBI Platform <span>→</span></a></section>

        <section class="cubi-faq" id="faq"><div><p class="cubi-kicker">FAQ</p><h2>Built for professional project teams.</h2></div><div class="cubi-faq-list"><details><summary>What is CUBI Platform?</summary><p>CUBI is a construction and building intelligence platform focused on planning, project controls, cost, progress, resources, documents and AI-assisted workflows.</p></details><details><summary>Does CUBI replace Primavera/CPM logic?</summary><p>No. The homepage is a product entry point; the underlying CPM and calculation core remains protected.</p></details><details><summary>Can teams work in multiple languages?</summary><p>The web platform is designed for multilingual operation, including RTL/LTR behavior.</p></details></div></section>
      </main>

      <footer class="cubi-footer"><div class="cubi-brand"><img src="/logo-dark.svg" width="40" height="40" alt="" /><span><strong>CUBI</strong><small>Platform</small></span></div><p>Plan. Control. Build Smarter.</p><span>Construction & Building Intelligence</span></footer>
    </div>`;
}
