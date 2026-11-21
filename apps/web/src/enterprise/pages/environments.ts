import type { PageContext } from "../app.js";
import { BASE_PATH } from "../router.js";
import { environmentAccess, readLastEnvironment, rememberLastEnvironment } from "../session.js";
import { badge, el } from "../ui.js";
import { note, pageActions, section, sectionBody, testId } from "./shared.js";

/**
 * Page 5 — Environment selector.
 *
 * Engineering and Enterprise are separate products. This page opens one or the
 * other; it never renders Enterprise data inside the Engineering shell, and it
 * never recomputes Engineering facts.
 */

const BOUNDARIES: { domain: string; owner: string; enterpriseMode: string }[] = [
  { domain: "Schedule, CPM and critical path", owner: "CUBI Engineering", enterpriseMode: "Versioned read-only projection" },
  { domain: "WBS, activities and relationships", owner: "CUBI Engineering", enterpriseMode: "Versioned read-only projection" },
  { domain: "Progress, resources and cost", owner: "CUBI Engineering", enterpriseMode: "Versioned read-only projection" },
  { domain: "Earned value and indicators", owner: "CUBI Engineering", enterpriseMode: "Read from the EVM source; never recalculated" },
  { domain: "Portfolio, tasks and workflows", owner: "CUBI Enterprise", enterpriseMode: "Created and stored here" },
  { domain: "Organization, access and audit", owner: "CUBI Enterprise", enterpriseMode: "Server-side authorization and audit" },
];

export function renderEnvironments(ctx: PageContext, host: HTMLElement): void {
  const access = environmentAccess(ctx.session);
  const last = readLastEnvironment();

  const intro = section("Choose an environment", "The session is shared. The products, data ownership and release paths are not.");
  sectionBody(intro, note(last ? `Last opened environment on this device: ${last}.` : "No environment has been opened on this device yet."));
  host.append(intro);

  const grid = el("div", { class: "cubi-env-grid" });
  grid.append(
    envCard(
      ctx,
      "CUBI Engineering",
      "engineering",
      "Authoritative planning and delivery: schedule, CPM, WBS, activities, relationships, resources, cost, progress and earned value.",
      access.engineering.allowed ? "Your session can enter Engineering." : access.engineering.reason,
      access.engineering.allowed,
      "Open Engineering workspace",
      "/app?view=live",
      false,
    ),
    envCard(
      ctx,
      "CUBI Enterprise",
      "enterprise",
      "Organizational collaboration: portfolios, project register, teams, generic tasks, workflow, approvals, reports and access governance.",
      access.enterprise.allowed ? access.enterprise.reason : access.enterprise.reason,
      access.enterprise.allowed,
      "Open Enterprise dashboard",
      `${BASE_PATH}/enterprise/dashboard`,
      true,
    ),
  );
  testId(grid, "environments-grid");
  host.append(grid);

  const boundaries = section("Data ownership boundaries", "A page in Enterprise may display an Engineering fact only through an official, revision-stamped read model.");
  const table = el("div", { class: "cubi-table-wrap" });
  const node = el("table", { class: "cubi-table" });
  node.append(el("thead", {}, el("tr", {},
    el("th", { text: "Data domain" }),
    el("th", { text: "Authoritative owner" }),
    el("th", { text: "Enterprise access mode" }),
  )));
  const body = el("tbody");
  for (const row of BOUNDARIES) {
    body.append(el("tr", {},
      el("td", {}, el("strong", { text: row.domain })),
      el("td", {}, badge(row.owner, row.owner === "CUBI Engineering" ? "info" : "warning")),
      el("td", { text: row.enterpriseMode }),
    ));
  }
  node.append(body);
  table.append(node);
  sectionBody(boundaries, table);
  testId(boundaries, "environments-boundaries");
  host.append(boundaries);

  host.append(
    pageActions(
      linkButton("Personal workbench", `${BASE_PATH}/workbench/`),
      linkButton("Role & access", `${BASE_PATH}/roles/`),
      linkButton("Engineering workspace", "/app?view=live"),
    ),
  );
}

function envCard(
  ctx: PageContext,
  title: string,
  id: "engineering" | "enterprise",
  description: string,
  status: string,
  allowed: boolean,
  actionText: string,
  href: string,
  enterprise: boolean,
): HTMLElement {
  const card = el("div", { class: `cubi-env-card ${enterprise ? "enterprise" : ""}`.trim() });
  card.append(
    el("div", { class: "cubi-spread" }, el("h2", { text: title }), badge(allowed ? "available" : "restricted", allowed ? "success" : "warning")),
    el("p", { class: "desc", text: description }),
    el("div", { class: "cubi-env-meta" },
      el("span", {}, el("strong", { text: "Server decision: " }), status),
      el("span", { text: enterprise ? "Enterprise permissions are separate from project roles." : "Project permissions are evaluated by the Engineering server." }),
    ),
  );
  if (allowed) {
    const anchor = el("a", { class: "cubi-btn cubi-btn-primary", text: actionText });
    anchor.href = href;
    anchor.addEventListener("click", () => rememberLastEnvironment(id));
    card.append(el("div", { class: "cubi-env-actions" }, anchor));
  } else {
    // A denied environment has no entry button: the server gate is the
    // authority, and the UI must not offer a link that cannot succeed.
    const denied = el("p", { class: "cubi-field-hint", text: reasonText(status) });
    card.append(el("div", { class: "cubi-env-actions" }, denied));
  }
  testId(card, `environment-${id}`);
  return card;
}

function reasonText(status: string): string {
  return `Entry denied by the server: ${status}`;
}

function linkButton(text: string, href: string): HTMLElement {
  const anchor = el("a", { class: "cubi-btn cubi-btn-secondary", text });
  anchor.href = href;
  return anchor;
}
