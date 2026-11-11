import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  createRole,
  loadRole,
  loadRoleLimits,
  loadRoleResourceOptions,
  loadRoleRates,
  loadRoleResources,
  loadRoles,
  removeRoleResource,
  roleRegisterRows,
  saveRoleLimit,
  saveRoleRate,
  saveRoleResource,
  updateRole,
  type RoleRecord,
} from "./workspace-roles.js";

const CONTEXT: ProjectContext = { tenant_id: "t1", project_id: "project-1", revision: 4 };

const ROLE = {
  role_id: "RPS-CIVIL",
  name: "Civil superintendent",
  description: "Site civil supervision",
  parent_role_id: null,
  calculate_costs_from_units: true,
  record_revision: 2,
};

const RATE = {
  role_id: "RPS-CIVIL",
  effective_from: "2026-01-01",
  rate_type: "Standard",
  rate: "85.5",
  unit: "h",
  currency: "USD",
  source: "manual-entry:u1",
  record_revision: 1,
};

const LIMIT = {
  role_id: "RPS-CIVIL",
  effective_from: "2026-01-01",
  max_units: "12",
  unit_basis: "units",
  record_revision: 1,
};

const RESOURCE = {
  role_id: "RPS-CIVIL",
  resource_id: "RES-A",
  proficiency: "skilled",
  is_primary: true,
  record_revision: 1,
};

function envelope(role: unknown = ROLE) {
  return {
    contract_version: "p6-role-api.v1",
    kind: "p6_role",
    scope: { tenant_id: "t1", project_id: "project-1", project_revision: 4 },
    role,
  };
}

function resourceEnvelope(resource: unknown = RESOURCE) {
  return {
    contract_version: "p6-role-resource-api.v1",
    kind: "role_resource",
    scope: { tenant_id: "t1", project_id: "project-1", project_revision: 4 },
    resource,
  };
}

type Call = { method: string; path: string; request?: unknown; idempotencyKey?: string };

function transportWith(
  respond: (call: Call) => ApiResult<unknown>,
  calls: Call[] = [],
): ApiTransport {
  const record = (call: Call): ApiResult<never> => {
    calls.push(call);
    return respond(call) as ApiResult<never>;
  };
  return {
    async get(path) {
      return record({ method: "GET", path });
    },
    async post(path, request, _context, idempotencyKey) {
      return record({ method: "POST", path, request, idempotencyKey });
    },
    async patch(path, request) {
      return record({ method: "PATCH", path, request });
    },
    async delete(path, request) {
      return record({ method: "DELETE", path, request });
    },
  };
}

function staticTransport(result: ApiResult<unknown>, calls: Call[] = []): ApiTransport {
  return transportWith(() => result, calls);
}

test("role list reads the p6-role-api contract and preserves hierarchy fields", async () => {
  const calls: Call[] = [];
  const result = await loadRoles(
    staticTransport({ ok: true, data: { contract_version: "p6-role-api.v1", roles: [envelope()] } }, calls),
    CONTEXT,
  );
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.deepEqual(result.data, [{
    roleId: "RPS-CIVIL",
    name: "Civil superintendent",
    description: "Site civil supervision",
    parentRoleId: null,
    calculateCostsFromUnits: true,
    recordRevision: 2,
  }]);
  assert.deepEqual(calls, [{ method: "GET", path: "/api/projects/project-1/p6/roles" }]);
});

test("role list fails closed on a foreign contract or malformed role", async () => {
  const wrongContract = await loadRoles(
    staticTransport({ ok: true, data: { contract_version: "other", roles: [envelope()] } }),
    CONTEXT,
  );
  assert.equal(wrongContract.ok, false);
  if (!wrongContract.ok) assert.equal(wrongContract.error.code, "INVALID_ROLE_LIST");

  const missingName = await loadRoles(
    staticTransport({ ok: true, data: { contract_version: "p6-role-api.v1", roles: [envelope({ ...ROLE, name: "" })] } }),
    CONTEXT,
  );
  assert.equal(missingName.ok, false);
  if (!missingName.ok) assert.equal(missingName.error.code, "INVALID_ROLE_RECORD");

  const badCostFlag = await loadRoles(
    staticTransport({ ok: true, data: { contract_version: "p6-role-api.v1", roles: [envelope({ ...ROLE, calculate_costs_from_units: "yes" })] } }),
    CONTEXT,
  );
  assert.equal(badCostFlag.ok, false);
  if (!badCostFlag.ok) assert.equal(badCostFlag.error.code, "INVALID_ROLE_RECORD");
});

