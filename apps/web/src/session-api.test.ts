import assert from "node:assert/strict";
import test from "node:test";
import { FetchSessionApi, toWorkspaceContext } from "./session-api.js";

test("projects authoritative lifecycle context into the workspace context", () => {
  assert.deepEqual(
    toWorkspaceContext({ tenant_id: "t1", project_id: "p1", revision: 4, user_id: "u1" }),
    { tenant_id: "t1", project_id: "p1", revision: 4 },
  );
});

test("session requests include browser credentials", async () => {
  const calls: Array<{ url: string; credentials?: RequestCredentials }> = [];
  const fetchImpl = async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ url: String(input), credentials: init?.credentials });
    return new Response(JSON.stringify({
      session_id: "s1", user_id: "u1", tenant_id: "t1",
      roles: ["viewer"], expires_at: "2030-01-01T00:00:00Z",
    }), { status: 200, headers: { "Content-Type": "application/json" } });
  };

  const result = await new FetchSessionApi("https://example.test", fetchImpl).getSession();
  assert.equal(result.ok, true);
  assert.equal(calls[0]?.url, "https://example.test/api/session");
  assert.equal(calls[0]?.credentials, "include");
});

test("openProject rejects an empty project id before transport", async () => {
  let called = false;
  const fetchImpl = async () => {
    called = true;
    return new Response("{}", { status: 200 });
  };
  const result = await new FetchSessionApi("https://example.test", fetchImpl).openProject("");
  assert.equal(result.ok, false);
  if (!result.ok) assert.equal(result.error.code, "PROJECT_ID_REQUIRED");
  assert.equal(called, false);
});

test("API errors preserve the authoritative error envelope", async () => {
  const fetchImpl = async () => new Response(JSON.stringify({
    code: "SESSION_REQUIRED",
    retryable: false,
    message_key: "error.session.required",
    available_actions: [],
  }), { status: 401, headers: { "Content-Type": "application/json" } });

  const result = await new FetchSessionApi("https://example.test", fetchImpl).getSession();
  assert.equal(result.ok, false);
  if (!result.ok) assert.deepEqual(result.error, {
    code: "SESSION_REQUIRED",
    retryable: false,
    message_key: "error.session.required",
    available_actions: [],
  });
});
