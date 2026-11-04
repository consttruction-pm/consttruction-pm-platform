import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  createRole,
  loadRole,
  loadRoles,
  updateRole,
  type RoleRecord,
} from "./workspace-roles.js";

const CONTEXT: ProjectContext = { tenant_id: "t1", project_id: "project-1", revision: 4 };

const ROLE = {
  role_id: "RPS-CIVIL",
  name: "Civil superintendent",
  description: "Site civil supervision",
  record_revision: 2,
};

function envelope(role: unknown = ROLE) {
  return {
    contract_version: "p6-role-api.v1",
    kind: "p6_role",
    scope: { tenant_id: "t1", project_id: "project-1", project_revision: 4 },
    role,
  };
}

type Calls = {
  gets: { path: string }[];
  posts: { path: string; request: unknown; idempotencyKey?: string }[];
  patches: { path: string; request: unknown }[];
};

function transportWith(
  result: ApiResult<unknown>,
  calls: Calls = { gets: [], posts: [], patches: [] },
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
    async patch(path, request) {
      calls.patches.push({ path, request });
      return result as ApiResult<never>;
    },
  };
}

test("role list reads the p6-role-api contract and preserves stored fields", async () => {
  const calls: Calls = { gets: [], posts: [], patches: [] };
  const result = await loadRoles(
    transportWith({ ok: true, data: { contract_version: "p6-role-api.v1", roles: [envelope()] } }, calls),
    CONTEXT,
  );
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.deepEqual(result.data, [{
    roleId: "RPS-CIVIL",
    name: "Civil superintendent",
    description: "Site civil supervision",
    recordRevision: 2,
  }]);
  assert.deepEqual(calls.gets, [{ path: "/api/projects/project-1/p6/roles" }]);
});

test("role list fails closed on a foreign contract or malformed role", async () => {
  const wrongContract = await loadRoles(
    transportWith({ ok: true, data: { contract_version: "other", roles: [envelope()] } }),
    CONTEXT,
  );
  assert.equal(wrongContract.ok, false);
  if (!wrongContract.ok) assert.equal(wrongContract.error.code, "INVALID_ROLE_LIST");

  const missingName = await loadRoles(
    transportWith({ ok: true, data: { contract_version: "p6-role-api.v1", roles: [envelope({ ...ROLE, name: "" })] } }),
    CONTEXT,
  );
  assert.equal(missingName.ok, false);
  if (!missingName.ok) assert.equal(missingName.error.code, "INVALID_ROLE_RECORD");
});

test("role read requests the selected identifier", async () => {
  const calls: Calls = { gets: [], posts: [], patches: [] };
  const result = await loadRole(transportWith({ ok: true, data: envelope() }, calls), CONTEXT, "RPS-CIVIL");
  assert.equal(result.ok, true);
  assert.deepEqual(calls.gets, [{ path: "/api/projects/project-1/p6/roles/RPS-CIVIL" }]);
});

test("role create posts trimmed identity and description", async () => {
  const calls: Calls = { gets: [], posts: [], patches: [] };
  const result = await createRole(
    transportWith({ ok: true, data: envelope() }, calls),
    CONTEXT,
    { roleId: "  RPS-CIVIL  ", name: "  Civil superintendent ", description: "  Site civil supervision  " },
  );
  assert.equal(result.ok, true);
  assert.deepEqual(calls.posts, [{
    path: "/api/projects/project-1/p6/roles",
    request: { role_id: "RPS-CIVIL", name: "Civil superintendent", description: "Site civil supervision" },
    idempotencyKey: calls.posts[0].idempotencyKey,
  }]);
  assert.equal(typeof calls.posts[0].idempotencyKey, "string");
});

test("role create rejects missing fields without a write", async () => {
  const calls: Calls = { gets: [], posts: [], patches: [] };
  const result = await createRole(transportWith({ ok: true, data: envelope() }, calls), CONTEXT, {
    roleId: " ",
    name: "Civil",
    description: null,
  });
  assert.equal(result.ok, false);
  if (!result.ok) assert.equal(result.error.code, "ROLE_FIELDS_REQUIRED");
  assert.equal(calls.posts.length, 0);
});

test("role update patches the persisted revision and nullable description", async () => {
  const calls: Calls = { gets: [], posts: [], patches: [] };
  const role: RoleRecord = { roleId: "RPS-CIVIL", name: "Old", description: "Old notes", recordRevision: 3 };
  const result = await updateRole(
    transportWith({ ok: true, data: envelope({ ...ROLE, record_revision: 4 }) }, calls),
    CONTEXT,
    role,
    { name: "Civil superintendent", description: "  " },
  );
  assert.equal(result.ok, true);
  assert.deepEqual(calls.patches, [{
    path: "/api/projects/project-1/p6/roles/RPS-CIVIL",
    request: { name: "Civil superintendent", description: null, expected_revision: 3 },
  }]);
});

test("role update refuses to write without a stored revision", async () => {
  const calls: Calls = { gets: [], posts: [], patches: [] };
  const result = await updateRole(
    transportWith({ ok: true, data: envelope() }, calls),
    CONTEXT,
    { roleId: "RPS-CIVIL", name: "Civil", description: null, recordRevision: 0 },
    { name: "Civil", description: null },
  );
  assert.equal(result.ok, false);
  if (!result.ok) assert.equal(result.error.code, "ROLE_REVISION_REQUIRED");
  assert.equal(calls.patches.length, 0);
});
