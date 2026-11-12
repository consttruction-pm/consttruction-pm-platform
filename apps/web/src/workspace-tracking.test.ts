import assert from "node:assert/strict";
import { test } from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  DEFAULT_TRACKING_QUERY,
  TRACKING_API_VERSION,
  loadTrackingRead,
  mountWorkspaceTrackingPage,
  parseTrackingRead,
  trackingPath,
} from "./workspace-tracking.js";

const context: ProjectContext = { tenant_id: "T-1", project_id: "P-1", revision: 7 };
const BASE = "/api/projects/P-1/tracking/read";

type Call = { method: string; path: string; body?: unknown };

function transport(handler: (call: Call) => ApiResult<unknown>): {
  transport: ApiTransport;
  calls: Call[];
} {
  const calls: Call[] = [];
  const send = (method: string) => async (path: string, body?: unknown) => {
    const call = { method, path, body };
    calls.push(call);
    return handler(call);
  };
  return {
    calls,
    transport: {
      get: send("GET"),
      post: send("POST"),
      patch: send("PATCH"),
      delete: send("DELETE"),
    } as unknown as ApiTransport,
  };
}

function row(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    activity_id: "A100",
    name: "Kickoff",
    wbs_id: "W1",
    wbs_code: "1",
    status: "Completed",
    percent_complete: 100,
    start: "2026-09-21",
    finish: "2026-09-21",
    early_start: "2026-09-21",
    early_finish: "2026-09-21",
    late_start: "2026-10-07",
    late_finish: "2026-10-07",
    total_float: 12,
    free_float: 1,
    critical: false,
    float_path: null,
    float_path_order: null,
    duration: 0,
    planned_finish: "2026-09-20",
    finish_variance_days: 1,
    ...overrides,
  };
}

function payload(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    contract_version: TRACKING_API_VERSION,
    scope: { tenant_id: "T-1", project_id: "P-1", project_revision: 7 },
    layout: { scale: "week", group_by: null, sort: "start", direction: "asc" },
    source: {
      calculation_run_identity: "649385baec94103763c36c802b3d17b6c0744ea67bd7dbc481c3e490a7fa6063",
      schedule_projection: "schedule.query.result",
      authoritative: true,
    },
    summary: {
      activity_count: 2,
      not_started_count: 1,
      in_progress_count: 0,
      completed_count: 1,
      critical_count: 1,
      project_finish: "2026-12-03",
      mean_percent_complete: null,
      mean_percent_basis: "unweighted_mean_of_persisted_percent_complete",
      diagnostic_count: 0,
    },
    rows: [
      row(),
      row({
        activity_id: "A110",
        name: "Mobilization",
        status: "Not Started",
        percent_complete: null,
        total_float: 0,
        critical: true,
        planned_finish: null,
        finish_variance_days: null,
      }),
    ],
    groups: [],
    bar_chart: [
      { bucket: "2026-09-21", total: 1, not_started: 0, in_progress: 0, completed: 1, critical: 0 },
      { bucket: "2026-09-28", total: 1, not_started: 1, in_progress: 0, completed: 0, critical: 1 },
    ],
    profile: [
      { bucket: "2026-09-21", activity_count: 1, duration: "0" },
      { bucket: "2026-09-28", activity_count: 1, duration: "2" },
    ],
    resource_analysis: {
      status: "unavailable",
      reason: "resource_assignment_source_not_configured",
      resources: [],
      totals: {},
    },
    warnings: [],
    ...overrides,
  };
}

function availableResources(): Record<string, unknown> {
  return {
    status: "available",
    basis: "persisted_assignments",
    resources: [
      {
        resource_id: "R-1",
        resource_name: "Crew",
        resource_type: "labor",
        assignment_count: 2,
        activity_count: 1,
        planned_units: "16",
        actual_units: "8",
        remaining_units: "8",
        planned_cost: "1600",
        actual_cost: "800",
        remaining_cost: "800",
        currency: "USD",
      },
    ],
    totals: {
      planned_units: "16",
      actual_units: "8",
      remaining_units: "8",
      planned_cost: "1600",
      actual_cost: "800",
      remaining_cost: "800",
    },
  };
}

test("trackingPath sends the documented query and omits an empty grouping", () => {
  assert.equal(
    trackingPath(context, { ...DEFAULT_TRACKING_QUERY, scale: "month", sort: "finish", direction: "desc" }),
    `${BASE}?scale=month&sort=finish&direction=desc`,
  );
  assert.equal(
    trackingPath(context, { ...DEFAULT_TRACKING_QUERY, groupBy: "wbs" }),
    `${BASE}?scale=week&group_by=wbs&sort=start&direction=asc`,
  );
});

