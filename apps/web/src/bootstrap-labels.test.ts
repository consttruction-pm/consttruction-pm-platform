import assert from "node:assert/strict";
import test from "node:test";
import { getBootstrapLabels } from "./bootstrap-labels.js";

test("bootstrap labels preserve English and Persian project-flow parity", () => {
  const en = getBootstrapLabels("en");
  const fa = getBootstrapLabels("fa");

  assert.equal(en.createProject, "Create project");
  assert.equal(en.projectName, "Project name");
  assert.equal(fa.createProject, "ایجاد پروژه");
  assert.equal(fa.projectName, "نام پروژه");
  assert.equal(fa.createAndOpen, "ایجاد و باز کردن");
  assert.notEqual(en.selectProject, fa.selectProject);
});
