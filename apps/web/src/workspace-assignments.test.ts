import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  addDecimalText,
  buildAssignmentPayload,
  buildAssignmentPeriodPayload,
  buildAssignmentProfile,
  cellValue,
  compareDecimalText,
  defaultAssignmentViewPrefs,
  filterAssignments,
  groupAssignments,
  loadAssignmentPeriods,
  loadAssignments,
  loadAssignmentViewPrefs,
  parseAssignment,
  parseAssignmentPeriod,
  reviseAssignmentId,
  saveAssignment,
  saveAssignmentPeriod,
  saveAssignmentViewPrefs,
  sortAssignments,
  type AssignmentInput,
  type AssignmentPeriod,
  type AssignmentRecord,
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

const PERIOD = {
  assignment_id: "AS-1",
  activity_id: "A100",
  resource_id: "RPS-CIVIL-CREW",
  period_start: "2026-01-05",
  units: "8",
  cost: "120.50",
};

function periodEnvelope(period: unknown = PERIOD, contract = "p6-resource-read-api.v1") {
  return {
    contract_version: contract,
    kind: "resource_assignment_period",
    scope: { tenant_id: "t1", project_id: "project-1", project_revision: 4 },
    period,
  };
}

function record(overrides: Partial<AssignmentRecord> = {}): AssignmentRecord {
  return {
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
    ...overrides,
  };
}

function memoryStorage(initial: Record<string, string> = {}) {
  const map = new Map(Object.entries(initial));
  return {
    getItem(key: string): string | null { return map.get(key) ?? null; },
    setItem(key: string, value: string): void { map.set(key, value); },
  };
}

test("decimal totals stay exact for fractional and beyond-safe-integer values", () => {
  assert.equal(addDecimalText(["0.1", "0.2"]), "0.3");
  assert.equal(addDecimalText(["1200.50", "300", null, undefined, "  "]), "1500.5");
  assert.equal(addDecimalText(["1.000", "2.0"]), "3");
  assert.equal(addDecimalText(["-1.25", "0.25"]), "-1");
  assert.equal(addDecimalText(["99999999999999999999.99", "0.01"]), "100000000000000000000");
  assert.equal(addDecimalText([]), null);
  assert.equal(addDecimalText([null, undefined]), null);
});

test("decimal comparison orders by numeric value and keeps empty values last", () => {
  assert.equal(compareDecimalText("8.0", "10"), -1);
  assert.equal(compareDecimalText("2.50", "2.5"), 0);
  assert.equal(compareDecimalText("-1", "-2"), 1);
  assert.equal(compareDecimalText(null, "1"), 1);
  assert.equal(compareDecimalText("1", null), -1);
  assert.equal(compareDecimalText(null, null), 0);
});

test("cells resolve stored values, localized labels and the driving flag", () => {
  const label = (id: string): string => `A100 Civil ${id}`;
  assert.equal(cellValue(record(), "assignment", label, { yes: "Yes", no: "No" }), "AS-1");
  assert.equal(cellValue(record(), "activity", label, { yes: "Yes", no: "No" }), "A100 Civil A100");
  assert.equal(cellValue(record({ isDriving: false }), "driving", label, { yes: "Yes", no: "No" }), "No");
  assert.equal(cellValue(record({ isDriving: null }), "driving", label, { yes: "Yes", no: "No" }), null);
  assert.equal(cellValue(record({ note: null }), "note", label, { yes: "Yes", no: "No" }), null);
});

test("filters match text, activity label and exact resource or activity selection", () => {
  const rows = [
    record({ assignmentId: "AS-1", activityId: "A100", resourceId: "R1", roleId: null, note: "Crew pour" }),
    record({ assignmentId: "AS-2", activityId: "A110", resourceId: "R2", roleId: "ROLE-2", note: "Steel fix" }),
  ];
  const label = (id: string): string => (id === "A100" ? "Foundations" : "Columns");
  const none = { query: "", resourceId: "", activityId: "" };
  assert.equal(filterAssignments(rows, none, label).length, 2);
  assert.deepEqual(filterAssignments(rows, { ...none, query: "  STEEL " }, label).map((row) => row.assignmentId), ["AS-2"]);
  assert.deepEqual(filterAssignments(rows, { ...none, query: "foundations" }, label).map((row) => row.assignmentId), ["AS-1"]);
  assert.deepEqual(filterAssignments(rows, { ...none, resourceId: "R2" }, label).map((row) => row.assignmentId), ["AS-2"]);
  assert.deepEqual(filterAssignments(rows, { ...none, activityId: "A100" }, label).map((row) => row.assignmentId), ["AS-1"]);
  assert.deepEqual(filterAssignments(rows, { ...none, query: "room-404" }, label), []);
});