test("parser accepts the versioned projection and keeps server values verbatim", () => {
  const parsed = parseTrackingRead(payload());
  assert.equal(parsed.contractVersion, TRACKING_API_VERSION);
  assert.equal(parsed.rows.length, 2);
  assert.equal(parsed.rows[0].percentComplete, "100");
  assert.equal(parsed.rows[0].totalFloat, "12");
  assert.equal(parsed.rows[0].duration, "0");
  assert.equal(parsed.rows[0].plannedFinish, "2026-09-20");
  assert.equal(parsed.rows[0].finishVarianceDays, 1);
  assert.equal(parsed.rows[1].percentComplete, null);
  assert.equal(parsed.rows[1].critical, true);
  assert.equal(parsed.summary.meanPercentComplete, null);
  assert.equal(parsed.resourceAnalysis.status, "unavailable");
  assert.equal(parsed.barChart[1].critical, 1);
});

test("parser fails closed on contract, scope, layout and inconsistent totals", () => {
  for (const bad of [
    payload({ contract_version: "tracking-read-model.v2" }),
    payload({ scope: { tenant_id: "", project_id: "P-1", project_revision: 7 } }),
    payload({ layout: { scale: "quarter", group_by: null, sort: "start", direction: "asc" } }),
    payload({ layout: { scale: "week", group_by: "phase", sort: "start", direction: "asc" } }),
    payload({ summary: { ...(payload().summary as object), activity_count: 3 } }),
    payload({ rows: [row(), row()] }),
    payload({ rows: [row({ critical: "yes" })] }),
    payload({ rows: [row({ name: null })] }),
    payload({ rows: [row({ duration: true })] }),
    payload({
      bar_chart: [
        { bucket: "2026-09-21", total: 1, not_started: 1, in_progress: 1, completed: 0, critical: 0 },
      ],
    }),
    payload({ profile: [{ bucket: "2026-09-21", activity_count: 1, duration: {} }] }),
    payload({ resource_analysis: { status: "available", basis: "x", resources: [], totals: {} } }),
    payload({ warnings: [{ count: 2 }] }),
  ]) {
    assert.throws(() => parseTrackingRead(bad), /INVALID_TRACKING_RESPONSE/, JSON.stringify(bad).slice(0, 120));
  }
});

test("parser requires WBS groups to cover every row", () => {
  const grouped = payload({
    layout: { scale: "week", group_by: "wbs", sort: "start", direction: "asc" },
    groups: [
      { group: "1", activity_count: 2, critical_count: 1, completed_count: 1 },
    ],
  });
  const parsed = parseTrackingRead(grouped);
  assert.equal(parsed.groups[0].activityCount, 2);
  assert.throws(() =>
    parseTrackingRead(
      payload({
        layout: { scale: "week", group_by: "wbs", sort: "start", direction: "asc" },
        groups: [{ group: "1", activity_count: 1, critical_count: 1, completed_count: 1 }],
      }),
    ),
  );
});

test("parser accepts authoritative resource totals exactly as serialized", () => {
  const parsed = parseTrackingRead(payload({ resource_analysis: availableResources() }));
  assert.equal(parsed.resourceAnalysis.status, "available");
  if (parsed.resourceAnalysis.status === "available") {
    assert.equal(parsed.resourceAnalysis.resources[0].resourceName, "Crew");
    assert.equal(parsed.resourceAnalysis.resources[0].plannedCost, "1600");
    assert.equal(parsed.resourceAnalysis.totals.remainingCost, "800");
  }
});

test("loadTrackingRead forwards transport failures and rejects malformed payloads", async () => {
  const denied = transport(() => ({
    ok: false,
    error: { code: "TRACKING_READ_NOT_AUTHORIZED", retryable: false, message_key: "error.authorization.denied", available_actions: [] },
  }));
  const deniedResult = await loadTrackingRead(denied.transport, context, DEFAULT_TRACKING_QUERY);
  assert.equal(deniedResult.ok, false);
  if (!deniedResult.ok) assert.equal(deniedResult.error.code, "TRACKING_READ_NOT_AUTHORIZED");
  assert.equal(denied.calls[0].method, "GET");
  assert.equal(denied.calls[0].path, trackingPath(context, DEFAULT_TRACKING_QUERY));

  const malformed = transport(() => ({ ok: true, data: { ...payload(), rows: "none" } }));
  const malformedResult = await loadTrackingRead(malformed.transport, context, DEFAULT_TRACKING_QUERY);
  assert.equal(malformedResult.ok, false);
  if (!malformedResult.ok) assert.equal(malformedResult.error.code, "INVALID_TRACKING_RESPONSE");
});

