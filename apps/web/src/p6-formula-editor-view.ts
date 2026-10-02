import type { P6FormulaEditorState } from "./p6-formula-editor.js";

export type P6FormulaEditorPresentation = {
  expression: string;
  validating: boolean;
  validation: NonNullable<P6FormulaEditorState["authoritative"]>["validation"] | null;
  dependencyFieldIds: readonly string[];
  resultDataType: NonNullable<P6FormulaEditorState["authoritative"]>["result_type"]["data_type"] | null;
};

export function getP6FormulaEditorPresentation(
  state: P6FormulaEditorState,
): P6FormulaEditorPresentation {
  const authoritative = state.authoritative;
  return {
    expression: state.expression,
    validating: state.validating,
    validation: authoritative ? { ...authoritative.validation } : null,
    dependencyFieldIds: authoritative ? [...authoritative.dependencies.field_ids] : [],
    resultDataType: authoritative?.result_type.data_type ?? null,
  };
}
