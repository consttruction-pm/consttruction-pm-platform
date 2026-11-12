import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import type { AssignmentRecord } from "./workspace-assignments.js";
import {
  RESOURCE_API_VERSION,
  buildResourceRows,
  createResource,
  loadResourceWorkspace,
  parseCapacitySegment,
  parseRateFact,
  mountWorkspaceResourcesPage,
  parseResourceMaster,
  resourceSaveErrorNotice,
  sumDecimal,
  updateResource,
  type ResourceCapacitySegment,
  type ResourceInput,
  type ResourceMasterRecord,
  type ResourceRateFact,
} from "./workspace-resources.js";

const CONTEXT: ProjectContext = { tenant_id: "t1", project_id: "project-1", revision: 4 };
const RESOURCES_PATH = "/api/projects/project-1/p6/resources";

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

function master(overrides: Partial<ResourceMasterRecord> = {}): ResourceMasterRecord {
  return {
    resourceId: "RPS-CIVIL-CREW",
    name: "Riverside Civil Crew",
    resourceType: "labor",
    parentResourceId: null,
    calendarId: "CUBI-RPS-CAL",
    defaultUnitsPerTime: "8",
    unitOfMeasure: "crew",
    email: null,
    isActive: true,
    recordRevision: 1,
    ...overrides,
  };
}

