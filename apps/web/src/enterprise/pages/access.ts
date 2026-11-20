import type { PageContext } from "../app.js";
import { probe, type CapabilityProbe } from "../api.js";
import { enterpriseTier } from "../session.js";
import { badge, el } from "../ui.js";
import {
  capabilityChip,
  connectionList,
  detailList,
  note,
  section,
  sectionBody,
  sourceState,
  testId,
} from "./shared.js";

/**
 * Page 9 — Organization and access center.
 *
 * Access is server-authoritative. This page reads the organization routes and
 * shows their real state. It never edits a grant client-side and never falls back
 * to a local user list. The verification panel documents the isolation tests the
 * server must pass.
 */

const ENTITIES: { key: string; title: string; endpoint: string; description: string }[] = [
  { key: "organizations", title: "Organizations", endpoint: "/api/enterprise/organizations", description: "Tenants and organizational units visible to this session." },
  { key: "users", title: "People", endpoint: "/api/enterprise/users", description: "Members of the organization. Email addresses are never invented." },
  { key: "teams", title: "Teams", endpoint: "/api/enterprise/teams", description: "Delivery and functional teams." },
  { key: "memberships", title: "Memberships", endpoint: "/api/enterprise/memberships", description: "User-to-team and user-to-organization membership." },
  { key: "invitations", title: "Invitations", endpoint: "/api/enterprise/invitations", description: "Pending invitations with expiry and inviter." },
  { key: "roles", title: "Roles", endpoint: "/api/enterprise/roles", description: "Enterprise role catalogue, separate from project roles." },
  { key: "grants", title: "Grants", endpoint: "/api/enterprise/grants", description: "Project and portfolio grants, including their source revision." },
  { key: "audit", title: "Audit", endpoint: "/api/enterprise/audit", description: "Access events with actor, target, decision and timestamp." },
];

const POLICY: { role: string; scope: string; permissions: string }[] = [
  { role: "enterprise_viewer", scope: "Tenant read", permissions: "Read dashboards, portfolio, projects, resources, reports" },
  { role: "enterprise_user", scope: "Tenant contribute", permissions: "Viewer plus tasks, feedback, workflow participation, knowledge contribution" },
  { role: "enterprise_admin", scope: "Tenant administer", permissions: "User plus organization, access, invitations, grants, audit and dashboard administration" },
];

