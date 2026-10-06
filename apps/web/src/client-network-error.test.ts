import assert from "node:assert/strict";
import test from "node:test";
import { FetchApiTransport } from "./client.js";

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
