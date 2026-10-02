import assert from "node:assert/strict";
import test from "node:test";

import { getProjectSelectionOptions, selectProjectId } from "./project-bootstrap.js";

test("project bootstrap selects the requested project only when it is available", () => {
  const projects = [{ project_id: "p1" }, { project_id: "p2" }];
  assert.equal(selectProjectId(projects, "p2"), "p2");
  assert.throws(() => selectProjectId(projects, "p3"), /PROJECT_NOT_AVAILABLE/);
});

test("project bootstrap exposes stable project selection options", () => {
  assert.deepEqual(
    getProjectSelectionOptions([
      { project_id: "p1", name: "  Project One  " },
      { project_id: "p2", name: " " },
    ]),
    [
      { project_id: "p1", label: "Project One" },
      { project_id: "p2", label: "p2" },
    ],
  );
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
