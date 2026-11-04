import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import { createP6InterchangeClient } from "./p6-interchange-api.js";

const CONTEXT: ProjectContext = {
  tenant_id: "t1",
  project_id: "preview-rps-01",
  revision: 7,
};

type PostCall = {
  path: string;
  request: unknown;
  context: ProjectContext;
};

type RawCall = {
  path: string;
  body: string;
  contentType: string;
  context: ProjectContext;
  idempotencyKey?: string;
};
type GetCall = { path: string; context: ProjectContext };

function transportWith(
  result: ApiResult<unknown>,
  options: {
    calls?: PostCall[];
    rawCalls?: RawCall[];
    rawResult?: ApiResult<unknown>;
    getResult?: ApiResult<unknown>;
    getCalls?: GetCall[];
    withRaw?: boolean;
  } = {},
): ApiTransport {
  const transport: ApiTransport = {
    async get(path, context) {
      options.getCalls?.push({ path, context });
      return (options.getResult ?? result) as ApiResult<never>;
    },
    async post(path, request, context) {
      options.calls?.push({ path, request, context });
      return result as ApiResult<never>;
    },
  };
  if (options.withRaw) {
    transport.postRaw = async (path, body, contentType, context, idempotencyKey) => {
      options.rawCalls?.push({ path, body, contentType, context, idempotencyKey });
      return (options.rawResult ?? result) as ApiResult<never>;
    };
  }
  return transport;
}

function exportEnvelope(document: unknown = { encoding: "utf-8", data: "<root/>" }) {
  return {
    contract_version: "p6-interchange-api.v1",
    scope: {
      tenant_id: "t1",
      project_id: "preview-rps-01",
      project_revision: 7,
    },
    format: "PRIMAVERA_XML",
    document,
  };
}

function importEnvelope(rows: unknown[] = [], importAudit?: unknown) {
  return {
    contract_version: "p6-interchange-api.v1",
    scope: {
      tenant_id: "t1",
      project_id: "preview-rps-01",
      project_revision: 7,
    },
    format: "PRIMAVERA_XML",
    rows,
    ...(importAudit === undefined ? {} : { import_audit: importAudit }),
  };
}

test("export posts canonical values and extensions to the persisted mapping route", async () => {
  const calls: PostCall[] = [];
  const client = createP6InterchangeClient(
    transportWith({ ok: true, data: exportEnvelope() }, { calls }),
    CONTEXT,
  );

  const values = [{ "activity.id": "A130", "activity.name": "Earthworks" }];
  const extensions = [{ "p6.primavera.xml.object": "Activity" }];
  const result = await client.exportDocument(values, extensions);

  assert.equal(calls.length, 1);
  assert.equal(
    calls[0].path,
    "/api/projects/preview-rps-01/p6/interchange/PRIMAVERA_XML/export",
  );
  assert.deepEqual(calls[0].request, { values, extensions });
  assert.deepEqual(calls[0].context, CONTEXT);
  assert.equal(result.document.encoding, "utf-8");
  assert.equal(result.document.data, "<root/>");
});

test("import sends the provider document verbatim as XML and projects mapped rows", async () => {
  const rawCalls: RawCall[] = [];
  const client = createP6InterchangeClient(
    transportWith(
      { ok: true, data: importEnvelope() },
      {
        withRaw: true,
        rawCalls,
        rawResult: {
          ok: true,
          data: importEnvelope([
            {
              values: { "activity.id": "A130", "activity.name": "Earthworks" },
              extensions: { "p6.primavera.xml.object": "Activity" },
              warnings: [],
            },
          ]),
        },
      },
    ),
    CONTEXT,
  );

  const document = '<?xml version="1.0"?><APIBusinessObjects><Activity><Id>A130</Id></Activity></APIBusinessObjects>';
  const result = await client.importDocument(document);

  assert.equal(rawCalls.length, 1);
  assert.equal(
    rawCalls[0].path,
    "/api/projects/preview-rps-01/p6/interchange/PRIMAVERA_XML/import",
  );
  assert.equal(rawCalls[0].body, document);
  assert.equal(rawCalls[0].contentType, "application/xml; charset=utf-8");
  assert.deepEqual(rawCalls[0].context, CONTEXT);
  assert.equal(typeof rawCalls[0].idempotencyKey, "string");
  assert.equal(result.rows.length, 1);
  assert.equal(result.rows[0].values["activity.name"], "Earthworks");
  assert.deepEqual(result.rows[0].warnings, []);
});