test("sorting orders decimals numerically, nulls last and text with numeric awareness", () => {
  const rows = [
    record({ assignmentId: "AS-1", units: "10" }),
    record({ assignmentId: "AS-2", units: "9" }),
    record({ assignmentId: "AS-3", units: null }),
    record({ assignmentId: "AS-10", units: "9" }),
  ];
  const label = (id: string): string => id;
  assert.deepEqual(
    sortAssignments(rows, { column: "units", dir: "asc" }, label).map((row) => row.assignmentId),
    ["AS-2", "AS-10", "AS-1", "AS-3"],
  );
  assert.deepEqual(
    sortAssignments(rows, { column: "units", dir: "desc" }, label).map((row) => row.assignmentId),
    ["AS-3", "AS-1", "AS-2", "AS-10"],
  );
  assert.deepEqual(
    sortAssignments(rows, { column: "assignment", dir: "asc" }, label).map((row) => row.assignmentId),
    ["AS-1", "AS-2", "AS-3", "AS-10"],
  );
  assert.deepEqual(sortAssignments(rows, null, label).map((row) => row.assignmentId), ["AS-1", "AS-2", "AS-3", "AS-10"]);
});

test("grouping computes exact subtotals, labels activities and keeps unassigned roles", () => {
  const rows = [
    record({ assignmentId: "AS-1", activityId: "A100", resourceId: "R1", roleId: "ROLE-1", units: "1.5", plannedCost: "100", actualCost: "10" }),
    record({ assignmentId: "AS-2", activityId: "A100", resourceId: "R1", roleId: null, units: "2.5", plannedCost: "0.5", actualCost: "5" }),
    record({ assignmentId: "AS-3", activityId: "A110", resourceId: "R2", roleId: "ROLE-1", units: null, plannedCost: null, actualCost: null }),
  ];
  assert.deepEqual(groupAssignments(rows, "none"), []);

  const byResource = groupAssignments(rows, "resource");
  assert.deepEqual(byResource.map((group) => [group.key, group.label, group.rows.length]), [
    ["R1", "R1", 2],
    ["R2", "R2", 1],
  ]);
  assert.deepEqual(byResource[0].totals, { units: "4", plannedCost: "100.5", actualCost: "15" });
  assert.deepEqual(byResource[1].totals, { units: null, plannedCost: null, actualCost: null });

  const byActivity = groupAssignments(rows, "activity", (id) => `Activity ${id}`);
  assert.deepEqual(byActivity.map((group) => group.label), ["Activity A100", "Activity A110"]);

  const byRole = groupAssignments(rows, "role", (id) => id, "Unassigned");
  assert.deepEqual(byRole.map((group) => [group.key, group.label, group.rows.length]), [
    ["ROLE-1", "ROLE-1", 2],
    ["", "Unassigned", 1],
  ]);
});

test("profile orders stored periods, totals them and finds the peak bucket", () => {
  const periods: AssignmentPeriod[] = [
    { assignmentId: "AS-1", activityId: "A100", resourceId: "R1", periodStart: "2026-02-01", units: "4", cost: "40" },
    { assignmentId: "AS-2", activityId: "A110", resourceId: "R1", periodStart: "2026-01-01", units: "99", cost: "990" },
    { assignmentId: "AS-1", activityId: "A100", resourceId: "R1", periodStart: "2026-01-01", units: "8", cost: "120.50" },
  ];
  const profile = buildAssignmentProfile(periods, "AS-1");
  assert.deepEqual(profile.points, [
    { periodStart: "2026-01-01", units: "8", cost: "120.50" },
    { periodStart: "2026-02-01", units: "4", cost: "40" },
  ]);
  assert.equal(profile.totalUnits, "12");
  assert.equal(profile.totalCost, "160.5");
  assert.equal(profile.maxUnits, "8");

  const empty = buildAssignmentProfile(periods, "AS-404");
  assert.deepEqual(empty.points, []);
  assert.equal(empty.totalUnits, null);
  assert.equal(empty.totalCost, null);
  assert.equal(empty.maxUnits, null);
});

