import type { ProjectContext } from "./client.js";

export const P6_INTERCHANGE_CONTRACT_VERSION = "p6-interchange-client.v1" as const;

export type P6InterchangeDataType =
  | "string"
  | "enum"
  | "integer"
  | "decimal"
  | "date"
  | "datetime"
  | "duration"
  | "boolean";

export type P6DurationPayload = Readonly<{
  value: string;
  unit: string;
}>;

export type P6InterchangeTypedValue =
  | Readonly<{ data_type: "string" | "enum"; value: string; unit: string | null; currency: string | null }>
  | Readonly<{ data_type: "integer"; value: number; unit: string | null; currency: string | null }>
  | Readonly<{ data_type: "decimal"; value: string; unit: string | null; currency: string | null }>
  | Readonly<{ data_type: "date" | "datetime"; value: string; unit: string | null; currency: string | null }>
  | Readonly<{ data_type: "duration"; value: P6DurationPayload; unit: string | null; currency: string | null }>
  | Readonly<{ data_type: "boolean"; value: boolean; unit: string | null; currency: string | null }>;

export type P6InterchangeEnvelope<T> = Readonly<{
  contract_version: typeof P6_INTERCHANGE_CONTRACT_VERSION;
  context: ProjectContext;
  value: T;
}>;

export function validateP6InterchangeTypedValue(value: unknown): value is P6InterchangeTypedValue {
  if (!isRecord(value) || typeof value.data_type !== "string") return false;
  if (!isNullableString(value.unit) || !isNullableString(value.currency)) return false;

  switch (value.data_type) {
    case "string":
    case "enum":
      return typeof value.value === "string";
    case "integer":
      return typeof value.value === "number" && Number.isSafeInteger(value.value);
    case "decimal":
      return typeof value.value === "string" && isFiniteDecimal(value.value);
    case "date":
      return typeof value.value === "string" && isIsoDate(value.value);
    case "datetime":
      return typeof value.value === "string" && isIsoDateTime(value.value);
    case "duration":
      return isRecord(value.value)
        && typeof value.value.value === "string"
        && isFiniteDecimal(value.value.value)
        && typeof value.value.unit === "string"
        && value.value.unit.trim().length > 0;
    case "boolean":
      return typeof value.value === "boolean";
    default:
      return false;
  }
}

export function assertP6InterchangeTypedValue(value: unknown): P6InterchangeTypedValue {
  if (!validateP6InterchangeTypedValue(value)) {
    throw new Error("INVALID_P6_INTERCHANGE_TYPED_VALUE");
  }
  return value;
}

export function validateP6InterchangeEnvelope<T>(
  value: unknown,
  validator: (payload: unknown) => payload is T,
): value is P6InterchangeEnvelope<T> {
  if (!isRecord(value) || value.contract_version !== P6_INTERCHANGE_CONTRACT_VERSION) return false;
  if (!isProjectContext(value.context) || !validator(value.value)) return false;
  return true;
}

function isProjectContext(value: unknown): value is ProjectContext {
  if (!isRecord(value)) return false;
  return typeof value.tenant_id === "string"
    && value.tenant_id.trim().length > 0
    && typeof value.project_id === "string"
    && value.project_id.trim().length > 0
    && typeof value.revision === "number"
    && Number.isSafeInteger(value.revision)
    && value.revision >= 0;
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isFiniteDecimal(value: string): boolean {
  if (!value.trim()) return false;
  return Number.isFinite(Number(value));
}

function isIsoDate(value: string): boolean {
  if (!/^\\d{4}-\\d{2}-\\d{2}$/.test(value)) return false;
  const parsed = new Date(value + "T00:00:00Z");
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

function isIsoDateTime(value: string): boolean {
  if (!value.includes("T") || Number.isNaN(Date.parse(value))) return false;
  return /(?:Z|[+-]\\d{2}:\\d{2})$/.test(value);
}

function isRecord(value: unknown): value is Record<string, any> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
