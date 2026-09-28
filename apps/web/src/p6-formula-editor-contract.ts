import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";

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

export type FormulaValidationRequest = Readonly<{
  formula_id: string | null;
  version: string | null;
  expression: string;
  subject_area: string;
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

export async function validateFormulaAuthoritatively(
  transport: ApiTransport,
  endpoint: string,
  context: ProjectContext,
  request: FormulaValidationRequest,
): Promise<ApiResult<FormulaValidationResult>> {
  const result = await transport.post<FormulaValidationRequest, unknown>(
    endpoint,
    request,
    context,
  );
  if (!result.ok) return result;

  if (!isAuthoritativeValidationResult(result.data)) {
    return {
      ok: false,
      error: {
        code: "NON_AUTHORITATIVE_FORMULA_RESULT",
        retryable: false,
        message_key: "formula.validation.nonAuthoritative",
        available_actions: ["retry"],
      },
    };
  }

  return { ok: true, data: freezeValidationResult(result.data) };
}

export function applyAuthoritativeValidation(
  state: FormulaEditorState,
  result: FormulaValidationResult,
): FormulaEditorState {
  if (result.authoritative !== true) throw new Error("NON_AUTHORITATIVE_FORMULA_RESULT");
  return Object.freeze({
    ...state,
    declared_result_type: result.result_type,
    validation: freezeValidationResult(result),
  });
}

export function canSubmitFormula(state: FormulaEditorState): boolean {
  return state.expression.trim().length > 0 && state.validation?.status === "valid";
}

function isAuthoritativeValidationResult(value: unknown): value is FormulaValidationResult {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return false;
  const record = value as Record<string, unknown>;
  if (record.authoritative !== true) return false;
  if (record.status !== "valid" && record.status !== "invalid" && record.status !== "pending") return false;
  if (record.message_key !== null && typeof record.message_key !== "string") return false;
  if (record.result_type !== null && typeof record.result_type !== "string") return false;
  if (record.result_unit !== null && typeof record.result_unit !== "string") return false;
  if (!Array.isArray(record.dependencies)) return false;
  return record.dependencies.every((dependency) => {
    if (typeof dependency !== "object" || dependency === null || Array.isArray(dependency)) return false;
    const item = dependency as Record<string, unknown>;
    return typeof item.field_id === "string"
      && (item.dependency_type === "field" || item.dependency_type === "formula")
      && typeof item.subject_area === "string";
  });
}

function freezeValidationResult(result: FormulaValidationResult): FormulaValidationResult {
  return Object.freeze({
    ...result,
    dependencies: Object.freeze(result.dependencies.map((dependency) => Object.freeze({ ...dependency }))),
  });
}
