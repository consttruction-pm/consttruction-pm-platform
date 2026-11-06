import type { ApiTransport, ProjectContext } from "./client.js";
import {
  P6_FIELD_REGISTRY_VERSION,
  validateFormulaAuthoritativeResult,
} from "./p6-field-layout-foundation.js";
import type {
  FormulaAuthoritativeResult,
  P6FieldDataType,
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

export const P6_FORMULA_COLUMN_API_VERSION = "p6-formula-column-api.v1" as const;

export type P6FormulaColumn = {
  formula_id: string;
  version: string;
  title: string;
  expression: string;
  result_type: "text" | "number" | "boolean" | "date" | "datetime";
  data_type: P6FieldDataType;
  result_unit: string | null;
  dependencies: readonly string[];
};

export type P6FormulaColumnRecord = {
  contract_version: typeof P6_FORMULA_COLUMN_API_VERSION;
  kind: "formula_column";
  scope: {
    tenant_id: string;
    project_id: string;
    project_revision: number;
  };
  formula: P6FormulaColumn;
};

export type P6FormulaColumnList = {
  contract_version: typeof P6_FORMULA_COLUMN_API_VERSION;
  kind: "formula_column_list";
  scope: {
    tenant_id: string;
    project_id: string;
    project_revision: number;
  };
  formula_columns: readonly P6FormulaColumnRecord[];
};

export type P6FormulaColumnCreateRequest = {
  formula_id: string;
  title: string;
  expression: string;
};

function assertFormulaColumnRecord(value: unknown): P6FormulaColumnRecord {
  if (!value || typeof value !== "object") throw new Error("INVALID_P6_FORMULA_COLUMN_RESPONSE");
  const record = value as Partial<P6FormulaColumnRecord>;
  if (record.contract_version !== P6_FORMULA_COLUMN_API_VERSION || record.kind !== "formula_column") {
    throw new Error("INVALID_P6_FORMULA_COLUMN_RESPONSE");
  }
  const formula = record.formula;
  if (!formula || typeof formula !== "object") throw new Error("INVALID_P6_FORMULA_COLUMN_RESPONSE");
  if (typeof formula.formula_id !== "string" || !formula.formula_id.startsWith("formula.")) {
    throw new Error("INVALID_P6_FORMULA_COLUMN_ID");
  }
  if (typeof formula.title !== "string" || !formula.title.trim()) {
    throw new Error("INVALID_P6_FORMULA_COLUMN_TITLE");
  }
  if (typeof formula.expression !== "string" || !formula.expression.trim()) {
    throw new Error("INVALID_P6_FORMULA_COLUMN_EXPRESSION");
  }
  if (!Array.isArray(formula.dependencies)) throw new Error("INVALID_P6_FORMULA_COLUMN_DEPENDENCIES");
  return record as P6FormulaColumnRecord;
}

/**
 * Persisted formula-column client.
 *
 * The server owns parsing, typing and evaluation. The client submits a title,
 * an id and an expression, then displays only the value returned by the
 * workspace read; it never evaluates the expression in the browser.
 */
export function createP6FormulaColumnClient(
  transport: ApiTransport,
  context: ProjectContext,
) {
  const path = `/api/projects/${encodeURIComponent(context.project_id)}/p6/formula-columns`;

  return {
    async list(): Promise<readonly P6FormulaColumnRecord[]> {
      const result = await transport.get<P6FormulaColumnList>(path, context);
      if (!result.ok) throw new Error(result.error.code || "P6_FORMULA_COLUMN_LIST_FAILED");
      if (
        result.data.contract_version !== P6_FORMULA_COLUMN_API_VERSION ||
        result.data.kind !== "formula_column_list" ||
        !Array.isArray(result.data.formula_columns)
      ) {
        throw new Error("INVALID_P6_FORMULA_COLUMN_LIST_RESPONSE");
      }
      return result.data.formula_columns.map(assertFormulaColumnRecord);
    },
    async create(input: P6FormulaColumnCreateRequest): Promise<P6FormulaColumnRecord> {
      const result = await transport.post<P6FormulaColumnCreateRequest, P6FormulaColumnRecord>(
        path,
        input,
        context,
      );
      if (!result.ok) throw new Error(result.error.code || "P6_FORMULA_COLUMN_SAVE_FAILED");
      return assertFormulaColumnRecord(result.data);
    },
  };
}
