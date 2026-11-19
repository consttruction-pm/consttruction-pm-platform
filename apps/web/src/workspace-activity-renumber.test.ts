import assert from "node:assert/strict";
import test from "node:test";

import {
  DEFAULT_RENUMBER_OPTIONS,
  planRenumber,
  renumberActivityIds,
  type RenumberOptions,
} from "./workspace-activity-renumber.js";

const ACTIVITIES = [
  { id: "AF567", name: "Piling" },
  { id: "AF568", name: "Pile caps" },
  { id: "AF569", name: "Ground beams" },
  { id: "ZZ900", name: "Handover" },
];

function options(overrides: Partial<RenumberOptions> = {}): RenumberOptions {
  return { ...DEFAULT_RENUMBER_OPTIONS, ...overrides };
}

test("increment keeps the prefix and steps over an ID owned outside the selection", () => {
  const plan = planRenumber(
    [...ACTIVITIES, { id: "AF577", name: "Existing" }],
    ["AF567"],
    options({ mode: "increment", increment: 10 }),
  );
  assert.deepEqual(plan.rows.map((row) => row.nextId), ["AF587"]);
  assert.deepEqual(plan.conflicts, []);
});

test("increment preserves zero padding and reports IDs without a numeric suffix", () => {
  const padded = planRenumber(
    [{ id: "A0001" }, { id: "A0002" }, { id: "MILESTONE" }],
    ["A0001", "A0002", "MILESTONE"],
    options({ mode: "increment", increment: 5 }),
  );
  assert.deepEqual(padded.rows.map((row) => [row.sourceId, row.nextId]), [
    ["A0001", "A0006"],
    ["A0002", "A0007"],
    ["MILESTONE", "MILESTONE"],
  ]);
  assert.equal(padded.conflicts[0]?.reason, "NO_NUMERIC_SUFFIX");
});

test("auto-number starts above a populated prefix range and increments in table order", () => {
  const plan = planRenumber(
    [
      { id: "KK380" },
      { id: "KK390" },
      { id: "AF567" },
      { id: "AF568" },
    ],
    ["AF567", "AF568"],
    options({ mode: "auto-number", prefix: "KK", suffix: 400, increment: 10 }),
  );
  assert.deepEqual(plan.rows.map((row) => row.nextId), ["KK400", "KK410"]);
  assert.deepEqual(plan.conflicts, []);
});

test("replace beginning characters flags a collision with an unselected activity", () => {
  const plan = planRenumber(
    [{ id: "AF567" }, { id: "JY567" }],
    ["AF567"],
    options({ mode: "replace", replaceWith: "JY", replaceCount: 2 }),
  );
  assert.equal(plan.rows[0]?.nextId, "JY567");
  assert.equal(plan.conflicts[0]?.reason, "COLLISION");
});

test("a manual override resolves a duplicate and is validated against the project", () => {
  const duplicated = planRenumber(
    [{ id: "AA1" }, { id: "AA2" }, { id: "A2" }],
    ["AA1", "AA2"],
    options({ mode: "replace", replaceWith: "A", replaceCount: 2, increment: 1 }),
  );
  assert.equal(duplicated.conflicts.length, 1);
  const resolved = planRenumber(
    [{ id: "AA1" }, { id: "AA2" }, { id: "A2" }],
    ["AA1", "AA2"],
    options({ mode: "replace", replaceWith: "A", replaceCount: 2, increment: 1 }),
    { AA2: "A9" },
  );
  assert.deepEqual(resolved.conflicts, []);
  assert.deepEqual(resolved.rows.map((row) => row.nextId), ["A1", "A9"]);
});

test("renumberActivityIds posts the revision-checked entries and baseline flag", async () => {
  const calls: Array<{ path: string; body: Record<string, unknown> }> = [];
  const result = await renumberActivityIds(
    {
      get: async () => ({ ok: false, error: { code: "UNUSED", retryable: false, message_key: "", available_actions: [] } }),
      post: async (path: string, body: Record<string, unknown>) => {
        calls.push({ path, body });
        return { ok: true, data: { mappings: [{ activity_id: "A-1", new_activity_id: "A-10" }] } };
      },
    } as never,
    { tenant_id: "t1", project_id: "p1", project_revision: 3 } as never,
    [{ activityId: "A-1", newActivityId: "A-10", expectedRevision: 2 }],
    false,
  );
  assert.equal(result.ok, true);
  assert.equal(calls[0]?.path, "/api/projects/p1/p6/activities/renumber");
  assert.deepEqual(calls[0]?.body, {
    contract_version: "p6-activity-master-api.v1",
    entries: [{ activity_id: "A-1", new_activity_id: "A-10", expected_revision: 2 }],
    renumber_baselines: false,
  });
});
