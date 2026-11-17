import test from "node:test";
import assert from "node:assert/strict";
import { EnterpriseDashboardHttpError, FetchEnterpriseDashboardClient } from "./enterprise-dashboard-http-client.js";

type Captured = { url: string; init: RequestInit };

function fixtureFetch(payload: unknown = { ok: true }, status = 200) {
  const calls: Captured[] = [];
  const fetcher: typeof fetch = async (input, init = {}) => {
    calls.push({ url: String(input), init });
    return new Response(JSON.stringify(payload), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  };
  return { calls, fetcher };
}

test("dashboard HTTP client sends authenticated same-origin no-store requests", async () => {
  const { calls, fetcher } = fixtureFetch({ displayed_dashboards: [], available_dashboards: [] });
  const client = new FetchEnterpriseDashboardClient(fetcher);
  await client.listCatalog("Riverside Pump");
  assert.equal(calls[0].url, "/api/enterprise/dashboards?limit=500&search=Riverside+Pump");
  assert.equal(calls[0].init.credentials, "same-origin");
  assert.equal(calls[0].init.cache, "no-store");
  assert.equal(new Headers(calls[0].init.headers).get("Accept"), "application/json");
});

test("dashboard HTTP client maps every UI command to the authenticated HTTP contract", async () => {
  const { calls, fetcher } = fixtureFetch({ dashboard: { dashboard_id: "d-1" }, revision: 2 });
  const client = new FetchEnterpriseDashboardClient(fetcher);
  await client.getDashboard("d 1");
  await client.readPortlets("d-1", [{ key: "project_id", operator: "eq", value: "p-1" }]);
  await client.setDisplayPreference("d-1", true, 0);
  await client.createDashboard({ title: "Board", description: "", context: "enterprise_home" });
  await client.duplicateDashboard("d-1", "Copy");
  await client.updateDashboard("d-1", {
    title: "Board", description: "", portlets: [], filters: [],
    restrict_filter_override: false, max_rows_per_portlet: 50,
  }, 2);
  await client.archiveDashboard("d-1", 2);
  await client.saveFilterOverride("d-1", [{ key: "project_id", operator: "eq", value: "p-1" }]);
  await client.resetFilterOverride("d-1");
  await client.assignShare("d-1", "user", "u-2", 2);
  await client.revokeShare("d-1", "role", "enterprise_viewer", 3);
  assert.deepEqual(calls.map((call) => [call.init.method ?? "GET", call.url]), [
    ["GET", "/api/enterprise/dashboards/d%201"],
    ["POST", "/api/enterprise/dashboards/d-1/read"],
    ["PUT", "/api/enterprise/dashboards/d-1/display"],
    ["POST", "/api/enterprise/dashboards"],
    ["POST", "/api/enterprise/dashboards/d-1/duplicate"],
    ["PATCH", "/api/enterprise/dashboards/d-1"],
    ["POST", "/api/enterprise/dashboards/d-1/archive"],
    ["POST", "/api/enterprise/dashboards/d-1/filter-override"],
    ["DELETE", "/api/enterprise/dashboards/d-1/filter-override"],
    ["POST", "/api/enterprise/dashboards/d-1/shares"],
    ["DELETE", "/api/enterprise/dashboards/d-1/shares"],
  ]);
  assert.equal(new Headers(calls[3].init.headers).get("Idempotency-Key")?.length, 36);
  assert.equal(new Headers(calls[4].init.headers).get("Idempotency-Key")?.length, 36);
  assert.deepEqual(JSON.parse(String(calls[7].init.body)), { filters: [{ key: "project_id", operator: "eq", value: "p-1" }] });
  assert.deepEqual(JSON.parse(String(calls[9].init.body)), {
    target_type: "user", target_id: "u-2", expected_revision: 2,
  });
  assert.deepEqual(JSON.parse(String(calls[10].init.body)), {
    target_type: "role", target_id: "enterprise_viewer", expected_revision: 3,
  });
});

test("dashboard HTTP client surfaces server error codes without swallowing status", async () => {
  const { fetcher } = fixtureFetch({ code: "DASHBOARD_SHARE_TARGET_NOT_IN_TENANT" }, 403);
  const client = new FetchEnterpriseDashboardClient(fetcher);
  await assert.rejects(
    client.assignShare("d-1", "user", "foreign-user", 1),
    (error: unknown) => error instanceof EnterpriseDashboardHttpError
      && error.status === 403
      && error.code === "DASHBOARD_SHARE_TARGET_NOT_IN_TENANT",
  );
});
