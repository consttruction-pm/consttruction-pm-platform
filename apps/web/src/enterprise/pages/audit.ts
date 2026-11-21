/**
 * Page 24 — Audit trail.
 *
 * The audit table is append-only on the server: this page reads it and offers
 * no write control. If the route is not mounted the page says so instead of
 * showing a substitute history.
 */

import type { PageContext } from "../app.js";
import { api, probe } from "../api.js";
import { badge, el } from "../ui.js";
import { connectionRow, note, section, sectionBody, sourceState, testId } from "./shared.js";
import type { CapabilityProbe } from "../api.js";

type AuditEvent = {
  event_id: string;
  actor_id: string;
  action: string;
  target_kind: string;
  target_id: string;
  decision: string;
  occurred_at: string;
  detail?: Record<string, unknown>;
};

export function renderAudit(ctx: PageContext, host: HTMLElement): void {
  const intro = section("Append-only history", "Every Enterprise write records the actor, the action, the target and the decision.");
  const help = el("a", { class: "cubi-btn cubi-btn-ghost", text: "Open the Help topic", attrs: { target: "_blank", rel: "noopener noreferrer" } });
  help.href = "https://docs.oracle.com/cd/G48897_01/p6help/en/102813.htm";
  sectionBody(intro,
    el("p", { class: "cubi-field-hint", text: "Help topic: About Table Auditing" }),
    note("There is no delete or edit control on this page. The server exposes the trail read-only; a 405 is the expected answer to a write.", "warning"),
    el("div", { class: "cubi-row" }, help),
  );
  testId(intro, "audit-intro");
  host.append(intro);

  const trail = section("Recent events", "The newest events first, bounded by the server limit.");
  const trailHost = el("div", { class: "cubi-loading" }, el("div", { class: "cubi-spinner" }), el("span", { text: ctx.t("common.loading") }));
  const refresh = el("button", { class: "cubi-btn cubi-btn-secondary", text: ctx.t("common.refresh"), attrs: { type: "button" } });
  refresh.addEventListener("click", () => { void load(); });
  sectionBody(trail, el("div", { class: "cubi-row" }, refresh), trailHost);
  testId(trail, "audit-events");
  host.append(trail);

  const capability = section("Connection", "The server answer for the audit route is reported as it is.");
  const capabilityHost = el("div");
  sectionBody(capability, capabilityHost);
  testId(capability, "audit-capability");
  host.append(capability);

  let state: CapabilityProbe | null = null;

  const load = async (): Promise<void> => {
    state = await probe("/api/enterprise/audit");
    if (state.state !== "available") {
      trailHost.replaceChildren(sourceState(state, ctx.t, {
        title: "The audit trail is not connected",
        source: "Enterprise audit API",
        retry: () => { void load(); },
      }));
      capabilityHost.replaceChildren(connectionRow("audit", state, ctx.t));
      return;
    }
    try {
      const payload = await api.enterpriseList("audit") as unknown as { items: AuditEvent[] };
      const items = payload.items ?? [];
      trailHost.replaceChildren(items.length ? eventTable(items) : el("p", { class: "cubi-field-hint", text: "The audit route answered with zero events for this tenant." }));
    } catch (error) {
      trailHost.replaceChildren(el("p", { class: "cubi-alert cubi-alert-error", text: String(error) }));
    }
    capabilityHost.replaceChildren(connectionRow("audit", state, ctx.t));
  };

  void load();
}

function eventTable(items: AuditEvent[]): HTMLElement {
  const wrap = el("div", { class: "cubi-table-wrap" });
  testId(wrap, "audit-table");
  const table = el("table", { class: "cubi-table" });
  table.append(el("thead", {}, el("tr", {},
    el("th", { text: "When" }),
    el("th", { text: "Actor" }),
    el("th", { text: "Action" }),
    el("th", { text: "Target" }),
    el("th", { text: "Decision" }),
  )));
  const body = el("tbody");
  for (const event of items) {
    body.append(el("tr", {},
      el("td", { text: event.occurred_at }),
      el("td", { text: event.actor_id }),
      el("td", { text: event.action }),
      el("td", {}, el("strong", { text: event.target_kind }), el("div", { class: "cubi-field-hint", text: event.target_id })),
      el("td", {}, badge(event.decision, event.decision === "allowed" ? "success" : "warning")),
    ));
  }
  table.append(body);
  wrap.append(table);
  return wrap;
}
