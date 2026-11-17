import test from "node:test";
import assert from "node:assert/strict";
import {
  displaySummaryMetric,
  mapEnterprisePortletState,
  orderDashboardCatalog,
  reorderDashboardPortlets,
  supportedDashboardPortlets,
  validateDashboardLayout,
  type EnterpriseDashboardCatalogItem,
  type EnterpriseDashboardPortlet,
} from "./enterprise-dashboard.js";

function portlet(
  instance_id: string,
  x: number,
  y: number,
  w: number,
  h = 4,
  type_id: EnterpriseDashboardPortlet["type_id"] = "portfolio-control-snapshot.v1",
): EnterpriseDashboardPortlet {
  return {
    instance_id,
    type_id,
    contract_version: type_id,
    config: { portfolio_id: "portfolio-1" },
    layout: { x, y, w, h },
  };
}

function catalogItem(id: string, title: string, order: number): EnterpriseDashboardCatalogItem {
  return {
    dashboard: {
      contract_version: "cubi-enterprise-dashboard.v1",
      dashboard_id: id,
      tenant_id: "tenant-1",
      context: "enterprise_home",
      context_portfolio_id: null,
      owner_user_id: "user-1",
      title,
      description: "",
      status: "active",
      visibility: "private",
      shared_user_ids: [],
      shared_role_ids: [],
      portlets: [],
      filters: [],
      revision: 1,
      created_at: "2026-11-17T00:00:00Z",
      updated_at: null,
      restrict_filter_override: false,
      max_rows_per_portlet: 100,
    },
    revision: 1,
    display_order: order,
  };
}

test("dashboard catalog order is deterministic by order, title and id", () => {
  const ordered = orderDashboardCatalog([
    catalogItem("z", "Zulu", 1),
    catalogItem("b", "Beta", 0),
    catalogItem("a", "Alpha", 0),
  ]);
  assert.deepEqual(ordered.map((item) => item.dashboard.dashboard_id), ["a", "b", "z"]);
});

test("only the two registered source-backed portlet types are selectable", () => {
  const supported = portlet("supported", 0, 0, 12);
  const unknown = { ...supported, instance_id: "unknown", type_id: "unregistered.v9" } as unknown as EnterpriseDashboardPortlet;
  assert.deepEqual(supportedDashboardPortlets([supported, unknown]).map((item) => item.instance_id), ["supported"]);
});

test("layout validation enforces bounds, 12-portlet cap and no overlap", () => {
  assert.equal(validateDashboardLayout([portlet("left", 0, 0, 6), portlet("right", 6, 0, 6)]), true);
  assert.equal(validateDashboardLayout([portlet("a", 0, 0, 12), portlet("b", 0, 2, 12)]), false);
  assert.equal(validateDashboardLayout([portlet("bad", 6, 0, 12)]), false);
  assert.equal(validateDashboardLayout(Array.from({ length: 13 }, (_, i) => portlet(String(i), 0, i * 4, 12))), false);
});

test("portlet state mapping preserves permission, missing, filtered, stale and empty states", () => {
  const base = { data: { projects: [{ project_id: "p1" }] }, freshness_state: "fresh" as const, filtered_out: false };
  assert.equal(mapEnterprisePortletState(base), "ready");
  assert.equal(mapEnterprisePortletState({ ...base, data: null }), "missing");
  assert.equal(mapEnterprisePortletState({ ...base, freshness_state: "stale" }), "stale");
  assert.equal(mapEnterprisePortletState({ ...base, filtered_out: true }), "filtered");
  assert.equal(mapEnterprisePortletState({ ...base, data: { projects: [] } }), "empty");
  assert.equal(mapEnterprisePortletState(base, "PROJECT_READ_FORBIDDEN"), "permission_denied");
  assert.equal(mapEnterprisePortletState(base, "SOURCE_FAILURE"), "error");
});

test("missing summary metrics are shown as unavailable, never fabricated zeroes", () => {
  assert.equal(displaySummaryMetric(undefined, "total_projects"), "—");
  assert.equal(displaySummaryMetric({}, "total_projects"), "—");
  assert.equal(displaySummaryMetric({ total_projects: null }, "total_projects"), "—");
  assert.equal(displaySummaryMetric({ total_projects: 0 }, "total_projects"), "0");
  assert.equal(displaySummaryMetric({ total_projects: 12 }, "total_projects"), "12");
});


test("dashboard layout ordering supports bounded move-up and move-down operations", () => {
  assert.deepEqual(reorderDashboardPortlets(["a", "b", "c"], 2, 0), ["c", "a", "b"]);
  assert.deepEqual(reorderDashboardPortlets(["a", "b", "c"], 0, 2), ["b", "c", "a"]);
  assert.deepEqual(reorderDashboardPortlets(["a", "b"], -1, 1), ["a", "b"]);
  assert.deepEqual(reorderDashboardPortlets(["a", "b"], 0, 2), ["a", "b"]);
});