function input(overrides: Partial<ResourceInput> = {}): ResourceInput {
  return {
    resourceId: "RPS-CRANE",
    name: "Tower Crane",
    resourceType: "nonlabor",
    parentResourceId: "RPS-CIVIL-CREW",
    calendarId: null,
    defaultUnitsPerTime: "4.5",
    unitOfMeasure: null,
    email: "crew@example.test",
    isActive: false,
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

function resourceDto(record: ResourceMasterRecord) {
  return {
    contract_version: RESOURCE_API_VERSION,
    kind: "p6_resource",
    scope: { tenant_id: "t1", project_id: "project-1", project_revision: 4 },
    resource: {
      resource_id: record.resourceId,
      name: record.name,
      resource_type: record.resourceType,
      parent_resource_id: record.parentResourceId,
      calendar_id: record.calendarId,
      default_units_per_time: record.defaultUnitsPerTime,
      unit_of_measure: record.unitOfMeasure,
      email: record.email,
      is_active: record.isActive,
      record_revision: record.recordRevision,
    },
  };
}

function resourceList(...records: ResourceMasterRecord[]) {
  return { contract_version: RESOURCE_API_VERSION, resources: records.map(resourceDto) };
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

test("capacity, rate and resource master parsers keep the stored contract fields", () => {
  assert.deepEqual(parseCapacitySegment(capacityDto(segment())), segment());
  assert.deepEqual(parseRateFact(rateDto(rate())), rate());
  assert.deepEqual(parseResourceMaster(resourceDto(master()).resource), master());

  assert.throws(() => parseCapacitySegment(capacityDto(segment(), "resource_capacity_profile")), /INVALID_RESOURCE_CAPACITY/);
  assert.throws(() => parseCapacitySegment({ kind: "resource_capacity_segment" }), /INVALID_RESOURCE_CAPACITY/);
  assert.throws(() => parseRateFact({ ...rateDto(rate()), rate: "free" }), /INVALID_RESOURCE_RATE/);
  assert.throws(() => parseResourceMaster({ ...resourceDto(master()).resource, resource_type: "equipment" }), /INVALID_RESOURCE_RECORD/);
  assert.throws(() => parseResourceMaster({ ...resourceDto(master()).resource, is_active: "yes" }), /INVALID_RESOURCE_RECORD/);
  assert.throws(() => parseResourceMaster({ ...resourceDto(master()).resource, record_revision: -1 }), /INVALID_RESOURCE_RECORD/);
  assert.throws(() => parseResourceMaster({ ...resourceDto(master()).resource, default_units_per_time: "many" }), /INVALID_RESOURCE_RECORD/);
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
  assert.equal(crew.master, null);
  assert.equal(crew.name, null);
  assert.equal(crew.depth, 0);
  assert.deepEqual(crew.capacities.map((item) => item.effectiveFrom), ["2026-09-21", "2026-10-15"]);
  assert.deepEqual(crew.rates.map((item) => item.rate), ["480.00", "525.00"]);

  const design = rows[0];
  assert.equal(design.budgetedUnits, "4");
  assert.equal(design.latestMaxUnits, "4");
  assert.equal(design.rates.length, 0);
});

test("buildResourceRows merges master records into a parents-first hierarchy with fact-only rows", () => {
  const rows = buildResourceRows(
    [
      assignment({ assignmentId: "AS-1", resourceId: "R-CREW-A", units: "3" }),
      assignment({ assignmentId: "AS-2", resourceId: "R-FACT-ONLY", units: "2" }),
    ],
    [segment({ resourceId: "R-CREW", identity: "R-CREW", maxUnits: "6" })],
    [],
    [
      master({ resourceId: "R-CREW-B", name: "Crew B", parentResourceId: "R-CREW" }),
      master({ resourceId: "R-CREW-A-1", name: "Crew A1", parentResourceId: "R-CREW-A" }),
      master({ resourceId: "R-CREW", name: "Civil Crew", defaultUnitsPerTime: "6" }),
      master({ resourceId: "R-CREW-A", name: "Crew A", parentResourceId: "R-CREW" }),
      master({ resourceId: "R-LEGACY", name: "Legacy Resource", calendarId: null, defaultUnitsPerTime: null, unitOfMeasure: null }),
    ],
  );

  assert.deepEqual(rows.map((row) => [row.resourceId, row.depth, row.hasChildren]), [
    ["R-CREW", 0, true],
    ["R-CREW-A", 1, true],
    ["R-CREW-A-1", 2, false],
    ["R-CREW-B", 1, false],
    ["R-FACT-ONLY", 0, false],
    ["R-LEGACY", 0, false],
  ]);
  assert.equal(rows[1].name, "Crew A");
  assert.equal(rows[1].master?.recordRevision, 1);
  assert.equal(rows[1].budgetedUnits, "3");
  assert.equal(rows[0].latestMaxUnits, "6");
  assert.equal(rows[4].master, null);
  assert.equal(rows[4].budgetedUnits, "2");
  assert.equal(rows[5].name, "Legacy Resource");
  assert.equal(rows[5].assignments.length, 0);

  const cyclic = buildResourceRows([], [], [], [
    master({ resourceId: "R-A", name: "A", parentResourceId: "R-B" }),
    master({ resourceId: "R-B", name: "B", parentResourceId: "R-A" }),
  ]);
  assert.deepEqual(cyclic.map((row) => row.resourceId).sort(), ["R-A", "R-B"]);
});

test("loadResourceWorkspace reads assignments, capacity, rates and the resource master from their own endpoints", async () => {
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
    [RESOURCES_PATH]: { ok: true, data: resourceList(master()) },
  }, gets);

  const result = await loadResourceWorkspace(transport, CONTEXT);
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.equal(result.data.assignments.length, 1);
  assert.deepEqual(result.data.capacities, [segment()]);
  assert.deepEqual(result.data.rates, [rate()]);
  assert.deepEqual(result.data.resources, [master()]);
  assert.deepEqual(gets.sort(), [
    "/api/projects/project-1/p6/resource-assignments",
    "/api/projects/project-1/p6/resource-capacities",
    "/api/projects/project-1/p6/resource-rates",
    "/api/projects/project-1/p6/resources",
  ]);
});

test("loadResourceWorkspace fails closed on a foreign contract or unreadable list", async () => {
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
    [RESOURCES_PATH]: { ok: true, data: resourceList() },
  }), CONTEXT);
  assert.equal(foreignCapacity.ok, false);
  if (!foreignCapacity.ok) assert.equal(foreignCapacity.error.code, "INVALID_RESOURCE_CAPACITY_LIST");

  const foreignResources = await loadResourceWorkspace(transportWith({
    "/api/projects/project-1/p6/resource-assignments": {
      ok: true,
      data: { contract_version: "p6-resource-read-api.v1", assignments: [] },
    },
    "/api/projects/project-1/p6/resource-capacities": {
      ok: true,
      data: { contract_version: "p6-resource-capacity-read-api.v1", capacities: [] },
    },
    "/api/projects/project-1/p6/resource-rates": {
      ok: true,
      data: { contract_version: "p6-resource-rate-read-api.v1", rates: [] },
    },
    [RESOURCES_PATH]: { ok: true, data: { contract_version: "p6-resource-api.v0", resources: [] } },
  }), CONTEXT);
  assert.equal(foreignResources.ok, false);
  if (!foreignResources.ok) assert.equal(foreignResources.error.code, "INVALID_RESOURCE_LIST");

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
    [RESOURCES_PATH]: { ok: true, data: resourceList() },
  }), CONTEXT);
  assert.equal(assignmentFailure.ok, false);
  if (!assignmentFailure.ok) assert.equal(assignmentFailure.error.code, "RESOURCE_READ_NOT_AUTHORIZED");
});

