export const P6_FORMULA_EDITOR_CONTRACT_VERSION = "p6-formula-editor-client.v1" as const;

export type FormulaValidationStatus = "valid" | "invalid" | "pending";

export type FormulaDependencyResult = Readonly<{
  field_id: string;
  dependency_type: "field" | "formula";
  subject_area: string;
}>;

export type FormulaValidationResult = Readonly<{
  status: FormulaValidationStatus;
  message_key: string | null;
  result_type: string | null;
  result_unit: string | null;
  dependencies: readonly FormulaDependencyResult[];
  authoritative: true;
}>;

export type FormulaEditorState = Readonly<{
  contract_version: typeof P6_FORMULA_EDITOR_CONTRACT_VERSION;
  formula_id: string | null;
  version: string | null;
  expression: string;
  declared_result_type: string | null;
  validation: FormulaValidationResult | null;
}>;

export function createFormulaEditorState(expression = ""): FormulaEditorState {
  return Object.freeze({
    contract_version: P6_FORMULA_EDITOR_CONTRACT_VERSION,
    formula_id: null,
    version: null,
    expression,
    declared_result_type: null,
    validation: null,
  });
}

export function setFormulaExpression(state: FormulaEditorState, expression: string): FormulaEditorState {
  return Object.freeze({ ...state, expression, validation: null });
}

export function applyAuthoritativeValidation(
  state: FormulaEditorState,
  result: FormulaValidationResult,
): FormulaEditorState {
  if (result.authoritative !== true) throw new Error("NON_AUTHORITATIVE_FORMULA_RESULT");
  return Object.freeze({
    ...state,
    declared_result_type: result.result_type,
    validation: Object.freeze({
      ...result,
      dependencies: Object.freeze([...result.dependencies]),
    }),
  });
}

export function canSubmitFormula(state: FormulaEditorState): boolean {
  return state.expression.trim().length > 0 && state.validation?.status === "valid";
}
