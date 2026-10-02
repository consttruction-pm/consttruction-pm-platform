import type {
  FormulaAuthoritativeResult,
  FormulaEditorModel,
  P6FormulaAuthority,
} from "./p6-field-layout-foundation.js";
import { applyFormulaAuthority } from "./p6-field-layout-foundation.js";

export type P6FormulaEditorState = FormulaEditorModel & {
  validating: boolean;
};

export type P6FormulaEditorModel = {
  getState(): P6FormulaEditorState;
  setExpression(expression: string): P6FormulaEditorState;
  validate(): Promise<P6FormulaEditorState>;
  applyAuthoritativeResult(result: FormulaAuthoritativeResult): P6FormulaEditorState;
};

export function createP6FormulaEditor(
  fieldId: string,
  authority: P6FormulaAuthority,
  expression = "",
): P6FormulaEditorModel {
  let model: FormulaEditorModel = {
    field_id: fieldId,
    expression,
    authoritative: null,
  };
  let validating = false;

  const state = (): P6FormulaEditorState => ({
    ...model,
    validating,
    authoritative: model.authoritative
      ? {
          validation: { ...model.authoritative.validation },
          dependencies: { field_ids: [...model.authoritative.dependencies.field_ids] },
          result_type: { ...model.authoritative.result_type },
        }
      : null,
  });

  return {
    getState() {
      return state();
    },

    setExpression(nextExpression) {
      model = { ...model, expression: nextExpression, authoritative: null };
      return state();
    },

    async validate() {
      validating = true;
      const expressionAtRequest = model.expression;
      try {
        const result = await authority.validate(expressionAtRequest, model.field_id);
        if (model.expression === expressionAtRequest) {
          model = applyFormulaAuthority(model, result);
        }
      } finally {
        validating = false;
      }
      return state();
    },

    applyAuthoritativeResult(result) {
      model = applyFormulaAuthority(model, result);
      return state();
    },
  };
}