test("createResource posts the trimmed master payload with an idempotency key", async () => {
  const posts: { path: string; body: Record<string, unknown>; key: string }[] = [];
  const expected = master({
    resourceId: "RPS-CRANE",
    name: "Tower Crane",
    resourceType: "nonlabor",
    parentResourceId: "RPS-CIVIL-CREW",
    calendarId: null,
    defaultUnitsPerTime: "4.5",
    unitOfMeasure: null,
    email: "crew@example.test",
    isActive: false,
    recordRevision: 1,
  });
  const transport: ApiTransport = {
    async get<T>(): Promise<ApiResult<T>> {
      throw new Error("create must not read");
    },
    async post<TRequest, TResponse>(path: string, request: TRequest, _context: ProjectContext, key?: string): Promise<ApiResult<TResponse>> {
      posts.push({ path, body: request as Record<string, unknown>, key: key ?? "" });
      return { ok: true, data: resourceDto(expected) } as ApiResult<TResponse>;
    },
  };

  const result = await createResource(transport, CONTEXT, input({
    parentResourceId: " RPS-CIVIL-CREW ",
    email: " crew@example.test ",
  }));
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.deepEqual(result.data, expected);
  assert.equal(posts.length, 1);
  assert.equal(posts[0].path, RESOURCES_PATH);
  assert.ok(posts[0].key.length > 0);
  assert.deepEqual(posts[0].body, {
    resource_id: "RPS-CRANE",
    name: "Tower Crane",
    resource_type: "nonlabor",
    parent_resource_id: "RPS-CIVIL-CREW",
    calendar_id: null,
    default_units_per_time: "4.5",
    unit_of_measure: null,
    email: "crew@example.test",
    is_active: false,
  });

  const missing = await createResource(transport, CONTEXT, input({ resourceId: " " }));
  assert.equal(missing.ok, false);
  if (!missing.ok) assert.equal(missing.error.code, "RESOURCE_FIELDS_REQUIRED");
  assert.equal(posts.length, 1);
});

test("updateResource patches with expected_revision and refuses missing or stale revisions", async () => {
  const patches: { path: string; body: Record<string, unknown> }[] = [];
  const transport: ApiTransport = {
    async get<T>(): Promise<ApiResult<T>> {
      throw new Error("update must not read");
    },
    async post<TRequest, TResponse>(): Promise<ApiResult<TResponse>> {
      throw new Error("update must not create");
    },
    async patch<TRequest, TResponse>(path: string, request: TRequest): Promise<ApiResult<TResponse>> {
      patches.push({ path, body: request as Record<string, unknown> });
      if ((request as { expected_revision?: number }).expected_revision === 1) {
        return { ok: true, data: resourceDto(master({ name: "Renamed Crew", recordRevision: 2 })) } as ApiResult<TResponse>;
      }
      return {
        ok: false,
        error: { code: "REVISION_CONFLICT", retryable: false, message_key: "error.p6.resource.conflict", available_actions: [] },
      } as ApiResult<TResponse>;
    },
  };

  const updated = await updateResource(transport, CONTEXT, master({ recordRevision: 1 }), input({
    resourceId: "IGNORED",
    name: "Renamed Crew",
    resourceType: "labor",
    parentResourceId: null,
    calendarId: "CUBI-RPS-CAL",
    defaultUnitsPerTime: "8",
    unitOfMeasure: "crew",
    email: null,
    isActive: true,
  }));
  assert.equal(updated.ok, true);
  if (updated.ok) {
    assert.equal(updated.data.name, "Renamed Crew");
    assert.equal(updated.data.recordRevision, 2);
  }
  assert.equal(patches.length, 1);
  assert.equal(patches[0].path, `${RESOURCES_PATH}/RPS-CIVIL-CREW`);
  assert.deepEqual(patches[0].body, {
    resource_id: "RPS-CIVIL-CREW",
    name: "Renamed Crew",
    resource_type: "labor",
    parent_resource_id: null,
    calendar_id: "CUBI-RPS-CAL",
    default_units_per_time: "8",
    unit_of_measure: "crew",
    email: null,
    is_active: true,
    expected_revision: 1,
  });

  const stale = await updateResource(transport, CONTEXT, master({ recordRevision: 99 }), input());
  assert.equal(stale.ok, false);
  if (!stale.ok) assert.equal(stale.error.code, "REVISION_CONFLICT");
  assert.equal(patches.length, 2);

  const unpersisted = await updateResource(transport, CONTEXT, master({ recordRevision: 0 }), input());
  assert.equal(unpersisted.ok, false);
  if (!unpersisted.ok) assert.equal(unpersisted.error.code, "RESOURCE_REVISION_REQUIRED");
  assert.equal(patches.length, 2);
});


