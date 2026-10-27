import assert from "node:assert/strict";
import test from "node:test";
import { getBootstrapErrorCopy, getBootstrapLabels } from "./bootstrap-labels.js";

test("bootstrap labels preserve English and Persian project-flow parity", () => {
  const en = getBootstrapLabels("en");
  const fa = getBootstrapLabels("fa");

  assert.equal(en.createProject, "Create project");
  assert.equal(en.projectName, "Project name");
  assert.equal(fa.createProject, "ایجاد پروژه");
  assert.equal(fa.projectName, "نام پروژه");
  assert.equal(fa.createAndOpen, "ایجاد و باز کردن");
  assert.notEqual(en.selectProject, fa.selectProject);
  assert.notEqual(en.createFirstProject, fa.createFirstProject);
  assert.notEqual(en.noProjects, fa.noProjects);
  assert.notEqual(en.validationNameLength, fa.validationNameLength);
});

test("bootstrap errors are localized and never expose a raw message key", () => {
  const session = getBootstrapErrorCopy("fa", {
    code: "SESSION_REQUIRED",
    message_key: "error.session.required",
  });
  assert.match(session.message, /نشست/);
  assert.equal(session.title, "محیط کار باز نشد");
  assert.equal(session.reference, "SESSION_REQUIRED");

  const unknown = getBootstrapErrorCopy("fa", {
    code: "SOMETHING_NEW",
    message_key: "error.some.server.phrase",
  });
  assert.equal(unknown.message, getBootstrapLabels("fa").errorGeneric);
  assert.doesNotMatch(unknown.message, /message_key|error\.some/);

  const englishUnknown = getBootstrapErrorCopy("en", {
    code: "SOMETHING_NEW",
    message_key: "error.some.server.phrase",
  });
  assert.equal(englishUnknown.message, getBootstrapLabels("en").errorGeneric);
  assert.doesNotMatch(englishUnknown.message, /error\.some/);

  const network = getBootstrapErrorCopy("en", {
    code: "NETWORK_ERROR",
    message_key: "error.network",
  });
  assert.match(network.message, /connection/i);
});
