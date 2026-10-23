import assert from "node:assert/strict";
import test from "node:test";
import { getBootstrapErrorMessage, getBootstrapLabels } from "./bootstrap-labels.js";

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

test("bootstrap error messages are translated for common API and workspace failures", () => {
  assert.equal(
    getBootstrapErrorMessage("error.network", "en"),
    "Unable to connect to the server. Check your connection and try again.",
  );
  assert.equal(
    getBootstrapErrorMessage("error.network", "fa"),
    "اتصال به سرور برقرار نشد. اتصال اینترنت را بررسی و دوباره تلاش کنید.",
  );
  assert.equal(
    getBootstrapErrorMessage("error.workspace_read.invalid_payload", "fa"),
    "پاسخ سرویس محیط کار معتبر نیست. صفحه را بازخوانی و دوباره تلاش کنید.",
  );
});

test("bootstrap error messages never expose unknown machine keys to users", () => {
  const unknownKey = "INTERNAL_UNRECOGNIZED_ERROR_123";
  assert.equal(
    getBootstrapErrorMessage(unknownKey, "en"),
    getBootstrapErrorMessage("error.generic", "en"),
  );
  assert.equal(
    getBootstrapErrorMessage(unknownKey, "fa"),
    getBootstrapErrorMessage("error.generic", "fa"),
  );
  assert.notEqual(getBootstrapErrorMessage(unknownKey, "en"), unknownKey);
  assert.notEqual(getBootstrapErrorMessage(unknownKey, "fa"), unknownKey);
  assert.notEqual(
    getBootstrapErrorMessage(unknownKey, "en"),
    getBootstrapErrorMessage(unknownKey, "fa"),
  );
});
