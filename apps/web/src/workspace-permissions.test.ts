import assert from "node:assert/strict";
import test from "node:test";
import {
  PROJECT_ADMIN_ROLES,
  PROJECT_ROLE,
  PROJECT_WRITE_ROLES,
  canAdministerProject,
  canWriteProject,
  hasAnyRole,
} from "./workspace-permissions.js";

test("project write requires a server-issued planner or project administrator role", () => {
  assert.deepEqual(PROJECT_WRITE_ROLES, ["planner", "project_admin"]);
  assert.equal(canWriteProject([]), false);
  assert.equal(canWriteProject([PROJECT_ROLE.viewer]), false);
  assert.equal(canWriteProject([PROJECT_ROLE.planner]), true);
  assert.equal(canWriteProject([PROJECT_ROLE.projectAdmin]), true);
  // The platform owner role is an administrator but not a project writer on
  // its own: project membership still decides writes.
  assert.equal(canWriteProject([PROJECT_ROLE.globalAdmin]), false);
});

test("administration recognizes the project administrator and the platform owner", () => {
  assert.deepEqual(PROJECT_ADMIN_ROLES, ["project_admin", "global_admin"]);
  assert.equal(canAdministerProject([]), false);
  assert.equal(canAdministerProject([PROJECT_ROLE.planner]), false);
  assert.equal(canAdministerProject([PROJECT_ROLE.viewer]), false);
  assert.equal(canAdministerProject([PROJECT_ROLE.projectAdmin]), true);
  assert.equal(canAdministerProject([PROJECT_ROLE.globalAdmin]), true);
  assert.equal(canAdministerProject([PROJECT_ROLE.planner, PROJECT_ROLE.projectAdmin]), true);
});

test("role matching is exact and never accepts a loose substring", () => {
  assert.equal(hasAnyRole(["project_admin_reader"], PROJECT_ADMIN_ROLES), false);
  assert.equal(hasAnyRole(["planners"], PROJECT_WRITE_ROLES), false);
  assert.equal(hasAnyRole([], PROJECT_WRITE_ROLES), false);
});
