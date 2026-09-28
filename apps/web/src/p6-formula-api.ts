import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  validateFormulaAuthoritatively,
  type FormulaDependencyResult,
  type FormulaValidationResult,
} from "./p6-formula-editor-contract.js";

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

  return validateFormulaAuthoritatively(
    transport,
    "/api/v1/p6/formulas/validate",
    context,
    {
      formula_id: request.formula_id ?? null,
      version: null,
      expression: request.expression,
      subject_area: request.subject_area,
    },
  );
}

export function dependencyFieldIds(result: FormulaValidationResult): readonly string[] {
  return Object.freeze(
    result.dependencies
      .filter((dependency: FormulaDependencyResult) => dependency.dependency_type === "field")
      .map((dependency) => dependency.field_id),
  );
}
