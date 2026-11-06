import assert from "node:assert/strict";
import test from "node:test";

import {
  describeInterchangeError,
  getInterchangePanelLabels,
  renderInterchangeExportResult,
  renderInterchangeImportResult,
  renderInterchangeImportBatchList,
  renderInterchangeImportBatchDetail,
  renderInterchangePanel,
} from "./p6-interchange-panel.js";

const ACTIVITIES = [
  { id: "A100", name: "Project kickoff" },
  { id: "A130", name: "Earthworks" },
];

test("interchange panel exposes export and import with bilingual labels", () => {
  const en = renderInterchangePanel(ACTIVITIES, getInterchangePanelLabels("en"));
  assert.match(en, /Import \/ Export|Provider format/);
  assert.match(en, /Provider XML/);
  assert.match(en, /data-interchange-export/);
  assert.match(en, /data-interchange-import/);
  assert.match(en, /data-interchange-activity-count="2"/);
  assert.match(en, /does not change activities/);
  assert.doesNotMatch(en, /Oracle|Primavera|\bP6\b|https?:\/\//i);

  const fa = renderInterchangePanel(ACTIVITIES, getInterchangePanelLabels("fa"));
  assert.match(fa, /قالب ارائه‌دهنده/);
  assert.match(fa, /نگاشت سند/);
  assert.match(fa, /فقط خواندنی/);
});

test("interchange panel shows an explicit empty export state", () => {
  const html = renderInterchangePanel([], getInterchangePanelLabels("en"));
  assert.match(html, /No activities are loaded to export/);
  assert.doesNotMatch(html, /data-interchange-export-form/);
  assert.match(html, /data-interchange-import-form/);
});

test("export result reports the generated document and a download link", () => {
  const html = renderInterchangeExportResult(
    {
      contract_version: "p6-interchange-api.v1",
      format: "PRIMAVERA_XML",
      document: { encoding: "utf-8", data: "<document/>" },
    },
    2,
    getInterchangePanelLabels("en"),
  );
  assert.match(html, /2 loaded activities/);
  assert.match(html, /UTF-8/);
  assert.match(html, /data-interchange-download/);
  assert.doesNotMatch(html, /Oracle|Primavera|\bP6\b|https?:\/\//i);
});

test("import result renders canonical values, provider object and warnings", () => {
  const html = renderInterchangeImportResult(
    {
      contract_version: "p6-interchange-api.v1",
      format: "PRIMAVERA_XML",
      rows: [
        {
          values: {
            "activity.id": "A130",
            "activity.name": "<script>alert(1)</script>",
          },
          extensions: { "p6.primavera.xml.object": "Activity" },
          warnings: ["PRESERVED_UNKNOWN_FIELD:Status"],
        },
      ],
    },
    getInterchangePanelLabels("en"),
  );
  assert.match(html, /1<\/strong> rows mapped by the server codec/);
  assert.match(html, /activity\.id/);
  assert.match(html, /A130/);
  assert.match(html, /&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
  assert.doesNotMatch(html, /<script>alert/);
  assert.match(html, /Provider object/);
  assert.match(html, /Activity/);
  assert.match(html, /PRESERVED_UNKNOWN_FIELD:Status/);
  assert.doesNotMatch(html, /Oracle|Primavera|\bP6\b|https?:\/\//i);
});

test("an imported document with no rows has an explicit empty state", () => {
  const html = renderInterchangeImportResult(
    {
      contract_version: "p6-interchange-api.v1",
      format: "PRIMAVERA_XML",
      rows: [],
    },
    getInterchangePanelLabels("en"),
  );
  assert.match(html, /The document contained no rows/);
  assert.doesNotMatch(html, /<table/);
});

test("server errors map to explicit permission, session, mapping and request states", () => {
  const labels = getInterchangePanelLabels("en");
  assert.match(
    describeInterchangeError(
      "authorization denied for permission=project:write",
      labels,
    ),
    /denied this operation/,
  );
  assert.match(describeInterchangeError("SESSION_NOT_FOUND", labels), /session/);
  assert.match(
    describeInterchangeError("MAPPING_REGISTRY_EMPTY", labels),
    /No provider mapping/,
  );
  assert.match(describeInterchangeError("INVALID_XML", labels), /rejected this document/);
  assert.match(describeInterchangeError("NETWORK_ERROR", labels), /could not be reached/);
});


test("import result reports durable batch receipt and no target application", () => {
  const html = renderInterchangeImportResult(
    {
      contract_version: "p6-interchange-api.v1",
      format: "PRIMAVERA_XML",
      rows: [],
      import_audit: {
        status: "recorded",
        target_application_status: "PARSED_NOT_APPLIED",
        batch_id: "batch-1",
        source_sha256: "a".repeat(64),
        source_byte_count: 120,
        row_count: 0,
        mapping_count: 3,
        warning_count: 0,
      },
    },
    getInterchangePanelLabels("en"),
  );
  assert.match(html, /Import audit receipt/);
  assert.match(html, /batch-1/);
  assert.match(html, /PARSED_NOT_APPLIED/);
  assert.match(html, /no project activities or resources were changed/);
  assert.match(html, /aaaa/);
});

test("import history list and batch detail render mapping and privacy-safe field evidence", () => {
  const labels = getInterchangePanelLabels("en");
  const history = renderInterchangeImportBatchList(
    {
      contract_version: "p6-interchange-api.v1",
      scope: { tenant_id: "t1", project_id: "preview-rps-01", project_revision: 7 },
      status: "available",
      batches: [{
        batch_id: "batch-1",
        format: "XER_PROJECT",
        source_sha256: "a".repeat(64),
        source_byte_count: 120,
        row_count: 1,
        mapping_count: 2,
        warning_count: 1,
        imported_by: "user-1",
        imported_at: "2026-11-04T20:00:00+00:00",
        target_application_status: "PARSED_NOT_APPLIED",
      }],
    },
    labels,
  );
  assert.match(history, /batch-1/);
  assert.match(history, /data-interchange-batch-id/);
  assert.match(history, /user-1/);

  const detail = renderInterchangeImportBatchDetail(
    {
      contract_version: "p6-interchange-api.v1",
      batch: {
        batch_id: "batch-1",
        tenant_id: "t1",
        project_id: "preview-rps-01",
        project_revision: 7,
        request_key: "request-1",
        format: "XER_PROJECT",
        source_sha256: "a".repeat(64),
        source_byte_count: 120,
        row_count: 1,
        mapping_count: 2,
        warning_count: 1,
        imported_by: "user-1",
        imported_at: "2026-11-04T20:00:00+00:00",
        target_application_status: "PARSED_NOT_APPLIED",
        mapping_snapshot: [{
          mapping_id: "task-code",
          source_field: "task_code",
          canonical_field: "activity.id",
          status: "SUPPORTED",
        }],
        row_summaries: [{
          row_index: 0,
          source_fields: ["task_code", "vendor_field"],
          canonical_fields: ["activity.id"],
          preserved_extension_fields: ["p6.interchange.vendor_field"],
          source_value_hashes: { task_code: "b".repeat(64) },
          warnings: ["PRESERVED_UNKNOWN_FIELD:vendor_field"],
        }],
      },
    },
    labels,
  );
  assert.match(detail, /task-code/);
  assert.match(detail, /task_code/);
  assert.match(detail, /activity\.id/);
  assert.match(detail, /PRESERVED_UNKNOWN_FIELD:vendor_field/);
  assert.match(detail, /Value hashes only/);
  assert.match(detail, /raw source values are not stored/);
});