function mountHost(): {
  host: HTMLElement;
  click: (target: Record<string, unknown>) => void;
  change: (target: Record<string, unknown>) => void;
} {
  const listeners = new Map<string, (event: Event) => void>();
  const host = {
    dataset: {} as Record<string, string>,
    innerHTML: "",
    addEventListener: (type: string, listener: (event: Event) => void) =>
      listeners.set(type, listener),
    querySelectorAll: () => [],
    querySelector: () => null,
    contains: () => true,
  };
  const fire = (type: string, target: Record<string, unknown>): void => {
    const withClosest = {
      ...target,
      closest: (selector: string) => {
        const dataset = (target.dataset ?? {}) as Record<string, string>;
        if (selector === "[data-tracking-view]" && dataset.trackingView) return withClosest;
        if (selector === "[data-tracking-action='refresh']" && dataset.trackingAction === "refresh") {
          return withClosest;
        }
        return null;
      },
    };
    listeners.get(type)?.({ target: withClosest } as unknown as Event);
  };
  return {
    host: host as unknown as HTMLElement,
    click: (target) => fire("click", target),
    change: (target) => fire("change", target),
  };
}

const tick = (): Promise<void> => new Promise((resolve) => setTimeout(resolve, 0));

test("mounted page renders the summary, row values and each presentation", async () => {
  const stub = transport(() => ({ ok: true, data: payload() }));
  const { host, click, change } = mountHost();
  mountWorkspaceTrackingPage(host, { transport: stub.transport, context, locale: "en" });
  await tick();

  assert.equal((host as unknown as { dataset: Record<string, string> }).dataset.trackingStatus, "loaded");
  assert.match(host.innerHTML, /data-tracking-summary/);
  assert.match(host.innerHTML, /data-tracking-stat="activity-count"><span>Activities<\/span><strong>2<\/strong>/);
  assert.match(host.innerHTML, /data-tracking-stat="mean-percent"><span>Mean % Complete<\/span><strong>—<\/strong>/);
  assert.match(host.innerHTML, /data-tracking-row data-activity-id="A100"/);
  assert.match(host.innerHTML, /data-activity-id="A110"[^>]*data-critical="true"/);
  assert.match(host.innerHTML, /2026-09-20/);
  assert.match(host.innerHTML, /data-tracking-project>P-1/);
  assert.equal(stub.calls[0].path, `${BASE}?scale=week&sort=start&direction=asc`);

  click({ dataset: { trackingView: "bar-chart" } });
  assert.match(host.innerHTML, /data-tracking-bars/);
  assert.match(host.innerHTML, /data-tracking-bar="2026-09-21"/);
  click({ dataset: { trackingView: "gantt-profile" } });
  assert.match(host.innerHTML, /data-tracking-profile-bars/);
  click({ dataset: { trackingView: "resource-analysis" } });
  assert.match(host.innerHTML, /data-tracking-resource-unavailable/);

  change({ name: "tracking-scale", value: "month" });
  await tick();
  assert.equal(stub.calls[1].path, `${BASE}?scale=month&sort=start&direction=asc`);
  change({ name: "tracking-group", value: "wbs" });
  await tick();
  assert.equal(stub.calls[2].path, `${BASE}?scale=month&group_by=wbs&sort=start&direction=asc`);
});

test("mounted page renders WBS groups and authoritative resource rows", async () => {
  const grouped = payload({
    layout: { scale: "week", group_by: "wbs", sort: "start", direction: "asc" },
    groups: [{ group: "1", activity_count: 2, critical_count: 1, completed_count: 1 }],
    resource_analysis: availableResources(),
  });
  const stub = transport(() => ({ ok: true, data: grouped }));
  const { host, click } = mountHost();
  mountWorkspaceTrackingPage(host, { transport: stub.transport, context, locale: "fa" });
  await tick();

  assert.match(host.innerHTML, /data-tracking-groups/);
  assert.match(host.innerHTML, /data-tracking-group="1"/);
  click({ dataset: { trackingView: "resource-analysis" } });
  assert.match(host.innerHTML, /data-tracking-resource="R-1"/);
  assert.match(host.innerHTML, /Crew/);
  assert.match(host.innerHTML, /data-tracking-resource-totals/);
});

test("mounted page states the server error honestly and offers refresh", async () => {
  const stub = transport(() => ({
    ok: false,
    error: {
      code: "TRACKING_SCHEDULE_NOT_PUBLISHED",
      retryable: false,
      message_key: "error.tracking.schedule.not_published",
      available_actions: [],
    },
  }));
  const { host } = mountHost();
  mountWorkspaceTrackingPage(host, { transport: stub.transport, context, locale: "en" });
  await tick();

  assert.equal((host as unknown as { dataset: Record<string, string> }).dataset.trackingStatus, "error");
  assert.match(host.innerHTML, /data-tracking-error="TRACKING_SCHEDULE_NOT_PUBLISHED"/);
  assert.match(host.innerHTML, /No schedule has been published/);
  assert.doesNotMatch(host.innerHTML, /data-tracking-summary/);
  assert.match(host.innerHTML, /data-tracking-action="refresh"/);
});
