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
export type InterchangeImportAudit = {
  status: "recorded" | "not_configured";
  target_application_status: "PARSED_NOT_APPLIED" | "not_configured";
  batch_id: string | null;
  source_sha256?: string;
  source_byte_count?: number;
  row_count?: number;
  mapping_count?: number;
  warning_count?: number;
};
export type InterchangeImportResultWithAudit = InterchangeImportResult & {
  import_audit?: InterchangeImportAudit;
};
export type InterchangeImportBatchSummary = {
  batch_id: string;
  format: string;
  source_sha256: string;
  source_byte_count: number;
  row_count: number;
  mapping_count: number;
  warning_count: number;
  imported_by: string;
  imported_at: string;
  target_application_status: string;
};
export type InterchangeImportBatchList = {
  contract_version: string;
  scope: { tenant_id: string; project_id: string; project_revision: number };
  status: "available" | "not_configured";
  batches: readonly InterchangeImportBatchSummary[];
};
export type InterchangeImportBatchDetail = {
  contract_version: string;
  batch: InterchangeImportBatchSummary & {
    tenant_id: string;
    project_id: string;
    project_revision: number;
    request_key: string | null;
    mapping_snapshot: readonly Readonly<Record<string, unknown>>[];
    row_summaries: readonly Readonly<Record<string, unknown>>[];
  };
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
): InterchangeImportResultWithAudit {
  const envelope = requireEnvelope(payload, context);
  if (!Array.isArray(envelope.rows)) invalid("INVALID_INTERCHANGE_ROWS");
  let importAudit: InterchangeImportAudit | undefined;
  if (envelope.import_audit !== undefined) {
    if (!isRecord(envelope.import_audit)) invalid("INVALID_INTERCHANGE_IMPORT_AUDIT");
    const audit = envelope.import_audit;
    if (
      (audit.status !== "recorded" && audit.status !== "not_configured") ||
      (audit.target_application_status !== "PARSED_NOT_APPLIED" && audit.target_application_status !== "not_configured") ||
      (audit.batch_id !== null && typeof audit.batch_id !== "string")
    ) {
      invalid("INVALID_INTERCHANGE_IMPORT_AUDIT");
    }
    for (const key of ["source_byte_count", "row_count", "mapping_count", "warning_count"] as const) {
      const numericValue = audit[key];
      if (numericValue !== undefined && (
        typeof numericValue !== "number" || !Number.isInteger(numericValue) || numericValue < 0
      )) {
        invalid("INVALID_INTERCHANGE_IMPORT_AUDIT");
      }
    }
    if (audit.source_sha256 !== undefined && (
      typeof audit.source_sha256 !== "string" || !/^[0-9a-f]{64}$/i.test(audit.source_sha256)
    )) {
      invalid("INVALID_INTERCHANGE_IMPORT_AUDIT");
    }
    importAudit = {
      status: audit.status,
      target_application_status: audit.target_application_status,
      batch_id: audit.batch_id,
      ...(typeof audit.source_sha256 === "string" ? { source_sha256: audit.source_sha256 } : {}),
      ...(typeof audit.source_byte_count === "number" ? { source_byte_count: audit.source_byte_count } : {}),
      ...(typeof audit.row_count === "number" ? { row_count: audit.row_count } : {}),
      ...(typeof audit.mapping_count === "number" ? { mapping_count: audit.mapping_count } : {}),
      ...(typeof audit.warning_count === "number" ? { warning_count: audit.warning_count } : {}),
    };
  }
  return {
    contract_version: P6_INTERCHANGE_API_VERSION,
    format: PROVIDER_XML_FORMAT,
    rows: envelope.rows.map(projectImportRow),
    ...(importAudit ? { import_audit: importAudit } : {}),
  };
}

export type P6InterchangeClient = {
  exportDocument(
    values: readonly Readonly<Record<string, unknown>>[],
    extensions?: readonly Readonly<Record<string, unknown>>[],
  ): Promise<InterchangeExportResult>;
  importDocument(document: string): Promise<InterchangeImportResultWithAudit>;
  listImportBatches(): Promise<InterchangeImportBatchList>;
  getImportBatch(batchId: string): Promise<InterchangeImportBatchDetail>;
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
      const response = await transport.postRaw<InterchangeImportResultWithAudit>(
        `${path}/import`,
        document,
        "application/xml; charset=utf-8",
        context,
        crypto.randomUUID(),
      );
      if (!response.ok) invalid(response.error.code || "INTERCHANGE_IMPORT_FAILED");
      return projectImport(response.data, context);
    },

    async listImportBatches() {
      const response = await transport.get<InterchangeImportBatchList>(
        `/api/projects/${encodeURIComponent(context.project_id)}/p6/interchange/imports`,
        context,
      );
      if (!response.ok) invalid(response.error.code || "INTERCHANGE_IMPORT_HISTORY_FAILED");
      if (
        response.data.contract_version !== P6_INTERCHANGE_API_VERSION ||
        !isRecord(response.data.scope) ||
        response.data.scope.tenant_id !== context.tenant_id ||
        response.data.scope.project_id !== context.project_id ||
        Number(response.data.scope.project_revision) !== context.revision ||
        !Array.isArray(response.data.batches) ||
        (response.data.status !== "available" && response.data.status !== "not_configured")
      ) {
        invalid("INVALID_INTERCHANGE_IMPORT_HISTORY");
      }
      return response.data;
    },

    async getImportBatch(batchId: string) {
      if (!batchId.trim()) invalid("INTERCHANGE_IMPORT_BATCH_ID_REQUIRED");
      const response = await transport.get<InterchangeImportBatchDetail>(
        `/api/projects/${encodeURIComponent(context.project_id)}/p6/interchange/imports/${encodeURIComponent(batchId)}`,
        context,
      );
      if (!response.ok) invalid(response.error.code || "INTERCHANGE_IMPORT_BATCH_DETAIL_FAILED");
      const batch = response.data.batch;
      if (
        response.data.contract_version !== P6_INTERCHANGE_API_VERSION ||
        !isRecord(batch) ||
        batch.tenant_id !== context.tenant_id ||
        batch.project_id !== context.project_id ||
        Number(batch.project_revision) < 0 ||
        typeof batch.source_sha256 !== "string" ||
        !/^[0-9a-f]{64}$/i.test(batch.source_sha256) ||
        !Array.isArray(batch.mapping_snapshot) ||
        !Array.isArray(batch.row_summaries)
      ) {
        invalid("INVALID_INTERCHANGE_IMPORT_BATCH_DETAIL");
      }
      return response.data;
    },
  };
}
