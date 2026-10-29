import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import { loadProjectWbs } from "./ai-action-panel.js";

const CONTEXT: ProjectContext = {
  tenant_id: "t1",
  project_id: "preview-rps-01",
  revision: 7,
};

function transportWith(result: ApiResult<unknown>, paths: string[] = []): ApiTransport {
  return {
    async get(path) {
      paths.push(path);
      return result as ApiResult<never>;
    },
    async post() {
      throw new Error("UNEXPECTED_POST");
    },
  };
}

test("reads the persisted WBS tree and labels each real node", async () => {
  const paths: string[] = [];
  const result = await loadProjectWbs(
    transportWith({
      ok: true,
      data: {
        contract_version: "p6-wbs-master-api.v1",
        wbs_nodes: [
          { wbs: { wbs_id: "WBS-ROOT", code: "1", name: "Root" } },
          { wbs: { wbs_id: "WBS-DESIGN", code: "2", name: "Design" } },
        ],
      },
    }, paths),
    CONTEXT,
  );
  assert.equal(paths[0], "/api/projects/preview-rps-01/p6/wbs");
  assert.equal(result.ok, true);
  if (result.ok) {
    assert.deepEqual(result.data.map((item) => item.id), ["WBS-ROOT", "WBS-DESIGN"]);
    assert.equal(result.data[1]?.label, "2 · Design (WBS-DESIGN)");
  }
});

test("accepts a flat node shape and an empty tree without inventing nodes", async () => {
  const flat = await loadProjectWbs(
    transportWith({
      ok: true,
      data: { wbs_nodes: [{ wbs_id: "W-1", code: "", name: "" }] },
    }),
    CONTEXT,
  );
  assert.equal(flat.ok, true);
  if (flat.ok) assert.deepEqual(flat.data, [{ id: "W-1", label: "W-1 (W-1)" }]);

  const empty = await loadProjectWbs(
    transportWith({ ok: true, data: { wbs_nodes: [] } }),
    CONTEXT,
  );
  assert.equal(empty.ok, true);
  if (empty.ok) assert.equal(empty.data.length, 0);
});

test("rejects malformed WBS responses instead of fabricating options", async () => {
  for (const data of [
    {},
    { wbs_nodes: "all" },
    { wbs_nodes: [null] },
    { wbs_nodes: [{ wbs: { wbs_id: "" } }] },
  ]) {
    const result = await loadProjectWbs(transportWith({ ok: true, data }), CONTEXT);
    assert.equal(result.ok, false);
    if (!result.ok) assert.equal(result.error.code, "INVALID_WBS_OPTIONS_RESPONSE");
  }
});

test("passes an authorization failure through unchanged", async () => {
  const result = await loadProjectWbs(
    transportWith({
      ok: false,
      error: {
        code: "authorization denied for permission=project.read",
        retryable: false,
        message_key: "error.authorization.denied",
        available_actions: [],
      },
    }),
    CONTEXT,
  );
  assert.equal(result.ok, false);
  if (!result.ok) assert.match(result.error.code, /project\.read/);
});
