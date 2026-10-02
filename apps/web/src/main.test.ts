import assert from "node:assert/strict";
import test from "node:test";

import { selectProjectId } from "./main.js";

test("project bootstrap selects the requested project only when it is available", () => {
  const projects = [{ project_id: "p1" }, { project_id: "p2" }];
  assert.equal(selectProjectId(projects, "p2"), "p2");
  assert.throws(() => selectProjectId(projects, "p3"), /PROJECT_NOT_AVAILABLE/);
});

test("project bootstrap auto-selects the only available project", () => {
  assert.equal(selectProjectId([{ project_id: "p1" }], null), "p1");
});

test("project bootstrap requires explicit selection when multiple projects exist", () => {
  assert.throws(
    () => selectProjectId([{ project_id: "p1" }, { project_id: "p2" }], null),
    /PROJECT_SELECTION_REQUIRED/,
  );
});

test("project bootstrap rejects an empty project list", () => {
  assert.throws(() => selectProjectId([], null), /NO_PROJECTS_AVAILABLE/);
});
