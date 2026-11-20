/**
 * Enterprise Workbench visual system.
 *
 * Scoped to the isolated `/cubi` document. It deliberately does not modify the
 * Engineering shell stylesheet. Uses logical properties so Persian/Arabic RTL
 * mirrors without a second stylesheet.
 */

export const ENTERPRISE_CSS = `
:root {
  --cubi-navy-950: #071627;
  --cubi-navy-900: #0b1f36;
  --cubi-navy-800: #12304d;
  --cubi-navy-700: #1b4268;
  --cubi-slate-600: #445b72;
  --cubi-slate-500: #64798d;
  --cubi-slate-300: #c7d3de;
  --cubi-slate-200: #dde6ee;
  --cubi-slate-100: #eef3f7;
  --cubi-slate-50: #f6f9fb;
  --cubi-gold-500: #b98a2f;
  --cubi-gold-300: #e5c987;
  --cubi-teal-600: #0f7c78;
  --cubi-teal-100: #dcf2f0;
  --cubi-red-600: #b2372e;
  --cubi-red-100: #fbe5e2;
  --cubi-amber-600: #9a6412;
  --cubi-amber-100: #fdf0d5;
  --cubi-green-600: #1f6b45;
  --cubi-green-100: #ddf0e4;
  --cubi-radius: 12px;
  --cubi-radius-sm: 8px;
  --cubi-shadow: 0 12px 34px rgba(9, 30, 51, 0.10);
  --cubi-shadow-sm: 0 2px 8px rgba(9, 30, 51, 0.07);
  --cubi-font: "Segoe UI", "Inter", "Vazirmatn", system-ui, -apple-system, sans-serif;
  color-scheme: light;
}

* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body.cubi-body {
  font-family: var(--cubi-font);
  background: var(--cubi-slate-50);
  color: var(--cubi-navy-900);
  min-height: 100vh;
  font-size: 15px;
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}
button, input, select, textarea { font: inherit; color: inherit; }
a { color: var(--cubi-navy-700); }
h1, h2, h3, h4 { margin: 0; line-height: 1.25; letter-spacing: -0.01em; }
p { margin: 0; }
.cubi-visually-hidden { position: absolute !important; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0; }
:focus-visible { outline: 3px solid var(--cubi-gold-500); outline-offset: 2px; }

/* ---------- shell ---------- */
.cubi-shell { display: grid; grid-template-columns: 272px minmax(0, 1fr); min-height: 100vh; }
.cubi-sidebar {
  background: linear-gradient(178deg, var(--cubi-navy-950), var(--cubi-navy-900) 62%, #0d2741);
  color: #eaf1f8;
  display: flex; flex-direction: column; gap: 18px;
  padding: 22px 16px 18px;
  position: sticky; top: 0; height: 100vh; overflow-y: auto;
}
.cubi-brand { display: flex; align-items: center; gap: 10px; padding: 0 8px; text-decoration: none; color: #fff; }
.cubi-brand-mark {
  width: 38px; height: 38px; border-radius: 11px; flex: none;
  background: linear-gradient(140deg, var(--cubi-gold-300), var(--cubi-gold-500));
  color: var(--cubi-navy-950); display: grid; place-items: center;
  font-weight: 800; font-size: 15px; letter-spacing: -0.03em;
}
.cubi-brand-text { display: flex; flex-direction: column; }
.cubi-brand-text strong { font-size: 15px; letter-spacing: .06em; }
.cubi-brand-text span { font-size: 11.5px; color: #a9bfd3; letter-spacing: .04em; }
.cubi-nav-group { display: flex; flex-direction: column; gap: 2px; }
.cubi-nav-label { font-size: 10.5px; text-transform: uppercase; letter-spacing: .12em; color: #7e97ad; padding: 4px 10px 6px; }
.cubi-nav a {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 11px; border-radius: 8px; color: #cfdcea; text-decoration: none;
  font-size: 13.5px; border: 1px solid transparent;
}
.cubi-nav a:hover { background: rgba(255,255,255,.06); color: #fff; }
.cubi-nav a[aria-current="page"] { background: rgba(229, 201, 135, .14); border-color: rgba(229, 201, 135, .35); color: #fff; }
.cubi-nav a[aria-current="page"] .cubi-icon { background: var(--cubi-gold-500); }
.cubi-icon { width: 16px; height: 16px; border-radius: 4px; background: rgba(255,255,255,.14); flex: none; position: relative; }
.cubi-icon::after { content: ""; position: absolute; inset: 4px; border: 1.5px solid rgba(7,22,39,.65); border-radius: 2px; }
.cubi-sidebar-foot { margin-top: auto; border-top: 1px solid rgba(255,255,255,.10); padding-top: 14px; display: flex; flex-direction: column; gap: 10px; }
.cubi-identity { display: flex; align-items: center; gap: 10px; padding: 6px 8px; }
.cubi-avatar { width: 34px; height: 34px; border-radius: 50%; background: var(--cubi-navy-700); color: #fff; display: grid; place-items: center; font-weight: 700; font-size: 12px; flex: none; border: 1px solid rgba(255,255,255,.18); }
.cubi-identity-text { min-width: 0; }
.cubi-identity-text strong { display: block; font-size: 12.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cubi-identity-text span { display: block; font-size: 11px; color: #93aabf; }
.cubi-signout { background: none; border: 1px solid rgba(255,255,255,.18); color: #cfdcea; border-radius: 8px; padding: 7px 10px; cursor: pointer; font-size: 12.5px; }
.cubi-signout:hover { background: rgba(255,255,255,.07); }

.cubi-main { min-width: 0; display: flex; flex-direction: column; }
.cubi-topbar {
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
  padding: 14px 26px; background: rgba(255,255,255,.9); backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--cubi-slate-200); position: sticky; top: 0; z-index: 20;
}
.cubi-crumbs { display: flex; align-items: center; gap: 7px; color: var(--cubi-slate-500); font-size: 12.5px; flex-wrap: wrap; }
.cubi-crumbs a { color: var(--cubi-slate-600); text-decoration: none; }
.cubi-crumbs span.sep { opacity: .5; }
.cubi-topbar-actions { display: flex; align-items: center; gap: 9px; }
.cubi-lang select { border: 1px solid var(--cubi-slate-300); background: #fff; border-radius: 8px; padding: 7px 9px; font-size: 12.5px; }
.cubi-env-pill { display: inline-flex; align-items: center; gap: 6px; border: 1px solid var(--cubi-slate-300); background: #fff; border-radius: 999px; padding: 5px 11px; font-size: 12px; color: var(--cubi-slate-600); }
.cubi-env-pill::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--cubi-teal-600); }
.cubi-content { padding: 26px; max-width: 1440px; width: 100%; margin-inline: auto; }

/* ---------- page header ---------- */
.cubi-page-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; margin-bottom: 20px; flex-wrap: wrap; }
.cubi-page-head h1 { font-size: 25px; font-weight: 700; }
.cubi-page-head p { color: var(--cubi-slate-500); margin-top: 5px; max-width: 70ch; font-size: 13.5px; }
.cubi-page-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.cubi-eyebrow { display: inline-block; font-size: 10.5px; letter-spacing: .14em; text-transform: uppercase; color: var(--cubi-gold-500); font-weight: 700; margin-bottom: 6px; }

/* ---------- buttons ---------- */
.cubi-btn { border-radius: 9px; border: 1px solid transparent; padding: 8px 13px; font-size: 13px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 7px; text-decoration: none; }
.cubi-btn:disabled { opacity: .5; cursor: not-allowed; }
.cubi-btn-primary { background: var(--cubi-navy-800); color: #fff; }
.cubi-btn-primary:hover:not(:disabled) { background: var(--cubi-navy-700); }
.cubi-btn-secondary { background: #fff; border-color: var(--cubi-slate-300); color: var(--cubi-navy-800); }
.cubi-btn-secondary:hover:not(:disabled) { background: var(--cubi-slate-100); }
.cubi-btn-ghost { background: transparent; color: var(--cubi-slate-600); }
.cubi-btn-ghost:hover:not(:disabled) { background: var(--cubi-slate-100); }
.cubi-btn-danger { background: var(--cubi-red-600); color: #fff; }

/* ---------- badges ---------- */
.cubi-badge { display: inline-flex; align-items: center; gap: 5px; padding: 3px 9px; border-radius: 999px; font-size: 11.5px; font-weight: 600; border: 1px solid transparent; white-space: nowrap; }
.cubi-badge-neutral { background: var(--cubi-slate-100); color: var(--cubi-slate-600); border-color: var(--cubi-slate-200); }
.cubi-badge-success { background: var(--cubi-green-100); color: var(--cubi-green-600); }
.cubi-badge-warning { background: var(--cubi-amber-100); color: var(--cubi-amber-600); }
.cubi-badge-danger { background: var(--cubi-red-100); color: var(--cubi-red-600); }
.cubi-badge-info { background: var(--cubi-teal-100); color: var(--cubi-teal-600); }

/* ---------- grid / cards ---------- */
.cubi-grid { display: grid; gap: 16px; }
.cubi-grid-2 { grid-template-columns: repeat(2, minmax(0,1fr)); }
.cubi-grid-3 { grid-template-columns: repeat(3, minmax(0,1fr)); }
.cubi-grid-4 { grid-template-columns: repeat(4, minmax(0,1fr)); }
.cubi-stack { display: flex; flex-direction: column; gap: 16px; }
.cubi-row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.cubi-spread { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.cubi-card { background: #fff; border: 1px solid var(--cubi-slate-200); border-radius: var(--cubi-radius); box-shadow: var(--cubi-shadow-sm); overflow: hidden; }
.cubi-card-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; padding: 16px 18px 0; flex-wrap: wrap; }
.cubi-card-title { font-size: 15px; font-weight: 700; }
.cubi-card-actions { display: flex; gap: 6px; flex-wrap: wrap; }
.cubi-card-body { padding: 14px 18px 18px; }
.cubi-card-accent { border-top: 3px solid var(--cubi-gold-500); }
.cubi-section-title { font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; color: var(--cubi-slate-500); margin-bottom: 10px; }

.cubi-stat { background: #fff; border: 1px solid var(--cubi-slate-200); border-radius: var(--cubi-radius); padding: 15px 16px; box-shadow: var(--cubi-shadow-sm); }
.cubi-stat-label { display: block; font-size: 12px; color: var(--cubi-slate-500); }
.cubi-stat-value { display: block; font-size: 24px; font-weight: 750; letter-spacing: -0.02em; margin: 4px 0 2px; }
.cubi-stat-meta { font-size: 11.5px; color: var(--cubi-slate-500); }
.cubi-stat-success { border-inline-start: 3px solid var(--cubi-green-600); }
.cubi-stat-warning { border-inline-start: 3px solid var(--cubi-amber-600); }
.cubi-stat-danger { border-inline-start: 3px solid var(--cubi-red-600); }

/* ---------- states ---------- */
.cubi-state { display: flex; gap: 13px; align-items: flex-start; padding: 18px; border-radius: var(--cubi-radius); border: 1px dashed var(--cubi-slate-300); background: #fff; }
.cubi-state-mark { width: 30px; height: 30px; border-radius: 8px; display: grid; place-items: center; background: var(--cubi-slate-100); color: var(--cubi-slate-500); font-weight: 700; flex: none; }
.cubi-state-body strong { display: block; font-size: 14px; }
.cubi-state-body p { color: var(--cubi-slate-500); font-size: 13px; margin-top: 3px; }
.cubi-state-actions { margin-top: 10px; display: flex; gap: 8px; flex-wrap: wrap; }
.cubi-state-error { border-color: #ecc7c2; background: #fffafa; }
.cubi-state-error .cubi-state-mark { background: var(--cubi-red-100); color: var(--cubi-red-600); }
.cubi-state-forbidden .cubi-state-mark { background: var(--cubi-amber-100); color: var(--cubi-amber-600); }
.cubi-state-unavailable .cubi-state-mark { background: var(--cubi-slate-100); color: var(--cubi-slate-600); }
.cubi-state-loading { align-items: center; }
.cubi-loading { display: flex; align-items: center; gap: 10px; padding: 28px; justify-content: center; color: var(--cubi-slate-500); font-size: 13px; }
.cubi-spinner { width: 18px; height: 18px; border-radius: 50%; border: 2px solid var(--cubi-slate-200); border-top-color: var(--cubi-navy-700); animation: cubi-spin .8s linear infinite; }
@keyframes cubi-spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .cubi-spinner { animation-duration: 2.4s; } }

/* ---------- tables ---------- */
.cubi-table-wrap { overflow-x: auto; border: 1px solid var(--cubi-slate-200); border-radius: var(--cubi-radius-sm); background: #fff; }
.cubi-table { border-collapse: collapse; width: 100%; min-width: 560px; font-size: 13px; }
.cubi-table th { text-align: start; font-size: 11px; text-transform: uppercase; letter-spacing: .07em; color: var(--cubi-slate-500); background: var(--cubi-slate-50); padding: 10px 12px; border-bottom: 1px solid var(--cubi-slate-200); white-space: nowrap; }
.cubi-table td { padding: 11px 12px; border-bottom: 1px solid var(--cubi-slate-100); vertical-align: top; }
.cubi-table tbody tr:last-child td { border-bottom: none; }
.cubi-table tbody tr:hover { background: var(--cubi-slate-50); }
.cubi-row-action { cursor: pointer; }
.cubi-table-empty { text-align: center; color: var(--cubi-slate-500); padding: 24px !important; }
.cubi-table .cubi-strong { font-weight: 650; }
.cubi-mono { font-family: "SFMono-Regular", ui-monospace, Menlo, monospace; font-size: 12px; }

/* ---------- forms ---------- */
.cubi-form-grid { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 14px; }
.cubi-field { display: flex; flex-direction: column; gap: 5px; font-size: 13px; }
.cubi-field-label { font-weight: 600; color: var(--cubi-navy-800); }
.cubi-field-label em { color: var(--cubi-red-600); font-style: normal; }
.cubi-field-hint { color: var(--cubi-slate-500); font-size: 11.5px; }
.cubi-input { width: 100%; border: 1px solid var(--cubi-slate-300); border-radius: 8px; padding: 8px 10px; background: #fff; font-size: 13.5px; min-height: 38px; }
.cubi-input:disabled { background: var(--cubi-slate-100); color: var(--cubi-slate-500); cursor: not-allowed; }
.cubi-textarea { resize: vertical; min-height: 80px; }
.cubi-form-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 14px; flex-wrap: wrap; }
.cubi-form-note { background: var(--cubi-slate-50); border: 1px solid var(--cubi-slate-200); border-radius: 8px; padding: 10px 12px; font-size: 12px; color: var(--cubi-slate-600); }

/* ---------- tabs / toolbar ---------- */
.cubi-tabs { display: flex; gap: 4px; border-bottom: 1px solid var(--cubi-slate-200); overflow-x: auto; }
.cubi-tab { background: none; border: none; border-bottom: 2px solid transparent; padding: 9px 13px; font-size: 13px; color: var(--cubi-slate-500); cursor: pointer; white-space: nowrap; }
.cubi-tab:hover { color: var(--cubi-navy-800); }
.cubi-tab.is-selected { color: var(--cubi-navy-900); border-bottom-color: var(--cubi-gold-500); font-weight: 650; }
.cubi-toolbar { display: flex; gap: 9px; align-items: center; flex-wrap: wrap; margin-bottom: 12px; }
.cubi-toolbar .cubi-input { width: auto; min-width: 170px; }

/* ---------- split / detail ---------- */
.cubi-split { display: grid; grid-template-columns: minmax(0, 1.65fr) minmax(300px, 1fr); gap: 16px; align-items: start; }
.cubi-detail { position: sticky; top: 78px; }
.cubi-kv { display: grid; grid-template-columns: 128px minmax(0,1fr); gap: 6px 12px; font-size: 12.5px; }
.cubi-kv dt { color: var(--cubi-slate-500); }
.cubi-kv dd { margin: 0; font-weight: 550; overflow-wrap: anywhere; }

/* ---------- hero / public ---------- */
.cubi-public { background: radial-gradient(1100px 520px at 80% -10%, rgba(185,138,47,.16), transparent 60%), radial-gradient(900px 500px at -10% 20%, rgba(15,124,120,.15), transparent 55%), var(--cubi-navy-950); color: #eaf2fa; min-height: 100vh; display: flex; flex-direction: column; }
.cubi-public-nav { display: flex; align-items: center; justify-content: space-between; gap: 18px; padding: 18px 30px; border-bottom: 1px solid rgba(255,255,255,.10); }
.cubi-public-nav .cubi-brand-text span { color: #a9bfd3; }
.cubi-public-links { display: flex; gap: 16px; align-items: center; flex-wrap: wrap; }
.cubi-public-links a { color: #c9d8e6; text-decoration: none; font-size: 13px; }
.cubi-public-links a:hover { color: #fff; }
.cubi-hero { padding: 64px 30px 40px; max-width: 1180px; margin-inline: auto; width: 100%; }
.cubi-hero h1 { font-size: clamp(32px, 5vw, 54px); line-height: 1.06; letter-spacing: -0.035em; max-width: 18ch; }
.cubi-hero .lede { color: #b9cbdb; font-size: 17px; max-width: 62ch; margin-top: 18px; }
.cubi-hero-actions { display: flex; gap: 10px; margin-top: 26px; flex-wrap: wrap; }
.cubi-hero-actions .cubi-btn-primary { background: var(--cubi-gold-500); color: var(--cubi-navy-950); }
.cubi-hero-actions .cubi-btn-primary:hover { background: var(--cubi-gold-300); }
.cubi-hero-actions .cubi-btn-secondary { background: rgba(255,255,255,.06); border-color: rgba(255,255,255,.22); color: #eaf2fa; }
.cubi-hero-actions .cubi-btn-secondary:hover { background: rgba(255,255,255,.12); }
.cubi-hero-grid { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 14px; margin-top: 44px; }
.cubi-hero-tile { border: 1px solid rgba(255,255,255,.13); background: rgba(255,255,255,.04); border-radius: 14px; padding: 16px; }
.cubi-hero-tile strong { display: block; font-size: 13.5px; margin-bottom: 4px; }
.cubi-hero-tile span { color: #a9bfd3; font-size: 12px; }
.cubi-public-section { padding: 34px 30px; max-width: 1180px; margin-inline: auto; width: 100%; }
.cubi-public-section h2 { font-size: 24px; margin-bottom: 10px; }
.cubi-public-section p { color: #b9cbdb; max-width: 72ch; }
.cubi-public-split { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 16px; margin-top: 20px; }
.cubi-public-card { border: 1px solid rgba(255,255,255,.15); background: rgba(255,255,255,.05); border-radius: 16px; padding: 20px; }
.cubi-public-card h3 { font-size: 17px; margin-bottom: 8px; }
.cubi-public-card ul { margin: 10px 0 0; padding-inline-start: 18px; color: #b9cbdb; font-size: 13px; }
.cubi-public-card li { margin-bottom: 5px; }
.cubi-public-footer { margin-top: auto; border-top: 1px solid rgba(255,255,255,.1); padding: 18px 30px; color: #8fa7bd; font-size: 12px; display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.cubi-public-footer a { color: #b9cbdb; }

/* ---------- login ---------- */
.cubi-auth-wrap { min-height: 100vh; display: grid; grid-template-columns: minmax(0,1fr) minmax(420px, 520px); }
.cubi-auth-art { background: radial-gradient(800px 480px at 20% 0%, rgba(185,138,47,.2), transparent 60%), var(--cubi-navy-950); color: #eaf2fa; padding: 46px 40px; display: flex; flex-direction: column; justify-content: space-between; }
.cubi-auth-art h2 { font-size: 34px; line-height: 1.1; letter-spacing: -.03em; max-width: 16ch; }
.cubi-auth-art p { color: #b9cbdb; max-width: 52ch; margin-top: 14px; }
.cubi-auth-card { background: #fff; display: flex; align-items: center; justify-content: center; padding: 34px; }
.cubi-auth-form { width: 100%; max-width: 380px; display: flex; flex-direction: column; gap: 14px; }
.cubi-auth-form h1 { font-size: 24px; }
.cubi-alert { border-radius: 9px; padding: 10px 12px; font-size: 12.5px; border: 1px solid; }
.cubi-alert-error { background: var(--cubi-red-100); color: var(--cubi-red-600); border-color: #efc9c4; }
.cubi-alert-info { background: var(--cubi-teal-100); color: var(--cubi-teal-600); border-color: #bfe3e0; }
.cubi-password-row { display: flex; gap: 6px; }
.cubi-password-row .cubi-input { flex: 1; }
.cubi-demo-grid { display: grid; gap: 8px; margin-top: 4px; }
.cubi-demo-role { display: flex; justify-content: space-between; gap: 10px; align-items: center; border: 1px solid var(--cubi-slate-200); border-radius: 9px; padding: 9px 11px; background: var(--cubi-slate-50); font-size: 12.5px; }
.cubi-demo-role form { margin: 0; }

/* ---------- environments ---------- */
.cubi-env-grid { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 18px; }
.cubi-env-card { background: #fff; border: 1px solid var(--cubi-slate-200); border-radius: 16px; padding: 22px; box-shadow: var(--cubi-shadow-sm); display: flex; flex-direction: column; gap: 12px; position: relative; overflow: hidden; }
.cubi-env-card::before { content: ""; position: absolute; inset-block-start: 0; inset-inline: 0; height: 4px; background: var(--cubi-teal-600); }
.cubi-env-card.enterprise::before { background: var(--cubi-gold-500); }
.cubi-env-card h2 { font-size: 19px; }
.cubi-env-card .desc { color: var(--cubi-slate-500); font-size: 13px; }
.cubi-env-meta { display: flex; flex-direction: column; gap: 6px; font-size: 12.5px; color: var(--cubi-slate-600); }
.cubi-env-actions { margin-top: auto; display: flex; gap: 8px; flex-wrap: wrap; }

/* ---------- workbench widgets ---------- */
.cubi-widgets { display: grid; grid-template-columns: repeat(12, minmax(0,1fr)); gap: 16px; }
.cubi-widget { grid-column: span 4; }
.cubi-widget.wide { grid-column: span 8; }
.cubi-widget.full { grid-column: span 12; }
.cubi-widget.narrow { grid-column: span 3; }
.cubi-widget-handle { display: flex; gap: 4px; }
.cubi-widget-handle .cubi-btn { padding: 4px 7px; font-size: 11px; }
.cubi-list { display: flex; flex-direction: column; }
.cubi-list-item { display: flex; justify-content: space-between; gap: 10px; padding: 9px 0; border-bottom: 1px solid var(--cubi-slate-100); font-size: 12.5px; }
.cubi-list-item:last-child { border-bottom: none; }
.cubi-list-item strong { font-weight: 600; }
.cubi-empty-line { color: var(--cubi-slate-500); font-size: 12.5px; padding: 8px 0; }
.cubi-conn { display: flex; flex-direction: column; gap: 8px; }
.cubi-conn-row { display: flex; justify-content: space-between; gap: 10px; font-size: 12px; padding: 7px 9px; background: var(--cubi-slate-50); border: 1px solid var(--cubi-slate-200); border-radius: 7px; }
.cubi-conn-row .path { font-family: ui-monospace, Menlo, monospace; font-size: 11px; color: var(--cubi-slate-500); }

/* ---------- dashboard portlets ---------- */
.cubi-dash-layout { display: grid; grid-template-columns: repeat(12, minmax(0,1fr)); gap: 14px; }
.cubi-portlet { grid-column: span 6; background: #fff; border: 1px solid var(--cubi-slate-200); border-radius: 12px; box-shadow: var(--cubi-shadow-sm); min-height: 140px; display: flex; flex-direction: column; }
.cubi-portlet.narrow { grid-column: span 4; }
.cubi-portlet.wide { grid-column: span 12; }
.cubi-portlet-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; padding: 10px 13px; border-bottom: 1px solid var(--cubi-slate-100); }
.cubi-portlet-head strong { font-size: 12.5px; }
.cubi-portlet-body { padding: 12px 13px; flex: 1; font-size: 12.5px; color: var(--cubi-slate-600); }
.cubi-portlet-actions { display: flex; gap: 3px; }
.cubi-portlet-actions button { background: none; border: 1px solid var(--cubi-slate-200); border-radius: 6px; padding: 2px 6px; cursor: pointer; font-size: 11px; color: var(--cubi-slate-600); }
.cubi-portlet-actions button:disabled { opacity: .4; cursor: not-allowed; }
.cubi-designer { display: grid; grid-template-columns: minmax(0,1fr) 310px; gap: 16px; align-items: start; }
.cubi-catalog { display: flex; flex-direction: column; gap: 7px; }
.cubi-catalog-item { display: flex; justify-content: space-between; align-items: center; gap: 8px; border: 1px solid var(--cubi-slate-200); border-radius: 8px; padding: 8px 10px; font-size: 12.5px; }
.cubi-catalog-item span { color: var(--cubi-slate-500); font-size: 11px; display: block; }

/* ---------- workflow studio ---------- */
.cubi-workflow { display: grid; grid-template-columns: minmax(0,1fr) 320px; gap: 16px; align-items: start; }
.cubi-flow-canvas { background: linear-gradient(180deg, #fbfdff, #f1f6fa); border: 1px solid var(--cubi-slate-200); border-radius: 12px; padding: 18px; min-height: 380px; display: flex; flex-direction: column; gap: 0; align-items: stretch; }
.cubi-flow-node { border: 1px solid var(--cubi-slate-300); border-radius: 9px; background: #fff; padding: 9px 12px; box-shadow: var(--cubi-shadow-sm); max-width: 280px; align-self: center; width: 100%; }
.cubi-flow-node strong { font-size: 12.5px; display: block; }
.cubi-flow-node span { font-size: 11px; color: var(--cubi-slate-500); }
.cubi-flow-node.terminal { border-color: var(--cubi-teal-600); }
.cubi-flow-edge { width: 2px; height: 26px; background: var(--cubi-slate-300); align-self: center; position: relative; }
.cubi-flow-edge::after { content: "▾"; position: absolute; bottom: -9px; left: 50%; transform: translateX(-50%); color: var(--cubi-slate-500); font-size: 11px; }
.cubi-flow-empty { text-align: center; color: var(--cubi-slate-500); font-size: 12.5px; padding: 40px 10px; }

/* ---------- knowledge ---------- */
.cubi-knowledge-grid { display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 14px; }
.cubi-knowledge-card { background: #fff; border: 1px solid var(--cubi-slate-200); border-radius: 12px; padding: 15px; cursor: pointer; text-align: start; }
.cubi-knowledge-card:hover { border-color: var(--cubi-gold-500); box-shadow: var(--cubi-shadow-sm); }
.cubi-knowledge-card h3 { font-size: 14px; margin-bottom: 5px; }
.cubi-knowledge-card p { font-size: 12px; color: var(--cubi-slate-500); }
.cubi-chip-row { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }

/* ---------- small utilities added with the enterprise pages ---------- */
.cubi-home-plan-item { margin-bottom: 16px; }
.cubi-home-cta-row { margin-top: 14px; }
.cubi-inline { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.cubi-table tr.is-selected { background: var(--cubi-gold-50, #fbf7ec); }

/* ---------- knowledge search ---------- */
.cubi-knowledge-results { display: flex; flex-direction: column; gap: 12px; margin-top: 14px; }
.cubi-knowledge-hit { border: 1px solid var(--cubi-slate-200); border-radius: 10px; padding: 12px 14px; background: #fff; text-align: start; }
.cubi-knowledge-hit-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 6px; }
.cubi-knowledge-hit p { margin: 0 0 6px; }
.cubi-knowledge-card-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; text-align: start; }
.cubi-knowledge-card-body { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 10px; text-align: start; }

/* ---------- timeline / audit ---------- */
.cubi-timeline { list-style: none; margin: 0; padding: 0; }
.cubi-timeline li { position: relative; padding-inline-start: 20px; padding-bottom: 14px; font-size: 12.5px; }
.cubi-timeline li::before { content: ""; position: absolute; inset-inline-start: 4px; top: 4px; width: 8px; height: 8px; border-radius: 50%; background: var(--cubi-gold-500); }
.cubi-timeline li::after { content: ""; position: absolute; inset-inline-start: 7px; top: 14px; bottom: 0; width: 1px; background: var(--cubi-slate-200); }
.cubi-timeline li:last-child::after { display: none; }
.cubi-timeline time { display: block; color: var(--cubi-slate-500); font-size: 11px; }

/* ---------- misc ---------- */
.cubi-note { font-size: 12px; color: var(--cubi-slate-500); background: var(--cubi-slate-50); border: 1px solid var(--cubi-slate-200); border-radius: 9px; padding: 10px 12px; }
.cubi-note-strong { border-inline-start: 3px solid var(--cubi-gold-500); }
.cubi-toast-host { position: fixed; inset-block-end: 20px; inset-inline-end: 20px; display: flex; flex-direction: column; gap: 8px; z-index: 100; }
.cubi-toast { background: var(--cubi-navy-900); color: #fff; border-radius: 9px; padding: 10px 14px; font-size: 13px; box-shadow: var(--cubi-shadow); max-width: 340px; }
.cubi-toast.error { background: var(--cubi-red-600); }
.cubi-skip { position: absolute; inset-inline-start: -9999px; top: 0; background: #fff; color: var(--cubi-navy-900); padding: 10px; z-index: 200; }
.cubi-skip:focus { inset-inline-start: 10px; }
.cubi-public .cubi-skip { background: var(--cubi-gold-300); }

@media (max-width: 1180px) {
  .cubi-grid-4 { grid-template-columns: repeat(2, minmax(0,1fr)); }
  .cubi-hero-grid { grid-template-columns: repeat(2, minmax(0,1fr)); }
  .cubi-widget, .cubi-widget.narrow { grid-column: span 6; }
  .cubi-widget.wide { grid-column: span 12; }
}
@media (max-width: 980px) {
  .cubi-shell { grid-template-columns: 1fr; }
  .cubi-sidebar { position: static; height: auto; }
  .cubi-nav-group { flex-direction: row; flex-wrap: wrap; }
  .cubi-nav-label { display: none; }
  .cubi-split, .cubi-designer, .cubi-workflow { grid-template-columns: 1fr; }
  .cubi-detail { position: static; }
  .cubi-grid-3 { grid-template-columns: repeat(2, minmax(0,1fr)); }
  .cubi-auth-wrap { grid-template-columns: 1fr; }
  .cubi-auth-art { display: none; }
  .cubi-env-grid { grid-template-columns: 1fr; }
  .cubi-knowledge-grid { grid-template-columns: repeat(2, minmax(0,1fr)); }
}
@media (max-width: 680px) {
  .cubi-content { padding: 16px; }
  .cubi-grid-2, .cubi-grid-3, .cubi-grid-4, .cubi-hero-grid, .cubi-knowledge-grid, .cubi-form-grid, .cubi-public-split { grid-template-columns: 1fr; }
  .cubi-widget, .cubi-widget.narrow, .cubi-widget.wide { grid-column: span 12; }
  .cubi-portlet, .cubi-portlet.narrow, .cubi-portlet.wide { grid-column: span 12; }
  .cubi-page-head h1 { font-size: 21px; }
  .cubi-topbar { padding: 10px 14px; }
  .cubi-public-links { gap: 10px; }
}

@media (prefers-color-scheme: dark) {
  /* Deliberately not a full dark theme: enterprise print/report fidelity wins. */
}
`;
