import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import type { AssignmentRecord } from "./workspace-assignments.js";
import {
  buildResourceRows,
  loadResourceWorkspace,
  parseCapacitySegment,
  parseRateFact,
  sumDecimal,
  type ResourceCapacitySegment,
  type ResourceRateFact,
} from "./workspace-resources.js";

const CONTEXT: ProjectContext = { tenant_id: "t1", project_id: "project-1", revision: 4 };

function assignment(overrides: Partial<AssignmentRecord> = {}): AssignmentRecord {
  return {
    assignmentId: "AS-1",
    activityId: "A100",
    resourceId: "RPS-CIVIL-CREW",
    roleId: null,
    units: "8.0",
    actualUnits: null,
    remainingUnits: null,
    plannedCost: "1200.50",
    actualCost: "300",
    remainingCost: null,
    unit: "hour",
    currency: "USD",
    calendarId: "CUBI-RPS-CAL",
    calendarVersion: null,
    note: null,
    isDriving: null,
    unitsPerTime: null,
    unitsPerTimePeriod: null,
    hoursPerUnitsTimePeriod: null,
    ...overrides,
  };
}

function segment(overrides: Partial<ResourceCapacitySegment> = {}): ResourceCapacitySegment {
  return {
    resourceId: "RPS-CIVIL-CREW",
    identity: "RPS-CIVIL-CREW",
    maxUnits: "8",
    unitBasis: "day",
    hoursPerTimePeriod: "8",
    unitsPerHour: null,
    effectiveFrom: "2026-09-21",
    effectiveTo: "2026-10-14",
    source: "preview-fixture:RPS-rev7-capacity-1",
    ...overrides,
  };
}

function rate(overrides: Partial<ResourceRateFact> = {}): ResourceRateFact {
  return {
    resourceId: "RPS-CIVIL-CREW",
    identity: "RPS-CIVIL-CREW",
    rate: "480.00",
    basis: "per_day",
    currency: "USD",
    unit: "crew-day",
    effectiveFrom: "2026-09-21",
    effectiveTo: "2026-10-14",
    source: "preview-fixture:RPS-rev7-rate-1",
    ...overrides,
  };
}

function capacityDto(capacity: ResourceCapacitySegment, kind = "resource_capacity_segment") {
  return {
    contract_version: "p6-resource-capacity-read-api.v1",
    kind,
    scope: { tenant_id: "t1", project_id: "project-1", project_revision: 4 },
    capacity: {
      resource_id: capacity.resourceId,
      identity: capacity.identity,
      max_units: capacity.maxUnits,
      unit_basis: capacity.unitBasis,
      hours_per_time_period: capacity.hoursPerTimePeriod,
      units_per_hour: capacity.unitsPerHour,
      effective_from: capacity.effectiveFrom,
      effective_to: capacity.effectiveTo,
      source: capacity.source,
    },
  };
}

function rateDto(fact: ResourceRateFact) {
  return {
    resource_id: fact.resourceId,
    identity: fact.identity,
    rate: fact.rate,
    basis: fact.basis,
    currency: fact.currency,
    unit: fact.unit,
    effective_from: fact.effectiveFrom,
    effective_to: fact.effectiveTo,
    source: fact.source,
  };
}

const ASSIGNMENT_DTO = {
  assignment_id: "AS-1",
  activity_id: "A100",
  resource_id: "RPS-CIVIL-CREW",
  role_id: null,
  units: "8.0",
  actual_units: null,
  remaining_units: null,
  planned_cost: "1200.50",
  actual_cost: "300",
  remaining_cost: null,
  unit: "hour",
  currency: "USD",
  calendar_id: "CUBI-RPS-CAL",
  calendar_version: null,
  note: null,
  is_driving: null,
  units_per_time: null,
  units_per_time_period: null,
  hours_per_units_time_period: null,
};

function assignmentDto(assignmentValue: Record<string, unknown> = ASSIGNMENT_DTO) {
  return {
    contract_version: "p6-resource-read-api.v1",
    kind: "resource_assignment",
    scope: { tenant_id: "t1", project_id: "project-1", project_revision: 4 },
    assignment: assignmentValue,
  };
}

function transportWith(routes: Record<string, ApiResult<unknown>>, gets: string[] = []): ApiTransport {
  return {
    async get<T>(path: string): Promise<ApiResult<T>> {
      gets.push(path);
      const result = routes[path];
      if (!result) throw new Error(`unexpected GET ${path}`);
      return result as ApiResult<T>;
    },
    async post<TRequest, TResponse>(): Promise<ApiResult<TResponse>> {
      throw new Error("resource workspace must not write");
    },
  };
}

test("sumDecimal keeps exact decimal addition instead of float rounding", () => {
  assert.equal(sumDecimal(["0.1", "0.2"]), "0.3");
  assert.equal(sumDecimal(["8.0", "2.5"]), "10.5");
  assert.equal(sumDecimal(["1200.50", "300", "0.005"]), "1500.505");
  assert.equal(sumDecimal(["-2.5", "1"]), "-1.5");
  assert.equal(sumDecimal(["10.00", "-10"]), "0");
  assert.equal(sumDecimal([]), null);
  assert.equal(sumDecimal([null, null]), null);
});

