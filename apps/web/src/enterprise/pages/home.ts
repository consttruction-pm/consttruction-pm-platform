import type { PublicPageContext } from "../app.js";
import { BASE_PATH } from "../router.js";
import { button, el, link as uiLink } from "../ui.js";

/**
 * Page 1 — CUBI product homepage.
 *
 * CUBI-owned; no P6 Help topic is the reference. Sign-up is not self-service in
 * the current product, so the call to action is an honest access request, not a
 * fake registration form.
 */

const FEATURES = [
  { title: "Engineering workspace", body: "Planning, scheduling, WBS, progress, resources and cost under the authoritative calculation core." },
  { title: "Enterprise workbench", body: "Organization, portfolio, projects, tasks, approvals, reports and governance in one organizational environment." },
  { title: "Revision-aware contracts", body: "Every cross-environment read is versioned, permission-checked and pinned to a source revision." },
  { title: "Server-side authorization", body: "Role, project, tenant and Enterprise entitlements are enforced by the server on every request." },
  { title: "Audit and provenance", body: "Decisions, submissions and access events are recorded with actor and source identity." },
  { title: "Ten languages", body: "Persian, English, German, Chinese, Arabic, French, Japanese, Korean, Russian and Turkish, with RTL support." },
];

const PLANS = [
  { name: "Engineering", body: "Project controls and scheduling delivery.", points: ["Scheduling core", "WBS & activities", "Progress and resources"] },
  { name: "Enterprise", body: "Organizational collaboration and governance.", points: ["Portfolios & projects", "Tasks & approvals", "Reports & audit"] },
  { name: "Platform", body: "Both environments with shared identity.", points: ["Single sign-in", "Personal workbench", "Cross-environment grants"] },
];

export function renderHome(ctx: PublicPageContext, host: HTMLElement): void {
  const hero = el("section", { class: "cubi-hero" });
  hero.append(
    el("span", { class: "cubi-eyebrow", text: "CUBI PLATFORM" }),
    el("h1", { text: ctx.t("page.home.title") }),
    el("p", { class: "lede", text: ctx.t("page.home.subtitle") + " Choose one entry point; the server decides which environments and roles are yours." }),
  );
  const actions = el("div", { class: "cubi-hero-actions" });
  const signIn = el("a", { class: "cubi-btn cubi-btn-primary", text: ctx.t("common.signIn") });
  signIn.href = `${BASE_PATH}/login/`;
  const request = el("a", { class: "cubi-btn cubi-btn-secondary", text: "Request access" });
  request.href = "/contact/";
  const help = el("a", { class: "cubi-btn cubi-btn-secondary", text: ctx.t("nav.help") });
  help.href = "https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm";
  help.target = "_blank";
  help.rel = "noopener noreferrer";
  actions.append(signIn, request, help);
  hero.append(actions);

  const tiles = el("div", { class: "cubi-hero-grid", attrs: { id: "environments" } });
  tiles.append(
    tile("CUBI Engineering", "Authoritative schedule, WBS, activities, progress, resources and cost."),
    tile("CUBI Enterprise", "Portfolios, projects, organization, tasks, workflows, approvals and reporting."),
    tile("Personal workbench", "One command centre for personal tasks, approvals and recent projects."),
    tile("Governed by default", "No client-side permission, no shadow calculation, no duplicated data owner."),
  );
  hero.append(tiles);

  const environments = el("section", { class: "cubi-public-section" });
  environments.append(el("h2", { text: "Two environments, one identity" }), el("p", { text: "The environments are independent products with separate ownership and release paths. The workbench is the coordination surface between them — not a third environment." }));
  const split = el("div", { class: "cubi-public-split" });
  split.append(
    publicCard("CUBI Engineering", "The single authority for schedule, CPM, activities, WBS, resource assignment, cost, progress and earned value. Enterprise consumes only versioned, permission-checked projections.", ["Schedule and critical path", "Activity and WBS records", "Resource and cost facts"]),
    publicCard("CUBI Enterprise", "Organizational collaboration: portfolios, project registers, teams, generic tasks, workflows, approvals, reports and access governance. It never recomputes Engineering metrics.", ["Portfolio and executive views", "Task and approval lifecycle", "Organization and access"]),
  );
  environments.append(split);

  const features = el("section", { class: "cubi-public-section" });
  features.append(el("h2", { text: "Built for governed delivery" }), el("p", { text: "Professional controls without inventing a second source of truth." }));
  const fgrid = el("div", { class: "cubi-public-split" });
  const fcol = el("div", { class: "cubi-public-card" });
  const fcol2 = el("div", { class: "cubi-public-card" });
  FEATURES.forEach((feature, index) => {
    const target = index % 2 === 0 ? fcol : fcol2;
    target.append(el("h3", { text: feature.title }), el("p", { text: feature.body, class: "desc" }));
  });
  fgrid.append(fcol, fcol2);
  features.append(fgrid);

  const plans = el("section", { class: "cubi-public-section" });
  plans.append(el("h2", { text: "Plans" }), el("p", { text: "Environment-based plans. Commercial terms are confirmed during access provisioning; no plan is activated by this page." }));
  const pgrid = el("div", { class: "cubi-public-split" });
  const planWrap = el("div", { class: "cubi-public-card" });
  for (const plan of PLANS) {
    const item = el("div", { class: "cubi-home-plan-item" });
    item.append(el("h3", { text: plan.name }), el("p", { text: plan.body, class: "desc" }));
    const list = el("ul");
    for (const point of plan.points) list.append(el("li", { text: point }));
    item.append(list);
    planWrap.append(item);
  }
  const security = publicCard("Security and support", "Sessions are server-issued. Enterprise roles are separate from project roles, and admin UI never grants authority. Support and access provisioning run through the product team.", ["Same-origin session and CSRF", "Tenant isolation", "Server-side IDOR checks", "Audited mutations"]);
  pgrid.append(planWrap, security);
  plans.append(pgrid);

  const footerCta = el("section", { class: "cubi-public-section" });
  footerCta.append(el("h2", { text: "Start from the workbench" }), el("p", { text: "Sign in with a provisioned account. New accounts are created by an administrator; self-service roles cannot create access." }));
  const row = el("div", { class: "cubi-row cubi-home-cta-row" });
  row.append(button(ctx.t("common.signIn"), () => ctx.navigate(`${BASE_PATH}/login/`), { variant: "primary" }));
  footerCta.append(row);
  host.append(hero, environments, features, plans, footerCta);
}

function tile(title: string, body: string): HTMLElement {
  return el("div", { class: "cubi-hero-tile" }, el("strong", { text: title }), el("span", { text: body }));
}

function publicCard(title: string, body: string, points: string[]): HTMLElement {
  const card = el("div", { class: "cubi-public-card" });
  card.append(el("h3", { text: title }), el("p", { text: body }));
  const list = el("ul");
  for (const point of points) list.append(el("li", { text: point }));
  card.append(list);
  return card;
}

export const homepageFeatureCount = FEATURES.length;
export const homepagePlanCount = PLANS.length;
export { uiLink };