test("empty exports and empty imports fail closed before contacting the server", async () => {
  const client = createP6InterchangeClient(
    transportWith({ ok: true, data: exportEnvelope() }),
    CONTEXT,
  );
  await assert.rejects(client.exportDocument([]), /INTERCHANGE_EXPORT_EMPTY/);
  await assert.rejects(client.importDocument("   "), /INTERCHANGE_IMPORT_EMPTY/);
});

test("extension row count must match exported values", async () => {
  const client = createP6InterchangeClient(
    transportWith({ ok: true, data: exportEnvelope() }),
    CONTEXT,
  );
  await assert.rejects(
    client.exportDocument(
      [{ "activity.id": "A100" }, { "activity.id": "A110" }],
      [{ "p6.primavera.xml.object": "Activity" }],
    ),
    /INTERCHANGE_EXTENSION_ROW_COUNT_MISMATCH/,
  );
});

test("a transport without raw posting reports an explicit unsupported state", async () => {
  const client = createP6InterchangeClient(
    transportWith({ ok: true, data: importEnvelope() }),
    CONTEXT,
  );
  await assert.rejects(
    client.importDocument("<APIBusinessObjects/>"),
    /INTERCHANGE_RAW_HTTP_UNSUPPORTED/,
  );
});

test("authorization denial is surfaced with the server error code", async () => {
  const client = createP6InterchangeClient(
    transportWith(
      {
        ok: false,
        error: {
          code: "authorization denied for permission=project:write",
          retryable: false,
          message_key: "error.authorization.denied",
          available_actions: [],
        },
      },
      { withRaw: true },
    ),
    CONTEXT,
  );
  await assert.rejects(client.importDocument("<APIBusinessObjects/>"), (error: Error) =>
    /authorization denied/.test(error.message),
  );
});

test("responses from another project, revision or contract are rejected", async () => {
  const wrongScope = exportEnvelope();
  wrongScope.scope = {
    tenant_id: "t1",
    project_id: "other-project",
    project_revision: 7,
  };
  await assert.rejects(
    createP6InterchangeClient(
      transportWith({ ok: true, data: wrongScope }),
      CONTEXT,
    ).exportDocument([{ "activity.id": "A100" }]),
    /INTERCHANGE_RESPONSE_SCOPE_MISMATCH/,
  );

  const wrongRevision = exportEnvelope();
  wrongRevision.scope = {
    tenant_id: "t1",
    project_id: "preview-rps-01",
    project_revision: 8,
  };
  await assert.rejects(
    createP6InterchangeClient(
      transportWith({ ok: true, data: wrongRevision }),
      CONTEXT,
    ).exportDocument([{ "activity.id": "A100" }]),
    /INTERCHANGE_RESPONSE_SCOPE_MISMATCH/,
  );

  const wrongContract = { ...exportEnvelope(), contract_version: "other.v9" };
  await assert.rejects(
    createP6InterchangeClient(
      transportWith({ ok: true, data: wrongContract }),
      CONTEXT,
    ).exportDocument([{ "activity.id": "A100" }]),
    /UNSUPPORTED_INTERCHANGE_CONTRACT/,
  );
});

test("malformed documents and rows are rejected instead of being rendered", async () => {
  const emptyDocument = exportEnvelope({ encoding: "utf-8", data: "" });
  await assert.rejects(
    createP6InterchangeClient(
      transportWith({ ok: true, data: emptyDocument }),
      CONTEXT,
    ).exportDocument([{ "activity.id": "A100" }]),
    /INVALID_INTERCHANGE_DOCUMENT/,
  );

  const badRow = importEnvelope([
    { values: "not-a-mapping", extensions: {}, warnings: [] },
  ]);
  await assert.rejects(
    createP6InterchangeClient(
      transportWith(
        { ok: true, data: importEnvelope() },
        { withRaw: true, rawResult: { ok: true, data: badRow } },
      ),
      CONTEXT,
    ).importDocument("<APIBusinessObjects/>"),
    /INVALID_INTERCHANGE_ROW_VALUES/,
  );

  const badWarnings = importEnvelope([
    { values: {}, extensions: {}, warnings: [1] },
  ]);
  await assert.rejects(
    createP6InterchangeClient(
      transportWith(
        { ok: true, data: importEnvelope() },
        { withRaw: true, rawResult: { ok: true, data: badWarnings } },
      ),
      CONTEXT,
    ).importDocument("<APIBusinessObjects/>"),
    /INVALID_INTERCHANGE_ROW_WARNINGS/,
  );
});


