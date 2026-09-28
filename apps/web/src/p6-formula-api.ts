import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import type { FormulaDependencyResult, FormulaValidationResult } from "./p6-formula-editor-contract.js";

export type P6FormulaValidationRequest = Readonly<{
  formula_id?: string;
  expression: string;
  subject_area: string;
}>;

export type P6FormulaValidationResponse = FormulaValidationResult;

export async function validateP6Formula(
  transport: ApiTransport,
  context: ProjectContext,
  request: P6FormulaValidationRequest,
): Promise<ApiResult<P6FormulaValidationResponse>> {
  if (!request.expression.trim()) {
    throw new Error("FORMULA_REQUIRED");
  }
  if (!request.subject_area.trim()) {
    throw new Error("SUBJECT_AREA_REQUIRED");
  }
  return transport.post<P6FormulaValidationRequest, P6FormulaValidationResponse>(
    "/api/v1/p6/formulas/validate",
    request,
    context,
  );
}

export function dependencyFieldIds(result: FormulaValidationResult): readonly string[] {
  return Object.freeze(result.dependencies
    .filter((dependency: FormulaDependencyResult) => dependency.dependency_type === "field")
    .map((dependency) => dependency.field_id));
}