test("revision identifiers continue the -R sequence and skip taken numbers", () => {
  assert.equal(reviseAssignmentId("AS-1", ["AS-1"]), "AS-1-R2");
  assert.equal(reviseAssignmentId("AS-1", ["AS-1", "AS-1-R2"]), "AS-1-R3");
  assert.equal(reviseAssignmentId("AS-1-R2", ["AS-1-R2"]), "AS-1-R3");
  assert.equal(reviseAssignmentId("AS-1-R2", ["AS-1-R2", "AS-1-R3", "AS-1-R4"]), "AS-1-R5");
  assert.equal(reviseAssignmentId("CUSTOM", ["CUSTOM"]), "CUSTOM-R2");
});

test("period parsing accepts both resource contracts and fails closed on malformed facts", () => {
  assert.deepEqual(parseAssignmentPeriod(periodEnvelope()), {
    assignmentId: "AS-1",
    activityId: "A100",
    resourceId: "RPS-CIVIL-CREW",
    periodStart: "2026-01-05",
    units: "8",
    cost: "120.50",
  });
  assert.equal(
    parseAssignmentPeriod(periodEnvelope(PERIOD, "p6-resource-write-api.v1")).periodStart,
    "2026-01-05",
  );
  assert.throws(() => parseAssignmentPeriod(periodEnvelope(PERIOD, "other")), /INVALID_ASSIGNMENT_PERIOD_RESPONSE/);
  assert.throws(() => parseAssignmentPeriod(periodEnvelope({ ...PERIOD, period_start: "2026-1-5" })), /INVALID_ASSIGNMENT_PERIOD_RECORD/);
  assert.throws(() => parseAssignmentPeriod(periodEnvelope({ ...PERIOD, units: "eight" })), /INVALID_ASSIGNMENT_PERIOD_RECORD/);
  assert.throws(() => parseAssignmentPeriod(periodEnvelope({ ...PERIOD, cost: null })), /INVALID_ASSIGNMENT_PERIOD_RECORD/);
});

test("period payload trims identity, validates the ISO date and requires both values", () => {
  assert.deepEqual(
    buildAssignmentPeriodPayload({
      assignmentId: " AS-1 ",
      activityId: " A100 ",
      resourceId: " R1 ",
      periodStart: " 2026-03-02 ",
      units: " 8.5 ",
      cost: " 102.25 ",
    }),
    {
      assignment_id: "AS-1",
      activity_id: "A100",
      resource_id: "R1",
      period_start: "2026-03-02",
      units: "8.5",
      cost: "102.25",
    },
  );
  assert.throws(
    () => buildAssignmentPeriodPayload({ assignmentId: "", activityId: "A100", resourceId: "R1", periodStart: "2026-03-02", units: "1", cost: "1" }),
    /ASSIGNMENT_PERIOD_FIELDS_REQUIRED/,
  );
  assert.throws(
    () => buildAssignmentPeriodPayload({ assignmentId: "AS-1", activityId: "A100", resourceId: "R1", periodStart: "03/02/2026", units: "1", cost: "1" }),
    /INVALID_ASSIGNMENT_PERIOD_START/,
  );
  assert.throws(
    () => buildAssignmentPeriodPayload({ assignmentId: "AS-1", activityId: "A100", resourceId: "R1", periodStart: "2026-03-02", units: "", cost: "1" }),
    /ASSIGNMENT_PERIOD_VALUES_REQUIRED/,
  );
});

