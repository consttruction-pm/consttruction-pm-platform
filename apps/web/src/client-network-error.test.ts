import assert from "node:assert/strict";
import test from "node:test";
import { API_REQUEST_TIMEOUT_MS, FetchApiTransport } from "./client.js";

test("workspace API requests allow time for a slow preview bootstrap", () => {
  assert.equal(API_REQUEST_TIMEOUT_MS, 45_000);
});

test("FetchApiTransport normalizes network failure to retryable client error", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    throw new Error("simulated network loss");
  };

  try {
    const result = await new FetchApiTransport("https://example.test").get(
      "/api/v1/workspace/control-room/read",
      { tenant_id: "t1", project_id: "p1", revision: 7 },
    );

    assert.deepEqual(result, {
      ok: false,
      error: {
        code: "NETWORK_ERROR",
        retryable: true,
        message_key: "error.network",
        available_actions: ["retry"],
      },
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("FetchApiTransport preserves structured HTTP API errors", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(JSON.stringify({
      code: "FORBIDDEN",
      retryable: false,
      message_key: "error.forbidden",
      available_actions: [],
    }), { status: 403, headers: { "content-type": "application/json" } });

  try {
    const result = await new FetchApiTransport("https://example.test").get(
      "/api/v1/workspace/control-room/read",
      { tenant_id: "t1", project_id: "p1", revision: 7 },
    );

    assert.deepEqual(result, {
      ok: false,
      error: {
        code: "FORBIDDEN",
        retryable: false,
        message_key: "error.forbidden",
        available_actions: [],
      },
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("FetchApiTransport forwards structured error details without inventing them", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(JSON.stringify({
      code: "P6_ACTIVITY_DELETE_CONFIRMATION_REQUIRED",
      retryable: false,
      message_key: "error.activity.delete.confirmation_required",
      available_actions: [],
      details: { relationships: 2, assignments: 1 },
    }), { status: 409, headers: { "content-type": "application/json" } });

  try {
    const result = await new FetchApiTransport("https://example.test").post(
      "/api/projects/p1/p6/activity-operations",
      { operation: "delete" },
      { tenant_id: "t1", project_id: "p1", revision: 7 },
      "idem-1",
    );
    assert.equal(result.ok, false);
    if (result.ok) return;
    assert.deepEqual(result.error.details, { relationships: 2, assignments: 1 });
    assert.equal(result.error.code, "P6_ACTIVITY_DELETE_CONFIRMATION_REQUIRED");
  } finally {
    globalThis.fetch = originalFetch;
  }
});