test("role read requests the selected identifier", async () => {
  const calls: Call[] = [];
  const result = await loadRole(staticTransport({ ok: true, data: envelope() }, calls), CONTEXT, "RPS-CIVIL");
  assert.equal(result.ok, true);
  assert.deepEqual(calls, [{ method: "GET", path: "/api/projects/project-1/p6/roles/RPS-CIVIL" }]);
});

test("role create posts the hierarchy and cost-recalculation flag", async () => {
  const calls: Call[] = [];
  const result = await createRole(
    staticTransport({ ok: true, data: envelope() }, calls),
    CONTEXT,
    {
      roleId: "  RPS-CIVIL  ",
      name: "  Civil superintendent ",
      description: "  Site civil supervision  ",
      parentRoleId: " RPS-PROGRAM ",
      calculateCostsFromUnits: false,
    },
  );
  assert.equal(result.ok, true);
  assert.deepEqual(calls, [{
    method: "POST",
    path: "/api/projects/project-1/p6/roles",
    request: {
      role_id: "RPS-CIVIL",
      name: "Civil superintendent",
      description: "Site civil supervision",
      parent_role_id: "RPS-PROGRAM",
      calculate_costs_from_units: false,
    },
    idempotencyKey: calls[0]?.idempotencyKey,
  }]);
  assert.equal(typeof calls[0]?.idempotencyKey, "string");
});

test("role create rejects missing fields without a write", async () => {
  const calls: Call[] = [];
  const result = await createRole(staticTransport({ ok: true, data: envelope() }, calls), CONTEXT, {
    roleId: " ",
    name: "Civil",
    description: null,
    parentRoleId: null,
    calculateCostsFromUnits: true,
  });
  assert.equal(result.ok, false);
  if (!result.ok) assert.equal(result.error.code, "ROLE_FIELDS_REQUIRED");
  assert.equal(calls.length, 0);
});

test("role update patches the persisted revision and nullable description", async () => {
  const calls: Call[] = [];
  const role: RoleRecord = {
    roleId: "RPS-CIVIL",
    name: "Old",
    description: "Old notes",
    parentRoleId: null,
    calculateCostsFromUnits: true,
    recordRevision: 3,
  };
  const result = await updateRole(
    staticTransport({ ok: true, data: envelope({ ...ROLE, record_revision: 4 }) }, calls),
    CONTEXT,
    role,
    { name: "Civil superintendent", description: "  ", parentRoleId: "RPS-PROGRAM", calculateCostsFromUnits: false },
  );
  assert.equal(result.ok, true);
  assert.deepEqual(calls, [{
    method: "PATCH",
    path: "/api/projects/project-1/p6/roles/RPS-CIVIL",
    request: {
      name: "Civil superintendent",
      description: null,
      parent_role_id: "RPS-PROGRAM",
      calculate_costs_from_units: false,
      expected_revision: 3,
    },
  }]);
});

test("role update refuses to write without a stored revision", async () => {
  const calls: Call[] = [];
  const result = await updateRole(
    staticTransport({ ok: true, data: envelope() }, calls),
    CONTEXT,
    { roleId: "RPS-CIVIL", name: "Civil", description: null, parentRoleId: null, calculateCostsFromUnits: true, recordRevision: 0 },
    { name: "Civil", description: null, parentRoleId: null, calculateCostsFromUnits: true },
  );
  assert.equal(result.ok, false);
  if (!result.ok) assert.equal(result.error.code, "ROLE_REVISION_REQUIRED");
  assert.equal(calls.length, 0);
});

