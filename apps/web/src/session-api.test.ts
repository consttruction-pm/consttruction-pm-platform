import assert from "node:assert/strict";
import test from "node:test";
import { toWorkspaceContext } from "./session-api.js";

test("session API client projects authoritative context into WorkspaceContext", () => {
  assert.deepEqual(
    toWorkspaceContext({
      tenant_id: "t1", project_id: "p1", revision: 4, user_id: "u1",
    }),
    { tenant_id: "t1", project_id: "p1", revision: 4 },
  );
});

test("session API sends project metadata as a revision-guarded PATCH", async () => {
  const calls: Array<{ url: string; method?: string; body?: unknown }> = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (async (input: URL | RequestInfo, init?: RequestInit) => {
    calls.push({
      url: String(input),
      method: init?.method,
      body: init?.body ? JSON.parse(String(init.body)) : undefined,
    });
    return new Response(JSON.stringify({
      project: {
        project_id: "p 1", tenant_id: "t1", name: "Renamed", revision: 5,
        description: "Scope", start_date: "2026-11-02",
        date_system: "jalali", primary_calendar_id: "CAL-1",
      },
    }), { status: 200, headers: { "Content-Type": "application/json" } });
  }) as typeof fetch;
  try {
    const { FetchSessionApi } = await import("./session-api.js");
    const api = new FetchSessionApi("https://app.example");
    const result = await api.updateProject("p 1", {
      name: "Renamed",
      description: "Scope",
      start_date: "2026-11-02",
      date_system: "jalali",
      primary_calendar_id: "CAL-1",
    }, 4);
    assert.equal(result.ok, true);
    assert.equal(calls.length, 1);
    assert.equal(calls[0].method, "PATCH");
    assert.equal(calls[0].url, "https://app.example/api/projects/p%201");
    assert.deepEqual(calls[0].body, {
      name: "Renamed",
      description: "Scope",
      start_date: "2026-11-02",
      date_system: "jalali",
      primary_calendar_id: "CAL-1",
      expected_revision: 4,
    });
    assert.equal(result.ok ? result.data.project.revision : 0, 5);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("session API sends a status change as a revision-guarded POST", async () => {
  const calls: Array<{ url: string; method?: string; body?: unknown }> = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (async (input: URL | RequestInfo, init?: RequestInit) => {
    calls.push({
      url: String(input),
      method: init?.method,
      body: init?.body ? JSON.parse(String(init.body)) : undefined,
    });
    return new Response(JSON.stringify({
      contract_version: "project-status-api.v1",
      project: {
        project_id: "p 1", tenant_id: "t1", name: "Project", revision: 5,
        settings_revision: 3, status: "what_if",
      },
    }), { status: 200, headers: { "Content-Type": "application/json" } });
  }) as typeof fetch;
  try {
    const { FetchSessionApi } = await import("./session-api.js");
    const api = new FetchSessionApi("https://app.example");
    const result = await api.setProjectStatus("p 1", "what_if", 2);
    assert.equal(result.ok, true);
    assert.equal(calls.length, 1);
    assert.equal(calls[0].method, "POST");
    assert.equal(calls[0].url, "https://app.example/api/projects/p%201/status");
    assert.deepEqual(calls[0].body, { status: "what_if", expected_revision: 2 });
    assert.equal(result.ok ? result.data.project.status : null, "what_if");
    assert.equal(result.ok ? result.data.project.settings_revision : 0, 3);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("session API reads the append-only project status history", async () => {
  const calls: Array<{ url: string; method?: string }> = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = (async (input: URL | RequestInfo, init?: RequestInit) => {
    calls.push({ url: String(input), method: init?.method });
    return new Response(JSON.stringify({
      contract_version: "project-status-api.v1",
      events: [{
        event_id: "p1@1", tenant_id: "t1", project_id: "p1",
        from_status: "active", to_status: "planned",
        actor_user_id: "u1", recorded_at: "2026-11-12T09:00:00+00:00",
        settings_revision: 1,
      }],
    }), { status: 200, headers: { "Content-Type": "application/json" } });
  }) as typeof fetch;
  try {
    const { FetchSessionApi } = await import("./session-api.js");
    const api = new FetchSessionApi("https://app.example");
    const result = await api.projectStatusHistory("p1");
    assert.equal(result.ok, true);
    assert.equal(calls.length, 1);
    assert.equal(calls[0].method, "GET");
    assert.equal(calls[0].url, "https://app.example/api/projects/p1/status-history");
    assert.equal(result.ok ? result.data.events[0].to_status : null, "planned");
  } finally {
    globalThis.fetch = originalFetch;
  }
});
