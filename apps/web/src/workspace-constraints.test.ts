import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  CONSTRAINT_API_VERSION,
  buildConstraintPayload,
  deleteConstraint,
  loadConstraints,
  parseConstraint,
  saveConstraint,
} from "./workspace-constraints.js";

const CONTEXT: ProjectContext = { tenant_id: "t1", project_id: "project-1", revision: 4 };

function envelope(constraint: unknown) {
  return {
    contract_version: CONSTRAINT_API_VERSION,
    kind: "p6_constraint",
    scope: { tenant_id: "t1", project_id: "project-1", project_revision: 4 },
    constraint,
  };
}

const CONSTRAINT = {
  constraint_id: "constraint-1",
  activity_id: "A140",
  constraint_type: "START_NO_EARLIER_THAN",
  constraint_date: "2026-10-20",
  record_revision: 1,
};

function transportWith(result: ApiResult<unknown>, calls: { gets: string[]; posts: { path: string; request: unknown }[]; deletes: { path: string; request: unknown }[] }): ApiTransport {
  return {
    async get(path) {
      calls.gets.push(path);
      return result as ApiResult<never>;
    },
    async post(path, request) {
      calls.posts.push({ path, request });
      return result as ApiResult<never>;
    },
    async delete(path, request) {
      calls.deletes.push({ path, request });
      return result as ApiResult<never>;
    },
  };
}

test("parseConstraint keeps the typed wire value and exact ISO date", () => {
  assert.deepEqual(parseConstraint(envelope(CONSTRAINT)), {
    constraintId: "constraint-1",
    activityId: "A140",
    constraintType: "START_NO_EARLIER_THAN",
    constraintDate: "2026-10-20",
    recordRevision: 1,
  });
});

test("parseConstraint rejects unknown types and non-date values", () => {
  assert.throws(
    () => parseConstraint(envelope({ ...CONSTRAINT, constraint_type: "AS_SOON_AS_POSSIBLE" })),
    /INVALID_CONSTRAINT_TYPE/,
  );
  assert.throws(
    () => parseConstraint(envelope({ ...CONSTRAINT, constraint_date: "2026-10-20T08:00:00Z" })),
    /INVALID_CONSTRAINT_RECORD/,
  );
  assert.throws(() => parseConstraint({}), /INVALID_CONSTRAINT_RESPONSE/);
});

test("buildConstraintPayload validates required fields without inventing a date", () => {
  assert.deepEqual(
    buildConstraintPayload({
      constraintId: "constraint-2",
      activityId: "A150",
      constraintType: "MANDATORY_FINISH",
      constraintDate: "2026-11-02",
    }),
    {
      constraint_id: "constraint-2",
      activity_id: "A150",
      constraint_type: "MANDATORY_FINISH",
      constraint_date: "2026-11-02",
    },
  );
  assert.throws(
    () => buildConstraintPayload({ constraintId: "", activityId: "A150", constraintType: "MANDATORY_FINISH", constraintDate: "2026-11-02" }),
    /CONSTRAINT_FIELDS_REQUIRED/,
  );
  assert.throws(
    () => buildConstraintPayload({ constraintId: "c", activityId: "A150", constraintType: "MANDATORY_FINISH", constraintDate: "2026-11-02T00:00" }),
    /INVALID_CONSTRAINT_DATE/,
  );
});

test("loadConstraints reads the project-scoped register and parses every row", async () => {
  const calls = { gets: [] as string[], posts: [] as { path: string; request: unknown }[], deletes: [] as { path: string; request: unknown }[] };
  const result = await loadConstraints(
    transportWith({ ok: true, data: { contract_version: CONSTRAINT_API_VERSION, constraints: [envelope(CONSTRAINT)] } }, calls),
    CONTEXT,
  );
  assert.equal(result.ok, true);
  assert.deepEqual(calls.gets, ["/api/projects/project-1/p6/constraints"]);
  assert.equal(result.ok && result.data[0]?.constraintId, "constraint-1");
});

test("saveConstraint posts the exact typed payload", async () => {
  const calls = { gets: [] as string[], posts: [] as { path: string; request: unknown }[], deletes: [] as { path: string; request: unknown }[] };
  const result = await saveConstraint(
    transportWith({ ok: true, data: envelope(CONSTRAINT) }, calls),
    CONTEXT,
    { constraintId: "constraint-1", activityId: "A140", constraintType: "START_NO_EARLIER_THAN", constraintDate: "2026-10-20" },
  );
  assert.equal(result.ok, true);
  assert.deepEqual(calls.posts, [{
    path: "/api/projects/project-1/p6/constraints",
    request: {
      constraint_id: "constraint-1",
      activity_id: "A140",
      constraint_type: "START_NO_EARLIER_THAN",
      constraint_date: "2026-10-20",
    },
  }]);
});

test("deleteConstraint sends the record revision and reports the stored delete", async () => {
  const calls = { gets: [] as string[], posts: [] as { path: string; request: unknown }[], deletes: [] as { path: string; request: unknown }[] };
  const result = await deleteConstraint(
    transportWith({
      ok: true,
      data: {
        contract_version: CONSTRAINT_API_VERSION,
        kind: "p6_constraint_delete",
        scope: { tenant_id: "t1", project_id: "project-1", project_revision: 4 },
        constraint_id: "constraint-1",
        deleted: true,
      },
    }, calls),
    CONTEXT,
    "constraint-1",
    3,
  );
  assert.equal(result.ok, true);
  assert.deepEqual(calls.deletes, [
    { path: "/api/projects/project-1/p6/constraints/constraint-1", request: { expected_revision: 3 } },
  ]);
});