test("register rows order parents before children with hierarchy depth", () => {
  const base = { description: null, calculateCostsFromUnits: true, recordRevision: 1 };
  const rows = roleRegisterRows([
    { ...base, roleId: "B", name: "Child B", parentRoleId: "A" },
    { ...base, roleId: "A", name: "Root A", parentRoleId: null },
    { ...base, roleId: "C", name: "Grandchild C", parentRoleId: "B" },
    { ...base, roleId: "ORPHAN", name: "Unknown parent", parentRoleId: "MISSING" },
    { ...base, roleId: "X", name: "Cycle X", parentRoleId: "Y" },
    { ...base, roleId: "Y", name: "Cycle Y", parentRoleId: "X" },
  ]);
  assert.deepEqual(rows.map((row) => [row.roleId, row.depth]), [
    ["A", 0],
    ["B", 1],
    ["C", 2],
    ["ORPHAN", 0],
    ["X", 0],
    ["Y", 1],
  ]);
});

test("role rates read the rate contract and fail closed on malformed values", async () => {
  const calls: Call[] = [];
  const result = await loadRoleRates(
    staticTransport({ ok: true, data: { contract_version: "p6-role-rate-api.v1", rates: [RATE] } }, calls),
    CONTEXT,
    "RPS-CIVIL",
  );
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.deepEqual(result.data, [{
    effectiveFrom: "2026-01-01",
    rateType: "Standard",
    rate: "85.5",
    unit: "h",
    currency: "USD",
    source: "manual-entry:u1",
    recordRevision: 1,
  }]);
  assert.deepEqual(calls, [{ method: "GET", path: "/api/projects/project-1/p6/roles/RPS-CIVIL/rates" }]);

  const badCurrency = await loadRoleRates(
    staticTransport({ ok: true, data: { contract_version: "p6-role-rate-api.v1", rates: [{ ...RATE, currency: "usd" }] } }),
    CONTEXT,
    "RPS-CIVIL",
  );
  assert.equal(badCurrency.ok, false);
  if (!badCurrency.ok) assert.equal(badCurrency.error.code, "INVALID_ROLE_RATE");

  const badUnit = await loadRoleRates(
    staticTransport({ ok: true, data: { contract_version: "p6-role-rate-api.v1", rates: [{ ...RATE, unit: "x" }] } }),
    CONTEXT,
    "RPS-CIVIL",
  );
  assert.equal(badUnit.ok, false);
});

test("role rate create posts and rate update patches the effective date", async () => {
  const created = await saveRoleRate(
    staticTransport({
      ok: true,
      data: { contract_version: "p6-role-rate-api.v1", kind: "role_rate", rate: RATE },
    }, []),
    CONTEXT,
    "RPS-CIVIL",
    { effectiveFrom: "2026-01-01", rateType: " Standard ", rate: "85.5", unit: "h", currency: "usd", expectedRevision: null },
  );
  assert.equal(created.ok, true);

  const calls: Call[] = [];
  const updated = await saveRoleRate(
    staticTransport({
      ok: true,
      data: { contract_version: "p6-role-rate-api.v1", kind: "role_rate", rate: { ...RATE, record_revision: 2 } },
    }, calls),
    CONTEXT,
    "RPS-CIVIL",
    { effectiveFrom: "2026-01-01", rateType: "Standard", rate: "90", unit: "h", currency: "USD", expectedRevision: 1 },
  );
  assert.equal(updated.ok, true);
  assert.deepEqual(calls, [{
    method: "PATCH",
    path: "/api/projects/project-1/p6/roles/RPS-CIVIL/rates/2026-01-01",
    request: { rate_type: "Standard", rate: "90", unit: "h", currency: "USD", expected_revision: 1 },
  }]);
});

test("role limit create validates fields and update patches the effective date", async () => {
  const rejected = await saveRoleLimit(
    staticTransport({ ok: true, data: {} }),
    CONTEXT,
    "RPS-CIVIL",
    { effectiveFrom: "01/01/2026", maxUnits: "12", unitBasis: "units", expectedRevision: null },
  );
  assert.equal(rejected.ok, false);
  if (!rejected.ok) assert.equal(rejected.error.code, "ROLE_LIMIT_FIELDS_REQUIRED");

  const calls: Call[] = [];
  const updated = await saveRoleLimit(
    staticTransport({
      ok: true,
      data: { contract_version: "p6-role-limit-api.v1", kind: "role_limit", limit: { ...LIMIT, max_units: "80", unit_basis: "percent", record_revision: 2 } },
    }, calls),
    CONTEXT,
    "RPS-CIVIL",
    { effectiveFrom: "2026-01-01", maxUnits: "80", unitBasis: "percent", expectedRevision: 1 },
  );
  assert.equal(updated.ok, true);
  assert.deepEqual(calls, [{
    method: "PATCH",
    path: "/api/projects/project-1/p6/roles/RPS-CIVIL/limits/2026-01-01",
    request: { max_units: "80", unit_basis: "percent", expected_revision: 1 },
  }]);
});

