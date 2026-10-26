import type { ApiTransport, ProjectContext } from "./client.js";

export const P6_INTERCHANGE_API_VERSION = "p6-interchange-api.v1";
export const PROVIDER_XML_FORMAT = "PRIMAVERA_XML";

export type InterchangeFormat = typeof PROVIDER_XML_FORMAT;

export type InterchangeExportDocument = {
  encoding: "utf-8" | "base64";
  data: string;
};

export type InterchangeExportResult = {
  contract_version: string;
  format: InterchangeFormat;
  document: InterchangeExportDocument;
};

export type InterchangeImportRow = {
  values: Readonly<Record<string, unknown>>;
  extensions: Readonly<Record<string, unknown>>;
  warnings: readonly string[];
};

export type InterchangeImportResult = {
  contract_version: string;
  format: InterchangeFormat;
  rows: readonly InterchangeImportRow[];
};

export class InterchangeClientError extends Error {
  constructor(readonly code: string) {
    super(code);
    this.name = "InterchangeClientError";
  }
}

function invalid(code: string): never {
  throw new InterchangeClientError(code);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requireScope(payload: Record<string, unknown>, context: ProjectContext): void {
  const scope = payload.scope;
  if (!isRecord(scope)) invalid("INVALID_INTERCHANGE_RESPONSE_SCOPE");
  if (
    scope.tenant_id !== context.tenant_id ||
    scope.project_id !== context.project_id ||
    Number(scope.project_revision) !== context.revision
  ) {
    invalid("INTERCHANGE_RESPONSE_SCOPE_MISMATCH");
  }
}

function requireEnvelope(
  payload: unknown,
  context: ProjectContext,
): Record<string, unknown> {
  if (!isRecord(payload)) invalid("INVALID_INTERCHANGE_RESPONSE");
  if (payload.contract_version !== P6_INTERCHANGE_API_VERSION) {
    invalid("UNSUPPORTED_INTERCHANGE_CONTRACT");
  }
  if (payload.format !== PROVIDER_XML_FORMAT) {
    invalid("UNSUPPORTED_INTERCHANGE_FORMAT");
  }
  requireScope(payload, context);
  return payload;
}

function projectExport(
  payload: unknown,
  context: ProjectContext,
): InterchangeExportResult {
  const envelope = requireEnvelope(payload, context);
  const document = envelope.document;
  if (!isRecord(document)) invalid("INVALID_INTERCHANGE_DOCUMENT");
  if (document.encoding !== "utf-8" && document.encoding !== "base64") {
    invalid("INVALID_INTERCHANGE_DOCUMENT_ENCODING");
  }
  if (typeof document.data !== "string" || document.data.length === 0) {
    invalid("INVALID_INTERCHANGE_DOCUMENT");
  }
  return {
    contract_version: P6_INTERCHANGE_API_VERSION,
    format: PROVIDER_XML_FORMAT,
    document: {
      encoding: document.encoding,
      data: document.data,
    },
  };
}

function projectImportRow(value: unknown): InterchangeImportRow {
  if (!isRecord(value)) invalid("INVALID_INTERCHANGE_ROW");
  if (!isRecord(value.values)) invalid("INVALID_INTERCHANGE_ROW_VALUES");
  if (!isRecord(value.extensions)) invalid("INVALID_INTERCHANGE_ROW_EXTENSIONS");
  if (
    !Array.isArray(value.warnings) ||
    value.warnings.some((warning) => typeof warning !== "string")
  ) {
    invalid("INVALID_INTERCHANGE_ROW_WARNINGS");
  }
  return {
    values: value.values,
    extensions: value.extensions,
    warnings: value.warnings as string[],
  };
}

function projectImport(
  payload: unknown,
  context: ProjectContext,
): InterchangeImportResult {
  const envelope = requireEnvelope(payload, context);
  if (!Array.isArray(envelope.rows)) invalid("INVALID_INTERCHANGE_ROWS");
  return {
    contract_version: P6_INTERCHANGE_API_VERSION,
    format: PROVIDER_XML_FORMAT,
    rows: envelope.rows.map(projectImportRow),
  };
}

export type P6InterchangeClient = {
  exportDocument(
    values: readonly Readonly<Record<string, unknown>>[],
    extensions?: readonly Readonly<Record<string, unknown>>[],
  ): Promise<InterchangeExportResult>;
  importDocument(document: string): Promise<InterchangeImportResult>;
};

export function createP6InterchangeClient(
  transport: ApiTransport,
  context: ProjectContext,
  format: InterchangeFormat = PROVIDER_XML_FORMAT,
): P6InterchangeClient {
  const path = `/api/projects/${encodeURIComponent(
    context.project_id,
  )}/p6/interchange/${encodeURIComponent(format)}`;

  return {
    async exportDocument(values, extensions) {
      if (values.length === 0) invalid("INTERCHANGE_EXPORT_EMPTY");
      if (extensions && extensions.length !== values.length) {
        invalid("INTERCHANGE_EXTENSION_ROW_COUNT_MISMATCH");
      }
      const request = {
        values,
        ...(extensions ? { extensions } : {}),
      };
      const response = await transport.post<
        typeof request,
        InterchangeExportResult
      >(`${path}/export`, request, context);
      if (!response.ok) invalid(response.error.code || "INTERCHANGE_EXPORT_FAILED");
      return projectExport(response.data, context);
    },

    async importDocument(document) {
      if (!document.trim()) invalid("INTERCHANGE_IMPORT_EMPTY");
      if (!transport.postRaw) {
        invalid("INTERCHANGE_RAW_HTTP_UNSUPPORTED");
      }
      const response = await transport.postRaw<InterchangeImportResult>(
        `${path}/import`,
        document,
        "application/xml; charset=utf-8",
        context,
      );
      if (!response.ok) invalid(response.error.code || "INTERCHANGE_IMPORT_FAILED");
      return projectImport(response.data, context);
    },
  };
}
