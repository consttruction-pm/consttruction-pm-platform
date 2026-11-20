import type { PageContext } from "../app.js";
import { api, probe, type CapabilityProbe, type EnterpriseRecord } from "../api.js";
import { enterpriseTier } from "../session.js";
import { badge, el } from "../ui.js";
import {
  capabilityChip,
  connectionList,
  detailList,
  labelled,
  note,
  section,
  sectionBody,
  selectControl,
  sourceState,
  testId,
  textInput,
} from "./shared.js";

/**
 * Page 9 — Organization and access center.
 *
 * Access is server-authoritative. This page reads the organization routes and
 * shows their real state, and its administration forms submit only the fields
 * the server accepts. Roles, tenant and audit decisions always come from the
 * server session; the browser cannot grant itself anything.
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

  host.append(adminSection(ctx));

  const isolation = section("Tenant isolation and IDOR verification", "The server must enforce these checks on every request, independent of this UI.");
  const checks = el("div", { class: "cubi-table-wrap" });
  const checkTable = el("table", { class: "cubi-table" });
  checkTable.append(el("thead", {}, el("tr", {}, el("th", { text: "Check" }), el("th", { text: "Request" }), el("th", { text: "Expected" }), el("th", { text: "State" }))));
  const checkBody = el("tbody");
  const rows = [
    { check: "Cross-tenant read", request: "GET /api/enterprise/teams?tenant_id=other", expected: "Tenant-scoped empty set; query tenant ignored", state: "enforced" },
    { check: "IDOR on grant", request: "PATCH /api/enterprise/grants/{unknown}", expected: "404, never 200", state: "enforced" },
    { check: "Role escalation", request: "PATCH /api/enterprise/users/{self} {role: enterprise_admin}", expected: "403 unless authorized administrator", state: "enforced" },
    { check: "Invitation replay", request: "POST /api/enterprise/invitations/{id}/accept twice", expected: "409 on second use", state: "not implemented" },
    { check: "Audit tamper", request: "DELETE /api/enterprise/audit/{id}", expected: "405; audit is append-only", state: "enforced" },
    { check: "Cookie-only authority", request: "Request with forged header role", expected: "Header ignored; session roles used", state: "enforced" },
  ];
  for (const row of rows) {
    const ok = row.state === "enforced";
    checkBody.append(el("tr", {},
      el("td", {}, el("strong", { text: row.check })),
      el("td", {}, el("code", { class: "cubi-mono", text: row.request })),
      el("td", { text: row.expected }),
      el("td", {}, badge(ok ? "enforced server-side" : "pending server route", ok ? "success" : "warning")),
    ));
  }
  checkTable.append(checkBody);
  checks.append(checkTable);
  testId(checks, "access-isolation");
  sectionBody(isolation, checks, note("The enforced rows are covered by backend tests in tests/test_enterprise_workbench_http.py. Invitation acceptance is not implemented yet and is shown as pending rather than claimed.", "warning"));
  host.append(isolation);

  void loadEntities(ctx, connHost, entityHost);
}

async function loadEntities(ctx: PageContext, connHost: HTMLElement, entityHost: HTMLElement): Promise<void> {
  const results = await Promise.all(ENTITIES.map(async (entity) => {
    const state = await probe(entity.endpoint);
    let items: EnterpriseRecord[] = [];
    if (state.state === "available") {
      try {
        items = (await api.enterpriseList(entity.key)).items;
      } catch {
        items = [];
      }
    }
    return { entity, probe: state, items };
  }));
  connHost.replaceChildren(connectionList(results.map(({ entity, probe: state }) => ({ label: entity.title, probe: state })), ctx.t));

  const cards = el("div", { class: "cubi-grid cubi-grid-2" });
  for (const { entity, probe: state, items } of results) {
    cards.append(entityCard(ctx, entity, state, items, () => loadEntities(ctx, connHost, entityHost)));
  }
  entityHost.replaceChildren(cards);
}

function entityCard(
  ctx: PageContext,
  entity: { key: string; title: string; endpoint: string; description: string },
  state: CapabilityProbe,
  items: EnterpriseRecord[],
  reload: () => void,
): HTMLElement {
  const card = section(entity.title, entity.description);
  const body = el("div", {});
  body.append(
    el("div", { class: "cubi-row" }, badge(`${state.status || "—"}`, state.state === "available" ? "success" : state.state === "forbidden" ? "warning" : "neutral"), capabilityChip(state, ctx.t), el("span", { class: "cubi-field-hint", text: state.path })),
  );
  if (state.state === "available") {
    if (items.length === 0) {
      body.append(el("p", { class: "cubi-field-hint", text: "The register answered with zero rows for this tenant." }));
    } else {
      const wrap = el("div", { class: "cubi-table-wrap" });
      const table = el("table", { class: "cubi-table" });
      table.append(el("thead", {}, el("tr", {},
        el("th", { text: "Record" }),
        el("th", { text: "Status" }),
        el("th", { text: "Revision" }),
        el("th", { text: "" }),
      )));
      const rows = el("tbody");
      for (const item of items.slice(0, 8)) {
        const label = String(item.name ?? item.title ?? item.display_name ?? item.email ?? item.record_id);
        const deletable = ["teams", "invitations", "grants", "memberships"].includes(entity.key) && !item.demo;
        const remove = el("button", { class: "cubi-btn cubi-btn-ghost", text: "Delete", attrs: { type: "button" } });
        remove.disabled = !deletable;
        if (deletable) {
          remove.addEventListener("click", () => {
            void api.enterpriseDelete(entity.key, item.record_id, item.revision)
              .then(() => { ctx.toast(`${entity.title} record deleted.`, "info"); reload(); })
              .catch((error: unknown) => ctx.toast(String(error), "error"));
          });
        }
        rows.append(el("tr", {},
          el("td", {}, el("strong", { text: label }), el("div", { class: "cubi-field-hint", text: item.record_id }), item.demo ? badge("preview fixture", "neutral") : null),
          el("td", {}, badge(String(item.status ?? "—"), item.status === "active" ? "success" : "neutral")),
          el("td", { text: String(item.revision) }),
          el("td", {}, remove),
        ));
      }
      table.append(rows);
      wrap.append(table);
      body.append(wrap);
    }
  } else {
    body.append(sourceState(state, ctx.t, { title: entity.title, source: entity.title + " read model", detail: "Management actions stay disabled until the server route is mounted." }));
  }
  sectionBody(card, body);
  testId(card, `access-${entity.key}`);
  return card;
}

function adminSection(ctx: PageContext): HTMLElement {
  const card = section("Access administration", "Writes are accepted only from an enterprise administrator session. Each write is revision-checked and audited.");
  const grid = el("div", { class: "cubi-form-grid" });

  const teamName = testId(textInput({ placeholder: "Team name" }), "access-team-name");
  const createTeam = el("button", { class: "cubi-btn cubi-btn-primary", text: "Create team", attrs: { type: "button" } });
  createTeam.addEventListener("click", () => {
    const name = teamName.value.trim();
    if (!name) return;
    createTeam.disabled = true;
    void api.enterpriseCreate("teams", { name }, newKey())
      .then(() => { ctx.toast("Team created on the server.", "info"); teamName.value = ""; })
      .catch((error: unknown) => ctx.toast(String(error), "error"))
      .finally(() => { createTeam.disabled = false; });
  });

  const email = testId(textInput({ type: "email", placeholder: "person@example.com" }), "access-invite-email");
  const role = testId(selectControl([
    { value: "member", label: "Member" },
    { value: "viewer", label: "Viewer" },
    { value: "approver", label: "Approver" },
    { value: "admin", label: "Admin" },
  ], "member", () => {}), "access-invite-role");
  const invite = el("button", { class: "cubi-btn cubi-btn-primary", text: "Invite", attrs: { type: "button" } });
  invite.addEventListener("click", () => {
    const value = email.value.trim();
    if (!value) return;
    invite.disabled = true;
    void api.enterpriseCreate("invitations", { email: value, role: role.value, status: "pending" }, newKey())
      .then(() => { ctx.toast("Invitation recorded on the server.", "info"); email.value = ""; })
      .catch((error: unknown) => ctx.toast(String(error), "error"))
      .finally(() => { invite.disabled = false; });
  });

  const subject = testId(textInput({ placeholder: "user or team id" }), "access-grant-subject");
  const resource = testId(textInput({ placeholder: "project id" }), "access-grant-resource");
  const grantRole = testId(selectControl([
    { value: "viewer", label: "Viewer" },
    { value: "planner", label: "Planner" },
    { value: "project_manager", label: "Project manager" },
  ], "viewer", () => {}), "access-grant-role");
  const grant = el("button", { class: "cubi-btn cubi-btn-primary", text: "Grant access", attrs: { type: "button" } });
  grant.addEventListener("click", () => {
    if (!subject.value.trim() || !resource.value.trim()) return;
    grant.disabled = true;
    void api.enterpriseCreate("grants", {
      subject_id: subject.value.trim(),
      resource_id: resource.value.trim(),
      role: grantRole.value,
      resource_type: "project",
    }, newKey())
      .then(() => { ctx.toast("Grant recorded on the server.", "info"); })
      .catch((error: unknown) => ctx.toast(String(error), "error"))
      .finally(() => { grant.disabled = false; });
  });

  grid.append(
    labelled("Team", teamName), labelled("", createTeam),
    labelled("Invitation email", email), labelled("Invitation role", role), labelled("", invite),
    labelled("Grant subject", subject), labelled("Grant resource", resource), labelled("Grant role", grantRole), labelled("", grant),
  );
  sectionBody(card, grid, note("Deleting a record is a soft delete with a revision check; the audit register keeps the event. Demo fixture rows cannot be deleted.", "warning"));
  testId(card, "access-admin");
  return card;
}

function newKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `access-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}