function calendarCatalogue(...entries: { id: string; version: string; name: string }[]) {
  return {
    contract_version: "p6-calendar-read-api.v1",
    kind: "calendar_catalog",
    calendars: entries.map((entry) => ({
      calendar_id: entry.id,
      calendar_version: entry.version,
      kind: "working-day",
      calendar_type: "resource",
      name: entry.name,
      record_revision: 1,
    })),
  };
}

function mountHost() {
  const listeners = new Map<string, (event: Event) => void>();
  const host = {
    dataset: {} as Record<string, string>,
    innerHTML: "",
    addEventListener: (type: string, listener: (event: Event) => void) => listeners.set(type, listener),
    querySelectorAll: () => [],
    querySelector: () => null,
    contains: () => true,
  };
  const click = (action: string): void => {
    const target = {
      dataset: { resourceAction: action },
      closest: (selector: string) => (selector === "[data-resource-action]" ? target : null),
    };
    listeners.get("click")?.({ target } as unknown as Event);
  };
  return { host, click };
}

function resourceWorkspaceTransport(calendars: unknown) {
  return transportWith({
    "/api/projects/project-1/p6/resource-assignments": {
      ok: true,
      data: { contract_version: "p6-resource-read-api.v1", assignments: [assignmentDto()] },
    },
    "/api/projects/project-1/p6/resource-capacities": {
      ok: true,
      data: { contract_version: "p6-resource-capacity-read-api.v1", capacities: [] },
    },
    "/api/projects/project-1/p6/resource-rates": {
      ok: true,
      data: { contract_version: "p6-resource-rate-read-api.v1", rates: [] },
    },
    [RESOURCES_PATH]: { ok: true, data: resourceList(master()) },
    "/api/projects/project-1/p6/calendars": { ok: true, data: calendars },
  });
}

test("resource editor offers the stored calendars instead of a free-text id", async () => {
  const { host, click } = mountHost();
  mountWorkspaceResourcesPage(host as unknown as HTMLElement, {
    transport: resourceWorkspaceTransport(
      calendarCatalogue(
        { id: "CUBI-RPS-CAL", version: "v2", name: "Riverside resource calendar" },
        { id: "CUBI-RPS-CAL", version: "v1", name: "Riverside resource calendar" },
      ),
    ),
    context: CONTEXT,
    locale: "en",
  });
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.match(host.innerHTML, /Riverside Civil Crew/);

  click("new");
  assert.match(host.innerHTML, /<select name="resource-calendar">/);
  assert.match(host.innerHTML, /Project calendar \(default\)/);
  assert.match(host.innerHTML, /Riverside resource calendar — CUBI-RPS-CAL \(v1, v2\)/);
  assert.doesNotMatch(host.innerHTML, /<input name="resource-calendar"/);
});

test("resource editor falls back to a typed calendar id when the catalogue is empty", async () => {
  const { host, click } = mountHost();
  mountWorkspaceResourcesPage(host as unknown as HTMLElement, {
    transport: resourceWorkspaceTransport(calendarCatalogue()),
    context: CONTEXT,
    locale: "en",
  });
  await new Promise((resolve) => setTimeout(resolve, 0));
  click("new");
  assert.match(host.innerHTML, /<input name="resource-calendar"/);
  assert.match(host.innerHTML, /No calendar is stored in this project yet/);
});

test("resource save errors keep the calendar domain code visible", () => {
  assert.equal(
    resourceSaveErrorNotice("RESOURCE_CALENDAR_NOT_FOUND", true, "en"),
    "The selected calendar is not stored in this project. Choose a stored calendar or the project default. (RESOURCE_CALENDAR_NOT_FOUND)",
  );
  assert.match(resourceSaveErrorNotice("REVISION_CONFLICT", false, "fa"), /ذخیره ناموفق بود \(REVISION_CONFLICT\)/);
});
