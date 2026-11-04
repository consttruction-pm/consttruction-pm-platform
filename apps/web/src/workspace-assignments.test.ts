import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  buildAssignmentPayload,
  loadAssignments,
  parseAssignment,
  saveAssignment,
  type AssignmentInput,
} from "./workspace-assignments.js";

const CONTEXT: ProjectContext = { tenant_id: "t1", project_id: "project-1", revision: 4 };

const ASSIGNMENT = {
  assignment_id: "AS-1",
  activity_id: "A100",
  resource_id: "RPS-CIVIL-CREW",
  role_id: "RPS-ROLE-CIVIL",
  units: "8.0",
  actual_units: "2.0",
  remaining_units: "6.0",
  planned_cost: "1200.50",
  actual_cost: "300",
  remaining_cost: "900.50",
  unit: "hour",
  currency: "USD",
  calendar_id: null,
  calendar_version: null,
  note: "Crew assignment",
  is_driving: true,
  units_per_time: null,
  units_per_time_period: null,
  hours_per_units_time_period: null,
};

function envelope(assignment: unknown = ASSIGNMENT, contract = "p6-resource-read-api.v1") {
  return {
    contract_version: contract,
    kind: "resource_assignment",
    scope: { tenant_id: "t1", project_id: "project-1", project_revision: 4 },
    assignment,
  };
}

type Calls = {
  gets: { path: string }[];
  posts: { path: string; request: unknown; idempotencyKey?: string }[];
};

function transportWith(
  result: ApiResult<unknown>,
  calls: Calls = { gets: [], posts: [] },
): ApiTransport {
  return {
    async get(path) {
      calls.gets.push({ path });
      return result as ApiResult<never>;
    },
    async post(path, request, _context, idempotencyKey) {
      calls.posts.push({ path, request, idempotencyKey });
      return result as ApiResult<never>;
    },
  };
}

test("assignment list reads the authoritative contract and keeps stored decimal strings", async () => {
  const calls: Calls = { gets: [], posts: [] };
  const result = await loadAssignments(
    transportWith({ ok: true, data: { contract_version: "p6-resource-read-api.v1", assignments: [envelope()] } }, calls),
    CONTEXT,
  );
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.deepEqual(result.data, [{
    assignmentId: "AS-1",
    activityId: "A100",
    resourceId: "RPS-CIVIL-CREW",
    roleId: "RPS-ROLE-CIVIL",
    units: "8.0",
    actualUnits: "2.0",
    remainingUnits: "6.0",
    plannedCost: "1200.50",
    actualCost: "300",
    remainingCost: "900.50",
    unit: "hour",
    currency: "USD",
    calendarId: null,
    calendarVersion: null,
    note: "Crew assignment",
    isDriving: true,
    unitsPerTime: null,
    unitsPerTimePeriod: null,
    hoursPerUnitsTimePeriod: null,
  }]);
  assert.deepEqual(calls.gets, [{ path: "/api/projects/project-1/p6/resource-assignments" }]);
});

test("assignment list fails closed on a foreign contract or non-numeric units", async () => {
  const wrongContract = await loadAssignments(
    transportWith({ ok: true, data: { contract_version: "other", assignments: [envelope()] } }),
    CONTEXT,
  );
  assert.equal(wrongContract.ok, false);
  if (!wrongContract.ok) assert.equal(wrongContract.error.code, "INVALID_ASSIGNMENT_LIST");

  const badUnits = await loadAssignments(
    transportWith({
      ok: true,
      data: { contract_version: "p6-resource-read-api.v1", assignments: [envelope({ ...ASSIGNMENT, units: "eight" })] },
    }),
    CONTEXT,
  );
  assert.equal(badUnits.ok, false);
  if (!badUnits.ok) assert.equal(badUnits.error.code, "INVALID_ASSIGNMENT_RECORD");
});

test("assignment create request carries the write contract version and nullable fields", async () => {
  const calls: Calls = { gets: [], posts: [] };
  const input: AssignmentInput = {
    assignmentId: "  AS-2 ",
    activityId: "A110",
    resourceId: " RPS-CIVIL-CREW ",
    roleId: "  ",
    units: " 4.5 ",
    unit: "day",
    plannedCost: "",
    currency: "",
    note: "  ",
  };
  const result = await saveAssignment(
    transportWith({ ok: true, data: envelope(ASSIGNMENT, "p6-resource-write-api.v1") }, calls),
    CONTEXT,
    input,
  );
  assert.equal(result.ok, true);
  assert.deepEqual(calls.posts, [{
    path: "/api/projects/project-1/p6/resource-assignments",
    request: {
      contract_version: "p6-resource-write-api.v1",
      assignment_id: "AS-2",
      activity_id: "A110",
      resource_id: "RPS-CIVIL-CREW",
      role_id: null,
      units: "4.5",
      unit: "day",
      planned_cost: null,
      currency: null,
      note: null,
    },
    idempotencyKey: calls.posts[0].idempotencyKey,
  }]);
  assert.equal(typeof calls.posts[0].idempotencyKey, "string");
});

test("assignment create refuses missing identity and malformed decimals without a write", async () => {
  const calls: Calls = { gets: [], posts: [] };
  const missing = await saveAssignment(transportWith({ ok: true, data: envelope() }, calls), CONTEXT, {
    assignmentId: "",
    activityId: "A110",
    resourceId: "R1",
    roleId: null,
    units: null,
    unit: null,
    plannedCost: null,
    currency: null,
    note: null,
  });
  assert.equal(missing.ok, false);
  if (!missing.ok) assert.equal(missing.error.code, "ASSIGNMENT_FIELDS_REQUIRED");

  const malformed = await saveAssignment(transportWith({ ok: true, data: envelope() }, calls), CONTEXT, {
    assignmentId: "AS-3",
    activityId: "A110",
    resourceId: "R1",
    roleId: null,
    units: "1e3",
    unit: null,
    plannedCost: null,
    currency: null,
    note: null,
  });
  assert.equal(malformed.ok, false);
  if (!malformed.ok) assert.equal(malformed.error.code, "INVALID_ASSIGNMENT_NUMBER");
  assert.equal(calls.posts.length, 0);
});

test("assignment payload never invents a value for an empty field", () => {
  assert.deepEqual(
    buildAssignmentPayload({
      assignmentId: "AS-4",
      activityId: "A120",
      resourceId: "R1",
      roleId: null,
      units: null,
      unit: null,
      plannedCost: null,
      currency: null,
      note: null,
    }),
    {
      contract_version: "p6-resource-write-api.v1",
      assignment_id: "AS-4",
      activity_id: "A120",
      resource_id: "R1",
      role_id: null,
      units: null,
      unit: null,
      planned_cost: null,
      currency: null,
      note: null,
    },
  );
  assert.throws(
    () => buildAssignmentPayload({
      assignmentId: "AS-5",
      activityId: "A120",
      resourceId: "R1",
      roleId: null,
      units: "  ",
      unit: null,
      plannedCost: "12,5",
      currency: null,
      note: null,
    }),
    /INVALID_ASSIGNMENT_NUMBER/,
  );
});

test("assignment parse rejects a missing identifier and non-boolean driving flag", () => {
  assert.throws(() => parseAssignment(envelope({ ...ASSIGNMENT, assignment_id: "" })), /INVALID_ASSIGNMENT_RECORD/);
  assert.throws(() => parseAssignment(envelope({ ...ASSIGNMENT, is_driving: "yes" })), /INVALID_ASSIGNMENT_RECORD/);
});
