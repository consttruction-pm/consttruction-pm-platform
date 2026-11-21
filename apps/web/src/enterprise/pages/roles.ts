import type { PageContext } from "../app.js";
import { BASE_PATH } from "../router.js";
import { ENTERPRISE_ROLES, enterpriseTier, environmentAccess } from "../session.js";
import { badge, el } from "../ui.js";
import { detailList, note, pageActions, section, sectionBody, selectControl, testId } from "./shared.js";

/**
 * Page 3 — Role and permission selection.
 *
 * The list below reports the roles the server returned on the session. Choosing
 * a preferred view is a convenience preference, not a grant; every API call is
 * still authorized on the server using the session roles.
 */

const VIEW_KEY = "cubi.enterprise.preferred-view";
type PreferredView = "engineering" | "enterprise" | "personal";

export function renderRoles(ctx: PageContext, host: HTMLElement): void {
  const access = environmentAccess(ctx.session);
  const tier = enterpriseTier(ctx.session.roles);

  const intro = section("What this session may do", "Entitlements come from the server session. This page never creates, escalates or caches a permission.");
  const overview = el("div", { class: "cubi-grid cubi-grid-3" });
  overview.append(
    accessCard("CUBI Engineering", access.engineering.allowed, "Project role required", access.engineering.reason, "engineering"),
    accessCard("CUBI Enterprise", access.enterprise.allowed, tier ? `Enterprise ${tier}` : "No Enterprise entitlement", access.enterprise.reason, "enterprise"),
    accessCard("Personal workbench", true, "Signed-in account", "The workbench is a personal coordination surface. It does not grant access to any project or environment by itself.", "personal"),
  );
  sectionBody(intro, overview);
  testId(intro, "roles-access");
  host.append(intro);

  const assigned = section("Granted roles on this session", "Sorted exactly as the server returned them.");
  const roleRows = el("div", { class: "cubi-chip-row" });
  for (const role of ctx.session.roles) {
    const enterprise = ENTERPRISE_ROLES.includes(role as (typeof ENTERPRISE_ROLES)[number]);
    roleRows.append(badge(role, enterprise ? "warning" : "info"));
  }
  const matrix = el("div", { class: "cubi-table-wrap" });
  const table = el("table", { class: "cubi-table" });
  table.append(
    el("thead", {}, el("tr", {}, el("th", { text: "Enterprise role" }), el("th", { text: "State" }), el("th", { text: "What the server may allow" }))),
  );
  const body = el("tbody");
  const meanings: Record<string, string> = {
    enterprise_admin: "Manage organization, access, dashboards and approvals across the tenant.",
    enterprise_user: "Contribute tasks, workflows, feedback and project participation.",
    enterprise_viewer: "Read enterprise dashboards, portfolio and reports.",
  };
  for (const role of ENTERPRISE_ROLES) {
    const granted = ctx.session.roles.includes(role);
    body.append(
      el("tr", {},
        el("td", {}, el("strong", { text: role })),
        el("td", {}, badge(granted ? ctx.t("status.allowed") : ctx.t("status.denied"), granted ? "success" : "neutral")),
        el("td", { text: meanings[role] ?? "" }),
      ),
    );
  }
  table.append(body);
  matrix.append(table);
  sectionBody(assigned, roleRows, matrix);
  testId(assigned, "roles-matrix");
  host.append(assigned);

  const viewCard = section("Preferred entry view", "This preference is stored on this device only. It changes where the workbench opens, not what the server authorizes.");
  const stored = readView();
  const select = testId(selectControl([
    { value: "personal", label: "Personal workbench" },
    { value: "enterprise", label: "Enterprise dashboard" },
    { value: "engineering", label: "Engineering workspace" },
  ], stored, (value) => { writeView(value as PreferredView); }), "roles-view-select");
  const continueButton = el("button", { class: "cubi-btn cubi-btn-primary", text: "Continue", attrs: { type: "button" } });
  continueButton.addEventListener("click", () => {
    const view = readView();
    if (view === "engineering") window.location.assign("/app?view=live");
    else if (view === "enterprise") window.location.assign(`${BASE_PATH}/enterprise/dashboard/`);
    else window.location.assign("/workbench/");
  });
  sectionBody(
    viewCard,
    el("div", { class: "cubi-form-grid" },
      el("label", { class: "cubi-field" }, el("span", { class: "cubi-field-label", text: "Entry view" }), select),
    ),
    note("Administrators grant Enterprise roles. If a role is missing, request it through your access process; this page cannot add it.", "warning"),
  );
  testId(viewCard, "roles-preference");
  host.append(viewCard);

  host.append(
    pageActions(
      continueButton,
      linkButton("Open Engineering workspace", "/app/"),
      linkButton("Open Enterprise dashboard", `${BASE_PATH}/enterprise/dashboard/`),
      linkButton("Personal workbench", `${BASE_PATH}/workbench/`),
    ),
  );
}

function accessCard(title: string, allowed: boolean, stateText: string, reason: string, kind: string): HTMLElement {
  const card = el("div", { class: `cubi-env-card ${kind === "enterprise" ? "enterprise" : ""}`.trim() });
  card.append(
    el("div", { class: "cubi-spread" }, el("h2", { text: title }), badge(allowed ? "available" : "restricted", allowed ? "success" : "warning")),
    el("p", { class: "desc", text: stateText }),
    el("p", { class: "cubi-field-hint", text: reason }),
  );
  return card;
}

function linkButton(text: string, href: string): HTMLElement {
  const anchor = el("a", { class: "cubi-btn cubi-btn-secondary", text });
  anchor.href = href;
  return anchor;
}

function readView(): PreferredView {
  try {
    const value = window.localStorage.getItem(VIEW_KEY);
    if (value === "engineering" || value === "enterprise") return value;
  } catch {
    // Ignore unavailable storage.
  }
  return "personal";
}

function writeView(value: PreferredView): void {
  try {
    window.localStorage.setItem(VIEW_KEY, value);
  } catch {
    // Non-fatal preference.
  }
}

export { detailList };
