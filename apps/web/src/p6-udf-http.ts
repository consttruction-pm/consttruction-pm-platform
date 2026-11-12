import type { P6FieldDataType } from "./p6-field-layout-foundation.js";
import type { P6UdfEditorMetadata } from "./p6-field-editor.js";

export type P6UdfHttpResponse = {
  registry_version: string;
  udfs: readonly P6UdfEditorMetadata[];
};

export type P6ActivityUdfValue = {
  udf_id: string;
  subject_area: string;
  display_name: string;
  data_type: P6FieldDataType;
  writable: boolean;
  nullable: boolean;
  unit: string | null;
  allowed_values: readonly string[] | null;
  value: unknown;
};

export type P6UdfValueListResponse = {
  object_type: string;
  object_id: string;
  values: readonly P6ActivityUdfValue[];
};

export type P6UdfFetch = (
  input: string,
  init?: {
    method?: string;
    credentials?: "include";
    headers?: Record<string, string>;
    body?: string;
  },
) => Promise<{
  ok: boolean;
  status: number;
  json(): Promise<unknown>;
}>;

const P6_FIELD_DATA_TYPES = new Set<P6FieldDataType>([
  "string", "date", "datetime", "duration", "decimal", "percentage",
  "boolean", "enum", "integer", "double", "cost", "unit",
  "object-id", "object-id-array", "string-array", "complex", "spread",
]);

export async function fetchP6ActivityUdfs(
  projectId: string,
  registryVersion: string,
  fetchImpl: P6UdfFetch = globalThis.fetch,
): Promise<P6UdfHttpResponse> {
  const url = `/api/projects/${encodeURIComponent(projectId)}/p6/udfs/${encodeURIComponent(registryVersion)}`;
  const response = await fetchImpl(url, { credentials: "include" });
  if (!response.ok) {
    throw new Error(`P6_UDF_HTTP_${response.status}`);
  }

  const payload = await response.json();
  if (!isP6UdfHttpResponse(payload) || payload.registry_version !== registryVersion) {
    throw new Error("P6_UDF_RESPONSE_INVALID");
  }
  return payload;
}

export async function fetchP6ActivityUdfValues(
  projectId: string,
  registryVersion: string,
  objectType: string,
  objectId: string,
  fetchImpl: P6UdfFetch = globalThis.fetch,
): Promise<P6UdfValueListResponse> {
  const url = `/api/projects/${encodeURIComponent(projectId)}/p6/udf-values/${encodeURIComponent(registryVersion)}/${encodeURIComponent(objectType)}/${encodeURIComponent(objectId)}`;
  const response = await fetchImpl(url, { credentials: "include" });
  if (!response.ok) {
    throw new Error(await responseErrorCode(response, `P6_UDF_VALUE_HTTP_${response.status}`));
  }
  const payload = await response.json();
  if (!isP6UdfValueListResponse(payload)) {
    throw new Error("P6_UDF_VALUE_RESPONSE_INVALID");
  }
  return payload;
}

export async function saveP6ActivityUdfValue(
  projectId: string,
  registryVersion: string,
  objectType: string,
  objectId: string,
  udfId: string,
  value: unknown,
  fetchImpl: P6UdfFetch = globalThis.fetch,
): Promise<P6ActivityUdfValue> {
  const url = `/api/projects/${encodeURIComponent(projectId)}/p6/udf-values/${encodeURIComponent(registryVersion)}/${encodeURIComponent(objectType)}/${encodeURIComponent(objectId)}/${encodeURIComponent(udfId)}`;
  const response = await fetchImpl(url, {
    method: "PUT",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ value }),
  });
  if (!response.ok) {
    throw new Error(await responseErrorCode(response, `P6_UDF_VALUE_HTTP_${response.status}`));
  }
  const payload = await response.json();
  if (!isP6ActivityUdfValue(payload)) {
    throw new Error("P6_UDF_VALUE_RESPONSE_INVALID");
  }
  return payload;
}

async function responseErrorCode(
  response: { json(): Promise<unknown> },
  fallback: string,
): Promise<string> {
  try {
    const payload = await response.json();
    if (payload && typeof payload === "object") {
      const code = (payload as Record<string, unknown>).code;
      if (typeof code === "string" && code) return code;
    }
  } catch {
    // A non-JSON error body still keeps the HTTP status in the message.
  }
  return fallback;
}

function isP6UdfHttpResponse(value: unknown): value is P6UdfHttpResponse {
  if (!value || typeof value !== "object") return false;
  const record = value as Record<string, unknown>;
  if (typeof record.registry_version !== "string" || !Array.isArray(record.udfs)) return false;

  return record.udfs.every((item) => {
    if (!item || typeof item !== "object") return false;
    const udf = item as Record<string, unknown>;
    const dataType = udf.data_type;
    const allowedValues = udf.allowed_values;
    return typeof udf.udf_id === "string"
      && typeof udf.subject_area === "string"
      && typeof udf.display_name === "string"
      && typeof dataType === "string"
      && P6_FIELD_DATA_TYPES.has(dataType as P6FieldDataType)
      && typeof udf.writable === "boolean"
      && typeof udf.nullable === "boolean"
      && (udf.unit === null || typeof udf.unit === "string")
      && (allowedValues === null
        || (Array.isArray(allowedValues) && allowedValues.every((item) => typeof item === "string")));
  });
}

function isP6UdfValueListResponse(value: unknown): value is P6UdfValueListResponse {
  if (!value || typeof value !== "object") return false;
  const record = value as Record<string, unknown>;
  return typeof record.object_type === "string"
    && typeof record.object_id === "string"
    && Array.isArray(record.values)
    && record.values.every(isP6ActivityUdfValue);
}

function isP6ActivityUdfValue(value: unknown): value is P6ActivityUdfValue {
  if (!value || typeof value !== "object") return false;
  const item = value as Record<string, unknown>;
  const dataType = item.data_type;
  const allowedValues = item.allowed_values;
  return typeof item.udf_id === "string"
    && typeof item.subject_area === "string"
    && typeof item.display_name === "string"
    && typeof dataType === "string"
    && P6_FIELD_DATA_TYPES.has(dataType as P6FieldDataType)
    && typeof item.writable === "boolean"
    && typeof item.nullable === "boolean"
    && (item.unit === null || typeof item.unit === "string")
    && (allowedValues === null
      || (Array.isArray(allowedValues) && allowedValues.every((entry) => typeof entry === "string")))
    && "value" in item;
}