test("period list and save talk to the scoped period route with the write contract response", async () => {
  const calls: Calls = { gets: [], posts: [] };
  const listed = await loadAssignmentPeriods(
    transportWith({ ok: true, data: { contract_version: "p6-resource-read-api.v1", periods: [periodEnvelope()] } }, calls),
    CONTEXT,
  );
  assert.equal(listed.ok, true);
  if (listed.ok) assert.equal(listed.data[0].cost, "120.50");
  assert.deepEqual(calls.gets, [{ path: "/api/projects/project-1/p6/resource-assignment-periods" }]);

  const posted = await saveAssignmentPeriod(
    transportWith({ ok: true, data: periodEnvelope(PERIOD, "p6-resource-write-api.v1") }, calls),
    CONTEXT,
    { assignmentId: "AS-1", activityId: "A100", resourceId: "RPS-CIVIL-CREW", periodStart: "2026-01-05", units: "8", cost: "120.50" },
  );
  assert.equal(posted.ok, true);
  assert.deepEqual(calls.posts, [{
    path: "/api/projects/project-1/p6/resource-assignment-periods",
    request: {
      assignment_id: "AS-1",
      activity_id: "A100",
      resource_id: "RPS-CIVIL-CREW",
      period_start: "2026-01-05",
      units: "8",
      cost: "120.50",
    },
    idempotencyKey: calls.posts[0].idempotencyKey,
  }]);
  assert.equal(typeof calls.posts[0].idempotencyKey, "string");

  const foreign = await loadAssignmentPeriods(
    transportWith({ ok: true, data: { contract_version: "other", periods: [periodEnvelope()] } }),
    CONTEXT,
  );
  assert.equal(foreign.ok, false);
  if (!foreign.ok) assert.equal(foreign.error.code, "INVALID_ASSIGNMENT_PERIOD_LIST");

  const badRecord = await loadAssignmentPeriods(
    transportWith({ ok: true, data: { contract_version: "p6-resource-read-api.v1", periods: [periodEnvelope({ ...PERIOD, units: "many" })] } }),
    CONTEXT,
  );
  assert.equal(badRecord.ok, false);
  if (!badRecord.ok) assert.equal(badRecord.error.code, "INVALID_ASSIGNMENT_PERIOD_RECORD");
});

test("view preferences persist per project and fall back on foreign or corrupt payloads", () => {
  assert.deepEqual(loadAssignmentViewPrefs(null, "project-1"), defaultAssignmentViewPrefs());

  const storage = memoryStorage();
  const prefs = {
    groupBy: "resource" as const,
    sort: { column: "units" as const, dir: "desc" as const },
    columns: ["assignment", "units", "plannedCost"] as const,
  };
  saveAssignmentViewPrefs(storage, "project-1", { groupBy: prefs.groupBy, sort: prefs.sort, columns: [...prefs.columns] });
  assert.equal(
    storage.getItem("cubi.assignments.view.v1.project-2"),
    null,
  );
  assert.deepEqual(loadAssignmentViewPrefs(storage, "project-1"), {
    groupBy: "resource",
    sort: { column: "units", dir: "desc" },
    columns: ["assignment", "units", "plannedCost"],
  });
  assert.deepEqual(loadAssignmentViewPrefs(storage, "project-2"), defaultAssignmentViewPrefs());

  const corrupt = memoryStorage({ "cubi.assignments.view.v1.p": "{not-json" });
  assert.deepEqual(loadAssignmentViewPrefs(corrupt, "p"), defaultAssignmentViewPrefs());

  const foreign = memoryStorage({
    "cubi.assignments.view.v1.p": JSON.stringify({
      groupBy: "wbs",
      sort: { column: "missing", dir: "sideways" },
      columns: ["assignment", "missing", "units", "units"],
    }),
  });
  assert.deepEqual(loadAssignmentViewPrefs(foreign, "p"), {
    groupBy: "none",
    sort: null,
    columns: ["assignment", "units"],
  });

  const emptyColumns = memoryStorage({
    "cubi.assignments.view.v1.p": JSON.stringify({ groupBy: "role", sort: null, columns: ["nope"] }),
  });
  assert.deepEqual(loadAssignmentViewPrefs(emptyColumns, "p"), {
    groupBy: "role",
    sort: null,
    columns: defaultAssignmentViewPrefs().columns,
  });
});

