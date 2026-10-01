import test from "node:test";
import assert from "node:assert/strict";
import { createP6FormulaEditor } from "./p6-formula-editor.js";
import type {
  FormulaAuthoritativeResult,
  P6FormulaAuthority,
} from "./p6-field-layout-foundation.js";

const validResult: FormulaAuthoritativeResult = {
  validation: {
    valid: true,
    error_code: null,
    message_key: null,
  },
  dependencies: {
    field_ids: ["activity-duration", "activity-units"],
  },
  result_type: {
    data_type: "double",
  },
};

const authority: P6FormulaAuthority = {
  async validate(expression, contextFieldId) {
    assert.equal(expression, "Original Duration * Units");
    assert.equal(contextFieldId, "activity-cost");
    return validResult;
  },
};

test("keeps expression state local and consumes authoritative validation results", async () => {
  const editor = createP6FormulaEditor("activity-cost", authority);

  assert.equal(editor.getState().authoritative, null);

  editor.setExpression("Original Duration * Units");
  assert.equal(editor.getState().expression, "Original Duration * Units");
  assert.equal(editor.getState().validating, false);

  const state = await editor.validate();

  assert.equal(state.authoritative?.validation.valid, true);
  assert.deepEqual(state.authoritative?.dependencies.field_ids, [
    "activity-duration",
    "activity-units",
  ]);
  assert.equal(state.authoritative?.result_type.data_type, "double");
  assert.equal(state.validating, false);
});

test("clears stale authority when expression changes", async () => {
  const editor = createP6FormulaEditor("activity-cost", authority);

  editor.setExpression("Original Duration * Units");
  await editor.validate();
  assert.notEqual(editor.getState().authoritative, null);

  editor.setExpression("Changed");
  assert.equal(editor.getState().authoritative, null);
});

test("does not apply a stale validation result to a newer expression", async () => {
  let resolveValidation: ((result: FormulaAuthoritativeResult) => void) | undefined;
  const delayedAuthority: P6FormulaAuthority = {
    validate() {
      return new Promise<FormulaAuthoritativeResult>((resolve) => {
        resolveValidation = resolve;
      });
    },
  };

  const editor = createP6FormulaEditor("activity-cost", delayedAuthority);
  editor.setExpression("Old expression");
  const pending = editor.validate();

  editor.setExpression("New expression");
  resolveValidation?.(validResult);
  await pending;

  assert.equal(editor.getState().expression, "New expression");
  assert.equal(editor.getState().authoritative, null);
  assert.equal(editor.getState().validating, false);
});



test("keeps validating state owned by the newest validation request", async () => {
  const resolvers: Array<(result: FormulaAuthoritativeResult) => void> = [];
  const concurrentAuthority: P6FormulaAuthority = {
    validate() {
      return new Promise<FormulaAuthoritativeResult>((resolve) => {
        resolvers.push(resolve);
      });
    },
  };

  const editor = createP6FormulaEditor("activity-cost", concurrentAuthority);
  editor.setExpression("First");
  const first = editor.validate();
  editor.setExpression("Second");
  const second = editor.validate();

  assert.equal(editor.getState().validating, true);
  resolvers[0]?.(validResult);
  await first;
  assert.equal(editor.getState().validating, true);
  assert.equal(editor.getState().authoritative, null);

  resolvers[1]?.(validResult);
  await second;
  assert.equal(editor.getState().validating, false);
  assert.equal(editor.getState().expression, "Second");
  assert.equal(editor.getState().authoritative?.validation.valid, true);
});

test("does not expose formula evaluation when authoritative validation is absent", async () => {
  const editor = createP6FormulaEditor("activity-cost", {
    async validate() {
      return {
        validation: { valid: false, error_code: "INVALID_FORMULA", message_key: "invalid" },
        dependencies: { field_ids: [] },
        result_type: { data_type: "double" },
      };
    },
  });
  editor.setExpression("Original Duration * Units");
  const state = await editor.validate();
  assert.equal(state.authoritative?.validation.valid, false);
  assert.equal(state.authoritative?.result_type.data_type, "double");
  assert.equal("evaluate" in editor, false);
});
