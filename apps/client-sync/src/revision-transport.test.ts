import assert from "node:assert/strict";
import test from "node:test";
import { ApiRevisionTransport } from "./revision-transport.ts";
import type { SyncProjectContext, SyncApiResult } from "./api-sync-transport.ts";

const context: SyncProjectContext = {
  tenant_id: "t1",
  project_id: "p1",
  revision: 7,
};

test("refresh returns the versioned project revision", async () => {
  const transport = new ApiRevisionTransport({
    async get<TResponse>(path: string, receivedContext: SyncProjectContext): Promise<SyncApiResult<TResponse>> {
      assert.equal(path, "/api/v1/sync/revision");
      assert.deepEqual(receivedContext, context);
      return {
        ok: true,
        data: {
          contract_version: "sync-project-revision.v1",
          tenant_id: "t1",
          project_id: "p1",
          revision: 8,
        } as TResponse,
      };
    },
  });

  assert.deepEqual(await transport.refresh(context), {
    contract_version: "sync-project-revision.v1",
    tenant_id: "t1",
    project_id: "p1",
    revision: 8,
  });
});

test("refresh rejects an invalid project revision response", async () => {
  const transport = new ApiRevisionTransport({
    async get() {
      return {
        ok: true,
        data: {
          contract_version: "sync-project-revision.v1",
          tenant_id: "other",
          project_id: "p1",
          revision: 8,
        },
      };
    },
  });

  await assert.rejects(() => transport.refresh(context), {
    message: "INVALID_PROJECT_REVISION_RESPONSE",
  });
});

test("refresh surfaces api errors", async () => {
  const transport = new ApiRevisionTransport({
    async get() {
      return {
        ok: false,
        error: { code: "PROJECT_NOT_FOUND", retryable: false },
      };
    },
  });

  await assert.rejects(() => transport.refresh(context), {
    message: "PROJECT_NOT_FOUND",
  });
});
