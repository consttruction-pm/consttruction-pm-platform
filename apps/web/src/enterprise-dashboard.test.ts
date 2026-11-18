import test from "node:test";
import assert from "node:assert/strict";
import {
  displaySummaryMetric,
  dashboardDisplayMoveTarget,
  dashboardShareAccountOptions,
  authorizedDashboardFilterOptions,
  dashboardFilterDefinition,
  ENTERPRISE_DASHBOARD_FILTER_CATALOG,
  effectiveDashboardPortletLimit,
  mapEnterprisePortletState,
  moveDashboardPortletHorizontally,
  moveDashboardPortletToPosition,
  moveDashboardPortletVertically,
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


test("dashboard share account search is active-only and excludes already shared users", () => {
  const accounts = [
    { user_id: "u-1", display_name: "Alice Smith", email: "alice@example.test", active: true },
    { user_id: "u-2", display_name: "Bob Jones", email: "bob@example.test", active: true },
    { user_id: "u-3", display_name: "Alice Disabled", email: "disabled@example.test", active: false },
  ];
  assert.deepEqual(dashboardShareAccountOptions(accounts, " ALICE ", ["u-1"]), []);
  assert.deepEqual(dashboardShareAccountOptions(accounts, "bob@example", []), [accounts[1]]);
  assert.deepEqual(dashboardShareAccountOptions(accounts, "u-3", []), []);
  assert.deepEqual(dashboardShareAccountOptions(accounts, "", ["u-1"]), [accounts[1]]);
});

test("displayed dashboard move targets use the rendered sorted order at first, middle and last positions", () => {
  const items = [
    catalogItem("last", "Last", 2),
    catalogItem("first", "First", 0),
    catalogItem("middle", "Middle", 1),
  ];
  assert.equal(dashboardDisplayMoveTarget(items, "first", "up"), null);
  assert.equal(dashboardDisplayMoveTarget(items, "first", "down"), 1);
  assert.equal(dashboardDisplayMoveTarget(items, "middle", "up"), 0);
  assert.equal(dashboardDisplayMoveTarget(items, "middle", "down"), 2);
  assert.equal(dashboardDisplayMoveTarget(items, "last", "up"), 1);
  assert.equal(dashboardDisplayMoveTarget(items, "last", "down"), null);
  assert.equal(dashboardDisplayMoveTarget(items, "missing", "up"), null);
});

test("only the two registered source-backed portlet types are selectable", () => {
  const supported = portlet("supported", 0, 0, 12);
  const unknown = { ...supported, instance_id: "unknown", type_id: "unregistered.v9" } as unknown as EnterpriseDashboardPortlet;
  assert.deepEqual(supportedDashboardPortlets([supported, unknown]).map((item) => item.instance_id), ["supported"]);
});

test("layout validation follows the effective tenant portlet limit with 12 as legacy fallback", () => {
  const eight = Array.from({ length: 8 }, (_, i) => portlet(String(i), 0, i * 4, 12));
  const twelve = Array.from({ length: 12 }, (_, i) => portlet(String(i), 0, i * 4, 12));
  const twenty = Array.from({ length: 20 }, (_, i) => portlet(String(i), 0, i * 4, 12));
  assert.equal(effectiveDashboardPortletLimit(undefined), 12);
  assert.equal(effectiveDashboardPortletLimit({ max_portlets: 8 }), 8);
  assert.equal(effectiveDashboardPortletLimit({ max_portlets: 12 }), 12);
  assert.equal(effectiveDashboardPortletLimit({ max_portlets: 20 }), 20);
  assert.equal(effectiveDashboardPortletLimit({ max_portlets: 0 }), 12);
  assert.equal(validateDashboardLayout(eight, 8), true);
  assert.equal(validateDashboardLayout(twelve, 8), false);
  assert.equal(validateDashboardLayout(twelve, 12), true);
  assert.equal(validateDashboardLayout(twenty, 20), true);
  assert.equal(validateDashboardLayout(twenty, 12), false);

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

test("dashboard layout preserves two-dimensional positions and supports bounded vertical moves", () => {
  const items = [portlet("top", 0, 0, 6), portlet("bottom", 0, 4, 6), portlet("right", 6, 0, 6)];
  const movedDown = moveDashboardPortletVertically(items, 0, "down");
  assert.deepEqual(movedDown.map((item) => item.layout.y), [4, 0, 0]);
  assert.equal(validateDashboardLayout(movedDown), true);
  const movedUp = moveDashboardPortletVertically(movedDown, 0, "up");
  assert.deepEqual(movedUp.map((item) => item.layout.y), [0, 4, 0]);
  assert.equal(validateDashboardLayout(movedUp), true);
  assert.deepEqual(moveDashboardPortletVertically(items, 0, "up").map((item) => item.layout.y), [0, 4, 0]);
  const wideCollision = [portlet("narrow", 0, 0, 6), portlet("wide", 0, 4, 12)];
  assert.deepEqual(moveDashboardPortletVertically(wideCollision, 0, "down").map((item) => item.layout.y), [0, 4]);
});

test("dashboard layout supports bounded left/right movement and preserves valid non-overlapping columns", () => {
  const items = [portlet("left", 0, 0, 6), portlet("right", 6, 0, 6)];
  const moved = moveDashboardPortletHorizontally(items, 0, "right");
  assert.deepEqual(moved.map((item) => item.layout.x), [6, 0]);
  assert.equal(validateDashboardLayout(moved), true);
  assert.deepEqual(moveDashboardPortletHorizontally(items, 0, "left").map((item) => item.layout.x), [0, 6]);
  assert.deepEqual(moveDashboardPortletHorizontally(items, 0, "right").map((item) => item.layout.x), [6, 0]);
  assert.deepEqual(moveDashboardPortletHorizontally(items, 9, "right").map((item) => item.layout.x), [0, 6]);
  const wide = [portlet("wide", 0, 0, 12)];
  assert.deepEqual(moveDashboardPortletHorizontally(wide, 0, "right")[0].layout, wide[0].layout);
});

test("Filter By pickers expose only portfolio and project identifiers already present in authorized dashboard reads", () => {
  const dashboard = catalogItem("d-1", "Board", 0).dashboard;
  dashboard.portlets = [
    portlet("snapshot-a", 0, 0, 12),
    { ...portlet("snapshot-b", 0, 4, 12), config: { portfolio_id: "portfolio-2" } },
  ];
  const read = {
    portlets: [
      {
        data: { projects: [
          { project_id: "p-2", project_name: "Bridge" },
          { project_id: "p-1", name: "Road" },
          { project_id: "p-2", project_name: "Bridge duplicate" },
          { name: "Missing identifier" },
        ] },
      },
      { data: { projects: [{ project_id: "p-3" }] } },
    ],
  } as unknown as import("./enterprise-dashboard.js").EnterpriseDashboardRead;

  assert.deepEqual(authorizedDashboardFilterOptions("portfolio_id", dashboard, read), [
    { value: "portfolio-1", label: "portfolio-1" },
    { value: "portfolio-2", label: "portfolio-2" },
  ]);
  assert.deepEqual(authorizedDashboardFilterOptions("project_id", dashboard, read), [
    { value: "p-1", label: "Road" },
    { value: "p-2", label: "Bridge" },
    { value: "p-3", label: "p-3" },
  ]);
  assert.deepEqual(authorizedDashboardFilterOptions("project_id", dashboard, null), []);
  assert.deepEqual(authorizedDashboardFilterOptions("project_code", dashboard, read), []);
});

test("Filter By catalog mirrors every backend-supported key and operator without inventing fields", () => {
  assert.deepEqual(
    ENTERPRISE_DASHBOARD_FILTER_CATALOG.map((item) => [item.key, [...item.operators]]),
    [
      ["portfolio_id", ["eq"]],
      ["project_id", ["eq", "in"]],
      ["project_status", ["eq", "in"]],
      ["membership_status", ["eq", "in"]],
      ["decision_status", ["eq", "in"]],
      ["generated_after", ["gte"]],
      ["generated_before", ["lte"]],
      ["include_stale", ["eq"]],
    ],
  );
  assert.deepEqual(dashboardFilterDefinition("membership_status")?.options, ["included", "on_hold", "excluded"]);
  assert.deepEqual(dashboardFilterDefinition("decision_status")?.options, [
    "proposed", "under_review", "approved", "rejected", "implemented", "closed", "cancelled",
  ]);
  assert.equal(dashboardFilterDefinition("project_code"), undefined);
  assert.equal(dashboardFilterDefinition("arbitrary_sql"), undefined);
});

test("dashboard layout drag-and-drop swaps two-dimensional positions only when the result is valid", () => {
  const items = [portlet("left-top", 0, 0, 6), portlet("right-top", 6, 0, 6), portlet("left-bottom", 0, 4, 6)];
  const moved = moveDashboardPortletToPosition(items, 0, 1);
  assert.deepEqual(moved.map((item) => [item.layout.x, item.layout.y]), [[6, 0], [0, 0], [0, 4]]);
  assert.equal(validateDashboardLayout(moved), true);
  // Dropping the top-left portlet onto the bottom-left portlet is a valid
  // two-dimensional position exchange; array order and instance identity stay stable.
  const movedDown = moveDashboardPortletToPosition(items, 0, 2);
  assert.deepEqual(movedDown.map((item) => [item.layout.x, item.layout.y]), [[0, 4], [6, 0], [0, 0]]);
  assert.deepEqual(movedDown.map((item) => item.instance_id), ["left-top", "right-top", "left-bottom"]);
  assert.equal(validateDashboardLayout(movedDown), true);

  // A Wide portlet cannot be exchanged into the right column; reject the whole drop.
  const incompatible = [portlet("wide-left", 0, 0, 12), portlet("narrow-right", 6, 4, 6)];
  const rejected = moveDashboardPortletToPosition(incompatible, 0, 1);
  assert.deepEqual(rejected.map((item) => item.layout), incompatible.map((item) => item.layout));
  assert.deepEqual(moveDashboardPortletToPosition(items, -1, 1).map((item) => item.layout), items.map((item) => item.layout));
});