test("role limits read the limit contract", async () => {
  const result = await loadRoleLimits(
    staticTransport({ ok: true, data: { contract_version: "p6-role-limit-api.v1", limits: [LIMIT] } }),
    CONTEXT,
    "RPS-CIVIL",
  );
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.deepEqual(result.data, [{
    effectiveFrom: "2026-01-01",
    maxUnits: "12",
    unitBasis: "units",
    recordRevision: 1,
  }]);
});

test("role resources read, assign, update and unassign with revisions", async () => {
  const list = await loadRoleResources(
    staticTransport({ ok: true, data: { contract_version: "p6-role-resource-api.v1", resources: [RESOURCE] } }),
    CONTEXT,
    "RPS-CIVIL",
  );
  assert.equal(list.ok, true);
  if (!list.ok) return;
  assert.deepEqual(list.data, [{ resourceId: "RES-A", proficiency: "skilled", isPrimary: true, recordRevision: 1 }]);

  const createCalls: Call[] = [];
  const created = await saveRoleResource(
    staticTransport({ ok: true, data: resourceEnvelope() }, createCalls),
    CONTEXT,
    "RPS-CIVIL",
    { resourceId: " RES-A ", proficiency: "skilled", isPrimary: true, expectedRevision: null },
  );
  assert.equal(created.ok, true);
  assert.deepEqual(createCalls, [{
    method: "POST",
    path: "/api/projects/project-1/p6/roles/RPS-CIVIL/resources",
    request: { proficiency: "skilled", is_primary: true, resource_id: "RES-A" },
    idempotencyKey: createCalls[0]?.idempotencyKey,
  }]);

  const patchCalls: Call[] = [];
  const updated = await saveRoleResource(
    staticTransport({ ok: true, data: resourceEnvelope({ ...RESOURCE, proficiency: "expert", record_revision: 2 }) }, patchCalls),
    CONTEXT,
    "RPS-CIVIL",
    { resourceId: "RES-A", proficiency: "expert", isPrimary: false, expectedRevision: 1 },
  );
  assert.equal(updated.ok, true);
  assert.deepEqual(patchCalls, [{
    method: "PATCH",
    path: "/api/projects/project-1/p6/roles/RPS-CIVIL/resources/RES-A",
    request: { proficiency: "expert", is_primary: false, expected_revision: 1 },
  }]);

  const deleteCalls: Call[] = [];
  const removed = await removeRoleResource(
    staticTransport({
      ok: true,
      data: {
        contract_version: "p6-role-resource-api.v1",
        kind: "role_resource_removed",
        resource_id: "RES-A",
        status: "REMOVED",
      },
    }, deleteCalls),
    CONTEXT,
    "RPS-CIVIL",
    "RES-A",
    2,
  );
  assert.equal(removed.ok, true);
  assert.deepEqual(deleteCalls, [{
    method: "DELETE",
    path: "/api/projects/project-1/p6/roles/RPS-CIVIL/resources/RES-A",
    request: { expected_revision: 2 },
  }]);
});

test("role resource options read the resource master contract", async () => {
  const calls: Call[] = [];
  const result = await loadRoleResourceOptions(
    staticTransport({
      ok: true,
      data: {
        contract_version: "p6-resource-api.v1",
        resources: [{
          contract_version: "p6-resource-api.v1",
          kind: "p6_resource",
          resource: { resource_id: "RES-A", name: "Civil crew", resource_type: "labor", is_active: true },
        }],
      },
    }, calls),
    CONTEXT,
  );
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.deepEqual(result.data, [{ resourceId: "RES-A", name: "Civil crew", resourceType: "labor" }]);
  assert.deepEqual(calls, [{ method: "GET", path: "/api/projects/project-1/p6/resources" }]);
});
