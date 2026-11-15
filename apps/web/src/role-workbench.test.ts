import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import assert from "node:assert/strict";
import test from "node:test";
import {
  DEVELOPMENT_ROLE_STORAGE_KEY,
  DEVELOPMENT_ROLES,
  DEVELOPMENT_ENVIRONMENTS,
  parseDevelopmentEnvironment,
  parseDevelopmentRole,
  persistDevelopmentRole,
  persistDevelopmentEnvironment,
  readDevelopmentEnvironment,
  previewLoginRole,
  readDevelopmentRole,
  resolveRoleSelectionNext,
} from "./role-workbench.js";

test("only roles from the existing authorization catalog are selectable", () => {
  assert.deepEqual(DEVELOPMENT_ROLES, ["viewer", "planner", "project_admin"]);
  for (const role of DEVELOPMENT_ROLES) assert.equal(parseDevelopmentRole(role), role);
  assert.deepEqual(DEVELOPMENT_ENVIRONMENTS, ["engineering", "enterprise"]);
  for (const environment of DEVELOPMENT_ENVIRONMENTS) assert.equal(parseDevelopmentEnvironment(environment), environment);
  assert.equal(parseDevelopmentEnvironment("production"), null);
  assert.equal(previewLoginRole("viewer"), "viewer");
  assert.equal(previewLoginRole("planner"), "planner");
  assert.equal(previewLoginRole("project_admin"), "admin");
  for (const role of ["admin", "manager", "reviewer", "superuser", "", null, 3]) assert.equal(parseDevelopmentRole(role), null);
});

test("role-selection next path is same-origin and restricted to the personal workbench", () => {
  assert.equal(resolveRoleSelectionNext(null), "/workbench");
  assert.equal(resolveRoleSelectio¶»§q«^