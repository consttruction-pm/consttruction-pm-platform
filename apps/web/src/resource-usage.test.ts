import assert from "node:assert/strict";
import test from "node:test";

import type { AssignmentPeriod, AssignmentRecord } from "./workspace-assignments.js";
import {
  buildResourceUsage,
  groupResourceUsagePeriods,
  normalizeDecimalText,
  parseAssignmentRate,
  resourceUsageResolveKey,
  summarizeResourceUsageRates,
  type CapacityResolution,
} from "./resource-usage.js";

function assignment(overrides: Partial<AssignmentRecord> = {}): AssignmentRecord {
  return {
    assignmentId: "AS-1",
    activityId: "A100",
    resourceId: "RPS-CIVIL-CREW",
    roleId: null,
    units: "8",
    actualUnits: null,
    remainingUnits: null,
    plannedCost: "1200",
    actualCost: null,
    remainingCost: null,
    unit: "crew-day",
    currency: "USD",
    calendarId: "CUBI-RPS-CAL",
    calendarVersion: null,
    note: null,
    isDriving: null,
    unitsPerTime: "4",
    unitsPerTimePeriod: "day",
    hoursPerUnitsTimePeriod: "8",
    ...overrides,
  };
}

function period(overrides: Partial<AssignmentPeriod> = {}): AssignmentPeriod {
  return {
    assignmentId: "AS-1",
    activityId: "A100",
    resourceId: "RPS-CIVIL-CREW",
    periodStart: "2026-09-30",
    units: "4",
    cost: "640.5",
    ...overrides,
  };
}

function resolved(capacity: string): CapacityResolution {
  return {
    status: "resolved",
    capacity,
    basis: "day",
    identity: "identity-1",
    source: "preview-fixture:capacity",
    errorCode: null,
  };
}

test("normalizeDecimalText canonicalizes stored decimals without changing values", () => {
  assert.equal(normalizeDecimalText("08.500"), "8.5");
  assert.equal(normalizeDecimalText("0.000"), "0");
  assert.equal(normalizeDecimalText("-0.0"), "0");
  assert.equal(normalizeDecimalText("-0.250"), "-0.25");
  assert.equal(normalizeDecimalText("100"), "100");
});

test("resource usage resolves one cache key per period and time definition", () => {
  assert.equal(
    resourceUsageResolveKey("2026-09-30", "DAY", "8.0"),
    "2026-09-30|day|8",
  );
  assert.equal(
    resourceUsageResolveKey("2026-09-30", "hour", "08"),
    "2026-09-30|hour|8",
  );
});

test("groupResourceUsagePeriods keeps only the selected resource and sums stored values exactly", () => {
  const groups = groupResourceUsagePeriods([
    period({ assignmentId: "AS-1", units: "0.1", cost: "0.2" }),
    period({ assignmentId: "AS-2", units: "0.2", cost: "0.3" }),
    period({ assignmentId: "AS-1", periodStart: "2026-10-16", units: "5", cost: "400" }),
    period({ assignmentId: "AS-9", resourceId: "OTHER", units: "99", cost: "99" }),
  ], "RPS-CIVIL-CREW");
  assert.deepEqual(groups.map((group) => group.periodStart), ["2026-09-30", "2026-10-16"]);
  assert.deepEqual(groups[0].assignmentIds, ["AS-1", "AS-2"]);
  assert.equal(groups[0].demandUnits, "0.3");
  assert.equal(groups[0].demandCost, "0.5");
  assert.equal(groups[1].demandUnits, "5");
});

test("parseAssignmentRate requires every stored Units/Time component and a known basis", () => {
  assert.deepEqual(parseAssignmentRate(assignment()), {
    assignmentId: "AS-1",
    unitsPerTime: "4",
    basis: "day",
    hoursPerTimePeriod: "8",
  });
  assert.equal(parseAssignmentRate(assignment({ unitsPerTime: null })), null);
  assert.equal(parseAssignmentRate(assignment({ unitsPerTimePeriod: null })), null);
  assert.equal(parseAssignmentRate(assignment({ hoursPerUnitsTimePeriod: null })), null);
  assert.equal(parseAssignmentRate(assignment({ unitsPerTimePeriod: "fortnight" })), null);
  assert.equal(parseAssignmentRate(assignment({ unitsPerTime: "not-a-decimal" })), null);
  assert.equal(parseAssignmentRate(assignment({ hoursPerUnitsTimePeriod: "0" })), null);
});

