import type { P6FieldDataType } from "./p6-field-layout-foundation.js";
import type { P6UdfEditorMetadata } from "./p6-field-editor.js";

export type P6UdfHttpResponse = {
  registry_version: string;
  udfs: readonly P6UdfEditorMetadata[];
};

export type P6UdfFetch = (
  input: string,
  init?: { credentials?: "include" },
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
  if (!isP6UdfHttpResponse(payload)) {
    throw new Error("P6_UDF_RESPONSE_INVALID");
  }
  return payload;
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
