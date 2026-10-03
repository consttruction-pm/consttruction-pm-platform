import assert from "node:assert/strict";
import test from "node:test";
import { FetchApiTransport } from "./client.js";

const context = {
  tenant_id: "tenant-1",
  project_id: "project-1",
  revision: 7,
};

test("API transport normalizes network failures into a retryable client error", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    throw new TypeError("network unavailable");
  };

  try {
    const result = await new FetchApiTransport("https://example.test").get(
      "/api/v1/workspace",
      context,
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
