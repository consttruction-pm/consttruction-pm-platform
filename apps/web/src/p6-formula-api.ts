import type { ApiTransport, ProjectContext } from "./client.js";
import {
  P6_FIELD_REGISTRY_VERSION,
  validateFormulaAuthoritativeResult,
} from "./p6-field-layout-foundation.js";
import type {
  FormulaAuthoritativeResult,
  P6FormulaAuthority,
} from "./p6-field-layout-foundation.js";

type FormulaValidationResponse = FormulaAuthoritativeResult & {
  contract_version?: string;
};

/**
 * Authoritative formula validation client.
 *
 * The Shared Core API is the only parser/type/dependency authority. This
 * client forwards the expression and context field and validates the response
 * shape; it never infers a result type or dependency locally.
 */
export function createP6FormulaAuthority(
  transport: ApiTransport,
  context: ProjectContext,
  registryVersion: string = P6_FIELD_REGISTRY_VERSION,
): P6FormulaAuthority {
  const path = `/api/projects/${encodeURIComponent(context.project_id)}/p6/formulas/${encodeURIComponent(registryVersion)}`;

  return {
    async validate(expression, contextFieldId) {
      const request: { expression: string; context_field_id?: string } = {
        expression,
      };
      if (contextFieldId) request.context_field_id = contextFieldId;
      const result = await transport.post<
        typeof request,
        FormulaValidationResponse
      >(path, request, context);
      if (!result.ok) {
        throw new Error(result.error.code || "P6_FORMULA_VALIDATION_FAILED");
      }
      return validateFormulaAuthoritativeResult({
        validation: result.data.validation,
        dependencies: result.data.dependencies,
        result_type: result.data.result_type,
      });
    },
  };
}
