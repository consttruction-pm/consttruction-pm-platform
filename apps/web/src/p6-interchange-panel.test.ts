import assert from "node:assert/strict";
import test from "node:test";

import {
  describeInterchangeError,
  getInterchangePanelLabels,
  renderInterchangeExportResult,
  renderInterchangeImportResult,
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