test("capacity and rate parsers keep the stored contract fields", () => {
  assert.deepEqual(parseCapacitySegment(capacityDto(segment())), segment());
  assert.deepEqual(parseRateFact(rateDto(rate())), rate());

  assert.throws(() => parseCapacitySegment(capacityDto(segment(), "resource_capacity_profile")), /INVALID_RESOURCE_CAPACITY/);
  assert.throws(() => parseCapacitySegment({ kind: "resource_capacity_segment" }), /INVALID_RESOURCE_CAPACITY/);
  assert.throws(() => parseRateFact({ ...rateDto(rate()), rate: "free" }), /INVALID_RESOURCE_RATE/);
});

test("buildResourceRows groups facts per resource and reports the latest stored capacity segment", () => {
  const rows = buildResourceRows(
    [
      assignment({ assignmentId: "AS-1", units: "8.0", plannedCost: "1200.50", actualCost: "300" }),
      assignment({ assignmentId: "AS-2", units: "2.5", plannedCost: "400.25", actualCost: null }),
      assignment({ assignmentId: "AS-3", resourceId: "NSE-DESIGN-TEAM", units: "4", plannedCost: "100", actualCost: "0", currency: "IRR", calendarId: null }),
    ],
    [
      segment({ effectiveFrom: "2026-09-21", effectiveTo: "2026-10-14", maxUnits: "8" }),
      segment({ effectiveFrom: "2026-10-15", effectiveTo: null, maxUnits: "12" }),
      segment({ resourceId: "NSE-DESIGN-TEAM", identity: "NSE-DESIGN-TEAM", effectiveFrom: "2027-02-02", effectiveTo: null, maxUnits: "4" }),
    ],
    [
      rate({ effectiveFrom: "2026-09-21", effectiveTo: "2026-10-14", rate: "480.00" }),
      rate({ effectiveFrom: "2026-10-15", effectiveTo: null, rate: "525.00" }),
    ],
  );

  assert.deepEqual(rows.map((row) => row.resourceId), ["NSE-DESIGN-TEAM", "RPS-CIVIL-CREW"]);
  const crew = rows[1];
  assert.equal(crew.assignments.length, 2);
  assert.equal(crew.budgetedUnits, "10.5");
  assert.equal(crew.plannedCost, "1600.75");
  assert.equal(crew.actualCost, "300");
  assert.equal(crew.latestMaxUnits, "12");
  assert.equal(crew.latestEffectiveFrom, "2026-10-15");
  assert.deepEqual(crew.capacities.map((item) => item.effectiveFrom), ["2026-09-21", "2026-10-15"]);
  assert.deepEqual(crew.rates.map((item) => item.rate), ["480.00", "525.00"]);

  const design = rows[0];
  assert.equal(design.budgetedUnits, "4");
  assert.equal(design.latestMaxUnits, "4");
  assert.equal(design.rates.length, 0);
});

test("loadResourceWorkspace reads assignments, capacity and rates from their own endpoints", async () => {
  const gets: string[] = [];
  const transport = transportWith({
    "/api/projects/project-1/p6/resource-assignments": {
      ok: true,
      data: { contract_version: "p6-resource-read-api.v1", assignments: [assignmentDto()] },
    },
    "/api/projects/project-1/p6/resource-capacities": {
      ok: true,
      data: { contract_version: "p6-resource-capacity-read-api.v1", capacities: [capacityDto(segment())] },
    },
    "/api/projects/project-1/p6/resource-rates": {
      ok: true,
      data: { contract_version: "p6-resource-rate-read-api.v1", rates: [rateDto(rate())] },
    },
  }, gets);

  const result = await loadResourceWorkspace(transport, CONTEXT);
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.equal(result.data.assignments.length, 1);
  assert.deepEqual(result.data.capacities, [segment()]);
  assert.deepEqual(result.data.rates, [rate()]);
  assert.deepEqual(gets.sort(), [
    "/api/projects/project-1/p6/resource-assignments",
    "/api/projects/project-1/p6/resource-capacities",
    "/api/projects/project-1/p6/resource-rates",
  ]);
});

test("loadResourceWorkspace fails closed on a foreign contract or unreadable assignment list", async () => {
  const foreignCapacity = await loadResourceWorkspace(transportWith({
    "/api/projects/project-1/p6/resource-assignments": {
      ok: true,
      data: { contract_version: "p6-resource-read-api.v1", assignments: [] },
    },
    "/api/projects/project-1/p6/resource-capacities": {
      ok: true,
      data: { contract_version: "other", capacities: [] },
    },
    "/api/projects/project-1/p6/resource-rates": {
      ok: true,
      data: { contract_version: "p6-resource-rate-read-api.v1", rates: [] },
    },
  }), CONTEXT);
  assert.equal(foreignCapacity.ok, false);
  if (!foreignCapacity.ok) assert.equal(foreignCapacity.error.code, "INVALID_RESOURCE_CAPACITY_LIST");

  const assignmentFailure = await loadResourceWorkspace(transportWith({
    "/api/projects/project-1/p6/resource-assignments": {
      ok: false,
      error: { code: "RESOURCE_READ_NOT_AUTHORIZED", retryable: false, message_key: "error.authorization.denied", available_actions: [] },
    },
    "/api/projects/project-1/p6/resource-capacities": {
      ok: true,
      data: { contract_version: "p6-resource-capacity-read-api.v1", capacities: [] },
    },
    "/api/projects/project-1/p6/resource-rates": {
      ok: true,
      data: { contract_version: "p6-resource-rate-read-api.v1", rates: [] },
    },
  }), CONTEXT);
  assert.equal(assignmentFailure.ok, false);
  if (!assignmentFailure.ok) assert.equal(assignmentFailure.error.code, "RESOURCE_READ_NOT_AUTHORIZED");
});