export function renderAccess(ctx: PageContext, host: HTMLElement): void {
  const tier = enterpriseTier(ctx.session.roles);

  const sessionCard = section("This session's organization scope", "Values are read from the server session. The browser cannot change them.");
  sectionBody(sessionCard,
    detailList([
      ["User", ctx.session.user_id],
      ["Tenant", ctx.session.tenant_id],
      ["Enterprise tier", tier ?? "none"],
      ["Roles", ctx.session.roles.join(", ") || "—"],
      ["Session expires", ctx.session.expires_at],
    ]),
    note("Organization, team, grant and audit writes are accepted only from an authorized server session. This page has no client-side permission check that could be bypassed.", "warning"),
  );
  testId(sessionCard, "access-session");
  host.append(sessionCard);

  const connections = section("Organization API status", "Each route is probed for this exact session. A missing route is a real capability gap, not an empty organization.");
  const connHost = el("div");
  sectionBody(connections, connHost);
  testId(connections, "access-connections");
  host.append(connections);

  const policy = section("Enterprise role policy (reference)", "This is the product policy definition, not a statement that the current session holds the role.");
  const policyTable = el("div", { class: "cubi-table-wrap" });
  const node = el("table", { class: "cubi-table" });
  node.append(el("thead", {}, el("tr", {}, el("th", { text: "Role" }), el("th", { text: "Scope" }), el("th", { text: "Server permissions" }), el("th", { text: "This session" }))));
  const body = el("tbody");
  for (const row of POLICY) {
    const granted = ctx.session.roles.includes(row.role);
    body.append(el("tr", {},
      el("td", {}, el("strong", { text: row.role })),
      el("td", { text: row.scope }),
      el("td", { text: row.permissions }),
      el("td", {}, badge(granted ? "granted" : "not granted", granted ? "success" : "neutral")),
    ));
  }
  node.append(body);
  policyTable.append(node);
  sectionBody(policy, policyTable);
  testId(policy, "access-policy");
  host.append(policy);

  const entities = section("Organization registers", "Every register below reports its real source state. No row is fabricated to make the page look populated.");
  const entityHost = el("div");
  sectionBody(entities, entityHost);
  testId(entities, "access-registers");
  host.append(entities);

  const isolation = section("Tenant isolation and IDOR verification", "The server must enforce these checks on every request, independent of this UI.");
  const checks = el("div", { class: "cubi-table-wrap" });
  const checkTable = el("table", { class: "cubi-table" });
  checkTable.append(el("thead", {}, el("tr", {}, el("th", { text: "Check" }), el("th", { text: "Request" }), el("th", { text: "Expected" }), el("th", { text: "State" }))));
  const checkBody = el("tbody");
  const rows = [
    { check: "Cross-tenant read", request: "GET /api/enterprise/teams?tenant_id=other", expected: "403 or tenant-scoped empty set" },
    { check: "IDOR on grant", request: "PATCH /api/enterprise/grants/{unknown}", expected: "404, never 200" },
    { check: "Role escalation", request: "PATCH /api/enterprise/users/{self} {role: enterprise_admin}", expected: "403 unless authorized administrator" },
    { check: "Invitation replay", request: "POST /api/enterprise/invitations/{id}/accept twice", expected: "409 on second use" },
    { check: "Audit tamper", request: "DELETE /api/enterprise/audit/{id}", expected: "405 or 403; audit is append-only" },
    { check: "Cookie-only authority", request: "Request with forged header role", expected: "Header ignored; session roles used" },
  ];
  for (const row of rows) {
    checkBody.append(el("tr", {},
      el("td", {}, el("strong", { text: row.check })),
      el("td", {}, el("code", { class: "cubi-mono", text: row.request })),
      el("td", { text: row.expected }),
      el("td", {}, badge("pending server route", "warning")),
    ));
  }
  checkTable.append(checkBody);
  checks.append(checkTable);
  testId(checks, "access-isolation");
  sectionBody(isolation, checks, note("These checks are part of the access contract. They are reported as pending because the organization API is not mounted in this build; the UI does not claim they passed."));
  host.append(isolation);

  void loadEntities(ctx, connHost, entityHost);
}

async function loadEntities(ctx: PageContext, connHost: HTMLElement, entityHost: HTMLElement): Promise<void> {
  const results = await Promise.all(ENTITIES.map(async (entity) => ({ entity, probe: await probe(entity.endpoint) })));
  connHost.replaceChildren(connectionList(results.map(({ entity, probe: state }) => ({ label: entity.title, probe: state })), ctx.t));

  const cards = el("div", { class: "cubi-grid cubi-grid-2" });
  for (const { entity, probe: state } of results) {
    cards.append(entityCard(ctx, entity, state));
  }
  entityHost.replaceChildren(cards);
}

function entityCard(ctx: PageContext, entity: { key: string; title: string; endpoint: string; description: string }, state: CapabilityProbe): HTMLElement {
  const card = section(entity.title, entity.description);
  const body = el("div", {});
  body.append(
    el("div", { class: "cubi-row" }, badge(`${state.status || "—"}`, state.state === "available" ? "success" : state.state === "forbidden" ? "warning" : "neutral"), capabilityChip(state, ctx.t), el("span", { class: "cubi-field-hint", text: state.path })),
  );
  if (state.state === "available") {
    body.append(el("p", { class: "cubi-field-hint", text: "The route responded. Table rendering for this register is provided by the organization read model; no local records are shown." }));
  } else {
    body.append(sourceState(state, ctx.t, { title: entity.title, source: entity.title + " read model", detail: "Management actions stay disabled until the server route is mounted." }));
  }
  sectionBody(card, body);
  testId(card, `access-${entity.key}`);
  return card;
}
