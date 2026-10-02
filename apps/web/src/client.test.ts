import assert from "node:assert/strict";
import test from "node:test";

import { FetchProjectLifecycleClient } from "./client.js";

test("project lifecycle client lists projects with session credentials", async () => {
  const originalFetch = globalThis.fetch;
  const requests: Array<{ url: string; init: RequestInit }> = [];
  globalThis.fetch = async (input, init = {}) => {
    requests.push({ url: String(input), init });
    return new Response(
      JSON.stringify({
        projects: [{ project_id: "p1", tenant_id: "t1", name: "Project One", revision: 2 }],
      }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );
  };

  try {
    const result = await new FetchProjectLifecycleClient("https://example.test").listProjects();
    assert.equal(result.ok, true);
    if (result.ok) assert.equal(result.data.projects[0]?.project_id, "p1");
    assert.equal(requests[0]?.url, "https://example.test/api/projects");
    assert.equal(requests[0]?.init.credentials, "same-origin");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("project lifecycle client opens the selected project and preserves server context", async () => {
  const originalFetch = globalThis.fetch;
  const requests: Array<{ url: string; init: RequestInit }> = [];
  globalThis.fetch = async (input, init = {}) => {
    requests.push({ url: String(input), init });
    return new Response(
      JSON.stringify({ context: { tenant_id: "t1", project_id: "p/1", revision: 7 } }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );
  };

  try {
    const result = await new FetchProjectLifecycleClient("https://example.test").openProject("p/1");
    assert.equal(result.ok, true);
    if (result.ok) {
      assert.deepEqual(result.data.context, { tenant_id: "t1", project_id: "p/1", revision: 7 });
    }
    assert.equal(requests[0]?.url, "https://example.test/api/projects/p%2F1/open");
    assert.equal(requests[0]?.init.method, "POST");
    assert.equal(requests[0]?.init.credentials, "same-origin");
  } finally {
    globalThis.fetch = originalFetch;
  }
});