test("summarizeResourceUsageRates combines comparable rates and refuses partial or mixed definitions", () => {
  const group = {
    periodStart: "2026-09-30",
    assignmentIds: ["AS-1", "AS-2"],
    demandUnits: "8",
    demandCost: "100",
  };
  const comparable = summarizeResourceUsageRates(group, new Map([
    ["AS-1", assignment({ unitsPerTime: "4", unitsPerTimePeriod: "day", hoursPerUnitsTimePeriod: "8" })],
    ["AS-2", assignment({ assignmentId: "AS-2", unitsPerTime: "2.5", unitsPerTimePeriod: "day", hoursPerUnitsTimePeriod: "8.0" })],
  ]));
  assert.deepEqual(comparable, {
    state: "comparable",
    unitsPerTime: "6.5",
    basis: "day",
    hoursPerTimePeriod: "8",
  });

  assert.equal(summarizeResourceUsageRates(group, new Map([
    ["AS-1", assignment({ unitsPerTime: null })],
    ["AS-2", assignment({ assignmentId: "AS-2", unitsPerTime: null })],
  ])).state, "missing");

  assert.equal(summarizeResourceUsageRates(group, new Map([
    ["AS-1", assignment()],
    ["AS-2", assignment({ assignmentId: "AS-2", unitsPerTime: null })],
  ])).state, "partial");

  assert.equal(summarizeResourceUsageRates(group, new Map([
    ["AS-1", assignment()],
    ["AS-2", assignment({ assignmentId: "AS-2", unitsPerTimePeriod: "week" })],
  ])).state, "mixed");

  assert.equal(summarizeResourceUsageRates(group, new Map([
    ["AS-1", assignment()],
    ["AS-2", assignment({ assignmentId: "AS-2", hoursPerUnitsTimePeriod: "7.5" })],
  ])).state, "mixed");
});

test("buildResourceUsage compares summed Units/Time with the resolved capacity and reports excess exactly", () => {
  const group = {
    periodStart: "2026-09-30",
    assignmentIds: ["AS-1", "AS-2"],
    demandUnits: "16",
    demandCost: "100",
  };
  const assignments = new Map([
    ["AS-1", assignment({ unitsPerTime: "12", unitsPerTimePeriod: "day", hoursPerUnitsTimePeriod: "8" })],
    ["AS-2", assignment({ assignmentId: "AS-2", unitsPerTime: "4", unitsPerTimePeriod: "day", hoursPerUnitsTimePeriod: "8" })],
  ]);
  const key = resourceUsageResolveKey("2026-09-30", "day", "8");
  const [over] = buildResourceUsage([group], assignments, new Map([[key, resolved("8")]]));
  assert.equal(over.status, "overallocated");
  assert.equal(over.unitsPerTime, "16");
  assert.equal(over.capacity, "8");
  assert.equal(over.excess, "8");
  assert.equal(over.capacityIdentity, "identity-1");
  assert.equal(over.capacitySource, "preview-fixture:capacity");

  const [within] = buildResourceUsage([group], assignments, new Map([[key, resolved("16")]]));
  assert.equal(within.status, "within");
  assert.equal(within.excess, null);
});

test("buildResourceUsage never invents capacity or combines unrunnable rows", () => {
  const group = {
    periodStart: "2026-09-30",
    assignmentIds: ["AS-1"],
    demandUnits: "4",
    demandCost: "10",
  };
  const assignments = new Map([["AS-1", assignment()]]);
  const key = resourceUsageResolveKey("2026-09-30", "day", "8");

  const [missing] = buildResourceUsage([group], assignments, new Map([[key, {
    status: "not-registered",
    capacity: null,
    basis: null,
    identity: null,
    source: null,
    errorCode: "RESOURCE_CAPACITY_NOT_REGISTERED",
  } satisfies CapacityResolution]]));
  assert.equal(missing.status, "missing-capacity");
  assert.equal(missing.capacity, null);
  assert.equal(missing.errorCode, "RESOURCE_CAPACITY_NOT_REGISTERED");

  const [conflict] = buildResourceUsage([group], assignments, new Map([[key, {
    status: "conflict",
    capacity: null,
    basis: null,
    identity: null,
    source: null,
    errorCode: "CAPACITY_SEGMENTS_OVERLAP",
  } satisfies CapacityResolution]]));
  assert.equal(conflict.status, "capacity-conflict");

  const [unresolved] = buildResourceUsage([group], assignments, new Map());
  assert.equal(unresolved.status, "capacity-error");
  assert.equal(unresolved.errorCode, "RESOURCE_CAPACITY_RESOLUTION_MISSING");

  const [noRate] = buildResourceUsage([group], new Map([["AS-1", assignment({ unitsPerTime: null })]]), new Map());
  assert.equal(noRate.status, "missing-rate");
  assert.equal(noRate.unitsPerTime, null);
});
