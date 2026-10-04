import assert from "node:assert/strict";
import test from "node:test";
import { getWorkspaceShellLabels } from "./shell-labels.js";

test("workspace shell labels preserve English and Persian parity", () => {
  const en = getWorkspaceShellLabels("en");
  const fa = getWorkspaceShellLabels("fa");

  assert.equal(en.status, "Web shell · Authenticated workspace");
  assert.equal(fa.status, "پوسته وب · محیط کار احراز هویت‌شده");
  assert.equal(en.switchToPersian, "Switch to Persian");
  assert.equal(fa.switchToEnglish, "تغییر به انگلیسی");
});