test("import response validates and preserves its durable audit receipt", async () => {
  const audit = {
    status: "recorded",
    target_application_status: "PARSED_NOT_APPLIED",
    batch_id: "batch-1",
    source_sha256: "a".repeat(64),
    source_byte_count: 200,
    row_count: 1,
    mapping_count: 3,
    warning_count: 1,
  };
  const client = createP6InterchangeClient(
    transportWith(
      { ok: true, data: importEnvelope() },
      { withRaw: true, rawResult: { ok: true, data: importEnvelope([], audit) } },
    ),
    CONTEXT,
  );
  const result = await client.importDocument("<root/>");
  assert.equal(result.import_audit?.status, "recorded");
  assert.equal(result.import_audit?.target_application_status, "PARSED_NOT_APPLIED");
  assert.equal(result.import_audit?.batch_id, "batch-1");
  assert.equal(result.import_audit?.source_sha256, "a".repeat(64));

  const invalid = { ...audit, source_sha256: "not-a-hash" };
  const invalidClient = createP6InterchangeClient(
    transportWith(
      { ok: true, data: importEnvelope() },
      { withRaw: true, rawResult: { ok: true, data: importEnvelope([], invalid) } },
    ),
    CONTEXT,
  );
  await assert.rejects(invalidClient.importDocument("<root/>"), /INVALID_INTERCHANGE_IMPORT_AUDIT/);
});

test("import history list and detail reads validate the active project scope", async () => {
  const calls: GetCall[] = [];
  const list = {
    contract_version: "p6-interchange-api.v1",
    scope: { tenant_id: "t1", project_id: "preview-rps-01", project_revision: 7 },
    status: "available",
    batches: [{
      batch_id: "batch-1",
      format: "XER_PROJECT",
      source_sha256: "a".repeat(64),
      source_byte_count: 200,
      row_count: 1,
      mapping_count: 2,
      warning_count: 1,
      imported_by: "user-1",
      imported_at: "2026-11-04T20:00:00+00:00",
      target_application_status: "PARSED_NOT_APPLIED",
    }],
  };
  const listClient = createP6InterchangeClient(
    transportWith({ ok: true, data: importEnvelope() }, {
      getCalls: calls,
      getResult: { ok: true, data: list },
    }),
    CONTEXT,
  );
  const history = await listClient.listImportBatches();
  assert.equal(history.batches[0].batch_id, "batch-1");
  assert.equal(calls[0].path, "/api/projects/preview-rps-01/p6/interchange/imports");

  const detail = {
    contract_version: "p6-interchange-api.v1",
    batch: {
      tenant_id: "t1",
      project_id: "preview-rps-01",
      project_revision: 7,
      request_key: "request-1",
      ...list.batches[0],
      mapping_snapshot: [{ mapping_id: "task-code", source_field: "task_code", canonical_field: "activity.id", status: "SUPPORTED" }],
      row_summaries: [{ row_index: 0, source_fields: ["task_code"], canonical_fields: ["activity.id"], preserved_extension_fields: [], source_value_hashes: {}, warnings: [] }],
    },
  };
  const detailClient = createP6InterchangeClient(
    transportWith({ ok: true, data: importEnvelope() }, {
      getResult: { ok: true, data: detail },
    }),
    CONTEXT,
  );
  const saved = await detailClient.getImportBatch("batch-1");
  assert.equal(saved.batch.batch_id, "batch-1");
  assert.equal(saved.batch.mapping_snapshot[0].mapping_id, "task-code");
});
